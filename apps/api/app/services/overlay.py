from __future__ import annotations

from sqlalchemy import select

from app.core.logging import get_logger
from app.db.models import CertificateAlertRow, CloudEnvironmentRow, GithubAlertRow, GithubWorkflowRunRow, PipelineAlertRow, PipelineRunRow
from app.db.repository import InventoryRepository
from app.db.session import SessionLocal
from app.domain.models import (
    ApplicationRecord,
    CertificateRecord,
    ClusterRecord,
    EnvironmentCertificate,
    EnvironmentIdentity,
    EnvironmentRecord,
    MatrixRow,
    OperationalAlert,
    RunRecord,
)
from app.providers.common.certificates import CRITICAL, EXPIRED, HEALTHY, URGENT, WARNING, classify_expiry
from app.services.mappers import annotate_certificate, to_certificate_record, to_cluster_record, to_health_record, to_job_record, _age
from app.topology.models import environment_slug

logger = get_logger(__name__)


def _scope_key(row: CloudEnvironmentRow) -> tuple[str, str, str]:
    return (row.provider, row.platform_region, row.environment)


def _identity_from_row(identity: EnvironmentIdentity, row: CloudEnvironmentRow) -> EnvironmentIdentity:
        source = identity.source
        if row.discovery_active:
            source = "alibaba" if row.provider == "Alibaba" else "aws"
        return identity.model_copy(
            update={
                "account": row.account_alias,
                "cloudRegion": row.cloud_region,
                "readonly": row.readonly,
                "source": source,
                "lastSuccessfulScan": row.last_successful_scan_at.isoformat() if row.last_successful_scan_at else None,
                "lastError": row.last_error or None,
                "discoveryActive": row.discovery_active,
                "awsAccountId": None,
            }
        )


def overlay_environment_identities(items: list[EnvironmentIdentity]) -> list[EnvironmentIdentity]:
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        by_key = {_scope_key(row): row for row in repo.list_environment_rows()}
        updated: list[EnvironmentIdentity] = []
        for item in items:
            row = by_key.get((item.provider, item.region, item.environment))
            updated.append(_identity_from_row(item, row) if row else item)
        return updated
    except Exception:
        logger.exception("Environment identity overlay unavailable")
        return items
    finally:
        session.close()


def overlay_clusters(items: list[ClusterRecord]) -> list[ClusterRecord]:
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        live_scopes = repo.live_discovery_scopes()
        if not live_scopes:
            return items
        live = [
            to_cluster_record(cluster, repo.get_health(cluster.id))
            for cluster in repo.present_clusters()
            if (cluster.provider, cluster.platform_region, cluster.environment) in live_scopes
        ]
        kept = [item for item in items if (item.provider, item.region, item.environment) not in live_scopes]
        return kept + live
    except Exception:
        logger.exception("Live cluster overlay unavailable; using mock data")
        return items
    finally:
        session.close()


def _alert_status_map(session) -> dict[str, str]:
    from sqlalchemy import select

    mapping: dict[str, str] = {}
    for alert in session.scalars(
        select(CertificateAlertRow).where(CertificateAlertRow.status.in_(("OPEN", "ACKNOWLEDGED")))
    ):
        mapping[alert.certificate_id] = alert.status
    return mapping


def overlay_certificates(items: list[CertificateRecord]) -> list[CertificateRecord]:
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        live_scopes = repo.live_certificate_scopes()
        annotated = [annotate_certificate(item) for item in items]
        if not live_scopes:
            return annotated
        env_rows = repo.list_environment_rows()
        envs_by_account: dict[str, list[CloudEnvironmentRow]] = {}
        for row in env_rows:
            envs_by_account.setdefault(row.account_alias, []).append(row)
        alerts = _alert_status_map(session)
        live: list[CertificateRecord] = []
        for row in repo.present_certificates():
            record = to_certificate_record(row, alert_status=alerts.get(row.id))
            targets = envs_by_account.get(row.account_alias, [])
            if row.environment:
                targets = [item for item in targets if item.environment == row.environment]
            for env in targets:
                if (env.provider, env.platform_region, env.environment) not in live_scopes:
                    continue
                copied = record.model_copy(
                    update={
                        "environment": env.environment,
                        "region": env.platform_region,
                        "id": f"{record.id}-{environment_slug(env.environment)}" if len(targets) > 1 else record.id,
                    }
                )
                live.append(copied)
        kept = [
            item
            for item in annotated
            if (item.provider, item.region, item.environment)
            not in {(cert.provider, cert.region, cert.environment) for cert in live}
        ]
        return kept + live
    except Exception:
        logger.exception("Live certificate overlay unavailable; using mock data")
        return [annotate_certificate(item) for item in items]
    finally:
        session.close()


def overlay_jobs(items: list[RunRecord]) -> list[RunRecord]:
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        live = [to_job_record(row) for row in repo.list_jobs()]
        return live + items
    except Exception:
        logger.exception("Live job overlay unavailable; using mock data")
        return items
    finally:
        session.close()


def apply_environment_certificates(
    record: EnvironmentRecord, certs: list[CertificateRecord]
) -> EnvironmentRecord:
    env_certs = [
        EnvironmentCertificate(
            name=item.domain,
            daysToExpiry=item.daysRemaining if item.daysRemaining is not None else 0,
            status=item.expiryStatus or item.status or classify_expiry(item.daysRemaining),
            source=item.source,
            issuer=item.issuer,
        )
        for item in certs
    ]
    statuses = [item.status for item in env_certs]
    warning = sum(1 for status in statuses if status == WARNING)
    critical = sum(1 for status in statuses if status in {CRITICAL, URGENT, EXPIRED})
    if critical:
        cert_status = "Critical"
    elif warning:
        cert_status = "Warning"
    else:
        cert_status = "Healthy"
    identity = record.identity.model_copy(
        update={
            "certificateStatus": cert_status,
            "certificateTotal": len(env_certs),
            "certificateWarning": warning,
            "certificateCritical": critical,
        }
    )
    return record.model_copy(update={"identity": identity, "certificates": env_certs})


def overlay_environment(record: EnvironmentRecord | None) -> EnvironmentRecord | None:
    if record is None:
        return record
    original = record
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        env_row = repo.environment_row(record.identity.provider, record.identity.region, record.identity.environment)
        if env_row is None:
            return record
        updated = record.model_copy(deep=True)
        updated.identity = _identity_from_row(record.identity, env_row)
        if env_row.discovery_active:
            updated.clusters = [
                to_cluster_record(cluster, repo.get_health(cluster.id))
                for cluster in repo.present_clusters_for(env_row.platform_region, env_row.environment)
                if cluster.provider == env_row.provider
            ]
        if env_row.last_certificate_scan_at is not None:
            certs = [
                to_certificate_record(row)
                for row in repo.present_certificates_for_account(env_row.account_alias)
                if not row.environment or row.environment == env_row.environment
            ]
            if certs:
                updated = apply_environment_certificates(updated, certs)
        github_items = []
        from app.domain.models import ActivityItem
        from app.services.github_presenters import apply_source_control, to_run_record
        from app.services.pipeline_presenters import apply_pipeline, to_activity, to_run_record as to_pipeline_run_record

        for run in session.scalars(select(GithubWorkflowRunRow).order_by(GithubWorkflowRunRow.started_at.desc())):
            github_run = to_run_record(session, run)
            if (
                github_run.provider == updated.identity.provider
                and github_run.region == updated.identity.region
                and github_run.environment == updated.identity.environment
            ):
                github_items.append(
                    ActivityItem(title=github_run.name, detail=github_run.detail, age=github_run.age, href=github_run.href)
                )
            if len(github_items) >= 8:
                break
        if github_items:
            updated = updated.model_copy(update={"github": github_items})
        pipeline_items = []
        for run in session.scalars(select(PipelineRunRow).order_by(PipelineRunRow.started_at.desc())):
            run_record = to_pipeline_run_record(session, run)
            if (
                run_record.provider == updated.identity.provider
                and run_record.region == updated.identity.region
                and run_record.environment == updated.identity.environment
            ):
                pipeline_items.append(to_activity(session, run))
            if len(pipeline_items) >= 8:
                break
        applications = [apply_pipeline(session, apply_source_control(session, app)) for app in updated.applications]
        applications = [apply_health(session, app) for app in applications]
        patch: dict = {"applications": applications}
        if pipeline_items:
            patch["pipelines"] = pipeline_items
        health_items = _environment_health_activity(session, updated.identity.provider, updated.identity.region, updated.identity.environment)
        if health_items:
            patch["health"] = health_items
        identity_health = _environment_identity_health(session, updated.identity.provider, updated.identity.region, updated.identity.environment)
        if identity_health:
            patch["identity"] = updated.identity.model_copy(update=identity_health)
        from app.alerting.models import AlertStatus, AlertSeverity
        from app.db.models import AlertRow, MaintenanceWindowRow
        from app.alerting.suppression import _aware
        from app.db.repository import utcnow
        from app.domain.models import EnvironmentAlertsSummary, EnvironmentMaintenanceWindow

        scoped_alerts = [
            row
            for row in session.scalars(select(AlertRow))
            if (row.provider or "").lower() == updated.identity.provider.lower()
            and (row.region or "").lower() == updated.identity.region.lower()
            and (row.environment or "").upper() == updated.identity.environment
        ]
        patch["alertsSummary"] = EnvironmentAlertsSummary(
            openAlerts=sum(1 for row in scoped_alerts if row.status == AlertStatus.OPEN),
            criticalAlerts=sum(1 for row in scoped_alerts if row.status in {AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED} and (row.severity or "").upper() == AlertSeverity.CRITICAL),
            highAlerts=sum(1 for row in scoped_alerts if row.status in {AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED} and (row.severity or "").upper() == "HIGH"),
            acknowledgedAlerts=sum(1 for row in scoped_alerts if row.status == AlertStatus.ACKNOWLEDGED),
        )
        now = utcnow()
        window = None
        for item in session.scalars(select(MaintenanceWindowRow).where(MaintenanceWindowRow.enabled.is_(True))):
            if _aware(item.starts_at) <= now <= _aware(item.ends_at):
                if item.provider and item.provider.lower() != updated.identity.provider.lower():
                    continue
                if item.region and item.region.lower() != updated.identity.region.lower():
                    continue
                if item.environment and item.environment.upper() != updated.identity.environment:
                    continue
                window = item
                break
        if window is not None:
            patch["maintenanceWindow"] = EnvironmentMaintenanceWindow(
                id=window.id,
                name=window.name,
                startsAt=window.starts_at.isoformat(),
                endsAt=window.ends_at.isoformat(),
                reason=window.reason,
                changeTicket=window.change_ticket,
            )
        return updated.model_copy(update=patch)
    except Exception:
        logger.exception("Live environment overlay unavailable; using mock data")
        return original
    finally:
        session.close()


def overlay_matrix(rows: list[MatrixRow]) -> list[MatrixRow]:
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        env_rows = repo.list_environment_rows()
        if not env_rows:
            return rows
        live_clusters = repo.present_clusters()
        health_by_scope: dict[tuple[str, str, str], list] = {}
        for cluster in live_clusters:
            key = (cluster.provider, cluster.platform_region, cluster.environment)
            health_by_scope.setdefault(key, []).append(cluster)
        certs_by_account = {}
        for cert in repo.present_certificates():
            certs_by_account.setdefault(cert.account_alias, []).append(cert)
        env_by_key = {_scope_key(row): row for row in env_rows}
        patched: list[MatrixRow] = []
        for row in rows:
            cells = dict(row.cells)
            changed = False
            for environment, current in cells.items():
                env_row = env_by_key.get((row.provider, row.region, environment))
                if env_row is None:
                    continue
                next_cell = current
                if env_row.discovery_active:
                    scoped = health_by_scope.get((row.provider, row.region, environment), [])
                    healthy = degraded = unreachable = 0
                    for cluster in scoped:
                        status = to_cluster_record(cluster, repo.get_health(cluster.id)).status
                        if status == "Unreachable":
                            unreachable += 1
                        elif status == "Degraded":
                            degraded += 1
                        else:
                            healthy += 1
                    next_cell = next_cell.model_copy(
                        update={
                            "clustersHealthy": healthy,
                            "clustersDegraded": degraded,
                            "clustersUnreachable": unreachable,
                            "live": True,
                        }
                    )
                    changed = True
                if env_row.last_certificate_scan_at is not None:
                    certs = certs_by_account.get(env_row.account_alias, [])
                    scoped = [
                        item
                        for item in certs
                        if not item.environment or item.environment == environment
                    ]
                    if scoped:
                        expiring14 = [
                            item
                            for item in scoped
                            if item.days_remaining is not None and 0 < item.days_remaining <= 14
                        ]
                        statuses = [(item.expiry_status or classify_expiry(item.days_remaining)) for item in scoped]
                        next_cert = min(
                            (
                                item.days_remaining
                                for item in scoped
                                if item.days_remaining is not None and item.days_remaining >= 0
                            ),
                            default=current.nextCertExpiryDays,
                        )
                        next_cell = next_cell.model_copy(
                            update={
                                "certsExpiring14d": len(expiring14),
                                "certsHealthy": sum(1 for status in statuses if status == HEALTHY),
                                "certsExpiring60d": sum(
                                    1
                                    for item in scoped
                                    if item.days_remaining is not None and 0 < item.days_remaining <= 60
                                ),
                                "certsExpiring30d": sum(
                                    1
                                    for item in scoped
                                    if item.days_remaining is not None and 0 < item.days_remaining <= 30
                                ),
                                "certsExpiring7d": sum(
                                    1
                                    for item in scoped
                                    if item.days_remaining is not None and 0 < item.days_remaining <= 7
                                ),
                                "certsExpired": sum(1 for status in statuses if status == EXPIRED),
                                "nextCertExpiryDays": next_cert,
                                "live": True,
                            }
                        )
                        changed = True
                if env_row.last_error or env_row.readonly:
                    next_cell = next_cell.model_copy(
                        update={"lastError": env_row.last_error or None, "readonly": env_row.readonly}
                    )
                    changed = True
                github_failed = [
                    run
                    for run in _github_runs_by_scope(session).get((row.provider, row.region, environment), [])
                    if run.status == "FAILED"
                ]
                if github_failed:
                    next_cell = next_cell.model_copy(update={"githubFailures": len(github_failed), "live": True})
                    changed = True
                pipeline_failed = [
                    run
                    for run in _pipeline_runs_by_scope(session).get((row.provider, row.region, environment), [])
                    if run.status == "FAILED"
                ]
                if pipeline_failed:
                    next_cell = next_cell.model_copy(update={"pipelineFailures": len(pipeline_failed), "live": True})
                    changed = True
                health = _health_by_scope(session).get((row.provider, row.region, environment))
                if health:
                    next_cell = next_cell.model_copy(update={**health, "live": True})
                    changed = True
                cells[environment] = next_cell
            patched.append(
                MatrixRow(provider=row.provider, platform=row.platform, region=row.region, cells=cells)
                if changed
                else row
            )
        return patched
    except Exception:
        logger.exception("Live dashboard overlay unavailable; using mock data")
        return rows
    finally:
        session.close()


def overlay_alerts(items: list[OperationalAlert]) -> list[OperationalAlert]:
    session = SessionLocal()
    try:
        from sqlalchemy import select

        from app.alerting.models import AlertStatus
        from app.alerting.presenters import alert_dump
        from app.db.models import AlertRow
        from app.services.certificate_monitor import to_operational_alert
        from app.services.github_presenters import to_github_alert

        live_central = []
        for row in session.scalars(select(AlertRow).where(AlertRow.status.in_((AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED, AlertStatus.SUPPRESSED)))):
            payload = alert_dump(row)
            try:
                live_central.append(
                    OperationalAlert(
                        id=payload["id"],
                        severity=payload["uiSeverity"],  # type: ignore[arg-type]
                        title=payload["title"],
                        objectName=payload["objectName"],
                        provider=payload["provider"],  # type: ignore[arg-type]
                        region=payload["region"],  # type: ignore[arg-type]
                        environment=payload["environment"],  # type: ignore[arg-type]
                        age=payload["age"],
                        href=payload["href"],
                    )
                )
            except Exception:
                continue
        live = [
            to_operational_alert(row)
            for row in session.scalars(
                select(CertificateAlertRow).where(CertificateAlertRow.status.in_(("OPEN", "ACKNOWLEDGED")))
            )
        ]
        github_live = [
            to_github_alert(session, row)
            for row in session.scalars(select(GithubAlertRow).where(GithubAlertRow.status == "OPEN"))
        ]
        from app.services.pipeline_presenters import to_pipeline_alert

        pipeline_live = [
            to_pipeline_alert(session, row)
            for row in session.scalars(select(PipelineAlertRow).where(PipelineAlertRow.status == "OPEN"))
        ]
        from app.db.models import HealthAlertRow
        from app.services.health_presenters import to_health_alert

        health_live = [
            to_health_alert(session, row)
            for row in session.scalars(select(HealthAlertRow).where(HealthAlertRow.status == "OPEN"))
        ]
        return live_central + health_live + pipeline_live + github_live + live + items
    except Exception:
        logger.exception("Live certificate alert overlay unavailable")
        return items
    finally:
        session.close()


def overlay_certificate_audit(items):
    session = SessionLocal()
    try:
        from sqlalchemy import select

        from app.db.models import CertificateAuditRow
        from app.domain.models import AuditEvent
        from app.services.mappers import _age

        live = [
            AuditEvent(
                id=row.id,
                event=row.action.replace("_", " ").title(),
                actor=row.actor,
                objectName=row.certificate_id or "certificates",
                detail=row.detail,
                age=_age(row.created_at),
                provider=row.provider or "AWS",  # type: ignore[arg-type]
                region=row.platform_region or "EMEA",  # type: ignore[arg-type]
                environment=row.environment or "DEV",  # type: ignore[arg-type]
            )
            for row in session.scalars(select(CertificateAuditRow).order_by(CertificateAuditRow.created_at.desc()))
        ]
        return live + items
    except Exception:
        logger.exception("Live certificate audit overlay unavailable")
        return items
    finally:
        session.close()


def _github_runs_by_scope(session) -> dict[tuple[str, str, str], list]:
    from app.services.github_presenters import environment_label

    grouped: dict[tuple[str, str, str], list] = {}
    for run in session.scalars(select(GithubWorkflowRunRow)):
        label = environment_label(session, run.cloudops_environment_id)
        provider = label.get("provider")
        region = label.get("region")
        environment = label.get("environment")
        if not provider or not region or not environment:
            continue
        grouped.setdefault((provider, region, environment), []).append(run)
    return grouped


def _pipeline_runs_by_scope(session) -> dict[tuple[str, str, str], list]:
    from app.services.github_presenters import environment_label

    grouped: dict[tuple[str, str, str], list] = {}
    for run in session.scalars(select(PipelineRunRow)):
        label = environment_label(session, run.environment_id)
        provider = label.get("provider")
        region = label.get("region")
        environment = label.get("environment")
        if not provider or not region or not environment:
            continue
        grouped.setdefault((provider, region, environment), []).append(run)
    return grouped


def overlay_pipelines(items: list[RunRecord]) -> list[RunRecord]:
    session = SessionLocal()
    try:
        from app.services.pipeline_presenters import to_run_record

        live = [to_run_record(session, row) for row in session.scalars(select(PipelineRunRow))]
        if not live:
            return items
        return live
    except Exception:
        logger.exception("Live pipeline overlay unavailable; using mock data")
        return items
    finally:
        session.close()


def overlay_pipeline_failures(items):
    session = SessionLocal()
    try:
        from app.integrations.pipelines.status import FAILED
        from app.services.pipeline_presenters import to_recent_failure

        live = [
            to_recent_failure(session, row)
            for row in session.scalars(select(PipelineRunRow).where(PipelineRunRow.status == FAILED))
        ]
        live = sorted(live, key=lambda item: item.age)
        return live + items
    except Exception:
        logger.exception("Live pipeline failure overlay unavailable")
        return items
    finally:
        session.close()


def overlay_pipeline_audit(items):
    session = SessionLocal()
    try:
        from app.db.models import PipelineAuditRow
        from app.services.pipeline_presenters import to_pipeline_audit

        live = [
            to_pipeline_audit(row)
            for row in session.scalars(select(PipelineAuditRow).order_by(PipelineAuditRow.created_at.desc()))
        ]
        return live + items
    except Exception:
        logger.exception("Live pipeline audit overlay unavailable")
        return items
    finally:
        session.close()


def overlay_github_runs(items: list[RunRecord]) -> list[RunRecord]:
    session = SessionLocal()
    try:
        from app.services.github_presenters import to_run_record

        live = [to_run_record(session, row) for row in session.scalars(select(GithubWorkflowRunRow))]
        if not live:
            return items
        return live
    except Exception:
        logger.exception("Live GitHub run overlay unavailable; using mock data")
        return items
    finally:
        session.close()


def overlay_github_failures(items):
    session = SessionLocal()
    try:
        from app.integrations.github.mapper import FAILED
        from app.services.github_presenters import to_recent_failure

        live = [
            to_recent_failure(session, row)
            for row in session.scalars(select(GithubWorkflowRunRow).where(GithubWorkflowRunRow.status == FAILED))
        ]
        live = sorted(live, key=lambda item: item.age)
        return live + items
    except Exception:
        logger.exception("Live GitHub failure overlay unavailable")
        return items
    finally:
        session.close()


def overlay_applications(items: list[ApplicationRecord]) -> list[ApplicationRecord]:
    session = SessionLocal()
    try:
        from app.services.github_presenters import apply_source_control
        from app.services.pipeline_presenters import apply_pipeline

        return [apply_health(session, apply_pipeline(session, apply_source_control(session, item))) for item in items]
    except Exception:
        logger.exception("Application source-control overlay unavailable")
        return items
    finally:
        session.close()


def overlay_github_audit(items):
    session = SessionLocal()
    try:
        from app.db.models import GithubAuditRow
        from app.services.github_presenters import to_github_audit

        live = [
            to_github_audit(row)
            for row in session.scalars(select(GithubAuditRow).order_by(GithubAuditRow.created_at.desc()))
        ]
        from app.db.models import HealthAuditRow
        from app.domain.models import AuditEvent
        from app.services.mappers import _age

        health_live = [
            AuditEvent(
                id=row.id,
                event=row.action.replace("_", " ").title(),
                actor=row.actor,
                objectName=row.object_name or "health",
                detail=row.detail,
                age=_age(row.created_at),
                provider="AWS",
                region="EMEA",
                environment="DEV",
            )
            for row in session.scalars(select(HealthAuditRow).order_by(HealthAuditRow.created_at.desc()))
        ]
        return health_live + live + items
    except Exception:
        logger.exception("Live GitHub audit overlay unavailable")
        return items
    finally:
        session.close()


def _health_by_scope(session) -> dict[tuple[str, str, str], dict]:
    from app.db.models import ApplicationHealthRow, HealthIncidentRow, ResourceHealthRow
    from app.integrations.health.status import CRITICAL, DEGRADED, HEALTHY, UNHEALTHY

    grouped: dict[tuple[str, str, str], dict] = {}
    apps = list(session.scalars(select(ApplicationHealthRow)))
    if not apps:
        return grouped
    for row in apps:
        key = (row.provider, row.region, row.environment)
        bucket = grouped.setdefault(
            key,
            {
                "appsHealthy": 0,
                "appsDegraded": 0,
                "appsUnhealthy": 0,
                "appsCritical": 0,
                "openIncidents": 0,
                "unhealthyClusters": 0,
            },
        )
        if row.status == HEALTHY:
            bucket["appsHealthy"] += 1
        elif row.status == DEGRADED:
            bucket["appsDegraded"] += 1
        elif row.status == UNHEALTHY:
            bucket["appsUnhealthy"] += 1
        elif row.status == CRITICAL:
            bucket["appsCritical"] += 1
    for incident in session.scalars(select(HealthIncidentRow).where(HealthIncidentRow.status.in_(("OPEN", "ACKNOWLEDGED")))):
        key = (incident.provider, incident.region, incident.environment)
        if key in grouped:
            grouped[key]["openIncidents"] += 1
        elif incident.provider and incident.region and incident.environment:
            grouped[key] = {
                "appsHealthy": 0,
                "appsDegraded": 0,
                "appsUnhealthy": 0,
                "appsCritical": 0,
                "openIncidents": 1,
                "unhealthyClusters": 0,
            }
    for cluster in session.scalars(select(ResourceHealthRow).where(ResourceHealthRow.resource_type == "cluster")):
        key = (cluster.provider, cluster.region, cluster.environment)
        if cluster.status in {UNHEALTHY, CRITICAL} and key in grouped:
            grouped[key]["unhealthyClusters"] = grouped[key].get("unhealthyClusters", 0) + 1
    return grouped


def apply_health(session, item: ApplicationRecord) -> ApplicationRecord:
    from app.db.models import ApplicationHealthRow
    from app.integrations.health.status import CRITICAL, DEGRADED, HEALTHY, UNHEALTHY

    row = session.scalar(
        select(ApplicationHealthRow).where(
            ApplicationHealthRow.application_id == item.id,
        )
    )
    if row is None:
        row = session.scalar(
            select(ApplicationHealthRow).where(
                ApplicationHealthRow.application_name == item.name,
                ApplicationHealthRow.environment == item.environment,
            )
        )
    if row is None:
        return item
    issue = item.issue
    if row.status == HEALTHY:
        issue = "Healthy"
    elif row.status == DEGRADED:
        issue = "Degraded"
    elif row.status == UNHEALTHY:
        issue = "Unhealthy"
    elif row.status == CRITICAL:
        issue = "Critical"
    return item.model_copy(
        update={
            "healthStatus": row.status,
            "healthSummary": row.summary,
            "likelyCause": row.likely_cause or None,
            "issue": issue,
        }
    )


def overlay_health_checks(items):
    session = SessionLocal()
    try:
        from app.db.models import HealthCheckResultRow
        from app.services.health_presenters import to_health_check_record

        live = [to_health_check_record(session, row) for row in session.scalars(select(HealthCheckResultRow))]
        if not live:
            return items
        return live
    except Exception:
        logger.exception("Live health-check overlay unavailable; using mock data")
        return items
    finally:
        session.close()


def _environment_health_activity(session, provider: str, region: str, environment: str):
    from app.db.models import HealthIncidentRow, HealthTimelineEventRow
    from app.domain.models import ActivityItem

    items = []
    for incident in session.scalars(select(HealthIncidentRow).order_by(HealthIncidentRow.opened_at.desc())):
        if incident.provider == provider and incident.region == region and incident.environment == environment:
            items.append(
                ActivityItem(
                    title=f"Incident {incident.status}",
                    detail=incident.root_symptom,
                    age=_age(incident.opened_at) if incident.opened_at else "",
                    href=f"/health-checks?incident={incident.id}",
                )
            )
        if len(items) >= 8:
            break
    if items:
        return items
    for event in session.scalars(select(HealthTimelineEventRow).order_by(HealthTimelineEventRow.created_at.desc())):
        items.append(ActivityItem(title=event.title, detail=event.detail, age=_age(event.created_at), href=event.href or "/health-checks"))
        if len(items) >= 8:
            break
    return items


def _environment_identity_health(session, provider: str, region: str, environment: str) -> dict:
    from app.db.models import ApplicationHealthRow, HealthIncidentRow, PipelineRunRow
    from app.integrations.health.status import CRITICAL, DEGRADED, HEALTHY, UNHEALTHY, worst
    from app.integrations.pipelines.status import FAILED

    apps = [
        row
        for row in session.scalars(select(ApplicationHealthRow))
        if row.provider == provider and row.region == region and row.environment == environment
    ]
    if not apps:
        return {}
    overall = worst(*(row.status for row in apps))
    incidents = [
        row
        for row in session.scalars(select(HealthIncidentRow).where(HealthIncidentRow.status.in_(("OPEN", "ACKNOWLEDGED"))))
        if row.provider == provider and row.region == region and row.environment == environment
    ]
    failed_pipelines = [
        row
        for row in _pipeline_runs_by_scope(session).get((provider, region, environment), [])
        if row.status == FAILED
    ]
    return {
        "overallHealth": overall,
        "appsTotal": len(apps),
        "appsHealthyCount": sum(1 for row in apps if row.status == HEALTHY),
        "appsDegradedCount": sum(1 for row in apps if row.status == DEGRADED),
        "appsUnhealthyCount": sum(1 for row in apps if row.status == UNHEALTHY),
        "appsCriticalCount": sum(1 for row in apps if row.status == CRITICAL),
        "openIncidents": len(incidents),
        "pipelinesFailedRecently": len(failed_pipelines),
    }


def load_cluster_detail(cluster_id: str):
    session = SessionLocal()
    try:
        repo = InventoryRepository(session)
        cluster = repo.get_cluster(cluster_id)
        if cluster is None or not cluster.present:
            return None, None
        health = repo.get_health(cluster_id)
        health_record = to_health_record(cluster, health) if health else None
        return to_cluster_record(cluster, health), health_record
    except Exception:
        logger.exception("Live cluster detail unavailable")
        return None, None
    finally:
        session.close()
