export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  is_active: boolean;
  is_admin?: boolean;
  disabled_reason?: string | null;
  disabled_at?: string | null;
  failed_login_count?: number;
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
  context_prompt: string;
  no_context_prompt: string;
  is_active: boolean;
  top_k: number;
  threshold: number;
  rerank_top_k: number;
}

export interface AuditLogItem {
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
  delete_doc: '删除文档',
  admin_update_user: '修改用户',
  admin_grant_permission: '授予权限',
  admin_revoke_permission: '撤销权限',
  'admin.update_user': '修改用户',
  'admin.health.view': '查看健康状态',
  'document.upload': '上传文档',
  'document.delete': '删除文档',
  'document.retry_index': '重试索引',
  'document.preview': '预览文档',
  'chat.feedback': '对话反馈',
  'rag_eval.run': '运行评测',
  'rag_quality.issue_create': '创建质量问题',
  'rag_quality.issue_update': '更新质量问题',
  'rag_quality.issue_resolve': '解决质量问题',
  'knowledge_base.create': '创建知识库',
  'knowledge_base.delete': '删除知识库',
  'knowledge_base.member_add': '添加成员',
  'knowledge_base.member_remove': '移除成员',
  'agent.publish': '发布 Agent',
  'agent.debug': '调试 Agent',
  'auth.login.success': '登录成功',
  'auth.login.failed': '登录失败',
  'user.disable': '禁用用户',
  'user.enable': '启用用户',
};

export const TAB_LABELS: Record<string, string> = {
  users: '用户',
  permissions: '权限',
  templates: '场景',
  agents: 'Agent',
  audit: '审计',
  stats: '统计',
  eval: '评测',
  health: '健康',
  rag_debug: 'RAG 调试',
  rag_quality: 'RAG 质量',
};

export type TabKey = 'users' | 'stats' | 'permissions' | 'templates' | 'agents' | 'audit' | 'eval' | 'health' | 'rag_debug' | 'rag_quality';
