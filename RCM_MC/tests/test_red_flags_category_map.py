"""Wave-9 visual: red-flags category × severity cluster map.

The red-flags page sorted hits by severity but never showed *where*
they cluster — which diligence categories the fired triggers live in.
Pins the stacked-bar SVG: severity tones, severity-weighted row order,
and the empty state rendering nothing.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from rcm_mc.ui.chartis.red_flags_page import _SEV_COLORS, _category_severity_svg


def _hit(category: str, severity: str) -> SimpleNamespace:
    return SimpleNamespace(category=category, severity=severity)


def _review(hits) -> SimpleNamespace:
    return SimpleNamespace(heuristic_hits=hits)


class CategorySeverityMapTests(unittest.TestCase):
    def test_renders_stacked_bars_with_severity_tones(self):
        svg = _category_severity_svg(_review([
            _hit("Financial", "CRITICAL"),
            _hit("Financial", "MEDIUM"),
            _hit("Regulatory", "HIGH"),
            _hit("Labor", "LOW"),
        ]))
        self.assertIn("<svg", svg)
        self.assertIn("ck-rf-category-map", svg)
        self.assertIn("Where the Flags Cluster", svg)
        for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            self.assertIn(_SEV_COLORS[sev], svg)

    def test_rows_sorted_by_severity_weight(self):
        # One CRITICAL (weight 8) outranks three LOWs (weight 3).
        svg = _category_severity_svg(_review([
            _hit("Labor", "LOW"),
            _hit("Labor", "LOW"),
            _hit("Labor", "LOW"),
            _hit("Regulatory", "CRITICAL"),
        ]))
        self.assertLess(svg.index("Regulatory"), svg.index("Labor"))

    def test_missing_category_buckets_as_uncategorized(self):
        svg = _category_severity_svg(_review([
            SimpleNamespace(category=None, severity="HIGH"),
        ]))
        self.assertIn("Uncategorized", svg)

    def test_unknown_severity_treated_as_low(self):
        svg = _category_severity_svg(_review([
            SimpleNamespace(category="Other", severity="WEIRD"),
        ]))
        self.assertIn(_SEV_COLORS["LOW"], svg)

    def test_no_hits_renders_nothing(self):
        self.assertEqual(_category_severity_svg(_review([])), "")
        self.assertEqual(_category_severity_svg(_review(None)), "")


if __name__ == "__main__":
    unittest.main()
