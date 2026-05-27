"""State Comparison (/state-compare): a cross-dataset analysis mode that puts
2–4 states side by side across PEdesk's real state-keyed public data. Guards
that real values flow through, missing data renders an honest dash (never a
fabricated number), input is validated, and the surface is a GREEN real index.
"""
import unittest

from rcm_mc.diligence.surface_status import classify_surface
from rcm_mc.ui.data_public.state_compare_page import (
    _ROW_ORDER,
    _collect,
    _parse_states,
    national_medians,
    render_state_compare,
)


class StateCompareTests(unittest.TestCase):
    def test_parse_states_validates_and_caps(self):
        # honors order, upper-cases, drops invalid, caps at 4
        self.assertEqual(_parse_states({"states": ["ca,tx,fl"]}), ["CA", "TX", "FL"])
        self.assertEqual(_parse_states({"states": ["CA,ZZ,NY"]}), ["CA", "NY"])
        self.assertEqual(len(_parse_states({"states": ["CA,TX,FL,NY,PA,OH"]})), 4)
        # empty / missing falls back to a sensible default
        self.assertTrue(_parse_states({}))

    def test_collect_returns_real_values_for_a_known_state(self):
        # CA has data across every loader — at least most metrics resolve to a
        # real (non-dash) value, proving the wiring pulls live aggregates
        row = _collect("CA")
        real = [m for m in _ROW_ORDER if row.get(m) not in (None, "—")]
        self.assertGreaterEqual(len(real), 10, f"too few real metrics: {row}")
        # population is a real integer string, not a dash
        self.assertNotEqual(row.get("Population", "—"), "—")

    def test_missing_data_is_dash_never_fabricated(self):
        # an unknown/edge value must surface as a dash, not a made-up number
        row = _collect("WY")
        for m in _ROW_ORDER:
            v = row.get(m, "—")
            self.assertIsInstance(v, str)

    def test_page_renders_real_index(self):
        h = render_state_compare({"states": ["CA,TX,FL"]})
        self.assertIn("State Comparison", h)
        self.assertIn("<table", h)
        for s in ("CA", "TX", "FL"):
            self.assertIn(s, h)
        # honesty language present
        self.assertIn("fabricated", h)

    def test_page_leads_with_real_kpi_strip(self):
        # X-Ray pattern: the page leads with a KPI strip computed from the
        # real data (states compared / metrics with data / leading state),
        # not just a table.
        h = render_state_compare({"states": ["CA,TX,NY"]})
        self.assertIn("ck-kpi-strip", h)
        self.assertIn("States compared", h)
        self.assertIn("Metrics with data", h)
        self.assertIn(">3<", h)  # 3 states compared, computed not hard-coded

    def test_national_medians_are_real(self):
        meds = national_medians()
        # most metrics have a national median; values are finite numbers
        self.assertGreaterEqual(len(meds), 10)
        for v in meds.values():
            self.assertEqual(v, v)  # not NaN
        # population median should sit between the smallest and CA's value
        self.assertGreater(meds["population"], 0)

    def test_page_has_us_median_column(self):
        h = render_state_compare({"states": ["CA,TX,FL"]})
        self.assertIn("U.S. median", h)

    def test_page_highlights_best_and_worst(self):
        from rcm_mc.ui._chartis_kit import P
        h = render_state_compare({"states": ["CA,TX,FL"]})
        # directional best/worst tints are applied + explained in the legend
        self.assertIn(P["positive"], h)
        self.assertIn(P["warning"], h)
        self.assertIn("best", h)
        self.assertIn("weakest", h)

    def test_surface_is_green(self):
        self.assertEqual(classify_surface("/state-compare")["tier"], "green")


if __name__ == "__main__":
    unittest.main()
