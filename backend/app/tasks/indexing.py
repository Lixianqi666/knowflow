import asyncio
import hashlib
import logging

from sqlalchemy import delete, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.core.celery import celery_app
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
            await db.commit()

            chunks = chunker.chunk(doc.content, {"title": doc.title})
            if not chunks:
                doc.status = "indexed"
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
            logger.info(f"文档索引完成: {doc.title}")
    finally:
        await engine.dispose()


@celery_app.task(name="index_document", bind=True, max_retries=2, default_retry_delay=30)
def index_document_task(self, document_id: str):
    """Celery 入口：运行异步索引"""
    try:
        asyncio.run(_index(document_id))
    except Exception as e:
        logger.exception(f"文档索引失败: {e}")
        raise self.retry(exc=e)
