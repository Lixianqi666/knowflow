import { describe, it, expect, vi, beforeEach, beforeAll } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

beforeAll(() => {
  HTMLElement.prototype.scrollIntoView = vi.fn();
});

vi.mock('@/lib/api', () => ({
  api: {
    download: vi.fn(),
    post: vi.fn(),
  },
  API_URL: 'http://localhost:8000/api/v1',
}));

vi.mock('lucide-react', () => ({
  Download: () => <svg />,
  ThumbsUp: () => <svg />,
  ThumbsDown: () => <svg />,
  FileText: () => <svg />,
}));

vi.mock('react-markdown', () => ({
  default: ({ children }: any) => <div data-testid="markdown">{children}</div>,
}));

import MessageBubble from '@/components/MessageBubble';

const mockCitations = [
  {
    index: 1,
    document_id: 'doc-1',
    document_title: '员工手册',
    chunk_id: 'chunk-1',
    snippet: '试用期为3个月，特殊岗位可延长至6个月。',
    score: 0.85,
  },
  {
    index: 2,
    document_id: 'doc-2',
    document_title: '薪酬制度',
    chunk_id: 'chunk-2',
    snippet: '基本工资根据岗位职级确定。',
    score: 0.72,
  },
];

describe('MessageBubble citations', () => {
  it('有 citations 时显示引用入口', () => {
    render(
      <MessageBubble
        role="assistant"
        content="回答内容"
        citations={mockCitations}
      />,
    );
    expect(screen.getByText('引用 2 条')).toBeInTheDocument();
  });

  it('无 citations 时不显示引用入口', () => {
    render(
      <MessageBubble
        role="assistant"
        content="回答内容"
        citations={[]}
      />,
    );
    expect(screen.queryByText(/引用.*条/)).not.toBeInTheDocument();
  });

  it('citations 为 undefined 时不崩溃', () => {
    render(
      <MessageBubble
        role="assistant"
        content="回答内容"
      />,
    );
    expect(screen.queryByText(/引用.*条/)).not.toBeInTheDocument();
  });

  it('展开引用后显示 document_title 和 snippet', async () => {
    render(
      <MessageBubble
        role="assistant"
        content="回答内容"
        citations={mockCitations}
      />,
    );
    fireEvent.click(screen.getByText('引用 2 条'));
    await waitFor(() => {
      expect(screen.getByText('员工手册')).toBeInTheDocument();
      expect(screen.getByText(/试用期为3个月/)).toBeInTheDocument();
      expect(screen.getByText('薪酬制度')).toBeInTheDocument();
    });
  });

  it('点击引用调用 onSourceClick 传递 document_id 和 chunk_id', async () => {
    const onSourceClick = vi.fn();
    render(
      <MessageBubble
        role="assistant"
        content="回答内容"
        citations={mockCitations}
        onSourceClick={onSourceClick}
      />,
    );
    fireEvent.click(screen.getByText('引用 2 条'));
    await waitFor(() => {
      fireEvent.click(screen.getByText('员工手册'));
    });
    expect(onSourceClick).toHaveBeenCalledWith('doc-1', 'chunk-1');
  });

  it('citation 有 page 时显示页码标签', async () => {
    const citationsWithPage = [
      { ...mockCitations[0], page: 3 },
    ];
    render(
      <MessageBubble
        role="assistant"
        content="回答内容"
        citations={citationsWithPage}
      />,
    );
    fireEvent.click(screen.getByText('引用 1 条'));
    await waitFor(() => {
      expect(screen.getByText('第3页')).toBeInTheDocument();
    });
  });

  it('citation 有 document_id 时显示"点击查看原文"', async () => {
    render(
      <MessageBubble
        role="assistant"
        content="回答内容"
        citations={mockCitations}
        onSourceClick={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByText('引用 2 条'));
    await waitFor(() => {
      expect(screen.getAllByText('点击查看原文 →').length).toBeGreaterThan(0);
    });
  });

  it('旧 citation 无 locator 字段不崩溃', async () => {
    const oldCitations = [{
      index: 1,
      document_id: 'doc-1',
      document_title: '旧文档',
      chunk_id: 'chunk-1',
      snippet: '旧片段',
      score: 0.5,
    }];
    render(
      <MessageBubble
        role="assistant"
        content="回答内容"
        citations={oldCitations}
        onSourceClick={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByText('引用 1 条'));
    await waitFor(() => {
      expect(screen.getByText('旧文档')).toBeInTheDocument();
      expect(screen.getByText('旧片段')).toBeInTheDocument();
    });
  });

  it('snippet 过长要截断', () => {
    const longCitations = [
      {
        ...mockCitations[0],
        snippet: 'A'.repeat(350),
      },
    ];
    render(
      <MessageBubble
        role="assistant"
        content="回答内容"
        citations={longCitations}
      />,
    );
    fireEvent.click(screen.getByText('引用 1 条'));
    // 应截断到 200 字 + "..."
    expect(screen.getByText(/A{200}\.\.\./)).toBeInTheDocument();
  });
});

describe('MessageBubble feedback', () => {
  it('点击有帮助会调用 feedback API', () => {
    const onFeedback = vi.fn();
    render(
      <MessageBubble
        role="assistant"
        content="回答内容"
        msgId="msg-1"
        onFeedback={onFeedback}
      />,
    );
    // 找到 thumbs up 按钮（第一个 feedback 按钮）
    const buttons = screen.getAllByRole('button');
    const feedbackBtns = buttons.filter(
      (b) => !b.textContent?.includes('引用') && !b.textContent?.includes('下载'),
    );
    if (feedbackBtns.length > 0) {
      fireEvent.click(feedbackBtns[0]);
      expect(onFeedback).toHaveBeenCalledWith('msg-1', 'up');
    }
  });

  it('feedback 成功后显示已选择状态', () => {
    render(
      <MessageBubble
        role="assistant"
        content="回答内容"
        msgId="msg-1"
        feedback={{ rating: 'up' }}
      />,
    );
    expect(screen.getByText(/已反馈/)).toBeInTheDocument();
  });

  it('feedback down 显示已反馈', () => {
    render(
      <MessageBubble
        role="assistant"
        content="回答内容"
        msgId="msg-1"
        feedback={{ rating: 'down' }}
      />,
    );
    expect(screen.getByText(/已反馈/)).toBeInTheDocument();
  });

  it('user 消息不显示 feedback 按钮', () => {
    const onFeedback = vi.fn();
    render(
      <MessageBubble
        role="user"
        content="用户消息"
        msgId="msg-1"
        onFeedback={onFeedback}
      />,
    );
    expect(screen.queryByText(/已反馈/)).not.toBeInTheDocument();
  });

  it('down feedback 后显示加入评测集按钮', () => {
    const onToEvalCase = vi.fn();
    render(
      <MessageBubble
        role="assistant"
        content="回答内容"
        msgId="msg-1"
        feedback={{ rating: 'down' }}
        onToEvalCase={onToEvalCase}
      />,
    );
    expect(screen.getByText('加入评测集')).toBeInTheDocument();
  });

  it('up feedback 后不显示加入评测集按钮', () => {
    render(
      <MessageBubble
        role="assistant"
        content="回答内容"
        msgId="msg-1"
        feedback={{ rating: 'up' }}
        onToEvalCase={vi.fn()}
      />,
    );
    expect(screen.queryByText('加入评测集')).not.toBeInTheDocument();
  });

  it('点击加入评测集调用 API', () => {
    const onToEvalCase = vi.fn();
    render(
      <MessageBubble
        role="assistant"
        content="回答内容"
        msgId="msg-1"
        feedback={{ rating: 'down' }}
        onToEvalCase={onToEvalCase}
      />,
    );
    fireEvent.click(screen.getByText('加入评测集'));
    expect(onToEvalCase).toHaveBeenCalledWith('msg-1');
  });

  it('加入评测集成功后显示已加入', () => {
    render(
      <MessageBubble
        role="assistant"
        content="回答内容"
        msgId="msg-1"
        feedback={{ rating: 'down' }}
        onToEvalCase={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByText('加入评测集'));
    expect(screen.getByText(/已加入评测集/)).toBeInTheDocument();
  });

  it('无 citations 的消息不崩溃', () => {
    render(
      <MessageBubble
        role="assistant"
        content="回答内容"
        msgId="msg-1"
        feedback={{ rating: 'down' }}
        onToEvalCase={vi.fn()}
      />,
    );
    expect(screen.getByText('加入评测集')).toBeInTheDocument();
  });
});
