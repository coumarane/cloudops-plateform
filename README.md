# CloudOps Platform

Enterprise multi-cloud operations portal for AWS EKS and Alibaba ACK.

## Local run (Phase 5)

Start PostgreSQL and Redis if you are not using the SQLite / eager-Celery defaults, then FastAPI and Next.js.

```bash
cd apps/api
python3 -m pip install -r requirements.txt
PYTHONPATH=. alembic upgrade head
python3 -m uvicorn app.main:app --reload --port 8000
```

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Optional worker (when `CLOUDOPS_CELERY_EAGER=false`):

```bash
cd apps/worker
PYTHONPATH=../api:. python3 -m celery -A celery_app worker --loglevel=info
```

Live AWS data is used for **AMER, EMEA, and APAC** after a successful scan of that account. Live Alibaba data is used for **China** after a successful ACK scan. Unscanned cells keep mock catalog data. PRD is read-only.

Secret values are never returned by the API or rendered in the console. See [docs/aws-emea-dev-iam.md](docs/aws-emea-dev-iam.md) and [docs/alibaba-china-ram.md](docs/alibaba-china-ram.md).
