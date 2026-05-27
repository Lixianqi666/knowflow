'use client';

import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('页面错误:', error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-4">
      <div
        className="w-16 h-16 rounded-2xl flex items-center justify-center mb-6"
        style={{ background: 'var(--c-error-subtle)', color: 'var(--c-error)' }}
      >
        <svg
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>
      <h2 className="text-lg font-semibold mb-2" style={{ color: 'var(--c-text)' }}>
        出错了
      </h2>
      <p className="text-sm mb-6 text-center max-w-md" style={{ color: 'var(--c-text-secondary)' }}>
        {error.message || '页面运行时发生错误，请尝试刷新。'}
      </p>
      <button
        onClick={reset}
        className="px-4 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer border-none"
        style={{ background: 'var(--c-primary)', color: '#fff' }}
      >
        重试
      </button>
    </div>
  );
}
