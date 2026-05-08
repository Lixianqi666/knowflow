import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ToastContainer, toast } from '@/components/Toast';

describe('Toast', () => {
  it('无消息时 ToastContainer 返回 null', () => {
    const { container } = render(<ToastContainer />);
    expect(container.innerHTML).toBe('');
  });

  it('调用 toast() 后渲染消息', async () => {
    render(<ToastContainer />);
    toast('测试消息', 'success');

    expect(await screen.findByText('测试消息')).toBeInTheDocument();
  });

  it('多条消息按顺序渲染', async () => {
    render(<ToastContainer />);
    toast('消息A', 'info');
    toast('消息B', 'error');

    expect(await screen.findByText('消息A')).toBeInTheDocument();
    expect(await screen.findByText('消息B')).toBeInTheDocument();
  });
});
