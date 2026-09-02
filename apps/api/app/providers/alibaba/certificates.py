from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.providers.alibaba.client import AlibabaClientFactory
from app.providers.alibaba.exceptions import classify_alibaba_error
from app.providers.alibaba.models import AlibabaConnectionConfig
from app.providers.common.certificates import classify_certificate_age
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
    _status, classification = classify_certificate_age(days)
    return DiscoveredCertificate(
        arn=f"acs:cas:{config.cloud_region}:{config.account_id or 'unknown'}:certificate/{cert_id or domain}",
        domain_name=domain,
        subject_alternative_names=sans or [domain],
        issuer=str(payload.get("issuer") or payload.get("org_name") or "Alibaba Cloud CAS"),
        status=str(payload.get("status") or classification),
        not_before=not_before,
        not_after=not_after,
        days_remaining=days,
        in_use_by=[],
        renewal_eligibility=classification,
        last_checked=now,
        environment="",
        platform_region=config.platform_region,
        account_alias=config.account_alias,
        cloud_region=config.cloud_region,
        provider="Alibaba",
        cluster_name="",
        namespace="",
        source="cas",
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
    data = secret.get("data") or {}
    cert_b64 = data.get("tls.crt") or data.get("tls_crt")
    if not cert_b64:
        return None
    try:
        pem = base64.b64decode(cert_b64)
    except Exception:
        return None
    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        from cryptography.x509.oid import NameOID, ExtensionOID
    except ImportError:
        logger.warning("cryptography is not installed; skipping Kubernetes TLS certificate parse")
        return None
    try:
        parsed = x509.load_pem_x509_certificate(pem, default_backend())
    except Exception:
        return None
    cn_attrs = parsed.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    domain = cn_attrs[0].value if cn_attrs else str(metadata.get("name") or "tls")
    sans: list[str] = []
    try:
        ext = parsed.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        sans = [str(name.value) if hasattr(name, "value") else str(name) for name in ext.value]
    except Exception:
        sans = [domain]
    issuer_cn = parsed.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
    issuer = issuer_cn[0].value if issuer_cn else parsed.issuer.rfc4514_string()
    not_before = parsed.not_valid_before_utc if hasattr(parsed, "not_valid_before_utc") else parsed.not_valid_before.replace(tzinfo=timezone.utc)
    not_after = parsed.not_valid_after_utc if hasattr(parsed, "not_valid_after_utc") else parsed.not_valid_after.replace(tzinfo=timezone.utc)
    days = _days_remaining(not_after, now)
    _status, classification = classify_certificate_age(days)
    namespace = str(metadata.get("namespace") or "default")
    name = str(metadata.get("name") or domain)
    return DiscoveredCertificate(
        arn=f"acs:ack:{config.cloud_region}:{config.account_id or 'unknown'}:secret/{cluster_name}/{namespace}/{name}",
        domain_name=str(domain),
        subject_alternative_names=sans or [str(domain)],
        issuer=str(issuer),
        status=classification,
        not_before=not_before,
        not_after=not_after,
        days_remaining=days,
        in_use_by=[f"{namespace}/{name}"],
        renewal_eligibility=classification,
        last_checked=now,
        environment="",
        platform_region=config.platform_region,
        account_alias=config.account_alias,
        cloud_region=config.cloud_region,
        provider="Alibaba",
        cluster_name=cluster_name,
        namespace=namespace,
        source="kubernetes",
    )


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
