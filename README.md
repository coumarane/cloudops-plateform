# CloudOps Platform

Enterprise multi-cloud operations portal for AWS EKS and Alibaba ACK.

## Local run (Phase 2)

Start the mock FastAPI service, then the Next.js console. The web app proxies `/api/v1` to FastAPI.

```bash
cd apps/api
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --port 8000
```

```bash
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

AWS and Alibaba credentials are not used. Secret values are never returned by the API or rendered in the console.
