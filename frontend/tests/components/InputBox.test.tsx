import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import InputBox from '@/components/InputBox';

describe('InputBox', () => {
  it('渲染输入框和发送按钮', () => {
    render(<InputBox onSend={() => {}} />);
    expect(screen.getByPlaceholderText('基于文档提问...')).toBeInTheDocument();
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('空输入时发送按钮禁用', () => {
    render(<InputBox onSend={() => {}} />);
    const btn = screen.getByRole('button');
    expect(btn).toBeDisabled();
  });

  it('输入内容后点击发送调用 onSend', async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<InputBox onSend={onSend} />);

    const textarea = screen.getByPlaceholderText('基于文档提问...');
    await user.type(textarea, '你好');
    await user.click(screen.getByRole('button'));

    expect(onSend).toHaveBeenCalledWith('你好');
  });

  it('按 Enter 触发发送（非 Shift+Enter）', async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<InputBox onSend={onSend} />);

    const textarea = screen.getByPlaceholderText('基于文档提问...');
    await user.type(textarea, '测试消息');
    await user.keyboard('{Enter}');

    expect(onSend).toHaveBeenCalledWith('测试消息');
  });

  it('按 Shift+Enter 不触发发送', async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<InputBox onSend={onSend} />);

    const textarea = screen.getByPlaceholderText('基于文档提问...');
    await user.type(textarea, '测试');
    await user.keyboard('{Shift>}{Enter}{/Shift}');

    expect(onSend).not.toHaveBeenCalled();
  });

  it('disabled 时按钮禁用', () => {
    render(<InputBox onSend={() => {}} disabled />);
    const btn = screen.getByRole('button');
    expect(btn).toBeDisabled();
  });

  it('streaming 时显示停止按钮', () => {
    render(<InputBox onSend={() => {}} streaming onStop={() => {}} />);
    expect(screen.getByText('停止生成')).toBeInTheDocument();
  });

  it('发送后清空输入框', async () => {
    const user = userEvent.setup();
    render(<InputBox onSend={() => {}} />);

    const textarea = screen.getByPlaceholderText('基于文档提问...');
    await user.type(textarea, '发送后清空');
    await user.keyboard('{Enter}');

    expect(textarea).toHaveValue('');
  });
});
