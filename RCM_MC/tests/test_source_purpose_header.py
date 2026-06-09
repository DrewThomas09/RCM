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
    # 2026 collapse (see ck_source_purpose docstring): the band was reduced to
    # the load-bearing integrity signal — the data-universe / confidence chips
    # + the named source. `purpose` and `next_action` stay in the signature for
    # call-site documentation but are no longer rendered (the page title +
    # content carry the purpose). These tests assert the CURRENT contract: the
    # chip + source must always render so a partner never mistakes an
    # illustrative model for live evidence. Any page-specific honesty caveat
    # that used to live in `purpose`/`next_action` is now rendered explicitly
    # by the page itself (see test_cost_debt_hcris_wiring / payer_stress).
    def test_header_declares_source_and_confidence(self):
        h = ck_source_purpose(
            purpose="Size the cost gap vs HCRIS peers.",
            universe="hcris", source="CMS HCRIS", confidence="derived",
            next_action="Run X-Ray", next_href="/diligence/hcris-xray")
        self.assertIn("HCRIS PUBLIC DATA", h)        # universe chip
        self.assertIn("DERIVED", h)                  # confidence chip
        self.assertIn("CMS HCRIS", h)                # named source (rendered)

    def test_illustrative_page_header(self):
        # The ILLUSTRATIVE chip is the integrity signal that must survive.
        h = ck_source_purpose(
            purpose="Illustrative payer-stress framework.",
            universe="illustrative", source="",
            next_action="Connect HCRIS payer mix")
        self.assertIn("ILLUSTRATIVE", h)

    def test_escapes_strings(self):
        # The rendered field (source) must be escaped — no markup injection.
        h = ck_source_purpose(purpose="x", universe="cms", source="<s>&")
        self.assertNotIn("<s>", h)
        self.assertIn("&lt;s&gt;", h)


if __name__ == "__main__":
    unittest.main()
