# CloudOps API

FastAPI service for the CloudOps console.

Phase 6 stores credential **metadata** in PostgreSQL and secret material in a secret backend (`local` for development only). Topology remains config/database-driven. PRD inventory is read-only. NPD/PRD credential writes require `credential:prod_update`.

```bash
cd apps/api
python3 -m pip install -r requirements.txt
PYTHONPATH=. alembic upgrade head
python3 -m uvicorn app.main:app --reload --port 8000
```

Celery worker (optional when `CLOUDOPS_CELERY_EAGER=true`):

```bash
cd apps/worker
PYTHONPATH=../api:. python3 -m celery -A celery_app worker --loglevel=info
```

## AWS connection

Prefer IAM role assumption. Do not put access keys in PostgreSQL.

| Variable | Purpose |
| --- | --- |
| `CLOUDOPS_AWS_{REGION}_{NONPROD\|PROD}_ROLE_ARN` | Role to assume in that account (e.g. `CLOUDOPS_AWS_EMEA_NONPROD_ROLE_ARN`) |
| `CLOUDOPS_AWS_{REGION}_{NONPROD\|PROD}_ACCOUNT_ID` | Expected account ID check |
| `CLOUDOPS_AWS_{REGION}_CLOUD_REGION` | AWS region override (`us-east-1`, `eu-west-1`, `ap-southeast-1`) |
| `CLOUDOPS_AWS_ROLE_ARN` / `CLOUDOPS_AWS_ACCOUNT_ID` | Legacy fallback for EMEA NonProd |
| `CLOUDOPS_AWS_EXTERNAL_ID` | Optional external ID shared by AssumeRole |
| `CLOUDOPS_AWS_SCAN_CONCURRENCY` | Max parallel account scans (default 3) |
| `CLOUDOPS_AWS_TOPOLOGY_PATH` | Optional JSON file replacing the default topology (see `docs/aws-topology.example.json`) |
| `CLOUDOPS_AWS_CONFIG_SECRET_ARN` | Secrets Manager JSON with `roleArn` / `accountId` / `region` (reference only) |
| `CLOUDOPS_AWS_PROFILE` | Optional local named profile |
| `CLOUDOPS_DATABASE_URL` | SQLAlchemy URL (PostgreSQL in production) |
| `CLOUDOPS_REDIS_URL` | Celery broker |
| `CLOUDOPS_CELERY_EAGER` | `true` runs jobs in-process for local use |
| `CLOUDOPS_SECRET_BACKEND` | `local` (dev/tests), `aws`, or `alibaba` |
| `CLOUDOPS_ALLOW_LOCAL_SECRETS` | Must be `false` in production |
| `CLOUDOPS_REQUIRE_AUTH` | Require `X-CloudOps-User` |
| `CLOUDOPS_REQUIRE_HTTPS` | Reject non-HTTPS when `X-Forwarded-Proto` is not https |

Secret values, tokens, private keys, PEM, kubeconfig, AWS access keys, and Alibaba AccessKey Secrets are never returned. Credential lifecycle: [docs/credentials.md](../../docs/credentials.md).

## Alibaba China connection

Prefer RAM role assumption. Do not put AccessKey Secrets in PostgreSQL. See [docs/alibaba-china-ram.md](../../docs/alibaba-china-ram.md).

| Variable | Purpose |
| --- | --- |
| `CLOUDOPS_ALIBABA_{NONPROD\|PROD}_ACCOUNT_ID` | Expected account ID check |
| `CLOUDOPS_ALIBABA_{NONPROD\|PROD}_ROLE_ARN` | RAM role to assume |
| `CLOUDOPS_ALIBABA_{NONPROD\|PROD}_ACCESS_KEY_ID` | AccessKey ID used to assume the role |
| `CLOUDOPS_ALIBABA_{NONPROD\|PROD}_ACCESS_KEY_SECRET` | AccessKey Secret. Runtime only. |
| `CLOUDOPS_ALIBABA_ACCOUNT_ID` / `_ROLE_ARN` / `_ACCESS_KEY_*` | Legacy NonProd fallbacks |
| `CLOUDOPS_ALIBABA_CLOUD_REGION` | ACK region (default `cn-hangzhou`) |
| `CLOUDOPS_ALIBABA_SCAN_CONCURRENCY` | Max parallel account scans (default 2) |

Secret values, tokens, private keys, PEM, kubeconfig, AWS access keys, and Alibaba AccessKey Secrets are never returned.
