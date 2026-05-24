"""Shared X-Ray design primitives (handoff: ~/Desktop/design_handoff_xray).

Pins the reusable kit used by BOTH HCRIS X-Ray and CMS Provider X-Ray:
scoped .xr-* CSS, the editorial primitives, and — critically — the peer-band
box-plot, which must render exactly the values passed and degrade to an honest
empty band (no fabricated geometry) when inputs can't be placed. No external
scripts/CDNs.
"""
from __future__ import annotations

import unittest

from rcm_mc.ui import xray_kit as k


class PrimitiveTests(unittest.TestCase):
    def test_tokens_and_scope(self):
        self.assertIn("--xr-navy:#0d2336", k.XRAY_CSS)
        self.assertIn("--xr-green:#1f7a5a", k.XRAY_CSS)
        # Sharp 90° corners per handoff: no border-radius anywhere in the kit.
        self.assertNotIn("border-radius:", k.XRAY_CSS)

    def test_eyebrow_ribbon_chip_crumb(self):
        self.assertIn("xr-eyebrow", k.xr_eyebrow("HCRIS X-RAY"))
        r = k.xr_ribbon("FULL BENCHMARK", "SIZE · PAYER")
        self.assertIn("xr-ribbon", r)
        self.assertIn("SIZE · PAYER", r)
        for tone in ("green", "red", "amber", "neutral"):
            self.assertIn(f"xr-chip {tone}", k.xr_chip("x", tone))
        self.assertIn("<b>HCRIS X-Ray</b>", k.xr_crumb("Home", "Diligence", "HCRIS X-Ray"))

    def test_caveat_and_source(self):
        self.assertIn("xr-caveat", k.xr_caveat("public data only"))
        self.assertIn("xr-source", k.xr_source("SOURCE: CMS HCRIS"))

    def test_escaping(self):
        self.assertIn("&lt;script&gt;", k.xr_eyebrow("<script>"))


class PeerBandTests(unittest.TestCase):
    def test_renders_box_median_target(self):
        svg = k.xr_peer_band(0, 12, 2.7, 3.5, 8.8, 11.8, "aboveRed")
        self.assertIn("<svg", svg)
        self.assertIn("<rect", svg)         # IQR box
        self.assertIn("<polygon", svg)      # target diamond
        self.assertNotIn("script", svg.lower())

    def test_target_state_colors(self):
        above = k.xr_peer_band(0, 12, 2, 3, 8, 11, "above")
        below = k.xr_peer_band(0, 12, 2, 3, 8, 1, "below")
        self.assertIn("--xr-green-deep", above)
        self.assertIn("--xr-red", below)

    def test_honest_empty_band_no_fabrication(self):
        # No data to place → dashed empty band, never invented geometry.
        e = k.xr_peer_band(0, 0, None, None, None, None, "inband")
        self.assertIn("unavailable", e)
        self.assertNotIn("<polygon", e)
        self.assertNotIn("<rect", e)

    def test_positions_clamp_in_range(self):
        # Target far outside [lo,hi] must clamp, not overflow the 0–100 axis.
        svg = k.xr_peer_band(0, 10, 2, 5, 8, 999, "aboveRed")
        self.assertIn("<polygon", svg)
        # No coordinate beyond 100 in the polygon points.
        import re
        for val in re.findall(r"polygon points=\"([^\"]+)\"", svg):
            for pt in val.split():
                x = float(pt.split(",")[0])
                self.assertLessEqual(x, 102.5)  # diamond half-width tolerance


class BenchmarkTableTests(unittest.TestCase):
    def test_section_rows_and_cells(self):
        rows = [
            {"section": True, "label": "SIZE"},
            {"cells": ["Beds", "312", "180", "250", "410"]},
        ]
        t = k.xr_benchmark_table(rows, ["Metric", "Target", "P25", "Median", "P75"])
        self.assertIn("xr-tbl", t)
        self.assertIn('class="section"', t)
        self.assertIn("SIZE", t)
        self.assertIn("Beds", t)
        self.assertIn('colspan="5"', t)


if __name__ == "__main__":
    unittest.main()
