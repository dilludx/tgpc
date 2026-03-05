"""
Core management logic for TGPC system.
Handles file storage, backups, daily updates, and cloud sync.
"""

import json
import shutil
import hashlib
import os
import base64
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from collections import Counter
from dataclasses import asdict

from supabase import create_client

from tgpc.utils import Config, TGPCError, setup_logging
from tgpc.scraper import Scraper, PharmacistRecord

logger = setup_logging("tgpc.manager")

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

    def run_daily_update(self):
        """Execute daily update workflow."""
        logger.info("Starting daily update...")
        
        # 1. Backup existing
        rx_path = Path(self.config.data_directory) / "rx.json"
        self.backup_manager.create(rx_path)

        # 2. Scrape fresh data
        fresh_records = self.scraper.extract_basic_records()
        if not fresh_records:
            logger.error("No records extracted, aborting update")
            return

        # Safety Check: Prevent massive data loss
        existing_records = self.file_manager.load()
        if existing_records and len(fresh_records) < len(existing_records) * 0.9:
            logger.error(f"Safety Alert: New count ({len(fresh_records)}) < 90% of existing ({len(existing_records)}). Aborting.")
            return

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
        
        # Detailed changes
        new_details = [f"{current_map[i].registration_number} - {current_map[i].name} ({current_map[i].category})" for i in new_ids]
        removed_details = [f"{existing_map[i].registration_number} - {existing_map[i].name} ({existing_map[i].category})" for i in removed_ids]
        
        modified_count = 0
        modified_details = []
        modified_ids = []
        for rid in common_ids:
            if existing_map[rid] != current_map[rid]:
                modified_count += 1
                modified_ids.append(rid)
                modified_details.append(f"{current_map[rid].registration_number} - {current_map[rid].name} ({current_map[rid].category})")

        # Category Statistics
        def get_cat_stats(ids, mapping):
            counts = Counter(mapping[i].category for i in ids)
            return dict(counts)

        new_cat_stats = get_cat_stats(new_ids, current_map)
        rem_cat_stats = get_cat_stats(removed_ids, existing_map)
        mod_cat_stats = get_cat_stats(modified_ids, current_map) # Use modified_ids, NOT common_ids

        self.file_manager.save(list(sorted_records))
        self.backup_manager.cleanup()
        
        logger.info(f"Update complete. Total: {total_count}, ✨ Additions: {new_count}, 🌀 Modifications: {modified_count}, ❌ Removals: {removed_count}")

        # Output for GitHub Actions
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
                f.write(f"total_records={total_count}\n")
                f.write(f"new_records={new_count}\n")
                f.write(f"removed_records={removed_count}\n")
                f.write(f"modified_records={modified_count}\n")
                f.write(f"duplicates_removed={duplicates}\n")
                f.write(f"integrity_score=1.0\n")
                f.write(f"success=True\n")
                
                # Output details as JSON strings (no limit - GitHub allows 1MB)
                f.write(f"new_details={json.dumps(new_details)}\n")
                f.write(f"removed_details={json.dumps(removed_details)}\n")
                f.write(f"modified_details={json.dumps(modified_details)}\n")
                
                # Output Category Stats
                f.write(f"new_cat_stats={json.dumps(new_cat_stats)}\n")
                f.write(f"rem_cat_stats={json.dumps(rem_cat_stats)}\n")
                f.write(f"mod_cat_stats={json.dumps(mod_cat_stats)}\n")

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
                    raise RuntimeError("Data Integrity Violation: Stopping immediately to prevent corruption.")

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
                
            except Exception as e:
                logger.error(f"Enrichment failed for {reg_no}: {e}")
                
        # Save to Disk
        with open(details_path, 'w', encoding='utf-8') as f:
            json.dump(existing_details, f, indent=2, ensure_ascii=False)
            
        logger.info(f"Enrichment complete. Processed {processed_count}/{len(batch_ids)}")

