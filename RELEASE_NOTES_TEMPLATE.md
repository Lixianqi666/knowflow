# KnowFlow vX.Y.Z Release Notes

## 基本信息

| 项目 | 内容 |
|------|------|
| 版本号 | vX.Y.Z |
| 发布日期 | YYYY-MM-DD |
| 适用环境 | 生产 / 测试 / 开发 |
| 最低 Docker 版本 | 24.0+ |
| 最低 Docker Compose 版本 | v2.20+ |

## 新增功能

- 功能 1：说明
- 功能 2：说明

## 修复内容

- 修复 1：说明
- 修复 2：说明

## 安全更新

- 安全修复 1：说明
- 安全修复 2：说明

## 数据库迁移

- [ ] 是否包含 migration：是 / 否
- Migration 文件：`0XX_description.py`
- 向后兼容：是 / 否
- 回滚支持：是 / 否

## 运维注意事项

- 注意事项 1
- 注意事项 2

## 升级步骤

```bash
# 1. 备份
bash scripts/backup-db.sh

# 2. 拉取新版本
git pull origin main

# 3. 构建部署
docker compose up -d --build
docker compose restart nginx

# 4. 验证
bash scripts/release-smoke.sh
```

## 回滚步骤

```bash
# 1. 停止服务
docker compose down

# 2. 恢复代码
git checkout <previous-commit>

# 3. 恢复数据库（如需要）
bash scripts/restore-db.sh ./backups/<backup-file>

# 4. 重建启动
docker compose up -d --build
docker compose restart nginx

# 5. 验证
bash scripts/release-smoke.sh
```

## 已知问题

- 问题 1：说明 + 影响范围 + 规避方案

## 验证结果

| 验证项 | 结果 |
|--------|------|
| CI 全绿 | ✓ / ✗ |
| 后端测试 | X passed, Y skipped |
| 前端测试 | X passed |
| Trivy 扫描 | 通过 / 有豁免 |
| Smoke Test | 通过 |
| UAT 验收 | 通过 / 有条件通过 / 未完成 |

## 已知风险

| 编号 | 描述 | 影响 | 规避方案 |
|------|------|------|----------|
| | | | |

## 遗留问题

| 编号 | 描述 | 计划修复版本 |
|------|------|--------------|
| | | |

## 确认签字

| 角色 | 姓名 | 日期 | 签字 |
|------|------|------|------|
| 发布人 | | | |
| 审核人 | | | |
| 客户确认人 | | | |
| 实施确认人 | | | |
