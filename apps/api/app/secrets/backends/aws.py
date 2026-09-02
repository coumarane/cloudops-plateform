from __future__ import annotations

from app.core.logging import get_logger
from app.secrets.backends.base import SecretBackend, SecretMetadata

logger = get_logger(__name__)


class AwsSecretsManagerBackend(SecretBackend):
    name = "aws"

    def __init__(self, *, region: str, client=None) -> None:
        self._region = region
        self._client = client

    def _sm(self):
        if self._client is not None:
            return self._client
        import boto3
        from botocore.config import Config

        return boto3.client(
            "secretsmanager",
            region_name=self._region,
            config=Config(retries={"max_attempts": 5, "mode": "standard"}, connect_timeout=5, read_timeout=20),
        )

    def get_metadata(self, reference: str) -> SecretMetadata:
        response = self._sm().describe_secret(SecretId=reference)
        return SecretMetadata(
            reference=response.get("ARN") or reference,
            backend=self.name,
            version=str((response.get("VersionIdsToStages") or {}) and next(iter(response.get("VersionIdsToStages")), "")),
            description=response.get("Name") or "",
        )

    def store_secret(self, reference: str, secret: str) -> SecretMetadata:
        client = self._sm()
        try:
            client.create_secret(Name=reference, SecretString=secret)
        except client.exceptions.ResourceExistsException:
            client.put_secret_value(SecretId=reference, SecretString=secret)
        logger.info("Stored AWS secret reference=%s", reference)
        return self.get_metadata(reference)

    def replace_secret(self, reference: str, secret: str) -> SecretMetadata:
        self._sm().put_secret_value(SecretId=reference, SecretString=secret)
        logger.info("Replaced AWS secret reference=%s", reference)
        return self.get_metadata(reference)

    def delete_secret_reference(self, reference: str) -> None:
        self._sm().delete_secret(SecretId=reference, ForceDeleteWithoutRecovery=True)
        logger.info("Deleted AWS secret reference=%s", reference)

    def validate_reference(self, reference: str) -> bool:
        try:
            self.get_metadata(reference)
        except Exception:
            return False
        return True

    def get_secret(self, reference: str) -> str:
        payload = self._sm().get_secret_value(SecretId=reference)
        return payload.get("SecretString") or ""
