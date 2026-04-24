"""Power-UI + Compare page regression tests.

Scope:
    - power_ui Python helpers (provenance, sortable_table,
      export_json_panel, diff_badge) emit correct data-attributes
    - bundle tags are injected into the Chartis shell
    - /static/power_ui.{js,css} exist on disk
    - compare page renders landing + two-fixture view with delta
      badges
    - counterfactual page retrofit still renders + includes
      data-provenance on derived-from-CCD cells
    - nav link for /diligence/compare present
"""
from __future__ import annotations

import json
import pathlib
import unittest

from rcm_mc.ui.compare_page import render_compare_page
from rcm_mc.ui.counterfactual_page import render_counterfactual_page
from rcm_mc.ui.power_ui import (
    diff_badge, export_json_panel, power_ui_tags, provenance,
    sortable_table,
)


STATIC = pathlib.Path(
    __file__,
).resolve().parent.parent / "rcm_mc" / "ui" / "static"


class BundleAssetsTests(unittest.TestCase):

    def test_power_ui_js_exists_and_nontrivial(self):
        js = STATIC / "power_ui.js"
        self.assertTrue(js.exists())
        content = js.read_text("utf-8")
        # A few key features we rely on.
        for marker in (
            "initSortable", "initFilterable", "initExport",
            "openCommandPalette", "bookmarkCurrentView",
            "toggleHelpOverlay",
        ):
            self.assertIn(
                marker, content,
                msg=f"power_ui.js missing {marker}",
            )

    def test_power_ui_css_exists(self):
        css = STATIC / "power_ui.css"
        self.assertTrue(css.exists())
        content = css.read_text("utf-8")
        for cls in (
            "rcm-filter-bar", "rcm-export-btn", "rcm-overlay",
            "rcm-palette", "rcm-compare-grid", "rcm-diff-indicator",
        ):
            self.assertIn(cls, content)


class PowerUIHelperTests(unittest.TestCase):

    def test_provenance_tag_has_data_attributes(self):
        h = provenance(
            "$4,200",
            source="hospital_06 claims",
            formula="sum(paid_amount)",
            detail="Mature cohort 2024-02",
        )
        self.assertIn('data-provenance="hospital_06 claims"', h)
        self.assertIn("sum(paid_amount)", h)
        self.assertIn("Mature cohort 2024-02", h)
        self.assertIn('tabindex="0"', h)

    def test_sortable_table_has_data_attributes(self):
        h = sortable_table(
            ["Name", "Revenue"],
            [("Hospital A", "$100M"), ("Hospital B", "$250M")],
            name="demo",
            sort_keys=[[None, 100_000_000], [None, 250_000_000]],
        )
        self.assertIn("data-sortable", h)
        self.assertIn("data-filterable", h)
        self.assertIn("data-export", h)
        self.assertIn('data-sort-key="250000000"', h)
        self.assertIn('data-export-name="demo"', h)

    def test_export_json_panel_embeds_payload(self):
        payload = {"answer": 42, "items": [1, 2]}
        h = export_json_panel(
            "<p>content</p>", payload=payload, name="widget",
        )
        self.assertIn("data-export-json", h)
        self.assertIn('data-export-name="widget"', h)
        # The serialised payload survives round-trip.
        import re
        m = re.search(r'data-export-json="([^"]+)"', h)
        self.assertIsNotNone(m)
        import html as htmllib
        decoded = htmllib.unescape(m.group(1))
        self.assertEqual(json.loads(decoded), payload)

    def test_diff_badge_direction(self):
        # Higher-is-better: right bigger → positive
        self.assertIn(
            "rcm-diff-positive",
            diff_badge(100, 150, higher_is_better=True),
        )
        self.assertIn(
            "rcm-diff-negative",
            diff_badge(100, 150, higher_is_better=False),
        )
        # Equal → neutral
        self.assertIn(
            "rcm-diff-neutral",
            diff_badge(100, 100),
        )

    def test_shell_injects_power_ui_bundle(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        rendered = chartis_shell("<p>x</p>", "Test")
        self.assertIn("/static/power_ui.css", rendered)
        self.assertIn("/static/power_ui.js", rendered)

    def test_tags_helper_emits_both_assets(self):
        t = power_ui_tags()
        self.assertIn("power_ui.css", t)
        self.assertIn("power_ui.js", t)


class ComparePageTests(unittest.TestCase):

    def test_landing_renders_picker_form(self):
        h = render_compare_page()
        self.assertIn("Side-by-side Compare", h)
        self.assertIn('name="left"', h)
        self.assertIn('name="right"', h)

    def test_live_compare_renders_metrics_and_grid(self):
        h = render_compare_page(
            left="hospital_07_waterfall_concordant",
            right="hospital_08_waterfall_critical",
        )
        # Header shows both fixture names
        self.assertIn("hospital_07_waterfall_concordant", h)
        self.assertIn("hospital_08_waterfall_critical", h)
        # Delta badges present
        self.assertIn("rcm-diff-indicator", h)
        # Two-column grid rendered
        self.assertIn("rcm-compare-grid", h)
        # Bookmark hint rendered
        self.assertIn("bookmark", h.lower())

    def test_bad_fixture_handled_gracefully(self):
        h = render_compare_page(
            left="hospital_07_waterfall_concordant",
            right="not_a_real_fixture",
        )
        self.assertIn("Unable to resolve", h)


class CounterfactualRetrofitTests(unittest.TestCase):

    def test_ccd_summary_cells_have_provenance(self):
        h = render_counterfactual_page(
            dataset="hospital_08_waterfall_critical",
            metadata={
                "legal_structure": "FRIENDLY_PC_PASS_THROUGH",
                "states": ["OR"],
            },
        )
        # Provenance tooltips live on every derived-from-CCD number.
        self.assertIn("data-provenance", h)
        self.assertIn("sum(claim.paid_amount)", h)


class NavTests(unittest.TestCase):

    def test_compare_link_in_sidebar(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        rendered = chartis_shell("<p>x</p>", "Test")
        self.assertIn('href="/diligence/compare"', rendered)


if __name__ == "__main__":
    unittest.main()
