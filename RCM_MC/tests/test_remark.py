"""Tests for underwrite re-mark (Brick 61)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from rcm_mc.pe.hold_tracking import record_quarterly_actuals
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.portfolio.portfolio_snapshots import list_snapshots, register_snapshot
from rcm_mc.pe.remark import (
    _quarters_elapsed,
    compute_remark,
    format_remark,
    persist_remark,
    remark_to_dict,
)


def _seed_deal(store: PortfolioStore, tmp: str, *,
               entry_ebitda=50e6, moic=2.55, irr=0.206,
               entry_multiple=9.0, exit_multiple=10.0, hold_years=5.0,
               exit_ev=None, deal_id="ccf") -> str:
    run = os.path.join(tmp, deal_id + "_run")
    os.makedirs(run, exist_ok=True)
    bridge = {
        "entry_ebitda": entry_ebitda,
        "entry_ev": entry_ebitda * entry_multiple,
        "entry_multiple": entry_multiple,
        "exit_multiple": exit_multiple,
        "hold_years": hold_years,
    }
    if exit_ev is not None:
        bridge["exit_ev"] = exit_ev
    with open(os.path.join(run, "pe_bridge.json"), "w") as f:
        json.dump(bridge, f)
    with open(os.path.join(run, "pe_returns.json"), "w") as f:
        json.dump({"moic": moic, "irr": irr}, f)
    register_snapshot(store, deal_id, "hold", run_dir=run)
    return deal_id


class TestQuartersElapsed(unittest.TestCase):
    def test_same_quarter_returns_1(self):
        self.assertEqual(_quarters_elapsed("2026Q1", "2026Q1"), 1)

    def test_full_year(self):
        self.assertEqual(_quarters_elapsed("2025Q1", "2025Q4"), 4)

    def test_across_year_boundary(self):
        self.assertEqual(_quarters_elapsed("2025Q4", "2026Q2"), 3)

    def test_malformed_returns_zero(self):
        self.assertEqual(_quarters_elapsed("bogus", "2026Q1"), 0)


class TestComputeRemark(unittest.TestCase):
    def test_no_snapshot_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            with self.assertRaises(ValueError) as ctx:
                compute_remark(store, "nonexistent", "2026Q2")
            self.assertIn("No snapshots", str(ctx.exception))

    def test_no_actuals_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            _seed_deal(store, tmp)
            with self.assertRaises(ValueError) as ctx:
                compute_remark(store, "ccf", "2026Q2")
            self.assertIn("No EBITDA actuals", str(ctx.exception))

    def test_snapshot_missing_entry_fields_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            register_snapshot(store, "bare", "hold")  # no run_dir → no PE math
            record_quarterly_actuals(store, "bare", "2026Q1",
                                     actuals={"ebitda": 10e6})
            with self.assertRaises(ValueError) as ctx:
                compute_remark(store, "bare", "2026Q1")
            self.assertIn("missing entry_ebitda", str(ctx.exception))

    def test_remark_improves_when_actuals_beat_plan(self):
        """Platform outperforming original underwrite → re-marked MOIC rises."""
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            # Conservative original: MOIC 1.8x (implied exit EBITDA ~$59M)
            _seed_deal(store, tmp, entry_ebitda=50e6, moic=1.8, irr=0.12)
            # Outperform: $20M/qtr = $80M TTM → much higher implied exit EBITDA
            for qtr in ("2025Q3", "2025Q4", "2026Q1", "2026Q2"):
                record_quarterly_actuals(store, "ccf", qtr,
                                         actuals={"ebitda": 20e6},
                                         plan={"ebitda": 12.5e6})
            r = compute_remark(store, "ccf", "2026Q2")
            self.assertGreater(r.remark_moic, r.original_moic)
            self.assertGreater(r.moic_delta, 0)
            self.assertGreater(r.ebitda_delta_vs_plan, 0)

    def test_remark_deteriorates_when_actuals_miss_plan(self):
        """Platform underperforming → re-marked MOIC drops."""
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            _seed_deal(store, tmp, entry_ebitda=50e6, moic=2.5, irr=0.20)
            # Flat $11M/qtr = $44M TTM — below $50M entry baseline
            for qtr in ("2025Q3", "2025Q4", "2026Q1", "2026Q2"):
                record_quarterly_actuals(store, "ccf", qtr,
                                         actuals={"ebitda": 11e6},
                                         plan={"ebitda": 13e6})
            r = compute_remark(store, "ccf", "2026Q2")
            self.assertLess(r.remark_moic, r.original_moic)
            self.assertLess(r.moic_delta, 0)
            self.assertLess(r.ebitda_delta_vs_plan, 0)

    def test_ttm_averages_last_four_quarters(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            _seed_deal(store, tmp)
            # Record 4 quarters at $10M → TTM $40M
            for qtr in ("2025Q3", "2025Q4", "2026Q1", "2026Q2"):
                record_quarterly_actuals(store, "ccf", qtr,
                                         actuals={"ebitda": 10e6})
            r = compute_remark(store, "ccf", "2026Q2")
            self.assertAlmostEqual(r.actual_ttm_ebitda, 40e6, places=0)
            self.assertEqual(r.quarters_of_actuals, 4)

    def test_as_of_quarter_truncates_later_data(self):
        """Quarters after as-of aren't included in TTM."""
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            _seed_deal(store, tmp)
            # Record 6 quarters, re-mark as-of Q4 → only first 4 in TTM
            for qtr in ("2025Q1", "2025Q2", "2025Q3", "2025Q4",
                        "2026Q1", "2026Q2"):
                record_quarterly_actuals(store, "ccf", qtr,
                                         actuals={"ebitda": 10e6})
            r = compute_remark(store, "ccf", "2025Q4")
            self.assertEqual(r.quarters_of_actuals, 4)

    def test_years_remaining_respects_hold_years(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            _seed_deal(store, tmp, hold_years=5.0)
            for qtr in ("2025Q3", "2025Q4", "2026Q1", "2026Q2"):
                record_quarterly_actuals(store, "ccf", qtr, actuals={"ebitda": 12e6})
            r = compute_remark(store, "ccf", "2026Q2")
            # 4 quarters in on a 5-year hold → 4.0 years remaining
            self.assertAlmostEqual(r.years_remaining, 4.0, places=2)


class TestPersistRemark(unittest.TestCase):
    def test_persist_adds_new_snapshot_with_remark_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            _seed_deal(store, tmp)
            for qtr in ("2025Q3", "2025Q4", "2026Q1", "2026Q2"):
                record_quarterly_actuals(store, "ccf", qtr,
                                         actuals={"ebitda": 12e6})
            r = compute_remark(store, "ccf", "2026Q2")
            sid = persist_remark(store, r)
            self.assertGreater(sid, 0)
            snaps = list_snapshots(store, deal_id="ccf")
            # Original + persisted re-mark = 2 snapshots
            self.assertEqual(len(snaps), 2)
            remark_row = snaps.iloc[0]  # newest first
            self.assertIn("Re-mark as of 2026Q2", str(remark_row.get("notes") or ""))


class TestRemarkDictAndFormat(unittest.TestCase):
    def _result(self, tmp: str):
        store = PortfolioStore(os.path.join(tmp, "p.db"))
        _seed_deal(store, tmp)
        for qtr in ("2025Q3", "2025Q4", "2026Q1", "2026Q2"):
            record_quarterly_actuals(store, "ccf", qtr,
                                     actuals={"ebitda": 11e6},
                                     plan={"ebitda": 13e6})
        return compute_remark(store, "ccf", "2026Q2")

    def test_dict_has_nested_original_and_remark_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = remark_to_dict(self._result(tmp))
            self.assertIn("original", d)
            self.assertIn("remark", d)
            self.assertIn("deltas", d)
            # Round-trips as JSON
            json.dumps(d, default=str)

    def test_format_uses_multiple_suffix_for_moic_delta(self):
        """MOIC delta rendered as '-1.49x' NOT '-149.4%'."""
        with tempfile.TemporaryDirectory() as tmp:
            text = format_remark(self._result(tmp))
            # Find the MOIC line
            moic_line = next(l for l in text.splitlines() if "MOIC" in l and "Δ" not in l)
            # MOIC delta formatted as "+Nx" or "-Nx" never "%"
            self.assertIn("x", moic_line.split()[-1])

    def test_format_uses_pp_for_irr_delta(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = format_remark(self._result(tmp))
            self.assertIn("pp", text)


class TestRemarkCLI(unittest.TestCase):
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

    def test_remark_subcommand_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            store = PortfolioStore(db)
            _seed_deal(store, tmp)
            for qtr in ("2025Q3", "2025Q4", "2026Q1", "2026Q2"):
                record_quarterly_actuals(store, "ccf", qtr,
                                         actuals={"ebitda": 12e6})
            rc, out, _ = self._capture([
                "--db", db, "remark", "--deal-id", "ccf", "--as-of", "2026Q2",
            ])
            self.assertEqual(rc, 0)
            self.assertIn("Underwrite re-mark", out)
            self.assertIn("MOIC", out)
            self.assertIn("IRR", out)

    def test_remark_persist_writes_new_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            store = PortfolioStore(db)
            _seed_deal(store, tmp)
            for qtr in ("2025Q3", "2025Q4", "2026Q1", "2026Q2"):
                record_quarterly_actuals(store, "ccf", qtr, actuals={"ebitda": 12e6})
            rc, out, _ = self._capture([
                "--db", db, "remark", "--deal-id", "ccf",
                "--as-of", "2026Q2", "--persist",
            ])
            self.assertEqual(rc, 0)
            self.assertIn("Persisted re-mark snapshot", out)
            snaps = list_snapshots(store, deal_id="ccf")
            self.assertEqual(len(snaps), 2)

    def test_remark_unknown_deal_returns_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            rc, _, err = self._capture([
                "--db", db, "remark",
                "--deal-id", "ghost", "--as-of", "2026Q2",
            ])
            self.assertEqual(rc, 1)
            self.assertIn("No snapshots", err)

    def test_remark_json_emits_structured_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            store = PortfolioStore(db)
            _seed_deal(store, tmp)
            for qtr in ("2025Q3", "2025Q4", "2026Q1", "2026Q2"):
                record_quarterly_actuals(store, "ccf", qtr, actuals={"ebitda": 12e6})
            rc, out, _ = self._capture([
                "--db", db, "remark", "--deal-id", "ccf",
                "--as-of", "2026Q2", "--json",
            ])
            self.assertEqual(rc, 0)
            payload = json.loads(out)
            self.assertIn("original", payload)
            self.assertIn("remark", payload)
            self.assertIn("deltas", payload)
