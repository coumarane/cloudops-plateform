# CloudOps worker

Celery worker for AWS and Alibaba inventory jobs.

```bash
cd apps/worker
python3 -m pip install -r requirements.txt
PYTHONPATH=../api:. python3 -m celery -A celery_app worker --loglevel=info
PYTHONPATH=../api:. python3 -m celery -A celery_app beat --loglevel=info
```

AWS tasks:

- `tasks.aws_cluster_discovery.discover_clusters`
- `tasks.aws_cluster_health.scan_health`
- `tasks.aws_certificate_scan.scan_certificates`

Alibaba China tasks:

- `tasks.alibaba_account_validation.validate_accounts`
- `tasks.alibaba_cluster_discovery.discover_clusters`
- `tasks.alibaba_cluster_health.scan_health`
- `tasks.alibaba_certificate_scan.scan_certificates`
- `tasks.alibaba_certificate_expiry.scan_expiry`

Credential tasks (Phase 6):

- `tasks.credential_validate.validate_credential`
- `tasks.credential_rotation_scan.scan_rotation_status`
- `tasks.credential_rotation_scan.periodic_scan` (Beat, every 6 hours)

Jobs are idempotent upserts. Transient provider errors retry. Authentication and permission errors do not retry. One account failure does not stop other environments. Credential validation never stores secret material in the task result.
