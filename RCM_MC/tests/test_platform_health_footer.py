"""tests for ``platform_health_footer`` (P62)."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from rcm_mc.ui._ui_kit import platform_health_footer


class FullMetricsFooter(unittest.TestCase):

    def setUp(self) -> None:
        self.html = platform_health_footer({
            "version": "1.0",
            "tests_passing": 2878,
            "hcris_refreshed": (
                datetime.now(timezone.utc) - timedelta(hours=2)
            ).isoformat(),
            "packet_cache_hit": 0.94,
            "mc_coverage": 0.91,
        })

    def test_renders_footer_element(self) -> None:
        self.assertIn("platform-health-footer", self.html)

    def test_version_shown(self) -> None:
        self.assertIn("Platform v1.0", self.html)

    def test_test_count_with_thousands_separator(self) -> None:
        self.assertIn("2,878 tests passing", self.html)

    def test_hcris_freshness(self) -> None:
        self.assertIn("HCRIS refreshed", self.html)
        self.assertIn("h ago", self.html)

    def test_cache_hit_rendered_as_pct(self) -> None:
        self.assertIn("packet cache 94% hit", self.html)

    def test_mc_coverage_rendered_as_pct(self) -> None:
        self.assertIn("MC calibration coverage 91%", self.html)


class PartialMetrics(unittest.TestCase):

    def test_only_supplied_keys_render(self) -> None:
        html = platform_health_footer({"version": "1.0"})
        self.assertIn("Platform v1.0", html)
        self.assertNotIn("tests passing", html)
        self.assertNotIn("HCRIS", html)

    def test_invalid_floats_skipped(self) -> None:
        # Non-numeric percent values are silently dropped rather
        # than rendering "nan%" — ugly numbers are worse than
        # missing rails.
        html = platform_health_footer({
            "version": "1.0",
            "packet_cache_hit": "not-a-number",
        })
        self.assertIn("Platform v1.0", html)
        self.assertNotIn("packet cache", html)


class EmptyOrNoneCollapses(unittest.TestCase):

    def test_none_returns_empty(self) -> None:
        self.assertEqual(platform_health_footer(None), "")

    def test_empty_dict_returns_empty(self) -> None:
        self.assertEqual(platform_health_footer({}), "")

    def test_unknown_keys_only_returns_empty(self) -> None:
        self.assertEqual(
            platform_health_footer({"random": "value"}),
            "",
        )


if __name__ == "__main__":
    unittest.main()
