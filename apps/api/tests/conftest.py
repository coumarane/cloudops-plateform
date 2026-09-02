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
    CertificateAlertRow,
    CertificateAuditRow,
    CertificateEndpointRow,
    CertificateHistoryRow,
    CertificateValidationRow,
    CloudEnvironmentRow,
    CredentialAuditRow,
    CredentialRotationEventRow,
    CredentialRow,
    CredentialValidationRow,
    CredentialVersionRow,
    EksClusterHealthRow,
    EksClusterRow,
    GithubAlertRow,
    GithubApplicationRepositoryRow,
    GithubAuditRow,
    GithubEnvironmentMappingRow,
    GithubIntegrationRow,
    GithubOrganizationRow,
    GithubRepositoryRow,
    GithubSecretRow,
    GithubVariableRow,
    GithubWebhookDeliveryRow,
    GithubWorkflowJobRow,
    GithubWorkflowRunRow,
    GithubWorkflowRow,
    LiveScopeStateRow,
    NotificationEventRow,
    PipelineAlertRow,
    PipelineApplicationMappingRow,
    PipelineAuditRow,
    PipelineEnvironmentMappingRow,
    PipelineJobRow,
    PipelineProviderRow,
    PipelineRow,
    PipelineRunRow,
    PipelineStageRow,
    PipelineWebhookDeliveryRow,
    PlatformJobRow,
    ApplicationDependencyRow,
    ApplicationHealthRow,
    ApplicationResourceMappingRow,
    HealthAlertRow,
    HealthAuditRow,
    HealthCheckDefinitionRow,
    HealthCheckResultRow,
    HealthIncidentRow,
    HealthScanLockRow,
    HealthTimelineEventRow,
    ResourceHealthRow,
)
from app.db.session import SessionLocal
from app.secrets.backends.local import LocalDevSecretBackend


@pytest.fixture(autouse=True)
def reset_live_tables() -> None:
    LocalDevSecretBackend.reset()
    reset_rate_limits()
    session = SessionLocal()
    for model in (
        PipelineJobRow,
        PipelineStageRow,
        PipelineAlertRow,
        PipelineAuditRow,
        PipelineWebhookDeliveryRow,
        PipelineEnvironmentMappingRow,
        PipelineApplicationMappingRow,
        PipelineRunRow,
        PipelineRow,
        PipelineProviderRow,
        HealthCheckResultRow,
        HealthTimelineEventRow,
        HealthAlertRow,
        HealthAuditRow,
        HealthIncidentRow,
        ApplicationDependencyRow,
        ApplicationResourceMappingRow,
        ApplicationHealthRow,
        ResourceHealthRow,
        HealthCheckDefinitionRow,
        HealthScanLockRow,
        GithubWorkflowJobRow,
        GithubAlertRow,
        GithubAuditRow,
        GithubWebhookDeliveryRow,
        GithubSecretRow,
        GithubVariableRow,
        GithubWorkflowRunRow,
        GithubWorkflowRow,
        GithubEnvironmentMappingRow,
        GithubApplicationRepositoryRow,
        GithubRepositoryRow,
        GithubOrganizationRow,
        GithubIntegrationRow,
        CertificateValidationRow,
        CertificateAlertRow,
        CertificateHistoryRow,
        CertificateAuditRow,
        NotificationEventRow,
        CertificateEndpointRow,
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
        row.last_attempted_scan_at = None
        row.last_error = ""
        row.last_error_class = ""
        row.last_error_at = None
    session.commit()
    session.close()
