"""tests for contrast-ratio helper + palette WCAG audit (P95)."""
from __future__ import annotations

import os
import sys
import unittest

from rcm_mc.ui.contrast import (
    contrast_ratio, passes_aa_large, passes_aa_normal,
)


class ContrastFormula(unittest.TestCase):
    """Cross-check against published WCAG values."""

    def test_black_on_white_max(self) -> None:
        # Black on white is ≈ 21.0 in WCAG.
        ratio = contrast_ratio("#000000", "#FFFFFF")
        self.assertAlmostEqual(ratio, 21.0, places=1)

    def test_same_color_min(self) -> None:
        ratio = contrast_ratio("#888888", "#888888")
        self.assertAlmostEqual(ratio, 1.0, places=2)

    def test_three_char_hex(self) -> None:
        ratio = contrast_ratio("#000", "#FFF")
        self.assertAlmostEqual(ratio, 21.0, places=1)


class WCAGThresholds(unittest.TestCase):

    def test_passes_aa_normal_when_ratio_geq_4_5(self) -> None:
        # Navy on parchment from the kit palette.
        self.assertTrue(passes_aa_normal("#0b2341", "#f5f1ea"))

    def test_passes_aa_large_when_ratio_geq_3_0(self) -> None:
        # text-dim on white passes large but possibly not normal.
        self.assertTrue(passes_aa_large("#465366", "#ffffff"))


class PalettePairsAudit(unittest.TestCase):
    """Pin that the kit palette's key text+background pairs pass
    WCAG AA. If a future palette change breaks one of these, the
    test fires before the regression ships."""

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
        from rcm_mc.ui._chartis_kit import P
        cls.P = P

    def test_main_text_on_panel(self) -> None:
        self.assertTrue(passes_aa_normal(
            self.P["text"], self.P["panel"],
        ))

    def test_main_text_on_parchment(self) -> None:
        self.assertTrue(passes_aa_normal(
            self.P["text"], self.P["bg"],
        ))

    def test_text_dim_on_panel(self) -> None:
        self.assertTrue(passes_aa_normal(
            self.P["text_dim"], self.P["panel"],
        ))

    def test_navy_text_on_bone(self) -> None:
        self.assertTrue(passes_aa_normal(
            self.P["navy"], self.P.get("bone", self.P["panel_alt"]),
        ))

    def test_on_navy_text_on_navy(self) -> None:
        self.assertTrue(passes_aa_normal(
            self.P["on_navy"], self.P["navy"],
        ))


if __name__ == "__main__":
    unittest.main()
