# CloudOps API

FastAPI service for the CloudOps console.

Phase 4 uses one AWS adapter for **AMER, EMEA, and APAC** across NonProd and Prod accounts. Topology is config/database-driven. Alibaba stays on mock data. PRD is read-only.

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

Secret values, tokens, private keys, PEM, kubeconfig, and AWS access keys are never returned.
