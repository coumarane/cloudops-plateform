from app.domain.enums import ENVIRONMENTS, Environment, Platform, Provider, Region
from app.domain.models import CellMetrics, MatrixRow


def _cell(**overrides: object) -> CellMetrics:
    payload = {
        "clustersHealthy": 1,
        "clustersDegraded": 0,
        "clustersUnreachable": 0,
        "appsHealthy": 9,
        "appsDegraded": 0,
        "certsExpiring14d": 0,
        "secretsOverdue": 0,
        "secretsDueSoon": 0,
        "failedDeploys": 0,
        "githubFailures": 0,
        "pipelineFailures": 0,
        "openAlerts": 0,
    }
    payload.update(overrides)
    return CellMetrics.model_validate(payload)


def _row(
    provider: Provider,
    platform: Platform,
    region: Region,
    cells: dict[Environment, dict[str, object]],
) -> MatrixRow:
    filled: dict[Environment, CellMetrics] = {}
    for environment in ENVIRONMENTS:
        filled[environment] = _cell(**cells.get(environment, {}))
    filled["DEV"] = _cell(**{**cells.get("DEV", {}), "clustersHealthy": 2, "appsHealthy": 12})
    return MatrixRow(provider=provider, platform=platform, region=region, cells=filled)


MATRIX_ROWS: list[MatrixRow] = [
    _row(
        "AWS",
        "EKS",
        "AMER",
        {
            "INT/TST": {"githubFailures": 1, "appsHealthy": 8},
            "UAT": {"clustersHealthy": 0, "clustersDegraded": 1, "secretsOverdue": 1, "appsHealthy": 8},
            "PRD": {
                "certsExpiring14d": 1,
                "nextCertExpiryDays": 12,
                "appsHealthy": 11,
                "openAlerts": 1,
            },
        },
    ),
    _row(
        "AWS",
        "EKS",
        "EMEA",
        {
            "UAT": {
                "clustersHealthy": 0,
                "clustersUnreachable": 1,
                "appsHealthy": 0,
                "appsDegraded": 4,
                "openAlerts": 1,
            },
            "NPD": {"pipelineFailures": 1, "appsHealthy": 8},
        },
    ),
    _row(
        "AWS",
        "EKS",
        "APAC",
        {
            "INT/TST": {"clustersHealthy": 0, "clustersDegraded": 1, "appsHealthy": 7, "appsDegraded": 1},
            "PRD": {"failedDeploys": 1, "appsHealthy": 10},
        },
    ),
    _row(
        "Alibaba",
        "ACK",
        "China",
        {
            "UAT": {"openAlerts": 2, "appsHealthy": 8},
            "PRD": {"secretsDueSoon": 1, "nextSecretDueDays": 4, "appsHealthy": 11},
        },
    ),
]


def cell_for(provider: Provider, region: Region, environment: Environment) -> CellMetrics:
    for row in MATRIX_ROWS:
        if row.provider == provider and row.region == region:
            return row.cells[environment]
    return _cell(clustersHealthy=0, appsHealthy=0)
