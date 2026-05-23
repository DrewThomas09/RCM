"""Reusable US state tile-grid map renderer (rcm_mc.ui.us_map).

Local/static SVG cartogram — no external map tiles, no CDN, no network.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.us_map import _TILE, STATE_NAMES, render_us_state_map


class TileGridIntegrityTests(unittest.TestCase):
    def test_all_states_plus_dc_present_and_unique(self):
        self.assertEqual(len(_TILE), 51)                  # 50 + DC
        self.assertEqual(len(set(_TILE.values())), 51)    # no overlapping cells
        # every tile has a display name
        for abbr in _TILE:
            self.assertIn(abbr, set(STATE_NAMES) | {"DC"})


class RendererTests(unittest.TestCase):
    def setUp(self):
        self.html = render_us_state_map(
            {"CA": 12, "TX": 7, "NY": 3},
            metric_label="deals",
            accent_states=["NY"], accent_label="CON state",
            empty_message="none",
        )

    def test_emits_svg_with_state_cells(self):
        self.assertIn("<svg", self.html)
        # one cell per state (accent class appends, so count the data attr)
        self.assertEqual(self.html.count('data-state="'), 51)

    def test_accessible_labels(self):
        self.assertIn('role="img"', self.html)
        self.assertIn('aria-label="California: 12 deals', self.html)
        self.assertIn("<title>", self.html)

    def test_legend_present(self):
        self.assertIn("usm-legend", self.html)
        self.assertIn("deals", self.html)

    def test_metric_shading_is_relative(self):
        # The max value (CA=12) should get a deeper teal than the min (NY=3).
        self.assertIn("rgba(21,87,82,", self.html)  # teal ramp used

    def test_accent_outline(self):
        self.assertIn("usm-accent", self.html)
        self.assertIn("CON state", self.html)

    def test_no_external_map_script_or_cdn(self):
        low = self.html.lower()
        for bad in ("mapbox", "maps.googleapis", "leaflet", "cdn.",
                    "http://", "https://"):
            self.assertNotIn(bad, low)

    def test_empty_state_still_draws_map(self):
        h = render_us_state_map(
            {}, metric_label="deals",
            empty_message="No state-level portfolio data is available yet.")
        self.assertEqual(h.count('data-state="'), 51)   # map still drawn
        self.assertIn("No state-level portfolio data is available yet", h)
        # no invented data: nothing clickable when there are no values
        self.assertNotIn('data-clickable="1"', h)

    def test_unknown_states_ignored_not_invented(self):
        # A bogus abbreviation must not create a cell or crash.
        h = render_us_state_map({"ZZ": 99, "CA": 1}, metric_label="deals")
        self.assertEqual(h.count('data-state="'), 51)
        self.assertNotIn('data-state="ZZ"', h)


class GeographyAuditDocTests(unittest.TestCase):
    def test_audit_doc_exists_and_lists_inspected_routes(self):
        import pathlib
        doc = (pathlib.Path(__file__).resolve().parents[1]
               / "docs" / "PEDESK_INTERACTIVE_MAPS.md")
        self.assertTrue(doc.exists())
        text = doc.read_text(encoding="utf-8")
        self.assertIn("Geography data audit", text)
        for route in ("/portfolio/map", "/market-data/map",
                      "/rcm-benchmarks", "/payer-intelligence"):
            self.assertIn(route, text)
        # honest data-gap notes for the blocked phases
        self.assertIn("no county FIPS", text)
        self.assertIn("no latitude/longitude", text)


class StateLinkTemplateTests(unittest.TestCase):
    def test_link_template_adds_drilldown_href(self):
        h = render_us_state_map(
            {"CA": 5, "TX": 3}, metric_label="hospitals",
            state_link_template="/market-data/state/{state}")
        self.assertIn('data-href="/market-data/state/CA"', h)
        self.assertIn("window.location.href=href", h)   # JS navigates
        self.assertIn('tabindex="0"', h)                  # keyboard-focusable

    def test_no_template_keeps_select_behavior(self):
        h = render_us_state_map({"CA": 5}, metric_label="x")
        self.assertNotIn('data-href="/', h)               # no cell hrefs
        self.assertIn("us-map-select", h)                  # selection event kept

    def test_only_states_with_data_are_linked(self):
        # A state with no metric value is not navigable (no invented link).
        h = render_us_state_map(
            {"CA": 5}, metric_label="x",
            state_link_template="/market-data/state/{state}")
        self.assertIn('data-href="/market-data/state/CA"', h)
        self.assertNotIn('data-href="/market-data/state/WY"', h)


if __name__ == "__main__":
    unittest.main()
