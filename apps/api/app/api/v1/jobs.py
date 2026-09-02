from fastapi import APIRouter, HTTPException

from app.core.security import assert_no_secret_values, walk_strings
from app.services.job_kinds import KIND_CERTIFICATES, KIND_DISCOVERY, KIND_HEALTH
from app.services.jobs import enqueue_job
from app.services.mappers import to_job_record

router = APIRouter()


def _queued(kind: str) -> dict:
    try:
        job = enqueue_job(kind)
    except KeyError:
        raise HTTPException(status_code=400, detail="Unknown job kind") from None
    payload = to_job_record(job).model_dump()
    payload["queued"] = True
    assert_no_secret_values(walk_strings(payload))
    return payload


@router.post("/jobs/aws/cluster-discovery")
def trigger_cluster_discovery() -> dict:
    return _queued(KIND_DISCOVERY)


@router.post("/jobs/aws/health-scan")
def trigger_health_scan() -> dict:
    return _queued(KIND_HEALTH)


@router.post("/jobs/aws/certificate-scan")
def trigger_certificate_scan() -> dict:
    return _queued(KIND_CERTIFICATES)
