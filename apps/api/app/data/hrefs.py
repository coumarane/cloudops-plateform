from app.domain.enums import Environment, Provider, Region


def provider_slug(provider: Provider) -> str:
    return provider.lower()


def region_slug(region: Region) -> str:
    return region.lower()


def environment_slug(environment: Environment) -> str:
    return "int-tst" if environment == "INT/TST" else environment.lower()


def catalog_href(
    path: str,
    provider: Provider,
    region: Region,
    environment: Environment,
    selected: str | None = None,
    extra: dict[str, str] | None = None,
) -> str:
    params = [
        f"provider={provider_slug(provider)}",
        f"region={region_slug(region)}",
        f"environment={environment_slug(environment)}",
    ]
    if selected:
        key = "certificate" if path == "/certificates" else "selected"
        params.append(f"{key}={selected}")
    if extra:
        params.extend(f"{key}={value}" for key, value in extra.items())
    return f"{path}?{'&'.join(params)}"
