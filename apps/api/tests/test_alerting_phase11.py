from datetime import timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.alerting.deduplication import fingerprint
from app.alerting.escalation import due_for_escalation
from app.alerting.models import AlertSignal, AlertSeverity, AlertStatus, DeliveryStatus, FailureClass, NotificationType
from app.alerting.routing import matching_routes
from app.alerting.rules import rule_allows_notification, rule_matches, select_rule
from app.alerting.service import (
    acknowledge_alert,
    ensure_defaults,
    publish,
    resolve_alert,
    run_escalation,
    suppress_alert,
)
from app.alerting.suppression import active_maintenance, active_suppression
from app.core.rbac import ROLE_PERMISSIONS
from app.core.security import walk_strings
from app.db.models import (
    AlertRow,
    AlertRuleRow,
    AlertRoutingRuleRow,
    MaintenanceWindowRow,
    NotificationDeliveryRow,
    NotificationDestinationRow,
)
from app.db.repository import utcnow
from app.db.session import SessionLocal
from app.main import app
from app.notifications.base import NotificationProvider
from app.notifications.dispatcher import dispatch_pending, register_test_provider
from app.notifications.exceptions import TemporaryNotificationError
from app.notifications.models import NotificationMessage
from app.secrets.backends.local import LocalDevSecretBackend

client = TestClient(app)


def _headers(role: str = "PlatformAdmin", user: str = "ops@cloudops.local") -> dict[str, str]:
    return {"X-CloudOps-User": user, "X-CloudOps-Role": role}


def _signal(**overrides) -> AlertSignal:
    payload = dict(
        alert_type="APPLICATION_UNHEALTHY",
        source_type="application",
        source_id="payments-api",
        title="payments-api unhealthy",
        summary="HTTP endpoint unavailable",
        severity=AlertSeverity.CRITICAL,
        provider="AWS",
        region="EMEA",
        environment_id="aws-emea-prd",
        environment="PRD",
        application_id="payments-api",
    )
    payload.update(overrides)
    return AlertSignal(**payload)


class RecordingProvider(NotificationProvider):
    name = "log"

    def __init__(self, *, fail: Exception | None = None, name: str = "log"):
        self.name = name
        self.fail = fail
        self.sent: list[NotificationMessage] = []

    def send(self, message: NotificationMessage, *, secret: str = "", config: dict | None = None) -> str:
        if self.fail is not None:
            raise self.fail
        self.sent.append(message)
        return f"{self.name}-{len(self.sent)}"

    def validate_configuration(self, *, secret: str = "", config: dict | None = None) -> None:
        return None


def test_fingerprint_is_stable_and_ignores_timestamps() -> None:
    first = fingerprint(_signal(summary="one", first_seen_at=utcnow()))
    second = fingerprint(_signal(summary="two"))
    other = fingerprint(_signal(source_id="orders-api"))
    assert first == second
    assert first != other
    assert "T" not in first


def test_deduplication_updates_same_alert() -> None:
    recorder = RecordingProvider(name="teams")
    register_test_provider("teams", recorder)
    register_test_provider("log", recorder)
    session = SessionLocal()
    try:
        first = publish(session, _signal())
        session.flush()
        second = publish(session, _signal(summary="still down"))
        session.commit()
        assert first is not None and second is not None
        assert first.id == second.id
        assert second.occurrence_count == 2
        assert second.status == AlertStatus.OPEN
        assert len({row.id for row in session.query(AlertRow).all()}) == 1
        initial = [item for item in session.query(NotificationDeliveryRow).all() if item.notification_type == NotificationType.INITIAL]
        assert len(initial) >= 1
    finally:
        register_test_provider("teams", None)
        register_test_provider("log", None)
        session.close()


def test_alert_rule_matching_and_environment_floor() -> None:
    session = SessionLocal()
    try:
        ensure_defaults(session)
        session.flush()
        prd = select_rule(list(session.query(AlertRuleRow)), _signal())
        assert prd is not None
        assert prd.environment_filter == "PRD"
        assert rule_allows_notification(prd, _signal(severity="CRITICAL"), 1)
        assert not rule_allows_notification(prd, _signal(severity="HIGH"), 1)
        dev_signal = _signal(environment="DEV", environment_id="aws-emea-dev", severity="CRITICAL")
        dev = select_rule(list(session.query(AlertRuleRow)), dev_signal)
        assert dev is None or not rule_matches(dev, dev_signal)
        tst = select_rule(list(session.query(AlertRuleRow)), _signal(environment="INT/TST", environment_id="aws-emea-tst", severity="LOW"))
        assert tst is not None
        assert tst.environment_filter == "INT/TST"
    finally:
        session.close()


def test_prd_critical_routing_and_payments() -> None:
    session = SessionLocal()
    try:
        ensure_defaults(session)
        session.flush()
        routes = matching_routes(list(session.query(AlertRoutingRuleRow)), _signal())
        dests = {route.destination_id for route in routes}
        assert "dest-teams-critical" in dests
        assert "dest-slack-emea" in dests
        assert "dest-log-payments" in dests
        china = matching_routes(
            list(session.query(AlertRoutingRuleRow)),
            _signal(provider="Alibaba", region="China", environment="PRD", application_id="other"),
        )
        assert any(route.destination_id == "dest-webhook-china" for route in china)
    finally:
        session.close()


def test_provider_failure_does_not_roll_back_alert() -> None:
    failing = RecordingProvider(fail=TemporaryNotificationError("teams down"), name="teams")
    register_test_provider("teams", failing)
    session = SessionLocal()
    try:
        alert = publish(session, _signal())
        session.commit()
        assert alert is not None
        assert session.get(AlertRow, alert.id) is not None
        assert alert.status == AlertStatus.OPEN
        deliveries = list(session.query(NotificationDeliveryRow).filter_by(alert_id=alert.id))
        assert deliveries
        assert any(item.status in {DeliveryStatus.RETRY, DeliveryStatus.FAILED} for item in deliveries)
    finally:
        register_test_provider("teams", None)
        session.close()


def test_notification_retries_temporary_failure() -> None:
    failing = RecordingProvider(fail=TemporaryNotificationError("timeout"), name="log")
    register_test_provider("log", failing)
    session = SessionLocal()
    try:
        alert = publish(session, _signal(environment="UAT", environment_id="aws-emea-uat", severity="MEDIUM", application_id="demo"))
        session.flush()
        delivery = session.query(NotificationDeliveryRow).filter_by(alert_id=alert.id).first()
        assert delivery is not None
        assert delivery.status == DeliveryStatus.RETRY
        assert delivery.error_category == FailureClass.TEMPORARY_FAILURE
        assert delivery.next_retry_at is not None
        assert delivery.attempt >= 1
    finally:
        register_test_provider("log", None)
        session.close()


def test_acknowledgement_stops_escalation() -> None:
    recorder = RecordingProvider(name="teams")
    register_test_provider("teams", recorder)
    session = SessionLocal()
    try:
        alert = publish(session, _signal())
        session.flush()
        acknowledge_alert(session, alert.id, actor="alice@cloudops.local", comment="Investigating deployment failure")
        session.flush()
        alert.first_seen_at = utcnow() - timedelta(minutes=40)
        session.flush()
        due = due_for_escalation(session)
        assert due == []
        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.acknowledged_by == "alice@cloudops.local"
        assert alert.resolved_at is None
    finally:
        register_test_provider("teams", None)
        session.close()


def test_resolution_and_recovery_notification() -> None:
    recorder = RecordingProvider(name="teams")
    register_test_provider("teams", recorder)
    session = SessionLocal()
    try:
        alert = publish(session, _signal())
        session.flush()
        recovered = publish(session, _signal(recovered=True, resolution_reason="application recovered"))
        session.commit()
        assert recovered is not None
        assert recovered.status == AlertStatus.RESOLVED
        assert recovered.resolution_reason == "application recovered"
        types = {item.notification_type for item in session.query(NotificationDeliveryRow).filter_by(alert_id=alert.id)}
        assert NotificationType.RECOVERY in types or recorder.sent
    finally:
        register_test_provider("teams", None)
        session.close()


def test_suppression_blocks_notifications() -> None:
    recorder = RecordingProvider(name="teams")
    register_test_provider("teams", recorder)
    session = SessionLocal()
    try:
        alert = publish(session, _signal(application_id="orders-api", source_id="orders-api"))
        session.flush()
        sent_before = len(recorder.sent)
        suppress_alert(session, alert.id, actor="ops@cloudops.local", reason="change freeze")
        session.flush()
        publish(session, _signal(application_id="orders-api", source_id="orders-api", summary="still failing"))
        session.commit()
        assert alert.status == AlertStatus.SUPPRESSED
        assert len(recorder.sent) == sent_before
        assert active_suppression(session, _signal(application_id="orders-api", source_id="orders-api")) is not None
    finally:
        register_test_provider("teams", None)
        session.close()


def test_maintenance_window_suppresses_notifications() -> None:
    recorder = RecordingProvider(name="teams")
    register_test_provider("teams", recorder)
    session = SessionLocal()
    try:
        now = utcnow()
        session.add(
            MaintenanceWindowRow(
                id=str(uuid4()),
                name="PRD payments deployment",
                scope="application",
                provider="AWS",
                region="EMEA",
                environment="PRD",
                application="payments-api",
                starts_at=now - timedelta(minutes=5),
                ends_at=now + timedelta(hours=1),
                reason="scheduled deploy",
                change_ticket="CHG-1",
                created_by="ops@cloudops.local",
                enabled=True,
            )
        )
        session.flush()
        assert active_maintenance(session, _signal()) is not None
        publish(session, _signal())
        session.commit()
        deliveries = list(session.query(NotificationDeliveryRow).all())
        assert deliveries == []
    finally:
        register_test_provider("teams", None)
        session.close()


def test_escalation_after_delay() -> None:
    recorder = RecordingProvider(name="email")
    register_test_provider("email", recorder)
    register_test_provider("webhook", recorder)
    session = SessionLocal()
    try:
        alert = publish(session, _signal())
        session.flush()
        alert.first_seen_at = utcnow() - timedelta(minutes=12)
        session.flush()
        run_escalation(session)
        session.commit()
        types = {(item.destination_id, item.notification_type) for item in session.query(NotificationDeliveryRow).filter_by(alert_id=alert.id)}
        assert ("dest-email-oncall", NotificationType.ESCALATION) in types
    finally:
        register_test_provider("email", None)
        register_test_provider("webhook", None)
        session.close()


def test_notification_deduplication() -> None:
    recorder = RecordingProvider(name="teams")
    register_test_provider("teams", recorder)
    session = SessionLocal()
    try:
        alert = publish(session, _signal())
        session.flush()
        dispatch_pending(session, alert_id=alert.id)
        session.flush()
        first_count = session.query(NotificationDeliveryRow).filter_by(alert_id=alert.id, notification_type=NotificationType.INITIAL).count()
        publish(session, _signal(summary="again"))
        session.flush()
        second_count = session.query(NotificationDeliveryRow).filter_by(alert_id=alert.id, notification_type=NotificationType.INITIAL).count()
        assert first_count == second_count
    finally:
        register_test_provider("teams", None)
        session.close()


def test_alert_api_acknowledge_resolve_and_filters() -> None:
    session = SessionLocal()
    try:
        alert = publish(session, _signal())
        session.commit()
        alert_id = alert.id
    finally:
        session.close()
    listed = client.get("/api/v1/alerts", params={"status": "open", "severity": "critical", "provider": "aws", "region": "emea", "environment": "prd", "application": "payments", "type": "application_unhealthy"}, headers=_headers())
    assert listed.status_code == 200
    assert listed.json()["items"]
    body = client.post(f"/api/v1/alerts/{alert_id}/acknowledge", json={"comment": "Investigating deployment failure"}, headers=_headers("OperationsEngineer", "alice@cloudops.local"))
    assert body.status_code == 200
    assert body.json()["status"] == "ACKNOWLEDGED"
    detail = client.get(f"/api/v1/alerts/{alert_id}", headers=_headers())
    assert detail.status_code == 200
    assert detail.json()["timeline"]
    history = client.get(f"/api/v1/alerts/{alert_id}/history", headers=_headers())
    assert history.status_code == 200
    notifications = client.get(f"/api/v1/alerts/{alert_id}/notifications", headers=_headers())
    assert notifications.status_code == 200
    resolved = client.post(f"/api/v1/alerts/{alert_id}/resolve", json={"comment": "rolled back"}, headers=_headers())
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "RESOLVED"


def test_rbac_and_secret_redaction() -> None:
    assert "alert:read" in ROLE_PERMISSIONS["Developer"]
    assert "alert:acknowledge" in ROLE_PERMISSIONS["OperationsEngineer"]
    assert "alert:resolve" not in ROLE_PERMISSIONS["OperationsEngineer"]
    assert "alert:acknowledge" not in ROLE_PERMISSIONS["SecurityAuditor"]
    assert "alert:resolve" in ROLE_PERMISSIONS["PlatformAdmin"]
    denied = client.post("/api/v1/alerts/missing/acknowledge", json={"comment": "nope"}, headers=_headers("Developer"))
    assert denied.status_code == 403
    created = client.post(
        "/api/v1/notification-destinations",
        json={
            "name": "Ops Webhook",
            "providerType": "webhook",
            "description": "test",
            "secretValue": "https://hooks.example.internal/secret-token-value",
            "config": {"to": "ops@cloudops.local"},
        },
        headers=_headers(),
    )
    assert created.status_code == 200
    payload = created.json()
    blob = " ".join(walk_strings(payload))
    assert "secret-token-value" not in blob
    assert payload["hasSecret"] is True
    assert "url" not in (payload.get("config") or {})
    stored = LocalDevSecretBackend().get_secret(payload["configurationReference"])
    assert stored.startswith("https://")


def test_alert_rules_and_maintenance_api() -> None:
    rules = client.get("/api/v1/alert-rules", headers=_headers())
    assert rules.status_code == 200
    assert rules.json()["items"]
    created = client.post(
        "/api/v1/alert-rules",
        json={"name": "UAT custom", "environmentFilter": "UAT", "severity": "MEDIUM", "enabled": True},
        headers=_headers(),
    )
    assert created.status_code == 200
    rule_id = created.json()["id"]
    updated = client.put(
        f"/api/v1/alert-rules/{rule_id}",
        json={"name": "UAT custom", "environmentFilter": "UAT", "severity": "HIGH", "enabled": True},
        headers=_headers(),
    )
    assert updated.status_code == 200
    deleted = client.delete(f"/api/v1/alert-rules/{rule_id}", headers=_headers())
    assert deleted.status_code == 200
    now = utcnow()
    window = client.post(
        "/api/v1/maintenance-windows",
        json={
            "name": "PRD payments deployment",
            "provider": "AWS",
            "region": "EMEA",
            "environment": "PRD",
            "application": "payments-api",
            "startsAt": now.isoformat(),
            "endsAt": (now + timedelta(hours=1)).isoformat(),
            "reason": "deploy",
            "changeTicket": "CHG-9",
        },
        headers=_headers("DevOpsEngineer"),
    )
    assert window.status_code == 200
    destinations = client.get("/api/v1/notification-destinations", headers=_headers())
    assert destinations.status_code == 200
    policies = client.get("/api/v1/notification-policies", headers=_headers())
    assert policies.status_code == 200
    routes = client.get("/api/v1/alert-routing-rules", headers=_headers())
    assert routes.status_code == 200
