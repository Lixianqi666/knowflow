import time

from fastapi import Request, Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match

http_requests_total = Counter("http_requests_total", "总请求数", ["method", "endpoint", "status"])
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "请求耗时分布（秒）",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 5, 10),
)
http_requests_in_progress = Gauge("http_requests_in_progress", "当前正在处理的请求数", ["method"])
documents_indexed_total = Counter("documents_indexed_total", "已索引文档总数")
agent_runs_total = Counter("agent_runs_total", "Agent 运行总数", ["status"])
agent_steps_total = Counter("agent_steps_total", "Agent 步骤总数", ["phase"])
agent_tool_calls_total = Counter("agent_tool_calls_total", "Agent 工具调用总数", ["tool", "status"])
agent_step_duration_seconds = Histogram(
    "agent_step_duration_seconds",
    "Agent 单步耗时分布（秒）",
    ["phase"],
    buckets=(0.05, 0.1, 0.5, 1, 2, 5, 10, 30),
)
llm_requests_total = Counter("llm_requests_total", "LLM 请求总数", ["operation"])
llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "LLM 请求耗时分布（秒）",
    ["operation"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30),
)


def _get_endpoint_template(request: Request) -> str:
    """优先使用路由模板，fallback 到原始 path"""
    try:
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL and hasattr(route, "path"):
                return route.path
    except Exception:
        pass
    return request.url.path


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method
        endpoint = _get_endpoint_template(request)

        http_requests_in_progress.labels(method=method).inc()
        start = time.time()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            elapsed = time.time() - start
            http_requests_total.labels(method=method, endpoint=endpoint, status=status_code).inc()
            http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(elapsed)
            http_requests_in_progress.labels(method=method).dec()


def setup_metrics(app):
    from fastapi import FastAPI

    app: FastAPI
    app.add_middleware(MetricsMiddleware)

    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        from prometheus_client import REGISTRY

        return Response(content=generate_latest(REGISTRY), media_type="text/plain; charset=utf-8")
