from unittest.mock import MagicMock, patch

import litellm
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import Base, get_db

# 全局引用，供 override 使用
_session_factory = None


def _make_override():
    async def override_get_db():
        async with _session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return override_get_db


def _make_stream_chunks(tokens):
    """用 litellm.ModelResponse 构造流式 chunk 列表"""
    chunks = []
    for t in tokens:
        chunk = litellm.ModelResponse(
            id="mock",
            choices=[
                litellm.Choices(
                    index=0,
                    delta=litellm.ChatCompletionDeltaChunk(content=t, role="assistant"),
                    finish_reason=None,
                )
            ],
            model="mock",
            object="chat.completion.chunk",
        )
        chunks.append(chunk)
    return chunks


class _FakeStreamingResponse:
    def __init__(self, chunks):
        self._chunks = chunks

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for c in self._chunks:
            yield c


@pytest_asyncio.fixture(scope="session", autouse=True)
async def llm_mock():
    """mock LLM 调用，CI 环境无需真实 API key"""
    tokens = ["你好", "，", "我是", "测试", "助手", "。"]
    stream_chunks = _make_stream_chunks(tokens)

    async def fake_acompletion(**kwargs):
        if kwargs.get("stream"):
            return _FakeStreamingResponse(stream_chunks)
        return litellm.ModelResponse(
            id="mock",
            choices=[
                litellm.Choices(
                    index=0,
                    message=litellm.Message(content="".join(tokens), role="assistant"),
                    finish_reason="stop",
                )
            ],
            model="mock",
            object="chat.completion",
        )

    async def fake_aembedding(**kwargs):
        dim = settings.EMBEDDING_DIM
        n = len(kwargs.get("input", []))
        mock_resp = MagicMock()
        mock_resp.data = [{"embedding": [0.1] * dim} for _ in range(n)]
        mock_resp.model_dump.return_value = {"data": [{"embedding": [0.1] * dim} for _ in range(n)]}
        return mock_resp

    with (
        patch("litellm.acompletion", side_effect=fake_acompletion),
        patch("litellm.aembedding", side_effect=fake_aembedding),
        patch("app.tasks.indexing.index_document_task.delay"),
    ):
        yield


@pytest_asyncio.fixture(scope="session")
async def client():
    """session 级别的测试客户端，建表 + dependency override"""
    global _session_factory
    import app.database as db_mod
    import app.models.agent  # noqa
    import app.models.agent_session  # noqa
    import app.models.agent_trace  # noqa
    import app.models.audit_log  # noqa
    import app.models.conversation  # noqa
    import app.models.document  # noqa
    import app.models.feedback  # noqa
    import app.models.kb_member  # noqa
    import app.models.knowledge_base  # noqa
    import app.models.message_feedback  # noqa
    import app.models.permission  # noqa
    import app.models.rag_eval  # noqa
    import app.models.rag_quality_issue  # noqa
    import app.models.prompt_template  # noqa
    import app.models.reimbursement  # noqa
    import app.models.user  # noqa
    import app.models.webhook  # noqa

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    _session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    db_mod.engine = engine
    db_mod.async_session = _session_factory

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    from app.main import app

    app.dependency_overrides[get_db] = _make_override()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def db_session_factory(client):
    """暴露 session 工厂给需要直接操作数据库的测试"""
    return _session_factory


@pytest_asyncio.fixture(scope="session")
async def auth_headers(client: AsyncClient):
    """注册并登录，返回带 token 的 headers"""
    email = "pytest@test.com"
    password = "test1234"
    resp = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": password, "name": "PyTest"}
    )
    if resp.status_code == 200:
        token = resp.json()["access_token"]
    else:
        resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
        token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="session")
async def admin_headers(client: AsyncClient):
    """注册管理员账号并返回 headers"""
    from sqlalchemy import text

    email = "admin@test.com"
    password = "admin1234"
    resp = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": password, "name": "Admin"}
    )
    if resp.status_code == 200:
        token = resp.json()["access_token"]
        user_id = resp.json()["user"]["id"]
    else:
        resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, f"登录失败: {resp.text}"
        token = resp.json()["access_token"]
        user_id = resp.json()["user"]["id"]
    # 直接在数据库中提升为管理员
    async with _session_factory() as session:
        await session.execute(
            text("UPDATE users SET role = 'admin' WHERE id = :uid"), {"uid": user_id}
        )
        await session.commit()
    return {"Authorization": f"Bearer {token}"}
