from dataclasses import dataclass


@dataclass(frozen=True)
class AzureConnectionConfig:
    cloud_region: str
    account_id: str | None
    tenant_id: str | None
    client_id: str | None
    client_secret_ref: str | None
    vault_url: str | None
    platform_region: str
    environment: str
    account_alias: str
    credential_ref: str | None = None
