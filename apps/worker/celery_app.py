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
    include=(
        "tasks.aws_cluster_discovery",
        "tasks.aws_cluster_health",
        "tasks.aws_certificate_scan",
        "tasks.alibaba_account_validation",
        "tasks.alibaba_cluster_discovery",
        "tasks.alibaba_cluster_health",
        "tasks.alibaba_certificate_scan",
        "tasks.alibaba_certificate_expiry",
        "tasks.credential_validate",
        "tasks.credential_rotation_scan",
        "tasks.certificate_discovery",
        "tasks.certificate_expiry",
        "tasks.certificate_endpoint",
        "tasks.certificate_alerts",
        "tasks.certificate_validate",
    ),
)
celery_app.conf.update(
    task_always_eager=settings.celery_eager,
    task_eager_propagates=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "credential-rotation-status-scan": {
            "task": "tasks.credential_rotation_scan.periodic_scan",
            "schedule": 6 * 60 * 60,
        },
        "certificate-discovery": {
            "task": "tasks.certificate_discovery.periodic_scan",
            "schedule": settings.certificate_discovery_interval_seconds,
        },
        "certificate-expiry-scan": {
            "task": "tasks.certificate_expiry.periodic_scan",
            "schedule": settings.certificate_expiry_interval_seconds,
        },
        "certificate-endpoint-validation": {
            "task": "tasks.certificate_endpoint.periodic_scan",
            "schedule": settings.certificate_endpoint_interval_seconds,
        },
        "certificate-alert-evaluation": {
            "task": "tasks.certificate_alerts.periodic_scan",
            "schedule": settings.certificate_alert_interval_seconds,
        },
    },
)
