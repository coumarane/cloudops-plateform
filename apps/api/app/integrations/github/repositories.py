from __future__ import annotations

from app.integrations.github.client import GitHubClient
from app.integrations.github.mapper import parse_datetime
from app.integrations.scm.base import ScmOrganization, ScmRepository


def list_installations(client: GitHubClient) -> list[dict]:
    payload = client.request("GET", "/app/installations")
    if isinstance(payload, list):
        return payload
    return list((payload or {}).get("installations") or [])


def list_organizations(client: GitHubClient) -> list[ScmOrganization]:
    orgs: list[ScmOrganization] = []
    seen: set[str] = set()
    for payload in client.paginate("/user/installations", item_key="installations") or []:
        account = payload.get("account") or {}
        login = str(account.get("login") or "")
        if not login or login in seen:
            continue
        seen.add(login)
        orgs.append(
            ScmOrganization(
                external_id=str(account.get("id") or login),
                login=login,
                name=str(account.get("name") or login),
                avatar_url=str(account.get("avatar_url") or ""),
                html_url=str(account.get("html_url") or f"https://github.com/{login}"),
            )
        )
    if orgs:
        return orgs
    for payload in client.paginate("/installation/repositories", item_key="repositories"):
        owner = payload.get("owner") or {}
        login = str(owner.get("login") or "")
        if not login or login in seen:
            continue
        seen.add(login)
        orgs.append(
            ScmOrganization(
                external_id=str(owner.get("id") or login),
                login=login,
                name=str(owner.get("login") or login),
                avatar_url=str(owner.get("avatar_url") or ""),
                html_url=str(owner.get("html_url") or f"https://github.com/{login}"),
            )
        )
    return orgs


def list_repositories(client: GitHubClient) -> list[ScmRepository]:
    repos: list[ScmRepository] = []
    for payload in client.paginate("/installation/repositories", item_key="repositories"):
        owner = payload.get("owner") or {}
        name = str(payload.get("name") or "")
        full_name = str(payload.get("full_name") or f"{owner.get('login')}/{name}")
        repos.append(
            ScmRepository(
                external_id=str(payload.get("id") or full_name),
                organization=str(owner.get("login") or ""),
                name=name,
                full_name=full_name,
                description=str(payload.get("description") or ""),
                default_branch=str(payload.get("default_branch") or "main"),
                visibility=str(payload.get("visibility") or ("private" if payload.get("private") else "public")),
                archived=bool(payload.get("archived")),
                html_url=str(payload.get("html_url") or f"https://github.com/{full_name}"),
                pushed_at=parse_datetime(payload.get("pushed_at")),
            )
        )
    return repos
