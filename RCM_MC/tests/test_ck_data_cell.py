"""Test the ck_data_cell helper added in cycle 22.

The helper replaces the ~1200 hand-rolled inline-styled <td>
attributes that the cycle-22 audit identified as the dominant
inline-style source across data_public/ pages. Pin the contract
so future bulk migrations can rely on stable behavior.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui._chartis_kit import ck_data_cell


class CkDataCellTests(unittest.TestCase):
    def test_minimal_cell_emits_td_with_base_class(self):
        html = ck_data_cell("hello")
        self.assertEqual(
            html, '<td class="ck-cell">hello</td>',
        )

    def test_header_cell_emits_th(self):
        html = ck_data_cell("Header", is_header=True)
        self.assertEqual(
            html, '<th class="ck-cell">Header</th>',
        )

    def test_mono_cell_adds_mono_class(self):
        html = ck_data_cell("1.23", mono=True)
        self.assertIn("ck-cell-mono", html)
        # Base class is still present
        self.assertIn("ck-cell ", html)

    def test_alignment_classes(self):
        right = ck_data_cell("$1.23", align="right")
        center = ck_data_cell("X", align="center")
        left = ck_data_cell("X", align="left")
        self.assertIn("ck-cell-r", right)
        self.assertIn("ck-cell-c", center)
        # Default left has no alignment class (the base is left)
        self.assertNotIn("ck-cell-r", left)
        self.assertNotIn("ck-cell-c", left)

    def test_tone_modifier_classes(self):
        for tone in ("dim", "pos", "neg", "acc"):
            html = ck_data_cell("X", tone=tone)
            self.assertIn(f"tone-{tone}", html)

    def test_unknown_tone_is_silently_dropped(self):
        # Defensive: an unknown tone shouldn't emit garbage class
        html = ck_data_cell("X", tone="bogus")
        self.assertNotIn("tone-bogus", html)
        self.assertNotIn("tone-", html)

    def test_weight_modifier_classes(self):
        html_700 = ck_data_cell("Bold", weight=700)
        html_600 = ck_data_cell("Semi", weight=600)
        self.assertIn("ck-cell-w-700", html_700)
        self.assertIn("ck-cell-w-600", html_600)

    def test_unknown_weight_is_silently_dropped(self):
        html = ck_data_cell("X", weight=400)
        self.assertNotIn("ck-cell-w-", html)

    def test_typical_dpi_tracker_cell(self):
        # Real-world shape: right-aligned mono numeric cell with
        # accent tone + bold weight. Replaces the ~700-instance
        # pattern in dpi_tracker_page.py and friends.
        html = ck_data_cell(
            "2.40x", align="right", mono=True, tone="acc", weight=600,
        )
        for cls in (
            "ck-cell", "ck-cell-mono", "ck-cell-r", "tone-acc", "ck-cell-w-600",
        ):
            self.assertIn(cls, html)
        self.assertIn(">2.40x</td>", html)

    def test_value_renders_verbatim(self):
        # The helper does NOT html-escape — caller must pre-escape.
        # This matches the cycle-6 ck_table convention and lets
        # callers embed pre-rendered HTML (e.g. badge spans).
        html = ck_data_cell("<span>X</span>")
        self.assertIn("<span>X</span>", html)


if __name__ == "__main__":
    unittest.main()
