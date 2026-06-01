'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { toast } from '@/components/Toast';
import { Settings, Play, Upload, RotateCcw, RefreshCw } from 'lucide-react';

interface AgentConfigData {
  draft_config: {
    system_prompt: string;
    knowledge_base_ids: string[];
    temperature: number;
    max_tokens: number;
    tools: string[];
  };
  published_config: Record<string, unknown>;
  status: string;
  published_version: number;
  last_published_at: string | null;
  has_unpublished_changes: boolean;
}

interface Props {
  agentId: string;
}

export default function AgentConfig({ agentId }: Props) {
  const [config, setConfig] = useState<AgentConfigData | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [rollingBack, setRollingBack] = useState(false);

  // Debug state
  const [debugQuestion, setDebugQuestion] = useState('');
  const [debugResult, setDebugResult] = useState<{
    answer: string;
    citations: Array<{ document_title: string; snippet: string }>;
  } | null>(null);
  const [debugging, setDebugging] = useState(false);

  // Edit state
  const [systemPrompt, setSystemPrompt] = useState('');
  const [temperature, setTemperature] = useState(0.2);
  const [maxTokens, setMaxTokens] = useState(1000);

  const loadConfig = () => {
    setLoading(true);
    api
      .get<AgentConfigData>(`/agents/${agentId}/config`)
      .then((data) => {
        setConfig(data);
        setSystemPrompt(data.draft_config.system_prompt || '');
        setTemperature(data.draft_config.temperature ?? 0.2);
        setMaxTokens(data.draft_config.max_tokens ?? 1000);
      })
      .catch((e) => toast(e.message, 'error'))
      .finally(() => setLoading(false));
  };

  useEffect(loadConfig, [agentId]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const data = await api.patch<AgentConfigData>(`/agents/${agentId}/config`, {
        system_prompt: systemPrompt,
        temperature,
        max_tokens: maxTokens,
      });
      setConfig(data);
      toast('草稿已保存', 'success');
    } catch (e: any) {
      toast(e.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    setPublishing(true);
    try {
      const data = await api.post<AgentConfigData>(`/agents/${agentId}/publish`);
      setConfig(data);
      toast('已发布', 'success');
    } catch (e: any) {
      toast(e.message, 'error');
    } finally {
      setPublishing(false);
    }
  };

  const handleRollback = async () => {
    setRollingBack(true);
    try {
      const data = await api.post<AgentConfigData>(`/agents/${agentId}/rollback`);
      setConfig(data);
      setSystemPrompt(data.draft_config.system_prompt || '');
      setTemperature(data.draft_config.temperature ?? 0.2);
      setMaxTokens(data.draft_config.max_tokens ?? 1000);
      toast('已回滚到已发布版本', 'success');
    } catch (e: any) {
      toast(e.message, 'error');
    } finally {
      setRollingBack(false);
    }
  };

  const handleDebug = async () => {
    if (!debugQuestion.trim()) return;
    setDebugging(true);
    setDebugResult(null);
    try {
      const result = await api.post<{
        answer: string;
        citations: Array<{ document_title: string; snippet: string }>;
      }>(`/agents/${agentId}/debug`, { content: debugQuestion });
      setDebugResult(result);
    } catch (e: any) {
      toast(e.message, 'error');
    } finally {
      setDebugging(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-5 h-5 animate-spin" style={{ color: 'var(--c-text-tertiary)' }} />
        <span className="ml-2 text-sm" style={{ color: 'var(--c-text-tertiary)' }}>加载中...</span>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="text-center py-12">
        <p className="text-sm" style={{ color: 'var(--c-error)' }}>加载失败</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 状态栏 */}
      <div className="flex items-center gap-3 flex-wrap">
        <span
          className="text-xs px-2 py-1 rounded-full"
          style={{
            background: config.status === 'published' ? 'var(--c-success-subtle)' : 'var(--c-warning-subtle)',
            color: config.status === 'published' ? '#16a34a' : '#d97706',
          }}
        >
          {config.status === 'published' ? '已发布' : config.status === 'draft' ? '草稿' : config.status}
        </span>
        {config.published_version > 0 && (
          <span className="text-xs" style={{ color: 'var(--c-text-tertiary)' }}>
            v{config.published_version}
          </span>
        )}
        {config.has_unpublished_changes && (
          <span className="text-xs" style={{ color: '#d97706' }}>
            有未发布变更
          </span>
        )}
        {config.last_published_at && (
          <span className="text-xs ml-auto" style={{ color: 'var(--c-text-tertiary)' }}>
            上次发布：{new Date(config.last_published_at).toLocaleString('zh-CN')}
          </span>
        )}
      </div>

      {/* 配置表单 */}
      <div className="space-y-4">
        <div>
          <label className="text-xs font-medium block mb-1.5" style={{ color: 'var(--c-text-secondary)' }}>
            System Prompt
          </label>
          <textarea
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            rows={6}
            maxLength={4000}
            className="w-full text-sm px-3 py-2 rounded-lg border input-base"
            placeholder="Agent 系统提示词..."
          />
          <div className="text-xs mt-1 text-right" style={{ color: 'var(--c-text-tertiary)' }}>
            {systemPrompt.length}/4000
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-medium block mb-1.5" style={{ color: 'var(--c-text-secondary)' }}>
              Temperature
            </label>
            <input
              type="number"
              value={temperature}
              onChange={(e) => setTemperature(Number(e.target.value))}
              min={0}
              max={2}
              step={0.1}
              className="w-full text-sm px-3 py-2 rounded-lg border input-base"
            />
          </div>
          <div>
            <label className="text-xs font-medium block mb-1.5" style={{ color: 'var(--c-text-secondary)' }}>
              Max Tokens
            </label>
            <input
              type="number"
              value={maxTokens}
              onChange={(e) => setMaxTokens(Number(e.target.value))}
              min={1}
              max={8000}
              className="w-full text-sm px-3 py-2 rounded-lg border input-base"
            />
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-primary text-xs"
          >
            {saving ? '保存中...' : '保存草稿'}
          </button>
          <button
            onClick={handlePublish}
            disabled={publishing}
            className="text-xs px-3 py-2 rounded-lg border-none cursor-pointer disabled:opacity-50"
            style={{ background: 'var(--c-success-subtle)', color: '#16a34a' }}
          >
            <Upload className="w-3.5 h-3.5 inline mr-1" />
            {publishing ? '发布中...' : '发布'}
          </button>
          {config.published_version > 0 && (
            <button
              onClick={handleRollback}
              disabled={rollingBack}
              className="text-xs px-3 py-2 rounded-lg border-none cursor-pointer disabled:opacity-50"
              style={{ background: 'var(--c-bg)', color: 'var(--c-text-secondary)' }}
            >
              <RotateCcw className="w-3.5 h-3.5 inline mr-1" />
              {rollingBack ? '回滚中...' : '回滚'}
            </button>
          )}
        </div>
      </div>

      {/* 调试区 */}
      <div className="pt-4 border-t" style={{ borderColor: 'var(--c-border)' }}>
        <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
          <Settings className="w-4 h-4" style={{ color: 'var(--c-text-tertiary)' }} />
          调试
        </h4>
        <div className="flex gap-2 mb-3">
          <input
            value={debugQuestion}
            onChange={(e) => setDebugQuestion(e.target.value)}
            placeholder="输入测试问题..."
            className="flex-1 text-sm px-3 py-2 rounded-lg border input-base"
            onKeyDown={(e) => e.key === 'Enter' && handleDebug()}
          />
          <button
            onClick={handleDebug}
            disabled={debugging || !debugQuestion.trim()}
            className="text-xs px-3 py-2 rounded-lg border-none cursor-pointer disabled:opacity-50"
            style={{ background: 'var(--c-primary-subtle)', color: 'var(--c-primary)' }}
          >
            <Play className="w-3.5 h-3.5 inline mr-1" />
            {debugging ? '调试中...' : '调试'}
          </button>
        </div>

        {debugResult && (
          <div className="p-3 rounded-lg text-xs" style={{ background: 'var(--c-bg)', border: '1px solid var(--c-border)' }}>
            <div className="font-medium mb-2">回答：</div>
            <div className="whitespace-pre-wrap" style={{ color: 'var(--c-text-secondary)' }}>
              {debugResult.answer}
            </div>
            {debugResult.citations.length > 0 && (
              <div className="mt-3 pt-2 border-t" style={{ borderColor: 'var(--c-border)' }}>
                <div className="font-medium mb-1">引用 ({debugResult.citations.length})：</div>
                {debugResult.citations.map((c, i) => (
                  <div key={i} className="ml-2 mb-1" style={{ color: 'var(--c-text-tertiary)' }}>
                    {c.document_title}: {c.snippet.slice(0, 100)}...
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
