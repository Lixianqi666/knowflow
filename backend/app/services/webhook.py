import asyncio
import hashlib
import hmac
import json
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook

logger = logging.getLogger(__name__)


def _matches_event(events_str: str, target_event: str) -> bool:
    """精确匹配事件名，不允许前缀/后缀模糊命中"""
    for e in events_str.split(","):
        if e.strip() == target_event:
            return True
    return False


async def dispatch(db: AsyncSession, event: str, payload: dict):
    """向所有订阅了该事件的活跃 webhook 发送通知"""
    result = await db.execute(select(Webhook).where(Webhook.is_active.is_(True)))
    all_hooks = result.scalars().all()
    hooks = [h for h in all_hooks if _matches_event(h.events, event)]
    if not hooks:
        return

    body = json.dumps({"event": event, "payload": payload}, ensure_ascii=False).encode()

    async with httpx.AsyncClient(timeout=10) as client:

        async def _send(hook):
            try:
                headers = {"Content-Type": "application/json"}
                if hook.secret:
                    sig = hmac.new(hook.secret.encode(), body, hashlib.sha256).hexdigest()
                    headers["X-Webhook-Signature"] = sig
                await client.post(hook.url, content=body, headers=headers)
                logger.debug(f"webhook sent: {event} -> {hook.url}")
            except Exception as e:
                logger.warning(f"webhook failed: {hook.url} - {e}")

        await asyncio.gather(*[_send(h) for h in hooks])
