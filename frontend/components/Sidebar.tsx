'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useStore, Conversation } from '@/lib/store';
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
  Moon,
  Sun,
} from 'lucide-react';

function groupByDate(convs: Conversation[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 7 * 86400000);

  const pinned: Conversation[] = [];
  const unpinned: Conversation[] = [];
  for (const c of convs) {
    (c.is_pinned ? pinned : unpinned).push(c);
  }

  const groups: { label: string; items: Conversation[] }[] = [];
  if (pinned.length) groups.push({ label: '置顶', items: pinned });

  const map: Record<string, Conversation[]> = { today: [], yesterday: [], week: [], older: [] };
  for (const c of unpinned) {
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
  const { conversations, currentConvId, setCurrentConvId, removeConversation, logout, user, theme, resolvedTheme, setTheme } =
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

  // 全局搜索
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<{
    conversations: { id: string; title: string; updated_at: string }[];
    documents: { id: string; title: string; status: string; created_at: string }[];
  } | null>(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const searchTimerRef = useState<{ current: ReturnType<typeof setTimeout> | null }>(() => ({
    current: null,
  }))[0];

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
      // ⌘K 快捷键：全局搜索
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        openSearch();
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

  const handleTogglePin = async (convId: string) => {
    setContextMenuId(null);
    setMenuPos(null);
    try {
      const res = await api.patch<any>(`/chat/conversations/${convId}/pin`);
      useStore.setState((s) => ({
        conversations: s.conversations.map((c) =>
          c.id === convId ? { ...c, is_pinned: res.is_pinned, pinned_at: res.pinned_at } : c,
        ),
      }));
      toast(res.is_pinned ? '已置顶' : '已取消置顶', 'success');
    } catch {
      toast('操作失败', 'error');
    }
  };

  const handleSearch = (value: string) => {
    setSearchQuery(value);
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
    if (!value.trim()) {
      setSearchResults(null);
      setSearchLoading(false);
      return;
    }
    setSearchLoading(true);
    searchTimerRef.current = setTimeout(async () => {
      try {
        const res = await api.get<any>(`/chat/search?q=${encodeURIComponent(value.trim())}`);
        setSearchResults(res);
      } catch {
        setSearchResults(null);
      } finally {
        setSearchLoading(false);
      }
    }, 300);
  };

  const openSearch = () => {
    setSearchOpen(true);
    setSearchQuery('');
    setSearchResults(null);
  };

  const closeSearch = () => {
    setSearchOpen(false);
    setSearchQuery('');
    setSearchResults(null);
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current);
  };

  const startRename = (conv: Conversation) => {
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
          background: 'var(--c-surface)',
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
              onClick={openSearch}
              className="p-1.5 rounded-lg transition-colors border-none cursor-pointer"
              style={{ color: 'var(--c-text-tertiary)', background: 'none' }}
              title="搜索 (⌘K)"
            >
              <Search className="w-4 h-4" />
            </button>
            <button
              onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
              className="p-1.5 rounded-lg transition-colors border-none cursor-pointer"
              style={{ color: 'var(--c-text-tertiary)', background: 'none' }}
              title={resolvedTheme === 'dark' ? '切换亮色模式' : '切换暗色模式'}
            >
              {resolvedTheme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
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
              borderColor: 'var(--c-border)',
              color: 'var(--c-text)',
              background: 'var(--c-surface)',
              fontWeight: 400,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--c-surface-hover)';
              e.currentTarget.style.borderColor = 'var(--c-border-hover)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'var(--c-surface)';
              e.currentTarget.style.borderColor = 'var(--c-border)';
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
                              background: 'var(--c-surface)',
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
                          <span className="flex items-center gap-1.5">
                            {conv.is_pinned && (
                              <Pin className="w-3 h-3 shrink-0" style={{ color: 'var(--c-primary)' }} />
                            )}
                            <span className="truncate">{conv.title || '新对话'}</span>
                          </span>
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
            background: 'var(--c-surface)',
            border: '1px solid var(--c-border)',
            boxShadow: 'var(--shadow-lg)',
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
          {(() => {
            const targetConv = conversations.find((c) => c.id === contextMenuId);
            const isPinned = targetConv?.is_pinned;
            return (
              <button
                onClick={() => handleTogglePin(contextMenuId!)}
                className="w-full flex items-center gap-2.5 px-3 py-2 text-sm border-none cursor-pointer transition-colors"
                style={{ color: 'var(--c-text)', background: 'none' }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'var(--c-bg)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'none';
                }}
              >
                <Pin className="w-3.5 h-3.5" style={{ color: isPinned ? 'var(--c-primary)' : 'var(--c-text-tertiary)' }} />
                {isPinned ? '取消置顶' : '置顶'}
              </button>
            );
          })()}
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

      {/* 全局搜索面板 */}
      {searchOpen && (
        <>
          <div
            className="fixed inset-0 z-[90]"
            style={{ background: 'rgba(0,0,0,.3)', backdropFilter: 'blur(2px)' }}
            onClick={closeSearch}
          />
          <div
            className="fixed z-[100] top-[15%] left-1/2 -translate-x-1/2 w-[90vw] max-w-lg rounded-2xl overflow-hidden"
            style={{
              background: 'var(--c-surface)',
              boxShadow: 'var(--shadow-lg)',
              border: '1px solid var(--c-border)',
            }}
          >
            <div className="flex items-center gap-2 px-4 py-3" style={{ borderBottom: '1px solid var(--c-border)' }}>
              <Search className="w-4 h-4 shrink-0" style={{ color: 'var(--c-text-tertiary)' }} />
              <input
                autoFocus
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Escape' && closeSearch()}
                placeholder="搜索对话和文档..."
                className="flex-1 text-sm outline-none border-none"
                style={{ color: 'var(--c-text)', background: 'transparent' }}
              />
              {searchQuery && (
                <button
                  onClick={() => handleSearch('')}
                  className="p-1 rounded-md border-none cursor-pointer"
                  style={{ color: 'var(--c-text-tertiary)', background: 'none' }}
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            <div className="max-h-[60vh] overflow-y-auto">
              {searchLoading ? (
                <div className="flex items-center justify-center py-8">
                  <div className="w-5 h-5 border-2 rounded-full animate-spin" style={{ borderColor: 'var(--c-border)', borderTopColor: 'var(--c-primary)' }} />
                </div>
              ) : searchResults ? (
                <>
                  {searchResults.conversations.length === 0 && searchResults.documents.length === 0 ? (
                    <p className="text-sm text-center py-8" style={{ color: 'var(--c-text-tertiary)' }}>
                      未找到匹配结果
                    </p>
                  ) : (
                    <>
                      {searchResults.conversations.length > 0 && (
                        <div>
                          <div className="px-4 py-2 text-xs font-medium" style={{ color: 'var(--c-text-tertiary)' }}>
                            对话
                          </div>
                          {searchResults.conversations.map((c) => (
                            <button
                              key={c.id}
                              onClick={() => {
                                setCurrentConvId(c.id);
                                router.push(`/chat/${c.id}`);
                                closeSearch();
                              }}
                              className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-left border-none cursor-pointer transition-colors"
                              style={{ color: 'var(--c-text)', background: 'none' }}
                              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--c-bg)'; }}
                              onMouseLeave={(e) => { e.currentTarget.style.background = 'none'; }}
                            >
                              <MessageSquare className="w-4 h-4 shrink-0" style={{ color: 'var(--c-text-tertiary)' }} />
                              <span className="truncate">{c.title || '新对话'}</span>
                            </button>
                          ))}
                        </div>
                      )}
                      {searchResults.documents.length > 0 && (
                        <div>
                          <div className="px-4 py-2 text-xs font-medium" style={{ color: 'var(--c-text-tertiary)', borderTop: '1px solid var(--c-border)' }}>
                            文档
                          </div>
                          {searchResults.documents.map((d) => (
                            <button
                              key={d.id}
                              onClick={() => {
                                router.push(`/documents`);
                                closeSearch();
                              }}
                              className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-left border-none cursor-pointer transition-colors"
                              style={{ color: 'var(--c-text)', background: 'none' }}
                              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--c-bg)'; }}
                              onMouseLeave={(e) => { e.currentTarget.style.background = 'none'; }}
                            >
                              <FileText className="w-4 h-4 shrink-0" style={{ color: 'var(--c-text-tertiary)' }} />
                              <span className="truncate">{d.title}</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </>
              ) : searchQuery ? (
                <p className="text-sm text-center py-8" style={{ color: 'var(--c-text-tertiary)' }}>
                  输入关键词开始搜索
                </p>
              ) : (
                <p className="text-sm text-center py-8" style={{ color: 'var(--c-text-tertiary)' }}>
                  搜索对话标题和文档标题
                </p>
              )}
            </div>
            <div className="px-4 py-2 text-[10px]" style={{ color: 'var(--c-text-tertiary)', borderTop: '1px solid var(--c-border)' }}>
              <kbd className="px-1 py-0.5 rounded text-[10px]" style={{ background: 'var(--c-bg)', border: '1px solid var(--c-border)' }}>⌘K</kbd> 打开搜索
              <span className="mx-2">·</span>
              <kbd className="px-1 py-0.5 rounded text-[10px]" style={{ background: 'var(--c-bg)', border: '1px solid var(--c-border)' }}>Esc</kbd> 关闭
            </div>
          </div>
        </>
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
