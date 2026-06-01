import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

beforeAll(() => {
  HTMLElement.prototype.scrollIntoView = vi.fn();
});

const mockPost = vi.fn();
const mockGet = vi.fn();
const mockDownload = vi.fn();

vi.mock('@/lib/api', () => ({
  api: {
    post: (...args: any[]) => mockPost(...args),
    get: (...args: any[]) => mockGet(...args),
    download: (...args: any[]) => mockDownload(...args),
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

vi.mock('react-markdown', () => ({
  default: ({ children }: any) => <div>{children}</div>,
}));

import RAGDebugPanel from '@/components/RAGDebugPanel';

const mockKbOptions = [
  { id: 'kb-1', name: '知识库A' },
  { id: 'kb-2', name: '知识库B' },
];

const mockResults = {
  query: '试用期',
  top_k: 5,
  results: [
    {
      rank: 1,
      document_id: 'doc-1',
      document_title: '员工手册',
      chunk_id: 'chunk-1',
      snippet: '试用期为3个月，特殊岗位可延长至6个月。',
      score: 0.85,
      page: 3,
      locator: { type: 'page', value: '3' },
    },
    {
      rank: 2,
      document_id: 'doc-2',
      document_title: '劳动合同',
      chunk_id: 'chunk-2',
      snippet: '试用期根据合同期限确定。',
      score: 0.62,
      locator: { type: 'chunk', value: 'chunk-2' },
    },
  ],
  no_result_reason: null,
};

const mockEmptyResults = {
  query: '不存在的query',
  top_k: 5,
  results: [],
  no_result_reason: '未检索到相关内容',
};

describe('RAGDebugPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('渲染初始状态', () => {
    render(<RAGDebugPanel kbOptions={mockKbOptions} />);
    expect(screen.getByText('RAG 检索调试')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('输入检索词...')).toBeInTheDocument();
    expect(screen.getByText('运行检索')).toBeInTheDocument();
  });

  it('输入 query 后点击运行调用 API', async () => {
    mockPost.mockResolvedValueOnce(mockResults);
    render(<RAGDebugPanel kbOptions={mockKbOptions} />);

    fireEvent.change(screen.getByPlaceholderText('输入检索词...'), {
      target: { value: '试用期' },
    });
    fireEvent.click(screen.getByText('运行检索'));

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/rag/debug-search', {
        query: '试用期',
        top_k: 5,
      });
    });
  });

  it('top_k 传给 API', async () => {
    mockPost.mockResolvedValueOnce(mockResults);
    render(<RAGDebugPanel kbOptions={mockKbOptions} />);

    const topKInput = screen.getByDisplayValue('5');
    fireEvent.change(topKInput, { target: { value: '10' } });

    fireEvent.change(screen.getByPlaceholderText('输入检索词...'), {
      target: { value: 'test' },
    });
    fireEvent.click(screen.getByText('运行检索'));

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/rag/debug-search', {
        query: 'test',
        top_k: 10,
      });
    });
  });

  it('成功后显示 document_title / score / snippet', async () => {
    mockPost.mockResolvedValueOnce(mockResults);
    render(<RAGDebugPanel kbOptions={mockKbOptions} />);

    fireEvent.change(screen.getByPlaceholderText('输入检索词...'), {
      target: { value: '试用期' },
    });
    fireEvent.click(screen.getByText('运行检索'));

    await waitFor(() => {
      expect(screen.getByText('员工手册')).toBeInTheDocument();
      expect(screen.getByText('劳动合同')).toBeInTheDocument();
      expect(screen.getByText(/试用期为3个月/)).toBeInTheDocument();
      expect(screen.getByText('85.0%')).toBeInTheDocument();
    });
  });

  it('显示 page / locator', async () => {
    mockPost.mockResolvedValueOnce(mockResults);
    render(<RAGDebugPanel kbOptions={mockKbOptions} />);

    fireEvent.change(screen.getByPlaceholderText('输入检索词...'), {
      target: { value: '试用期' },
    });
    fireEvent.click(screen.getByText('运行检索'));

    await waitFor(() => {
      expect(screen.getByText('第3页')).toBeInTheDocument();
      expect(screen.getByText('定位片段')).toBeInTheDocument();
    });
  });

  it('无结果时显示 no_result_reason', async () => {
    mockPost.mockResolvedValueOnce(mockEmptyResults);
    render(<RAGDebugPanel kbOptions={mockKbOptions} />);

    fireEvent.change(screen.getByPlaceholderText('输入检索词...'), {
      target: { value: '不存在的query' },
    });
    fireEvent.click(screen.getByText('运行检索'));

    await waitFor(() => {
      expect(screen.getByText('未检索到相关内容')).toBeInTheDocument();
    });
  });

  it('403 显示无权限', async () => {
    mockPost.mockRejectedValueOnce(new Error('403'));
    render(<RAGDebugPanel kbOptions={mockKbOptions} />);

    fireEvent.change(screen.getByPlaceholderText('输入检索词...'), {
      target: { value: 'test' },
    });
    fireEvent.click(screen.getByText('运行检索'));

    await waitFor(() => {
      expect(screen.getByText('无权限访问该知识库')).toBeInTheDocument();
    });
  });

  it('API 失败显示错误', async () => {
    mockPost.mockRejectedValueOnce(new Error('网络错误'));
    render(<RAGDebugPanel kbOptions={mockKbOptions} />);

    fireEvent.change(screen.getByPlaceholderText('输入检索词...'), {
      target: { value: 'test' },
    });
    fireEvent.click(screen.getByText('运行检索'));

    await waitFor(() => {
      expect(screen.getByText('网络错误')).toBeInTheDocument();
    });
  });

  it('点击结果打开预览面板', async () => {
    mockPost.mockResolvedValueOnce(mockResults);
    mockGet.mockResolvedValueOnce({
      document_id: 'doc-1',
      title: '员工手册',
      file_type: 'txt',
      status: 'indexed',
      preview_mode: 'text',
      content: '试用期为3个月',
      download_url: '/api/v1/documents/doc-1/file',
    });

    render(<RAGDebugPanel kbOptions={mockKbOptions} />);

    fireEvent.change(screen.getByPlaceholderText('输入检索词...'), {
      target: { value: '试用期' },
    });
    fireEvent.click(screen.getByText('运行检索'));

    await waitFor(() => {
      expect(screen.getByText('员工手册')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('员工手册'));

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith('/documents/doc-1/preview');
    });
  });

  it('知识库选择传给 API', async () => {
    mockPost.mockResolvedValueOnce(mockResults);
    render(<RAGDebugPanel kbOptions={mockKbOptions} />);

    fireEvent.change(screen.getByPlaceholderText('输入检索词...'), {
      target: { value: 'test' },
    });
    fireEvent.change(screen.getByDisplayValue('全部可访问知识库'), {
      target: { value: 'kb-1' },
    });
    fireEvent.click(screen.getByText('运行检索'));

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/rag/debug-search', {
        query: 'test',
        top_k: 5,
        knowledge_base_id: 'kb-1',
      });
    });
  });
});
