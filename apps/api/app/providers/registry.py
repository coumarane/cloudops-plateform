from app.domain.enums import Provider
from app.providers.base import CloudProviderPort
from app.providers.mock_alibaba import MockAlibabaAdapter
from app.providers.mock_aws import MockAwsAdapter


class ProviderRegistry:
    def __init__(self, adapters: list[CloudProviderPort] | None = None) -> None:
        self._adapters = adapters or [MockAwsAdapter(), MockAlibabaAdapter()]

    def all(self) -> list[CloudProviderPort]:
        return list(self._adapters)

    def get(self, provider: Provider) -> CloudProviderPort:
        for adapter in self._adapters:
            if adapter.name == provider:
                return adapter
        raise KeyError(provider)


registry = ProviderRegistry()
