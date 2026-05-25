'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useStore } from '@/lib/store';
import { api } from '@/lib/api';
import Sidebar from '@/components/Sidebar';

export default function MainLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { token, hydrate, conversations, setConversations } = useStore();

  useEffect(() => {
    hydrate();
  }, []);

  useEffect(() => {
    if (!useStore.getState().token) {
      router.replace('/login');
    }
  }, [token]);

  // 公共数据只获取一次
  useEffect(() => {
    if (!token) return;
    if (conversations.length === 0) {
      api
        .get<any[]>('/chat/conversations')
        .then((items) => setConversations(Array.isArray(items) ? items : []))
        .catch((e) => console.error('加载对话列表失败', e));
    }
  }, [token]);

  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 overflow-hidden">{children}</div>
    </div>
  );
}
