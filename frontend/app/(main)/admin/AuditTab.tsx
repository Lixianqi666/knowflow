'use client';

import { AuditLogItem, ACTION_LABELS } from './types';

interface AuditTabProps {
  auditLogs: AuditLogItem[];
  auditLoading: boolean;
  auditFilter: string;
  onSetAuditFilter: (v: string) => void;
  onRefresh: () => void;
}

export default function AuditTab({
  auditLogs,
  auditLoading,
  auditFilter,
  onSetAuditFilter,
  onRefresh,
}: AuditTabProps) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-4">
        <input
          value={auditFilter}
          onChange={(e) => onSetAuditFilter(e.target.value)}
          placeholder="筛选操作类型 (send_message/view_doc/download_file/...)"
          className="flex-1 text-sm border rounded-lg px-3 py-1.5 input-base"
        />
        <button onClick={onRefresh} className="text-xs text-blue-600 hover:underline">
          刷新
        </button>
      </div>
      {auditLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="bg-white rounded-xl border p-4">
              <div className="skeleton h-4 w-3/4 mb-2" />
              <div className="skeleton h-3 w-1/2" />
            </div>
          ))}
        </div>
      ) : auditLogs.length === 0 ? (
        <div className="py-12 text-center text-gray-400 text-sm">暂无审计日志</div>
      ) : (
        <div className="space-y-2">
          {auditLogs
            .filter(
              (log) =>
                !auditFilter ||
                log.action.includes(auditFilter) ||
                (log.resource_type ?? '').includes(auditFilter),
            )
            .map((log) => (
              <div key={log.id} className="bg-white rounded-xl border p-4">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">
                      {ACTION_LABELS[log.action] || log.action}
                    </span>
                    {log.resource_type && <span className="text-xs text-gray-400">{log.resource_type}</span>}
                    {log.ip && <span className="text-xs text-gray-300">{log.ip}</span>}
                  </div>
                  <span className="text-xs text-gray-400">
                    {new Date(log.created_at).toLocaleString()}
                  </span>
                </div>
                {log.actor_email && <p className="text-xs text-gray-400">{log.actor_email}</p>}
                {log.resource_id && (
                  <p className="text-xs text-gray-400 mt-0.5">资源ID: {log.resource_id}</p>
                )}
                {log.metadata && Object.keys(log.metadata).length > 0 && (
                  <p className="text-xs text-gray-400 mt-0.5 font-mono truncate">{JSON.stringify(log.metadata)}</p>
                )}
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
