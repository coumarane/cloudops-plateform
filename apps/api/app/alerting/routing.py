from __future__ import annotations

from app.alerting.models import AlertSignal
from app.db.models import AlertRoutingRuleRow


def _matches(configured: str, actual: str) -> bool:
    if not configured:
        return True
    return configured.strip().lower() == (actual or "").strip().lower()


def routing_matches(rule: AlertRoutingRuleRow, signal: AlertSignal) -> bool:
    if not rule.enabled:
        return False
    return all(
        (
            _matches(rule.provider_filter, signal.provider),
            _matches(rule.region_filter, signal.region),
            _matches(rule.account_filter, signal.account_id),
            _matches(rule.environment_filter, signal.environment),
            _matches(rule.application_filter, signal.application_id),
            _matches(rule.severity_filter, signal.severity),
            _matches(rule.alert_type_filter, signal.alert_type),
        )
    )


def matching_routes(rules: list[AlertRoutingRuleRow], signal: AlertSignal) -> list[AlertRoutingRuleRow]:
    return [rule for rule in rules if routing_matches(rule, signal)]
