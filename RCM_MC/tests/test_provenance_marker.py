"""tests for ``rcm_mc.ui._ui_kit.provenance_marker``.

PROMPTS.md Phase 2 / Prompt 17. Tests cover each documented source,
confidence-level → opacity, escaped title detail, and graceful
fallback when an unknown source string is passed.
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.ui._ui_kit import provenance_marker


class GlyphPerSource(unittest.TestCase):

    EXPECTATIONS = {
        # source string,          glyph,  family
        "USER_INPUT":             ("●", "observed"),
        "HCRIS":                  ("●", "observed"),
        "IRS990":                 ("●", "observed"),
        "REGRESSION_PREDICTED":   ("◐", "predicted"),
        "MONTE_CARLO_P50":        ("◆", "simulated"),
        "CALCULATED":             ("▴", "derived"),
        "BENCHMARK_MEDIAN":       ("○", "benchmark"),
    }

    def test_each_source_emits_its_glyph_and_family(self) -> None:
        for source, (glyph, family) in self.EXPECTATIONS.items():
            with self.subTest(source=source):
                html = provenance_marker(source)
                self.assertIn(glyph, html)
                self.assertIn(f"prov-{family}", html)
                self.assertIn(f'data-source="{source}"', html)


class ConfidenceOpacity(unittest.TestCase):

    def test_confidence_emits_opacity_style(self) -> None:
        html = provenance_marker("REGRESSION_PREDICTED", confidence=0.85)
        m = re.search(r'style="opacity:([0-9.]+)"', html)
        self.assertIsNotNone(m)
        self.assertAlmostEqual(float(m.group(1)), 0.85, places=2)

    def test_confidence_clamps_at_floor(self) -> None:
        # A 0.05 confidence still renders visibly at min 0.30.
        html = provenance_marker("REGRESSION_PREDICTED", confidence=0.05)
        m = re.search(r'opacity:([0-9.]+)', html)
        self.assertIsNotNone(m)
        self.assertAlmostEqual(float(m.group(1)), 0.30, places=2)

    def test_no_confidence_means_no_opacity_style(self) -> None:
        html = provenance_marker("HCRIS")
        self.assertNotIn("opacity", html)


class TitleAttribute(unittest.TestCase):

    def test_detail_emitted_as_title(self) -> None:
        html = provenance_marker(
            "HCRIS",
            detail="HCRIS 2024 cost report, worksheet S-3 line 4",
        )
        self.assertIn('title="HCRIS 2024 cost report', html)

    def test_detail_html_escaped(self) -> None:
        html = provenance_marker(
            "HCRIS",
            detail='<script>alert("x")</script>',
        )
        # Title attribute must escape both < > and the literal quote.
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&quot;", html)


class UnknownSourceFallback(unittest.TestCase):

    def test_unknown_source_renders_fallback_glyph(self) -> None:
        html = provenance_marker("MADE_UP_SOURCE_TYPE")
        # Must NOT raise; must NOT empty the marker; family is unknown.
        self.assertIn("prov-unknown", html)
        self.assertIn("·", html)
        self.assertIn('data-source="MADE_UP_SOURCE_TYPE"', html)


if __name__ == "__main__":
    unittest.main()
