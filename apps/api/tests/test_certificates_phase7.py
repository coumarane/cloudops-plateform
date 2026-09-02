from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.metrics import reset_metrics
from app.core.rbac import Principal
from app.db.models import AcmCertificateRow, CertificateAlertRow, CertificateEndpointRow, CertificateHistoryRow
from app.db.repository import InventoryRepository, certificate_public_id
from app.db.session import SessionLocal
from app.main import app
from app.providers.alibaba.certificates import normalize_cas_certificate, normalize_tls_secret
from app.providers.alibaba.models import AlibabaConnectionConfig
from app.providers.common.certificates import classify_expiry
from app.providers.common.k8s_certs import discovered_from_tls_secret
from app.providers.common.models import DiscoveredCertificate
from app.providers.common.tls import kubernetes_tls_metadata
from app.services.certificate_monitor import evaluate_alerts, refresh_days, upsert_discovered
from app.services.endpoint_tls import EndpointCheckResult, EndpointPolicyError, validate_endpoint_url
from app.services.job_kinds import KIND_CERTIFICATE_DISCOVERY

client = TestClient(app)
NOW = datetime(2026, 9, 2, tzinfo=timezone.utc)


def _pem_bundle(days_valid: int = 90, cn: str = "app.example.com"):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(123456789)
        .not_valid_before(NOW - timedelta(days=10))
        .not_valid_after(NOW + timedelta(days=days_valid))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(cn)]), critical=False)
        .sign(key, hashes.SHA256())
    )
    pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    return pem, key_pem


def _alibaba_config() -> AlibabaConnectionConfig:
    return AlibabaConnectionConfig(
        cloud_region="cn-hangzhou",
        account_id="2",
        role_arn=None,
        session_name="cloudops-alibaba",
        access_key_id_ref=None,
        access_key_secret_ref=None,
        credential_ref=None,
        platform_region="China",
        environment="DEV",
        account_alias="alibaba-china-nonprod",
        cluster_environment_tag="Environment",
    )


def _item(**overrides) -> DiscoveredCertificate:
    payload = dict(
        arn="arn:aws:acm:eu-west-1:1:certificate/demo-1",
        domain_name="demo.example.com",
        subject_alternative_names=["demo.example.com"],
        issuer="Amazon",
        status="ISSUED",
        not_before=NOW - timedelta(days=30),
        not_after=NOW + timedelta(days=90),
        days_remaining=90,
        in_use_by=[],
        renewal_eligibility="ELIGIBLE",
        last_checked=NOW,
        environment="UAT",
        platform_region="EMEA",
        account_alias="aws-emea-nonprod",
        cloud_region="eu-west-1",
        provider="AWS",
        source="acm",
        serial_number="abc123",
    )
    payload.update(overrides)
    return DiscoveredCertificate(**payload)


def test_expiry_classification() -> None:
    assert classify_expiry(None) == "UNKNOWN"
    assert classify_expiry(90) == "HEALTHY"
    assert classify_expiry(61) == "HEALTHY"
    assert classify_expiry(60) == "WARNING"
    assert classify_expiry(31) == "WARNING"
    assert classify_expiry(30) == "CRITICAL"
    assert classify_expiry(8) == "CRITICAL"
    assert classify_expiry(7) == "URGENT"
    assert classify_expiry(1) == "URGENT"
    assert classify_expiry(0) == "EXPIRED"
    assert classify_expiry(-3) == "EXPIRED"


def test_alert_threshold_transitions_and_dedup() -> None:
    session = SessionLocal()
    try:
        row = upsert_discovered(session, _item(days_remaining=45, not_after=NOW + timedelta(days=45)))
        session.flush()
        first = evaluate_alerts(session)
        assert first["created"] == 1
        alert = session.scalar(select(CertificateAlertRow).where(CertificateAlertRow.certificate_id == row.id))
        assert alert is not None
        assert alert.kind == "CERTIFICATE_WARNING"
        assert alert.status == "OPEN"
        alert_id = alert.id
        evaluate_alerts(session)
        alerts = list(session.scalars(select(CertificateAlertRow).where(CertificateAlertRow.certificate_id == row.id)))
        assert len(alerts) == 1
        assert alerts[0].id == alert_id
        row.days_remaining = 5
        row.expiry_status = "URGENT"
        stats = evaluate_alerts(session)
        assert stats["updated"] == 1
        session.refresh(alert)
        assert alert.kind == "CERTIFICATE_URGENT"
        assert alert.status == "OPEN"
    finally:
        session.close()


def test_alert_auto_resolution_on_renewal() -> None:
    session = SessionLocal()
    try:
        row = upsert_discovered(session, _item(days_remaining=3, not_after=NOW + timedelta(days=3), serial_number="old"))
        evaluate_alerts(session)
        renewed = _item(days_remaining=200, not_after=NOW + timedelta(days=200), serial_number="new")
        upsert_discovered(session, renewed)
        stats = evaluate_alerts(session)
        assert stats["resolved"] == 1
        alert = session.scalar(select(CertificateAlertRow))
        assert alert.status == "RESOLVED"
        events = {item.event for item in session.scalars(select(CertificateHistoryRow))}
        assert "renewed" in events or "serial_changed" in events
    finally:
        session.close()


def test_upsert_is_idempotent() -> None:
    session = SessionLocal()
    try:
        first = upsert_discovered(session, _item())
        session.flush()
        second = upsert_discovered(session, _item(issuer="Amazon RSA"))
        session.flush()
        assert first.id == second.id
        rows = list(session.scalars(select(AcmCertificateRow)))
        assert len(rows) == 1
        assert rows[0].issuer == "Amazon RSA"
        assert rows[0].last_seen_at is not None
    finally:
        session.close()


def test_kubernetes_tls_parsing_discards_private_key() -> None:
    pem, key_pem = _pem_bundle()
    secret = {
        "metadata": {"name": "ingress-tls", "namespace": "platform"},
        "data": {
            "tls.crt": base64.b64encode(pem).decode("ascii"),
            "tls.key": base64.b64encode(key_pem).decode("ascii"),
        },
        "type": "kubernetes.io/tls",
    }
    original_keys = set(secret["data"])
    parsed = kubernetes_tls_metadata(secret, now=NOW)
    assert parsed is not None
    assert parsed.common_name == "app.example.com"
    assert set(secret["data"]) == original_keys
    discovered = discovered_from_tls_secret(
        secret,
        arn="arn:aws:eks:eu-west-1:1:secret/cluster/platform/ingress-tls",
        provider="AWS",
        platform_region="EMEA",
        account_alias="aws-emea-nonprod",
        cloud_region="eu-west-1",
        cluster_name="cluster",
        environment="UAT",
    )
    assert discovered is not None
    assert discovered.source == "kubernetes"
    blob = str(discovered)
    assert "BEGIN PRIVATE KEY" not in blob
    assert key_pem.decode() not in blob


def test_external_tls_ssrf_and_allowlist(monkeypatch) -> None:
    try:
        validate_endpoint_url("http://example.com")
        assert False, "http should be rejected"
    except EndpointPolicyError:
        pass
    try:
        validate_endpoint_url("https://localhost", registered=True)
        assert False, "localhost should be rejected"
    except EndpointPolicyError:
        pass
    try:
        validate_endpoint_url("https://127.0.0.1", registered=True)
        assert False, "loopback should be rejected"
    except EndpointPolicyError:
        pass
    try:
        validate_endpoint_url("https://api.example.com")
        assert False, "unlisted host should be rejected when allow-list is empty"
    except EndpointPolicyError:
        pass


def test_aws_and_alibaba_normalization() -> None:
    from app.providers.aws.acm import AcmScanner
    from app.providers.aws.models import AwsConnectionConfig
    from unittest.mock import MagicMock

    client_mock = MagicMock()
    client_mock.get_paginator.return_value.paginate.return_value = [
        {"CertificateSummaryList": [{"CertificateArn": "arn:aws:acm:eu-west-1:1:certificate/x"}]}
    ]
    client_mock.describe_certificate.return_value = {
        "Certificate": {
            "CertificateArn": "arn:aws:acm:eu-west-1:1:certificate/x",
            "DomainName": "api.example.com",
            "SubjectAlternativeNames": ["api.example.com"],
            "Issuer": "Amazon",
            "Status": "ISSUED",
            "NotBefore": NOW - timedelta(days=10),
            "NotAfter": NOW + timedelta(days=80),
            "InUseBy": [],
            "RenewalEligibility": "ELIGIBLE",
            "Serial": "aa11",
        }
    }
    factory = MagicMock()
    factory.client.return_value = client_mock
    config = AwsConnectionConfig(
        cloud_region="eu-west-1",
        account_id="1",
        role_arn=None,
        external_id=None,
        session_name="s",
        profile=None,
        config_secret_arn=None,
        platform_region="EMEA",
        environment="DEV",
        account_alias="aws-emea-nonprod",
        cluster_environment_tag="Environment",
    )
    found = AcmScanner(factory, config).list_certificates()
    assert found[0].source == "acm"
    assert found[0].serial_number == "aa11"
    assert found[0].provider == "AWS"

    cas = normalize_cas_certificate(
        {
            "certificate_id": "cas-1",
            "domain": "dev.china.example.com",
            "end_date": "2026-12-01",
            "start_date": "2026-01-01",
            "issuer": "Aliyun",
            "serial": "cas-serial",
        },
        _alibaba_config(),
        now=NOW,
    )
    assert cas.source == "cas"
    assert cas.provider == "Alibaba"
    assert cas.serial_number == "cas-serial"


def test_partial_provider_failure_continues() -> None:
    from app.services.aws_sync import persist_certificate_results
    from app.topology.loader import load_topology

    topology = load_topology()
    aws = topology.account_by_alias("aws-emea-nonprod")
    apac = topology.account_by_alias("aws-apac-nonprod")
    results = [
        (aws, [_item()], None),
        (apac, None, RuntimeError("apac down")),
    ]
    total = persist_certificate_results(results)
    assert total == 1
    session = SessionLocal()
    try:
        stored = list(session.scalars(select(AcmCertificateRow)))
        assert stored
        env = InventoryRepository(session).environment_row("AWS", "APAC", "DEV")
        if env is not None:
            assert env.last_error
    finally:
        session.close()


def test_api_filters_and_scan_enqueue() -> None:
    from unittest.mock import patch

    response = client.get("/api/v1/certificates", params={"status": "critical"})
    assert response.status_code == 200
    for item in response.json()["items"]:
        assert item["expiryStatus"] == "CRITICAL"
        assert "privateKey" not in item
        assert "tls.key" not in str(item)
    within = client.get("/api/v1/certificates", params={"expires_within_days": 30})
    assert within.status_code == 200
    assert all(0 < item["daysRemaining"] <= 30 for item in within.json()["items"])
    featured = client.get("/api/v1/certificates/cert-amer-prd-wildcard")
    assert featured.status_code == 200
    assert featured.json()["id"] == "cert-amer-prd-wildcard"
    history = client.get("/api/v1/certificates/cert-amer-prd-wildcard/history")
    assert history.status_code == 200
    with patch("app.services.aws_sync.scan_aws_certificates", return_value=0), patch(
        "app.services.alibaba_sync.scan_alibaba_certificates", return_value=0
    ):
        scan = client.post("/api/v1/certificates/scan")
    assert scan.status_code == 200
    assert scan.json()["queued"] is True
    assert scan.json()["kind"] == KIND_CERTIFICATE_DISCOVERY


def test_dashboard_certificate_kpis() -> None:
    body = client.get("/api/v1/dashboard").json()
    assert "certsHealthy" in body["kpis"]
    assert "certsExpiring60d" in body["kpis"]
    assert "certsExpiring30d" in body["kpis"]
    assert "certsExpiring7d" in body["kpis"]
    assert "certsExpired" in body["kpis"]
    assert body["kpis"]["certsExpiring14d"] >= 0
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "cloudops_certificates" in metrics.text or metrics.text.endswith("\n")


def test_no_private_key_persistence() -> None:
    pem, key_pem = _pem_bundle()
    secret = {
        "metadata": {"name": "ingress-tls", "namespace": "platform"},
        "data": {
            "tls.crt": base64.b64encode(pem).decode("ascii"),
            "tls.key": base64.b64encode(key_pem).decode("ascii"),
        },
        "type": "kubernetes.io/tls",
    }
    parsed = normalize_tls_secret(
        secret,
        _alibaba_config(),
        cluster_name="platform-ack-dev",
        now=NOW,
    )
    session = SessionLocal()
    try:
        row = upsert_discovered(session, parsed)
        session.commit()
        stored = session.get(AcmCertificateRow, row.id)
        dumped = " ".join(str(getattr(stored, column)) for column in stored.__table__.columns.keys())
        assert "BEGIN PRIVATE KEY" not in dumped
        assert "tls.key" not in dumped
        assert key_pem.decode() not in dumped
    finally:
        session.close()


def test_job_retry_configuration() -> None:
    import sys
    from pathlib import Path

    worker_root = Path(__file__).resolve().parents[2] / "worker"
    if str(worker_root) not in sys.path:
        sys.path.insert(0, str(worker_root))
    from celery_app import celery_app
    from app.core.config import settings

    schedule = celery_app.conf.beat_schedule
    assert schedule["certificate-discovery"]["schedule"] == settings.certificate_discovery_interval_seconds
    assert schedule["certificate-expiry-scan"]["schedule"] == settings.certificate_expiry_interval_seconds
    assert schedule["certificate-endpoint-validation"]["schedule"] == settings.certificate_endpoint_interval_seconds
    assert schedule["certificate-alert-evaluation"]["schedule"] == settings.certificate_alert_interval_seconds
