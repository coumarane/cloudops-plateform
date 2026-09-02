from __future__ import annotations

import ipaddress
import re
import socket
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.core.config import settings
from app.core.logging import get_logger
from app.services.endpoint_tls import BLOCKED_NETWORKS, EndpointPolicyError, allowlisted_hosts

logger = get_logger(__name__)

BLOCKED_HOSTS = {"localhost", "metadata.google.internal", "metadata", "instance-data", "kubernetes", "kubernetes.default"}


@dataclass(frozen=True)
class HttpProbeResult:
    url: str
    success: bool
    status: str
    latency_ms: int
    status_code: int | None
    error_category: str
    summary: str


def health_allowlisted_hosts() -> set[str]:
    raw = settings.health_http_allowlist or settings.certificate_https_allowlist or ""
    return {item.strip().lower() for item in raw.split(",") if item.strip()} or allowlisted_hosts()


def validate_health_url(url: str, *, registered: bool = False) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    if parsed.scheme not in {"http", "https"}:
        raise EndpointPolicyError("Only HTTP and HTTPS endpoints are allowed")
    host = (parsed.hostname or "").lower()
    if not host:
        raise EndpointPolicyError("Hostname is required")
    if host in BLOCKED_HOSTS or host.endswith(".internal") or host.endswith(".local"):
        raise EndpointPolicyError("Internal hostnames are not allowed")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise EndpointPolicyError("Hostname could not be resolved") from error
    for info in infos:
        address = info[4][0]
        ip = ipaddress.ip_address(address)
        if any(ip in network for network in BLOCKED_NETWORKS) or ip.is_private or ip.is_loopback or ip.is_link_local:
            raise EndpointPolicyError("Resolved address is not allowed")
    allowed = health_allowlisted_hosts()
    if allowed:
        if host not in allowed and not any(host.endswith(f".{item}") for item in allowed):
            raise EndpointPolicyError("Hostname is not on the HTTP health allow-list")
    elif not registered:
        raise EndpointPolicyError("Hostname is not on the HTTP health allow-list")
    return host


def expected_status_codes(spec: str | None) -> set[int]:
    raw = (spec or "200-299").strip() or "200-299"
    codes: set[int] = set()
    for part in raw.split(","):
        item = part.strip()
        if not item:
            continue
        if "-" in item:
            start, end = item.split("-", 1)
            codes.update(range(int(start), int(end) + 1))
        else:
            codes.add(int(item))
    return codes or set(range(200, 300))


def probe_http(
    url: str,
    *,
    method: str = "GET",
    timeout: float | None = None,
    expected: str = "200-299",
    expected_pattern: str = "",
    registered: bool = False,
) -> HttpProbeResult:
    timeout = timeout if timeout is not None else settings.health_http_timeout_seconds
    host = validate_health_url(url, registered=registered)
    method = (method or "GET").upper()
    if method not in {"GET", "HEAD"}:
        raise EndpointPolicyError("Only GET and HEAD methods are allowed")
    started = datetime.now(timezone.utc)
    try:
        request = Request(url, method=method, headers={"User-Agent": "CloudOps-Health/1.0", "Accept": "*/*"})
        kwargs: dict = {"timeout": timeout}
        if urlparse(url).scheme == "https":
            kwargs["context"] = ssl.create_default_context()
        with urlopen(request, **kwargs) as response:
            status_code = int(getattr(response, "status", 0) or 0)
            snippet = b""
            if expected_pattern:
                snippet = response.read(2048)
        latency = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        codes = expected_status_codes(expected)
        matched = True
        if expected_pattern:
            matched = bool(re.search(expected_pattern.encode() if isinstance(expected_pattern, str) else expected_pattern, snippet))
        ok = status_code in codes and matched
        from app.integrations.health.status import CRITICAL, HEALTHY

        return HttpProbeResult(
            url=url,
            success=ok,
            status=HEALTHY if ok else CRITICAL,
            latency_ms=latency,
            status_code=status_code,
            error_category="" if ok else "http",
            summary=f"HTTP {status_code}" + ("" if matched else " pattern mismatch"),
        )
    except EndpointPolicyError:
        raise
    except TimeoutError:
        latency = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        from app.integrations.health.status import UNHEALTHY

        return HttpProbeResult(url=url, success=False, status=UNHEALTHY, latency_ms=latency, status_code=None, error_category="timeout", summary="HTTP timeout")
    except Exception as error:
        latency = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        logger.warning("HTTP health probe failed host=%s", host)
        status_code = getattr(getattr(error, "code", None), "real", None)
        code = getattr(error, "code", None)
        if isinstance(code, int):
            from app.integrations.health.status import CRITICAL, HEALTHY

            codes = expected_status_codes(expected)
            ok = code in codes
            return HttpProbeResult(
                url=url,
                success=ok,
                status=HEALTHY if ok else CRITICAL,
                latency_ms=latency,
                status_code=code,
                error_category="" if ok else "http",
                summary=f"HTTP {code}",
            )
        from app.integrations.health.status import UNHEALTHY

        return HttpProbeResult(url=url, success=False, status=UNHEALTHY, latency_ms=latency, status_code=None, error_category="network", summary="HTTP network error")
