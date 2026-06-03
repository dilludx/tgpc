# TGPC Pharmacist Registry

TGPC Pharmacist registry scraper, local data management, Supabase synchronisation, and static search UI publishing.

## What This Repo Does
- Scrapes the public TGPC Pharmacist registry into `data/rx.json`
- Syncs the latest dataset to Supabase for the public search UI
- Supports local enrichment into `data/jsn/` (per-record JSON) plus `data/img/` (photos)
- Serves desktop and mobile search pages from `docs/`

## Workflows
- `rxsync.yml`: manual workflow — scrapes, syncs to Supabase + Cloudflare R2 + Google Drive, sends email notification

## Local Commands
Install the package in a virtual environment:

```bash
python3 -m venv venv
./venv/bin/pip install -e .
```

Run the main commands:

```bash
python3 -m tgpc update
python3 -m tgpc sync
python3 -m tgpc enrich
```

Run tests locally:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

## Required Environment Variables / GitHub Secrets
- `SUPABASE_URL`: project URL used by the sync command
- `SUPABASE_SECRET_KEY`: secret key used by the sync command
- `RESEND_API_KEY`: Resend API key for sync notification emails
- `NOTIFICATION_EMAIL`: recipient email address for sync notifications
- `TGPC_PROXY_URL`: optional outbound proxy for TGPC scraping

The frontend uses the publishable key from `docs/config.js` — database access rules must stay locked down.

> **Note:** `rxsync.yml` sends a detailed HTML email (new/changed/removed records by category) after each successful sync via Resend.

## Data Artifacts
- `data/rx.json`: canonical Pharmacist registry snapshot
- `data/jsn/`: optional enrichment output (`<registration_number>.json`)
- `data/img/`: optional photo cache (`<registration_number>.jpg`/`.png`/`.webp`)

## Operational Notes
- `update` refuses to replace data if the new scrape drops below 90% of the existing count
- `enrich` aborts on registration mismatches to prevent corrupt data
- `data/jsn/` and `data/img/` are local working artifacts, ignored by Git
- Desktop and mobile UIs both read from Supabase and share the same config

## License & Disclaimer

**NO LIABILITY**: The creator, repository owner, contributors, and hosting platform assume **no liability** for any damages, data loss, or legal consequences arising from the use or existence of this repository.

- **Code**: MIT License.
- **Data**: Belongs to the respective authority. Educational purposes only.
- **Usage**: Full responsibility rests with the user.

**Indian Copyright Act, 1957**: Developed for educational and research purposes under Section 52 (Fair Dealing). All data remains the intellectual property of the original copyright holder.
