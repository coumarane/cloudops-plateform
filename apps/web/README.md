# CloudOps Platform web

Next.js + TypeScript + Tailwind implementation of the CloudOps operations console.

The console loads fleet data from the FastAPI service at `/api/v1` (proxied to `http://127.0.0.1:8000` by default). AWS AMER, EMEA, and APAC cells use live backend data after account scans; Alibaba China uses live data after ACK scans. PRD inventory is read-only.

```bash
npm install
npm run test
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The console is desktop-first. Below the `md` breakpoint the sidebar collapses behind an Open navigation control.

Secret values are never rendered and cannot be retrieved. The API returns metadata, fingerprints, and rotation state only. NPD/PRD Update / Replace / Validate requires confirmation, a reason, and backend `credential:prod_update`.
