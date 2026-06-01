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
  Database: () => <svg />,
  Zap: () => <svg />,
  FileText: () => <svg />,
  MessageSquare: () => <svg />,
  BarChart3: () => <svg />,
}));

import HealthTab from '@/components/HealthTab';

const mockHealthData = {
  status: 'ok',
  database: { status: 'ok', latency_ms: 12 },
  redis: { status: 'ok', latency_ms: 8 },
  documents: {
    total: 120,
    indexed: 110,
    processing: 2,
    failed: 8,
    recent_failed: [
      {
        id: 'doc-1',
        title: '失败文档.txt',
        status: 'failed',
        error_message: '解析失败',
        updated_at: '2026-05-31T10:00:00Z',
      },
    ],
  },
  rag_evals: {
    total_runs: 30,
    latest_score: 0.82,
    latest_passed: 24,
    latest_failed: 6,
  },
  feedback: { up: 50, down: 7 },
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('HealthTab', () => {
  it('加载时显示 loading', () => {
    mockGet.mockReturnValueOnce(new Promise(() => {}));
    render(<HealthTab />);
    expect(screen.getByText('加载中...')).toBeInTheDocument();
  });

  it('成功后显示整体状态', async () => {
    mockGet.mockResolvedValueOnce(mockHealthData);
    render(<HealthTab />);
    await waitFor(() => {
      expect(screen.getByText(/系统状态：正常/)).toBeInTheDocument();
    });
  });

  it('显示 database / redis 状态', async () => {
    mockGet.mockResolvedValueOnce(mockHealthData);
    render(<HealthTab />);
    await waitFor(() => {
      expect(screen.getByText('数据库')).toBeInTheDocument();
      expect(screen.getByText('Redis')).toBeInTheDocument();
      expect(screen.getByText(/12ms/)).toBeInTheDocument();
      expect(screen.getByText(/8ms/)).toBeInTheDocument();
    });
  });

  it('显示文档索引统计', async () => {
    mockGet.mockResolvedValueOnce(mockHealthData);
    render(<HealthTab />);
    await waitFor(() => {
      expect(screen.getByText('120')).toBeInTheDocument(); // total
      expect(screen.getByText('110')).toBeInTheDocument(); // indexed
      expect(screen.getByText('8')).toBeInTheDocument(); // failed
    });
  });

  it('显示最近失败文档', async () => {
    mockGet.mockResolvedValueOnce(mockHealthData);
    render(<HealthTab />);
    await waitFor(() => {
      expect(screen.getByText('失败文档.txt')).toBeInTheDocument();
      expect(screen.getByText('解析失败')).toBeInTheDocument();
    });
  });

  it('显示 RAG Eval 摘要', async () => {
    mockGet.mockResolvedValueOnce(mockHealthData);
    render(<HealthTab />);
    await waitFor(() => {
      expect(screen.getByText('RAG 评测')).toBeInTheDocument();
      expect(screen.getByText('30')).toBeInTheDocument(); // total
      expect(screen.getByText('24')).toBeInTheDocument(); // passed
      expect(screen.getByText('6')).toBeInTheDocument(); // failed
    });
  });

  it('显示 feedback up/down', async () => {
    mockGet.mockResolvedValueOnce(mockHealthData);
    render(<HealthTab />);
    await waitFor(() => {
      expect(screen.getByText('用户反馈')).toBeInTheDocument();
      expect(screen.getByText('50')).toBeInTheDocument(); // up
      expect(screen.getByText('7')).toBeInTheDocument(); // down
    });
  });

  it('403 时显示错误提示', async () => {
    mockGet.mockRejectedValueOnce(new Error('无权限访问'));
    render(<HealthTab />);
    await waitFor(() => {
      expect(screen.getByText('无权限访问')).toBeInTheDocument();
    });
  });

  it('API 失败时显示错误提示', async () => {
    mockGet.mockRejectedValueOnce(new Error('网络错误'));
    render(<HealthTab />);
    await waitFor(() => {
      expect(screen.getByText('网络错误')).toBeInTheDocument();
    });
  });

  it('空数据时页面不崩溃', async () => {
    mockGet.mockResolvedValueOnce({
      ...mockHealthData,
      documents: { ...mockHealthData.documents, recent_failed: [] },
      rag_evals: { ...mockHealthData.rag_evals, latest_score: null },
    });
    render(<HealthTab />);
    await waitFor(() => {
      expect(screen.getByText(/系统状态/)).toBeInTheDocument();
    });
  });
});
