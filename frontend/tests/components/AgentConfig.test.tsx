import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

beforeAll(() => {
  HTMLElement.prototype.scrollIntoView = vi.fn();
});

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();

vi.mock('@/lib/api', () => ({
  api: {
    get: (...a: any[]) => mockGet(...a),
    post: (...a: any[]) => mockPost(...a),
    patch: (...a: any[]) => mockPatch(...a),
  },
  API_URL: 'http://localhost:8000/api/v1',
}));

vi.mock('@/components/Toast', () => ({
  toast: vi.fn(),
}));

vi.mock('lucide-react', () => ({
  Settings: () => <svg />,
  Play: () => <svg />,
  Upload: () => <svg />,
  RotateCcw: () => <svg />,
  RefreshCw: () => <svg />,
}));

import AgentConfig from '@/components/AgentConfig';

const mockConfig = {
  draft_config: {
    system_prompt: '你是测试助手',
    knowledge_base_ids: [],
    temperature: 0.2,
    max_tokens: 1000,
    tools: [],
  },
  published_config: {},
  status: 'draft',
  published_version: 0,
  last_published_at: null,
  has_unpublished_changes: false,
};

const mockPublishedConfig = {
  ...mockConfig,
  status: 'published',
  published_version: 1,
  last_published_at: '2026-05-31T10:00:00Z',
  published_config: {
    system_prompt: '你是测试助手',
    temperature: 0.2,
    max_tokens: 1000,
  },
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('AgentConfig', () => {
  it('loading 状态', () => {
    mockGet.mockReturnValueOnce(new Promise(() => {}));
    render(<AgentConfig agentId="agent-1" />);
    expect(screen.getByText('加载中...')).toBeInTheDocument();
  });

  it('成功后显示 system_prompt / temperature / max_tokens', async () => {
    mockGet.mockResolvedValueOnce(mockConfig);
    render(<AgentConfig agentId="agent-1" />);
    await waitFor(() => {
      expect(screen.getByDisplayValue('你是测试助手')).toBeInTheDocument();
      expect(screen.getByDisplayValue('0.2')).toBeInTheDocument();
      expect(screen.getByDisplayValue('1000')).toBeInTheDocument();
    });
  });

  it('保存草稿会调用 PATCH config', async () => {
    mockGet.mockResolvedValueOnce(mockConfig);
    mockPatch.mockResolvedValueOnce(mockConfig);
    render(<AgentConfig agentId="agent-1" />);
    await waitFor(() => {
      expect(screen.getByText('保存草稿')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('保存草稿'));
    await waitFor(() => {
      expect(mockPatch).toHaveBeenCalledWith(
        '/agents/agent-1/config',
        expect.objectContaining({ system_prompt: '你是测试助手' }),
      );
    });
  });

  it('发布按钮调用 publish API', async () => {
    mockGet.mockResolvedValueOnce(mockConfig);
    mockPost.mockResolvedValueOnce(mockPublishedConfig);
    render(<AgentConfig agentId="agent-1" />);
    await waitFor(() => {
      expect(screen.getByText('发布')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('发布'));
    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/agents/agent-1/publish');
    });
  });

  it('回滚按钮调用 rollback API', async () => {
    mockGet.mockResolvedValueOnce(mockPublishedConfig);
    mockPost.mockResolvedValueOnce(mockConfig);
    render(<AgentConfig agentId="agent-1" />);
    await waitFor(() => {
      expect(screen.getByText('回滚')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('回滚'));
    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/agents/agent-1/rollback');
    });
  });

  it('has_unpublished_changes 显示未发布变更提示', async () => {
    mockGet.mockResolvedValueOnce({
      ...mockPublishedConfig,
      has_unpublished_changes: true,
    });
    render(<AgentConfig agentId="agent-1" />);
    await waitFor(() => {
      expect(screen.getByText('有未发布变更')).toBeInTheDocument();
    });
  });

  it('调试按钮会调用 debug API', async () => {
    mockGet.mockResolvedValueOnce(mockConfig);
    mockPost.mockResolvedValueOnce({
      answer: '调试回答',
      citations: [],
      used_config: {},
    });
    render(<AgentConfig agentId="agent-1" />);
    await waitFor(() => {
      expect(screen.getByPlaceholderText('输入测试问题...')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText('输入测试问题...'), {
      target: { value: '测试问题' },
    });
    // 点击调试按钮（不是标题）
    const debugButtons = screen.getAllByText(/调试/);
    const button = debugButtons.find((el) => el.tagName === 'BUTTON');
    if (button) fireEvent.click(button);

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/agents/agent-1/debug', { content: '测试问题' });
    });
  });

  it('调试中按钮 disabled', async () => {
    mockGet.mockResolvedValueOnce(mockConfig);
    mockPost.mockReturnValueOnce(new Promise(() => {}));
    render(<AgentConfig agentId="agent-1" />);
    await waitFor(() => {
      fireEvent.change(screen.getByPlaceholderText('输入测试问题...'), {
        target: { value: '测试' },
      });
      const debugButtons = screen.getAllByText(/调试/);
      const button = debugButtons.find((el) => el.tagName === 'BUTTON');
      if (button) fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getByText('调试中...')).toBeInTheDocument();
    });
  });

  it('调试结果显示 answer', async () => {
    mockGet.mockResolvedValueOnce(mockConfig);
    mockPost.mockResolvedValueOnce({
      answer: '这是调试回答',
      citations: [],
      used_config: {},
    });
    render(<AgentConfig agentId="agent-1" />);
    await waitFor(() => {
      fireEvent.change(screen.getByPlaceholderText('输入测试问题...'), {
        target: { value: '测试' },
      });
      const debugButtons = screen.getAllByText(/调试/);
      const button = debugButtons.find((el) => el.tagName === 'BUTTON');
      if (button) fireEvent.click(button);
    });

    await waitFor(() => {
      expect(screen.getByText('这是调试回答')).toBeInTheDocument();
    });
  });

  it('403 时显示无权限', async () => {
    mockGet.mockRejectedValueOnce(new Error('无权查看该 Agent 配置'));
    render(<AgentConfig agentId="agent-1" />);
    await waitFor(() => {
      expect(screen.getByText('加载失败')).toBeInTheDocument();
    });
  });

  it('旧 Agent config 为空时页面不崩溃', async () => {
    mockGet.mockResolvedValueOnce({
      draft_config: {
        system_prompt: '',
        knowledge_base_ids: [],
        temperature: 0.2,
        max_tokens: 1000,
        tools: [],
      },
      published_config: {},
      status: 'draft',
      published_version: 0,
      last_published_at: null,
      has_unpublished_changes: false,
    });
    render(<AgentConfig agentId="agent-1" />);
    await waitFor(() => {
      expect(screen.getByText('保存草稿')).toBeInTheDocument();
    });
  });
});
