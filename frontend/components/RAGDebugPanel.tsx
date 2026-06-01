'use client';

import { useState } from 'react';
import { api } from '@/lib/api';
import { toast } from './Toast';
import SourceViewer from './SourceViewer';

interface DebugResult {
  rank: number;
  document_id: string;
  document_title: string;
  chunk_id: string;
  snippet: string;
  score: number;
  page?: number;
  locator?: { type: string; value: string };
}

interface DebugResponse {
  query: string;
  knowledge_base_id?: string;
  top_k: number;
  results: DebugResult[];
  no_result_reason?: string;
  used_config?: { top_k: number; score_threshold: number };
}

interface KBOption {
  id: string;
  name: string;
}

interface Props {
  kbOptions: KBOption[];
}

export default function RAGDebugPanel({ kbOptions }: Props) {
  const [query, setQuery] = useState('');
  const [kbId, setKbId] = useState('');
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DebugResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 预览状态
  const [previewSource, setPreviewSource] = useState<{
    documentId: string;
    chunkId: string;
    snippet: string;
    page?: number;
    locator?: { type: string; value: string };
  } | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) {
      toast('请输入检索 query', 'error');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const body: Record<string, unknown> = { query: query.trim(), top_k: topK };
      if (kbId) body.knowledge_base_id = kbId;
      const data = await api.post<DebugResponse>('/rag/debug-search', body);
      setResult(data);
    } catch (e: any) {
      if (e.message?.includes('403') || e.message?.includes('无权限')) {
        setError('无权限访问该知识库');
      } else if (e.message?.includes('404')) {
        setError('知识库不存在');
      } else {
        setError(e.message || '检索失败');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* 输入区 */}
      <div
        className="rounded-xl border p-4"
        style={{ background: 'var(--c-surface)', borderColor: 'var(--c-border)' }}
      >
        <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--c-text)' }}>
          RAG 检索调试
        </h3>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--c-text-secondary)' }}>
              Query
            </label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !loading && handleSearch()}
              placeholder="输入检索词..."
              className="w-full px-3 py-2 rounded-lg border text-sm outline-none focus:ring-2"
              style={{
                background: 'var(--c-bg)',
                borderColor: 'var(--c-border)',
                color: 'var(--c-text)',
              }}
            />
          </div>
          <div className="flex gap-3 flex-wrap">
            <div className="flex-1 min-w-[140px]">
              <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--c-text-secondary)' }}>
                知识库（可选）
              </label>
              <select
                value={kbId}
                onChange={(e) => setKbId(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border text-sm outline-none"
                style={{
                  background: 'var(--c-bg)',
                  borderColor: 'var(--c-border)',
                  color: 'var(--c-text)',
                }}
              >
                <option value="">全部可访问知识库</option>
                {kbOptions.map((kb) => (
                  <option key={kb.id} value={kb.id}>
                    {kb.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="w-24">
              <label className="text-xs font-medium mb-1 block" style={{ color: 'var(--c-text-secondary)' }}>
                Top K
              </label>
              <input
                type="number"
                min={1}
                max={20}
                value={topK}
                onChange={(e) => setTopK(Math.min(20, Math.max(1, Number(e.target.value) || 5)))}
                className="w-full px-3 py-2 rounded-lg border text-sm outline-none"
                style={{
                  background: 'var(--c-bg)',
                  borderColor: 'var(--c-border)',
                  color: 'var(--c-text)',
                }}
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={handleSearch}
                disabled={loading || !query.trim()}
                className="px-4 py-2 rounded-lg text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? '检索中...' : '运行检索'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 错误 */}
      {error && (
        <div
          className="rounded-xl border p-4 text-sm"
          style={{
            background: 'var(--c-error-subtle)',
            borderColor: 'rgba(220,38,38,.15)',
            color: 'var(--c-error)',
          }}
        >
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="rounded-xl border p-4 animate-pulse"
              style={{ background: 'var(--c-surface)', borderColor: 'var(--c-border)' }}
            >
              <div className="skeleton h-4 w-1/3 mb-2" />
              <div className="skeleton h-3 w-full mb-1" />
              <div className="skeleton h-3 w-2/3" />
            </div>
          ))}
        </div>
      )}

      {/* 结果 */}
      {result && !loading && (
        <div className="space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-1">
            <span className="text-xs font-medium" style={{ color: 'var(--c-text-secondary)' }}>
              查询: {result.query} · Top {result.top_k}
              {result.knowledge_base_id && ' · 指定知识库'}
            </span>
            <span className="text-xs" style={{ color: 'var(--c-text-tertiary)' }}>
              {result.results.length} 条结果
            </span>
          </div>
          {result.used_config && (
            <div className="flex items-center gap-2 flex-wrap text-[10px]" style={{ color: 'var(--c-text-tertiary)' }}>
              <span>使用配置:</span>
              <span className="px-1.5 py-0.5 rounded" style={{ background: 'var(--c-bg)' }}>top_k={result.used_config.top_k}</span>
              <span className="px-1.5 py-0.5 rounded" style={{ background: 'var(--c-bg)' }}>threshold={result.used_config.score_threshold}</span>
            </div>
          )}

          {result.results.length === 0 ? (
            <div
              className="rounded-xl border p-8 text-center"
              style={{ background: 'var(--c-surface)', borderColor: 'var(--c-border)' }}
            >
              <div className="text-sm" style={{ color: 'var(--c-text-tertiary)' }}>
                {result.no_result_reason || '未检索到相关内容'}
              </div>
            </div>
          ) : (
            result.results.map((r) => (
              <div
                key={r.chunk_id}
                className="rounded-xl border p-4 cursor-pointer transition-all hover:shadow-sm"
                style={{ background: 'var(--c-surface)', borderColor: 'var(--c-border)' }}
                onClick={() =>
                  setPreviewSource({
                    documentId: r.document_id,
                    chunkId: r.chunk_id,
                    snippet: r.snippet,
                    page: r.page,
                    locator: r.locator,
                  })
                }
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setPreviewSource({
                      documentId: r.document_id,
                      chunkId: r.chunk_id,
                      snippet: r.snippet,
                      page: r.page,
                      locator: r.locator,
                    });
                  }
                }}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                      style={{ background: 'var(--c-bg)', color: 'var(--c-text-tertiary)' }}
                    >
                      #{r.rank}
                    </span>
                    <span className="text-sm font-medium truncate" style={{ color: 'var(--c-text)' }}>
                      {r.document_title}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {r.page && (
                      <span
                        className="text-[10px] px-1.5 py-0.5 rounded-full"
                        style={{ background: 'var(--c-primary-subtle)', color: 'var(--c-primary)' }}
                      >
                        第{r.page}页
                      </span>
                    )}
                    <span
                      className="text-xs font-mono px-2 py-0.5 rounded-full"
                      style={{
                        background:
                          r.score >= 0.8
                            ? 'rgba(22,163,74,.1)'
                            : r.score >= 0.5
                              ? 'rgba(234,179,8,.1)'
                              : 'var(--c-bg)',
                        color:
                          r.score >= 0.8 ? '#16a34a' : r.score >= 0.5 ? '#ca8a04' : 'var(--c-text-tertiary)',
                      }}
                    >
                      {(r.score * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div
                  className="text-xs leading-relaxed mb-2"
                  style={{ color: 'var(--c-text-secondary)' }}
                >
                  {r.snippet.length > 200 ? r.snippet.slice(0, 200) + '...' : r.snippet}
                </div>
                <div className="flex items-center gap-3 text-[10px]" style={{ color: 'var(--c-text-tertiary)' }}>
                  <span className="font-mono">{r.document_id.slice(0, 8)}...</span>
                  <span className="font-mono">{r.chunk_id.slice(0, 8)}...</span>
                  {r.locator && (
                    <span>
                      {r.locator.type === 'page' && `页码: ${r.locator.value}`}
                      {r.locator.type === 'text' && r.locator.value}
                      {r.locator.type === 'chunk' && '定位片段'}
                    </span>
                  )}
                  <span className="ml-auto" style={{ color: 'var(--c-primary)' }}>
                    点击预览 →
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* 预览面板 */}
      {previewSource && (
        <SourceViewer
          documentId={previewSource.documentId}
          highlightChunkId={previewSource.chunkId}
          snippet={previewSource.snippet}
          page={previewSource.page}
          locator={previewSource.locator}
          onClose={() => setPreviewSource(null)}
        />
      )}
    </div>
  );
}
