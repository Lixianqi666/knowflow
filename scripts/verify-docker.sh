#!/bin/sh
# 本地 Docker 验证脚本 — 不在宿主机安装任何依赖
# 与 CI backend-test / frontend-test 使用同款命令
set -e

cleanup() {
  echo ">>> 清理容器..."
  docker compose down 2>/dev/null || true
}
trap cleanup EXIT

echo "=== 1. 验证 docker compose 配置 ==="
docker compose config --quiet
echo "OK"

echo "=== 2. 构建后端镜像 ==="
docker compose build backend
echo "OK"

echo "=== 3. 构建前端测试镜像 ==="
docker build --target test -t knowflow-frontend-test ./frontend
echo "OK"

echo "=== 4. 启动依赖服务 ==="
docker compose up -d postgres redis
echo "OK"

echo "=== 5. 后端测试（与 CI 一致） ==="
docker compose run --rm backend sh -c \
  "TESTING=1 pytest tests/test_auth.py tests/test_chat.py tests/test_goal_context.py tests/test_prompts.py tests/test_webhooks.py tests/test_documents.py tests/test_knowledge_bases.py tests/test_agents_api.py tests/test_indexing_lock.py tests/test_metrics.py -q --tb=short"
echo "OK"

echo "=== 6. 前端测试 ==="
docker run --rm knowflow-frontend-test sh -c "npm run test"
echo "OK"

echo "=== 7. 前端构建验证 ==="
docker compose build frontend
echo "OK"

echo "=== 全部通过 ==="
