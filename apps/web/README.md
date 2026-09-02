# CloudOps Platform web

Next.js + TypeScript + Tailwind implementation of the CloudOps operations console.

The console loads fleet data from the FastAPI service at `/api/v1` (proxied to `http://127.0.0.1:8000` by default). AWS EMEA DEV clusters and ACM certificates come from the live backend when discovery jobs have run; other scopes stay mocked.

```bash
npm install
npm run test
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The console is desktop-first. Below the `md` breakpoint the sidebar collapses behind an Open navigation control.

Secret values are never rendered. The API returns rotation status, due dates, and object names only. PRD Update / Rotate / Validate requires an explicit production confirmation.
