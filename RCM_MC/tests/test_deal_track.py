"""Tests for the post-close tracker: baseline capture + ``rcm-mc deal track``."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd
import yaml

from rcm_mc.deals.deal import (
    _capture_baseline,
    _load_actuals,
    _parse_pct_or_decimal,
    _pct_to_benchmark,
    _track_one_month,
    create_deal,
    track_deal,
)


BASE_DIR = Path(__file__).resolve().parents[1]
ACTUAL_PATH = str(BASE_DIR / "configs" / "actual.yaml")
BENCH_PATH = str(BASE_DIR / "configs" / "benchmark.yaml")


# ── Unit tests for helpers ────────────────────────────────────────────────

class TestParsePct(unittest.TestCase):
    def test_decimal_passes_through(self):
        self.assertAlmostEqual(_parse_pct_or_decimal(0.135), 0.135)

    def test_percent_form_auto_divided(self):
        self.assertAlmostEqual(_parse_pct_or_decimal(13.5), 0.135)

    def test_percent_suffix_stripped(self):
        self.assertAlmostEqual(_parse_pct_or_decimal("13.5%"), 0.135)

    def test_none_returns_none(self):
        self.assertIsNone(_parse_pct_or_decimal(None))

    def test_empty_string_returns_none(self):
        self.assertIsNone(_parse_pct_or_decimal(""))

    def test_garbage_returns_none(self):
        self.assertIsNone(_parse_pct_or_decimal("n/a"))


class TestPctToBenchmark(unittest.TestCase):
    def test_at_baseline_returns_zero(self):
        self.assertEqual(_pct_to_benchmark(0.135, 0.135, 0.113), 0.0)

    def test_at_benchmark_returns_one(self):
        self.assertEqual(_pct_to_benchmark(0.113, 0.135, 0.113), 1.0)

    def test_halfway_returns_half(self):
        self.assertAlmostEqual(_pct_to_benchmark(0.124, 0.135, 0.113), 0.5, delta=0.01)

    def test_past_benchmark_returns_greater_than_one(self):
        self.assertGreater(_pct_to_benchmark(0.10, 0.135, 0.113), 1.0)

    def test_worse_than_baseline_returns_negative(self):
        self.assertLess(_pct_to_benchmark(0.15, 0.135, 0.113), 0.0)

    def test_zero_gap_returns_none(self):
        self.assertIsNone(_pct_to_benchmark(0.1, 0.1, 0.1))


class TestTrackOneMonth(unittest.TestCase):
    BASELINE = {
        "blended": {"idr": 0.135, "fwr": 0.30, "dar_clean_days": 52.0},
        "benchmark_targets": {"idr": 0.113, "fwr": 0.10, "dar_clean_days": 29.0},
    }

    def test_variance_sign_is_actual_minus_baseline(self):
        entry = _track_one_month("2026-04", {"idr": 0.125}, self.BASELINE)
        self.assertAlmostEqual(entry["variance_vs_baseline"]["idr"], -0.010, delta=1e-5)

    def test_pct_to_benchmark_scales_with_improvement(self):
        # idr improved from 0.135 → 0.124 (halfway to 0.113 benchmark)
        entry = _track_one_month("2026-04", {"idr": 0.124}, self.BASELINE)
        self.assertAlmostEqual(entry["pct_to_benchmark"]["idr"], 0.5, delta=0.02)

    def test_worsening_metric_raises_alert(self):
        entry = _track_one_month("2026-04", {"idr": 0.150}, self.BASELINE)
        self.assertTrue(entry["alerts"])
        self.assertIn("idr", entry["alerts"][0])

    def test_improving_metric_no_alert(self):
        entry = _track_one_month("2026-04", {"idr": 0.120}, self.BASELINE)
        self.assertEqual(entry["alerts"], [])

    def test_missing_baseline_skips_metric(self):
        entry = _track_one_month(
            "2026-04",
            {"idr": 0.12, "net_patient_revenue": 5e8},
            self.BASELINE,  # no annual_revenue key
        )
        self.assertIn("idr", entry["variance_vs_baseline"])
        self.assertNotIn("net_patient_revenue", entry["variance_vs_baseline"])


# ── Actuals loader ────────────────────────────────────────────────────────

class TestLoadActuals(unittest.TestCase):
    def test_reads_canonical_column_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "act.csv"
            pd.DataFrame({
                "month": ["2026-04"],
                "idr": [0.125],
                "fwr": [0.29],
                "dar_clean_days": [51.0],
            }).to_csv(path, index=False)
            df = _load_actuals(str(path))
            self.assertEqual(df.iloc[0]["idr"], 0.125)
            self.assertEqual(df.iloc[0]["month"], "2026-04")

    def test_reads_alias_column_names(self):
        """Operator-friendly variants: 'Initial Denial Rate', 'AR Days', etc."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "act.csv"
            pd.DataFrame({
                "period": ["2026-04"],
                "initial_denial_rate": [12.5],  # percent-form
                "writeoff_rate": [29.0],
                "days_in_ar": [51.0],
                "npsr": [4.8e7],
            }).to_csv(path, index=False)
            df = _load_actuals(str(path))
            self.assertAlmostEqual(df.iloc[0]["idr"], 0.125, delta=1e-5)
            self.assertAlmostEqual(df.iloc[0]["fwr"], 0.29, delta=1e-5)

    def test_currency_cleaning(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "act.csv"
            pd.DataFrame({
                "month": ["2026-04"],
                "net_patient_revenue": ["$48,000,000"],
            }).to_csv(path, index=False)
            df = _load_actuals(str(path))
            self.assertEqual(df.iloc[0]["net_patient_revenue"], 48_000_000)

    def test_no_month_column_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "act.csv"
            pd.DataFrame({"idr": [0.12]}).to_csv(path, index=False)
            with self.assertRaises(ValueError):
                _load_actuals(str(path))


# ── End-to-end with baseline capture ──────────────────────────────────────

class TestBaselineCapture(unittest.TestCase):
    def test_baseline_captured_after_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = create_deal(
                tmp,
                actual_path=ACTUAL_PATH,
                skip_intake=True,
                partner_brief=False,
                n_sims=200,
            )
            baseline = state.get("baseline") or {}
            self.assertIn("blended", baseline)
            self.assertIn("idr", baseline["blended"])
            self.assertIn("fwr", baseline["blended"])
            self.assertIn("dar_clean_days", baseline["blended"])
            self.assertIn("benchmark_targets", baseline)
            # Modeled drag block also present
            self.assertIn("modeled_ebitda_drag", baseline)
            self.assertGreater(baseline["modeled_ebitda_drag"]["mean"], 0)


class TestTrackDeal(unittest.TestCase):
    def _setup_deal(self, tmp: str) -> Path:
        """Create a real deal folder with baseline. Returns the deal dir."""
        create_deal(
            tmp,
            actual_path=ACTUAL_PATH,
            skip_intake=True,
            partner_brief=False,
            n_sims=200,
        )
        return Path(tmp)

    def _write_actuals(self, path: Path, months: list) -> Path:
        p = path / "actuals.csv"
        pd.DataFrame(months).to_csv(p, index=False)
        return p

    def test_append_single_month(self):
        with tempfile.TemporaryDirectory() as tmp:
            deal = self._setup_deal(tmp)
            actuals = self._write_actuals(deal, [
                {"month": "2026-04", "idr": 0.125, "fwr": 0.29, "dar_clean_days": 51.0},
            ])
            result = track_deal(str(deal), str(actuals))
            self.assertEqual(len(result["new_entries"]), 1)

            # deal.yaml now has a tracking block
            with open(deal / "deal.yaml") as f:
                state = yaml.safe_load(f)
            self.assertIn("tracking", state)
            self.assertEqual(state["tracking"][0]["month"], "2026-04")

            # Files written
            self.assertTrue((deal / "tracking_history.csv").exists())
            self.assertTrue((deal / "tracking_report.md").exists())

    def test_multiple_months_accumulate(self):
        with tempfile.TemporaryDirectory() as tmp:
            deal = self._setup_deal(tmp)
            actuals = self._write_actuals(deal, [
                {"month": "2026-04", "idr": 0.125, "fwr": 0.29},
                {"month": "2026-05", "idr": 0.120, "fwr": 0.28},
                {"month": "2026-06", "idr": 0.115, "fwr": 0.27},
            ])
            track_deal(str(deal), str(actuals))

            with open(deal / "deal.yaml") as f:
                state = yaml.safe_load(f)
            self.assertEqual(len(state["tracking"]), 3)
            self.assertEqual(state["tracking"][0]["month"], "2026-04")
            self.assertEqual(state["tracking"][-1]["month"], "2026-06")

    def test_calling_track_twice_appends(self):
        with tempfile.TemporaryDirectory() as tmp:
            deal = self._setup_deal(tmp)
            actuals_1 = self._write_actuals(deal, [
                {"month": "2026-04", "idr": 0.125},
            ])
            track_deal(str(deal), str(actuals_1))
            actuals_2 = deal / "actuals_2.csv"
            pd.DataFrame([{"month": "2026-05", "idr": 0.120}]).to_csv(actuals_2, index=False)
            track_deal(str(deal), str(actuals_2))

            with open(deal / "deal.yaml") as f:
                state = yaml.safe_load(f)
            self.assertEqual(len(state["tracking"]), 2)

    def test_alert_when_metric_worsens(self):
        with tempfile.TemporaryDirectory() as tmp:
            deal = self._setup_deal(tmp)
            # Baseline IDR is ~0.135. 0.20 is much worse.
            actuals = self._write_actuals(deal, [
                {"month": "2026-04", "idr": 0.20},
            ])
            result = track_deal(str(deal), str(actuals))
            entry = result["new_entries"][0]
            self.assertTrue(entry["alerts"])

    def test_missing_deal_yaml_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            actuals = Path(tmp) / "a.csv"
            pd.DataFrame([{"month": "2026-04", "idr": 0.12}]).to_csv(actuals, index=False)
            with self.assertRaises(FileNotFoundError):
                track_deal(tmp, str(actuals))

    def test_deal_without_baseline_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "deal.yaml"
            p.write_text("deal: {name: X, status: complete}\n")
            actuals = Path(tmp) / "a.csv"
            pd.DataFrame([{"month": "2026-04", "idr": 0.12}]).to_csv(actuals, index=False)
            with self.assertRaises(ValueError):
                track_deal(tmp, str(actuals))


class TestDealTrackCLI(unittest.TestCase):
    def test_cli_track_command(self):
        env = os.environ.copy()
        env.setdefault("MPLCONFIGDIR", "/tmp/mplcache")
        with tempfile.TemporaryDirectory() as tmp:
            # 1) Build a deal with baseline via the subprocess CLI
            r1 = subprocess.run(
                [sys.executable, "-m", "rcm_mc", "deal", "new",
                 "--dir", tmp, "--actual", ACTUAL_PATH, "--skip-intake",
                 "--no-partner-brief", "--n-sims", "200"],
                cwd=str(BASE_DIR), env=env,
                capture_output=True, text=True, timeout=240,
            )
            self.assertEqual(r1.returncode, 0, msg=r1.stderr[-800:])

            # 2) Write actuals
            actuals = Path(tmp) / "may.csv"
            pd.DataFrame([{"month": "2026-05", "idr": 0.12, "fwr": 0.28}]).to_csv(
                actuals, index=False,
            )

            # 3) Track
            r2 = subprocess.run(
                [sys.executable, "-m", "rcm_mc", "deal", "track",
                 "--dir", tmp, "--actuals", str(actuals)],
                cwd=str(BASE_DIR), env=env,
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(r2.returncode, 0, msg=r2.stderr[-800:])
            self.assertTrue((Path(tmp) / "tracking_history.csv").exists())
            self.assertTrue((Path(tmp) / "tracking_report.md").exists())
