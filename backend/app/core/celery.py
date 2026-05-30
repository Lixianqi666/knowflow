from celery import Celery

from app.config import settings
from app.core.logging import init_logging

init_logging()

celery_app = Celery(
    "knowflow",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=300,
    task_soft_time_limit=240,
)

# 显式导入任务模块（autodiscovery 只找 tasks.py，不找 indexing.py）
import app.tasks.indexing  # noqa
