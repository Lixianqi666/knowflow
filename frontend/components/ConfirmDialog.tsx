'use client';

import { useEffect, useState } from 'react';

interface Props {
  open: boolean;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmText = '确定',
  cancelText = '取消',
  danger = false,
  onConfirm,
  onCancel,
}: Props) {
  const [closing, setClosing] = useState(false);
  const [visible, setVisible] = useState(open);

  useEffect(() => {
    if (open) {
      setVisible(true);
      setClosing(false);
    }
  }, [open]);

  const close = () => {
    setClosing(true);
    setTimeout(() => {
      setVisible(false);
      setClosing(false);
      onCancel();
    }, 150);
  };

  if (!visible) return null;

  const bgClass = closing ? 'animate-fade-out' : 'animate-fade-in';
  const cardClass = closing ? 'animate-scale-out' : 'animate-scale-in';

  return (
    <div
      className={`fixed inset-0 bg-black/50 flex items-center justify-center z-[90] ${bgClass}`}
      onClick={close}
    >
      <div
        className={`bg-white rounded-xl p-6 w-full max-w-sm mx-4 ${cardClass}`}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold mb-2">{title}</h3>
        <p className="text-sm text-gray-500 mb-6">{message}</p>
        <div className="flex justify-end gap-2">
          <button
            onClick={close}
            className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg text-sm"
          >
            {cancelText}
          </button>
          <button
            onClick={() => {
              setClosing(true);
              setTimeout(() => {
                setVisible(false);
                setClosing(false);
                onConfirm();
              }, 150);
            }}
            className={`px-4 py-2 rounded-lg text-sm text-white ${
              danger ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'
            }`}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
