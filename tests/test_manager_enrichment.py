import os
import sys
import tempfile
import unittest
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
        self.enterContext(
            patch(
                "tgpc.manager.Config.load", return_value=Config(data_directory=temp_dir, enrichment_directory=temp_dir)
            )
        )
        self.enterContext(patch("tgpc.manager.Scraper", return_value=DetailScraper(details_by_id)))
        return Manager()

    @patch("tgpc.manager.create_client")
    def test_run_enrichment_upserts_first_pending_record_in_sorted_order(self, mock_create_client):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["SUPABASE_URL"] = "https://test.supabase.co"
            os.environ["SUPABASE_SECRET_KEY"] = "test-key"
            fake_client = MagicMock()
            fake_client.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
                data=[]
            )
            mock_create_client.return_value = fake_client

            manager = self._make_manager(
                temp_dir,
                {
                    "RPH001": PharmacistRecord(
                        registration_number="RPH001",
                        name="Alpha",
                        father_name="Parent",
                        category="BPharm",
                        validity_date="2026-12-31",
                        education=[
                            {
                                "qualification": "BPharm",
                                "university": "OU",
                                "year": "2018",
                            }
                        ],
                        work_experience={"address": "Clinic Street"},
                    ),
                    "RPH002": PharmacistRecord(
                        registration_number="RPH002",
                        name="Name",
                        father_name="Father",
                        category="BPharm",
                    ),
                },
            )
            manager.file_manager.save(
                [
                    record("RPH002", serial=2),
                    record("RPH001", name="Alpha", father="Parent", serial=1),
                ]
            )

            manager.run_enrichment()

            upsert_calls = fake_client.table.return_value.upsert.call_args_list
            self.assertEqual(len(upsert_calls), 2)
            data_rph001 = upsert_calls[0][0][0]
            self.assertEqual(data_rph001["validity_date"], "2026-12-31")
            self.assertEqual(data_rph001["education"][0]["qualification"], "BPharm")
            self.assertEqual(data_rph001["work_experience"]["address"], "Clinic Street")
            data_rph002 = upsert_calls[1][0][0]
            self.assertEqual(data_rph002["registration_number"], "RPH002")
            self.assertEqual(data_rph002["validity_date"], "")

            del os.environ["SUPABASE_URL"]
            del os.environ["SUPABASE_SECRET_KEY"]

    @patch("tgpc.manager.create_client")
    def test_run_enrichment_raises_on_registration_mismatch(self, mock_create_client):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["SUPABASE_URL"] = "https://test.supabase.co"
            os.environ["SUPABASE_SECRET_KEY"] = "test-key"
            fake_client = MagicMock()
            fake_client.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
                data=[]
            )
            mock_create_client.return_value = fake_client

            manager = self._make_manager(
                temp_dir,
                {
                    "RPH001": PharmacistRecord(
                        registration_number="WRONG001",
                        name="Wrong Record",
                        father_name="Parent",
                        category="BPharm",
                    )
                },
            )
            manager.file_manager.save([record("RPH001", serial=1)])

            with self.assertRaises(DataIntegrityError):
                manager.run_enrichment()

            upsert_calls = fake_client.table.return_value.upsert.call_args_list
            self.assertEqual(len(upsert_calls), 0)

            del os.environ["SUPABASE_URL"]
            del os.environ["SUPABASE_SECRET_KEY"]


if __name__ == "__main__":
    unittest.main()
