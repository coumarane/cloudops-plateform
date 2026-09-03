# CloudOps Platform

CloudOps Platform is an enterprise multi-cloud operations portal.

## Stack

Frontend:
- Next.js
- TypeScript
- Tailwind CSS

Backend:
- FastAPI
- PostgreSQL
- Celery
- Redis

Cloud providers:
- AWS EKS
- Alibaba ACK

Integrations:
- GitHub Actions
- GitHub Variables
- GitHub Secrets
- DevOps pipelines

## Infrastructure model

Provider
→ Region
→ Account
→ Environment
→ Cluster
→ Application

AWS regions:
- AMER
- EMEA
- APAC

Each AWS region contains:

Non-production account:
- DEV
- INT/TST
- UAT

Production account:
- NPD
- PRD

Alibaba China contains:

Non-production account:
- DEV
- TST
- UAT

Production account:
- NPD
- PRD

## UI Design

Use Google Stitch for UI design work.

Before implementing significant UI screens:

1. Generate or refine the screen using Stitch.
2. Maintain a consistent CloudOps Platform design system.
3. Prefer reusable components.
4. Then convert the selected design into Next.js + TypeScript + Tailwind.
5. Do not copy generated HTML blindly.
6. Refactor output into production-quality React components.

Primary navigation:

- Overview
- Infrastructure
- Clusters
- Environments
- Applications
- Secrets
- Certificates
- Health Checks
- Deployments
- Pipelines
- GitHub
- Jobs
- Alerts
- Audit
- Administration

The main dashboard must provide:

AWS:
- AMER
- EMEA
- APAC

Alibaba:
- China

with environment health for:

DEV / INT-TST / UAT / NPD / PRD

Always clearly distinguish production from non-production.

Secret catalog responses stay metadata-only. Revealed values are allowed only after an explicit operator action and must never be written to logs or audit detail.