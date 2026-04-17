"""Tests for hold-period variance tracking (Brick 52)."""
from __future__ import annotations

import os
import tempfile
import unittest

import pandas as pd

from rcm_mc.pe.hold_tracking import (
    TRACKED_KPIS,
    _classify_severity,
    cumulative_drift,
    format_variance_report,
    import_actuals_csv,
    record_quarterly_actuals,
    variance_report,
)
from rcm_mc.portfolio.store import PortfolioStore


def _store(tmp: str) -> PortfolioStore:
    return PortfolioStore(os.path.join(tmp, "p.db"))


class TestClassifySeverity(unittest.TestCase):
    def test_within_5pct_on_track(self):
        self.assertEqual(_classify_severity(0.03), "on_track")
        self.assertEqual(_classify_severity(-0.04), "on_track")

    def test_5_to_15_lagging(self):
        self.assertEqual(_classify_severity(0.08), "lagging")
        self.assertEqual(_classify_severity(-0.12), "lagging")

    def test_15_plus_off_track(self):
        self.assertEqual(_classify_severity(0.20), "off_track")
        self.assertEqual(_classify_severity(-0.30), "off_track")


class TestRecordQuarterlyActuals(unittest.TestCase):
    def test_records_kpis_with_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            aid = record_quarterly_actuals(
                store, deal_id="ccf", quarter="2026Q1",
                actuals={"ebitda": 48e6, "idr_blended": 0.13},
                plan={"ebitda": 50e6, "idr_blended": 0.12},
            )
            self.assertIsInstance(aid, int)
            df = variance_report(store, "ccf")
            self.assertEqual(len(df), 2)  # one row per KPI

    def test_unknown_kpi_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            # 'ebidta' typo — common mistake; must be caught
            with self.assertRaises(ValueError):
                record_quarterly_actuals(
                    store, deal_id="ccf", quarter="2026Q1",
                    actuals={"ebidta": 48e6},
                )

    def test_invalid_quarter_format_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            with self.assertRaises(ValueError):
                record_quarterly_actuals(
                    store, deal_id="ccf", quarter="2026-04-15",
                    actuals={"ebitda": 50e6},
                )

    def test_upsert_overwrites_same_quarter(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            record_quarterly_actuals(
                store, deal_id="ccf", quarter="2026Q1",
                actuals={"ebitda": 48e6}, plan={"ebitda": 50e6},
            )
            # Correction: restate Q1 number
            record_quarterly_actuals(
                store, deal_id="ccf", quarter="2026Q1",
                actuals={"ebitda": 47e6}, plan={"ebitda": 50e6},
            )
            df = variance_report(store, "ccf")
            self.assertEqual(len(df), 1)  # still one row
            self.assertAlmostEqual(df.iloc[0]["actual"], 47e6)


class TestVarianceReport(unittest.TestCase):
    def test_computes_variance_pct_and_severity(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            record_quarterly_actuals(
                store, "ccf", "2026Q1",
                actuals={"ebitda": 48e6}, plan={"ebitda": 50e6},
            )
            df = variance_report(store, "ccf")
            row = df[df["kpi"] == "ebitda"].iloc[0]
            self.assertAlmostEqual(row["variance_pct"], -0.04, places=4)
            self.assertEqual(row["severity"], "on_track")

    def test_off_track_when_variance_above_15pct(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            record_quarterly_actuals(
                store, "ccf", "2026Q1",
                actuals={"ebitda": 40e6}, plan={"ebitda": 50e6},
            )
            df = variance_report(store, "ccf")
            self.assertEqual(df.iloc[0]["severity"], "off_track")

    def test_no_plan_marker_when_plan_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            record_quarterly_actuals(
                store, "ccf", "2026Q1",
                actuals={"ebitda": 50e6}, plan=None,
            )
            df = variance_report(store, "ccf")
            self.assertEqual(df.iloc[0]["severity"], "no_plan")

    def test_fallback_plan_from_snapshot_entry_ebitda(self):
        """When actuals omit plan, variance_report pulls entry_ebitda from the snapshot."""
        from rcm_mc.portfolio.portfolio_snapshots import register_snapshot
        import json
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            run = os.path.join(tmp, "run")
            os.makedirs(run)
            with open(os.path.join(run, "pe_bridge.json"), "w") as f:
                json.dump({"entry_ebitda": 50e6}, f)
            register_snapshot(store, "ccf", "hold", run_dir=run)
            record_quarterly_actuals(
                store, "ccf", "2026Q1", actuals={"ebitda": 48e6},
            )
            df = variance_report(store, "ccf")
            row = df.iloc[0]
            self.assertAlmostEqual(row["plan"], 50e6)
            self.assertAlmostEqual(row["variance_pct"], -0.04, places=4)

    def test_empty_deal_returns_empty_frame(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            df = variance_report(store, "nonexistent")
            self.assertTrue(df.empty)


class TestCumulativeDrift(unittest.TestCase):
    def test_drift_sums_across_quarters(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            for qtr, actual in [("2026Q1", 48e6), ("2026Q2", 46e6), ("2026Q3", 44e6)]:
                record_quarterly_actuals(
                    store, "ccf", qtr,
                    actuals={"ebitda": actual}, plan={"ebitda": 50e6},
                )
            drift = cumulative_drift(store, "ccf", kpi="ebitda")
            self.assertEqual(len(drift), 3)
            # Q1: -4%, Q2: -8%, Q3: -12% → cumulative: -4, -12, -24
            self.assertAlmostEqual(drift.iloc[-1]["cumulative_drift"], -0.24, places=4)

    def test_empty_deal_returns_empty_frame(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            self.assertTrue(cumulative_drift(store, "nope").empty)


class TestFormatVarianceReport(unittest.TestCase):
    def test_empty_renders_placeholder(self):
        self.assertIn("no quarterly actuals",
                      format_variance_report(pd.DataFrame()))

    def test_text_includes_severity_glyph(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            record_quarterly_actuals(
                store, "ccf", "2026Q1",
                actuals={"ebitda": 40e6}, plan={"ebitda": 50e6},
            )
            df = variance_report(store, "ccf")
            text = format_variance_report(df)
            self.assertIn("2026Q1", text)
            # Off-track glyph ✗ appears for -20% variance
            self.assertIn("✗", text)

    def test_tracked_kpis_is_frozen_tuple(self):
        self.assertIsInstance(TRACKED_KPIS, tuple)
        self.assertIn("ebitda", TRACKED_KPIS)


class TestImportActualsCSV(unittest.TestCase):
    """Brick 56: bulk-ingest actuals from a management-reporting CSV."""

    def _write_csv(self, path: str, rows: list, headers: list) -> None:
        import csv
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(headers)
            for r in rows:
                w.writerow(r)

    def test_imports_multiple_deals_and_quarters(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            csv_path = os.path.join(tmp, "q2.csv")
            self._write_csv(csv_path, [
                ["ccf", "2026Q1", 48e6, 0.13, 50e6, 0.12],
                ["ccf", "2026Q2", 46e6, 0.14, 52e6, 0.115],
                ["rural", "2026Q1", 14.5e6, 0.15, 15e6, 0.14],
            ], headers=["deal_id", "quarter", "ebitda", "idr_blended",
                        "plan_ebitda", "plan_idr_blended"])
            summary = import_actuals_csv(store, csv_path)
            self.assertEqual(summary["rows_ingested"], 3)
            self.assertEqual(set(summary["deals"]), {"ccf", "rural"})
            self.assertEqual(set(summary["quarters"]), {"2026Q1", "2026Q2"})

    def test_upsert_semantics_when_reimporting(self):
        """Re-ingesting corrected numbers overwrites, doesn't duplicate."""
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            csv1 = os.path.join(tmp, "v1.csv")
            csv2 = os.path.join(tmp, "v2.csv")
            self._write_csv(csv1, [["ccf", "2026Q1", 48e6]],
                            headers=["deal_id", "quarter", "ebitda"])
            self._write_csv(csv2, [["ccf", "2026Q1", 47e6]],  # restated
                            headers=["deal_id", "quarter", "ebitda"])
            import_actuals_csv(store, csv1)
            import_actuals_csv(store, csv2)
            df = variance_report(store, "ccf")
            self.assertEqual(len(df), 1)
            self.assertAlmostEqual(df.iloc[0]["actual"], 47e6)

    def test_missing_required_columns_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            csv_path = os.path.join(tmp, "bad.csv")
            self._write_csv(csv_path, [[48e6]], headers=["ebitda"])  # no deal_id / quarter
            with self.assertRaises(ValueError) as ctx:
                import_actuals_csv(store, csv_path)
            self.assertIn("missing required column", str(ctx.exception))

    def test_unknown_columns_raise_in_strict(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            csv_path = os.path.join(tmp, "x.csv")
            self._write_csv(csv_path, [["ccf", "2026Q1", 48e6, 100]],
                            headers=["deal_id", "quarter", "ebitda", "random_extra"])
            with self.assertRaises(ValueError):
                import_actuals_csv(store, csv_path, strict=True)

    def test_lenient_mode_warns_but_ingests(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            csv_path = os.path.join(tmp, "x.csv")
            self._write_csv(csv_path, [["ccf", "2026Q1", 48e6, 100]],
                            headers=["deal_id", "quarter", "ebitda", "random_extra"])
            summary = import_actuals_csv(store, csv_path, strict=False)
            self.assertEqual(summary["rows_ingested"], 1)
            self.assertTrue(summary["warnings"])

    def test_missing_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            with self.assertRaises(FileNotFoundError):
                import_actuals_csv(store, os.path.join(tmp, "nope.csv"))

    def test_blank_cells_skipped(self):
        """Empty KPI cells shouldn't raise; they just don't contribute a value."""
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            csv_path = os.path.join(tmp, "sparse.csv")
            self._write_csv(csv_path, [
                ["ccf", "2026Q1", 48e6, "", 50e6, ""],  # idr blank, plan_idr blank
            ], headers=["deal_id", "quarter", "ebitda", "idr_blended",
                        "plan_ebitda", "plan_idr_blended"])
            summary = import_actuals_csv(store, csv_path)
            self.assertEqual(summary["rows_ingested"], 1)
            df = variance_report(store, "ccf")
            kpis_with_data = set(df["kpi"])
            self.assertIn("ebitda", kpis_with_data)
            self.assertNotIn("idr_blended", kpis_with_data)


class TestVarianceDisplayNaNHandling(unittest.TestCase):
    """Regression: plan=None in pandas surfaces as NaN; format must show '—'."""

    def test_no_plan_kpi_renders_dash_not_nan(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _store(tmp)
            # EBITDA with plan, NPSR without plan
            record_quarterly_actuals(
                store, "ccf", "2026Q1",
                actuals={"ebitda": 48e6, "net_patient_revenue": 500e6},
                plan={"ebitda": 50e6},
            )
            df = variance_report(store, "ccf")
            text = format_variance_report(df)
            self.assertNotIn("nan", text.lower())
            # Dash appears where plan is missing
            self.assertIn("—", text)


class TestVarianceCLI(unittest.TestCase):
    """Brick 52: `rcm-mc portfolio actuals` and `variance` subcommands."""

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

    def test_actuals_and_variance_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            rc, _, _ = self._capture([
                "--db", db, "actuals",
                "--deal-id", "ccf", "--quarter", "2026Q1",
                "--ebitda", "48e6", "--plan-ebitda", "50e6",
            ])
            self.assertEqual(rc, 0)
            rc2, out, _ = self._capture([
                "--db", db, "variance", "--deal-id", "ccf",
            ])
            self.assertEqual(rc2, 0)
            self.assertIn("2026Q1", out)
            self.assertIn("ebitda", out)

    def test_actuals_requires_at_least_one_kpi(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            rc, _, err = self._capture([
                "--db", db, "actuals",
                "--deal-id", "ccf", "--quarter", "2026Q1",
            ])
            self.assertEqual(rc, 2)
            self.assertIn("at least one KPI flag", err)

    def test_variance_unknown_deal_returns_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            rc, _, err = self._capture([
                "--db", db, "variance", "--deal-id", "ghost",
            ])
            self.assertEqual(rc, 1)
            self.assertIn("No quarterly actuals", err)
