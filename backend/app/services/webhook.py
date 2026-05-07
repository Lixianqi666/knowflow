import hashlib
import hmac
import json
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook

logger = logging.getLogger(__name__)


async def dispatch(db: AsyncSession, event: str, payload: dict):
    """向所有订阅了该事件的活跃 webhook 发送通知"""
    result = await db.execute(
        select(Webhook).where(
            Webhook.is_active.is_(True),
            Webhook.events.like(f"%{event}%"),
        )
    )
    hooks = result.scalars().all()
    if not hooks:
        return

    body = json.dumps({"event": event, "payload": payload}, ensure_ascii=False).encode()

    async with httpx.AsyncClient(timeout=10) as client:
        for hook in hooks:
            try:
                headers = {"Content-Type": "application/json"}
                if hook.secret:
                    sig = hmac.new(hook.secret.encode(), body, hashlib.sha256).hexdigest()
                    headers["X-Webhook-Signature"] = sig
                await client.post(hook.url, content=body, headers=headers)
                logger.debug(f"webhook sent: {event} -> {hook.url}")
            except Exception as e:
                logger.warning(f"webhook failed: {hook.url} - {e}")
