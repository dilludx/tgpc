import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Mock supabase before importing manager
sys.modules["supabase"] = MagicMock()

from tgpc.manager import Manager
from tgpc.scraper import PharmacistRecord
from tgpc.utils import Config


class FakeScraper:
    def __init__(self, records):
        self._records = records

    def extract_basic_records(self):
        return self._records


def record(reg_no, name, father, category, serial):
    return PharmacistRecord(
        registration_number=reg_no,
        name=name,
        father_name=father,
        category=category,
        serial_number=serial,
    )


class ManagerUpdateTests(unittest.TestCase):
    def _make_manager(self, temp_dir: str, fresh_records):
        with patch("tgpc.manager.Config.load", return_value=Config(data_directory=temp_dir)):
            with patch("tgpc.manager.Scraper", return_value=FakeScraper(fresh_records)):
                return Manager()

    def test_safety_guard_blocks_large_drop(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            existing = [
                record(f"RX{i:03d}", f"Name{i}", f"Father{i}", "BPharm", i)
                for i in range(1, 101)
            ]
            fresh = [
                record(f"RX{i:03d}", f"Name{i}", f"Father{i}", "BPharm", i)
                for i in range(1, 81)
            ]

            manager = self._make_manager(temp_dir, fresh)
            manager.file_manager.save(existing)

            manager.run_daily_update()

            final_records = manager.file_manager.load()
            self.assertEqual(len(final_records), 100)
            self.assertEqual(final_records[0].registration_number, "RX001")
            self.assertEqual(final_records[-1].registration_number, "RX100")

    def test_update_writes_sorted_deduped_data_and_github_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            existing = [
                record("A1", "Alpha Old", "F1", "BPharm", 2),
                record("B2", "Beta", "F2", "DPharm", 4),
                record("D4", "Delta", "F4", "QP", 8),
            ]
            fresh = [
                record("B2", "Beta", "F2", "DPharm", 5),
                record("A1", "Alpha New", "F1", "BPharm", 3),
                record("C3", "Gamma", "F3", "PharmD", 1),
                record("B2", "Beta", "F2", "DPharm", 4),  # duplicate
            ]

            manager = self._make_manager(temp_dir, fresh)
            manager.file_manager.save(existing)

            with tempfile.NamedTemporaryFile(delete=False) as out_file:
                github_output = out_file.name

            old_env = os.environ.get("GITHUB_OUTPUT")
            try:
                os.environ["GITHUB_OUTPUT"] = github_output
                manager.run_daily_update()
            finally:
                if old_env is None:
                    os.environ.pop("GITHUB_OUTPUT", None)
                else:
                    os.environ["GITHUB_OUTPUT"] = old_env

            saved = json.loads(Path(temp_dir, "rx.json").read_text(encoding="utf-8"))
            self.assertEqual([r["registration_number"] for r in saved], ["C3", "A1", "B2"])
            self.assertEqual(saved[1]["name"], "Alpha New")

            output_lines = Path(github_output).read_text(encoding="utf-8").splitlines()
            output = {}
            for line in output_lines:
                if "=" in line:
                    k, v = line.split("=", 1)
                    output[k] = v

            self.assertEqual(output["total_records"], "3")
            self.assertEqual(output["new_records"], "1")
            self.assertEqual(output["removed_records"], "1")
            self.assertEqual(output["modified_records"], "1")
            self.assertEqual(output["duplicates_removed"], "1")
            self.assertEqual(output["success"], "True")

            self.assertEqual(json.loads(output["new_cat_stats"]), {"PharmD": 1})
            self.assertEqual(json.loads(output["rem_cat_stats"]), {"QP": 1})
            self.assertEqual(json.loads(output["mod_cat_stats"]), {"BPharm": 1})

            os.unlink(github_output)


if __name__ == "__main__":
    unittest.main()
