"""tests for the shared motion tokens.

PROMPTS.md Phase 2 / Prompt 19. The kit's CSS must declare six
motion tokens at :root so components can reach for them instead of
hardcoding timing/easing values.
"""
from __future__ import annotations

import os
import re
import sys
import unittest


class MotionTokensDeclared(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
        from rcm_mc.ui._chartis_kit import chartis_shell
        cls.html = chartis_shell("<p>x</p>", "T")

    def test_durations(self) -> None:
        for token in ("--motion-fast", "--motion-base", "--motion-slow"):
            with self.subTest(token=token):
                self.assertIn(token, self.html)

    def test_easings(self) -> None:
        for token in (
            "--ease-standard", "--ease-decelerate", "--ease-accelerate",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.html)

    def test_no_legacy_inline_03s_transition(self) -> None:
        # The acceptance step from PROMPTS.md: zero remaining inline
        # ``transition: 0.3s`` strings. Allow ``transition:`` followed
        # by a token reference (var(--motion-…)) — only flag literal
        # 0.3s declarations.
        legacy = re.findall(
            r"transition\s*:\s*0\.3s",
            self.html,
        )
        self.assertEqual(legacy, [],
            "legacy 'transition: 0.3s ease' strings must be replaced "
            "with motion tokens",
        )


if __name__ == "__main__":
    unittest.main()
