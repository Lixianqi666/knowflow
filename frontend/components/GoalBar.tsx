'use client';

import { useState } from 'react';
import { Target, ChevronDown, ChevronUp } from 'lucide-react';
import { Conversation } from '@/lib/store';
import { api } from '@/lib/api';

const STATUS_LABELS: Record<string, { text: string; color: string }> = {
  active: { text: '进行中', color: 'var(--c-primary)' },
  blocked: { text: '需补充信息', color: 'var(--c-error)' },
  done: { text: '已完成', color: '#16a34a' },
};

interface GoalBarProps {
  conversation?: Conversation;
  pendingGoal?: string | null;
  onGoalChange: (goal: string) => void;
}

export default function GoalBar({ conversation, pendingGoal, onGoalChange }: GoalBarProps) {
  const [editing, setEditing] = useState(false);
  const [goalInput, setGoalInput] = useState('');
  const [expanded, setExpanded] = useState(false);

  const hasConversation = !!conversation;
  // conversation 存在时只用 conversation.goal，不存在时才用 pendingGoal
  const goal = hasConversation ? conversation!.goal : (pendingGoal || null);
  const goal_summary = hasConversation ? conversation!.goal_summary : null;
  const goal_status = hasConversation ? conversation!.goal_status : 'active';
  const missing_info = hasConversation ? conversation!.missing_info : [];
  const hasGoal = !!goal;

  const handleSave = async () => {
    if (!goalInput.trim()) return;
    if (hasConversation) {
      try {
        await api.patch(`/chat/conversations/${conversation!.id}`, { goal: goalInput.trim() });
      } catch (e) {
        console.error('设置目标失败:', e);
        return;
      }
    }
    onGoalChange(goalInput.trim());
    setEditing(false);
  };

  if (!hasGoal && !editing) {
    return (
      <div className="mb-3">
        <button
          onClick={() => setEditing(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border-none cursor-pointer transition-all"
          style={{ background: 'var(--c-surface)', color: 'var(--c-text-tertiary)' }}
        >
          <Target className="w-3.5 h-3.5" />
          设置对话目标
        </button>
      </div>
    );
  }

  if (editing) {
    return (
      <div className="mb-3 p-3 rounded-xl" style={{ background: 'var(--c-surface)', border: '1px solid var(--c-border)' }}>
        <input
          type="text"
          value={goalInput}
          onChange={(e) => setGoalInput(e.target.value)}
          placeholder="输入对话目标，例如：帮我制定Q3营销方案"
          className="w-full text-sm px-3 py-2 rounded-lg border outline-none"
          style={{ borderColor: 'var(--c-border)', background: 'var(--c-bg)', color: 'var(--c-text)' }}
          maxLength={200}
          autoFocus
          onKeyDown={(e) => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') setEditing(false); }}
        />
        <div className="flex gap-2 mt-2">
          <button onClick={handleSave} className="px-3 py-1 text-xs rounded-lg border-none cursor-pointer" style={{ background: 'var(--c-primary)', color: '#fff' }}>
            保存
          </button>
          <button onClick={() => setEditing(false)} className="px-3 py-1 text-xs rounded-lg border-none cursor-pointer" style={{ background: 'var(--c-bg)', color: 'var(--c-text-tertiary)' }}>
            取消
          </button>
        </div>
      </div>
    );
  }

  const status = STATUS_LABELS[goal_status] || STATUS_LABELS.active;
  const missingCount = Array.isArray(missing_info) ? missing_info.length : 0;

  return (
    <div className="mb-3 rounded-xl overflow-hidden" style={{ background: 'var(--c-surface)', border: '1px solid var(--c-border)' }}>
      <div
        className="flex items-center justify-between px-3 py-2 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
        data-testid="goal-bar-header"
      >
        <div className="flex items-center gap-2 min-w-0">
          <Target className="w-3.5 h-3.5 shrink-0" style={{ color: status.color }} />
          <span className="text-xs font-medium truncate" style={{ color: 'var(--c-text)' }}>{goal}</span>
          <span data-testid="goal-status" className="text-[10px] px-1.5 py-0.5 rounded-full shrink-0" style={{ background: `${status.color}15`, color: status.color }}>
            {status.text}
          </span>
          {missingCount > 0 && (
            <span data-testid="missing-count" className="text-[10px] px-1.5 py-0.5 rounded-full shrink-0" style={{ background: 'var(--c-error-subtle)', color: 'var(--c-error)' }}>
              {missingCount}项待补充
            </span>
          )}
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={(e) => { e.stopPropagation(); setEditing(true); setGoalInput(goal || ''); }}
            className="text-[10px] px-1.5 py-0.5 rounded border-none cursor-pointer"
            style={{ background: 'var(--c-bg)', color: 'var(--c-text-tertiary)' }}
          >
            修改
          </button>
          {expanded ? <ChevronUp className="w-3.5 h-3.5" style={{ color: 'var(--c-text-tertiary)' }} /> : <ChevronDown className="w-3.5 h-3.5" style={{ color: 'var(--c-text-tertiary)' }} />}
        </div>
      </div>
      {expanded && goal_summary && (
        <div data-testid="goal-summary" className="px-3 pb-2 text-xs" style={{ color: 'var(--c-text-secondary)' }}>
          <span className="font-medium">进展：</span>{goal_summary}
        </div>
      )}
    </div>
  );
}
