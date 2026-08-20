"""
Detect inactive records that are now Active on the source.

Two subcommands:

    python3 -m tgpc.inactive_sweep inactive   # Phase 1: build data/inactive_records.jsonl
    python3 -m tgpc.inactive_sweep sweep      # Phase 2: sweep batches, write actives to JSONL

Phase 1 pulls every record with status='Inactive' from Supabase and joins it
with data/rph.json for full identity fields, writing data/inactive_records.jsonl.

Phase 2 re-scrapes each record (status check only, no photo/R2 work) in batches
of 1000 and appends any that now resolve as 'Active' to
data/now_active_from_inactive.jsonl. A checkpoint file tracks completed batches
so the sweep is resumable across crashes/restarts.

No Supabase writes are performed; enrichment/upsert of the actives is a
separate, later step.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
INACTIVE_FILE = DATA_DIR / "inactive_records.jsonl"
ACTIVE_FILE = DATA_DIR / "now_active_from_inactive.jsonl"
CHECKPOINT_FILE = DATA_DIR / "inactive_sweep_checkpoint.json"

BATCH_SIZE = 1000

IDENTITY_FIELDS = ["registration_number", "name", "father_name", "category", "serial_number"]


def _load_rph():
    path = DATA_DIR / "rph.json"
    if not path.exists():
        print(f"Missing {path} — cannot join identity fields.", file=sys.stderr)
        return {}
    return {r["registration_number"]: r for r in json.loads(path.read_text())}


def _sb_client():
    from tgpc.utils import load_credentials

    load_credentials()
    from supabase import create_client

    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SECRET_KEY"])


def _load_records():
    if not INACTIVE_FILE.exists():
        print(f"Missing {INACTIVE_FILE} — run 'inactive' subcommand first.", file=sys.stderr)
        sys.exit(1)
    return [json.loads(line) for line in INACTIVE_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]


def _existing_active_set():
    active_set = set()
    if ACTIVE_FILE.exists():
        for line in ACTIVE_FILE.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    active_set.add(json.loads(line)["registration_number"])
                except Exception:
                    pass
    return active_set


def _write_active(out_fh, reg, basic, details):
    out_fh.write(
        json.dumps(
            {
                "registration_number": reg,
                "name": basic.get("name") or details.name,
                "father_name": basic.get("father_name") or details.father_name,
                "category": basic.get("category") or details.category,
                "serial_number": basic.get("serial_number"),
                "gender": details.gender or "",
                "validity_date": details.validity_date or "",
                "status": details.status,
            },
            ensure_ascii=False,
        )
        + "\n"
    )
    out_fh.flush()


def _sweep_regs(regs, records, offset=0, global_total=None, min_delay=3.0, workers=1):
    """Re-scrape regs, write now-Active ones to ACTIVE_FILE. Returns (counts, actives_found).

    ``offset``/``global_total`` let a per-batch call render a single bar across
    the whole sweep (e.g. 3450/15397) instead of 450/1000 per batch.
    ``min_delay`` overrides the scraper's rate limiter floor (seconds per request).
    ``workers`` splits the work across N parallel Scraper instances (each with
    its own session + rate limiter) for a multi-X speedup.
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from tgpc.progress import ProgressBar, step
    from tgpc.scraper import Scraper

    ACTIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    active_set = _existing_active_set()
    by_reg = {r["registration_number"]: r for r in records}
    counts_lock = threading.Lock()
    counts = {"active": 0, "inactive": 0, "other": 0, "not_found": 0, "error": 0}
    start = time.time()

    def process_reg(sc, reg):
        d = sc.extract_detailed_info(reg, None)
        if d is None:
            with counts_lock:
                counts["not_found"] += 1
            step(f"{reg}: NOT FOUND")
        elif d.status == "Active":
            with counts_lock:
                counts["active"] += 1
                if reg not in active_set:
                    _write_active(out_fh, reg, by_reg.get(reg, {}), d)
                    active_set.add(reg)
            step(f"{reg}: ACTIVE")
        elif d.status == "Inactive":
            with counts_lock:
                counts["inactive"] += 1
            step(f"{reg}: inactive")
        else:
            with counts_lock:
                counts["other"] += 1
            step(f"{reg}: {d.status}")

    def worker(chunk):
        sc = Scraper()
        sc.rate_limiter.min_delay = min_delay
        sc.rate_limiter.current_delay = min_delay
        for reg in chunk:
            try:
                process_reg(sc, reg)
            except Exception as e:
                with counts_lock:
                    counts["error"] += 1
                step(f"{reg}: ERROR {e}")
                print(f"ERROR {reg}: {e}", file=sys.stderr)
            finally:
                bar.update(1, detail=reg)

    with (
        ProgressBar(
            total=global_total if global_total is not None else len(regs), label="Sweeping inactive", cadence=1
        ) as bar,
        open(ACTIVE_FILE, "a", encoding="utf-8") as out_fh,
    ):
        bar.n = offset
        if workers <= 1:
            worker(regs)
        else:
            chunks = [regs[i::workers] for i in range(workers)]
            with ThreadPoolExecutor(max_workers=workers) as pool:
                list(pool.map(worker, chunks))

    return counts, (time.time() - start)


# --- Phase 1 -----------------------------------------------------------


def cmd_inactive(_args):
    from tgpc.progress import ProgressBar

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("Pulling status='Inactive' from Supabase...")
    sb = _sb_client()
    rows = sb.table("rph").select("registration_number").eq("status", "Inactive").limit(100000).execute()
    inactive = sorted(r["registration_number"] for r in rows.data)
    print(f"Found {len(inactive)} inactive records")

    rph = _load_rph()
    missing = 0
    with (
        ProgressBar(total=len(inactive), label="Joining rph.json identity") as bar,
        open(INACTIVE_FILE, "w", encoding="utf-8") as f,
    ):
        for reg in inactive:
            basic = rph.get(reg, {})
            if not basic:
                missing += 1
            record = {k: basic.get(k) for k in IDENTITY_FIELDS}
            record["registration_number"] = reg
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            bar.update(1, detail=reg)

    print(f"Wrote {len(inactive)} records to {INACTIVE_FILE} ({missing} missing from rph.json)")


# --- Phase 2 -----------------------------------------------------------


def _load_checkpoint():
    if CHECKPOINT_FILE.exists():
        try:
            return json.loads(CHECKPOINT_FILE.read_text())
        except Exception:
            pass
    return {"done_batches": []}


def _save_checkpoint(state):
    CHECKPOINT_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def cmd_sweep(args):
    records = _load_records()
    regs = [r["registration_number"] for r in records]
    total = len(regs)

    if args.batches is not None or args.limit is not None:
        limit = args.limit if args.limit is not None else args.batches * BATCH_SIZE
        limit = min(total, limit)
        print(f"Partial run: first {limit} records")
        counts, elapsed = _sweep_regs(regs[:limit], records, min_delay=args.min_delay, workers=args.workers)
        print(f"\nPartial sweep done in {elapsed:.0f}s: {counts}")
        return 0

    print(f"Loaded {total} inactive records from {INACTIVE_FILE}")

    state = _load_checkpoint()
    done_batches = set(state.get("done_batches", []))
    skip_n = sum(len(regs[i : i + BATCH_SIZE]) for i in range(0, total, BATCH_SIZE) if i // BATCH_SIZE in done_batches)
    print(f"Resuming: {skip_n} records in {len(done_batches)} completed batch(es) skipped")

    counts = {"active": 0, "inactive": 0, "other": 0, "not_found": 0, "error": 0}
    start_all = time.time()

    for batch_idx in range(0, total, BATCH_SIZE):
        batch = regs[batch_idx : batch_idx + BATCH_SIZE]
        bnum = batch_idx // BATCH_SIZE
        if bnum in done_batches:
            continue

        b_start = time.time()
        partial, _ = _sweep_regs(
            batch, records, offset=batch_idx, global_total=total, min_delay=args.min_delay, workers=args.workers
        )
        for k in counts:
            counts[k] += partial[k]

        done_batches.add(bnum)
        state["done_batches"] = sorted(done_batches)
        _save_checkpoint(state)

        processed = min(batch_idx + len(batch), total)
        overall = time.time() - start_all
        rate = processed / overall if overall > 0 else 0
        print(
            f"batch {bnum + 1} done in {time.time() - b_start:.0f}s — cumulative {processed}/{total} "
            f"({rate:.1f}/s, ETA {(total - processed) / rate / 3600 if rate else float('nan'):.1f}h) "
            f"actives={counts['active']}"
        )

    print(f"\nSweep complete. {counts['active']} now-Active records written to {ACTIVE_FILE}")
    print(f"Breakdown: {counts}")
    return 0


# --- CLI ---------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Find inactive records that are now Active on the source")
    sub = parser.add_subparsers(dest="command", required=True)

    p1 = sub.add_parser("inactive", help="Build data/inactive_records.jsonl (all status='Inactive' records)")
    p1.set_defaults(func=cmd_inactive)

    p2 = sub.add_parser("sweep", help="Re-scrape inactive records; write now-Active ones to JSONL")
    p2.add_argument("--batches", type=int, default=None, help="Process only the first N batches (dry-run)")
    p2.add_argument("--limit", type=int, default=None, help="Process only the first N records (dry-run)")
    p2.add_argument(
        "--min-delay",
        type=float,
        default=3.0,
        help="Rate-limiter floor in seconds between requests (default 3.0; ~0.5 gives ~6h for the full sweep)",
    )
    p2.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Parallel Scraper workers (each with its own session + rate limiter). "
        "e.g. 4 workers at --min-delay 0.5 ≈ 1.4h for the full sweep",
    )
    p2.set_defaults(func=cmd_sweep)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
