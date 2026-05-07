'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useStore } from '@/lib/store';
import { api } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import MessageBubble from '@/components/MessageBubble';
import { toast } from '@/components/Toast';

export default function AgentChatPage() {
  const router = useRouter();
  const params = useParams();
  const sessionId = params.sessionId as string;

  const {
    token,
    hydrate,
    user,
    agentMessages,
    setAgentMessages,
    addAgentMessage,
    updateLastAgentMessage,
    agentStreaming,
    setAgentStreaming,
  } = useStore();

  const [session, setSession] = useState<any>(null);
  const [agent, setAgent] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [input, setInput] = useState('');
  const [title, setTitle] = useState('');

  const abortRef = useRef<AbortController | null>(null);
  const msgEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    hydrate();
  }, []);

  useEffect(() => {
    if (!useStore.getState().token) {
      router.replace('/login');
      return;
    }
    if (sessionId) loadSession();
  }, [token, sessionId]);

  useEffect(() => {
    msgEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [agentMessages]);

  // Keyboard shortcut: focus input
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (
        e.key === '/' &&
        !e.ctrlKey &&
        !e.metaKey &&
        document.activeElement !== inputRef.current
      ) {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  const loadSession = async () => {
    setLoading(true);
    try {
      const [s, msgs] = await Promise.all([
        api.get<any>(`/agents/sessions/${sessionId}`),
        api.get<any[]>(`/agents/sessions/${sessionId}/messages`),
      ]);
      setSession(s);
      setTitle(s.title);
      setAgentMessages(Array.isArray(msgs) ? msgs : []);
      // Load agent info
      try {
        const a = await api.get<any>(`/agents/${s.agent_id}`);
        setAgent(a);
      } catch {}
    } catch {
      router.replace('/agents');
    }
    setLoading(false);
  };

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || sending || agentStreaming) return;
    setInput('');
    setSending(true);

    // Add user message to UI
    addAgentMessage({ role: 'user', content: text });
    // Add placeholder assistant message
    addAgentMessage({ role: 'assistant', content: '' });

    setAgentStreaming(true);
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/agents/sessions/${sessionId}/messages`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${api.getToken()}`,
          },
          body: JSON.stringify({ content: text }),
          signal: controller.signal,
        },
      );

      if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: '请求失败' }));
        throw new Error(err.detail || '请求失败');
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6));
              if (event.type === 'token') {
                updateLastAgentMessage(event.data);
              } else if (event.type === 'sources') {
                // Sources received, stored in store via the last message
              } else if (event.type === 'done') {
                // Reload to get proper messages with sources
                const msgs = await api.get<any[]>(`/agents/sessions/${sessionId}/messages`);
                setAgentMessages(Array.isArray(msgs) ? msgs : []);
                // Refresh session to get updated title
                const s = await api.get<any>(`/agents/sessions/${sessionId}`);
                setSession(s);
                setTitle(s.title);
              } else if (event.type === 'error') {
                toast(event.data || '服务错误', 'error');
              }
            } catch {}
          }
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        toast(e.message || '发送失败', 'error');
        // Remove empty assistant message on error
        const msgs = useStore.getState().agentMessages;
        const last = msgs[msgs.length - 1];
        if (last && last.role === 'assistant' && !last.content) {
          setAgentMessages(msgs.slice(0, -1));
        }
      }
    } finally {
      setAgentStreaming(false);
      setSending(false);
      abortRef.current = null;
    }
  };

  const stopGeneration = () => {
    abortRef.current?.abort();
    setAgentStreaming(false);
    setSending(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const renameSession = async () => {
    if (!title.trim() || title === session?.title) return;
    try {
      await api.patch(`/agents/sessions/${sessionId}`, { title: title.trim() });
      setSession((s: any) => ({ ...s, title: title.trim() }));
      toast('已重命名', 'success');
    } catch {}
  };

  if (loading) {
    return (
      <div className="flex h-screen">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-gray-400">加载中...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col pl-10 md:pl-0">
        {/* Header */}
        <div className="shrink-0 border-b bg-white px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => router.push(`/agents/${session?.agent_id}`)}
            className="text-gray-400 hover:text-gray-600 text-sm"
          >
            &larr;
          </button>
          <div className="flex-1 min-w-0 flex items-center gap-2">
            <span className="text-sm text-blue-600 font-medium shrink-0">{agent?.name}</span>
            <span className="text-gray-300">/</span>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onBlur={renameSession}
              className="text-sm font-medium bg-transparent border-none focus:outline-none focus:ring-0 p-0 truncate"
            />
          </div>
          <button
            onClick={() => router.push(`/agents/${session?.agent_id}`)}
            className="text-xs text-gray-400 hover:text-gray-600 shrink-0"
          >
            历史会话
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {agentMessages.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center max-w-md">
                <div className="text-5xl mb-4">🤖</div>
                <h2 className="text-lg font-semibold text-gray-700 mb-2">
                  与 {agent?.name || 'Agent'} 开始对话
                </h2>
                <p className="text-sm text-gray-400">
                  {agent?.description ||
                    '你可以向此 Agent 提问任何问题，它将基于关联的知识库进行回答。'}
                </p>
              </div>
            </div>
          ) : (
            agentMessages.map((msg, i) => (
              <MessageBubble
                key={msg.id || i}
                role={msg.role}
                content={msg.content}
                sources={msg.sources}
                msgId={msg.id}
                rating={msg.rating}
              />
            ))
          )}
          {agentStreaming && (
            <div className="text-center">
              <span className="inline-block w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
            </div>
          )}
          <div ref={msgEndRef} />
        </div>

        {/* Input */}
        <div className="shrink-0 border-t bg-white px-4 py-3">
          <div className="max-w-3xl mx-auto flex gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入消息… (Enter 发送, Shift+Enter 换行)"
              rows={1}
              disabled={agentStreaming}
              className="flex-1 resize-none text-sm border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            />
            {agentStreaming ? (
              <button
                onClick={stopGeneration}
                className="px-4 py-2 text-sm bg-red-500 text-white rounded-lg hover:bg-red-600 shrink-0"
              >
                停止
              </button>
            ) : (
              <button
                onClick={sendMessage}
                disabled={!input.trim() || sending}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 shrink-0"
              >
                发送
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
