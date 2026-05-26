"""Geo Metrics & Sources reference (/geo-metrics): a transparency page generated
from the shared _METRICS registry + live coverage. Guards that it lists every
metric, reports real (non-fabricated) coverage counts, and is GREEN.
"""
import unittest

from rcm_mc.diligence.surface_status import classify_surface
from rcm_mc.ui.data_public.geo_metrics_page import _coverage, render_geo_metrics
from rcm_mc.ui.data_public.state_compare_page import _METRICS, _VALID


class GeoMetricsReferenceTests(unittest.TestCase):
    def test_coverage_is_real_and_bounded(self):
        cov = _coverage()
        # one entry per registry metric, each within [0, #jurisdictions]
        self.assertEqual(set(cov), {m[0] for m in _METRICS})
        for n in cov.values():
            self.assertGreaterEqual(n, 0)
            self.assertLessEqual(n, len(_VALID))
        # population is reported by every jurisdiction
        self.assertEqual(cov["population"], len(_VALID))

    def test_page_lists_every_metric(self):
        h = render_geo_metrics()
        self.assertIn("Metrics", h)
        for _k, label, _src, _f, _h in _METRICS:
            self.assertIn(label, h)
        self.assertIn("fabricated", h)

    def test_surface_is_green(self):
        self.assertEqual(classify_surface("/geo-metrics")["tier"], "green")


if __name__ == "__main__":
    unittest.main()
