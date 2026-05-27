'use client';

import { Stats } from './types';

interface StatsTabProps {
  stats: Stats;
}

export default function StatsTab({ stats }: StatsTabProps) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        {[
          { label: '用户', value: stats.users },
          { label: '知识库', value: stats.knowledge_bases },
          { label: '文档', value: stats.documents },
          { label: '分块', value: stats.chunks },
          { label: '对话', value: stats.conversations },
          { label: '消息', value: stats.messages },
          { label: '今日对话', value: stats.today_conversations },
          { label: '检索命中率', value: `${stats.hit_rate}%` },
        ].map((item) => (
          <div key={item.label} className="bg-white rounded-xl shadow-sm border p-4 md:p-6">
            <div className="text-xs md:text-sm text-gray-500 mb-1">{item.label}</div>
            <div className="text-xl md:text-3xl font-bold text-gray-900">
              {item.value.toLocaleString()}
            </div>
          </div>
        ))}
      </div>
      <div className="bg-white rounded-xl shadow-sm border p-4 md:p-6">
        <div className="text-sm text-gray-500 mb-3">用户反馈</div>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="text-2xl">👍</span>
            <span className="text-xl font-bold text-green-600">{stats.praise}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">👎</span>
            <span className="text-xl font-bold text-red-500">{stats.criticism}</span>
          </div>
          <div className="text-sm text-gray-400">
            {stats.praise + stats.criticism > 0
              ? `满意度 ${((stats.praise / (stats.praise + stats.criticism)) * 100).toFixed(1)}%`
              : '暂无反馈'}
          </div>
        </div>
      </div>
    </div>
  );
}
