"""Quota-reporter tests (CODE_REVIEW.md T3 remainder).

Covers the pure helpers, the fail-closed behavior when credentials are
missing, and a smoke run of show_quotas() — no network access anywhere.
"""

import unittest
from unittest.mock import patch

from tgpc import quota


class QuotaHelperTests(unittest.TestCase):
    def test_supabase_ref_parsing(self):
        with patch("tgpc.quota.os.environ", {"SUPABASE_URL": "https://xyz999.supabase.co"}):
            self.assertEqual(quota._get_supabase_project_ref(), "xyz999")
        with patch("tgpc.quota.os.environ", {"SUPABASE_URL": "not-a-url"}):
            self.assertIsNone(quota._get_supabase_project_ref())
        with patch("tgpc.quota.os.environ", {}):
            self.assertIsNone(quota._get_supabase_project_ref())

    def test_pct_handles_none_zero_and_values(self):
        self.assertEqual(quota._pct(None, 10), "N/A")
        self.assertEqual(quota._pct(5, None), "N/A")
        self.assertEqual(quota._pct(5, 0), "-")
        self.assertEqual(quota._pct(5, 10), "50.0%")

    def test_fmt_val_formats(self):
        self.assertEqual(quota._fmt_val(None), "?")
        self.assertEqual(quota._fmt_val(0.5), "0.50")
        self.assertEqual(quota._fmt_val(1234567.0), "1,234,567.0")  # floats keep 1 decimal
        self.assertEqual(quota._fmt_val(1234567), "1,234,567")
        self.assertEqual(quota._fmt_val(42), "42")


class QuotaFailClosedTests(unittest.TestCase):
    def test_check_supabase_requires_credentials(self):
        with patch("tgpc.quota.os.environ", {}):
            result = quota.check_supabase()
        self.assertIn("error", result)

    def test_check_r2_requires_credentials(self):
        with patch("tgpc.quota.os.environ", {}):
            result = quota.check_r2()
        self.assertIn("error", result)

    def test_check_resend_requires_key(self):
        with patch("tgpc.quota.os.environ", {}):
            result = quota.check_resend()
        self.assertIn("error", result)

    def test_check_google_drive_requires_config(self):
        with patch("tgpc.quota.os.environ", {}):
            result = quota.check_google_drive()
        self.assertIn("error", result)

    def test_show_quotas_smoke_runs_without_credentials(self):
        """Every check errors, but the report still renders without raising."""
        with patch("tgpc.quota.os.environ", {}):
            quota.show_quotas()  # must not raise


if __name__ == "__main__":
    unittest.main()
