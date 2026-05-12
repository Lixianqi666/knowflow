'use client';

import { useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useStore } from '@/lib/store';
import { api } from '@/lib/api';
import ChatWindow from '@/components/ChatWindow';

export default function ConversationPage() {
  const params = useParams();
  const convId = params.conversationId as string;
  const { token, setConversations, setCurrentConvId } = useStore();

  useEffect(() => {
    if (!token) return;
    setCurrentConvId(convId);
    api
      .get<any[]>('/chat/conversations')
      .then((items) => setConversations(Array.isArray(items) ? items : []))
      .catch(() => {});
  }, [token, convId]);

  return (
    <div className="flex flex-col h-full pl-10 md:pl-0">
      <ChatWindow />
    </div>
  );
}
