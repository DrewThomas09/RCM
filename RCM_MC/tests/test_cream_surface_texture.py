"""tests for the subtle paper texture on cream surfaces.

PROMPTS.md Phase 2 / Prompt 24. Marketing critique noted the cream
sections feel sterile; a barely-visible dot grid at <3% opacity
lifts them. Pin that the rule exists and reads as background-image
data-URI on body / cream-surface containers.
"""
from __future__ import annotations

import os
import re
import sys
import unittest


class TextureRulePresent(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        os.environ["CHARTIS_UI_V2"] = "1"
        for name in list(sys.modules):
            if name.startswith("rcm_mc.ui._chartis_kit"):
                sys.modules.pop(name, None)
        from rcm_mc.ui._chartis_kit import chartis_shell
        cls.html = chartis_shell("<p>x</p>", "T")

    def test_body_has_background_image(self) -> None:
        # Match the body { background-image: url(...) } declaration.
        self.assertRegex(
            self.html,
            r"body[^{]*\{[^}]*background-image:url\(",
        )

    def test_uses_inline_svg_data_uri(self) -> None:
        self.assertIn("data:image/svg+xml", self.html)

    def test_opacity_is_subtle(self) -> None:
        # The dot fill-opacity must be ≤ 0.03 — felt, not seen.
        m = re.search(r"fill-opacity='([0-9.]+)'", self.html)
        self.assertIsNotNone(m, "no fill-opacity in texture SVG")
        self.assertLessEqual(float(m.group(1)), 0.03)


if __name__ == "__main__":
    unittest.main()
