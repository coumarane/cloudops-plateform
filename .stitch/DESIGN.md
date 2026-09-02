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
