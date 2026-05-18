'use client';

import { ReactNode, useEffect, useState } from 'react';

interface Props {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer: ReactNode;
  maxWidth?: string;
}

export default function FormModal({
  open,
  title,
  onClose,
  children,
  footer,
  maxWidth = 'max-w-2xl',
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
      onClose();
    }, 150);
  };

  if (!visible) return null;

  const bgClass = closing ? 'animate-fade-out' : 'animate-fade-in';
  const cardClass = closing ? 'animate-scale-out' : 'animate-scale-in';

  return (
    <div
      className={`fixed inset-0 bg-black/50 flex items-center justify-center z-50 ${bgClass}`}
      onClick={close}
    >
      <div
        className={`bg-white rounded-xl w-full ${maxWidth} max-h-[85vh] flex flex-col mx-4 ${cardClass}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b shrink-0">
          <h3 className="font-semibold">{title}</h3>
          <button onClick={close} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        </div>
        <div className="p-4 overflow-y-auto flex-1 space-y-3">{children}</div>
        <div className="p-4 border-t flex justify-end gap-2">{footer}</div>
      </div>
    </div>
  );
}
