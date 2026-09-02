from __future__ import annotations

from dataclasses import dataclass, field

from app.integrations.health.status import CRITICAL, DEGRADED, HEALTHY, UNHEALTHY, UNKNOWN, worst


@dataclass
class HealthSignals:
    workload_status: str = UNKNOWN
    desired_replicas: int = 0
    available_replicas: int = 0
    crashloop: int = 0
    failed_pods: int = 0
    restart_count: int = 0
    http_status: str = UNKNOWN
    ingress_status: str = UNKNOWN
    certificate_status: str = UNKNOWN
    pipeline_status: str = UNKNOWN
    deployment_status: str = UNKNOWN
    dependency_status: str = UNKNOWN
    cluster_status: str = UNKNOWN
    restart_degraded_threshold: int = 5


@dataclass
class AggregationResult:
    status: str
    summary: str
    likely_cause: str = ""
    evidence: list[str] = field(default_factory=list)


def aggregate_application(signals: HealthSignals) -> AggregationResult:
    evidence: list[str] = []
    if signals.desired_replicas > 0 and signals.available_replicas == 0:
        evidence.append("all replicas unavailable")
        status = CRITICAL
    elif signals.http_status == CRITICAL or signals.http_status == UNHEALTHY:
        evidence.append("HTTP endpoint unavailable")
        status = CRITICAL if signals.http_status == CRITICAL else UNHEALTHY
    elif signals.ingress_status in {CRITICAL, UNHEALTHY}:
        evidence.append("ingress unavailable")
        status = CRITICAL if signals.ingress_status == CRITICAL else UNHEALTHY
    elif signals.certificate_status == "EXPIRED" or signals.certificate_status == CRITICAL:
        evidence.append("certificate expired")
        status = CRITICAL
    elif signals.cluster_status == CRITICAL:
        evidence.append("cluster connectivity")
        status = CRITICAL
    elif signals.crashloop > 0 or signals.failed_pods > 0 or (
        signals.desired_replicas > 0 and signals.available_replicas < signals.desired_replicas
    ):
        if signals.crashloop:
            evidence.append("CrashLoopBackOff")
        if signals.failed_pods:
            evidence.append("pod failures")
        if signals.desired_replicas and signals.available_replicas < signals.desired_replicas:
            evidence.append("partial workload failure")
        status = UNHEALTHY
    elif (
        signals.restart_count >= signals.restart_degraded_threshold
        or signals.certificate_status in {"WARNING", "CRITICAL", DEGRADED}
        or signals.pipeline_status == "FAILED"
        or signals.deployment_status == "Failed"
        or signals.workload_status == DEGRADED
    ):
        if signals.restart_count >= signals.restart_degraded_threshold:
            evidence.append("increased restarts")
        if signals.certificate_status in {"WARNING", "CRITICAL", DEGRADED}:
            evidence.append("certificate warning")
        if signals.pipeline_status == "FAILED" or signals.deployment_status == "Failed":
            evidence.append("recent failed deployment")
        status = DEGRADED
    elif all(
        item in {HEALTHY, UNKNOWN, "", "HEALTHY", "Succeeded", "SUCCESS", "OK"}
        for item in (
            signals.workload_status,
            signals.http_status,
            signals.ingress_status,
            signals.cluster_status,
        )
    ) and signals.desired_replicas == signals.available_replicas:
        if signals.workload_status == UNKNOWN and signals.http_status == UNKNOWN and signals.desired_replicas == 0:
            status = UNKNOWN
            evidence.append("insufficient data")
        else:
            status = HEALTHY
            evidence.append("required signals passed")
    else:
        status = worst(
            signals.workload_status,
            signals.http_status,
            signals.ingress_status,
            signals.cluster_status,
            signals.dependency_status,
        )
        if status == HEALTHY and signals.desired_replicas == 0 and signals.http_status == UNKNOWN:
            status = UNKNOWN
            evidence.append("insufficient data")

    likely = ""
    deployment_key = (signals.deployment_status or "").upper()
    if deployment_key in {"FAILED", "RUNNING", "SUCCEEDED", "SUCCESS", "PARTIAL"} and status in {UNHEALTHY, CRITICAL, DEGRADED}:
        if "CrashLoopBackOff" in evidence or signals.crashloop:
            likely = "Likely related to a recent deployment"
    if signals.certificate_status in {"EXPIRED", CRITICAL} and status in {UNHEALTHY, CRITICAL}:
        likely = "Likely related to an expired certificate"
    if signals.cluster_status == CRITICAL:
        likely = "Likely related to cluster connectivity"
    summary = "; ".join(evidence) if evidence else status.lower()
    return AggregationResult(status=status, summary=summary, likely_cause=likely, evidence=evidence)
