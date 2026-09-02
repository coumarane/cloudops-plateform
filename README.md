# CloudOps Platform

Enterprise multi-cloud operations portal for AWS EKS and Alibaba ACK.

## Current scope

Implemented screens in `apps/web`:

- **Global Operations Dashboard** (`/`) — AWS AMER / EMEA / APAC and Alibaba China across DEV, INT/TST, UAT, NPD, and PRD
- **Environment Details** (`/environments/...`) — per-environment cockpit with Overview, Clusters, Applications, Secrets, Certificates, Deployments, Pipelines, GitHub, Health, and Audit tabs

Production is visually separated from non-production. Secret values are never displayed.

## Web app

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).
