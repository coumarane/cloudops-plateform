from __future__ import annotations

from app.integrations.github.client import GitHubClient
from app.integrations.github.crypto import encrypt_secret
from app.integrations.github.mapper import parse_datetime
from app.integrations.scm.base import ScmPublicKey, ScmRepository, ScmSecret
from app.integrations.github.variables import _environments


def list_secrets(client: GitHubClient, repository: ScmRepository) -> list[ScmSecret]:
    secrets: list[ScmSecret] = []
    for payload in client.paginate(f"/repos/{repository.full_name}/actions/secrets", item_key="secrets"):
        secrets.append(_from_payload(payload, repository, scope="repository"))
    for environment in _environments(client, repository):
        for payload in client.paginate(
            f"/repos/{repository.full_name}/environments/{environment}/secrets",
            item_key="secrets",
        ):
            secrets.append(_from_payload(payload, repository, scope="environment", github_environment=environment))
    return [item for item in secrets if item.name]


def list_organization_secrets(client: GitHubClient, organization: str) -> list[ScmSecret]:
    if not organization:
        return []
    secrets: list[ScmSecret] = []
    try:
        for payload in client.paginate(f"/orgs/{organization}/actions/secrets", item_key="secrets"):
            name = str(payload.get("name") or "")
            if not name:
                continue
            secrets.append(
                ScmSecret(
                    name=name,
                    scope="organization",
                    organization=organization,
                    created_at=parse_datetime(payload.get("created_at")),
                    updated_at=parse_datetime(payload.get("updated_at")),
                )
            )
    except Exception:
        return secrets
    return secrets


def put_secret(
    client: GitHubClient,
    repository: ScmRepository,
    *,
    name: str,
    value: str,
    github_environment: str = "",
) -> None:
    key = _public_key(client, repository, github_environment=github_environment)
    encrypted = encrypt_secret(key.key, value)
    path = (
        f"/repos/{repository.full_name}/environments/{github_environment}/secrets/{name}"
        if github_environment
        else f"/repos/{repository.full_name}/actions/secrets/{name}"
    )
    client.request("PUT", path, json_body={"encrypted_value": encrypted, "key_id": key.key_id})


def delete_secret(client: GitHubClient, repository: ScmRepository, *, name: str, github_environment: str = "") -> None:
    path = (
        f"/repos/{repository.full_name}/environments/{github_environment}/secrets/{name}"
        if github_environment
        else f"/repos/{repository.full_name}/actions/secrets/{name}"
    )
    client.request("DELETE", path)


def _public_key(client: GitHubClient, repository: ScmRepository, *, github_environment: str = "") -> ScmPublicKey:
    path = (
        f"/repos/{repository.full_name}/environments/{github_environment}/secrets/public-key"
        if github_environment
        else f"/repos/{repository.full_name}/actions/secrets/public-key"
    )
    payload = client.request("GET", path) or {}
    return ScmPublicKey(key_id=str(payload.get("key_id") or ""), key=str(payload.get("key") or ""))


def _from_payload(payload: dict, repository: ScmRepository, *, scope: str, github_environment: str = "") -> ScmSecret:
    return ScmSecret(
        name=str(payload.get("name") or ""),
        scope=scope,
        repository_external_id=repository.external_id,
        organization=repository.organization,
        github_environment=github_environment,
        created_at=parse_datetime(payload.get("created_at")),
        updated_at=parse_datetime(payload.get("updated_at")),
    )
