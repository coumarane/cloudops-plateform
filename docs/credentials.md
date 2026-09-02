# Credential and secret lifecycle (Phase 6)

CloudOps stores **credential metadata** in PostgreSQL. Secret material is written only to a secret backend and is never persisted in the database, logs, Celery results, API responses, or audit records.

There is no `GET /api/v1/credentials/{id}/secret` route. `get_secret()` exists on backends for in-process Celery workers only.

## Model

Provider → Region → Account → Environment → Credential

Tables:

- `credentials` — metadata, fingerprint, secret **reference**, rotation timestamps
- `credential_versions` — fingerprint + reference per replace
- `credential_validations` — identity-check results
- `credential_rotation_events` — replace / update / validate history
- `credential_audit_events` — sanitized audit trail

Statuses: `HEALTHY`, `ROTATION_DUE`, `OVERDUE`, `INVALID`, `DISABLED`.

`rotation_due_at = last_rotated_at + rotation_policy_days`. Phase 6 tracks due dates and does **not** rotate provider credentials automatically.

## Secret backends

| `CLOUDOPS_SECRET_BACKEND` | Class | Use |
| --- | --- | --- |
| `local` | `LocalDevSecretBackend` | Local development and tests only. In-process dict. |
| `aws` / `secretsmanager` | `AwsSecretsManagerBackend` | AWS Secrets Manager |
| `alibaba` | `AlibabaSecretsBackend` | Alibaba Cloud KMS Secrets Manager |

`CLOUDOPS_ALLOW_LOCAL_SECRETS=false` must be set in production so the local backend cannot be selected.

Preferred credential types:

- AWS: IAM role / STS AssumeRole, then access keys only when required
- Alibaba: RAM role / STS, then AccessKey only when required

## API

| Method | Path | Permission |
| --- | --- | --- |
| GET | `/api/v1/credentials` | `credential:read` |
| GET | `/api/v1/credentials/{id}` | `credential:read` |
| POST | `/api/v1/credentials` | `credential:create` (+ `credential:prod_update` for NPD/PRD) |
| POST | `/api/v1/credentials/{id}` | `credential:update` (metadata only) |
| POST | `/api/v1/credentials/{id}/replace` | `credential:rotate` |
| POST | `/api/v1/credentials/{id}/validate` | `credential:validate` (Celery job) |
| GET | `/api/v1/credentials/{id}/history` | `credential:read_history` |
| GET | `/api/v1/credentials/{id}/validations` | `credential:read_history` |
| POST | `/api/v1/jobs/credentials/rotation-status-scan` | (job enqueue) |

Filters: `?provider=aws|alibaba&region=emea&environment=prd&status=rotation_due`.

NPD and PRD writes require `confirmed=true`, a non-empty `reason`, optional `changeTicket`, and `credential:prod_update`. Frontend checks are not sufficient.

## RBAC

Header auth (no cookies, so CSRF is not applicable):

- `X-CloudOps-User`
- `X-CloudOps-Role`

| Role | Permissions |
| --- | --- |
| PlatformAdmin | all `credential:*` |
| DevOpsEngineer | non-prod create/update/validate/rotate/read/history |
| SecurityAuditor | read + history |
| Developer / ReadOnly | read metadata |

`CLOUDOPS_REQUIRE_AUTH=true` requires the user header. Default local/test role is PlatformAdmin.

## Celery

- `credential_validate` — STS GetCallerIdentity (AWS) or STS GetCallerIdentity (Alibaba). Loads secret into memory, uses it, discards it.
- `credential_rotation_status_scan` — updates HEALTHY / ROTATION_DUE / OVERDUE. Celery Beat every 6 hours via `tasks.credential_rotation_scan.periodic_scan`.

Worker:

```bash
cd apps/worker
PYTHONPATH=../api:. python3 -m celery -A celery_app worker --loglevel=info
PYTHONPATH=../api:. python3 -m celery -A celery_app beat --loglevel=info
```

## Environment variables

| Variable | Purpose |
| --- | --- |
| `CLOUDOPS_SECRET_BACKEND` | `local`, `aws`, or `alibaba` |
| `CLOUDOPS_ALLOW_LOCAL_SECRETS` | Must be `false` in production |
| `CLOUDOPS_REQUIRE_AUTH` | Require `X-CloudOps-User` |
| `CLOUDOPS_REQUIRE_HTTPS` | Reject non-HTTPS when behind a TLS terminator (`X-Forwarded-Proto`) |
| `CLOUDOPS_DEFAULT_ROLE` / `CLOUDOPS_DEFAULT_USER` | Unauthenticated local defaults |
| `CLOUDOPS_MAX_SECRET_BYTES` | Request size cap (default 65536) |
| `CLOUDOPS_CREDENTIAL_VALIDATE_RATE_PER_MINUTE` | Validate rate limit |
| `CLOUDOPS_CREDENTIAL_MUTATE_RATE_PER_MINUTE` | Create/replace rate limit |
| `CLOUDOPS_ROTATION_DUE_SOON_DAYS` | Days before due that map to `ROTATION_DUE` (default 14) |

AWS/Alibaba inventory role env vars from earlier phases still apply for cluster scans. Credential **application** secrets go to the secret backend, not those env vars.

## Security assumptions

- TLS is terminated in front of FastAPI outside local development.
- Request bodies for `/credentials` are not written to access logs.
- Header RBAC is a stand-in until SSO; do not expose the API without a trusted identity proxy if `CLOUDOPS_REQUIRE_AUTH` is false.
- In-memory rate limits are per process, not shared across replicas.
- LocalDev secrets die with the process.

## Known limitations

- Automatic provider credential rotation is not implemented.
- Alibaba KMS uses NonProd AccessKey env vars to talk to Secrets Manager unless a client is injected.
- Validation against live STS requires reachable cloud credentials; tests patch the identity helpers.
- Mock Secrets catalog rows remain until a live credential with the same provider/region/environment/name is created.
