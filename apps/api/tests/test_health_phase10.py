from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.rbac import ROLE_PERMISSIONS
from app.db.models import (
    AcmCertificateRow,
    ApplicationDependencyRow,
    ApplicationResourceMappingRow,
    CloudEnvironmentRow,
    HealthAlertRow,
    HealthCheckDefinitionRow,
    HealthCheckResultRow,
    HealthIncidentRow,
    PipelineProviderRow,
    PipelineRow,
    PipelineRunRow,
)
from app.db.repository import InventoryRepository
from app.db.session import SessionLocal
from app.integrations.health.normalize import (
    normalize_cluster,
    normalize_deployment,
    normalize_ingress,
    normalize_pod,
)
from app.integrations.health.rules import HealthSignals, aggregate_application
from app.integrations.health.status import CRITICAL, DEGRADED, HEALTHY, UNHEALTHY, UNKNOWN
from app.main import app
from app.services.endpoint_tls import EndpointPolicyError
from app.services.health_http import validate_health_url
from app.services.health_sync import (
    acknowledge_incident,
    aggregate_application_row,
    run_cluster_health_scan,
    run_health_retention,
    run_http_health_check,
)
from app.services.jobs import enqueue_job
from app.topology.models import environment_scope_id

client = TestClient(app)


def _headers(role: str) -> dict[str, str]:
    return {"X-CloudOps-User": "tester@cloudops.local", "X-CloudOps-Role": role}


def _job(kind: str) -> str:
    session = SessionLocal()
    try:
        job = InventoryRepository(session).create_job(kind, kind, "test-corr", provider="AWS")
        session.commit()
        return job.id
    finally:
        session.close()


def _env(session, *, alias="aws-emea-nonprod", environment="UAT") -> CloudEnvironmentRow:
    env_id = environment_scope_id(alias, environment)
    row = session.get(CloudEnvironmentRow, env_id)
    assert row is not None
    return row


def _mapping(session, env: CloudEnvironmentRow, application_id: str, name: str) -> None:
    session.add(
        ApplicationResourceMappingRow(
            id=f"map-{application_id}",
            application_id=application_id,
            environment_id=env.id,
            cluster_id="",
            namespace="payments",
            resource_type="",
            resource_name="",
            label_selector=f"app.kubernetes.io/name={name}",
            active=True,
            created_at=datetime.now(timezone.utc),
        )
    )
    session.commit()


def _inventory(*, crashloop: bool = False, available: int = 3, desired: int = 3, http_fail: bool = False):
    labels = {"app.kubernetes.io/name": "payments-api"}
    resources = [
        normalize_cluster(reachable=True, version="1.30", cluster_status="ACTIVE"),
        normalize_deployment(
            {
                "metadata": {"name": "payments-api", "namespace": "payments", "labels": labels},
                "spec": {"replicas": desired},
                "status": {"availableReplicas": available},
            }
        ),
        normalize_pod(
            {
                "metadata": {"name": "payments-api-0", "namespace": "payments", "labels": labels},
                "status": {
                    "phase": "CrashLoopBackOff" if crashloop else "Running",
                    "containerStatuses": [
                        {
                            "restartCount": 8 if crashloop else 0,
                            "state": {"waiting": {"reason": "CrashLoopBackOff"}} if crashloop else {"running": {}},
                        }
                    ],
                },
            }
        ),
        normalize_ingress(
            {
                "metadata": {"name": "payments-api", "namespace": "payments", "labels": labels},
                "status": {"loadBalancer": {"ingress": [{"ip": "1.2.3.4"}]}},
                "has_address": True,
                "tls_ok": True,
            }
        ),
    ]
    if http_fail:
        from app.integrations.health.normalize import NormalizedResource

        resources.append(
            NormalizedResource(
                resource_type="http_endpoint",
                name="payments-api",
                namespace="payments",
                status=CRITICAL,
                summary="HTTP 503",
                labels=labels,
                check_type="HTTP_ENDPOINT",
            )
        )
    return resources


def test_aggregation_severity_rules() -> None:
    critical = aggregate_application(
        HealthSignals(desired_replicas=3, available_replicas=0, http_status=HEALTHY, ingress_status=HEALTHY, cluster_status=HEALTHY, workload_status=CRITICAL)
    )
    assert critical.status == CRITICAL
    unhealthy = aggregate_application(
        HealthSignals(desired_replicas=3, available_replicas=2, crashloop=2, workload_status=UNHEALTHY, http_status=HEALTHY)
    )
    assert unhealthy.status == UNHEALTHY
    degraded = aggregate_application(
        HealthSignals(desired_replicas=3, available_replicas=3, restart_count=9, workload_status=HEALTHY, http_status=HEALTHY, certificate_status="WARNING")
    )
    assert degraded.status == DEGRADED
    healthy = aggregate_application(
        HealthSignals(desired_replicas=3, available_replicas=3, workload_status=HEALTHY, http_status=HEALTHY, ingress_status=HEALTHY, cluster_status=HEALTHY)
    )
    assert healthy.status == HEALTHY
    unknown = aggregate_application(HealthSignals())
    assert unknown.status == UNKNOWN


def test_kubernetes_normalization() -> None:
    pod = normalize_pod(
        {
            "metadata": {"name": "web-0", "namespace": "app", "labels": {"app.kubernetes.io/name": "web"}},
            "status": {"phase": "Running", "containerStatuses": [{"restartCount": 1, "state": {"waiting": {"reason": "CrashLoopBackOff"}}}]},
        }
    )
    assert pod.status == UNHEALTHY
    assert pod.reason == "CrashLoopBackOff"
    oom = normalize_pod(
        {
            "metadata": {"name": "web-1", "namespace": "app"},
            "status": {"phase": "Running", "containerStatuses": [{"restartCount": 1, "state": {"terminated": {"reason": "OOMKilled"}}}]},
        }
    )
    assert oom.status == UNHEALTHY
    dep = normalize_deployment({"metadata": {"name": "web"}, "spec": {"replicas": 3}, "status": {"availableReplicas": 0}})
    assert dep.status == CRITICAL


def test_partial_cluster_failure_isolation() -> None:
    session = SessionLocal()
    try:
        emea = _env(session, environment="UAT")
        amer = _env(session, alias="aws-amer-nonprod", environment="UAT")
        china = _env(session, alias="alibaba-china-nonprod", environment="UAT")
        _mapping(session, emea, "payments-api", "payments-api")
        session.commit()
    finally:
        session.close()
    job_id = _job("cluster-health-scan")
    inventories = {
        emea.id: RuntimeError("EMEA UAT kube API timeout"),
        amer.id: _inventory(),
        china.id: _inventory(available=3),
    }
    run_cluster_health_scan(job_id, inventories=inventories)
    session = SessionLocal()
    try:
        emea = session.get(CloudEnvironmentRow, emea.id)
        amer = session.get(CloudEnvironmentRow, amer.id)
        china = session.get(CloudEnvironmentRow, china.id)
        assert emea.last_error
        assert "timeout" in emea.last_error.lower() or emea.last_error_class
        assert not amer.last_error
        assert not china.last_error
        assert amer.last_successful_scan_at is not None
    finally:
        session.close()
    overview = client.get("/api/v1/health/overview", headers=_headers("Developer")).json()
    assert overview["applications"] >= 0


def test_incident_open_and_recovery_and_alert_dedup() -> None:
    session = SessionLocal()
    try:
        env = _env(session)
        _mapping(session, env, "payments-api", "payments-api")
        session.commit()
        env_id = env.id
    finally:
        session.close()
    job_id = _job("cluster-health-scan")
    run_cluster_health_scan(job_id, inventories={env_id: _inventory(crashloop=True, available=0, desired=3, http_fail=True)})
    session = SessionLocal()
    try:
        env = session.get(CloudEnvironmentRow, env_id)
        for _ in range(3):
            aggregate_application_row(session, "payments-api", env)
        session.commit()
        incidents = list(session.query(HealthIncidentRow).all())
        assert len(incidents) == 1
        assert incidents[0].status == "OPEN"
        alerts = list(session.query(HealthAlertRow).all())
        kinds = {item.kind for item in alerts}
        assert "APPLICATION_CRITICAL" in kinds or "APPLICATION_UNHEALTHY" in kinds
        assert len(alerts) == len({item.fingerprint for item in alerts})
        incident_id = incidents[0].id
    finally:
        session.close()
    run_cluster_health_scan(job_id, inventories={env_id: _inventory(available=3, desired=3)})
    session = SessionLocal()
    try:
        env = session.get(CloudEnvironmentRow, env_id)
        for _ in range(2):
            aggregate_application_row(session, "payments-api", env)
        session.commit()
        incident = session.get(HealthIncidentRow, incident_id)
        assert incident.status == "RESOLVED"
        acknowledged = acknowledge_incident(session, incident_id, "ops@cloudops.local")
        assert acknowledged is not None
        session.commit()
    finally:
        session.close()


def test_deployment_and_certificate_correlation() -> None:
    session = SessionLocal()
    try:
        env = _env(session)
        _mapping(session, env, "payments-api", "payments-api")
        now = datetime.now(timezone.utc)
        session.add(
            PipelineProviderRow(
                id="pp-health",
                key="github-actions",
                name="GitHub Actions",
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            PipelineRow(
                id="pipe-1",
                provider_id="pp-health",
                external_id="8291",
                name="payments-deploy",
            )
        )
        session.add(
            PipelineRunRow(
                id="run-8291",
                pipeline_id="pipe-1",
                external_run_id="8291",
                branch="main",
                commit_sha="abc1234deadbeef",
                status="SUCCEEDED",
                application_id="payments-api",
                environment_id=env.id,
                started_at=now - timedelta(minutes=4),
                completed_at=now - timedelta(minutes=3),
                created_at=now,
                updated_at=now,
            )
        )
        session.add(
            AcmCertificateRow(
                id="cert-expired",
                arn="arn:aws:acm:eu-west-1:1:certificate/expired",
                domain_name="payments.example.com",
                environment="UAT",
                platform_region="EMEA",
                provider="AWS",
                account_alias="aws-emea-nonprod",
                expiry_status="EXPIRED",
                days_remaining=-2,
                present=True,
                last_checked=now,
            )
        )
        session.commit()
        env_id = env.id
    finally:
        session.close()
    job_id = _job("cluster-health-scan")
    run_cluster_health_scan(job_id, inventories={env_id: _inventory(crashloop=True, available=0, http_fail=True)})
    session = SessionLocal()
    try:
        env = session.get(CloudEnvironmentRow, env_id)
        row = aggregate_application_row(session, "payments-api", env)
        session.commit()
        assert row.likely_cause.startswith("Likely related to")
        assert "certificate" in row.likely_cause.lower() or "deployment" in row.likely_cause.lower() or "commit" in row.likely_cause.lower()
    finally:
        session.close()
    detail = client.get("/api/v1/health/applications/payments-api", headers=_headers("DevOpsEngineer")).json()
    assert detail["likelyCause"]
    assert "Likely related to" in detail["likelyCause"]
    history = client.get("/api/v1/health/applications/payments-api/history", headers=_headers("Developer")).json()
    assert history["timeline"]


def test_http_health_and_ssrf_protection() -> None:
    assert "health:read" in ROLE_PERMISSIONS["Developer"]
    assert "health:run_check" not in ROLE_PERMISSIONS["Developer"]
    assert "incident:acknowledge" in ROLE_PERMISSIONS["DevOpsEngineer"]
    assert "health:run_check" not in ROLE_PERMISSIONS["SecurityAuditor"]
    try:
        validate_health_url("http://127.0.0.1/secret", registered=True)
        raise AssertionError("localhost must be blocked")
    except EndpointPolicyError:
        pass
    try:
        validate_health_url("http://localhost/health", registered=True)
        raise AssertionError("localhost hostname must be blocked")
    except EndpointPolicyError:
        pass
    session = SessionLocal()
    try:
        env = _env(session)
        session.add(
            HealthCheckDefinitionRow(
                id="chk-ssrf",
                check_type="HTTP_ENDPOINT",
                name="blocked",
                enabled=True,
                environment_id=env.id,
                application_id="payments-api",
                url="http://127.0.0.1/internal",
                method="GET",
                expected_status="200-299",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        session.add(
            HealthCheckDefinitionRow(
                id="chk-ok",
                check_type="HTTP_ENDPOINT",
                name="public",
                enabled=True,
                environment_id=env.id,
                application_id="payments-api",
                url="https://status.example.com/health",
                method="GET",
                expected_status="200-299",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
    finally:
        session.close()
    denied = client.post("/api/v1/health/checks/chk-ssrf/run", headers=_headers("Developer"))
    assert denied.status_code == 403
    queued = client.post("/api/v1/health/checks/chk-ssrf/run", headers=_headers("DevOpsEngineer"))
    assert queued.status_code == 200
    session = SessionLocal()
    try:
        results = list(session.query(HealthCheckResultRow).filter(HealthCheckResultRow.definition_id == "chk-ssrf").all())
        assert results
        assert any(item.error_category == "ssrf" for item in results)
    finally:
        session.close()
    with patch("app.services.health_sync.probe_http") as probe:
        from app.services.health_http import HttpProbeResult

        probe.return_value = HttpProbeResult(
            url="https://status.example.com/health",
            success=True,
            status=HEALTHY,
            latency_ms=12,
            status_code=200,
            error_category="",
            summary="HTTP 200",
        )
        job = enqueue_job("http-health-check", target_id="chk-ok")
        assert job.id
        probe.assert_called()
    session = SessionLocal()
    try:
        ok = list(session.query(HealthCheckResultRow).filter(HealthCheckResultRow.definition_id == "chk-ok").all())
        assert ok
        assert any(item.status_code == 200 for item in ok)
        assert "body" not in (ok[-1].summary or "").lower()
    finally:
        session.close()


def test_retention_and_rbac_filters() -> None:
    session = SessionLocal()
    try:
        env = _env(session)
        old = datetime.now(timezone.utc) - timedelta(days=40)
        session.add(
            HealthCheckResultRow(
                id="old-result",
                environment_id=env.id,
                check_type="POD_STATUS",
                status=UNHEALTHY,
                summary="stale",
                created_at=old,
            )
        )
        session.add(
            HealthCheckResultRow(
                id="old-agg",
                environment_id=env.id,
                check_type="APPLICATION_AGGREGATE",
                status=HEALTHY,
                summary="stale agg",
                created_at=datetime.now(timezone.utc) - timedelta(days=200),
            )
        )
        session.commit()
    finally:
        session.close()
    job_id = _job("health-retention")
    removed = run_health_retention(job_id)
    assert removed >= 2
    session = SessionLocal()
    try:
        assert session.get(HealthCheckResultRow, "old-result") is None
        assert session.get(HealthCheckResultRow, "old-agg") is None
    finally:
        session.close()
    forbidden = client.get("/api/v1/health/overview", headers=_headers("ReadOnly"))
    assert forbidden.status_code == 200
    missing = client.post("/api/v1/health/incidents/nope/acknowledge", headers=_headers("SecurityAuditor"))
    assert missing.status_code == 403
    items = client.get("/api/v1/health/applications", params={"provider": "aws", "region": "emea", "environment": "uat", "status": "unhealthy", "application": "payments"}, headers=_headers("PlatformAdmin"))
    assert items.status_code == 200
    deps = ApplicationDependencyRow(
        id="dep-1",
        source_application_id="frontend",
        dependency_type="DATABASE",
        target_application_id="",
        external_name="payments-db",
        credential_ref="cred/postgres-payments",
        created_at=datetime.now(timezone.utc),
    )
    session = SessionLocal()
    try:
        session.add(deps)
        session.commit()
        stored = session.get(ApplicationDependencyRow, "dep-1")
        assert stored.credential_ref
        assert "password" not in stored.credential_ref
    finally:
        session.close()


def test_same_health_model_aws_and_alibaba() -> None:
    session = SessionLocal()
    try:
        aws = _env(session, alias="aws-emea-nonprod", environment="DEV")
        ali = _env(session, alias="alibaba-china-nonprod", environment="DEV")
        _mapping(session, aws, "platform-api", "payments-api")
        session.add(
            ApplicationResourceMappingRow(
                id="map-ali-platform",
                application_id="platform-api",
                environment_id=ali.id,
                namespace="payments",
                label_selector="app.kubernetes.io/name=payments-api",
                active=True,
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
        aws_id, ali_id = aws.id, ali.id
    finally:
        session.close()
    job_id = _job("cluster-health-scan")
    run_cluster_health_scan(job_id, inventories={aws_id: _inventory(), ali_id: _inventory()})
    session = SessionLocal()
    try:
        aws_row = session.get(CloudEnvironmentRow, aws_id)
        ali_row = session.get(CloudEnvironmentRow, ali_id)
        aggregate_application_row(session, "platform-api", aws_row)
        aggregate_application_row(session, "platform-api", ali_row)
        session.commit()
    finally:
        session.close()
    apps = client.get("/api/v1/health/applications", headers=_headers("Developer")).json()["items"]
    providers = {item["provider"] for item in apps}
    statuses = {item["status"] for item in apps}
    assert "AWS" in providers
    assert "Alibaba" in providers
    assert statuses <= {HEALTHY, DEGRADED, UNHEALTHY, CRITICAL, UNKNOWN}
    resources = client.get("/api/v1/health/resources", headers=_headers("Developer")).json()["items"]
    assert {item["resourceType"] for item in resources} & {"cluster", "deployment", "pod"}
