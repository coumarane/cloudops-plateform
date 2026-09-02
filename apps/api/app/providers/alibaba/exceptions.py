from __future__ import annotations


class AlibabaIntegrationError(Exception):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class AlibabaAuthError(AlibabaIntegrationError):
    def __init__(self, message: str = "Alibaba authentication failed") -> None:
        super().__init__(message, retryable=False)


class AlibabaPermissionError(AlibabaIntegrationError):
    def __init__(self, message: str = "Alibaba permission denied") -> None:
        super().__init__(message, retryable=False)


class AlibabaTransientError(AlibabaIntegrationError):
    def __init__(self, message: str = "Transient Alibaba error") -> None:
        super().__init__(message, retryable=True)


def classify_alibaba_error(error: Exception) -> AlibabaIntegrationError:
    if isinstance(error, AlibabaIntegrationError):
        return error
    text = str(error)
    lowered = text.lower()
    code = ""
    status = 0
    if hasattr(error, "code"):
        code = str(getattr(error, "code") or "")
    if hasattr(error, "statusCode"):
        try:
            status = int(getattr(error, "statusCode") or 0)
        except (TypeError, ValueError):
            status = 0
    if hasattr(error, "status_code"):
        try:
            status = status or int(getattr(error, "status_code") or 0)
        except (TypeError, ValueError):
            pass
    combined = f"{code} {lowered}"
    if status in {429, 500, 502, 503, 504} or any(
        token in combined for token in ("throttl", "timeout", "unavailable", "servicebusy", "internalerror")
    ):
        return AlibabaTransientError("Transient Alibaba Cloud error")
    if status in {401, 403} or any(
        token in combined
        for token in (
            "invalidaccesskeyid",
            "signaturedoesnotmatch",
            "invalidsecuritytoken",
            "forbidden",
            "unauthorized",
            "accessdenied",
            "incomplete signature",
            "invalidaccesskey",
        )
    ):
        if "accessdenied" in combined or "forbidden" in combined or status == 403:
            return AlibabaPermissionError("Alibaba permission denied")
        return AlibabaAuthError("Alibaba authentication failed")
    if "credential" in lowered or "access key" in lowered:
        return AlibabaAuthError("Alibaba credentials were not found or were incomplete")
    return AlibabaIntegrationError("Alibaba Cloud request failed")
