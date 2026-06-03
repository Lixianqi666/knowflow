import { useStore } from './store';

export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class ApiClient {
  private token: string | null = null;
  private refreshing: Promise<string | null> | null = null;

  /** 清理本地 token 状态，不调用后端 logout */
  private handleUnauthorized() {
    this.clearToken();
    useStore.getState().logout();
  }

  setToken(token: string) {
    this.token = token;
    if (typeof window !== 'undefined') {
      localStorage.setItem('token', token);
    }
  }

  getToken(): string | null {
    if (!this.token && typeof window !== 'undefined') {
      this.token = localStorage.getItem('token');
    }
    return this.token;
  }

  clearToken() {
    this.token = null;
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token');
    }
  }

  private headers(): HeadersInit {
    const h: HeadersInit = { 'Content-Type': 'application/json' };
    const token = this.getToken();
    if (token) h['Authorization'] = `Bearer ${token}`;
    return h;
  }

  /**
   * 尝试用 refresh token 续期 access token。
   * 并发请求共享同一个 refresh Promise，避免重复刷新。
   */
  private async tryRefresh(): Promise<string | null> {
    if (this.refreshing) return this.refreshing;
    this.refreshing = this._doRefresh();
    try {
      return await this.refreshing;
    } finally {
      this.refreshing = null;
    }
  }

  private async _doRefresh(): Promise<string | null> {
    try {
      const res = await fetch(`${API_URL}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      });
      if (!res.ok) return null;
      const data = await res.json();
      this.setToken(data.access_token);
      return data.access_token;
    } catch {
      return null;
    }
  }

  /**
   * 包装 fetch，401 时自动 refresh 并重试一次。
   */
  private async fetchWithRefresh(
    url: string,
    init: RequestInit,
    retried = false,
  ): Promise<Response> {
    const res = await fetch(url, init);
    if (res.status === 401 && !retried) {
      const newToken = await this.tryRefresh();
      if (newToken) {
        const retryInit = { ...init };
        retryInit.headers = {
          ...((retryInit.headers as Record<string, string>) || {}),
          Authorization: `Bearer ${newToken}`,
        };
        return fetch(url, retryInit);
      }
      this.handleUnauthorized();
    }
    return res;
  }

  async post<T>(path: string, body?: unknown): Promise<T> {
    const res = await this.fetchWithRefresh(`${API_URL}${path}`, {
      method: 'POST',
      headers: this.headers(),
      body: body ? JSON.stringify(body) : undefined,
      credentials: 'include',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '请求失败' }));
      throw new Error(err.detail || '请求失败');
    }
    return res.json();
  }

  async get<T>(path: string): Promise<T> {
    const res = await this.fetchWithRefresh(`${API_URL}${path}`, {
      headers: this.headers(),
      credentials: 'include',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '请求失败' }));
      throw new Error(err.detail || '请求失败');
    }
    return res.json();
  }

  upload(file: File, kbId?: string, onProgress?: (percent: number) => void): Promise<any> {
    return new Promise((resolve, reject) => {
      const doUpload = (token: string | null, retried = false) => {
        const xhr = new XMLHttpRequest();
        const url = kbId
          ? `${API_URL}/documents/upload?kb_id=${kbId}`
          : `${API_URL}/documents/upload`;
        xhr.open('POST', url);
        xhr.withCredentials = true;
        if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);

        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable && onProgress) {
            onProgress(Math.round((e.loaded / e.total) * 100));
          }
        };

        xhr.onload = async () => {
          if (xhr.status === 401 && !retried) {
            const newToken = await this.tryRefresh();
            if (newToken) {
              doUpload(newToken, true);
              return;
            }
            this.handleUnauthorized();
            reject(new Error('认证已过期'));
            return;
          }
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(JSON.parse(xhr.responseText));
          } else {
            try {
              const err = JSON.parse(xhr.responseText);
              reject(new Error(err.detail || '上传失败'));
            } catch {
              reject(new Error('上传失败'));
            }
          }
        };

        xhr.onerror = () => reject(new Error('网络错误'));
        xhr.ontimeout = () => reject(new Error('上传超时'));
        xhr.timeout = 120_000;

        const form = new FormData();
        form.append('file', file);
        xhr.send(form);
      };

      doUpload(this.getToken());
    });
  }

  async patch<T>(path: string, body?: unknown): Promise<T> {
    const res = await this.fetchWithRefresh(`${API_URL}${path}`, {
      method: 'PATCH',
      headers: this.headers(),
      body: body ? JSON.stringify(body) : undefined,
      credentials: 'include',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '请求失败' }));
      throw new Error(err.detail || '请求失败');
    }
    return res.json();
  }

  async put<T>(path: string, body?: unknown): Promise<T> {
    const res = await this.fetchWithRefresh(`${API_URL}${path}`, {
      method: 'PUT',
      headers: this.headers(),
      body: body ? JSON.stringify(body) : undefined,
      credentials: 'include',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '请求失败' }));
      throw new Error(err.detail || '请求失败');
    }
    return res.json();
  }

  async delete<T>(path: string): Promise<T> {
    const res = await this.fetchWithRefresh(`${API_URL}${path}`, {
      method: 'DELETE',
      headers: this.headers(),
      credentials: 'include',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '删除失败' }));
      throw new Error(err.detail || '删除失败');
    }
    return res.json();
  }

  async download(path: string): Promise<Blob> {
    const res = await this.fetchWithRefresh(`${API_URL}${path}`, {
      headers: this.headers(),
      credentials: 'include',
    });
    if (!res.ok) throw new Error('下载失败');
    return res.blob();
  }

  async streamChat(
    convId: string,
    content: string,
    signal?: AbortSignal,
    templateId?: string,
    goal?: string,
  ): Promise<ReadableStream> {
    const res = await this.fetchWithRefresh(`${API_URL}/chat/conversations/${convId}/messages`, {
      method: 'POST',
      headers: this.headers(),
      signal,
      body: JSON.stringify({ content, template_id: templateId, goal }),
      credentials: 'include',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '请求失败' }));
      throw new Error(err.detail || '请求失败');
    }
    if (!res.body) throw new Error('响应体为空');
    return res.body;
  }

  async streamPost(path: string, body: unknown, signal?: AbortSignal): Promise<Response> {
    const res = await this.fetchWithRefresh(
      `${API_URL}${path}`,
      {
        method: 'POST',
        headers: this.headers(),
        body: JSON.stringify(body),
        signal,
        credentials: 'include',
      },
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '请求失败' }));
      throw new Error(err.detail || '请求失败');
    }
    return res;
  }

  async logout(): Promise<void> {
    try {
      await fetch(`${API_URL}/auth/logout`, {
        method: 'POST',
        headers: this.headers(),
        credentials: 'include',
      });
    } catch {
      // 即使失败也要继续
    }
  }
}

export const api = new ApiClient();
