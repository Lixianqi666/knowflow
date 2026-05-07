import { useStore } from './store';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

class ApiClient {
  private token: string | null = null;

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

  async post<T>(path: string, body?: unknown): Promise<T> {
    const res = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: this.headers(),
      body: body ? JSON.stringify(body) : undefined,
    });
    if (res.status === 401) {
      this.handleUnauthorized();
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '请求失败' }));
      throw new Error(err.detail || '请求失败');
    }
    return res.json();
  }

  async get<T>(path: string): Promise<T> {
    const res = await fetch(`${API_URL}${path}`, { headers: this.headers() });
    if (res.status === 401) {
      this.handleUnauthorized();
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '请求失败' }));
      throw new Error(err.detail || '请求失败');
    }
    return res.json();
  }

  upload(file: File, kbId?: string, onProgress?: (percent: number) => void): Promise<any> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const url = kbId
        ? `${API_URL}/documents/upload?kb_id=${kbId}`
        : `${API_URL}/documents/upload`;
      xhr.open('POST', url);
      const token = this.getToken();
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      };

      xhr.onload = () => {
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
    });
  }

  async patch<T>(path: string, body?: unknown): Promise<T> {
    const res = await fetch(`${API_URL}${path}`, {
      method: 'PATCH',
      headers: this.headers(),
      body: body ? JSON.stringify(body) : undefined,
    });
    if (res.status === 401) {
      this.handleUnauthorized();
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '请求失败' }));
      throw new Error(err.detail || '请求失败');
    }
    return res.json();
  }

  async put<T>(path: string, body?: unknown): Promise<T> {
    const res = await fetch(`${API_URL}${path}`, {
      method: 'PUT',
      headers: this.headers(),
      body: body ? JSON.stringify(body) : undefined,
    });
    if (res.status === 401) {
      this.handleUnauthorized();
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '请求失败' }));
      throw new Error(err.detail || '请求失败');
    }
    return res.json();
  }

  async delete<T>(path: string): Promise<T> {
    const res = await fetch(`${API_URL}${path}`, {
      method: 'DELETE',
      headers: this.headers(),
    });
    if (res.status === 401) {
      this.handleUnauthorized();
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '删除失败' }));
      throw new Error(err.detail || '删除失败');
    }
    return res.json();
  }

  async download(path: string): Promise<Blob> {
    const res = await fetch(`${API_URL}${path}`, { headers: this.headers() });
    if (res.status === 401) {
      this.handleUnauthorized();
    }
    if (!res.ok) throw new Error('下载失败');
    return res.blob();
  }

  async streamChat(
    convId: string,
    content: string,
    signal?: AbortSignal,
    templateId?: string,
  ): Promise<ReadableStream> {
    const res = await fetch(`${API_URL}/chat/conversations/${convId}/messages`, {
      method: 'POST',
      headers: this.headers(),
      signal,
      body: JSON.stringify({ content, template_id: templateId }),
    });
    if (res.status === 401) {
      this.handleUnauthorized();
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '请求失败' }));
      throw new Error(err.detail || '请求失败');
    }
    return res.body!;
  }
}

export const api = new ApiClient();
