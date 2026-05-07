'use client';

import { useState, useRef, KeyboardEvent } from 'react';
import { Send } from 'lucide-react';

interface Props {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export default function InputBox({ onSend, disabled }: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
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
      el.style.height = Math.min(el.scrollHeight, 200) + 'px';
    }
  };

  return (
    <div className="p-4 bg-white border-t">
      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder="基于文档提问，例如：公司的考勤制度是什么？"
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none rounded-xl border px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap flex items-center gap-2"
        >
          <Send className="w-4 h-4" />
          发送
        </button>
      </div>
      <p className="text-xs text-gray-400 mt-1.5 ml-1">
        <kbd className="px-1 py-0.5 bg-gray-100 rounded text-[10px] font-mono">Enter</kbd> 发送
        <span className="mx-1.5">·</span>
        <kbd className="px-1 py-0.5 bg-gray-100 rounded text-[10px] font-mono">
          Shift+Enter
        </kbd>{' '}
        换行
      </p>
    </div>
  );
}
