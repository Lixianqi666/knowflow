'use client';

import { useEffect, useState, useRef } from 'react';
import { api, API_URL } from '@/lib/api';

interface Chunk {
  id: string;
  chunk_index: number;
  content: string;
}

interface Props {
  documentId: string;
  highlightChunkId: string;
  onClose: () => void;
}

export default function SourceViewer({ documentId, highlightChunkId, onClose }: Props) {
  const [doc, setDoc] = useState<{ title: string; content: string } | null>(null);
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [loading, setLoading] = useState(true);
  const highlightRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLoading(true);
    api
      .get<{ document: { title: string; content: string }; chunks: Chunk[] }>(`/documents/${documentId}/chunks`)
      .then((data) => {
        setDoc(data.document);
        setChunks(Array.isArray(data?.chunks) ? data.chunks : []);
      })
      .catch((e) => console.error('加载文档内容失败', e))
      .finally(() => setLoading(false));
  }, [documentId]);

  // 滚动到高亮位置
  useEffect(() => {
    if (!loading && highlightRef.current) {
      highlightRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [loading, chunks]);

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
          <h2 className="font-semibold truncate">{doc?.title || '加载中...'}</h2>
          <div className="flex items-center gap-2">
            {doc && (
              <a
                href={`${API_URL}/documents/${documentId}/file`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:underline flex items-center gap-1"
                onClick={(e) => e.stopPropagation()}
              >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                  />
                </svg>
                下载原文
              </a>
            )}
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-lg">
              ✕
            </button>
          </div>
        </div>
        {/* 内容区 */}
        <div className="p-6 overflow-y-auto flex-1">
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="skeleton h-4" style={{ width: `${85 - i * 8}%` }} />
              ))}
            </div>
          ) : (
            <div className="text-sm leading-relaxed font-sans">
              {chunks.map((chunk) => (
                <div
                  key={chunk.id}
                  ref={chunk.id === highlightChunkId ? highlightRef : undefined}
                  className={`mb-4 p-3 rounded-lg transition-colors ${
                    chunk.id === highlightChunkId
                      ? 'bg-yellow-100 border-2 border-yellow-400'
                      : 'bg-transparent'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{chunk.content}</p>
                  {chunk.id === highlightChunkId && (
                    <p className="text-xs text-yellow-600 mt-1 font-medium">↑ 匹配段落</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
