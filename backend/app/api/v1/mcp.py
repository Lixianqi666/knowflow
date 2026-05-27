"""MCP HTTP API — 通过 HTTP 调用知识库工具

Claude Desktop 配置示例:
```json
{
  "mcpServers": {
    "knowflow": {
      "url": "http://localhost:8000/api/v1/mcp",
      "headers": { "Authorization": "Bearer your-token" }
    }
  }
}
```
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/mcp", tags=["MCP"])


class MCPRequest(BaseModel):
    tool: str
    arguments: dict[str, Any] = {}


@router.post("/")
async def mcp_call(req: MCPRequest, user: User = Depends(get_current_user)):
    """调用 MCP 工具"""
    if req.tool == "search":
        return await _search(req.arguments, user)
    elif req.tool == "get_document":
        return await _get_document(req.arguments, user)
    elif req.tool == "list_knowledge_bases":
        return await _list_kbs()
    raise HTTPException(400, f"未知工具: {req.tool}")


async def _search(args: dict, user: User):
    from app.database import async_session
    from app.services.retrieval import RetrievalService

    query = args.get("query", "")
    top_k = min(args.get("top_k", 5), 20)
    kb_id = args.get("kb_id")

    async with async_session() as db:
        svc = RetrievalService(db)
        chunks = await svc.search(
            query, str(user.id), is_admin=(user.role == "admin"), top_k=top_k, kb_id=kb_id
        )
        return [
            {
                "title": c.document_title,
                "content": c.content[:500],
                "score": round(c.score, 3),
                "document_id": str(c.document_id),
            }
            for c in chunks
        ]


async def _get_document(args: dict, user: User):
    from app.database import async_session
    from app.models.document import Document
    from app.models.permission import DocumentPermission
    from sqlalchemy import select

    doc_id = args.get("document_id", "")
    async with async_session() as db:
        doc = await db.get(Document, doc_id)
        if not doc:
            raise HTTPException(404, "文档不存在")
        if user.role != "admin":
            perm = await db.execute(
                select(DocumentPermission).where(
                    DocumentPermission.document_id == doc_id,
                    DocumentPermission.user_id == user.id,
                )
            )
            if not perm.scalar_one_or_none():
                raise HTTPException(403, "无权限访问该文档")
        return {"title": doc.title, "content": doc.content[:3000]}


async def _list_kbs():
    from sqlalchemy import select

    from app.database import async_session
    from app.models.knowledge_base import KnowledgeBase

    async with async_session() as db:
        result = await db.execute(select(KnowledgeBase).order_by(KnowledgeBase.name))
        return [
            {"id": str(kb.id), "name": kb.name, "description": kb.description}
            for kb in result.scalars().all()
        ]
