from dataclasses import dataclass, field
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DiscoveredCluster:
    name: str
    arn: str
    cloud_region: str
    aws_account_id: str
    kubernetes_version: str
    endpoint_status: str
    cluster_status: str
    platform_version: str
    created_at: datetime | None
    endpoint: str | None = None
    environment: str = "DEV"
    platform_region: str = "EMEA"
    account_alias: str = "aws-emea-nonprod"
    environment_id: str = ""
    provider: str = "AWS"
    cluster_type: str = ""
    extra_json: str = "{}"


@dataclass
class ClusterHealthSnapshot:
    cluster_arn: str
    control_plane_status: str
    kubernetes_api_reachable: bool
    node_count: int = 0
    ready_node_count: int = 0
    pod_count: int = 0
    unhealthy_pod_count: int = 0
    crashloop_backoff_count: int = 0
    pending_pod_count: int = 0
    unavailable_deployment_count: int = 0
    failed_job_count: int = 0
    stateful_set_unhealthy_count: int = 0
    ingress_unhealthy_count: int = 0
    last_checked: datetime = field(default_factory=utc_now)
    detail: str = ""


@dataclass
class DiscoveredCertificate:
    arn: str
    domain_name: str
    subject_alternative_names: list[str]
    issuer: str
    status: str
    not_before: datetime | None
    not_after: datetime | None
    days_remaining: int | None
    in_use_by: list[str]
    renewal_eligibility: str
    last_checked: datetime = field(default_factory=utc_now)
    environment: str = "DEV"
    platform_region: str = "EMEA"
    account_alias: str = "aws-emea-nonprod"
    cloud_region: str = "eu-west-1"
    environment_id: str = ""
    provider: str = "AWS"
    cluster_name: str = ""
    namespace: str = ""
    source: str = ""
