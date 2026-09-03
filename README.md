# CloudOps Platform

Enterprise multi-cloud operations portal for AWS EKS and Alibaba ACK.

## Run With Docker Or Podman

Both container runtimes launch PostgreSQL, Redis, the API, web console, Celery worker, scheduler, and database migrations. The web console is available at [http://localhost:3000](http://localhost:3000) and the API health endpoint at [http://localhost:8000/health](http://localhost:8000/health).

### Docker

Launch the complete local stack, including PostgreSQL migrations:

```bash
docker compose -f infrastructure/docker-compose.yml up --build
```

The `migrate` service runs `alembic upgrade head` once PostgreSQL is healthy; the API, Celery worker, and scheduler start only after it succeeds.

Stop the stack with `docker compose -f infrastructure/docker-compose.yml down`. Add `-v` only when you intend to remove the local PostgreSQL and Redis data volumes.

### Podman On Windows

Install Podman Desktop or Podman, then initialize and start its Linux machine in PowerShell:

```powershell
podman machine init
podman machine start
podman compose -f infrastructure/docker-compose.yml up --build -d
```

Confirm that a Compose provider is available with `podman compose version`. Podman delegates Compose support to an installed provider. If that provider does not support the migration dependency condition, run the migration explicitly before starting the services:

```powershell
podman compose -f infrastructure/docker-compose.yml run --rm migrate
podman compose -f infrastructure/docker-compose.yml up -d postgres redis api worker beat web
```

Stop the Podman stack with `podman compose -f infrastructure/docker-compose.yml down`. Add `-v` only when you intend to remove the local PostgreSQL and Redis data volumes.

## Manual local run

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
PYTHONPATH=../api:. python3 -m celery -A celery_app beat --loglevel=info
```

Live AWS data is used for **AMER, EMEA, and APAC** after a successful scan of that account. Live Alibaba data is used for **China** after a successful ACK scan. Unscanned cells keep mock catalog data. PRD is read-only for cluster inventory. Credential replace on NPD/PRD requires `credential:prod_update`.

Certificate expiry classification is computed in the API. Dashboard cards link to `/certificates?expires_within_days=7` (and related filters). Private keys are never stored or returned.

Secret values are never returned by the API or rendered in the console. See [docs/certificate-monitoring.md](docs/certificate-monitoring.md), [docs/credentials.md](docs/credentials.md), [docs/aws-emea-dev-iam.md](docs/aws-emea-dev-iam.md) and [docs/alibaba-china-ram.md](docs/alibaba-china-ram.md).
