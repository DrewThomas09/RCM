"""tests for the diligence four-phase tab strip.

PROMPTS.md Phase 3 / Prompt 36: 16+ flat diligence tabs are
unscannable. The helper carries the four-phase grouping that already
exists on the diligence front page into the secondary navigation.

Tests pin: clicking each phase routes to its first child;
deep-linking to a child highlights the parent phase; an unknown
path falls through to the first phase.
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.ui._ui_kit import DILIGENCE_PHASES, diligence_phase_nav


class FourPhasesPresent(unittest.TestCase):

    def test_four_phases_defined(self) -> None:
        self.assertEqual(len(DILIGENCE_PHASES), 4)

    def test_phase_keys(self) -> None:
        keys = [p["key"] for p in DILIGENCE_PHASES]
        self.assertEqual(keys, ["profile", "thesis", "audit", "exit"])

    def test_each_phase_has_children(self) -> None:
        for phase in DILIGENCE_PHASES:
            with self.subTest(phase=phase["key"]):
                self.assertGreater(len(phase["children"]), 0)


class PhaseHeaderLinking(unittest.TestCase):

    def test_phase_header_links_to_first_child(self) -> None:
        # Each phase header href should be the first child's href.
        html = diligence_phase_nav(active_path="")
        for phase in DILIGENCE_PHASES:
            first_href = phase["children"][0]["href"]
            with self.subTest(phase=phase["key"]):
                self.assertIn(
                    f'data-phase="{phase["key"]}"',
                    html,
                )
                self.assertIn(f'href="{first_href}"', html)


class ActiveStateHighlights(unittest.TestCase):

    def test_active_child_highlights_parent_phase(self) -> None:
        # /diligence/bridge-audit is under "audit" — that phase
        # link must carry .active. The other three must not.
        html = diligence_phase_nav(active_path="/diligence/bridge-audit")
        # Pull all phase-link tags and check class assignments.
        phase_tags = re.findall(
            r'<a class="phase-link[^"]*" href="[^"]*" '
            r'data-phase="(\w+)">',
            html,
        )
        # Order of phase tags matches DILIGENCE_PHASES order.
        self.assertEqual(phase_tags, ["profile", "thesis", "audit", "exit"])
        # Active phase carries the active class; others don't.
        self.assertIn(
            'class="phase-link active" href',
            html,
        )
        # Match the audit phase specifically.
        m = re.search(
            r'class="phase-link active"[^>]*data-phase="audit"',
            html,
        )
        self.assertIsNotNone(m)

    def test_active_child_carries_child_active_class(self) -> None:
        html = diligence_phase_nav(active_path="/diligence/bridge-audit")
        m = re.search(
            r'<a class="child-link active" href="/diligence/bridge-audit">',
            html,
        )
        self.assertIsNotNone(m)


class UnknownPathFallsThroughCleanly(unittest.TestCase):

    def test_unknown_path_falls_through_to_first_phase(self) -> None:
        # Unknown paths fall through to the first phase as the
        # active row — better than rendering a blank child strip.
        # No child should be marked active, but the first phase IS
        # the active phase.
        html = diligence_phase_nav(active_path="/some/unrelated/route")
        self.assertNotIn('class="child-link active"', html)
        # First phase header marked active so the user has a row of
        # tabs to click on, not an empty bar.
        self.assertIn(
            'class="phase-link active" href="/diligence/checklist"',
            html,
        )


if __name__ == "__main__":
    unittest.main()
