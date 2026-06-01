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
    get: (...args: any[]) => mockGet(...args),
    post: (...args: any[]) => mockPost(...args),
    patch: (...args: any[]) => mockPatch(...args),
  },
  API_URL: 'http://localhost:8000/api/v1',
}));

vi.mock('@/components/Toast', () => ({
  toast: vi.fn(),
}));

vi.mock('lucide-react', () => ({
  Download: () => <svg />,
  ThumbsUp: () => <svg />,
  ThumbsDown: () => <svg />,
  FileText: () => <svg />,
}));

import RAGQualityPanel from '@/components/RAGQualityPanel';

const mockIssues = [
  {
    id: 'issue-1',
    knowledge_base_id: 'kb-1',
    source_type: 'feedback',
    source_id: 'msg-1',
    question: '试用期多久？',
    answer: '试用期为3个月',
    citations: [{ document_title: '员工手册', snippet: '试用期为3个月' }],
    severity: 'medium',
    status: 'open',
    reason: '回答不准确',
    created_at: '2026-06-01T10:00:00Z',
  },
  {
    id: 'issue-2',
    knowledge_base_id: null,
    source_type: 'eval_failed',
    source_id: 'run-1',
    question: '薪资结构',
    answer: null,
    citations: [],
    severity: 'high',
    status: 'resolved',
    reason: '答案不匹配',
    resolution_note: '已更新文档',
    created_at: '2026-06-01T09:00:00Z',
    resolved_at: '2026-06-01T11:00:00Z',
  },
];

describe('RAGQualityPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loading 状态', () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    const { container } = render(<RAGQualityPanel canUpdate={true} />);
    expect(container.querySelector('.skeleton')).toBeInTheDocument();
  });

  it('成功后显示 issue 列表', async () => {
    mockGet.mockResolvedValueOnce(mockIssues);
    render(<RAGQualityPanel canUpdate={true} />);
    await waitFor(() => {
      expect(screen.getByText('试用期多久？')).toBeInTheDocument();
      expect(screen.getByText('薪资结构')).toBeInTheDocument();
    });
  });

  it('空数据状态', async () => {
    mockGet.mockResolvedValueOnce([]);
    render(<RAGQualityPanel canUpdate={true} />);
    await waitFor(() => {
      expect(screen.getByText('暂无质量问题')).toBeInTheDocument();
    });
  });

  it('status/severity/source_type 显示正确', async () => {
    mockGet.mockResolvedValueOnce(mockIssues);
    render(<RAGQualityPanel canUpdate={true} />);
    await waitFor(() => {
      expect(screen.getByText('待处理')).toBeInTheDocument();
      expect(screen.getByText('已解决')).toBeInTheDocument();
      expect(screen.getByText('中')).toBeInTheDocument();
      expect(screen.getByText('高')).toBeInTheDocument();
      expect(screen.getByText('用户反馈')).toBeInTheDocument();
      expect(screen.getByText('评测失败')).toBeInTheDocument();
    });
  });

  it('过滤会调用带 query 的 API', async () => {
    mockGet.mockResolvedValue([]);
    render(<RAGQualityPanel canUpdate={true} />);

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalled();
    });

    const statusSelect = screen.getAllByRole('combobox')[0];
    fireEvent.change(statusSelect, { target: { value: 'open' } });

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith(expect.stringContaining('status=open'));
    });
  });

  it('展开 issue 显示 question/answer/reason', async () => {
    mockGet.mockResolvedValueOnce(mockIssues);
    render(<RAGQualityPanel canUpdate={true} />);
    await waitFor(() => {
      expect(screen.getByText('试用期多久？')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('试用期多久？'));

    await waitFor(() => {
      expect(screen.getByText('试用期为3个月')).toBeInTheDocument();
      expect(screen.getByText('回答不准确')).toBeInTheDocument();
    });
  });

  it('标记处理中调用 PATCH', async () => {
    mockGet.mockResolvedValueOnce(mockIssues);
    mockPatch.mockResolvedValueOnce({ ...mockIssues[0], status: 'in_progress' });
    render(<RAGQualityPanel canUpdate={true} />);

    await waitFor(() => {
      expect(screen.getByText('试用期多久？')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('试用期多久？'));

    await waitFor(() => {
      expect(screen.getByText('标记处理中')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('标记处理中'));

    await waitFor(() => {
      expect(mockPatch).toHaveBeenCalledWith('/rag-quality/issues/issue-1', { status: 'in_progress' });
    });
  });

  it('标记解决可填写 resolution_note', async () => {
    mockGet.mockResolvedValueOnce(mockIssues);
    mockPatch.mockResolvedValueOnce({ ...mockIssues[0], status: 'resolved' });
    render(<RAGQualityPanel canUpdate={true} />);

    await waitFor(() => {
      expect(screen.getByText('试用期多久？')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('试用期多久？'));

    await waitFor(() => {
      expect(screen.getByPlaceholderText('解决方案（可选）')).toBeInTheDocument();
    });
    fireEvent.change(screen.getByPlaceholderText('解决方案（可选）'), { target: { value: '已修复' } });
    fireEvent.click(screen.getByText('解决'));

    await waitFor(() => {
      expect(mockPatch).toHaveBeenCalledWith('/rag-quality/issues/issue-1', {
        status: 'resolved',
        resolution_note: '已修复',
      });
    });
  });

  it('viewer 不显示更新按钮', async () => {
    mockGet.mockResolvedValueOnce(mockIssues);
    render(<RAGQualityPanel canUpdate={false} />);

    await waitFor(() => {
      expect(screen.getByText('试用期多久？')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('试用期多久？'));

    expect(screen.queryByText('标记处理中')).not.toBeInTheDocument();
    expect(screen.queryByText('解决')).not.toBeInTheDocument();
  });

  it('API 失败显示错误', async () => {
    mockGet.mockRejectedValueOnce(new Error('加载失败'));
    render(<RAGQualityPanel canUpdate={true} />);
    await waitFor(() => {
      expect(screen.getByText('加载失败')).toBeInTheDocument();
    });
  });

  it('手动创建 issue 调用 POST', async () => {
    mockGet.mockResolvedValue([]);
    mockPost.mockResolvedValueOnce({ id: 'new-issue' });
    render(<RAGQualityPanel canUpdate={true} />);

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalled();
    });

    // 点击"手动创建"按钮（不是下拉选项）
    const createBtn = screen.getByRole('button', { name: '手动创建' });
    fireEvent.click(createBtn);
    fireEvent.change(screen.getByPlaceholderText('问题描述'), { target: { value: '手动问题' } });

    const submitBtn = screen.getByRole('button', { name: '创建' });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/rag-quality/issues', {
        source_type: 'manual',
        question: '手动问题',
        severity: 'medium',
      });
    });
  });

  it('无 citations 不崩溃', async () => {
    mockGet.mockResolvedValueOnce([mockIssues[1]]);
    render(<RAGQualityPanel canUpdate={true} />);
    await waitFor(() => {
      expect(screen.getByText('薪资结构')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('薪资结构'));
    // 不应崩溃
    await waitFor(() => {
      expect(screen.getByText('答案不匹配')).toBeInTheDocument();
    });
  });
});
