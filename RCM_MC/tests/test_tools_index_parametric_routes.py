"""Pin: parametric bare-slug routes don't leak into /tools as
dead-end orphan entries.

Three parametric routes used to appear in /tools as bare slugs:
  /my, /market-data/state, /pipeline/stage

Clicking any of them would 404 because the handler requires a
trailing parameter (username / state code / ccn). Two of them have
curated palette siblings (/my/AT, /market-data/state/CA) that
resolve cleanly; /pipeline/stage is POST-only and shouldn't appear
at all.

Guard: bare slugs must be hidden, curated variants must remain in
the palette so partners still have a working jump-target.
"""
from __future__ import annotations

import unittest


class ToolsHiddenRoutesTests(unittest.TestCase):
    def test_my_bare_slug_hidden(self):
        from rcm_mc.server import RCMHandler
        self.assertIn("/my", RCMHandler._TOOLS_HIDDEN_ROUTES)

    def test_market_data_state_bare_slug_hidden(self):
        from rcm_mc.server import RCMHandler
        self.assertIn(
            "/market-data/state", RCMHandler._TOOLS_HIDDEN_ROUTES,
        )

    def test_pipeline_stage_bare_slug_hidden(self):
        from rcm_mc.server import RCMHandler
        self.assertIn(
            "/pipeline/stage", RCMHandler._TOOLS_HIDDEN_ROUTES,
        )

    def test_curated_my_palette_entry_still_present(self):
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/my/AT", routes)

    def test_curated_market_state_palette_entry_present(self):
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/market-data/state/CA", routes)


class DiscoveredRoutesFilterTests(unittest.TestCase):
    """The /tools index runs ``_discover_all_routes()`` which parses
    server.py for every `path == "/X"` and `path.startswith("/X/")`
    string and then filters through ``_TOOLS_HIDDEN_ROUTES``. Verify
    the three parametric bare slugs are filtered out."""

    def test_discovered_routes_exclude_parametric_bare_slugs(self):
        from rcm_mc.server import RCMHandler
        # Reset the per-class cache so the discovery runs fresh
        # against the current source — required when test ordering
        # leaves a stale cache from a different test.
        RCMHandler._CACHED_ROUTES = None
        discovered = RCMHandler._discover_all_routes()
        for bare in ("/my", "/market-data/state", "/pipeline/stage"):
            self.assertNotIn(
                bare, discovered,
                f"{bare!r} should be filtered out — it 404s when "
                f"clicked from /tools",
            )


if __name__ == "__main__":
    unittest.main()
