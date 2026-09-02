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
        "tasks.github_repository_sync",
        "tasks.github_workflow_sync",
        "tasks.github_workflow_run_sync",
        "tasks.github_variable_sync",
        "tasks.github_secret_sync",
        "tasks.github_webhook",
        "tasks.pipeline_provider_sync",
        "tasks.pipeline_sync",
        "tasks.pipeline_run_sync",
        "tasks.pipeline_run_detail_sync",
        "tasks.pipeline_retention",
        "tasks.pipeline_webhook",
        "tasks.cluster_health_scan",
        "tasks.application_health_scan",
        "tasks.http_health_check",
        "tasks.dependency_health_check",
        "tasks.health_aggregation",
        "tasks.health_alert_evaluation",
        "tasks.health_retention",
        "tasks.alert_evaluate",
        "tasks.alert_notification_dispatch",
        "tasks.alert_escalation_check",
        "tasks.alert_recovery_notification",
        "tasks.alert_suppression_expiry",
        "tasks.maintenance_window_expiry",
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
        "github-repository-sync": {
            "task": "tasks.github_repository_sync.periodic_scan",
            "schedule": settings.github_repository_sync_interval_seconds,
        },
        "github-workflow-sync": {
            "task": "tasks.github_workflow_sync.periodic_scan",
            "schedule": settings.github_workflow_sync_interval_seconds,
        },
        "github-workflow-run-sync": {
            "task": "tasks.github_workflow_run_sync.periodic_scan",
            "schedule": settings.github_workflow_run_sync_interval_seconds,
        },
        "github-variable-sync": {
            "task": "tasks.github_variable_sync.periodic_scan",
            "schedule": settings.github_variable_sync_interval_seconds,
        },
        "github-secret-metadata-sync": {
            "task": "tasks.github_secret_sync.periodic_scan",
            "schedule": settings.github_secret_sync_interval_seconds,
        },
        "pipeline-provider-sync": {
            "task": "tasks.pipeline_provider_sync.periodic_scan",
            "schedule": settings.pipeline_metadata_sync_interval_seconds,
        },
        "pipeline-sync": {
            "task": "tasks.pipeline_sync.periodic_scan",
            "schedule": settings.pipeline_metadata_sync_interval_seconds,
        },
        "pipeline-run-sync": {
            "task": "tasks.pipeline_run_sync.periodic_scan",
            "schedule": settings.pipeline_run_sync_interval_seconds,
        },
        "pipeline-run-detail-sync": {
            "task": "tasks.pipeline_run_detail_sync.periodic_scan",
            "schedule": settings.pipeline_running_sync_interval_seconds,
        },
        "pipeline-retention": {
            "task": "tasks.pipeline_retention.periodic_scan",
            "schedule": settings.pipeline_retention_interval_seconds,
        },
        "cluster-health-scan": {
            "task": "tasks.cluster_health_scan.periodic_scan",
            "schedule": settings.health_cluster_interval_seconds,
        },
        "application-health-scan": {
            "task": "tasks.application_health_scan.periodic_scan",
            "schedule": settings.health_application_interval_seconds,
        },
        "http-health-check": {
            "task": "tasks.http_health_check.periodic_scan",
            "schedule": settings.health_http_interval_seconds,
        },
        "dependency-health-check": {
            "task": "tasks.dependency_health_check.periodic_scan",
            "schedule": settings.health_dependency_interval_seconds,
        },
        "health-aggregation": {
            "task": "tasks.health_aggregation.periodic_scan",
            "schedule": settings.health_aggregation_interval_seconds,
        },
        "health-alert-evaluation": {
            "task": "tasks.health_alert_evaluation.periodic_scan",
            "schedule": settings.health_alert_interval_seconds,
        },
        "health-retention": {
            "task": "tasks.health_retention.periodic_scan",
            "schedule": settings.health_retention_interval_seconds,
        },
        "alert-evaluate": {
            "task": "tasks.alert_evaluate.periodic_scan",
            "schedule": settings.alert_evaluate_interval_seconds,
        },
        "alert-notification-dispatch": {
            "task": "tasks.alert_notification_dispatch.periodic_scan",
            "schedule": settings.alert_notification_dispatch_interval_seconds,
        },
        "alert-escalation-check": {
            "task": "tasks.alert_escalation_check.periodic_scan",
            "schedule": settings.alert_escalation_interval_seconds,
        },
        "alert-recovery-notification": {
            "task": "tasks.alert_recovery_notification.periodic_scan",
            "schedule": settings.alert_recovery_interval_seconds,
        },
        "alert-suppression-expiry": {
            "task": "tasks.alert_suppression_expiry.periodic_scan",
            "schedule": settings.alert_suppression_expiry_interval_seconds,
        },
        "maintenance-window-expiry": {
            "task": "tasks.maintenance_window_expiry.periodic_scan",
            "schedule": settings.maintenance_window_expiry_interval_seconds,
        },
    },
)
