'use client';

import { useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useStore } from '@/lib/store';
import { api } from '@/lib/api';
import { toast } from '@/components/Toast';
import ConfirmDialog from '@/components/ConfirmDialog';
import {
  ChevronLeft, Menu, X, Plus, type LucideIcon,
  MessageSquare, FileText, Bot, Settings, LogOut, Search, Trash2,
} from 'lucide-react';

interface NavItem { path: string; label: string; icon: LucideIcon; admin?: boolean }
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
    conversations, currentConvId, setCurrentConvId,
    removeConversation, logout, user, sidebarCollapsed, toggleSidebar,
  } = useStore();
  const [confirmTarget, setConfirmTarget] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [search, setSearch] = useState('');
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => { setMobileOpen(false); }, [currentConvId]);

  const filtered = search
    ? conversations.filter((c) => (c.title || '').toLowerCase().includes(search.toLowerCase()))
    : conversations;
  const initial = (user?.name || 'U').charAt(0).toUpperCase();
  const navItems = NAV.filter((i) => !i.admin || user?.role === 'admin');

  const isActive = (path: string) => {
    if (path === '/chat') return pathname?.startsWith('/chat');
    if (path === '/admin') return pathname?.startsWith('/admin');
    return pathname === path;
  };

  const nav = (path: string) => { router.push(path); closeMobile(); };
  const closeMobile = () => setMobileOpen(false);

  const handleDelete = async () => {
    if (!confirmTarget) return;
    const id = confirmTarget;
    setConfirmTarget(null); setDeleting(true);
    try {
      await api.delete(`/chat/conversations/${id}`);
      removeConversation(id);
      if (currentConvId === id) router.push('/chat');
      toast('对话已删除', 'success');
    } catch { toast('删除失败', 'error'); }
    finally { setDeleting(false); }
  };

  return (
    <>
      <button onClick={() => setMobileOpen(true)}
        className="fixed top-2 left-2 z-30 p-2 rounded-lg shadow md:hidden border-none cursor-pointer"
        style={{ background: 'var(--c-surface)', color: 'var(--c-text-secondary)' }} aria-label="菜单">
        <Menu className="w-5 h-5" />
      </button>
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden" onClick={closeMobile}
          style={{ background: 'rgba(15,23,42,.35)', backdropFilter: 'blur(2px)' }} />
      )}

      <div
        className="flex flex-col shrink-0 h-screen transition-all duration-200"
        style={{
          width: sidebarCollapsed && !mobileOpen ? 0 : 280,
          minWidth: sidebarCollapsed && !mobileOpen ? 0 : 280,
          overflow: 'hidden',
          background: 'rgba(255,255,255,.95)',
          backdropFilter: 'blur(8px)',
          borderRight: '1px solid var(--c-border)',
          boxShadow: 'var(--shadow-sm)',
          position: mobileOpen ? 'fixed' : undefined,
          left: 0, top: 0, zIndex: 50,
        }}>
        {/* Brand + New chat */}
        <div className="flex items-center justify-between px-4 py-3 shrink-0">
          <div className="flex items-center gap-2">
            <button onClick={() => { setCurrentConvId(null); nav('/chat'); }}
              className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 border-none cursor-pointer transition-all shrink-0" title="新对话">
              <Plus className="w-5 h-5" />
            </button>
            <span className="text-sm font-semibold" style={{ color: 'var(--c-text)', letterSpacing: '-.2px' }}>KnowFlow</span>
          </div>
          <button onClick={toggleSidebar}
            className="p-1 rounded hover:bg-gray-100 transition-colors max-md:hidden border-none cursor-pointer"
            style={{ color: 'var(--c-text-tertiary)' }} title="收起侧边栏">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button onClick={closeMobile}
            className="p-1 rounded hover:bg-gray-100 transition-colors md:hidden border-none cursor-pointer"
            style={{ color: 'var(--c-text-tertiary)' }} title="关闭">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Search */}
        <div className="px-3 pb-2 shrink-0">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ width: 14, height: 14, color: 'var(--c-text-tertiary)' }} />
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="搜索对话..."
              className="w-full text-sm rounded-lg pl-8 pr-3 py-2 border outline-none transition-all"
              style={{ borderColor: 'var(--c-border)', color: 'var(--c-text)', background: 'var(--c-bg)' }}
              onFocus={e => { e.target.style.borderColor = 'var(--c-primary)'; e.target.style.boxShadow = '0 0 0 2px rgba(37,99,235,.1)'; }}
              onBlur={e => { e.target.style.borderColor = 'var(--c-border)'; e.target.style.boxShadow = 'none'; }} />
          </div>
        </div>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto px-2 space-y-0.5">
          {filtered.length === 0 && search ? (
            <p className="text-xs text-center py-8" style={{ color: 'var(--c-text-tertiary)' }}>未找到匹配的对话</p>
          ) : filtered.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-xs" style={{ color: 'var(--c-text-tertiary)' }}>暂无对话</p>
              <button onClick={() => { setCurrentConvId(null); nav('/chat'); }}
                className="text-xs mt-2 border-none cursor-pointer" style={{ color: 'var(--c-primary)', background: 'none' }}>
                开始新对话
              </button>
            </div>
          ) : filtered.map(conv => (
            <div key={conv.id} className="group relative rounded-lg text-sm"
              style={{ background: currentConvId === conv.id ? 'var(--c-primary-subtle)' : 'transparent' }}>
              <button onClick={() => { setCurrentConvId(conv.id); router.push(`/chat/${conv.id}`); closeMobile(); }}
                className="w-full text-left px-3 py-2.5 truncate border-none cursor-pointer rounded-lg transition-colors"
                style={{
                  color: currentConvId === conv.id ? 'var(--c-primary)' : 'var(--c-text-secondary)',
                  fontWeight: currentConvId === conv.id ? 500 : 400,
                  background: 'transparent',
                }}>
                {conv.title || '新对话'}
              </button>
              <div className="absolute right-1.5 top-1/2 -translate-y-1/2 hidden group-hover:flex gap-0.5">
                <button onClick={e => { e.stopPropagation(); setConfirmTarget(conv.id); }} disabled={deleting}
                  className="p-1 rounded border-none cursor-pointer transition-colors disabled:opacity-50"
                  style={{ color: 'var(--c-text-tertiary)', background: 'none' }} title="删除">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Bottom: Nav + User */}
        <div className="shrink-0 border-t" style={{ borderColor: 'var(--c-border)' }}>
          {/* Nav icons */}
          <div className="flex px-2 py-1.5 gap-0.5">
            {navItems.map(item => {
              const active = isActive(item.path);
              return (
                <button key={item.path} onClick={() => nav(item.path)}
                  className="flex-1 flex flex-col items-center gap-0.5 py-1.5 rounded-lg border-none cursor-pointer transition-all text-xs"
                  style={{
                    color: active ? 'var(--c-primary)' : 'var(--c-text-tertiary)',
                    background: active ? 'var(--c-primary-subtle)' : 'transparent',
                    fontWeight: active ? 500 : 400,
                  }}>
                  <item.icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
          {/* User */}
          <div className="flex items-center gap-2.5 px-4 py-2.5 border-t" style={{ borderColor: 'var(--c-border)' }}>
            <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold text-white shrink-0">
              {initial}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">{user?.name || '未登录'}</div>
            </div>
            <button onClick={() => { logout(); router.push('/login'); }}
              className="p-1.5 rounded transition-colors border-none cursor-pointer"
              style={{ color: 'var(--c-text-tertiary)', background: 'none' }} title="退出">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <ConfirmDialog open={!!confirmTarget} title="删除对话"
        message="确定删除该对话？删除后不可恢复。"
        confirmText="删除" danger
        onConfirm={handleDelete}
        onCancel={() => setConfirmTarget(null)} />
    </>
  );
}
