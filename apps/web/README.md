# CloudOps Platform web

Next.js + TypeScript + Tailwind implementation of the CloudOps operations console.

Implemented screens, converted from the CloudOps Platform Stitch project into reusable React components:

- Global Operations Dashboard (`/`)
- Environments catalog (`/environments`)
- Environment Details (`/environments/{provider}/{region}/{environment}`), including INT/TST as `int-tst`

Other navigation routes remain placeholders.

```bash
npm install
npm run test
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The console is desktop-first. Below the `md` breakpoint the sidebar collapses behind an Open navigation control.

Secret values are never rendered. Mock data only includes rotation status and object names.
