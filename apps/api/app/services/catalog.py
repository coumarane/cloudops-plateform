from collections.abc import Sequence

from app.domain.enums import ENVIRONMENTS, Environment
from app.domain.models import CellMetrics, DashboardResponse, KpiSummary, MatrixRow, OperationalAlert, RecentFailure, Scope
from app.providers.registry import registry
from app.services.overlay import (
    overlay_certificates,
    overlay_clusters,
    overlay_environment,
    overlay_environment_identities,
    overlay_jobs,
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

    def providers(self):
        from app.data.inventory import MOCK_INVENTORY

        return MOCK_INVENTORY.providers

    def regions(self, scope: Scope):
        return filter_items(self._collect("list_regions"), scope)

    def accounts(self, scope: Scope):
        return filter_items(self._collect("list_accounts"), scope)

    def environments(self, scope: Scope):
        return filter_items(overlay_environment_identities(self._collect("list_environments")), scope)

    def environment_detail(self, provider, region, environment):
        record = registry.get(provider).get_environment(region, environment)
        return overlay_environment(record)

    def clusters(self, scope: Scope):
        return filter_items(overlay_clusters(self._collect("list_clusters")), scope)

    def applications(self, scope: Scope):
        return filter_items(self._collect("list_applications"), scope)

    def certificates(self, scope: Scope):
        return filter_items(overlay_certificates(self._collect("list_certificates")), scope)

    def secrets(self, scope: Scope):
        from app.services.credentials import overlay_secret_records

        return filter_items(overlay_secret_records(self._collect("list_secrets")), scope)

    def health_checks(self, scope: Scope):
        return filter_items(self._collect("list_health_checks"), scope)

    def deployments(self, scope: Scope):
        return filter_items(self._collect("list_deployments"), scope)

    def pipelines(self, scope: Scope):
        return filter_items(self._collect("list_pipelines"), scope)

    def jobs(self, scope: Scope):
        return filter_items(overlay_jobs(self._collect("list_jobs")), scope)

    def github_runs(self, scope: Scope):
        return filter_items(self._collect("list_github_runs"), scope)

    def alerts(self, scope: Scope):
        return filter_items(self._collect("list_alerts"), scope)

    def audit_events(self, scope: Scope):
        from app.services.credentials import overlay_audit_events

        return filter_items(overlay_audit_events(self._collect("list_audit_events")), scope)

    def admin_users(self):
        from app.data.inventory import MOCK_INVENTORY

        return MOCK_INVENTORY.admin_users

    def admin_integrations(self):
        from app.data.inventory import MOCK_INVENTORY

        return MOCK_INVENTORY.admin_integrations


catalog_service = CatalogService()


def _empty_kpis() -> KpiSummary:
    return KpiSummary(
        clustersHealthy=0,
        clustersDegraded=0,
        clustersUnreachable=0,
        appsHealthy=0,
        appsDegraded=0,
        certsExpiring14d=0,
        secretsOverdue=0,
        failedDeploys=0,
        githubFailures=0,
        pipelineFailures=0,
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
            summary.certsExpiring14d += cell.certsExpiring14d
            summary.secretsOverdue += cell.secretsOverdue
            summary.failedDeploys += cell.failedDeploys
            summary.githubFailures += cell.githubFailures
            summary.pipelineFailures += cell.pipelineFailures
            summary.openAlerts += cell.openAlerts
    return summary


def dashboard_snapshot(scope: Scope, last_synced: str) -> DashboardResponse:
    from app.data.inventory import MOCK_INVENTORY
    from app.services.overlay import overlay_matrix

    live_matrix = overlay_matrix(MOCK_INVENTORY.matrix)
    matrix = [
        row
        for row in live_matrix
        if (not scope.provider or row.provider == scope.provider)
        and (not scope.region or row.region == scope.region)
    ]
    alerts = filter_items(MOCK_INVENTORY.alerts, scope)
    # Dashboard feed uses the four primary operational alerts, not the extra APAC deploy card.
    dashboard_alerts = [item for item in alerts if item.id != "alert-apac-prd-deploy"]
    failures = filter_items(MOCK_INVENTORY.failures, scope)
    return DashboardResponse(
        lastSynced=last_synced,
        kpis=summarize_kpis(live_matrix, scope),
        matrix=matrix,
        alerts=dashboard_alerts,
        failures=failures,
    )
