#!/bin/sh
set -e

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="knowflow_${TIMESTAMP}.sql.gz"

# 保留最近 7 天的备份
KEEP_DAYS=${BACKUP_KEEP_DAYS:-7}

echo "[$(date)] 开始备份..."

pg_dump -h postgres -U knowflow -d knowflow | gzip > "${BACKUP_DIR}/${FILENAME}"

# 清理旧备份
find "${BACKUP_DIR}" -name "knowflow_*.sql.gz" -mtime +${KEEP_DAYS} -delete

echo "[$(date)] 备份完成: ${FILENAME}"
