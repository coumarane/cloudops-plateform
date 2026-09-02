from __future__ import annotations

HEALTHY = "HEALTHY"
DEGRADED = "DEGRADED"
UNHEALTHY = "UNHEALTHY"
CRITICAL = "CRITICAL"
UNKNOWN = "UNKNOWN"

STATUSES = (HEALTHY, DEGRADED, UNHEALTHY, CRITICAL, UNKNOWN)

RANK = {
    HEALTHY: 0,
    UNKNOWN: 1,
    DEGRADED: 2,
    UNHEALTHY: 3,
    CRITICAL: 4,
}

RESOURCE_TYPES = (
    "cloud_account",
    "environment",
    "cluster",
    "node",
    "namespace",
    "deployment",
    "statefulset",
    "daemonset",
    "pod",
    "service",
    "ingress",
    "application",
    "http_endpoint",
    "certificate",
    "pipeline",
    "deployment_event",
    "dependency",
    "job",
)

CHECK_TYPES = (
    "KUBERNETES_API",
    "NODE_READY",
    "DEPLOYMENT_AVAILABILITY",
    "POD_STATUS",
    "POD_RESTART_RATE",
    "SERVICE_ENDPOINT",
    "INGRESS_REACHABILITY",
    "HTTP_ENDPOINT",
    "TLS_CERTIFICATE",
    "DATABASE_CONNECTIVITY",
    "REDIS_CONNECTIVITY",
    "RABBITMQ_CONNECTIVITY",
    "DEPENDENCY_HTTP",
)

INCIDENT_OPEN = "OPEN"
INCIDENT_ACKNOWLEDGED = "ACKNOWLEDGED"
INCIDENT_RESOLVED = "RESOLVED"

APP_K8S_NAME = "app.kubernetes.io/name"
APP_K8S_INSTANCE = "app.kubernetes.io/instance"
APP_K8S_VERSION = "app.kubernetes.io/version"
APP_K8S_MANAGED_BY = "app.kubernetes.io/managed-by"


def worst(*statuses: str) -> str:
    current = HEALTHY
    found = False
    for status in statuses:
        value = status or UNKNOWN
        if value not in RANK:
            value = UNKNOWN
        if not found or RANK[value] > RANK[current]:
            current = value
            found = True
    return current if found else UNKNOWN


def catalog_status(status: str) -> str:
    if status == HEALTHY:
        return "Passing"
    if status == DEGRADED:
        return "Warning"
    if status in {UNHEALTHY, CRITICAL}:
        return "Failing"
    return "Warning"
