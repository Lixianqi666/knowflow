'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useStore } from '@/lib/store';
import { api } from '@/lib/api';

export default function AgentDetailPage() {
  const router = useRouter();
  const params = useParams();
  const agentId = params.agentId as string;
  const { token, agentSessions, setAgentSessions, setCurrentAgentId } = useStore();
  const [agent, setAgent] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (!token) return;
    loadData();
  }, [token, agentId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [a, sessions] = await Promise.all([
        api.get<any>(`/agents/${agentId}`),
        api.get<any[]>(`/agents/${agentId}/sessions`),
      ]);
      setAgent(a);
      setAgentSessions(Array.isArray(sessions) ? sessions : []);
      setCurrentAgentId(agentId);
    } catch {
      router.replace('/agents');
    }
    setLoading(false);
  };

  const createSession = async () => {
    setCreating(true);
    try {
      const session = await api.post<any>(`/agents/${agentId}/sessions`, { title: '新会话' });
      setCreating(false);
      router.push(`/agents/sessions/${session.id}`);
    } catch {
      setCreating(false);
    }
  };

  const deleteSession = async (e: React.MouseEvent, sessionId: string) => {
    e.stopPropagation();
    if (!confirm('确定删除此会话？')) return;
    try {
      await api.delete(`/agents/sessions/${sessionId}`);
      setAgentSessions(agentSessions.filter((s) => s.id !== sessionId));
    } catch {}
  };

  return (
    <div className="h-full p-4 md:p-8 pt-14 md:pt-8 overflow-y-auto">
      <div className="max-w-3xl mx-auto">
        {loading ? (
          <div className="space-y-4">
            <div className="skeleton h-8 w-48 mb-2" />
            <div className="skeleton h-4 w-64 mb-6" />
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="skeleton h-16 w-full rounded-xl" />
            ))}
          </div>
        ) : agent ? (
          <>
            <button
              onClick={() => router.push('/agents')}
              className="text-sm text-gray-500 hover:text-gray-700 mb-4 block"
            >
              &larr; 返回 Agent 列表
            </button>

            <div className="bg-white rounded-xl border p-6 mb-6">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center text-2xl">
                  🤖
                </div>
                <div>
                  <h1 className="text-xl font-bold">{agent.name}</h1>
                  {agent.description && (
                    <p className="text-sm text-gray-500">{agent.description}</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-3 text-xs text-gray-400">
                <span>top_k={agent.top_k}</span>
                <span>阈值={agent.threshold}%</span>
                <span>重排={agent.rerank_top_k}</span>
              </div>
            </div>

            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-sm text-gray-700">历史会话</h2>
              <button
                onClick={createSession}
                disabled={creating}
                className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {creating ? '创建中...' : '新会话'}
              </button>
            </div>

            {agentSessions.length === 0 ? (
              <div className="py-12 text-center text-gray-400 text-sm">
                暂无会话，点击上方按钮开始新对话
              </div>
            ) : (
              <div className="space-y-2">
                {agentSessions.map((s) => (
                  <button
                    key={s.id}
                    onClick={() => router.push(`/agents/sessions/${s.id}`)}
                    className="w-full bg-white rounded-xl border p-4 text-left hover:shadow-sm transition-shadow"
                  >
                    <div className="flex items-center justify-between">
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-medium truncate">{s.title}</div>
                        <div className="text-xs text-gray-400 mt-0.5">
                          {new Date(s.created_at).toLocaleString()}
                        </div>
                      </div>
                      <button
                        onClick={(e) => deleteSession(e, s.id)}
                        className="ml-2 text-gray-300 hover:text-red-500 text-xs shrink-0"
                      >
                        删除
                      </button>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </>
        ) : null}
      </div>
    </div>
  );
}
