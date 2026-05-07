'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useStore } from '@/lib/store';

export default function Home() {
  const router = useRouter();
  const { token, hydrate } = useStore();

  useEffect(() => {
    hydrate();
  }, []);

  useEffect(() => {
    const t = useStore.getState().token;
    router.replace(t ? '/chat' : '/login');
  }, [token, router]);

  return null;
}
