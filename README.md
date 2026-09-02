# CloudOps Platform

Enterprise multi-cloud operations portal for AWS EKS and Alibaba ACK.

## Current scope

The first implemented screen is the **Global Operations Dashboard** in `apps/web`.

It shows AWS AMER / EMEA / APAC and Alibaba China across DEV, INT/TST, UAT, NPD, and PRD, with production visually separated from non-production. Secret values are never displayed.

## Web app

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).
