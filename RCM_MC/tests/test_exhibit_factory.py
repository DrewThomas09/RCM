"""P5 — ExhibitFactory: numbered, sourced, print-ready exhibit chrome.

The wrap discipline exists so a partner can Cmd+P any analytic page and get
deck-insertable exhibits: per-render numbering (no module state), units
stated, source + vintage in the footer, site chrome suppressed in print.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import (
    _EXHIBIT_PRINT_CSS, ExhibitFactory, chartis_shell,
)


class FactoryTests(unittest.TestCase):
    def test_numbering_increments_within_one_render(self):
        xf = ExhibitFactory()
        h1 = xf.wrap("<p>a</p>", title="First")
        h2 = xf.wrap("<p>b</p>", title="Second")
        self.assertIn("EXHIBIT 1", h1)
        self.assertIn("EXHIBIT 2", h2)

    def test_numbering_resets_per_instance(self):
        # One instance per render pass — two concurrent renders must not
        # bleed numbering into each other (no module state).
        a, b = ExhibitFactory(), ExhibitFactory()
        a.wrap("x", title="t")
        self.assertIn("EXHIBIT 1", b.wrap("y", title="t"))

    def test_title_units_vintage_escaped(self):
        xf = ExhibitFactory()
        h = xf.wrap("inner", title="<b>T</b>", units="<i>u</i>",
                    vintage="<s>v</s>")
        self.assertIn("&lt;b&gt;T&lt;/b&gt;", h)
        self.assertIn("&lt;i&gt;u&lt;/i&gt;", h)
        self.assertIn("&lt;s&gt;v&lt;/s&gt;", h)
        self.assertIn("inner", h)          # body is trusted server markup

    def test_source_accepts_markup_and_deal_label_renders(self):
        xf = ExhibitFactory(deal_label="Project Falcon",
                            source_default='<a href="/x">CMS HCRIS</a>')
        h = xf.wrap("inner", title="t")
        self.assertIn('Source: <a href="/x">CMS HCRIS</a>', h)
        self.assertIn("Project Falcon", h)

    def test_units_line_omitted_when_blank(self):
        h = ExhibitFactory().wrap("inner", title="t")
        # no stray empty units div
        self.assertNotIn('margin:2px 0 0;"></div>', h)


class PrintCssTests(unittest.TestCase):
    def test_shell_ships_print_css_once(self):
        page = chartis_shell("<p>body</p>", "T")
        self.assertEqual(page.count(_EXHIBIT_PRINT_CSS), 1)
        self.assertIn("page-break-inside:avoid", page)

    def test_print_css_hides_site_chrome(self):
        for sel in ("nav", ".ck-topbar", "#ck-deal-bar", "form", "button"):
            self.assertIn(sel, _EXHIBIT_PRINT_CSS)
        self.assertIn("display:none !important", _EXHIBIT_PRINT_CSS)


class ConsumerTests(unittest.TestCase):
    def test_rollup_page_renders_two_numbered_exhibits(self):
        from rcm_mc.ui.rollup_builder_page import render_rollup_builder
        h = render_rollup_builder({"ccns": ["450076,450068"]})
        self.assertIn("EXHIBIT 1", h)
        self.assertIn("EXHIBIT 2", h)
        self.assertIn("latest HCRIS filing per CCN", h)
        self.assertIn("HHI in points", h)             # units stated

    def test_cim_page_renders_exhibit_on_results(self):
        from rcm_mc.ui.cim_crosscheck_page import render_cim_crosscheck
        h = render_cim_crosscheck(
            {"state": ["TX"], "c_provider_count": ["400"]})
        self.assertIn("EXHIBIT 1", h)
        self.assertIn("CIM cross-check", h)
        # form-only view (no claims) carries no exhibit chrome
        h0 = render_cim_crosscheck({})
        self.assertNotIn("EXHIBIT 1", h0)


if __name__ == "__main__":
    unittest.main()
