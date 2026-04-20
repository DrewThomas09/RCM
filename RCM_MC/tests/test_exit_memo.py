"""Tests for exit-readiness memo (Brick 55)."""
from __future__ import annotations

import json
import os
import tempfile
import unittest

from rcm_mc.reports.exit_memo import build_exit_memo
from rcm_mc.pe.hold_tracking import record_quarterly_actuals
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.portfolio.portfolio_snapshots import register_snapshot


def _seed_held_deal_with_history(tmp: str, *,
                                 entry_ebitda: float = 50e6,
                                 quarters=(
                                     ("2025Q1", 48e6),
                                     ("2025Q2", 49e6),
                                     ("2025Q3", 50e6),
                                     ("2025Q4", 51e6),
                                 ),
                                 plan: float = 50e6,
                                 headroom: float = 1.1,
                                 concerning: int = 0,
                                 deal_id: str = "ccf") -> PortfolioStore:
    """Fixture: held deal with N quarters of actuals + PE math snapshot."""
    store = PortfolioStore(os.path.join(tmp, "p.db"))
    run = os.path.join(tmp, deal_id + "_run")
    os.makedirs(run, exist_ok=True)
    with open(os.path.join(run, "pe_bridge.json"), "w") as f:
        json.dump({
            "entry_ebitda": entry_ebitda, "entry_ev": entry_ebitda * 9.0,
            "entry_multiple": 9.0, "exit_multiple": 10.0, "hold_years": 5.0,
        }, f)
    with open(os.path.join(run, "pe_returns.json"), "w") as f:
        json.dump({"moic": 2.55, "irr": 0.206}, f)
    with open(os.path.join(run, "pe_covenant.json"), "w") as f:
        json.dump({"actual_leverage": 5.4,
                   "covenant_headroom_turns": headroom}, f)
    if concerning:
        import pandas as _pd
        _pd.DataFrame({"severity": ["concerning"] * concerning + ["neutral"] * 3}).to_csv(
            os.path.join(run, "trend_signals.csv"), index=False,
        )
    register_snapshot(store, deal_id, "hold", run_dir=run)
    for qtr, actual in quarters:
        record_quarterly_actuals(
            store, deal_id, qtr,
            actuals={"ebitda": actual}, plan={"ebitda": plan},
        )
    return store


def _read_text(path: str) -> str:
    with open(path) as f:
        return f.read()


class TestBuildExitMemo(unittest.TestCase):
    def test_writes_valid_html_with_all_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_held_deal_with_history(tmp)
            out = os.path.join(tmp, "exit.html")
            build_exit_memo(store, "ccf", out)
            self.assertTrue(os.path.isfile(out))
            text = _read_text(out)
            # Structural sections
            for section in ("Deal facts", "Track record", "Current pace", "Risk factors"):
                self.assertIn(section, text)
            # Well-formed HTML
            self.assertIn("<!doctype html>", text.lower())
            self.assertIn("</html>", text)

    def test_entry_underwrite_fields_rendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_held_deal_with_history(tmp, entry_ebitda=50e6)
            out = os.path.join(tmp, "e.html")
            build_exit_memo(store, "ccf", out)
            text = _read_text(out)
            # $50M entry EBITDA, $450M entry EV, 2.55x MOIC
            self.assertIn("$50M", text)
            self.assertIn("$450M", text)
            self.assertIn("2.55x", text)

    def test_quarters_appear_in_track_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_held_deal_with_history(tmp)
            out = os.path.join(tmp, "e.html")
            build_exit_memo(store, "ccf", out)
            text = _read_text(out)
            for qtr in ("2025Q1", "2025Q2", "2025Q3", "2025Q4"):
                self.assertIn(qtr, text)

    def test_risk_factors_clean_when_safe_and_no_concerning(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_held_deal_with_history(tmp, headroom=1.5, concerning=0)
            out = os.path.join(tmp, "e.html")
            build_exit_memo(store, "ccf", out)
            text = _read_text(out)
            self.assertIn("No material risk flags", text)

    def test_risk_factors_surfaces_covenant_tripped(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_held_deal_with_history(tmp, headroom=-0.5)
            out = os.path.join(tmp, "e.html")
            build_exit_memo(store, "ccf", out)
            text = _read_text(out)
            self.assertIn("Covenant TRIPPED", text)

    def test_risk_factors_shows_concerning_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_held_deal_with_history(tmp, concerning=3)
            out = os.path.join(tmp, "e.html")
            build_exit_memo(store, "ccf", out)
            text = _read_text(out)
            self.assertIn("concerning trend signals", text)
            # Count "3" rendered somewhere near the concerning bullet
            self.assertIn("<strong>3</strong>", text)

    def test_current_pace_includes_cumulative_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            # EBITDA well above plan → positive cumulative drift
            store = _seed_held_deal_with_history(
                tmp, quarters=(("2026Q1", 55e6), ("2026Q2", 56e6), ("2026Q3", 57e6)),
                plan=50e6,
            )
            out = os.path.join(tmp, "e.html")
            build_exit_memo(store, "ccf", out)
            text = _read_text(out)
            self.assertIn("Cumulative drift", text)

    def test_initiative_attribution_section_when_actuals_present(self):
        """B58: memo surfaces per-initiative cumulative actuals vs plan."""
        from rcm_mc.rcm.initiative_tracking import record_initiative_actual
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_held_deal_with_history(tmp)
            # Record attribution for two shipped initiatives
            record_initiative_actual(store, deal_id="ccf",
                initiative_id="prior_auth_improvement",
                quarter="2025Q1", ebitda_impact=5000)
            record_initiative_actual(store, deal_id="ccf",
                initiative_id="prior_auth_improvement",
                quarter="2025Q2", ebitda_impact=6000)
            record_initiative_actual(store, deal_id="ccf",
                initiative_id="coding_cdi_improvement",
                quarter="2025Q1", ebitda_impact=20000)

            out = os.path.join(tmp, "e.html")
            build_exit_memo(store, "ccf", out)
            text = _read_text(out)
            self.assertIn("Initiative attribution", text)
            self.assertIn("prior_auth_improvement", text)
            self.assertIn("coding_cdi_improvement", text)

    def test_initiative_section_omitted_when_no_attribution(self):
        """Memo must not render the attribution block for deals that lack it."""
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_held_deal_with_history(tmp)  # no initiative_actuals
            out = os.path.join(tmp, "e.html")
            build_exit_memo(store, "ccf", out)
            text = _read_text(out)
            self.assertNotIn("Initiative attribution", text)

    def test_missing_deal_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = PortfolioStore(os.path.join(tmp, "p.db"))
            out = os.path.join(tmp, "e.html")
            with self.assertRaises(ValueError):
                build_exit_memo(store, "nonexistent", out)

    def test_title_override_respected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _seed_held_deal_with_history(tmp)
            out = os.path.join(tmp, "e.html")
            build_exit_memo(store, "ccf", out, title="Project Alpha Exit Memo")
            text = _read_text(out)
            self.assertIn("Project Alpha Exit Memo", text)


class TestExitMemoCLI(unittest.TestCase):
    def test_exit_memo_subcommand_writes_file(self):
        import io
        import sys
        from rcm_mc.portfolio_cmd import main as pm

        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "p.db")
            # Seed via the fixture but redirect to the CLI db path
            store = _seed_held_deal_with_history(tmp)
            # Move the seeded db to the CLI's expected path
            os.rename(os.path.join(tmp, "p.db"), db_path)

            out = os.path.join(tmp, "exit.html")
            buf = io.StringIO()
            saved = sys.stdout
            sys.stdout = buf
            try:
                rc = pm([
                    "--db", db_path, "exit-memo",
                    "--deal-id", "ccf", "--out", out,
                ])
            finally:
                sys.stdout = saved
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.isfile(out))
            self.assertIn("Wrote:", buf.getvalue())

    def test_exit_memo_unknown_deal_returns_1(self):
        import io
        import sys
        from rcm_mc.portfolio_cmd import main as pm

        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "p.db")
            err = io.StringIO()
            se = sys.stderr
            sys.stderr = err
            try:
                rc = pm([
                    "--db", db, "exit-memo",
                    "--deal-id", "ghost",
                    "--out", os.path.join(tmp, "e.html"),
                ])
            finally:
                sys.stderr = se
            self.assertEqual(rc, 1)
            self.assertIn("No snapshots", err.getvalue())
