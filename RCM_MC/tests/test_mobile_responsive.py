"""Mobile/tablet-responsiveness guard for the shared chartis shell.

A 390px-viewport audit (2026-06) found ~50 of ~51 sampled PE Desk pages
forced horizontal *page* scroll on phones, from systemic shared-shell
causes: the topbar never wrapped (~600px), wide data tables overflowed,
the viz|data pair blocks sat side-by-side, and provenance tooltip cards
(``visibility:hidden`` but still in layout, ``min-width:240px``) pushed
the page wide.

A follow-up full-app crawl (2026-06) found the *same* classes of overflow
persisting through the 641–960px tablet range, because the original
safety-net was scoped to ≤640px only (e.g. /portfolio/regression's panel
grid would not stack at 768px; legacy .cad-table stayed unwrapped). The
shell CSS now uses a two-tier design:

  * ``@media (max-width:640px)`` — phone-only topbar/nav wrapping (kept
    narrow so the 7-link nav does not wrap prematurely on tablets).
  * ``@media (max-width:960px)`` — the overflow-prevention rules (table
    scroll, viz|data stack, inline-flex wrap, inline-grid stack, svg
    scaling, tooltip drop-from-flow). These only cap width / stack /
    scroll, so they reach into the tablet range without affecting the
    desktop layout (≥961px), the product's primary target.

This test locks both tiers in so the rules can't be silently dropped, and
asserts each rule lives in the right tier so the overflow net keeps
covering tablets while the nav wrap stays phone-only.
"""
from __future__ import annotations

import re
import unittest

from rcm_mc.ui._chartis_kit import chartis_shell


def _enclosing_media_query(html: str, rule: str) -> str:
    """Return the ``@media (...)`` query string of the block that directly
    encloses the first occurrence of ``rule``.

    Robust to there being several ``@media`` blocks with the same
    breakpoint elsewhere in the CSS: we find the rule, walk back to the
    nearest preceding ``@media`` (these are never nested in this shell),
    and assert the rule really sits inside that block's braces.
    """
    r = html.index(rule)
    q = html.rindex("@media", 0, r)
    start = html.index("{", q)
    query = html[q:start]
    depth, j = 0, start
    while j < len(html):
        if html[j] == "{":
            depth += 1
        elif html[j] == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    assert start < r < j, f"{rule!r} is not inside the {query.strip()!r} block"
    return query


class MobileResponsiveShellTests(unittest.TestCase):
    def setUp(self):
        self.html = chartis_shell("<p>body</p>", title="Mobile Guard")

    def test_mobile_media_blocks_present(self):
        # phone tier (nav wrap) + tablet tier (overflow safety-net)
        self.assertIn(
            "@media (max-width:640px)", self.html,
            "the ≤640px phone block is missing — the topbar/nav will stop "
            "wrapping on phones.",
        )
        self.assertIn(
            "@media (max-width:960px)", self.html,
            "the ≤960px overflow safety-net is missing — the 641–960px "
            "tablet range will horizontally-scroll pages again.",
        )

    def test_key_mobile_rules_present(self):
        # Each systemic fix must survive (its tier is asserted below).
        for frag in (
            ".ck-topbar-inner{ flex-wrap:wrap",   # topbar wraps (phone)
            ".ck-nav{ flex-wrap:wrap",            # nav links wrap (phone)
            ".ck-pair{ grid-template-columns:1fr",  # viz|data stacks (tablet)
        ):
            self.assertIn(frag, self.html, f"missing mobile rule: {frag}")
        # every content table scrolls in place rather than widening the page
        self.assertTrue(
            re.search(r"\.ck-main table\{[^}]*overflow-x:auto", self.html),
            "content tables must scroll-x on small screens",
        )
        # absolutely-positioned hover cards (provenance tooltip + help
        # popover) drop from flow so they stop widening the page.
        self.assertTrue(
            re.search(r"\.ck-prov-tt-card[^}]*display:none", self.html),
            "tooltip/popover cards must leave flow (display:none) on small screens",
        )

    def test_rules_are_scoped_to_the_right_tier(self):
        # Phone tier: topbar/nav wrapping lives at ≤640 so it does not fire
        # across the whole tablet range.
        self.assertIn(
            "max-width:640px",
            _enclosing_media_query(self.html, ".ck-nav{ flex-wrap:wrap"),
            "nav-wrap must stay scoped to the ≤640 phone tier",
        )

        # Tablet tier: the overflow-prevention rules live at ≤960 — they
        # reach 641–960px but, being a max-width query, never leak onto
        # desktop (≥961px).
        for rule in (
            ".ck-pair{ grid-template-columns:1fr",   # viz|data stack
            ".ck-prov-tt-card{ left:auto",           # tooltip right-anchor
        ):
            self.assertIn(
                "max-width:960px",
                _enclosing_media_query(self.html, rule),
                f"{rule} must live in the ≤960 overflow tier",
            )


if __name__ == "__main__":
    unittest.main()
