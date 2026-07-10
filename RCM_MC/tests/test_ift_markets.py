"""Real-path tests for the IFT geographic deep-dive page (``/ift-markets``).

Pins four things, all against the real code path (no mocks of our own code):

  1. ``render_ift_markets()`` returns a full, non-trivial, tag-balanced,
     leak-free editorial page that lists every target metro with its real
     (SOURCED) facility counts and the honesty basis chips.
  2. The national overview renders the TAM → SAM → SOM funnel — the top-down
     TAM, the structural multi-hospital-health-system SAM (dual method), and the
     bottom-up footprint SOM — and the honest data caveats surface.
  3. The ``/ift-markets`` route is wired into ``server.py`` and the renderer
     symbol imports.
  4. ``ift_geo`` / ``ift_analytics`` return sane per-market numbers offline.
"""
from __future__ import annotations

import html as _h
import pathlib
import unittest
from html.parser import HTMLParser

from rcm_mc.market_reports import ift_analytics as _an
from rcm_mc.market_reports import ift_geo as _geo
from rcm_mc.ui.ift_markets_page import render_ift_markets


# ── Structural tag-balance parser (html.parser, CDATA-aware for <style>) ─────
_TRACK = {"section", "table", "thead", "tbody", "ul", "ol", "tr", "div",
          "header", "style"}


class _BalanceParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag in _TRACK:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in _TRACK:
            if self.stack and self.stack[-1] == tag:
                self.stack.pop()
            elif tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass
            else:
                self.errors.append(("stray_close", tag))


def _assert_balanced(test, html, label):
    p = _BalanceParser()
    p.feed(html)
    test.assertEqual(p.errors, [], f"{label}: unbalanced {p.errors[:5]}")
    test.assertEqual(p.stack, [], f"{label}: unclosed {p.stack[:5]}")


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = render_ift_markets()

    def test_page_is_non_trivial(self):
        self.assertGreater(len(self.html), 20_000)
        self.assertIn("Interfacility Transport — Target Markets", self.html)
        # editorial cadence + shell markers
        self.assertIn("<em>", self.html)
        self.assertIn("</html>", self.html.lower())

    def test_tags_are_balanced(self):
        _assert_balanced(self, self.html, "ift-markets")

    def test_exactly_one_page_title(self):
        # Regression: the page used ck_editorial_head (a ck-eh <h1>) AND
        # ck_section_intro, which made the shell auto-inject a SECOND ck_page_title
        # <h1> — a duplicate title. There must be exactly one <h1>.
        self.assertEqual(self.html.count("<h1"), 1,
                         "IFT markets page must render exactly one <h1>")

    def test_has_chart_visuals_with_export(self):
        # The 'at a glance' strip renders real SVG charts (funnel, growth levers,
        # per-metro SOM, moat composite) with PNG-export affordances.
        self.assertIn("At a glance", self.html)
        self.assertIn("ck-chart-card", self.html)
        self.assertIn("ck-chart-dl", self.html)         # export button
        self.assertGreaterEqual(self.html.count("<svg"), 4)
        for probe in ("TAM → SAM → SOM", "Three growth levers",
                      "Footprint SOM by metro", "Moat composite by metro"):
            self.assertIn(probe, self.html, f"missing chart: {probe}")

    def test_no_template_token_leaks(self):
        # Markers that indicate an unrendered template / repr leak in OUR
        # content (bare "{}" and "nan" occur legitimately in the shell's inline
        # JS/CSS, so they are excluded from this check).
        for marker in ("None", "{0}", "{1}", "{{", "%s", "%d", "0.0%",
                       "&lt;span"):
            self.assertNotIn(marker, self.html, f"leaked {marker!r}")

    def test_lists_every_target_metro_with_real_counts(self):
        # Every registry metro appears; and its SOURCED structure's real SNF-bed
        # and hospital counts are rendered (formatted with thousands commas).
        for md in _geo.MARKETS:
            s = _geo.metro_structure(md.name)
            self.assertTrue(s.available, f"{md.name}: structure unavailable")
            self.assertIn(_h.escape(md.name), self.html,
                          f"{md.name}: name missing from page")
            self.assertIn(f"{s.n_snf:,}", self.html,
                          f"{md.name}: SNF count {s.n_snf} missing")

    def test_anchor_metro_counts_match_sourced_structure(self):
        # Lock the marquee SOURCED hospital counts the research briefs cite.
        expect = {"Omaha": 11, "Cleveland": 14, "Kansas City (bi-state)": 22,
                  "North Platte": 1}
        for name, n in expect.items():
            s = _geo.metro_structure(name)
            self.assertEqual(s.n_hospitals, n, f"{name}: {s.n_hospitals} != {n}")
            self.assertIn(f"{n:,}", self.html)

    def test_every_basis_chip_family_present(self):
        for cls in ("ift-chip-sourced", "ift-chip-gov", "ift-chip-illustrative",
                    "ift-chip-public"):
            self.assertIn(cls, self.html, f"{cls} missing")
        self.assertIn("Every figure is labelled", self.html)

    def test_national_overview_tam_and_sam(self):
        # The funnel renders: TAM (top-down) → SAM (multi-hospital health systems,
        # dual method) → SOM (footprint, bottom-up).
        self.assertIn("National TAM", self.html)
        self.assertIn("National SAM", self.html)
        self.assertIn("multi-hospital health systems", self.html)
        self.assertIn("Footprint SOM", self.html)
        # the excluded-from-TAM discipline is stated
        self.assertIn("NEMT", self.html)
        self.assertIn("air", self.html.lower())
        # the SOM formula spine is shown
        self.assertIn("s(m)", self.html)

    def test_structural_sam_dual_method_and_nascent_share(self):
        # SAM = multi-hospital health systems, sized two ways (top-down ratio +
        # bottoms-up structure proxy), with the health-system-biller insource
        # ceiling and the ~1% nascent operator share.
        self.assertIn("top-down", self.html)
        self.assertIn("bottoms-up", self.html)
        self.assertIn("Insource ceiling", self.html)
        self.assertIn("MSA-restricted", self.html)
        # the funnel headline naming appears
        self.assertIn("TAM → SAM → SOM", self.html)

    def test_market_education_boundary(self):
        # Chapter one teaches IFT is its own market — not 911 / NEMT / air.
        self.assertIn("MARKET EDUCATION", self.html)
        self.assertIn("What IFT is", self.html)
        for excl in ("911", "NEMT", "Air ambulance"):
            self.assertIn(excl, self.html, f"boundary term {excl} missing")

    def test_investor_layers_present(self):
        # The four deepened analytic layers each render a section.
        self.assertIn("three levers", self.html)            # growth tracker
        self.assertIn("Competitive landscape", self.html)   # competition
        self.assertIn("MMT positioning", self.html)
        self.assertIn("Insource vs outsource", self.html)   # addressability
        self.assertIn("claims UNDERCOUNT", self.html)
        self.assertIn("moat scorecard", self.html)          # defensibility
        self.assertIn("proof points", self.html.lower())

    def test_excel_download_offered(self):
        self.assertIn("/api/ift/markets.xlsx", self.html)
        self.assertIn("Download Excel", self.html)

    def test_per_metro_deep_dive_content(self):
        # Each card carries anchor systems, an insource-vs-outsource read and a
        # moat verdict — check the section scaffolding + real operator names.
        self.assertIn("Anchor health systems", self.html)
        self.assertIn("insource vs outsource", self.html)
        self.assertIn("Moat verdict", self.html)
        for operator in ("MMT", "AmeriPro", "Superior Air-Ground",
                         "Ryan Brothers", "Mayo Clinic Ambulance"):
            self.assertIn(operator, self.html, f"{operator} missing")

    def test_honest_data_caveats_surface(self):
        # The two absent-from-rolls anchors are named with the gap flagged.
        self.assertIn("Data caveat", self.html)
        self.assertIn("Nebraska Medicine", self.html)
        self.assertIn("Via Christi", self.html)

    def test_footprint_table_and_state_grouping(self):
        self.assertIn("Every target metro at a glance", self.html)
        # grouped by state region
        for label in _geo.REGION_LABELS.values():
            self.assertIn(_h.escape(label), self.html, f"{label} missing")


class RouteWiringTests(unittest.TestCase):
    def test_renderer_symbol_imports(self):
        from rcm_mc.ui.ift_markets_page import render_ift_markets as r
        self.assertTrue(callable(r))

    def test_route_is_wired_into_server(self):
        # The additive dispatch block exists and points at the renderer — proves
        # the route wiring without standing up the authenticated server.
        src = pathlib.Path("rcm_mc/server.py").read_text(encoding="utf-8")
        self.assertIn('path == "/ift-markets"', src)
        self.assertIn("render_ift_markets", src)
        self.assertIn("from .ui.ift_markets_page import render_ift_markets", src)


class GeoAnalyticsSanityTests(unittest.TestCase):
    def test_footprint_rollup_is_sane(self):
        ru = _geo.footprint_rollup()
        self.assertTrue(ru.available)
        self.assertEqual(ru.n_metros, len(_geo.MARKETS))
        self.assertEqual(ru.n_regions, len(_geo.REGION_LABELS))
        self.assertGreater(ru.n_hospitals, 100)
        self.assertGreater(ru.snf_beds, 10_000)
        for share in (ru.hospitals_national_share, ru.snf_beds_national_share):
            self.assertIsNotNone(share)
            self.assertGreater(share, 0.0)
            self.assertLess(share, 1.0)

    def test_every_metro_structure_available_and_positive(self):
        for md in _geo.MARKETS:
            s = _geo.metro_structure(md.name)
            self.assertTrue(s.available, md.name)
            self.assertGreaterEqual(s.n_hospitals, 1, md.name)
            self.assertGreaterEqual(s.snf_beds, 0, md.name)
            self.assertGreaterEqual(s.hcris_beds, 0.0, md.name)
            # registry read travels with the structure
            self.assertTrue(s.anchor_systems, md.name)
            self.assertTrue(s.moat_note, md.name)

    def test_tam_is_sane_and_ranged(self):
        tam = _an.ground_tam()
        self.assertTrue(tam.available)
        self.assertGreater(tam.allpayer_tam_bn_central, 0.0)
        self.assertLess(tam.allpayer_tam_bn_low, tam.allpayer_tam_bn_central)
        self.assertLess(tam.allpayer_tam_bn_central, tam.allpayer_tam_bn_high)
        self.assertTrue(tam.exclusions)  # NEMT + air documented

    def test_sam_is_sane_and_ranged(self):
        sam = _an.sam_formula()
        self.assertTrue(sam.available)
        self.assertEqual(len(sam.rows), len(_geo.MARKETS))
        self.assertGreater(sam.sam_dollars_central, 0.0)
        self.assertLess(sam.sam_dollars_low, sam.sam_dollars_central)
        self.assertLess(sam.sam_dollars_central, sam.sam_dollars_high)
        # every metro carries a positive serviceable share in the 0.10-0.35 band
        for r in sam.rows:
            self.assertGreaterEqual(r.serviceable_share, 0.10, r.name)
            self.assertLessEqual(r.serviceable_share, 0.35, r.name)
            self.assertGreater(r.sam_dollars, 0.0, r.name)

    def test_health_system_sam_is_coherent(self):
        # SAM = multi-hospital health systems, the structural addressable market:
        # TAM → SAM → SOM funnel with a nascent ~1% operator share.
        hs = _an.health_system_sam()
        self.assertTrue(hs.available)
        tam = _an.ground_tam()
        som = _an.sam_formula()
        # top-down = TAM × system-share × addressable, so 0 < SAM_td < TAM
        self.assertGreater(hs.sam_td_central_bn, 0.0)
        self.assertLess(hs.sam_td_central_bn, tam.allpayer_tam_bn_central)
        # addressable = 1 - insource ceiling; ceiling is a real (0,1) band
        for i in range(3):
            self.assertGreater(hs.insource_ceiling[i], 0.0)
            self.assertLess(hs.insource_ceiling[i], 1.0)
            self.assertAlmostEqual(
                hs.addressable_share[i] + hs.insource_ceiling[2 - i], 1.0, places=3)
        # MSA-restricted SAM is a strict subset of the all-geography SAM
        self.assertLess(hs.sam_td_msa_central_bn, hs.sam_td_central_bn)
        # bottoms-up structure proxy exists offline and reads low vs top-down
        self.assertIsNotNone(hs.sam_bu_central_bn)
        self.assertLess(hs.sam_bu_central_bn, hs.sam_td_central_bn)
        # triangulated central sits between the two methods
        self.assertGreaterEqual(hs.sam_central_bn, hs.sam_bu_central_bn)
        self.assertLessEqual(hs.sam_central_bn, hs.sam_td_central_bn)
        # SOM = footprint (in $M); SAM (in $B) dwarfs it, and the operator holds ~1%
        self.assertAlmostEqual(hs.som_central_m,
                               som.sam_dollars_central / 1e6, places=1)
        self.assertGreater(hs.sam_over_som_multiple, 1.0)
        self.assertAlmostEqual(
            hs.operator_current_revenue_m,
            hs.sam_central_bn * 1e3 * hs.operator_share_of_sam, places=1)
        # every build step carries an honesty basis chip
        for st in hs.steps:
            self.assertIn(st.basis, ("GOV", "FRAMEWORK", "ILLUSTRATIVE",
                         "SOURCED", "unavailable"))

    def test_unknown_metro_degrades_without_raising(self):
        s = _geo.metro_structure("Nowhere")
        self.assertFalse(s.available)
        self.assertIsNone(_geo.metro_def("Nowhere"))


if __name__ == "__main__":
    unittest.main()
