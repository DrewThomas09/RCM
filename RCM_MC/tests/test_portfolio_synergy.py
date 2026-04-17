"""Tests for cross-platform RCM synergy math (Brick 60)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.portfolio.portfolio_snapshots import register_snapshot
from rcm_mc.portfolio.portfolio_synergy import (
    SynergyResult,
    compute_synergy,
    format_synergy,
    synergy_to_dict,
)


def _seed_held_deal(store: PortfolioStore, tmp: str, deal_id: str,
                    entry_ebitda: float) -> None:
    run = os.path.join(tmp, deal_id + "_run")
    os.makedirs(run, exist_ok=True)
    with open(os.path.join(run, "pe_bridge.json"), "w") as f:
        json.dump({
            "entry_ebitda": entry_ebitda, "entry_ev": entry_ebitda * 9.0,
            "entry_multiple": 9.0, "exit_multiple": 10.0, "hold_years": 5.0,
        }, f)
    register_snapshot(store, deal_id, "hold", run_dir=run)


class TestComputeSynergy(unittest.TestCase):
    def _store_with_n_deals(self, tmp: str, n: int,
                            ebitdas=None) -> PortfolioStore:
        store = PortfolioStore(os.path.join(tmp, "p.db"))
        ebs = ebitdas or [50e6] * n
        for i, eb in enumerate(ebs[:n]):
            _seed_held_deal(store, tmp, f"deal_{i}", eb)
        return store

    def test_empty_portfolio_produces_zero_synergy(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            r = compute_synergy(store)
            self.assertEqual(r.deal_count, 0)
            self.assertEqual(r.synergy_ebitda, 0.0)
            self.assertIn("Portfolio is empty", r.warnings)

    def test_single_platform_warns_below_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store_with_n_deals(tmp, 1)
            r = compute_synergy(store)
            # Math still runs but a warning flags insufficient scale
            self.assertEqual(r.platforms_in_scope, 1)
            self.assertTrue(any("3+ platforms" in w for w in r.warnings))

    def test_three_platforms_meets_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store_with_n_deals(tmp, 3)
            r = compute_synergy(store)
            # No "3+ platforms" warning at exactly 3 — the check is < 3
            self.assertFalse(any("3+ platforms" in w for w in r.warnings))

    def test_synergy_math_reconciles(self):
        """synergy = Σ(entry_ebitda × cost_pct × shared_pct × savings_pct)."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store_with_n_deals(tmp, 3, ebitdas=[100e6, 50e6, 20e6])
            r = compute_synergy(store, shared_service_pct=0.4, savings_pct=0.15)
            # Sum of entry EBITDA = 170M; RCM cost @ 8% = 13.6M
            # Shared @ 40% = 5.44M; savings @ 15% = 816K
            expected = (100e6 + 50e6 + 20e6) * 0.08 * 0.4 * 0.15
            self.assertAlmostEqual(r.synergy_ebitda, expected, places=0)

    def test_per_platform_attribution_sums_to_total(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store_with_n_deals(tmp, 4, ebitdas=[50e6, 30e6, 20e6, 15e6])
            r = compute_synergy(store)
            per_platform_total = sum(
                p["synergy_contribution"] for p in r.per_platform
            )
            self.assertAlmostEqual(per_platform_total, r.synergy_ebitda, places=2)

    def test_stage_filter_excludes_pipeline_deals(self):
        """Deals at sourced / ioi can't share services yet."""
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            _seed_held_deal(store, tmp, "d1", 50e6)
            _seed_held_deal(store, tmp, "d2", 30e6)
            register_snapshot(store, "pipeline", "ioi")  # excluded
            r = compute_synergy(store)
            self.assertEqual(r.platforms_in_scope, 2)
            self.assertTrue(any("Excluded" in w for w in r.warnings))

    def test_deal_without_entry_ebitda_excluded_not_zero_filled(self):
        """A deal we can't size must not fabricate synergy."""
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            _seed_held_deal(store, tmp, "d1", 50e6)
            register_snapshot(store, "no_ebitda", "hold")  # no run_dir = no entry_ebitda
            r = compute_synergy(store)
            self.assertEqual(r.platforms_in_scope, 1)
            self.assertTrue(any("no_ebitda" in w and "excluded" in w for w in r.warnings))

    def test_invalid_shared_service_pct_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store_with_n_deals(tmp, 3)
            with self.assertRaises(ValueError):
                compute_synergy(store, shared_service_pct=1.5)

    def test_invalid_savings_pct_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store_with_n_deals(tmp, 3)
            with self.assertRaises(ValueError):
                compute_synergy(store, savings_pct=-0.1)


class TestFormatSynergy(unittest.TestCase):
    def test_empty_portfolio_renders_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            text = format_synergy(compute_synergy(store))
            self.assertIn("0 platform", text)
            self.assertIn("Portfolio is empty", text)

    def test_populated_synergy_shows_per_platform_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            _seed_held_deal(store, tmp, "ccf", 50e6)
            _seed_held_deal(store, tmp, "rural", 15e6)
            _seed_held_deal(store, tmp, "regional", 30e6)
            text = format_synergy(compute_synergy(store))
            self.assertIn("ccf", text)
            self.assertIn("rural", text)
            self.assertIn("regional", text)
            # Largest deal surfaced first in per-platform table
            ccf_pos = text.find("ccf ")
            rural_pos = text.find("rural ")
            self.assertLess(ccf_pos, rural_pos)


class TestSynergyToDict(unittest.TestCase):
    def test_round_trips_cleanly_to_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            _seed_held_deal(store, tmp, "d1", 50e6)
            _seed_held_deal(store, tmp, "d2", 30e6)
            _seed_held_deal(store, tmp, "d3", 20e6)
            payload = synergy_to_dict(compute_synergy(store))
            round_trip = json.loads(json.dumps(payload, default=str))
            self.assertEqual(round_trip["platforms_in_scope"], 3)


class TestSynergyCLI(unittest.TestCase):
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

    def test_synergy_subcommand_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            store = PortfolioStore(db)
            _seed_held_deal(store, tmp, "a", 50e6)
            _seed_held_deal(store, tmp, "b", 30e6)
            _seed_held_deal(store, tmp, "c", 20e6)
            rc, out, _ = self._capture(["--db", db, "synergy"])
            self.assertEqual(rc, 0)
            self.assertIn("synergy", out.lower())

    def test_synergy_json_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            store = PortfolioStore(db)
            _seed_held_deal(store, tmp, "a", 50e6)
            _seed_held_deal(store, tmp, "b", 30e6)
            _seed_held_deal(store, tmp, "c", 20e6)
            rc, out, _ = self._capture(["--db", db, "synergy", "--json"])
            self.assertEqual(rc, 0)
            parsed = json.loads(out)
            self.assertIn("synergy_ebitda", parsed)
            self.assertIn("per_platform", parsed)
            self.assertEqual(len(parsed["per_platform"]), 3)

    def test_synergy_override_flags(self):
        """Override shared-service and savings pcts via CLI flags."""
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            store = PortfolioStore(db)
            _seed_held_deal(store, tmp, "a", 50e6)
            _seed_held_deal(store, tmp, "b", 30e6)
            _seed_held_deal(store, tmp, "c", 20e6)
            rc, out, _ = self._capture([
                "--db", db, "synergy", "--json",
                "--shared-service-pct", "0.60",
                "--savings-pct", "0.20",
            ])
            self.assertEqual(rc, 0)
            parsed = json.loads(out)
            self.assertAlmostEqual(parsed["shared_service_pct"], 0.60)
            self.assertAlmostEqual(parsed["savings_pct"], 0.20)
