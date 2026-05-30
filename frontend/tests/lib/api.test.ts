import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// mock store
vi.mock('@/lib/store', () => ({
  useStore: {
    getState: () => ({ logout: vi.fn() }),
  },
}));

import { api } from '@/lib/api';

beforeEach(() => {
  api.clearToken();
  vi.restoreAllMocks();
});

// ---------- fetch 401 refresh retry ----------

describe('ApiClient 401 refresh retry', () => {
  it('401 后调用 /auth/refresh 并重试原请求', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');

    fetchSpy
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'unauthorized' }), { status: 401 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ access_token: 'new_token', user: {} }), { status: 200 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), { status: 200 }),
      );

    api.setToken('old_token');
    const result = await api.get<{ ok: boolean }>('/test');

    expect(fetchSpy).toHaveBeenCalledTimes(3);
    expect(fetchSpy.mock.calls[1][0]).toContain('/auth/refresh');
    const retryHeaders = fetchSpy.mock.calls[2][1]?.headers as Record<string, string>;
    expect(retryHeaders['Authorization']).toBe('Bearer new_token');
    expect(result.ok).toBe(true);
  });

  it('refresh 失败后清理 token', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');

    fetchSpy
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'unauthorized' }), { status: 401 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'invalid' }), { status: 401 }),
      );

    api.setToken('old_token');

    try {
      await api.get('/test');
    } catch {
      // 预期抛出
    }

    expect(api.getToken()).toBeNull();
  });

  it('streamChat 发送时携带 goal 参数', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');

    fetchSpy.mockResolvedValueOnce(
      new Response('ok', { status: 200, headers: { 'content-type': 'text/event-stream' } }),
    );

    api.setToken('tok');
    await api.streamChat('conv1', '你好', undefined, undefined, '制定方案');

    const body = JSON.parse(fetchSpy.mock.calls[0][1]?.body as string);
    expect(body.goal).toBe('制定方案');
    expect(body.content).toBe('你好');
  });

  it('streamPost 401 后会 refresh 并重试一次', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');

    fetchSpy
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'unauthorized' }), { status: 401 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ access_token: 'new_token', user: {} }), { status: 200 }),
      )
      .mockResolvedValueOnce(
        new Response('ok', { status: 200 }),
      );

    api.setToken('old_token');
    const res = await api.streamPost('/test', {});

    expect(fetchSpy).toHaveBeenCalledTimes(3);
    expect(res.status).toBe(200);
  });

  it('401 refresh 失败只清理本地状态，不额外打 /auth/logout', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');

    fetchSpy
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'unauthorized' }), { status: 401 }),
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'invalid' }), { status: 401 }),
      );

    api.setToken('old_token');

    try {
      await api.get('/test');
    } catch {
      // 预期
    }

    const logoutCalls = fetchSpy.mock.calls.filter((c) =>
      String(c[0]).includes('/auth/logout'),
    );
    expect(logoutCalls).toHaveLength(0);
    expect(api.getToken()).toBeNull();
  });
});

// ---------- logout ----------

describe('ApiClient logout', () => {
  it('logout 调用后端 /auth/logout，带 Authorization header', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: '已退出' }), { status: 200 }),
    );

    api.setToken('test_token');
    await api.logout();

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    expect(fetchSpy.mock.calls[0][0]).toContain('/auth/logout');
    const headers = fetchSpy.mock.calls[0][1]?.headers as Record<string, string>;
    expect(headers['Authorization']).toBe('Bearer test_token');
  });

  it('logout 网络失败不抛出，调用方可继续执行', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    fetchSpy.mockRejectedValueOnce(new Error('network error'));

    api.setToken('test_token');
    // logout 不应抛出
    await expect(api.logout()).resolves.toBeUndefined();
  });
});

// ---------- upload ----------

describe('ApiClient upload', () => {
  let xhrInstances: any[] = [];
  let OriginalXHR: any;

  beforeEach(() => {
    xhrInstances = [];
    OriginalXHR = globalThis.XMLHttpRequest;
    (globalThis as any).XMLHttpRequest = class {
      open = vi.fn();
      setRequestHeader = vi.fn();
      send = vi.fn();
      upload = { onprogress: null };
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      ontimeout: (() => void) | null = null;
      timeout = 0;
      withCredentials = false;
      status = 200;
      responseText = '{"id":"1","title":"test.txt","status":"processing"}';
      constructor() {
        xhrInstances.push(this);
      }
    };
  });

  afterEach(() => {
    globalThis.XMLHttpRequest = OriginalXHR;
  });

  it('upload 设置 withCredentials=true', async () => {
    api.setToken('tok');
    const p = api.upload(new File(['content'], 'test.txt'));
    xhrInstances[0].onload!();
    await p;
    expect(xhrInstances[0].withCredentials).toBe(true);
  });

  it('upload 带 Authorization header', async () => {
    api.setToken('my_token');
    const p = api.upload(new File(['content'], 'test.txt'));
    xhrInstances[0].onload!();
    await p;
    expect(xhrInstances[0].setRequestHeader).toHaveBeenCalledWith(
      'Authorization',
      'Bearer my_token',
    );
  });

  it('upload 401 后 refresh 成功会重新发起 XMLHttpRequest', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ access_token: 'refreshed_token' }), { status: 200 }),
    );

    api.setToken('old_token');
    const p = api.upload(new File(['content'], 'test.txt'));

    xhrInstances[0].status = 401;
    xhrInstances[0].onload!();

    await new Promise((r) => setTimeout(r, 50));

    expect(xhrInstances.length).toBe(2);
    expect(xhrInstances[1].setRequestHeader).toHaveBeenCalledWith(
      'Authorization',
      'Bearer refreshed_token',
    );

    xhrInstances[1].status = 200;
    xhrInstances[1].responseText = '{"id":"1","title":"test.txt","status":"processing"}';
    xhrInstances[1].onload!();

    const result = await p;
    expect(result.id).toBe('1');
  });

  it('upload 401 refresh 失败会清理 token', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'invalid' }), { status: 401 }),
    );

    api.setToken('old_token');
    const p = api.upload(new File(['content'], 'test.txt'));

    xhrInstances[0].status = 401;
    xhrInstances[0].onload!();

    await expect(p).rejects.toThrow('认证已过期');
    expect(api.getToken()).toBeNull();
  });

  it('upload 401 只重试一次', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch');
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ access_token: 'refreshed' }), { status: 200 }),
    );

    api.setToken('old_token');
    const p = api.upload(new File(['content'], 'test.txt'));

    xhrInstances[0].status = 401;
    xhrInstances[0].onload!();

    await new Promise((r) => setTimeout(r, 50));

    xhrInstances[1].status = 401;
    xhrInstances[1].onload!();

    await expect(p).rejects.toThrow();
    expect(xhrInstances.length).toBe(2);
  });
});
