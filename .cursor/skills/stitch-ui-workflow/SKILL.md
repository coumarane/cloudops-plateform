---
name: stitch-ui-workflow
description: Use Stitch to generate or refine major CloudOps Platform UI screens before implementing them in Next.js, TypeScript, and Tailwind.
---

# Stitch UI Workflow

Use this skill when the task involves a new screen, a substantial dashboard change, or a meaningful redesign of an existing UI flow.

## Objectives

1. Use Stitch before writing substantial frontend implementation code.
2. Keep the output aligned with the CloudOps Platform design system and domain model.
3. Convert the selected design into production-quality React components instead of copying generated HTML directly.

## Workflow

1. Read `README.md` if product constraints or navigation are unclear.
2. Identify the target user flow, required data, and whether the screen is production or non-production oriented.
3. Use Stitch to generate or refine the screen concept first.
4. Evaluate the result against these project requirements:
   - Providers: AWS and Alibaba
   - AWS regions: `AMER`, `EMEA`, `APAC`
   - Alibaba region: `China`
   - Environments: `DEV`, `INT/TST`, `UAT`, `NPD`, `PRD`
   - Production must be visually distinct from non-production
   - Secret values must never be shown
5. Iterate in Stitch until the structure and operational states are clear.
6. Implement the selected direction in Next.js + TypeScript + Tailwind using reusable components.
7. Refactor any generated structure for maintainability, responsiveness, and accessibility.

## Guardrails

- Do not paste Stitch HTML into the application unchanged.
- Reuse the existing CloudOps Platform design language.
- Prefer reusable layout, table, filter, card, and status components.
- Keep dashboards operational and information-dense rather than marketing-oriented.
- Make `PRD` and other production states immediately obvious.

## Deliverables

- A Stitch-assisted screen concept or refinement.
- Production-ready frontend code aligned to that concept.
