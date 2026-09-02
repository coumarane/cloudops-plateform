from __future__ import annotations

import hashlib
import json
import re

MAX_SECRET_BYTES = 65536

_AWS_KEY = re.compile(r"^AKIA[0-9A-Z]{16}$")
_ALIBABA_KEY = re.compile(r"^LTAI[A-Za-z0-9]{12,}$")


def fingerprint_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()[:16]


def fingerprint_identifier(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def assert_secret_size(secret: str, limit: int = MAX_SECRET_BYTES) -> None:
    if len(secret.encode("utf-8")) > limit:
        raise ValueError("Secret exceeds the maximum allowed size")
    if not secret.strip():
        raise ValueError("Secret value is required")


def parse_secret_payload(secret: str, credential_type: str, provider: str) -> dict[str, str]:
    """Return metadata extracted from a secret without keeping extra copies of unused fields."""
    credential_type = credential_type.lower()
    if credential_type in {"iam_role", "ram_role", "sts_assume_role", "sts"}:
        return {}
    try:
        payload = json.loads(secret)
    except json.JSONDecodeError:
        payload = None
    if credential_type in {"access_key", "accesskey"}:
        if not isinstance(payload, dict):
            raise ValueError("Access key credentials must be JSON with an identifier and secret")
        key_id = str(payload.get("AccessKeyId") or payload.get("access_key_id") or payload.get("aws_access_key_id") or "")
        secret_key = str(
            payload.get("SecretAccessKey")
            or payload.get("access_key_secret")
            or payload.get("aws_secret_access_key")
            or payload.get("AccessKeySecret")
            or ""
        )
        if not key_id or not secret_key:
            raise ValueError("Access key credentials must include an identifier and secret")
        if provider == "AWS" and not _AWS_KEY.match(key_id):
            raise ValueError("AWS access key id format is invalid")
        if provider == "Alibaba" and not _ALIBABA_KEY.match(key_id):
            raise ValueError("Alibaba AccessKey id format is invalid")
        return {"key_id": key_id}
    if not secret.strip():
        raise ValueError("Application credential value is required")
    return {}
