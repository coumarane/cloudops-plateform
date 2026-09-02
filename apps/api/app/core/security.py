import re

SECRET_VALUE_PATTERN = re.compile(
    r"(password|token|apikey|api_key|secret[_-]?value|private[_-]?key)\s*[:=]",
    re.IGNORECASE,
)

FORBIDDEN_KEYS = {
    "password",
    "token",
    "apikey",
    "api_key",
    "secret_value",
    "private_key",
    "pem",
    "kubeconfig",
    "aws_secret_access_key",
    "secret_access_key",
    "session_token",
    "access_key_id",
    "aws_access_key_id",
}


def contains_secret_value(value: str) -> bool:
    return bool(SECRET_VALUE_PATTERN.search(value))


def assert_no_secret_values(values: list[str]) -> None:
    leaked = [value for value in values if contains_secret_value(value)]
    if leaked:
        raise ValueError("Secret values must never be returned by the CloudOps API.")


def walk_strings(payload: object) -> list[str]:
    found: list[str] = []
    if isinstance(payload, str):
        found.append(payload)
    elif isinstance(payload, dict):
        for key, value in payload.items():
            if key.lower() in FORBIDDEN_KEYS:
                raise ValueError(f"Forbidden secret field {key!r} must never be serialized.")
            found.extend(walk_strings(value))
    elif isinstance(payload, list):
        for item in payload:
            found.extend(walk_strings(item))
    return found
