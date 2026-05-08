'use client';

import { useState, useRef, KeyboardEvent } from 'react';
import { Send, StopCircle } from 'lucide-react';

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
  onStop?: () => void;
  streaming?: boolean;
}

export default function InputBox({ onSend, disabled, onStop, streaming }: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled || streaming) return;
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 160) + 'px';
    }
  };

  return (
    <div className="border-t" style={{ background: 'var(--c-bg)', borderColor: 'var(--c-border)' }}>
      <div className="max-w-3xl mx-auto px-4 py-3">
        {streaming && onStop && (
          <div className="flex justify-center mb-2">
            <button
              onClick={onStop}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-all border-none cursor-pointer"
              style={{
                color: 'var(--c-error)',
                background: 'var(--c-error-subtle)',
                border: '1px solid rgba(220,38,38,.15)',
              }}
            >
              <StopCircle className="w-3.5 h-3.5" />
              停止生成
            </button>
          </div>
        )}

        <div
          className="flex items-end gap-2 rounded-2xl border transition-all"
          style={{
            background: 'var(--c-surface)',
            borderColor: value.trim() ? 'var(--c-primary)' : 'var(--c-border)',
            boxShadow: value.trim() ? '0 0 0 3px var(--c-primary-ring)' : 'var(--shadow-sm)',
            padding: '8px 8px 8px 16px',
          }}
        >
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            placeholder="基于文档提问..."
            disabled={disabled}
            rows={1}
            className="flex-1 resize-none text-sm outline-none bg-transparent py-2 leading-6"
            style={{ color: 'var(--c-text)', maxHeight: 160 }}
          />
          <button
            onClick={handleSend}
            disabled={disabled || streaming || !value.trim()}
            className="shrink-0 w-10 h-10 flex items-center justify-center rounded-xl transition-all border-none cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed hover:scale-105 active:scale-95"
            style={{
              background: value.trim() ? 'var(--c-primary)' : 'var(--c-border)',
              color: value.trim() ? '#fff' : 'var(--c-text-tertiary)',
              boxShadow: value.trim() ? '0 2px 8px rgba(37,99,235,.3)' : 'none',
            }}
          >
            <Send className="w-4 h-4" />
          </button>
        </div>

        <p
          className="text-xs mt-2"
          style={{ color: 'var(--c-text-tertiary)', textAlign: 'center' }}
        >
          <kbd
            className="px-1.5 py-0.5 rounded text-[10px] font-mono"
            style={{ background: 'var(--c-border)', color: 'var(--c-text-secondary)' }}
          >
            Enter
          </kbd>
          <span className="mx-1">发送</span>
          <span className="mx-0.5">·</span>
          <kbd
            className="px-1.5 py-0.5 rounded text-[10px] font-mono"
            style={{ background: 'var(--c-border)', color: 'var(--c-text-secondary)' }}
          >
            Shift+Enter
          </kbd>
          <span className="ml-1">换行</span>
        </p>
      </div>
    </div>
  );
}
