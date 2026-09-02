from __future__ import annotations

from typing import Any

import boto3

from app.providers.aws.auth import build_session, client_config
from app.providers.aws.models import AwsConnectionConfig


class AwsClientFactory:
    def __init__(self, session: boto3.Session | None = None, config: AwsConnectionConfig | None = None) -> None:
        self._session = session
        self._config = config

    @property
    def session(self) -> boto3.Session:
        if self._session is None:
            self._session = build_session(config=self._config)
        return self._session

    def client(self, service_name: str, *, region_name: str | None = None) -> Any:
        return self.session.client(
            service_name,
            region_name=region_name or (self._config.cloud_region if self._config else None),
            config=client_config(),
        )
