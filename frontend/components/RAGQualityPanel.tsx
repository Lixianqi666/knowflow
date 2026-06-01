'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { toast } from './Toast';

interface QualityIssue {
  id: string;
  knowledge_base_id?: string | null;
  source_type: string;
  source_id?: string | null;
  question?: string | null;
  answer?: string | null;
  citations?: { document_title?: string; snippet?: string; document_id?: string; chunk_id?: string }[];
  severity: string;
  status: string;
  reason?: string | null;
  resolution_note?: string | null;
  assignee_user_id?: string | null;
  created_by?: string | null;
  created_at: string;
  resolved_at?: string | null;
}

const STATUS_LABELS: Record<string, string> = {
  open: '待处理',
  in_progress: '处理中',
  resolved: '已解决',
  ignored: '已忽略',
};

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  open: { bg: 'rgba(234,179,8,.1)', text: '#ca8a04' },
  in_progress: { bg: 'rgba(59,130,246,.1)', text: '#2563eb' },
  resolved: { bg: 'rgba(22,163,74,.1)', text: '#16a34a' },
  ignored: { bg: 'var(--c-bg)', text: 'var(--c-text-tertiary)' },
};

const SEVERITY_LABELS: Record<string, string> = { low: '低', medium: '中', high: '高' };
const SOURCE_LABELS: Record<string, string> = {
  feedback: '用户反馈',
  eval_failed: '评测失败',
  no_evidence: '无依据',
  manual: '手动创建',
};

interface Props {
  canUpdate: boolean;
}

export default function RAGQualityPanel({ canUpdate }: Props) {
  const [issues, setIssues] = useState<QualityIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<{ status: string; severity: string; source_type: string }>({
    status: '',
    severity: '',
    source_type: '',
  });
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [resolutionNote, setResolutionNote] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ question: '', reason: '', severity: 'medium' });

  const loadIssues = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (filter.status) params.set('status', filter.status);
      if (filter.severity) params.set('severity', filter.severity);
      if (filter.source_type) params.set('source_type', filter.source_type);
      const qs = params.toString();
      const data = await api.get<QualityIssue[]>(`/rag-quality/issues${qs ? `?${qs}` : ''}`);
      setIssues(Array.isArray(data) ? data : []);
    } catch (e: any) {
      setError(e.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIssues();
  }, [filter]);

  const handleUpdate = async (issueId: string, newStatus: string) => {
    setUpdatingId(issueId);
    try {
      const body: Record<string, unknown> = { status: newStatus };
      if ((newStatus === 'resolved' || newStatus === 'ignored') && resolutionNote.trim()) {
        body.resolution_note = resolutionNote.trim();
      }
      await api.patch(`/rag-quality/issues/${issueId}`, body);
      toast(`已标记为${STATUS_LABELS[newStatus]}`, 'success');
      setResolutionNote('');
      setExpandedId(null);
      loadIssues();
    } catch (e: any) {
      toast(e.message || '操作失败', 'error');
    } finally {
      setUpdatingId(null);
    }
  };

  const handleCreate = async () => {
    if (!createForm.question.trim()) {
      toast('请输入问题描述', 'error');
      return;
    }
    try {
      await api.post('/rag-quality/issues', {
        source_type: 'manual',
        question: createForm.question.trim(),
        reason: createForm.reason.trim() || undefined,
        severity: createForm.severity,
      });
      toast('已创建质量问题', 'success');
      setShowCreate(false);
      setCreateForm({ question: '', reason: '', severity: 'medium' });
      loadIssues();
    } catch (e: any) {
      toast(e.message || '创建失败', 'error');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="text-sm font-semibold" style={{ color: 'var(--c-text)' }}>
          RAG 质量问题队列
        </h3>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-3 py-1.5 text-xs font-medium rounded-lg border-none cursor-pointer"
          style={{ background: 'var(--c-primary)', color: '#fff' }}
        >
          {showCreate ? '取消' : '手动创建'}
        </button>
      </div>

      {/* 手动创建 */}
      {showCreate && (
        <div className="p-3 rounded-xl border space-y-2" style={{ background: 'var(--c-surface)', borderColor: 'var(--c-border)' }}>
          <input
            value={createForm.question}
            onChange={(e) => setCreateForm((p) => ({ ...p, question: e.target.value }))}
            placeholder="问题描述"
            className="w-full px-3 py-2 rounded-lg border text-sm outline-none"
            style={{ background: 'var(--c-bg)', borderColor: 'var(--c-border)', color: 'var(--c-text)' }}
          />
          <input
            value={createForm.reason}
            onChange={(e) => setCreateForm((p) => ({ ...p, reason: e.target.value }))}
            placeholder="原因（可选）"
            className="w-full px-3 py-2 rounded-lg border text-sm outline-none"
            style={{ background: 'var(--c-bg)', borderColor: 'var(--c-border)', color: 'var(--c-text)' }}
          />
          <div className="flex items-center gap-2">
            <select
              value={createForm.severity}
              onChange={(e) => setCreateForm((p) => ({ ...p, severity: e.target.value }))}
              className="px-3 py-2 rounded-lg border text-sm outline-none"
              style={{ background: 'var(--c-bg)', borderColor: 'var(--c-border)', color: 'var(--c-text)' }}
            >
              <option value="low">低</option>
              <option value="medium">中</option>
              <option value="high">高</option>
            </select>
            <button
              onClick={handleCreate}
              className="px-3 py-2 text-xs font-medium rounded-lg text-white border-none cursor-pointer"
              style={{ background: 'var(--c-primary)' }}
            >
              创建
            </button>
          </div>
        </div>
      )}

      {/* 过滤 */}
      <div className="flex items-center gap-2 flex-wrap">
        {[
          { key: 'status', label: '状态', options: ['', 'open', 'in_progress', 'resolved', 'ignored'] },
          { key: 'severity', label: '严重度', options: ['', 'low', 'medium', 'high'] },
          { key: 'source_type', label: '来源', options: ['', 'feedback', 'eval_failed', 'no_evidence', 'manual'] },
        ].map((f) => (
          <select
            key={f.key}
            value={(filter as Record<string, string>)[f.key]}
            onChange={(e) => setFilter((p) => ({ ...p, [f.key]: e.target.value }))}
            className="px-2 py-1.5 rounded-lg border text-xs outline-none"
            style={{ background: 'var(--c-bg)', borderColor: 'var(--c-border)', color: 'var(--c-text)' }}
          >
            <option value="">{f.label}（全部）</option>
            {f.options.filter(Boolean).map((o) => (
              <option key={o} value={o}>
                {f.key === 'status' ? STATUS_LABELS[o] : f.key === 'severity' ? SEVERITY_LABELS[o] : SOURCE_LABELS[o] || o}
              </option>
            ))}
          </select>
        ))}
      </div>

      {/* 错误 */}
      {error && (
        <div className="text-xs px-3 py-2 rounded-lg" style={{ background: 'var(--c-error-subtle)', color: 'var(--c-error)' }}>
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded-xl border p-4 animate-pulse" style={{ background: 'var(--c-surface)', borderColor: 'var(--c-border)' }}>
              <div className="skeleton h-4 w-1/3 mb-2" />
              <div className="skeleton h-3 w-full" />
            </div>
          ))}
        </div>
      )}

      {/* 列表 */}
      {!loading && issues.length === 0 && (
        <div className="text-center py-8 text-sm" style={{ color: 'var(--c-text-tertiary)' }}>
          暂无质量问题
        </div>
      )}

      {!loading &&
        issues.map((issue) => {
          const expanded = expandedId === issue.id;
          const sc = STATUS_COLORS[issue.status] || STATUS_COLORS.open;
          return (
            <div
              key={issue.id}
              className="rounded-xl border overflow-hidden"
              style={{ background: 'var(--c-surface)', borderColor: 'var(--c-border)' }}
            >
              <div
                className="p-3 cursor-pointer flex items-center justify-between gap-2"
                onClick={() => setExpandedId(expanded ? null : issue.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setExpandedId(expanded ? null : issue.id);
                  }
                }}
              >
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded-full shrink-0"
                    style={{ background: sc.bg, color: sc.text }}
                  >
                    {STATUS_LABELS[issue.status] || issue.status}
                  </span>
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded-full shrink-0"
                    style={{ background: 'var(--c-bg)', color: 'var(--c-text-tertiary)' }}
                  >
                    {SEVERITY_LABELS[issue.severity] || issue.severity}
                  </span>
                  <span
                    className="text-[10px] px-1.5 py-0.5 rounded shrink-0"
                    style={{ background: 'var(--c-bg)', color: 'var(--c-text-tertiary)' }}
                  >
                    {SOURCE_LABELS[issue.source_type] || issue.source_type}
                  </span>
                  <span className="text-xs truncate" style={{ color: 'var(--c-text)' }}>
                    {issue.question || '无问题描述'}
                  </span>
                </div>
                <span className="text-[10px] shrink-0" style={{ color: 'var(--c-text-tertiary)' }}>
                  {new Date(issue.created_at).toLocaleDateString()}
                </span>
              </div>

              {expanded && (
                <div className="px-3 pb-3 space-y-2 border-t" style={{ borderColor: 'var(--c-border)' }}>
                  {issue.question && (
                    <div className="mt-2">
                      <span className="text-[10px] font-medium" style={{ color: 'var(--c-text-tertiary)' }}>问题</span>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--c-text)' }}>{issue.question}</p>
                    </div>
                  )}
                  {issue.answer && (
                    <div>
                      <span className="text-[10px] font-medium" style={{ color: 'var(--c-text-tertiary)' }}>回答摘要</span>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--c-text-secondary)' }}>
                        {issue.answer.length > 300 ? issue.answer.slice(0, 300) + '...' : issue.answer}
                      </p>
                    </div>
                  )}
                  {issue.reason && (
                    <div>
                      <span className="text-[10px] font-medium" style={{ color: 'var(--c-text-tertiary)' }}>原因</span>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--c-text-secondary)' }}>{issue.reason}</p>
                    </div>
                  )}
                  {issue.resolution_note && (
                    <div>
                      <span className="text-[10px] font-medium" style={{ color: 'var(--c-text-tertiary)' }}>解决方案</span>
                      <p className="text-xs mt-0.5" style={{ color: 'var(--c-text-secondary)' }}>{issue.resolution_note}</p>
                    </div>
                  )}
                  {issue.citations && issue.citations.length > 0 && (
                    <div>
                      <span className="text-[10px] font-medium" style={{ color: 'var(--c-text-tertiary)' }}>
                        引用 ({issue.citations.length})
                      </span>
                      <div className="mt-1 space-y-1">
                        {issue.citations.slice(0, 5).map((c, i) => (
                          <div
                            key={i}
                            className="text-[10px] px-2 py-1 rounded"
                            style={{ background: 'var(--c-bg)', color: 'var(--c-text-secondary)' }}
                          >
                            {c.document_title || '未知文档'}
                            {c.snippet && ` — ${c.snippet.slice(0, 80)}...`}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 操作 */}
                  {canUpdate && (
                    <div className="flex items-center gap-2 pt-2 flex-wrap">
                      {issue.status === 'open' && (
                        <button
                          onClick={() => handleUpdate(issue.id, 'in_progress')}
                          disabled={updatingId === issue.id}
                          className="px-2.5 py-1 text-[11px] rounded-lg border-none cursor-pointer disabled:opacity-50"
                          style={{ background: 'rgba(59,130,246,.1)', color: '#2563eb' }}
                        >
                          标记处理中
                        </button>
                      )}
                      {(issue.status === 'open' || issue.status === 'in_progress') && (
                        <>
                          <input
                            value={resolutionNote}
                            onChange={(e) => setResolutionNote(e.target.value)}
                            placeholder="解决方案（可选）"
                            className="px-2 py-1 rounded-lg border text-[11px] outline-none flex-1 min-w-[120px]"
                            style={{ background: 'var(--c-bg)', borderColor: 'var(--c-border)', color: 'var(--c-text)' }}
                          />
                          <button
                            onClick={() => handleUpdate(issue.id, 'resolved')}
                            disabled={updatingId === issue.id}
                            className="px-2.5 py-1 text-[11px] rounded-lg border-none cursor-pointer disabled:opacity-50"
                            style={{ background: 'rgba(22,163,74,.1)', color: '#16a34a' }}
                          >
                            解决
                          </button>
                          <button
                            onClick={() => handleUpdate(issue.id, 'ignored')}
                            disabled={updatingId === issue.id}
                            className="px-2.5 py-1 text-[11px] rounded-lg border-none cursor-pointer disabled:opacity-50"
                            style={{ background: 'var(--c-bg)', color: 'var(--c-text-tertiary)' }}
                          >
                            忽略
                          </button>
                        </>
                      )}
                      {issue.status === 'resolved' && (
                        <button
                          onClick={() => handleUpdate(issue.id, 'open')}
                          disabled={updatingId === issue.id}
                          className="px-2.5 py-1 text-[11px] rounded-lg border-none cursor-pointer disabled:opacity-50"
                          style={{ background: 'rgba(234,179,8,.1)', color: '#ca8a04' }}
                        >
                          重新打开
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
    </div>
  );
}
