"""查询改写 — 用 LLM 扩展/改写用户查询，提高 BM25 召回率"""

import logging

from app.config import settings

logger = logging.getLogger(__name__)


async def rewrite(query: str, history: str = "") -> str:
    """用 LLM 改写查询：解析代词指代、补充专有名词/件号"""
    if not query.strip():
        return query

    from litellm import acompletion

    try:
        system_prompt = (
            "你是搜索查询改写助手。任务：1) 将代词（这个、它、该型号等）替换为对话历史中的具体实体 "
            "2) 提取关键术语和件号 3) 不要解释，只输出改写后的查询"
        )
        user_prompt = f"当前问题：{query}"
        if history:
            # 提取历史中的专有名词（件号、型号等）
            import re

            entities = re.findall(r"[A-Z]{2,}-[A-Z0-9]+[-A-Z0-9]*", history)
            if entities:
                user_prompt = (
                    f"已知实体：{' '.join(entities)}\n对话历史：{history}\n当前问题：{query}"
                )

        kwargs = dict(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=100,
            timeout=30,
        )
        if settings.LLM_API_KEY:
            kwargs["api_key"] = settings.LLM_API_KEY
        if settings.LLM_BASE_URL:
            kwargs["api_base"] = settings.LLM_BASE_URL

        resp = await acompletion(**kwargs)
        rewritten = resp.choices[0].message.content.strip().strip('"').strip("'")
        if rewritten and len(rewritten) <= 200 and rewritten != query:
            logger.info(f"查询改写: '{query[:30]}' -> '{rewritten[:60]}'")
            return rewritten
    except Exception as e:
        logger.debug(f"查询改写失败: {e}")

    return query
