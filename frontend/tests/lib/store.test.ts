import { describe, it, expect, beforeEach } from 'vitest';
import { useStore } from '@/lib/store';

describe('Store', () => {
  beforeEach(() => {
    useStore.setState({
      token: null,
      user: null,
      conversations: [],
      currentConvId: null,
      messages: [],
      sources: [],
      streaming: false,
      chatError: null,
      loadingMessages: false,
      sidebarCollapsed: false,
      activeSource: null,
      agents: [],
      agentSessions: [],
      currentAgentId: null,
      currentAgentSessionId: null,
      agentMessages: [],
      agentStreaming: false,
    });
  });

  it('setAuth 设置 token 和 user', () => {
    useStore.getState().setAuth('test-token', { id: '1', name: '测试' });
    const state = useStore.getState();
    expect(state.token).toBe('test-token');
    expect(state.user).toEqual({ id: '1', name: '测试' });
  });

  it('logout 清除所有认证状态', () => {
    useStore.getState().setAuth('token', { id: '1' });
    useStore.getState().addMessage({ role: 'user', content: 'hi' });
    useStore.getState().logout();

    const state = useStore.getState();
    expect(state.token).toBeNull();
    expect(state.user).toBeNull();
    expect(state.messages).toEqual([]);
    expect(state.conversations).toEqual([]);
  });

  it('addMessage 追加消息', () => {
    useStore.getState().addMessage({ role: 'user', content: '你好' });
    useStore.getState().addMessage({ role: 'assistant', content: '嗨' });

    expect(useStore.getState().messages).toHaveLength(2);
    expect(useStore.getState().messages[0].content).toBe('你好');
  });

  it('updateLastAssistant 追加到最后一条 assistant 消息', () => {
    useStore.getState().addMessage({ role: 'user', content: '你好' });
    useStore.getState().addMessage({ role: 'assistant', content: '我' });
    useStore.getState().updateLastAssistant('是');
    useStore.getState().updateLastAssistant('AI');

    expect(useStore.getState().messages[1].content).toBe('我是AI');
  });

  it('removeConversation 删除对话并清除 currentConvId', () => {
    useStore
      .getState()
      .setConversations([{ id: '1', title: '对话1', created_at: '', updated_at: '' }]);
    useStore.getState().setCurrentConvId('1');
    useStore.getState().removeConversation('1');

    expect(useStore.getState().conversations).toHaveLength(0);
    expect(useStore.getState().currentConvId).toBeNull();
  });

  it('toggleSidebar 切换侧边栏', () => {
    expect(useStore.getState().sidebarCollapsed).toBe(false);
    useStore.getState().toggleSidebar();
    expect(useStore.getState().sidebarCollapsed).toBe(true);
    useStore.getState().toggleSidebar();
    expect(useStore.getState().sidebarCollapsed).toBe(false);
  });

  it('set sources 过滤非数组', () => {
    useStore.getState().setSources(null as any);
    expect(useStore.getState().sources).toEqual([]);
    useStore.getState().setSources([{ id: 1 }]);
    expect(useStore.getState().sources).toHaveLength(1);
  });

  it('Agent 状态管理', () => {
    useStore.getState().setAgents([{ id: 'a1', name: 'Agent1', description: '', is_active: true }]);
    useStore.getState().setCurrentAgentId('a1');
    useStore.getState().addAgentMessage({ role: 'user', content: '测试' });

    expect(useStore.getState().agents).toHaveLength(1);
    expect(useStore.getState().currentAgentId).toBe('a1');
    expect(useStore.getState().agentMessages).toHaveLength(1);
  });
});
