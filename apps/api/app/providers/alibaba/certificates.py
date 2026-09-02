from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.providers.alibaba.client import AlibabaClientFactory
from app.providers.alibaba.exceptions import classify_alibaba_error
from app.providers.alibaba.models import AlibabaConnectionConfig
from app.providers.common.k8s_certs import discovered_from_tls_secret
from app.providers.common.models import DiscoveredCertificate

logger = get_logger(__name__)


def _as_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
        try:
            parsed = datetime.strptime(text[:19], fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _days_remaining(not_after: datetime | None, now: datetime) -> int | None:
    if not_after is None:
        return None
    return (not_after - now).days


def normalize_cas_certificate(
    payload: dict[str, Any],
    config: AlibabaConnectionConfig,
    *,
    now: datetime | None = None,
) -> DiscoveredCertificate:
    now = now or datetime.now(timezone.utc)
    cert_id = str(payload.get("certificate_id") or payload.get("CertificateId") or payload.get("id") or "")
    domain = str(payload.get("domain") or payload.get("common_name") or payload.get("name") or cert_id)
    sans_raw = payload.get("sans") or payload.get("san") or payload.get("subject_alt_name") or []
    if isinstance(sans_raw, str):
        sans = [item.strip() for item in sans_raw.replace(";", ",").split(",") if item.strip()]
    else:
        sans = [str(item) for item in sans_raw]
    not_before = _as_datetime(payload.get("start_date") or payload.get("not_before") or payload.get("startDate"))
    not_after = _as_datetime(payload.get("end_date") or payload.get("not_after") or payload.get("endDate"))
    days = _days_remaining(not_after, now)
    serial = str(payload.get("serial") or payload.get("serial_number") or payload.get("fingerprint") or "")
    return DiscoveredCertificate(
        arn=f"acs:cas:{config.cloud_region}:{config.account_id or 'unknown'}:certificate/{cert_id or domain}",
        domain_name=domain,
        subject_alternative_names=sans or [domain],
        issuer=str(payload.get("issuer") or payload.get("org_name") or "Alibaba Cloud CAS"),
        status=str(payload.get("status") or "ISSUED"),
        not_before=not_before,
        not_after=not_after,
        days_remaining=days,
        in_use_by=[],
        renewal_eligibility=str(payload.get("renewal_status") or "UNKNOWN"),
        last_checked=now,
        environment="",
        platform_region=config.platform_region,
        account_alias=config.account_alias,
        cloud_region=config.cloud_region,
        provider="Alibaba",
        cluster_name="",
        namespace="",
        source="cas",
        serial_number=serial,
        auto_renew=bool(payload.get("auto_renew") or payload.get("autoRenew")),
    )


def normalize_tls_secret(
    secret: dict[str, Any],
    config: AlibabaConnectionConfig,
    *,
    cluster_name: str,
    now: datetime | None = None,
) -> DiscoveredCertificate | None:
    now = now or datetime.now(timezone.utc)
    metadata = secret.get("metadata") or {}
    namespace = str(metadata.get("namespace") or "default")
    name = str(metadata.get("name") or "tls")
    arn = f"acs:ack:{config.cloud_region}:{config.account_id or 'unknown'}:secret/{cluster_name}/{namespace}/{name}"
    parsed = discovered_from_tls_secret(
        secret,
        arn=arn,
        provider="Alibaba",
        platform_region=config.platform_region,
        account_alias=config.account_alias,
        cloud_region=config.cloud_region,
        cluster_name=cluster_name,
        environment="",
        now=now,
    )
    if parsed is not None:
        parsed.last_checked = now
    return parsed


class AlibabaCertificateScanner:
    def __init__(self, factory: AlibabaClientFactory, config: AlibabaConnectionConfig) -> None:
        self._factory = factory
        self._config = config

    def list_certificates(self) -> list[DiscoveredCertificate]:
        discovered: list[DiscoveredCertificate] = []
        try:
            for payload in self._factory.list_user_certificates():
                discovered.append(normalize_cas_certificate(payload, self._config))
        except Exception as error:
            logger.warning("CAS certificate listing failed error=%s", classify_alibaba_error(error))
            raise classify_alibaba_error(error) from error
        logger.info("Discovered %s Alibaba CAS certificates account=%s", len(discovered), self._config.account_alias)
        return discovered
