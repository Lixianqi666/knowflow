'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useStore } from '@/lib/store';
import { api } from '@/lib/api';

export default function AgentsPage() {
  const router = useRouter();
  const { token, user, agents, setAgents } = useStore();
  const [loading, setLoading] = useState(!agents.length);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ name: '', description: '', system_prompt: '' });

  useEffect(() => {
    if (!token) return;
    loadAgents();
  }, [token]);

  const loadAgents = async () => {
    if (useStore.getState().agents.length) return;
    setLoading(true);
    try {
      const items = await api.get<any[]>('/agents/');
      setAgents(Array.isArray(items) ? items : []);
    } catch {}
    setLoading(false);
  };

  const createAgent = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      const agent = await api.post<any>('/agents/', {
        name: form.name.trim(),
        description: form.description.trim(),
        system_prompt: form.system_prompt.trim(),
        is_active: true,
      });
      setAgents([...agents, agent]);
      setShowForm(false);
      setForm({ name: '', description: '', system_prompt: '' });
    } catch (e: any) {
      alert(e.message || '创建失败');
    }
    setSaving(false);
  };

  const isAdmin = user?.role === 'admin';

  return (
    <div className="h-full p-4 md:p-8 pt-14 md:pt-8 overflow-y-auto">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-xl md:text-2xl font-bold">Agent 应用</h1>
          {isAdmin && (
            <button
              onClick={() => setShowForm(!showForm)}
              className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              {showForm ? '取消' : '新建 Agent'}
            </button>
          )}
        </div>
        <p className="text-sm text-gray-500 mb-6">
          选择 Agent 开始对话，每个 Agent 拥有独立的知识库和对话会话
        </p>

        {showForm && (
          <div className="bg-white rounded-xl border p-6 mb-6">
            <h2 className="font-semibold text-sm mb-4">新建 Agent</h2>
            <div className="space-y-3">
              <input
                type="text"
                placeholder="Agent 名称 *"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg text-sm input-base"
              />
              <input
                type="text"
                placeholder="描述（可选）"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg text-sm input-base"
              />
              <textarea
                placeholder="系统提示词（可选）"
                value={form.system_prompt}
                onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
                rows={3}
                className="w-full px-3 py-2 border rounded-lg text-sm input-base resize-none"
              />
              <button
                onClick={createAgent}
                disabled={saving || !form.name.trim()}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {saving ? '创建中...' : '确认创建'}
              </button>
            </div>
          </div>
        )}

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
            {isAdmin && (
              <p className="text-gray-400 text-xs mt-1">点击上方「新建 Agent」按钮创建</p>
            )}
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
