# CloudOps API

FastAPI service for the CloudOps console.

Phase 3 uses a live AWS adapter for **AWS → EMEA → NonProd → DEV → EKS**.
All other providers, regions, and environments stay on mock data.

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
| `CLOUDOPS_AWS_ROLE_ARN` | Role to assume in the NonProd account |
| `CLOUDOPS_AWS_EXTERNAL_ID` | Optional external ID |
| `CLOUDOPS_AWS_ACCOUNT_ID` | Expected account ID check |
| `CLOUDOPS_AWS_CLOUD_REGION` | Default `eu-west-1` |
| `CLOUDOPS_AWS_CONFIG_SECRET_ARN` | Secrets Manager JSON with `roleArn` / `accountId` / `region` (reference only) |
| `CLOUDOPS_AWS_PROFILE` | Optional local named profile |
| `CLOUDOPS_DATABASE_URL` | SQLAlchemy URL (PostgreSQL in production) |
| `CLOUDOPS_REDIS_URL` | Celery broker |
| `CLOUDOPS_CELERY_EAGER` | `true` runs jobs in-process for local use |

Secret values, tokens, private keys, PEM, kubeconfig, and AWS access keys are never returned.
