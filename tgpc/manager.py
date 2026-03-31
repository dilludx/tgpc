"""
Core management logic for TGPC system.
Handles file storage, backups, daily updates, and cloud sync.
"""

import json
import shutil
import os
import base64
import time
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Iterable
from collections import Counter

from supabase import create_client

from tgpc.utils import Config, TGPCError, setup_logging
from tgpc.scraper import Scraper, PharmacistRecord

logger = setup_logging("tgpc.manager")


class DataIntegrityError(RuntimeError):
    """Raised when scraped detail data does not match the requested record."""


class FileManager:
    """Handles local file storage."""
    
    def __init__(self, config: Config):
        self.data_dir = Path(config.data_directory)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save(self, records: List[PharmacistRecord], filename: str = "rx.json") -> Path:
        """Save records to JSON."""
        path = self.data_dir / filename
        data = [r.to_dict() for r in records]
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Saved {len(records)} records to {path}")
        return path

    def load(self, filename: str = "rx.json") -> List[PharmacistRecord]:
        """Load records from JSON."""
        path = self.data_dir / filename
        if not path.exists(): return []
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return [PharmacistRecord(**d) for d in data]

class BackupManager:
    """Handles secure backups."""
    
    def __init__(self, config: Config):
        self.backup_dir = Path(config.data_directory) / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create(self, source: Path) -> str:
        """Create timestamped backup."""
        if not source.exists(): return ""
        
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = self.backup_dir / f"rx_backup_{ts}.json"
        shutil.copy2(source, dest)
        logger.info(f"Backup created: {dest}")
        return str(dest)

    def cleanup(self, days: int = 30) -> int:
        """Remove old backups. Returns count of deleted files."""
        cutoff = datetime.now() - timedelta(days=days)
        deleted = 0
        for f in self.backup_dir.glob("rx_backup_*.json"):
            try:
                ts = f.stem.split('_', 2)[2]
                if datetime.strptime(ts, "%Y%m%d_%H%M%S") < cutoff:
                    f.unlink()
                    deleted += 1
            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse backup file {f.name}: {e}")
            except OSError as e:
                logger.warning(f"Could not delete backup file {f.name}: {e}")
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
            if isinstance(current, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
                return True

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
        return type(error).__name__

    def _write_update_outputs(self, **values) -> None:
        output_path = os.environ.get("GITHUB_OUTPUT")
        if not output_path:
            return

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
        }
        defaults.update(values)

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
        
        # 1. Backup existing
        rx_path = Path(self.config.data_directory) / "rx.json"
        self.backup_manager.create(rx_path)
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
            logger.error(f"Safety Alert: New count ({len(fresh_records)}) < 90% of existing ({len(existing_records)}). Aborting.")
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
        mod_cat_stats = get_cat_stats(modified_ids, current_map) # Use modified_ids, NOT common_ids

        self.file_manager.save(list(sorted_records))
        self.backup_manager.cleanup()
        
        logger.info(f"Update complete. Total: {total_count}, 🌱 NEW: {new_count}, 🌀 CHANGES: {modified_count}, ❌ REMOVALS: {removed_count}")

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
        key = os.environ.get("SUPABASE_SERVICE_KEY")
        
        if not url or not key:
            logger.error("Missing Supabase credentials")
            return

        try:
            supabase = create_client(url, key)
            records = self.file_manager.load()
            
            logger.info(f"Syncing {len(records)} records to Supabase...")
            
            # Batch upsert
            batch_size = 1000
            for i in range(0, len(records), batch_size):
                batch = [r.to_dict() for r in records[i:i+batch_size]]
                supabase.table('rx').upsert(batch, on_conflict='registration_number').execute()
                logger.info(f"Synced batch {i//batch_size + 1}")
            
            # Update last_sync timestamp in metadata table
            try:
                sync_time = datetime.now().isoformat()
                supabase.table('metadata').upsert({
                    'key': 'last_sync',
                    'value': sync_time
                }, on_conflict='key').execute()
                logger.info(f"Updated last_sync timestamp: {sync_time}")
            except Exception as e:
                logger.warning(f"Could not update metadata (table may not exist): {e}")
                
            logger.info("Supabase sync complete")
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")

    def run_enrichment(self, batch_size: int = 50):
        """Run enrichment pipeline."""
        logger.info(f"Starting enrichment batch ({batch_size})...")
        
        # Load Data
        rx_records = self.file_manager.load("rx.json")
        details_path = Path(self.config.data_directory) / "rxdetails.json"
        
        existing_details = {}
        if details_path.exists():
            with open(details_path, 'r', encoding='utf-8') as f:
                existing_details = json.load(f)
                
        # Identify Pending
        all_ids = {r.registration_number for r in rx_records}
        done_ids = set(existing_details.keys())
        pending_ids = list(all_ids - done_ids)
        pending_ids.sort() # Deterministic order
        
        if not pending_ids:
            logger.info("No pending records to enrich.")
            return

        batch_ids = pending_ids[:batch_size]
        logger.info(f"Processing {len(batch_ids)} records...")
        
        # Setup Photos Directory
        photos_dir = Path(self.config.data_directory) / "photos"
        photos_dir.mkdir(parents=True, exist_ok=True)
        
        processed_count = 0
        
        for reg_no in batch_ids:
            try:
                # Scrape
                details = self.scraper.extract_detailed_info(reg_no)
                if not details: 
                    continue
                
                # CRITICAL SAFETY CHECK
                # Ensure the data we got belongs to the ID we asked for
                if details.registration_number != reg_no:
                    logger.critical(f"SECURITY MISMATCH! Requested {reg_no} but got data for {details.registration_number}")
                    raise DataIntegrityError("Data Integrity Violation: Stopping immediately to prevent corruption.")

                logger.info(f"✅ MATCH CONFIRMED: {reg_no}")

                # Convert to dictionary for storage
                data = details.to_detailed_dict()

                # Save Photo Locally with WebP conversion
                if details.photo_base64:
                    try:
                        file_data = base64.b64decode(details.photo_base64)
                        
                        # Convert to WebP for better compression
                        try:
                            from PIL import Image
                            import io
                            
                            # Open image from bytes
                            img = Image.open(io.BytesIO(file_data))
                            
                            # Convert to RGB if necessary (for PNG with transparency)
                            if img.mode in ('RGBA', 'LA', 'P'):
                                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                                img = rgb_img
                            
                            # Save as WebP with good quality/compression balance
                            webp_path = photos_dir / f"{reg_no}.webp"
                            img.save(webp_path, 'WebP', quality=85, method=6)
                            
                            # Store relative path for WebP
                            data['photo_path'] = f"photos/{reg_no}.webp"
                            data['photo_format'] = 'webp'
                            
                        except ImportError:
                            # Fallback to JPEG if Pillow not available
                            file_path = photos_dir / f"{reg_no}.jpg"
                            with open(file_path, "wb") as f:
                                f.write(file_data)
                            
                            # Store relative path for JPEG
                            data['photo_path'] = f"photos/{reg_no}.jpg"
                            data['photo_format'] = 'jpeg'
                            
                    except Exception as e:
                        logger.error(f"Photo save failed for {reg_no}: {e}")
                
                # Save to memory
                existing_details[reg_no] = data
                processed_count += 1
                
                # Rate limit
                time.sleep(1) 
                
            except DataIntegrityError:
                raise
            except Exception as e:
                logger.error(f"Enrichment failed for {reg_no}: {e}")
                
        # Save to Disk
        with open(details_path, 'w', encoding='utf-8') as f:
            json.dump(existing_details, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Enrichment complete. Processed {processed_count}/{len(batch_ids)}")
