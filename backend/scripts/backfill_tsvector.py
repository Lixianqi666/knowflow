"""回填已有 document_chunks 的 tsvector_content 列

用法: docker compose exec backend python -m scripts.backfill_tsvector
"""
import asyncio
import logging

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine, async_session
from app.models.document import DocumentChunk
from app.pipeline.indexer import _build_tsvector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill():
    async with async_session() as db:
        # 统计需要回填的数量
        count_result = await db.execute(
            select(func.count()).where(DocumentChunk.tsvector_content.is_(None))
        )
        total = count_result.scalar()
        logger.info(f"需要回填的 chunk 数量: {total}")

        if total == 0:
            logger.info("无需回填")
            return

        # 分批处理
        batch_size = 100
        offset = 0
        filled = 0

        while offset < total:
            result = await db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.tsvector_content.is_(None))
                .limit(batch_size)
            )
            chunks = result.scalars().all()
            if not chunks:
                break

            for chunk in chunks:
                tsv_str = _build_tsvector(chunk.content)
                if tsv_str:
                    chunk.tsvector_content = func.to_tsvector('simple', tsv_str)
                filled += 1

            await db.commit()
            offset += len(chunks)
            logger.info(f"已回填 {offset}/{total}")

        logger.info(f"回填完成，共处理 {filled} 个 chunk")


if __name__ == "__main__":
    asyncio.run(backfill())
