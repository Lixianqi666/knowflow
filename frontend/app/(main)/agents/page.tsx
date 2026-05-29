'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useStore, Agent } from '@/lib/store';
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
      const items = await api.get<Agent[]>('/agents/');
      setAgents(Array.isArray(items) ? items : []);
    } catch (e) {
      console.error('加载 Agent 列表失败:', e);
    }
    setLoading(false);
  };

  const createAgent = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      const agent = await api.post<Agent>('/agents/', {
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
              className="px-4 py-2 text-sm text-white rounded-lg transition-colors"
              style={{ background: 'var(--c-primary)' }}
            >
              {showForm ? '取消' : '新建 Agent'}
            </button>
          )}
        </div>
        <p className="text-sm mb-6" style={{ color: 'var(--c-text-secondary)' }}>
          选择 Agent 开始对话，每个 Agent 拥有独立的知识库和对话会话
        </p>

        {showForm && (
          <div
            className="rounded-xl border p-6 mb-6"
            style={{ background: 'var(--c-surface)', borderColor: 'var(--c-border)' }}
          >
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
                className="px-4 py-2 text-sm text-white rounded-lg disabled:opacity-50 transition-colors"
                style={{ background: 'var(--c-primary)' }}
              >
                {saving ? '创建中...' : '确认创建'}
              </button>
            </div>
          </div>
        )}

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="rounded-xl border p-6"
                style={{ background: 'var(--c-surface)', borderColor: 'var(--c-border)' }}
              >
                <div className="skeleton h-5 w-32 mb-3" />
                <div className="skeleton h-4 w-full mb-2" />
                <div className="skeleton h-4 w-3/4" />
              </div>
            ))}
          </div>
        ) : agents.length === 0 ? (
          <div className="py-16 text-center">
            <div className="text-4xl mb-3">🤖</div>
            <p className="text-sm" style={{ color: 'var(--c-text-secondary)' }}>暂无可用 Agent</p>
            {isAdmin && (
              <p className="text-xs mt-1" style={{ color: 'var(--c-text-tertiary)' }}>
                点击上方「新建 Agent」按钮创建
              </p>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {agents.map((agent) => (
              <button
                key={agent.id}
                onClick={() => router.push(`/agents/${agent.id}`)}
                className="rounded-xl border p-6 text-left hover:shadow-md transition-all"
                style={{
                  background: 'var(--c-surface)',
                  borderColor: 'var(--c-border)',
                }}
              >
                <div className="flex items-center gap-3 mb-3">
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center text-lg"
                    style={{ background: 'var(--c-primary-subtle)' }}
                  >
                    🤖
                  </div>
                  <div>
                    <div className="font-semibold text-sm">{agent.name}</div>
                    {agent.description && (
                      <div className="text-xs" style={{ color: 'var(--c-text-secondary)' }}>
                        {agent.description}
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--c-text-tertiary)' }}>
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
