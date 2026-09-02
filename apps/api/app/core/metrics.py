from __future__ import annotations

from collections import defaultdict
from threading import Lock

_lock = Lock()
_counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
_gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
_duration_sum: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
_duration_count: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)

HELP = {
    "cloudops_certificates_total": "Certificates currently present, labeled by provider/region/environment/status",
    "cloudops_certificates_expiring_total": "Certificates with a finite expiry window (not HEALTHY/UNKNOWN/EXPIRED)",
    "cloudops_certificates_expired_total": "Certificates classified as EXPIRED",
    "cloudops_certificate_scan_duration_seconds": "Certificate job duration in seconds",
    "cloudops_certificate_scan_failures_total": "Certificate scan failures isolated per provider/region/environment",
    "cloudops_github_sync_total": "GitHub synchronization jobs (labels: status, job)",
    "cloudops_github_sync_failures_total": "GitHub synchronization failures (labels: status, job)",
    "cloudops_github_workflow_runs_total": "GitHub workflow runs observed (labels: status, environment_class)",
    "cloudops_github_workflow_failures_total": "GitHub workflow failures (labels: status, environment_class)",
    "cloudops_github_webhook_events_total": "GitHub webhook deliveries (labels: status)",
    "cloudops_github_webhook_failures_total": "GitHub webhook processing failures (labels: status)",
    "cloudops_pipeline_runs_total": "Normalized pipeline runs (labels: provider, status, environment_class)",
    "cloudops_pipeline_runs_failed_total": "Normalized pipeline failures (labels: provider, status, environment_class)",
    "cloudops_pipeline_runs_running": "Currently running pipeline runs (labels: provider, status, environment_class)",
    "cloudops_pipeline_sync_duration_seconds": "Pipeline synchronization duration in seconds",
    "cloudops_pipeline_sync_failures_total": "Pipeline provider synchronization failures (labels: provider, status, environment_class)",
    "cloudops_application_health_total": "Applications by health status (labels: provider, region, environment_class, health_status)",
    "cloudops_cluster_health_total": "Clusters by health status (labels: provider, region, environment_class, health_status)",
    "cloudops_health_checks_total": "Health checks executed (labels: provider, region, environment_class, health_status)",
    "cloudops_health_check_failures_total": "Health check failures isolated per environment (labels: provider, region, environment_class, health_status)",
    "cloudops_open_incidents_total": "Open health incidents (labels: provider, region, environment_class, health_status)",
    "cloudops_health_scan_duration_seconds": "Health scan duration in seconds (labels: provider, region, environment_class, health_status)",
}


def _key(name: str, labels: dict[str, str] | None) -> tuple[str, tuple[tuple[str, str], ...]]:
    items = tuple(sorted((str(k), str(v)) for k, v in (labels or {}).items()))
    return name, items


def inc(name: str, labels: dict[str, str] | None = None, amount: float = 1) -> None:
    with _lock:
        _counters[_key(name, labels)] += amount


def set_gauge(name: str, labels: dict[str, str] | None, value: float) -> None:
    with _lock:
        _gauges[_key(name, labels)] = value


def observe_duration(name: str, labels: dict[str, str] | None, seconds: float) -> None:
    with _lock:
        key = _key(name, labels)
        _duration_sum[key] += seconds
        _duration_count[key] += 1


def reset_metrics() -> None:
    with _lock:
        _counters.clear()
        _gauges.clear()
        _duration_sum.clear()
        _duration_count.clear()


def _format_labels(labels: tuple[tuple[str, str], ...]) -> str:
    if not labels:
        return ""
    inner = ",".join(f'{key}="{value}"' for key, value in labels)
    return f"{{{inner}}}"


def render_prometheus() -> str:
    lines: list[str] = []
    with _lock:
        names = sorted(
            {key[0] for key in list(_counters) + list(_gauges) + list(_duration_sum)}
            | set(HELP)
        )
        for name in names:
            help_text = HELP.get(name, name)
            if name.endswith("_seconds"):
                lines.append(f"# HELP {name} {help_text}")
                lines.append(f"# TYPE {name} summary")
                for key, total in sorted(_duration_sum.items()):
                    if key[0] != name:
                        continue
                    labels = _format_labels(key[1])
                    lines.append(f"{name}_sum{labels} {total}")
                    lines.append(f"{name}_count{labels} {_duration_count[key]}")
                continue
            metric_type = "gauge" if name in {item[0] for item in _gauges} or name.endswith("_total") and name.startswith("cloudops_certificates") and "scan" not in name else "counter"
            if name.startswith("cloudops_certificates") and "scan" not in name:
                metric_type = "gauge"
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} {metric_type}")
            for key, value in sorted({**_counters, **_gauges}.items()):
                if key[0] != name:
                    continue
                lines.append(f"{name}{_format_labels(key[1])} {value}")
    return "\n".join(lines) + "\n"
