"""Prometheus 指标 endpoint label 模板化测试"""

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from app.core.metrics import _get_endpoint_template


@pytest.fixture
def metrics_app():
    app = FastAPI()

    @app.get("/api/v1/documents/{doc_id}")
    async def get_doc(doc_id: str):
        return {"id": doc_id}

    @app.get("/api/v1/users")
    async def list_users():
        return []

    @app.get("/error")
    async def error_route():
        raise RuntimeError("boom")

    return app


def test_route_template_with_uuid(metrics_app):
    """带 UUID 的路径应归一化为路由模板"""
    from starlette.requests import Request as StarletteRequest

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/documents/11111111-1111-1111-1111-111111111111",
        "query_string": b"",
        "headers": [],
        "app": metrics_app,
    }
    req = StarletteRequest(scope)
    result = _get_endpoint_template(req)
    assert result == "/api/v1/documents/{doc_id}"


def test_route_template_static_path(metrics_app):
    """静态路径应原样返回"""
    from starlette.requests import Request as StarletteRequest

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/users",
        "query_string": b"",
        "headers": [],
        "app": metrics_app,
    }
    req = StarletteRequest(scope)
    result = _get_endpoint_template(req)
    assert result == "/api/v1/users"


def test_unknown_route_fallback(metrics_app):
    """未匹配路由应 fallback 到原始 path"""
    from starlette.requests import Request as StarletteRequest

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/unknown/path",
        "query_string": b"",
        "headers": [],
        "app": metrics_app,
    }
    req = StarletteRequest(scope)
    result = _get_endpoint_template(req)
    assert result == "/unknown/path"


def test_error_route_no_crash(metrics_app):
    """异常路由不会导致 middleware 报错"""
    from app.core.metrics import MetricsMiddleware

    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/error")
    async def error_route():
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/error")
    assert resp.status_code == 500


def test_metrics_endpoint_records_status(metrics_app):
    """验证指标记录正确的 status code"""
    from app.core.metrics import MetricsMiddleware, http_requests_total

    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/api/v1/documents/{doc_id}")
    async def get_doc(doc_id: str):
        return {"id": doc_id}

    client = TestClient(app)
    client.get("/api/v1/documents/11111111-1111-1111-1111-111111111111")

    from prometheus_client import REGISTRY

    val = REGISTRY.get_sample_value(
        "http_requests_total",
        {"method": "GET", "endpoint": "/api/v1/documents/{doc_id}", "status": "200"},
    )
    assert val is not None and val >= 1
