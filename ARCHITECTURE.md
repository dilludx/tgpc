# TGPC Pharmacist Registry — Full Architecture

> **IMPORTANT:** Before making ANY code change, read this document fully and update the Change Log at the bottom when done. This file is the single source of truth for context across sessions.
>
> For the v2 rebuild plans (SvelteKit + Tailwind), see `AGENTS.md`.

## Project Overview

Unofficial tool that scrapes ~87K pharmacist records from the Telangana State Pharmacy Council website, maintains a canonical dataset (`data/rx.json`), syncs to multiple cloud destinations (Supabase, Cloudflare R2, Google Drive), and serves a search UI via Cloudflare Pages.

## Tech Stack

| Layer | Technology |
|---|---|
| Language (backend) | Python 3.9+ |
| Scraping | requests 2.31, beautifulsoup4 4.12, tenacity 8.2 |
| CLI/terminal UI | rich 13.7 |
| Image processing | Pillow 12.2 |
| Database | Supabase (PostgreSQL via REST API) |
| Storage | Supabase Storage, Cloudflare R2 (S3-compatible), Google Drive (rclone) |
| Frontend | Vanilla JS/HTML + ES6 (no framework) |
| CDN libs (frontend) | Supabase JS 2.57, jsPDF 2.5.1, jsPDF-autotable 3.8.2 |
| Hosting | Cloudflare Pages + Workers |
| CI/CD | GitHub Actions (manual `workflow_dispatch`) |
| Linting | Ruff v0.11.5, pre-commit + Husky |
| Notifications | Resend (email API) |

## Directory Map

| Directory | Purpose |
|---|---|
| `tgpc/` | Python package — scraping, management, sync |
| `tests/` | Unit tests (unittest with mocking) |
| `data/` | Canonical dataset (gitignored) |
| `docs/` | Cloudflare Pages site (HTML, JS, CSS, Worker) |
| `.github/workflows/` | CI — `rxsync.yml` |
| `.husky/` | Pre-commit hooks (runs `pre-commit run`) |
| `v2/` | _(future)_ SvelteKit rebuild (see AGENTS.md) |

## Python Pipeline (`tgpc/`)

### Files

| File | Lines | Purpose |
|---|---|---|
| `__init__.py` | 9 | Exports Config, Scraper, Manager. Version 2.0.0 |
| `__main__.py` | 129 | CLI entry: `update`, `sync` (--supabase/r2/gdrive/release/all), `enrich` (--start/stop/force) |
| `utils.py` | 76 | `Config` dataclass (base_url, timeouts, rate limits, proxy), `TGPCError`, `setup_logging()` |
| `scraper.py` | 435 | `PharmacistRecord` dataclass, `RateLimiter` (adaptive delay), `Scraper` class with block detection |
| `manager.py` | 1000 | `FileManager`, `BackupManager`, `Manager` — orchestration of update/sync/enrich |

### CLI Commands

```bash
python3 -m tgpc update          # Scrape → save → sync all destinations
python3 -m tgpc sync --all      # Sync existing data to all destinations
python3 -m tgpc enrich          # Fetch per-record details (education, photo)
```

### Update Flow

1. Health check (connection OK, not blocked)
2. Backup existing `rx.json` to `data/backups/`
3. Scrape fresh records from TGPC website
4. Safety check: abort if new count < 90% of existing
5. Deduplicate by registration number
6. Calculate diff stats (new/changed/removed by category)
7. Save to `data/rx.json`, clean old backups
8. Write outputs to `$GITHUB_OUTPUT` and `data/update_details.json`
9. _(optionally)_ Sync to all destinations

### Sync Destinations

| Destination | Method | Credentials |
|---|---|---|
| Supabase DB | `supabase.table("rx").upsert()` (batch 1000) | `SUPABASE_URL` + `SUPABASE_SECRET_KEY` |
| Supabase Storage | HTTP PUT to `/storage/v1/object/tgpc/rx.json` | same |
| Cloudflare R2 | `aws s3api put-object` via subprocess | `R2_ACCESS_KEY_ID` + `R2_SECRET_ACCESS_KEY` |
| Google Drive | `rclone copyto` via subprocess | `RCLONE_GDRIVE_CONFIG` (base64) |
| GitHub Release | `gh release upload` via subprocess | `GITHUB_TOKEN` |
| Email | Resend API via curl | `RESEND_API_KEY` |

### Enrichment Flow

- Iterates records by serial number
- POSTs to TGPC search endpoint for detailed info
- Extracts: education history, work address, validity dates
- Downloads photos (base64 data URIs or URLs)
- Critical validation: aborts if scraped data doesn't match basic record (name/father/category mismatch)
- Saves per-record JSON to `data/jsn/` and photos to `data/img/`

### Rate Limiting

- `RateLimiter` adjusts delay dynamically: 0.9x on success, 1.5x on failure
- Range: 3.0s–8.0s (configurable)
- `long_break` every 100 requests (60s pause)

## Frontend (`docs/`)

### Pages

| File | Lines | Purpose |
|---|---|---|
| `_worker.js` | 82 | Cloudflare Worker: device detection, routing (`/api/dispatch`, `/api/notice`, `/dispatch`, `/notice`), security headers |
| `config.js` | 4 | Supabase URL + publishable anon key |
| `index.html` | ~1555 | Desktop UI: header with stats (7 categories), search bar, filter chips, table with pagination, PDF/CSV export, scroll-to-top, realtime polling |
| `search.js` | ~740 | Desktop search logic: Supabase queries, filter chips, custom sort (TS/TG/TSDR/TGDR), pagination (50/page), PDF/CSV |
| `mobile.html` | ~560 | Mobile UI: compact header, stats bar, search bar, filter chips with slider, card results |
| `mobile.js` | ~210 | Mobile search logic: Supabase queries, category filter, card rendering, pagination (25/page) |
| `notice.html` | 371 | Notices page: table with date/title/links, year tabs, responsive |
| `notice.js` | 149 | Notices logic: fetches `/api/notice`, filtered by year + search |
| `notice.json` | 204 | 19 notice entries (2018–2026) with dates, titles, links |
| `dispatch.html` | 316 | Dispatch PDF grid, search, year tabs, responsive grid |
| `dispatch.js` | 157 | Dispatch logic: fetches `/api/dispatch`, parses `DLDDMMYYYY.pdf` filenames |
| `pdf.png` | — | PDF icon (used by dispatch link and export button) |
| `excel.png` | — | CSV icon (used by export button) |
| `og-image.png` | — | Open Graph preview image |

### Key Behaviors

- **Cache-first stats**: Load from localStorage immediately, then fetch fresh via Supabase RPC `get_rx_stats`
- **Connection status**: "Busy" → "Live" (with date + clock) or "Offline" on error
- **Realtime polling**: Checks `metadata.last_sync` every 5 minutes; shows notification on change
- **Search**: `SELECT reg_no, name, father_name, category FROM rx WHERE ilike %q% LIMIT 100000`
- **Sort**: Custom prefix order `TS → TG → TSDR → TGDR`, then numeric
- **Pagination**: 50/page desktop, 25/page mobile
- **Export**: jsPDF for PDF, Blob download for CSV
- **Security**: CSP headers in all HTML pages, X-Content-Type-Options, Referrer-Policy, Permissions-Policy

### Worker Routes (`_worker.js`)

| Route | Behavior |
|---|---|
| `/` | Detect mobile UA → serve `mobile.html` or `index.html` |
| `/dispatch` | Serve `dispatch.html` |
| `/notice` | Serve `notice.html` |
| `/api/dispatch` | List objects from R2 `DISPATCH` bucket (prefix `dispatch/`) |
| `/api/notice` | Serve `notice.json` |
| All others | Serve static assets from Cloudflare Pages |

## Data Model

### `PharmacistRecord` (rx.json)

```json
{
  "registration_number": "TS12345",
  "name": "John Doe",
  "father_name": "Richard Doe",
  "category": "BPharm",
  "serial_number": 1
}
```

- Stored in Supabase `rx` table
- Categories: BPharm, DPharm, MPharm, PharmD, QC, QP
- ~87,210 records (~14MB JSON)

### `data/update_details.json` (generated)

```json
{
  "new_details": ["RX001 - Name (BPharm)"],
  "modified_details": [],
  "removed_details": [],
  "new_cat_stats": {"BPharm": 1},
  "rem_cat_stats": {},
  "mod_cat_stats": {}
}
```

## Deployment

- **Current**: `docs/` directory deployed directly on Cloudflare Pages
- **Future**: `v2/` SvelteKit build (see `AGENTS.md`)
- **Domain**: `tgpc.pages.dev` (via Cloudflare Pages)
- **Worker**: `_worker.js` runs at the edge, adding security headers and routing

## Safety Mechanisms

| Mechanism | Where | What it does |
|---|---|---|
| 90% integrity threshold | `manager.py:318` | Aborts if new scrape < 90% of existing record count |
| Field-level mismatch | `manager.py:936-960` | Aborts enrichment if scraped name/father/category don't match rx.json |
| Block detection | `scraper.py:200-208` | Detects captcha/blocked/access-denied responses |
| Health check | `scraper.py:133-167` | Quick connectivity test before starting scrape |
| Backup cleanup | `manager.py:140-154` | Auto-deletes backups older than 30 days |
| Secret isolation | `.gitignore` | `tgpc-creds.sh` never committed |

## Testing

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

13 tests covering:
- `test_scraper.py` (6): request timeouts, basic record parsing (bad rows, missing table), detailed info parsing (education, work, photo, legacy headers)
- `test_manager_update.py` (4): safety guard, sorted deduped output with GitHub outputs, deterministic ordering, soft skip on source unavailable
- `test_manager_enrichment.py` (2): saves pending record, raises on registration mismatch

## Known Notes

- `data/rx.json` is gitignored — restored from CI artifacts or generated by running `python3 -m tgpc update`
- `data/jsn/` and `data/img/` are enrichment artifacts on external volume (`/Volumes/MEDIA/tgpc`) — or configurable via `TGPC_ENRICHMENT_DIR`
- `update_details.json` is gitignored — transient CI artifact

## Git References

- Git tag `rxjson` exists for GitHub Release (data distribution)
- Workflow: `.github/workflows/rxsync.yml` (manual trigger only)

## Change Log

| Date | Change |
|---|---|
| _(first entry on creation)_ | Initial architecture document |

## Status

_This is a reference document for the current (v1) production codebase. For active v2 development tracking, see `AGENTS.md`._
