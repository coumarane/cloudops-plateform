import inspect

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.providers.aws import eks as eks_module
from app.providers.aws.errors import AwsAuthError
from app.topology.loader import load_topology
from tests.test_aws_phase3 import _cluster, _discovery_for_config

client = TestClient(app)


def test_topology_covers_all_aws_accounts_without_adapter_hardcoding() -> None:
    topology = load_topology()
    aliases = {account.alias for account in topology.accounts}
    assert aliases == {
        "aws-amer-nonprod",
        "aws-amer-prod",
        "aws-emea-nonprod",
        "aws-emea-prod",
        "aws-apac-nonprod",
        "aws-apac-prod",
    }
    prod = topology.account_by_alias("aws-emea-prod")
    assert prod is not None
    assert prod.readonly is True
    assert prod.environments == ("NPD", "PRD")
    source = inspect.getsource(eks_module)
    assert "AMER" not in source
    assert "EMEA" not in source
    assert "APAC" not in source


def test_prd_environments_are_readonly() -> None:
    payload = client.get("/api/v1/environments/aws/emea/prd").json()
    assert payload["identity"]["readonly"] is True
    assert payload["identity"]["account"] == "aws-emea-prod"
    dev = client.get("/api/v1/environments/aws/emea/dev").json()
    assert dev["identity"]["readonly"] is False
    assert dev["identity"]["account"] == "aws-emea-nonprod"


def test_partial_account_failure_does_not_stop_other_accounts() -> None:
    def discovery(factory, config):
        mock = MagicMock()
        if config.account_alias == "aws-amer-nonprod":
            mock.list_clusters.side_effect = AwsAuthError("amer nonprod unavailable")
        elif config.account_alias == "aws-emea-nonprod":
            mock.list_clusters.return_value = [_cluster()]
        else:
            mock.list_clusters.return_value = []
        return mock

    with patch("app.services.aws_sync.EksDiscovery", side_effect=discovery):
        response = client.post("/api/v1/jobs/aws/cluster-discovery")
    assert response.status_code == 200
    body = response.json()
    assert body["result"] == "Succeeded"
    assert "aws-amer-nonprod" in body["detail"]

    emea = client.get("/api/v1/environments/aws/emea/dev").json()
    assert emea["identity"]["discoveryActive"] is True
    assert emea["clusters"][0]["name"] == "platform-dev"

    amer = client.get("/api/v1/environments/aws/amer/dev").json()
    assert amer["identity"]["discoveryActive"] is False
    assert amer["identity"]["lastError"]
    assert "amer nonprod unavailable" in amer["identity"]["lastError"]
    assert any(item["name"] == "us-east-1-dev-k8s" for item in amer["clusters"])

    dashboard = client.get("/api/v1/dashboard").json()
    emea_row = next(row for row in dashboard["matrix"] if row["provider"] == "AWS" and row["region"] == "EMEA")
    assert emea_row["cells"]["DEV"]["live"] is True
    amer_row = next(row for row in dashboard["matrix"] if row["provider"] == "AWS" and row["region"] == "AMER")
    assert amer_row["cells"]["DEV"]["live"] is not True
    assert amer_row["cells"]["DEV"]["lastError"]


def test_replace_clusters_is_scoped_to_environment() -> None:
    with patch("app.services.aws_sync.EksDiscovery", side_effect=_discovery_for_config):
        client.post("/api/v1/jobs/aws/cluster-discovery")
    alibaba = client.get("/api/v1/clusters", params={"provider": "alibaba"}).json()["items"]
    assert alibaba
    assert all(item.get("source") != "aws" for item in alibaba)
    emea_dev = client.get("/api/v1/clusters", params={"provider": "aws", "region": "emea", "environment": "dev"}).json()["items"]
    assert {item["name"] for item in emea_dev} == {"platform-dev"}


def test_scan_concurrency_is_bounded() -> None:
    seen: list[int] = []
    from concurrent.futures import ThreadPoolExecutor as RealExecutor

    def factory(*args, **kwargs):
        workers = kwargs.get("max_workers", args[0] if args else None)
        seen.append(int(workers))
        return RealExecutor(*args, **kwargs)

    with patch("app.services.aws_sync.EksDiscovery", side_effect=_discovery_for_config):
        with patch("app.services.aws_sync.ThreadPoolExecutor", side_effect=factory):
            client.post("/api/v1/jobs/aws/cluster-discovery")
    assert seen
    assert max(seen) <= load_topology().scan_concurrency
