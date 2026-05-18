'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useStore } from '@/lib/store';
import { api } from '@/lib/api';
import { toast } from '@/components/Toast';

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface Stats {
  users: number;
  documents: number;
  conversations: number;
  chunks: number;
  knowledge_bases: number;
  messages: number;
  hit_rate: number;
  praise: number;
  criticism: number;
  today_conversations: number;
}

interface DocPerm {
  user_id: string;
  name: string;
  email: string;
  permission: string;
}

interface DocItem {
  id: string;
  title: string;
  status: string;
  created_at: string;
}

interface Template {
  id: string;
  name: string;
  description: string;
  is_active: boolean;
  top_k: number;
  threshold: number;
}

interface AuditLogItem {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  detail: string | null;
  ip: string | null;
  created_at: string;
}

interface AgentItem {
  id: string;
  name: string;
  description: string;
  system_prompt: string;
  knowledge_base_ids: string[];
  top_k: number;
  threshold: number;
  rerank_top_k: number;
  is_active: boolean;
  created_at: string;
}

interface KnowledgeBaseOption {
  id: string;
  name: string;
}

const ACTION_LABELS: Record<string, string> = {
  send_message: '发送消息',
  view_doc: '查看文档',
  download_file: '下载文件',
  admin_update_user: '修改用户',
  admin_grant_permission: '授予权限',
  admin_revoke_permission: '撤销权限',
  delete_doc: '删除文档',
};

export default function AdminPage() {
  const router = useRouter();
  const { token, user, adminUsers, setAdminUsers, adminStats, setAdminStats } = useStore();
  const [tab, setTab] = useState<
    'users' | 'stats' | 'permissions' | 'templates' | 'agents' | 'audit'
  >('users');
  const [users, setUsers] = useState<User[]>(adminUsers);
  const [stats, setStats] = useState<Stats | null>(adminStats);
  const [loading, setLoading] = useState(!adminUsers.length);
  const [error, setError] = useState('');

  const [docs, setDocs] = useState<DocItem[]>([]);
  const [docPerms, setDocPerms] = useState<Record<string, DocPerm[]>>({});
  const [searchingDocId, setSearchingDocId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<User[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const searchRef = useRef<HTMLDivElement>(null);

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

  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditFilter, setAuditFilter] = useState('');

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

  const loadTemplates = async () => {
    try {
      const ts = await api.get<Template[]>('/admin/prompt-templates');
      setTemplates(ts);
    } catch {}
  };

  const loadAuditLogs = async () => {
    setAuditLoading(true);
    try {
      const logs = await api.get<AuditLogItem[]>('/audit/logs?limit=200');
      setAuditLogs(logs);
    } catch {}
    setAuditLoading(false);
  };

  const loadAgentItems = async () => {
    try {
      const items = await api.get<AgentItem[]>('/agents/admin-list');
      setAgentItems(items);
    } catch {}
  };

  const loadKbOptions = async () => {
    try {
      const kbs = await api.get<KnowledgeBaseOption[]>('/knowledge-bases');
      setKbOptions(kbs);
    } catch {}
  };

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

  const loadData = async () => {
    // store 已有数据时直接使用，不重新请求
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

  useEffect(() => {
    if (tab === 'permissions') loadDocs();
    if (tab === 'templates') loadTemplates();
    if (tab === 'agents') {
      loadAgentItems();
      loadKbOptions();
    }
    if (tab === 'audit') loadAuditLogs();
  }, [tab]);

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

  return (
    <div className="h-full p-4 md:p-8 pt-14 md:pt-8 overflow-y-auto">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-xl md:text-2xl font-bold mb-6">管理后台</h1>

        <div className="flex gap-1 mb-6 border-b overflow-x-auto">
          {(['users', 'permissions', 'templates', 'agents', 'audit', 'stats'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`whitespace-nowrap px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                tab === t
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {t === 'users'
                ? '用户管理'
                : t === 'permissions'
                  ? '权限管理'
                  : t === 'templates'
                    ? '场景管理'
                    : t === 'agents'
                      ? 'Agent 应用'
                      : t === 'audit'
                        ? '审计日志'
                        : '数据统计'}
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
          <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-gray-600">
                <tr>
                  <th className="text-left px-4 py-3 font-medium">用户</th>
                  <th className="text-left px-4 py-3 font-medium">邮箱</th>
                  <th className="text-center px-4 py-3 font-medium">角色</th>
                  <th className="text-center px-4 py-3 font-medium">状态</th>
                  <th className="text-center px-4 py-3 font-medium">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium">{u.name}</td>
                    <td className="px-4 py-3 text-gray-500">{u.email}</td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                          u.role === 'admin'
                            ? 'bg-purple-100 text-purple-700'
                            : 'bg-gray-100 text-gray-600'
                        }`}
                      >
                        {u.role === 'admin' ? '管理员' : '成员'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span
                        className={`inline-block w-2 h-2 rounded-full ${
                          u.is_active ? 'bg-green-500' : 'bg-red-400'
                        }`}
                      />
                    </td>
                    <td className="px-4 py-3 text-center space-x-2">
                      {u.id !== user?.id && (
                        <button
                          onClick={() => handleRoleToggle(u)}
                          className="text-xs text-blue-600 hover:underline"
                        >
                          {u.role === 'admin' ? '设为成员' : '设为管理员'}
                        </button>
                      )}
                      {u.id !== user?.id && (
                        <button
                          onClick={() => handleActiveToggle(u)}
                          className={`text-xs hover:underline ${
                            u.is_active ? 'text-red-500' : 'text-green-600'
                          }`}
                        >
                          {u.is_active ? '禁用' : '启用'}
                        </button>
                      )}
                      {u.id === user?.id && <span className="text-xs text-gray-400">当前用户</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {users.length === 0 && <div className="py-12 text-center text-gray-400">暂无用户</div>}
          </div>
        ) : tab === 'permissions' ? (
          <div className="space-y-3">
            {docs.length === 0 ? (
              <div className="py-12 text-center text-gray-400 text-sm">暂无文档</div>
            ) : (
              docs.map((doc) => {
                const perms = docPerms[doc.id] || [];
                const isSearching = searchingDocId === doc.id;
                return (
                  <div key={doc.id} className="bg-white rounded-xl shadow-sm border p-3 md:p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-sm font-medium truncate">{doc.title}</span>
                        <span
                          className={`text-xs px-1.5 py-0.5 rounded ${
                            doc.status === 'indexed'
                              ? 'bg-green-100 text-green-700'
                              : 'bg-yellow-100 text-yellow-700'
                          }`}
                        >
                          {doc.status === 'indexed' ? '已索引' : doc.status}
                        </span>
                      </div>
                      <div className="relative shrink-0" ref={isSearching ? searchRef : undefined}>
                        <button
                          onClick={() => {
                            setSearchingDocId(isSearching ? null : doc.id);
                            setSearchQuery('');
                            setSearchResults([]);
                          }}
                          className="text-xs px-3 py-1.5 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100"
                        >
                          授予权限
                        </button>
                        {isSearching && (
                          <div className="absolute right-0 top-full mt-1 w-72 bg-white border rounded-xl shadow-lg z-10">
                            <input
                              autoFocus
                              type="text"
                              placeholder="搜索用户名或邮箱..."
                              value={searchQuery}
                              onChange={(e) => handleSearch(doc.id, e.target.value)}
                              className="w-full px-3 py-2 text-sm border-b rounded-t-xl input-base"
                            />
                            <div className="max-h-48 overflow-y-auto">
                              {searchLoading ? (
                                <div className="px-3 py-4 text-center text-gray-400 text-xs">
                                  搜索中...
                                </div>
                              ) : searchResults.length === 0 ? (
                                <div className="px-3 py-4 text-center text-gray-400 text-xs">
                                  {searchQuery ? '无匹配结果' : '输入关键词搜索'}
                                </div>
                              ) : (
                                searchResults.map((u) => {
                                  const hasPerm = perms.some((p) => p.user_id === u.id);
                                  return (
                                    <button
                                      key={u.id}
                                      disabled={hasPerm}
                                      onClick={() => handleGrant(doc.id, u.id)}
                                      className={`w-full px-3 py-2 text-left text-sm flex items-center justify-between hover:bg-gray-50 ${
                                        hasPerm ? 'opacity-50 cursor-not-allowed' : ''
                                      }`}
                                    >
                                      <div>
                                        <span className="font-medium">{u.name}</span>
                                        <span className="text-gray-400 ml-2 text-xs">
                                          {u.email}
                                        </span>
                                      </div>
                                      {hasPerm && (
                                        <span className="text-xs text-gray-400">已有权限</span>
                                      )}
                                    </button>
                                  );
                                })
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                    {perms.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5">
                        {perms.map((p) => (
                          <span
                            key={p.user_id}
                            className="inline-flex items-center gap-1 text-xs bg-gray-50 border border-gray-200 text-gray-600 rounded px-2 py-1"
                          >
                            <span>{p.name}</span>
                            <span className="text-gray-400">{p.email}</span>
                            <button
                              onClick={() => handleRevoke(doc.id, p.user_id)}
                              className="ml-1 text-gray-400 hover:text-red-500"
                              title="撤销权限"
                            >
                              ✕
                            </button>
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-gray-400">无授权用户</p>
                    )}
                  </div>
                );
              })
            )}
          </div>
        ) : tab === 'templates' ? (
          <div>
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-gray-500">配置不同问答场景的 prompt 风格和检索参数</p>
              <button
                onClick={() =>
                  setTemplateForm({
                    name: '',
                    description: '',
                    context_prompt: '',
                    no_context_prompt: '',
                    top_k: 5,
                    threshold: 30,
                    rerank_top_k: 3,
                  })
                }
                className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                新建场景
              </button>
            </div>
            <div className="space-y-2">
              {templates.length === 0 ? (
                <div className="py-12 text-center text-gray-400 text-sm">
                  暂无场景模板，点击上方按钮创建
                </div>
              ) : (
                templates.map((t) => (
                  <div key={t.id} className="bg-white rounded-xl shadow-sm border p-4">
                    <div className="flex items-center justify-between">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm">{t.name}</span>
                          <span
                            className={`text-xs px-1.5 py-0.5 rounded ${t.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}
                          >
                            {t.is_active ? '启用' : '停用'}
                          </span>
                        </div>
                        {t.description && (
                          <p className="text-xs text-gray-400 mt-0.5">{t.description}</p>
                        )}
                        <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                          <span>top_k={t.top_k}</span>
                          <span>阈值={t.threshold}%</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          onClick={async () => {
                            try {
                              const detail = await api.get<any>(`/prompt-templates/${t.id}`);
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
                            } catch {}
                          }}
                          className="text-xs text-blue-600 hover:underline"
                        >
                          编辑
                        </button>
                        <button
                          onClick={async () => {
                            try {
                              await api.patch(`/prompt-templates/${t.id}`, {
                                is_active: !t.is_active,
                              });
                              loadTemplates();
                              toast(t.is_active ? '已停用' : '已启用', 'success');
                            } catch (e: any) {
                              toast(e.message, 'error');
                            }
                          }}
                          className="text-xs text-gray-500 hover:text-blue-600"
                        >
                          {t.is_active ? '停用' : '启用'}
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
            {templateForm && (
              <div
                className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
                onClick={() => setTemplateForm(null)}
              >
                <div
                  className="bg-white rounded-xl w-full max-w-2xl max-h-[85vh] flex flex-col mx-4"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="flex items-center justify-between p-4 border-b shrink-0">
                    <h3 className="font-semibold">{templateForm.name ? '编辑场景' : '新建场景'}</h3>
                    <button
                      onClick={() => setTemplateForm(null)}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      ✕
                    </button>
                  </div>
                  <div className="p-4 overflow-y-auto flex-1 space-y-3">
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block">名称</label>
                      <input
                        value={templateForm.name}
                        onChange={(e) => setTemplateForm({ ...templateForm, name: e.target.value })}
                        className="w-full text-sm border rounded-lg px-3 py-2 input-base"
                        placeholder="如：HR场景、技术问答"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block">描述</label>
                      <input
                        value={templateForm.description}
                        onChange={(e) =>
                          setTemplateForm({ ...templateForm, description: e.target.value })
                        }
                        className="w-full text-sm border rounded-lg px-3 py-2 input-base"
                        placeholder="简短描述该场景的用途"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block">
                        有上下文时的系统提示
                      </label>
                      <textarea
                        value={templateForm.context_prompt}
                        onChange={(e) =>
                          setTemplateForm({ ...templateForm, context_prompt: e.target.value })
                        }
                        className="w-full text-sm border rounded-lg px-3 py-2 h-24 input-base font-mono"
                        placeholder="检索到相关文档时使用的 prompt，告知 AI 如何回答"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block">
                        无上下文时的系统提示
                      </label>
                      <textarea
                        value={templateForm.no_context_prompt}
                        onChange={(e) =>
                          setTemplateForm({ ...templateForm, no_context_prompt: e.target.value })
                        }
                        className="w-full text-sm border rounded-lg px-3 py-2 h-24 input-base font-mono"
                        placeholder="未检索到相关文档时使用的 prompt"
                      />
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="text-xs text-gray-500 mb-1 block">检索数量 (top_k)</label>
                        <input
                          type="number"
                          value={templateForm.top_k}
                          onChange={(e) =>
                            setTemplateForm({ ...templateForm, top_k: +e.target.value })
                          }
                          className="w-full text-sm border rounded-lg px-3 py-2 input-base"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 mb-1 block">相似度阈值 (%)</label>
                        <input
                          type="number"
                          value={templateForm.threshold}
                          onChange={(e) =>
                            setTemplateForm({ ...templateForm, threshold: +e.target.value })
                          }
                          className="w-full text-sm border rounded-lg px-3 py-2 input-base"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 mb-1 block">重排数量</label>
                        <input
                          type="number"
                          value={templateForm.rerank_top_k}
                          onChange={(e) =>
                            setTemplateForm({ ...templateForm, rerank_top_k: +e.target.value })
                          }
                          className="w-full text-sm border rounded-lg px-3 py-2 input-base"
                        />
                      </div>
                    </div>
                  </div>
                  <div className="p-4 border-t flex justify-end gap-2">
                    <button
                      onClick={() => setTemplateForm(null)}
                      className="px-4 py-2 text-sm text-gray-600 border rounded-lg hover:bg-gray-50"
                    >
                      取消
                    </button>
                    <button
                      onClick={async () => {
                        if (!templateForm.name.trim()) {
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
                      }}
                      disabled={savingTemplate}
                      className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                    >
                      {savingTemplate ? '保存中...' : '保存'}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : tab === 'agents' ? (
          <div>
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-gray-500">
                创建和管理 AI Agent，每个 Agent 可关联知识库并独立对话
              </p>
              <button
                onClick={() =>
                  setAgentForm({
                    name: '',
                    description: '',
                    system_prompt: '',
                    knowledge_base_ids: [],
                    top_k: 5,
                    threshold: 30,
                    rerank_top_k: 3,
                  })
                }
                className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                新建 Agent
              </button>
            </div>
            <div className="space-y-2">
              {agentItems.length === 0 ? (
                <div className="py-12 text-center text-gray-400 text-sm">
                  暂无 Agent，点击上方按钮创建
                </div>
              ) : (
                agentItems.map((a) => (
                  <div key={a.id} className="bg-white rounded-xl shadow-sm border p-4">
                    <div className="flex items-center justify-between">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm">{a.name}</span>
                          <span
                            className={`text-xs px-1.5 py-0.5 rounded ${a.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}
                          >
                            {a.is_active ? '启用' : '停用'}
                          </span>
                        </div>
                        {a.description && (
                          <p className="text-xs text-gray-400 mt-0.5">{a.description}</p>
                        )}
                        <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                          <span>top_k={a.top_k}</span>
                          <span>阈值={a.threshold}%</span>
                          <span>知识库 {a.knowledge_base_ids?.length || 0} 个</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          onClick={async () => {
                            try {
                              const detail = await api.get<any>(`/agents/${a.id}`);
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
                            } catch {}
                          }}
                          className="text-xs text-blue-600 hover:underline"
                        >
                          编辑
                        </button>
                        <button
                          onClick={async () => {
                            try {
                              await api.patch(`/agents/${a.id}`, { is_active: !a.is_active });
                              loadAgentItems();
                            } catch (e: any) {
                              toast(e.message, 'error');
                            }
                          }}
                          className="text-xs text-gray-500 hover:text-blue-600"
                        >
                          {a.is_active ? '停用' : '启用'}
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
            {agentForm && (
              <div
                className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
                onClick={() => setAgentForm(null)}
              >
                <div
                  className="bg-white rounded-xl w-full max-w-2xl max-h-[85vh] flex flex-col mx-4"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="flex items-center justify-between p-4 border-b shrink-0">
                    <h3 className="font-semibold">{agentForm.id ? '编辑 Agent' : '新建 Agent'}</h3>
                    <button
                      onClick={() => setAgentForm(null)}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      ✕
                    </button>
                  </div>
                  <div className="p-4 overflow-y-auto flex-1 space-y-3">
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block">名称</label>
                      <input
                        value={agentForm.name}
                        onChange={(e) => setAgentForm({ ...agentForm, name: e.target.value })}
                        className="w-full text-sm border rounded-lg px-3 py-2 input-base"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block">描述</label>
                      <input
                        value={agentForm.description}
                        onChange={(e) =>
                          setAgentForm({ ...agentForm, description: e.target.value })
                        }
                        className="w-full text-sm border rounded-lg px-3 py-2 input-base"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block">系统提示词</label>
                      <textarea
                        value={agentForm.system_prompt}
                        onChange={(e) =>
                          setAgentForm({ ...agentForm, system_prompt: e.target.value })
                        }
                        className="w-full text-sm border rounded-lg px-3 py-2 h-24 input-base font-mono"
                        placeholder="Agent 的系统提示词，定义 AI 的行为和回答风格"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-gray-500 mb-1 block">关联知识库</label>
                      <div className="flex flex-wrap gap-2">
                        {kbOptions.map((kb) => {
                          const selected = agentForm.knowledge_base_ids.includes(kb.id);
                          return (
                            <button
                              key={kb.id}
                              onClick={() => {
                                const ids = selected
                                  ? agentForm.knowledge_base_ids.filter((id) => id !== kb.id)
                                  : [...agentForm.knowledge_base_ids, kb.id];
                                setAgentForm({ ...agentForm, knowledge_base_ids: ids });
                              }}
                              className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                                selected
                                  ? 'bg-blue-100 border-blue-300 text-blue-700'
                                  : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100'
                              }`}
                            >
                              {kb.name}
                            </button>
                          );
                        })}
                        {kbOptions.length === 0 && (
                          <span className="text-xs text-gray-400">暂无知识库</span>
                        )}
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-3">
                      <div>
                        <label className="text-xs text-gray-500 mb-1 block">检索数量 (top_k)</label>
                        <input
                          type="number"
                          value={agentForm.top_k}
                          onChange={(e) => setAgentForm({ ...agentForm, top_k: +e.target.value })}
                          className="w-full text-sm border rounded-lg px-3 py-2 input-base"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 mb-1 block">相似度阈值 (%)</label>
                        <input
                          type="number"
                          value={agentForm.threshold}
                          onChange={(e) =>
                            setAgentForm({ ...agentForm, threshold: +e.target.value })
                          }
                          className="w-full text-sm border rounded-lg px-3 py-2 input-base"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 mb-1 block">重排数量</label>
                        <input
                          type="number"
                          value={agentForm.rerank_top_k}
                          onChange={(e) =>
                            setAgentForm({ ...agentForm, rerank_top_k: +e.target.value })
                          }
                          className="w-full text-sm border rounded-lg px-3 py-2 input-base"
                        />
                      </div>
                    </div>
                  </div>
                  <div className="p-4 border-t flex justify-end gap-2">
                    <button
                      onClick={() => setAgentForm(null)}
                      className="px-4 py-2 text-sm text-gray-600 border rounded-lg hover:bg-gray-50"
                    >
                      取消
                    </button>
                    <button
                      onClick={async () => {
                        if (!agentForm.name.trim()) {
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
                      }}
                      disabled={savingAgent}
                      className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                    >
                      {savingAgent ? '保存中...' : '保存'}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        ) : tab === 'audit' ? (
          <div>
            <div className="flex items-center gap-2 mb-4">
              <input
                value={auditFilter}
                onChange={(e) => setAuditFilter(e.target.value)}
                placeholder="筛选操作类型 (send_message/view_doc/download_file/...)"
                className="flex-1 text-sm border rounded-lg px-3 py-1.5 input-base"
              />
              <button onClick={loadAuditLogs} className="text-xs text-blue-600 hover:underline">
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
                      log.resource_type.includes(auditFilter),
                  )
                  .map((log) => (
                    <div key={log.id} className="bg-white rounded-xl border p-4">
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">
                            {ACTION_LABELS[log.action] || log.action}
                          </span>
                          <span className="text-xs text-gray-400">{log.resource_type}</span>
                          {log.ip && <span className="text-xs text-gray-300">{log.ip}</span>}
                        </div>
                        <span className="text-xs text-gray-400">
                          {new Date(log.created_at).toLocaleString()}
                        </span>
                      </div>
                      {log.detail && <p className="text-sm text-gray-600">{log.detail}</p>}
                      {log.resource_id && (
                        <p className="text-xs text-gray-400 mt-0.5">资源ID: {log.resource_id}</p>
                      )}
                    </div>
                  ))}
              </div>
            )}
          </div>
        ) : (
          stats && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
                {[
                  { label: '用户', value: stats.users },
                  { label: '知识库', value: stats.knowledge_bases },
                  { label: '文档', value: stats.documents },
                  { label: '分块', value: stats.chunks },
                  { label: '对话', value: stats.conversations },
                  { label: '消息', value: stats.messages },
                  { label: '今日对话', value: stats.today_conversations },
                  { label: '检索命中率', value: `${stats.hit_rate}%` },
                ].map((item) => (
                  <div key={item.label} className="bg-white rounded-xl shadow-sm border p-4 md:p-6">
                    <div className="text-xs md:text-sm text-gray-500 mb-1">{item.label}</div>
                    <div className="text-xl md:text-3xl font-bold text-gray-900">
                      {item.value.toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
              <div className="bg-white rounded-xl shadow-sm border p-4 md:p-6">
                <div className="text-sm text-gray-500 mb-3">用户反馈</div>
                <div className="flex items-center gap-6">
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">👍</span>
                    <span className="text-xl font-bold text-green-600">{stats.praise}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">👎</span>
                    <span className="text-xl font-bold text-red-500">{stats.criticism}</span>
                  </div>
                  <div className="text-sm text-gray-400">
                    {stats.praise + stats.criticism > 0
                      ? `满意度 ${((stats.praise / (stats.praise + stats.criticism)) * 100).toFixed(1)}%`
                      : '暂无反馈'}
                  </div>
                </div>
              </div>
            </div>
          )
        )}
      </div>
    </div>
  );
}
