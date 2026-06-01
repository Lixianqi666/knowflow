'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { RefreshCw, Shield } from 'lucide-react';

interface AuditLogItem {
  id: string;
  actor_email?: string | null;
  action: string;
  resource_type?: string | null;
  resource_id?: string | null;
  status: string;
  ip?: string | null;
  metadata?: Record<string, unknown>;
  created_at: string;
}

interface AuditLogsResponse {
  items: AuditLogItem[];
  total: number;
  limit: number;
  offset: number;
}

const ACTION_OPTIONS = [
  '',
  'auth.login.success',
  'auth.login.failed',
  'document.upload',
  'document.delete',
  'document.retry_index',
  'chat.feedback',
  'rag_eval.run',
  'admin.health.view',
];

export default function AuditTab() {
  const [data, setData] = useState<AuditLogsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionFilter, setActionFilter] = useState('');

  const load = () => {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams();
    if (actionFilter) params.set('action', actionFilter);
    params.set('limit', '50');

    api
      .get<AuditLogsResponse>(`/admin/audit-logs?${params}`)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, [actionFilter]);

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

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4" style={{ color: 'var(--c-text-tertiary)' }} />
          <h3 className="text-sm font-semibold">审计日志</h3>
          {data && (
            <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: 'var(--c-bg)', color: 'var(--c-text-tertiary)' }}>
              {data.total} 条
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="text-xs rounded-lg px-2 py-1.5 border input-base cursor-pointer"
          >
            <option value="">全部操作</option>
            {ACTION_OPTIONS.filter(Boolean).map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
          <button
            onClick={load}
            className="text-xs flex items-center gap-1 px-2 py-1.5 rounded-lg border-none cursor-pointer"
            style={{ color: 'var(--c-text-tertiary)', background: 'none' }}
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {!data || data.items.length === 0 ? (
        <div className="text-center py-12">
          <Shield className="w-8 h-8 mx-auto mb-3" style={{ color: 'var(--c-text-tertiary)', opacity: 0.3 }} />
          <p className="text-sm" style={{ color: 'var(--c-text-tertiary)' }}>暂无审计日志</p>
        </div>
      ) : (
        <div className="space-y-1.5">
          {data.items.map((item) => (
            <div
              key={item.id}
              className="p-3 rounded-lg text-xs"
              style={{ background: 'var(--c-surface)', border: '1px solid var(--c-border)' }}
            >
              <div className="flex items-center gap-2 flex-wrap">
                <span
                  className="px-1.5 py-0.5 rounded text-[10px] font-medium"
                  style={{
                    background: item.status === 'success' ? 'var(--c-success-subtle)' : 'var(--c-error-subtle)',
                    color: item.status === 'success' ? '#16a34a' : '#dc2626',
                  }}
                >
                  {item.status}
                </span>
                <span className="font-mono font-medium" style={{ color: 'var(--c-primary)' }}>
                  {item.action}
                </span>
                {item.resource_type && (
                  <span style={{ color: 'var(--c-text-tertiary)' }}>
                    {item.resource_type}
                  </span>
                )}
                <span className="ml-auto" style={{ color: 'var(--c-text-tertiary)' }}>
                  {new Date(item.created_at).toLocaleString('zh-CN')}
                </span>
              </div>
              <div className="mt-1.5 flex items-center gap-2 flex-wrap" style={{ color: 'var(--c-text-tertiary)' }}>
                {item.actor_email && <span>{item.actor_email}</span>}
                {item.ip && <span>IP: {item.ip}</span>}
              </div>
              {item.metadata && Object.keys(item.metadata).length > 0 && (
                <div className="mt-1.5 font-mono truncate" style={{ color: 'var(--c-text-tertiary)', fontSize: '10px' }}>
                  {JSON.stringify(item.metadata)}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
