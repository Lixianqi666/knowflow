'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useStore } from '@/lib/store';
import { api } from '@/lib/api';
import { toast } from '@/components/Toast';
import {
  User,
  Stats,
  DocPerm,
  DocItem,
  Template,
  AuditLogItem,
  AgentItem,
  KnowledgeBaseOption,
  TAB_LABELS,
  TabKey,
} from './types';
import UsersTab from './UsersTab';
import PermissionsTab from './PermissionsTab';
import TemplatesTab from './TemplatesTab';
import AgentsTab from './AgentsTab';
import AuditTab from './AuditTab';
import StatsTab from './StatsTab';

export default function AdminPage() {
  const router = useRouter();
  const { token, user, adminUsers, setAdminUsers, adminStats, setAdminStats } = useStore();
  const [tab, setTab] = useState<TabKey>('users');
  const [users, setUsers] = useState<User[]>(adminUsers);
  const [stats, setStats] = useState<Stats | null>(adminStats);
  const [loading, setLoading] = useState(!adminUsers.length);
  const [error, setError] = useState('');

  // 权限 tab
  const [docs, setDocs] = useState<DocItem[]>([]);
  const [docPerms, setDocPerms] = useState<Record<string, DocPerm[]>>({});
  const [searchingDocId, setSearchingDocId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<User[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const searchRef = useRef<HTMLDivElement>(null);

  // 场景模板 tab
  const [templates, setTemplates] = useState<Template[]>([]);
  const [templateForm, setTemplateForm] = useState<{
    id?: string;
    name: string;
    description: string;
    context_prompt: string;
    no_context_prompt: string;
    top_k: number;
    threshold: number;
    rerank_top_k: number;
  } | null>(null);
  const [savingTemplate, setSavingTemplate] = useState(false);

  // 审计 tab
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditFilter, setAuditFilter] = useState('');

  // Agent tab
  const [agentItems, setAgentItems] = useState<AgentItem[]>([]);
  const [agentForm, setAgentForm] = useState<{
    id?: string;
    name: string;
    description: string;
    system_prompt: string;
    knowledge_base_ids: string[];
    top_k: number;
    threshold: number;
    rerank_top_k: number;
  } | null>(null);
  const [savingAgent, setSavingAgent] = useState(false);
  const [kbOptions, setKbOptions] = useState<KnowledgeBaseOption[]>([]);

  // ---- 数据加载 ----

  const loadTemplates = async () => {
    try {
      const ts = await api.get<Template[]>('/admin/prompt-templates');
      setTemplates(ts);
    } catch (e) {
      console.error('加载场景模板失败:', e);
    }
  };

  const loadAuditLogs = async () => {
    setAuditLoading(true);
    try {
      const logs = await api.get<AuditLogItem[]>('/audit/logs?limit=200');
      setAuditLogs(logs);
    } catch (e) {
      console.error('加载审计日志失败:', e);
    }
    setAuditLoading(false);
  };

  const loadAgentItems = async () => {
    try {
      const items = await api.get<AgentItem[]>('/agents/admin-list');
      setAgentItems(items);
    } catch (e) {
      console.error('加载 Agent 列表失败:', e);
    }
  };

  const loadKbOptions = async () => {
    try {
      const kbs = await api.get<KnowledgeBaseOption[]>('/knowledge-bases');
      setKbOptions(kbs);
    } catch (e) {
      console.error('加载知识库列表失败:', e);
    }
  };

  const loadData = async () => {
    if (useStore.getState().adminUsers.length && useStore.getState().adminStats) return;
    setLoading(true);
    setError('');
    try {
      const [u, s] = await Promise.all([
        api.get<User[]>('/admin/users'),
        api.get<Stats>('/admin/stats'),
      ]);
      setUsers(u);
      setStats(s);
      setAdminUsers(u);
      setAdminStats(s);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const loadDocs = async () => {
    try {
      const d = await api.get<DocItem[]>('/admin/documents');
      setDocs(d);
      const permsMap: Record<string, DocPerm[]> = {};
      await Promise.all(
        d.map(async (doc) => {
          try {
            permsMap[doc.id] = await api.get<DocPerm[]>(`/admin/documents/${doc.id}/permissions`);
          } catch {
            permsMap[doc.id] = [];
          }
        }),
      );
      setDocPerms(permsMap);
    } catch (e: any) {
      toast(e.message, 'error');
    }
  };

  // ---- effects ----

  useEffect(() => {
    if (!token) return;
    if (useStore.getState().user?.role !== 'admin') {
      router.replace('/chat');
      return;
    }
    loadData();
  }, [token]);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setSearchingDocId(null);
        setSearchQuery('');
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  useEffect(() => {
    if (tab === 'permissions') loadDocs();
    if (tab === 'templates') loadTemplates();
    if (tab === 'agents') {
      loadAgentItems();
      loadKbOptions();
    }
    if (tab === 'audit') loadAuditLogs();
  }, [tab]);

  // ---- UsersTab handlers ----

  const handleRoleToggle = async (u: User) => {
    const newRole = u.role === 'admin' ? 'member' : 'admin';
    try {
      await api.put(`/admin/users/${u.id}`, { role: newRole });
      setUsers((prev) => prev.map((x) => (x.id === u.id ? { ...x, role: newRole } : x)));
      toast(`已将 ${u.name} 设为${newRole === 'admin' ? '管理员' : '成员'}`, 'success');
    } catch (e: any) {
      toast(e.message, 'error');
    }
  };

  const handleActiveToggle = async (u: User) => {
    try {
      await api.put(`/admin/users/${u.id}`, { is_active: !u.is_active });
      setUsers((prev) => prev.map((x) => (x.id === u.id ? { ...x, is_active: !x.is_active } : x)));
      toast(u.is_active ? `已禁用 ${u.name}` : `已启用 ${u.name}`, 'success');
    } catch (e: any) {
      toast(e.message, 'error');
    }
  };

  // ---- PermissionsTab handlers ----

  const handleSearch = useCallback((docId: string, query: string) => {
    setSearchQuery(query);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }
    setSearchLoading(true);
    searchTimer.current = setTimeout(async () => {
      try {
        const all = await api.get<User[]>('/admin/users');
        const q = query.toLowerCase();
        const filtered = all.filter(
          (u) => u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q),
        );
        setSearchResults(filtered);
      } catch {
        setSearchResults([]);
      } finally {
        setSearchLoading(false);
      }
    }, 300);
  }, []);

  const handleGrant = async (docId: string, userId: string) => {
    try {
      await api.post(`/admin/documents/${docId}/permissions`, { user_id: userId });
      toast('授权成功', 'success');
      setSearchingDocId(null);
      setSearchQuery('');
      const perms = await api.get<DocPerm[]>(`/admin/documents/${docId}/permissions`);
      setDocPerms((prev) => ({ ...prev, [docId]: perms }));
    } catch (e: any) {
      toast(e.message, 'error');
    }
  };

  const handleRevoke = async (docId: string, userId: string) => {
    try {
      await api.delete(`/admin/documents/${docId}/permissions/${userId}`);
      toast('已撤销权限', 'success');
      setDocPerms((prev) => ({
        ...prev,
        [docId]: (prev[docId] || []).filter((p) => p.user_id !== userId),
      }));
    } catch (e: any) {
      toast(e.message, 'error');
    }
  };

  // ---- TemplatesTab handlers ----

  const handleOpenTemplateEdit = async (t: Template) => {
    try {
      const detail = await api.get<Template>(`/prompt-templates/${t.id}`);
      setTemplateForm({
        id: t.id,
        name: detail.name,
        description: detail.description,
        context_prompt: detail.context_prompt,
        no_context_prompt: detail.no_context_prompt,
        top_k: detail.top_k,
        threshold: detail.threshold,
        rerank_top_k: detail.rerank_top_k,
      });
    } catch (e) {
      console.error('加载模板详情失败:', e);
    }
  };

  const handleToggleTemplateActive = async (t: Template) => {
    try {
      await api.patch(`/prompt-templates/${t.id}`, { is_active: !t.is_active });
      loadTemplates();
      toast(t.is_active ? '已停用' : '已启用', 'success');
    } catch (e: any) {
      toast(e.message, 'error');
    }
  };

  const handleSaveTemplate = async () => {
    if (!templateForm?.name.trim()) {
      toast('请输入场景名称', 'error');
      return;
    }
    setSavingTemplate(true);
    try {
      if (templateForm.id) {
        await api.patch(`/prompt-templates/${templateForm.id}`, templateForm);
      } else {
        await api.post('/prompt-templates/', templateForm);
      }
      loadTemplates();
      setTemplateForm(null);
      toast('保存成功', 'success');
    } catch (e: any) {
      toast(e.message, 'error');
    } finally {
      setSavingTemplate(false);
    }
  };

  // ---- AgentsTab handlers ----

  const handleOpenAgentEdit = async (a: AgentItem) => {
    try {
      const detail = await api.get<AgentItem>(`/agents/${a.id}`);
      setAgentForm({
        id: a.id,
        name: detail.name,
        description: detail.description,
        system_prompt: detail.system_prompt,
        knowledge_base_ids: detail.knowledge_base_ids || [],
        top_k: detail.top_k,
        threshold: detail.threshold,
        rerank_top_k: detail.rerank_top_k,
      });
    } catch (e) {
      console.error('加载 Agent 详情失败:', e);
    }
  };

  const handleToggleAgentActive = async (a: AgentItem) => {
    try {
      await api.patch(`/agents/${a.id}`, { is_active: !a.is_active });
      loadAgentItems();
    } catch (e: any) {
      toast(e.message, 'error');
    }
  };

  const handleSaveAgent = async () => {
    if (!agentForm?.name.trim()) {
      toast('请输入 Agent 名称', 'error');
      return;
    }
    setSavingAgent(true);
    try {
      if (agentForm.id) {
        await api.patch(`/agents/${agentForm.id}`, agentForm);
      } else {
        await api.post('/agents/', agentForm);
      }
      loadAgentItems();
      setAgentForm(null);
      toast('保存成功', 'success');
    } catch (e: any) {
      toast(e.message, 'error');
    } finally {
      setSavingAgent(false);
    }
  };

  // ---- 渲染 ----

  const tabs: TabKey[] = ['users', 'permissions', 'templates', 'agents', 'audit', 'stats'];

  return (
    <div className="h-full p-4 md:p-8 pt-14 md:pt-8 overflow-y-auto">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-xl md:text-2xl font-bold mb-6">管理后台</h1>

        {/* Tab 栏 - 移动端紧凑可滚动 */}
        <div className="flex gap-0.5 mb-6 border-b overflow-x-auto scrollbar-hide">
          {tabs.map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`whitespace-nowrap px-3 md:px-4 py-2 text-xs md:text-sm font-medium border-b-2 -mb-px transition-colors shrink-0 ${
                tab === t
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {TAB_LABELS[t]}
            </button>
          ))}
        </div>

        {error && (
          <div className="mb-4 px-4 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
            {error}
          </div>
        )}

        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className="bg-white rounded-xl border p-4 flex items-center gap-2 md:gap-4"
              >
                <div className="skeleton h-4 w-20" />
                <div className="skeleton h-4 w-40" />
                <div className="skeleton h-5 w-14 rounded-full" />
                <div className="skeleton h-3 w-3 rounded-full" />
                <div className="flex-1" />
                <div className="skeleton h-4 w-16" />
              </div>
            ))}
          </div>
        ) : tab === 'users' ? (
          <UsersTab
            users={users}
            currentUserId={user?.id}
            onRoleToggle={handleRoleToggle}
            onActiveToggle={handleActiveToggle}
          />
        ) : tab === 'permissions' ? (
          <PermissionsTab
            docs={docs}
            docPerms={docPerms}
            searchingDocId={searchingDocId}
            searchQuery={searchQuery}
            searchResults={searchResults}
            searchLoading={searchLoading}
            onSetSearchingDocId={setSearchingDocId}
            onSearch={handleSearch}
            onGrant={handleGrant}
            onRevoke={handleRevoke}
            searchRef={searchRef}
          />
        ) : tab === 'templates' ? (
          <TemplatesTab
            templates={templates}
            templateForm={templateForm}
            savingTemplate={savingTemplate}
            onSetTemplateForm={setTemplateForm}
            onOpenEditForm={handleOpenTemplateEdit}
            onToggleActive={handleToggleTemplateActive}
            onSave={handleSaveTemplate}
          />
        ) : tab === 'agents' ? (
          <AgentsTab
            agentItems={agentItems}
            agentForm={agentForm}
            savingAgent={savingAgent}
            kbOptions={kbOptions}
            onSetAgentForm={setAgentForm}
            onOpenEditForm={handleOpenAgentEdit}
            onToggleActive={handleToggleAgentActive}
            onSave={handleSaveAgent}
          />
        ) : tab === 'audit' ? (
          <AuditTab
            auditLogs={auditLogs}
            auditLoading={auditLoading}
            auditFilter={auditFilter}
            onSetAuditFilter={setAuditFilter}
            onRefresh={loadAuditLogs}
          />
        ) : (
          stats && <StatsTab stats={stats} />
        )}
      </div>
    </div>
  );
}
