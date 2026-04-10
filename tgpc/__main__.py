"""
CLI entry point for TGPC system.
"""

import argparse
from tgpc.manager import Manager

def main():
    parser = argparse.ArgumentParser(description="TGPC Rx Registry Manager")
    subparsers = parser.add_subparsers(dest='command', help='Available commands', required=True)

    # Update command
    update_parser = subparsers.add_parser('update', help='Run daily update process')

    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Sync data to Supabase')

    # Enrich command
    enrich_parser = subparsers.add_parser('enrich', help='Run enrichment pipeline')
    enrich_parser.add_argument('--batch-size', type=int, default=50, help='Number of records per batch')
    enrich_parser.add_argument('--start', type=int, default=1, help='Start from serial number (default: 1)')
    enrich_parser.add_argument('--stop', type=int, default=None, help='Stop at serial number (default: all)')

    args = parser.parse_args()
    
    manager = Manager()

    if args.command == 'update':
        status = manager.run_daily_update()
        if status in {"source_unavailable", "updated"}:
            return
        raise SystemExit(1)
    elif args.command == 'sync':
        manager.sync_to_supabase()
    elif args.command == 'enrich':
        manager.run_enrichment(batch_size=args.batch_size, start=args.start, stop=args.stop)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
