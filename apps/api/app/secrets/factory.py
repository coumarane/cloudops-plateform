from __future__ import annotations

from app.core.config import settings
from app.secrets.backends.alibaba import AlibabaSecretsBackend
from app.secrets.backends.aws import AwsSecretsManagerBackend
from app.secrets.backends.base import SecretBackend
from app.secrets.backends.local import LocalDevSecretBackend, LocalSecretBackendError


def secret_backend(name: str | None = None, *, region: str | None = None, client=None) -> SecretBackend:
    backend = (name or settings.secret_backend or "local").lower()
    cloud_region = region or settings.alibaba_cloud_region
    if backend == "local":
        return LocalDevSecretBackend()
    if backend in {"aws", "secretsmanager"}:
        return AwsSecretsManagerBackend(region=region or settings.aws_cloud_region, client=client)
    if backend == "alibaba":
        return AlibabaSecretsBackend(region=cloud_region, client=client)
    raise ValueError(f"Unknown secret backend {backend}")


def assert_backend_allowed(name: str) -> None:
    backend = name.lower()
    if backend == "local" and not settings.allow_local_secrets:
        raise LocalSecretBackendError("LocalDevSecretBackend is not permitted in this environment")
