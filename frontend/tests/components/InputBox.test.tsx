import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import InputBox, { MAX_MESSAGE_LENGTH } from '@/components/InputBox';

describe('InputBox', () => {
  it('渲染输入框和发送按钮', () => {
    render(<InputBox onSend={() => {}} />);
    expect(screen.getByPlaceholderText('输入消息...')).toBeInTheDocument();
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

    const textarea = screen.getByPlaceholderText('输入消息...');
    await user.type(textarea, '你好');
    await user.click(screen.getByRole('button'));

    expect(onSend).toHaveBeenCalledWith('你好');
  });

  it('按 Enter 触发发送（非 Shift+Enter）', async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<InputBox onSend={onSend} />);

    const textarea = screen.getByPlaceholderText('输入消息...');
    await user.type(textarea, '测试消息');
    await user.keyboard('{Enter}');

    expect(onSend).toHaveBeenCalledWith('测试消息');
  });

  it('按 Shift+Enter 不触发发送', async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<InputBox onSend={onSend} />);

    const textarea = screen.getByPlaceholderText('输入消息...');
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

    const textarea = screen.getByPlaceholderText('输入消息...');
    await user.type(textarea, '发送后清空');
    await user.keyboard('{Enter}');

    expect(textarea).toHaveValue('');
  });

  it('导出 MAX_MESSAGE_LENGTH 常量', () => {
    expect(MAX_MESSAGE_LENGTH).toBe(4000);
  });

  it('textarea 有 maxLength 属性', () => {
    render(<InputBox onSend={() => {}} />);
    const textarea = screen.getByPlaceholderText('输入消息...');
    expect(textarea).toHaveAttribute('maxlength', String(MAX_MESSAGE_LENGTH));
  });

  it('handleSend 防御：超长消息不发送', () => {
    const onSend = vi.fn();
    render(<InputBox onSend={onSend} />);

    const textarea = screen.getByPlaceholderText('输入消息...');
    // 直接设置超长值绕过 maxLength
    fireEvent.change(textarea, { target: { value: 'a'.repeat(4001) } });
    fireEvent.keyDown(textarea, { key: 'Enter' });

    expect(onSend).not.toHaveBeenCalled();
  });

  it('接近上限时显示字符计数', () => {
    render(<InputBox onSend={() => {}} />);

    const textarea = screen.getByPlaceholderText('输入消息...');
    // 直接设置 3950 字符（超过 3900 阈值）
    fireEvent.change(textarea, { target: { value: 'a'.repeat(3950) } });

    expect(screen.getByText(/3950\/4000/)).toBeInTheDocument();
  });
});
