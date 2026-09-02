from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SecretMetadata:
    reference: str
    backend: str
    version: str = ""
    description: str = ""


class SecretBackend(ABC):
    name: str

    @abstractmethod
    def get_metadata(self, reference: str) -> SecretMetadata: ...

    @abstractmethod
    def store_secret(self, reference: str, secret: str) -> SecretMetadata: ...

    @abstractmethod
    def replace_secret(self, reference: str, secret: str) -> SecretMetadata: ...

    @abstractmethod
    def delete_secret_reference(self, reference: str) -> None: ...

    @abstractmethod
    def validate_reference(self, reference: str) -> bool: ...

    def get_secret(self, reference: str) -> str:
        """Worker-only. Never expose through FastAPI."""
        raise NotImplementedError
