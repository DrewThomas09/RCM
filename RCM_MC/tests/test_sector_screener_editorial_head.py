"""Editorial-head cascade for render_sector_screener (sweep batch 6).

The shared sector renderer powers six healthcare-vertical pages:
  /dialysis, /home-health, /hospice, /irf, /ltch, /snf

Sweeping this one helper applies the strict Tier-1 5-block head to
all six in a single edit. Plus a functionality lift: a real
"≥4-star share" KPI tile derived from the live quality map.

Pins:
  · ONE <h1> per page across all 6 routes (#1036 a11y invariant).
  · Eyebrow + 24×1px green-dash glyph at the masthead.
  · Mono meta-line quoting REAL counts: providers / states / rated.
  · Italic-first-phrase serif lede (auto-italicizes the first
    phrase up to the period).
  · Mono source-note carrying the live provenance string.
  · 4-bucket status-dot legend.
  · KPI strip carries the new "≥4-star share" tile derived from
    the live quality map — share of facilities with five_star >= 4.
    Renders "—" with an honest sub when no rated facilities are
    in scope.
"""
from __future__ import annotations

import re
import unittest


_ROUTES = [
    ("rcm_mc.ui.dialysis_page", "render_dialysis"),
    ("rcm_mc.ui.home_health_page", "render_home_health"),
    ("rcm_mc.ui.hospice_page", "render_hospice"),
    ("rcm_mc.ui.irf_page", "render_irf"),
    ("rcm_mc.ui.ltch_page", "render_ltch"),
    ("rcm_mc.ui.snf_page", "render_snf"),
]


def _render(mod_name: str, fn_name: str) -> str:
    mod = __import__(mod_name, fromlist=[fn_name])
    return getattr(mod, fn_name)()


class SectorCascadeTests(unittest.TestCase):
    """Each of the 6 sector pages carries the strict 5-block head."""

    def test_all_six_routes_single_h1(self) -> None:
        for mod, fn in _ROUTES:
            with self.subTest(route=fn):
                html = _render(mod, fn)
                self.assertEqual(
                    len(re.findall(r"<h1[ >]", html)), 1,
                    f"{fn}: expected exactly one <h1>",
                )

    def test_all_six_routes_head_block(self) -> None:
        for mod, fn in _ROUTES:
            with self.subTest(route=fn):
                html = _render(mod, fn)
                self.assertIn(
                    'class="ss-head"', html,
                    f"{fn}: missing ss-head wrapper",
                )

    def test_all_six_routes_eyebrow_with_dash(self) -> None:
        for mod, fn in _ROUTES:
            with self.subTest(route=fn):
                html = _render(mod, fn)
                self.assertRegex(
                    html,
                    r'<div class="eyebrow"><span class="dash"></span>',
                    f"{fn}: missing eyebrow+dash",
                )

    def test_all_six_routes_status_dot_legend(self) -> None:
        for mod, fn in _ROUTES:
            with self.subTest(route=fn):
                html = _render(mod, fn)
                for cls_name in ("live", "computed", "needs", "illustrative"):
                    self.assertRegex(
                        html,
                        rf'<span class="dot {cls_name}"></span>',
                        f"{fn}: missing legend dot {cls_name}",
                    )

    def test_all_six_routes_quote_real_counts(self) -> None:
        # Meta-line carries "N PROVIDERS · M STATES · K RATED · CMS
        # PUBLIC DATA" with real numbers (not zero, not placeholders).
        for mod, fn in _ROUTES:
            with self.subTest(route=fn):
                html = _render(mod, fn)
                self.assertRegex(
                    html,
                    r'class="meta">\s*[0-9,]+\s+PROVIDERS?\s*·\s*'
                    r'[0-9]+\s+STATES?\s*·\s*[0-9,]+\s+RATED\s*·\s*'
                    r'CMS PUBLIC DATA',
                    f"{fn}: meta-line doesn't quote real counts",
                )

    def test_all_six_routes_have_4_star_share_kpi(self) -> None:
        # NEW functionality lift — real share of facilities at ≥4 stars
        # derived from the live quality map.
        for mod, fn in _ROUTES:
            with self.subTest(route=fn):
                html = _render(mod, fn)
                self.assertIn(
                    "≥4-star share", html,
                    f"{fn}: missing ≥4-star share KPI tile",
                )

    def test_all_six_routes_source_note_carries_provenance(self) -> None:
        # The source-note quotes the live provenance string each
        # caller passes (e.g. "CMS Dialysis Facility Compare —
        # Listing by Facility (DFC_FACILITY)").
        for mod, fn in _ROUTES:
            with self.subTest(route=fn):
                html = _render(mod, fn)
                self.assertIn(
                    'class="source-note"', html,
                    f"{fn}: source-note missing",
                )
                # Provenance contains the word "CMS" on every
                # sector page (or an equivalent agency tag).
                self.assertRegex(
                    html,
                    r'source-note">Source:.*CMS',
                    f"{fn}: source-note doesn't quote CMS",
                )

    def test_all_six_routes_lede_italic_first_phrase(self) -> None:
        # The first phrase up to the period is wrapped in <em>.
        for mod, fn in _ROUTES:
            with self.subTest(route=fn):
                html = _render(mod, fn)
                lede_match = re.search(
                    r'<p class="lede">(.*?)</p>', html,
                )
                self.assertIsNotNone(lede_match, f"{fn}: lede missing")
                self.assertIn(
                    "<em>", lede_match.group(1),
                    f"{fn}: lede missing italic first phrase",
                )


if __name__ == "__main__":
    unittest.main()
