"""Tests for the IFT suite hub (/ift) — the index page added in the
2026-07-10 rehaul."""
import unittest

from rcm_mc.ui.ift_hub_page import render_ift_hub, _SURFACES


class HubTests(unittest.TestCase):
    def test_renders_all_surfaces(self):
        h = render_ift_hub()
        for route, title, _job, _notfor in _SURFACES:
            self.assertIn(f'href="{route}"', h)
        self.assertEqual(h.count("NOT here"), len(_SURFACES))

    def test_data_assets_linked(self):
        h = render_ift_hub()
        for asset in ("/api/ift/markets.xlsx", "/api/ift/demand.xlsx",
                      "/api/ift/mmt.json", "/connector-estate"):
            self.assertIn(asset, h)

    def test_never_raises_with_qs(self):
        self.assertTrue(render_ift_hub({"x": ["1"]}))


if __name__ == "__main__":
    unittest.main()
