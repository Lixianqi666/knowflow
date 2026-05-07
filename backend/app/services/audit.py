import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


async def log(
    db: AsyncSession,
    user_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    detail: str | None = None,
    ip: str | None = None,
):
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
