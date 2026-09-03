from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.alerts import router as alerts_router
from app.api.v1.clusters import router as clusters_router
from app.api.v1.credentials import router as credentials_router
from app.api.v1.certificates import router as certificates_router
from app.api.v1.health import router as health_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.pipelines import router as pipelines_router
from app.api.v1.platform import router as platform_router
from app.api.v1.scm import router as scm_router
from app.api.v1.storage import router as storage_router
from app.api.v1.listing import add_list_route, listed
from app.api.v1.params import parse_environment, parse_provider, parse_region, parse_scope
from app.core.config import settings
from app.core.security import assert_no_secret_values, walk_strings
from app.domain.models import Scope
from app.services.catalog import catalog_service, dashboard_snapshot

router = APIRouter()
router.include_router(platform_router)


add_list_route(router, "/regions", catalog_service.regions)
add_list_route(router, "/clusters", catalog_service.clusters)
router.include_router(certificates_router)
add_list_route(router, "/secrets", catalog_service.secrets)
add_list_route(router, "/health-checks", catalog_service.health_checks)
add_list_route(router, "/deployments", catalog_service.deployments)
router.include_router(pipelines_router)
router.include_router(health_router)
add_list_route(router, "/jobs", catalog_service.jobs)
add_list_route(router, "/github-runs", catalog_service.github_runs)
router.include_router(alerts_router)
add_list_route(router, "/audit-events", catalog_service.audit_events)

router.include_router(clusters_router)
router.include_router(jobs_router)
router.include_router(credentials_router)
router.include_router(scm_router)
router.include_router(storage_router)


@router.get("/environments/{provider}/{region}/{environment}")
def get_environment(provider: str, region: str, environment: str) -> dict:
    parsed_provider = parse_provider(provider)
    parsed_region = parse_region(region)
    parsed_environment = parse_environment(environment)
    if not parsed_provider or not parsed_region or not parsed_environment:
        raise HTTPException(status_code=404, detail="Environment not found")
    record = catalog_service.environment_detail(parsed_provider, parsed_region, parsed_environment)
    if record is None:
        raise HTTPException(status_code=404, detail="Environment not found")
    payload = record.model_dump()
    payload["lastSynced"] = settings.last_synced
    assert_no_secret_values(walk_strings(payload))
    return payload


@router.get("/secrets/{secret_id}")
def get_secret(secret_id: str) -> dict:
    match = next((item for item in catalog_service.secrets(Scope()) if item.id == secret_id), None)
    if match is None:
        raise HTTPException(status_code=404, detail="Secret metadata not found")
    payload = match.model_dump()
    payload["lastSynced"] = settings.last_synced
    assert_no_secret_values(walk_strings(payload))
    return payload


@router.get("/dashboard")
def get_dashboard(scope: Scope = Depends(parse_scope)) -> dict:
    payload = dashboard_snapshot(scope, settings.last_synced).model_dump()
    assert_no_secret_values(walk_strings(payload))
    return payload


@router.get("/admin/users")
def list_admin_users() -> dict:
    return listed(catalog_service.admin_users())
