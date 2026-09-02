from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.logging import get_logger
from app.providers.common.models import DiscoveredCertificate
from app.providers.common.tls import kubernetes_tls_metadata

logger = get_logger(__name__)


def discovered_from_tls_secret(
    secret: dict[str, Any],
    *,
    arn: str,
    provider: str,
    platform_region: str,
    account_alias: str,
    cloud_region: str,
    cluster_name: str,
    cluster_id: str = "",
    environment: str = "",
    account_id: str = "",
    now: datetime | None = None,
) -> DiscoveredCertificate | None:
    metadata = secret.get("metadata") or {}
    parsed = kubernetes_tls_metadata(secret, now=now)
    if parsed is None:
        return None
    namespace = str(metadata.get("namespace") or "default")
    name = str(metadata.get("name") or parsed.common_name or "tls")
    domain = parsed.common_name or name
    return DiscoveredCertificate(
        arn=arn,
        domain_name=domain,
        subject_alternative_names=list(parsed.subject_alternative_names),
        issuer=parsed.issuer,
        status=parsed.days_remaining is not None and "ISSUED" or "UNKNOWN",
        not_before=parsed.valid_from,
        not_after=parsed.expires_at,
        days_remaining=parsed.days_remaining,
        in_use_by=[f"{namespace}/{name}"],
        renewal_eligibility="UNKNOWN",
        environment=environment,
        platform_region=platform_region,
        account_alias=account_alias,
        cloud_region=cloud_region,
        provider=provider,
        cluster_name=cluster_name,
        namespace=namespace,
        source="kubernetes",
        serial_number=parsed.serial_number,
        cluster_id=cluster_id,
    )


def ingress_secret_hosts(ingresses: list[Any]) -> dict[tuple[str, str], list[str]]:
    mapping: dict[tuple[str, str], list[str]] = {}
    for ingress in ingresses:
        metadata = getattr(ingress, "metadata", None)
        spec = getattr(ingress, "spec", None)
        namespace = str(getattr(metadata, "namespace", None) or "default")
        ingress_name = str(getattr(metadata, "name", None) or "ingress")
        tls_entries = getattr(spec, "tls", None) or []
        for entry in tls_entries:
            secret_name = str(getattr(entry, "secret_name", None) or getattr(entry, "secretName", None) or "")
            hosts = [str(host) for host in (getattr(entry, "hosts", None) or []) if host]
            if not secret_name:
                continue
            key = (namespace, secret_name)
            current = mapping.setdefault(key, [])
            current.append(f"ingress:{namespace}/{ingress_name}")
            current.extend(hosts)
    return mapping


def apply_ingress_usage(certificates: list[DiscoveredCertificate], hosts: dict[tuple[str, str], list[str]]) -> None:
    for cert in certificates:
        secret_name = ""
        if cert.in_use_by:
            raw = cert.in_use_by[0]
            secret_name = raw.split("/", 1)[-1]
        extra = hosts.get((cert.namespace, secret_name), [])
        if extra:
            merged = list(dict.fromkeys([*cert.in_use_by, *extra]))
            cert.in_use_by = merged
