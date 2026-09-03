from __future__ import annotations

from app.providers.gcp.auth import load_credentials, resolve_project_id
from app.providers.gcp.errors import GcpAuthError, classify_gcp_error
from app.providers.gcp.models import GcpConnectionConfig


class GcpClientFactory:
    def __init__(self, config: GcpConnectionConfig | None = None) -> None:
        self._config = config

    def secret_manager(self):
        try:
            from google.cloud import secretmanager
        except ImportError as error:
            raise GcpAuthError("Google Secret Manager SDK is not installed") from error
        try:
            credentials, _path = load_credentials(self._config)
            return secretmanager.SecretManagerServiceClient(credentials=credentials)
        except Exception as error:
            raise classify_gcp_error(error) from error

    def project_id(self) -> str:
        project = resolve_project_id(self._config)
        if not project:
            raise GcpAuthError("GCP project id is not configured")
        return project
