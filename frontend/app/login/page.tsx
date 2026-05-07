'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { useStore } from '@/lib/store';

export default function LoginPage() {
  const router = useRouter();
  const setAuth = useStore((s) => s.setAuth);
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = isRegister
        ? await api.post<any>('/auth/register', { email, name, password })
        : await api.post<any>('/auth/login', { email, password });
      api.setToken(data.access_token);
      setAuth(data.access_token, data.user);
      router.push('/chat');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex">
      {/* 左侧品牌区 */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-blue-600 to-blue-800 text-white p-12 flex-col justify-center relative overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-20 left-20 w-72 h-72 bg-white rounded-full blur-3xl" />
          <div className="absolute bottom-20 right-20 w-96 h-96 bg-blue-300 rounded-full blur-3xl" />
        </div>
        <div className="relative z-10">
          <h1 className="text-4xl font-bold mb-4">KnowFlow</h1>
          <p className="text-xl text-blue-100 mb-10">企业内部知识库智能问答</p>
          <div className="space-y-6">
            {[
              { icon: '📄', text: '支持 txt / md / pdf / docx / xlsx 多格式文档' },
              { icon: '🔍', text: '基于 RAG 的精准检索，回答有据可依' },
              { icon: '⚡', text: '流式输出，实时查看生成过程' },
              { icon: '🔒', text: '企业级权限管理，数据安全可控' },
            ].map((item) => (
              <div key={item.text} className="flex items-center gap-3">
                <span className="text-2xl">{item.icon}</span>
                <span className="text-blue-50">{item.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 右侧表单区 */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="lg:hidden mb-8">
            <h1 className="text-2xl font-bold">KnowFlow</h1>
            <p className="text-gray-500 text-sm mt-1">企业内部知识库</p>
          </div>

          <h2 className="text-2xl font-bold mb-1">{isRegister ? '创建账号' : '欢迎回来'}</h2>
          <p className="text-gray-500 text-sm mb-8">
            {isRegister ? '注册后即可使用知识库问答' : '登录以继续使用 KnowFlow'}
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">姓名</label>
                <input
                  type="text"
                  placeholder="请输入姓名"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">邮箱</label>
              <input
                type="email"
                placeholder="请输入邮箱"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">密码</label>
              <input
                type="password"
                placeholder="请输入密码"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>

            {error && (
              <div className="px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 font-medium"
            >
              {loading ? '处理中...' : isRegister ? '注册' : '登录'}
            </button>
          </form>

          <p className="text-center mt-6 text-sm text-gray-500">
            {isRegister ? '已有账号？' : '没有账号？'}
            <button
              onClick={() => {
                setIsRegister(!isRegister);
                setError('');
              }}
              className="text-blue-600 ml-1 hover:underline font-medium"
            >
              {isRegister ? '去登录' : '去注册'}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
