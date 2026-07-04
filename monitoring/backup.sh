#!/bin/sh
# KnowFlow 数据库备份脚本（POSIX sh 兼容）
# 环境变量：POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, PGPASSWORD, BACKUP_KEEP_DAYS

set -e

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/knowflow_${DATE}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] 开始备份数据库 ${POSTGRES_DB:-knowflow}..."

pg_dump \
  -h "${POSTGRES_HOST:-postgres}" \
  -p "${POSTGRES_PORT:-5432}" \
  -U "${POSTGRES_USER:-knowflow}" \
  -d "${POSTGRES_DB:-knowflow}" \
  --no-owner \
  --no-privileges \
  | gzip > "${BACKUP_FILE}"

echo "[$(date)] 备份完成: ${BACKUP_FILE}"

# 清理旧备份
KEEP_DAYS="${BACKUP_KEEP_DAYS:-7}"
find "${BACKUP_DIR}" -name "knowflow_*.sql.gz" -type f -mtime +"${KEEP_DAYS}" -delete
echo "[$(date)] 已清理 ${KEEP_DAYS} 天前的旧备份"
