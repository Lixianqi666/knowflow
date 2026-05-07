'use client';

import { useEffect, useState, useCallback } from 'react';

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
  }, 3000);
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  useEffect(() => {
    _listeners = setToasts;
    return () => {
      _listeners = null;
    };
  }, []);

  if (toasts.length === 0) return null;

  const colorMap: Record<ToastType, string> = {
    success: 'bg-green-600',
    error: 'bg-red-600',
    info: 'bg-gray-800',
  };
  const iconMap: Record<ToastType, string> = {
    success: '✓',
    error: '✕',
    info: 'i',
  };

  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`pointer-events-auto flex items-center gap-2 px-4 py-3 rounded-lg text-white text-sm shadow-lg ${colorMap[t.type]} ${
            t.closing ? 'animate-toast-out' : 'animate-toast-in'
          }`}
        >
          <span className="font-bold text-base">{iconMap[t.type]}</span>
          <span>{t.message}</span>
        </div>
      ))}
    </div>
  );
}
