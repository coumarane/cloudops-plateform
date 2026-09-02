from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from app.core.logging import get_logger
from app.integrations.github.exceptions import GitHubApiError, GitHubAuthError, GitHubRateLimitError

logger = get_logger(__name__)

HttpFn = Callable[[str, str, dict[str, str], bytes | None], tuple[int, dict[str, str], bytes]]


def _default_http(method: str, url: str, headers: dict[str, str], body: bytes | None) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, {key.lower(): value for key, value in response.headers.items()}, response.read()
    except urllib.error.HTTPError as error:
        payload = error.read() if error.fp else b""
        return error.code, {key.lower(): value for key, value in error.headers.items()}, payload


class GitHubClient:
    def __init__(
        self,
        *,
        api_url: str,
        token: str,
        http: HttpFn | None = None,
        sleep: Callable[[float], None] | None = None,
        max_retries: int = 3,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.token = token
        self._http = http or _default_http
        self._sleep = sleep or time.sleep
        self.max_retries = max_retries
        self.rate_limit_remaining: int | None = None
        self.rate_limit_reset: int | None = None

    def request(self, method: str, path: str, *, params: dict | None = None, json_body: dict | None = None) -> Any:
        url = path if path.startswith("http") else f"{self.api_url}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode({key: value for key, value in params.items() if value is not None})}"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cloudops-platform",
        }
        body = json.dumps(json_body).encode("utf-8") if json_body is not None else None
        if body is not None:
            headers["Content-Type"] = "application/json"
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            status, response_headers, payload = self._http(method, url, headers, body)
            self._record_rate_limit(response_headers)
            if status == 401:
                raise GitHubAuthError("GitHub rejected the installation token")
            if status == 403 and self.rate_limit_remaining == 0:
                wait_for = max(1, (self.rate_limit_reset or int(time.time()) + 5) - int(time.time()))
                last_error = GitHubRateLimitError(
                    "GitHub API rate limit exceeded",
                    reset_at=self.rate_limit_reset,
                    remaining=0,
                )
                if attempt >= self.max_retries:
                    raise last_error
                logger.info("GitHub rate limited; backing off seconds=%s", min(wait_for, 30))
                self._sleep(min(float(wait_for), 30.0))
                continue
            if status >= 500:
                last_error = GitHubApiError(f"GitHub server error {status}", status=status)
                if attempt >= self.max_retries:
                    raise last_error
                self._sleep(min(2 ** attempt, 8))
                continue
            if status >= 400:
                detail = payload.decode("utf-8", errors="replace")[:300]
                raise GitHubApiError(f"GitHub API error {status}: {detail}", status=status)
            if not payload:
                return None
            return json.loads(payload.decode("utf-8"))
        raise last_error or GitHubApiError("GitHub request failed")

    def paginate(self, path: str, *, params: dict | None = None, item_key: str | None = None) -> list[dict]:
        page = 1
        collected: list[dict] = []
        query = dict(params or {})
        while True:
            query["per_page"] = 100
            query["page"] = page
            payload = self.request("GET", path, params=query)
            if payload is None:
                break
            if isinstance(payload, list):
                batch = payload
            elif item_key:
                batch = list(payload.get(item_key) or [])
            elif isinstance(payload, dict):
                batch = list(payload.get("workflow_runs") or payload.get("jobs") or payload.get("repositories") or payload.get("workflows") or [])
            else:
                batch = []
            collected.extend(batch)
            if len(batch) < 100:
                break
            page += 1
            if page > 20:
                break
        return collected

    def _record_rate_limit(self, headers: dict[str, str]) -> None:
        remaining = headers.get("x-ratelimit-remaining")
        reset = headers.get("x-ratelimit-reset")
        if remaining is not None:
            try:
                self.rate_limit_remaining = int(remaining)
            except ValueError:
                pass
        if reset is not None:
            try:
                self.rate_limit_reset = int(reset)
            except ValueError:
                pass
