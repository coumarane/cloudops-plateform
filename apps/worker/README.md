# CloudOps worker

Celery worker for AWS and Alibaba inventory jobs.

```bash
cd apps/worker
python3 -m pip install -r requirements.txt
PYTHONPATH=../api:. python3 -m celery -A celery_app worker --loglevel=info
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

Jobs are idempotent upserts. Transient provider errors retry. Authentication and permission errors do not retry. One account failure does not stop other environments.
