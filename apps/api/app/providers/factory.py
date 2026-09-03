from app.core.config import settings
from app.domain.enums import Provider
from app.providers.alibaba.adapter import AlibabaProviderAdapter
from app.providers.aws.adapter import AWSProviderAdapter
from app.providers.contract import CloudProviderAdapter
from app.providers.stub import StubCloudProviderAdapter

_LIVE_ADAPTERS: dict[str, CloudProviderAdapter] = {
    "AWS": AWSProviderAdapter(),
    "Alibaba": AlibabaProviderAdapter(),
}

AWSProviderAdapter.provider_type = "AWS"
AWSProviderAdapter.discovery_job_kind = "aws-cluster-discovery"
AWSProviderAdapter.health_job_kind = "aws-health-scan"
AWSProviderAdapter.certificate_job_kind = "aws-certificate-scan"
AlibabaProviderAdapter.provider_type = "Alibaba"
AlibabaProviderAdapter.discovery_job_kind = "alibaba-cluster-discovery"
AlibabaProviderAdapter.health_job_kind = "alibaba-health-scan"
AlibabaProviderAdapter.certificate_job_kind = "alibaba-certificate-discovery"


def provider_adapter(provider: Provider | str) -> CloudProviderAdapter:
    key = str(provider)
    if settings.provider_stub:
        return StubCloudProviderAdapter(key if key in _LIVE_ADAPTERS else "AWS")
    try:
        return _LIVE_ADAPTERS[key]
    except KeyError as error:
        raise KeyError(provider) from error


def list_providers() -> list[Provider]:
    return ["AWS", "Alibaba"]
