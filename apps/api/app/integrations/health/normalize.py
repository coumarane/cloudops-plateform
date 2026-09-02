from __future__ import annotations

from dataclasses import dataclass, field

from app.integrations.health.status import CRITICAL, DEGRADED, HEALTHY, UNHEALTHY, UNKNOWN, worst


@dataclass
class NormalizedResource:
    resource_type: str
    name: str
    namespace: str = ""
    status: str = UNKNOWN
    summary: str = ""
    desired: int = 0
    ready: int = 0
    available: int = 0
    unavailable: int = 0
    restart_count: int = 0
    reason: str = ""
    labels: dict[str, str] = field(default_factory=dict)
    error_category: str = ""
    check_type: str = ""


def _labels(item) -> dict[str, str]:
    meta = getattr(item, "metadata", None)
    labels = getattr(meta, "labels", None) if meta is not None else None
    if isinstance(item, dict):
        labels = (item.get("metadata") or {}).get("labels") or item.get("labels")
    return {str(key): str(value) for key, value in (labels or {}).items()}


def _name(item) -> str:
    meta = getattr(item, "metadata", None)
    if meta is not None:
        return getattr(meta, "name", "") or ""
    if isinstance(item, dict):
        return str((item.get("metadata") or {}).get("name") or item.get("name") or "")
    return getattr(item, "name", "") or ""


def _namespace(item) -> str:
    meta = getattr(item, "metadata", None)
    if meta is not None:
        return getattr(meta, "namespace", "") or ""
    if isinstance(item, dict):
        return str((item.get("metadata") or {}).get("namespace") or item.get("namespace") or "")
    return getattr(item, "namespace", "") or ""


def normalize_cluster(*, reachable: bool, version: str = "", cluster_status: str = "", detail: str = "") -> NormalizedResource:
    if not reachable:
        return NormalizedResource(
            resource_type="cluster",
            name="api",
            status=CRITICAL,
            summary=detail or "Kubernetes API unreachable",
            reason="api_unreachable",
            error_category="connectivity",
            check_type="KUBERNETES_API",
        )
    return NormalizedResource(
        resource_type="cluster",
        name="api",
        status=HEALTHY,
        summary=f"API reachable {version} {cluster_status}".strip(),
        check_type="KUBERNETES_API",
    )


def normalize_node(item) -> NormalizedResource:
    name = _name(item)
    status_obj = getattr(item, "status", None)
    conditions = getattr(status_obj, "conditions", None) if status_obj is not None else None
    if isinstance(item, dict):
        conditions = ((item.get("status") or {}).get("conditions")) or []
    ready = False
    pressure: list[str] = []
    for condition in conditions or []:
        cond_type = getattr(condition, "type", None) or (condition.get("type") if isinstance(condition, dict) else "")
        cond_status = getattr(condition, "status", None) or (condition.get("status") if isinstance(condition, dict) else "")
        if cond_type == "Ready" and str(cond_status) == "True":
            ready = True
        if cond_type in {"MemoryPressure", "DiskPressure", "PIDPressure"} and str(cond_status) == "True":
            pressure.append(str(cond_type))
    if not ready:
        status = UNHEALTHY
        reason = "NotReady"
    elif pressure:
        status = DEGRADED
        reason = ",".join(pressure)
    else:
        status = HEALTHY
        reason = "Ready"
    return NormalizedResource(
        resource_type="node",
        name=name,
        status=status,
        summary=reason,
        ready=1 if ready else 0,
        desired=1,
        reason=reason,
        labels=_labels(item),
        check_type="NODE_READY",
        error_category="node" if status != HEALTHY else "",
    )


def _pod_waiting_reason(item) -> str:
    status_obj = getattr(item, "status", None)
    container_statuses = getattr(status_obj, "container_statuses", None) if status_obj is not None else None
    if isinstance(item, dict):
        container_statuses = ((item.get("status") or {}).get("containerStatuses") or item.get("container_statuses") or [])
    for container in container_statuses or []:
        state = getattr(container, "state", None)
        waiting = getattr(state, "waiting", None) if state is not None else None
        terminated = getattr(state, "terminated", None) if state is not None else None
        last = getattr(container, "last_state", None) or getattr(container, "last_termination_state", None)
        last_terminated = getattr(last, "terminated", None) if last is not None else None
        if isinstance(container, dict):
            waiting = ((container.get("state") or {}).get("waiting")) or {}
            terminated = ((container.get("state") or {}).get("terminated")) or {}
            last_terminated = ((container.get("lastState") or {}).get("terminated")) or {}
            reason = waiting.get("reason") or terminated.get("reason") or last_terminated.get("reason") or ""
        else:
            reason = (
                getattr(waiting, "reason", "")
                or getattr(terminated, "reason", "")
                or getattr(last_terminated, "reason", "")
                or ""
            )
        if reason:
            return str(reason)
    return ""


def _restart_count(item) -> int:
    status_obj = getattr(item, "status", None)
    container_statuses = getattr(status_obj, "container_statuses", None) if status_obj is not None else None
    if isinstance(item, dict):
        container_statuses = ((item.get("status") or {}).get("containerStatuses") or [])
    total = 0
    for container in container_statuses or []:
        if isinstance(container, dict):
            total += int(container.get("restartCount") or 0)
        else:
            total += int(getattr(container, "restart_count", 0) or 0)
    return total


def normalize_pod(item, *, restart_degraded_threshold: int = 5) -> NormalizedResource:
    phase = ""
    status_obj = getattr(item, "status", None)
    if status_obj is not None:
        phase = (getattr(status_obj, "phase", "") or "").lower()
    if isinstance(item, dict):
        phase = str((item.get("status") or {}).get("phase") or item.get("phase") or "").lower()
    reason = _pod_waiting_reason(item)
    restarts = _restart_count(item)
    status = HEALTHY
    error = ""
    if reason in {"CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull"}:
        status = UNHEALTHY
        error = "pod"
    elif reason == "OOMKilled":
        status = UNHEALTHY
        error = "memory"
    elif phase == "failed":
        status = UNHEALTHY
        error = "pod"
        reason = reason or "Failed"
    elif phase == "pending":
        status = DEGRADED
        error = "scheduling"
        reason = reason or "Pending"
    elif phase == "unknown":
        status = UNKNOWN
        error = "unknown"
    elif restarts >= restart_degraded_threshold:
        status = DEGRADED
        error = "restarts"
        reason = reason or "ExcessiveRestarts"
    elif phase in {"running", "succeeded", ""}:
        status = HEALTHY
    else:
        status = DEGRADED
    return NormalizedResource(
        resource_type="pod",
        name=_name(item),
        namespace=_namespace(item),
        status=status,
        summary=f"{phase or 'running'} {reason}".strip(),
        restart_count=restarts,
        reason=reason or phase,
        labels=_labels(item),
        error_category=error,
        check_type="POD_STATUS",
        ready=1 if status == HEALTHY else 0,
        desired=1,
    )


def normalize_deployment(item) -> NormalizedResource:
    spec = getattr(item, "spec", None)
    status_obj = getattr(item, "status", None)
    desired = int(getattr(spec, "replicas", 0) or 0) if spec is not None else 0
    available = int(getattr(status_obj, "available_replicas", 0) or 0) if status_obj is not None else 0
    if isinstance(item, dict):
        desired = int((item.get("spec") or {}).get("replicas") or item.get("desired") or 0)
        available = int((item.get("status") or {}).get("availableReplicas") or item.get("available") or 0)
    unavailable = max(desired - available, 0)
    if desired > 0 and available == 0:
        status = CRITICAL
        reason = "Unavailable"
    elif unavailable:
        status = UNHEALTHY
        reason = "Partial"
    else:
        status = HEALTHY
        reason = "Available"
    return NormalizedResource(
        resource_type="deployment",
        name=_name(item),
        namespace=_namespace(item),
        status=status,
        summary=f"{available}/{desired} available",
        desired=desired,
        ready=available,
        available=available,
        unavailable=unavailable,
        reason=reason,
        labels=_labels(item),
        error_category="workload" if status != HEALTHY else "",
        check_type="DEPLOYMENT_AVAILABILITY",
    )


def normalize_statefulset(item) -> NormalizedResource:
    spec = getattr(item, "spec", None)
    status_obj = getattr(item, "status", None)
    desired = int(getattr(spec, "replicas", 0) or 0) if spec is not None else 0
    ready = int(getattr(status_obj, "ready_replicas", 0) or 0) if status_obj is not None else 0
    if isinstance(item, dict):
        desired = int((item.get("spec") or {}).get("replicas") or item.get("desired") or 0)
        ready = int((item.get("status") or {}).get("readyReplicas") or item.get("ready") or 0)
    unavailable = max(desired - ready, 0)
    if desired > 0 and ready == 0:
        status = CRITICAL
    elif unavailable:
        status = UNHEALTHY
    else:
        status = HEALTHY
    return NormalizedResource(
        resource_type="statefulset",
        name=_name(item),
        namespace=_namespace(item),
        status=status,
        summary=f"{ready}/{desired} ready",
        desired=desired,
        ready=ready,
        available=ready,
        unavailable=unavailable,
        labels=_labels(item),
        check_type="DEPLOYMENT_AVAILABILITY",
        error_category="workload" if status != HEALTHY else "",
    )


def normalize_daemonset(item) -> NormalizedResource:
    status_obj = getattr(item, "status", None)
    desired = int(getattr(status_obj, "desired_number_scheduled", 0) or 0) if status_obj is not None else 0
    available = int(getattr(status_obj, "number_available", 0) or 0) if status_obj is not None else 0
    if isinstance(item, dict):
        status_obj = item.get("status") or item
        desired = int(status_obj.get("desiredNumberScheduled") or item.get("desired") or 0)
        available = int(status_obj.get("numberAvailable") or item.get("available") or 0)
    unavailable = max(desired - available, 0)
    if desired > 0 and available == 0:
        status = CRITICAL
    elif unavailable:
        status = UNHEALTHY
    else:
        status = HEALTHY
    return NormalizedResource(
        resource_type="daemonset",
        name=_name(item),
        namespace=_namespace(item),
        status=status,
        summary=f"{available}/{desired} available",
        desired=desired,
        ready=available,
        available=available,
        unavailable=unavailable,
        labels=_labels(item),
        check_type="DEPLOYMENT_AVAILABILITY",
        error_category="workload" if status != HEALTHY else "",
    )


def normalize_job(item) -> NormalizedResource:
    status_obj = getattr(item, "status", None)
    failed = int(getattr(status_obj, "failed", 0) or 0) if status_obj is not None else 0
    succeeded = int(getattr(status_obj, "succeeded", 0) or 0) if status_obj is not None else 0
    active = int(getattr(status_obj, "active", 0) or 0) if status_obj is not None else 0
    if isinstance(item, dict):
        status_obj = item.get("status") or item
        failed = int(status_obj.get("failed") or 0)
        succeeded = int(status_obj.get("succeeded") or 0)
        active = int(status_obj.get("active") or 0)
    if failed:
        status = UNHEALTHY
        reason = "Failed"
    elif active:
        status = DEGRADED
        reason = "Running"
    else:
        status = HEALTHY
        reason = "Completed"
    return NormalizedResource(
        resource_type="job",
        name=_name(item),
        namespace=_namespace(item),
        status=status,
        summary=f"active={active} succeeded={succeeded} failed={failed}",
        desired=succeeded + failed + active,
        ready=succeeded,
        reason=reason,
        labels=_labels(item),
        check_type="POD_STATUS",
        error_category="job" if failed else "",
    )


def normalize_service(item, *, endpoint_ready: int = 0, endpoint_expected: int = 1) -> NormalizedResource:
    if endpoint_ready <= 0:
        status = UNHEALTHY
        reason = "NoEndpoints"
    else:
        status = HEALTHY
        reason = "EndpointsReady"
    return NormalizedResource(
        resource_type="service",
        name=_name(item),
        namespace=_namespace(item),
        status=status,
        summary=f"{endpoint_ready} endpoints",
        desired=endpoint_expected,
        ready=endpoint_ready,
        available=endpoint_ready,
        reason=reason,
        labels=_labels(item),
        check_type="SERVICE_ENDPOINT",
        error_category="endpoints" if status != HEALTHY else "",
    )


def normalize_ingress(item, *, has_address: bool = False, tls_ok: bool = True) -> NormalizedResource:
    if isinstance(item, dict) and "has_address" in item:
        has_address = bool(item.get("has_address"))
        tls_ok = bool(item.get("tls_ok", True))
    status_obj = getattr(item, "status", None)
    load_balancer = getattr(status_obj, "load_balancer", None) if status_obj is not None else None
    ingress = getattr(load_balancer, "ingress", None) if load_balancer is not None else None
    if ingress:
        has_address = True
    spec = getattr(item, "spec", None)
    tls = getattr(spec, "tls", None) if spec is not None else None
    if isinstance(item, dict):
        ingress = (((item.get("status") or {}).get("loadBalancer") or {}).get("ingress")) or []
        has_address = bool(ingress) or has_address
        tls = (item.get("spec") or {}).get("tls")
    if not has_address:
        status = UNHEALTHY
        reason = "NoAddress"
    elif tls and not tls_ok:
        status = UNHEALTHY
        reason = "TLS"
    else:
        status = HEALTHY
        reason = "Configured"
    return NormalizedResource(
        resource_type="ingress",
        name=_name(item),
        namespace=_namespace(item),
        status=status,
        summary=reason,
        reason=reason,
        labels=_labels(item),
        check_type="INGRESS_REACHABILITY",
        error_category="ingress" if status != HEALTHY else "",
        ready=1 if status == HEALTHY else 0,
        desired=1,
    )


def snapshot_from_resources(resources: list[NormalizedResource], *, cluster_arn: str, control_plane_status: str, detail: str = ""):
    from datetime import datetime, timezone

    from app.providers.common.models import ClusterHealthSnapshot

    nodes = [item for item in resources if item.resource_type == "node"]
    pods = [item for item in resources if item.resource_type == "pod"]
    deployments = [item for item in resources if item.resource_type == "deployment"]
    jobs = [item for item in resources if item.resource_type == "job"]
    stateful = [item for item in resources if item.resource_type == "statefulset"]
    ingresses = [item for item in resources if item.resource_type == "ingress"]
    api = next((item for item in resources if item.resource_type == "cluster"), None)
    reachable = api.status == HEALTHY if api else True
    return ClusterHealthSnapshot(
        cluster_arn=cluster_arn,
        control_plane_status=control_plane_status,
        kubernetes_api_reachable=reachable,
        node_count=len(nodes),
        ready_node_count=sum(1 for item in nodes if item.status == HEALTHY),
        pod_count=len(pods),
        unhealthy_pod_count=sum(1 for item in pods if item.status in {UNHEALTHY, CRITICAL}),
        crashloop_backoff_count=sum(1 for item in pods if item.reason == "CrashLoopBackOff"),
        pending_pod_count=sum(1 for item in pods if item.reason.lower() == "pending" or "pending" in item.summary.lower()),
        unavailable_deployment_count=sum(1 for item in deployments if item.unavailable),
        failed_job_count=sum(1 for item in jobs if item.status in {UNHEALTHY, CRITICAL}),
        stateful_set_unhealthy_count=sum(1 for item in stateful if item.status in {UNHEALTHY, CRITICAL, DEGRADED}),
        ingress_unhealthy_count=sum(1 for item in ingresses if item.status in {UNHEALTHY, CRITICAL}),
        last_checked=datetime.now(timezone.utc),
        detail=detail,
    )


def cluster_health_status(snapshot) -> str:
    if not snapshot.kubernetes_api_reachable:
        return CRITICAL
    if snapshot.crashloop_backoff_count or snapshot.unavailable_deployment_count or snapshot.failed_job_count:
        return UNHEALTHY
    if snapshot.pending_pod_count or snapshot.ready_node_count < snapshot.node_count or snapshot.unhealthy_pod_count:
        return DEGRADED
    return HEALTHY
