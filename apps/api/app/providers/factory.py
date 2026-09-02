from app.domain.enums import Provider
from app.providers.alibaba.adapter import AlibabaProviderAdapter
from app.providers.aws.adapter import AWSProviderAdapter

_LIVE_ADAPTERS = {
    "AWS": AWSProviderAdapter(),
    "Alibaba": AlibabaProviderAdapter(),
}


def provider_adapter(provider: Provider) -> AWSProviderAdapter | AlibabaProviderAdapter:
    try:
        return _LIVE_ADAPTERS[provider]
    except KeyError as error:
        raise KeyError(provider) from error


def list_providers() -> list[Provider]:
    return ["AWS", "Alibaba"]
