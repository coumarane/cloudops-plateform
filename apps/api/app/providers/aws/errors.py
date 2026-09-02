from botocore.exceptions import (
    ClientError,
    ConnectTimeoutError,
    EndpointConnectionError,
    NoCredentialsError,
    PartialCredentialsError,
    ReadTimeoutError,
)

AUTH_CODES = {
    "ExpiredToken",
    "ExpiredTokenException",
    "InvalidClientTokenId",
    "UnrecognizedClientException",
    "AuthFailure",
    "InvalidUserID.NotFound",
    "AccessDeniedException",  # STS assume-role identity failure is classified below
}

PERMISSION_CODES = {
    "AccessDenied",
    "AccessDeniedException",
    "UnauthorizedOperation",
    "ForbiddenException",
    "AccessDeniedException",
}

TRANSIENT_CODES = {
    "Throttling",
    "ThrottlingException",
    "RequestLimitExceeded",
    "TooManyRequestsException",
    "ServiceUnavailable",
    "InternalFailure",
    "InternalServerError",
}


class AwsIntegrationError(Exception):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class AwsAuthError(AwsIntegrationError):
    def __init__(self, message: str = "AWS authentication failed") -> None:
        super().__init__(message, retryable=False)


class AwsPermissionError(AwsIntegrationError):
    def __init__(self, message: str = "AWS permission denied") -> None:
        super().__init__(message, retryable=False)


class AwsTransientError(AwsIntegrationError):
    def __init__(self, message: str = "Transient AWS error") -> None:
        super().__init__(message, retryable=True)


def classify_aws_error(error: Exception) -> AwsIntegrationError:
    if isinstance(error, (NoCredentialsError, PartialCredentialsError)):
        return AwsAuthError("AWS credentials were not found or were incomplete")
    if isinstance(error, (EndpointConnectionError, ConnectTimeoutError, ReadTimeoutError)):
        return AwsTransientError("AWS endpoint was unreachable")
    if isinstance(error, ClientError):
        code = error.response.get("Error", {}).get("Code", "")
        status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
        operation = error.operation_name if hasattr(error, "operation_name") else ""
        if code in TRANSIENT_CODES or status in {429, 500, 502, 503, 504}:
            return AwsTransientError(f"Transient AWS error ({code or status})")
        if code in {"ExpiredToken", "ExpiredTokenException", "InvalidClientTokenId", "UnrecognizedClientException"}:
            return AwsAuthError(f"AWS authentication failed ({code})")
        if code in {"AccessDenied", "AccessDeniedException", "UnauthorizedOperation", "ForbiddenException"}:
            if operation == "AssumeRole" or "sts" in operation.lower():
                return AwsPermissionError("Not permitted to assume the CloudOps AWS role")
            return AwsPermissionError(f"AWS permission denied ({code})")
        if status == 401:
            return AwsAuthError("AWS authentication failed")
        if status == 403:
            return AwsPermissionError("AWS permission denied")
        return AwsIntegrationError(f"AWS request failed ({code or status})")
    if isinstance(error, AwsIntegrationError):
        return error
    return AwsIntegrationError(str(error))
