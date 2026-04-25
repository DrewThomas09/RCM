"""Tests for the Portfolio Pulse hero — the wow-moment top-of-
dashboard card that synthesizes total EV + health + MOIC + the
single most-striking aggregate signal across the portfolio.

(Distinct from the earlier B144 ``test_portfolio_pulse.py`` which
tests a one-line summary; this covers the full hero section.)
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone


def _seed_deals(db_path: str, deals: list) -> None:
    """Insert minimal deal rows. Sector/stage live in profile_json,
    not as columns on the deals table — fold them in here so each
    test fixture only specifies the deal-shape it cares about."""
    from rcm_mc.portfolio.store import PortfolioStore
    store = PortfolioStore(db_path)
    store.init_db()
    with store.connect() as con:
        for d in deals:
            profile = dict(d.get("profile", {}))
            profile.setdefault("sector", d.get("sector", "hospital"))
            profile.setdefault("stage", d.get("stage", "hold"))
            con.execute(
                "INSERT INTO deals (deal_id, name, created_at, "
                "profile_json) VALUES (?, ?, ?, ?)",
                (d["deal_id"], d["name"],
                 datetime.now(timezone.utc).isoformat(),
                 json.dumps(profile)),
            )
        con.commit()


class TestPulseInputs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "p.db")
        _seed_deals(self.db, [
            {"deal_id": "D1", "name": "One",
             "profile": {"ev_mm": 200}},
            {"deal_id": "D2", "name": "Two",
             "profile": {"ev_mm": 450}},
            {"deal_id": "D3", "name": "Three",
             "profile": {"ev_mm": 1200}},
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def test_aggregates_ev_and_health(self):
        from rcm_mc.ui.dashboard_page import _portfolio_pulse_inputs
        scan = [
            {"deal_id": "D1", "name": "One", "score": 80,
             "band": "great", "covenant_status": "SAFE",
             "alerts": 0, "snap_age_days": 1, "open_deadlines": 0,
             "overdue_deadlines": 0, "chain": "", "chain_size": 0,
             "quality_rating": 5, "hrrp_pct": None,
             "sector": "hospital"},
            {"deal_id": "D2", "name": "Two", "score": 60,
             "band": "good", "covenant_status": "SAFE",
             "alerts": 0, "snap_age_days": 1, "open_deadlines": 0,
             "overdue_deadlines": 0, "chain": "", "chain_size": 0,
             "quality_rating": 4, "hrrp_pct": None,
             "sector": "hospital"},
            {"deal_id": "D3", "name": "Three", "score": 40,
             "band": "fair", "covenant_status": "SAFE",
             "alerts": 0, "snap_age_days": 1, "open_deadlines": 0,
             "overdue_deadlines": 0, "chain": "", "chain_size": 0,
             "quality_rating": 3, "hrrp_pct": None,
             "sector": "hospital"},
        ]
        out = _portfolio_pulse_inputs(self.db, deals=scan)
        self.assertEqual(out["n_deals"], 3)
        self.assertAlmostEqual(out["total_ev_mm"], 1850.0, places=1)
        self.assertEqual(out["avg_health"], 60.0)
        self.assertEqual(out["band_counts"]["great"], 1)
        self.assertEqual(out["band_counts"]["good"], 1)
        self.assertEqual(out["band_counts"]["fair"], 1)
        self.assertEqual(out["band_counts"]["poor"], 0)
        self.assertEqual(len(out["deal_tiles"]), 3)


class TestHrrpExposureSynthesis(unittest.TestCase):
    """When 2+ deals carry HRRP penalties, the synthesis line should
    fire with a $-quantified EBITDA-at-risk figure."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "p.db")
        _seed_deals(self.db, [
            {"deal_id": "H1", "name": "Hosp 1",
             "profile": {"ev_mm": 200}},
            {"deal_id": "H2", "name": "Hosp 2",
             "profile": {"ev_mm": 200}},
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def test_hrrp_dollarized(self):
        from rcm_mc.ui.dashboard_page import _portfolio_pulse_inputs
        scan = [
            {"deal_id": "H1", "name": "Hosp 1", "score": 70,
             "band": "good", "covenant_status": "SAFE",
             "alerts": 0, "snap_age_days": 1, "open_deadlines": 0,
             "overdue_deadlines": 0, "chain": "", "chain_size": 0,
             "quality_rating": 4, "hrrp_pct": 3.0,
             "sector": "hospital"},
            {"deal_id": "H2", "name": "Hosp 2", "score": 65,
             "band": "good", "covenant_status": "SAFE",
             "alerts": 0, "snap_age_days": 1, "open_deadlines": 0,
             "overdue_deadlines": 0, "chain": "", "chain_size": 0,
             "quality_rating": 4, "hrrp_pct": 2.5,
             "sector": "hospital"},
        ]
        out = _portfolio_pulse_inputs(self.db, deals=scan)
        self.assertEqual(out["n_hrrp_exposed"], 2)
        # 200 * 0.10 * 0.0030 * 3.0 + 200 * 0.10 * 0.0030 * 2.5
        # = 0.18 + 0.15 = 0.33
        self.assertAlmostEqual(out["hrrp_exposure_mm"], 0.33,
                               places=2)
        self.assertIn("2 portfolio hospitals",
                      out["headline_synthesis"])


class TestCovenantSynthesis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "p.db")
        _seed_deals(self.db, [
            {"deal_id": "C1", "name": "Cov 1",
             "profile": {"ev_mm": 100}},
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def test_tripped_covenant_synthesis(self):
        """No HRRP exposure → covenant line wins."""
        from rcm_mc.ui.dashboard_page import _portfolio_pulse_inputs
        scan = [{
            "deal_id": "C1", "name": "Cov 1", "score": 40,
            "band": "poor", "covenant_status": "TRIPPED",
            "alerts": 0, "snap_age_days": 1, "open_deadlines": 0,
            "overdue_deadlines": 0, "chain": "", "chain_size": 0,
            "quality_rating": None, "hrrp_pct": None,
            "sector": "hospital",
        }]
        out = _portfolio_pulse_inputs(self.db, deals=scan)
        self.assertIn("TRIPPED covenant", out["headline_synthesis"])


class TestRenderPortfolioPulseHero(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "p.db")
        _seed_deals(self.db, [
            {"deal_id": "X1", "name": "Alpha Hospital",
             "profile": {"ev_mm": 800}},
            {"deal_id": "X2", "name": "Beta Hospital",
             "profile": {"ev_mm": 200}},
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def test_renders_with_deals(self):
        from rcm_mc.ui.dashboard_page import _render_portfolio_pulse_hero
        scan = [
            {"deal_id": "X1", "name": "Alpha Hospital", "score": 85,
             "band": "great", "covenant_status": "SAFE",
             "alerts": 0, "snap_age_days": 1, "open_deadlines": 0,
             "overdue_deadlines": 0, "chain": "", "chain_size": 0,
             "quality_rating": 5, "hrrp_pct": None,
             "sector": "hospital"},
            {"deal_id": "X2", "name": "Beta Hospital", "score": 55,
             "band": "fair", "covenant_status": "SAFE",
             "alerts": 0, "snap_age_days": 1, "open_deadlines": 0,
             "overdue_deadlines": 0, "chain": "", "chain_size": 0,
             "quality_rating": 3, "hrrp_pct": None,
             "sector": "hospital"},
        ]
        html = _render_portfolio_pulse_hero(self.db, deals=scan)
        self.assertIn("Portfolio pulse", html)
        # Total EV: 800 + 200 = $1.00B compact
        self.assertIn("$1.00B", html)
        self.assertIn("/deal/X1", html)
        self.assertIn("/deal/X2", html)
        self.assertIn("wc-pulse-dot", html)
        self.assertIn("synthesis you'd miss", html)

    def test_empty_returns_empty(self):
        """No deals → hero hidden so the dashboard doesn't render an
        empty gradient block."""
        from rcm_mc.ui.dashboard_page import _render_portfolio_pulse_hero
        tmp = tempfile.TemporaryDirectory()
        try:
            db = os.path.join(tmp.name, "p.db")
            from rcm_mc.portfolio.store import PortfolioStore
            PortfolioStore(db).init_db()
            html = _render_portfolio_pulse_hero(db, deals=[])
            self.assertEqual(html, "")
        finally:
            tmp.cleanup()


class TestMoneyFormatter(unittest.TestCase):
    def test_compact_units(self):
        from rcm_mc.ui.dashboard_page import _format_money_compact
        self.assertEqual(_format_money_compact(1840), "$1.84B")
        self.assertEqual(_format_money_compact(320), "$320M")
        self.assertEqual(_format_money_compact(0.5), "$500K")
        self.assertEqual(_format_money_compact(None), "—")

    def test_band_color(self):
        from rcm_mc.ui.dashboard_page import _band_color
        self.assertEqual(_band_color("great"), "#10b981")
        self.assertEqual(_band_color("good"), "#3b82f6")
        self.assertEqual(_band_color("fair"), "#f59e0b")
        self.assertEqual(_band_color("poor"), "#ef4444")
        self.assertEqual(_band_color("unknown"), "#9ca3af")


class TestDashboardIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "p.db")
        _seed_deals(self.db, [
            {"deal_id": "I1", "name": "Integration One",
             "profile": {"ev_mm": 300}},
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def test_pulse_appears_above_sharpest_insight(self):
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn("Portfolio pulse", html)
        pulse_idx = html.find("Portfolio pulse")
        sharpest_idx = html.find("Sharpest insight")
        # Hero must precede the legacy headline strip when both render.
        if sharpest_idx > -1:
            self.assertLess(pulse_idx, sharpest_idx)


if __name__ == "__main__":
    unittest.main()
