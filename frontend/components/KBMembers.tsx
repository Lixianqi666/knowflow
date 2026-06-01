'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { toast } from '@/components/Toast';
import { Users, UserPlus, RefreshCw, Trash2 } from 'lucide-react';

interface Member {
  user_id: string;
  email: string;
  name: string;
  role: string;
  created_at: string;
}

interface Props {
  kbId: string;
  currentUserRole: string | null;
}

export default function KBMembers({ kbId, currentUserRole }: Props) {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [newUserId, setNewUserId] = useState('');
  const [newRole, setNewRole] = useState('viewer');
  const [adding, setAdding] = useState(false);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [removingId, setRemovingId] = useState<string | null>(null);

  const canManage = currentUserRole === 'owner' || currentUserRole === 'admin';

  const loadMembers = () => {
    setLoading(true);
    api
      .get<Member[]>(`/knowledge-bases/${kbId}/members`)
      .then(setMembers)
      .catch((e) => toast(e.message, 'error'))
      .finally(() => setLoading(false));
  };

  useEffect(loadMembers, [kbId]);

  const handleAdd = async () => {
    if (!newUserId.trim()) return;
    setAdding(true);
    try {
      await api.post(`/knowledge-bases/${kbId}/members`, {
        user_id: newUserId,
        role: newRole,
      });
      setNewUserId('');
      setNewRole('viewer');
      setShowAdd(false);
      loadMembers();
      toast('成员已添加', 'success');
    } catch (e: any) {
      toast(e.message, 'error');
    } finally {
      setAdding(false);
    }
  };

  const handleUpdateRole = async (userId: string, role: string) => {
    setUpdatingId(userId);
    try {
      await api.patch(`/knowledge-bases/${kbId}/members/${userId}`, { role });
      loadMembers();
      toast('角色已更新', 'success');
    } catch (e: any) {
      toast(e.message, 'error');
    } finally {
      setUpdatingId(null);
    }
  };

  const handleRemove = async (userId: string) => {
    setRemovingId(userId);
    try {
      await api.delete(`/knowledge-bases/${kbId}/members/${userId}`);
      loadMembers();
      toast('成员已移除', 'success');
    } catch (e: any) {
      toast(e.message, 'error');
    } finally {
      setRemovingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <RefreshCw className="w-4 h-4 animate-spin" style={{ color: 'var(--c-text-tertiary)' }} />
        <span className="ml-2 text-sm" style={{ color: 'var(--c-text-tertiary)' }}>加载中...</span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4" style={{ color: 'var(--c-text-tertiary)' }} />
          <span className="text-sm font-medium">成员 ({members.length})</span>
        </div>
        {canManage && (
          <button
            onClick={() => setShowAdd(!showAdd)}
            className="text-xs flex items-center gap-1 px-2.5 py-1.5 rounded-lg border-none cursor-pointer"
            style={{ background: 'var(--c-primary)', color: '#fff' }}
          >
            <UserPlus className="w-3.5 h-3.5" />
            添加
          </button>
        )}
      </div>

      {showAdd && (
        <div className="p-3 rounded-xl border animate-slide-up" style={{ borderColor: 'var(--c-border)', background: 'var(--c-surface)' }}>
          <input
            value={newUserId}
            onChange={(e) => setNewUserId(e.target.value)}
            placeholder="用户 ID"
            className="w-full text-sm px-3 py-2 rounded-lg border input-base mb-2"
          />
          <select
            value={newRole}
            onChange={(e) => setNewRole(e.target.value)}
            className="w-full text-sm px-3 py-2 rounded-lg border input-base mb-2 cursor-pointer"
          >
            <option value="viewer">viewer（查看）</option>
            <option value="editor">editor（编辑）</option>
            <option value="owner">owner（管理）</option>
          </select>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowAdd(false)} className="text-xs px-3 py-1.5 rounded-lg border-none cursor-pointer" style={{ color: 'var(--c-text-secondary)', background: 'none' }}>取消</button>
            <button onClick={handleAdd} disabled={adding} className="text-xs px-3 py-1.5 rounded-lg border-none cursor-pointer disabled:opacity-50" style={{ background: 'var(--c-primary)', color: '#fff' }}>
              {adding ? '添加中...' : '添加'}
            </button>
          </div>
        </div>
      )}

      {members.length === 0 ? (
        <div className="text-center py-8">
          <Users className="w-8 h-8 mx-auto mb-3" style={{ color: 'var(--c-text-tertiary)', opacity: 0.3 }} />
          <p className="text-sm" style={{ color: 'var(--c-text-tertiary)' }}>暂无成员</p>
        </div>
      ) : (
        <div className="space-y-1.5">
          {members.map((m) => (
            <div
              key={m.user_id}
              className="flex items-center gap-3 p-3 rounded-lg"
              style={{ background: 'var(--c-surface)', border: '1px solid var(--c-border)' }}
            >
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{m.name || m.email}</div>
                <div className="text-xs" style={{ color: 'var(--c-text-tertiary)' }}>
                  {m.email}
                </div>
              </div>
              {canManage ? (
                <select
                  value={m.role}
                  onChange={(e) => handleUpdateRole(m.user_id, e.target.value)}
                  disabled={updatingId === m.user_id}
                  className="text-xs px-2 py-1 rounded-lg border input-base cursor-pointer disabled:opacity-50"
                >
                  <option value="viewer">viewer</option>
                  <option value="editor">editor</option>
                  <option value="owner">owner</option>
                </select>
              ) : (
                <span
                  className="text-xs px-2 py-1 rounded-full"
                  style={{ background: 'var(--c-bg)', color: 'var(--c-text-tertiary)' }}
                >
                  {m.role}
                </span>
              )}
              {canManage && (
                <button
                  onClick={() => handleRemove(m.user_id)}
                  disabled={removingId === m.user_id}
                  className="p-1.5 rounded-lg border-none cursor-pointer disabled:opacity-50 transition-all"
                  style={{ color: 'var(--c-text-tertiary)', background: 'none' }}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
