from __future__ import annotations

from app.integrations.github.client import GitHubClient
from app.integrations.github.mapper import parse_datetime
from app.integrations.scm.base import ScmRepository, ScmVariable


def list_variables(client: GitHubClient, repository: ScmRepository) -> list[ScmVariable]:
    variables: list[ScmVariable] = []
    for payload in client.paginate(f"/repos/{repository.full_name}/actions/variables", item_key="variables"):
        variables.append(
            ScmVariable(
                name=str(payload.get("name") or ""),
                value=str(payload.get("value") or ""),
                scope="repository",
                repository_external_id=repository.external_id,
                organization=repository.organization,
                updated_at=parse_datetime(payload.get("updated_at")),
                sensitive=False,
            )
        )
    for environment in _environments(client, repository):
        for payload in client.paginate(
            f"/repos/{repository.full_name}/environments/{environment}/variables",
            item_key="variables",
        ):
            variables.append(
                ScmVariable(
                    name=str(payload.get("name") or ""),
                    value=str(payload.get("value") or ""),
                    scope="environment",
                    repository_external_id=repository.external_id,
                    organization=repository.organization,
                    github_environment=environment,
                    updated_at=parse_datetime(payload.get("updated_at")),
                    sensitive=False,
                )
            )
    return [item for item in variables if item.name]


def list_organization_variables(client: GitHubClient, organization: str) -> list[ScmVariable]:
    if not organization:
        return []
    variables: list[ScmVariable] = []
    try:
        for payload in client.paginate(f"/orgs/{organization}/actions/variables", item_key="variables"):
            name = str(payload.get("name") or "")
            if not name:
                continue
            variables.append(
                ScmVariable(
                    name=name,
                    value=str(payload.get("value") or ""),
                    scope="organization",
                    organization=organization,
                    updated_at=parse_datetime(payload.get("updated_at")),
                    sensitive=False,
                )
            )
    except Exception:
        return variables
    return variables


def put_variable(
    client: GitHubClient,
    repository: ScmRepository,
    *,
    name: str,
    value: str,
    github_environment: str = "",
) -> None:
    path = (
        f"/repos/{repository.full_name}/environments/{github_environment}/variables/{name}"
        if github_environment
        else f"/repos/{repository.full_name}/actions/variables/{name}"
    )
    try:
        client.request("PATCH", path, json_body={"name": name, "value": value})
    except Exception:
        create_path = (
            f"/repos/{repository.full_name}/environments/{github_environment}/variables"
            if github_environment
            else f"/repos/{repository.full_name}/actions/variables"
        )
        client.request("POST", create_path, json_body={"name": name, "value": value})


def delete_variable(client: GitHubClient, repository: ScmRepository, *, name: str, github_environment: str = "") -> None:
    path = (
        f"/repos/{repository.full_name}/environments/{github_environment}/variables/{name}"
        if github_environment
        else f"/repos/{repository.full_name}/actions/variables/{name}"
    )
    client.request("DELETE", path)


def _environments(client: GitHubClient, repository: ScmRepository) -> list[str]:
    names: list[str] = []
    try:
        for payload in client.paginate(f"/repos/{repository.full_name}/environments", item_key="environments"):
            name = str(payload.get("name") or "")
            if name:
                names.append(name)
    except Exception:
        return names
    return names
