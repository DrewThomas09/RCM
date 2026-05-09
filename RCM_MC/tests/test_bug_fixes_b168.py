"""b168 — Bear Case primary CTA color.

PROMPTS.md Phase 1 / Prompt 7: the "Generate bear case" button on
/diligence/bear-case rendered with the platform's red/negative
severity colour. Red signals destruction in this token system —
reserved for delete/reset — so colouring a primary form-submit red
read as "this will erase something" rather than "run analysis".

Fix: switch ``.bc-form-submit`` to the accent (Chartis blue) token
that every other primary CTA on diligence pages uses.
"""
from __future__ import annotations

import re
import unittest


class BearCaseSubmitColor(unittest.TestCase):

    def test_submit_uses_accent_not_negative(self) -> None:
        from rcm_mc.ui._chartis_kit import P
        from rcm_mc.ui.bear_case_page import _scoped_styles

        css = _scoped_styles()
        # Pull the .bc-form-submit rule body.
        m = re.search(r"\.bc-form-submit\{[^}]*\}", css)
        self.assertIsNotNone(m, "bc-form-submit rule missing")
        rule = m.group(0)
        # The rule must reference the accent colour, not negative.
        self.assertIn(
            f"background:{P['accent']}", rule,
            "bc-form-submit must use the accent token (Chartis blue), "
            "not the negative/red token",
        )
        self.assertNotIn(
            f"background:{P['negative']}", rule,
            "bc-form-submit must not use the negative/red token "
            "for a primary action",
        )


if __name__ == "__main__":
    unittest.main()
