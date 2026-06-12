"""National infusion-market scan — state attractiveness ranking.

Every figure is a pure function of real per-state ACS demographics + CMS
MA data + the documented no-CON list, so the score recomputes and audits.
"""
from __future__ import annotations

import unittest

from rcm_mc.diligence.infusion_market import (
    infusion_state_attractiveness, NON_CON_STATES, _WEIGHTS,
)
from rcm_mc.ui.infusion_market_page import render_infusion_market_page


class AttractivenessTests(unittest.TestCase):
    def setUp(self):
        self.a = infusion_state_attractiveness()

    def test_all_states_scored_and_ranked(self):
        self.assertEqual(len(self.a["states"]), 51)
        scores = [s["score"] for s in self.a["states"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual([s["rank"] for s in self.a["states"]],
                         list(range(1, 52)))

    def test_score_is_the_weighted_blend(self):
        # Recompute from the (3dp-rounded) axes; tolerance covers the
        # rounding vs the full-precision score stored on the row.
        for s in self.a["states"]:
            exp = 100 * sum(s["axes"][k] * w for k, w in _WEIGHTS.items())
            self.assertAlmostEqual(s["score"], exp, delta=0.5)
            self.assertTrue(0 <= s["score"] <= 100)

    def test_no_con_flag_matches_the_documented_list(self):
        for s in self.a["states"]:
            self.assertEqual(s["no_con"], s["code"] in NON_CON_STATES)
            self.assertEqual(s["axes"]["no_con"],
                             1.0 if s["no_con"] else 0.0)

    def test_texas_present_and_high(self):
        tx = self.a["texas"]
        self.assertEqual(tx["code"], "TX")
        self.assertLessEqual(tx["rank"], 10)   # TX is a strong market
        self.assertGreater(tx["seniors"], 3_000_000)


class MarketPageTests(unittest.TestCase):
    def test_page_renders_map_table_and_tx_read(self):
        h = render_infusion_market_page()
        for needle in ("Infusion Market Scan — by State",
                       "WHERE ELSE AFTER TEXAS", "No-CON", "Texas ranks",
                       "<svg", "/diligence/texas-infusion"):
            self.assertIn(needle, h, needle)

    def test_excel_mapping_crosslink_round_trips(self):
        import re
        import html as _html
        import urllib.parse
        from rcm_mc.ui.excel_mapping_page import parse_values_text
        h = render_infusion_market_page()
        self.assertIn("Open this scan in Excel Mapping", h)
        m = re.search(r'/excel-mapping\?([^"]+)"', h)
        self.assertIsNotNone(m)
        qs = urllib.parse.parse_qs(_html.unescape(m.group(1)))
        vals = parse_values_text(qs["data"][0])
        # Every state's score flows into the mapping tool.
        self.assertEqual(len(vals), 51)
        self.assertIn("TX", vals)

    def test_registered_in_palette_nav_and_guide(self):
        from rcm_mc.ui._chartis_kit import (
            _DEFAULT_PALETTE_MODULES, _SUB_SECTION_MAP)
        from rcm_mc.assistant.context.guide_context_packet import (
            build_guide_context_packet)
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn("/diligence/infusion-markets", routes)
        self.assertEqual(_SUB_SECTION_MAP.get("/diligence/infusion-markets"),
                         "diligence")
        self.assertIsNotNone(build_guide_context_packet(
            "/diligence/infusion-markets").page_context)


if __name__ == "__main__":
    unittest.main()
