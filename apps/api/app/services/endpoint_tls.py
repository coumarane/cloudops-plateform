from __future__ import annotations

import ipaddress
import socket
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

from app.core.config import settings
from app.core.logging import get_logger
from app.providers.common.tls import ParsedCertificate, parse_certificate_pem

logger = get_logger(__name__)

BLOCKED_NETWORKS = (
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)


class EndpointPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class EndpointCheckResult:
    hostname: str
    success: bool
    latency_ms: int
    error_category: str
    certificate: ParsedCertificate | None


def allowlisted_hosts() -> set[str]:
    raw = settings.certificate_https_allowlist or ""
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def validate_endpoint_url(url: str, *, registered: bool = False) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    if parsed.scheme != "https":
        raise EndpointPolicyError("Only HTTPS endpoints are allowed")
    host = (parsed.hostname or "").lower()
    if not host:
        raise EndpointPolicyError("Hostname is required")
    if host in {"localhost", "metadata.google.internal", "metadata", "instance-data"}:
        raise EndpointPolicyError("Internal hostnames are not allowed")
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise EndpointPolicyError("Hostname could not be resolved") from error
    for info in infos:
        address = info[4][0]
        ip = ipaddress.ip_address(address)
        if any(ip in network for network in BLOCKED_NETWORKS) or ip.is_private or ip.is_loopback or ip.is_link_local:
            raise EndpointPolicyError("Resolved address is not allowed")
    allowed = allowlisted_hosts()
    if allowed:
        if host not in allowed and not any(host.endswith(f".{item}") for item in allowed):
            raise EndpointPolicyError("Hostname is not on the HTTPS certificate allow-list")
    elif not registered:
        raise EndpointPolicyError("Hostname is not on the HTTPS certificate allow-list")
    return host


def check_https_endpoint(url: str, *, timeout: float | None = None, registered: bool = False) -> EndpointCheckResult:
    timeout = timeout if timeout is not None else settings.certificate_https_timeout_seconds
    host = validate_endpoint_url(url, registered=registered)
    started = datetime.now(timezone.utc)
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=host) as tls:
                der = tls.getpeercert(binary_form=True)
        pem = ssl.DER_cert_to_PEM_cert(der).encode("utf-8") if der else b""
        parsed = parse_certificate_pem(pem) if pem else None
        latency = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return EndpointCheckResult(hostname=host, success=True, latency_ms=latency, error_category="", certificate=parsed)
    except EndpointPolicyError:
        raise
    except ssl.SSLError:
        latency = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return EndpointCheckResult(hostname=host, success=False, latency_ms=latency, error_category="tls", certificate=None)
    except TimeoutError:
        latency = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return EndpointCheckResult(hostname=host, success=False, latency_ms=latency, error_category="timeout", certificate=None)
    except Exception:
        latency = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        logger.warning("HTTPS endpoint check failed host=%s", host)
        return EndpointCheckResult(hostname=host, success=False, latency_ms=latency, error_category="network", certificate=None)
