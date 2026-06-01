'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { toast } from './Toast';

interface RagConfig {
  top_k: number;
  score_threshold: number;
  chunk_size: number;
  chunk_overlap: number;
  no_evidence_policy: string;
}

interface Props {
  kbId: string;
  kbName: string;
  canEdit: boolean;
}

const DEFAULT_CONFIG: RagConfig = {
  top_k: 5,
  score_threshold: 0,
  chunk_size: 1000,
  chunk_overlap: 150,
  no_evidence_policy: 'strict',
};

export default function RAGConfigPanel({ kbId, kbName, canEdit }: Props) {
  const [config, setConfig] = useState<RagConfig>(DEFAULT_CONFIG);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reindexing, setReindexing] = useState(false);
  const [reindexResult, setReindexResult] = useState<number | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .get<{ rag_config: RagConfig }>(`/knowledge-bases/${kbId}/rag-config`)
      .then((data) => setConfig(data.rag_config || DEFAULT_CONFIG))
      .catch((e) => setError(e.message || '加载失败'))
      .finally(() => setLoading(false));
  }, [kbId]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const data = await api.patch<{ rag_config: RagConfig }>(
        `/knowledge-bases/${kbId}/rag-config`,
        { rag_config: config },
      );
      setConfig(data.rag_config);
      toast('配置已保存', 'success');
    } catch (e: any) {
      const msg = e.message || '保存失败';
      setError(msg);
      toast(msg, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleReindex = async () => {
    if (!confirm(`确定要重建「${kbName}」的全部索引吗？这将重新处理所有文档。`)) return;
    setReindexing(true);
    setReindexResult(null);
    setError(null);
    try {
      const data = await api.post<{ queued: number }>(
        `/knowledge-bases/${kbId}/reindex`,
      );
      setReindexResult(data.queued);
      toast(`已将 ${data.queued} 个文档加入索引队列`, 'success');
    } catch (e: any) {
      const msg = e.message || '重建失败';
      setError(msg);
      toast(msg, 'error');
    } finally {
      setReindexing(false);
    }
  };

  const updateField = (key: keyof RagConfig, value: string | number) => {
    setConfig((prev) => ({ ...prev, [key]: value }));
  };

  if (loading) {
    return (
      <div className="space-y-3 p-4 rounded-xl border" style={{ background: 'var(--c-surface)', borderColor: 'var(--c-border)' }}>
        <div className="skeleton h-4 w-32" />
        <div className="skeleton h-8 w-full" />
        <div className="skeleton h-8 w-full" />
        <div className="skeleton h-8 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4 rounded-xl border" style={{ background: 'var(--c-surface)', borderColor: 'var(--c-border)' }}>
      <h3 className="text-sm font-semibold" style={{ color: 'var(--c-text)' }}>
        RAG 配置 — {kbName}
      </h3>

      {error && (
        <div className="text-xs px-3 py-2 rounded-lg" style={{ background: 'var(--c-error-subtle)', color: 'var(--c-error)' }}>
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <FieldInput label="Top K" sub="检索返回数量 (1-20)" value={config.top_k} min={1} max={20}
          disabled={!canEdit} onChange={(v) => updateField('top_k', v)} />
        <FieldInput label="Score Threshold" sub="最低分数阈值 (0-1)" value={config.score_threshold} min={0} max={1} step={0.01}
          disabled={!canEdit} onChange={(v) => updateField('score_threshold', v)} />
        <FieldInput label="Chunk Size" sub="分块大小 (300-3000)" value={config.chunk_size} min={300} max={3000}
          disabled={!canEdit} onChange={(v) => updateField('chunk_size', v)} />
        <FieldInput label="Chunk Overlap" sub="分块重叠 (0-500)" value={config.chunk_overlap} min={0} max={500}
          disabled={!canEdit} onChange={(v) => updateField('chunk_overlap', v)} />
      </div>

      <div>
        <label className="text-xs font-medium block mb-1" style={{ color: 'var(--c-text-secondary)' }}>
          无证据策略
        </label>
        <select
          value={config.no_evidence_policy}
          onChange={(e) => updateField('no_evidence_policy', e.target.value)}
          disabled={!canEdit}
          className="w-full px-3 py-2 rounded-lg border text-sm outline-none"
          style={{ background: 'var(--c-bg)', borderColor: 'var(--c-border)', color: 'var(--c-text)' }}
        >
          <option value="strict">strict — 无依据时拒答</option>
          <option value="balanced">balanced — 尽量回答并标注不确定性</option>
        </select>
      </div>

      {canEdit && (
        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {saving ? '保存中...' : '保存配置'}
          </button>
          <button
            onClick={handleReindex}
            disabled={reindexing}
            className="px-4 py-2 rounded-lg text-sm font-medium border transition-colors"
            style={{ borderColor: 'var(--c-border)', color: 'var(--c-text-secondary)', background: 'var(--c-bg)' }}
          >
            {reindexing ? '重建中...' : '重建索引'}
          </button>
          {reindexResult !== null && (
            <span className="text-xs" style={{ color: 'var(--c-success, #16a34a)' }}>
              已入队 {reindexResult} 个文档
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function FieldInput({ label, sub, value, min, max, step, disabled, onChange }: {
  label: string; sub: string; value: number; min: number; max: number; step?: number;
  disabled: boolean; onChange: (v: number) => void;
}) {
  return (
    <div>
      <label className="text-xs font-medium block mb-1" style={{ color: 'var(--c-text-secondary)' }}>
        {label} <span className="font-normal opacity-60">({sub})</span>
      </label>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step || 1}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full px-3 py-2 rounded-lg border text-sm outline-none disabled:opacity-50"
        style={{ background: 'var(--c-bg)', borderColor: 'var(--c-border)', color: 'var(--c-text)' }}
      />
    </div>
  );
}
