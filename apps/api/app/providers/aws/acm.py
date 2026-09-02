from __future__ import annotations

from datetime import datetime, timezone

from botocore.exceptions import ClientError

from app.core.logging import get_logger
from app.providers.aws.client import AwsClientFactory
from app.providers.aws.errors import classify_aws_error
from app.providers.aws.models import AwsConnectionConfig, DiscoveredCertificate

logger = get_logger(__name__)


def _as_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return None


def _days_remaining(not_after: datetime | None, now: datetime) -> int | None:
    if not_after is None:
        return None
    delta = not_after - now
    return delta.days


def _renewal_status(days: int | None, eligibility: str) -> str:
    if days is None:
        return eligibility or "UNKNOWN"
    if days < 0:
        return "EXPIRED"
    if days <= 14:
        return "EXPIRING"
    return eligibility or "ELIGIBLE"


class AcmScanner:
    def __init__(self, factory: AwsClientFactory, config: AwsConnectionConfig) -> None:
        self._factory = factory
        self._config = config

    def list_certificates(self) -> list[DiscoveredCertificate]:
        client = self._factory.client("acm", region_name=self._config.cloud_region)
        summaries: list[dict] = []
        try:
            paginator = client.get_paginator("list_certificates")
            for page in paginator.paginate():
                summaries.extend(page.get("CertificateSummaryList", []))
        except ClientError as error:
            raise classify_aws_error(error) from error

        now = datetime.now(timezone.utc)
        discovered: list[DiscoveredCertificate] = []
        for summary in summaries:
            arn = summary.get("CertificateArn")
            if not arn:
                continue
            try:
                detail = client.describe_certificate(CertificateArn=arn)["Certificate"]
            except ClientError as error:
                mapped = classify_aws_error(error)
                logger.warning("Skipping ACM certificate error=%s", mapped)
                continue
            not_after = _as_datetime(detail.get("NotAfter"))
            days = _days_remaining(not_after, now)
            in_use = [str(item) for item in detail.get("InUseBy") or []]
            eligibility = str(detail.get("RenewalEligibility") or "UNKNOWN")
            discovered.append(
                DiscoveredCertificate(
                    arn=arn,
                    domain_name=detail.get("DomainName") or summary.get("DomainName") or "",
                    subject_alternative_names=[str(item) for item in detail.get("SubjectAlternativeNames") or []],
                    issuer=detail.get("Issuer") or "",
                    status=detail.get("Status") or summary.get("Status") or "UNKNOWN",
                    not_before=_as_datetime(detail.get("NotBefore")),
                    not_after=not_after,
                    days_remaining=days,
                    in_use_by=in_use,
                    renewal_eligibility=_renewal_status(days, eligibility),
                    last_checked=now,
                    environment="",
                    platform_region=self._config.platform_region,
                    account_alias=self._config.account_alias,
                    cloud_region=self._config.cloud_region,
                )
            )
        logger.info("Discovered %s ACM certificates account=%s", len(discovered), self._config.account_alias)
        return discovered
