"""
CLI entry point for TGPC system.
"""

import argparse
import os
from pathlib import Path
from tgpc.manager import Manager

def load_credentials():
    """Load Supabase credentials from file if not set in environment."""
    if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SECRET_KEY"):
        return
    
    creds_file = Path(__file__).parent.parent / "supabase-creds.sh"
    if creds_file.exists():
        try:
            with open(creds_file, 'r') as f:
                for line in f:
                    if line.strip().startswith('export '):
                        var, value = line.strip()[7:].split('=', 1)
                        value = value.strip('"\'')
                        os.environ[var] = value
        except Exception as e:
            print(f"Warning: Could not load credentials file: {e}")

def main():
    parser = argparse.ArgumentParser(description="TGPC Rx Registry Manager")
    subparsers = parser.add_subparsers(dest='command', help='Available commands', required=True)

    # Update command
    update_parser = subparsers.add_parser('update', help='Run daily update process')
    update_parser.add_argument('--sync-supabase', action='store_true', help='Also sync to Supabase after update')

    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Sync data to Supabase')

    # Enrich command
    enrich_parser = subparsers.add_parser('enrich', help='Run enrichment pipeline')
    enrich_parser.add_argument('--start', type=int, default=1, help='Start from serial number (default: 1)')
    enrich_parser.add_argument('--stop', type=int, default=None, help='Stop at serial number (default: all)')
    enrich_parser.add_argument('--force', action='store_true', help='Re-extract even if already done')
    enrich_parser.add_argument('--skip-validation', action='store_true', help='Skip file validation checks')
    enrich_parser.add_argument('--skip-sync', action='store_true', help='Skip Google Drive sync')

    # Dispatch command
    dispatch_parser = subparsers.add_parser('dispatch', help='Sync dispatch PDFs')

    args = parser.parse_args()
    
    manager = Manager()

    if args.command == 'update':
        status = manager.run_daily_update()
        if status in {"source_unavailable", "updated", "blocked"}:
            if args.sync_supabase:
                load_credentials()
                manager.sync_to_supabase()
            return
        raise SystemExit(1)
    elif args.command == 'sync':
        load_credentials()
        manager.sync_to_supabase()
    elif args.command == 'enrich':
        manager.run_enrichment(start=args.start, stop=args.stop, force=args.force, skip_validation=args.skip_validation, skip_sync=args.skip_sync)
    elif args.command == 'dispatch':
        manager.sync_dispatch_pdfs()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
