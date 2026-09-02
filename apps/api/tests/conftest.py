import os

os.environ.setdefault("CLOUDOPS_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("CLOUDOPS_CELERY_EAGER", "true")
os.environ.setdefault("CLOUDOPS_AWS_ENABLED", "false")
os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
os.environ.setdefault("CLOUDOPS_SECRET_BACKEND", "local")
os.environ.setdefault("CLOUDOPS_ALLOW_LOCAL_SECRETS", "true")
os.environ.setdefault("CLOUDOPS_REQUIRE_AUTH", "false")

from app.db.session import init_db

init_db()

import pytest

from app.core.rate_limit import reset_rate_limits
from app.db.models import (
    AcmCertificateRow,
    CloudEnvironmentRow,
    CredentialAuditRow,
    CredentialRotationEventRow,
    CredentialRow,
    CredentialValidationRow,
    CredentialVersionRow,
    EksClusterHealthRow,
    EksClusterRow,
    LiveScopeStateRow,
    PlatformJobRow,
)
from app.db.session import SessionLocal
from app.secrets.backends.local import LocalDevSecretBackend


@pytest.fixture(autouse=True)
def reset_live_tables() -> None:
    LocalDevSecretBackend.reset()
    reset_rate_limits()
    session = SessionLocal()
    for model in (
        CredentialValidationRow,
        CredentialVersionRow,
        CredentialRotationEventRow,
        CredentialAuditRow,
        CredentialRow,
        EksClusterHealthRow,
        EksClusterRow,
        AcmCertificateRow,
        PlatformJobRow,
        LiveScopeStateRow,
    ):
        session.query(model).delete()
    for row in session.query(CloudEnvironmentRow):
        row.discovery_active = False
        row.last_discovery_at = None
        row.last_health_at = None
        row.last_certificate_scan_at = None
        row.last_successful_scan_at = None
        row.last_error = ""
        row.last_error_class = ""
        row.last_error_at = None
    session.commit()
    session.close()
