# DB-PLAN: Merge Detail Data into RPH Table

Add 5 new columns (gender, validity_date, status, education jsonb, work_experience jsonb) to the Supabase `rph` table and backfill all 87,564 records.

---

## Phase 1 — Add Columns (manual SQL)

- [ ] **1.1** Open Supabase Dashboard → SQL Editor → New query
- [ ] **1.2** Run SQL:
  ```sql
  ALTER TABLE rph 
    ADD COLUMN IF NOT EXISTS gender text DEFAULT '',
    ADD COLUMN IF NOT EXISTS validity_date text DEFAULT '',
    ADD COLUMN IF NOT EXISTS status text DEFAULT '',
    ADD COLUMN IF NOT EXISTS education jsonb DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS work_experience jsonb DEFAULT '{}';
  ```
- [ ] **1.3** Verify:
  ```sql
  SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'rph';
  ```
  → 10 columns (5 original + 5 new)

---

## Phase 2 — Modify `sync_to_supabase()` in `tgpc/manager.py`

- [ ] **2.1** Confirm imports exist (already at lines 6, 11): `import json`, `from pathlib import Path`
- [ ] **2.2** Replace lines 449-451:
  **Before:**
  ```python
  for i in range(0, len(records), batch_size):
      batch = [r.to_dict() for r in records[i : i + batch_size]]
      supabase.table("rph").upsert(batch, on_conflict="registration_number").execute()
  ```
  **After:**
  ```python
  jsn_dir = Path(self.config.enrichment_directory) / "jsn"

  for i in range(0, len(records), batch_size):
      batch = []
      for r in records[i : i + batch_size]:
          row = r.to_dict()
          detail_file = jsn_dir / f"{r.registration_number}.json"
          if detail_file.exists():
              with open(detail_file, "r", encoding="utf-8") as f:
                  detail = json.load(f)
              row["gender"] = detail.get("gender", "")
              row["validity_date"] = detail.get("validity_date", "")
              row["status"] = detail.get("status", "")
              row["education"] = detail.get("education", [])
              row["work_experience"] = detail.get("work_experience", {})
          else:
              row["gender"] = ""
              row["validity_date"] = ""
              row["status"] = ""
              row["education"] = []
              row["work_experience"] = {}
          batch.append(row)
      supabase.table("rph").upsert(batch, on_conflict="registration_number").execute()
      logger.info(f"Synced batch {i // batch_size + 1}")
  ```
- [ ] **2.3** Lines 454-465 (metadata timestamp + logging) stay unchanged

---

## Phase 3 — Backfill 87,564 Records

- [ ] **3.1** Confirm Phase 1 SQL ran (columns exist)
- [ ] **3.2** Run:
  ```bash
  python3 -m tgpc sync
  ```
- [ ] **3.3** Verify in Supabase SQL Editor:
  ```sql
  SELECT 
    COUNT(*) as total,
    COUNT(gender) FILTER (WHERE gender != '') as has_gender,
    COUNT(validity_date) FILTER (WHERE validity_date != '') as has_validity,
    COUNT(status) FILTER (WHERE status != '') as has_status,
    COUNT(*) FILTER (WHERE education != '[]') as has_education,
    COUNT(*) FILTER (WHERE work_experience != '{}') as has_work_experience
  FROM rph;
  ```
  → all 5 counts = 87,564

---

## Phase 4 — Enrichment Upserts Immediately

- [ ] **4.1** `tgpc/__main__.py` line 207 — add `load_credentials()` before `manager.run_enrichment()`:
  ```python
  elif args.command == "enrich":
      load_credentials()
      manager.run_enrichment(
          start=args.start,
          stop=args.stop,
      )
  ```

- [ ] **4.2** `tgpc/manager.py` line 805 — create Supabase client once in `run_enrichment()`:
  ```python
  supabase = None
  url = os.environ.get("SUPABASE_URL")
  key = os.environ.get("SUPABASE_SECRET_KEY")
  if url and key:
      supabase = create_client(url, key)
  ```

- [ ] **4.3** `tgpc/manager.py` line 858 — pass `supabase` as keyword:
  ```python
  total_processed = self._process_records_sequential(
      pending_records, rph_lookup, jsn_dir, img_dir, supabase=supabase
  )
  ```
  **Must use keyword** — 5th positional is `ip_rotation_interval=500`.

- [ ] **4.4** `tgpc/manager.py` line 924 — update function signature:
  ```python
  def _process_records_sequential(self, pending_records, rph_lookup, jsn_dir, img_dir, ip_rotation_interval=500, supabase=None):
  ```

- [ ] **4.5** `tgpc/manager.py` line 996 — add Supabase upsert after saving detail JSON:
  ```python
  if supabase:
      try:
          supabase.table("rph").upsert(data, on_conflict="registration_number").execute()
      except Exception as e:
          logger.warning(f"Failed to upsert enriched record {reg_no} to Supabase: {e}")
  ```

---

## Final Verification

- [ ] **V1** `SELECT COUNT(*) FROM rph;` → 87,564
- [ ] **V2** Spot check: `SELECT registration_number, name, gender, status, validity_date FROM rph LIMIT 5;`
- [ ] **V3** Load v2 frontend — no console errors, stats show
- [ ] **V4** Run `python3 -m tgpc sync` twice — second run is idempotent, no errors

---

## Rollback

| Phase | Command |
|---|---|
| Phase 1 | `ALTER TABLE rph DROP COLUMN gender, DROP COLUMN validity_date, DROP COLUMN status, DROP COLUMN education, DROP COLUMN work_experience;` |
| Phase 2/3 | `git checkout -- tgpc/manager.py` then `python3 -m tgpc sync` |
| Phase 4 | `git checkout -- tgpc/manager.py tgpc/__main__.py` |
