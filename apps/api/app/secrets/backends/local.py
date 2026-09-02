from __future__ import annotations

from app.core.config import settings
from app.secrets.backends.base import SecretBackend, SecretMetadata


class LocalSecretBackendError(RuntimeError):
    pass


class LocalDevSecretBackend(SecretBackend):
    """In-process store for local development and tests. Never used as PostgreSQL storage."""

    name = "local"
    _store: dict[str, str] = {}

    def __init__(self, *, allow: bool | None = None) -> None:
        permitted = settings.allow_local_secrets if allow is None else allow
        if not permitted:
            raise LocalSecretBackendError("LocalDevSecretBackend is disabled outside local development")

    @classmethod
    def reset(cls) -> None:
        cls._store.clear()

    def get_metadata(self, reference: str) -> SecretMetadata:
        if reference not in self._store:
            raise KeyError(reference)
        return SecretMetadata(reference=reference, backend=self.name, version=str(len(self._store[reference])))

    def store_secret(self, reference: str, secret: str) -> SecretMetadata:
        self._store[reference] = secret
        return self.get_metadata(reference)

    def replace_secret(self, reference: str, secret: str) -> SecretMetadata:
        self._store[reference] = secret
        return self.get_metadata(reference)

    def delete_secret_reference(self, reference: str) -> None:
        self._store.pop(reference, None)

    def validate_reference(self, reference: str) -> bool:
        return bool(reference) and reference in self._store

    def get_secret(self, reference: str) -> str:
        return self._store[reference]
