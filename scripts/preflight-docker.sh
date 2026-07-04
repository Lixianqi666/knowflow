#!/bin/sh
# 部署前检查脚本
set -eu

echo "=== KnowFlow 部署前检查 ==="

# 检查 docker
if ! command -v docker >/dev/null 2>&1; then
  echo "FAIL: docker 未安装"
  exit 1
fi
echo "OK: docker $(docker --version | head -1)"

# 检查 docker compose
if ! docker compose version >/dev/null 2>&1; then
  echo "FAIL: docker compose 不可用"
  exit 1
fi
echo "OK: docker compose $(docker compose version --short)"

# 检查 docker compose 配置
if ! docker compose config --quiet 2>/dev/null; then
  echo "FAIL: docker compose 配置无效"
  exit 1
fi
echo "OK: docker compose 配置有效"

# 检查必要文件
for f in docker-compose.yml backend/Dockerfile frontend/Dockerfile; do
  if [ ! -f "$f" ]; then
    echo "FAIL: 缺少 $f"
    exit 1
  fi
done
echo "OK: 必要文件存在"

# 检查 nginx 配置目录
if [ ! -d "nginx/conf.d" ]; then
  echo "WARN: nginx/conf.d 目录不存在"
fi

# 检查 scripts 目录
for f in scripts/backup-db.sh scripts/restore-db.sh scripts/release-smoke.sh; do
  if [ ! -f "$f" ]; then
    echo "WARN: 缺少 $f"
  fi
done

# 检查 .env（不读取内容）
if [ ! -f ".env" ]; then
  echo "WARN: .env 文件不存在，请从 .env.example 复制并配置"
else
  echo "OK: .env 文件存在"
fi

echo ""
echo "=== 检查完成 ==="
