'use client';

import { DocItem, DocPerm, User } from './types';

interface PermissionsTabProps {
  docs: DocItem[];
  docPerms: Record<string, DocPerm[]>;
  searchingDocId: string | null;
  searchQuery: string;
  searchResults: User[];
  searchLoading: boolean;
  onSetSearchingDocId: (id: string | null) => void;
  onSearch: (docId: string, query: string) => void;
  onGrant: (docId: string, userId: string) => void;
  onRevoke: (docId: string, userId: string) => void;
  searchRef: React.RefObject<HTMLDivElement | null>;
}

export default function PermissionsTab({
  docs,
  docPerms,
  searchingDocId,
  searchQuery,
  searchResults,
  searchLoading,
  onSetSearchingDocId,
  onSearch,
  onGrant,
  onRevoke,
  searchRef,
}: PermissionsTabProps) {
  return (
    <div className="space-y-3">
      {docs.length === 0 ? (
        <div className="py-12 text-center text-gray-400 text-sm">暂无文档</div>
      ) : (
        docs.map((doc) => {
          const perms = docPerms[doc.id] || [];
          const isSearching = searchingDocId === doc.id;
          return (
            <div key={doc.id} className="bg-white rounded-xl shadow-sm border p-3 md:p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-sm font-medium truncate">{doc.title}</span>
                  <span
                    className={`text-xs px-1.5 py-0.5 rounded ${
                      doc.status === 'indexed'
                        ? 'bg-green-100 text-green-700'
                        : 'bg-yellow-100 text-yellow-700'
                    }`}
                  >
                    {doc.status === 'indexed' ? '已索引' : doc.status}
                  </span>
                </div>
                <div className="relative shrink-0" ref={isSearching ? searchRef : undefined}>
                  <button
                    onClick={() => {
                      onSetSearchingDocId(isSearching ? null : doc.id);
                      onSearch(doc.id, '');
                    }}
                    className="text-xs px-3 py-1.5 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100"
                  >
                    授予权限
                  </button>
                  {isSearching && (
                    <div className="absolute right-0 top-full mt-1 w-72 bg-white border rounded-xl shadow-lg z-10">
                      <input
                        autoFocus
                        type="text"
                        placeholder="搜索用户名或邮箱..."
                        value={searchQuery}
                        onChange={(e) => onSearch(doc.id, e.target.value)}
                        className="w-full px-3 py-2 text-sm border-b rounded-t-xl input-base"
                      />
                      <div className="max-h-48 overflow-y-auto">
                        {searchLoading ? (
                          <div className="px-3 py-4 text-center text-gray-400 text-xs">
                            搜索中...
                          </div>
                        ) : searchResults.length === 0 ? (
                          <div className="px-3 py-4 text-center text-gray-400 text-xs">
                            {searchQuery ? '无匹配结果' : '输入关键词搜索'}
                          </div>
                        ) : (
                          searchResults.map((u) => {
                            const hasPerm = perms.some((p) => p.user_id === u.id);
                            return (
                              <button
                                key={u.id}
                                disabled={hasPerm}
                                onClick={() => onGrant(doc.id, u.id)}
                                className={`w-full px-3 py-2 text-left text-sm flex items-center justify-between hover:bg-gray-50 ${
                                  hasPerm ? 'opacity-50 cursor-not-allowed' : ''
                                }`}
                              >
                                <div>
                                  <span className="font-medium">{u.name}</span>
                                  <span className="text-gray-400 ml-2 text-xs">
                                    {u.email}
                                  </span>
                                </div>
                                {hasPerm && (
                                  <span className="text-xs text-gray-400">已有权限</span>
                                )}
                              </button>
                            );
                          })
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
              {perms.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {perms.map((p) => (
                    <span
                      key={p.user_id}
                      className="inline-flex items-center gap-1 text-xs bg-gray-50 border border-gray-200 text-gray-600 rounded px-2 py-1"
                    >
                      <span>{p.name}</span>
                      <span className="text-gray-400">{p.email}</span>
                      <button
                        onClick={() => onRevoke(doc.id, p.user_id)}
                        className="ml-1 text-gray-400 hover:text-red-500"
                        title="撤销权限"
                      >
                        ✕
                      </button>
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-gray-400">无授权用户</p>
              )}
            </div>
          );
        })
      )}
    </div>
  );
}
