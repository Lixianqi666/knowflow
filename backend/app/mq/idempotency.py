"""幂等落库：task_idempotency 表操作"""

import logging
import os

import psycopg2

logger = logging.getLogger(__name__)

_db_url = None


def _get_conn():
    global _db_url
    if _db_url is None:
        _db_url = os.getenv("DATABASE_URL", "").replace("+asyncpg", "").replace("+psycopg2", "")
    return psycopg2.connect(_db_url)


def is_duplicate(idempotency_key: str) -> bool:
    """检查是否已处理完成"""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT status FROM task_idempotency WHERE idempotency_key = %s", (idempotency_key,)
            )
            row = cur.fetchone()
            return row is not None and row[0] == "completed"
    finally:
        conn.close()


def mark_processing(idempotency_key: str, task_id: str):
    """标记为处理中（INSERT ON CONFLICT DO NOTHING）"""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO task_idempotency (idempotency_key, task_id, task_type, status)
                   VALUES (%s, %s, 'index_document', 'processing')
                   ON CONFLICT (idempotency_key) DO NOTHING""",
                (idempotency_key, task_id),
            )
            conn.commit()
    finally:
        conn.close()


def mark_completed(idempotency_key: str):
    """标记为完成"""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                (
                    "UPDATE task_idempotency "
                    "SET status = 'completed', completed_at = NOW() "
                    "WHERE idempotency_key = %s"
                ),
                (idempotency_key,),
            )
            conn.commit()
    finally:
        conn.close()


def mark_failed(idempotency_key: str):
    """标记为失败"""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE task_idempotency SET status = 'failed' WHERE idempotency_key = %s",
                (idempotency_key,),
            )
            conn.commit()
    finally:
        conn.close()
