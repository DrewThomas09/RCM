"""Wave-19 visual: roll-up platform composition strip.

The roll-up builder's facility table listed absolute NPR dollars but
never answered the structural question — anchor + tuck-ins or merger
of equals? Pins the 100% strip: share math on reported NPR only,
shape verdicts, missing-NPR exclusion note, and the <2-reporting
empty state.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from rcm_mc.ui.rollup_builder_page import _platform_composition_svg


def _f(ccn, name, npr):
    return SimpleNamespace(ccn=ccn, name=name, npr=npr)


class PlatformCompositionTests(unittest.TestCase):
    def test_anchor_shape_detected(self):
        svg = _platform_composition_svg([
            _f("450076", "Memorial Hermann", 600e6),
            _f("450068", "Smaller General", 250e6),
            _f("450358", "Tiny District", 150e6),
        ])
        self.assertIn("<svg", svg)
        self.assertIn("ck-rollup-composition", svg)
        self.assertIn("TOP FACILITY 60% → ANCHOR + TUCK-INS", svg)
        self.assertIn("3 REPORTING FACILITIES", svg)

    def test_balanced_shape_detected(self):
        svg = _platform_composition_svg([
            _f("1", "A", 100e6), _f("2", "B", 100e6),
            _f("3", "C", 100e6), _f("4", "D", 100e6),
        ])
        self.assertIn("BALANCED PLATFORM", svg)

    def test_missing_npr_excluded_and_noted(self):
        svg = _platform_composition_svg([
            _f("1", "A", 300e6),
            _f("2", "B", 200e6),
            _f("3", "NoFile", None),
        ])
        self.assertIn("1 FACILITY WITHOUT FILED NPR EXCLUDED", svg)
        self.assertNotIn("NoFile", svg)

    def test_fewer_than_two_reporting_renders_nothing(self):
        self.assertEqual(
            _platform_composition_svg([_f("1", "A", 300e6),
                                       _f("2", "B", None)]),
            "",
        )
        self.assertEqual(_platform_composition_svg([]), "")


if __name__ == "__main__":
    unittest.main()
