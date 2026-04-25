"""Tests for saved_analyses templates — the time-saver feature.

Partner saves a (name, route, params) triple; one click relaunches
it. Core ergonomic loop for repeated diligence runs.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest


class TestSavedAnalysesStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_and_list_roundtrip(self):
        from rcm_mc.analysis.saved_analyses import (
            save_template, list_templates,
        )
        tid = save_template(
            self.store,
            name="My HCRIS scan",
            route="/diligence/hcris-xray",
            params={"ccn": "010001"},
            description="CCN 010001, weekly",
            created_by="partner",
        )
        self.assertGreater(tid, 0)

        out = list_templates(self.store)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["name"], "My HCRIS scan")
        self.assertEqual(out[0]["route"], "/diligence/hcris-xray")
        self.assertEqual(out[0]["params"], {"ccn": "010001"})
        self.assertEqual(out[0]["run_count"], 0)

    def test_resolved_href_encodes_params(self):
        from rcm_mc.analysis.saved_analyses import resolved_href
        t = {"route": "/diligence/hcris-xray",
             "params": {"ccn": "010001"}}
        self.assertEqual(resolved_href(t),
                         "/diligence/hcris-xray?ccn=010001")

    def test_resolved_href_merges_with_existing_query(self):
        """If the route already has a `?`, params should join with `&`."""
        from rcm_mc.analysis.saved_analyses import resolved_href
        t = {"route": "/x?a=1", "params": {"b": "2"}}
        self.assertEqual(resolved_href(t), "/x?a=1&b=2")

    def test_resolved_href_empty_params(self):
        from rcm_mc.analysis.saved_analyses import resolved_href
        t = {"route": "/foo", "params": {}}
        self.assertEqual(resolved_href(t), "/foo")

    def test_save_rejects_non_local_route(self):
        """Open-redirect prevention: route must be a local path."""
        from rcm_mc.analysis.saved_analyses import save_template
        with self.assertRaises(ValueError):
            save_template(self.store, name="x",
                          route="https://evil.com")
        with self.assertRaises(ValueError):
            save_template(self.store, name="x",
                          route="//evil.com")

    def test_save_rejects_empty_name(self):
        from rcm_mc.analysis.saved_analyses import save_template
        with self.assertRaises(ValueError):
            save_template(self.store, name="", route="/foo")
        with self.assertRaises(ValueError):
            save_template(self.store, name="   ", route="/foo")

    def test_delete_template(self):
        from rcm_mc.analysis.saved_analyses import (
            save_template, delete_template, list_templates,
        )
        tid = save_template(self.store, name="Drop me",
                            route="/x", params={"k": "v"})
        self.assertTrue(delete_template(self.store, tid))
        self.assertEqual(list_templates(self.store), [])
        # Second delete returns False (already gone)
        self.assertFalse(delete_template(self.store, tid))

    def test_bump_run_updates_counter(self):
        from rcm_mc.analysis.saved_analyses import (
            save_template, bump_run, list_templates,
        )
        tid = save_template(self.store, name="t", route="/x")
        bump_run(self.store, tid)
        bump_run(self.store, tid)
        bump_run(self.store, tid)
        out = list_templates(self.store)
        self.assertEqual(out[0]["run_count"], 3)
        self.assertIsNotNone(out[0]["last_run_at"])

    def test_pinned_templates_sort_first(self):
        from rcm_mc.analysis.saved_analyses import (
            save_template, list_templates,
        )
        save_template(self.store, name="A", route="/a")
        save_template(self.store, name="B", route="/b", pinned=True)
        save_template(self.store, name="C", route="/c")
        out = list_templates(self.store)
        # B is pinned so it comes first
        self.assertEqual(out[0]["name"], "B")


class TestDashboardSurface(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        from rcm_mc.portfolio.store import PortfolioStore
        self.store = PortfolioStore(self.db)

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_templates_no_card(self):
        """Empty state → no 'Your templates' card at all (don't
        add vertical space for a feature the partner hasn't used)."""
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertNotIn("Your templates", html)

    def test_save_button_appears_on_each_curated_analysis(self):
        """Every row in 'What you can run' carries a ★ Save button —
        the only in-browser way to create a template before this fix.
        Regression guard: 10 curated analyses → 10 save forms in
        the rendered HTML."""
        from rcm_mc.ui.dashboard_page import (
            render_dashboard, _CURATED_ANALYSES,
        )
        html = render_dashboard(self.db)
        # Each save form posts to /api/saved-analyses; count those.
        save_forms = html.count('action="/api/saved-analyses"')
        # Should be at least 1 per curated analysis (only +0 because
        # there's no other render path that posts there).
        self.assertGreaterEqual(
            save_forms, len(_CURATED_ANALYSES),
            msg=f"expected ≥{len(_CURATED_ANALYSES)} save forms "
                f"(one per curated analysis), got {save_forms}",
        )
        # Hint copy in the section header
        self.assertIn("click ★ to save as template", html)

    def test_template_renders_with_launch_link(self):
        from rcm_mc.analysis.saved_analyses import save_template
        save_template(self.store, name="Weekly HCRIS",
                      route="/diligence/hcris-xray",
                      params={"ccn": "010001"},
                      description="Routine Monday")
        from rcm_mc.ui.dashboard_page import render_dashboard
        html = render_dashboard(self.db)
        self.assertIn("Your templates", html)
        self.assertIn("Weekly HCRIS", html)
        # Launch link targets the /api/saved-analyses/<id>/run path
        self.assertIn("/api/saved-analyses/", html)
        self.assertIn("/run", html)


if __name__ == "__main__":
    unittest.main()
