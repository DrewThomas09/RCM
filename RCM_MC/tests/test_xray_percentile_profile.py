"""Wave-18 visual: provider X-ray percentile profile.

The peer-benchmark table printed four percentile columns per metric;
the provider's overall shape — top-quartile on outcomes, bottom on
cost — required reading every cell. Pins the profile SVG: state dot
toned by quartile, national reference ring, median guide, suppressed
metrics omitted, and the empty state.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from rcm_mc.ui.provider_xray_page import (
    _pctl_tone,
    _percentile_profile_svg,
)


def _pp(peer_set, percentile, suppressed=False):
    return SimpleNamespace(
        peer_set=peer_set, percentile=percentile,
        suppressed=suppressed, peer_n=10, label=peer_set,
    )


def _bm(label, state_p, national_p, *, suppress_state=False):
    return SimpleNamespace(
        label=label,
        percentiles=[
            _pp("state", state_p, suppressed=suppress_state),
            _pp("national", national_p),
        ],
    )


def _report(benchmarks):
    return SimpleNamespace(benchmarks=benchmarks)


class PercentileProfileTests(unittest.TestCase):
    def test_renders_dots_with_quartile_tones(self):
        svg = _percentile_profile_svg(_report([
            _bm("Star rating", 82, 70),
            _bm("Readmission score", 18, 25),
        ]))
        self.assertIn("<svg", svg)
        self.assertIn("ck-xr-pctl-profile", svg)
        self.assertIn("MEDIAN", svg)
        self.assertIn(_pctl_tone(82), svg)  # top-quartile green
        self.assertIn(_pctl_tone(18), svg)  # bottom-quartile red

    def test_quartile_tone_bands(self):
        self.assertEqual(_pctl_tone(80), "#0a8a5f")
        self.assertEqual(_pctl_tone(60), "#1F7A75")
        self.assertEqual(_pctl_tone(30), "#b8732a")
        self.assertEqual(_pctl_tone(10), "#b5321e")

    def test_suppressed_state_still_plots_national(self):
        svg = _percentile_profile_svg(_report([
            _bm("Thin metric", 50, 60, suppress_state=True),
        ]))
        self.assertIn("Thin metric", svg)
        # National ring present, no filled state dot tone for p=50.
        self.assertIn('fill="none"', svg)

    def test_fully_suppressed_metric_omitted(self):
        svg = _percentile_profile_svg(_report([
            SimpleNamespace(label="Ghost", percentiles=[
                _pp("state", None, suppressed=True),
                _pp("national", None, suppressed=True),
            ]),
            _bm("Real", 55, 60),
        ]))
        self.assertNotIn("Ghost", svg)
        self.assertIn("Real", svg)

    def test_empty_renders_nothing(self):
        self.assertEqual(_percentile_profile_svg(_report([])), "")
        self.assertEqual(
            _percentile_profile_svg(SimpleNamespace(benchmarks=None)), "")


if __name__ == "__main__":
    unittest.main()
