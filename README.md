# TGPC RPh Registry

Scrapes the public [Telangana Pharmacy Council](https://www.pharmacycouncil.telangana.gov.in) pharmacist registry, syncs to Supabase + R2 + Google Drive + GitHub Release, and serves a public search UI at [tgpc.pages.dev](https://tgpc.pages.dev).

## What This Repo Does

1. **Scrapes** the public TGPC registry website → `data/rph.json`
2. **Syncs** to Supabase (`rph` table + Storage) + Cloudflare R2 + Google Drive + GitHub Release
3. **Enriches** records with photos and detailed info from individual detail pages
4. **Serves** a search frontend (SvelteKit) via Cloudflare Pages

## Stack

| Layer | Technology |
|---|---|
| Scraper | Python 3.14+ (requests, beautifulsoup4, tenacity, supabase-py) |
| Database | Supabase (PostgreSQL + REST API + Storage) |
| Cloud storage | Cloudflare R2 + Google Drive |
| Frontend | SvelteKit + TypeScript + Supabase JS client + jsPDF |
| Hosting | Cloudflare Pages |
| CI/CD | GitHub Actions (manual `workflow_dispatch`) |
| Notifications | Resend (email) |

## CLI Commands

```bash
git clone https://github.com/dilludx/tgpc.git && cd tgpc
python3 -m venv venv && source venv/bin/activate && pip install -e .

python3 -m tgpc update                          # Scrape → data/rph.json → sync all 6 destinations
python3 -m tgpc update --no-sync                # Scrape only, skip cloud sync
python3 -m tgpc sync                             # Sync data/rph.json to all destinations (Supabase DB + Storage, R2, GDrive, Release, Email)
python3 -m tgpc enrich --start 1 --stop 100     # Enrich records with detail pages
make scrape                                      # Shorthand: scrape + sync all
make sync                                        # Sync all destinations
make enrich                                      # Enrich records
python3 -m unittest discover -s tests -p 'test_*.py' -v  # 13+ tests
```

## Required Environment Variables

| Variable | Purpose |
|---|---|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SECRET_KEY` | Supabase service role key |
| `CLOUDFLARE_ACCOUNT_ID` | R2 endpoint account ID |
| `R2_ACCESS_KEY_ID` | R2 S3-compatible access key |
| `R2_SECRET_ACCESS_KEY` | R2 S3-compatible secret key |
| `RCLONE_GDRIVE_CONFIG` | Base64-encoded rclone Google Drive config |
| `RESEND_API_KEY` | Resend.com API key |
| `NOTIFICATION_EMAIL` | Email recipient |

The frontend embeds a Supabase anon key — safe because RLS restricts to `SELECT` only.

## CI Pipeline (`.github/workflows/rphsync.yml`)

Single `rphsync` job (manual trigger). Steps:

1. Restore `data/rph.json` from artifact cache
2. Run `python3 -m tgpc update`
3. Sync to Supabase DB + Storage
4. Upload to Cloudflare R2
5. Upload to Google Drive
6. Upload artifact for next run
7. Send HTML email via Resend with categorized change details

## Frontend

The search UI is a SvelteKit app at [tgpc.pages.dev](https://tgpc.pages.dev). Search by name or RPC number, filter by category, export CSV/PDF, view notices and dispatch lists.

## Data Artifacts (all gitignored)

- `data/rph.json` — Canonical JSON array of all pharmacist records
- `data/update_details.json` — Sync diff consumed by CI summary + email
- `data/backups/` — Timestamped backups cleaned after 30 days
- `data/jsn/` — Per-record enrichment JSON files (deleted after migration to Supabase)
- `data/img/` — Per-record photos from enrichment

## Operational Notes

- `update` refuses to replace data if fresh scrape < ~90% of existing count
- `enrich` aborts on registration mismatches to prevent corrupt data
- Search requires 3+ characters; results paginated 50/page with category filter chips

## Disclaimer

**NO LIABILITY**: The creator, repository owner, contributors, and hosting platform assume **no liability** for any damages, data loss, or legal consequences arising from the use or existence of this repository.

**Indian Copyright Act, 1957**: Developed for educational and research purposes under Section 52 (Fair Dealing). All data remains the intellectual property of the original copyright holder.
