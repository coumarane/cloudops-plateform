from __future__ import annotations


class AzureIntegrationError(Exception):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class AzureAuthError(AzureIntegrationError):
    def __init__(self, message: str = "Azure authentication failed") -> None:
        super().__init__(message, retryable=False)


class AzurePermissionError(AzureIntegrationError):
    def __init__(self, message: str = "Azure permission denied") -> None:
        super().__init__(message, retryable=False)


def classify_azure_error(error: Exception) -> AzureIntegrationError:
    if isinstance(error, AzureIntegrationError):
        return error
    text = str(error)
    lowered = text.lower()
    if any(token in lowered for token in ("unauthorized", "authentication", "credential", "login")):
        return AzureAuthError(text or "Azure authentication failed")
    if any(token in lowered for token in ("forbidden", "authorization", "permission", "access denied")):
        return AzurePermissionError(text or "Azure permission denied")
    return AzureIntegrationError(text or "Azure request failed")
