'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { RefreshCw, Database, Zap, FileText, MessageSquare, BarChart3 } from 'lucide-react';

interface HealthOverview {
  status: string;
  database: { status: string; latency_ms: number };
  redis: { status: string; latency_ms: number };
  documents: {
    total: number;
    indexed: number;
    processing: number;
    failed: number;
    recent_failed: Array<{
      id: string;
      title: string;
      status: string;
      error_message: string;
      updated_at: string;
    }>;
  };
  rag_evals: {
    total_runs: number;
    latest_score: number | null;
    latest_passed: number;
    latest_failed: number;
  };
  feedback: { up: number; down: number };
}

export default function HealthTab() {
  const [data, setData] = useState<HealthOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    api
      .get<HealthOverview>('/admin/health/overview')
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-5 h-5 animate-spin" style={{ color: 'var(--c-text-tertiary)' }} />
        <span className="ml-2 text-sm" style={{ color: 'var(--c-text-tertiary)' }}>加载中...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-sm mb-3" style={{ color: 'var(--c-error)' }}>{error}</div>
        <button onClick={load} className="btn-primary text-xs">
          <RefreshCw className="w-3.5 h-3.5" />
          重试
        </button>
      </div>
    );
  }

  if (!data) return null;

  const statusColor = (s: string) => {
    if (s === 'ok') return '#16a34a';
    if (s === 'degraded') return '#d97706';
    return '#dc2626';
  };

  const statusLabel = (s: string) => {
    if (s === 'ok') return '正常';
    if (s === 'degraded') return '降级';
    return '异常';
  };

  return (
    <div className="space-y-4">
      {/* 整体状态 */}
      <div
        className="p-4 rounded-xl flex items-center gap-3"
        style={{
          background: data.status === 'ok' ? 'var(--c-success-subtle)' : 'var(--c-warning-subtle)',
          border: `1px solid ${data.status === 'ok' ? 'rgba(22,163,74,.2)' : 'rgba(217,119,6,.2)'}`,
        }}
      >
        <div
          className="w-3 h-3 rounded-full"
          style={{ background: statusColor(data.status) }}
        />
        <span className="text-sm font-medium" style={{ color: statusColor(data.status) }}>
          系统状态：{statusLabel(data.status)}
        </span>
        <button
          onClick={load}
          className="ml-auto text-xs flex items-center gap-1 border-none cursor-pointer"
          style={{ color: 'var(--c-text-tertiary)', background: 'none' }}
        >
          <RefreshCw className="w-3.5 h-3.5" />
          刷新
        </button>
      </div>

      {/* 依赖状态 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <StatusCard
          icon={<Database className="w-4 h-4" />}
          title="数据库"
          status={data.database.status}
          detail={`${data.database.latency_ms}ms`}
        />
        <StatusCard
          icon={<Zap className="w-4 h-4" />}
          title="Redis"
          status={data.redis.status}
          detail={`${data.redis.latency_ms}ms`}
        />
      </div>

      {/* 文档索引统计 */}
      <div className="p-4 rounded-xl border" style={{ borderColor: 'var(--c-border)', background: 'var(--c-surface)' }}>
        <div className="flex items-center gap-2 mb-3">
          <FileText className="w-4 h-4" style={{ color: 'var(--c-text-tertiary)' }} />
          <span className="text-sm font-medium">文档索引</span>
        </div>
        <div className="grid grid-cols-4 gap-3">
          <StatItem label="总计" value={data.documents.total} />
          <StatItem label="已索引" value={data.documents.indexed} color="#16a34a" />
          <StatItem label="处理中" value={data.documents.processing} color="#d97706" />
          <StatItem label="失败" value={data.documents.failed} color="#dc2626" />
        </div>
      </div>

      {/* 最近失败文档 */}
      {data.documents.recent_failed.length > 0 && (
        <div className="p-4 rounded-xl border" style={{ borderColor: 'var(--c-border)', background: 'var(--c-surface)' }}>
          <div className="text-sm font-medium mb-3">最近失败文档</div>
          <div className="space-y-2">
            {data.documents.recent_failed.map((doc) => (
              <div
                key={doc.id}
                className="p-2.5 rounded-lg text-xs"
                style={{ background: 'var(--c-bg)', border: '1px solid var(--c-border)' }}
              >
                <div className="font-medium truncate">{doc.title}</div>
                {doc.error_message && (
                  <div className="mt-1 truncate" style={{ color: 'var(--c-error)' }}>
                    {doc.error_message}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* RAG Eval 摘要 */}
      <div className="p-4 rounded-xl border" style={{ borderColor: 'var(--c-border)', background: 'var(--c-surface)' }}>
        <div className="flex items-center gap-2 mb-3">
          <BarChart3 className="w-4 h-4" style={{ color: 'var(--c-text-tertiary)' }} />
          <span className="text-sm font-medium">RAG 评测</span>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <StatItem label="总运行" value={data.rag_evals.total_runs} />
          <StatItem label="通过" value={data.rag_evals.latest_passed} color="#16a34a" />
          <StatItem label="失败" value={data.rag_evals.latest_failed} color="#dc2626" />
        </div>
        {data.rag_evals.latest_score !== null && (
          <div className="mt-2 text-xs" style={{ color: 'var(--c-text-tertiary)' }}>
            平均分：{data.rag_evals.latest_score}
          </div>
        )}
      </div>

      {/* Feedback 摘要 */}
      <div className="p-4 rounded-xl border" style={{ borderColor: 'var(--c-border)', background: 'var(--c-surface)' }}>
        <div className="flex items-center gap-2 mb-3">
          <MessageSquare className="w-4 h-4" style={{ color: 'var(--c-text-tertiary)' }} />
          <span className="text-sm font-medium">用户反馈</span>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <StatItem label="👍 有帮助" value={data.feedback.up} color="#16a34a" />
          <StatItem label="👎 无帮助" value={data.feedback.down} color="#dc2626" />
        </div>
      </div>
    </div>
  );
}

function StatusCard({
  icon,
  title,
  status,
  detail,
}: {
  icon: React.ReactNode;
  title: string;
  status: string;
  detail: string;
}) {
  return (
    <div className="p-3 rounded-xl border" style={{ borderColor: 'var(--c-border)', background: 'var(--c-surface)' }}>
      <div className="flex items-center gap-2 mb-1">
        <span style={{ color: 'var(--c-text-tertiary)' }}>{icon}</span>
        <span className="text-xs font-medium">{title}</span>
        <div
          className="w-2 h-2 rounded-full ml-auto"
          style={{ background: status === 'ok' ? '#16a34a' : '#dc2626' }}
        />
      </div>
      <div className="text-xs" style={{ color: 'var(--c-text-tertiary)' }}>
        {status === 'ok' ? `正常 · ${detail}` : '异常'}
      </div>
    </div>
  );
}

function StatItem({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color?: string;
}) {
  return (
    <div className="text-center">
      <div className="text-lg font-semibold" style={{ color: color || 'var(--c-text)' }}>
        {value}
      </div>
      <div className="text-[10px]" style={{ color: 'var(--c-text-tertiary)' }}>
        {label}
      </div>
    </div>
  );
}
