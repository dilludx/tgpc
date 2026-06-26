"""
Core management logic for TGPC system.
Handles file storage, backups, daily updates, and cloud sync.
"""

import json
import shutil
import os
import subprocess
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List, Iterable
from collections import Counter

from supabase import create_client

from tgpc.utils import Config, setup_logging
from tgpc.scraper import Scraper, PharmacistRecord


logger = setup_logging("tgpc.manager")


class DataIntegrityError(RuntimeError):
    """Raised when scraped detail data does not match the requested record."""


class FileManager:
    """Handles local file storage."""

    def __init__(self, config: Config):
        self.data_dir = Path(config.data_directory)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save(self, records: List[PharmacistRecord], filename: str = "rph.json") -> Path:
        """Save records to JSON."""
        path = self.data_dir / filename
        data = [r.to_dict() for r in records]

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Saved {len(records)} records to {path}")
        return path

    def load(self, filename: str = "rph.json") -> List[PharmacistRecord]:
        """Load records from JSON."""
        path = self.data_dir / filename
        if not path.exists():
            return []

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return [PharmacistRecord(**d) for d in data]


class BackupManager:
    """Handles secure backups."""

    def __init__(self, config: Config):
        self.backup_dir = Path(config.data_directory) / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create(self, source: Path) -> str:
        """Create timestamped backup."""
        if not source.exists():
            return ""

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = self.backup_dir / f"rph_backup_{ts}.json"
        shutil.copy2(source, dest)
        logger.info(f"Backup created: {dest}")
        return str(dest)

    def cleanup(self, keep: int = 7) -> int:
        """Keep the most recent N backups, delete older ones. Returns count of deleted files."""
        files = sorted(self.backup_dir.glob("rph_backup_*.json"), reverse=True)
        deleted = 0
        for f in files[keep:]:
            try:
                f.unlink()
                deleted += 1
            except OSError as e:
                logger.warning(f"Could not delete backup file {f.name}: {e}")
        if deleted:
            logger.info(f"Cleaned {deleted} old backups, kept {min(keep, len(files))}")

        details = self.backup_dir.parent / "update_details.json"
        if details.exists():
            try:
                details.unlink()
                logger.info("Cleaned update_details.json")
            except OSError as e:
                logger.warning(f"Could not delete update_details.json: {e}")
        return deleted


class Manager:
    """Main management class."""

    def __init__(self):
        self.config = Config.load()
        self.file_manager = FileManager(self.config)
        self.backup_manager = BackupManager(self.config)
        self.scraper = Scraper()

    @staticmethod
    def _iter_exception_chain(error: BaseException) -> Iterable[BaseException]:
        seen = set()
        pending = [error]

        while pending:
            current = pending.pop()
            if current is None:
                continue

            current_id = id(current)
            if current_id in seen:
                continue
            seen.add(current_id)
            yield current

            for attr in ("original_error", "__cause__", "__context__"):
                nested = getattr(current, attr, None)
                if isinstance(nested, BaseException):
                    pending.append(nested)

    @classmethod
    def _is_source_unavailable_error(cls, error: BaseException) -> bool:
        for current in cls._iter_exception_chain(error):
            if isinstance(
                current,
                (requests.exceptions.Timeout, requests.exceptions.ConnectionError),
            ):
                return True

            # Catch urllib3 timeout errors (common in GitHub Actions)
            try:
                from urllib3.exceptions import (
                    ConnectTimeoutError,
                    MaxRetryError,
                    NewConnectionError,
                )

                if isinstance(current, (ConnectTimeoutError, MaxRetryError, NewConnectionError)):
                    return True
            except ImportError:
                pass

            if isinstance(current, requests.exceptions.HTTPError):
                status_code = getattr(getattr(current, "response", None), "status_code", None)
                if status_code == 429 or (status_code is not None and status_code >= 500):
                    return True

        return False

    @classmethod
    def _source_error_label(cls, error: BaseException) -> str:
        for current in cls._iter_exception_chain(error):
            if isinstance(current, requests.exceptions.RequestException):
                return type(current).__name__

            # Also handle urllib3 exceptions
            try:
                from urllib3.exceptions import (
                    ConnectTimeoutError,
                    MaxRetryError,
                    NewConnectionError,
                )

                if isinstance(current, (ConnectTimeoutError, MaxRetryError, NewConnectionError)):
                    return type(current).__name__
            except ImportError:
                pass

        return type(error).__name__

    def _write_update_outputs(self, **values) -> None:
        output_path = os.environ.get("GITHUB_OUTPUT")

        defaults = {
            "update_status": "",
            "source_error": "",
            "success": False,
            "total_records": 0,
            "new_records": 0,
            "removed_records": 0,
            "modified_records": 0,
            "duplicates_removed": 0,
            "integrity_score": 1.0,
            "new_details": [],
            "removed_details": [],
            "modified_details": [],
            "new_cat_stats": {},
            "rem_cat_stats": {},
            "mod_cat_stats": {},
            "blocked": False,
        }
        defaults.update(values)

        if output_path:
            with open(output_path, "a", encoding="utf-8") as f:
                for key, value in defaults.items():
                    if isinstance(value, (dict, list)):
                        serialized = json.dumps(value)
                    else:
                        serialized = str(value)
                    f.write(f"{key}={serialized}\n")

    def run_daily_update(self):
        """Execute daily update workflow."""
        logger.info("Starting daily update...")

        # 0. Health check - abort if blocked
        if not self.scraper.health_check():
            logger.error("Health check failed - connection is blocked. Aborting to avoid wasted time.")
            self._write_update_outputs(
                update_status="blocked",
                success=False,
                blocked=True,
                total_records=len(self.file_manager.load()),
            )
            return "blocked"

        # 1. Backup existing
        rph_path = Path(self.config.data_directory) / "rph.json"
        self.backup_manager.create(rph_path)
        existing_records = self.file_manager.load()

        # 2. Scrape fresh data
        try:
            fresh_records = self.scraper.extract_basic_records()
        except Exception as e:
            if self._is_source_unavailable_error(e):
                source_error = self._source_error_label(e)
                logger.warning(
                    "TGPC source is temporarily unavailable (%s). Preserving existing data and skipping sync.",
                    source_error,
                )
                self._write_update_outputs(
                    update_status="source_unavailable",
                    source_error=source_error,
                    success=False,
                    total_records=len(existing_records),
                )
                return "source_unavailable"
            raise

        if not fresh_records:
            logger.error("No records extracted, aborting update")
            self._write_update_outputs(
                update_status="empty_scrape",
                success=False,
                total_records=len(existing_records),
            )
            return "empty_scrape"

        # Safety Check: Prevent massive data loss
        if existing_records and len(fresh_records) < len(existing_records) * 0.9:
            logger.error(
                f"Safety Alert: New count ({len(fresh_records)}) < 90% of existing ({len(existing_records)}). Aborting."
            )
            self._write_update_outputs(
                update_status="safety_abort",
                success=False,
                total_records=len(existing_records),
            )
            return "safety_abort"

        # 3. Validate & Save
        # Simple deduplication by registration number
        unique_records = {r.registration_number: r for r in fresh_records}.values()
        sorted_records = sorted(unique_records, key=lambda r: r.serial_number or 0)

        # Calculate stats
        existing_map = {r.registration_number: r for r in existing_records}
        current_map = {r.registration_number: r for r in sorted_records}

        existing_ids = set(existing_map.keys())
        current_ids = set(current_map.keys())

        new_ids = current_ids - existing_ids
        removed_ids = existing_ids - current_ids
        common_ids = current_ids & existing_ids

        new_count = len(new_ids)
        removed_count = len(removed_ids)
        total_count = len(sorted_records)
        duplicates = len(fresh_records) - len(sorted_records)

        def detail_sort_key(record: PharmacistRecord):
            return (
                record.serial_number is None,
                record.serial_number if record.serial_number is not None else 0,
                record.registration_number,
            )

        def format_detail(record: PharmacistRecord) -> str:
            return f"{record.registration_number} - {record.name} ({record.category})"

        sorted_new_ids = sorted(new_ids, key=lambda rid: detail_sort_key(current_map[rid]))
        sorted_removed_ids = sorted(removed_ids, key=lambda rid: detail_sort_key(existing_map[rid]))

        # Detailed changes
        new_details = [format_detail(current_map[rid]) for rid in sorted_new_ids]
        removed_details = [format_detail(existing_map[rid]) for rid in sorted_removed_ids]

        modified_ids = sorted(
            [rid for rid in common_ids if existing_map[rid] != current_map[rid]],
            key=lambda rid: detail_sort_key(current_map[rid]),
        )
        modified_count = len(modified_ids)
        modified_details = [format_detail(current_map[rid]) for rid in modified_ids]

        # Category Statistics
        def get_cat_stats(ids, mapping):
            counts = Counter(mapping[i].category for i in ids)
            return dict(sorted(counts.items()))

        new_cat_stats = get_cat_stats(sorted_new_ids, current_map)
        rem_cat_stats = get_cat_stats(sorted_removed_ids, existing_map)
        mod_cat_stats = get_cat_stats(modified_ids, current_map)  # Use modified_ids, NOT common_ids

        self.file_manager.save(list(sorted_records))
        self.backup_manager.cleanup()

        logger.info(
            "Update complete. Total: %d, 🌱 NEW: %d, 🌀 CHANGES: %d, ❌ REMOVALS: %d",
            total_count,
            new_count,
            modified_count,
            removed_count,
        )

        self._last_update_details = {
            "new_details": new_details,
            "modified_details": modified_details,
            "removed_details": removed_details,
            "new_cat_stats": new_cat_stats,
            "rem_cat_stats": rem_cat_stats,
            "mod_cat_stats": mod_cat_stats,
        }

        if os.environ.get("GITHUB_OUTPUT"):
            details_path = Path(self.file_manager.data_dir) / "update_details.json"
            with open(details_path, "w", encoding="utf-8") as f:
                json.dump(self._last_update_details, f, indent=2, ensure_ascii=False)

        self._write_update_outputs(
            update_status="updated",
            success=True,
            total_records=total_count,
            new_records=new_count,
            removed_records=removed_count,
            modified_records=modified_count,
            duplicates_removed=duplicates,
            integrity_score=1.0,
            new_details=new_details,
            removed_details=removed_details,
            modified_details=modified_details,
            new_cat_stats=new_cat_stats,
            rem_cat_stats=rem_cat_stats,
            mod_cat_stats=mod_cat_stats,
        )
        return "updated"

    def sync_to_supabase(self):
        """Sync data to Supabase."""
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SECRET_KEY")

        if not url or not key:
            logger.error("Missing Supabase credentials")
            return

        try:
            supabase = create_client(url, key)
            records = self.file_manager.load()

            logger.info(f"Syncing {len(records)} records to Supabase...")

            # Batch upsert (5 core fields only — enrichment fields already in Supabase)
            batch_size = 1000
            for i in range(0, len(records), batch_size):
                batch = [r.to_dict() for r in records[i : i + batch_size]]
                supabase.table("rph").upsert(batch, on_conflict="registration_number").execute()
                logger.info(f"Synced batch {i // batch_size + 1}")

            # Update last_sync timestamp in metadata table
            try:
                sync_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                supabase.table("metadata").upsert({"key": "last_sync", "value": sync_time}, on_conflict="key").execute()
                logger.info(f"Updated last_sync timestamp: {sync_time}")
            except Exception as e:
                logger.warning(f"Could not update metadata (table may not exist): {e}")

            logger.info("Supabase sync complete")

        except Exception as e:
            logger.error(f"Sync failed: {e}")

    def sync_to_supabase_storage(self):
        """Upload rph.json to Supabase Storage (tgpc bucket)."""
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SECRET_KEY")
        if not url or not key:
            logger.error("Missing Supabase credentials")
            return
        file_path = self.file_manager.data_dir / "rph.json"
        try:
            with open(file_path, "rb") as f:
                resp = requests.post(
                    f"{url}/storage/v1/object/tgpc/rph.json",
                    headers={
                        "Authorization": f"Bearer {key}",
                        "apikey": key,
                        "x-upsert": "true",
                    },
                    data=f,
                    timeout=300,
                )
            if resp.ok:
                logger.info("Supabase Storage sync complete")
            else:
                logger.error(f"Supabase Storage sync failed: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.error(f"Supabase Storage sync error: {e}")

    def sync_to_r2(self):
        """Sync rph.json to Cloudflare R2."""
        account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        access_key = os.environ.get("R2_ACCESS_KEY_ID")
        secret_key = os.environ.get("R2_SECRET_ACCESS_KEY")

        if not all([account_id, access_key, secret_key]):
            logger.error("Missing R2 credentials")
            return

        endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
        file_path = str(self.file_manager.data_dir / "rph.json")
        env = os.environ.copy()
        env["AWS_ACCESS_KEY_ID"] = access_key
        env["AWS_SECRET_ACCESS_KEY"] = secret_key
        try:
            result = subprocess.run(
                [
                    "aws",
                    "s3api",
                    "put-object",
                    "--endpoint-url",
                    endpoint,
                    "--region",
                    "auto",
                    "--bucket",
                    "tgpc",
                    "--key",
                    "rph.json",
                    "--body",
                    file_path,
                ],
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
            )
            if result.returncode == 0:
                logger.info("R2 sync complete")
            else:
                logger.error(f"R2 sync failed: {result.stderr.strip()}")
        except FileNotFoundError:
            logger.error("awscli not installed. Run: pip install awscli")
        except Exception as e:
            logger.error(f"R2 sync error: {e}")

    def sync_to_gdrive(self):
        """Sync rph.json to Google Drive via rclone."""
        gdrive_config_b64 = os.environ.get("RCLONE_GDRIVE_CONFIG")
        if not gdrive_config_b64:
            logger.error("Missing RCLONE_GDRIVE_CONFIG")
            return

        config_path = Path("/tmp/rclone-gdrive.conf")
        try:
            import base64

            config_path.write_bytes(base64.b64decode(gdrive_config_b64))
            result = subprocess.run(
                [
                    "rclone",
                    "copyto",
                    str(self.file_manager.data_dir / "rph.json"),
                    "gdrive:tgpc/rph.json",
                ],
                capture_output=True,
                text=True,
                timeout=300,
                env={**os.environ, "RCLONE_CONFIG": str(config_path)},
            )
            config_path.unlink(missing_ok=True)
            if result.returncode == 0:
                logger.info("GDrive sync complete")
            else:
                logger.error(f"GDrive sync failed: {result.stderr.strip()}")
        except FileNotFoundError:
            logger.error("rclone not installed")
        except Exception as e:
            logger.error(f"GDrive sync error: {e}")

    def sync_to_release(self):
        """Upload rph.json to GitHub Release."""
        tag = "rphjson"
        file_path = str(self.file_manager.data_dir / "rph.json")
        repo = os.environ.get("GITHUB_REPOSITORY", "dilludx/tgpc")

        try:
            with open(file_path) as f:
                count = len(json.load(f))
        except Exception:
            count = 0

        title = f"{count:,} records — rph.json"

        try:
            result = subprocess.run(
                ["gh", "release", "view", tag, "--repo", repo],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode != 0:
                logger.info(f"Creating release {tag}...")
                subprocess.run(
                    [
                        "gh",
                        "release",
                        "create",
                        tag,
                        "--repo",
                        repo,
                        "--title",
                        title,
                        "--notes",
                        title,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            subprocess.run(
                [
                    "gh",
                    "release",
                    "upload",
                    tag,
                    file_path,
                    "--repo",
                    repo,
                    "--clobber",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            subprocess.run(
                [
                    "gh",
                    "release",
                    "edit",
                    tag,
                    "--repo",
                    repo,
                    "--title",
                    title,
                    "--notes",
                    title,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            logger.info(f"Release sync complete ({count:,} records)")
        except FileNotFoundError:
            logger.error("gh CLI not installed")
        except Exception as e:
            logger.error(f"Release sync error: {e}")

    def sync_to_email(self):
        """Send update report via Resend email."""
        api_key = os.environ.get("RESEND_API_KEY")
        recipient = os.environ.get("NOTIFICATION_EMAIL")
        if not api_key or not recipient:
            logger.warning("Missing RESEND_API_KEY or NOTIFICATION_EMAIL")
            return

        data = getattr(self, "_last_update_details", None)
        if not data:
            logger.info("No update details found — skipping email")
            return

        new = data.get("new_details", [])
        mod = data.get("modified_details", [])
        rem = data.get("removed_details", [])

        if not new and not mod and not rem:
            logger.info("No changes — skipping email")
            return

        import re

        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)
        sync_time = now.strftime("%d %B %Y, %A, %H:%M IST")
        subj_time = now.strftime("%d%b%Y %a %H:%M IST").upper()

        def cat(s):
            m = re.search(r"\((.*?)\)", s)
            if not m:
                return "Other"
            return {
                "BPharm": "BPharm",
                "MPharm": "MPharm",
                "DPharm": "DPharm",
                "PharmD": "PharmD",
                "QC": "QC",
                "QP": "QP",
            }.get(m.group(1), m.group(1).title())

        def reg_no(s):
            m = re.search(r"(\d+)", s)
            return int(m.group(1)) if m else 0

        def fmt_html(title, items, color):
            if not items:
                return ""
            grouped = {}
            for i in items:
                grouped.setdefault(cat(i), []).append(i)
            html = f'<div style="margin-bottom:35px;"><h4 style="margin:0 0 16px;color:{color};font-size:14px;font-weight:700;text-transform:uppercase;border-bottom:2px solid {color};padding-bottom:6px;display:inline-block;letter-spacing:.5px;">{title} ({len(items)})</h4>'  # noqa: E501
            for c in sorted(grouped):
                recs = grouped[c]
                html += f'<div style="margin-bottom:18px;"><div style="font-size:11px;font-weight:700;color:#111;text-transform:uppercase;margin-bottom:6px;letter-spacing:1px;">{c} ({len(recs)})</div>'  # noqa: E501
                for r in sorted(recs, key=reg_no):
                    parts = r.split(" - ", 1)
                    reg = parts[0]
                    name = re.sub(r"\s*\(.*?\)$", "", parts[1] if len(parts) > 1 else r).strip()
                    html += f'<div style="font-size:13px;color:#6b7280;padding:4px 0;"><span style="font-family:ui-monospace,monospace;">{reg}</span> - {name}</div>'  # noqa: E501
                html += "</div>"
            return html + "</div>"

        MAX_EMAIL = 200
        new_t, mod_t, rem_t = new[:MAX_EMAIL], mod[:MAX_EMAIL], rem[:MAX_EMAIL]

        text = f"TGPC RPh Registry Sync Report\n{sync_time}\n\n"
        html = (
            '<!DOCTYPE html><html><head><meta charset="UTF-8"></head>'
            '<body style="font-family:-apple-system,sans-serif;background:#fff;padding:15px 20px;color:#333;line-height:1.3;margin:0;">'  # noqa: E501
            '<div style="max-width:600px;">'
            f'<h2 style="margin:0;font-size:17px;line-height:1.2;"><span style="color:#00cc66;">TGPC</span> <span style="color:#ef4444;">RPh</span> <span style="color:#808080;">Registry</span> Sync Report</h2>'  # noqa: E501
            f'<div style="color:#666;font-size:12px;margin-bottom:30px;font-weight:500;">{sync_time}</div>'
            f"{fmt_html('🌱 NEW', new_t, '#00cc66')}{fmt_html('🌀 CHANGES', mod_t, '#3b82f6')}{fmt_html('❌ REMOVALS', rem_t, '#ef4444')}"  # noqa: E501
            '<div style="margin-top:15px;font-size:11px;color:#888;padding-top:10px;">'
            '<div style="font-weight:700;"><span style="color:#00cc66;">TGPC</span> <span style="color:#ef4444;">RPh</span> <span style="color:#808080;">Registry</span></div>'  # noqa: E501
            "<div>Open-Source TGPC Pharmacist Data</div></div></div></body></html>"
        )
        for label, items, total in [("NEW", new_t, new), ("CHANGES", mod_t, mod), ("REMOVALS", rem_t, rem)]:
            if total:
                text += (
                    f"{label} ({len(total)}):\n" + "\n".join(sorted(items, key=lambda x: (cat(x), reg_no(x)))) + "\n\n"
                )
        text += "---\nTGPC RPh Registry\nOpen-Source TGPC Pharmacist Data"

        parts = []
        if new:
            parts.append(f"🌱 {len(new)}")
        if mod:
            parts.append(f"🌀 {len(mod)}")
        if rem:
            parts.append(f"❌ {len(rem)}")
        subject = " | ".join(parts + ["RPh Data Sync", subj_time])

        import tempfile

        payload = json.dumps(
            {
                "from": "RPh Data Sync <onboarding@resend.dev>",
                "to": [recipient],
                "subject": subject,
                "text": text,
                "html": html,
            }
        )
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                f.write(payload)
                f.flush()
                tmp = f.name
            result = subprocess.run(
                [
                    "curl",
                    "-s",
                    "-X",
                    "POST",
                    "https://api.resend.com/emails",
                    "-H",
                    f"Authorization: Bearer {api_key}",
                    "-H",
                    "Content-Type: application/json",
                    "-d",
                    f"@{tmp}",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            os.unlink(tmp)
            if result.returncode == 0 and "error" not in result.stdout:
                logger.info(f"Email sent: {result.stdout.strip()}")
            else:
                logger.warning(f"Resend API error: {result.stdout.strip()}")
        except Exception as e:
            logger.warning(f"Email send error: {e}")

    def run_enrichment(
        self,
        start: int = 1,
        stop: int = None,
    ):
        """
        Run enrichment for serial number range.

        Args:
            start: Start from serial number (default: 1)
            stop: Stop at serial number (default: all)
        """

        # Health check
        if not self.scraper.health_check():
            logger.error("Health check failed. Aborting enrichment.")
            return

        logger.info("Starting enrichment...")

        # Create Supabase client for live upsert
        supabase = None
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SECRET_KEY")
        if url and key:
            supabase = create_client(url, key)

        # Load Data
        rph_records = self.file_manager.load("rph.json")

        # Create lookup by registration number
        rph_lookup = {r.serial_number: r for r in rph_records}

        # Identify Pending - check Supabase for already enriched records
        done_ids = set()
        if supabase:
            BATCH = 1000
            for i in range(0, len(rph_records), BATCH):
                end = min(i + BATCH - 1, len(rph_records) - 1)
                try:
                    resp = (
                        supabase.table("rph")
                        .select("registration_number, gender, validity_date, status, education, work_experience")
                        .order("registration_number")
                        .range(i, end)
                        .execute()
                    )
                    for r in resp.data:
                        if (
                            r.get("gender")
                            or r.get("validity_date")
                            or r.get("status")
                            or r.get("education")
                            or r.get("work_experience")
                        ):
                            done_ids.add(r["registration_number"])
                except Exception as e:
                    logger.warning(f"Failed to check enrichment status batch {i}: {e}")
            logger.info(f"Found {len(done_ids)} already enriched records in Supabase")
        else:
            logger.warning("Supabase credentials missing — all records will be considered pending")

        # Sort by serial number ascending (start from serial 1)
        pending_records = [r for r in rph_records if r.registration_number not in done_ids]
        pending_records.sort(key=lambda r: r.serial_number or 0)

        if not pending_records:
            logger.info("No pending records to enrich.")
            return

        total_pending = len(pending_records)
        logger.info(f"Total pending: {total_pending} records")

        # Setup Photos Directory
        img_dir = Path(self.config.enrichment_directory) / "img"
        img_dir.mkdir(parents=True, exist_ok=True)

        # Filter by start/stop range - use serial_number from rph.json as position
        if start != 1 or stop is not None:
            rph_records_all = self.file_manager.load("rph.json")
            rph_records_all.sort(key=lambda r: r.serial_number or 0)

            filtered = []
            for i, r in enumerate(rph_records_all):
                if start and i + 1 < start:
                    continue
                if stop and i + 1 > stop:
                    break
                if r.registration_number not in done_ids:
                    filtered.append(r)
            pending_records = filtered

            start_str = f"serial {start}" if start else "all"
            stop_str = f"serial {stop}" if stop else "end"
            logger.info(f"Processing {start_str} to {stop_str} ({len(pending_records)} records)")

        if not pending_records:
            logger.info("No records in range.")
            return

        # Process records sequentially
        total_processed = self._process_records_sequential(pending_records, rph_lookup, img_dir, supabase=supabase)

        # Keep progress file for tracking
        if total_processed > 0:
            logger.info(f"Enrichment complete: {total_processed} records processed")
        else:
            logger.info("No records processed")

    def _process_records_sequential(
        self, pending_records, rph_lookup, img_dir, ip_rotation_interval=500, supabase=None
    ):
        """Process records sequentially."""
        total_processed = 0

        for idx, record in enumerate(pending_records):
            serial = record.serial_number
            reg_no = record.registration_number
            try:
                # Scrape using original synchronous scraper
                details = self.scraper.extract_detailed_info(reg_no, img_dir)
                if not details:
                    continue

                # Get basic info from rph.json lookup for validation
                basic_info = rph_lookup.get(serial)

                # CRITICAL SAFETY CHECK - Validate all details match
                mismatches = []
                if details.registration_number and details.registration_number.lower() != reg_no.lower():
                    mismatches.append(f"registration_number: expected '{reg_no}', got '{details.registration_number}'")
                if details.name and basic_info and details.name.strip().lower() != basic_info.name.strip().lower():
                    mismatches.append(f"name: expected '{basic_info.name}', got '{details.name}'")
                if (
                    details.father_name
                    and basic_info
                    and details.father_name.strip().lower() != basic_info.father_name.strip().lower()
                ):
                    mismatches.append(f"father_name: expected '{basic_info.father_name}', got '{details.father_name}'")
                if (
                    details.category
                    and basic_info
                    and details.category.strip().lower() != basic_info.category.strip().lower()
                ):
                    mismatches.append(f"category: expected '{basic_info.category}', got '{details.category}'")

                if mismatches:
                    logger.critical(
                        f"DATA CORRUPTION PREVENTED for serial {serial} ({reg_no}): " + "; ".join(mismatches)
                    )
                    raise DataIntegrityError(
                        f"Data Integrity Violation: Mismatched fields for {reg_no}. Stopping to prevent corruption."
                    )

                logger.info(
                    f"✅ DATA VALIDATION PASSED: serial {serial} ({reg_no}) - {details.name} ({details.category})"
                )

                basic_info = rph_lookup.get(serial)
                if not basic_info:
                    logger.warning(f"Basic info not found for {reg_no}, using scraped data")

                basic_data = {
                    "registration_number": (
                        basic_info.registration_number if basic_info else details.registration_number
                    ),
                    "name": (basic_info.name if basic_info else details.name),
                    "father_name": (basic_info.father_name if basic_info else details.father_name),
                    "gender": details.gender or "",
                    "category": (basic_info.category if basic_info else details.category),
                    "status": details.status or "",
                    "serial_number": (basic_info.serial_number if basic_info else None),
                }

                # Combine basic info + extracted details
                extracted_data = details.to_detailed_dict()
                data = {**extracted_data, **basic_data}

                total_processed += 1

                # Upsert to Supabase immediately
                if supabase:
                    try:
                        supabase.table("rph").upsert(data, on_conflict="registration_number").execute()
                    except Exception as e:
                        logger.warning(f"Failed to upsert enriched record {reg_no} to Supabase: {e}")

            except DataIntegrityError:
                raise
            except Exception as e:
                logger.error(f"Enrichment failed for {reg_no}: {e}")

        return total_processed
