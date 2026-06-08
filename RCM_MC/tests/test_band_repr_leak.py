"""Regression: reasonableness-band cells must never leak the Band repr.

The /deal/<id>/red-flags and /deal/<id>/partner-review tables render a
``BandCheck`` whose ``.band`` is a ``Band`` dataclass. Both renderers had
a branch that fell back to ``html.escape(str(band))`` for any non
(list, tuple) band — which dumped the entire dataclass repr
(``Band(metric='irr', regime='…', low=0.15, stretch_low=None,
source='…')``) straight into the partner-facing cell. The cell must
instead show the readable bounds, formatted like the observed column.
"""
from __future__ import annotations

import types
import unittest

from rcm_mc.pe_intelligence.reasonableness import Band, BandCheck
from rcm_mc.ui.chartis.partner_review_page import _bands_table
from rcm_mc.ui.chartis.red_flags_page import _violations_section


def _review_with_band_dataclass():
    band = Band(
        metric="irr", regime="small / balanced payer mix",
        low=0.15, high=0.28, stretch_high=0.35, implausible_high=0.48,
        source="HC-PE middle-market balanced",
    )
    check = BandCheck(
        metric="irr", observed=0.0, verdict="OUT_OF_BAND", band=band,
        partner_note="Below fund hurdle for this regime.",
    )
    return types.SimpleNamespace(reasonableness_checks=[check])


class BandReprLeakTests(unittest.TestCase):
    def test_red_flags_no_repr_leak(self):
        html = _violations_section(_review_with_band_dataclass())
        self.assertNotIn("Band(metric=", html)
        self.assertNotIn("stretch_low=", html)
        self.assertNotIn("source=", html)
        # irr is a percent metric → bounds render as percentages.
        self.assertIn("15.0%", html)
        self.assertIn("28.0%", html)

    def test_partner_review_no_repr_leak(self):
        html = _bands_table(_review_with_band_dataclass())
        self.assertNotIn("Band(metric=", html)
        self.assertNotIn("stretch_low=", html)
        self.assertNotIn("source=", html)
        self.assertIn("15.0%", html)
        self.assertIn("28.0%", html)


if __name__ == "__main__":
    unittest.main()
