'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useStore } from '@/lib/store';
import { api } from '@/lib/api';
import MessageBubble from './MessageBubble';
import InputBox from './InputBox';
import SourceViewer from './SourceViewer';
import { MessageSquare } from 'lucide-react';

export default function ChatWindow() {
  const router = useRouter();
  const {
    messages,
    addMessage,
    updateLastAssistant,
    streaming,
    setStreaming,
    currentConvId,
    setCurrentConvId,
    setConversations,
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
  const [templates, setTemplates] = useState<{ id: string; name: string; description: string }[]>(
    [],
  );
  const [activeTemplate, setActiveTemplate] = useState('');

  useEffect(() => {
    api
      .get<any[]>('/prompt-templates/')
      .then((ts) => {
        const items = Array.isArray(ts) ? ts : [];
        setTemplates(items);
        if (items.length > 0) setActiveTemplate(items[0].id);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, waitingFirstToken]);

  useEffect(() => {
    if (!currentConvId) return;
    if (streaming) return;

    // 有缓存时直接使用，不显示加载状态
    const cached = messagesCache[currentConvId];
    if (cached) {
      setMessages(cached);
      // 后台静默刷新
      api
        .get<any[]>(`/chat/conversations/${currentConvId}/messages`)
        .then((msgs) => {
          const mapped = Array.isArray(msgs)
            ? msgs.map((m: any) => ({
                id: m.id,
                role: m.role,
                content: m.content,
                sources: m.sources || undefined,
                rating: m.rating,
              }))
            : [];
          setMessages(mapped);
          setCachedMessages(currentConvId, mapped);
        })
        .catch(() => {});
      return;
    }

    // 无缓存时显示加载状态
    setLoadingMessages(true);
    api
      .get<any[]>(`/chat/conversations/${currentConvId}/messages`)
      .then((msgs) => {
        const mapped = Array.isArray(msgs)
          ? msgs.map((m: any) => ({
              id: m.id,
              role: m.role,
              content: m.content,
              sources: m.sources || undefined,
              rating: m.rating,
            }))
          : [];
        setMessages(mapped);
        setCachedMessages(currentConvId, mapped);
      })
      .catch((e) => setChatError(`加载失败: ${e.message}`))
      .finally(() => setLoadingMessages(false));
  }, [currentConvId, streaming]);

  const handleSend = async (content: string) => {
    const controller = new AbortController();
    abortRef.current = controller;
    addMessage({ role: 'user', content });
    addMessage({ role: 'assistant', content: '' });
    setSources([]);
    setChatError(null);
    setStreaming(true);
    setWaitingFirstToken(true);

    try {
      let convId = currentConvId;
      if (!convId) {
        const conv = await api.post<any>('/chat/conversations', { title: content.slice(0, 30) });
        convId = conv.id;
        setCurrentConvId(convId);
        router.replace(`/chat/${convId}`);
        setConversations(await api.get<any[]>('/chat/conversations'));
      }
      const stream = await api.streamChat(
        convId!,
        content,
        controller.signal,
        activeTemplate || undefined,
      );
      const reader = stream.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        for (const line of buffer.split('\n')) {
          if (!line.startsWith('data: ')) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if (event.type === 'token') {
              setWaitingFirstToken(false);
              updateLastAssistant(event.data);
            } else if (event.type === 'sources') {
              setSources(event.data);
            } else if (event.type === 'error') {
              setChatError(event.data);
            }
          } catch {}
        }
        buffer = '';
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') setChatError(err.message);
    } finally {
      setStreaming(false);
      setWaitingFirstToken(false);
      abortRef.current = null;
      api
        .get<any[]>('/chat/conversations')
        .then(setConversations)
        .catch(() => {});
    }
  };

  const handleStop = () => abortRef.current?.abort();

  const handleRate = async (msgId: string, rating: number) => {
    try {
      await api.patch(`/chat/messages/${msgId}/rating`, { rating });
      useStore.setState((s) => ({
        messages: s.messages.map((m) => (m.id === msgId ? { ...m, rating } : m)),
      }));
    } catch {}
  };

  return (
    <div className="flex flex-col h-screen" style={{ background: 'var(--c-bg)' }}>
      <div className="flex-1 overflow-y-auto px-4 md:px-6">
        <div className="max-w-3xl mx-auto py-6">
          {messages.length === 0 && !loadingMessages ? (
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
            <>
              {messages.map((msg, i) => (
                <MessageBubble
                  key={i}
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
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {templates.length > 1 && (
        <div className="flex items-center justify-center gap-2 px-4 pb-1">
          <span className="text-xs" style={{ color: 'var(--c-text-tertiary)' }}>
            场景：
          </span>
          <select
            value={activeTemplate}
            onChange={(e) => setActiveTemplate(e.target.value)}
            className="text-xs rounded-lg px-2 py-1.5 border input-base cursor-pointer"
            style={{
              borderColor: 'var(--c-border)',
              color: 'var(--c-text-secondary)',
              background: 'var(--c-surface)',
            }}
          >
            {templates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </div>
      )}

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
