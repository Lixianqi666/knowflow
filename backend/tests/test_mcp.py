"""P2: MCP 权限校验 + 工具分发测试"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_mcp_unknown_tool(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/mcp/",
        headers=auth_headers,
        json={"tool": "nonexistent", "arguments": {}},
    )
    assert resp.status_code == 400
    assert "未知工具" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_mcp_list_knowledge_bases(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/mcp/",
        headers=auth_headers,
        json={"tool": "list_knowledge_bases", "arguments": {}},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_mcp_unauthenticated(client: AsyncClient):
    resp = await client.post(
        "/api/v1/mcp/",
        json={"tool": "list_knowledge_bases", "arguments": {}},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_mcp_get_document_not_found(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/mcp/",
        headers=auth_headers,
        json={
            "tool": "get_document",
            "arguments": {"document_id": "00000000-0000-0000-0000-000000000000"},
        },
    )
    assert resp.status_code == 404
