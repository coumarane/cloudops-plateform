from __future__ import annotations


class GcpIntegrationError(Exception):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class GcpAuthError(GcpIntegrationError):
    def __init__(self, message: str = "GCP authentication failed") -> None:
        super().__init__(message, retryable=False)


class GcpPermissionError(GcpIntegrationError):
    def __init__(self, message: str = "GCP permission denied") -> None:
        super().__init__(message, retryable=False)


def classify_gcp_error(error: Exception) -> GcpIntegrationError:
    if isinstance(error, GcpIntegrationError):
        return error
    text = str(error)
    lowered = text.lower()
    if any(token in lowered for token in ("unauthenticated", "authentication", "credential", "token")):
        return GcpAuthError(text or "GCP authentication failed")
    if any(token in lowered for token in ("permission", "forbidden", "access denied", "403")):
        return GcpPermissionError(text or "GCP permission denied")
    return GcpIntegrationError(text or "GCP request failed")
