import hashlib
import logging

from sqlalchemy import delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import embedding_service
from app.models.document import Document, DocumentChunk
from app.pipeline.chunker import chunker

logger = logging.getLogger(__name__)


def _build_tsvector(content: str) -> str | None:
    """jieba 分词后构建 tsvector 字符串（空格分隔），保留中文单字"""
    import re

    import jieba

    words = jieba.cut_for_search(content)
    tokens = []
    for w in words:
        w = w.strip()
        if not w:
            continue
        # 短于2的英文/数字过滤，但中文单字保留（如人名"赵六"→"赵""六"）
        if len(w) < 2 and not re.search(r"[一-鿿]", w):
            continue
        tokens.append(w)
    return " ".join(tokens) if tokens else None


async def index_document(db: AsyncSession, document: Document) -> None:
    """对单个文档进行分块+向量化+写入（embedding失败时跳过向量化，用全文搜索兜底）"""
    document.status = "processing"
    await db.flush()

    chunks = chunker.chunk(document.content, {"title": document.title})
    if not chunks:
        document.status = "indexed"
        return

    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))

    texts = [c["content"] for c in chunks]

    # 尝试向量化，失败则跳过（后续用全文搜索）
    embeddings = None
    try:
        embeddings = await embedding_service.embed(texts)
    except Exception as e:
        logger.warning(f"Embedding失败，使用全文搜索模式: {e}")

    for i, chunk_data in enumerate(chunks):
        emb = embeddings[i] if embeddings else None
        tsv_str = _build_tsvector(chunk_data["content"])
        db.add(
            DocumentChunk(
                document_id=document.id,
                chunk_index=chunk_data["index"],
                content=chunk_data["content"],
                embedding=emb,
                tsvector_content=func.to_tsvector("simple", tsv_str) if tsv_str else None,
                metadata_=chunk_data["metadata"],
            )
        )

    document.status = "indexed"
    document.content_hash = hashlib.md5(document.content.encode()).hexdigest()

    # webhook
    from app.services.webhook import dispatch

    await dispatch(
        db,
        "document.indexed",
        {
            "document_id": str(document.id),
            "title": document.title,
            "status": "indexed",
        },
    )
