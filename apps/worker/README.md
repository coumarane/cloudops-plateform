# CloudOps worker

Celery worker for AWS EMEA DEV discovery jobs.

```bash
cd apps/worker
python3 -m pip install -r requirements.txt
PYTHONPATH=../api:. python3 -m celery -A celery_app worker --loglevel=info
```

Tasks:

- `tasks.aws_cluster_discovery.discover_clusters`
- `tasks.aws_cluster_health.scan_health`
- `tasks.aws_certificate_scan.scan_certificates`

Jobs are idempotent upserts. Transient AWS errors retry. Authentication and permission errors do not retry.
