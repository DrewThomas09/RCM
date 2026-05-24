"""Diligence source-and-purpose header + confidence chips (PR 1).

Additive kit helpers for the Diligence reform — no existing page changes.
Adds confidence-state chips (illustrative / data-required / experimental /
hcris / derived) and a `ck_source_purpose` header band declaring purpose +
data universe + source + next action.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import (
    ck_data_universe, ck_source_purpose, chartis_shell,
)


class ConfidenceChipTests(unittest.TestCase):
    def test_new_kinds_render(self):
        cases = {
            "illustrative": "ILLUSTRATIVE",
            "data-required": "DATA REQUIRED",
            "experimental": "EXPERIMENTAL",
            "hcris": "HCRIS PUBLIC DATA",
            "derived": "DERIVED",
        }
        for kind, label in cases.items():
            self.assertIn(label, ck_data_universe(kind))

    def test_illustrative_tooltip_is_honest(self):
        self.assertIn("NOT a real source", ck_data_universe("illustrative"))

    def test_unknown_kind_safe_empty(self):
        self.assertEqual(ck_data_universe("nope"), "")

    def test_chip_css_present(self):
        css = chartis_shell(body="<main/>", title="x")
        self.assertIn(".ck-universe-illus", css)
        self.assertIn(".ck-universe-datareq", css)
        self.assertIn(".ck-sp ", css)            # header band styled


class SourcePurposeHeaderTests(unittest.TestCase):
    def test_header_declares_all_facets(self):
        h = ck_source_purpose(
            purpose="Size the cost gap vs HCRIS peers.",
            universe="hcris", source="CMS HCRIS", confidence="derived",
            next_action="Run X-Ray", next_href="/diligence/hcris-xray")
        self.assertIn("HCRIS PUBLIC DATA", h)        # universe chip
        self.assertIn("DERIVED", h)                  # confidence chip
        self.assertIn("Size the cost gap", h)        # purpose
        self.assertIn("Source:", h)
        self.assertIn("CMS HCRIS", h)
        self.assertIn("/diligence/hcris-xray", h)    # next action link

    def test_illustrative_page_header(self):
        h = ck_source_purpose(
            purpose="Illustrative payer-stress framework.",
            universe="illustrative", source="",
            next_action="Connect HCRIS payer mix")
        self.assertIn("ILLUSTRATIVE", h)
        self.assertIn("Connect HCRIS payer mix", h)

    def test_escapes_strings(self):
        h = ck_source_purpose(purpose="<x>&", universe="cms", source="<s>")
        self.assertNotIn("<x>", h)
        self.assertIn("&lt;x&gt;", h)


if __name__ == "__main__":
    unittest.main()
