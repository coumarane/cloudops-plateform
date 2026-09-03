from __future__ import annotations


class AlertingError(Exception):
    """Base alerting error."""


class AlertNotFoundError(AlertingError):
    pass


class AlertPermissionError(AlertingError):
    pass


class AlertStateError(AlertingError):
    pass
