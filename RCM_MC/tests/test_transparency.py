"""Tests for the Hospital Price Transparency MRF parser."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from rcm_mc.infra.transparency import (
    MRFSummary,
    PayerRateSummary,
    _safe_float,
    format_mrf_summary,
    parse_mrf,
)


def _write_compliant_csv(path: Path, rows=None) -> Path:
    """Write a minimally-compliant CMS v2.0 MRF CSV."""
    rows = rows or [
        {"code": "99213", "description": "Office visit 15m",
         "payer_name": "Medicare",   "plan_name": "Part B", "standard_charge_dollar_amount": "150.00"},
        {"code": "99213", "description": "Office visit 15m",
         "payer_name": "Commercial", "plan_name": "PPO",    "standard_charge_dollar_amount": "225.00"},
        {"code": "99214", "description": "Office visit 25m",
         "payer_name": "Medicare",   "plan_name": "Part B", "standard_charge_dollar_amount": "220.00"},
        {"code": "99214", "description": "Office visit 25m",
         "payer_name": "Commercial", "plan_name": "PPO",    "standard_charge_dollar_amount": "310.00"},
        {"code": "99215", "description": "Office visit 40m",
         "payer_name": "Medicaid",   "plan_name": "",       "standard_charge_dollar_amount": "180.00"},
    ]
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def _write_compliant_json(path: Path) -> Path:
    """Write a minimally-compliant CMS v2.0 MRF JSON."""
    payload = {
        "hospital_name": "Test Hospital",
        "standard_charge_information": [
            {"code": "99213", "description": "Office visit 15m",
             "payer_specific_negotiated_charges": [
                 {"payer_name": "Medicare",   "standard_charge_dollar_amount": 150.00},
                 {"payer_name": "Commercial", "standard_charge_dollar_amount": 225.00},
             ]},
            {"code": "99214", "description": "Office visit 25m",
             "payer_specific_negotiated_charges": [
                 {"payer_name": "Medicare",   "standard_charge_dollar_amount": 220.00},
                 {"payer_name": "Commercial", "standard_charge_dollar_amount": 310.00},
             ]},
        ],
    }
    with open(path, "w") as f:
        json.dump(payload, f)
    return path


# ── Helpers ────────────────────────────────────────────────────────────────

class TestSafeFloat(unittest.TestCase):
    def test_dollar_sign_stripped(self):
        self.assertEqual(_safe_float("$150.00"), 150.00)

    def test_commas_stripped(self):
        self.assertEqual(_safe_float("1,250.00"), 1250.00)

    def test_none_returns_none(self):
        self.assertIsNone(_safe_float(None))

    def test_empty_returns_none(self):
        self.assertIsNone(_safe_float(""))

    def test_na_string_returns_none(self):
        self.assertIsNone(_safe_float("n/a"))

    def test_garbage_returns_none(self):
        self.assertIsNone(_safe_float("—"))


# ── CSV parsing ───────────────────────────────────────────────────────────

class TestParseMRFCompliantCSV(unittest.TestCase):
    def test_identifies_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_compliant_csv(Path(tmp) / "mrf.csv")
            summary = parse_mrf(str(path))
            self.assertEqual(summary.format, "csv")
            self.assertTrue(summary.compliant)

    def test_counts_rows_codes_payers(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_compliant_csv(Path(tmp) / "mrf.csv")
            summary = parse_mrf(str(path))
            self.assertEqual(summary.total_rows, 5)
            self.assertEqual(summary.unique_codes, 3)       # 99213, 99214, 99215
            self.assertEqual(summary.unique_payers, 3)      # Medicare, Medicaid, Commercial

    def test_per_payer_rate_stats(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_compliant_csv(Path(tmp) / "mrf.csv")
            summary = parse_mrf(str(path))
            by_payer = {p.payer: p for p in summary.payer_summaries}
            self.assertIn("Medicare", by_payer)
            self.assertEqual(by_payer["Medicare"].rate_count, 2)
            self.assertEqual(by_payer["Medicare"].min_rate, 150.0)
            self.assertEqual(by_payer["Medicare"].max_rate, 220.0)
            self.assertAlmostEqual(by_payer["Medicare"].mean_rate, 185.0)

    def test_payer_summaries_sorted_by_rate_count(self):
        # Medicare has 2, Commercial has 2, Medicaid has 1
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_compliant_csv(Path(tmp) / "mrf.csv")
            summary = parse_mrf(str(path))
            rate_counts = [p.rate_count for p in summary.payer_summaries]
            self.assertEqual(rate_counts, sorted(rate_counts, reverse=True))


class TestParseMRFNonCompliantCSV(unittest.TestCase):
    def test_missing_required_columns_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mrf.csv"
            # Only has code and charge_amount; missing payer_name and description
            pd.DataFrame([
                {"code": "99213", "charge_amount": 150},
                {"code": "99214", "charge_amount": 220},
            ]).to_csv(path, index=False)
            summary = parse_mrf(str(path))
            self.assertFalse(summary.compliant)
            self.assertIn("payer_name", summary.missing_required)
            self.assertTrue(summary.warnings)

    def test_alias_columns_recognized(self):
        """'payor_name' should resolve to payer_name; 'negotiated_rate' to charge."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mrf.csv"
            pd.DataFrame([
                {"billing_code": "99213", "description": "visit",
                 "payor_name": "Aetna", "negotiated_rate": "$175.00"},
            ]).to_csv(path, index=False)
            summary = parse_mrf(str(path))
            self.assertTrue(summary.compliant)
            self.assertEqual(summary.unique_payers, 1)
            self.assertEqual(summary.payer_summaries[0].payer, "Aetna")


# ── JSON parsing ──────────────────────────────────────────────────────────

class TestParseMRFJSON(unittest.TestCase):
    def test_flattens_negotiated_charges(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_compliant_json(Path(tmp) / "mrf.json")
            summary = parse_mrf(str(path))
            self.assertEqual(summary.format, "json")
            self.assertTrue(summary.compliant)
            self.assertEqual(summary.total_rows, 4)   # 2 codes × 2 payers
            self.assertEqual(summary.unique_codes, 2)
            self.assertEqual(summary.unique_payers, 2)


# ── File type guard rails ─────────────────────────────────────────────────

class TestMRFGuards(unittest.TestCase):
    def test_missing_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            parse_mrf("/nonexistent/mrf.csv")

    def test_bad_extension_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "data.xlsx"
            p.touch()
            with self.assertRaises(ValueError):
                parse_mrf(str(p))

    def test_empty_csv_produces_zero_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "empty.csv"
            # Headers only
            p.write_text("code,description,payer_name,standard_charge_dollar_amount\n")
            summary = parse_mrf(str(p))
            self.assertEqual(summary.total_rows, 0)
            self.assertEqual(summary.unique_payers, 0)


# ── Formatter ──────────────────────────────────────────────────────────────

class TestFormatMRFSummary(unittest.TestCase):
    def test_formatted_text_contains_core_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_compliant_csv(Path(tmp) / "mrf.csv")
            summary = parse_mrf(str(path))
            text = format_mrf_summary(summary)
            self.assertIn("MRF Summary", text)
            self.assertIn("CSV", text)
            self.assertIn("compliant", text.lower())
            self.assertIn("Medicare", text)

    def test_top_n_limits_payer_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = _write_compliant_csv(Path(tmp) / "mrf.csv")
            summary = parse_mrf(str(path))
            text = format_mrf_summary(summary, top_n=1)
            # Only top payer rendered
            self.assertEqual(text.count("Medicare") + text.count("Commercial"), 1)

    def test_non_compliant_warning_rendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mrf.csv"
            pd.DataFrame([{"code": "99213", "charge_amount": 150}]).to_csv(path, index=False)
            summary = parse_mrf(str(path))
            text = format_mrf_summary(summary)
            self.assertIn("Warnings", text)


# ── Lookup CLI integration ────────────────────────────────────────────────

class TestLookupMRFFlag(unittest.TestCase):
    def test_mrf_flag_renders_summary_block(self):
        import io
        import sys

        from rcm_mc.data.lookup import main as lookup_main

        with tempfile.TemporaryDirectory() as tmp:
            path = _write_compliant_csv(Path(tmp) / "mrf.csv")
            buf = io.StringIO()
            saved = sys.stdout
            sys.stdout = buf
            try:
                rc = lookup_main(["--ccn", "360180", "--mrf", str(path)])
            finally:
                sys.stdout = saved
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("MRF Summary", out)

    def test_missing_mrf_prints_error_line(self):
        import io
        import sys

        from rcm_mc.data.lookup import main as lookup_main

        buf = io.StringIO()
        saved = sys.stdout
        sys.stdout = buf
        try:
            rc = lookup_main(["--ccn", "360180", "--mrf", "/nonexistent.csv"])
        finally:
            sys.stdout = saved
        self.assertEqual(rc, 0)
        self.assertIn("MRF summary unavailable", buf.getvalue())
