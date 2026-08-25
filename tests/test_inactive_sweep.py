"""Inactive-sweep helper tests (CODE_REVIEW.md T3 remainder).

Covers the JSONL/checkpoint plumbing and the resume-skip decision path of
cmd_sweep — no scraping, no Supabase. All file paths are redirected to a
temp directory via patch.object on the module constants.
"""

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tgpc import inactive_sweep as sweep


def make_args(**kw):
    defaults = dict(command="sweep", batches=None, limit=None, min_delay=3.0, workers=1)
    defaults.update(kw)
    return argparse.Namespace(**defaults)


class SweepHelperTests(unittest.TestCase):
    def _tmp(self):
        return self.enterContext(tempfile.TemporaryDirectory())

    def test_existing_active_set_parses_good_lines_and_skips_bad(self):
        tmp = self._tmp()
        active = Path(tmp) / "active.jsonl"
        active.write_text(
            json.dumps({"registration_number": "R1"})
            + "\n"
            + "not-json\n"
            + json.dumps({"registration_number": "R2"})
            + "\n",
            encoding="utf-8",
        )
        with patch.object(sweep, "ACTIVE_FILE", active):
            self.assertEqual(sweep._existing_active_set(), {"R1", "R2"})

    def test_load_records_exits_when_input_missing(self):
        with patch.object(sweep, "INACTIVE_FILE", Path(self._tmp()) / "nope.jsonl"):
            with self.assertRaises(SystemExit):
                sweep._load_records()

    def test_checkpoint_roundtrip(self):
        tmp = Path(self._tmp())
        cp = tmp / "cp.json"
        with patch.object(sweep, "CHECKPOINT_FILE", cp):
            self.assertEqual(sweep._load_checkpoint(), {"done_batches": []})
            sweep._save_checkpoint({"done_batches": [0, 2]})
            self.assertEqual(sweep._load_checkpoint(), {"done_batches": [0, 2]})

    def test_write_active_emits_full_record(self):
        class FH:
            def __init__(self):
                self.chunks = []

            def write(self, s):
                self.chunks.append(s)

            def flush(self):
                pass

        fh = FH()
        sweep._write_active(fh, "R9", {"name": "Basic Name", "serial_number": 7}, sweep.__dict__ and _detail())
        record = json.loads("".join(fh.chunks))
        self.assertEqual(record["registration_number"], "R9")
        self.assertEqual(record["status"], "Active")
        self.assertEqual(record["name"], "Basic Name")
        self.assertEqual(record["validity_date"], "31-Dec-2026")


def _detail():
    from tgpc.scraper import PharmacistRecord

    return PharmacistRecord(
        registration_number="IGNORED",
        name="Scraped",
        father_name="F",
        category="BPharm",
        status="Active",
        validity_date="31-Dec-2026",
    )


class SweepResumeTests(unittest.TestCase):
    def _seed(self, tmp: Path, n=4):
        inactive = Path(tmp) / "inactive.jsonl"
        inactive.write_text(
            "".join(json.dumps({"registration_number": f"R{i}", "name": f"N{i}"}) + "\n" for i in range(1, n + 1)),
            encoding="utf-8",
        )
        return inactive

    def test_completed_batches_are_skipped(self):
        tmp = self.enterContext(tempfile.TemporaryDirectory())
        inactive = self._seed(Path(tmp))
        checkpoint = Path(tmp) / "cp.json"
        checkpoint.write_text(json.dumps({"done_batches": [0]}), encoding="utf-8")

        with (
            patch.object(sweep, "INACTIVE_FILE", inactive),
            patch.object(sweep, "CHECKPOINT_FILE", checkpoint),
            patch.object(sweep, "_sweep_regs") as regs_mock,
        ):
            sweep.cmd_sweep(make_args())

        regs_mock.assert_not_called()

    def test_partial_run_processes_only_requested_slice(self):
        tmp = self.enterContext(tempfile.TemporaryDirectory())
        inactive = self._seed(Path(tmp))
        checkpoint = Path(tmp) / "cp.json"

        captured = {}

        def fake_regs(regs, records, offset=0, global_total=None, min_delay=3.0, workers=1):
            captured["regs"] = list(regs)
            return {"active": 0, "inactive": 0, "other": 0, "not_found": 0, "error": 0}, 1.0

        with (
            patch.object(sweep, "INACTIVE_FILE", inactive),
            patch.object(sweep, "CHECKPOINT_FILE", checkpoint),
            patch.object(sweep, "_sweep_regs", side_effect=fake_regs),
        ):
            sweep.cmd_sweep(make_args(limit=2))

        self.assertEqual(captured["regs"], ["R1", "R2"])


if __name__ == "__main__":
    unittest.main()
