from fastapi.testclient import TestClient

from app.core.security import contains_secret_value, walk_strings
from app.main import app

client = TestClient(app)

CATALOG_PATHS = [
    "/api/v1/providers",
    "/api/v1/regions",
    "/api/v1/accounts",
    "/api/v1/environments",
    "/api/v1/clusters",
    "/api/v1/applications",
    "/api/v1/certificates",
    "/api/v1/secrets",
    "/api/v1/health-checks",
    "/api/v1/deployments",
    "/api/v1/pipelines",
    "/api/v1/jobs",
    "/api/v1/github-runs",
    "/api/v1/alerts",
    "/api/v1/audit-events",
    "/api/v1/admin/users",
    "/api/v1/admin/integrations",
    "/api/v1/dashboard",
]


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_catalog_endpoints_return_items() -> None:
    for path in CATALOG_PATHS:
        response = client.get(path)
        assert response.status_code == 200, path
        body = response.json()
        if path.endswith("/dashboard"):
            assert body["kpis"]["clustersUnreachable"] == 1
            assert body["kpis"]["openAlerts"] == 4
            assert len(body["matrix"]) == 4
            assert len(body["alerts"]) == 4
            assert len(body["failures"]) == 3
        else:
            assert "items" in body, path
            if path.endswith("/alerts"):
                continue
            assert len(body["items"]) > 0, path


def test_provider_filter_keeps_alibaba_china() -> None:
    response = client.get("/api/v1/clusters", params={"provider": "alibaba"})
    body = response.json()["items"]
    assert body
    assert {f"{item['provider']} {item['region']}" for item in body} == {"Alibaba China"}


def test_environment_filter_int_tst_slug() -> None:
    response = client.get("/api/v1/clusters", params={"environment": "int-tst"})
    items = response.json()["items"]
    assert items
    assert all(item["environment"] == "INT/TST" for item in items)


def test_known_exceptions() -> None:
    clusters = client.get("/api/v1/clusters").json()["items"]
    assert any(item["name"] == "eu-west-1-uat-k8s" and item["status"] == "Unreachable" for item in clusters)
    apps = client.get("/api/v1/applications").json()["items"]
    assert any(item["name"] == "payment-svc" and item["environment"] == "PRD" for item in apps)
    certs = client.get("/api/v1/certificates").json()["items"]
    featured = next(item for item in certs if item["id"] == "cert-amer-prd-wildcard")
    assert featured["daysRemaining"] == 12
    secrets = client.get("/api/v1/secrets").json()["items"]
    assert all("value" not in item for item in secrets)
    assert any(item["status"] == "Overdue" for item in secrets)


def test_environment_detail_emea_uat() -> None:
    response = client.get("/api/v1/environments/aws/emea/uat")
    assert response.status_code == 200
    body = response.json()
    assert body["identity"]["account"] == "aws-emea-nonprod"
    assert body["clusters"][0]["status"] == "Unreachable"
    assert len(body["applications"]) == 4
    assert body["identity"]["certificateTotal"] >= 1
    assert body["identity"]["certificateStatus"] in {"Healthy", "Warning", "Critical"}
    assert len(body["certificates"]) == body["identity"]["certificateTotal"]


def test_dashboard_prd_filter() -> None:
    response = client.get("/api/v1/dashboard", params={"environment": "prd"})
    body = response.json()
    assert body["kpis"]["certsExpiring14d"] == 1
    assert body["alerts"][0]["environment"] == "PRD"
    assert body["failures"][0]["name"] == "payment-svc"


def test_no_secret_values_in_any_payload() -> None:
    for path in CATALOG_PATHS + ["/api/v1/environments/aws/amer/prd", "/api/v1/secrets/sec-amer-prd-app"]:
        body = client.get(path).json()
        for value in walk_strings(body):
            assert contains_secret_value(value) is False, f"{path}: {value}"
