import { create } from 'zustand';

interface Message {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: any[];
  rating?: number | null;
}

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

interface Agent {
  id: string;
  name: string;
  description: string;
  is_active: boolean;
  knowledge_base_ids?: string[];
  top_k?: number;
  threshold?: number;
}

interface AgentSessionItem {
  id: string;
  agent_id: string;
  title: string;
  created_at: string;
}

interface Store {
  token: string | null;
  user: any | null;
  _hydrated: boolean;
  hydrate: () => void;
  setAuth: (token: string, user: any) => void;
  logout: () => void;

  conversations: Conversation[];
  setConversations: (convs: Conversation[]) => void;
  removeConversation: (id: string) => void;
  currentConvId: string | null;
  setCurrentConvId: (id: string | null) => void;

  messages: Message[];
  addMessage: (msg: Message) => void;
  updateLastAssistant: (content: string) => void;
  setMessages: (msgs: Message[]) => void;

  sources: any[];
  setSources: (s: any[]) => void;

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
    set({ token, user, _hydrated: true });
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
      chatError: null,
    });
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
}));
