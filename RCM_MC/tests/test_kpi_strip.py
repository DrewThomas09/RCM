"""tests for ``rcm_mc.ui._ui_kit.kpi_strip``.

PROMPTS.md Phase 2 / Prompt 11. The helper renders a horizontal KPI
row used across Library, Alerts, Watchlist, IRR Analysis, Hold
Analysis, etc. Per the spec these tests cover:

* item counts 1, 3, 5, 8 — column count comes through correctly
* missing sublabels render cleanly
* every documented tone applies a tone-class on the item
* dense mode triggers via explicit flag and via len > 5
* mobile breakpoint CSS is present in the shared kit stylesheet
"""
from __future__ import annotations

import os
import re
import sys
import unittest


def _kpi(label: str, value: str, **extra) -> dict:
    return {"label": label, "value": value, **extra}


class ColumnCountThroughInline(unittest.TestCase):

    def setUp(self) -> None:
        from rcm_mc.ui._ui_kit import kpi_strip
        self.kpi_strip = kpi_strip

    def _column_count(self, html: str) -> int:
        m = re.search(r"grid-template-columns:repeat\((\d+),1fr\)", html)
        self.assertIsNotNone(m, f"no grid-template-columns in: {html}")
        return int(m.group(1))

    def test_one_item(self) -> None:
        html = self.kpi_strip([_kpi("ALPHA", "1")])
        self.assertEqual(self._column_count(html), 1)

    def test_three_items(self) -> None:
        html = self.kpi_strip(
            [_kpi(f"L{i}", str(i)) for i in range(3)]
        )
        self.assertEqual(self._column_count(html), 3)

    def test_five_items(self) -> None:
        html = self.kpi_strip(
            [_kpi(f"L{i}", str(i)) for i in range(5)]
        )
        self.assertEqual(self._column_count(html), 5)

    def test_eight_items(self) -> None:
        html = self.kpi_strip(
            [_kpi(f"L{i}", str(i)) for i in range(8)]
        )
        self.assertEqual(self._column_count(html), 8)

    def test_empty_returns_empty_string(self) -> None:
        # Empty list short-circuits — no markup, no orphaned wrapper.
        self.assertEqual(self.kpi_strip([]), "")


class SublabelHandling(unittest.TestCase):

    def setUp(self) -> None:
        from rcm_mc.ui._ui_kit import kpi_strip
        self.kpi_strip = kpi_strip

    def test_sublabel_renders_when_provided(self) -> None:
        html = self.kpi_strip([_kpi("L", "1", sublabel="in corpus")])
        self.assertIn("kpi-sublabel", html)
        self.assertIn("in corpus", html)

    def test_no_sublabel_div_when_omitted(self) -> None:
        html = self.kpi_strip([_kpi("L", "1")])
        self.assertNotIn("kpi-sublabel", html)


class TonesApply(unittest.TestCase):

    def setUp(self) -> None:
        from rcm_mc.ui._ui_kit import kpi_strip
        self.kpi_strip = kpi_strip

    def test_each_tone_applies_class(self) -> None:
        for tone in ("neutral", "positive", "negative", "warning"):
            with self.subTest(tone=tone):
                html = self.kpi_strip([_kpi("L", "1", tone=tone)])
                self.assertIn(f"tone-{tone}", html)

    def test_invalid_tone_falls_back_to_neutral(self) -> None:
        # Defensive: a typo in the caller shouldn't break rendering.
        html = self.kpi_strip([_kpi("L", "1", tone="purple")])
        self.assertIn("tone-neutral", html)
        self.assertNotIn("tone-purple", html)


class DenseMode(unittest.TestCase):

    def setUp(self) -> None:
        from rcm_mc.ui._ui_kit import kpi_strip
        self.kpi_strip = kpi_strip

    def test_dense_flag_adds_modifier_class(self) -> None:
        html = self.kpi_strip([_kpi("L", "1")], dense=True)
        self.assertIn("kpi-strip-dense", html)

    def test_six_items_auto_dense(self) -> None:
        # Per spec: > 5 items auto-densifies so the strip still fits.
        html = self.kpi_strip(
            [_kpi(f"L{i}", str(i)) for i in range(6)]
        )
        self.assertIn("kpi-strip-dense", html)

    def test_five_items_not_dense_unless_flagged(self) -> None:
        html = self.kpi_strip(
            [_kpi(f"L{i}", str(i)) for i in range(5)]
        )
        self.assertNotIn("kpi-strip-dense", html)


class ResponsiveCSSPresent(unittest.TestCase):
    """The shared kit CSS must include the 768/480 breakpoints so the
    strip degrades to 2 then 1 column on narrow viewports."""

    def setUp(self) -> None:
        # Force v2 on so the kit's CSS path is the active one.
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
        from rcm_mc.ui._chartis_kit import chartis_shell
        self.html = chartis_shell("<p>x</p>", "T")

    def test_768_breakpoint_collapses_to_two_columns(self) -> None:
        self.assertRegex(
            self.html,
            r"@media\s*\(max-width:768px\)\s*\{[^}]*\.kpi-strip[^}]*"
            r"grid-template-columns:repeat\(2,1fr\)",
        )

    def test_480_breakpoint_collapses_to_one_column(self) -> None:
        self.assertRegex(
            self.html,
            r"@media\s*\(max-width:480px\)\s*\{[^}]*\.kpi-strip[^}]*"
            r"grid-template-columns:1fr",
        )


class HtmlEscapesLabel(unittest.TestCase):

    def test_label_is_escaped(self) -> None:
        from rcm_mc.ui._ui_kit import kpi_strip

        html = kpi_strip([_kpi("<b>bad</b>", "1")])
        self.assertNotIn("<b>bad", html)
        self.assertIn("&lt;b&gt;bad&lt;/b&gt;", html)


if __name__ == "__main__":
    unittest.main()
