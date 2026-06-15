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
    parser = argparse.ArgumentParser(description="TGPC RPh Registry Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # Update command
    update_parser = subparsers.add_parser("update", help="Run daily update process")
    update_parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Skip sync to cloud destinations after update",
    )

    # Sync command
    subparsers.add_parser("sync", help="Sync rph.json to all cloud destinations")

    # Enrich command
    enrich_parser = subparsers.add_parser("enrich", help="Run enrichment pipeline")
    enrich_parser.add_argument("--start", type=int, default=1, help="Start from serial number (default: 1)")
    enrich_parser.add_argument("--stop", type=int, default=None, help="Stop at serial number (default: all)")

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
        manager.sync_to_supabase()
        manager.sync_to_supabase_storage()
        manager.sync_to_r2()
        manager.sync_to_gdrive()
        manager.sync_to_release()
        manager.sync_to_email()
    elif args.command == "enrich":
        manager.run_enrichment(
            start=args.start,
            stop=args.stop,
        )

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
