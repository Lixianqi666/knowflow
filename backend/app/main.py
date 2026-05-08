import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import (
    admin,
    agents,
)
from app.api.v1 import audit as audit_router
from app.api.v1 import (
    auth,
    chat,
    documents,
    knowledge_bases,
    mcp,
)
from app.api.v1 import plugins as plugins_router
from app.api.v1 import (
    prompt_templates,
    webhooks,
)
from app.config import settings
from app.core.logging import RequestIDMiddleware, init_logging
from app.core.metrics import setup_metrics
from app.core.observability import init_langfuse
from app.core.plugins import load_all as load_plugins
from app.core.ratelimit import close_redis
from app.database import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_logging()
    await init_db()
    init_langfuse()
    # 加载内置插件
    import app.plugins.log_plugin  # noqa

    loaded = await load_plugins()
    if loaded:
        import logging

        logging.getLogger(__name__).info(f"已加载 {len(loaded)} 个插件: {[p.name for p in loaded]}")
    yield
    await close_redis()


app = FastAPI(title="KnowFlow", version="0.1.0", lifespan=lifespan)

# Request ID — 最先注册，确保日志中全局可用
app.add_middleware(RequestIDMiddleware)

# CORS — 从配置读取允许来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

setup_metrics(app)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(knowledge_bases.router, prefix="/api/v1")
app.include_router(audit_router.router, prefix="/api/v1")
app.include_router(prompt_templates.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(plugins_router.router, prefix="/api/v1")
app.include_router(mcp.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"未捕获异常: {request.method} {request.url.path}")
    return JSONResponse(status_code=500, content={"detail": "服务内部错误"})


@app.get("/health")
async def health():
    return {"status": "ok"}
