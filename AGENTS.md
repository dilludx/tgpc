# AGENTS.md — Repository Guidelines

These instructions apply to any human or AI agent working in this repository.

## Project

TGPC RPh Registry — public search portal for the Telangana State Pharmacy Council
pharmacist registry. SvelteKit 5 + Tailwind v4 + Supabase frontend (`ui/`),
Python scraping/enrichment pipeline (`tgpc/`). Pushes to `main` auto-deploy to
Cloudflare Pages (`tgpc.pages.dev`).

## MANDATORY: Brand Colors

Every screen, component, export, and new UI code MUST use only the in-house TGPC
colors. Do not invent or hardcode any new hex values.

| Token | Hex | Usage |
|---|---|---|
| tgpc green | `#00cc66` | Primary, active states |
| tgpc red | `#ef4444` | Destructive, inactive |
| tgpc grey | `#9ca3af` | Secondary text ("Registry") |
| tgpc blue | `#2563eb` | Links, RPC numbers |

Supporting neutrals: `#111827` text, `#6b7280` muted, `#e5e7eb` border,
`#f4f4f5` rows, `#ffffff` bg, `#00b359` green-dark.

**Rules:**
- Prefer the `TGPC` export from `ui/src/lib/colors.ts` (`TGPC.green`, etc.).
- Do NOT use off-brand colors such as `#dc2626` or `#16a34a`.
- Full details: `ui/src/lib/BrandColors.md` (single source of truth).
- Exception: `CATEGORY_COLORS` in `ui/src/lib/colors.ts` are brand-derived
  data-visualization hues (already on-palette).

## Commands

- Frontend dev: `cd ui && npm run dev`
- Type check: `cd ui && npm run check` (svelte-check, must stay at 0 errors)
- JS/Svelte lint: `cd ui && npm run lint` (eslint, 0 errors; `require-each-key`
  warnings are accepted debt)
- Unit tests: `cd ui && npm run test:unit`
- Data pipeline: `make` targets (see `Makefile`); run via `cd tgpc` as needed.

## Workflow

- Do not commit or push unless explicitly asked.
- When verifying UI changes, the page must load 200 and `svelte-check` must not
  introduce new errors.
