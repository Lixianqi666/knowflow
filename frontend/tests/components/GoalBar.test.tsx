import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import GoalBar from '@/components/GoalBar';
import { Conversation } from '@/lib/store';

vi.mock('@/lib/api', () => ({
  api: { patch: vi.fn().mockResolvedValue({}) },
}));

vi.mock('lucide-react', () => ({
  Target: (props: any) => <svg data-testid="target-icon" {...props} />,
  ChevronDown: (props: any) => <svg data-testid="chevron-down" {...props} />,
  ChevronUp: (props: any) => <svg data-testid="chevron-up" {...props} />,
}));

import { api } from '@/lib/api';

const baseConv: Conversation = {
  id: 'conv1',
  title: '测试',
  is_pinned: false,
  pinned_at: null,
  goal: null,
  goal_summary: null,
  goal_status: 'active',
  missing_info: [],
  created_at: '',
  updated_at: '',
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('GoalBar 基本显示', () => {
  it('有 goal 时显示目标文本', () => {
    render(
      <GoalBar conversation={{ ...baseConv, goal: '制定营销方案' }} onGoalChange={() => {}} />,
    );
    expect(screen.getByText('制定营销方案')).toBeInTheDocument();
  });

  it('missing_info 有内容时显示数量提示', () => {
    render(
      <GoalBar conversation={{ ...baseConv, goal: '目标', missing_info: ['预算', '时间'] }} onGoalChange={() => {}} />,
    );
    expect(screen.getByTestId('missing-count')).toHaveTextContent('2项待补充');
  });

  it('active 状态显示"进行中"', () => {
    render(
      <GoalBar conversation={{ ...baseConv, goal: '目标', goal_status: 'active' }} onGoalChange={() => {}} />,
    );
    expect(screen.getByTestId('goal-status')).toHaveTextContent('进行中');
  });

  it('blocked 状态显示"需补充信息"', () => {
    render(
      <GoalBar conversation={{ ...baseConv, goal: '目标', goal_status: 'blocked' }} onGoalChange={() => {}} />,
    );
    expect(screen.getByTestId('goal-status')).toHaveTextContent('需补充信息');
  });

  it('done 状态显示"已完成"', () => {
    render(
      <GoalBar conversation={{ ...baseConv, goal: '目标', goal_status: 'done' }} onGoalChange={() => {}} />,
    );
    expect(screen.getByTestId('goal-status')).toHaveTextContent('已完成');
  });

  it('无 goal 时显示"设置对话目标"按钮', () => {
    render(<GoalBar conversation={baseConv} onGoalChange={() => {}} />);
    expect(screen.getByText('设置对话目标')).toBeInTheDocument();
  });

  it('展开后显示 goal_summary', () => {
    render(
      <GoalBar conversation={{ ...baseConv, goal: '目标', goal_summary: '已确定方向' }} onGoalChange={() => {}} />,
    );
    fireEvent.click(screen.getByTestId('goal-bar-header'));
    expect(screen.getByTestId('goal-summary')).toHaveTextContent('已确定方向');
  });
});

describe('GoalBar 有 conversation 时保存', () => {
  it('调用 api.patch 并调用 onGoalChange', async () => {
    const onGoalChange = vi.fn();
    render(<GoalBar conversation={baseConv} onGoalChange={onGoalChange} />);

    fireEvent.click(screen.getByText('设置对话目标'));
    fireEvent.change(screen.getByPlaceholderText(/输入对话目标/), { target: { value: '新目标' } });
    fireEvent.click(screen.getByText('保存'));

    await waitFor(() => {
      expect(api.patch).toHaveBeenCalledWith('/chat/conversations/conv1', { goal: '新目标' });
      expect(onGoalChange).toHaveBeenCalledWith('新目标');
    });
  });
});

describe('GoalBar pendingGoal 边界（无 conversation）', () => {
  it('有 pendingGoal 且无 conversation 时显示 pendingGoal 文本', () => {
    render(<GoalBar pendingGoal="草稿目标" onGoalChange={() => {}} />);
    expect(screen.getByText('草稿目标')).toBeInTheDocument();
  });

  it('有 conversation 无 goal + pendingGoal 时，不显示 pendingGoal，显示"设置对话目标"', () => {
    render(<GoalBar conversation={baseConv} pendingGoal="草稿目标" onGoalChange={() => {}} />);
    expect(screen.queryByText('草稿目标')).not.toBeInTheDocument();
    expect(screen.getByText('设置对话目标')).toBeInTheDocument();
  });

  it('无 conversation 无 pendingGoal 时显示"设置对话目标"', () => {
    render(<GoalBar onGoalChange={() => {}} />);
    expect(screen.getByText('设置对话目标')).toBeInTheDocument();
  });

  it('无 conversation 时保存不调用 api.patch，只调用 onGoalChange', async () => {
    const onGoalChange = vi.fn();
    render(<GoalBar onGoalChange={onGoalChange} />);

    fireEvent.click(screen.getByText('设置对话目标'));
    fireEvent.change(screen.getByPlaceholderText(/输入对话目标/), { target: { value: '本地草稿' } });
    fireEvent.click(screen.getByText('保存'));

    await waitFor(() => {
      expect(api.patch).not.toHaveBeenCalled();
      expect(onGoalChange).toHaveBeenCalledWith('本地草稿');
    });
  });

  it('无 conversation 有 pendingGoal 时可修改草稿目标', async () => {
    const onGoalChange = vi.fn();
    render(<GoalBar pendingGoal="旧草稿" onGoalChange={onGoalChange} />);

    fireEvent.click(screen.getByText('修改'));
    fireEvent.change(screen.getByPlaceholderText(/输入对话目标/), { target: { value: '新草稿' } });
    fireEvent.click(screen.getByText('保存'));

    await waitFor(() => {
      expect(api.patch).not.toHaveBeenCalled();
      expect(onGoalChange).toHaveBeenCalledWith('新草稿');
    });
  });
});
