from collections.abc import Callable, Sequence

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.v1.params import parse_scope
from app.core.config import settings
from app.core.security import assert_no_secret_values, walk_strings
from app.domain.models import Scope


def listed(items: Sequence[BaseModel]) -> dict:
    payload = {"items": [item.model_dump() for item in items], "lastSynced": settings.last_synced}
    assert_no_secret_values(walk_strings(payload))
    return payload


def add_list_route(router: APIRouter, path: str, loader: Callable[[Scope], Sequence[BaseModel]]) -> None:
    @router.get(path)
    def endpoint(scope: Scope = Depends(parse_scope)) -> dict:
        return listed(loader(scope))

    endpoint.__name__ = f"list_{path.strip('/').replace('/', '_')}"
