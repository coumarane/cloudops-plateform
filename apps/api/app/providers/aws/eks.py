from __future__ import annotations

from datetime import datetime, timezone

from botocore.exceptions import ClientError

from app.core.logging import get_logger
from app.providers.aws.auth import connection_config
from app.providers.aws.client import AwsClientFactory
from app.providers.aws.errors import classify_aws_error
from app.providers.aws.models import DiscoveredCluster

logger = get_logger(__name__)


def _parse_created_at(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return None


def _environment_from_tags(tags: dict[str, str], expected: str, tag_key: str) -> str | None:
    raw = tags.get(tag_key) or tags.get(tag_key.lower()) or tags.get("environment")
    if raw is None:
        return expected
    normalized = raw.strip().upper().replace("_", "/")
    if normalized in {"INT/TST", "INT-TST", "INTTST"}:
        return "INT/TST"
    if normalized in {"DEV", "UAT", "NPD", "PRD"}:
        return normalized
    return None


def _endpoint_status(resources_vpc: dict) -> str:
    public = bool(resources_vpc.get("endpointPublicAccess"))
    private = bool(resources_vpc.get("endpointPrivateAccess"))
    if public and private:
        return "PUBLIC_PRIVATE"
    if public:
        return "PUBLIC"
    if private:
        return "PRIVATE"
    return "UNKNOWN"


class EksDiscovery:
    def __init__(self, factory: AwsClientFactory | None = None) -> None:
        self._factory = factory or AwsClientFactory()

    def list_dev_clusters(self) -> list[DiscoveredCluster]:
        config = connection_config()
        client = self._factory.client("eks", region_name=config.cloud_region)
        names: list[str] = []
        try:
            paginator = client.get_paginator("list_clusters")
            for page in paginator.paginate():
                names.extend(page.get("clusters", []))
        except ClientError as error:
            raise classify_aws_error(error) from error

        discovered: list[DiscoveredCluster] = []
        for name in names:
            try:
                description = client.describe_cluster(name=name)["cluster"]
            except ClientError as error:
                mapped = classify_aws_error(error)
                logger.warning("Skipping EKS cluster name=%s error=%s", name, mapped)
                continue
            tags = description.get("tags") or {}
            environment = _environment_from_tags(tags, config.environment, config.cluster_environment_tag)
            if environment != config.environment:
                continue
            arn = description.get("arn") or f"arn:aws:eks:{config.cloud_region}:unknown:cluster/{name}"
            account_id = arn.split(":")[4] if arn.count(":") >= 4 else (config.account_id or "unknown")
            resources_vpc = description.get("resourcesVpcConfig") or {}
            discovered.append(
                DiscoveredCluster(
                    name=description.get("name") or name,
                    arn=arn,
                    cloud_region=config.cloud_region,
                    aws_account_id=account_id,
                    kubernetes_version=description.get("version") or "",
                    endpoint_status=_endpoint_status(resources_vpc),
                    cluster_status=description.get("status") or "UNKNOWN",
                    platform_version=description.get("platformVersion") or "",
                    created_at=_parse_created_at(description.get("createdAt")),
                    endpoint=description.get("endpoint"),
                    environment=config.environment,
                    platform_region=config.platform_region,
                    account_alias=config.account_alias,
                )
            )
        logger.info("Discovered %s EKS clusters in %s DEV", len(discovered), config.cloud_region)
        return discovered

    def describe_raw(self, name: str) -> dict:
        config = connection_config()
        client = self._factory.client("eks", region_name=config.cloud_region)
        try:
            return client.describe_cluster(name=name)["cluster"]
        except ClientError as error:
            raise classify_aws_error(error) from error
