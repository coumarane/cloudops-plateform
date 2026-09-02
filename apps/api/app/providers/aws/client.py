from __future__ import annotations

from typing import Any

import boto3

from app.providers.aws.auth import build_session, client_config


class AwsClientFactory:
    def __init__(self, session: boto3.Session | None = None) -> None:
        self._session = session

    @property
    def session(self) -> boto3.Session:
        if self._session is None:
            self._session = build_session()
        return self._session

    def client(self, service_name: str, *, region_name: str | None = None) -> Any:
        return self.session.client(
            service_name,
            region_name=region_name,
            config=client_config(),
        )
