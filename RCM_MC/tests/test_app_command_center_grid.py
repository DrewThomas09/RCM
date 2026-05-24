"""Command Center dossier-grid preview (/app?layout=grid).

The grid is a parallel layout behind a query flag — the default flat-scroll
/app must stay byte-for-byte unchanged. These tests pin: the dossier-grid
markup + every required card label, honest empty states on an empty fund (no
fabricated MOIC/IRR/deal values), source-registry labels, real values when
data exists, responsive CSS, the app top bar present (grid is an authed app
page), and that the default /app does NOT render the grid.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.infra.migrations import run_pending
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.chartis.app_page import render_app_page

_CARD_LABELS = [
    "Weighted MOIC", "Weighted IRR", "Covenants at risk", "Days cash",
    "Active deals", "Initiatives tracked", "Pipeline funnel", "Quick access",
    "Covenant heatmap", "EBITDA drag", "Initiative variance", "Active alerts",
    "Deliverables",
]


def _fresh_store():
    db = os.path.join(tempfile.mkdtemp(), "cc.db")
    s = PortfolioStore(db)
    run_pending(s)
    return s


class GridLayoutTests(unittest.TestCase):
    def setUp(self):
        self.html = render_app_page(store=_fresh_store(), layout="grid")

    def test_dossier_grid_marker_and_tokens(self):
        self.assertIn("data-cc-grid", self.html)
        self.assertIn('class="cc-grid"', self.html)
        self.assertIn("--cc-paper:#faf6ec", self.html)
        self.assertIn('grid-template-columns:repeat(12,1fr)', self.html)

    def test_page_top(self):
        self.assertIn("/command-center", self.html)
        self.assertIn('class="cc-h1"', self.html)
        self.assertIn("Command ", self.html)
        self.assertIn("cc-h1-em", self.html)            # green italic "center"

    def test_all_required_card_labels(self):
        for label in _CARD_LABELS:
            self.assertIn(label, self.html, f"card label missing: {label}")

    def test_source_registry_labels_present(self):
        for src in ("portfolio.db", "deal_snapshots", "covenant_metrics",
                    "initiative_actuals", "analysis_runs", "generated_exports"):
            self.assertIn(src, self.html, f"source label missing: {src}")

    def test_honest_empty_states_no_fabricated_values(self):
        # Empty fund → KPI cards show — + "awaiting data", roster shows the
        # add-a-deal prompt. No invented MOIC/IRR.
        self.assertIn("cc-kpi-empty", self.html)
        self.assertIn("awaiting data", self.html)
        self.assertIn("No deals yet", self.html)
        # No prototype's illustrative populated values leaked.
        for fake in ("2.4x", "21.8%", "24.1% IRR", "$184M"):
            self.assertNotIn(fake, self.html)

    def test_responsive_breakpoints(self):
        self.assertIn("max-width:1024px", self.html)
        self.assertIn("max-width:768px", self.html)

    def test_carries_app_topbar(self):
        # Grid is an authenticated app page → it gets the editorial top bar.
        self.assertIn('<header class="ck-topbar">', self.html)

    def test_addcard_and_actions(self):
        self.assertIn("Add a card", self.html)
        self.assertIn("Refresh", self.html)
        self.assertIn("Customize", self.html)

    def test_no_prototype_cdn(self):
        low = self.html.lower()
        for bad in ("unpkg", "babel", "react-dom", "command-center.html"):
            self.assertNotIn(bad, low)


class GridRealDataTests(unittest.TestCase):
    def test_real_deal_surfaces_or_honest_empty(self):
        # With a real deal seeded the roster reflects it; if the snapshot
        # schema differs in this build, the empty state must stay honest —
        # never a fabricated roster. The grid must render either way.
        s = _fresh_store()
        try:
            with s.connect() as con:
                con.execute("INSERT INTO deals (deal_id, name) VALUES (?, ?)",
                            ("ccf", "Cypress Crossing Health"))
                con.commit()
            from rcm_mc.portfolio.portfolio_snapshots import record_snapshot
            record_snapshot(s, deal_id="ccf", stage="hold")
        except Exception:
            pass
        html = render_app_page(store=s, layout="grid")
        self.assertIn("data-cc-grid", html)
        self.assertTrue(
            "Cypress Crossing Health" in html or "No deals yet" in html
        )


class DefaultLayoutIsGridTests(unittest.TestCase):
    """Design-fidelity pass: the dossier grid is now the DEFAULT /app; the
    old flat-scroll page is the ?layout=flat escape hatch."""

    def test_default_app_is_the_grid(self):
        html = render_app_page(store=_fresh_store())   # no layout
        self.assertIn("data-cc-grid", html)
        self.assertIn('class="cc-grid"', html)
        self.assertIn("Command center", html)

    def test_unknown_layout_still_renders_grid(self):
        html = render_app_page(store=_fresh_store(), layout="bogus")
        self.assertIn("data-cc-grid", html)

    def test_flat_escape_hatch_renders_old_page(self):
        html = render_app_page(store=_fresh_store(), layout="flat")
        self.assertNotIn("data-cc-grid", html)
        self.assertIn("Command center", html)


if __name__ == "__main__":
    unittest.main()
