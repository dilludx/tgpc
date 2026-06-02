"""
CLI entry point for TGPC system.
"""

import argparse
import os
from pathlib import Path
from tgpc.manager import Manager


def load_credentials():
    """Load all credentials from file if not already set in environment."""
    creds_file = Path(__file__).parent.parent / "tgpc-creds.sh"
    if not creds_file.exists():
        return

    loaded = 0
    try:
        with open(creds_file, "r") as f:
            for line in f:
                if line.strip().startswith("export "):
                    var, value = line.strip()[7:].split("=", 1)
                    value = value.strip("\"'")
                    if not os.environ.get(var):
                        os.environ[var] = value
                        loaded += 1
        if loaded:
            print(f"Loaded {loaded} credential(s) from tgpc-creds.sh")
    except Exception as e:
        print(f"Warning: Could not load credentials file: {e}")


def main():
    parser = argparse.ArgumentParser(description="TGPC Rx Registry Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # Update command
    update_parser = subparsers.add_parser("update", help="Run daily update process")
    update_parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Skip sync to cloud destinations after update",
    )

    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Sync data to cloud destinations")
    sync_parser.add_argument(
        "--supabase",
        action="store_true",
        help="Sync to Supabase",
    )
    sync_parser.add_argument(
        "--r2",
        action="store_true",
        help="Sync to Cloudflare R2",
    )
    sync_parser.add_argument(
        "--gdrive",
        action="store_true",
        help="Sync to Google Drive",
    )
    sync_parser.add_argument(
        "--release",
        action="store_true",
        help="Upload rx.json to GitHub Release",
    )
    sync_parser.add_argument(
        "--all",
        action="store_true",
        help="Sync to all destinations (Supabase + R2 + GDrive + Release)",
    )

    # Enrich command
    enrich_parser = subparsers.add_parser("enrich", help="Run enrichment pipeline")
    enrich_parser.add_argument("--start", type=int, default=1, help="Start from serial number (default: 1)")
    enrich_parser.add_argument("--stop", type=int, default=None, help="Stop at serial number (default: all)")
    enrich_parser.add_argument("--force", action="store_true", help="Re-extract even if already done")
    enrich_parser.add_argument("--skip-validation", action="store_true", help="Skip file validation checks")

    args = parser.parse_args()

    manager = Manager()

    if args.command == "update":
        status = manager.run_daily_update()
        if status in {"source_unavailable", "updated", "blocked"}:
            if not args.no_sync:
                load_credentials()
                manager.sync_to_supabase()
                manager.sync_to_supabase_storage()
                manager.sync_to_r2()
                manager.sync_to_gdrive()
                manager.sync_to_release()
                manager.sync_to_email()
            return
        raise SystemExit(1)
    elif args.command == "sync":
        load_credentials()
        do_supabase = args.all or args.supabase
        do_r2 = args.all or args.r2
        do_gdrive = args.all or args.gdrive
        do_release = args.all or args.release

        if not any([do_supabase, do_r2, do_gdrive, do_release]):
            print("Specify a destination: --supabase, --r2, --gdrive, --release, or --all")
            raise SystemExit(1)

        if do_supabase:
            manager.sync_to_supabase()
        if do_r2:
            manager.sync_to_r2()
        if do_gdrive:
            manager.sync_to_gdrive()
        if do_release:
            manager.sync_to_release()
    elif args.command == "enrich":
        manager.run_enrichment(
            start=args.start,
            stop=args.stop,
            force=args.force,
            skip_validation=args.skip_validation,
        )

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
