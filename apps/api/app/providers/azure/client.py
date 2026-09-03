from __future__ import annotations

from app.providers.azure.auth import credential_from_config, load_service_principal
from app.providers.azure.errors import AzureAuthError, classify_azure_error
from app.providers.azure.models import AzureConnectionConfig


class AzureClientFactory:
    def __init__(self, config: AzureConnectionConfig | None = None) -> None:
        self._config = config

    def secret_client(self, vault_url: str | None = None):
        try:
            from azure.keyvault.secrets import SecretClient
        except ImportError as error:
            raise AzureAuthError("Azure Key Vault Secrets SDK is not installed") from error
        url = vault_url or (self._config.vault_url if self._config else None) or load_service_principal().get("vaultUrl")
        if not url:
            raise AzureAuthError("Azure Key Vault URL is not configured")
        try:
            return SecretClient(vault_url=url, credential=credential_from_config(self._config))
        except Exception as error:
            raise classify_azure_error(error) from error
