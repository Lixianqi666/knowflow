import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

beforeAll(() => {
  HTMLElement.prototype.scrollIntoView = vi.fn();
});

const mockGet = vi.fn();
const mockDownload = vi.fn();

vi.mock('@/lib/api', () => ({
  api: {
    get: (...args: any[]) => mockGet(...args),
    download: (...args: any[]) => mockDownload(...args),
  },
  API_URL: 'http://localhost:8000/api/v1',
}));

vi.mock('lucide-react', () => ({
  Download: () => <svg />,
  ThumbsUp: () => <svg />,
  ThumbsDown: () => <svg />,
  FileText: () => <svg />,
}));

import SourceViewer from '@/components/SourceViewer';

const textPreviewData = {
  document_id: 'doc-1',
  title: '测试文档.txt',
  file_type: 'txt',
  status: 'indexed',
  preview_mode: 'text',
  content: '这是文档的正文内容，包含一些测试文本。',
  download_url: '/api/v1/documents/doc-1/file',
};

const downloadOnlyData = {
  document_id: 'doc-2',
  title: '报告.pdf',
  file_type: 'pdf',
  status: 'indexed',
  preview_mode: 'download_only',
  download_url: '/api/v1/documents/doc-2/file',
};

describe('SourceViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('调用 preview API 加载文档', async () => {
    mockGet.mockResolvedValueOnce(textPreviewData);
    render(
      <SourceViewer documentId="doc-1" onClose={vi.fn()} />,
    );
    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith('/documents/doc-1/preview');
    });
  });

  it('text preview 显示 content', async () => {
    mockGet.mockResolvedValueOnce(textPreviewData);
    render(
      <SourceViewer documentId="doc-1" onClose={vi.fn()} />,
    );
    await waitFor(() => {
      expect(screen.getByText(/这是文档的正文内容/)).toBeInTheDocument();
    });
  });

  it('download_only 显示下载提示', async () => {
    mockGet.mockResolvedValueOnce(downloadOnlyData);
    render(
      <SourceViewer documentId="doc-2" onClose={vi.fn()} />,
    );
    await waitFor(() => {
      expect(screen.getByText('此文件类型暂不支持在线预览')).toBeInTheDocument();
      expect(screen.getByText(/PDF 文件，请下载后查看/)).toBeInTheDocument();
    });
  });

  it('显示引用片段', async () => {
    mockGet.mockResolvedValueOnce(textPreviewData);
    render(
      <SourceViewer
        documentId="doc-1"
        snippet="这是引用的片段内容"
        onClose={vi.fn()}
      />,
    );
    await waitFor(() => {
      expect(screen.getByText('引用片段')).toBeInTheDocument();
      expect(screen.getByText('这是引用的片段内容')).toBeInTheDocument();
    });
  });

  it('有 page 时显示页码', async () => {
    mockGet.mockResolvedValueOnce(textPreviewData);
    render(
      <SourceViewer
        documentId="doc-1"
        page={3}
        onClose={vi.fn()}
      />,
    );
    await waitFor(() => {
      expect(screen.getByText('页码：3')).toBeInTheDocument();
    });
  });

  it('locator type=chunk 显示定位片段', async () => {
    mockGet.mockResolvedValueOnce(textPreviewData);
    render(
      <SourceViewer
        documentId="doc-1"
        locator={{ type: 'chunk', value: 'chunk-123' }}
        onClose={vi.fn()}
      />,
    );
    await waitFor(() => {
      expect(screen.getByText('定位片段')).toBeInTheDocument();
    });
  });

  it('preview error 显示错误提示', async () => {
    mockGet.mockRejectedValueOnce(new Error('加载失败'));
    render(
      <SourceViewer documentId="doc-1" onClose={vi.fn()} />,
    );
    await waitFor(() => {
      expect(screen.getByText('加载失败')).toBeInTheDocument();
    });
  });

  it('403 显示无权限提示', async () => {
    mockGet.mockRejectedValueOnce(new Error('403'));
    render(
      <SourceViewer documentId="doc-1" onClose={vi.fn()} />,
    );
    await waitFor(() => {
      expect(screen.getByText('无权限查看此文档')).toBeInTheDocument();
    });
  });

  it('关闭按钮调用 onClose', async () => {
    mockGet.mockResolvedValueOnce(textPreviewData);
    const onClose = vi.fn();
    render(
      <SourceViewer documentId="doc-1" onClose={onClose} />,
    );
    await waitFor(() => {
      expect(screen.getByText('测试文档.txt')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('✕'));
    expect(onClose).toHaveBeenCalled();
  });

  it('点击遮罩层调用 onClose', async () => {
    mockGet.mockResolvedValueOnce(textPreviewData);
    const onClose = vi.fn();
    render(
      <SourceViewer documentId="doc-1" onClose={onClose} />,
    );
    await waitFor(() => {
      expect(screen.getByText('测试文档.txt')).toBeInTheDocument();
    });
    // 点击背景遮罩
    fireEvent.click(document.querySelector('.fixed')!);
    expect(onClose).toHaveBeenCalled();
  });
});
