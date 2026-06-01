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
  Users: () => <svg />,
  Settings: () => <svg />,
  Search: () => <svg />,
  RefreshCw: () => <svg />,
}));

import RAGConfigPanel from '@/components/RAGConfigPanel';

const defaultConfig = {
  rag_config: {
    top_k: 5,
    score_threshold: 0,
    chunk_size: 1000,
    chunk_overlap: 150,
    no_evidence_policy: 'strict',
  },
};

describe('RAGConfigPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('loading 状态', () => {
    mockGet.mockReturnValue(new Promise(() => {})); // never resolves
    const { container } = render(<RAGConfigPanel kbId="kb-1" kbName="测试KB" canEdit={true} />);
    expect(container.querySelector('.skeleton')).toBeInTheDocument();
  });

  it('成功后显示 top_k / score_threshold / chunk_size', async () => {
    mockGet.mockResolvedValueOnce(defaultConfig);
    render(<RAGConfigPanel kbId="kb-1" kbName="测试KB" canEdit={true} />);
    await waitFor(() => {
      expect(screen.getByDisplayValue('5')).toBeInTheDocument();
      expect(screen.getByDisplayValue('0')).toBeInTheDocument();
      expect(screen.getByDisplayValue('1000')).toBeInTheDocument();
    });
  });

  it('owner 可保存配置', async () => {
    mockGet.mockResolvedValueOnce(defaultConfig);
    mockPatch.mockResolvedValueOnce({ rag_config: { ...defaultConfig.rag_config, top_k: 10 } });
    render(<RAGConfigPanel kbId="kb-1" kbName="测试KB" canEdit={true} />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('5')).toBeInTheDocument();
    });

    const topKInput = screen.getByDisplayValue('5');
    fireEvent.change(topKInput, { target: { value: '10' } });
    fireEvent.click(screen.getByText('保存配置'));

    await waitFor(() => {
      expect(mockPatch).toHaveBeenCalledWith('/knowledge-bases/kb-1/rag-config', {
        rag_config: expect.objectContaining({ top_k: 10 }),
      });
    });
  });

  it('viewer 保存按钮不可见', async () => {
    mockGet.mockResolvedValueOnce(defaultConfig);
    render(<RAGConfigPanel kbId="kb-1" kbName="测试KB" canEdit={false} />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('5')).toBeInTheDocument();
    });

    expect(screen.queryByText('保存配置')).not.toBeInTheDocument();
    expect(screen.queryByText('重建索引')).not.toBeInTheDocument();
  });

  it('保存失败显示错误', async () => {
    mockGet.mockResolvedValueOnce(defaultConfig);
    mockPatch.mockRejectedValueOnce(new Error('top_k 必须是 1~20 的整数'));
    render(<RAGConfigPanel kbId="kb-1" kbName="测试KB" canEdit={true} />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('5')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('保存配置'));

    await waitFor(() => {
      expect(screen.getByText('top_k 必须是 1~20 的整数')).toBeInTheDocument();
    });
  });

  it('点击重建索引会弹确认并调用 API', async () => {
    mockGet.mockResolvedValueOnce(defaultConfig);
    mockPost.mockResolvedValueOnce({ queued: 3 });
    window.confirm = vi.fn().mockReturnValue(true);

    render(<RAGConfigPanel kbId="kb-1" kbName="测试KB" canEdit={true} />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('5')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('重建索引'));

    await waitFor(() => {
      expect(window.confirm).toHaveBeenCalled();
      expect(mockPost).toHaveBeenCalledWith('/knowledge-bases/kb-1/reindex');
    });
  });

  it('重建索引成功显示 queued 数量', async () => {
    mockGet.mockResolvedValueOnce(defaultConfig);
    mockPost.mockResolvedValueOnce({ queued: 5 });
    window.confirm = vi.fn().mockReturnValue(true);

    render(<RAGConfigPanel kbId="kb-1" kbName="测试KB" canEdit={true} />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('5')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('重建索引'));

    await waitFor(() => {
      expect(screen.getByText('已入队 5 个文档')).toBeInTheDocument();
    });
  });

  it('重建索引失败显示错误', async () => {
    mockGet.mockResolvedValueOnce(defaultConfig);
    mockPost.mockRejectedValueOnce(new Error('无权重建'));
    window.confirm = vi.fn().mockReturnValue(true);

    render(<RAGConfigPanel kbId="kb-1" kbName="测试KB" canEdit={true} />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('5')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('重建索引'));

    await waitFor(() => {
      expect(screen.getByText('无权重建')).toBeInTheDocument();
    });
  });

  it('空 rag_config 不崩溃', async () => {
    mockGet.mockResolvedValueOnce({ rag_config: null });
    render(<RAGConfigPanel kbId="kb-1" kbName="测试KB" canEdit={true} />);
    await waitFor(() => {
      expect(screen.getByText(/RAG 配置/)).toBeInTheDocument();
      expect(screen.getByDisplayValue('5')).toBeInTheDocument(); // default top_k
    });
  });

  it('非法输入不导致页面崩溃', async () => {
    mockGet.mockResolvedValueOnce(defaultConfig);
    render(<RAGConfigPanel kbId="kb-1" kbName="测试KB" canEdit={true} />);

    await waitFor(() => {
      expect(screen.getByDisplayValue('5')).toBeInTheDocument();
    });

    const topKInput = screen.getByDisplayValue('5');
    fireEvent.change(topKInput, { target: { value: '999' } });
    // 页面不应崩溃
    expect(topKInput).toHaveValue(999);
  });
});
