import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'KnowFlow - 企业知识库',
    short_name: 'KnowFlow',
    description: '企业内部知识库智能问答系统',
    start_url: '/chat',
    display: 'standalone',
    background_color: '#f6f7f9',
    theme_color: '#2563eb',
    icons: [{ src: '/icon.svg', sizes: 'any', type: 'image/svg+xml' }],
  };
}
