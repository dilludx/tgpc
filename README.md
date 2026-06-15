# TGPC Pharmacist Registry

Scrapes the public [Telangana Pharmacy Council](https://www.pharmacycouncil.telangana.gov.in) pharmacist registry, syncs to Supabase + R2 + Google Drive + GitHub Release, and serves a public search UI at [tgpc.pages.dev](https://tgpc.pages.dev).

## What This Repo Does

1. **Scrapes** the public TGPC registry website → `data/rph.json` (JSON array)
2. **Syncs** to Supabase (`rph` table) + Cloudflare R2 + Google Drive + GitHub Release
3. **Enriches** records with photos and detailed info from individual detail pages
4. **Serves** a static search frontend from `docs/` via Cloudflare Pages + `_worker.js`

## Stack

| Layer | Technology |
|---|---|
| Scraper | Python 3.9+ (requests, beautifulsoup4, tenacity, supabase-py) |
| Database | Supabase (PostgreSQL + REST API + Storage) |
| Cloud storage | Cloudflare R2 + Google Drive |
| Frontend | Vanilla HTML/JS/CSS + jsPDF + Supabase JS client |
| Hosting | Cloudflare Pages + Workers |
| CI/CD | GitHub Actions (manual `workflow_dispatch`) |
| Notifications | Resend (email) |

## CLI Commands

```bash
python3 -m venv venv && ./venv/bin/pip install -e .

python3 -m tgpc update                          # Scrape → data/rph.json → sync all destinations
python3 -m tgpc update --no-sync                # Scrape only, skip cloud sync
python3 -m tgpc sync --supabase                 # Sync data/rph.json → Supabase
python3 -m tgpc sync --all                      # Sync to all 4 destinations
python3 -m tgpc enrich --start 1 --stop 100     # Enrich records with detail pages
python3 -m unittest discover -s tests -p 'test_*.py' -v  # 13 tests
```

## Required Environment Variables

| Variable | Used By | Purpose |
|---|---|---|
| `SUPABASE_URL` | `sync` command, CI | Supabase project URL |
| `SUPABASE_SECRET_KEY` | `sync` command, CI | Supabase service role key |
| `CLOUDFLARE_ACCOUNT_ID` | `sync --r2`, CI | R2 endpoint account ID |
| `R2_ACCESS_KEY_ID` | `sync --r2`, CI | R2 S3-compatible access key |
| `R2_SECRET_ACCESS_KEY` | `sync --r2`, CI | R2 S3-compatible secret key |
| `RCLONE_GDRIVE_CONFIG` | `sync --gdrive`, CI | Base64-encoded rclone Google Drive config |
| `RESEND_API_KEY` | `sync --email`, CI | Resend.com API key |
| `NOTIFICATION_EMAIL` | `sync --email`, CI | Email recipient |

The frontend embeds its own Supabase anon key in `docs/config.js` — this is safe because RLS restricts access to `SELECT` only.

## CI Pipeline (`.github/workflows/rphsync.yml`)

Single `rphsync` job (manual trigger). Steps:

1. Restore `data/rph.json` from artifact cache
2. Run `python3 -m tgpc update`
3. Sync to Supabase DB + Storage
4. Upload to Cloudflare R2
5. Upload to Google Drive
6. Upload artifact for next run
7. Send HTML email via Resend with categorized change details

## Data Artifacts (all gitignored)

- `data/rph.json` — Canonical JSON array of all pharmacist records (`registration_number`, `name`, `father_name`, `category`, `serial_number`)
- `data/update_details.json` — Sync diff written by `run_daily_update()` (consumed by CI summary + email)
- `data/backups/` — Timestamped backups of rph.json (cleaned after 30 days)
- `data/jsn/` — Per-record enrichment JSON files
- `data/img/` — Per-record photos from enrichment

## Operational Notes

- `update` refuses to replace data if fresh scrape < 90% of existing count
- `enrich` aborts on registration mismatches to prevent corrupt data
- Frontend: 3-char min query desktop, 2-char mobile. 50/page desktop, 25/page mobile.
- Category filter chips + PDF/CSV export (desktop only)

## License & Disclaimer

**NO LIABILITY**: The creator, repository owner, contributors, and hosting platform assume **no liability** for any damages, data loss, or legal consequences arising from the use or existence of this repository.

- **Code**: MIT License
- **Data**: Belongs to the respective authority. Educational purposes only.
- **Usage**: Full responsibility rests with the user.

**Indian Copyright Act, 1957**: Developed for educational and research purposes under Section 52 (Fair Dealing). All data remains the intellectual property of the original copyright holder.
