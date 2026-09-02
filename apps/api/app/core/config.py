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
    aws_account_alias: str = "nonprod-emea"
    aws_cloud_region: str = "eu-west-1"
    aws_account_id: str | None = None
    aws_role_arn: str | None = None
    aws_external_id: str | None = None
    aws_session_name: str = "cloudops-emea-dev"
    aws_profile: str | None = None
    aws_config_secret_arn: str | None = None
    aws_cluster_environment_tag: str = "Environment"

    @property
    def live_scope(self) -> tuple[str, str, str]:
        return (self.aws_provider, self.aws_platform_region, self.aws_environment)


settings = Settings()
