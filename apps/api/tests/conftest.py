import os

os.environ.setdefault("CLOUDOPS_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("CLOUDOPS_CELERY_EAGER", "true")
os.environ.setdefault("CLOUDOPS_AWS_ENABLED", "false")
os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")

from app.db.session import init_db

init_db()

import pytest

from app.db.models import (
    AcmCertificateRow,
    CloudEnvironmentRow,
    EksClusterHealthRow,
    EksClusterRow,
    LiveScopeStateRow,
    PlatformJobRow,
)
from app.db.session import SessionLocal


@pytest.fixture(autouse=True)
def reset_live_tables() -> None:
    session = SessionLocal()
    for model in (EksClusterHealthRow, EksClusterRow, AcmCertificateRow, PlatformJobRow, LiveScopeStateRow):
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
