'use client';

import { User } from './types';

interface UsersTabProps {
  users: User[];
  currentUserId?: string;
  onRoleToggle: (u: User) => void;
  onActiveToggle: (u: User) => void;
}

export default function UsersTab({
  users,
  currentUserId,
  onRoleToggle,
  onActiveToggle,
}: UsersTabProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
      {/* 桌面端表格 */}
      <table className="w-full text-sm hidden md:table">
        <thead className="bg-gray-50 text-gray-600">
          <tr>
            <th className="text-left px-4 py-3 font-medium">用户</th>
            <th className="text-left px-4 py-3 font-medium">邮箱</th>
            <th className="text-center px-4 py-3 font-medium">角色</th>
            <th className="text-center px-4 py-3 font-medium">状态</th>
            <th className="text-center px-4 py-3 font-medium">操作</th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {users.map((u) => (
            <tr key={u.id} className="hover:bg-gray-50">
              <td className="px-4 py-3 font-medium">{u.name}</td>
              <td className="px-4 py-3 text-gray-500">{u.email}</td>
              <td className="px-4 py-3 text-center">
                <span
                  className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                    u.role === 'admin'
                      ? 'bg-purple-100 text-purple-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {u.role === 'admin' ? '管理员' : '成员'}
                </span>
              </td>
              <td className="px-4 py-3 text-center">
                <span
                  className={`inline-block w-2 h-2 rounded-full ${
                    u.is_active ? 'bg-green-500' : 'bg-red-400'
                  }`}
                />
              </td>
              <td className="px-4 py-3 text-center space-x-2">
                {u.id !== currentUserId && (
                  <button
                    onClick={() => onRoleToggle(u)}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    {u.role === 'admin' ? '设为成员' : '设为管理员'}
                  </button>
                )}
                {u.id !== currentUserId && (
                  <button
                    onClick={() => onActiveToggle(u)}
                    className={`text-xs hover:underline ${
                      u.is_active ? 'text-red-500' : 'text-green-600'
                    }`}
                  >
                    {u.is_active ? '禁用' : '启用'}
                  </button>
                )}
                {u.id === currentUserId && <span className="text-xs text-gray-400">当前用户</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {/* 移动端卡片 */}
      <div className="md:hidden divide-y">
        {users.map((u) => (
          <div key={u.id} className="p-3">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2 min-w-0">
                <span className="font-medium text-sm truncate">{u.name}</span>
                <span
                  className={`text-xs px-1.5 py-0.5 rounded-full shrink-0 ${
                    u.role === 'admin'
                      ? 'bg-purple-100 text-purple-700'
                      : 'bg-gray-100 text-gray-600'
                  }`}
                >
                  {u.role === 'admin' ? '管理员' : '成员'}
                </span>
                <span
                  className={`w-2 h-2 rounded-full shrink-0 ${
                    u.is_active ? 'bg-green-500' : 'bg-red-400'
                  }`}
                />
              </div>
            </div>
            <div className="text-xs text-gray-500 truncate mb-2">{u.email}</div>
            {u.id !== currentUserId ? (
              <div className="flex items-center gap-3">
                <button onClick={() => onRoleToggle(u)} className="text-xs text-blue-600">
                  {u.role === 'admin' ? '设为成员' : '设为管理员'}
                </button>
                <button
                  onClick={() => onActiveToggle(u)}
                  className={`text-xs ${u.is_active ? 'text-red-500' : 'text-green-600'}`}
                >
                  {u.is_active ? '禁用' : '启用'}
                </button>
              </div>
            ) : (
              <span className="text-xs text-gray-400">当前用户</span>
            )}
          </div>
        ))}
      </div>
      {users.length === 0 && <div className="py-12 text-center text-gray-400">暂无用户</div>}
    </div>
  );
}
