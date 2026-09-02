from __future__ import annotations

from app.core.logging import get_logger
from app.secrets.backends.base import SecretBackend, SecretMetadata

logger = get_logger(__name__)


class AlibabaSecretsBackend(SecretBackend):
    """Alibaba Cloud Secrets Manager (KMS). SDK objects stay inside this class."""

    name = "alibaba"

    def __init__(self, *, region: str, client=None) -> None:
        self._region = region
        self._client = client

    def _kms(self):
        if self._client is not None:
            return self._client
        try:
            from alibabacloud_kms20160120.client import Client
            from alibabacloud_tea_openapi import models as open_api_models
        except ImportError as error:
            raise RuntimeError("Alibaba KMS SDK is not installed") from error
        import os

        config = open_api_models.Config(
            access_key_id=os.environ.get("CLOUDOPS_ALIBABA_NONPROD_ACCESS_KEY_ID")
            or os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID"),
            access_key_secret=os.environ.get("CLOUDOPS_ALIBABA_NONPROD_ACCESS_KEY_SECRET")
            or os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET"),
            region_id=self._region,
            endpoint=f"kms.{self._region}.aliyuncs.com",
        )
        return Client(config)

    def get_metadata(self, reference: str) -> SecretMetadata:
        if self._client is not None:
            return self._client.get_metadata(reference)
        from alibabacloud_kms20160120 import models as kms_models

        response = self._kms().describe_secret(kms_models.DescribeSecretRequest(secret_name=reference))
        body = getattr(response, "body", response)
        name = getattr(body, "secret_name", None) or reference
        version = str(getattr(body, "version_id", "") or "")
        return SecretMetadata(reference=name, backend=self.name, version=version)

    def store_secret(self, reference: str, secret: str) -> SecretMetadata:
        if self._client is not None:
            try:
                self._client.store_secret(reference, secret)
            except Exception:
                self._client.replace_secret(reference, secret)
            logger.info("Stored Alibaba secret reference=%s", reference)
            return SecretMetadata(reference=reference, backend=self.name)
        from alibabacloud_kms20160120 import models as kms_models

        try:
            self._kms().create_secret(
                kms_models.CreateSecretRequest(secret_name=reference, secret_data=secret, version_id="v1")
            )
        except Exception:
            self.replace_secret(reference, secret)
        logger.info("Stored Alibaba secret reference=%s", reference)
        return SecretMetadata(reference=reference, backend=self.name)

    def replace_secret(self, reference: str, secret: str) -> SecretMetadata:
        if self._client is not None:
            self._client.replace_secret(reference, secret)
            logger.info("Replaced Alibaba secret reference=%s", reference)
            return SecretMetadata(reference=reference, backend=self.name)
        from alibabacloud_kms20160120 import models as kms_models
        from uuid import uuid4

        self._kms().put_secret_value(
            kms_models.PutSecretValueRequest(secret_name=reference, secret_data=secret, version_id=uuid4().hex[:12])
        )
        logger.info("Replaced Alibaba secret reference=%s", reference)
        return SecretMetadata(reference=reference, backend=self.name)

    def delete_secret_reference(self, reference: str) -> None:
        if self._client is not None:
            self._client.delete_secret_reference(reference)
            logger.info("Deleted Alibaba secret reference=%s", reference)
            return
        from alibabacloud_kms20160120 import models as kms_models

        self._kms().delete_secret(kms_models.DeleteSecretRequest(secret_name=reference, force_delete_without_recovery="true"))
        logger.info("Deleted Alibaba secret reference=%s", reference)

    def validate_reference(self, reference: str) -> bool:
        try:
            self.get_metadata(reference)
        except Exception:
            return False
        return True

    def get_secret(self, reference: str) -> str:
        if self._client is not None:
            return self._client.get_secret(reference)
        from alibabacloud_kms20160120 import models as kms_models

        response = self._kms().get_secret_value(kms_models.GetSecretValueRequest(secret_name=reference))
        body = getattr(response, "body", response)
        return str(getattr(body, "secret_data", "") or "")
