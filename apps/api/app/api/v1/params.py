from fastapi import HTTPException, Query

from app.domain.enums import ENVIRONMENTS, PROVIDERS, REGIONS, Environment, Provider, Region
from app.domain.models import Scope

PROVIDER_ALIASES: dict[str, Provider] = {item.lower(): item for item in PROVIDERS} | {
    "aws": "AWS",
    "alibaba": "Alibaba",
    "azure": "Azure",
    "gcp": "GCP",
    "google": "GCP",
}
REGION_ALIASES: dict[str, Region] = {item.lower(): item for item in REGIONS}
ENVIRONMENT_ALIASES: dict[str, Environment] = {
    item.lower(): item for item in ENVIRONMENTS
} | {"int-tst": "INT/TST", "int/tst": "INT/TST"}


def parse_provider(value: str | None) -> Provider | None:
    if not value or value == "all":
        return None
    parsed = PROVIDER_ALIASES.get(value.lower())
    if parsed is None:
        raise HTTPException(status_code=400, detail="Unknown provider")
    return parsed


def parse_region(value: str | None) -> Region | None:
    if not value or value == "all":
        return None
    parsed = REGION_ALIASES.get(value.lower())
    if parsed is None:
        raise HTTPException(status_code=400, detail="Unknown region")
    return parsed


def parse_environment(value: str | None) -> Environment | None:
    if not value or value == "all":
        return None
    parsed = ENVIRONMENT_ALIASES.get(value.lower())
    if parsed is None:
        raise HTTPException(status_code=400, detail="Unknown environment")
    return parsed


def parse_scope(
    provider: str | None = Query(default=None),
    region: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    account: str | None = Query(default=None),
) -> Scope:
    parsed_account = None if not account or account == "all" else account
    return Scope(
        provider=parse_provider(provider),
        region=parse_region(region),
        environment=parse_environment(environment),
        account=parsed_account,
    )
