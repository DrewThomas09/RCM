"""Every vertical screener + provider profile wears the handoff X-Ray skin.

The directive was to render all six non-hospital verticals in the same
editorial X-Ray system the hospital HCRIS X-Ray uses. Both shared scaffolds
(sector_screener, sector_provider_profile) opt into the kit by wrapping the
body in `.xr` and shipping XRAY_CSS. These assertions lock that in so a future
refactor can't silently drop the skin from one vertical.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui.dialysis_page import render_dialysis
from rcm_mc.ui.home_health_page import render_home_health
from rcm_mc.ui.hospice_page import render_hospice
from rcm_mc.ui.irf_page import render_irf
from rcm_mc.ui.ltch_page import render_ltch
from rcm_mc.ui.snf_page import render_snf
from rcm_mc.data.home_health import load_home_health_providers
from rcm_mc.data.snf import load_snf_providers

_SCREENERS = (render_home_health, render_hospice, render_dialysis,
              render_irf, render_ltch, render_snf)


class ScreenerXraySkinTests(unittest.TestCase):
    def test_national_view_carries_xray_skin(self):
        for render in _SCREENERS:
            h = render({})
            with self.subTest(render=render.__name__):
                self.assertIn('class="xr"', h)             # body opted in
                self.assertIn("--xr-navy", h)              # kit tokens present
                self.assertIn("--xr-green", h)
                self.assertIn(".xr .ck-panel-head", h)     # navy ribbon skin
                self.assertIn("xr-eyebrow", h)             # kit green-dash eyebrow

    def test_no_prototype_cdn_assets(self):
        # The base chartis_shell legitimately loads Google Fonts app-wide; we
        # only guard against the prototype CDNs the handoff forbade.
        for render in _SCREENERS:
            low = render({}).lower()
            with self.subTest(render=render.__name__):
                for bad in ("unpkg", "babel", "cdn.jsdelivr", "react."):
                    self.assertNotIn(bad, low)


class ProfileXraySkinTests(unittest.TestCase):
    def test_home_health_profile_carries_skin(self):
        ccn = next(iter(load_home_health_providers()))
        h = render_home_health({"ccn": [ccn]})
        self.assertIn('class="xr"', h)
        self.assertIn(".xr .ck-panel-head", h)
        self.assertIn("xr-eyebrow", h)

    def test_snf_profile_carries_skin(self):
        ccn = next(iter(load_snf_providers()))
        h = render_snf({"ccn": [ccn]})
        self.assertIn('class="xr"', h)
        self.assertIn(".xr .ck-panel-head", h)


if __name__ == "__main__":
    unittest.main()
