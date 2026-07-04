'use client';

import { useState } from 'react';
import dynamic from 'next/dynamic';
import { api } from '@/lib/api';
import { Download, ThumbsUp, ThumbsDown, FileText } from 'lucide-react';
import { Source } from '@/lib/store';

const ReactMarkdown = dynamic(() => import('react-markdown'), { ssr: false });

interface Citation {
  index: number;
  document_id: string;
  document_title: string;
  chunk_id: string;
  snippet: string;
  score?: number;
  page?: number;
  section?: string;
  locator?: { type: string; value: string };
}

interface FeedbackData {
  rating: string;
  reason?: string | null;
}

interface Props {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  citations?: Citation[];
  msgId?: string;
  rating?: number | null;
  feedback?: FeedbackData | null;
  onSourceClick?: (documentId: string, chunkId: string) => void;
  onRate?: (msgId: string, rating: number) => void;
  onFeedback?: (msgId: string, rating: string, reason?: string) => void;
  onToEvalCase?: (msgId: string) => void;
}

export default function MessageBubble({
  role,
  content,
  sources,
  citations,
  msgId,
  rating,
  feedback,
  onSourceClick,
  onRate,
  onFeedback,
  onToEvalCase,
}: Props) {
  const [citationsOpen, setCitationsOpen] = useState(false);
  const [evalCaseCreated, setEvalCaseCreated] = useState(false);
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
    } catch (e) {
      console.error('复制失败:', e);
    }
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

  // 把内容中疑似 LLM 误用的代码块拆开：当代码块内文本不包含换行/缩进（看起来像普通段落被错误包裹）
  // 时，按换行/箭头连接符拆为正常段落。
  const unescapeFencedParagraphs = (text: string) => {
    return text.replace(/```[a-zA-Z]*\n?([\s\S]*?)\n?```/g, (match, body) => {
      const trimmed = body.trim();
      // 判定：内容里没有换行、且不是典型的代码（含箭头/中文长段落）→ 当作段落拆出来
      const isLikelyParagraph =
        !trimmed.includes('\n') &&
        (trimmed.includes('→') || /[\u4e00-\u9fa5]/.test(trimmed));
      if (isLikelyParagraph) {
        return trimmed.replace(/→/g, '\n→ ');
      }
      return match;
    });
  };

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
                <ReactMarkdown>{unescapeFencedParagraphs(cleanContent)}</ReactMarkdown>
              </div>
            ) : (
              <div
                className="inline-flex items-center gap-2 text-sm"
                style={{ color: 'var(--c-text-tertiary)' }}
              >
                <div className="thinking-dots">
                  <span />
                  <span />
                  <span />
                </div>
                <span>正在检索文档并生成回答...</span>
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

            {citations && citations.length > 0 && (
              <div className="mt-3 pt-3 border-t" style={{ borderColor: 'var(--c-border)' }}>
                <button
                  onClick={() => setCitationsOpen(!citationsOpen)}
                  className="flex items-center gap-1.5 text-xs font-medium border-none cursor-pointer transition-colors"
                  style={{ color: 'var(--c-primary)', background: 'none' }}
                >
                  <FileText className="w-3 h-3" />
                  引用 {citations.length} 条
                  <span className="text-[10px]" style={{ color: 'var(--c-text-tertiary)' }}>
                    {citationsOpen ? '▲' : '▼'}
                  </span>
                </button>
                {citationsOpen && (
                  <div className="mt-2 space-y-2 animate-slide-up">
                    {citations.map((c) => (
                      <div
                        key={c.chunk_id}
                        className="p-2.5 rounded-lg text-xs cursor-pointer transition-all hover:shadow-sm"
                        style={{ background: 'var(--c-bg)', border: '1px solid var(--c-border)' }}
                        onClick={() => c.document_id && onSourceClick?.(c.document_id, c.chunk_id)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            c.document_id && onSourceClick?.(c.document_id, c.chunk_id);
                          }
                        }}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <div className="font-medium" style={{ color: 'var(--c-text-secondary)' }}>
                            {c.document_title}
                          </div>
                          {c.page && (
                            <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: 'var(--c-primary-subtle)', color: 'var(--c-primary)' }}>
                              第{c.page}页
                            </span>
                          )}
                        </div>
                        <div
                          className="leading-relaxed"
                          style={{ color: 'var(--c-text-tertiary)' }}
                        >
                          {c.snippet.length > 200 ? c.snippet.slice(0, 200) + '...' : c.snippet}
                        </div>
                        {c.document_id && (
                          <div className="mt-1 text-[10px]" style={{ color: 'var(--c-primary)' }}>
                            点击查看原文 →
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {msgId && content && (
              <div className="mt-3 flex items-center gap-1 flex-wrap">
                {feedback ? (
                  <>
                    <span
                      className="text-xs px-2 py-1 rounded-lg"
                      style={{
                        background: feedback.rating === 'up' ? 'var(--c-success-subtle)' : 'var(--c-error-subtle)',
                        color: feedback.rating === 'up' ? '#16a34a' : '#dc2626',
                      }}
                    >
                      {feedback.rating === 'up' ? '👍 已反馈' : '👎 已反馈'}
                    </span>
                    {feedback.rating === 'down' && onToEvalCase && (
                      evalCaseCreated ? (
                        <span className="text-xs px-2 py-1 rounded-lg" style={{ background: 'var(--c-success-subtle)', color: '#16a34a' }}>
                          ✓ 已加入评测集
                        </span>
                      ) : (
                        <button
                          onClick={() => {
                            onToEvalCase(msgId);
                            setEvalCaseCreated(true);
                          }}
                          className="text-xs px-2 py-1 rounded-lg border-none cursor-pointer transition-all"
                          style={{ background: 'var(--c-primary-subtle)', color: 'var(--c-primary)' }}
                        >
                          加入评测集
                        </button>
                      )
                    )}
                  </>
                ) : onFeedback ? (
                  <>
                    <FeedbackButton
                      icon={<ThumbsUp className="w-3.5 h-3.5" />}
                      onClick={() => onFeedback(msgId, 'up')}
                    />
                    <FeedbackButton
                      icon={<ThumbsDown className="w-3.5 h-3.5" />}
                      onClick={() => onFeedback(msgId, 'down')}
                    />
                  </>
                ) : rating === undefined && onRate ? (
                  <>
                    <RatingButton
                      icon={<ThumbsUp className="w-3.5 h-3.5" />}
                      onClick={() => onRate(msgId, 1)}
                    />
                    <RatingButton
                      icon={<ThumbsDown className="w-3.5 h-3.5" />}
                      onClick={() => onRate(msgId, -1)}
                    />
                  </>
                ) : null}
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

function FeedbackButton({ icon, onClick }: { icon: React.ReactNode; onClick: () => void }) {
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
