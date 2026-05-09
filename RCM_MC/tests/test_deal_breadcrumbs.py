"""tests for ``rcm_mc.ui._ui_kit.deal_breadcrumbs``.

PROMPTS.md Phase 3 / Prompt 38: when a partner is on a diligence
sub-page in a deal context, the breadcrumb should read
``HOME / DEAL: PROJECT AURORA / DILIGENCE / CHECKLIST`` rather
than the generic ``HOME / DILIGENCE / CHECKLIST``.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._ui_kit import deal_breadcrumbs


class WithoutDealContext(unittest.TestCase):

    def test_three_segments_when_no_deal(self) -> None:
        crumbs = deal_breadcrumbs(
            "Checklist",
            parent=("Diligence", "/diligence"),
        )
        self.assertEqual(len(crumbs), 3)
        self.assertEqual(crumbs[0]["label"], "HOME")
        self.assertEqual(crumbs[1]["label"], "DILIGENCE")
        self.assertEqual(crumbs[2]["label"], "CHECKLIST")

    def test_leaf_has_no_href(self) -> None:
        crumbs = deal_breadcrumbs(
            "Checklist",
            parent=("Diligence", "/diligence"),
        )
        self.assertNotIn("href", crumbs[-1])


class WithDealContext(unittest.TestCase):

    def test_four_segments_when_deal_supplied(self) -> None:
        crumbs = deal_breadcrumbs(
            "Checklist",
            deal_id="aurora", deal_name="Project Aurora",
            parent=("Diligence", "/diligence"),
        )
        self.assertEqual(len(crumbs), 4)
        labels = [c["label"] for c in crumbs]
        self.assertEqual(
            labels,
            ["HOME", "DEAL: PROJECT AURORA", "DILIGENCE", "CHECKLIST"],
        )

    def test_deal_segment_links_to_deal_page(self) -> None:
        crumbs = deal_breadcrumbs(
            "Checklist",
            deal_id="aurora",
            parent=("Diligence", "/diligence"),
        )
        self.assertEqual(crumbs[1]["href"], "/deal/aurora")

    def test_deal_id_used_when_name_omitted(self) -> None:
        crumbs = deal_breadcrumbs(
            "Checklist",
            deal_id="aurora",
            parent=("Diligence", "/diligence"),
        )
        self.assertIn("AURORA", crumbs[1]["label"])


class WithoutParent(unittest.TestCase):

    def test_two_segments_for_top_level_page(self) -> None:
        crumbs = deal_breadcrumbs("Library")
        self.assertEqual(len(crumbs), 2)
        self.assertEqual(crumbs[0]["label"], "HOME")
        self.assertEqual(crumbs[1]["label"], "LIBRARY")


if __name__ == "__main__":
    unittest.main()
