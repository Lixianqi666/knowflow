'use client';

import { useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useStore } from '@/lib/store';
import ChatWindow from '@/components/ChatWindow';

export default function ConversationPage() {
  const params = useParams();
  const convId = params.conversationId as string;
  const { setCurrentConvId } = useStore();

  useEffect(() => {
    setCurrentConvId(convId);
  }, [convId]);

  return (
    <div className="flex flex-col h-full pl-10 md:pl-0">
      <ChatWindow />
    </div>
  );
}
