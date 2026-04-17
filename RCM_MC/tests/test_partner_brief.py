"""Tests for the one-page partner-brief generator."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
ACTUAL = str(BASE_DIR / "configs" / "actual.yaml")
BENCH = str(BASE_DIR / "configs" / "benchmark.yaml")


def _seed_outdir(tmp: str, *, with_peer: bool = False, with_pressure: bool = False,
                 with_provenance: bool = True, grade: str = "B",
                 with_trend: bool = False, with_pe: bool = False) -> None:
    """Write the minimum set of files the brief reads."""
    # summary.csv — indexed by metric name
    pd.DataFrame({
        "mean": [6e6, 2e6],
        "median": [5.9e6, 1.9e6],
        "p10": [3e6, 1e6],
        "p90": [9e6, 3e6],
    }, index=["ebitda_drag", "economic_drag"]).to_csv(os.path.join(tmp, "summary.csv"))

    # provenance.json with grade block
    if with_provenance:
        doc = {
            "run": {"n_sims": 500, "generated_at_utc": "2026-04-14T00:00:00Z"},
            "metrics": [],
            "sources": {
                "classification": {},
                "counts": {"observed": 15, "prior": 0, "assumed": 17, "total": 32},
                "grade": grade,
                "notes": {},
            },
        }
        with open(os.path.join(tmp, "provenance.json"), "w") as f:
            json.dump(doc, f)

    if with_peer:
        pd.DataFrame({
            "kpi": ["net_patient_revenue", "beds", "medicare_day_pct"],
            "target": [6.4e9, 1326, 0.225],
            "peer_p10": [2.0e9, 500, 0.15],
            "peer_median": [2.8e9, 800, 0.22],
            "peer_p90": [4.0e9, 1200, 0.30],
            "target_percentile": [95.0, 93.0, 52.0],
        }).to_csv(os.path.join(tmp, "peer_target_percentiles.csv"), index=False)

    if with_trend:
        pd.DataFrame({
            "metric": ["net_patient_revenue", "medicare_day_pct", "operating_margin"],
            "start_year": [2020, 2020, 2020],
            "end_year": [2022, 2022, 2022],
            "start_value": [5.24e9, 0.270, -0.191],
            "end_value": [6.38e9, 0.225, -0.177],
            "pct_change": [0.217, None, None],
            "pts_change": [None, -4.5, 1.4],
            "direction": ["up", "down", "up"],
            "severity": ["favorable", "neutral", "neutral"],
        }).to_csv(os.path.join(tmp, "trend_signals.csv"), index=False)

    if with_pe:
        with open(os.path.join(tmp, "pe_bridge.json"), "w") as f:
            json.dump({
                "entry_ev": 450e6, "exit_ev": 659e6,
                "total_value_created": 209e6,
                "components": [
                    {"step": "Entry EV", "value": 450e6,
                     "share_of_creation": None, "note": "9.0x × 50M"},
                    {"step": "Organic EBITDA", "value": 72e6,
                     "share_of_creation": 0.34, "note": "3%/yr × 5y"},
                    {"step": "RCM uplift", "value": 72e6,
                     "share_of_creation": 0.34, "note": "× 9x entry"},
                    {"step": "Multiple expansion", "value": 66e6,
                     "share_of_creation": 0.32, "note": "Δ+1x"},
                    {"step": "Exit EV", "value": 659e6,
                     "share_of_creation": None, "note": "10.0x × 66M"},
                ],
            }, f)
        with open(os.path.join(tmp, "pe_returns.json"), "w") as f:
            json.dump({
                "entry_equity": 180e6, "exit_proceeds": 459e6,
                "hold_years": 5.0, "moic": 2.55, "irr": 0.206,
                "total_distributions": 459e6,
            }, f)
        with open(os.path.join(tmp, "pe_covenant.json"), "w") as f:
            json.dump({
                "ebitda": 50e6, "debt": 270e6,
                "covenant_max_leverage": 6.5, "actual_leverage": 5.4,
                "covenant_headroom_turns": 1.1, "ebitda_cushion_pct": 0.17,
                "covenant_trips_at_ebitda": 41.5e6, "interest_coverage": 2.3,
            }, f)

    if with_pressure:
        pd.DataFrame({
            "achievement": [0.0, 0.5, 0.75, 1.0],
            "ebitda_drag_mean": [6e6, 5.2e6, 4.5e6, 3.8e6],
            "ebitda_drag_p10": [4e6, 3.5e6, 3e6, 2.5e6],
            "ebitda_drag_p90": [9e6, 8e6, 7e6, 6e6],
        }).to_csv(os.path.join(tmp, "pressure_test_miss_scenarios.csv"), index=False)


class TestBuildPartnerBrief(unittest.TestCase):
    """Unit tests for the module (no CLI)."""

    def test_creates_html_at_default_path(self):
        from rcm_mc.reports._partner_brief import build_partner_brief
        with tempfile.TemporaryDirectory() as tmp:
            _seed_outdir(tmp)
            path = build_partner_brief(
                tmp, hospital_name="Test Hosp", ev_multiple=8.0,
                actual_config_path=ACTUAL, benchmark_config_path=BENCH,
            )
            self.assertTrue(os.path.exists(path))
            self.assertEqual(os.path.basename(path), "partner_brief.html")

    def test_brief_contains_core_sections(self):
        from rcm_mc.reports._partner_brief import build_partner_brief
        with tempfile.TemporaryDirectory() as tmp:
            _seed_outdir(tmp, grade="A")
            path = build_partner_brief(
                tmp, hospital_name="Acme Hospital", ev_multiple=8.0,
                actual_config_path=ACTUAL, benchmark_config_path=BENCH,
            )
            with open(path) as f:
                html = f.read()
            self.assertIn("Acme Hospital", html)
            self.assertIn("EBITDA Opportunity", html)
            self.assertIn("Enterprise Value", html)
            self.assertIn("Evidence grade A", html)
            self.assertIn("Bottom line", html)
            self.assertIn("report.html", html)  # footer pointer

    def test_brief_omits_peer_section_when_not_run(self):
        from rcm_mc.reports._partner_brief import build_partner_brief
        with tempfile.TemporaryDirectory() as tmp:
            _seed_outdir(tmp, with_peer=False)
            path = build_partner_brief(
                tmp, hospital_name="X", ev_multiple=8.0,
                actual_config_path=ACTUAL, benchmark_config_path=BENCH,
            )
            with open(path) as f: html = f.read()
            self.assertNotIn("Peer position", html)

    def test_brief_includes_trend_block_when_signals_present(self):
        from rcm_mc.reports._partner_brief import build_partner_brief
        with tempfile.TemporaryDirectory() as tmp:
            _seed_outdir(tmp, with_trend=True)
            path = build_partner_brief(
                tmp, hospital_name="X", ev_multiple=8.0,
                actual_config_path=ACTUAL, benchmark_config_path=BENCH,
            )
            with open(path) as f: html = f.read()
            self.assertIn("Multi-year trend", html)
            self.assertIn("2020", html)
            self.assertIn("2022", html)
            # Direction arrow rendered
            self.assertTrue(any(a in html for a in ("↑", "↓", "→")))

    def test_brief_includes_watchlist_summary_when_concerning_signals(self):
        from rcm_mc.reports._partner_brief import build_partner_brief
        with tempfile.TemporaryDirectory() as tmp:
            _seed_outdir(tmp, with_trend=False)
            pd.DataFrame({
                "metric": ["net_income", "operating_expenses"],
                "start_year": [2020, 2020],
                "end_year": [2022, 2022],
                "start_value": [-9.99e8, 6.24e9],
                "end_value": [-1.13e9, 7.51e9],
                "pct_change": [-0.130, 0.203],
                "pts_change": [None, None],
                "direction": ["down", "up"],
                "severity": ["concerning", "concerning"],
            }).to_csv(os.path.join(tmp, "trend_signals.csv"), index=False)
            path = build_partner_brief(
                tmp, hospital_name="X", ev_multiple=8.0,
                actual_config_path=ACTUAL, benchmark_config_path=BENCH,
            )
            with open(path) as f: html = f.read()
            self.assertIn("Watchlist:", html)
            self.assertIn("2 concerning", html)

    def test_brief_colors_trend_signals_by_severity(self):
        """Favorable rows render with green badge, concerning with red badge."""
        from rcm_mc.reports._partner_brief import build_partner_brief
        with tempfile.TemporaryDirectory() as tmp:
            _seed_outdir(tmp, with_trend=False)
            # Seed with mixed severities so both colors appear
            pd.DataFrame({
                "metric": ["net_patient_revenue", "net_income"],
                "start_year": [2020, 2020],
                "end_year": [2022, 2022],
                "start_value": [5.24e9, -9.99e8],
                "end_value": [6.38e9, -1.13e9],
                "pct_change": [0.217, -0.130],
                "pts_change": [None, None],
                "direction": ["up", "down"],
                "severity": ["favorable", "concerning"],
            }).to_csv(os.path.join(tmp, "trend_signals.csv"), index=False)
            path = build_partner_brief(
                tmp, hospital_name="X", ev_multiple=8.0,
                actual_config_path=ACTUAL, benchmark_config_path=BENCH,
            )
            with open(path) as f: html = f.read()
            self.assertIn("badge-green", html)
            self.assertIn("badge-red", html)

    def test_brief_includes_pe_section_when_artifacts_present(self):
        from rcm_mc.reports._partner_brief import build_partner_brief
        with tempfile.TemporaryDirectory() as tmp:
            _seed_outdir(tmp, with_pe=True)
            path = build_partner_brief(
                tmp, hospital_name="X", ev_multiple=8.0,
                actual_config_path=ACTUAL, benchmark_config_path=BENCH,
            )
            with open(path) as f: html = f.read()
            # Headline block
            self.assertIn("PE Deal Math", html)
            self.assertIn("MOIC", html)
            self.assertIn("IRR", html)
            self.assertIn("2.55x", html)
            # Covenant block
            self.assertIn("Covenant headroom", html)
            self.assertIn("SAFE", html)
            # Bridge table has entry + exit + 3 components
            self.assertIn("Bridge step", html)
            self.assertIn("Organic EBITDA", html)
            self.assertIn("RCM uplift", html)
            self.assertIn("Multiple expansion", html)

    def test_brief_omits_pe_section_when_no_artifacts(self):
        from rcm_mc.reports._partner_brief import build_partner_brief
        with tempfile.TemporaryDirectory() as tmp:
            _seed_outdir(tmp, with_pe=False)
            path = build_partner_brief(
                tmp, hospital_name="X", ev_multiple=8.0,
                actual_config_path=ACTUAL, benchmark_config_path=BENCH,
            )
            with open(path) as f: html = f.read()
            self.assertNotIn("PE Deal Math", html)
            self.assertNotIn("Covenant headroom", html)

    def test_brief_omits_trend_block_when_signals_absent(self):
        from rcm_mc.reports._partner_brief import build_partner_brief
        with tempfile.TemporaryDirectory() as tmp:
            _seed_outdir(tmp, with_trend=False)
            path = build_partner_brief(
                tmp, hospital_name="X", ev_multiple=8.0,
                actual_config_path=ACTUAL, benchmark_config_path=BENCH,
            )
            with open(path) as f: html = f.read()
            self.assertNotIn("Multi-year trend", html)

    def test_brief_includes_peer_section_when_run(self):
        from rcm_mc.reports._partner_brief import build_partner_brief
        with tempfile.TemporaryDirectory() as tmp:
            _seed_outdir(tmp, with_peer=True)
            path = build_partner_brief(
                tmp, hospital_name="X", ev_multiple=8.0,
                actual_config_path=ACTUAL, benchmark_config_path=BENCH,
            )
            with open(path) as f: html = f.read()
            self.assertIn("Peer position", html)
            # High-percentile KPI gets the green badge
            self.assertIn("badge-green", html)

    def test_brief_includes_pressure_headline_when_present(self):
        from rcm_mc.reports._partner_brief import build_partner_brief
        with tempfile.TemporaryDirectory() as tmp:
            _seed_outdir(tmp, with_pressure=True)
            path = build_partner_brief(
                tmp, hospital_name="X", ev_multiple=8.0,
                actual_config_path=ACTUAL, benchmark_config_path=BENCH,
            )
            with open(path) as f: html = f.read()
            self.assertIn("pressure-test", html.lower())
            self.assertIn("contingent", html)

    def test_brief_handles_missing_provenance_gracefully(self):
        from rcm_mc.reports._partner_brief import build_partner_brief
        with tempfile.TemporaryDirectory() as tmp:
            _seed_outdir(tmp, with_provenance=False)
            path = build_partner_brief(
                tmp, hospital_name="X", ev_multiple=8.0,
                actual_config_path=ACTUAL, benchmark_config_path=BENCH,
            )
            with open(path) as f: html = f.read()
            # Grade band is omitted, but brief still renders other sections
            self.assertNotIn("Evidence grade", html)
            self.assertIn("EBITDA Opportunity", html)

    def test_brief_is_self_contained_html(self):
        """No <script> tags, no external asset refs — emailable single file."""
        from rcm_mc.reports._partner_brief import build_partner_brief
        with tempfile.TemporaryDirectory() as tmp:
            _seed_outdir(tmp)
            path = build_partner_brief(
                tmp, hospital_name="X", ev_multiple=8.0,
                actual_config_path=ACTUAL, benchmark_config_path=BENCH,
            )
            with open(path) as f: html = f.read()
            self.assertNotIn("<script", html)
            # No external http(s) asset refs (inline CSS only)
            self.assertNotIn("http://", html)
            # Allowed: nothing, since we don't link out anywhere that requires loading


class TestPartnerBriefCLI(unittest.TestCase):
    """End-to-end: `rcm-mc run ... --partner-brief` produces the file at top level."""

    def test_cli_partner_brief_flag_produces_top_level_html(self):
        env = os.environ.copy()
        env.setdefault("MPLCONFIGDIR", "/tmp/mplcache")
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable, "-m", "rcm_mc", "run",
                    "--actual", ACTUAL, "--benchmark", BENCH,
                    "--outdir", tmp, "--n-sims", "200", "--seed", "42",
                    "--no-report", "--partner-brief",
                ],
                cwd=str(BASE_DIR), env=env,
                capture_output=True, text=True, timeout=180,
            )
            self.assertEqual(
                result.returncode, 0,
                msg=f"STDOUT:{result.stdout[-800:]}\nSTDERR:{result.stderr[-800:]}",
            )
            # Brief stays at top-level (not in _detail/)
            brief_path = os.path.join(tmp, "partner_brief.html")
            self.assertTrue(
                os.path.exists(brief_path),
                msg=f"Missing at {brief_path}. Files: {os.listdir(tmp)}",
            )
            with open(brief_path) as f:
                html = f.read()
            # Sanity: the brief has the actual hospital name from actual.yaml
            self.assertIn("Community Hospital", html)

    def test_cli_without_flag_does_not_produce_brief(self):
        env = os.environ.copy()
        env.setdefault("MPLCONFIGDIR", "/tmp/mplcache")
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [
                    sys.executable, "-m", "rcm_mc", "run",
                    "--actual", ACTUAL, "--benchmark", BENCH,
                    "--outdir", tmp, "--n-sims", "200", "--seed", "42",
                    "--no-report",
                ],
                cwd=str(BASE_DIR), env=env,
                capture_output=True, text=True, timeout=180,
            )
            self.assertEqual(result.returncode, 0)
            self.assertFalse(os.path.exists(os.path.join(tmp, "partner_brief.html")))
            # Also check it's not in _detail/
            self.assertFalse(os.path.exists(os.path.join(tmp, "_detail", "partner_brief.html")))
