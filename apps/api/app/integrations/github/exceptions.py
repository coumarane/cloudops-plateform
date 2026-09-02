from __future__ import annotations


class GitHubError(Exception):
    """Base GitHub integration error."""


class GitHubNotConfigured(GitHubError):
    pass


class GitHubAuthError(GitHubError):
    pass


class GitHubRateLimitError(GitHubError):
    def __init__(self, message: str, *, reset_at: int | None = None, remaining: int | None = None):
        super().__init__(message)
        self.reset_at = reset_at
        self.remaining = remaining


class GitHubWebhookError(GitHubError):
    pass


class GitHubApiError(GitHubError):
    def __init__(self, message: str, *, status: int | None = None):
        super().__init__(message)
        self.status = status
