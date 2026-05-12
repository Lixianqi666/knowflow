'use client';

import { useEffect } from 'react';
import { useStore } from '@/lib/store';
import { api } from '@/lib/api';
import ChatWindow from '@/components/ChatWindow';

export default function ChatPage() {
  const { token, setConversations, setCurrentConvId } = useStore();

  useEffect(() => {
    if (!token) return;
    api
      .get<any[]>('/chat/conversations')
      .then((items) => setConversations(Array.isArray(items) ? items : []))
      .catch(() => {});
    setCurrentConvId(null);
  }, [token]);

  return (
    <div className="flex flex-col h-full pl-10 md:pl-0">
      <ChatWindow />
    </div>
  );
}
