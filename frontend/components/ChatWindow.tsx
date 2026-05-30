'use client';

import { useEffect, useRef, useState } from 'react';
import { useStore } from '@/lib/store';
import { api } from '@/lib/api';
import MessageBubble from './MessageBubble';
import InputBox from './InputBox';
import SourceViewer from './SourceViewer';
import GoalBar from './GoalBar';
import { MessageSquare } from 'lucide-react';
import { Message, Conversation } from '@/lib/store';

interface ApiMessage {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Message['sources'];
  rating?: number | null;
}

function mapApiMessages(msgs: ApiMessage[]): Message[] {
  return Array.isArray(msgs)
    ? msgs.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        sources: m.sources || undefined,
        rating: m.rating,
      }))
    : [];
}

export default function ChatWindow() {
  const {
    messages,
    addMessage,
    updateLastAssistant,
    resetLastAssistant,
    streaming,
    setStreaming,
    currentConvId,
    setCurrentConvId,
    setConversations,
    conversations,
    sources,
    setSources,
    chatError,
    setChatError,
    loadingMessages,
    setLoadingMessages,
    setMessages,
    setCachedMessages,
    messagesCache,
    activeSource,
    setActiveSource,
  } = useStore();
  const bottomRef = useRef<HTMLDivElement>(null);
  const [waitingFirstToken, setWaitingFirstToken] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const sendingRef = useRef(false);
  const messagesConvIdRef = useRef<string | null>(null);
  const [pendingGoal, setPendingGoal] = useState<string | null>(null);

  const currentConversation = conversations.find((c) => c.id === currentConvId);

  // 切换到已有对话时清理 pendingGoal
  useEffect(() => {
    if (currentConvId) {
      setPendingGoal(null);
    }
  }, [currentConvId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, waitingFirstToken]);

  useEffect(() => {
    if (!currentConvId) {
      setMessages([]);
      messagesConvIdRef.current = null;
      return;
    }
    if (streaming || sendingRef.current) return;
    if (messages.length > 0 && messagesConvIdRef.current === currentConvId) return;

    const cached = messagesCache[currentConvId];
    if (cached) {
      setMessages(cached);
      messagesConvIdRef.current = currentConvId;
      api
        .get<ApiMessage[]>(`/chat/conversations/${currentConvId}/messages`)
        .then((msgs) => {
          const mapped = mapApiMessages(msgs);
          setMessages(mapped);
          messagesConvIdRef.current = currentConvId;
          setCachedMessages(currentConvId, mapped);
        })
        .catch((e) => console.error('加载消息失败', e));
      return;
    }

    setLoadingMessages(true);
    api
      .get<ApiMessage[]>(`/chat/conversations/${currentConvId}/messages`)
      .then((msgs) => {
        const mapped = mapApiMessages(msgs);
        setMessages(mapped);
        messagesConvIdRef.current = currentConvId;
        setCachedMessages(currentConvId, mapped);
      })
      .catch((e) => setChatError(`加载失败: ${e instanceof Error ? e.message : '未知错误'}`))
      .finally(() => setLoadingMessages(false));
  }, [currentConvId, streaming]);

  const MAX_RETRIES = 3;
  const RETRY_DELAYS = [1000, 2000, 4000];

  /** 读取一个 SSE 流，返回是否收到 done 及服务端错误。没收到 done 且无服务端错误视为中断。 */
  const consumeStream = async (
    stream: ReadableStream,
    signal: AbortSignal,
  ): Promise<{ receivedDone: boolean; serverError?: string }> => {
    const reader = stream.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let receivedDone = false;
    let serverError: string | undefined;

    // abort 时立即 cancel reader，让阻塞中的 read() 抛出
    const onAbort = () => { reader.cancel().catch(() => {}); };
    signal.addEventListener('abort', onAbort, { once: true });

    try {
      const processLine = (line: string) => {
        if (!line.startsWith('data: ')) return;
        try {
          const event = JSON.parse(line.slice(6));
          if (event.type === 'token') {
            setWaitingFirstToken(false);
            updateLastAssistant(event.data);
          } else if (event.type === 'sources') {
            setSources(event.data);
          } else if (event.type === 'error') {
            serverError = event.data;
            setChatError(event.data);
          } else if (event.type === 'done') {
            receivedDone = true;
          }
        } catch {
          // SSE 帧解析失败跳过
        }
      };

      while (true) {
        if (signal.aborted) break;
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) processLine(line);
      }
      if (buffer.trim()) processLine(buffer);
    } finally {
      signal.removeEventListener('abort', onAbort);
    }

    // 服务端业务错误不视为网络中断
    if (!receivedDone && !signal.aborted && !serverError) {
      throw new Error('流式响应中断');
    }
    return { receivedDone, serverError };
  };

  const handleSend = async (content: string) => {
    const controller = new AbortController();
    abortRef.current = controller;
    addMessage({ role: 'user', content });
    addMessage({ role: 'assistant', content: '' });
    setSources([]);
    setChatError(null);
    setLoadingMessages(false);
    setStreaming(true);
    setWaitingFirstToken(true);
    sendingRef.current = true;

    const activeGoal = currentConvId
      ? (currentConversation?.goal || undefined)
      : (pendingGoal || undefined);

    try {
      let convId = currentConvId;
      if (!convId) {
        const conv = await api.post<{ id: string }>('/chat/conversations', {
          title: content.slice(0, 30),
          goal: pendingGoal || undefined,
        });
        convId = conv.id;
        setCurrentConvId(convId);
        messagesConvIdRef.current = convId;
        window.history.replaceState(null, '', `/chat/${convId}`);
        setConversations(await api.get<Conversation[]>('/chat/conversations'));
        setPendingGoal(null);
      }

      // 带重试的流式请求
      let lastError: Error | null = null;
      let succeeded = false;
      let serverErrorOccurred = false;
      for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
        if (controller.signal.aborted) break;

        try {
          // 重试前清空半截 assistant 内容
          if (attempt > 0) {
            resetLastAssistant();
          }
          const stream = await api.streamChat(
            convId!, content, controller.signal, undefined, activeGoal,
          );
          const result = await consumeStream(stream, controller.signal);
          // 服务端业务错误不重试
          if (result.serverError) {
            serverErrorOccurred = true;
            break;
          }
          succeeded = true;
          lastError = null;
          break;
        } catch (err: any) {
          if (controller.signal.aborted) throw err;
          lastError = err;

          if (attempt < MAX_RETRIES && !controller.signal.aborted) {
            setChatError('连接中断，正在重试...');
            setWaitingFirstToken(true);
            await new Promise((r) => setTimeout(r, RETRY_DELAYS[attempt]));
          }
        }
      }

      if (!succeeded && !serverErrorOccurred && lastError && !controller.signal.aborted) {
        setChatError(`回答中断: ${lastError.message}`);
      }
    } catch (err: any) {
      if (err.name !== 'AbortError' && !controller.signal.aborted) {
        setChatError(err.message);
      }
    } finally {
      sendingRef.current = false;
      setStreaming(false);
      setWaitingFirstToken(false);
      abortRef.current = null;
      api
        .get<Conversation[]>('/chat/conversations')
        .then(setConversations)
        .catch((e) => console.error('加载对话失败', e));
    }
  };

  const handleStop = () => abortRef.current?.abort();

  const handleRate = async (msgId: string, rating: number) => {
    try {
      await api.patch(`/chat/messages/${msgId}/rating`, { rating });
      useStore.setState((s) => ({
        messages: s.messages.map((m) => (m.id === msgId ? { ...m, rating } : m)),
      }));
    } catch (e) {
      console.error('评分失败:', e);
    }
  };

  return (
    <div className="flex flex-col h-screen" style={{ background: 'var(--c-bg)' }}>
      <div className="flex-1 overflow-y-auto px-4 md:px-6">
        <div className="max-w-3xl mx-auto py-6">
          {/* 目标状态条 */}
          <GoalBar
            conversation={currentConversation}
            pendingGoal={pendingGoal}
            onGoalChange={(goal) => {
              if (currentConvId) {
                setConversations(
                  conversations.map((c) =>
                    c.id === currentConvId ? { ...c, goal, goal_status: 'active', goal_summary: null, missing_info: [] } : c
                  )
                );
              } else {
                setPendingGoal(goal);
              }
            }}
          />

          {messages.length > 0 ? (
            <>
              {messages.map((msg, i) => (
                <MessageBubble
                  key={msg.id || i}
                  role={msg.role}
                  content={msg.content}
                  sources={
                    msg.role === 'assistant' && i === messages.length - 1 && sources.length > 0
                      ? sources
                      : msg.sources
                  }
                  msgId={msg.id}
                  rating={msg.rating}
                  onSourceClick={(d, c) => setActiveSource({ documentId: d, chunkId: c })}
                  onRate={handleRate}
                />
              ))}
              {waitingFirstToken && (
                <div className="flex items-center gap-3 px-4 py-3 mb-4 animate-fade-in">
                  <div className="thinking-dots">
                    <span />
                    <span />
                    <span />
                  </div>
                  <span className="text-sm" style={{ color: 'var(--c-text-tertiary)' }}>
                    正在检索文档并生成回答...
                  </span>
                </div>
              )}
            </>
          ) : loadingMessages ? (
            <div className="space-y-6 py-8 px-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <div
                  key={i}
                  className={`flex ${i % 2 === 0 ? 'justify-end' : 'justify-start'} animate-fade-in`}
                  style={{ animationDelay: `${i * 100}ms` }}
                >
                  <div
                    className={`${i % 2 === 0 ? 'w-[60%]' : 'w-[75%]'} rounded-2xl px-4 py-3 ${i % 2 === 0 ? 'bg-blue-100' : 'bg-white border'}`}
                  >
                    <div className="skeleton h-4 mb-2" style={{ width: `${70 + (i % 3) * 10}%` }} />
                    <div className="skeleton h-4" style={{ width: `${50 + (i % 2) * 20}%` }} />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center min-h-[60vh] animate-fade-in">
              <div
                className="w-20 h-20 rounded-2xl flex items-center justify-center mb-6"
                style={{ background: 'var(--c-primary-subtle)', color: 'var(--c-primary)' }}
              >
                <MessageSquare className="w-10 h-10" />
              </div>
              <h2 className="text-xl font-semibold mb-1.5 tracking-tight">欢迎使用 KnowFlow</h2>
              <p className="text-sm mb-8" style={{ color: 'var(--c-text-tertiary)' }}>
                上传文档后，向我提问吧
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-lg px-4">
                {[
                  '公司的考勤制度是什么？',
                  '项目技术架构是怎样的？',
                  '本季度有哪些关键成果？',
                  '员工信息表中各部门人数？',
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => handleSend(q)}
                    className="text-left px-4 py-3 rounded-xl border text-sm transition-all border-none cursor-pointer animate-slide-up"
                    style={{
                      background: 'var(--c-surface)',
                      color: 'var(--c-text-secondary)',
                      borderColor: 'var(--c-border)',
                      boxShadow: 'var(--shadow-sm)',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'var(--c-primary)';
                      e.currentTarget.style.color = 'var(--c-primary)';
                      e.currentTarget.style.boxShadow = '0 0 0 2px var(--c-primary-ring)';
                      e.currentTarget.style.transform = 'translateY(-1px)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'var(--c-border)';
                      e.currentTarget.style.color = 'var(--c-text-secondary)';
                      e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                      e.currentTarget.style.transform = 'translateY(0)';
                    }}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {chatError && (
        <div
          className="mx-4 mb-2 px-4 py-2.5 rounded-xl flex items-center justify-between animate-slide-up"
          style={{
            background: 'var(--c-error-subtle)',
            color: 'var(--c-error)',
            border: '1px solid rgba(220,38,38,.15)',
          }}
        >
          <span className="text-sm">{chatError}</span>
          <button
            onClick={() => setChatError(null)}
            className="text-sm font-medium ml-3 border-none cursor-pointer opacity-60 hover:opacity-100 transition-opacity"
            style={{ color: 'var(--c-error)', background: 'none' }}
          >
            ✕
          </button>
        </div>
      )}

      <InputBox
        onSend={handleSend}
        disabled={streaming}
        onStop={handleStop}
        streaming={streaming}
      />

      {activeSource && (
        <SourceViewer
          documentId={activeSource.documentId}
          highlightChunkId={activeSource.chunkId}
          onClose={() => setActiveSource(null)}
        />
      )}
    </div>
  );
}
