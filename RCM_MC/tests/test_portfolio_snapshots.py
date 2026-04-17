"""Tests for portfolio deal-snapshot system (Brick 49)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest

import pandas as pd

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.portfolio.portfolio_snapshots import (
    DEAL_STAGES,
    _read_pe_artifacts,
    format_rollup,
    latest_per_deal,
    list_snapshots,
    portfolio_rollup,
    register_snapshot,
)


def _seed_pe_run(dirpath: str, *,
                 moic: float = 2.5, irr: float = 0.20,
                 headroom: float = 1.1,
                 entry_ebitda: float = 50e6,
                 entry_ev: float = 450e6, exit_ev: float = 659e6,
                 concerning: int = 2, favorable: int = 1) -> None:
    """Write a minimal set of pe_* artifacts that register_snapshot can read."""
    os.makedirs(dirpath, exist_ok=True)
    with open(os.path.join(dirpath, "pe_bridge.json"), "w") as f:
        json.dump({
            "entry_ebitda": entry_ebitda, "entry_multiple": 9.0,
            "exit_multiple": 10.0, "hold_years": 5.0,
            "entry_ev": entry_ev, "exit_ev": exit_ev,
        }, f)
    with open(os.path.join(dirpath, "pe_returns.json"), "w") as f:
        json.dump({"moic": moic, "irr": irr,
                   "entry_equity": 180e6, "exit_proceeds": 459e6,
                   "hold_years": 5.0}, f)
    with open(os.path.join(dirpath, "pe_covenant.json"), "w") as f:
        json.dump({"actual_leverage": 5.4,
                   "covenant_headroom_turns": headroom}, f)
    severities = (["concerning"] * concerning
                  + ["favorable"] * favorable
                  + ["neutral"] * 3)
    pd.DataFrame({"severity": severities}).to_csv(
        os.path.join(dirpath, "trend_signals.csv"), index=False,
    )


class TestReadPEArtifacts(unittest.TestCase):
    def test_reads_all_fields_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_pe_run(tmp, moic=2.5, irr=0.20, headroom=1.1)
            fields = _read_pe_artifacts(tmp)
            self.assertEqual(fields["entry_ebitda"], 50e6)
            self.assertEqual(fields["moic"], 2.5)
            self.assertAlmostEqual(fields["irr"], 0.20)
            self.assertEqual(fields["covenant_status"], "SAFE")
            self.assertEqual(fields["concerning_signals"], 2)
            self.assertEqual(fields["favorable_signals"], 1)

    def test_covenant_status_tight_when_headroom_below_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_pe_run(tmp, headroom=0.3)
            self.assertEqual(_read_pe_artifacts(tmp)["covenant_status"], "TIGHT")

    def test_covenant_status_tripped_when_headroom_negative(self):
        with tempfile.TemporaryDirectory() as tmp:
            _seed_pe_run(tmp, headroom=-0.5)
            self.assertEqual(_read_pe_artifacts(tmp)["covenant_status"], "TRIPPED")

    def test_missing_run_dir_returns_none_fields(self):
        fields = _read_pe_artifacts("/nonexistent/path")
        self.assertIsNone(fields["moic"])
        self.assertIsNone(fields["covenant_status"])


class TestRegisterSnapshot(unittest.TestCase):
    def _store(self, tmp: str) -> PortfolioStore:
        return PortfolioStore(os.path.join(tmp, "portfolio.db"))

    def test_registers_snapshot_with_pe_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            run = os.path.join(tmp, "ccf")
            _seed_pe_run(run, moic=2.55, irr=0.21)
            sid = register_snapshot(store, deal_id="ccf_001", stage="loi",
                                    run_dir=run, notes="Post-QoE")
            self.assertIsInstance(sid, int)
            self.assertGreater(sid, 0)

    def test_early_stage_snapshot_without_run_dir(self):
        """Sourced / IOI stages have no run yet — snapshot still works."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            sid = register_snapshot(store, deal_id="new_lead", stage="sourced")
            df = list_snapshots(store, deal_id="new_lead")
            self.assertEqual(len(df), 1)
            self.assertIsNone(df.iloc[0]["moic"])
            self.assertEqual(df.iloc[0]["stage"], "sourced")

    def test_invalid_stage_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            with self.assertRaises(ValueError):
                register_snapshot(store, deal_id="x", stage="not-a-stage")

    def test_append_only_multiple_snapshots_per_deal(self):
        """Snapshots form an audit trail — each new stage appends."""
        with tempfile.TemporaryDirectory() as tmp:
            store = self._store(tmp)
            register_snapshot(store, deal_id="ccf", stage="sourced")
            register_snapshot(store, deal_id="ccf", stage="ioi")
            register_snapshot(store, deal_id="ccf", stage="loi")
            df = list_snapshots(store, deal_id="ccf")
            self.assertEqual(len(df), 3)
            # Stages, newest first
            self.assertEqual(list(df["stage"]), ["loi", "ioi", "sourced"])


class TestLatestPerDeal(unittest.TestCase):
    def test_returns_only_newest_per_deal(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            register_snapshot(store, "A", "sourced")
            register_snapshot(store, "A", "ioi")
            register_snapshot(store, "B", "spa")
            df = latest_per_deal(store)
            self.assertEqual(len(df), 2)
            a_row = df[df["deal_id"] == "A"].iloc[0]
            self.assertEqual(a_row["stage"], "ioi")


class TestPortfolioRollup(unittest.TestCase):
    def test_empty_portfolio(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            r = portfolio_rollup(store)
            self.assertEqual(r["deal_count"], 0)
            self.assertIsNone(r["weighted_moic"])
            self.assertEqual(r["covenant_trips"], 0)

    def test_rollup_weighted_by_entry_ev(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            run_big = os.path.join(tmp, "big")
            run_small = os.path.join(tmp, "small")
            # Big deal $900M EV, 3.0x MOIC; small deal $100M EV, 2.0x MOIC
            # Weighted = (3.0 * 900 + 2.0 * 100) / (900+100) = 2.9x
            _seed_pe_run(run_big, moic=3.0, irr=0.25, entry_ev=900e6)
            _seed_pe_run(run_small, moic=2.0, irr=0.15, entry_ev=100e6)
            register_snapshot(store, "big", "hold", run_dir=run_big)
            register_snapshot(store, "small", "hold", run_dir=run_small)
            r = portfolio_rollup(store)
            self.assertAlmostEqual(r["weighted_moic"], 2.9, places=2)
            self.assertAlmostEqual(r["weighted_irr"], 0.24, places=2)

    def test_covenant_trip_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            run_tripped = os.path.join(tmp, "tripped")
            run_safe = os.path.join(tmp, "safe")
            _seed_pe_run(run_tripped, headroom=-0.5)
            _seed_pe_run(run_safe, headroom=1.2)
            register_snapshot(store, "tripped", "hold", run_dir=run_tripped)
            register_snapshot(store, "safe", "hold", run_dir=run_safe)
            r = portfolio_rollup(store)
            self.assertEqual(r["covenant_trips"], 1)
            self.assertEqual(r["covenant_tight"], 0)

    def test_stage_funnel_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            register_snapshot(store, "a", "sourced")
            register_snapshot(store, "b", "sourced")
            register_snapshot(store, "c", "loi")
            register_snapshot(store, "d", "hold")
            r = portfolio_rollup(store)
            self.assertEqual(r["stage_funnel"]["sourced"], 2)
            self.assertEqual(r["stage_funnel"]["loi"], 1)
            self.assertEqual(r["stage_funnel"]["hold"], 1)

    def test_stages_canonical_order(self):
        self.assertEqual(DEAL_STAGES[0], "sourced")
        self.assertEqual(DEAL_STAGES[-1], "exit")


class TestFormatRollup(unittest.TestCase):
    def test_empty_rollup_renders_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            out = format_rollup(portfolio_rollup(store))
            self.assertIn("0 deals", out)
            self.assertIn("—", out)  # dashes for missing weighted MOIC / IRR

    def test_populated_rollup_shows_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            run = os.path.join(tmp, "r1")
            _seed_pe_run(run)
            register_snapshot(store, "d1", "hold", run_dir=run)
            out = format_rollup(portfolio_rollup(store))
            self.assertIn("1 deals", out)
            self.assertIn("Weighted MOIC", out)
            self.assertIn("x", out)  # MOIC expressed as multiple
