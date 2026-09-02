from app.core.security import assert_no_secret_values, walk_strings
from app.data.matrix import MATRIX_ROWS, cell_for
from app.data.operations import ADMIN_INTEGRATIONS, ADMIN_USERS, ALERTS, AUDIT_EVENTS, FAILURES, JOBS
from app.data.security import CERTIFICATES, SECRETS
from app.domain.enums import (
    ENVIRONMENTS,
    PROVIDERS,
    Environment,
    account_name,
    cloud_region,
    cluster_name,
    environment_namespace,
    is_production,
    platform_for,
    regions_for,
)
from app.domain.models import (
    AccountRecord,
    ActivityItem,
    ApplicationRecord,
    CellMetrics,
    ClusterRecord,
    EnvironmentAlert,
    EnvironmentCertificate,
    EnvironmentIdentity,
    EnvironmentRecord,
    EnvironmentSecret,
    HealthCheckRecord,
    MatrixRow,
    ProviderRecord,
    RegionRecord,
    RunRecord,
)


def identity_of(provider, region, environment) -> EnvironmentIdentity:
    return EnvironmentIdentity(
        provider=provider,
        region=region,
        environment=environment,
        platform=platform_for(provider),
        cloudRegion=cloud_region(provider, region),
        account=account_name(provider, region, environment),
        clusterName=cluster_name(provider, region, environment),
    )


def _cluster_status(cell: CellMetrics) -> str:
    if cell.clustersUnreachable:
        return "Unreachable"
    if cell.clustersDegraded:
        return "Degraded"
    return "Healthy"


def _emea_uat() -> EnvironmentRecord:
    identity = identity_of("AWS", "EMEA", "UAT")
    return EnvironmentRecord(
        identity=identity,
        clusters=[
            ClusterRecord(
                id="eu-west-1-uat-k8s",
                name="eu-west-1-uat-k8s",
                platform="EKS",
                version="1.29",
                nodes=12,
                provider="AWS",
                region="EMEA",
                environment="UAT",
                account="nonprod-emea",
                status="Unreachable",
                appsLabel="4 degraded",
            )
        ],
        applications=[
            ApplicationRecord(
                id="app-AWS-EMEA-UAT-payment-gateway-svc",
                name="payment-gateway-svc",
                namespace="finance-uat",
                replicas="2/4",
                issue="CrashLoopBackOff",
                provider="AWS",
                region="EMEA",
                environment="UAT",
                cluster="eu-west-1-uat-k8s",
                action="Logs",
            ),
            ApplicationRecord(
                id="app-AWS-EMEA-UAT-user-profile-api",
                name="user-profile-api",
                namespace="users-uat",
                replicas="0/2",
                issue="ImagePullBackOff",
                provider="AWS",
                region="EMEA",
                environment="UAT",
                cluster="eu-west-1-uat-k8s",
                action="Events",
            ),
            ApplicationRecord(
                id="app-AWS-EMEA-UAT-inventory-sync-worker",
                name="inventory-sync-worker",
                namespace="logistics-uat",
                replicas="1/1 (Not Ready)",
                issue="ReadinessProbe Failed",
                provider="AWS",
                region="EMEA",
                environment="UAT",
                cluster="eu-west-1-uat-k8s",
                action="Describe",
            ),
            ApplicationRecord(
                id="app-AWS-EMEA-UAT-notification-dispatcher",
                name="notification-dispatcher",
                namespace="core-uat",
                replicas="1/3",
                issue="OOMKilled",
                provider="AWS",
                region="EMEA",
                environment="UAT",
                cluster="eu-west-1-uat-k8s",
                action="Metrics",
            ),
        ],
        secrets=[
            EnvironmentSecret(
                name="db-credentials-finance",
                namespace="finance-uat",
                status="Overdue",
                detail="Rotation overdue",
            )
        ],
        certificates=[],
        deployments=[ActivityItem(title="checkout-api rollout paused", detail="Waiting on cluster connectivity", age="25m ago")],
        pipelines=[ActivityItem(title="uat-promote pipeline skipped", detail="Gate blocked: cluster unreachable", age="40m ago")],
        github=[ActivityItem(title="workflow uat-deploy skipped", detail="Initiated by GitHub Actions", age="25m ago")],
        health=[ActivityItem(title="kube-apiserver probe failing", detail="eu-west-1-uat-k8s", age="10m ago")],
        audit=[ActivityItem(title="Audit log exported", detail="Destination recorded; no secret values included", age="3h ago")],
        alerts=[
            EnvironmentAlert(
                title="Cluster Unreachable",
                objectName="eu-west-1-uat-k8s",
                age="10m ago",
                severity="critical",
            )
        ],
        recentActivity=[
            ActivityItem(title="Deploy user-profile-api:v2.1.0", detail="Initiated by GitHub Actions", age="25m ago"),
            ActivityItem(title="Pipeline nightly-db-backup completed", detail="Duration: 12m 4s", age="4h ago"),
            ActivityItem(title="Audit log exported", detail="System event; no secret values included", age="6h ago"),
        ],
    )


def _record_from_matrix(provider, region, environment: Environment) -> EnvironmentRecord:
    identity = identity_of(provider, region, environment)
    cell = cell_for(provider, region, environment)
    status = _cluster_status(cell)
    namespace = environment_namespace(environment)
    degraded = cell.appsDegraded > 0
    apps = [
        ApplicationRecord(
            id=f"app-{provider}-{region}-{environment}-platform-api",
            name="platform-api",
            namespace=namespace,
            replicas="2/3" if degraded else "3/3",
            issue="Degraded" if degraded else "Healthy",
            provider=provider,
            region=region,
            environment=environment,
            cluster=identity.clusterName,
            action="Logs" if degraded else "Status",
        )
    ]
    if provider == "AWS" and region == "APAC" and environment == "PRD":
        apps.append(
            ApplicationRecord(
                id="app-apac-prd-payment",
                name="payment-svc",
                namespace="prd",
                replicas="0/3",
                issue="Rollout aborted",
                provider="AWS",
                region="APAC",
                environment="PRD",
                cluster=identity.clusterName,
                action="Logs",
            )
        )
    if provider == "Alibaba" and environment == "UAT":
        apps.append(
            ApplicationRecord(
                id="app-china-uat-gateway",
                name="api-gateway-v2",
                namespace="uat",
                replicas="1/2",
                issue="Restart loop",
                provider="Alibaba",
                region="China",
                environment="UAT",
                cluster=identity.clusterName,
                action="Logs",
            )
        )
    secrets = (
        [EnvironmentSecret(name="app-runtime-credentials", namespace=namespace, status="Overdue", detail="Rotation overdue")]
        if cell.secretsOverdue
        else (
            [
                EnvironmentSecret(
                    name="app-runtime-credentials",
                    namespace=namespace,
                    status="Due soon",
                    detail=f"Due in {cell.nextSecretDueDays or 4}d",
                )
            ]
            if cell.secretsDueSoon
            else [
                EnvironmentSecret(
                    name="app-runtime-credentials",
                    namespace=namespace,
                    status="OK",
                    detail="Rotation current",
                )
            ]
        )
    )
    certificates = (
        [EnvironmentCertificate(name="ingress-tls-wildcard", daysToExpiry=cell.nextCertExpiryDays or 12)]
        if cell.certsExpiring14d
        else []
    )
    deployments = (
        [ActivityItem(title="payment-svc deploy failed", detail="Rollout aborted", age="15m ago")]
        if cell.failedDeploys
        else [ActivityItem(title="platform-api deploy succeeded", detail="Rollout complete", age="2h ago")]
    )
    pipelines = (
        [ActivityItem(title="data-sync pipeline failed", detail="Stage test-gate", age="2h ago")]
        if cell.pipelineFailures
        else [ActivityItem(title="env-sync pipeline succeeded", detail="Last green run", age="6h ago")]
    )
    github = (
        [ActivityItem(title="auth-build workflow failed", detail="GitHub Actions", age="1h ago")]
        if cell.githubFailures
        else [ActivityItem(title="ci-verify workflow succeeded", detail="GitHub Actions", age="4h ago")]
    )
    unreachable = cell.clustersUnreachable > 0
    alerts = (
        [
            EnvironmentAlert(
                title="Cluster Unreachable" if unreachable else "Environment warning",
                objectName=identity.clusterName,
                age="10m ago",
                severity="critical" if unreachable else "warning",
            )
        ]
        if cell.openAlerts or unreachable
        else []
    )
    return EnvironmentRecord(
        identity=identity,
        clusters=[
            ClusterRecord(
                id=identity.clusterName,
                name=identity.clusterName,
                platform=identity.platform,
                version="1.29",
                nodes=6 if environment == "DEV" else 12,
                provider=provider,
                region=region,
                environment=environment,
                account=identity.account,
                status=status,  # type: ignore[arg-type]
                appsLabel=f"{cell.appsDegraded} degraded / {cell.appsHealthy} healthy",
            )
        ],
        applications=apps,
        secrets=secrets,
        certificates=certificates,
        deployments=deployments,
        pipelines=pipelines,
        github=github,
        health=[
            ActivityItem(
                title="API server unreachable" if unreachable else "Probes passing",
                detail=identity.clusterName,
                age="10m ago",
            )
        ],
        audit=[ActivityItem(title="Environment viewed", detail="Audit event recorded without secret values", age="1h ago")],
        alerts=alerts,
        recentActivity=[
            deployments[0],
            *(pipelines if cell.pipelineFailures else []),
            ActivityItem(title="Environment viewed", detail="Audit event recorded without secret values", age="1h ago"),
        ],
    )


class MockInventory:
    def __init__(self) -> None:
        self.providers = [
            ProviderRecord(id="AWS", name="AWS", platform="EKS", regions=list(regions_for("AWS"))),
            ProviderRecord(id="Alibaba", name="Alibaba", platform="ACK", regions=list(regions_for("Alibaba"))),
        ]
        self.regions = [
            RegionRecord(
                id=f"{provider}-{region}",
                name=region,
                provider=provider,
                cloudRegion=cloud_region(provider, region),
                platform=platform_for(provider),
            )
            for provider in PROVIDERS
            for region in regions_for(provider)
        ]
        self.identities = [
            identity_of(provider, region, environment)
            for provider in PROVIDERS
            for region in regions_for(provider)
            for environment in ENVIRONMENTS
        ]
        self.environment_map: dict[tuple[str, str, str], EnvironmentRecord] = {}
        for identity in self.identities:
            key = (identity.provider, identity.region, identity.environment)
            if key == ("AWS", "EMEA", "UAT"):
                self.environment_map[key] = _emea_uat()
            else:
                self.environment_map[key] = _record_from_matrix(
                    identity.provider, identity.region, identity.environment
                )
        self.matrix: list[MatrixRow] = MATRIX_ROWS
        self.certificates = CERTIFICATES
        self.secrets = SECRETS
        self.jobs = JOBS
        self.alerts = ALERTS
        self.failures = FAILURES
        self.audit_events = AUDIT_EVENTS
        self.admin_users = ADMIN_USERS
        self.admin_integrations = ADMIN_INTEGRATIONS
        self._build_accounts()
        self._build_catalogs()
        assert_no_secret_values(walk_strings(self._safety_payload()))

    def _build_accounts(self) -> None:
        seen: dict[str, AccountRecord] = {}
        for identity in self.identities:
            key = f"{identity.provider}-{identity.region}-{identity.account}"
            production = is_production(identity.environment)
            existing = seen.get(key)
            if not existing:
                seen[key] = AccountRecord(
                    id=key,
                    account=identity.account,
                    provider=identity.provider,
                    region=identity.region,
                    environment=identity.environment,
                    accountClass="Production" if production else "Non-production",
                    cloudRegion=identity.cloudRegion,
                    platform=identity.platform,
                    hostedEnvironments=[identity.environment],
                    environments="NPD · PRD" if production else "DEV · INT/TST · UAT",
                    clusters=1,
                )
            else:
                existing.clusters += 1
                if identity.environment not in existing.hostedEnvironments:
                    existing.hostedEnvironments.append(identity.environment)
        self.accounts = list(seen.values())

    def _build_catalogs(self) -> None:
        clusters: list[ClusterRecord] = []
        applications: list[ApplicationRecord] = []
        health: list[HealthCheckRecord] = []
        deployments: list[RunRecord] = []
        pipelines: list[RunRecord] = []
        github: list[RunRecord] = []
        for identity in self.identities:
            record = self.environment_map[(identity.provider, identity.region, identity.environment)]
            clusters.extend(record.clusters)
            applications.extend(record.applications)
            cluster = record.clusters[0]
            failing = cluster.status == "Unreachable"
            warning = cluster.status == "Degraded"
            health.append(
                HealthCheckRecord(
                    id=f"hc-{identity.clusterName}-apiserver",
                    name="kube-apiserver",
                    target=identity.clusterName,
                    checkType="API probe",
                    status="Failing" if failing else "Warning" if warning else "Passing",
                    lastRun="10m ago" if failing else "2m ago",
                    provider=identity.provider,
                    region=identity.region,
                    environment=identity.environment,
                    cluster=identity.clusterName,
                )
            )
            if identity.provider == "Alibaba" and identity.environment == "UAT":
                health.append(
                    HealthCheckRecord(
                        id="hc-china-uat-prometheus",
                        name="prometheus-server",
                        target="prometheus-server",
                        checkType="Memory",
                        status="Warning",
                        lastRun="2h ago",
                        provider="Alibaba",
                        region="China",
                        environment="UAT",
                        cluster=identity.clusterName,
                    )
                )
            failed_deploy = any("fail" in item.title.lower() for item in record.deployments)
            activity = record.deployments[0]
            deployments.append(
                RunRecord(
                    id=f"dep-{identity.clusterName}",
                    name="payment-svc" if failed_deploy else "platform-api",
                    detail=activity.detail,
                    result="Failed" if failed_deploy else "Succeeded",
                    age=activity.age,
                    provider=identity.provider,
                    region=identity.region,
                    environment=identity.environment,
                    cluster=identity.clusterName,
                )
            )
            failed_pipe = any("fail" in item.title.lower() for item in record.pipelines)
            pipe = record.pipelines[0]
            pipelines.append(
                RunRecord(
                    id=f"pipe-{identity.clusterName}",
                    name="data-sync" if failed_pipe else "env-sync",
                    detail=pipe.detail,
                    result="Failed" if failed_pipe else "Succeeded",
                    age=pipe.age,
                    provider=identity.provider,
                    region=identity.region,
                    environment=identity.environment,
                    cluster=identity.clusterName,
                )
            )
            failed_gh = any("fail" in item.title.lower() for item in record.github)
            gh = record.github[0]
            github.append(
                RunRecord(
                    id=f"gh-{identity.clusterName}",
                    name="auth-build" if failed_gh else "ci-verify",
                    detail="cloudops/ack-platform" if identity.provider == "Alibaba" else "cloudops/eks-platform",
                    result="Failed" if failed_gh else "Succeeded",
                    age=gh.age,
                    provider=identity.provider,
                    region=identity.region,
                    environment=identity.environment,
                    cluster=identity.clusterName,
                )
            )
        self.clusters = clusters
        self.applications = applications
        self.health_checks = health
        self.deployments = deployments
        self.pipelines = pipelines
        self.github_runs = github

    def _safety_payload(self) -> dict:
        return {
            "accounts": [item.model_dump() for item in self.accounts],
            "clusters": [item.model_dump() for item in self.clusters],
            "applications": [item.model_dump() for item in self.applications],
            "secrets": [item.model_dump() for item in self.secrets],
            "certificates": [item.model_dump() for item in self.certificates],
            "alerts": [item.model_dump() for item in self.alerts],
            "audit": [item.model_dump() for item in self.audit_events],
        }


MOCK_INVENTORY = MockInventory()
