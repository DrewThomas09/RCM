"""b165 — marketing CTA contrast on the navy callout strip.

PROMPTS.md Phase 1 / Prompt 4: the "Ready to diligence" callout box on
the marketing page rendered the primary CTA as a navy button on a navy
background — the button silhouette disappeared and the headline
flagged as unreadable in marketing review.

Fix: ``_cta_primary`` now accepts ``on_navy=True`` and flips its fill
to bone with navy text. The callout strip passes the flag.

This regression pins the visual contract.
"""
from __future__ import annotations

import re
import unittest


class CalloutCTAContrast(unittest.TestCase):

    def setUp(self) -> None:
        from rcm_mc.ui.chartis.marketing_page import render_marketing_page
        self.html = render_marketing_page()

    def test_callout_primary_button_does_not_blend_into_navy_strip(
        self,
    ) -> None:
        # Locate the "Ready to diligence" eyebrow and inspect the
        # surrounding ~3kB of markup — that is the callout strip.
        idx = self.html.find("Ready to diligence")
        self.assertGreater(idx, 0, "Ready-to-diligence callout missing")
        section = self.html[idx : idx + 3000]
        # The Open Platform CTA inside this section must NOT use a
        # navy background (which would merge with the strip's navy
        # surface and erase the button shape).
        m = re.search(
            r'<a[^>]*background:var\(--sc-bone\)[^>]*>[^<]*Open Platform',
            section,
        )
        self.assertIsNotNone(
            m,
            "Open Platform CTA in the navy callout must use a bone fill, "
            "not navy — otherwise the button silhouette disappears",
        )

    def test_callout_headline_still_readable(self) -> None:
        # The headline above the CTA should be cream-on-navy. We pin
        # that the on_navy h_section keeps the on-navy text token.
        idx = self.html.find("Ready to diligence")
        section = self.html[idx : idx + 3000]
        # Find the headline H2 and confirm its color token.
        m = re.search(
            r'<h2[^>]*color:var\(--sc-on-navy\)[^>]*>'
            r'[^<]*Open the platform',
            section,
        )
        self.assertIsNotNone(
            m,
            "Headline must use --sc-on-navy (cream) on the navy strip",
        )


if __name__ == "__main__":
    unittest.main()
