import type { Metadata, Viewport } from 'next';
import './globals.css';
import { ToastContainer } from '@/components/Toast';

export const metadata: Metadata = {
  title: 'KnowFlow - 企业知识库',
  description: '企业内部知识库智能问答系统。上传文档，基于 AI 进行智能检索与对话。',
  icons: {
    icon: '/icon.svg',
    apple: '/apple-icon.svg',
  },
  openGraph: {
    title: 'KnowFlow - 企业知识库',
    description: '企业内部知识库智能问答系统',
    type: 'website',
    siteName: 'KnowFlow',
  },
  appleWebApp: {
    capable: true,
    title: 'KnowFlow',
    statusBarStyle: 'default',
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(()=>{try{const t=localStorage.getItem('theme')||'system';const d=t==='system'?matchMedia('(prefers-color-scheme:dark)').matches:t==='dark';document.documentElement.setAttribute('data-theme',d?'dark':'light')}catch{}})()`,
          }}
        />
      </head>
      <body className="antialiased min-h-screen bg-[var(--c-bg)] text-[var(--c-text)]">
        {children}
        <ToastContainer />
      </body>
    </html>
  );
}
