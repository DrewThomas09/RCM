"""Tests for hold-period initiative attribution (Brick 57)."""
from __future__ import annotations

import csv
import os
import tempfile
import unittest

from rcm_mc.rcm.initiative_tracking import (
    format_initiative_variance,
    import_initiative_actuals_csv,
    initiative_variance_report,
    record_initiative_actual,
)
from rcm_mc.portfolio.store import PortfolioStore


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


# One canonical initiative ID from the shipped library
_KNOWN_INIT = "prior_auth_improvement"


class TestRecordInitiativeActual(unittest.TestCase):
    def test_records_and_returns_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            aid = record_initiative_actual(
                store, deal_id="ccf", initiative_id=_KNOWN_INIT,
                quarter="2026Q1", ebitda_impact=8000.0,
            )
            self.assertIsInstance(aid, int)
            self.assertGreater(aid, 0)

    def test_unknown_initiative_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            with self.assertRaises(ValueError) as ctx:
                record_initiative_actual(
                    store, deal_id="ccf", initiative_id="not_an_initiative",
                    quarter="2026Q1", ebitda_impact=8000.0,
                )
            self.assertIn("Unknown initiative", str(ctx.exception))

    def test_upsert_overwrites_same_quarter(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            record_initiative_actual(
                store, deal_id="ccf", initiative_id=_KNOWN_INIT,
                quarter="2026Q1", ebitda_impact=8000.0,
            )
            # Restated with a correction
            record_initiative_actual(
                store, deal_id="ccf", initiative_id=_KNOWN_INIT,
                quarter="2026Q1", ebitda_impact=7500.0,
            )
            df = initiative_variance_report(store, "ccf")
            row = df[df["initiative_id"] == _KNOWN_INIT].iloc[0]
            self.assertEqual(row["quarters_active"], 1)
            self.assertAlmostEqual(row["cumulative_actual"], 7500.0)

    def test_invalid_quarter_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            with self.assertRaises(ValueError):
                record_initiative_actual(
                    store, deal_id="ccf", initiative_id=_KNOWN_INIT,
                    quarter="not-a-quarter", ebitda_impact=8000.0,
                )


class TestInitiativeVarianceReport(unittest.TestCase):
    def test_empty_returns_empty_df(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            self.assertTrue(initiative_variance_report(store, "nope").empty)

    def test_cumulative_actual_sums_across_quarters(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            for qtr, impact in [("2026Q1", 8000), ("2026Q2", 10000), ("2026Q3", 9000)]:
                record_initiative_actual(
                    store, deal_id="ccf", initiative_id=_KNOWN_INIT,
                    quarter=qtr, ebitda_impact=impact,
                )
            df = initiative_variance_report(store, "ccf")
            row = df.iloc[0]
            self.assertEqual(row["quarters_active"], 3)
            self.assertAlmostEqual(row["cumulative_actual"], 27000.0)

    def test_plan_prorated_from_annual_run_rate(self):
        """Plan = annual_run_rate × (quarters_active / 4).

        prior_auth_improvement has annual_run_rate = 25000 in the library,
        so after 2 quarters, plan = 25000 × 0.5 = 12500.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            for qtr, impact in [("2026Q1", 5000), ("2026Q2", 5000)]:
                record_initiative_actual(
                    store, deal_id="ccf", initiative_id=_KNOWN_INIT,
                    quarter=qtr, ebitda_impact=impact,
                )
            df = initiative_variance_report(store, "ccf")
            row = df.iloc[0]
            self.assertAlmostEqual(row["cumulative_plan"], 12500.0, places=2)
            # Actual 10000 vs plan 12500 = -20% → off_track
            self.assertAlmostEqual(row["variance_pct"], -0.20, places=4)
            self.assertEqual(row["severity"], "off_track")

    def test_sorted_by_variance_worst_first(self):
        """Partner wants to see the worst-off initiatives at the top."""
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            # prior_auth has run_rate 25000 — under-deliver
            record_initiative_actual(store, deal_id="ccf",
                initiative_id="prior_auth_improvement",
                quarter="2026Q1", ebitda_impact=1000)
            # coding_cdi has run_rate 50000 — exceed plan
            record_initiative_actual(store, deal_id="ccf",
                initiative_id="coding_cdi_improvement",
                quarter="2026Q1", ebitda_impact=20000)
            df = initiative_variance_report(store, "ccf")
            # First row should be the worst variance (most negative)
            self.assertEqual(df.iloc[0]["initiative_id"], "prior_auth_improvement")


class TestImportCSV(unittest.TestCase):
    def _write(self, path: str, rows: list) -> None:
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["deal_id", "initiative_id", "quarter", "ebitda_impact"])
            for r in rows:
                w.writerow(r)

    def test_bulk_ingest(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            csv_path = os.path.join(tmp, "init.csv")
            self._write(csv_path, [
                ["ccf", _KNOWN_INIT, "2026Q1", 8000],
                ["ccf", _KNOWN_INIT, "2026Q2", 10000],
                ["rural", "coding_cdi_improvement", "2026Q1", 15000],
            ])
            summary = import_initiative_actuals_csv(store, csv_path)
            self.assertEqual(summary["rows_ingested"], 3)

    def test_missing_required_columns_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            csv_path = os.path.join(tmp, "bad.csv")
            with open(csv_path, "w") as f:
                f.write("deal_id,initiative_id\nccf,prior_auth_improvement\n")
            with self.assertRaises(ValueError):
                import_initiative_actuals_csv(store, csv_path)

    def test_bad_row_reported_but_doesnt_halt_ingest(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            csv_path = os.path.join(tmp, "mixed.csv")
            self._write(csv_path, [
                ["ccf", _KNOWN_INIT, "2026Q1", 8000],        # good
                ["ccf", "bogus_initiative", "2026Q1", 1000], # bad
                ["ccf", _KNOWN_INIT, "2026Q2", 10000],       # good
            ])
            summary = import_initiative_actuals_csv(store, csv_path)
            self.assertEqual(summary["rows_ingested"], 2)
            self.assertEqual(len(summary["errors"]), 1)


class TestFormatInitiativeVariance(unittest.TestCase):
    def test_empty_placeholder(self):
        import pandas as pd
        self.assertIn("no initiative actuals",
                      format_initiative_variance(pd.DataFrame()))

    def test_renders_severity_glyph(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            record_initiative_actual(store, deal_id="ccf",
                initiative_id=_KNOWN_INIT, quarter="2026Q1",
                ebitda_impact=1000)  # way under plan
            df = initiative_variance_report(store, "ccf")
            text = format_initiative_variance(df)
            self.assertIn("✗", text)  # off_track glyph
            self.assertIn(_KNOWN_INIT, text)


class TestInitiativeCLI(unittest.TestCase):
    def _capture(self, argv):
        import io
        import sys
        from rcm_mc.portfolio_cmd import main as pm
        out, err = io.StringIO(), io.StringIO()
        so, se = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = out, err
        try:
            rc = pm(argv)
        finally:
            sys.stdout, sys.stderr = so, se
        return rc, out.getvalue(), err.getvalue()

    def test_record_and_report_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            rc, _, _ = self._capture([
                "--db", db, "initiative-actual",
                "--deal-id", "ccf",
                "--initiative-id", _KNOWN_INIT,
                "--quarter", "2026Q1", "--impact", "8000",
            ])
            self.assertEqual(rc, 0)
            rc2, out, _ = self._capture([
                "--db", db, "initiative-variance", "--deal-id", "ccf",
            ])
            self.assertEqual(rc2, 0)
            self.assertIn(_KNOWN_INIT, out)

    def test_record_unknown_initiative_returns_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            rc, _, err = self._capture([
                "--db", db, "initiative-actual",
                "--deal-id", "ccf",
                "--initiative-id", "bogus_id",
                "--quarter", "2026Q1", "--impact", "1000",
            ])
            self.assertEqual(rc, 2)
            self.assertIn("Unknown initiative", err)
