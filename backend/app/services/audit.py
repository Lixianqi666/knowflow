"""审计日志服务"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

# 敏感 key 黑名单
_SENSITIVE_KEYS = frozenset({
    "password", "token", "secret", "authorization", "api_key",
    "access_token", "refresh_token", "hashed_password", "credential",
})

# metadata 值最大长度
_MAX_VALUE_LEN = 200


def _sanitize_metadata(meta: dict[str, Any] | None) -> dict[str, Any]:
    """清洗 metadata，移除敏感 key，截断长值"""
    if not meta or not isinstance(meta, dict):
        return {}
    clean = {}
    for k, v in meta.items():
        if k.lower() in _SENSITIVE_KEYS:
            continue
        if isinstance(v, str) and len(v) > _MAX_VALUE_LEN:
            v = v[:_MAX_VALUE_LEN] + "..."
        clean[k] = v
    return clean


async def log(
    db: AsyncSession,
    user_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    detail: str | None = None,
    ip: str | None = None,
):
    """兼容旧版接口"""
    try:
        db.add(
            AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                detail=detail,
                ip=ip,
            )
        )
        await db.flush()
    except Exception as e:
        logger.warning(f"审计日志写入失败: {e}")


async def record_audit_event(
    db: AsyncSession,
    *,
    actor_user=None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    status: str = "success",
    request=None,
    metadata: dict[str, Any] | None = None,
    detail: str | None = None,
):
    """记录审计事件，失败不影响主流程"""
    try:
        actor_email = None
        user_id = None
        ip = None
        user_agent = None

        if actor_user:
            user_id = str(actor_user.id) if hasattr(actor_user, "id") else None
            actor_email = getattr(actor_user, "email", None)

        if request:
            ip = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent", "")[:500] if request.headers else None

        clean_meta = _sanitize_metadata(metadata)

        db.add(
            AuditLog(
                user_id=user_id,
                actor_email=actor_email,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id) if resource_id else None,
                status=status,
                detail=detail,
                ip=ip,
                user_agent=user_agent,
                metadata_=clean_meta,
            )
        )
        # 不在这里 flush，由调用方决定何时 flush/commit
    except Exception as e:
        logger.warning(f"审计日志写入失败: {e}")
