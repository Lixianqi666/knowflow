import type { Metadata } from 'next';
import './globals.css';
import { ToastContainer } from '@/components/Toast';

export const metadata: Metadata = {
  title: 'KnowFlow - 企业知识库',
  description: '企业内部知识库智能问答',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="bg-gray-50 min-h-screen">
        {children}
        <ToastContainer />
      </body>
    </html>
  );
}
