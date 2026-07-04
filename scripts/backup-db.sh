#!/bin/sh
# 数据库备份脚本
set -eu

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/knowflow-${TIMESTAMP}.sql"

mkdir -p "${BACKUP_DIR}"

echo "开始备份数据库..."

# 尝试通过 docker compose exec 备份
if docker compose exec -T postgres pg_dump -U knowflow knowflow > "${BACKUP_FILE}" 2>/dev/null; then
  SIZE=$(wc -c < "${BACKUP_FILE}")
  echo "备份完成: ${BACKUP_FILE} (${SIZE} bytes)"
else
  echo "FAIL: 数据库备份失败"
  rm -f "${BACKUP_FILE}"
  exit 1
fi
