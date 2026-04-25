"""Tests for provenance icons + click-to-see-source popover."""
from __future__ import annotations

import unittest


class TestSourceIcons(unittest.TestCase):
    def test_known_sources_have_icons(self):
        from rcm_mc.ui.provenance_badge import SOURCE_ICONS
        for src in [
            "USER_INPUT", "HCRIS", "IRS990",
            "REGRESSION_PREDICTED", "BENCHMARK_MEDIAN",
            "MONTE_CARLO_P50", "CALCULATED",
        ]:
            self.assertIn(src, SOURCE_ICONS)
            self.assertTrue(SOURCE_ICONS[src])


class TestProvenanceBadgeWithDataPoint(unittest.TestCase):
    def _datapoint(self):
        from rcm_mc.provenance.tracker import (
            DataPoint, Source,
        )
        from datetime import date
        return DataPoint(
            value=0.10,
            metric_name="denial_rate",
            source=Source.REGRESSION_PREDICTED,
            source_detail=(
                "Ridge regression on 47 comparable "
                "hospitals, R²=0.84"),
            confidence=0.84,
            as_of_date=date(2024, 1, 1),
        )

    def test_renders_value_and_icon(self):
        from rcm_mc.ui.provenance_badge import (
            provenance_badge,
        )
        html = provenance_badge(self._datapoint())
        # Default formatted value
        self.assertIn("0.100", html)
        # Icon present
        self.assertIn("◈", html)
        # Source label in card
        self.assertIn("Regression prediction", html)
        # Detail in card
        self.assertIn("R²=0.84", html)

    def test_confidence_badge_rendered(self):
        from rcm_mc.ui.provenance_badge import (
            provenance_badge,
        )
        html = provenance_badge(self._datapoint())
        # 84% confidence
        self.assertIn("84%", html)
        # Watch-band background since 0.60 ≤ 0.84 < 0.85
        self.assertIn("#92400e", html)

    def test_explicit_value_html(self):
        from rcm_mc.ui.provenance_badge import (
            provenance_badge,
        )
        html = provenance_badge(
            self._datapoint(), value_html="10.0%")
        self.assertIn("10.0%", html)
        # Default '0.100' should NOT appear
        self.assertNotIn(">0.100<", html)


class TestProvenanceWithDict(unittest.TestCase):
    def test_dict_input(self):
        from rcm_mc.ui.provenance_badge import (
            provenance_badge,
        )
        html = provenance_badge({
            "value": 42.5,
            "source": "HCRIS",
            "source_detail": "FY2023 CCN 010001",
            "confidence": 1.0,
            "sample_size": 5_000,
        }, value_html="42.5")
        self.assertIn("42.5", html)
        self.assertIn("HCRIS public data", html)
        self.assertIn("n = 5,000", html)
        # Confidence 100% → positive band
        self.assertIn("100%", html)
        self.assertIn("#065f46", html)


class TestProvenanceUpstream(unittest.TestCase):
    def test_upstream_chain_rendered(self):
        from rcm_mc.ui.provenance_badge import (
            provenance_badge,
        )
        html = provenance_badge({
            "value": 5_000_000,
            "source": "CALCULATED",
            "source_detail": "Bridge sum",
            "confidence": 0.90,
            "upstream": [
                {"metric_name": "denial_rate",
                 "source": "REGRESSION_PREDICTED"},
                {"metric_name": "days_in_ar",
                 "source": "REGRESSION_PREDICTED"},
            ],
        })
        self.assertIn("Upstream", html)
        self.assertIn("denial_rate", html)
        self.assertIn("days_in_ar", html)


class TestIconOnly(unittest.TestCase):
    def test_renders_only_icon_no_value(self):
        from rcm_mc.ui.provenance_badge import (
            provenance_icon_only,
        )
        html = provenance_icon_only({
            "source": "BENCHMARK_MEDIAN",
            "source_detail": "Peer p50",
            "confidence": 0.7,
        })
        # Icon present, no value HTML
        self.assertIn("◇", html)
        self.assertIn("Peer benchmark median", html)
        # No 'pv' wrapper around a value
        # (the icon-only form uses <details> directly)
        self.assertIn("<details", html)


class TestConfidenceBands(unittest.TestCase):
    def test_high_confidence_green(self):
        from rcm_mc.ui.provenance_badge import (
            _confidence_kind, _confidence_color,
        )
        self.assertEqual(
            _confidence_kind(0.92), "positive")
        self.assertEqual(
            _confidence_color(0.92), "#10b981")

    def test_medium_confidence_amber(self):
        from rcm_mc.ui.provenance_badge import (
            _confidence_kind,
        )
        self.assertEqual(
            _confidence_kind(0.70), "watch")

    def test_low_confidence_red(self):
        from rcm_mc.ui.provenance_badge import (
            _confidence_kind,
        )
        self.assertEqual(
            _confidence_kind(0.40), "negative")

    def test_none_confidence_neutral(self):
        from rcm_mc.ui.provenance_badge import (
            _confidence_kind,
        )
        self.assertEqual(
            _confidence_kind(None), "neutral")


class TestHtmlEscape(unittest.TestCase):
    def test_escapes_source_detail(self):
        from rcm_mc.ui.provenance_badge import (
            provenance_badge,
        )
        html = provenance_badge({
            "value": 1,
            "source": "HCRIS",
            "source_detail": "<script>x</script>",
        })
        self.assertNotIn("<script>x", html)
        self.assertIn("&lt;script&gt;", html)


class TestCSSToggle(unittest.TestCase):
    def test_inject_css_disabled(self):
        from rcm_mc.ui.provenance_badge import (
            provenance_badge,
        )
        html = provenance_badge(
            {"value": 1, "source": "HCRIS"},
            inject_css=False)
        # Stylesheet not embedded
        self.assertNotIn("<style>", html)
        # But the structure is there
        self.assertIn("<details", html)


if __name__ == "__main__":
    unittest.main()
