from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.providers.common.certificates import classify_expiry

logger = get_logger(__name__)

FORBIDDEN_TLS_KEYS = {"tls.key", "key", "private_key", "privatekey"}


@dataclass(frozen=True)
class ParsedCertificate:
    common_name: str
    subject_alternative_names: list[str]
    issuer: str
    serial_number: str
    valid_from: datetime | None
    expires_at: datetime | None
    days_remaining: int | None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def parse_certificate_pem(pem: bytes, *, now: datetime | None = None) -> ParsedCertificate | None:
    """Extract public metadata from a PEM certificate and discard the parsed object."""
    now = now or datetime.now(timezone.utc)
    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        from cryptography.x509.oid import ExtensionOID, NameOID
    except ImportError:
        logger.warning("cryptography is not installed; skipping certificate parse")
        return None
    try:
        parsed = x509.load_pem_x509_certificate(pem, default_backend())
    except Exception:
        try:
            parsed = x509.load_der_x509_certificate(pem, default_backend())
        except Exception:
            return None
    try:
        cn_attrs = parsed.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        common_name = str(cn_attrs[0].value) if cn_attrs else ""
        sans: list[str] = []
        try:
            ext = parsed.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            sans = [str(getattr(name, "value", name)) for name in ext.value]
        except Exception:
            sans = [common_name] if common_name else []
        issuer_cn = parsed.issuer.get_attributes_for_oid(NameOID.COMMON_NAME)
        issuer = str(issuer_cn[0].value) if issuer_cn else parsed.issuer.rfc4514_string()
        valid_from = parsed.not_valid_before_utc if hasattr(parsed, "not_valid_before_utc") else _as_utc(parsed.not_valid_before)
        expires_at = parsed.not_valid_after_utc if hasattr(parsed, "not_valid_after_utc") else _as_utc(parsed.not_valid_after)
        days = (expires_at - now).days if expires_at else None
        serial = format(parsed.serial_number, "x")
        return ParsedCertificate(
            common_name=common_name,
            subject_alternative_names=sans or ([common_name] if common_name else []),
            issuer=issuer,
            serial_number=serial,
            valid_from=valid_from,
            expires_at=expires_at,
            days_remaining=days,
        )
    finally:
        parsed = None  # type: ignore[assignment]


def kubernetes_tls_metadata(secret: dict, *, now: datetime | None = None) -> ParsedCertificate | None:
    data = dict(secret.get("data") or {})
    for forbidden in FORBIDDEN_TLS_KEYS:
        data.pop(forbidden, None)
    cert_b64 = data.get("tls.crt") or data.get("tls_crt") or data.get("cert")
    if not cert_b64:
        return None
    import base64

    try:
        pem = base64.b64decode(cert_b64) if isinstance(cert_b64, str) else cert_b64
    except Exception:
        return None
    try:
        return parse_certificate_pem(pem, now=now)
    finally:
        pem = b""


def expiry_class(days_remaining: int | None) -> str:
    return classify_expiry(days_remaining)
