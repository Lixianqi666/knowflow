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
    download: vi.fn(),
  },
  API_URL: 'http://localhost:8000/api/v1',
}));

vi.mock('@/components/Toast', () => ({
  toast: vi.fn(),
}));

vi.mock('@/components/ConfirmDialog', () => ({
  default: ({ open, onConfirm, onCancel, title }: any) =>
    open ? (
      <div data-testid="confirm-dialog">
        <span>{title}</span>
        <button data-testid="confirm-btn" onClick={onConfirm}>确认</button>
        <button data-testid="cancel-btn" onClick={onCancel}>取消</button>
      </div>
    ) : null,
}));

vi.mock('lucide-react', () => ({
  FileText: () => <svg />,
  RefreshCw: () => <svg />,
  Trash2: () => <svg />,
  X: () => <svg />,
  Search: () => <svg />,
}));

import DocList from '@/components/DocList';

function makeDoc(overrides: Partial<any> = {}) {
  return {
    id: 'doc-1',
    title: '测试文档.txt',
    status: 'indexed',
    error_message: null,
    retry_count: 0,
    indexed_at: '2026-05-30T10:00:00Z',
    created_at: '2026-05-30T10:00:00Z',
    kb_id: null,
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mockGet.mockResolvedValue({ items: [] });
});

describe('DocList 状态显示', () => {
  it('显示 indexed 状态', async () => {
    mockGet.mockResolvedValueOnce({ items: [makeDoc({ status: 'indexed' })] });
    render(<DocList refreshKey={0} />);
    await waitFor(() => {
      expect(screen.getByText('已索引')).toBeInTheDocument();
    });
  });

  it('显示 failed 状态和错误提示', async () => {
    mockGet.mockResolvedValueOnce({
      items: [makeDoc({ status: 'failed', error_message: '索引超时' })],
    });
    render(<DocList refreshKey={0} />);
    await waitFor(() => {
      expect(screen.getByText('失败')).toBeInTheDocument();
      expect(screen.getByText('索引超时')).toBeInTheDocument();
    });
  });

  it('failed 文档显示重试按钮', async () => {
    mockGet.mockResolvedValueOnce({
      items: [makeDoc({ status: 'failed', error_message: '错误' })],
    });
    render(<DocList refreshKey={0} />);
    await waitFor(() => {
      expect(screen.getByText('重试')).toBeInTheDocument();
    });
  });

  it('非 failed 文档不显示重试按钮', async () => {
    mockGet.mockResolvedValueOnce({ items: [makeDoc({ status: 'indexed' })] });
    render(<DocList refreshKey={0} />);
    await waitFor(() => {
      expect(screen.getByText('已索引')).toBeInTheDocument();
    });
    expect(screen.queryByText('重试')).not.toBeInTheDocument();
  });

  it('点击重试调用 retry-index API', async () => {
    mockGet.mockResolvedValueOnce({
      items: [makeDoc({ id: 'retry-doc', status: 'failed', error_message: '错误' })],
    });
    mockPost.mockResolvedValueOnce({ id: 'retry-doc', status: 'pending', retry_count: 1 });
    mockGet.mockResolvedValueOnce({ items: [makeDoc({ id: 'retry-doc', status: 'pending', retry_count: 1 })] });

    render(<DocList refreshKey={0} />);
    await waitFor(() => {
      expect(screen.getByText('重试')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('重试'));
    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/documents/retry-doc/retry-index');
    });
  });

  it('重试中按钮 disabled', async () => {
    mockGet.mockResolvedValueOnce({
      items: [makeDoc({ id: 'retry-doc', status: 'failed', error_message: '错误' })],
    });
    // 让 API 调用挂起
    mockPost.mockReturnValueOnce(new Promise(() => {}));

    render(<DocList refreshKey={0} />);
    await waitFor(() => {
      expect(screen.getByText('重试')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('重试'));
    await waitFor(() => {
      expect(screen.getByText('重试中...')).toBeInTheDocument();
      expect(screen.getByText('重试中...')).toBeDisabled();
    });
  });

  it('无 status 或未知 status 不崩溃', async () => {
    mockGet.mockResolvedValueOnce({
      items: [makeDoc({ status: '' }), makeDoc({ id: 'doc-2', status: 'unknown_state' })],
    });
    render(<DocList refreshKey={0} />);
    await waitFor(() => {
      // 应渲染两个文档项
      expect(screen.getAllByText('测试文档.txt')).toHaveLength(2);
    });
  });
});
