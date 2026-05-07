'use client';

import { useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useStore } from '@/lib/store';
import { api } from '@/lib/api';
import { toast } from '@/components/Toast';
import ConfirmDialog from '@/components/ConfirmDialog';
import {
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
  Plus,
  type LucideIcon,
  MessageSquare,
  FileText,
  Bot,
  Settings,
  LogOut,
  Download,
  Trash2,
} from 'lucide-react';

interface NavItem {
  path: string;
  label: string;
  icon: LucideIcon;
  admin?: boolean;
}
const NAV: NavItem[] = [
  { path: '/chat', label: '对话', icon: MessageSquare },
  { path: '/documents', label: '文档', icon: FileText },
  { path: '/agents', label: 'Agent', icon: Bot },
  { path: '/admin', label: '管理', icon: Settings, admin: true },
];

export default function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const isChat = pathname?.startsWith('/chat');
  const {
    conversations,
    currentConvId,
    setCurrentConvId,
    removeConversation,
    logout,
    user,
    sidebarCollapsed,
    toggleSidebar,
  } = useStore();
  const [confirmTarget, setConfirmTarget] = useState<string | null>(null);
  const [kbs, setKbs] = useState<{ id: string; name: string }[]>([]);
  const [chatKbId, setChatKbId] = useState('');
  const [deleting, setDeleting] = useState(false);
  const [search, setSearch] = useState('');
  const [renaming, setRenaming] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (isChat)
      api
        .get<any[]>('/knowledge-bases')
        .then((items) => setKbs(Array.isArray(items) ? items : []))
        .catch(() => {});
  }, [isChat]);

  useEffect(() => {
    if (kbs.length > 0 && !chatKbId) setChatKbId(kbs[0].id);
  }, [kbs]);

  useEffect(() => {
    setMobileOpen(false);
  }, [currentConvId]);

  const filtered = search
    ? conversations.filter((c) => (c.title || '').toLowerCase().includes(search.toLowerCase()))
    : conversations;
  const initial = (user?.name || 'U').charAt(0).toUpperCase();

  const closeMobile = () => setMobileOpen(false);
  const nav = (path: string) => {
    router.push(path);
    closeMobile();
  };

  const isActive = (path: string) => {
    if (path === '/chat') return pathname?.startsWith('/chat');
    if (path === '/admin') return pathname?.startsWith('/admin');
    return pathname === path;
  };

  const handleDelete = async () => {
    if (!confirmTarget) return;
    const id = confirmTarget;
    setConfirmTarget(null);
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

  const handleExport = async (id: string, fmt: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const blob = await api.download(`/chat/conversations/${id}/export?format=${fmt}`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${id}.${fmt === 'markdown' ? 'md' : 'json'}`;
      a.click();
      URL.revokeObjectURL(url);
      toast('导出成功', 'success');
    } catch {
      toast('导出失败', 'error');
    }
  };

  const startRename = (id: string, title: string) => {
    setRenaming(id);
    setRenameValue(title || '');
  };

  const submitRename = async (id: string) => {
    const val = renameValue.trim();
    if (val) {
      try {
        await api.patch(`/chat/conversations/${id}`, { title: val });
      } catch {}
      useStore.setState((s) => ({
        conversations: s.conversations.map((c) => (c.id === id ? { ...c, title: val } : c)),
      }));
    }
    setRenaming(null);
  };

  const navItems = NAV.filter((i) => !i.admin || user?.role === 'admin');

  const sidebarContent = sidebarCollapsed ? (
    <div
      className="flex flex-col items-center gap-3 py-3 h-full"
      style={{ color: 'var(--c-text-secondary)' }}
    >
      <button
        onClick={toggleSidebar}
        className="p-2 rounded-lg hover:bg-gray-100 transition-colors border-none cursor-pointer"
        title="展开"
      >
        <ChevronRight className="w-5 h-5" />
      </button>
      <button
        onClick={() => {
          setCurrentConvId(null);
          nav('/chat');
        }}
        className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 border-none cursor-pointer"
        title="新对话"
      >
        <Plus className="w-5 h-5" />
      </button>
      {navItems.map((item) => (
        <button
          key={item.path}
          onClick={() => nav(item.path)}
          className="p-2 rounded-lg hover:bg-gray-100 transition-colors border-none cursor-pointer"
          title={item.label}
        >
          <item.icon className="w-5 h-5" />
        </button>
      ))}
      <div className="flex-1" />
      <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold text-white mb-2">
        {initial}
      </div>
      <button
        onClick={() => {
          logout();
          router.push('/login');
        }}
        className="p-2 rounded-lg hover:bg-gray-100 transition-colors border-none cursor-pointer"
        title="退出"
      >
        <LogOut className="w-5 h-5" />
      </button>
    </div>
  ) : (
    <>
      <div className="px-5 py-4 border-b shrink-0" style={{ borderColor: 'var(--c-border)' }}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold" style={{ letterSpacing: '-0.3px' }}>
              KnowFlow
            </h1>
            <p className="text-xs mt-0.5" style={{ color: 'var(--c-text-tertiary)' }}>
              知识库管理系统
            </p>
          </div>
          <button
            onClick={toggleSidebar}
            className="p-1 rounded hover:bg-gray-100 transition-colors max-md:hidden border-none cursor-pointer"
            style={{ color: 'var(--c-text-tertiary)' }}
            title="收起"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={closeMobile}
            className="p-1 rounded hover:bg-gray-100 transition-colors md:hidden border-none cursor-pointer"
            style={{ color: 'var(--c-text-tertiary)' }}
            title="关闭"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      <nav className="px-2.5 py-3 flex flex-col gap-0.5 shrink-0">
        {navItems.map((item) => {
          const active = isActive(item.path);
          return (
            <button
              key={item.path}
              onClick={() => nav(item.path)}
              className="flex items-center gap-2.5 px-3 py-2 rounded-md text-sm w-full text-left relative border-none cursor-pointer transition-all"
              style={{
                color: active ? 'var(--c-primary)' : 'var(--c-text-secondary)',
                background: active ? 'var(--c-primary-subtle)' : 'transparent',
                fontWeight: active ? 500 : 400,
              }}
            >
              {active && (
                <span
                  className="absolute left-0 top-2 bottom-2 w-0.5 rounded-r-sm"
                  style={{ background: 'var(--c-primary)' }}
                />
              )}
              <item.icon
                className="w-[18px] h-[18px] shrink-0"
                style={{ opacity: active ? 1 : 0.7 }}
              />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {isChat && (
        <div className="px-3 shrink-0">
          <button
            onClick={() => {
              setCurrentConvId(null);
              nav('/chat');
            }}
            className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium border-none cursor-pointer"
          >
            + 新对话
          </button>
          {kbs.length > 0 && (
            <select
              value={chatKbId}
              onChange={(e) => setChatKbId(e.target.value)}
              className="w-full text-xs rounded px-2 py-1.5 mt-2 border outline-none cursor-pointer"
              style={{
                borderColor: 'var(--c-border)',
                color: 'var(--c-text)',
                background: 'var(--c-surface)',
              }}
            >
              <option value="">全部知识库</option>
              {kbs.map((kb) => (
                <option key={kb.id} value={kb.id}>
                  {kb.name}
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      {isChat && (
        <>
          <div className="px-3 pt-3 shrink-0">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="搜索对话..."
              className="w-full text-xs rounded px-2 py-1.5 border outline-none transition-colors placeholder-gray-400"
              style={{
                borderColor: 'var(--c-border)',
                color: 'var(--c-text)',
                background: 'var(--c-bg)',
              }}
            />
          </div>
          <div className="flex-1 overflow-y-auto px-3 pt-2 space-y-0.5">
            {filtered.length === 0 && search ? (
              <p className="text-xs text-center py-4" style={{ color: 'var(--c-text-tertiary)' }}>
                未找到匹配的对话
              </p>
            ) : (
              filtered.map((conv) => (
                <div
                  key={conv.id}
                  className="group relative rounded-md text-sm"
                  style={{
                    background:
                      currentConvId === conv.id ? 'var(--c-primary-subtle)' : 'transparent',
                  }}
                >
                  {renaming === conv.id ? (
                    <input
                      autoFocus
                      value={renameValue}
                      onChange={(e) => setRenameValue(e.target.value)}
                      onBlur={() => submitRename(conv.id)}
                      onKeyDown={(e) => e.key === 'Enter' && submitRename(conv.id)}
                      className="w-full rounded px-3 py-2 text-sm outline-none"
                      style={{
                        background: 'var(--c-surface)',
                        border: '1px solid var(--c-primary)',
                        color: 'var(--c-text)',
                      }}
                      onClick={(e) => e.stopPropagation()}
                    />
                  ) : (
                    <button
                      onClick={() => {
                        setCurrentConvId(conv.id);
                        router.push(`/chat/${conv.id}`);
                        closeMobile();
                      }}
                      onDoubleClick={() => startRename(conv.id, conv.title)}
                      className="w-full text-left px-3 py-2 truncate border-none cursor-pointer transition-all"
                      style={{
                        color:
                          currentConvId === conv.id
                            ? 'var(--c-primary)'
                            : 'var(--c-text-secondary)',
                        background: 'none',
                        fontWeight: currentConvId === conv.id ? 500 : 400,
                      }}
                    >
                      {conv.title || '新对话'}
                    </button>
                  )}
                  <div className="absolute right-1 top-1/2 -translate-y-1/2 hidden group-hover:flex gap-0.5">
                    <button
                      onClick={(e) => handleExport(conv.id, 'markdown', e)}
                      className="p-1 rounded border-none cursor-pointer transition-colors"
                      style={{ color: 'var(--c-text-tertiary)', background: 'none' }}
                      title="导出 MD"
                    >
                      <Download className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setConfirmTarget(conv.id);
                      }}
                      disabled={deleting}
                      className="p-1 rounded border-none cursor-pointer transition-colors disabled:opacity-50"
                      style={{ color: 'var(--c-text-tertiary)', background: 'none' }}
                      title="删除"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      )}

      <div
        className="mt-auto px-5 py-4 border-t flex items-center gap-2.5 shrink-0"
        style={{ borderColor: 'var(--c-border)' }}
      >
        <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold text-white shrink-0">
          {initial}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium truncate">{user?.name || '未登录'}</div>
          <div className="text-xs" style={{ color: 'var(--c-text-tertiary)' }}>
            {user?.role === 'admin' ? '管理员' : '用户'}
          </div>
        </div>
        <button
          onClick={() => {
            logout();
            router.push('/login');
          }}
          className="p-1.5 rounded transition-colors border-none cursor-pointer"
          style={{ color: 'var(--c-text-tertiary)', background: 'none' }}
          title="退出"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </>
  );

  return (
    <>
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed top-2 left-2 z-30 p-2 rounded-lg shadow md:hidden border-none cursor-pointer"
        style={{ background: 'var(--c-surface)', color: 'var(--c-text-secondary)' }}
        aria-label="菜单"
      >
        <Menu className="w-5 h-5" />
      </button>

      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 md:hidden"
          onClick={closeMobile}
          style={{ background: 'rgba(15,23,42,.35)', backdropFilter: 'blur(2px)' }}
        />
      )}

      <div
        className={`${sidebarCollapsed ? 'w-14' : 'w-[268px]'} flex flex-col shrink-0 h-screen transition-all duration-200`}
        style={{
          background: 'rgba(255,255,255,.9)',
          backdropFilter: 'blur(8px)',
          borderRight: '1px solid var(--c-border)',
          boxShadow: 'var(--shadow-sm)',
          position: mobileOpen ? 'fixed' : undefined,
          left: 0,
          top: 0,
          zIndex: 50,
          transform: mobileOpen ? 'translateX(0)' : undefined,
        }}
      >
        {sidebarContent}
      </div>

      <ConfirmDialog
        open={!!confirmTarget}
        title="删除对话"
        message="确定删除该对话？删除后不可恢复。"
        confirmText="删除"
        danger
        onConfirm={handleDelete}
        onCancel={() => setConfirmTarget(null)}
      />
    </>
  );
}
