import asyncio
import hashlib
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.celery import celery_app
from app.core.metrics import documents_indexed_total
from app.models import (  # noqa: F401
    audit_log,
    conversation,
    knowledge_base,
    permission,
    prompt_template,
    user,
    webhook,
)
from app.models.document import Document, DocumentChunk
from app.pipeline.chunker import chunker
from app.pipeline.indexer import _build_tsvector

logger = logging.getLogger(__name__)

LOCK_KEY_PREFIX = "lock:index_document:"
LOCK_TTL = 600


async def clear_index_lock(document_id: str) -> bool:
    """清除文档索引 Redis 锁。返回 True 表示锁已删除或不存在，False 表示连接异常。"""
    key = f"{LOCK_KEY_PREFIX}{document_id}"
    # 优先使用全局连接
    try:
        from app.core.ratelimit import get_redis

        r = await get_redis()
        await r.delete(key)
        return True
    except Exception as e:
        logger.warning(f"get_redis 删除锁失败，尝试新建连接: {e}")
    # 全局连接异常时，创建独立连接作为兜底
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            await r.delete(key)
            return True
        finally:
            await r.aclose()
    except Exception as e:
        logger.error(f"新建 Redis 连接删除锁也失败: {e}")
        return False


async def _index(document_id: str):
    """异步索引逻辑"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as db:
            doc = await db.get(Document, document_id)
            if not doc:
                logger.error(f"文档不存在: {document_id}")
                return

            doc.status = "processing"
            doc.error_message = None
            await db.commit()

            try:
                chunks = chunker.chunk(doc.content, {"title": doc.title})
                if not chunks:
                    doc.status = "indexed"
                    doc.indexed_at = datetime.now(timezone.utc)
                    doc.error_message = None
                    await db.commit()
                    return

                await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))

                texts = [c["content"] for c in chunks]

                # 尝试向量化，失败则跳过
                embeddings = None
                try:
                    from app.core.llm import embedding_service

                    embeddings = await embedding_service.embed(texts)
                except Exception as e:
                    logger.warning(f"Embedding失败，使用全文搜索模式: {e}")

                for i, chunk_data in enumerate(chunks):
                    emb = embeddings[i] if embeddings else None
                    tsv_str = _build_tsvector(chunk_data["content"])
                    db.add(
                        DocumentChunk(
                            document_id=doc.id,
                            chunk_index=chunk_data["index"],
                            content=chunk_data["content"],
                            embedding=emb,
                            tsvector_content=(func.to_tsvector("simple", tsv_str) if tsv_str else None),
                            metadata_=chunk_data["metadata"],
                        )
                    )

                doc.status = "indexed"
                doc.indexed_at = datetime.now(timezone.utc)
                doc.error_message = None
                doc.content_hash = hashlib.md5(doc.content.encode()).hexdigest()

                # webhook
                from app.services.webhook import dispatch

                await dispatch(
                    db,
                    "document.indexed",
                    {
                        "document_id": document_id,
                        "title": doc.title,
                        "status": "indexed",
                    },
                )
                await db.commit()
                documents_indexed_total.inc()
                logger.info(f"文档索引完成: {doc.title}")
            except Exception as e:
                # 安全回退：确保状态一定写入，即使 commit 失败也不卡在 processing
                doc.status = "failed"
                doc.error_message = str(e)[:500]
                try:
                    await db.commit()
                except Exception:
                    logger.exception(f"文档 {document_id} 状态写入失败，尝试回滚后重写")
                    await db.rollback()
                    try:
                        doc = await db.get(Document, document_id)
                        if doc and doc.status == "processing":
                            doc.status = "failed"
                            doc.error_message = str(e)[:500]
                            await db.commit()
                    except Exception:
                        logger.exception(f"文档 {document_id} 状态重写也失败")
                logger.exception(f"文档索引失败: {document_id} - {e}")
    finally:
        await engine.dispose()


_FALLBACK_TOKEN = "__fallback__"

_RELEASE_LUA = "if redis.call('get',KEYS[1])==ARGV[1] then return redis.call('del',KEYS[1]) else return 0 end"


async def _acquire_lock(document_id: str) -> str | None:
    """获取 Redis 幂等锁，返回 token 表示成功，None 表示已有任务在处理"""
    token = uuid.uuid4().hex
    try:
        from app.core.ratelimit import get_redis

        r = await get_redis()
        ok = await r.set(f"{LOCK_KEY_PREFIX}{document_id}", token, nx=True, ex=LOCK_TTL)
        return token if ok else None
    except Exception as e:
        logger.warning(f"Redis 锁获取异常，允许继续索引: {e}")
        return _FALLBACK_TOKEN


async def _release_lock(document_id: str, token: str):
    """释放 Redis 幂等锁，仅当 token 匹配时才删除"""
    if token == _FALLBACK_TOKEN:
        return
    try:
        from app.core.ratelimit import get_redis

        r = await get_redis()
        await r.eval(_RELEASE_LUA, 1, f"{LOCK_KEY_PREFIX}{document_id}", token)
    except Exception as e:
        logger.warning(f"Redis 锁释放异常: {e}")


async def _index_with_lock(document_id: str):
    """带幂等锁的索引入口"""
    token = await _acquire_lock(document_id)
    if token is None:
        logger.info(f"文档 {document_id} 已有索引任务在处理，跳过")
        return
    try:
        await _index(document_id)
    finally:
        await _release_lock(document_id, token)


@celery_app.task(name="index_document", bind=True, max_retries=2, default_retry_delay=30)
def index_document_task(self, document_id: str):
    """Celery 入口：运行异步索引"""
    try:
        asyncio.run(_index_with_lock(document_id))
    except Exception as e:
        logger.exception(f"文档索引失败: {e}")
        raise self.retry(exc=e)
