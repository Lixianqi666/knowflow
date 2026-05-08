'use client';

import { useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useStore } from '@/lib/store';
import { api } from '@/lib/api';
import Sidebar from '@/components/Sidebar';
import ChatWindow from '@/components/ChatWindow';

export default function ConversationPage() {
  const router = useRouter();
  const params = useParams();
  const convId = params.conversationId as string;
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
    setCurrentConvId(convId);
    api
      .get<any[]>('/chat/conversations')
      .then(setConversations)
      .catch(() => {});
  }, [token, convId]);

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col pl-10 md:pl-0">
        <ChatWindow />
      </div>
    </div>
  );
}
