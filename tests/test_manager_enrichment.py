import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Mock supabase before importing manager
sys.modules["supabase"] = MagicMock()

from tgpc.manager import DataIntegrityError, Manager
from tgpc.scraper import PharmacistRecord
from tgpc.utils import Config


class DetailScraper:
    def __init__(self, details_by_id):
        self.details_by_id = details_by_id

    def health_check(self):
        return True

    def extract_detailed_info(self, reg_no, img_dir=None):
        return self.details_by_id.get(reg_no)


def record(reg_no, name="Name", father="Father", category="BPharm", serial=1):
    return PharmacistRecord(
        registration_number=reg_no,
        name=name,
        father_name=father,
        category=category,
        serial_number=serial,
    )


class ManagerEnrichmentTests(unittest.TestCase):
    def _make_manager(self, temp_dir: str, details_by_id):
        with patch("tgpc.manager.Config.load", return_value=Config(data_directory=temp_dir)):
            with patch("tgpc.manager.Scraper", return_value=DetailScraper(details_by_id)):
                return Manager()

    @patch("tgpc.manager.time.sleep", return_value=None)
    def test_run_enrichment_saves_first_pending_record_in_sorted_order(self, _sleep):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = self._make_manager(
                temp_dir,
                {
                    "RX001": PharmacistRecord(
                        registration_number="RX001",
                        name="Alpha",
                        father_name="Parent",
                        category="BPharm",
                        validity_date="2026-12-31",
                        education=[{"qualification": "BPharm", "university": "OU", "year": "2018"}],
                        work_experience={"address": "Clinic Street"},
                    )
                },
            )
            manager.file_manager.save(
                [
                    record("RX002", serial=2),
                    record("RX001", name="Alpha", father="Parent", serial=1),
                ]
            )

            manager.run_enrichment(skip_validation=True, skip_sync=True)

            detail_file = Path(temp_dir, "jsn", "RX001.json")
            self.assertTrue(detail_file.exists())
            details = json.loads(detail_file.read_text(encoding="utf-8"))
            self.assertEqual(details["validity_date"], "2026-12-31")
            self.assertEqual(details["education"][0]["qualification"], "BPharm")
            self.assertEqual(details["work_experience"]["address"], "Clinic Street")

    @patch("tgpc.manager.time.sleep", return_value=None)
    def test_run_enrichment_raises_on_registration_mismatch(self, _sleep):
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = self._make_manager(
                temp_dir,
                {
                    "RX001": PharmacistRecord(
                        registration_number="WRONG001",
                        name="Wrong Record",
                        father_name="Parent",
                        category="BPharm",
                    )
                },
            )
            manager.file_manager.save([record("RX001", serial=1)])

            with self.assertRaises(DataIntegrityError):
                manager.run_enrichment(skip_validation=True, skip_sync=True)

            self.assertFalse(Path(temp_dir, "jsn", "RX001.json").exists())


if __name__ == "__main__":
    unittest.main()
