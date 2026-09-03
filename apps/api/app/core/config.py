from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLOUDOPS_", extra="ignore")

    app_name: str = "CloudOps Platform API"
    last_synced: str = "14:32:45 UTC"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    database_url: str = "sqlite:///./cloudops.db"
    redis_url: str = "redis://127.0.0.1:6379/0"
    celery_eager: bool = True

    aws_enabled: bool = False
    aws_provider: str = "AWS"
    aws_platform_region: str = "EMEA"
    aws_environment: str = "DEV"
    aws_account_alias: str = "aws-emea-nonprod"
    aws_cloud_region: str = "eu-west-1"
    aws_account_id: str | None = None
    aws_role_arn: str | None = None
    aws_external_id: str | None = None
    aws_session_name: str = "cloudops-emea-dev"
    aws_profile: str | None = None
    aws_config_secret_arn: str | None = None
    aws_cluster_environment_tag: str = "Environment"
    aws_scan_concurrency: int = 3
    aws_topology_path: str | None = None

    alibaba_cluster_environment_tag: str = "Environment"
    alibaba_scan_concurrency: int = 2
    alibaba_cloud_region: str = "cn-hangzhou"

    secret_backend: str = "local"
    allow_local_secrets: bool = True
    require_auth: bool = False
    default_role: str = "PlatformAdmin"
    default_user: str = "ops@cloudops.local"
    max_secret_bytes: int = 65536
    credential_validate_rate_per_minute: int = 10
    credential_mutate_rate_per_minute: int = 5
    rotation_due_soon_days: int = 14
    require_https: bool = False

    certificate_discovery_interval_seconds: int = 6 * 60 * 60
    certificate_expiry_interval_seconds: int = 60 * 60
    certificate_endpoint_interval_seconds: int = 6 * 60 * 60
    certificate_alert_interval_seconds: int = 60 * 60
    certificate_https_timeout_seconds: float = 5.0
    certificate_https_allowlist: str = ""
    certificate_notification_cooldown_seconds: int = 6 * 60 * 60
    certificate_alert_severity_warning: str = "MEDIUM"
    certificate_alert_severity_critical: str = "HIGH"
    certificate_alert_severity_urgent: str = "CRITICAL"
    certificate_alert_severity_expired: str = "CRITICAL"
    certificate_notification_provider: str = "log"
    github_app_id: str = ""
    github_installation_id: str = ""
    github_private_key_ref: str = ""
    github_organization: str = ""
    github_api_url: str = "https://api.github.com"
    github_webhook_secret: str = ""
    github_webhook_secret_ref: str = ""
    github_repository_sync_interval_seconds: int = 6 * 60 * 60
    github_workflow_sync_interval_seconds: int = 60 * 60
    github_workflow_run_sync_interval_seconds: int = 5 * 60
    github_variable_sync_interval_seconds: int = 60 * 60
    github_secret_sync_interval_seconds: int = 60 * 60
    github_alert_dev: str = ""
    github_alert_int_tst: str = ""
    github_alert_uat: str = "MEDIUM"
    github_alert_npd: str = "HIGH"
    github_alert_prd: str = "CRITICAL"
    github_variable_sensitive_default: bool = False
    azure_devops_organization: str = ""
    azure_devops_project: str = ""
    azure_devops_base_url: str = "https://dev.azure.com"
    azure_devops_auth_ref: str = ""
    azure_devops_webhook_secret: str = ""
    azure_devops_webhook_secret_ref: str = ""
    azure_devops_mock: bool = False
    pipeline_metadata_sync_interval_seconds: int = 60 * 60
    pipeline_run_sync_interval_seconds: int = 5 * 60
    pipeline_running_sync_interval_seconds: int = 60
    pipeline_retention_interval_seconds: int = 24 * 60 * 60
    pipeline_run_retention_days: int = 90
    pipeline_detail_retention_days: int = 30
    pipeline_alert_dev: str = ""
    pipeline_alert_int_tst: str = "LOW"
    pipeline_alert_uat: str = "MEDIUM"
    pipeline_alert_npd: str = "HIGH"
    pipeline_alert_prd: str = "CRITICAL"

    health_cluster_interval_seconds: int = 120
    health_application_interval_seconds: int = 120
    health_http_interval_seconds: int = 60
    health_dependency_interval_seconds: int = 120
    health_aggregation_interval_seconds: int = 60
    health_alert_interval_seconds: int = 60
    health_retention_interval_seconds: int = 24 * 60 * 60
    health_result_retention_days: int = 30
    health_aggregate_retention_days: int = 180
    health_incident_open_threshold: int = 3
    health_incident_resolve_threshold: int = 2
    health_correlation_window_minutes: int = 30
    health_restart_degraded_threshold: int = 5
    health_http_timeout_seconds: float = 5.0
    health_http_allowlist: str = ""
    health_scan_lock_seconds: int = 90
    health_alert_dev: str = ""
    health_alert_int_tst: str = ""
    health_alert_uat: str = "MEDIUM"
    health_alert_npd: str = "HIGH"
    health_alert_prd: str = "HIGH"

    alert_notify_retry_seconds: str = "30,120,300"
    alert_evaluate_interval_seconds: int = 60
    alert_notification_dispatch_interval_seconds: int = 30
    alert_escalation_interval_seconds: int = 60
    alert_recovery_interval_seconds: int = 60
    alert_suppression_expiry_interval_seconds: int = 60
    maintenance_window_expiry_interval_seconds: int = 60


settings = Settings()
