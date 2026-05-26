"""CMS X-Ray must resolve the Target Screener's vertical keys.

The screener links every provider row to /diligence/xray?ccn=&vertical=,
passing loader-style keys (hospitals, home_health, snf, irf, ltch). The
resolver's canonical sector ids are hyphenated CMS-compare names, so without
an alias map five of seven verticals fell back to the search page instead of a
real report. This pins that every screener vertical resolves a CCN to a report.
"""
from __future__ import annotations

import unittest


class XRayVerticalAliasTests(unittest.TestCase):
    def _first_ccn(self, vertical):
        from rcm_mc.ui.target_screener_page import _vertical_rows
        rows = _vertical_rows(vertical)
        return rows[0]["ccn"] if rows else None

    def test_every_screener_vertical_resolves_by_ccn(self):
        from rcm_mc.data.provider_xray import provider_match_by_ccn
        for v in ("hospitals", "home_health", "hospice", "snf",
                  "dialysis", "irf", "ltch"):
            ccn = self._first_ccn(v)
            self.assertIsNotNone(ccn, v)
            self.assertIsNotNone(provider_match_by_ccn(ccn, v),
                                 f"{v} CCN {ccn} did not resolve in X-Ray")

    def test_xray_page_renders_resolved_report_not_search(self):
        from rcm_mc.ui.provider_xray_page import render_provider_xray
        for v in ("home_health", "snf", "irf", "ltch"):  # the previously-broken set
            ccn = self._first_ccn(v)
            h = render_provider_xray({"ccn": ccn, "vertical": v})
            self.assertIn(f"CCN {ccn}", h, f"{v} X-Ray did not resolve to a report")

    def test_alias_map_covers_the_mismatched_keys(self):
        from rcm_mc.data.provider_xray import _VERTICAL_ALIASES, SECTOR_BY_ID
        for alias, canonical in _VERTICAL_ALIASES.items():
            self.assertTrue(canonical in SECTOR_BY_ID or canonical == "hospital",
                            f"{alias}→{canonical} is not a real sector id")


if __name__ == "__main__":
    unittest.main()
