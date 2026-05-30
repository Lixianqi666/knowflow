import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

// jsdom 不支持 scrollIntoView
beforeAll(() => {
  HTMLElement.prototype.scrollIntoView = vi.fn();
});

// ---- Mocks ----

let capturedOnSend: ((msg: string) => void) | null = null;

vi.mock('@/components/InputBox', () => ({
  default: ({ onSend }: { onSend: (msg: string) => void }) => {
    capturedOnSend = onSend;
    return <div data-testid="input-box" />;
  },
}));

vi.mock('@/components/MessageBubble', () => ({
  default: () => <div data-testid="message-bubble" />,
}));

vi.mock('@/components/SourceViewer', () => ({
  default: () => <div data-testid="source-viewer" />,
}));

vi.mock('lucide-react', () => ({
  MessageSquare: () => <svg />,
  Target: (p: any) => <svg data-testid="target-icon" {...p} />,
  ChevronDown: () => <svg />,
  ChevronUp: () => <svg />,
}));

const mockPost = vi.fn();
const mockGet = vi.fn();
const mockStreamChat = vi.fn();
const mockPatch = vi.fn();

vi.mock('@/lib/api', () => ({
  api: {
    post: (...a: any[]) => mockPost(...a),
    get: (...a: any[]) => mockGet(...a),
    streamChat: (...a: any[]) => mockStreamChat(...a),
    patch: (...a: any[]) => mockPatch(...a),
  },
  API_URL: 'http://localhost:8000/api/v1',
}));

// Store state that tests can mutate
let storeState: any = {};
const mockSetConversations = vi.fn((updater: any) => {
  if (typeof updater === 'function') {
    storeState.conversations = updater(storeState.conversations);
  } else {
    storeState.conversations = updater;
  }
});

vi.mock('@/lib/store', () => ({
  useStore: (selector: any) => {
    const state = {
      messages: [],
      addMessage: vi.fn(),
      updateLastAssistant: vi.fn(),
      streaming: false,
      setStreaming: vi.fn(),
      currentConvId: storeState.currentConvId ?? null,
      setCurrentConvId: vi.fn((id: string) => { storeState.currentConvId = id; }),
      setConversations: mockSetConversations,
      conversations: storeState.conversations ?? [],
      sources: [],
      setSources: vi.fn(),
      chatError: null,
      setChatError: vi.fn(),
      loadingMessages: false,
      setLoadingMessages: vi.fn(),
      setMessages: vi.fn(),
      setCachedMessages: vi.fn(),
      messagesCache: {},
      activeSource: null,
      setActiveSource: vi.fn(),
    };
    return selector ? selector(state) : state;
  },
}));

import ChatWindow from '@/components/ChatWindow';

function makeStream(chunks: string[]) {
  const encoder = new TextEncoder();
  let i = 0;
  return {
    getReader() {
      return {
        async read() {
          if (i >= chunks.length) return { done: true, value: undefined };
          const val = encoder.encode(chunks[i]);
          i++;
          return { done: false, value: val };
        },
      };
    },
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  capturedOnSend = null;
  storeState = { currentConvId: null, conversations: [] };
  mockGet.mockResolvedValue([]);
});

describe('ChatWindow goal 真实行为', () => {
  it('无 currentConvId 时，设置目标后发送首条消息，api.post body 包含 goal', async () => {
    mockPost.mockResolvedValueOnce({ id: 'new-conv' });
    mockStreamChat.mockReturnValueOnce(makeStream(['data: {"type":"done"}\n']));
    mockGet.mockResolvedValue([]);

    render(<ChatWindow />);

    // 点击"设置对话目标"
    fireEvent.click(screen.getByText('设置对话目标'));
    const input = screen.getByPlaceholderText(/输入对话目标/);
    fireEvent.change(input, { target: { value: '制定营销方案' } });
    fireEvent.click(screen.getByText('保存'));

    // 触发发送
    await waitFor(() => expect(capturedOnSend).not.toBeNull());
    capturedOnSend!('帮我制定方案');

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/chat/conversations', {
        title: '帮我制定方案',
        goal: '制定营销方案',
      });
    });
  });

  it('无 currentConvId 时，streamChat 第 5 个参数携带 pendingGoal', async () => {
    mockPost.mockResolvedValueOnce({ id: 'new-conv' });
    mockStreamChat.mockReturnValueOnce(makeStream(['data: {"type":"done"}\n']));
    mockGet.mockResolvedValue([]);

    render(<ChatWindow />);

    fireEvent.click(screen.getByText('设置对话目标'));
    fireEvent.change(screen.getByPlaceholderText(/输入对话目标/), { target: { value: '测试目标' } });
    fireEvent.click(screen.getByText('保存'));

    await waitFor(() => expect(capturedOnSend).not.toBeNull());
    capturedOnSend!('开始');

    await waitFor(() => {
      expect(mockStreamChat).toHaveBeenCalledWith(
        'new-conv', '开始', expect.anything(), undefined, '测试目标',
      );
    });
  });

  it('创建 conversation 成功后 pendingGoal 不再显示', async () => {
    mockPost.mockResolvedValueOnce({ id: 'new-conv' });
    mockStreamChat.mockReturnValueOnce(makeStream(['data: {"type":"done"}\n']));
    mockGet.mockResolvedValue([{ id: 'new-conv', title: '开始', goal: null, goal_status: 'active', missing_info: [] }]);

    render(<ChatWindow />);

    // 设置目标
    fireEvent.click(screen.getByText('设置对话目标'));
    fireEvent.change(screen.getByPlaceholderText(/输入对话目标/), { target: { value: '临时目标' } });
    fireEvent.click(screen.getByText('保存'));

    // 确认目标已显示
    expect(screen.getByText('临时目标')).toBeInTheDocument();

    // 发送
    await waitFor(() => expect(capturedOnSend).not.toBeNull());
    capturedOnSend!('开始');

    // 等待创建完成，pendingGoal 被清空，conversations 刷新
    await waitFor(() => {
      expect(screen.queryByText('临时目标')).not.toBeInTheDocument();
    });
  });

  it('有 currentConvId 且 conversation.goal=null 时，不显示 pendingGoal，streamChat 第 5 参数 undefined', async () => {
    storeState.currentConvId = 'existing-conv';
    storeState.conversations = [
      { id: 'existing-conv', title: '已有', goal: null, goal_status: 'active', missing_info: [], is_pinned: false, pinned_at: null, goal_summary: null, created_at: '', updated_at: '' },
    ];
    mockGet.mockResolvedValue([]);
    mockStreamChat.mockReturnValueOnce(makeStream(['data: {"type":"done"}\n']));

    render(<ChatWindow />);

    await waitFor(() => expect(capturedOnSend).not.toBeNull());
    capturedOnSend!('继续');

    await waitFor(() => {
      expect(mockStreamChat).toHaveBeenCalledWith(
        'existing-conv', '继续', expect.anything(), undefined, undefined,
      );
    });
  });

  it('有 currentConvId 且 conversation.goal 有值时，streamChat 使用 conversation.goal', async () => {
    storeState.currentConvId = 'conv-with-goal';
    storeState.conversations = [
      { id: 'conv-with-goal', title: '目标对话', goal: '真实目标', goal_status: 'active', missing_info: [], is_pinned: false, pinned_at: null, goal_summary: null, created_at: '', updated_at: '' },
    ];
    mockGet.mockResolvedValue([]);
    mockStreamChat.mockReturnValueOnce(makeStream(['data: {"type":"done"}\n']));

    render(<ChatWindow />);

    await waitFor(() => expect(capturedOnSend).not.toBeNull());
    capturedOnSend!('推进');

    await waitFor(() => {
      expect(mockStreamChat).toHaveBeenCalledWith(
        'conv-with-goal', '推进', expect.anything(), undefined, '真实目标',
      );
    });
  });
});
