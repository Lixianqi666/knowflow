'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { useStore } from '@/lib/store';

interface SSOProvider {
  id: string;
  name: string;
  enabled: boolean;
  login_url: string | null;
}

export default function LoginPage() {
  const router = useRouter();
  const setAuth = useStore((s) => s.setAuth);
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [ssoProviders, setSsoProviders] = useState<SSOProvider[]>([]);

  useEffect(() => {
    api
      .get<{ providers: SSOProvider[] }>('/auth/sso/providers')
      .then((data) => setSsoProviders(data.providers || []))
      .catch(() => {});
  }, []);

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
      {/* Left brand */}
      <div className="hidden lg:flex lg:w-1/2 brand-gradient text-white p-12 flex-col justify-center relative overflow-hidden">
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full bg-white/5" />
          <div className="absolute -bottom-40 -left-40 w-[500px] h-[500px] rounded-full bg-white/5" />
          <svg className="absolute inset-0 w-full h-full opacity-[0.04]">
            <defs>
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="white" strokeWidth="0.5" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid)" />
          </svg>
        </div>
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-10">
            <svg width="40" height="40" viewBox="0 0 100 100" className="shrink-0">
              <rect width="100" height="100" rx="20" fill="rgba(255,255,255,.15)" />
              <path
                d="M30 25v50M30 50l22-25M30 50l22 25"
                stroke="white"
                strokeWidth="7"
                strokeLinecap="round"
                strokeLinejoin="round"
                fill="none"
              />
              <circle cx="68" cy="35" r="3.5" fill="white" opacity="0.7" />
              <circle cx="68" cy="65" r="3.5" fill="white" opacity="0.7" />
            </svg>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">KnowFlow</h1>
              <p className="text-sm text-blue-200/80">企业知识库</p>
            </div>
          </div>
          <div className="space-y-6">
            {[
              { icon: '📄', text: '支持 txt / md / pdf / docx / xlsx 多格式文档' },
              { icon: '🔍', text: '基于 RAG 的精准检索，回答有据可依' },
              { icon: '⚡', text: '流式输出，实时查看生成过程' },
              { icon: '🔒', text: '企业级权限管理，数据安全可控' },
            ].map((item, i) => (
              <div
                key={item.text}
                className="flex items-center gap-3 animate-slide-up"
                style={{ animationDelay: `${i * 80}ms` }}
              >
                <span className="text-2xl w-10 h-10 flex items-center justify-center rounded-xl bg-white/10">
                  {item.icon}
                </span>
                <span className="text-blue-50 text-sm">{item.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm animate-slide-up">
          <div className="lg:hidden mb-8 flex items-center gap-3">
            <svg width="32" height="32" viewBox="0 0 100 100">
              <rect width="100" height="100" rx="20" fill="#2563eb" />
              <path
                d="M30 25v50M30 50l22-25M30 50l22 25"
                stroke="white"
                strokeWidth="7"
                strokeLinecap="round"
                strokeLinejoin="round"
                fill="none"
              />
              <circle cx="68" cy="35" r="3.5" fill="white" opacity="0.7" />
              <circle cx="68" cy="65" r="3.5" fill="white" opacity="0.7" />
            </svg>
            <div>
              <h1 className="text-lg font-bold">KnowFlow</h1>
              <p className="text-xs" style={{ color: 'var(--c-text-tertiary)' }}>
                企业知识库
              </p>
            </div>
          </div>
          <h2 className="text-2xl font-bold mb-1 tracking-tight">
            {isRegister ? '创建账号' : '欢迎回来'}
          </h2>
          <p className="text-sm mb-8" style={{ color: 'var(--c-text-secondary)' }}>
            {isRegister ? '注册后即可使用知识库问答' : '登录以继续使用 KnowFlow'}
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <div>
                <label className="block text-sm font-medium mb-1.5">姓名</label>
                <input
                  type="text"
                  placeholder="请输入姓名"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl border input-base"
                  style={{
                    background: 'var(--c-surface)',
                    borderColor: 'var(--c-border)',
                    color: 'var(--c-text)',
                  }}
                  required
                />
              </div>
            )}
            <div>
              <label className="block text-sm font-medium mb-1.5">邮箱</label>
              <input
                type="email"
                placeholder="请输入邮箱"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl border input-base"
                style={{
                  background: 'var(--c-surface)',
                  borderColor: 'var(--c-border)',
                  color: 'var(--c-text)',
                }}
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">密码</label>
              <input
                type="password"
                placeholder="请输入密码"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl border input-base"
                style={{
                  background: 'var(--c-surface)',
                  borderColor: 'var(--c-border)',
                  color: 'var(--c-text)',
                }}
                required
              />
            </div>

            {error && (
              <div
                className="px-4 py-2.5 rounded-xl text-sm"
                style={{
                  background: 'var(--c-error-subtle)',
                  color: 'var(--c-error)',
                  border: '1px solid rgba(220,38,38,.15)',
                }}
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full py-2.5 text-base"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="3"
                      opacity="0.25"
                    />
                    <path
                      d="M12 2a10 10 0 0 1 10 10"
                      stroke="currentColor"
                      strokeWidth="3"
                      strokeLinecap="round"
                    />
                  </svg>
                  处理中...
                </span>
              ) : isRegister ? (
                '注册'
              ) : (
                '登录'
              )}
            </button>
          </form>

          <p className="text-center mt-6 text-sm" style={{ color: 'var(--c-text-secondary)' }}>
            {isRegister ? '已有账号？' : '没有账号？'}
            <button
              onClick={() => {
                setIsRegister(!isRegister);
                setError('');
              }}
              className="ml-1 font-medium hover:underline border-none cursor-pointer"
              style={{ color: 'var(--c-primary)', background: 'none' }}
            >
              {isRegister ? '去登录' : '去注册'}
            </button>
          </p>

          {/* SSO 预留 */}
          {!isRegister && ssoProviders.length > 0 && (
            <div className="mt-6">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t" style={{ borderColor: 'var(--c-border)' }} />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="px-2" style={{ background: 'var(--c-bg)', color: 'var(--c-text-tertiary)' }}>
                    或
                  </span>
                </div>
              </div>
              <div className="mt-4 space-y-2">
                {ssoProviders.map((p) =>
                  p.enabled ? (
                    <a
                      key={p.id}
                      href={p.login_url || '#'}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border text-sm transition-all"
                      style={{ borderColor: 'var(--c-border)', color: 'var(--c-text-secondary)' }}
                    >
                      使用 {p.name} 登录
                    </a>
                  ) : (
                    <div
                      key={p.id}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl border text-xs"
                      style={{ borderColor: 'var(--c-border)', color: 'var(--c-text-tertiary)', opacity: 0.6 }}
                    >
                      企业登录（{p.name}）未配置
                    </div>
                  ),
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
