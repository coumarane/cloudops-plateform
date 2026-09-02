from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CLOUDOPS_", extra="ignore")

    app_name: str = "CloudOps Platform API"
    last_synced: str = "14:32:45 UTC"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


settings = Settings()
