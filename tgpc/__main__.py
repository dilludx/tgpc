"""
CLI entry point for TGPC system.
"""

import argparse
import atexit
import getpass
import os
import subprocess
from pathlib import Path
from tgpc.manager import Manager

KEYCHAIN_SERVICE = "tgpc"

CREDENTIAL_KEYS = [
    "SUPABASE_URL",
    "SUPABASE_SECRET_KEY",
    "CLOUDFLARE_ACCOUNT_ID",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "RCLONE_GDRIVE_CONFIG",
    "RESEND_API_KEY",
    "NOTIFICATION_EMAIL",
]


# --- Cloudflare WARP ---

_warp_was_connected = False


def _warp_available() -> bool:
    """Check if warp-cli is installed and reachable."""
    try:
        r = subprocess.run(["warp-cli", "status"], capture_output=True, text=True, timeout=5)
        return r.returncode == 0 or "Connected" in r.stdout or "Disconnected" in r.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _warp_connect() -> bool:
    """Connect Cloudflare WARP. Returns True if connected (or already connected)."""
    if not _warp_available():
        return False

    try:
        r = subprocess.run(["warp-cli", "status"], capture_output=True, text=True, timeout=5)
        if "Connected" in r.stdout:
            print("WARP: already connected")
            return True

        r = subprocess.run(["warp-cli", "connect"], capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            print("WARP: connected")
            return True

        print(f"WARP: connect failed — {r.stderr.strip() or r.stdout.strip()}")
        return False
    except Exception as e:
        print(f"WARP: connect error — {e}")
        return False


def _warp_disconnect():
    """Disconnect Cloudflare WARP."""
    if not _warp_available():
        return

    try:
        r = subprocess.run(["warp-cli", "disconnect"], capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            print("WARP: disconnected")
        else:
            print(f"WARP: disconnect failed — {r.stderr.strip() or r.stdout.strip()}")
    except Exception as e:
        print(f"WARP: disconnect error — {e}")


def _warp_ensure_disconnected():
    """Ensure WARP is disconnected on exit. Registered with atexit."""
    global _warp_was_connected
    if _warp_was_connected:
        _warp_disconnect()
        _warp_was_connected = False


# --- Keychain ---


def _get_keychain(key: str) -> str | None:
    try:
        r = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", key, "-w"],
            capture_output=True,
            text=True,
            check=True,
        )
        return r.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _set_keychain(key: str, value: str) -> None:
    existing = _get_keychain(key)
    if existing:
        subprocess.run(
            ["security", "delete-generic-password", "-s", KEYCHAIN_SERVICE, "-a", key],
            capture_output=True,
            check=True,
        )
    subprocess.run(
        ["security", "add-generic-password", "-s", KEYCHAIN_SERVICE, "-a", key, "-w", value, "-U"],
        capture_output=True,
        check=True,
    )


def _load_from_files():
    candidates = [
        Path.home() / ".config" / "tgpc" / "creds.sh",
        Path(__file__).parent.parent / "tgpc-creds.sh",
    ]
    for creds_file in candidates:
        if not creds_file.exists():
            continue
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
                print(f"Loaded {loaded} credential(s) from {creds_file}")
        except Exception as e:
            print(f"Warning: Could not load {creds_file}: {e}")


def load_credentials():
    """Load credentials: env vars → macOS Keychain → file fallback."""
    _load_from_files()
    for key in CREDENTIAL_KEYS:
        if os.environ.get(key):
            continue
        val = _get_keychain(key)
        if val is not None:
            os.environ[key] = val


def _cmd_creds_set(args):
    if args.key_value and "=" in args.key_value:
        key, value = args.key_value.split("=", 1)
        _set_keychain(key, value)
        print(f"Stored {key} in Keychain")
        return
    for key in CREDENTIAL_KEYS:
        existing = _get_keychain(key)
        if existing and not args.force:
            print(f"{key} — already set (use --force to overwrite)")
            continue
        prompt = f"{key}" + (f" [{existing[:8]}...]" if existing else "")
        value = getpass.getpass(f"{prompt}: ")
        if value:
            _set_keychain(key, value)
            print(f"  ✓ {key} stored")
        else:
            print(f"  - {key} skipped")


def _cmd_creds_list(_args):
    for key in CREDENTIAL_KEYS:
        env = os.environ.get(key, "")
        kc = _get_keychain(key)
        if env:
            print(f"{key}  env: {env[:12]}...")
        elif kc:
            print(f"{key}  keychain: {kc[:12]}...")
        else:
            print(f"{key}  — not set")


def _cmd_creds_delete(args):
    existing = _get_keychain(args.key)
    if existing:
        subprocess.run(
            ["security", "delete-generic-password", "-s", KEYCHAIN_SERVICE, "-a", args.key],
            capture_output=True,
            check=True,
        )
        print(f"Deleted {args.key} from Keychain")
    else:
        print(f"{args.key} not found in Keychain")


def main():
    parser = argparse.ArgumentParser(description="TGPC RPh Registry Manager")
    subparsers = parser.add_subparsers(dest="command")

    # Update command
    update_parser = subparsers.add_parser("update", help="Run daily update process")
    update_parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Skip sync to cloud destinations after update",
    )

    # Sync command
    subparsers.add_parser("sync", help="Sync rph.json to all cloud destinations")

    # Retry-photos command
    subparsers.add_parser("retry-photos", help="Retry uploading failed photos from data/webp/ to R2")

    # Creds command
    creds_parser = subparsers.add_parser("creds", help="Manage credentials in macOS Keychain")
    creds_sub = creds_parser.add_subparsers(dest="creds_cmd")

    set_p = creds_sub.add_parser("set", help="Store credentials interactively or via KEY=VALUE")
    set_p.add_argument("key_value", nargs="?", help="KEY=VALUE pair (omit for interactive)")
    set_p.add_argument("--force", "-f", action="store_true", help="Overwrite existing values")

    creds_sub.add_parser("list", help="Show which credentials are set")

    del_p = creds_sub.add_parser("delete", help="Delete a credential from Keychain")
    del_p.add_argument("key", choices=CREDENTIAL_KEYS, help="Credential key to delete")

    args = parser.parse_args()
    if not getattr(args, "command", None):
        parser.print_help()
        return

    if args.command == "creds":
        if not args.creds_cmd:
            creds_parser.print_help()
            return
        if args.creds_cmd == "set":
            _cmd_creds_set(args)
        elif args.creds_cmd == "list":
            _cmd_creds_list(args)
        elif args.creds_cmd == "delete":
            _cmd_creds_delete(args)
        return

    manager = Manager()

    # Connect WARP for network-level routing (update and sync hit external services)
    global _warp_was_connected
    if args.command in ("update", "sync", "retry-photos"):
        atexit.register(_warp_ensure_disconnected)
        _warp_was_connected = _warp_connect()

    try:
        if args.command == "update":
            status = manager.run_daily_update()
            if status in {"source_unavailable", "updated", "blocked"}:
                if not args.no_sync:
                    load_credentials()
                    # Build delta: new + modified records only
                    delta = None
                    if status == "updated":
                        all_records = manager.file_manager.load()
                        new_regs = getattr(manager, "_last_new_regs", set())
                        mod_regs = getattr(manager, "_last_modified_regs", set())
                        delta_ids = new_regs | set(mod_regs)
                        delta = [r for r in all_records if r.registration_number in delta_ids] if delta_ids else []
                    manager.sync_to_supabase(delta_records=delta)
                    manager.sync_to_supabase_storage()
                    manager.sync_to_r2()
                    manager.sync_to_gdrive()
                    manager.sync_to_release()
                    manager.sync_to_email()
                    if status == "updated":
                        manager.enrich_new_records()
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
        elif args.command == "retry-photos":
            load_credentials()
            manager.retry_photos()
    finally:
        if _warp_was_connected:
            _warp_disconnect()
            _warp_was_connected = False


if __name__ == "__main__":
    main()
