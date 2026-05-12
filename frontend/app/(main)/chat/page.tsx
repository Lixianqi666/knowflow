'use client';

import { useEffect } from 'react';
import { useStore } from '@/lib/store';
import ChatWindow from '@/components/ChatWindow';

export default function ChatPage() {
  const { setCurrentConvId } = useStore();

  useEffect(() => {
    setCurrentConvId(null);
  }, []);

  return (
    <div className="flex flex-col h-full pl-10 md:pl-0">
      <ChatWindow />
    </div>
  );
}
