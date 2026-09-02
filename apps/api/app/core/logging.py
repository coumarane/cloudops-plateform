from __future__ import annotations

import logging
import re
from typing import Any

from app.core.correlation import current_correlation_id

REDACT = "***REDACTED***"

_SECRET_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"LTAI[A-Za-z0-9]{12,}"),
    re.compile(r"(?i)(aws_secret_access_key|secret_access_key|session_token|private_key|access_key_secret)\s*[:=]\s*\S+"),
    re.compile(r"(?i)k8s-aws-v1\.[A-Za-z0-9_\-=]+"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*"),
    re.compile(r"(?i)(password|token|apikey|api_key|secret[_-]?value)\s*[:=]\s*\S+"),
)


def sanitize_text(value: str) -> str:
    redacted = value
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub(REDACT, redacted)
    return redacted


def sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, dict):
        return {key: REDACT if _is_sensitive_key(key) else sanitize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    return value


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(
        token in lowered
        for token in (
            "password",
            "secret",
            "token",
            "access_key",
            "access_key_secret",
            "session",
            "private_key",
            "kubeconfig",
            "pem",
        )
    )


class SanitizingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = current_correlation_id()
        if isinstance(record.msg, str):
            record.msg = sanitize_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = sanitize_value(record.args)
            else:
                record.args = tuple(sanitize_value(arg) for arg in record.args)
        return True


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s correlation_id=%(correlation_id)s %(name)s %(message)s")
    )
    handler.addFilter(SanitizingFilter())
    root = logging.getLogger()
    if not any(isinstance(existing, logging.StreamHandler) for existing in root.handlers):
        root.addHandler(handler)
    root.setLevel(logging.INFO)
    for name in ("app", "celery", "uvicorn.error"):
        logging.getLogger(name).addFilter(SanitizingFilter())


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    logger = logging.getLogger(name)
    logger.addFilter(SanitizingFilter())
    return logger
