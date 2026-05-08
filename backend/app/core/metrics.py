import time

from fastapi import Request, Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

http_requests_total = Counter(
    "http_requests_total", "总请求数", ["method", "endpoint", "status"]
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "请求耗时分布（秒）",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 5, 10),
)
http_requests_in_progress = Gauge(
    "http_requests_in_progress", "当前正在处理的请求数", ["method"]
)
documents_indexed_total = Counter("documents_indexed_total", "已索引文档总数")
llm_requests_total = Counter("llm_requests_total", "LLM 请求总数", ["operation"])
llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "LLM 请求耗时分布（秒）",
    ["operation"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30),
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        method = request.method
        path = request.url.path

        http_requests_in_progress.labels(method=method).inc()
        start = time.time()
        try:
            response = await call_next(request)
            return response
        finally:
            elapsed = time.time() - start
            status = response.status_code if "response" in dir() else 500
            http_requests_total.labels(method=method, endpoint=path, status=status).inc()
            http_request_duration_seconds.labels(method=method, endpoint=path).observe(elapsed)
            http_requests_in_progress.labels(method=method).dec()


def setup_metrics(app):
    from fastapi import FastAPI

    app: FastAPI
    app.add_middleware(MetricsMiddleware)

    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        from prometheus_client import REGISTRY

        return Response(content=generate_latest(REGISTRY), media_type="text/plain; charset=utf-8")
