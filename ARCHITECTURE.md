# TGPC — Architecture & Developer Context

> **IMPORTANT:** Before making ANY code change, read this document fully and update it when done. This file is the single source of truth for context across sessions.

---

## Repository Overview

Code-only repository for the **Telangana Pharmacy Council (TGPC)** pharmacist registration search tool. Tracks source code but excludes data artifacts (e.g., `data/rph.json`, `data/update_details.json`, `data/jsn/`, `data/img/`), credentials, and IDE files.

The project consists of:
- **Python pipeline** (`tgpc/`) — scrapes data from the Telangana Pharmacy Council website, syncs to Supabase, Cloudflare R2, Google Drive, GitHub Release, and sends email notification
- **Frontend** (`ui/`) — production website served via Cloudflare Pages (SvelteKit)
- **Documentation** (`ARCHITECTURE.md`, `CODE_REVIEW.md`, `README.md`)

---

## Directory Map

```
tgpc/
├── .github/dependabot.yml          # Automated dependency-update PRs (pip, npm, actions)
├── .github/workflows/rphsync.yml   # Manual CI: single job, scrapes + syncs to 4 destinations + email
├── .github/workflows/python.yml    # ruff + pytest + pip-audit dependency scan
├── .github/workflows/ui.yml        # eslint + svelte-check + brand-color gate + tests + npm audit
├── .husky/                         # Husky pre-commit hook → triggers pre-commit (ruff)
├── .pre-commit-config.yaml         # ruff lint + ruff-format only
├── pyproject.toml                  # Package: tgpc-data-extraction v2.0.0, pinned deps
├── LICENSE                         # (present but not referenced)
├── .gitignore
├── ARCHITECTURE.md
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
│   ├── test_manager_update.py      # 7 tests: safety guard, dedup/sorting, deterministic order, source-unavailable, +3 sync return-value regressions
│   ├── test_manager_enrichment.py  # 3 tests: enrichment save, registration mismatch, null serial_number regression
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
- Builds an AES-256 encrypted zip of `rph.json` in-process via `pyzipper` (password from `RELEASE_PASSWORD`, never on a process argv) and uploads it to GitHub Release tag `rphjson` via `gh`
- Creates release if it doesn't exist, updates title with record count
- Skips (returns True) when `RELEASE_PASSWORD` is unset

**`Manager.sync_to_email()`**:
- Reads `RESEND_API_KEY`, `NOTIFICATION_EMAIL` from env
- Reads `_last_update_details` (set by `run_daily_update()`)
- Builds HTML + plain text email with categorized change details (new/changed/removed by category)
- Sends via Resend API using `requests` (POST to `https://api.resend.com/emails`)
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
    "pyzipper==0.3.6",        # AES-256 release archive in sync_to_release
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

**⚠️ RLS verification (do this in the Supabase dashboard → SQL Editor):**

The frontend uses the **publishable/anon key** against 87k rows, so protection from
unauthorized writes/deletes depends entirely on RLS being enabled. Run this to
confirm the right posture (public **read-only**, no writes from anon):

```sql
-- Confirm RLS is enabled and anon can only SELECT
select schemaname, tablename, rowsecurity
from pg_tables
where schemaname = 'public' and tablename in ('rph', 'metadata');

-- Anon should have a SELECT (read) policy and NO insert/update/delete policy.
-- If the query below returns any rows for rph/metadata, tighten it:
select polname, polcmd, pg_get_expr(polqual, polrelid)
from pg_policy
join pg_class on pg_class.oid = polrelid
join pg_namespace on pg_namespace.oid = relnamespace
where nspname = 'public' and relname in ('rph', 'metadata');

-- Correct anon posture — read-only. Run these if the SELECT policy is missing:
alter table public.rph enable row level security;
alter table public.metadata enable row level security;

create policy "anon select rph" on public.rph
  for select to anon using (true);

create policy "anon select metadata" on public.metadata
  for select to anon using (true);
```

The service-role key (used server-side / by the Python pipeline) bypasses RLS, so
writes continue to work via `sync_to_supabase()`.

**✅ Verified state (2026-09-01):** RLS is enabled on both tables
(`rowsecurity = true` on `rph` and `metadata`). Six policies are in place —
the anon/public/`realtime` roles have **read-only** (`SELECT`) policies only,
and the service role has full access. This is the correct read-only posture for
a public search portal; the publishable/anon key is safe to expose.

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

Built with SvelteKit 5 + Tailwind CSS v4 + TypeScript.

### Stack

| Layer | Technology |
|---|---|
| Framework | SvelteKit 5 (`@sveltejs/adapter-cloudflare`) |
| Styling | Tailwind CSS v4 |
| Database | Supabase (anon key with RLS — `SELECT` only) |
| Hosting | Cloudflare Pages (build: `ui/.svelte-kit/cloudflare`) |
| Env vars | Public: `PUBLIC_SUPABASE_URL`, `PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `PUBLIC_R2_PHOTO_BASE`. Server-side (Pages dashboard): `ADMIN_SECRET` (preferred) or `QUOTA_SECRET` for the admin session; `ADMIN_LINK_PHARMACIST_URL` / `ADMIN_LINK_EMAIL_VERIFY_URL` for the two credential-bearing admin links (no token fallbacks exist in code) |

### Routes

| Path | Description |
|---|---|
| `/` | Search: table (desktop) / cards (mobile), filter chips, pagination, PDF/CSV export |
| `/notice` | Notices table with year tabs, search, link badges |
| `/dispatch` | Dispatch PDF grid with year tabs, search |
| `/admin` | Operator console (usage report + internal TGPC links); payload served server-side only to a valid session |
| `/api/admin` | POST login (rate-limited, constant-time compare) issues an HttpOnly signed-cookie session; DELETE logs out |
| `/api/usage` | Service quota report; fails closed without `ADMIN_SECRET`/`QUOTA_SECRET`; accepts session cookie or `x-quota-secret` header |
| `/api/dispatch` | JSON — lists PDFs from R2 bucket (`dispatch/` prefix); stale-flagged fallback list when the binding is unavailable |
| `/api/notice` | JSON — notice data from `static/notice.json` |

Server-only modules under `ui/src/lib/server/` (`auth.ts`, `adminLinks.ts`, `rateLimit.ts`) are compiler-enforced: SvelteKit fails the build if client code imports them.

### Key Features

- **Stats bar** — 7 category cards with live counts from Supabase RPC, cached in localStorage
- **Realtime** — Supabase Realtime subscription on `metadata` table for live stats/timestamp updates
- **Search** — client-side Supabase query (min 3 chars), sorted by prefix priority then numeric, paginated 50/page (25 mobile), results capped at 500
- **Export** — PDF via jsPDF + jspdf-autotable; CSV via Blob download with formula-injection guard
- **Security headers** — applied globally in `hooks.server.ts` (+ `ui/static/_headers` for static assets):
  - **CSP** with a per-request **nonce** for inline scripts on route HTML (`script-src 'self' 'nonce-<n>' 'strict-dynamic'`) plus `img-src`/`connect-src` allowlists for the R2 photo CDN and Supabase origin
  - `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Strict-Transport-Security`, `Permissions-Policy`
  - `Cross-Origin-Opener-Policy: same-origin` + `Cross-Origin-Resource-Policy: same-origin` (cross-origin isolation)
- **Admin auth** — HMAC-SHA256 signed, expiring session cookie (`HttpOnly`/`SameSite=Strict`); login uses constant-time comparison + a fixed 250ms delay on every attempt (timing side-channel + brute-force throttling); best-effort in-isolate rate limiter (defence-in-depth — pair with a Cloudflare Rate Limiting rule on `/api/admin`)
- **Responsive** — single component, CSS toggles between table and cards at 768px
- **Connection status** — status pill (Busy/Live/Offline) with live clock
- **Design** — TGPC brand palette only, machine-enforced by `npm run check:colors`

---

## CI/CD

### GitHub Actions: `.github/workflows/rphsync.yml`

**Trigger:** `workflow_dispatch` (manual). Input: `force_sync` (boolean, default false).

**Single job `rphsync`** with these steps:

1. **Checkout** repository
2. **Install Python deps** (`pip install -e .` + `supabase` + `awscli`)
3. **Setup Cloudflare WARP** — install, register, connect (outbound routing for scraping/sync)
4. **Create data directory** (`mkdir -p data/backups`)
5. **Restore artifact** — `gh run download` artifact `rph-data` if `data/rph.json` doesn't exist locally
6. **Run data update** — `python3 -m tgpc update`; when `force_sync` is true and local data exists, runs `python3 -m tgpc sync` instead. All cloud syncs happen inside the CLI (delta to Supabase; Storage/R2/GDrive/Release/email only when there are changes); any destination failure exits non-zero and fails the job
7. **Upload data artifact** — `rph-data` with 90-day retention (`if: always()`)
8. **Clean up update details** — `rm -f data/update_details.json`
9. **Notify on failure** — prints failure message

Job permissions: `actions: write`, `contents: write` (release upload).

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
| `RELEASE_PASSWORD` | Password for the encrypted release zip |

**Quality gates:**
- `.github/workflows/ui.yml` runs on push/PR touching `ui/` — ESLint + brand-color gate (`check:colors`) + svelte-check + the 18 unit tests + a build with placeholder PUBLIC env vars (real values live in the Cloudflare Pages dashboard) + `npm audit --audit-level=high`. Auto-deploys from `main` build `ui/`.
- `.github/workflows/python.yml` runs on push/PR touching `tgpc/`, `tests/`, or `pyproject.toml` — `ruff check`, `ruff format --check` (pinned 0.11.5, matching pre-commit), the full pytest suite, and a `pip-audit` dependency vulnerability scan.

**Dependency updates (`.github/dependabot.yml`):**
Dependabot opens weekly PRs for the Python (`pip`), frontend (`npm`), and GitHub Actions ecosystems, targeting Monday 06:00 IST. Combined with the `pip-audit` / `npm audit` scans above, this keeps the pinned 2023-era Python deps (`requests==2.31.0`, etc.) patched against known CVEs.

---

## Testing

```bash
python3 -m pytest tests/ -v
```

37 tests across 4 files:

| File | Tests | What's tested |
|---|---|---|
| `test_scraper.py` | 7 | `_request` timeouts, `extract_basic_records` (no table, bad rows, fallback table), `extract_detailed_info` (no records, full parse with photo/education/work, legacy headers, missing tables) |
| `test_manager_update.py` | 7 | Safety guard (90% threshold), dedup/sort/GITHUB_OUTPUT, deterministic detail ordering, source-unavailable skip, +3 regressions covering `sync_to_*` return values (missing-creds failure, success, R2 missing-creds failure) |
| `test_manager_enrichment.py` | 3 | Enrichment saves first pending record, raises DataIntegrityError on registration mismatch, resolves records with `serial_number = None` (M2 regression) |
| `test_manager_sync.py` | 17 | Every `sync_to_*` destination's contract: fail-closed on missing credentials, True on success, False on transport/API failure. Release test uses real pyzipper and verifies encryption at upload time; email test asserts the Resend request shape |

All tests use mocking (no real HTTP or Supabase calls). The `supabase` and `requests` modules are mocked globally before imports. `sanity.py` — standalone script (not a test), parses sample HTML and verifies one record extraction. Run manually.

### Frontend

**Unit tests:** `ui/test:unit` runs `node --experimental-strip-types --test 'src/**/*.test.ts'` — 18 tests covering signed-cookie session creation/verification, constant-time comparison, and the `isAuthed` fail-closed path (no secret). No test framework beyond Node's built-in runner.

---

## Pre-commit

`.pre-commit-config.yaml` runs on commit for staged files:

**Python** (root, via `astral-sh/ruff-pre-commit` v0.11.5): `ruff check --fix` + `ruff-format` on changed Python files.

**UI** (local hooks, run from `ui/`): `ui-eslint` (ESLint flat config, 0 errors), `ui-svelte-check` (svelte-check), and `ui-check-colors` (brand-color gate, `npm run check:colors`) on changed Svelte/TS/JS files. `requirements`: a `node`/`npm` install is expected on the dev machine.

No Black, no trailing-whitespace, or end-of-file-fixer hooks.

---

## Deployment

| Component | Method | URL |
|---|---|---|---|
| Frontend | Cloudflare Pages (auto-deploy from `main`, builds `ui/`) | `https://tgpc.pages.dev` |
| CI/CD | GitHub Actions (manual trigger) | `github.com/tgpc-org/tgpc/actions` |
| Data download | GitHub Release | Tag `rphjson`, file `rph.json` |

---

## See Also

- `ui/src/lib/BrandColors.md` — mandatory palette and enforcement notes
- `README.md` — Project overview and quick-start
