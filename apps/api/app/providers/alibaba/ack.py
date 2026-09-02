from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.providers.alibaba.client import AlibabaClientFactory
from app.providers.alibaba.exceptions import classify_alibaba_error
from app.providers.alibaba.models import AlibabaConnectionConfig
from app.providers.common.models import DiscoveredCluster
from app.topology.models import environment_scope_id

logger = get_logger(__name__)

STATE_MAP = {
    "running": "ACTIVE",
    "active": "ACTIVE",
    "initial": "CREATING",
    "creating": "CREATING",
    "updating": "UPDATING",
    "deleting": "DELETING",
    "deleted": "DELETED",
    "unavailable": "FAILED",
    "failed": "FAILED",
}


def _parse_created_at(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def environment_from_tags(tags: object, tag_key: str) -> str | None:
    items: list[tuple[str, str]] = []
    if isinstance(tags, dict):
        items = [(str(key), str(value)) for key, value in tags.items()]
    elif isinstance(tags, list):
        for item in tags:
            if not isinstance(item, dict):
                continue
            key = item.get("key") or item.get("Key") or item.get("tagKey")
            value = item.get("value") or item.get("Value") or item.get("tagValue")
            if key is not None and value is not None:
                items.append((str(key), str(value)))
    lookup = {key.lower(): value for key, value in items}
    raw = lookup.get(tag_key.lower()) or lookup.get("environment") or lookup.get("env")
    if raw is None:
        return None
    normalized = raw.strip().upper().replace("_", "/")
    if normalized in {"INT/TST", "INT-TST", "INTTST", "TST"}:
        return "INT/TST"
    if normalized in {"DEV", "UAT", "NPD", "PRD"}:
        return normalized
    return None


def _endpoint_from_master_url(master_url: object) -> tuple[str | None, str]:
    if not master_url:
        return None, "UNKNOWN"
    payload = master_url
    if isinstance(master_url, str):
        try:
            payload = json.loads(master_url)
        except json.JSONDecodeError:
            if master_url.startswith("https://"):
                return master_url, "PUBLIC"
            return None, "UNKNOWN"
    if not isinstance(payload, dict):
        return None, "UNKNOWN"
    endpoint = (
        payload.get("api_server_endpoint")
        or payload.get("endpoint")
        or payload.get("intranet_api_server_endpoint")
    )
    if not endpoint:
        return None, "UNKNOWN"
    intranet = payload.get("intranet_api_server_endpoint")
    public = payload.get("api_server_endpoint")
    if public and intranet:
        status = "PUBLIC_PRIVATE"
    elif intranet and not public:
        status = "PRIVATE"
    else:
        status = "PUBLIC"
    return str(endpoint), status


def normalize_ack_cluster(
    payload: dict[str, Any],
    config: AlibabaConnectionConfig,
    allowed_environments: Sequence[str],
) -> DiscoveredCluster | None:
    tags = payload.get("tags") or payload.get("Tags") or []
    environment = environment_from_tags(tags, config.cluster_environment_tag)
    if environment is None or environment not in set(allowed_environments):
        return None
    cluster_id = str(payload.get("cluster_id") or payload.get("clusterId") or payload.get("ClusterId") or "")
    name = str(payload.get("name") or payload.get("Name") or cluster_id)
    if not cluster_id:
        return None
    region = str(payload.get("region_id") or payload.get("regionId") or config.cloud_region)
    state = str(payload.get("state") or payload.get("cluster_status") or payload.get("State") or "UNKNOWN")
    cluster_status = STATE_MAP.get(state.lower(), state.upper() or "UNKNOWN")
    version = str(payload.get("current_version") or payload.get("currentVersion") or payload.get("version") or "")
    cluster_type = str(payload.get("cluster_type") or payload.get("clusterType") or "ACK")
    endpoint, endpoint_status = _endpoint_from_master_url(payload.get("master_url") or payload.get("masterUrl"))
    account_id = config.account_id or "unknown"
    arn = f"acs:cs:{region}:{account_id}:cluster/{cluster_id}"
    return DiscoveredCluster(
        name=name,
        arn=arn,
        cloud_region=region,
        aws_account_id=account_id,
        kubernetes_version=version,
        endpoint_status=endpoint_status,
        cluster_status=cluster_status,
        platform_version=cluster_type,
        created_at=_parse_created_at(payload.get("created") or payload.get("created_at") or payload.get("Created")),
        endpoint=endpoint,
        environment=environment,
        platform_region=config.platform_region,
        account_alias=config.account_alias,
        environment_id=environment_scope_id(config.account_alias, environment),
        provider="Alibaba",
        cluster_type=cluster_type,
        extra_json=json.dumps({"cluster_id": cluster_id, "state": state}),
    )


class AckDiscovery:
    def __init__(self, factory: AlibabaClientFactory, config: AlibabaConnectionConfig) -> None:
        self._factory = factory
        self._config = config

    def list_clusters(self, allowed_environments: Sequence[str]) -> list[DiscoveredCluster]:
        try:
            raw_clusters = self._factory.list_clusters()
        except Exception as error:
            raise classify_alibaba_error(error) from error
        discovered: list[DiscoveredCluster] = []
        for payload in raw_clusters:
            cluster_id = str(payload.get("cluster_id") or payload.get("clusterId") or "")
            detail = payload
            if cluster_id:
                try:
                    detail = {**payload, **self._factory.describe_cluster(cluster_id)}
                except Exception as error:
                    logger.warning("Skipping ACK cluster detail id=%s error=%s", cluster_id, classify_alibaba_error(error))
            cluster = normalize_ack_cluster(detail, self._config, allowed_environments)
            if cluster is not None:
                discovered.append(cluster)
        logger.info(
            "Discovered %s ACK clusters account=%s region=%s",
            len(discovered),
            self._config.account_alias,
            self._config.cloud_region,
        )
        return discovered
