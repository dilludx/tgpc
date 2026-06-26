# TGPC — Architecture & Developer Context

> **IMPORTANT:** Before making ANY code change, read this document fully and update it when done. This file and `V2.md` are the single sources of truth for context across sessions.

---

## Repository Overview

Code-only repository for the **Telangana Pharmacy Council (TGPC)** pharmacist registration search tool. Tracks source code but excludes data artifacts (e.g., `data/rph.json`, `data/update_details.json`, `data/jsn/`, `data/img/`), credentials, and IDE files.

The project consists of:
- **Python pipeline** (`tgpc/`) — scrapes data from the Telangana Pharmacy Council website, syncs to Supabase, Cloudflare R2, Google Drive, GitHub Release, and sends email notification
- **Frontend** (`ui/`) — production website served via Cloudflare Pages (SvelteKit)
- **Documentation** (`ARCHITECTURE.md`, `V2.md`, `README.md`)

---

## Directory Map

```
tgpc/
├── .github/workflows/rphsync.yml   # Manual CI: single job, scrapes + syncs to 4 destinations + email
├── .husky/                         # Husky pre-commit hook → triggers pre-commit (ruff)
├── .pre-commit-config.yaml         # ruff lint + ruff-format only
├── pyproject.toml                  # Package: tgpc-data-extraction v2.0.0, pinned deps
├── LICENSE                         # (present but not referenced)
├── .gitignore
├── ARCHITECTURE.md
├── V2.md
├── README.md
├── data/
│   ├── rph.json                     # ~87K pharmacist records (JSON array) — gitignored but tracked historically
│   ├── update_details.json         # Sync diff summary — gitignored
│   ├── jsn/                        # Per-record enrichment JSON (deleted, retained in gitignore)
│   ├── img/                        # Per-record photos — gitignored
│   └── backups/                    # Timestamped rph.json backups — gitignored
├── tgpc/                           # Python package (5 files)
│   ├── __init__.py                 # Imports Config, setup_logging, Scraper, Manager; __version__ = "2.0.0"
│   ├── __main__.py                 # CLI: python3 -m tgpc {update, sync, creds}
│   ├── utils.py                    # Config dataclass, TGPCError, setup_logging
│   ├── scraper.py                  # Scraper, RateLimiter, PharmacistRecord, extractors
│   └── manager.py                  # FileManager, BackupManager, Manager (1004 lines)
├── ui/                            # Production frontend (SvelteKit)
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +layout.svelte     # Shared header/footer/stats bar
│   │   │   ├── +page.svelte       # Search page
│   │   │   ├── notice/+page.svelte
│   │   │   ├── dispatch/+page.svelte
│   │   │   └── api/
│   │   │       ├── dispatch/+server.ts  # R2 bucket listing proxy
│   │   │       └── notice/+server.ts    # Static notice JSON
│   │   └── lib/
│   │       ├── supabase.ts
│   │       ├── types.ts
│   │       └── utils.ts
│   ├── static/
│   │   ├── favicon.svg, .ico, -192.png
│   │   ├── pdf.svg, og-image.png, notice.json
│   ├── wrangler.toml
│   └── svelte.config.js
├── docs/                           # v1 (legacy, retained as reference)
├── tests/
│   ├── test_scraper.py             # 7 tests: timeouts, record parsing, empty tables, no-records, detailed info, legacy headers, missing tables
│   ├── test_manager_update.py      # 4 tests: safety guard, dedup/sorting, deterministic order, source-unavailable
│   ├── test_manager_enrichment.py  # 2 tests: enrichment save, registration mismatch
│   └── sanity.py                   # Quick sanity check (not a unittest)
└── (credentials stored in macOS Keychain, not files)
```

---

## Python Backend

### Dependency Graph

```
__main__.py ─── Manager ─── Config (utils.py)
                     ├── FileManager (load/save rph.json as JSON array)
                     ├── BackupManager (timestamped backups, cleanup after 30 days)
                     ├── Scraper (scraper.py)
                     │       ├── RateLimiter (adaptive delay 3-8s)
                     │       ├── PharmacistRecord dataclass
                     │       ├── extract_basic_records() — table parser via BeautifulSoup
                     │       └── extract_detailed_info() — per-record detail page parser
                     └── Sync methods:
                           ├── sync_to_supabase() — upsert to rph table, update metadata.last_sync
                           ├── sync_to_supabase_storage() — upload rph.json to Supabase Storage
                           ├── sync_to_r2() — aws s3api put-object to Cloudflare R2
                           ├── sync_to_gdrive() — rclone copyto Google Drive
                           ├── sync_to_release() — gh release upload rph.json
                           └── sync_to_email() — Resend API email with change details
```

### Entry Point: `tgpc/__main__.py`

```bash
python3 -m tgpc update              # Health check → backup → scrape → dedup → safety guard → save → sync to all destinations + email
python3 -m tgpc update --no-sync    # Scrape only, skip cloud sync
python3 -m tgpc sync                # Sync to all destinations
```

`load_credentials()` reads credentials from macOS Keychain via `security` command and exports vars into `os.environ`.

### `tgpc/utils.py` — Config & Exceptions

```python
class TGPCError(Exception):
    def __init__(self, message: str, original_error: Optional[Exception] = None)

@dataclass
class Config:
    base_url: str = "https://www.pharmacycouncil.telangana.gov.in"
    connect_timeout: int = 20
    read_timeout: int = 180
    max_retries: int = 3
    proxy_url: Optional[str] = None        # from TGPC_PROXY_URL, HTTPS_PROXY, or HTTP_PROXY
    min_delay: float = 3.0                 # RateLimiter floor
    max_delay: float = 8.0                 # RateLimiter ceiling
    long_break_after: int = 100            # Requests before long break (not actively used in RateLimiter)
    long_break_duration: int = 60
    data_directory: str = "data"
    enrichment_directory: str = "data"     # Override via TGPC_ENRICHMENT_DIR
    user_agent: str = "Mozilla/5.0 ..."
```

Config is loaded via `Config.load()` classmethod (reads env vars for proxy and enrichment dir). It does NOT contain Supabase credentials — those are read from env vars at sync time.

### `tgpc/scraper.py` — Data Extraction

**PharmacistRecord** dataclass:
- Core fields: `registration_number`, `name`, `father_name`, `category`, `serial_number`
- Optional detail fields: `gender`, `validity_date`, `status`, `education` (list of dicts), `work_experience` (dict)
- `to_dict()` → strict 5-field dict (for `rph.json`)
- `to_detailed_dict()` → 10-field dict (for enrichment JSON files)

**RateLimiter:**
- Adaptive delay: starts at `min_delay` (3s), adjusts based on success/failure
- On success: `current_delay *= 0.9` (faster)
- On failure: `current_delay *= 1.5` (slower, capped at `max_delay` 8s)
- Jitter: `delay * random.uniform(0.8, 1.2)`

**Scraper:**
- Uses `requests.Session` with connection pooling (10 pools, 10 max)
- Two API endpoints (constructed from `config.base_url`):
  - `total`: `{base_url}/pharmacy/srchpharmacisttotal` — full listing table
  - `search`: `{base_url}/pharmacy/getsearchpharmacist` — detail search (POST with `registration_no`)
- `health_check(timeout=30)` → `bool` — hits total endpoint, checks for blocked indicators
- `_request(method, url)` → `requests.Response` — wrapped with `@tenacity.retry` (3 attempts, exponential backoff 2-10s), calls `rate_limiter.wait()` before each request, runs block detection (status, access denied, captcha, short response)
- `extract_basic_records()` → `List[PharmacistRecord]` — fetches total endpoint, finds `<table id="tablesorter-demo">` (fallback to any `<table>`), extracts rows with ≥5 cells (serial, reg_no, name, father, category)
- `extract_detailed_info(reg_no, img_dir)` → `Optional[PharmacistRecord]` — POSTs to search endpoint, parses detail page for: registration table (name, father, gender, category, status, validity), education table (qualification → category, university, college, years, HT No), work experience table (address, state, district, pin code), and photos (base64 data URI or URL download → saved to `img_dir`)

### `tgpc/manager.py` — Orchestration (~1004 lines)

**`DataIntegrityError`** — raised when enrichment scraped data doesn't match the expected registration.

**`FileManager`** — handles local JSON storage:
- `save(records, filename)` → JSON array with `indent=2, ensure_ascii=False`
- `load(filename)` → deserializes `PharmacistRecord` list

**`BackupManager`** — timestamped backups (format: `rph_backup_YYYYMMDD_HHMMSS.json`), cleanup deletes files older than 30 days.

**`Manager.run_daily_update()`** — the core update workflow:
1. **Health check** → if blocked, writes `update_status=blocked` to GITHUB_OUTPUT, returns `"blocked"`
2. **Backup** existing `rph.json`
3. **Scrape** fresh data via `scraper.extract_basic_records()`
4. **Source unavailable check** — if scrape raises exception matching `_is_source_unavailable_error()` (timeouts, connection errors, 429/5xx), writes `source_unavailable`, preserves existing data, returns `"source_unavailable"`
5. **Empty check** — if no records returned, returns `"empty_scrape"`
6. **Safety guard** — if fresh count < 90% of existing, aborts with `"safety_abort"`
7. **Deduplicate** by registration number, sort by serial_number
8. **Calculate diffs** — new, removed, modified records with per-category stats
9. **Save** new data to `rph.json`, cleanup old backups
10. **Write `update_details.json`** with change details
11. **Write GITHUB_OUTPUT** for CI consumption
12. Returns `"updated"`

**`Manager.sync_to_supabase()`**:
- Reads `SUPABASE_URL`, `SUPABASE_SECRET_KEY` from env
- Creates Supabase client, batch upserts to `rph` table (1000/batch, `on_conflict="registration_number"`)
- Updates `metadata.last_sync` timestamp

**`Manager.sync_to_supabase_storage()`**:
- POSTs `rph.json` to `{url}/storage/v1/object/tgpc/rph.json` with `x-upsert: true`

**`Manager.sync_to_r2()`**:
- Reads `CLOUDFLARE_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`
- Runs `aws s3api put-object --endpoint-url https://{account_id}.r2.cloudflarestorage.com --bucket tgpc --key rph.json`

**`Manager.sync_to_gdrive()`**:
- Reads `RCLONE_GDRIVE_CONFIG` (base64-encoded rclone config file)
- Writes to temp file, runs `rclone copyto rph.json gdrive:tgpc/rph.json`
- Cleans up temp config

**`Manager.sync_to_release()`**:
- Uses `gh release` CLI to upload `rph.json` to GitHub Release tag `rphjson`
- Creates release if it doesn't exist, updates title with record count

**`Manager.sync_to_email()`**:
- Reads `RESEND_API_KEY`, `NOTIFICATION_EMAIL` from env
- Reads `_last_update_details` (set by `run_daily_update()`)
- Builds HTML + plain text email with categorized change details (new/changed/removed by category)
- Sends via Resend API (POST to `https://api.resend.com/emails`)
- Capped at 200 items per section in email

**`Manager.run_enrichment(start, stop, force)`**:
- Health check → queries Supabase `rph` table for records missing enrichment fields
- Load `rph.json`, filter pending records sorted by serial
- Optionally restrict to `start`/`stop` serial range
- `force` flag re-extracts even already-done records
- Calls `_process_records_sequential()` → for each record: scrapes detail page, validates registration/name/father/category match (raises `DataIntegrityError` on mismatch), upserts all 10 fields directly to Supabase, saves photo to `data/img/`

### `tgpc/__main__.py` — CLI

Uses `argparse` with subparsers:
- `update` → `manager.run_daily_update()`, optionally `--no-sync`
- `sync` → sync to all destinations
- `creds` → manage credentials in macOS Keychain (`set`, `list`, `delete`)

Credentials loaded from macOS Keychain via `load_credentials()` before sync operations. Auto-enrich runs automatically after successful `update`.

### Dependencies (`pyproject.toml`)

```toml
dependencies = [
    "requests==2.31.0",
    "beautifulsoup4==4.12.3",
    "tenacity==8.2.3",        # @retry decorator in scraper._request
    "supabase==2.28.0",       # create_client for sync_to_supabase
    "Pillow==12.2.0",         # Image.open() in validate_batch_files
]
```

### Supabase Schema

```sql
CREATE TABLE rph (
  registration_number TEXT PRIMARY KEY,
  name TEXT,
  father_name TEXT,
  category TEXT,
  serial_number TEXT
);

CREATE TABLE metadata (
  key TEXT PRIMARY KEY,
  value TEXT
);

-- RPC function (created via Supabase dashboard):
-- get_rph_stats() → { total: int, categories: { BPharm: int, DPharm: int, MPharm: int, PharmD: int, QC: int, QP: int } }
```

RLS allows anonymous `SELECT` on `rph` and `metadata` tables. The Publishable Key in `config.js` is safe to commit.

### Data File Formats

**`rph.json`** — standard JSON array:
```json
[
  {"registration_number": "TG12345", "name": "...", "father_name": "...", "category": "BPharm", "serial_number": 12345},
  ...
]
```

**`update_details.json`** — written by `run_daily_update()`:
```json
{
  "new_details": ["TG12345 - Name (BPharm)", ...],
  "modified_details": ["TG12346 - Other Name (DPharm)", ...],
  "removed_details": [],
  "new_cat_stats": {"BPharm": 5, "DPharm": 2},
  "rem_cat_stats": {},
  "mod_cat_stats": {"BPharm": 1}
}
```

### Environment Variables

| Variable | Used By | Purpose |
|---|---|---|
| `SUPABASE_URL` | `sync_to_supabase()`, CI | Supabase project URL |
| `SUPABASE_SECRET_KEY` | `sync_to_supabase()`, CI | Service role key (NOT the anon key) |
| `CLOUDFLARE_ACCOUNT_ID` | `sync_to_r2()`, CI | R2 endpoint account ID |
| `R2_ACCESS_KEY_ID` | `sync_to_r2()`, CI | R2 S3-compatible access key |
| `R2_SECRET_ACCESS_KEY` | `sync_to_r2()`, CI | R2 S3-compatible secret key |
| `RCLONE_GDRIVE_CONFIG` | `sync_to_gdrive()`, CI | Base64-encoded rclone Google Drive config |
| `RESEND_API_KEY` | `sync_to_email()`, CI | Resend.com API key |
| `NOTIFICATION_EMAIL` | `sync_to_email()`, CI | Email recipient for sync report |
| `TGPC_PROXY_URL` | `Config.load()` | Optional outbound proxy for scraping |
| `TGPC_ENRICHMENT_DIR` | `Config.load()` | Override enrichment working directory |

---

## Frontend (SvelteKit — Production)

Built with SvelteKit 5 + Tailwind CSS v4 + TypeScript. Full design spec in `V2.md`.

### Stack

| Layer | Technology |
|---|---|
| Framework | SvelteKit 5 (`@sveltejs/adapter-cloudflare`) |
| Styling | Tailwind CSS v4 |
| Database | Supabase (anon key with RLS — `SELECT` only) |
| Hosting | Cloudflare Pages (build: `ui/.svelte-kit/cloudflare`) |
| Env vars | `PUBLIC_SUPABASE_URL`, `PUBLIC_SUPABASE_PUBLISHABLE_KEY` |

### Routes

| Path | Description |
|---|---|
| `/` | Search: table (desktop) / cards (mobile), filter chips, pagination, PDF/CSV export |
| `/notice` | Notices table with year tabs, search, link badges |
| `/dispatch` | Dispatch PDF grid with year tabs, search |
| `/api/dispatch` | JSON — lists PDFs from R2 bucket (`dispatch/` prefix) |
| `/api/notice` | JSON — notice data from `static/notice.json` |

### Key Features

- **Stats bar** — 7 category cards with live counts from Supabase RPC, cached in localStorage
- **Realtime** — Supabase Realtime subscription on `metadata` table for live stats/timestamp updates
- **Search** — client-side Supabase query (min 3 chars), sorted by prefix priority then numeric, paginated 50/page (25 mobile)
- **Export** — PDF via jsPDF + jspdf-autotable, CSV via Blob download with UTF-8 BOM
- **Responsive** — single component, CSS toggles between table and cards at 768px
- **Connection status** — status pill (Busy/Live/Offline) with live clock
- **Design** — exact colors, fonts, badges, spacing as documented in V2.md

---

## CI/CD

### GitHub Actions: `.github/workflows/rphsync.yml`

**Trigger:** `workflow_dispatch` (manual). Input: `force_sync` (boolean, default false).

**Single job `rphsync`** with these steps:

1. **Checkout** repository
2. **Install Python deps** (`pip install -e .` + `pip install supabase`)
3. **Create data directory** (`mkdir -p data/backups`)
4. **Restore artifact** — `gh run download` artifact `rph-data` if `data/rph.json` doesn't exist locally
5. **Run data update** — `python3 -m tgpc update` (or force-skip if `force_sync` is true, sets GITHUB_OUTPUT directly)
6. **Sync to Supabase DB** (condition: `update.success == True`) — `python3 -m tgpc sync` (but only Supabase sync is done inline, not the full CLI sync)
7. **Upload to Supabase Storage** — curl POST to storage bucket `tgpc`
8. **Upload to Cloudflare R2** — `aws s3api put-object`
9. **Upload to Google Drive** — `rclone copyto` (also uploads `jsn-{max_serial}.zip` and `img-{max_serial}.zip` if they exist, cleans old versions)
10. **Clean old artifact** — deletes previous `rph-data` artifacts
11. **Upload new artifact** — `rph-data` with 90-day retention
12. **Create update summary** — Python script reads `update_details.json`, writes formatted markdown to `GITHUB_STEP_SUMMARY`
13. **Send email notification** — inline Python script builds HTML email and sends via Resend API
14. **Notify on failure** — prints failure message

**Secrets:**
| Secret | Purpose |
|---|---|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SECRET_KEY` | Supabase service role key |
| `R2_ACCESS_KEY_ID` | R2 S3-compatible access key |
| `R2_SECRET_ACCESS_KEY` | R2 S3-compatible secret key |
| `CLOUDFLARE_ACCOUNT_ID` | R2 endpoint account ID |
| `RCLONE_GDRIVE_CONFIG` | Base64-encoded rclone GDrive config |
| `RESEND_API_KEY` | Resend email API key |
| `NOTIFICATION_EMAIL` | Email recipient |

---

## Testing

```bash
python3 -m pytest tests/ -v
```

13 test methods across 3 files:

| File | Tests | What's tested |
|---|---|---|
| `test_scraper.py` | 7 | `_request` timeouts, `extract_basic_records` (no table, bad rows, fallback table), `extract_detailed_info` (no records, full parse with photo/education/work, legacy headers, missing tables) |
| `test_manager_update.py` | 4 | Safety guard (90% threshold), dedup/sort/GITHUB_OUTPUT, deterministic detail ordering, source-unavailable skip |
| `test_manager_enrichment.py` | 2 | Enrichment saves first pending record, raises DataIntegrityError on registration mismatch |

All tests use mocking (no real HTTP or Supabase calls). The `supabase` module is mocked globally before imports.

`sanity.py` — standalone script (not a test), parses sample HTML and verifies one record extraction. Run manually.

---

## Pre-commit

Only `ruff` (lint + fix) and `ruff-format` via `astral-sh/ruff-pre-commit` v0.11.5. No Black, no trailing-whitespace, no end-of-file-fixer hooks.

---

---

## Deployment

| Component | Method | URL |
|---|---|---|---|
| Frontend | Cloudflare Pages (auto-deploy from `main`, builds `ui/`) | `https://tgpc.pages.dev` |
| CI/CD | GitHub Actions (manual trigger) | `github.com/dilludx/tgpc/actions` |
| Data download | GitHub Release | Tag `rphjson`, file `rph.json` |

---

## Change Log

| Date | Change |
|---|---|
| _(Add when repo changes)_ | Description of architectural change |

---

## See Also

- `UI.md` — frontend architecture, component specs, design system
- `README.md` — Project overview and quick-start
