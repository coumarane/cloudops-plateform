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
    slack_webhook_url: str = ""


settings = Settings()
