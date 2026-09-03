import os

os.environ.setdefault("CLOUDOPS_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("CLOUDOPS_CELERY_EAGER", "true")
os.environ.setdefault("CLOUDOPS_AWS_ENABLED", "false")
os.environ.setdefault("AWS_EC2_METADATA_DISABLED", "true")
os.environ.setdefault("CLOUDOPS_SECRET_BACKEND", "local")
os.environ.setdefault("CLOUDOPS_ALLOW_LOCAL_SECRETS", "true")
os.environ.setdefault("CLOUDOPS_REQUIRE_AUTH", "false")
os.environ.setdefault("CLOUDOPS_DEMO_MODE", "true")
os.environ.setdefault("CLOUDOPS_SEED_TOPOLOGY", "true")

from app.db.session import init_db

init_db()

import pytest

from app.core.rate_limit import reset_rate_limits
from app.notifications.dispatcher import TEST_PROVIDERS
from app.db.models import (
    AcmCertificateRow,
    CertificateAlertRow,
    CertificateAuditRow,
    CertificateEndpointRow,
    CertificateHistoryRow,
    CertificateValidationRow,
    CloudEnvironmentRow,
    CloudAccountRow,
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
    AlertRow,
    AlertEventRow,
    AlertRuleRow,
    AlertRoutingRuleRow,
    AlertSuppressionRow,
    AlertAuditRow,
    MaintenanceWindowRow,
    NotificationDeliveryRow,
    NotificationDestinationRow,
    NotificationPolicyRow,
    NotificationPolicyStepRow,
    ApplicationEnvironmentBindingRow,
    ManagedApplicationRow,
    ManagedProviderRow,
    PlatformSettingRow,
    PlatformAuditRow,
)
from app.db.session import SessionLocal
from app.secrets.backends.local import LocalDevSecretBackend


@pytest.fixture(autouse=True)
def reset_live_tables() -> None:
    LocalDevSecretBackend.reset()
    TEST_PROVIDERS.clear()
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
    ApplicationEnvironmentBindingRow,
    ManagedApplicationRow,
    ManagedProviderRow,
    PlatformSettingRow,
    PlatformAuditRow,
    NotificationDeliveryRow,
        AlertEventRow,
        AlertAuditRow,
        AlertSuppressionRow,
        MaintenanceWindowRow,
        AlertRow,
        AlertRoutingRuleRow,
        NotificationPolicyStepRow,
        NotificationPolicyRow,
        NotificationDestinationRow,
        AlertRuleRow,
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
        ApplicationEnvironmentBindingRow,
        ManagedApplicationRow,
        ManagedProviderRow,
        PlatformSettingRow,
        PlatformAuditRow,
    ):
        session.query(model).delete()
    managed_ids = [
        row.id for row in session.query(CloudAccountRow).filter(CloudAccountRow.managed_provider_id != "")
    ]
    if managed_ids:
        session.query(CloudEnvironmentRow).filter(CloudEnvironmentRow.account_id.in_(managed_ids)).delete(
            synchronize_session=False
        )
        session.query(CloudAccountRow).filter(CloudAccountRow.id.in_(managed_ids)).delete(synchronize_session=False)
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
