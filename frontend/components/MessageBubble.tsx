'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { api } from '@/lib/api';
import { Download, ThumbsUp, ThumbsDown } from 'lucide-react';

interface Source {
  title: string;
  content?: string;
  score: number;
  chunk_id?: string;
  document_id?: string;
}

interface Props {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  msgId?: string;
  rating?: number | null;
  onSourceClick?: (documentId: string, chunkId: string) => void;
  onRate?: (msgId: string, rating: number) => void;
}

export default function MessageBubble({
  role,
  content,
  sources,
  msgId,
  rating,
  onSourceClick,
  onRate,
}: Props) {
  const isUser = role === 'user';
  const handleDownload = async (docId: string) => {
    try {
      const blob = await api.download(`/documents/${docId}/file`);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = '';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {} // 静默失败，download 已 toast
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[85%] md:max-w-[75%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-md'
            : 'bg-white text-gray-800 shadow-sm rounded-bl-md border'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{content}</p>
        ) : (
          <>
            {content ? (
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown>{content}</ReactMarkdown>
              </div>
            ) : (
              <span className="inline-block w-2 h-4 bg-gray-300 animate-pulse rounded" />
            )}
            {sources && sources.length > 0 && (
              <div className="mt-3 pt-2 border-t border-gray-100">
                <p className="text-xs text-gray-400 mb-2">引用来源</p>
                <div className="flex flex-wrap gap-1.5">
                  {sources.map((s, i) => {
                    const pct = Math.round(s.score * 100);
                    return (
                      <div
                        key={i}
                        className="inline-flex items-stretch text-xs bg-gray-50 border border-gray-200 text-gray-600 rounded overflow-hidden"
                      >
                        <button
                          onClick={() => onSourceClick?.(s.document_id!, s.chunk_id!)}
                          className="flex items-center gap-1 px-2 py-1 hover:bg-blue-50 hover:text-blue-600 transition-colors cursor-pointer"
                          title={s.content || ''}
                        >
                          <span className="max-w-[100px] truncate">{s.title}</span>
                          <span
                            className={`font-mono ${
                              pct >= 80
                                ? 'text-green-600'
                                : pct >= 50
                                  ? 'text-yellow-600'
                                  : 'text-gray-400'
                            }`}
                          >
                            {pct}%
                          </span>
                        </button>
                        {s.document_id && (
                          <button
                            onClick={() => handleDownload(s.document_id!)}
                            className="flex items-center px-1.5 border-l border-gray-200 text-gray-400 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                            title="下载原文"
                          >
                            <Download className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
            {/* 赞踩按钮 */}
            {msgId && content && rating === undefined && onRate && (
              <div className="mt-2 flex items-center gap-2 text-gray-400">
                <RatingButton
                  icon={<ThumbsUp className="w-4 h-4" />}
                  active={rating === 1}
                  onClick={() => onRate(msgId, 1)}
                />
                <RatingButton
                  icon={<ThumbsDown className="w-4 h-4" />}
                  active={rating === -1}
                  onClick={() => onRate(msgId, -1)}
                />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function RatingButton({
  icon,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  active: boolean;
  onClick: () => void;
}) {
  const [done, setDone] = useState(false);
  return (
    <button
      onClick={() => {
        onClick();
        setDone(true);
      }}
      disabled={done}
      className={`flex items-center justify-center w-8 h-8 rounded transition-colors ${
        done ? 'opacity-30 cursor-default' : 'hover:bg-gray-100'
      }`}
    >
      {icon}
    </button>
  );
}
