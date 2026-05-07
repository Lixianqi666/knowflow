"""MCP 服务器 — 暴露知识库查询能力为 MCP 工具

启动方式（stdio）:
  python -m app.mcp_server

或在 Claude Desktop 的 mcp_servers 配置中添加:
```json
{
  "knowflow": {
    "command": "python",
    "args": ["-m", "app.mcp_server"],
    "env": {
      "DATABASE_URL": "...",
      "LLM_API_KEY": "...",
      "MCP_API_KEY": "your-secret-key"
    }
  }
}
```
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)

_engine = None
_session_maker = None


def get_db_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://knowflow:knowflow@localhost:5432/knowflow",
    )


async def get_session() -> AsyncSession:
    global _engine, _session_maker
    if _engine is None:
        _engine = create_async_engine(get_db_url(), echo=False)
        _session_maker = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _session_maker()


def auth_ok(token: str | None) -> bool:
    expected = os.environ.get("MCP_API_KEY", "")
    return not expected or token == expected


server = Server("knowflow")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_knowledge_base",
            description="搜索知识库，检索与查询最相关的文档块",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "kb_id": {"type": "string", "description": "知识库 ID（可选，不传则搜索全部）"},
                    "top_k": {"type": "integer", "description": "返回结果数", "default": 5},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_document",
            description="获取文档内容",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "description": "文档 ID"},
                },
                "required": ["document_id"],
            },
        ),
        Tool(
            name="list_knowledge_bases",
            description="列出所有知识库",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "search_knowledge_base":
        return await _search_kb(arguments)
    elif name == "get_document":
        return await _get_doc(arguments)
    elif name == "list_knowledge_bases":
        return await _list_kbs()
    return [TextContent(type="text", text=f"未知工具: {name}")]


async def _search_kb(args: dict) -> list[TextContent]:
    query = args.get("query", "")
    kb_id = args.get("kb_id")
    top_k = min(args.get("top_k", 5), 20)
    if not query:
        return [TextContent(type="text", text="缺少 query 参数")]

    async with await get_session() as db:
        kb_cond = " AND d.kb_id = :kb_id::uuid" if kb_id else ""
        params: dict = {"q": f"%{query}%", "limit": top_k}
        if kb_id:
            params["kb_id"] = kb_id

        # ILIKE 全文搜索 + BM25（tsvector）
        sql = text(f"""
            SELECT dc.id, dc.content, d.title, d.id AS document_id
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE d.status = 'indexed' AND (dc.content ILIKE :q
               OR (
                   dc.tsvector_content IS NOT NULL
                   AND dc.tsvector_content @@ to_tsquery('simple', :q_tsv)
               ))
            {kb_cond}
            ORDER BY GREATEST(
                CASE WHEN dc.content ILIKE :q THEN 1 ELSE 0 END,
                CASE
                    WHEN dc.tsvector_content IS NOT NULL
                    AND dc.tsvector_content @@ to_tsquery('simple', :q_tsv)
                    THEN 1 ELSE 0
                END
            ) DESC
            LIMIT :limit
        """)
        params["q_tsv"] = " | ".join(w for w in query.split() if len(w) >= 2)

        try:
            result = await db.execute(sql, params)
            rows = result.fetchall()
        except Exception:
            # 降级为纯 ILIKE
            sql = text(f"""
                SELECT dc.id, dc.content, d.title, d.id AS document_id
                FROM document_chunks dc JOIN documents d ON dc.document_id = d.id
                WHERE d.status = 'indexed' AND dc.content ILIKE :q {kb_cond}
                LIMIT :limit
            """)
            result = await db.execute(sql, params)
            rows = result.fetchall()

        if not rows:
            return [TextContent(type="text", text=f"未找到与「{query}」相关的文档")]

        results = []
        for row in rows:
            results.append(f"文档: {row[2]}\n内容: {row[1][:500]}\n---")
        return [TextContent(type="text", text="\n".join(results))]


async def _get_doc(args: dict) -> list[TextContent]:
    doc_id = args.get("document_id", "")
    if not doc_id:
        return [TextContent(type="text", text="缺少 document_id")]

    async with await get_session() as db:
        from app.models.document import Document

        doc = await db.get(Document, doc_id)
        if not doc:
            return [TextContent(type="text", text="文档不存在")]
        return [TextContent(type="text", text=f"标题: {doc.title}\n\n{doc.content[:2000]}")]


async def _list_kbs() -> list[TextContent]:
    async with await get_session() as db:
        result = await db.execute(select(text("id, name FROM knowledge_bases ORDER BY name")))
        rows = result.fetchall()
        if not rows:
            return [TextContent(type="text", text="暂无知识库")]
        kbs = [f"  {r[1]} ({str(r[0])})" for r in rows]
        return [TextContent(type="text", text="知识库列表:\n" + "\n".join(kbs))]


@asynccontextmanager
async def lifespan(server: Server) -> AsyncIterator:
    """生命周期管理"""
    yield
    if _engine:
        await _engine.dispose()


async def main():
    logging.basicConfig(level=logging.WARNING)
    async with stdio_server() as streams:
        await server.run(streams[0], streams[1], server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
