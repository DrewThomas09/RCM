"""Tests for the semantic color system."""
from __future__ import annotations

import unittest


class TestStatusColor(unittest.TestCase):
    def test_lower_is_better(self):
        from rcm_mc.ui.colors import (
            STATUS, status_color,
        )
        # Denial rate: <0.08 good, >0.12 bad, between watch
        self.assertEqual(
            status_color(0.05, low_threshold=0.08,
                         high_threshold=0.12),
            STATUS["positive"])
        self.assertEqual(
            status_color(0.10, low_threshold=0.08,
                         high_threshold=0.12),
            STATUS["watch"])
        self.assertEqual(
            status_color(0.18, low_threshold=0.08,
                         high_threshold=0.12),
            STATUS["negative"])

    def test_higher_is_better(self):
        from rcm_mc.ui.colors import (
            STATUS, status_color,
        )
        # Collection rate: >0.97 good, <0.92 bad
        self.assertEqual(
            status_color(0.98, low_threshold=0.92,
                         high_threshold=0.97,
                         lower_is_better=False),
            STATUS["positive"])
        self.assertEqual(
            status_color(0.85, low_threshold=0.92,
                         high_threshold=0.97,
                         lower_is_better=False),
            STATUS["negative"])

    def test_none_returns_neutral(self):
        from rcm_mc.ui.colors import (
            STATUS, status_color,
        )
        self.assertEqual(
            status_color(None, low_threshold=0,
                         high_threshold=1),
            STATUS["neutral"])


class TestPeerColor(unittest.TestCase):
    def test_lower_is_better_above_peer(self):
        from rcm_mc.ui.colors import STATUS, peer_color
        # Denial rate 12% vs peer 10% (20% above) → red
        self.assertEqual(
            peer_color(0.12, 0.10),
            STATUS["negative"])

    def test_lower_is_better_below_peer(self):
        from rcm_mc.ui.colors import STATUS, peer_color
        # Denial rate 8% vs peer 10% (20% below) → green
        self.assertEqual(
            peer_color(0.08, 0.10),
            STATUS["positive"])

    def test_within_significance_band(self):
        from rcm_mc.ui.colors import STATUS, peer_color
        # Within ±10% → neutral
        self.assertEqual(
            peer_color(0.105, 0.10),
            STATUS["neutral"])

    def test_higher_is_better_inverted(self):
        from rcm_mc.ui.colors import STATUS, peer_color
        # Collection 0.98 vs peer 0.85 (well above) → green
        self.assertEqual(
            peer_color(0.98, 0.85,
                       lower_is_better=False),
            STATUS["positive"])
        # Collection 0.70 vs peer 0.85 (well below) → red
        self.assertEqual(
            peer_color(0.70, 0.85,
                       lower_is_better=False),
            STATUS["negative"])

    def test_none_or_zero_returns_neutral(self):
        from rcm_mc.ui.colors import STATUS, peer_color
        self.assertEqual(
            peer_color(None, 0.10), STATUS["neutral"])
        self.assertEqual(
            peer_color(0.10, None), STATUS["neutral"])
        self.assertEqual(
            peer_color(0.10, 0), STATUS["neutral"])


class TestChangeColor(unittest.TestCase):
    def test_growth_is_green(self):
        from rcm_mc.ui.colors import STATUS, change_color
        self.assertEqual(
            change_color(0.05), STATUS["positive"])

    def test_shrinkage_is_red(self):
        from rcm_mc.ui.colors import STATUS, change_color
        self.assertEqual(
            change_color(-0.05), STATUS["negative"])

    def test_lower_is_better_inverts(self):
        from rcm_mc.ui.colors import STATUS, change_color
        # Denial rate going UP is bad (red)
        self.assertEqual(
            change_color(0.02, lower_is_better=True),
            STATUS["negative"])
        # Going DOWN is good (green)
        self.assertEqual(
            change_color(-0.02, lower_is_better=True),
            STATUS["positive"])

    def test_within_epsilon_neutral(self):
        from rcm_mc.ui.colors import STATUS, change_color
        self.assertEqual(
            change_color(0.001, epsilon=0.005),
            STATUS["neutral"])

    def test_none_neutral(self):
        from rcm_mc.ui.colors import STATUS, change_color
        self.assertEqual(
            change_color(None), STATUS["neutral"])


class TestSeverityColor(unittest.TestCase):
    def test_critical_and_high_red(self):
        from rcm_mc.ui.colors import (
            STATUS, severity_color,
        )
        self.assertEqual(
            severity_color("critical"),
            STATUS["negative"])
        self.assertEqual(
            severity_color("high"), STATUS["negative"])

    def test_medium_and_warning_amber(self):
        from rcm_mc.ui.colors import (
            STATUS, severity_color,
        )
        self.assertEqual(
            severity_color("medium"), STATUS["watch"])
        self.assertEqual(
            severity_color("warning"), STATUS["watch"])

    def test_low_neutral(self):
        from rcm_mc.ui.colors import (
            STATUS, severity_color,
        )
        self.assertEqual(
            severity_color("low"), STATUS["neutral"])

    def test_unknown_neutral(self):
        from rcm_mc.ui.colors import (
            STATUS, severity_color,
        )
        self.assertEqual(
            severity_color("purple"), STATUS["neutral"])
        self.assertEqual(
            severity_color(None), STATUS["neutral"])

    def test_severity_kind(self):
        from rcm_mc.ui.colors import severity_kind
        self.assertEqual(
            severity_kind("critical"), "negative")
        self.assertEqual(
            severity_kind("medium"), "watch")
        self.assertEqual(
            severity_kind("low"), "neutral")


class TestStatusBadge(unittest.TestCase):
    def test_positive_badge(self):
        from rcm_mc.ui.colors import status_badge
        html = status_badge("good", kind="positive")
        # green bg + light green fg
        self.assertIn("#065f46", html)
        self.assertIn("#a7f3d0", html)
        self.assertIn("good", html)

    def test_negative_badge(self):
        from rcm_mc.ui.colors import status_badge
        html = status_badge("bad", kind="negative")
        self.assertIn("#7f1d1d", html)
        self.assertIn("#fecaca", html)

    def test_severity_string_accepted(self):
        """status_badge should accept severity strings as
        kind, mapping them to the canonical kind."""
        from rcm_mc.ui.colors import status_badge
        html = status_badge("critical alert",
                            kind="critical")
        # Should render as negative (red bg)
        self.assertIn("#7f1d1d", html)

    def test_unknown_kind_falls_back_to_neutral(self):
        from rcm_mc.ui.colors import status_badge
        html = status_badge("?", kind="purple")
        # Neutral bg
        self.assertIn("#374151", html)

    def test_size_medium(self):
        from rcm_mc.ui.colors import status_badge
        html = status_badge("x", kind="info", size="medium")
        self.assertIn("13px", html)

    def test_html_escape(self):
        from rcm_mc.ui.colors import status_badge
        html = status_badge("<script>", kind="info")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


class TestStatusDot(unittest.TestCase):
    def test_renders_circle(self):
        from rcm_mc.ui.colors import status_dot
        html = status_dot("positive")
        self.assertIn("border-radius:50%", html)
        self.assertIn("#10b981", html)

    def test_severity_string_mapped(self):
        from rcm_mc.ui.colors import status_dot
        html = status_dot("critical")
        self.assertIn("#ef4444", html)


if __name__ == "__main__":
    unittest.main()
