"""Workstream H (BACKLOG #10) — one demo deal rebuilt on a real named CCN.

Of the five demo.py deals, ``sth`` IS White Plains Hospital (CCN 330304):
its financial observed_metrics are the facility's filed HCRIS values,
loaded from the live vendored frame at seed time. The tests load BOTH
sides independently — the seeded DB and the HCRIS row — and assert they
match exactly, that the ENTERED→ACTUAL relabel applies to precisely the
sourced metrics (never the illustrative RCM workflow ones), and that the
provenance chip names the CCN on the deal surfaces.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import demo  # top-level demo.py seeder (path insert above)
from rcm_mc.data.hcris import _get_latest_per_ccn
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.deal_dashboard import render_deal_dashboard
from rcm_mc.ui.deal_quick_view import render_deal_quick_view

# The four metrics HCRIS genuinely files (and therefore the ONLY ones
# allowed to relabel ACTUAL on the rebuilt deal).
_SOURCED_KEYS = ("net_revenue", "bed_count", "ebitda_margin",
                 "medicare_day_pct")


def _kpi_card(html: str, label: str) -> str:
    """The rendered chunk belonging to one KPI card, so badge assertions
    are per-metric. Cards are disjoint ``<div class="ck-kpi">`` chunks;
    the last card's chunk runs to end-of-page, which is safe because the
    basis badges only render inside the cards under test."""
    for chunk in html.split('<div class="ck-kpi">'):
        if f'>{label}</div>' in chunk:
            return chunk
    raise AssertionError(f"no KPI card labelled {label!r}")


class RealCcnDemoDealTests(unittest.TestCase):
    """Seed once (the expensive real path), assert many."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        run_dir = os.path.join(cls.tmp.name, "runs")
        os.makedirs(run_dir)
        cls.db_path = os.path.join(cls.tmp.name, "p.db")
        store = PortfolioStore(cls.db_path)
        demo.seed(store, run_dir)
        with store.connect() as con:
            row = con.execute(
                "SELECT name, profile_json FROM deals WHERE deal_id = ?",
                (demo._REAL_CCN_DEAL,),
            ).fetchone()
        cls.deal_name = row["name"]
        cls.profile = json.loads(row["profile_json"])
        cls.profile["name"] = cls.deal_name
        ref = _get_latest_per_ccn()
        cls.ref = ref[ref["ccn"].astype(str) == demo._REAL_CCN].iloc[0]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    # ── Seeded values match the filing ─────────────────────────────

    def test_deal_named_for_the_real_facility(self):
        self.assertEqual(self.deal_name, str(self.ref["name"]).title())
        self.assertEqual(self.deal_name, "White Plains Hospital")
        self.assertEqual(self.profile["state"], str(self.ref["state"]))

    def test_observed_metrics_equal_hcris_row(self):
        om = self.profile["observed_metrics"]
        npr = float(self.ref["net_patient_revenue"])
        opex = float(self.ref["operating_expenses"])
        expected = {
            "net_revenue": npr,
            "bed_count": float(self.ref["beds"]),
            "ebitda_margin": round((npr - opex) / npr, 4),
            "medicare_day_pct": round(float(self.ref["medicare_day_pct"]), 4),
        }
        for key, want in expected.items():
            self.assertEqual(float(om[key]["value"]), want, key)
            # Flat copies (read by list_deals / regression / dashboard)
            # must agree with the nested sourced entry.
            self.assertEqual(float(self.profile[key]), want, key)

    def test_ccn_and_basis_recorded(self):
        self.assertEqual(str(self.profile["hcris_ccn"]), demo._REAL_CCN)
        self.assertEqual(int(self.profile["hcris_fy"]),
                         int(self.ref["fiscal_year"]))
        self.assertTrue(
            str(self.profile["metrics_basis"]).startswith("ACTUAL"))
        self.assertIn(demo._REAL_CCN, str(self.profile["metrics_basis"]))

    # ── Relabel applies to exactly the sourced metrics ─────────────

    def test_sourced_metrics_carry_hcris_source(self):
        om = self.profile["observed_metrics"]
        for key in _SOURCED_KEYS:
            self.assertEqual(om[key]["source"], "HCRIS", key)
            self.assertIn(demo._REAL_CCN, om[key]["source_detail"], key)

    def test_illustrative_rcm_metrics_stay_unsourced(self):
        # HCRIS files no denial/collection fields — those metrics must
        # NOT claim a filing source, and the basis flag stays honest.
        om = self.profile["observed_metrics"]
        for key in ("denial_rate", "days_in_ar", "net_collection_rate",
                    "clean_claim_rate", "cost_to_collect"):
            self.assertNotIn("source", om[key], key)
        self.assertEqual(self.profile["rcm_metrics_basis"],
                         "illustrative-demo")

    # ── Provenance chip + per-metric badges on the surfaces ────────

    def test_quick_view_chip_names_ccn(self):
        h = render_deal_quick_view(demo._REAL_CCN_DEAL, self.profile)
        self.assertIn("Real facility", h)
        self.assertIn("White Plains Hospital", h)
        self.assertIn(f"hcris-xray?ccn={demo._REAL_CCN}", h)
        self.assertIn(f"FY{int(self.ref['fiscal_year'])}", h)
        self.assertIn("illustrative demo values", h)

    def test_quick_view_relabels_only_sourced_cards(self):
        h = render_deal_quick_view(demo._REAL_CCN_DEAL, self.profile)
        # Sourced cards badge ACTUAL …
        self.assertIn(">ACTUAL</span>", _kpi_card(h, "Net Revenue"))
        self.assertIn(">ACTUAL</span>", _kpi_card(h, "Bed Count"))
        # … the illustrative RCM cards do not.
        self.assertNotIn(">ACTUAL</span>", _kpi_card(h, "Denial Rate"))
        self.assertNotIn(">ACTUAL</span>", _kpi_card(h, "Days in AR"))
        # The self-reported basis line survives the relabel.
        self.assertIn(">ENTERED</span>", h)

    def test_dashboard_identity_line_and_kpi_relabel(self):
        h = render_deal_dashboard(demo._REAL_CCN_DEAL, self.profile)
        self.assertIn(f"HCRIS CCN {demo._REAL_CCN}", h)
        self.assertIn(f"filed HCRIS · CCN {demo._REAL_CCN}", h)
        # Bed count + margin are filed values → ACTUAL; denial is not.
        self.assertIn(">ACTUAL</span>", _kpi_card(h, "Bed Count"))
        self.assertIn(">ACTUAL</span>", _kpi_card(h, "EBITDA Margin"))
        self.assertNotIn(">ACTUAL</span>", _kpi_card(h, "Denial Rate"))

    def test_snapshot_deal_page_names_ccn(self):
        # /deal/sth serves the snapshot-detail renderer (the demo seeds a
        # snapshot), so the identity line there must also name the CCN.
        from rcm_mc.server import ServerConfig, _render_deal_detail
        cfg = ServerConfig()
        cfg.db_path = self.db_path
        h = _render_deal_detail(cfg, demo._REAL_CCN_DEAL)
        self.assertIn(f"HCRIS CCN {demo._REAL_CCN}", h)
        self.assertIn(f"FY{int(self.ref['fiscal_year'])}", h)
        # Composite (non-rebuilt) deals must NOT claim a filing identity.
        self.assertNotIn("HCRIS CCN", _render_deal_detail(cfg, "ccf"))


class RelabelIsSourceDrivenTests(unittest.TestCase):
    """The relabel keys off per-metric provenance, not the deal — a
    partner-entered metric on the SAME deal keeps its ENTERED badge."""

    _PROFILE = {
        "name": "Mixed Basis Deal",
        "hcris_ccn": "330304", "hcris_fy": 2022,
        "observed_metrics": {
            "bed_count": {"value": 292.0, "source": "HCRIS",
                          "source_detail": "CMS HCRIS CCN 330304 FY2022",
                          "quality_flags": []},
            # Partner-entered: no filing source.
            "denial_rate": {"value": 9.9, "quality_flags": []},
        },
        "bed_count": 292.0,
        "denial_rate": 9.9,
        "ebitda_margin": 0.05,   # flat-entered, no nested source
    }

    def test_dashboard_mixed_bases(self):
        h = render_deal_dashboard("mix", self._PROFILE)
        bed = _kpi_card(h, "Bed Count")
        denial = _kpi_card(h, "Denial Rate")
        margin = _kpi_card(h, "EBITDA Margin")
        self.assertIn(">ACTUAL</span>", bed)
        self.assertIn(">ENTERED</span>", denial)
        self.assertNotIn(">ACTUAL</span>", denial)
        self.assertIn(">ENTERED</span>", margin)
        self.assertNotIn(">ACTUAL</span>", margin)

    def test_quick_view_no_chip_without_sourced_metrics(self):
        # hcris_ccn alone (no filed metrics) must not claim "Real facility".
        prof = {"name": "Bare", "hcris_ccn": "330304",
                "observed_metrics": {
                    "denial_rate": {"value": 9.9, "quality_flags": []}}}
        h = render_deal_quick_view("bare", prof)
        self.assertNotIn("Real facility", h)

    def test_quick_view_entered_deal_unchanged(self):
        # A plain partner-entered deal: no ACTUAL badges anywhere.
        prof = {"name": "Plain", "denial_rate": 11.0, "bed_count": 120}
        h = render_deal_quick_view("plain", prof)
        self.assertNotIn(">ACTUAL</span>", h)
        self.assertIn(">ENTERED</span>", h)


class PortfolioNanGuardTests(unittest.TestCase):
    """Route-walker regression: once ANY deal carries nested
    observed_metrics (the real-CCN deal does), _expand_profiles adds
    every profile-metric column — possibly all-empty. mean() of an empty
    column is NaN, which is truthy and not None, so /portfolio rendered
    a literal 'nan' in the Avg Denial / Avg Days-in-AR KPIs."""

    def test_portfolio_kpis_never_render_nan(self):
        import pandas as pd
        from rcm_mc.ui.portfolio_overview import render_portfolio_overview
        deals = pd.DataFrame([
            {"deal_id": "real", "name": "White Plains Hospital",
             "created_at": "2026-01-01", "net_revenue": 8.8e8,
             "observed_metrics": {
                 "net_revenue": {"value": 8.8e8, "source": "HCRIS"}}},
            {"deal_id": "other", "name": "Other",
             "created_at": "2026-01-01", "net_revenue": 2.0e8,
             "observed_metrics": None},
        ])
        h = render_portfolio_overview(deals, None)
        self.assertNotIn(">nan<", h)
        self.assertNotIn("nan%", h)


if __name__ == "__main__":
    unittest.main()
