import { create } from 'zustand';

export interface Source {
  document_id: string;
  chunk_id: string;
  title: string;
  content: string;
  score?: number;
}

export interface User {
  id: string;
  name: string;
  role: 'admin' | 'member';
  is_active: boolean;
}

export interface Message {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  rating?: number | null;
}

export interface Conversation {
  id: string;
  title: string;
  is_pinned: boolean;
  pinned_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Agent {
  id: string;
  name: string;
  description: string;
  is_active: boolean;
  knowledge_base_ids?: string[];
  top_k?: number;
  threshold?: number;
  rerank_top_k?: number;
}

export interface AgentSessionItem {
  id: string;
  agent_id: string;
  title: string;
  created_at: string;
}

export type Theme = 'light' | 'dark' | 'system';

interface Store {
  token: string | null;
  user: User | null;
  _hydrated: boolean;
  hydrate: () => void;
  setAuth: (token: string, user: User) => void;
  logout: () => void;

  // 主题
  theme: Theme;
  resolvedTheme: 'light' | 'dark';
  setTheme: (theme: Theme) => void;

  conversations: Conversation[];
  setConversations: (convs: Conversation[]) => void;
  removeConversation: (id: string) => void;
  currentConvId: string | null;
  setCurrentConvId: (id: string | null) => void;

  messages: Message[];
  messagesCache: Record<string, Message[]>; // 按对话ID缓存消息
  addMessage: (msg: Message) => void;
  updateLastAssistant: (content: string) => void;
  setMessages: (msgs: Message[]) => void;
  setCachedMessages: (convId: string, msgs: Message[]) => void;

  sources: Source[];
  setSources: (s: Source[]) => void;

  streaming: boolean;
  setStreaming: (v: boolean) => void;

  chatError: string | null;
  setChatError: (e: string | null) => void;
  loadingMessages: boolean;
  setLoadingMessages: (v: boolean) => void;

  sidebarCollapsed: boolean;
  toggleSidebar: () => void;

  activeSource: { documentId: string; chunkId: string } | null;
  setActiveSource: (source: { documentId: string; chunkId: string } | null) => void;

  // Agent 状态
  agents: Agent[];
  setAgents: (agents: Agent[]) => void;
  agentSessions: AgentSessionItem[];
  setAgentSessions: (sessions: AgentSessionItem[]) => void;
  currentAgentId: string | null;
  setCurrentAgentId: (id: string | null) => void;
  currentAgentSessionId: string | null;
  setCurrentAgentSessionId: (id: string | null) => void;
  agentMessages: Message[];
  setAgentMessages: (msgs: Message[]) => void;
  addAgentMessage: (msg: Message) => void;
  updateLastAgentMessage: (content: string) => void;
  agentStreaming: boolean;
  setAgentStreaming: (v: boolean) => void;

  // 管理后台
  adminUsers: {
    id: string;
    email: string;
    name: string;
    role: string;
    is_active: boolean;
    created_at: string;
  }[];
  setAdminUsers: (users: Store['adminUsers']) => void;
  adminStats: {
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
  } | null;
  setAdminStats: (stats: Store['adminStats']) => void;

  // 知识库
  kbs: { id: string; name: string; description: string }[];
  setKbs: (
    kbs:
      | { id: string; name: string; description: string }[]
      | ((
          prev: { id: string; name: string; description: string }[],
        ) => { id: string; name: string; description: string }[]),
  ) => void;
}

function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? value : [];
}

export const useStore = create<Store>((set, get) => ({
  token: null,
  user: null,
  _hydrated: false,
  hydrate: () => {
    if (get()._hydrated) return;
    const token = localStorage.getItem('token');
    let user = null;
    try {
      user = JSON.parse(localStorage.getItem('user') || 'null');
    } catch {
      localStorage.removeItem('user');
    }
    // 初始化主题
    const savedTheme = (localStorage.getItem('theme') as Theme) || 'system';
    const resolved =
      savedTheme === 'system'
        ? window.matchMedia('(prefers-color-scheme: dark)').matches
          ? 'dark'
          : 'light'
        : savedTheme;
    document.documentElement.setAttribute('data-theme', resolved);
    set({ token, user, _hydrated: true, theme: savedTheme, resolvedTheme: resolved });
  },
  setAuth: (token, user) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(user));
    set({ token, user });
  },
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    set({
      token: null,
      user: null,
      conversations: [],
      currentConvId: null,
      messages: [],
      messagesCache: {},
      chatError: null,
      adminUsers: [],
      adminStats: null,
      kbs: [],
    });
  },

  // 主题
  theme: 'system',
  resolvedTheme: 'light',
  setTheme: (theme: Theme) => {
    localStorage.setItem('theme', theme);
    const resolved =
      theme === 'system'
        ? window.matchMedia('(prefers-color-scheme: dark)').matches
          ? 'dark'
          : 'light'
        : theme;
    document.documentElement.setAttribute('data-theme', resolved);
    set({ theme, resolvedTheme: resolved });
  },

  conversations: [],
  setConversations: (conversations) => set({ conversations: asArray<Conversation>(conversations) }),
  removeConversation: (id) =>
    set((s) => ({
      conversations: asArray<Conversation>(s.conversations).filter((c) => c.id !== id),
      currentConvId: s.currentConvId === id ? null : s.currentConvId,
    })),
  currentConvId: null,
  setCurrentConvId: (currentConvId) => set({ currentConvId }),

  messages: [],
  messagesCache: {},
  addMessage: (msg) => set((s) => ({ messages: [...asArray<Message>(s.messages), msg] })),
  updateLastAssistant: (content) =>
    set((s) => {
      const msgs = [...asArray<Message>(s.messages)];
      const last = msgs[msgs.length - 1];
      if (last && last.role === 'assistant') {
        msgs[msgs.length - 1] = { ...last, content: last.content + content };
      }
      return { messages: msgs };
    }),
  setMessages: (messages) => set({ messages: asArray<Message>(messages) }),
  setCachedMessages: (convId, msgs) =>
    set((s) => {
      const cache = { ...s.messagesCache, [convId]: asArray<Message>(msgs) };
      const keys = Object.keys(cache);
      // LRU：保留最近 50 个对话的消息缓存
      if (keys.length > 50) {
        const oldest = keys[0];
        delete cache[oldest];
      }
      return { messagesCache: cache };
    }),

  sources: [],
  setSources: (sources) => set({ sources: asArray(sources) }),

  streaming: false,
  setStreaming: (streaming) => set({ streaming }),

  chatError: null,
  setChatError: (chatError) => set({ chatError }),
  loadingMessages: false,
  setLoadingMessages: (loadingMessages) => set({ loadingMessages }),

  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

  activeSource: null,
  setActiveSource: (activeSource) => set({ activeSource }),

  agents: [],
  setAgents: (agents) => set({ agents: asArray<Agent>(agents) }),
  agentSessions: [],
  setAgentSessions: (agentSessions) =>
    set({ agentSessions: asArray<AgentSessionItem>(agentSessions) }),
  currentAgentId: null,
  setCurrentAgentId: (currentAgentId) => set({ currentAgentId }),
  currentAgentSessionId: null,
  setCurrentAgentSessionId: (currentAgentSessionId) => set({ currentAgentSessionId }),
  agentMessages: [],
  setAgentMessages: (agentMessages) => set({ agentMessages: asArray<Message>(agentMessages) }),
  addAgentMessage: (msg) =>
    set((s) => ({ agentMessages: [...asArray<Message>(s.agentMessages), msg] })),
  updateLastAgentMessage: (content) =>
    set((s) => {
      const msgs = [...asArray<Message>(s.agentMessages)];
      const last = msgs[msgs.length - 1];
      if (last && last.role === 'assistant') {
        msgs[msgs.length - 1] = { ...last, content: last.content + content };
      }
      return { agentMessages: msgs };
    }),
  agentStreaming: false,
  setAgentStreaming: (agentStreaming) => set({ agentStreaming }),

  adminUsers: [],
  setAdminUsers: (adminUsers) => set({ adminUsers: Array.isArray(adminUsers) ? adminUsers : [] }),
  adminStats: null,
  setAdminStats: (adminStats) => set({ adminStats }),

  kbs: [],
  setKbs: (kbs) =>
    set((s) => ({
      kbs: typeof kbs === 'function' ? kbs(s.kbs) : Array.isArray(kbs) ? kbs : [],
    })),
}));
