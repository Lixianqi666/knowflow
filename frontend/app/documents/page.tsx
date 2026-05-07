'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useStore } from '@/lib/store';
import { api } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import UploadDialog from '@/components/UploadDialog';
import DocList from '@/components/DocList';
import { Search, Plus, RefreshCw } from 'lucide-react';

interface KB {
  id: string;
  name: string;
  description: string;
}

export default function DocumentsPage() {
  const router = useRouter();
  const { token, hydrate, _hydrated } = useStore();
  const [showUpload, setShowUpload] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [dragging, setDragging] = useState(false);
  const [kbs, setKbs] = useState<KB[]>([]);
  const [currentKbId, setCurrentKbId] = useState<string>('');
  const [showCreateKb, setShowCreateKb] = useState(false);
  const [newKbName, setNewKbName] = useState('');
  const [searchVal, setSearchVal] = useState('');

  useEffect(() => {
    hydrate();
  }, []);
  useEffect(() => {
    if (!useStore.getState().token) {
      router.replace('/login');
      return;
    }
    api
      .get<KB[]>('/knowledge-bases')
      .then((items) => setKbs(Array.isArray(items) ? items : []))
      .catch(() => {});
  }, [token]);
  useEffect(() => {
    if (kbs.length > 0 && !currentKbId) setCurrentKbId(kbs[0].id);
  }, [kbs]);

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const files = Array.from(e.dataTransfer.files).filter((f) => {
        const ext = f.name.split('.').pop()?.toLowerCase();
        return ['txt', 'md', 'markdown', 'pdf', 'docx', 'xlsx'].includes(ext || '');
      });
      if (files.length === 0) return;
      for (const file of files) {
        try {
          await api.upload(file, currentKbId);
        } catch {}
      }
      setRefreshKey((k) => k + 1);
    },
    [currentKbId],
  );

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

  const selectedKb = kbs.find((k) => k.id === currentKbId);

  if (!_hydrated || !token) return null;

  return (
    <div className="flex h-screen" style={{ background: 'var(--c-bg)' }}>
      <Sidebar />

      <div
        className="flex-1 flex flex-col overflow-hidden"
        onDragOver={(e) => {
          // 只对文件拖拽响应，忽略文本/链接拖拽
          if (e.dataTransfer.types.includes('Files')) {
            e.preventDefault();
            setDragging(true);
          }
        }}
        onDragLeave={(e) => {
          if (e.dataTransfer.types.includes('Files') && e.currentTarget === e.target) {
            setDragging(false);
          }
        }}
      >
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
                className="rounded-md text-sm outline-none transition-all"
                style={{
                  width: 220,
                  padding: '8px 12px 8px 36px',
                  border: '1px solid var(--c-border)',
                  background: 'var(--c-bg)',
                  color: 'var(--c-text)',
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = 'var(--c-primary)';
                  e.target.style.boxShadow = '0 0 0 3px rgba(37,99,235,.12)';
                  e.target.style.background = 'var(--c-surface)';
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = 'var(--c-border)';
                  e.target.style.boxShadow = 'none';
                  e.target.style.background = 'var(--c-bg)';
                }}
              />
            </div>
            <button
              onClick={() => setShowUpload(true)}
              className="btn-primary flex items-center gap-1.5 px-4 py-2 rounded-md text-sm font-medium border-none cursor-pointer whitespace-nowrap transition-all"
              style={{ background: 'var(--c-primary)', color: '#fff' }}
            >
              <Plus className="w-4 h-4" /> 上传
            </button>
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
                  className="rounded-md text-sm outline-none cursor-pointer transition-all"
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
                  onFocus={(e) => {
                    e.target.style.borderColor = 'var(--c-primary)';
                    e.target.style.boxShadow = '0 0 0 3px rgba(37,99,235,.12)';
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = 'var(--c-border)';
                    e.target.style.boxShadow = 'none';
                  }}
                >
                  {kbs.map((kb) => (
                    <option key={kb.id} value={kb.id}>
                      {kb.name}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => setRefreshKey((k) => k + 1)}
                  className="p-1.5 rounded-md border-none cursor-pointer transition-colors"
                  style={{ color: 'var(--c-text-secondary)', background: 'transparent' }}
                  title="刷新"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setShowCreateKb(!showCreateKb)}
                  className="text-xs border-none cursor-pointer shrink-0"
                  style={{ color: 'var(--c-primary)', background: 'none' }}
                >
                  +新建知识库
                </button>
                <span
                  className="ml-auto px-2.5 py-1 rounded-full text-xs border"
                  style={{
                    color: 'var(--c-text-secondary)',
                    background: '#f8fafc',
                    borderColor: 'var(--c-border)',
                  }}
                >
                  {selectedKb?.name || '全部知识库'}
                </span>
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
                  className="flex-1 text-sm border rounded px-2 py-1.5 outline-none transition-all"
                  style={{ borderColor: 'var(--c-border)', color: 'var(--c-text)' }}
                  onFocus={(e) => {
                    e.target.style.borderColor = 'var(--c-primary)';
                    e.target.style.boxShadow = '0 0 0 3px rgba(37,99,235,.12)';
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = 'var(--c-border)';
                    e.target.style.boxShadow = 'none';
                  }}
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

      {/* 全页拖拽上传遮罩 */}
      {dragging && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          style={{
            background: 'rgba(37,99,235,.08)',
            backdropFilter: 'blur(4px)',
          }}
          onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
          onDragLeave={(e) => {
            e.preventDefault();
            // 只在离开整个区域时才关闭
            if (e.currentTarget === e.target) setDragging(false);
          }}
          onDrop={handleDrop}
        >
          <div
            className="rounded-2xl p-12 text-center transition-all"
            style={{
              background: 'rgba(255,255,255,.95)',
              border: '2px dashed var(--c-primary)',
              boxShadow: '0 20px 60px rgba(37,99,235,.15)',
              transform: 'scale(1)',
            }}
          >
            <svg className="w-12 h-12 mx-auto mb-4" fill="none" stroke="var(--c-primary)" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <p className="text-base font-medium" style={{ color: 'var(--c-primary)' }}>
              松开以上传文件
            </p>
            <p className="text-sm mt-1" style={{ color: 'var(--c-text-tertiary)' }}>
              支持 txt / md / pdf / docx / xlsx
            </p>
          </div>
        </div>
      )}

      <UploadDialog
        open={showUpload}
        kbId={currentKbId}
        onClose={() => setShowUpload(false)}
        onUploaded={() => setRefreshKey((k) => k + 1)}
      />
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
