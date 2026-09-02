from __future__ import annotations

import sys
from pathlib import Path

from celery import Celery

API_ROOT = Path(__file__).resolve().parents[1] / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.core.config import settings  # noqa: E402

celery_app = Celery(
    "cloudops",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_always_eager=settings.celery_eager,
    task_eager_propagates=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    imports=(
        "tasks.aws_cluster_discovery",
        "tasks.aws_cluster_health",
        "tasks.aws_certificate_scan",
    ),
)
