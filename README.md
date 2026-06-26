# TGPC RPh Registry

Scrapes the [Telangana Pharmacy Council](https://www.pharmacycouncil.telangana.gov.in) pharmacist registry, syncs to Supabase + R2 + GDrive, and serves a search UI at [tgpc.pages.dev](https://tgpc.pages.dev).

## Repo

| What | Where |
|---|---|
| Python pipeline (scraper, sync, enrichment) | `tgpc/` |
| SvelteKit frontend | `ui/` |
| CI/CD | `.github/workflows/rphsync.yml` |

## Quick Start

```bash
git clone https://github.com/dilludx/tgpc.git && cd tgpc
python3 -m venv venv && source venv/bin/activate && pip install -e .

python3 -m tgpc update           # Scrape → sync all destinations
python3 -m tgpc update --no-sync # Scrape only
python3 -m tgpc sync             # Sync existing data to all destinations

cd ui && npm i && npm run dev    # Frontend dev server
```

Credentials stored in macOS Keychain via `python3 -m tgpc creds set`.

## Frontend

SvelteKit 5 + Tailwind v4 + Supabase. Source in `ui/`. Deploys via Cloudflare Pages (auto-build from `main`, output `ui/.svelte-kit/cloudflare`).

## Disclaimer

**NO LIABILITY.** Unofficial tool not affiliated with TGPC. Data for reference only. Operated under fair dealing (Indian Copyright Act, 1957, Section 52).
