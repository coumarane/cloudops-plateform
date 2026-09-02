# Design System: CloudOps Platform
**Project ID:** 16290258496511126264

## 1. Visual Theme & Atmosphere

Corporate, utilitarian, high-density operations cockpit for SREs and platform engineers. The UI is information-first: dense tables, compact status chips, and systematic alignment. Color is reserved for provider identity, environment class, and risk. Production (NPD/PRD) must be immediately obvious. Secret values are never shown.

## 2. Color Palette & Roles

- Deep Slate (`#0F172A`) — sidebar, navigation anchor
- Canvas Gray (`#F7F9FB`) — main background
- Surface White (`#FFFFFF`) — cards, tables
- Action Blue (`#0058BE`) — primary interactive / selected nav
- AWS Orange (`#FF9900`) — AWS provider accent only
- Alibaba Blue (`#1677FF`) — Alibaba provider accent only
- Production Red (`#DC2626`) — PRD/NPD stamps, production column headers, critical alerts
- Healthy Green (`#15803D`) — healthy clusters/apps
- Warning Amber (`#D97706`) — degraded, expiring certs, rotation due
- Critical Red (`#BA1A1A`) — unreachable, failed jobs, open critical alerts
- Neutral Outline (`#C6C6CD`) — table rules, non-production chrome

## 3. Typography Rules

- Inter for UI labels, headlines, and table data (compact: 13px table, 11px uppercase stamps)
- JetBrains Mono for cluster names, IDs, timestamps, and technical strings
- Environment badges (DEV, INT/TST, UAT, NPD, PRD) use uppercase 11px bold stamps

## 4. Component Stylings

- **Buttons:** Sharp, slightly softened corners; primary for Investigate; ghost for filters
- **Cards/Tables:** Tight 8–12px padding, 1px outline, no heavy shadows
- **Status chips:** Green/amber/red with icon + short count; em-dash when not applicable
- **Secrets:** Rotation state and due date only. Never render secret values, tokens, keys, or passwords

## 5. Layout Principles

- Persistent 240px dark sidebar; fluid 12-column main canvas
- 4px base unit; desktop-first 1440px+
- Global dashboard groups AWS (AMER, EMEA, APAC) and Alibaba (China)
- Environment columns always: DEV, INT/TST, UAT, NPD, PRD
- Non-production vs production column groups are visually separated

## 6. Environment Details

Screen ID `6d06bf5d9bd64ba1bc6e6b8048487364` (AWS EMEA UAT) is the source design for `/environments/{provider}/{region}/{environment}`.

Required tabs, in order: Overview, Clusters, Applications, Secrets, Certificates, Deployments, Pipelines, GitHub, Health, Audit.

The identity header must stamp NON-PRODUCTION or PRODUCTION. Production environments use the production red chrome. Secret values are never shown; rotation status and object names only.

## 7. Secrets Management

Screen ID `5a498af96dc742bfbb21a9d4b13659ca` (AWS AMER PRD) is the source design for `/secrets`.

Row actions: Update, Rotate, Validate, Rotation History. Secret values are never shown or accepted.

PRD mutations show a strong production warning and require explicit confirmation.

## 8. Certificate Monitoring

Screen ID `b43e64b6bb56414380ec5e695d76dad5` is the source design for `/certificates`.

The catalog covers AWS AMER, AWS EMEA, AWS APAC, and Alibaba China. Columns: certificate, domain, provider, region, environment, cluster, namespace, issuer, expiration date, days remaining, renewal status.

Production environments (NPD/PRD) use production stamps. Featured exception: AWS AMER PRD `ingress-tls-wildcard` expiring in 12 days.

Private keys are never shown.

## 9. Remaining console catalogs

All primary nav routes are implemented in `apps/web`. Fleet catalogs use Provider → Region → Environment filters, cover AWS AMER / EMEA / APAC and Alibaba China, stamp production (NPD/PRD), and never display secret values.

| Route | Screen ID | Title |
|---|---|---|
| `/infrastructure` | `ea67d2a3833c4683af73a99a2425a3c6` | Infrastructure Inventory |
| `/clusters` | `d99c299407d24fc9b1517aafe50715ce` | Cluster Management Fleet |
| `/applications` | `90f089e5523548f682160ac10de64f4a` | Application Health Explorer |
| `/health-checks` | `098e712b12f74ee19f4f662f7e2571d7` | Health Checks & Monitoring |
| `/deployments` | `7ec467752b254edeb28114dde0679be6` | Deployments: Rollout History |
| `/pipelines` | `458cc123554f4be9994960760c4179c7` | DevOps Pipeline Central |
| `/github` | `bc89840e83cc4fd698594aee2cc21594` | GitHub Operations Hub |
| `/jobs` | `5e1cef304d9b416e8a99901e9876016c` | Batch Jobs & Operations Monitoring |
| `/alerts` | `528dcc011a2e47baad5cd4eac8f74616` | Operations Centre: Alerts |
| `/audit` | `8f9fcbbe73d741dfb6ec7f4d4fffa88d` | Audit Logs Console |
| `/administration` | `2c1ff965c545494989e01e5f93c322d0` | Administration: Console Access & Integrations |

Known exceptions stay aligned with the dashboard: EMEA UAT cluster unreachable, APAC PRD `payment-svc` failed, EMEA NPD `data-sync` failed, AMER INT/TST `auth-build` failed. GitHub tokens, pipeline secrets, and private keys are never shown.
