"""HCRIS X-Ray results — A v2 · Headline lead (handoff design_handoff_xray).

The results page now leads with a top-finding hero computed from the engine's
own most-material real deviation (top unfavorable, else top favorable, else an
honest in-band state), rendered with the shared xray_kit peer-band box-plot.
The existing data-accurate report is preserved beneath it; nothing fabricated.
"""
from __future__ import annotations

import unittest

from rcm_mc.data.hcris import _get_latest_per_ccn
from rcm_mc.ui.hcris_xray_page import render_hcris_xray_page


def _a_ccn() -> str:
    return str(_get_latest_per_ccn().iloc[0]["ccn"])


class HeadlineResultsTests(unittest.TestCase):
    def setUp(self):
        self.html = render_hcris_xray_page(qs={"ccn": [_a_ccn()]})

    def test_top_finding_hero_leads(self):
        self.assertIn("xr-topfind", self.html)
        self.assertIn("Top finding", self.html)
        # The hero appears before the full benchmark panel (inverted pyramid).
        i_hero = self.html.find("xr-topfind")
        i_bench = self.html.find("Peer benchmark")
        self.assertTrue(0 < i_hero < i_bench)

    def test_hero_uses_kit_peer_band(self):
        self.assertIn("xr-topfind-band", self.html)
        self.assertIn("xr-band", self.html)          # kit box-plot
        self.assertIn("--xr-red:#b14a3a", self.html)  # kit vars resolve (.xr scope)
        self.assertIn("hx-wrap xr", self.html)

    def test_hero_is_honest_not_a_recommendation(self):
        self.assertIn("peer deviation, not a recommendation", self.html)
        self.assertIn("CMS HCRIS", self.html)

    def test_existing_report_preserved(self):
        # The rich engine report still renders beneath the hero.
        self.assertIn("Peer roster", self.html)
        self.assertGreater(len(self.html), 8000)

    def test_no_external_scripts(self):
        low = self.html.lower()
        for bad in ("unpkg", "react", "babel", "cdn.jsdelivr"):
            self.assertNotIn(bad, low)


if __name__ == "__main__":
    unittest.main()
