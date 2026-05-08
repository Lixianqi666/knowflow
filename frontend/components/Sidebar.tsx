'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useStore } from '@/lib/store';
import { api } from '@/lib/api';
import { toast } from '@/components/Toast';
import ConfirmDialog from '@/components/ConfirmDialog';
import {
  Menu,
  X,
  Plus,
  Search,
  MoreHorizontal,
  Trash2,
  LogOut,
  MessageSquare,
  FileText,
  Bot,
  Settings,
  Pencil,
  Pin,
} from 'lucide-react';

function groupByDate(convs: any[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 7 * 86400000);

  const groups: { label: string; items: any[] }[] = [];
  const map: Record<string, any[]> = { today: [], yesterday: [], week: [], older: [] };

  for (const c of convs) {
    const d = new Date(c.created_at);
    if (d >= today) map.today.push(c);
    else if (d >= yesterday) map.yesterday.push(c);
    else if (d >= weekAgo) map.week.push(c);
    else map.older.push(c);
  }

  if (map.today.length) groups.push({ label: '今天', items: map.today });
  if (map.yesterday.length) groups.push({ label: '昨天', items: map.yesterday });
  if (map.week.length) groups.push({ label: '7 天内', items: map.week });
  if (map.older.length) groups.push({ label: '更早', items: map.older });

  return groups;
}

export default function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const { conversations, currentConvId, setCurrentConvId, removeConversation, logout, user } =
    useStore();
  const [confirmTarget, setConfirmTarget] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [search, setSearch] = useState('');
  const [mobileOpen, setMobileOpen] = useState(false);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [contextMenuId, setContextMenuId] = useState<string | null>(null);
  const [menuPos, setMenuPos] = useState<{ top: number; left: number } | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');

  useEffect(() => {
    setMobileOpen(false);
  }, [currentConvId]);

  // 点击外部关闭菜单
  useEffect(() => {
    if (!contextMenuId) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.closest('[data-context-menu]')) {
        setContextMenuId(null);
        setMenuPos(null);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [contextMenuId]);

  // ⌘J 快捷键：新对话
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'j') {
        e.preventDefault();
        setCurrentConvId(null);
        router.push('/chat');
        closeMobile();
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [router, setCurrentConvId]);

  const filtered = search
    ? conversations.filter((c) => (c.title || '').toLowerCase().includes(search.toLowerCase()))
    : conversations;

  const groups = useMemo(() => groupByDate(filtered), [filtered]);
  const initial = (user?.name || 'U').charAt(0).toUpperCase();

  const isChatActive = pathname?.startsWith('/chat');
  const isDocsActive = pathname?.startsWith('/documents');
  const isAgentsActive = pathname?.startsWith('/agents');
  const isAdminActive = pathname?.startsWith('/admin');

  const nav = (path: string) => {
    router.push(path);
    closeMobile();
  };
  const closeMobile = () => setMobileOpen(false);

  const handleNewChat = () => {
    setCurrentConvId(null);
    router.push('/chat');
    closeMobile();
  };

  const handleDelete = async () => {
    if (!confirmTarget) return;
    const id = confirmTarget;
    setConfirmTarget(null);
    setContextMenuId(null);
    setMenuPos(null);
    setDeleting(true);
    try {
      await api.delete(`/chat/conversations/${id}`);
      removeConversation(id);
      if (currentConvId === id) router.push('/chat');
      toast('对话已删除', 'success');
    } catch {
      toast('删除失败', 'error');
    } finally {
      setDeleting(false);
    }
  };

  const startRename = (conv: any) => {
    setRenamingId(conv.id);
    setRenameValue(conv.title || '');
    setContextMenuId(null);
    setMenuPos(null);
  };

  const submitRename = async () => {
    if (!renamingId || !renameValue.trim()) {
      setRenamingId(null);
      return;
    }
    try {
      await api.patch(`/chat/conversations/${renamingId}`, { title: renameValue.trim() });
      useStore.setState((s) => ({
        conversations: s.conversations.map((c) =>
          c.id === renamingId ? { ...c, title: renameValue.trim() } : c,
        ),
      }));
      toast('已重命名', 'success');
    } catch {
      toast('重命名失败', 'error');
    } finally {
      setRenamingId(null);
    }
  };

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed top-3 left-3 z-30 p-2 rounded-xl shadow-sm md:hidden border-none cursor-pointer transition-all hover:scale-105 active:scale-95"
        style={{ background: 'var(--c-surface)', color: 'var(--c-text-secondary)' }}
        aria-label="菜单"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden"
          style={{ background: 'rgba(0,0,0,.3)', backdropFilter: 'blur(2px)' }}
          onClick={closeMobile}
        />
      )}

      {/* Sidebar */}
      <div
        className={`flex flex-col shrink-0 h-screen overflow-hidden transition-all duration-300
          md:w-[260px] md:min-w-[260px]
          ${mobileOpen ? 'w-[260px] min-w-[260px] fixed z-50 left-0 top-0' : 'w-0 min-w-0'}`}
        style={{
          background: '#fff',
          borderRight: '1px solid var(--c-border)',
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 pt-4 pb-4 shrink-0">
          <div className="flex items-center gap-2">
            <div
              className="w-7 h-7 rounded-lg flex items-center justify-center text-white text-xs font-bold"
              style={{
                background: 'linear-gradient(135deg, #4f6ef7 0%, #2563eb 100%)',
                boxShadow: '0 2px 8px rgba(37,99,235,.3)',
              }}
            >
              K
            </div>
            <span className="text-sm font-semibold" style={{ color: 'var(--c-text)' }}>
              KnowFlow
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => {
                /* TODO: 全局搜索 */
              }}
              className="p-1.5 rounded-lg transition-colors border-none cursor-pointer"
              style={{ color: 'var(--c-text-tertiary)', background: 'none' }}
              title="搜索"
            >
              <Search className="w-4 h-4" />
            </button>
            <button
              onClick={closeMobile}
              className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors md:hidden border-none cursor-pointer"
              style={{ color: 'var(--c-text-tertiary)' }}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* New chat button */}
        <div className="px-3 pb-3 shrink-0">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-full border text-sm transition-all cursor-pointer"
            style={{
              borderColor: '#e5e7eb',
              color: '#374151',
              background: '#fff',
              fontWeight: 400,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#f9fafb';
              e.currentTarget.style.borderColor = '#d1d5db';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = '#fff';
              e.currentTarget.style.borderColor = '#e5e7eb';
            }}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#6b7280"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="16" />
              <line x1="8" y1="12" x2="16" y2="12" />
            </svg>
            开启新对话
          </button>
        </div>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden px-2">
          {filtered.length === 0 && search ? (
            <p className="text-xs text-center py-8" style={{ color: 'var(--c-text-tertiary)' }}>
              未找到匹配的对话
            </p>
          ) : groups.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <MessageSquare
                className="w-8 h-8 mb-3"
                style={{ color: 'var(--c-text-tertiary)', opacity: 0.3 }}
              />
              <p className="text-xs" style={{ color: 'var(--c-text-tertiary)' }}>
                暂无对话
              </p>
            </div>
          ) : (
            groups.map((group) => (
              <div key={group.label} className="mb-1">
                <div
                  className="px-3 py-2 text-xs font-medium"
                  style={{ color: 'var(--c-text-tertiary)' }}
                >
                  {group.label}
                </div>
                {group.items.map((conv) => {
                  const active = currentConvId === conv.id;
                  const hovered = hoveredId === conv.id;
                  const isRenaming = renamingId === conv.id;
                  return (
                    <div
                      key={conv.id}
                      className="relative group"
                      onMouseEnter={() => setHoveredId(conv.id)}
                      onMouseLeave={() => setHoveredId(null)}
                    >
                      {isRenaming ? (
                        <div className="px-3 py-1.5">
                          <input
                            value={renameValue}
                            onChange={(e) => setRenameValue(e.target.value)}
                            onBlur={submitRename}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') submitRename();
                              if (e.key === 'Escape') setRenamingId(null);
                            }}
                            className="w-full text-sm px-2 py-1 rounded-lg border outline-none"
                            style={{
                              borderColor: 'var(--c-primary)',
                              color: 'var(--c-text)',
                              background: '#fff',
                              boxShadow: '0 0 0 2px var(--c-primary-ring)',
                            }}
                            autoFocus
                          />
                        </div>
                      ) : (
                        <button
                          onClick={() => {
                            setCurrentConvId(conv.id);
                            router.push(`/chat/${conv.id}`);
                            closeMobile();
                          }}
                          className="w-full text-left px-3 py-2 rounded-xl text-sm transition-all border-none cursor-pointer"
                          style={{
                            color: active ? 'var(--c-primary)' : 'var(--c-text)',
                            fontWeight: active ? 500 : 400,
                            background: active
                              ? 'var(--c-primary-subtle)'
                              : hovered
                                ? 'var(--c-bg)'
                                : 'transparent',
                          }}
                        >
                          <span className="truncate block">{conv.title || '新对话'}</span>
                        </button>
                      )}

                      {/* Three-dot menu */}
                      {hovered && !isRenaming && (
                        <div className="absolute right-1.5 top-1/2 -translate-y-1/2">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              if (contextMenuId === conv.id) {
                                setContextMenuId(null);
                                setMenuPos(null);
                              } else {
                                const rect = (
                                  e.currentTarget as HTMLElement
                                ).getBoundingClientRect();
                                setMenuPos({ top: rect.bottom + 4, left: rect.left });
                                setContextMenuId(conv.id);
                              }
                            }}
                            className="p-1 rounded-md border-none cursor-pointer transition-colors"
                            style={{
                              color: 'var(--c-text-tertiary)',
                              background: 'var(--c-bg)',
                            }}
                          >
                            <MoreHorizontal className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ))
          )}
        </div>

        {/* Bottom: Nav + User */}
        <div className="shrink-0 border-t" style={{ borderColor: 'var(--c-border)' }}>
          {/* Nav row */}
          <div className="flex px-2 pt-2 pb-1 gap-0.5">
            {[
              { path: '/chat', label: '对话', icon: MessageSquare, active: isChatActive },
              { path: '/documents', label: '文档', icon: FileText, active: isDocsActive },
              { path: '/agents', label: 'Agent', icon: Bot, active: isAgentsActive },
              ...(user?.role === 'admin'
                ? [{ path: '/admin', label: '管理', icon: Settings, active: isAdminActive }]
                : []),
            ].map((item) => (
              <button
                key={item.path}
                onClick={() => nav(item.path)}
                className="flex-1 flex flex-col items-center gap-0.5 py-1.5 rounded-lg border-none cursor-pointer transition-all text-[10px]"
                style={{
                  color: item.active ? 'var(--c-primary)' : 'var(--c-text-tertiary)',
                  background: item.active ? 'var(--c-primary-subtle)' : 'transparent',
                  fontWeight: item.active ? 600 : 400,
                }}
              >
                <item.icon className="w-4 h-4" />
                <span>{item.label}</span>
              </button>
            ))}
          </div>

          {/* User */}
          <div className="flex items-center gap-2.5 px-3 py-2.5">
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0"
              style={{
                background: 'linear-gradient(135deg, #4f6ef7 0%, #2563eb 100%)',
                boxShadow: '0 2px 6px rgba(37,99,235,.25)',
              }}
            >
              {initial}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate" style={{ color: 'var(--c-text)' }}>
                {user?.name || '未登录'}
              </div>
              <div className="text-[10px]" style={{ color: 'var(--c-text-tertiary)' }}>
                {user?.role === 'admin' ? '管理员' : '成员'}
              </div>
            </div>
            <button
              onClick={() => {
                logout();
                router.push('/login');
              }}
              className="p-1.5 rounded-lg transition-colors border-none cursor-pointer"
              style={{ color: 'var(--c-text-tertiary)', background: 'none' }}
              title="退出登录"
              onMouseEnter={(e) => {
                e.currentTarget.style.color = 'var(--c-error)';
                e.currentTarget.style.background = 'var(--c-error-subtle)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = 'var(--c-text-tertiary)';
                e.currentTarget.style.background = 'none';
              }}
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Context menu (fixed position, floats above everything) */}
      {contextMenuId && menuPos && (
        <div
          data-context-menu
          className="fixed rounded-xl py-1 z-[100] min-w-[140px]"
          style={{
            top: menuPos.top,
            left: menuPos.left,
            background: '#fff',
            border: '1px solid var(--c-border)',
            boxShadow: '0 6px 20px rgba(0,0,0,.12)',
          }}
        >
          <button
            onClick={() => {
              const conv = conversations.find((c) => c.id === contextMenuId);
              if (conv) startRename(conv);
            }}
            className="w-full flex items-center gap-2.5 px-3 py-2 text-sm border-none cursor-pointer transition-colors"
            style={{ color: 'var(--c-text)', background: 'none' }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--c-bg)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'none';
            }}
          >
            <Pencil className="w-3.5 h-3.5" style={{ color: 'var(--c-text-tertiary)' }} />
            重命名
          </button>
          <button
            onClick={() => {
              setContextMenuId(null);
              setMenuPos(null);
              toast('置顶功能开发中', 'info');
            }}
            className="w-full flex items-center gap-2.5 px-3 py-2 text-sm border-none cursor-pointer transition-colors"
            style={{ color: 'var(--c-text)', background: 'none' }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--c-bg)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'none';
            }}
          >
            <Pin className="w-3.5 h-3.5" style={{ color: 'var(--c-text-tertiary)' }} />
            置顶
          </button>
          <div className="my-1 mx-2 border-t" style={{ borderColor: 'var(--c-border)' }} />
          <button
            onClick={() => {
              setConfirmTarget(contextMenuId);
            }}
            disabled={deleting}
            className="w-full flex items-center gap-2.5 px-3 py-2 text-sm border-none cursor-pointer transition-colors disabled:opacity-50"
            style={{ color: 'var(--c-error)', background: 'none' }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--c-error-subtle)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'none';
            }}
          >
            <Trash2 className="w-3.5 h-3.5" />
            删除
          </button>
        </div>
      )}

      <ConfirmDialog
        open={!!confirmTarget}
        title="删除对话"
        message="确定删除该对话？删除后不可恢复。"
        confirmText="删除"
        danger
        onConfirm={handleDelete}
        onCancel={() => {
          setConfirmTarget(null);
          setContextMenuId(null);
          setMenuPos(null);
        }}
      />
    </>
  );
}
