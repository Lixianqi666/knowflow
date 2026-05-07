'use client';

import { useEffect, useRef, useState } from 'react';
import { useStore } from '@/lib/store';
import { api } from '@/lib/api';
import MessageBubble from './MessageBubble';
import InputBox from './InputBox';
import SourceViewer from './SourceViewer';

export default function ChatWindow() {
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
      .catch(() => {}); // 模板无强制要求，静默失败
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, waitingFirstToken]);

  // 会话恢复
  useEffect(() => {
    if (!currentConvId) return;
    setLoadingMessages(true);
    setChatError(null);
    api
      .get<any[]>(`/chat/conversations/${currentConvId}/messages`)
      .then((msgs) => {
        const items = Array.isArray(msgs) ? msgs : [];
        setMessages(
          items.map((m: any) => ({
            id: m.id,
            role: m.role,
            content: m.content,
            sources: m.sources || undefined,
            rating: m.rating,
          })),
        );
      })
      .catch((e) => setChatError(`加载历史消息失败: ${e.message}`))
      .finally(() => setLoadingMessages(false));
  }, [currentConvId]);

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
        const convs = await api.get<any[]>('/chat/conversations');
        setConversations(convs);
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
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
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
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setChatError(err.message);
      }
    } finally {
      setStreaming(false);
      setWaitingFirstToken(false);
      abortRef.current = null;
      // 刷新会话列表（可能标题已更新）
      api
        .get<any[]>('/chat/conversations')
        .then(setConversations)
        .catch(() => {});
    }
  };

  const handleStop = () => {
    abortRef.current?.abort();
  };

  const handleRate = async (msgId: string, rating: number) => {
    try {
      await api.patch(`/chat/messages/${msgId}/rating`, { rating });
      useStore.setState((s) => ({
        messages: s.messages.map((m) => (m.id === msgId ? { ...m, rating } : m)),
      }));
    } catch {}
  };

  return (
    <div className="flex flex-col h-screen">
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {messages.length === 0 && !loadingMessages ? (
          <div className="flex flex-col items-center justify-center h-full">
            <div className="text-5xl mb-4">📚</div>
            <h2 className="text-xl font-semibold mb-2 text-gray-800">欢迎使用 KnowFlow</h2>
            <p className="text-sm text-gray-400 mb-8">上传文档后，向我提问吧</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full px-4">
              {[
                '公司的考勤制度是什么？',
                '项目技术架构是怎样的？',
                '本季度有哪些关键成果？',
                '员工信息表中各部门人数？',
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => handleSend(q)}
                  className="text-left px-4 py-3 bg-white border rounded-xl text-sm text-gray-600 hover:border-blue-400 hover:text-blue-600 transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : loadingMessages ? (
          <div className="max-w-2xl mx-auto space-y-6 py-8 px-4">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className={`flex ${i % 2 === 0 ? 'justify-end' : 'justify-start'}`}>
                <div className={`${i % 2 === 0 ? 'w-[60%]' : 'w-[75%]'}`}>
                  <div
                    className={`rounded-2xl px-4 py-3 ${i % 2 === 0 ? 'bg-blue-100' : 'bg-gray-100'}`}
                  >
                    <div className="skeleton h-4 mb-2" style={{ width: `${70 + (i % 3) * 10}%` }} />
                    <div className="skeleton h-4" style={{ width: `${50 + (i % 2) * 20}%` }} />
                  </div>
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
                onSourceClick={(documentId, chunkId) => setActiveSource({ documentId, chunkId })}
                onRate={handleRate}
              />
            ))}
            {/* 等待首个 token 时显示思考指示 */}
            {waitingFirstToken && (
              <div className="flex items-center gap-2 text-gray-400 text-sm mb-4 px-4">
                <span className="inline-block w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
                正在检索文档并生成回答...
              </div>
            )}
          </>
        )}
        <div ref={bottomRef} />
      </div>

      {/* 场景切换 */}
      {templates.length > 1 && (
        <div className="flex items-center gap-2 mx-4 mb-2">
          <span className="text-xs text-gray-400">场景：</span>
          <select
            value={activeTemplate}
            onChange={(e) => setActiveTemplate(e.target.value)}
            className="text-xs border rounded px-2 py-1 text-gray-600 bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            {templates.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
          <span className="text-[10px] text-gray-400 truncate">
            {templates.find((t) => t.id === activeTemplate)?.description}
          </span>
        </div>
      )}

      {/* 错误提示 */}
      {chatError && (
        <div className="mx-4 mb-2 px-4 py-2 bg-red-50 border border-red-200 rounded-lg flex items-center justify-between">
          <span className="text-sm text-red-600">{chatError}</span>
          <button
            onClick={() => setChatError(null)}
            className="text-red-400 hover:text-red-600 text-sm"
          >
            ✕
          </button>
        </div>
      )}

      {streaming && (
        <div className="flex justify-center mb-2">
          <button
            onClick={handleStop}
            className="px-4 py-1.5 text-xs font-medium text-red-600 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors"
          >
            停止生成
          </button>
        </div>
      )}

      <InputBox onSend={handleSend} disabled={streaming} />

      {/* 源文档查看器 */}
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
