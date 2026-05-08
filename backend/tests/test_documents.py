import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_txt(client: AsyncClient, auth_headers: dict):
    content = "测试文档内容：这是一个自动化测试文件。"
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("test.txt", content.encode(), "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "test.txt"
    assert data["status"] in ("pending", "indexed", "failed")


@pytest.mark.asyncio
async def test_upload_rejected_extension(client: AsyncClient, auth_headers: dict):
    resp = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("bad.exe", b"bad", "application/octet-stream")},
    )
    assert resp.status_code == 400
    assert "不支持" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient, auth_headers: dict):
    resp = await client.get("/api/v1/documents", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict) and "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_upload_unauthorized(client: AsyncClient):
    resp = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.txt", b"content", "text/plain")},
    )
    assert resp.status_code == 403
