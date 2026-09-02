from __future__ import annotations

import json
import time
from base64 import urlsafe_b64encode

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.integrations.github.exceptions import GitHubAuthError, GitHubNotConfigured
from app.secrets.factory import secret_backend


def _b64url(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def build_app_jwt(app_id: str, private_key_pem: str, *, now: int | None = None) -> str:
    if not app_id or not private_key_pem:
        raise GitHubNotConfigured("GitHub App ID and private key are required")
    issued = int(now if now is not None else time.time())
    payload = {"iat": issued - 60, "exp": issued + 540, "iss": str(app_id)}
    header = {"alg": "RS256", "typ": "JWT"}
    signing_input = f"{_b64url(json.dumps(header, separators=(',', ':')).encode())}.{_b64url(json.dumps(payload, separators=(',', ':')).encode())}".encode()
    try:
        key = serialization.load_pem_private_key(private_key_pem.encode("utf-8"), password=None)
    except Exception as error:
        raise GitHubAuthError("GitHub App private key could not be loaded") from error
    signature = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f"{signing_input.decode()}.{_b64url(signature)}"


def load_private_key(secret_reference: str, *, backend_name: str | None = None) -> str:
    if not secret_reference:
        raise GitHubNotConfigured("GitHub App private key secret reference is missing")
    backend = secret_backend(backend_name)
    try:
        return backend.get_secret(secret_reference)
    except Exception as error:
        raise GitHubAuthError("GitHub App private key could not be read from the secret backend") from error
