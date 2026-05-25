'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { api } from '@/lib/api';
import { Download, ThumbsUp, ThumbsDown, FileText } from 'lucide-react';
import { Source } from '@/lib/store';

const ReactMarkdown = dynamic(() => import('react-markdown'), { ssr: false });

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
    } catch {}
  };

  // 去掉 LLM 回复末尾的 JSON 结构化数据和来源标注（前端已用组件展示来源）
  const cleanContent = (() => {
    if (!content || isUser) return content;
    let c = content
      // 去掉 ```json { ... } ``` 块
      .replace(/```json[\s\S]*?```/g, '')
      // 去掉末尾的 { "answer": ... } JSON
      .replace(/\s*\{[\s\S]*"answer"[\s\S]*"sources"[\s\S]*\}\s*$/, '')
      // 去掉 LLM 自行添加的 [来源: xxx]（前端用独立组件展示）
      .replace(/\[来源:\s*[^\]]+\]/g, '')
      // 去掉来源后的空行
      .replace(/\n{3,}/g, '\n\n');
    return c.trim();
  })();

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-5 animate-slide-up`}>
      <div
        className={`max-w-[88%] md:max-w-[75%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-sm'
            : 'bg-white text-[var(--c-text)] shadow-sm rounded-bl-sm border border-[var(--c-border)]/60'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-[15px] leading-relaxed">{content}</p>
        ) : (
          <div className="text-[15px] leading-relaxed">
            {cleanContent ? (
              <div className="prose">
                <ReactMarkdown>{cleanContent}</ReactMarkdown>
              </div>
            ) : (
              <div className="flex items-center gap-1.5 py-1">
                <span
                  className="inline-block w-2 h-4 rounded-sm"
                  style={{
                    background: 'var(--c-primary)',
                    opacity: 0.4,
                    animation: 'breathe 1.4s infinite',
                  }}
                />
                <span
                  className="inline-block w-2 h-4 rounded-sm"
                  style={{
                    background: 'var(--c-primary)',
                    opacity: 0.3,
                    animation: 'breathe 1.4s infinite 0.2s',
                  }}
                />
                <span
                  className="inline-block w-2 h-4 rounded-sm"
                  style={{
                    background: 'var(--c-primary)',
                    opacity: 0.2,
                    animation: 'breathe 1.4s infinite 0.4s',
                  }}
                />
              </div>
            )}

            {sources && sources.length > 0 && (
              <div className="mt-3 pt-3 border-t" style={{ borderColor: 'var(--c-border)' }}>
                <p className="text-xs font-medium mb-2" style={{ color: 'var(--c-text-tertiary)' }}>
                  引用来源 ({sources.length})
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {sources.map((s, i) => {
                    const pct = Math.round((s.score ?? 0) * 100);
                    return (
                      <div
                        key={i}
                        className="inline-flex items-stretch text-xs rounded-lg overflow-hidden transition-all animate-fade-in"
                        style={{
                          background: 'var(--c-bg)',
                          border: '1px solid var(--c-border)',
                          color: 'var(--c-text-secondary)',
                        }}
                      >
                        <button
                          onClick={() => onSourceClick?.(s.document_id!, s.chunk_id!)}
                          className="flex items-center gap-1.5 px-2 py-1.5 transition-colors border-none cursor-pointer"
                          style={{ background: 'none', color: 'inherit' }}
                        >
                          <FileText className="w-3 h-3 shrink-0" />
                          <span className="max-w-[80px] truncate">{s.title}</span>
                          <span
                            className={`font-mono text-[10px] font-medium ${pct >= 80 ? 'text-green-600' : pct >= 50 ? 'text-yellow-600' : 'text-gray-400'}`}
                          >
                            {pct}%
                          </span>
                        </button>
                        {s.document_id && (
                          <button
                            onClick={() => handleDownload(s.document_id!)}
                            className="flex items-center px-1.5 transition-colors border-none cursor-pointer"
                            style={{
                              borderLeft: '1px solid var(--c-border)',
                              color: 'var(--c-text-tertiary)',
                              background: 'none',
                            }}
                          >
                            <Download className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {msgId && content && rating === undefined && onRate && (
              <div className="mt-3 flex items-center gap-1">
                <RatingButton
                  icon={<ThumbsUp className="w-3.5 h-3.5" />}
                  onClick={() => onRate(msgId, 1)}
                />
                <RatingButton
                  icon={<ThumbsDown className="w-3.5 h-3.5" />}
                  onClick={() => onRate(msgId, -1)}
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function RatingButton({ icon, onClick }: { icon: React.ReactNode; onClick: () => void }) {
  const [done, setDone] = useState(false);
  return (
    <button
      onClick={() => {
        onClick();
        setDone(true);
      }}
      disabled={done}
      className="flex items-center justify-center w-7 h-7 rounded-lg transition-all border-none cursor-pointer disabled:opacity-40"
      style={{ color: 'var(--c-text-tertiary)', background: 'none' }}
      onMouseEnter={(e) => {
        if (!done) {
          e.currentTarget.style.background = 'var(--c-bg)';
          e.currentTarget.style.color = 'var(--c-primary)';
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'none';
        e.currentTarget.style.color = 'var(--c-text-tertiary)';
      }}
    >
      {icon}
    </button>
  );
}
