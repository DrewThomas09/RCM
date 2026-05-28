"""Editorial-head cascade for render_sector_provider_profile (sweep batch 7).

Six provider-profile renderers all delegate to this one helper:
  /dialysis/<ccn> · /home-health/<ccn> · /hospice/<ccn>
  /irf/<ccn> · /ltch/<ccn> · /snf/<ccn>

Sweeping the shared helper cascades the strict Tier-1 5-block head
to every drill-in, plus an auto-derived verdict line that quotes the
real within-state rank + state-mean delta in the lede.

Pins:
  · ONE <h1> per page across all 6 routes (#1036 a11y invariant).
  · Breadcrumb (All <kind>s / <STATE> list / Current).
  · Eyebrow + 24×1px green-dash glyph.
  · Mono meta-line (CCN · city/state · ownership).
  · Italic-first-phrase serif lede with REAL rank + delta (the
    auto-derived verdict).
  · Mono source-note carrying live provenance.
  · 4-bucket status-dot legend.
"""
from __future__ import annotations

import re
import unittest


_SPECS = [
    ("rcm_mc.ui.dialysis_page", "render_dialysis_profile",
     "rcm_mc.data.dialysis", "load_dialysis_providers"),
    ("rcm_mc.ui.home_health_page", "render_home_health_profile",
     "rcm_mc.data.home_health", "load_home_health_providers"),
    ("rcm_mc.ui.hospice_page", "render_hospice_profile",
     "rcm_mc.data.hospice", "load_hospice_providers"),
    ("rcm_mc.ui.irf_page", "render_irf_profile",
     "rcm_mc.data.irf", "load_irf_providers"),
    ("rcm_mc.ui.ltch_page", "render_ltch_profile",
     "rcm_mc.data.ltch", "load_ltch_providers"),
    ("rcm_mc.ui.snf_page", "render_snf_profile",
     "rcm_mc.data.snf", "load_snf_providers"),
]


def _sample_render(spec):
    mod_ui, fn_ui, mod_d, fn_d = spec
    ui = __import__(mod_ui, fromlist=[fn_ui])
    data = __import__(mod_d, fromlist=[fn_d])
    provs = getattr(data, fn_d)()
    if not provs:
        return None
    ccn = next(iter(provs))
    return getattr(ui, fn_ui)(ccn)


class ProviderProfileCascadeTests(unittest.TestCase):

    def test_all_six_profile_routes_single_h1(self) -> None:
        for spec in _SPECS:
            with self.subTest(route=spec[1]):
                html = _sample_render(spec)
                if html is None:
                    self.skipTest(f"{spec[1]}: no providers loaded")
                self.assertEqual(
                    len(re.findall(r"<h1[ >]", html)), 1,
                    f"{spec[1]}: expected exactly one <h1>",
                )

    def test_all_six_profile_routes_head_block(self) -> None:
        for spec in _SPECS:
            with self.subTest(route=spec[1]):
                html = _sample_render(spec)
                if html is None:
                    self.skipTest(f"{spec[1]}: no providers loaded")
                self.assertIn('class="pp-head"', html)

    def test_all_six_profile_routes_breadcrumb(self) -> None:
        for spec in _SPECS:
            with self.subTest(route=spec[1]):
                html = _sample_render(spec)
                if html is None:
                    self.skipTest(f"{spec[1]}: no providers loaded")
                self.assertIn('class="crumb"', html)
                self.assertRegex(html, r'>All [a-z]+s</a>')

    def test_all_six_profile_routes_eyebrow_with_dash(self) -> None:
        for spec in _SPECS:
            with self.subTest(route=spec[1]):
                html = _sample_render(spec)
                if html is None:
                    self.skipTest(f"{spec[1]}: no providers loaded")
                self.assertRegex(
                    html,
                    r'<div class="eyebrow"><span class="dash"></span>',
                )

    def test_all_six_profile_routes_status_dot_legend(self) -> None:
        for spec in _SPECS:
            with self.subTest(route=spec[1]):
                html = _sample_render(spec)
                if html is None:
                    self.skipTest(f"{spec[1]}: no providers loaded")
                for cls_name in ("live", "computed", "needs", "illustrative"):
                    self.assertRegex(
                        html,
                        rf'<span class="dot {cls_name}"></span>',
                    )

    def test_all_six_profile_routes_source_note(self) -> None:
        for spec in _SPECS:
            with self.subTest(route=spec[1]):
                html = _sample_render(spec)
                if html is None:
                    self.skipTest(f"{spec[1]}: no providers loaded")
                self.assertIn('class="source-note"', html)
                self.assertRegex(html, r'source-note">Source:')

    def test_all_six_profile_routes_italic_first_phrase_verdict(self) -> None:
        # The auto-derived verdict line carries an <em> wrapping the
        # first phrase. Verdict quotes a real number (rank, value, or
        # honest-absent), never editorial filler.
        for spec in _SPECS:
            with self.subTest(route=spec[1]):
                html = _sample_render(spec)
                if html is None:
                    self.skipTest(f"{spec[1]}: no providers loaded")
                lede = re.search(r'<p class="lede">(.*?)</p>', html)
                self.assertIsNotNone(lede)
                lede_text = lede.group(1)
                self.assertIn("<em>", lede_text)
                # Must contain a real signal phrase: "Ranks #N of M",
                # "reads ...", or "No <metric> on file".
                self.assertTrue(
                    any(p in lede_text for p in
                        ("Ranks #", " reads ", "on file")),
                    f"verdict doesn't quote real signal: {lede_text[:120]}",
                )


if __name__ == "__main__":
    unittest.main()
