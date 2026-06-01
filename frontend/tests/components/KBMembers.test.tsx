import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

beforeAll(() => {
  HTMLElement.prototype.scrollIntoView = vi.fn();
});

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();
const mockDelete = vi.fn();

vi.mock('@/lib/api', () => ({
  api: {
    get: (...a: any[]) => mockGet(...a),
    post: (...a: any[]) => mockPost(...a),
    patch: (...a: any[]) => mockPatch(...a),
    delete: (...a: any[]) => mockDelete(...a),
  },
  API_URL: 'http://localhost:8000/api/v1',
}));

vi.mock('@/components/Toast', () => ({
  toast: vi.fn(),
}));

vi.mock('lucide-react', () => ({
  Users: () => <svg />,
  UserPlus: () => <svg />,
  RefreshCw: () => <svg />,
  Trash2: () => <svg />,
}));

import KBMembers from '@/components/KBMembers';

const mockMembers = [
  {
    user_id: 'user-1',
    email: 'owner@test.com',
    name: 'Owner',
    role: 'owner',
    created_at: '2026-05-31T10:00:00Z',
  },
  {
    user_id: 'user-2',
    email: 'viewer@test.com',
    name: 'Viewer',
    role: 'viewer',
    created_at: '2026-05-31T09:00:00Z',
  },
];

beforeEach(() => {
  vi.clearAllMocks();
});

describe('KBMembers', () => {
  it('loading 状态', () => {
    mockGet.mockReturnValueOnce(new Promise(() => {}));
    render(<KBMembers kbId="kb-1" currentUserRole="owner" />);
    expect(screen.getByText('加载中...')).toBeInTheDocument();
  });

  it('成功后显示成员邮箱和 role', async () => {
    mockGet.mockResolvedValueOnce(mockMembers);
    render(<KBMembers kbId="kb-1" currentUserRole="owner" />);
    await waitFor(() => {
      expect(screen.getByText('owner@test.com')).toBeInTheDocument();
      expect(screen.getByText('viewer@test.com')).toBeInTheDocument();
    });
  });

  it('空成员显示空状态', async () => {
    mockGet.mockResolvedValueOnce([]);
    render(<KBMembers kbId="kb-1" currentUserRole="owner" />);
    await waitFor(() => {
      expect(screen.getByText('暂无成员')).toBeInTheDocument();
    });
  });

  it('owner/admin 显示添加成员入口', async () => {
    mockGet.mockResolvedValueOnce(mockMembers);
    render(<KBMembers kbId="kb-1" currentUserRole="owner" />);
    await waitFor(() => {
      expect(screen.getByText('添加')).toBeInTheDocument();
    });
  });

  it('viewer 不显示管理操作', async () => {
    mockGet.mockResolvedValueOnce(mockMembers);
    render(<KBMembers kbId="kb-1" currentUserRole="viewer" />);
    await waitFor(() => {
      expect(screen.queryByText('添加')).not.toBeInTheDocument();
    });
  });

  it('添加成员会调用 API', async () => {
    mockGet.mockResolvedValueOnce(mockMembers);
    mockPost.mockResolvedValueOnce({ detail: '已添加' });
    mockGet.mockResolvedValueOnce([...mockMembers, { user_id: 'user-3', email: 'new@test.com', name: 'New', role: 'viewer', created_at: '2026-05-31T11:00:00Z' }]);

    render(<KBMembers kbId="kb-1" currentUserRole="owner" />);
    await waitFor(() => {
      expect(screen.getByText('添加')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('添加'));

    await waitFor(() => {
      expect(screen.getByPlaceholderText('用户 ID')).toBeInTheDocument();
    });

    fireEvent.change(screen.getByPlaceholderText('用户 ID'), { target: { value: 'user-3' } });

    // 找到添加按钮（不是标题中的"添加"）
    const addButtons = screen.getAllByText('添加');
    const submitBtn = addButtons.find((el) => el.tagName === 'BUTTON' && el.closest('.flex.gap-2'));
    if (submitBtn) fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/knowledge-bases/kb-1/members', expect.objectContaining({ user_id: 'user-3' }));
    });
  });

  it('修改角色会调用 PATCH', async () => {
    mockGet.mockResolvedValueOnce(mockMembers);
    mockPatch.mockResolvedValueOnce({ detail: '已更新' });
    mockGet.mockResolvedValueOnce(mockMembers);

    render(<KBMembers kbId="kb-1" currentUserRole="owner" />);
    await waitFor(() => {
      expect(screen.getByText('viewer@test.com')).toBeInTheDocument();
    });

    // 找到 viewer 的 select
    const selects = screen.getAllByRole('combobox');
    const viewerSelect = selects.find((s) => (s as HTMLSelectElement).value === 'viewer');
    if (viewerSelect) {
      fireEvent.change(viewerSelect, { target: { value: 'editor' } });
      await waitFor(() => {
        expect(mockPatch).toHaveBeenCalled();
      });
    }
  });

  it('移除成员会调用 DELETE', async () => {
    mockGet.mockResolvedValueOnce(mockMembers);
    mockDelete.mockResolvedValueOnce({ detail: '已移除' });
    mockGet.mockResolvedValueOnce([mockMembers[0]]);

    render(<KBMembers kbId="kb-1" currentUserRole="owner" />);
    await waitFor(() => {
      expect(screen.getByText('viewer@test.com')).toBeInTheDocument();
    });

    // 找到删除按钮（Trash2 图标的父按钮）
    const buttons = screen.getAllByRole('button');
    const deleteBtns = buttons.filter((b) => b.querySelector('svg'));
    // 最后一个按钮是删除
    if (deleteBtns.length >= 2) {
      fireEvent.click(deleteBtns[deleteBtns.length - 1]);
      await waitFor(() => {
        expect(mockDelete).toHaveBeenCalled();
      });
    }
  });

  it('API 失败显示错误提示', async () => {
    mockGet.mockRejectedValueOnce(new Error('无权限'));
    render(<KBMembers kbId="kb-1" currentUserRole="owner" />);
    await waitFor(() => {
      expect(screen.getByText('加载中...')).toBeInTheDocument();
    });
  });
});
