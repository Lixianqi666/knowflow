'use client';

import { AgentItem, KnowledgeBaseOption } from './types';
import FormModal from '@/components/FormModal';

interface AgentForm {
  id?: string;
  name: string;
  description: string;
  system_prompt: string;
  knowledge_base_ids: string[];
  top_k: number;
  threshold: number;
  rerank_top_k: number;
}

interface AgentsTabProps {
  agentItems: AgentItem[];
  agentForm: AgentForm | null;
  savingAgent: boolean;
  kbOptions: KnowledgeBaseOption[];
  onSetAgentForm: (form: AgentForm | null) => void;
  onOpenEditForm: (a: AgentItem) => void;
  onToggleActive: (a: AgentItem) => void;
  onSave: () => void;
}

export default function AgentsTab({
  agentItems,
  agentForm,
  savingAgent,
  kbOptions,
  onSetAgentForm,
  onOpenEditForm,
  onToggleActive,
  onSave,
}: AgentsTabProps) {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-500">
          创建和管理 AI Agent，每个 Agent 可关联知识库并独立对话
        </p>
        <button
          onClick={() =>
            onSetAgentForm({
              name: '',
              description: '',
              system_prompt: '',
              knowledge_base_ids: [],
              top_k: 5,
              threshold: 30,
              rerank_top_k: 3,
            })
          }
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          新建 Agent
        </button>
      </div>
      <div className="space-y-2">
        {agentItems.length === 0 ? (
          <div className="py-12 text-center text-gray-400 text-sm">
            暂无 Agent，点击上方按钮创建
          </div>
        ) : (
          agentItems.map((a) => (
            <div key={a.id} className="bg-white rounded-xl shadow-sm border p-4">
              <div className="flex items-center justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{a.name}</span>
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded ${a.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}
                    >
                      {a.is_active ? '启用' : '停用'}
                    </span>
                  </div>
                  {a.description && (
                    <p className="text-xs text-gray-400 mt-0.5">{a.description}</p>
                  )}
                  <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                    <span>top_k={a.top_k}</span>
                    <span>阈值={a.threshold}%</span>
                    <span>知识库 {a.knowledge_base_ids?.length || 0} 个</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => onOpenEditForm(a)}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    编辑
                  </button>
                  <button
                    onClick={() => onToggleActive(a)}
                    className="text-xs text-gray-500 hover:text-blue-600"
                  >
                    {a.is_active ? '停用' : '启用'}
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
      {agentForm && (
        <FormModal
          open={!!agentForm}
          title={agentForm.id ? '编辑 Agent' : '新建 Agent'}
          onClose={() => onSetAgentForm(null)}
          footer={
            <>
              <button
                onClick={() => onSetAgentForm(null)}
                className="px-4 py-2 text-sm text-gray-600 border rounded-lg hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={onSave}
                disabled={savingAgent}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {savingAgent ? '保存中...' : '保存'}
              </button>
            </>
          }
        >
          <div>
            <label className="text-xs text-gray-500 mb-1 block">名称</label>
            <input
              value={agentForm.name}
              onChange={(e) => onSetAgentForm({ ...agentForm, name: e.target.value })}
              className="w-full text-sm border rounded-lg px-3 py-2 input-base"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">描述</label>
            <input
              value={agentForm.description}
              onChange={(e) => onSetAgentForm({ ...agentForm, description: e.target.value })}
              className="w-full text-sm border rounded-lg px-3 py-2 input-base"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">系统提示词</label>
            <textarea
              value={agentForm.system_prompt}
              onChange={(e) => onSetAgentForm({ ...agentForm, system_prompt: e.target.value })}
              className="w-full text-sm border rounded-lg px-3 py-2 h-24 input-base font-mono"
              placeholder="Agent 的系统提示词，定义 AI 的行为和回答风格"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">关联知识库</label>
            <div className="flex flex-wrap gap-2">
              {kbOptions.map((kb) => {
                const selected = agentForm.knowledge_base_ids.includes(kb.id);
                return (
                  <button
                    key={kb.id}
                    onClick={() => {
                      const ids = selected
                        ? agentForm.knowledge_base_ids.filter((id) => id !== kb.id)
                        : [...agentForm.knowledge_base_ids, kb.id];
                      onSetAgentForm({ ...agentForm, knowledge_base_ids: ids });
                    }}
                    className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
                      selected
                        ? 'bg-blue-100 border-blue-300 text-blue-700'
                        : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    {kb.name}
                  </button>
                );
              })}
              {kbOptions.length === 0 && (
                <span className="text-xs text-gray-400">暂无知识库</span>
              )}
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">检索数量 (top_k)</label>
              <input
                type="number"
                value={agentForm.top_k}
                onChange={(e) => onSetAgentForm({ ...agentForm, top_k: +e.target.value })}
                className="w-full text-sm border rounded-lg px-3 py-2 input-base"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">相似度阈值 (%)</label>
              <input
                type="number"
                value={agentForm.threshold}
                onChange={(e) => onSetAgentForm({ ...agentForm, threshold: +e.target.value })}
                className="w-full text-sm border rounded-lg px-3 py-2 input-base"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">重排数量</label>
              <input
                type="number"
                value={agentForm.rerank_top_k}
                onChange={(e) =>
                  onSetAgentForm({ ...agentForm, rerank_top_k: +e.target.value })
                }
                className="w-full text-sm border rounded-lg px-3 py-2 input-base"
              />
            </div>
          </div>
        </FormModal>
      )}
    </div>
  );
}
