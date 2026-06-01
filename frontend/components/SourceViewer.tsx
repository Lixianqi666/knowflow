'use client';

import { useEffect, useState, useRef } from 'react';
import { api } from '@/lib/api';

interface PreviewData {
  document_id: string;
  title: string;
  file_type: string;
  status: string;
  preview_mode: string;
  content?: string;
  download_url: string;
}

interface Props {
  documentId: string;
  highlightChunkId?: string;
  snippet?: string;
  page?: number;
  locator?: { type: string; value: string };
  onClose: () => void;
}

export default function SourceViewer({
  documentId,
  highlightChunkId,
  snippet,
  page,
  locator,
  onClose,
}: Props) {
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const snippetRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .get<PreviewData>(`/documents/${documentId}/preview`)
      .then((data) => setPreview(data))
      .catch((e: Error) => {
        if (e.message.includes('403') || e.message.includes('无权限')) {
          setError('无权限查看此文档');
        } else {
          setError(e.message || '加载失败');
        }
      })
      .finally(() => setLoading(false));
  }, [documentId]);

  // 滚动到 snippet 位置
  useEffect(() => {
    if (!loading && snippetRef.current) {
      snippetRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [loading, preview]);

  const handleDownload = async () => {
    setDownloading(true);
    setDownloadError(null);
    let url: string | null = null;
    try {
      const blob = await api.download(`/documents/${documentId}/file`);
      url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = preview?.title || documentId;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch {
      setDownloadError('下载失败，请稍后重试');
    } finally {
      if (url) URL.revokeObjectURL(url);
      setDownloading(false);
    }
  };

  // 在文本内容中定位 snippet 附近区域
  const renderTextContent = () => {
    if (!preview?.content) return null;

    const content = preview.content;

    // 如果有 snippet，尝试在内容中定位
    if (snippet && snippet.length > 20) {
      const searchSnippet = snippet.slice(0, 100);
      const idx = content.indexOf(searchSnippet);
      if (idx >= 0) {
        // 显示 snippet 前后各 500 字
        const start = Math.max(0, idx - 500);
        const end = Math.min(content.length, idx + snippet.length + 500);
        const before = content.slice(start, idx);
        const matchText = content.slice(idx, idx + snippet.length);
        const after = content.slice(idx + snippet.length, end);

        return (
          <div className="text-sm leading-relaxed font-sans whitespace-pre-wrap">
            {start > 0 && (
              <span style={{ color: 'var(--c-text-tertiary)' }}>
                {'...'}
                {before}
              </span>
            )}
            <span
              ref={snippetRef}
              className="bg-yellow-100 border-b-2 border-yellow-400 px-0.5"
            >
              {matchText}
            </span>
            {end < content.length && (
              <span style={{ color: 'var(--c-text-tertiary)' }}>
                {after}
                {'...'}
              </span>
            )}
          </div>
        );
      }
    }

    // 没有 snippet 或找不到，显示全文（限制长度）
    const displayText = content.length > 15000 ? content.slice(0, 15000) + '\n\n...(内容过长，已截断)' : content;
    return (
      <div className="text-sm leading-relaxed font-sans whitespace-pre-wrap">
        {displayText}
      </div>
    );
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 animate-fade-in"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl w-full max-w-3xl max-h-[85vh] flex flex-col mx-4 animate-scale-in"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 头部 */}
        <div className="flex items-center justify-between p-4 border-b shrink-0">
          <div className="min-w-0 flex-1">
            <h2 className="font-semibold truncate">{preview?.title || '加载中...'}</h2>
            {/* 定位信息 */}
            {(page || locator) && (
              <div className="flex items-center gap-2 mt-1">
                {page && (
                  <span
                    className="text-[11px] px-2 py-0.5 rounded-full"
                    style={{ background: 'var(--c-primary-subtle)', color: 'var(--c-primary)' }}
                  >
                    页码：{page}
                  </span>
                )}
                {locator?.type === 'chunk' && (
                  <span
                    className="text-[11px] px-2 py-0.5 rounded-full"
                    style={{ background: 'var(--c-bg)', color: 'var(--c-text-tertiary)' }}
                  >
                    定位片段
                  </span>
                )}
                {locator?.type === 'text' && (
                  <span
                    className="text-[11px] px-2 py-0.5 rounded-full"
                    style={{ background: 'var(--c-bg)', color: 'var(--c-text-tertiary)' }}
                  >
                    {locator.value}
                  </span>
                )}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0 ml-2">
            {preview && (
              <button
                onClick={handleDownload}
                disabled={downloading}
                className="text-xs text-blue-600 hover:underline flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                  />
                </svg>
                {downloading ? '下载中...' : '下载原文'}
              </button>
            )}
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg">
              ✕
            </button>
          </div>
        </div>
        {downloadError && (
          <div className="px-4 py-2 text-xs text-red-600 bg-red-50 border-b">{downloadError}</div>
        )}
        {/* 引用片段 */}
        {snippet && (
          <div className="px-4 py-3 border-b" style={{ background: 'var(--c-primary-subtle)' }}>
            <div className="text-[11px] font-medium mb-1" style={{ color: 'var(--c-primary)' }}>
              引用片段
            </div>
            <div className="text-xs leading-relaxed" style={{ color: 'var(--c-text-secondary)' }}>
              {snippet}
            </div>
          </div>
        )}
        {/* 内容区 */}
        <div className="p-6 overflow-y-auto flex-1">
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="skeleton h-4" style={{ width: `${85 - i * 8}%` }} />
              ))}
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <div className="text-sm" style={{ color: 'var(--c-text-tertiary)' }}>
                {error}
              </div>
            </div>
          ) : preview?.preview_mode === 'text' ? (
            renderTextContent()
          ) : (
            <div className="text-center py-12">
              <svg
                className="w-12 h-12 mx-auto mb-3"
                style={{ color: 'var(--c-text-tertiary)' }}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                />
              </svg>
              <div className="text-sm mb-2" style={{ color: 'var(--c-text-secondary)' }}>
                此文件类型暂不支持在线预览
              </div>
              <div className="text-xs mb-4" style={{ color: 'var(--c-text-tertiary)' }}>
                {preview?.file_type?.toUpperCase() || '未知格式'} 文件，请下载后查看
              </div>
              <button
                onClick={handleDownload}
                disabled={downloading}
                className="text-xs text-blue-600 hover:underline disabled:opacity-50"
              >
                {downloading ? '下载中...' : '点击下载原文'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
