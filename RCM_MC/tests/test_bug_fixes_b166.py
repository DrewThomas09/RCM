"""b166 — deal-sourcing table font density.

PROMPTS.md Phase 1 / Prompt 5: the loaded /deal-sourcing tables
rendered at ``font-size:11px`` while the rest of the app's tables
use the kit standard 13px / 11px-header pair. Visually the page
read as a different (smaller) typeface than every other table in
the platform.

Fix: align the inline cell + table-level font-sizes with the kit
standard. Stage-chip badges keep their smaller 10/11px to preserve
visual hierarchy.
"""
from __future__ import annotations

import unittest


class DealSourcingFontDensity(unittest.TestCase):

    def test_table_default_font_size_matches_kit_standard(self) -> None:
        from rcm_mc.ui.data_public.deal_sourcing_page import (
            _funnel_table, _channels_table,
        )

        # Render with empty input lists — the table-level font-size
        # declaration is independent of row content.
        funnel_html = _funnel_table([])
        channels_html = _channels_table([])

        # Both tables must declare the kit's 13px body size at the
        # <table> level. The previous bug had this at 11px.
        signature = (
            '<table style="width:100%;border-collapse:collapse;'
            'font-size:13px">'
        )
        self.assertIn(signature, funnel_html)
        self.assertIn(signature, channels_html)

    def test_no_residual_11px_table_default(self) -> None:
        # Pin that no <table> declaration regresses to 11px.
        from rcm_mc.ui.data_public.deal_sourcing_page import (
            _funnel_table, _channels_table,
        )
        for renderer in (_funnel_table, _channels_table):
            html = renderer([])
            self.assertNotIn(
                'border-collapse:collapse;font-size:11px"', html,
                f"{renderer.__name__} regressed to 11px table default",
            )


if __name__ == "__main__":
    unittest.main()
