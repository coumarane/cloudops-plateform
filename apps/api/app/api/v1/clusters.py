from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.security import assert_no_secret_values, walk_strings
from app.services.overlay import load_cluster_detail

router = APIRouter()


@router.get("/clusters/{cluster_id}")
def get_cluster(cluster_id: str) -> dict:
    cluster, health = load_cluster_detail(cluster_id)
    if cluster is None:
        from app.domain.models import Scope
        from app.services.catalog import catalog_service

        match = next((item for item in catalog_service.clusters(Scope()) if item.id == cluster_id), None)
        if match is None:
            raise HTTPException(status_code=404, detail="Cluster not found")
        payload = match.model_dump()
        payload["lastSynced"] = settings.last_synced
        assert_no_secret_values(walk_strings(payload))
        return payload
    payload = cluster.model_dump()
    payload["health"] = health.model_dump() if health else None
    payload["lastSynced"] = settings.last_synced
    assert_no_secret_values(walk_strings(payload))
    return payload


@router.get("/clusters/{cluster_id}/health")
def get_cluster_health(cluster_id: str) -> dict:
    cluster, health = load_cluster_detail(cluster_id)
    if cluster is None:
        raise HTTPException(status_code=404, detail="Cluster not found")
    if health is None:
        raise HTTPException(status_code=404, detail="Cluster health has not been collected")
    payload = health.model_dump()
    payload["lastSynced"] = settings.last_synced
    assert_no_secret_values(walk_strings(payload))
    return payload
