# Changelog

本文件记录 KnowFlow 的版本变更。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [SemVer](https://semver.org/lang/zh-CN/)。

## 0.1.0 - 2026-05-31

### Added
- RAG 问答系统：向量检索 + BM25 + RRF 融合 + LLM 流式生成
- 多知识库管理：文档上传（TXT/MD/PDF/DOCX/XLSX）、分块、索引
- Agent 对话：可配置系统提示词、关联知识库、调试与发布版本管理
- 管理后台：用户管理、文档权限、数据统计、审计日志、健康面板
- RAG Eval 评测集：标准问题、期望引用、运行评测、结果追踪
- 多轮目标对话：goal 持久化、LLM 状态更新、GoalBar 组件
- SSE 断线重连：3 次指数退避、abort-aware、serverError 不重试
- 审计日志：登录、上传、删除、反馈、评测等关键操作追踪
- 知识库成员权限：owner/editor/viewer 角色、权限继承
- 企业账号治理：密码策略、账号禁用、登录失败审计、SSO 预留
- 私有化交付脚本：preflight、备份、恢复、smoke test
- 版本化发布：VERSION、CHANGELOG、Release Notes 模板、交付包说明

### Changed
- Docker 化全部验证流程，不在宿主机安装依赖
- CI 高危漏洞扫描策略（Trivy exit-code: 1）
- 文档状态闭环：pending/processing/indexed/failed + 重试
- Prompt 注入防护：retrieved_documents XML 边界 + 安全警告
- 无依据拒答规则：检索不足时明确告知用户

### Security
- Webhook SSRF 防护：DNS 解析 + IP 校验
- SQL 注入修复：Webhook 事件精确匹配
- 文档权限 read/write 区分：DocumentPermission 优先于 SourcePermission
- 注册防邮箱枚举：统一错误文案
- Token 生命周期：短期 access + 长期 refresh + Redis 黑名单 + 轮换
- 审计日志：敏感 metadata 清洗、关键操作全覆盖
- 安全头：X-Content-Type-Options、X-Frame-Options、Referrer-Policy
