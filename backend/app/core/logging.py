import json
import logging
import threading
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

_request_id = threading.local()


class RequestIDFilter(logging.Filter):
    def filter(self, record):
        record.request_id = getattr(_request_id, "val", "-")
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info and record.exc_info[0]:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        _request_id.val = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def init_logging(*, json_format: bool = True):
    root = logging.getLogger()

    # 清除已有 handler 避免重复
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler()
    if json_format:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    handler.addFilter(RequestIDFilter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # 压制第三方库
    for name in ("httpx", "httpcore", "litellm", "LiteLLM", "openai", "urllib3", "asyncio"):
        logging.getLogger(name).setLevel(logging.WARNING)

    # uvicorn access 日志也走 JSON
    uvicorn_access = logging.getLogger("uvicorn.access")
    for h in list(uvicorn_access.handlers):
        uvicorn_access.removeHandler(h)
    if json_format:
        ua_handler = logging.StreamHandler()
        ua_handler.setFormatter(JsonFormatter())
        ua_handler.addFilter(RequestIDFilter())
        uvicorn_access.addHandler(ua_handler)
        uvicorn_access.setLevel(logging.INFO)
