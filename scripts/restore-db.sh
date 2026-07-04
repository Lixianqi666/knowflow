#!/bin/sh
# 数据库恢复脚本
set -eu

if [ $# -lt 1 ]; then
  echo "用法: $0 <备份文件路径>"
  echo "示例: $0 ./backups/knowflow-20260531-120000.sql"
  exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "FAIL: 备份文件不存在: ${BACKUP_FILE}"
  exit 1
fi

echo "=== 数据库恢复 ==="
echo "备份文件: ${BACKUP_FILE}"
echo ""

# 二次确认
if [ "${FORCE:-}" != "1" ]; then
  printf "确认恢复？这将覆盖当前数据库 [y/N]: "
  read -r confirm
  if [ "${confirm}" != "y" ] && [ "${confirm}" != "Y" ]; then
    echo "已取消"
    exit 0
  fi
fi

echo "停止后端和 worker..."
docker compose stop backend worker 2>/dev/null || true

echo "恢复数据库..."
if docker compose exec -T postgres psql -U knowflow -d knowflow < "${BACKUP_FILE}" >/dev/null 2>&1; then
  echo "恢复完成"
else
  echo "FAIL: 数据库恢复失败"
  exit 1
fi

echo "重启服务..."
docker compose up -d backend worker

echo ""
echo "=== 恢复完成 ==="
echo "请验证: curl -f http://127.0.0.1/health"
