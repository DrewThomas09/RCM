"""Test the editorial /my/<owner> renderer.

Cycle 15 ports `_route_my_dashboard` from a legacy inline `shell()`
implementation to the chartis editorial chrome — italic-serif intro,
pulse strip (5 KPI blocks), health-mix bar, ck_severity_panel
for alerts + deadlines, editorial deals table, ck_affirm_empty for
each empty section. These tests pin the chrome on each rendered
state — empty (no deals, no alerts, no deadlines) and populated.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.ui.my_dashboard_page import render_my_dashboard


def _fresh_store() -> PortfolioStore:
    db = os.path.join(tempfile.mkdtemp(prefix="my_dash_"), "p.db")
    return PortfolioStore(db)


class MyDashboardEditorialChromeTests(unittest.TestCase):
    def test_empty_state_renders_intro_pulse_and_three_affirm_bands(self):
        html = render_my_dashboard(store=_fresh_store(), owner="alice")
        # 2026-05-28 sweep batch 19 · /my/<owner> migrated to the
        # universal ck_editorial_head helper. The eyebrow text and
        # italic emphasis are preserved; the wrapper class changed
        # from ck-section-intro to ck-eh.
        self.assertIn('class="ck-eh"', html)
        self.assertIn("PARTNER · ALICE", html)
        # Italic-first-phrase is the deck phrase "Your week, in one
        # read." — preserves the "week" emphasis the old test pinned.
        self.assertIn("Your week, in one read.", html)
        # Pulse strip — 5 KPI blocks always rendered
        self.assertIn("ck-pulse-grid", html)
        self.assertIn(">My Deals</div>", html)
        self.assertIn(">Red Alerts</div>", html)
        self.assertIn(">Amber Alerts</div>", html)
        self.assertIn(">Overdue Deadlines</div>", html)
        self.assertIn(">Upcoming Deadlines</div>", html)
        # Three empty-state affirm bands (alerts, deadlines, deals)
        self.assertIn("No active alerts on your deals", html)
        self.assertIn("No deadlines assigned", html)
        self.assertIn("No deals currently assigned", html)

    def test_pulse_kpis_show_zero_counts_when_nothing_active(self):
        # Zeros across the pulse strip are a signal worth showing,
        # not a gap to hide. Locate the pulse block by its class
        # substring and confirm at least one ">0<" appears in it.
        html = render_my_dashboard(store=_fresh_store(), owner="alice")
        start = html.index("ck-pulse-grid")
        end = html.index('</div>', html.index('Upcoming Deadlines', start))
        block = html[start:end]
        self.assertIn(">0<", block)

    def test_breadcrumbs_render(self):
        html = render_my_dashboard(store=_fresh_store(), owner="alice")
        self.assertIn('class="ck-breadcrumbs"', html)
        # Two crumbs: Home (anchor) + My Work (text)
        self.assertIn('href="/"', html)
        self.assertIn("My Work", html)

    def test_subtitle_pluralizes_correctly(self):
        # 0 deals, 0 alerts, 0 overdue, 0 upcoming → "0 deals · 0 alerts"
        html = render_my_dashboard(store=_fresh_store(), owner="alice")
        # Subtitle is rendered by chartis_shell as `ck-subtitle` div
        # Fragments rather than the whole string for resilience to
        # whitespace.
        self.assertIn("0 deals", html)
        self.assertIn("0 alerts", html)
        self.assertIn("0 overdue", html)
        self.assertIn("0 upcoming", html)

    def test_owner_with_no_deals_shows_browse_corpus_cta(self):
        html = render_my_dashboard(store=_fresh_store(), owner="alice")
        # The deals affirm-empty band offers a CTA to /library
        self.assertIn('href="/library"', html)
        self.assertIn("Browse deal corpus", html)

    def test_alerts_empty_state_links_back_to_alerts(self):
        html = render_my_dashboard(store=_fresh_store(), owner="alice")
        # The alerts affirm-empty band offers a CTA to /alerts
        self.assertIn('href="/alerts"', html)
        self.assertIn("View portfolio alerts", html)

    def test_owned_deal_with_no_snapshot_renders_affirm_band_and_count(self):
        # Seed a deal owned by alice but no portfolio snapshot — the
        # renderer hits the "owned deals, no snapshots yet" branch
        # (between the populated table and the empty-no-deals band).
        # That branch is what a partner sees the moment after they
        # take ownership of a deal but before running an analysis.
        from rcm_mc.deals.deal_owners import assign_owner
        store = _fresh_store()
        store.upsert_deal("hca-001")
        assign_owner(store, deal_id="hca-001", owner="alice")
        html = render_my_dashboard(store=store, owner="alice")
        # Pulse strip reflects the owned deal
        self.assertIn(">My Deals</div>", html)
        # The affirm-empty band names the count and offers a CTA
        # back to /analysis so partner has the next step.
        self.assertIn("1 deal owned, no snapshots yet", html)
        self.assertIn('href="/analysis"', html)


if __name__ == "__main__":
    unittest.main()
