"""公共服务函数"""

import logging
import re

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings

logger = logging.getLogger(__name__)


def is_default_title(title: str) -> bool:
    """判断是否为默认标题"""
    if not title:
        return True
    return bool(re.match(r"^(新对话|New Chat|新会话)", title))


async def auto_generate_title(
    db: AsyncSession,
    obj,  # Conversation 或 AgentSession
    user_message: str,
    message_model,  # Message 或 AgentMessage
    foreign_key_field: str,  # conversation_id 或 session_id
) -> None:
    """自动生成对话标题"""
    if not is_default_title(obj.title):
        return

    count = await db.scalar(
        select(func.count()).where(getattr(message_model, foreign_key_field) == obj.id)
    )
    if count and count > 2:
        return

    try:
        from litellm import acompletion

        kwargs = dict(
            model=settings.LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "根据用户的提问，生成 4-6 个字的简短标题，只输出标题本身，不要标点。",
                },
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
            max_tokens=20,
        )
        if settings.LLM_API_KEY:
            kwargs["api_key"] = settings.LLM_API_KEY
        if settings.LLM_BASE_URL:
            kwargs["api_base"] = settings.LLM_BASE_URL
        resp = await acompletion(**kwargs)
        title = resp.choices[0].message.content.strip().strip("\"'").strip()
        if title and len(title) <= 20:
            obj.title = title
    except Exception as e:
        logger.debug(f"自动标题失败: {e}")
