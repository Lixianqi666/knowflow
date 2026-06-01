import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

beforeAll(() => {
  HTMLElement.prototype.scrollIntoView = vi.fn();
});

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockDelete = vi.fn();

vi.mock('@/lib/api', () => ({
  api: {
    get: (...a: any[]) => mockGet(...a),
    post: (...a: any[]) => mockPost(...a),
    delete: (...a: any[]) => mockDelete(...a),
  },
  API_URL: 'http://localhost:8000/api/v1',
}));

vi.mock('@/components/Toast', () => ({
  toast: vi.fn(),
}));

vi.mock('lucide-react', () => ({
  Play: () => <svg data-testid="play-icon" />,
  Trash2: () => <svg data-testid="trash-icon" />,
  Plus: () => <svg data-testid="plus-icon" />,
  RefreshCw: () => <svg data-testid="refresh-icon" />,
}));

import EvalTab from '@/components/EvalTab';

const mockCases = [
  {
    id: 'case-1',
    question: '公司的考勤制度是什么？',
    expected_answer: '工作时间',
    expected_citation_doc_ids: ['doc-001'],
    tags: ['hr'],
    created_at: '2026-05-31T10:00:00Z',
  },
];

beforeEach(() => {
  vi.clearAllMocks();
  mockGet.mockResolvedValue([]);
});

describe('EvalTab', () => {
  it('渲染 eval cases 列表', async () => {
    mockGet.mockResolvedValueOnce(mockCases);
    render(<EvalTab />);
    await waitFor(() => {
      expect(screen.getByText('公司的考勤制度是什么？')).toBeInTheDocument();
    });
  });

  it('显示新增按钮', async () => {
    mockGet.mockResolvedValueOnce([]);
    render(<EvalTab />);
    await waitFor(() => {
      expect(screen.getByText('新增')).toBeInTheDocument();
    });
  });

  it('点击新增显示表单', async () => {
    mockGet.mockResolvedValueOnce([]);
    render(<EvalTab />);
    await waitFor(() => {
      expect(screen.getByText('新增')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('新增'));
    expect(screen.getByPlaceholderText('评测问题')).toBeInTheDocument();
  });

  it('创建 eval case 调用 API', async () => {
    mockGet.mockResolvedValueOnce([]);
    mockPost.mockResolvedValueOnce({ id: 'new', question: '新问题' });
    mockGet.mockResolvedValueOnce([{ id: 'new', question: '新问题', tags: [], created_at: '2026-05-31T10:00:00Z' }]);

    render(<EvalTab />);
    await waitFor(() => {
      fireEvent.click(screen.getByText('新增'));
    });

    fireEvent.change(screen.getByPlaceholderText('评测问题'), { target: { value: '新问题' } });
    fireEvent.click(screen.getByText('创建'));

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/rag-evals/cases', expect.objectContaining({ question: '新问题' }));
    });
  });

  it('无评测用例时显示空状态', async () => {
    mockGet.mockResolvedValueOnce([]);
    render(<EvalTab />);
    await waitFor(() => {
      expect(screen.getByText('暂无评测用例')).toBeInTheDocument();
    });
  });
});
