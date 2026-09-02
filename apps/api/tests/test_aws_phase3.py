from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.db.models import AcmCertificateRow, EksClusterHealthRow, EksClusterRow, LiveScopeStateRow, PlatformJobRow
from app.db.repository import InventoryRepository
from app.db.session import SessionLocal
from app.main import app
from app.providers.aws.errors import AwsAuthError, AwsPermissionError, classify_aws_error
from app.providers.aws.models import ClusterHealthSnapshot, DiscoveredCertificate, DiscoveredCluster
from botocore.exceptions import ClientError, NoCredentialsError

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_live_tables() -> None:
    session = SessionLocal()
    for model in (EksClusterHealthRow, EksClusterRow, AcmCertificateRow, PlatformJobRow, LiveScopeStateRow):
        session.query(model).delete()
    session.commit()
    session.close()



def _cluster(name: str = "platform-dev") -> DiscoveredCluster:
    return DiscoveredCluster(
        name=name,
        arn=f"arn:aws:eks:eu-west-1:123456789012:cluster/{name}",
        cloud_region="eu-west-1",
        aws_account_id="123456789012",
        kubernetes_version="1.31",
        endpoint_status="PRIVATE",
        cluster_status="ACTIVE",
        platform_version="eks.5",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        endpoint="https://eks.example.eu-west-1.amazonaws.com",
    )


def _health(arn: str) -> ClusterHealthSnapshot:
    return ClusterHealthSnapshot(
        cluster_arn=arn,
        control_plane_status="ACTIVE",
        kubernetes_api_reachable=True,
        node_count=4,
        ready_node_count=4,
        pod_count=18,
        unhealthy_pod_count=1,
        crashloop_backoff_count=0,
        pending_pod_count=0,
        unavailable_deployment_count=0,
        failed_job_count=0,
        last_checked=datetime.now(timezone.utc),
    )


def test_live_clusters_replace_aws_emea_dev_mock() -> None:
    with patch("app.services.aws_sync.EksDiscovery") as discovery:
        discovery.return_value.list_dev_clusters.return_value = [_cluster()]
        response = client.post("/api/v1/jobs/aws/cluster-discovery")
    assert response.status_code == 200
    clusters = client.get("/api/v1/clusters", params={"provider": "aws", "region": "emea", "environment": "dev"}).json()["items"]
    names = {item["name"] for item in clusters}
    assert "platform-dev" in names
    assert "eu-west-1-dev-k8s" not in names
    assert all(item["source"] == "aws" for item in clusters)
    detail = client.get("/api/v1/clusters/eks-eu-west-1-platform-dev")
    assert detail.status_code == 200
    assert detail.json()["version"] == "1.31"


def test_health_and_certificate_scan_endpoints() -> None:
    with patch("app.services.aws_sync.EksDiscovery") as discovery:
        discovery.return_value.list_dev_clusters.return_value = [_cluster()]
        discovery.return_value.describe_raw.return_value = {
            "endpoint": "https://eks.example.eu-west-1.amazonaws.com",
            "certificateAuthority": {"data": None},
        }
        client.post("/api/v1/jobs/aws/cluster-discovery")
        with patch("app.services.aws_sync.ClusterHealthCollector") as collector:
            collector.return_value.collect.return_value = _health(_cluster().arn)
            health_job = client.post("/api/v1/jobs/aws/health-scan")
    assert health_job.status_code == 200
    health = client.get("/api/v1/clusters/eks-eu-west-1-platform-dev/health")
    assert health.status_code == 200
    body = health.json()
    assert body["kubernetesApiReachable"] is True
    assert body["nodeCount"] == 4
    assert "token" not in body

    cert = DiscoveredCertificate(
        arn="arn:aws:acm:eu-west-1:123456789012:certificate/abcd",
        domain_name="dev.emea.example.com",
        subject_alternative_names=["dev.emea.example.com"],
        issuer="Amazon",
        status="ISSUED",
        not_before=datetime(2026, 1, 1, tzinfo=timezone.utc),
        not_after=datetime(2026, 12, 1, tzinfo=timezone.utc),
        days_remaining=90,
        in_use_by=["arn:aws:elasticloadbalancing:eu-west-1:123456789012:loadbalancer/app/dev"],
        renewal_eligibility="ELIGIBLE",
    )
    with patch("app.services.aws_sync.AcmScanner") as scanner:
        scanner.return_value.list_certificates.return_value = [cert]
        client.post("/api/v1/jobs/aws/certificate-scan")
    certs = client.get("/api/v1/certificates", params={"provider": "aws", "region": "emea", "environment": "dev"}).json()["items"]
    assert any(item["domain"] == "dev.emea.example.com" and item["source"] == "aws" for item in certs)
    assert all("pem" not in item for item in certs)


def test_jobs_are_idempotent_while_running() -> None:
    session = SessionLocal()
    repo = InventoryRepository(session)
    first = repo.create_job("aws-cluster-discovery", "discovery", "cid-1")
    first.status = "running"
    session.commit()
    session.close()
    response = client.post("/api/v1/jobs/aws/cluster-discovery")
    assert response.json()["id"] == first.id


def test_classify_auth_versus_permission() -> None:
    assert isinstance(classify_aws_error(NoCredentialsError()), AwsAuthError)
    permission = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "not allowed"}, "ResponseMetadata": {"HTTPStatusCode": 403}},
        "ListClusters",
    )
    assert isinstance(classify_aws_error(permission), AwsPermissionError)
    auth = ClientError(
        {"Error": {"Code": "ExpiredTokenException", "Message": "expired"}, "ResponseMetadata": {"HTTPStatusCode": 403}},
        "AssumeRole",
    )
    assert isinstance(classify_aws_error(auth), AwsAuthError)


def test_repository_never_stores_access_keys() -> None:
    session = SessionLocal()
    repo = InventoryRepository(session)
    repo.replace_clusters([_cluster()])
    session.commit()
    row = repo.get_cluster("eks-eu-west-1-platform-dev")
    payload = {column.name: getattr(row, column.name) for column in row.__table__.columns}
    session.close()
    assert "access_key" not in str(payload).lower()
    assert "secret" not in str(payload).lower()
    assert "session_token" not in str(payload).lower()


def test_discovery_without_credentials_returns_failed_job() -> None:
    with patch("app.services.aws_sync.EksDiscovery") as discovery:
        discovery.return_value.list_dev_clusters.side_effect = AwsAuthError("missing credentials")
        response = client.post("/api/v1/jobs/aws/cluster-discovery")
    assert response.status_code == 200
    body = response.json()
    assert body["result"] == "Failed"
    assert body["jobStatus"] == "failed"
    assert body["queued"] is True
    blob = str(body).lower()
    assert "akia" not in blob
    assert "aws_secret_access_key" not in blob
    assert "session_token" not in blob
    clusters = client.get("/api/v1/clusters", params={"provider": "aws", "region": "emea", "environment": "dev"}).json()["items"]
    assert any(item["name"] == "eu-west-1-dev-k8s" for item in clusters)
