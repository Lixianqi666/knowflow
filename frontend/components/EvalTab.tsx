'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { toast } from '@/components/Toast';
import { Play, Trash2, Plus, RefreshCw } from 'lucide-react';

interface EvalCase {
  id: string;
  question: string;
  expected_answer?: string | null;
  expected_citation_doc_ids?: string[];
  tags?: string[];
  created_at: string;
}

interface EvalRun {
  id: string;
  case_id: string;
  question: string;
  answer?: string | null;
  passed: boolean;
  score?: number | null;
  failure_reason?: string | null;
  created_at: string;
}

export default function EvalTab() {
  const [cases, setCases] = useState<EvalCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newQuestion, setNewQuestion] = useState('');
  const [newExpectedAnswer, setNewExpectedAnswer] = useState('');
  const [runningId, setRunningId] = useState<string | null>(null);
  const [selectedCase, setSelectedCase] = useState<string | null>(null);
  const [runs, setRuns] = useState<EvalRun[]>([]);

  const loadCases = () => {
    setLoading(true);
    api
      .get<EvalCase[]>('/rag-evals/cases')
      .then(setCases)
      .catch((e) => toast(e.message, 'error'))
      .finally(() => setLoading(false));
  };

  useEffect(loadCases, []);

  const loadRuns = (caseId: string) => {
    setSelectedCase(caseId);
    api
      .get<EvalRun[]>(`/rag-evals/cases/${caseId}/runs`)
      .then(setRuns)
      .catch((e) => toast(e.message, 'error'));
  };

  const handleCreate = async () => {
    if (!newQuestion.trim()) return;
    try {
      await api.post('/rag-evals/cases', {
        question: newQuestion,
        expected_answer: newExpectedAnswer || null,
      });
      setNewQuestion('');
      setNewExpectedAnswer('');
      setShowCreate(false);
      loadCases();
      toast('评测用例已创建', 'success');
    } catch (e: any) {
      toast(e.message, 'error');
    }
  };

  const handleRun = async (caseId: string) => {
    setRunningId(caseId);
    try {
      const run = await api.post<EvalRun>(`/rag-evals/cases/${caseId}/run`);
      toast(run.passed ? '评测通过 ✓' : `评测未通过: ${run.failure_reason}`, run.passed ? 'success' : 'error');
      if (selectedCase === caseId) loadRuns(caseId);
    } catch (e: any) {
      toast(e.message, 'error');
    } finally {
      setRunningId(null);
    }
  };

  const handleDelete = async (caseId: string) => {
    try {
      await api.delete(`/rag-evals/cases/${caseId}`);
      setCases((prev) => prev.filter((c) => c.id !== caseId));
      if (selectedCase === caseId) {
        setSelectedCase(null);
        setRuns([]);
      }
      toast('已删除', 'success');
    } catch (e: any) {
      toast(e.message, 'error');
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold" style={{ color: 'var(--c-text)' }}>
          RAG 评测用例
        </h3>
        <div className="flex gap-2">
          <button
            onClick={loadCases}
            className="text-xs flex items-center gap-1 px-2.5 py-1.5 rounded-lg border-none cursor-pointer"
            style={{ color: 'var(--c-text-tertiary)', background: 'none' }}
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="text-xs flex items-center gap-1 px-3 py-1.5 rounded-lg border-none cursor-pointer"
            style={{ background: 'var(--c-primary)', color: '#fff' }}
          >
            <Plus className="w-3.5 h-3.5" />
            新增
          </button>
        </div>
      </div>

      {showCreate && (
        <div className="p-3 rounded-xl border animate-slide-up" style={{ borderColor: 'var(--c-border)', background: 'var(--c-surface)' }}>
          <input
            value={newQuestion}
            onChange={(e) => setNewQuestion(e.target.value)}
            placeholder="评测问题"
            className="w-full text-sm px-3 py-2 rounded-lg border input-base mb-2"
          />
          <input
            value={newExpectedAnswer}
            onChange={(e) => setNewExpectedAnswer(e.target.value)}
            placeholder="预期答案关键词（可选）"
            className="w-full text-sm px-3 py-2 rounded-lg border input-base mb-2"
          />
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowCreate(false)} className="text-xs px-3 py-1.5 rounded-lg border-none cursor-pointer" style={{ color: 'var(--c-text-secondary)', background: 'none' }}>取消</button>
            <button onClick={handleCreate} className="text-xs px-3 py-1.5 rounded-lg border-none cursor-pointer" style={{ background: 'var(--c-primary)', color: '#fff' }}>创建</button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="text-center py-8 text-sm" style={{ color: 'var(--c-text-tertiary)' }}>加载中...</div>
      ) : cases.length === 0 ? (
        <div className="text-center py-8 text-sm" style={{ color: 'var(--c-text-tertiary)' }}>暂无评测用例</div>
      ) : (
        <div className="space-y-2">
          {cases.map((c) => (
            <div
              key={c.id}
              className={`p-3 rounded-xl border cursor-pointer transition-all ${selectedCase === c.id ? 'ring-2' : ''}`}
              style={{
                borderColor: selectedCase === c.id ? 'var(--c-primary)' : 'var(--c-border)',
                background: 'var(--c-surface)',
                ...(selectedCase === c.id ? { boxShadow: '0 0 0 2px var(--c-primary-ring)' } : {}),
              }}
              onClick={() => loadRuns(c.id)}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{c.question}</div>
                  {c.expected_answer && (
                    <div className="text-xs mt-0.5 truncate" style={{ color: 'var(--c-text-tertiary)' }}>
                      预期: {c.expected_answer}
                    </div>
                  )}
                  {c.tags && c.tags.length > 0 && (
                    <div className="flex gap-1 mt-1">
                      {c.tags.map((t) => (
                        <span key={t} className="text-[10px] px-1.5 py-0.5 rounded-full" style={{ background: 'var(--c-bg)', color: 'var(--c-text-tertiary)' }}>
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex gap-1 ml-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRun(c.id);
                    }}
                    disabled={runningId === c.id}
                    className="p-1.5 rounded-lg border-none cursor-pointer disabled:opacity-50 transition-all"
                    style={{ color: 'var(--c-primary)', background: 'var(--c-primary-subtle)' }}
                  >
                    {runningId === c.id ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(c.id);
                    }}
                    className="p-1.5 rounded-lg border-none cursor-pointer transition-all"
                    style={{ color: 'var(--c-text-tertiary)', background: 'none' }}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedCase && runs.length > 0 && (
        <div className="mt-4">
          <h4 className="text-xs font-semibold mb-2" style={{ color: 'var(--c-text-tertiary)' }}>
            运行历史
          </h4>
          <div className="space-y-1.5">
            {runs.map((r) => (
              <div
                key={r.id}
                className="p-2.5 rounded-lg text-xs"
                style={{ background: 'var(--c-bg)', border: '1px solid var(--c-border)' }}
              >
                <div className="flex items-center gap-2">
                  <span
                    className="w-2 h-2 rounded-full"
                    style={{ background: r.passed ? '#16a34a' : '#dc2626' }}
                  />
                  <span className="font-medium" style={{ color: r.passed ? '#16a34a' : '#dc2626' }}>
                    {r.passed ? '通过' : '未通过'}
                  </span>
                  {r.score != null && (
                    <span className="font-mono" style={{ color: 'var(--c-text-tertiary)' }}>
                      {r.score.toFixed(1)}
                    </span>
                  )}
                  <span className="ml-auto" style={{ color: 'var(--c-text-tertiary)' }}>
                    {new Date(r.created_at).toLocaleString('zh-CN')}
                  </span>
                </div>
                {r.failure_reason && (
                  <div className="mt-1" style={{ color: 'var(--c-error)' }}>
                    {r.failure_reason}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
