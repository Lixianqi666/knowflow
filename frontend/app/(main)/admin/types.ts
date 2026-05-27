export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface Stats {
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

export interface DocPerm {
  user_id: string;
  name: string;
  email: string;
  permission: string;
}

export interface DocItem {
  id: string;
  title: string;
  status: string;
  created_at: string;
}

export interface Template {
  id: string;
  name: string;
  description: string;
  is_active: boolean;
  top_k: number;
  threshold: number;
}

export interface AuditLogItem {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string | null;
  detail: string | null;
  ip: string | null;
  created_at: string;
}

export interface AgentItem {
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

export interface KnowledgeBaseOption {
  id: string;
  name: string;
}

export const ACTION_LABELS: Record<string, string> = {
  send_message: '发送消息',
  view_doc: '查看文档',
  download_file: '下载文件',
  admin_update_user: '修改用户',
  admin_grant_permission: '授予权限',
  admin_revoke_permission: '撤销权限',
  delete_doc: '删除文档',
};

export const TAB_LABELS: Record<string, string> = {
  users: '用户',
  permissions: '权限',
  templates: '场景',
  agents: 'Agent',
  audit: '审计',
  stats: '统计',
};

export type TabKey = 'users' | 'stats' | 'permissions' | 'templates' | 'agents' | 'audit';
