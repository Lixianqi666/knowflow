'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useStore } from '@/lib/store';
import { api } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import ChatWindow from '@/components/ChatWindow';

export default function ChatPage() {
  const router = useRouter();
  const { token, hydrate, setConversations, setMessages, setCurrentConvId } = useStore();

  useEffect(() => {
    hydrate();
  }, []);

  useEffect(() => {
    const t = useStore.getState().token;
    if (!t) {
      router.replace('/login');
      return;
    }
    api
      .get<any[]>('/chat/conversations')
      .then((items) => setConversations(Array.isArray(items) ? items : []))
      .catch(() => {});
    setCurrentConvId(null);
    setMessages([]);
  }, [token]);

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col pl-10 md:pl-0">
        <ChatWindow />
      </div>
    </div>
  );
}
