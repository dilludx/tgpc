# TGPC Rx Registry

Automated TGPC pharmacist registry scraping, local data management, Supabase synchronisation, and static search UI publishing.

## What This Repo Does
- Scrapes the public TGPC pharmacist registry into `data/rx.json`
- Syncs the latest dataset to Supabase for the public search UI
- Supports local enrichment into `data/rxdetails.json` plus `data/photos/`
- Serves separate desktop and mobile search pages from `docs/`
- Runs automated validation and scheduled syncs with GitHub Actions

## Current Automation
- `rx-sync.yml`: runs every 4 hours, updates `data/rx.json`, syncs Supabase, and publishes a run summary
- `ci-validate.yml`: runs compile checks, parser sanity checks, unit tests, frontend JS syntax checks, and workflow linting
- `website-status.yml`: reusable/manual workflow that checks `https://tgpc.pages.dev/`

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
python3 -m tgpc enrich --batch-size 50
```

Run validation locally:

```bash
python3 tests/sanity.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m compileall -q tgpc scripts tests
node --check docs/config.js docs/search.js docs/mobile.js docs/_worker.js
```

## Required Environment Variables
- `SUPABASE_URL`: project URL used by the sync command
- `SUPABASE_SECRET_KEY`: secret key used by the sync command
- `TGPC_PROXY_URL`: optional outbound proxy URL for TGPC scraping when GitHub-hosted runners cannot reach the source directly

The public frontend uses the publishable key from `docs/config.js`, so database access rules must stay appropriately locked down in Supabase.

## Data Artifacts
- `data/rx.json`: canonical basic pharmacist registry snapshot
- `data/rxdetails.json`: optional local enrichment output
- `data/photos/`: optional local photo cache created by enrichment
- `data/backups/`: local timestamped snapshots created before update runs

## Operational Notes
- `update` refuses to replace the dataset if the new scrape drops below 90% of the existing record count
- `enrich` now aborts immediately on registration mismatches so bad detail pages cannot be silently written
- `rxdetails.json` and `data/photos/` are local working artifacts and are ignored by Git
- The desktop and mobile UIs both read from Supabase directly and share the same frontend config

## Status
The repo is operational and the scheduled sync path is intended to run autonomously, with CI covering backend parsing and frontend script integrity.

## ⚖️ License & Disclaimer
**NO LIABILITY**: The creator, the repository owner, the contributors, and the hosting platform (GitHub) assume **NO LIABILITY** and are **NOT RESPONSIBLE** for any lawsuits, damages, data loss, or legal consequences arising from the use, misuse, or existence of this repository.

- **Code**: Licensed under the MIT License.
- **Data**: All data belongs to the respective authority. This tool is for educational purposes only.
- **Usage**: Users assume full responsibility for how they use this tool and the data it accesses.

**Indian Copyright Act, 1957**: This tool is developed for educational and research purposes under the 'Fair Dealing' provisions of Section 52 of the Indian Copyright Act, 1957. The data accessed remains the intellectual property of the original copyright holder.
