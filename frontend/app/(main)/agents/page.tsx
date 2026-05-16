'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useStore } from '@/lib/store';
import { api } from '@/lib/api';

export default function AgentsPage() {
  const router = useRouter();
  const { token, agents, setAgents } = useStore();
  const [loading, setLoading] = useState(!agents.length);

  useEffect(() => {
    if (!token) return;
    loadAgents();
  }, [token]);

  const loadAgents = async () => {
    if (useStore.getState().agents.length) return;
    setLoading(true);
    try {
      const items = await api.get<any[]>('/agents');
      setAgents(Array.isArray(items) ? items : []);
    } catch {}
    setLoading(false);
  };

  return (
    <div className="h-full p-4 md:p-8 pt-14 md:pt-8 overflow-y-auto">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-xl md:text-2xl font-bold mb-2">Agent 应用</h1>
        <p className="text-sm text-gray-500 mb-6">
          选择 Agent 开始对话，每个 Agent 拥有独立的知识库和对话会话
        </p>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="bg-white rounded-xl border p-6">
                <div className="skeleton h-5 w-32 mb-3" />
                <div className="skeleton h-4 w-full mb-2" />
                <div className="skeleton h-4 w-3/4" />
              </div>
            ))}
          </div>
        ) : agents.length === 0 ? (
          <div className="py-16 text-center">
            <div className="text-4xl mb-3">🤖</div>
            <p className="text-gray-400 text-sm">暂无可用 Agent</p>
            <p className="text-gray-400 text-xs mt-1">请联系管理员创建 Agent</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {agents.map((agent) => (
              <button
                key={agent.id}
                onClick={() => router.push(`/agents/${agent.id}`)}
                className="bg-white rounded-xl border p-6 text-left hover:shadow-md hover:border-blue-200 transition-all"
              >
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-lg">
                    🤖
                  </div>
                  <div>
                    <div className="font-semibold text-sm">{agent.name}</div>
                    {agent.description && (
                      <div className="text-xs text-gray-400">{agent.description}</div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <span>top_k={agent.top_k}</span>
                  <span>阈值={agent.threshold}%</span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
