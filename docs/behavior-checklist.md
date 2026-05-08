# KnowFlow 行为对照清单

> Java 重构验收标准：每个检查项必须 Python 和 Java 行为一致。

## 1. 认证模块

| # | 检查项 | Python 行为 | Java 行为 | 状态 |
|---|--------|------------|----------|------|
| 1.1 | 注册成功 | 200 + {access_token, token_type, user} | | |
| 1.2 | 注册重复邮箱 | 400 + {detail: "..."} | | |
| 1.3 | 登录成功 | 200 + {access_token, token_type, user} | | |
| 1.4 | 登录密码错误 | 401 + {detail: "..."} | | |
| 1.5 | Token 过期 | 401 | | |
| 1.6 | 无效 Token | 401 | | |

## 2. 对话模块

| # | 检查项 | Python 行为 | Java 行为 | 状态 |
|---|--------|------------|----------|------|
| 2.1 | 创建对话 | 200 + {id, title, created_at, updated_at} | | |
| 2.2 | 列表对话 | 200 + [ConversationOut] | | |
| 2.3 | 修改对话标题 | 200 + ConversationOut | | |
| 2.4 | 删除对话 | 200 + {detail: "已删除"} | | |
| 2.5 | 获取消息列表 | 200 + [MessageOut] | | |
| 2.6 | 消息评分 | 200 + {detail: "已评分", rating: 1/-1} | | |
| 2.7 | 导出 JSON | StreamingResponse (application/json) | | |
| 2.8 | 导出 Markdown | StreamingResponse (text/markdown) | | |

## 3. SSE 流式对话

| # | 检查项 | Python 行为 | Java 行为 | 状态 |
|---|--------|------------|----------|------|
| 3.1 | 第一个事件是 sources | type=sources, data=[{title,content,score}] | | |
| 3.2 | token 事件连续输出 | type=token, data=string | | |
| 3.3 | structured 事件（有上下文） | type=structured, data={answer,sources,confidence,has_sufficient_context} | | |
| 3.4 | 最后一个事件是 done | type=done | | |
| 3.5 | 异常时发送 error 事件 | type=error, data="服务内部错误: ..." | | |
| 3.6 | Content-Type | text/event-stream | | |
| 3.7 | 无上下文时无 structured 事件 | 只有 sources + token + done | | |

## 4. 文档模块

| # | 检查项 | Python 行为 | Java 行为 | 状态 |
|---|--------|------------|----------|------|
| 4.1 | 上传 txt | 200 + {id, title, status} | | |
| 4.2 | 上传不支持格式 | 400 + {detail: "不支持..."} | | |
| 4.3 | 文档列表 | 200 + {total, items: [...]} | | |
| 4.4 | 文档详情 | 200 + {id, title, content[:5000], status} | | |
| 4.5 | 删除文档 | 200 + {detail: "已删除"} | | |
| 4.6 | 批量删除 | 200 + {detail: "已删除 N 个文档"} | | |
| 4.7 | 批量重建索引 | 200 + {detail: "已触发 N 个文档重新索引"} | | |
| 4.8 | 获取 chunks | 200 + {document, chunks: [...]} | | |
| 4.9 | 下载原文件 | FileResponse | | |
| 4.10 | 权限过滤（非管理员） | 只返回有权限的文档 | | |

## 5. 知识库模块

| # | 检查项 | Python 行为 | Java 行为 | 状态 |
|---|--------|------------|----------|------|
| 5.1 | 创建知识库 | 200 + {id, name, description} | | |
| 5.2 | 列表知识库 | 200 + [{id, name, description, created_at}] | | |
| 5.3 | 修改知识库 | 200 + {id, name, description} | | |
| 5.4 | 删除知识库 | 200 + {detail: "已删除"} | | |

## 6. Agent 模块

| # | 检查项 | Python 行为 | Java 行为 | 状态 |
|---|--------|------------|----------|------|
| 6.1 | 创建 Agent（管理员） | 200 + {id, name} | | |
| 6.2 | Agent 列表（用户） | 200 + [{id, name, description, top_k, threshold}] | | |
| 6.3 | Agent 详情（用户） | 200 + {id, name, ..., is_active} | | |
| 6.4 | 创建会话 | 200 + {id, agent_id, title} | | |
| 6.5 | 会话列表 | 200 + [{id, agent_id, title, created_at}] | | |
| 6.6 | Agent SSE 对话 | 同普通对话 SSE 格式 | | |
| 6.7 | 消息评分 | 200 + {detail: "已评分", rating} | | |

## 7. 管理后台

| # | 检查项 | Python 行为 | Java 行为 | 状态 |
|---|--------|------------|----------|------|
| 7.1 | 用户列表 | 200 + [{id, email, name, role, is_active}] | | |
| 7.2 | 修改用户 | 200 + {id, email, name, role, is_active} | | |
| 7.3 | 不能修改自己角色 | 400 | | |
| 7.4 | 统计数据 | 200 + {users, documents, conversations, ...} | | |
| 7.5 | 文档权限列表 | 200 + [{user_id, name, email, permission}] | | |
| 7.6 | 授权 | 200 + {detail: "已授权"} | | |
| 7.7 | 撤销权限 | 200 + {detail: "已撤销"} | | |

## 8. 其他模块

| # | 检查项 | Python 行为 | Java 行为 | 状态 |
|---|--------|------------|----------|------|
| 8.1 | Prompt 模板列表（公开） | 200 + [{id, name, ...}] | | |
| 8.2 | 反馈记录 | 200 + {detail: "反馈已记录", id} | | |
| 8.3 | 审计日志（管理员） | 200 + [{id, user_id, action, ...}] | | |
| 8.4 | Webhook CRUD | 标准 REST 响应 | | |
| 8.5 | MCP 工具调用 | 200 + 工具特定结果 | | |
| 8.6 | 健康检查 | 200 + {status: "ok"} | | |

## 9. 权限与安全

| # | 检查项 | Python 行为 | Java 行为 | 状态 |
|---|--------|------------|----------|------|
| 9.1 | 无 Token 访问受保护接口 | 403 | | |
| 9.2 | 伪造 Token | 401 | | |
| 9.3 | 普通用户访问管理接口 | 403 | | |
| 9.4 | 非 owner 访问他人对话 | 403/404 | | |
| 9.5 | 文档权限过滤生效 | 非管理员只能看到授权文档 | | |

## 验收标准

- [ ] 所有检查项 Java 行为列已填写
- [ ] 所有检查项状态为 PASS
- [ ] SSE 事件顺序与格式完全一致
- [ ] 错误响应格式 {detail: "..."} 一致
- [ ] HTTP 状态码一致
