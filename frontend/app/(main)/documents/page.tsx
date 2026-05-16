'use client';

import { useState, useEffect } from 'react';
import { useStore } from '@/lib/store';
import { api } from '@/lib/api';
import DocList from '@/components/DocList';
import { Search, RefreshCw } from 'lucide-react';

interface KB {
  id: string;
  name: string;
  description: string;
}

export default function DocumentsPage() {
  const { token, _hydrated, kbs, setKbs } = useStore();
  const [refreshKey, setRefreshKey] = useState(0);
  const [currentKbId, setCurrentKbId] = useState<string>('');
  const [showCreateKb, setShowCreateKb] = useState(false);
  const [newKbName, setNewKbName] = useState('');
  const [searchVal, setSearchVal] = useState('');

  useEffect(() => {
    if (!token) return;
    if (!kbs.length) {
      api
        .get<KB[]>('/knowledge-bases')
        .then((items) => setKbs(Array.isArray(items) ? items : []))
        .catch(() => {});
    }
  }, [token]);
  useEffect(() => {
    if (kbs.length > 0 && !currentKbId) setCurrentKbId(kbs[0].id);
  }, [kbs]);

  const createKb = async () => {
    if (!newKbName.trim()) return;
    try {
      const kb = await api.post<any>('/knowledge-bases', { name: newKbName.trim() });
      setKbs((prev) => [...prev, kb]);
      setCurrentKbId(kb.id);
      setNewKbName('');
      setShowCreateKb(false);
    } catch {}
  };

  if (!_hydrated || !token) return null;

  return (
    <div className="flex flex-col h-full overflow-hidden" style={{ background: 'var(--c-bg)' }}>
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header
          className="shrink-0 px-6 md:px-8 py-4 flex items-center justify-between gap-3 flex-wrap z-10"
          style={{
            background: 'rgba(255,255,255,.88)',
            backdropFilter: 'blur(8px)',
            borderBottom: '1px solid var(--c-border)',
          }}
        >
          <h2 className="text-xl md:text-2xl font-bold" style={{ letterSpacing: '-0.3px' }}>
            文档管理
          </h2>
          <div className="flex items-center gap-2.5">
            <div className="relative">
              <Search
                className="absolute left-3 top-1/2 -translate-y-1/2"
                style={{ width: 16, height: 16, color: 'var(--c-text-tertiary)' }}
              />
              <input
                value={searchVal}
                onChange={(e) => setSearchVal(e.target.value)}
                placeholder="搜索文档标题..."
                className="rounded-md text-sm input-base"
                style={{
                  width: 220,
                  padding: '8px 12px 8px 36px',
                  border: '1px solid var(--c-border)',
                  background: 'var(--c-bg)',
                  color: 'var(--c-text)',
                }}
              />
            </div>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 md:px-8 py-6">
          <div className="max-w-3xl mx-auto">
            {/* Toolbar Card */}
            <div
              className="mb-4 rounded-xl p-4"
              style={{
                background: 'rgba(255,255,255,.86)',
                border: '1px solid var(--c-border)',
                boxShadow: 'var(--shadow-sm)',
              }}
            >
              <div className="flex items-center gap-2.5 flex-wrap">
                <select
                  value={currentKbId}
                  onChange={(e) => setCurrentKbId(e.target.value)}
                  className="rounded-md text-sm input-base cursor-pointer"
                  style={{
                    padding: '7px 32px 7px 12px',
                    border: '1px solid var(--c-border)',
                    background: 'var(--c-surface)',
                    color: 'var(--c-text)',
                    appearance: 'none',
                    backgroundImage:
                      "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%236b7280' viewBox='0 0 16 16'%3E%3Cpath d='M4 6l4 4 4-4'/%3E%3C/svg%3E\")",
                    backgroundRepeat: 'no-repeat',
                    backgroundPosition: 'right 10px center',
                  }}
                >
                  {kbs.map((kb) => (
                    <option key={kb.id} value={kb.id}>
                      {kb.name}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => setShowCreateKb(!showCreateKb)}
                  className="ml-1 px-3 py-1.5 text-xs font-medium rounded-lg border-none cursor-pointer transition-all"
                  style={{ background: 'var(--c-primary)', color: '#fff' }}
                >
                  新建知识库
                </button>
                <button
                  onClick={() => setRefreshKey((k) => k + 1)}
                  className="ml-auto p-1.5 rounded-md border-none cursor-pointer transition-colors"
                  style={{ color: 'var(--c-text-secondary)', background: 'transparent' }}
                  title="刷新"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>

              {/* Quick Stats */}
              <div
                className="mt-2.5 pt-2.5 border-t border-dashed"
                style={{ borderColor: 'var(--c-border)' }}
              >
                <DocStats refreshKey={refreshKey} kbId={currentKbId} />
              </div>
            </div>

            {/* Create KB */}
            {showCreateKb && (
              <div
                className="flex items-center gap-2 mb-4 p-3 rounded-lg"
                style={{ background: 'var(--c-primary-subtle)', border: '1px solid #bfdbfe' }}
              >
                <input
                  value={newKbName}
                  onChange={(e) => setNewKbName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && createKb()}
                  placeholder="知识库名称"
                  className="flex-1 text-sm border rounded px-2 py-1.5 input-base"
                  style={{ borderColor: 'var(--c-border)', color: 'var(--c-text)' }}
                  autoFocus
                />
                <button
                  onClick={createKb}
                  className="px-3 py-1.5 text-sm text-white rounded border-none cursor-pointer"
                  style={{ background: 'var(--c-primary)' }}
                >
                  创建
                </button>
                <button
                  onClick={() => setShowCreateKb(false)}
                  className="text-sm border-none cursor-pointer"
                  style={{ color: 'var(--c-text-tertiary)', background: 'none' }}
                >
                  取消
                </button>
              </div>
            )}

            {/* DocList */}
            <DocList refreshKey={refreshKey} kbId={currentKbId} searchProp={searchVal} />
          </div>
        </div>
      </div>

    </div>
  );
}

/* 独立统计组件 */
function DocStats({ refreshKey, kbId }: { refreshKey: number; kbId?: string }) {
  const [stats, setStats] = useState({ all: 0, indexed: 0, processing: 0, others: 0 });
  useEffect(() => {
    api
      .get<any>(`/documents${kbId ? `?kb_id=${kbId}` : ''}`)
      .then((res) => {
        const items = Array.isArray(res?.items) ? res.items : [];
        setStats({
          all: items.length,
          indexed: items.filter((d: any) => d.status === 'indexed').length,
          processing: items.filter((d: any) => d.status === 'processing').length,
          others: items.filter((d: any) => !['indexed', 'processing'].includes(d.status)).length,
        });
      })
      .catch(() => {});
  }, [refreshKey, kbId]);

  return (
    <div className="grid grid-cols-4 gap-2">
      {[
        { label: '总计', value: stats.all, color: 'var(--c-text)' },
        { label: '已索引', value: stats.indexed, color: 'var(--c-success)' },
        { label: '处理中', value: stats.processing, color: 'var(--c-warning)' },
        { label: '异常/等待', value: stats.others, color: 'var(--c-text-tertiary)' },
      ].map((s) => (
        <div
          key={s.label}
          className="rounded-lg px-2.5 py-2"
          style={{ border: '1px solid var(--c-border)', background: '#fff' }}
        >
          <span
            className="block text-xs"
            style={{ color: 'var(--c-text-tertiary)', lineHeight: 1.2 }}
          >
            {s.label}
          </span>
          <span className="block mt-1 text-lg font-bold" style={{ color: s.color, lineHeight: 1 }}>
            {s.value}
          </span>
        </div>
      ))}
    </div>
  );
}
