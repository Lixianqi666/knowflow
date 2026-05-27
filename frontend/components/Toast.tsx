'use client';

import { useEffect, useState } from 'react';
import { CheckCircle, XCircle, Info } from 'lucide-react';

type ToastType = 'success' | 'error' | 'info';
interface ToastItem {
  id: number;
  type: ToastType;
  message: string;
  closing: boolean;
}

let _nextId = 0;
let _listeners: ((toasts: ToastItem[]) => void) | null = null;
let _toasts: ToastItem[] = [];

function notify() {
  _listeners?.([..._toasts]);
}

export function toast(message: string, type: ToastType = 'info') {
  const id = _nextId++;
  _toasts = [..._toasts, { id, type, message, closing: false }];
  notify();
  setTimeout(() => {
    _toasts = _toasts.map((t) => (t.id === id ? { ...t, closing: true } : t));
    notify();
    setTimeout(() => {
      _toasts = _toasts.filter((t) => t.id !== id);
      notify();
    }, 200);
  }, 3500);
}

const iconMap: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle className="w-4 h-4" />,
  error: <XCircle className="w-4 h-4" />,
  info: <Info className="w-4 h-4" />,
};
const styleMap: Record<ToastType, React.CSSProperties> = {
  success: { background: 'var(--c-success)', color: '#fff' },
  error: { background: 'var(--c-error)', color: '#fff' },
  info: { background: 'var(--c-text)', color: 'var(--c-bg)' },
};

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  useEffect(() => {
    _listeners = setToasts;
    return () => {
      _listeners = null;
    };
  }, []);
  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`pointer-events-auto flex items-center gap-2.5 px-4 py-3 rounded-xl text-sm shadow-lg ${t.closing ? 'animate-toast-out' : 'animate-toast-in'}`}
          style={{ ...styleMap[t.type], minWidth: 240, maxWidth: 400 }}
        >
          <span className="shrink-0">{iconMap[t.type]}</span>
          <span className="flex-1">{t.message}</span>
        </div>
      ))}
    </div>
  );
}
