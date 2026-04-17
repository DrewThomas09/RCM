"""Tests for IRS 990 fetch + cross-check (non-profit hospital cross-reference).

The fetch side uses a real HTTP call to ProPublica in production, but tests
monkey-patch the urlopen call to avoid network dependencies. Cross-check math
is pure-function testable.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from io import BytesIO
from unittest.mock import patch

from rcm_mc.data.irs990 import (
    CrossCheckReport,
    IRS990FetchError,
    _normalize_ein,
    _pct_variance,
    cross_check,
    cross_check_ccn,
    fetch_990,
    filings_by_tax_year,
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _sample_990_payload(ein: str = "340714585", years: dict = None) -> dict:
    """Fake ProPublica payload. ``years`` maps tax_year → {field: value}."""
    filings = []
    years = years or {
        2022: {"totrevenue": 7_000_000_000, "totfuncexpns": 7_500_000_000, "totrevlss": -500_000_000},
        2021: {"totrevenue": 6_200_000_000, "totfuncexpns": 6_900_000_000, "totrevlss": -700_000_000},
    }
    for yr, fields in years.items():
        filings.append({"tax_prd_yr": yr, **fields})
    return {
        "organization": {"ein": ein, "name": "TEST HOSPITAL"},
        "filings_with_data": filings,
    }


def _mock_urlopen_success(payload: dict):
    """Returns a patcher that makes urlopen yield the given JSON payload."""
    body = json.dumps(payload).encode("utf-8")

    class _FakeResp:
        def __init__(self):
            self.buf = BytesIO(body)
        def read(self):
            return self.buf.read()
        def __enter__(self): return self
        def __exit__(self, *a): self.buf.close()

    return patch("urllib.request.urlopen", return_value=_FakeResp())


# ── Pure-function tests ───────────────────────────────────────────────────

class TestNormalizeEin(unittest.TestCase):
    def test_strips_dashes(self):
        self.assertEqual(_normalize_ein("34-0714585"), "340714585")

    def test_strips_whitespace(self):
        self.assertEqual(_normalize_ein(" 34-0714585 "), "340714585")

    def test_none_returns_empty(self):
        self.assertEqual(_normalize_ein(None), "")  # type: ignore[arg-type]


class TestPctVariance(unittest.TestCase):
    def test_basic(self):
        self.assertAlmostEqual(_pct_variance(110, 100), 0.10)

    def test_negative(self):
        self.assertAlmostEqual(_pct_variance(80, 100), -0.20)

    def test_none_input_returns_none(self):
        self.assertIsNone(_pct_variance(None, 100))
        self.assertIsNone(_pct_variance(100, None))

    def test_zero_denominator_returns_none(self):
        self.assertIsNone(_pct_variance(100, 0))


class TestFilingsByTaxYear(unittest.TestCase):
    def test_extracts_years(self):
        data = _sample_990_payload()
        out = filings_by_tax_year(data)
        self.assertEqual(set(out.keys()), {2021, 2022})

    def test_empty_payload(self):
        self.assertEqual(filings_by_tax_year({}), {})

    def test_missing_year_skipped(self):
        data = {"filings_with_data": [{"totrevenue": 1e9}, {"tax_prd_yr": 2022}]}
        self.assertEqual(set(filings_by_tax_year(data).keys()), {2022})


# ── Cross-check math ──────────────────────────────────────────────────────

class TestCrossCheck(unittest.TestCase):
    def test_exact_year_match(self):
        hcris_row = {
            "fiscal_year": 2022,
            "net_patient_revenue": 7_100_000_000,
            "operating_expenses": 7_600_000_000,
            "net_income": -500_000_000,
        }
        report = cross_check(hcris_row, _sample_990_payload())
        self.assertTrue(report.matched)
        self.assertEqual(report.irs_tax_year, 2022)
        # NPSR variance: (7.0B - 7.1B) / 7.1B ≈ -1.4% → no flag
        self.assertLess(abs(report.variance_pct["total_revenue"]), 0.05)

    def test_large_variance_raises_flag(self):
        # 990 says $3B, HCRIS says $7B → 57% variance
        payload = _sample_990_payload(years={2022: {"totrevenue": 3_000_000_000, "totfuncexpns": 0, "totrevlss": 0}})
        hcris_row = {
            "fiscal_year": 2022,
            "net_patient_revenue": 7_000_000_000,
            "operating_expenses": 0,
            "net_income": 0,
        }
        report = cross_check(hcris_row, payload)
        # Flag should mention total_revenue
        self.assertTrue(any("total_revenue" in f for f in report.flags),
                        msg=f"expected total_revenue flag; got {report.flags}")

    def test_year_gap_fallback_raises_flag(self):
        payload = _sample_990_payload(years={2020: {"totrevenue": 5e9, "totfuncexpns": 5.5e9, "totrevlss": -0.5e9}})
        hcris_row = {
            "fiscal_year": 2022,
            "net_patient_revenue": 6e9,
            "operating_expenses": 6.5e9,
            "net_income": -0.5e9,
        }
        report = cross_check(hcris_row, payload)
        # Fallback to 2020; a "gap" flag should fire
        self.assertEqual(report.irs_tax_year, 2020)
        self.assertTrue(any("gap" in f.lower() or "fallback" in f.lower() for f in report.flags))

    def test_no_filings_returns_unmatched(self):
        hcris_row = {"fiscal_year": 2022, "net_patient_revenue": 1e9,
                     "operating_expenses": 0, "net_income": 0}
        report = cross_check(hcris_row, {"organization": {"ein": "123"}, "filings_with_data": []})
        self.assertFalse(report.matched)

    def test_missing_metrics_produces_none_variance(self):
        payload = _sample_990_payload(years={2022: {"totrevenue": 1e9}})  # no expenses, no net income
        hcris_row = {"fiscal_year": 2022, "net_patient_revenue": 1e9,
                     "operating_expenses": 1e9, "net_income": 0}
        report = cross_check(hcris_row, payload)
        # total_revenue variance ≈ 0, but expenses and net income unmatched → None
        self.assertEqual(report.variance_pct["total_expenses"], None)
        self.assertEqual(report.variance_pct["net_income"], None)


# ── Fetch (mocked) ────────────────────────────────────────────────────────

class TestFetch990(unittest.TestCase):
    def setUp(self):
        # Redirect cache to a temp dir so tests don't pollute ~/.cache
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["RCM_MC_IRS990_CACHE"] = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()
        os.environ.pop("RCM_MC_IRS990_CACHE", None)

    def test_fetches_and_parses(self):
        with _mock_urlopen_success(_sample_990_payload()):
            data = fetch_990("340714585", use_cache=False)
        self.assertEqual(data["organization"]["ein"], "340714585")
        self.assertEqual(len(data["filings_with_data"]), 2)

    def test_dashes_in_ein_accepted(self):
        with _mock_urlopen_success(_sample_990_payload()):
            data = fetch_990("34-0714585", use_cache=False)
        self.assertIsNotNone(data)

    def test_wrong_length_ein_raises(self):
        with self.assertRaises(IRS990FetchError):
            fetch_990("12345")  # 5 digits — not 9

    def test_cache_hit_avoids_network(self):
        # First call writes cache
        with _mock_urlopen_success(_sample_990_payload()):
            fetch_990("340714585", use_cache=False)
        # Second call with use_cache=True should NOT hit urlopen
        with patch("urllib.request.urlopen", side_effect=AssertionError("should not be called")):
            data = fetch_990("340714585", use_cache=True)
        self.assertEqual(data["organization"]["ein"], "340714585")

    def test_http_error_raises(self):
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
            "u", 404, "Not Found", {}, None)):  # type: ignore[arg-type]
            with self.assertRaises(IRS990FetchError) as ctx:
                fetch_990("999999999", use_cache=False)
            self.assertIn("404", str(ctx.exception))


# ── End-to-end via cross_check_ccn (injected fetch) ───────────────────────

class TestCrossCheckCCN(unittest.TestCase):
    def test_happy_path_with_injected_fetch(self):
        # Use a real HCRIS CCN so lookup_by_ccn returns data
        def fake_fetch(ein, **kwargs):
            return _sample_990_payload(ein=ein)

        report = cross_check_ccn("360180", "340714585", fetch_fn=fake_fetch)
        self.assertIsInstance(report, CrossCheckReport)
        # Real Cleveland Clinic 990-vs-HCRIS variance should land in the report
        self.assertIn("total_revenue", report.variance_pct)

    def test_unknown_ccn_raises(self):
        def fake_fetch(ein, **kwargs):
            return _sample_990_payload()

        with self.assertRaises(ValueError):
            cross_check_ccn("999999", "340714585", fetch_fn=fake_fetch)


# ── Lookup CLI integration ────────────────────────────────────────────────

class TestLookupEinFlag(unittest.TestCase):
    """rcm-mc lookup --ccn X --ein Y prints a 990 cross-check block."""

    def test_lookup_with_ein_prints_cross_check_block(self):
        import io
        import sys

        # Monkey-patch fetch_990 to return a sample payload
        from rcm_mc.data import irs990

        def fake_fetch(ein, **kwargs):
            return _sample_990_payload(ein=ein)

        with patch.object(irs990, "fetch_990", fake_fetch):
            from rcm_mc.data.lookup import main as lookup_main

            buf = io.StringIO()
            saved = sys.stdout
            sys.stdout = buf
            try:
                rc = lookup_main(["--ccn", "360180", "--ein", "340714585"])
            finally:
                sys.stdout = saved
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("IRS 990 Cross-Check", out)
        self.assertIn("340714585", out)

    def test_lookup_with_unresolvable_ein_prints_error_line(self):
        import io
        import sys

        from rcm_mc.data import irs990

        def bad_fetch(ein, **kwargs):
            raise irs990.IRS990FetchError("mock network failure")

        with patch.object(irs990, "fetch_990", bad_fetch):
            from rcm_mc.data.lookup import main as lookup_main

            buf = io.StringIO()
            saved = sys.stdout
            sys.stdout = buf
            try:
                rc = lookup_main(["--ccn", "360180", "--ein", "123456789"])
            finally:
                sys.stdout = saved
        # Even with a fetch failure, the hospital record still prints, rc=0
        self.assertEqual(rc, 0)
        self.assertIn("990 cross-check unavailable", buf.getvalue())
