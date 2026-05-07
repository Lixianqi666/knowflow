import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.ratelimit import upload_rate_limit
from app.core.security import get_current_user
from app.database import get_db
from app.models.document import DataSource, Document, DocumentChunk
from app.models.permission import DocumentPermission, SourcePermission
from app.models.user import User
from app.services.audit import log as audit_log
from app.services.webhook import dispatch as webhook_dispatch
from app.tasks.indexing import index_document_task

router = APIRouter(prefix="/documents", tags=["文档"])

ALLOWED_EXT = set(settings.ALLOWED_EXTENSIONS.split(","))


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    kb_id: str | None = None,
    _: None = Depends(upload_rate_limit),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 文件类型校验（扩展名 + MIME）
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {suffix}，允许: {settings.ALLOWED_EXTENSIONS}",
        )

    # 读取文件
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413, detail=f"文件过大，最大 {settings.MAX_FILE_SIZE // 1024 // 1024}MB"
        )

    # 保存文件
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    filepath = upload_dir / file.filename
    filepath.write_bytes(content)

    # 读取文本内容
    if suffix in (".txt", ".md", ".markdown"):
        text_content = content.decode("utf-8", errors="ignore")
    elif suffix == ".pdf":
        import pdfplumber

        try:
            with pdfplumber.open(str(filepath)) as pdf:
                pages = []
                for page in pdf.pages:
                    tables = page.extract_tables()
                    page_text = page.extract_text() or ""
                    # 表格以 tab 分隔追加到文本中
                    for tbl in tables:
                        if tbl:
                            rows = ["\t".join(str(c or "") for c in row) for row in tbl]
                            page_text += "\n" + "\n".join(rows)
                    pages.append(page_text)
                text_content = "\n\n".join(pages)
        except Exception:
            text_content = ""
    elif suffix == ".docx":
        import io

        from docx import Document as DocxDocument

        doc = DocxDocument(io.BytesIO(content))
        text_content = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    elif suffix == ".xlsx":
        import io

        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(content), read_only=True)
        sections = []
        for sheet in wb.worksheets:
            sheet_name = sheet.title
            all_rows = list(sheet.iter_rows(values_only=True))
            if not all_rows:
                continue
            header = [str(c or "") for c in all_rows[0]]
            lines = [f"## 表格：{sheet_name}"]
            for row in all_rows[1:]:
                pairs = [f"{header[i]}：{str(c)}" for i, c in enumerate(row) if c is not None]
                if pairs:
                    lines.append("；".join(pairs))
            sections.append("\n".join(lines))
        text_content = "\n\n".join(sections)
    else:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {suffix}")

    if not text_content.strip():
        raise HTTPException(status_code=400, detail="文件内容为空")

    # 获取或创建本地数据源
    result = await db.execute(select(DataSource).where(DataSource.type == "local"))
    source = result.scalar_one_or_none()
    if not source:
        source = DataSource(name="本地文件", type="local", created_by=user.id)
        db.add(source)
        await db.flush()

    # 创建文档记录
    content_hash = hashlib.md5(text_content.encode()).hexdigest()
    doc = Document(
        source_id=source.id,
        kb_id=kb_id,
        external_id=file.filename,
        title=file.filename,
        content=text_content,
        content_hash=content_hash,
    )
    db.add(doc)
    await db.flush()

    # 授予上传者读权限（先 flush 保证 doc.id 可用）
    db.add(DocumentPermission(document_id=doc.id, user_id=user.id, permission="read"))
    await db.flush()

    # 异步索引（Celery 任务，不阻塞响应）
    index_document_task.delay(str(doc.id))

    return {"id": str(doc.id), "title": doc.title, "status": doc.status}


@router.get("")
async def list_documents(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    kb_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    base = select(Document)
    if kb_id:
        base = base.where(Document.kb_id == kb_id)
    # 非管理员只能看有权限的文档
    if user.role != "admin":
        base = base.where(
            Document.id.in_(
                select(DocumentPermission.document_id).where(DocumentPermission.user_id == user.id)
            )
            | Document.source_id.in_(
                select(SourcePermission.source_id).where(SourcePermission.user_id == user.id)
            )
        )
    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    result = await db.execute(base.order_by(Document.created_at.desc()).offset(offset).limit(limit))
    docs = result.scalars().all()
    return {
        "total": total or 0,
        "items": [
            {
                "id": str(d.id),
                "title": d.title,
                "status": d.status,
                "kb_id": str(d.kb_id) if d.kb_id else None,
                "created_at": str(d.created_at),
            }
            for d in docs
        ],
    }


@router.get("/{doc_id}")
async def get_document(
    doc_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    # 非管理员检查权限
    if user.role != "admin":
        perm = await db.execute(
            select(DocumentPermission).where(
                DocumentPermission.document_id == doc_id,
                DocumentPermission.user_id == user.id,
            )
        )
        if not perm.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="无权限查看该文档")
    await audit_log(db, str(user.id), "view_doc", "document", doc_id, doc.title)
    return {
        "id": str(doc.id),
        "title": doc.title,
        "content": doc.content[:5000],
        "status": doc.status,
        "created_at": str(doc.created_at),
    }


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    # 非管理员检查权限
    if user.role != "admin":
        perm = await db.execute(
            select(DocumentPermission).where(
                DocumentPermission.document_id == doc_id,
                DocumentPermission.user_id == user.id,
            )
        )
        if not perm.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="无权限删除该文档")
    await db.delete(doc)
    await webhook_dispatch(
        db,
        "document.deleted",
        {
            "document_id": doc_id,
            "title": doc.title,
            "deleted_by": str(user.id),
        },
    )
    return {"detail": "已删除"}


@router.get("/{doc_id}/chunks")
async def get_document_chunks(
    doc_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取文档的全部 chunk（用于前端高亮定位）"""
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    if user.role != "admin":
        perm = await db.execute(
            select(DocumentPermission).where(
                DocumentPermission.document_id == doc_id,
                DocumentPermission.user_id == user.id,
            )
        )
        if not perm.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="无权限查看该文档")

    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == doc_id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = result.scalars().all()
    return {
        "document": {"id": str(doc.id), "title": doc.title, "content": doc.content},
        "chunks": [
            {"id": str(c.id), "chunk_index": c.chunk_index, "content": c.content} for c in chunks
        ],
    }


class BatchIds(BaseModel):
    ids: list[str]


@router.post("/batch-delete")
async def batch_delete(
    data: BatchIds,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from uuid import UUID

    deleted = 0
    for doc_id in data.ids:
        try:
            uid = UUID(doc_id)
        except ValueError:
            continue
        doc = await db.get(Document, uid)
        if not doc:
            continue
        if user.role != "admin":
            perm = await db.execute(
                select(DocumentPermission).where(
                    DocumentPermission.document_id == uid,
                    DocumentPermission.user_id == user.id,
                )
            )
            if not perm.scalar_one_or_none():
                continue
        await db.delete(doc)
        deleted += 1
    return {"detail": f"已删除 {deleted} 个文档"}


@router.post("/batch-reindex")
async def batch_reindex(
    data: BatchIds,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from uuid import UUID

    triggered = 0
    for doc_id in data.ids:
        try:
            uid = UUID(doc_id)
        except ValueError:
            continue
        doc = await db.get(Document, uid)
        if not doc:
            continue
        if user.role != "admin":
            perm = await db.execute(
                select(DocumentPermission).where(
                    DocumentPermission.document_id == uid,
                    DocumentPermission.user_id == user.id,
                )
            )
            if not perm.scalar_one_or_none():
                continue
        index_document_task.delay(str(uid))
        triggered += 1
    return {"detail": f"已触发 {triggered} 个文档重新索引"}


@router.get("/{doc_id}/file")
async def download_file(
    doc_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """返回文档原始文件"""
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    if user.role != "admin":
        perm = await db.execute(
            select(DocumentPermission).where(
                DocumentPermission.document_id == doc_id,
                DocumentPermission.user_id == user.id,
            )
        )
        if not perm.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="无权限查看该文档")

    filepath = Path(settings.UPLOAD_DIR) / doc.title
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    await audit_log(db, str(user.id), "download_file", "document", doc_id, doc.title)
    return FileResponse(str(filepath), filename=doc.title)


@router.get("/chunks/{chunk_id}")
async def get_chunk_detail(
    chunk_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """通过 chunk_id 获取 chunk 所属文档及全部 chunk"""
    chunk = await db.get(DocumentChunk, chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail="文档块不存在")

    doc = await db.get(Document, chunk.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if user.role != "admin":
        perm = await db.execute(
            select(DocumentPermission).where(
                DocumentPermission.document_id == doc.id,
                DocumentPermission.user_id == user.id,
            )
        )
        if not perm.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="无权限查看该文档")

    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == doc.id)
        .order_by(DocumentChunk.chunk_index)
    )
    all_chunks = result.scalars().all()
    return {
        "document": {"id": str(doc.id), "title": doc.title, "content": doc.content},
        "highlight_chunk_id": str(chunk_id),
        "chunks": [
            {"id": str(c.id), "chunk_index": c.chunk_index, "content": c.content}
            for c in all_chunks
        ],
    }
