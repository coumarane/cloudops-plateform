# CloudOps Platform

Enterprise multi-cloud operations portal for AWS EKS and Alibaba ACK.

## Current scope

Implemented screens in `apps/web`:

- **Global Operations Dashboard** (`/`)
- **Environment Details** (`/environments/...`)
- **Secrets Management** (`/secrets`) — Provider → Region → Account → Environment, with Update / Rotate / Validate / Rotation History. PRD changes require a production warning. Secret values are never displayed.

## Web app

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).
