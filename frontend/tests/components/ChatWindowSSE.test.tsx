import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

beforeAll(() => {
  HTMLElement.prototype.scrollIntoView = vi.fn();
});

let capturedOnSend: ((msg: string) => void) | null = null;
let capturedOnStop: (() => void) | null = null;

vi.mock('@/components/InputBox', () => ({
  default: (props: any) => {
    capturedOnSend = props.onSend;
    capturedOnStop = props.onStop;
    return (
      <div>
        <span data-testid="streaming">{String(props.streaming)}</span>
        {props.streaming && (
          <button data-testid="stop-btn" onClick={props.onStop}>停止</button>
        )}
      </div>
    );
  },
}));

vi.mock('@/components/MessageBubble', () => ({ default: () => <div /> }));
vi.mock('@/components/SourceViewer', () => ({ default: () => <div /> }));
vi.mock('@/components/GoalBar', () => ({ default: () => <div /> }));

vi.mock('lucide-react', () => ({
  MessageSquare: () => <svg />,
  Target: () => <svg />,
  ChevronDown: () => <svg />,
  ChevronUp: () => <svg />,
}));

const mockStreamChat = vi.fn();
const mockPost = vi.fn();
const mockGet = vi.fn();
const mockSetChatError = vi.fn();
const mockSetStreaming = vi.fn();
const mockResetLastAssistant = vi.fn();
const mockUpdateLastAssistant = vi.fn();

vi.mock('@/lib/api', () => ({
  api: {
    post: (...a: any[]) => mockPost(...a),
    get: (...a: any[]) => mockGet(...a),
    streamChat: (...a: any[]) => mockStreamChat(...a),
    patch: vi.fn(),
  },
  API_URL: 'http://localhost:8000/api/v1',
}));

let streamingState = false;

vi.mock('@/lib/store', () => ({
  useStore: (selector: any) => {
    const state = {
      messages: [],
      addMessage: vi.fn(),
      updateLastAssistant: mockUpdateLastAssistant,
      resetLastAssistant: mockResetLastAssistant,
      streaming: streamingState,
      setStreaming: mockSetStreaming,
      currentConvId: 'existing-conv',
      setCurrentConvId: vi.fn(),
      setConversations: vi.fn(),
      conversations: [{ id: 'existing-conv', title: 't', goal: null, goal_status: 'active', missing_info: [], is_pinned: false, pinned_at: null, goal_summary: null, created_at: '', updated_at: '' }],
      sources: [],
      setSources: vi.fn(),
      chatError: null,
      setChatError: mockSetChatError,
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

function makeFailingStream(error: Error) {
  return {
    getReader() {
      return {
        async read() {
          throw error;
        },
      };
    },
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  streamingState = false;
  mockGet.mockResolvedValue([]);
});

describe('ChatWindow SSE 重试', () => {
  it('流正常完成（收到 done）时不重试', async () => {
    mockStreamChat.mockReturnValueOnce(
      makeStream([
        'data: {"type":"token","data":"你好"}\n',
        'data: {"type":"done"}\n',
      ]),
    );

    render(<ChatWindow />);
    await waitFor(() => expect(capturedOnSend).not.toBeNull());
    capturedOnSend!('测试');

    await waitFor(() => {
      expect(mockStreamChat).toHaveBeenCalledTimes(1);
    });
    const errorCalls = mockSetChatError.mock.calls.filter((c: any) => c[0] !== null);
    expect(errorCalls).toHaveLength(0);
  });

  it('流中断后重试成功，不显示最终错误', async () => {
    mockStreamChat
      .mockImplementationOnce(() => makeFailingStream(new Error('网络断开')))
      .mockImplementationOnce(() => makeStream(['data: {"type":"done"}\n']));

    render(<ChatWindow />);
    await waitFor(() => expect(capturedOnSend).not.toBeNull());
    capturedOnSend!('测试');

    await waitFor(() => {
      expect(mockStreamChat).toHaveBeenCalledTimes(2);
    }, { timeout: 5000 });

    // 成功后不应有"回答中断"错误
    const interruptCalls = mockSetChatError.mock.calls.filter(
      (c: any) => typeof c[0] === 'string' && c[0].includes('回答中断'),
    );
    expect(interruptCalls).toHaveLength(0);
  });

  it('stream 正常 close 但没有 done，触发重试', async () => {
    // 第一次：正常 token 但没有 done 就 close 了
    // 第二次：正常 done
    mockStreamChat
      .mockImplementationOnce(() => makeStream(['data: {"type":"token","data":"部分内容"}\n']))
      .mockImplementationOnce(() => makeStream(['data: {"type":"token","data":"完整内容"}\n', 'data: {"type":"done"}\n']));

    render(<ChatWindow />);
    await waitFor(() => expect(capturedOnSend).not.toBeNull());
    capturedOnSend!('测试');

    // 应触发重试（第一次没有 done）
    await waitFor(() => {
      expect(mockStreamChat).toHaveBeenCalledTimes(2);
    }, { timeout: 5000 });
  });

  it('重试期间设置"连接中断，正在重试..."', async () => {
    mockStreamChat
      .mockImplementationOnce(() => makeFailingStream(new Error('断开')))
      .mockImplementationOnce(() => makeStream(['data: {"type":"done"}\n']));

    render(<ChatWindow />);
    await waitFor(() => expect(capturedOnSend).not.toBeNull());
    capturedOnSend!('测试');

    await waitFor(() => {
      expect(mockSetChatError).toHaveBeenCalledWith('连接中断，正在重试...');
    }, { timeout: 3000 });
  });

  it('用户停止后不显示"回答中断"错误', async () => {
    // 模拟 streamChat 调用时 controller 已被 abort
    mockStreamChat.mockImplementation(async (_c: any, _m: any, signal: AbortSignal) => {
      // 模拟 abort 触发后 stream 立即失败
      if (signal.aborted) throw new DOMException('abort', 'AbortError');
      return {
        getReader() {
          return {
            read: () => {
              if (signal.aborted) return Promise.reject(new DOMException('abort', 'AbortError'));
              return new Promise(() => {}); // hang
            },
            cancel: () => Promise.resolve(),
          };
        },
      };
    });

    const { rerender } = render(<ChatWindow />);
    await waitFor(() => expect(capturedOnSend).not.toBeNull());
    capturedOnSend!('测试');

    await waitFor(() => expect(mockStreamChat).toHaveBeenCalledTimes(1));

    // 点停止
    streamingState = true;
    rerender(<ChatWindow />);
    await waitFor(() => expect(screen.getByTestId('stop-btn')).toBeInTheDocument());
    fireEvent.click(screen.getByTestId('stop-btn'));

    await new Promise((r) => setTimeout(r, 3000));

    // 不应有"回答中断"错误
    const interruptCalls = mockSetChatError.mock.calls.filter(
      (c: any) => typeof c[0] === 'string' && c[0].includes('回答中断'),
    );
    expect(interruptCalls).toHaveLength(0);
  });

  it('3 次重试全部失败后设置最终错误', async () => {
    mockStreamChat.mockImplementation(() => makeFailingStream(new Error('持续断开')));

    render(<ChatWindow />);
    await waitFor(() => expect(capturedOnSend).not.toBeNull());
    capturedOnSend!('测试');

    await waitFor(() => {
      expect(mockSetChatError).toHaveBeenCalledWith(expect.stringContaining('回答中断'));
    }, { timeout: 15000 });

    expect(mockStreamChat.mock.calls.length).toBeGreaterThanOrEqual(4);
  }, 20000);

  it('最终失败后 setStreaming(false) 被调用', async () => {
    mockStreamChat.mockImplementation(() => makeFailingStream(new Error('断开')));

    render(<ChatWindow />);
    await waitFor(() => expect(capturedOnSend).not.toBeNull());
    capturedOnSend!('测试');

    await waitFor(() => {
      expect(mockSetStreaming).toHaveBeenCalledWith(false);
    }, { timeout: 15000 });
  }, 20000);

  it('重试前清空半截 assistant 内容', async () => {
    mockStreamChat
      .mockImplementationOnce(() => makeStream(['data: {"type":"token","data":"半截"}\n']))
      .mockImplementationOnce(() => makeStream(['data: {"type":"token","data":"完整"}\n', 'data: {"type":"done"}\n']));

    render(<ChatWindow />);
    await waitFor(() => expect(capturedOnSend).not.toBeNull());
    capturedOnSend!('测试');

    await waitFor(() => {
      expect(mockStreamChat).toHaveBeenCalledTimes(2);
    }, { timeout: 5000 });

    // 重试前 resetLastAssistant 被调用
    expect(mockResetLastAssistant).toHaveBeenCalled();
  });

  it('服务端 error 事件不触发重试，保留原始错误', async () => {
    mockStreamChat.mockReturnValueOnce(
      makeStream(['data: {"type":"error","data":"LLM API 密钥无效，请检查配置"}\n']),
    );

    render(<ChatWindow />);
    await waitFor(() => expect(capturedOnSend).not.toBeNull());
    capturedOnSend!('测试');

    await waitFor(() => {
      expect(mockStreamChat).toHaveBeenCalledTimes(1);
    });

    // 保留后端错误
    expect(mockSetChatError).toHaveBeenCalledWith('LLM API 密钥无效，请检查配置');

    // 不应有重试提示
    const retryCalls = mockSetChatError.mock.calls.filter(
      (c: any) => typeof c[0] === 'string' && c[0].includes('连接中断'),
    );
    expect(retryCalls).toHaveLength(0);

    // 不应有"回答中断"错误
    const interruptCalls = mockSetChatError.mock.calls.filter(
      (c: any) => typeof c[0] === 'string' && c[0].includes('回答中断'),
    );
    expect(interruptCalls).toHaveLength(0);
  });
});
