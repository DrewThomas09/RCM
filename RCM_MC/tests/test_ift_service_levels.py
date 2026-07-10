"""Tests for the IFT clinical service-levels research page.

Pins the model contract (four levels, sourced facts, ZERO illustrative
figures, fee/mix arithmetic), the page render (the required four-column
comparison table, inline source links), and the /tools registration
(route discovered, exact card title).
"""
import unittest

from rcm_mc.market_reports import ift_service_levels as M


class TestServiceLevelModel(unittest.TestCase):
    def test_four_levels_with_all_four_table_columns(self):
        levels = M.service_levels()
        self.assertEqual([lv.key for lv in levels],
                         ["BLS", "ALS1", "ALS2", "SCT"])
        for lv in levels:
            # the top table's four required columns are all populated
            self.assertTrue(lv.definition.text and lv.definition.srcs)
            self.assertTrue(lv.clinical and lv.operational
                            and lv.reimbursement)
            self.assertTrue(lv.boundary.text and lv.use_cases)
            self.assertTrue(lv.hcpcs)

    def test_every_fact_is_sourced_with_urls(self):
        for f in M._iter_facts():
            self.assertTrue(f.srcs, msg=f"unsourced fact: {f.text[:60]}")
            for s in f.srcs:
                self.assertTrue(s.url.startswith("http"),
                                msg=f"bad url on: {s.label}")
        for ec in M.edge_cases():
            self.assertTrue(ec.srcs)

    def test_zero_illustrative_anywhere(self):
        self.assertTrue(M.has_no_illustrative())
        allowed = {"GOV", "ACADEMIC", "SOURCED", "DERIVED", "FRAMEWORK"}
        self.assertLessEqual(set(M.n_by_basis()), allowed)

    def test_fee_rows_arithmetic_and_rvus(self):
        rows = {r.hcpcs: r for r in M.fee_rows()}
        self.assertEqual(set(rows), {"A0428", "A0429", "A0426", "A0427",
                                     "A0433", "A0434"})
        # regulatory RVU ladder (42 CFR 414.610)
        self.assertEqual(rows["A0428"].rvu, 1.00)
        self.assertEqual(rows["A0434"].rvu, 3.25)
        # CY2026 base = RVU x $284.56 (2dp)
        for r in rows.values():
            self.assertAlmostEqual(r.cy2026_base, round(r.rvu * 284.56, 2))
        # SCT is the thinnest book, ALS1-E the biggest
        self.assertLess(rows["A0434"].cy2024_services,
                        rows["A0433"].cy2024_services)
        self.assertGreater(rows["A0427"].cy2024_services, 3_000_000)

    def test_mix_shares_sum_to_100(self):
        mix = M.medicare_mix()
        self.assertEqual(len(mix), 6)
        self.assertAlmostEqual(sum(m.share_pct for m in mix), 100.0,
                               delta=0.3)

    def test_als2_definition_carries_eight_procedures(self):
        als2 = [lv for lv in M.service_levels() if lv.key == "ALS2"][0]
        self.assertIn("EIGHT", als2.definition.text)
        self.assertIn("Prehospital blood transfusion",
                      als2.definition.quote)

    def test_edge_cases_and_misconceptions_populated(self):
        self.assertGreaterEqual(len(M.edge_cases()), 15)
        self.assertGreaterEqual(len(M.misconceptions()), 10)

    def test_conclusion_is_tested_not_asserted(self):
        c = M.conclusion_test()
        self.assertIn("SUPPORTED", c.verdict)
        self.assertTrue(c.support and c.refinements)

    def test_bibliography_dedupes_and_links(self):
        bib = M.bibliography()
        self.assertGreaterEqual(len(bib), 40)
        urls = [s.url for s in bib]
        self.assertEqual(len(urls), len(set(urls)))

    def test_connector_reads_degrade_never_raise(self):
        cr = M.connector_reads()
        self.assertIn("part_b", cr)
        self.assertIn("qcew", cr)
        # offline the hooks must still return a well-formed block
        self.assertIn("available", cr["part_b"])

    def test_wage_ladder_is_monotonic(self):
        wages = [w.median_wage for w in M.wage_ladder()]
        self.assertEqual(wages, sorted(wages))


class TestServiceLevelPage(unittest.TestCase):
    def _html(self, qs=None):
        from rcm_mc.ui.ift_service_levels_page import (
            render_ift_service_levels)
        return render_ift_service_levels(qs)

    def test_renders_required_table_columns(self):
        h = self._html()
        for col in ("1 · Comprehensive definition",
                    "2 · Typical clinical needs",
                    "3 · Typical operational needs",
                    "4 · Reimbursement differences"):
            self.assertIn(col, h)

    def test_renders_all_levels_and_sources_as_links(self):
        h = self._html()
        for probe in ("A0428", "A0427", "A0433", "A0434",
                      "ecfr.gov", "bls.gov", "medpac.gov", "oig.hhs.gov",
                      "camts.org", "nemsis.org"):
            self.assertIn(probe, h)
        # sources render as anchors next to facts
        self.assertGreater(h.count('class="isl-src"'), 100)

    def test_no_illustrative_banner_or_chip(self):
        h = self._html()
        # no illustrative-template banner and no rendered ILLUSTRATIVE
        # basis chip (the shared chart-kit JS mentions the word in an
        # infrastructure comment; that is not page content)
        self.assertNotIn('class="ck-illus-note"', h)
        self.assertNotIn(">ILLUSTRATIVE<", h)

    def test_never_raises_with_query_noise(self):
        h = self._html({"view": ["x"], "junk": ["1"]})
        self.assertIn("In-Depth IFT", h)

    def test_verdict_and_sections_present(self):
        h = self._html()
        for anchor in ('id="table"', 'id="framework"', 'id="fee"',
                       'id="mix"', 'id="crew"', 'id="edges"',
                       'id="myths"', 'id="verdict"', 'id="sources"'):
            self.assertIn(anchor, h)
        self.assertIn("SUPPORTED", h)


class TestToolsRegistration(unittest.TestCase):
    ROUTE = "/in-depth-ift-bls-als1-als2-cct"

    def test_route_is_discovered(self):
        from rcm_mc.server import RCMHandler
        self.assertIn(self.ROUTE, RCMHandler._discover_all_routes())

    def test_tools_card_uses_exact_title(self):
        from rcm_mc.server import RCMHandler
        workspaces, _total = RCMHandler._build_tools_index_data()
        cards = {t["path"]: t for ws in workspaces for t in ws["tools"]}
        self.assertIn(self.ROUTE, cards)
        self.assertEqual(cards[self.ROUTE]["name"],
                         "In-Depth IFT — BLS · ALS1 · ALS2 · CCT")

    def test_palette_carries_the_page(self):
        from rcm_mc.ui._chartis_kit import _DEFAULT_PALETTE_MODULES
        routes = {m["route"] for m in _DEFAULT_PALETTE_MODULES}
        self.assertIn(self.ROUTE, routes)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
