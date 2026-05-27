'use client';

import { Template } from './types';
import FormModal from '@/components/FormModal';

interface TemplateForm {
  id?: string;
  name: string;
  description: string;
  context_prompt: string;
  no_context_prompt: string;
  top_k: number;
  threshold: number;
  rerank_top_k: number;
}

interface TemplatesTabProps {
  templates: Template[];
  templateForm: TemplateForm | null;
  savingTemplate: boolean;
  onSetTemplateForm: (form: TemplateForm | null) => void;
  onOpenEditForm: (t: Template) => void;
  onToggleActive: (t: Template) => void;
  onSave: () => void;
}

export default function TemplatesTab({
  templates,
  templateForm,
  savingTemplate,
  onSetTemplateForm,
  onOpenEditForm,
  onToggleActive,
  onSave,
}: TemplatesTabProps) {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-500">配置不同问答场景的 prompt 风格和检索参数</p>
        <button
          onClick={() =>
            onSetTemplateForm({
              name: '',
              description: '',
              context_prompt: '',
              no_context_prompt: '',
              top_k: 5,
              threshold: 30,
              rerank_top_k: 3,
            })
          }
          className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          新建场景
        </button>
      </div>
      <div className="space-y-2">
        {templates.length === 0 ? (
          <div className="py-12 text-center text-gray-400 text-sm">
            暂无场景模板，点击上方按钮创建
          </div>
        ) : (
          templates.map((t) => (
            <div key={t.id} className="bg-white rounded-xl shadow-sm border p-4">
              <div className="flex items-center justify-between">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{t.name}</span>
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded ${t.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}
                    >
                      {t.is_active ? '启用' : '停用'}
                    </span>
                  </div>
                  {t.description && (
                    <p className="text-xs text-gray-400 mt-0.5">{t.description}</p>
                  )}
                  <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                    <span>top_k={t.top_k}</span>
                    <span>阈值={t.threshold}%</span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => onOpenEditForm(t)}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    编辑
                  </button>
                  <button
                    onClick={() => onToggleActive(t)}
                    className="text-xs text-gray-500 hover:text-blue-600"
                  >
                    {t.is_active ? '停用' : '启用'}
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
      {templateForm && (
        <FormModal
          open={!!templateForm}
          title={templateForm.name ? '编辑场景' : '新建场景'}
          onClose={() => onSetTemplateForm(null)}
          footer={
            <>
              <button
                onClick={() => onSetTemplateForm(null)}
                className="px-4 py-2 text-sm text-gray-600 border rounded-lg hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={onSave}
                disabled={savingTemplate}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {savingTemplate ? '保存中...' : '保存'}
              </button>
            </>
          }
        >
          <div>
            <label className="text-xs text-gray-500 mb-1 block">名称</label>
            <input
              value={templateForm.name}
              onChange={(e) => onSetTemplateForm({ ...templateForm, name: e.target.value })}
              className="w-full text-sm border rounded-lg px-3 py-2 input-base"
              placeholder="如：HR场景、技术问答"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">描述</label>
            <input
              value={templateForm.description}
              onChange={(e) =>
                onSetTemplateForm({ ...templateForm, description: e.target.value })
              }
              className="w-full text-sm border rounded-lg px-3 py-2 input-base"
              placeholder="简短描述该场景的用途"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">有上下文时的系统提示</label>
            <textarea
              value={templateForm.context_prompt}
              onChange={(e) =>
                onSetTemplateForm({ ...templateForm, context_prompt: e.target.value })
              }
              className="w-full text-sm border rounded-lg px-3 py-2 h-24 input-base font-mono"
              placeholder="检索到相关文档时使用的 prompt，告知 AI 如何回答"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">无上下文时的系统提示</label>
            <textarea
              value={templateForm.no_context_prompt}
              onChange={(e) =>
                onSetTemplateForm({ ...templateForm, no_context_prompt: e.target.value })
              }
              className="w-full text-sm border rounded-lg px-3 py-2 h-24 input-base font-mono"
              placeholder="未检索到相关文档时使用的 prompt"
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">检索数量 (top_k)</label>
              <input
                type="number"
                value={templateForm.top_k}
                onChange={(e) => onSetTemplateForm({ ...templateForm, top_k: +e.target.value })}
                className="w-full text-sm border rounded-lg px-3 py-2 input-base"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">相似度阈值 (%)</label>
              <input
                type="number"
                value={templateForm.threshold}
                onChange={(e) =>
                  onSetTemplateForm({ ...templateForm, threshold: +e.target.value })
                }
                className="w-full text-sm border rounded-lg px-3 py-2 input-base"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">重排数量</label>
              <input
                type="number"
                value={templateForm.rerank_top_k}
                onChange={(e) =>
                  onSetTemplateForm({ ...templateForm, rerank_top_k: +e.target.value })
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
