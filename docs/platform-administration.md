# Platform administration and real data

CloudOps is configured from **Administration**, not by editing database rows or backend files. Create provider-side identities first using [cloud-provider-onboarding.md](cloud-provider-onboarding.md).

## Data modes

| Variable | Default | Behavior |
| --- | --- | --- |
| `CLOUDOPS_DEMO_MODE` | `false` | When `true`, catalog screens can show demo inventory. A **DEMO DATA** badge appears in the sidebar. |
| `CLOUDOPS_SEED_TOPOLOGY` | `false` | When `true`, seeds topology JSON accounts/environments. Does **not** seed fake clusters, certificates, applications, or alerts. |
| `CLOUDOPS_PROVIDER_STUB` | `false` | Uses a deterministic provider adapter for local E2E without cloud credentials. Not the same as demo catalog data. |
| `CLOUDOPS_BOOTSTRAP_ADMIN_ENABLED` | `false` | Required for mutating admin APIs when `CLOUDOPS_APP_ENVIRONMENT` is not `development` / `local` / `test`. |
| `CLOUDOPS_APP_ENVIRONMENT` | `development` | Local/dev/test allow bootstrap administration. Deployed environments must set `production` and leave bootstrap disabled until Phase 12 OIDC/RBAC. |

Empty database: the dashboard shows **Welcome to CloudOps Platform** and **Start Setup**. It does not invent production-looking infrastructure.

## Bootstrap admin

Until Phase 12, mutating provider/account/environment/application/integration APIs require:

- local/dev/test (`CLOUDOPS_APP_ENVIRONMENT`), or
- `CLOUDOPS_BOOTSTRAP_ADMIN_ENABLED=true`

Do not enable bootstrap admin on a deployed environment that is reachable without a trusted identity proxy.

## AWS setup (UI)

1. Administration → Credentials → Add Credential (`sts_assume_role`, Role ARN). Secret material is write-only.
2. Administration → Providers → Add Provider → AWS Corporate → AssumeRole.
3. Administration → Cloud Accounts → Add Account (account ID, EMEA, `eu-west-1`, Role ARN, NONPROD, credential reference).
4. Administration → Environments → Add Environment (DEV / UAT / …).
5. Account → Validate. CloudOps calls STS `GetCallerIdentity` and stores sanitized identity only.
6. Environment → Discover Clusters. Watch Administration → Discovery Jobs.
7. Scan Certificates / Run Health Check from the environment page.

Live IAM guidance: [cloud-provider-onboarding.md](cloud-provider-onboarding.md#aws-eks) and [aws-emea-dev-iam.md](aws-emea-dev-iam.md). Prefer IRSA / instance profile over access keys.

Local E2E without AWS: `CLOUDOPS_PROVIDER_STUB=true`.

## Alibaba setup (UI)

1. Add credential (`ram_role` or AccessKey JSON). AccessKey **Secret** goes only to SecretBackend.
2. Add provider **Alibaba China** (RAM / STS).
3. Add account (China, `cn-hangzhou`, RAM role, NONPROD or PROD).
4. Add environment, Validate, Discover Clusters.

RAM guidance: [cloud-provider-onboarding.md](cloud-provider-onboarding.md#alibaba-cloud-ack) and [alibaba-china-ram.md](alibaba-china-ram.md).

## Azure setup (UI)

1. Add provider **Microsoft Azure** and select the intended identity pattern.
2. Add the Azure subscription account, logical region, and Azure region.
3. Azure validation, AKS discovery, health scans, and certificate scans are unavailable until the Azure inventory adapter is implemented.

Azure identity planning: [cloud-provider-onboarding.md](cloud-provider-onboarding.md#microsoft-azure-aks).

## Integrations

Administration → Integrations:

- GitHub App: App ID, installation ID, organization, private key (write-only) or key reference. Validate / Synchronize / Disable.
- Azure DevOps: organization, project, auth secret reference. Validate / Synchronize.
- Notifications: existing destination configure/test UI.

## Remaining mock-only surfaces

When `CLOUDOPS_DEMO_MODE=false`:

- Deployments catalog is empty until a future deployment integration.
- GitHub workflow runs overlay live GitHub rows only; they are empty until a GitHub App is synchronized.
- Pipeline catalog is empty until Azure DevOps / GitHub Actions sync succeeds.

Demo catalog records are used only when `CLOUDOPS_DEMO_MODE=true`.
