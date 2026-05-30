import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import UploadDialog from '@/components/UploadDialog';

// mock api.upload
vi.mock('@/lib/api', () => ({
  api: { upload: vi.fn() },
}));

beforeEach(() => {
  vi.clearAllMocks();
});

function makeFile(name: string, size: number): File {
  const content = new Uint8Array(size);
  return new File([content], name);
}

describe('UploadDialog', () => {
  it('不合法扩展名时显示错误', () => {
    render(<UploadDialog open onClose={() => {}} />);
    const input = document.querySelector('input[type="file"]')!;
    const file = makeFile('bad.exe', 100);
    fireEvent.change(input, { target: { files: [file] } });

    expect(screen.getByText(/不支持的文件格式/)).toBeInTheDocument();
    // file 应被清空，按钮禁用
    const btn = screen.getByText('上传').closest('button')!;
    expect(btn).toBeDisabled();
  });

  it('超大文件时显示错误', () => {
    render(<UploadDialog open onClose={() => {}} />);
    const input = document.querySelector('input[type="file"]')!;
    const file = makeFile('big.txt', 21 * 1024 * 1024); // 21MB
    fireEvent.change(input, { target: { files: [file] } });

    expect(screen.getByText(/文件过大/)).toBeInTheDocument();
    const btn = screen.getByText('上传').closest('button')!;
    expect(btn).toBeDisabled();
  });

  it('合法文件时显示文件名并启用上传', () => {
    render(<UploadDialog open onClose={() => {}} />);
    const input = document.querySelector('input[type="file"]')!;
    const file = makeFile('test.pdf', 1024);
    fireEvent.change(input, { target: { files: [file] } });

    expect(screen.getByText('test.pdf')).toBeInTheDocument();
    const btn = screen.getByText('上传').closest('button')!;
    expect(btn).not.toBeDisabled();
  });

  it('合法 markdown 扩展名', () => {
    render(<UploadDialog open onClose={() => {}} />);
    const input = document.querySelector('input[type="file"]')!;
    const file = makeFile('readme.markdown', 512);
    fireEvent.change(input, { target: { files: [file] } });

    expect(screen.getByText('readme.markdown')).toBeInTheDocument();
  });

  it('选择非法文件后再选合法文件清除错误', () => {
    render(<UploadDialog open onClose={() => {}} />);
    const input = document.querySelector('input[type="file"]')!;

    // 先选非法
    fireEvent.change(input, { target: { files: [makeFile('bad.exe', 100)] } });
    expect(screen.getByText(/不支持/)).toBeInTheDocument();

    // 再选合法
    fireEvent.change(input, { target: { files: [makeFile('good.txt', 100)] } });
    expect(screen.queryByText(/不支持/)).not.toBeInTheDocument();
    expect(screen.getByText('good.txt')).toBeInTheDocument();
  });
});
