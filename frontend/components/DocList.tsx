'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { FileText, RefreshCw, Trash2, X, Search } from 'lucide-react';

const ReactMarkdown = dynamic(() => import('react-markdown'), { ssr: false });
import { api } from '@/lib/api';
import { toast } from '@/components/Toast';
import ConfirmDialog from '@/components/ConfirmDialog';

interface Doc {
  id: string;
  title: string;
  status: string;
  created_at: string;
  kb_id?: string | null;
}
const statusLabel: Record<string, string> = {
  indexed: '已索引',
  processing: '处理中',
  pending: '等待中',
  failed: '失败',
};
const statusColor: Record<string, string> = {
  indexed: '#16a34a',
  processing: '#d97706',
  pending: '#6b7280',
  failed: '#dc2626',
};
const statusBg: Record<string, string> = {
  indexed: 'var(--c-success-subtle)',
  processing: 'var(--c-warning-subtle)',
  pending: 'var(--c-bg)',
  failed: 'var(--c-error-subtle)',
};

function DocSkeleton() {
  return (
    <div className="space-y-2.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="flex items-center gap-3.5 p-4 rounded-xl card animate-fade-in"
          style={{ animationDelay: `${i * 50}ms` }}
        >
          <div className="skeleton shrink-0" style={{ width: 18, height: 18, borderRadius: 3 }} />
          <div className="skeleton shrink-0" style={{ width: 36, height: 36, borderRadius: 8 }} />
          <div className="flex-1 space-y-1.5">
            <div className="skeleton h-4" style={{ width: '55%' }} />
            <div className="skeleton h-3" style={{ width: '22%' }} />
          </div>
          <div className="skeleton shrink-0" style={{ width: 56, height: 24, borderRadius: 999 }} />
        </div>
      ))}
    </div>
  );
}

export default function DocList({
  refreshKey,
  kbId,
  searchProp,
}: {
  refreshKey: number;
  kbId?: string;
  searchProp?: string;
}) {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewDoc, setViewDoc] = useState<{
    id: string;
    title: string;
    content: string;
    status: string;
  } | null>(null);
  const [loadingContent, setLoadingContent] = useState(false);
  const [closing, setClosing] = useState(false);
  const [viewVisible, setViewVisible] = useState(false);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [batchDeleteOpen, setBatchDeleteOpen] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [batchBusy, setBatchBusy] = useState(false);
  const [sortBy, setSortBy] = useState<'date' | 'name' | 'status'>('date');

  const docItems = Array.isArray(docs) ? docs : [];
  let sorted = [...docItems];
  if (sortBy === 'name') sorted.sort((a, b) => a.title.localeCompare(b.title));
  else if (sortBy === 'status') {
    const order = { indexed: 0, processing: 1, pending: 2, failed: 3 };
    sorted.sort(
      (a, b) =>
        (order[a.status as keyof typeof order] ?? 9) - (order[b.status as keyof typeof order] ?? 9),
    );
  } else sorted.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  const filtered = searchProp
    ? sorted.filter((d) => d.title.toLowerCase().includes(searchProp.toLowerCase()))
    : sorted;

  const load = () => {
    setLoading(true);
    setError(null);
    api
      .get<any>(`/documents${kbId ? `?kb_id=${kbId}` : ''}`)
      .then((res) => setDocs(Array.isArray(res?.items) ? res.items : []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };
  useEffect(load, [refreshKey, kbId]);

  const toggleSelect = (id: string) =>
    setSelected((s) => {
      const n = new Set(s);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });
  const toggleAll = () =>
    setSelected(selected.size === docItems.length ? new Set() : new Set(docItems.map((d) => d.id)));

  const handleBatchDelete = async () => {
    setBatchBusy(true);
    try {
      await api.post('/documents/batch-delete', { ids: [...selected] });
      setDocs((prev) => prev.filter((d) => !selected.has(d.id)));
      setSelected(new Set());
      toast(`已删除 ${selected.size} 个文档`, 'success');
    } catch (e: any) {
      toast(e.message, 'error');
    } finally {
      setBatchBusy(false);
      setBatchDeleteOpen(false);
    }
  };
  const handleBatchReindex = async () => {
    setBatchBusy(true);
    try {
      await api.post('/documents/batch-reindex', { ids: [...selected] });
      toast('已触发重新索引', 'success');
      setSelected(new Set());
      load();
    } catch (e: any) {
      toast(e.message, 'error');
    } finally {
      setBatchBusy(false);
    }
  };

  const handleView = async (id: string) => {
    setLoadingContent(true);
    try {
      const doc = await api.get<any>(`/documents/${id}`);
      setViewDoc({ id, title: doc.title, content: doc.content, status: doc.status });
      setViewVisible(true);
      if (doc.title.match(/\.pdf$/i))
        setPdfBlobUrl(URL.createObjectURL(await api.download(`/documents/${id}/file`)));
    } catch (e: any) {
      toast(e.message, 'error');
    } finally {
      setLoadingContent(false);
    }
  };
  const handleCloseView = () => {
    setClosing(true);
    setTimeout(() => {
      setViewVisible(false);
      setClosing(false);
      setViewDoc(null);
      if (pdfBlobUrl) {
        URL.revokeObjectURL(pdfBlobUrl);
        setPdfBlobUrl(null);
      }
    }, 150);
  };
  const handleDeleteConfirm = async () => {
    if (!confirmDeleteId) return;
    try {
      await api.delete(`/documents/${confirmDeleteId}`);
      setDocs((prev) => prev.filter((d) => d.id !== confirmDeleteId));
      toast('文档已删除', 'success');
    } catch (e: any) {
      toast(e.message, 'error');
    } finally {
      setConfirmDeleteId(null);
    }
  };

  if (loading) return <DocSkeleton />;

  if (error)
    return (
      <div className="text-center py-12 px-8 rounded-xl card animate-fade-in">
        <div
          className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center"
          style={{ background: 'var(--c-error-subtle)', color: 'var(--c-error)' }}
        >
          <svg width="28" height="28" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
            />
          </svg>
        </div>
        <h3 className="text-base font-semibold mb-1">加载失败</h3>
        <p className="text-sm mb-4" style={{ color: 'var(--c-text-secondary)' }}>
          {error}
        </p>
        <button onClick={load} className="btn-primary">
          <RefreshCw className="w-3.5 h-3.5" />
          重新加载
        </button>
      </div>
    );

  if (docItems.length === 0)
    return (
      <div className="text-center py-16 px-8 rounded-xl card animate-fade-in">
        <div
          className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center"
          style={{ background: 'var(--c-primary-subtle)', color: 'var(--c-primary)' }}
        >
          <FileText className="w-8 h-8" />
        </div>
        <h3 className="text-base font-semibold mb-1">暂无文档</h3>
        <p className="text-sm" style={{ color: 'var(--c-text-secondary)' }}>
          上传文档后系统将自动索引
        </p>
      </div>
    );

  return (
    <>
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as any)}
          className="text-xs rounded-lg px-2.5 py-1.5 border input-base cursor-pointer"
          style={{
            borderColor: 'var(--c-border)',
            color: 'var(--c-text-secondary)',
            background: 'var(--c-surface)',
          }}
        >
          <option value="date">按时间</option>
          <option value="name">按名称</option>
          <option value="status">按状态</option>
        </select>
        <button
          onClick={load}
          className="text-xs flex items-center gap-1 px-2.5 py-1.5 rounded-lg transition-all border-none cursor-pointer"
          style={{ color: 'var(--c-text-tertiary)', background: 'none' }}
        >
          <RefreshCw className="w-3.5 h-3.5" />
          刷新
        </button>
        <span className="text-xs ml-auto" style={{ color: 'var(--c-text-tertiary)' }}>
          共 {filtered.length} 个文档
        </span>
      </div>

      {selected.size > 0 && (
        <div
          className="flex items-center gap-2 mb-3 px-1 py-2 rounded-xl animate-slide-up"
          style={{ background: 'var(--c-primary-subtle)', border: '1px solid rgba(37,99,235,.15)' }}
        >
          <input
            type="checkbox"
            checked={selected.size === filtered.length && filtered.length > 0}
            onChange={toggleAll}
            style={{ accentColor: 'var(--c-primary)', cursor: 'pointer' }}
          />
          <span className="text-xs font-medium" style={{ color: 'var(--c-primary)' }}>
            已选 {selected.size} 项
          </span>
          <div className="flex gap-1.5 ml-auto">
            <button
              onClick={() => setBatchDeleteOpen(true)}
              disabled={batchBusy}
              className="px-3 py-1 text-xs rounded-lg border cursor-pointer disabled:opacity-50 transition-all"
              style={{
                color: 'var(--c-error)',
                background: 'var(--c-error-subtle)',
                borderColor: 'rgba(220,38,38,.2)',
              }}
            >
              批量删除
            </button>
            <button
              onClick={handleBatchReindex}
              disabled={batchBusy}
              className="px-3 py-1 text-xs rounded-lg border cursor-pointer disabled:opacity-50 transition-all"
              style={{
                color: 'var(--c-primary)',
                background: 'var(--c-primary-subtle)',
                borderColor: 'rgba(37,99,235,.2)',
              }}
            >
              重新索引
            </button>
          </div>
        </div>
      )}

      {filtered.length === 0 && searchProp ? (
        <div className="text-center py-16 animate-fade-in">
          <div
            className="w-16 h-16 mx-auto mb-4 rounded-full flex items-center justify-center"
            style={{ background: 'var(--c-primary-subtle)', color: 'var(--c-primary)' }}
          >
            <Search className="w-8 h-8" />
          </div>
          <h3 className="text-base font-semibold mb-1">未找到匹配的文档</h3>
          <p className="text-sm" style={{ color: 'var(--c-text-secondary)' }}>
            尝试其他关键词
          </p>
        </div>
      ) : (
        <div className="space-y-2 animate-fade-in">
          {filtered.map((doc, idx) => (
            <div
              key={doc.id}
              onClick={() => handleView(doc.id)}
              className="flex items-center gap-3.5 p-3.5 rounded-xl cursor-pointer transition-all animate-slide-up card"
              style={{ animationDelay: `${idx * 30}ms`, background: 'var(--c-surface)' }}
            >
              <input
                type="checkbox"
                checked={selected.has(doc.id)}
                onChange={() => toggleSelect(doc.id)}
                onClick={(e) => e.stopPropagation()}
                style={{ accentColor: 'var(--c-primary)', cursor: 'pointer' }}
              />
              <div
                className="flex items-center justify-center shrink-0 rounded-lg"
                style={{
                  width: 36,
                  height: 36,
                  background: 'var(--c-primary-subtle)',
                  color: 'var(--c-primary)',
                }}
              >
                <FileText className="w-[18px] h-[18px]" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{doc.title}</div>
                <div className="text-xs mt-0.5" style={{ color: 'var(--c-text-tertiary)' }}>
                  {new Date(doc.created_at).toLocaleDateString('zh-CN', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                  })}
                </div>
              </div>
              <span
                className="shrink-0 text-xs font-medium px-2.5 py-1 rounded-full inline-flex items-center gap-1.5"
                style={{
                  background: statusBg[doc.status] || '#f3f4f6',
                  color: statusColor[doc.status] || '#6b7280',
                }}
              >
                <span
                  style={{
                    width: 5,
                    height: 5,
                    borderRadius: '50%',
                    background: 'currentColor',
                    display: 'inline-block',
                  }}
                />
                {statusLabel[doc.status] || doc.status}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setConfirmDeleteId(doc.id);
                }}
                className="shrink-0 p-1.5 rounded-lg border-none cursor-pointer transition-all"
                style={{ color: 'var(--c-text-tertiary)', background: 'none', opacity: 0.5 }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.opacity = '1';
                  e.currentTarget.style.background = 'var(--c-error-subtle)';
                  e.currentTarget.style.color = 'var(--c-error)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.opacity = '0.5';
                  e.currentTarget.style.background = 'none';
                  e.currentTarget.style.color = 'var(--c-text-tertiary)';
                }}
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {viewDoc && viewVisible && (
        <div
          className={`fixed inset-0 z-50 flex items-center justify-center ${closing ? 'animate-fade-out' : 'animate-fade-in'}`}
          style={{ background: 'rgba(15,23,42,.5)', backdropFilter: 'blur(4px)' }}
          onClick={handleCloseView}
        >
          <div
            className={`bg-white rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col mx-4 ${closing ? 'animate-scale-out' : 'animate-scale-in'}`}
            style={{ boxShadow: 'var(--shadow-lg)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 border-b shrink-0">
              <div className="flex items-center gap-2 min-w-0">
                <h2 className="font-semibold truncate">{viewDoc.title}</h2>
                <span
                  className="text-xs px-2 py-0.5 rounded-full inline-flex items-center gap-1 shrink-0"
                  style={{
                    background: statusBg[viewDoc.status],
                    color: statusColor[viewDoc.status],
                  }}
                >
                  <span
                    style={{
                      width: 5,
                      height: 5,
                      borderRadius: '50%',
                      background: 'currentColor',
                      display: 'inline-block',
                    }}
                  />
                  {statusLabel[viewDoc.status] || viewDoc.status}
                </span>
              </div>
              <button
                onClick={handleCloseView}
                className="p-1 rounded-lg transition-colors border-none cursor-pointer"
                style={{ color: 'var(--c-text-tertiary)', background: 'none' }}
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 md:p-6 overflow-y-auto flex-1">
              {loadingContent ? (
                <div className="space-y-3 py-4">
                  {Array.from({ length: 6 }).map((_, i) => (
                    <div key={i} className="skeleton h-4" style={{ width: `${85 - i * 10}%` }} />
                  ))}
                </div>
              ) : viewDoc.title.match(/\.pdf$/i) && pdfBlobUrl ? (
                <iframe src={pdfBlobUrl} className="w-full h-[70vh] border-0 rounded-lg" />
              ) : viewDoc.title.match(/\.(md|markdown)$/i) ? (
                <div className="text-sm leading-relaxed prose">
                  <ReactMarkdown>{viewDoc.content}</ReactMarkdown>
                </div>
              ) : (
                <pre
                  className="text-sm whitespace-pre-wrap leading-relaxed"
                  style={{ fontFamily: 'inherit' }}
                >
                  {viewDoc.content}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!confirmDeleteId}
        title="删除文档"
        message="确定删除？删除后不可恢复。"
        confirmText="删除"
        danger
        onConfirm={handleDeleteConfirm}
        onCancel={() => setConfirmDeleteId(null)}
      />
      <ConfirmDialog
        open={batchDeleteOpen}
        title="批量删除"
        message={`确定删除选中的 ${selected.size} 个文档？`}
        confirmText="全部删除"
        danger
        onConfirm={handleBatchDelete}
        onCancel={() => setBatchDeleteOpen(false)}
      />
    </>
  );
}
