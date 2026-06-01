import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

beforeAll(() => {
  HTMLElement.prototype.scrollIntoView = vi.fn();
});

const mockGet = vi.fn();

vi.mock('@/lib/api', () => ({
  api: {
    get: (...a: any[]) => mockGet(...a),
  },
  API_URL: 'http://localhost:8000/api/v1',
}));

vi.mock('lucide-react', () => ({
  RefreshCw: () => <svg />,
  Shield: () => <svg />,
}));

import AuditTab from '@/components/AuditTab';

const mockAuditData = {
  items: [
    {
      id: 'log-1',
      actor_email: 'admin@test.com',
      action: 'auth.login.success',
      resource_type: null,
      resource_id: null,
      status: 'success',
      ip: '127.0.0.1',
      metadata: {},
      created_at: '2026-05-31T10:00:00Z',
    },
    {
      id: 'log-2',
      actor_email: 'user@test.com',
      action: 'document.upload',
      resource_type: 'document',
      resource_id: 'doc-123',
      status: 'success',
      ip: '192.168.1.1',
      metadata: { title: 'test.txt' },
      created_at: '2026-05-31T09:00:00Z',
    },
  ],
  total: 2,
  limit: 50,
  offset: 0,
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('AuditTab', () => {
  it('渲染 loading 状态', () => {
    mockGet.mockReturnValueOnce(new Promise(() => {}));
    render(<AuditTab />);
    expect(screen.getByText('加载中...')).toBeInTheDocument();
  });

  it('成功后显示审计事件列表', async () => {
    mockGet.mockResolvedValueOnce(mockAuditData);
    render(<AuditTab />);
    await waitFor(() => {
      expect(screen.getByText('admin@test.com')).toBeInTheDocument();
    });
  });

  it('显示 action', async () => {
    mockGet.mockResolvedValueOnce(mockAuditData);
    render(<AuditTab />);
    await waitFor(() => {
      // action 以 font-mono 显示
      const actionElements = screen.getAllByText(/auth\.login\.success|document\.upload/);
      expect(actionElements.length).toBeGreaterThan(0);
    });
  });

  it('显示 status', async () => {
    mockGet.mockResolvedValueOnce(mockAuditData);
    render(<AuditTab />);
    await waitFor(() => {
      const successElements = screen.getAllByText('success');
      expect(successElements.length).toBeGreaterThan(0);
    });
  });

  it('空数据时显示空状态', async () => {
    mockGet.mockResolvedValueOnce({ items: [], total: 0, limit: 50, offset: 0 });
    render(<AuditTab />);
    await waitFor(() => {
      expect(screen.getByText('暂无审计日志')).toBeInTheDocument();
    });
  });

  it('API 失败时显示错误提示', async () => {
    mockGet.mockRejectedValueOnce(new Error('网络错误'));
    render(<AuditTab />);
    await waitFor(() => {
      expect(screen.getByText('网络错误')).toBeInTheDocument();
    });
  });

  it('403 时显示无权限提示', async () => {
    mockGet.mockRejectedValueOnce(new Error('无权限'));
    render(<AuditTab />);
    await waitFor(() => {
      expect(screen.getByText('无权限')).toBeInTheDocument();
    });
  });

  it('action 过滤会调用带 query 的 API', async () => {
    mockGet.mockResolvedValue(mockAuditData);
    render(<AuditTab />);
    await waitFor(() => {
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByRole('combobox'), {
      target: { value: 'auth.login.success' },
    });

    await waitFor(() => {
      const calls = mockGet.mock.calls;
      const lastCall = calls[calls.length - 1][0];
      expect(lastCall).toContain('action=auth.login.success');
    });
  });
});
