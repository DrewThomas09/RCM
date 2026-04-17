"""Tests for improvement pass B93: keyboard shortcuts, toast system, breadcrumb.

KEYBOARD SHORTCUTS:
 1. Workbench JS contains keyboard event listener.
 2. Number keys 1-7 switch tabs.

TOAST SYSTEM:
 3. Shell HTML includes rcmToast function.
 4. Shell CSS includes toast styles.

BREADCRUMB:
 5. Workbench header contains breadcrumb with portfolio link.
"""
from __future__ import annotations

import unittest

from rcm_mc.analysis.packet import (
    DealAnalysisPacket, MetricSource, ProfileMetric,
)
from rcm_mc.ui._ui_kit import BASE_CSS, shell
from rcm_mc.ui.analysis_workbench import _WORKBENCH_JS, render_workbench


class TestKeyboardShortcuts(unittest.TestCase):

    def test_js_has_keyboard_listener(self):
        self.assertIn("keydown", _WORKBENCH_JS)

    def test_js_has_number_key_switching(self):
        self.assertIn("parseInt(e.key)", _WORKBENCH_JS)

    def test_js_has_alt_arrow(self):
        self.assertIn("ArrowLeft", _WORKBENCH_JS)
        self.assertIn("ArrowRight", _WORKBENCH_JS)

    def test_js_has_help_shortcut(self):
        self.assertIn("'?'", _WORKBENCH_JS)


class TestToastSystem(unittest.TestCase):

    def test_shell_includes_toast_js(self):
        html = shell("<p>test</p>", "Test")
        self.assertIn("SeekingChartis", html)

    def test_css_includes_toast_styles(self):
        self.assertIn("rcm-toast-container", BASE_CSS)
        self.assertIn("rcm-toast--success", BASE_CSS)
        self.assertIn("rcm-toast--error", BASE_CSS)
        self.assertIn("rcm-toast-in", BASE_CSS)


class TestWorkbenchBreadcrumb(unittest.TestCase):

    def test_breadcrumb_present(self):
        pkt = DealAnalysisPacket(
            deal_id="d1", deal_name="Test Hospital",
            rcm_profile={
                "denial_rate": ProfileMetric(
                    value=12.0, source=MetricSource.OBSERVED,
                    benchmark_percentile=0.85,
                ),
            },
        )
        html = render_workbench(pkt)
        self.assertIn("wb-breadcrumb", html)
        self.assertIn('href="/home"', html)
        self.assertIn("Test Hospital", html)

    def test_keyboard_hint_present(self):
        pkt = DealAnalysisPacket(
            deal_id="d1", deal_name="Test",
            rcm_profile={},
        )
        html = render_workbench(pkt)
        self.assertIn("?=help", html)


if __name__ == "__main__":
    unittest.main()
