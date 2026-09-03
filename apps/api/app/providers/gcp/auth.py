from __future__ import annotations

import json
import os
from pathlib import Path

from app.core.logging import get_logger
from app.providers.gcp.errors import GcpAuthError, classify_gcp_error
from app.providers.gcp.models import GcpConnectionConfig

logger = get_logger(__name__)

_GCP_PROFILE = Path.home() / ".config" / "gcloud" / "cloudops-adc.json"


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def credentials_path() -> Path:
    env_path = _clean(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("CLOUDOPS_GCP_CREDENTIALS_FILE"))
    if env_path:
        return Path(env_path)
    return _GCP_PROFILE


def save_service_account(*, project_id: str, credentials_json: str) -> Path:
    path = _GCP_PROFILE
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.loads(credentials_json)
    if not isinstance(payload, dict):
        raise GcpAuthError("GCP service account JSON must be an object")
    if project_id and not payload.get("project_id"):
        payload["project_id"] = project_id
    path.write_text(json.dumps(payload, indent=2))
    return path


def load_credentials(config: GcpConnectionConfig | None = None):
    try:
        from google.oauth2 import service_account
        import google.auth
    except ImportError as error:
        raise GcpAuthError("Google Auth SDK is not installed") from error

    path = Path(config.credentials_file) if config and config.credentials_file else credentials_path()
    if path.exists():
        return service_account.Credentials.from_service_account_file(str(path)), path
    credentials, _project = google.auth.default()
    return credentials, path


def resolve_project_id(config: GcpConnectionConfig | None = None) -> str:
    if config and config.project_id:
        return config.project_id
    path = credentials_path()
    if path.exists():
        try:
            payload = json.loads(path.read_text())
            project = payload.get("project_id")
            if project:
                return str(project)
        except Exception:
            pass
    return os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT") or os.environ.get("CLOUDOPS_GCP_PROJECT_ID") or ""


def get_caller_identity(config: GcpConnectionConfig | None = None) -> dict[str, str]:
    try:
        credentials, path = load_credentials(config)
        project_id = resolve_project_id(config)
        principal = getattr(credentials, "service_account_email", None) or getattr(credentials, "signer_email", None) or "default"
        if not project_id and hasattr(credentials, "project_id"):
            project_id = str(getattr(credentials, "project_id") or "")
        if not project_id:
            raise GcpAuthError("GCP project id is not configured")
        # Force token acquisition to validate credentials.
        from google.auth.transport.requests import Request

        credentials.refresh(Request())
        logger.info("GCP session ready project=%s principal=%s file=%s", project_id, principal, path)
        return {
            "account": project_id,
            "arn": f"gcp://projects/{project_id}",
            "principal": str(principal),
        }
    except Exception as error:
        raise classify_gcp_error(error) from error
