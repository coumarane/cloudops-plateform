from __future__ import annotations

from app.alerting.models import SEVERITY_RANK, AlertSignal, normalize_severity
from app.db.models import AlertRuleRow


def _matches_filter(configured: str, actual: str) -> bool:
    if not configured:
        return True
    return configured.strip().lower() == (actual or "").strip().lower()


def rule_matches(rule: AlertRuleRow, signal: AlertSignal) -> bool:
    if not rule.enabled:
        return False
    if rule.alert_type and rule.alert_type.strip().upper() != (signal.alert_type or "").strip().upper():
        return False
    if not _matches_filter(rule.provider_filter, signal.provider):
        return False
    if not _matches_filter(rule.region_filter, signal.region):
        return False
    if not _matches_filter(rule.environment_filter, signal.environment):
        return False
    if not _matches_filter(rule.application_filter, signal.application_id):
        return False
    return True


def select_rule(rules: list[AlertRuleRow], signal: AlertSignal) -> AlertRuleRow | None:
    matches = [rule for rule in rules if rule_matches(rule, signal)]
    if not matches:
        return None

    def score(rule: AlertRuleRow) -> tuple[int, int]:
        specificity = sum(
            1
            for value in (
                rule.alert_type,
                rule.provider_filter,
                rule.region_filter,
                rule.environment_filter,
                rule.application_filter,
            )
            if value
        )
        return (specificity, SEVERITY_RANK.get(normalize_severity(rule.severity), 0))

    matches.sort(key=score, reverse=True)
    return matches[0]


def rule_allows_notification(rule: AlertRuleRow | None, signal: AlertSignal, occurrence_count: int) -> bool:
    if rule is None or not rule.enabled:
        return False
    if occurrence_count < max(rule.minimum_occurrences, 1):
        return False
    floor = normalize_severity(rule.severity)
    actual = normalize_severity(signal.severity)
    return SEVERITY_RANK.get(actual, 0) >= SEVERITY_RANK.get(floor, 99)
