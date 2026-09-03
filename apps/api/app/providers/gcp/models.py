from dataclasses import dataclass


@dataclass(frozen=True)
class GcpConnectionConfig:
    cloud_region: str
    account_id: str | None
    project_id: str | None
    credentials_file: str | None
    platform_region: str
    environment: str
    account_alias: str
    credential_ref: str | None = None
