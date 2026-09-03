from collections.abc import Sequence

from app.core.config import settings
from app.domain.enums import ENVIRONMENTS, Environment
from app.domain.models import (
    CellMetrics,
    DashboardResponse,
    EnvironmentRecord,
    KpiSummary,
    MatrixRow,
    OperationalAlert,
    ProviderRecord,
    RecentFailure,
    Scope,
)
from app.providers.registry import registry
from app.services.overlay import (
    apply_environment_certificates,
    overlay_alerts,
    overlay_applications,
    overlay_certificate_audit,
    overlay_certificates,
    overlay_clusters,
    overlay_environment,
    overlay_environment_identities,
    overlay_github_audit,
    overlay_github_failures,
    overlay_github_runs,
    overlay_jobs,
    overlay_health_checks,
    overlay_pipeline_audit,
    overlay_pipeline_failures,
    overlay_pipelines,
    overlay_matrix,
)


def matches_scope(item: object, scope: Scope) -> bool:
    provider = getattr(item, "provider", None)
    region = getattr(item, "region", None)
    environment = getattr(item, "environment", None)
    account = getattr(item, "account", None)
    hosted = getattr(item, "hostedEnvironments", None)
    if scope.provider and provider != scope.provider:
        return False
    if scope.region and region != scope.region:
        return False
    if scope.account and account != scope.account:
        return False
    if scope.environment:
        if hosted is not None:
            return scope.environment in hosted
        return environment == scope.environment
    return True


def filter_items[T](items: Sequence[T], scope: Scope) -> list[T]:
    return [item for item in items if matches_scope(item, scope)]


class CatalogService:
    def __init__(self) -> None:
        self._adapters = registry.all()

    def _collect(self, method: str) -> list:
        rows: list = []
        for adapter in self._adapters:
            rows.extend(getattr(adapter, method)())
        return rows

    def _use_demo(self) -> bool:
        return bool(settings.demo_mode)

    def providers(self):
        if self._use_demo():
            from app.data.inventory import MOCK_INVENTORY

            return MOCK_INVENTORY.providers
        from app.db.session import SessionLocal
        from app.platform.presenters import configured_provider_count
        from app.domain.enums import platform_for, regions_for

        session = SessionLocal()
        try:
            from sqlalchemy import select
            from app.db.models import ManagedProviderRow

            types = {
                row.provider_type
                for row in session.scalars(select(ManagedProviderRow).where(ManagedProviderRow.enabled.is_(True)))
            }
            return [
                ProviderRecord(id=item, name=item, platform=platform_for(item), regions=list(regions_for(item)))  # type: ignore[arg-type]
                for item in ("AWS", "Alibaba")
                if item in types
            ]
        finally:
            session.close()

    def regions(self, scope: Scope):
        if self._use_demo():
            return filter_items(self._collect("list_regions"), scope)
        from app.db.session import SessionLocal
        from app.platform.presenters import live_regions

        session = SessionLocal()
        try:
            return live_regions(session, scope)
        finally:
            session.close()

    def accounts(self, scope: Scope):
        if self._use_demo():
            return filter_items(self._collect("list_accounts"), scope)
        from app.db.session import SessionLocal
        from app.platform.presenters import live_accounts

        session = SessionLocal()
        try:
            return live_accounts(session, scope)
        finally:
            session.close()

    def environments(self, scope: Scope):
        if self._use_demo():
            return filter_items(overlay_environment_identities(self._collect("list_environments")), scope)
        from app.db.session import SessionLocal
        from app.platform.presenters import live_environments

        session = SessionLocal()
        try:
            return live_environments(session, scope)
        finally:
            session.close()

    def environment_detail(self, provider, region, environment):
        if self._use_demo():
            record = overlay_environment(registry.get(provider).get_environment(region, environment))
            if record is None:
                return None
            certs = self.certificates(Scope(provider=provider, region=region, environment=environment))
            return apply_environment_certificates(record, certs)
        return _live_environment_detail(provider, region, environment)

    def clusters(self, scope: Scope):
        if self._use_demo():
            return filter_items(overlay_clusters(self._collect("list_clusters")), scope)
        from app.db.session import SessionLocal
        from app.platform.presenters import live_clusters

        session = SessionLocal()
        try:
            return live_clusters(session, scope)
        finally:
            session.close()

    def applications(self, scope: Scope):
        if self._use_demo():
            return filter_items(overlay_applications(self._collect("list_applications")), scope)
        from app.db.session import SessionLocal
        from app.platform.presenters import live_applications

        session = SessionLocal()
        try:
            return live_applications(session, scope)
        finally:
            session.close()

    def certificates(self, scope: Scope):
        from app.services.mappers import annotate_certificate

        if self._use_demo():
            return [annotate_certificate(item) for item in filter_items(overlay_certificates(self._collect("list_certificates")), scope)]
        from app.db.session import SessionLocal
        from app.platform.presenters import live_certificates

        session = SessionLocal()
        try:
            return [annotate_certificate(item) for item in live_certificates(session, scope)]
        finally:
            session.close()

    def secrets(self, scope: Scope):
        from app.services.credentials import overlay_secret_records

        if self._use_demo():
            return filter_items(overlay_secret_records(self._collect("list_secrets")), scope)
        from app.providers.alibaba.secrets import list_live_alibaba_secrets
        from app.providers.aws.secrets import list_live_aws_secrets

        return filter_items(overlay_secret_records(list_live_aws_secrets() + list_live_alibaba_secrets()), scope)

    def health_checks(self, scope: Scope):
        if self._use_demo():
            return filter_items(overlay_health_checks(self._collect("list_health_checks")), scope)
        return filter_items(overlay_health_checks([]), scope)

    def deployments(self, scope: Scope):
        if self._use_demo():
            return filter_items(self._collect("list_deployments"), scope)
        return []

    def pipelines(self, scope: Scope):
        if self._use_demo():
            return filter_items(overlay_pipelines(self._collect("list_pipelines")), scope)
        return filter_items(overlay_pipelines([]), scope)

    def jobs(self, scope: Scope):
        if self._use_demo():
            return filter_items(overlay_jobs(self._collect("list_jobs")), scope)
        from app.db.session import SessionLocal
        from app.platform.presenters import live_jobs

        session = SessionLocal()
        try:
            return live_jobs(session, scope)
        finally:
            session.close()

    def github_runs(self, scope: Scope):
        if self._use_demo():
            return filter_items(overlay_github_runs(self._collect("list_github_runs")), scope)
        return filter_items(overlay_github_runs([]), scope)

    def alerts(self, scope: Scope):
        if self._use_demo():
            return filter_items(overlay_alerts(self._collect("list_alerts")), scope)
        return filter_items(overlay_alerts([]), scope)

    def audit_events(self, scope: Scope):
        from app.services.credentials import overlay_audit_events

        if self._use_demo():
            return filter_items(overlay_pipeline_audit(overlay_github_audit(overlay_certificate_audit(overlay_audit_events(self._collect("list_audit_events"))))), scope)
        return filter_items(overlay_pipeline_audit(overlay_github_audit(overlay_certificate_audit(overlay_audit_events([])))), scope)

    def admin_users(self):
        if self._use_demo():
            from app.data.inventory import MOCK_INVENTORY

            return MOCK_INVENTORY.admin_users
        return []

    def admin_integrations(self):
        if self._use_demo():
            from app.data.inventory import MOCK_INVENTORY

            return MOCK_INVENTORY.admin_integrations
        return []


catalog_service = CatalogService()


def _live_environment_detail(provider, region, environment) -> EnvironmentRecord | None:
    from app.db.repository import InventoryRepository
    from app.db.session import SessionLocal
    from app.domain.models import ActivityItem, EnvironmentAlert, EnvironmentSecret
    from app.platform.presenters import identity_from_row, live_applications, live_clusters
    from app.services.overlay import overlay_environment as overlay_env_unused  # noqa: F401

    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        row = repo.environment_row(provider, region, environment)
        if row is None:
            return None
        identity = identity_from_row(row)
        scope = Scope(provider=provider, region=region, environment=environment)
        record = EnvironmentRecord(
            identity=identity,
            clusters=live_clusters(session, scope),
            applications=live_applications(session, scope),
            secrets=[],
            certificates=[],
            deployments=[],
            pipelines=[],
            github=[],
            health=[],
            audit=[],
            alerts=[],
            recentActivity=[],
        )
        from app.services.overlay import overlay_environment

        record = overlay_environment(record) or record
        certs = catalog_service.certificates(scope)
        return apply_environment_certificates(record, certs)
    finally:
        session.close()


def _empty_kpis() -> KpiSummary:
    return KpiSummary(
        clustersHealthy=0,
        clustersDegraded=0,
        clustersUnreachable=0,
        appsHealthy=0,
        appsDegraded=0,
        certsExpiring14d=0,
        certsHealthy=0,
        certsExpiring60d=0,
        certsExpiring30d=0,
        certsExpiring7d=0,
        certsExpired=0,
        secretsOverdue=0,
        failedDeploys=0,
        githubFailures=0,
        githubWorkflowsRunning=0,
        githubWorkflowsFailed=0,
        githubWorkflowsSucceeded=0,
        pipelineFailures=0,
        pipelineRunsToday=0,
        pipelinesRunning=0,
        pipelinesFailed=0,
        pipelinesFailedPrd=0,
        pipelineAverageDurationSeconds=0,
        openAlerts=0,
    )


def summarize_kpis(rows: list[MatrixRow], scope: Scope) -> KpiSummary:
    summary = _empty_kpis()
    environments: tuple[Environment, ...] = (scope.environment,) if scope.environment else ENVIRONMENTS
    for row in rows:
        if scope.provider and row.provider != scope.provider:
            continue
        if scope.region and row.region != scope.region:
            continue
        for environment in environments:
            cell: CellMetrics = row.cells[environment]
            summary.clustersHealthy += cell.clustersHealthy
            summary.clustersDegraded += cell.clustersDegraded
            summary.clustersUnreachable += cell.clustersUnreachable
            summary.appsHealthy += cell.appsHealthy
            summary.appsDegraded += cell.appsDegraded
            summary.appsUnhealthy += cell.appsUnhealthy
            summary.appsCritical += cell.appsCritical
            summary.certsExpiring14d += cell.certsExpiring14d
            summary.certsHealthy += cell.certsHealthy
            summary.certsExpiring60d += cell.certsExpiring60d
            summary.certsExpiring30d += cell.certsExpiring30d
            summary.certsExpiring7d += cell.certsExpiring7d
            summary.certsExpired += cell.certsExpired
            summary.secretsOverdue += cell.secretsOverdue
            summary.failedDeploys += cell.failedDeploys
            summary.githubFailures += cell.githubFailures
            summary.pipelineFailures += cell.pipelineFailures
            summary.openAlerts += cell.openAlerts
            summary.openIncidents += cell.openIncidents
    return summary


def dashboard_snapshot(scope: Scope, last_synced: str) -> DashboardResponse:
    from app.data.inventory import MOCK_INVENTORY
    from app.db.session import SessionLocal
    from app.platform.presenters import configured_provider_count, data_source, live_matrix
    from app.services.overlay import overlay_matrix

    session = SessionLocal()
    try:
        demo = bool(settings.demo_mode)
        configured = configured_provider_count(session)
        source = data_source(session)
        if demo:
            live_matrix_rows = overlay_matrix(MOCK_INVENTORY.matrix)
            alerts = filter_items(overlay_alerts(MOCK_INVENTORY.alerts), scope)
            dashboard_alerts = [item for item in alerts if item.id != "alert-apac-prd-deploy"]
            failures = filter_items(overlay_pipeline_failures(overlay_github_failures(MOCK_INVENTORY.failures)), scope)
        else:
            live_matrix_rows = live_matrix(session, scope)
            alerts = filter_items(overlay_alerts([]), scope)
            dashboard_alerts = alerts
            failures = filter_items(overlay_pipeline_failures(overlay_github_failures([])), scope)
    finally:
        session.close()
    matrix = [
        row
        for row in live_matrix_rows
        if (not scope.provider or row.provider == scope.provider)
        and (not scope.region or row.region == scope.region)
    ]
    kpis = summarize_kpis(live_matrix_rows, scope)
    certs = catalog_service.certificates(scope)
    kpis = kpis.model_copy(
        update={
            "certsHealthy": sum(1 for item in certs if item.expiryStatus == "HEALTHY"),
            "certsExpiring60d": sum(
                1 for item in certs if item.daysRemaining is not None and 0 < item.daysRemaining <= 60
            ),
            "certsExpiring30d": sum(
                1 for item in certs if item.daysRemaining is not None and 0 < item.daysRemaining <= 30
            ),
            "certsExpiring7d": sum(
                1 for item in certs if item.daysRemaining is not None and 0 < item.daysRemaining <= 7
            ),
            "certsExpired": sum(1 for item in certs if item.expiryStatus == "EXPIRED" or item.daysRemaining <= 0),
        }
    )
    session = None
    try:
        from app.db.session import SessionLocal
        from app.services.github_presenters import overview_dump

        session = SessionLocal()
        overview = overview_dump(session)
        if (
            overview["repositories"]
            or overview["runningWorkflows"]
            or overview["failedWorkflows"]
            or overview["succeededWorkflows"]
        ):
            kpis = kpis.model_copy(
                update={
                    "githubWorkflowsRunning": overview["runningWorkflows"],
                    "githubWorkflowsFailed": overview["failedWorkflows"],
                    "githubWorkflowsSucceeded": overview["succeededWorkflows"],
                    "githubFailures": overview["failedWorkflowsLast24h"] or overview["failedWorkflows"],
                }
            )
    except Exception:
        pass
    finally:
        if session is not None:
            session.close()
    session = None
    try:
        from app.db.session import SessionLocal
        from app.services.pipeline_presenters import overview_dump as pipeline_overview_dump

        session = SessionLocal()
        overview = pipeline_overview_dump(session)
        if overview["pipelineRunsToday"] or overview["runningPipelines"] or overview["failedPipelines"]:
            kpis = kpis.model_copy(
                update={
                    "pipelineRunsToday": overview["pipelineRunsToday"],
                    "pipelinesRunning": overview["runningPipelines"],
                    "pipelinesFailed": overview["failedPipelines"],
                    "pipelinesFailedPrd": overview["failedPrdPipelines"],
                    "pipelineAverageDurationSeconds": overview["averageDeploymentDurationSeconds"],
                    "pipelineFailures": overview["failedPipelines"],
                }
            )
    except Exception:
        pass
    finally:
        if session is not None:
            session.close()
    session = None
    try:
        from app.db.session import SessionLocal
        from app.services.health_presenters import overview_dump as health_overview_dump

        session = SessionLocal()
        overview = health_overview_dump(session)
        if overview["applications"] or overview["openIncidents"]:
            kpis = kpis.model_copy(
                update={
                    "appsHealthy": overview["healthyApplications"],
                    "appsDegraded": overview["degradedApplications"],
                    "appsUnhealthy": overview["unhealthyApplications"],
                    "appsCritical": overview["criticalApplications"],
                    "openIncidents": overview["openIncidents"],
                    "unhealthyClusters": overview["unhealthyClusters"],
                }
            )
    except Exception:
        pass
    finally:
        if session is not None:
            session.close()
    session = None
    try:
        from sqlalchemy import select as sa_select

        from app.alerting.models import AlertStatus
        from app.alerting.presenters import kpi_counts
        from app.db.models import AlertRow
        from app.db.session import SessionLocal

        session = SessionLocal()
        rows = list(session.scalars(sa_select(AlertRow)))
        counts = kpi_counts(rows)
        live_open = sum(1 for row in rows if row.status in {AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED})
        kpis = kpis.model_copy(
            update={
                "openAlerts": max(kpis.openAlerts, live_open),
                "criticalAlerts": counts["critical"],
                "prdCriticalAlerts": counts["prdCritical"],
                "acknowledgedAlerts": counts["acknowledged"],
            }
        )
    except Exception:
        pass
    finally:
        if session is not None:
            session.close()
    return DashboardResponse(
        lastSynced=last_synced,
        kpis=kpis,
        matrix=matrix,
        alerts=dashboard_alerts,
        failures=failures,
        demoMode=demo,
        dataSource=source,
        onboarding=not demo and configured == 0,
        configuredProviders=configured,
    )
