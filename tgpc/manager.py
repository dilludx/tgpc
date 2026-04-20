"""
Core management logic for TGPC system.
Handles file storage, backups, daily updates, and cloud sync.
"""

import json
import shutil
import os
import base64
import time
import random
import subprocess
import requests
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Iterable
from collections import Counter

from supabase import create_client

from tgpc.utils import Config, TGPCError, setup_logging
from tgpc.progress import ProgressTracker
from tgpc.scraper import Scraper, PharmacistRecord

logger = setup_logging("tgpc.manager")


def connect_warp():
    """Connect to Cloudflare Warp VPN with IP rotation."""
    try:
        # Disconnect first to ensure IP changes
        subprocess.run(['warp-cli', 'disconnect'], capture_output=True, text=True, timeout=30)
        time.sleep(2)  # Wait for disconnection to complete
        
        # Connect to get new IP
        result = subprocess.run(['warp-cli', 'connect'], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            logger.info("Cloudflare Warp connected successfully")
            time.sleep(3)  # Wait for connection to stabilize
            
            # Get and display current IP
            ip = get_current_ip()
            if ip:
                logger.info(f"Current IP address: {ip}")
            else:
                logger.warning("Could not retrieve current IP address")
            return True
        else:
            logger.error(f"Failed to connect Warp: {result.stderr}")
            return False
    except FileNotFoundError:
        logger.warning("warp-cli not found. Skipping Warp connection.")
        return False
    except subprocess.TimeoutExpired:
        logger.error("Warp connection timed out")
        return False
    except Exception as e:
        logger.error(f"Error connecting Warp: {e}")
        return False


def disconnect_warp():
    """Disconnect from Cloudflare Warp VPN."""
    try:
        result = subprocess.run(['warp-cli', 'disconnect'], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            logger.info("Cloudflare Warp disconnected successfully")
            return True
        else:
            logger.error(f"Failed to disconnect Warp: {result.stderr}")
            return False
    except FileNotFoundError:
        logger.warning("warp-cli not found. Skipping Warp disconnection.")
        return False
    except subprocess.TimeoutExpired:
        logger.error("Warp disconnection timed out")
        return False
    except Exception as e:
        logger.error(f"Error disconnecting Warp: {e}")
        return False


def get_current_ip():
    """Get current public IP address."""
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=10)
        if response.status_code == 200:
            ip = response.json().get('ip')
            return ip
        else:
            logger.error(f"Failed to get IP: HTTP {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error getting IP address: {e}")
        return None


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

            # Catch urllib3 timeout errors (common in GitHub Actions)
            try:
                from urllib3.exceptions import ConnectTimeoutError, MaxRetryError, NewConnectionError
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
                from urllib3.exceptions import ConnectTimeoutError, MaxRetryError, NewConnectionError
                if isinstance(current, (ConnectTimeoutError, MaxRetryError, NewConnectionError)):
                    return type(current).__name__
            except ImportError:
                pass
                
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
            "blocked": False,
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
        key = os.environ.get("SUPABASE_SECRET_KEY")
        
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

    def run_enrichment(self, batch_size: int = 300, start: int = 1, stop: int = None, force: bool = False):
        """
        Run enrichment in batches.
        
        Args:
            batch_size: Records per batch (default 300)
            start: Start from serial number (default: 1)
            stop: Stop at serial number (default: all)
            force: Re-extract even if already done
        """
        
        # Get current IP before disconnecting Warp
        old_ip = get_current_ip()
        if old_ip:
            logger.info(f"Current IP before Warp rotation: {old_ip}")
        else:
            logger.warning("Could not get current IP before Warp rotation")
        
        # Always disconnect Warp first to ensure IP rotation
        logger.info("Disconnecting Warp to ensure IP rotation...")
        disconnect_warp()
        time.sleep(2)
        
        # Connect to Cloudflare Warp with IP rotation
        logger.info("Connecting to Cloudflare Warp with new IP...")
        warp_connected = connect_warp()
        if not warp_connected:
            logger.warning("Failed to connect to Warp. Proceeding without VPN.")
        
        # Verify IP changed
        new_ip = get_current_ip()
        if new_ip:
            logger.info(f"New IP after Warp rotation: {new_ip}")
            if old_ip and new_ip == old_ip:
                logger.warning(f"IP did not change (still {new_ip}). Attempting again...")
                # Retry IP rotation
                disconnect_warp()
                time.sleep(2)
                warp_connected = connect_warp()
                new_ip = get_current_ip()
                if new_ip:
                    logger.info(f"IP after retry: {new_ip}")
                    if new_ip == old_ip:
                        logger.error("IP still did not change after retry. Proceeding with current IP.")
                    else:
                        logger.info("IP successfully changed after retry.")
        else:
            logger.warning("Could not get new IP after Warp rotation")
        
        # Health check with automatic Warp retry on blocking
        max_retries = 3
        health_passed = False
        
        for attempt in range(max_retries):
            if self.scraper.health_check():
                health_passed = True
                logger.info("Health check passed")
                break
            else:
                logger.warning(f"Health check failed (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    logger.info("Attempting to change IP via Warp...")
                    # Disconnect and reconnect to get new IP
                    disconnect_warp()
                    time.sleep(2)
                    warp_connected = connect_warp()
                    if not warp_connected:
                        logger.warning("Failed to reconnect Warp. Proceeding without VPN.")
                    time.sleep(3)  # Wait for connection to stabilize
                else:
                    logger.error("Health check failed after all retry attempts. Aborting.")
                    return
        
        # Progress file for resume capability
        progress_dir = Path(self.config.data_directory) / "progress"
        progress_dir.mkdir(exist_ok=True)
        progress_file = Path(self.config.data_directory) / "progress" / "prog"
        progress_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize sophisticated progress tracker
        progress_tracker = ProgressTracker(progress_file)
        
        batch_count = 0
        try:
            progress = progress_tracker.load()
            if progress:
                batch_count = progress.get("batch_count", 0)
                logger.info(f"Resuming from batch {batch_count}")
        except ValueError as e:
            logger.warning(f"Progress file validation failed, starting fresh: {e}")
            batch_count = 0
        
        logger.info(f"Starting enrichment (batch_size={batch_size})...")
        
        # Load Data
        rx_records = self.file_manager.load("rx.json")
        details_dir = Path(self.config.data_directory) / "details"
        details_dir.mkdir(parents=True, exist_ok=True)
        
        # Create lookup by registration number
        rx_lookup = {r.serial_number: r for r in rx_records}
        
        # Identify Pending - check for existing individual detail files
        done_ids = {f.stem for f in details_dir.glob("*.json")}
        
        # Sort by serial number ascending (start from serial 1)
        pending_records = [r for r in rx_records if r.registration_number not in done_ids]
        pending_records.sort(key=lambda r: r.serial_number or 0)
        
        if not pending_records:
            logger.info("No pending records to enrich.")
            # Clear progress file when done
            if progress_file.exists():
                progress_file.unlink()
            return
        
        total_pending = len(pending_records)
        logger.info(f"Total pending: {total_pending} records")
        
        # Setup Photos Directory
        photos_dir = Path(self.config.data_directory) / "photos"
        photos_dir.mkdir(parents=True, exist_ok=True)
        
        # Filter by start/stop range - use serial_number from rx.json as position
        if start or stop:
            rx_records_all = self.file_manager.load("rx.json")
            rx_records_all.sort(key=lambda r: r.serial_number or 0)
            
            filtered = []
            for i, r in enumerate(rx_records_all):
                if start and i+1 < start:
                    continue
                if stop and i+1 > stop:
                    break
                if not force and r.registration_number in done_ids:
                    continue
                filtered.append(r)
            pending_records = filtered
            
            if force:
                logger.info(f"--force: re-extracting {len([r for r in pending_records if r.registration_number in done_ids])} already done records")
            
            start_str = f"serial {start}" if start else "all"
            stop_str = f"serial {stop}" if stop else "end"
            logger.info(f"Processing {start_str} to {stop_str} ({len(pending_records)} records)")
        
        if not pending_records:
            logger.info("No records in range.")
            return
        
        # Process in batches
        batch_num = 0
        total_processed = 0
        
        while pending_records:
            
            batch_num += 1
            progress_tracker.increment_batch()
            batch_count += 1
            
            batch_records = pending_records[:batch_size]
            pending_records = pending_records[batch_size:]
            
            serial_start = batch_records[0].serial_number
            serial_end = batch_records[-1].serial_number
            logger.info(f"Batch {batch_count}: Processing serial {serial_start}-{serial_end} ({len(batch_records)} records)")
            
            processed_in_batch = 0
            
            for record in batch_records:
                serial = record.serial_number
                reg_no = record.registration_number
                try:
                    # Scrape
                    details = self.scraper.extract_detailed_info(reg_no)
                    if not details: 
                        continue
                    
                    # Get basic info from rx.json lookup FIRST for validation
                    basic_info = rx_lookup.get(serial)
                    
                    # CRITICAL SAFETY CHECK - Validate all details match the same person
                    mismatches = []
                    if details.registration_number and details.registration_number.lower() != reg_no.lower():
                        mismatches.append(f"registration_number: expected '{reg_no}', got '{details.registration_number}'")
                    if details.name and basic_info and details.name.strip().lower() != basic_info.name.strip().lower():
                        mismatches.append(f"name: expected '{basic_info.name}', got '{details.name}'")
                    if details.father_name and basic_info and details.father_name.strip().lower() != basic_info.father_name.strip().lower():
                        mismatches.append(f"father_name: expected '{basic_info.father_name}', got '{details.father_name}'")
                    if details.category and basic_info and details.category.strip().lower() != basic_info.category.strip().lower():
                        mismatches.append(f"category: expected '{basic_info.category}', got '{details.category}'")
                    
                    if mismatches:
                        logger.critical(f"DATA CORRUPTION PREVENTED for serial {serial} ({reg_no}): " + "; ".join(mismatches))
                        raise DataIntegrityError(f"Data Integrity Violation: Mismatched fields for {reg_no}. Stopping to prevent corruption.")

                    logger.info(f"✅ DATA VALIDATION PASSED: serial {serial} ({reg_no}) - {details.name} ({details.category})")

                    basic_info = rx_lookup.get(serial)
                    if not basic_info:
                        logger.warning(f"Basic info not found for {reg_no}, using scraped data")
                    
                    basic_data = {
                        "registration_number": (basic_info.registration_number if basic_info else details.registration_number),
                        "name": (basic_info.name if basic_info else details.name),
                        "father_name": (basic_info.father_name if basic_info else details.father_name),
                        "gender": details.gender or "",
                        "category": (basic_info.category if basic_info else details.category),
                        "status": details.status or "",
                        "serial_number": (basic_info.serial_number if basic_info else None)
                    }
                    
                    # Combine basic info + extracted details
                    extracted_data = details.to_detailed_dict()
                    # Merge: use basic_data for core fields, extracted_data for extra fields (education, work_experience)
                    data = {**extracted_data, **basic_data}

                    # Save Photo Locally with smart optimization based on original resolution
                    if details.photo_base64:
                        try:
                            from PIL import Image
                            import io
                            
                            file_data = base64.b64decode(details.photo_base64)
                            img = Image.open(io.BytesIO(file_data))
                            
                            # Get original resolution
                            original_width, original_height = img.size
                            original_pixels = original_width * original_height
                            
                            # Convert to RGB if necessary (for PNG with transparency)
                            if img.mode in ('RGBA', 'LA', 'P'):
                                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                                rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                                img = rgb_img
                            
                            # Smart optimization: resize to uniform 400x512 based on original resolution
                            target_width, target_height = 400, 512
                            target_pixels = target_width * target_height  # 204,800 pixels
                            
                            if original_pixels < target_pixels:
                                # Low resolution: upscale with maximum quality to preserve detail
                                resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                                quality = 100
                                method = 6
                            else:
                                # High resolution: downscale with maximum quality to preserve detail
                                resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                                quality = 100
                                method = 5
                            
                            # Save as WebP with smart quality settings
                            webp_path = photos_dir / f"{reg_no}.webp"
                            resized.save(webp_path, 'WebP', quality=quality, method=method)
                            
                        except Exception as e:
                            logger.error(f"Photo save failed for serial {serial}: {e}")
                    
# Save to individual JSON file
                    detail_file = details_dir / f"{reg_no}.json"
                    with open(detail_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    processed_in_batch += 1
                    total_processed += 1
                    
                    # Save progress after each record with integrity checks
                    progress_tracker.update_progress(
                        total_processed=total_processed,
                        last_serial=record.serial_number,
                        remaining=len(pending_records) + len(batch_records) - processed_in_batch
                    )
                    
                    # Rate limit - 1.5-2.5 seconds between requests (optimized for speed)
                    time.sleep(random.uniform(1.5, 2.5))
                
                except DataIntegrityError:
                    raise
                except Exception as e:
                    logger.error(f"Enrichment failed for {reg_no}: {e}")
            
            logger.info(f"Batch {batch_count} complete: {processed_in_batch}/{len(batch_records)} processed")
            
            # Save progress periodically (every batch) with integrity checks
            progress_tracker.update_progress(
                total_processed=total_processed,
                last_serial=serial_end,
                remaining=len(pending_records)
            )
        
        # Disconnect from Cloudflare Warp before sync (Warp slows down upload)
        if warp_connected:
            logger.info("Disconnecting from Cloudflare Warp...")
            disconnect_warp()
        
        # Sync to Google Drive after all records are extracted (excluding rx.json)
        logger.info("Syncing to Google Drive...")
        try:
            # details
            logger.info("  → Syncing details...")
            result = subprocess.run(['rclone', 'copy', str(self.file_manager.data_dir / 'details'), 'gdrive:tgpc/details', 
                          '--transfers', '16', '--checkers', '16', '--drive-chunk-size', '32M'], 
                          capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"rclone details sync failed: {result.stderr}")
                raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
            logger.info("  → details: 100% ✓")
            # photos
            logger.info("  → Syncing photos...")
            result = subprocess.run(['rclone', 'copy', str(self.file_manager.data_dir / 'photos'), 'gdrive:tgpc/photos',
                          '--transfers', '16', '--checkers', '16', '--drive-chunk-size', '32M'],
                          capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"rclone photos sync failed: {result.stderr}")
                raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)
            logger.info("  → photos: 100% ✓")
            logger.info("✅ Sync to Google Drive complete")
        except subprocess.CalledProcessError as e:
            logger.error(f"Google Drive sync failed: {e}")
        
        # Keep progress file for tracking across batches
        if not pending_records:
            logger.info("All enrichment complete! Progress saved for tracking.")
        else:
            logger.info(f"Enrichment paused: {len(pending_records)} records remaining, {total_processed} processed")
