"""Regression: suspect-high margins are flagged + demoted, not led with.

The default screener ranks by margin descending. Margins in the extreme
upper tail (≥24%, ~95th pct of real hospitals) pass the hard +30% gate but
are disproportionately incomplete-opex filing artifacts — so a naive
descending sort led with a wall of ~29% "best targets" that were mostly
errors. These are kept and shown (some are real high-margin specialty/rehab
hospitals) but flagged "verify" and ranked BELOW clean values. See
_chartis_kit.margin_is_suspect_high and target_screener_page._quality_sort_key.
"""
import unittest

from rcm_mc.ui._chartis_kit import (
    MARGIN_PLAUSIBLE_HI,
    MARGIN_SUSPECT_HI,
    margin_is_suspect_high,
)
from rcm_mc.ui.target_screener_page import _fmt_q, _quality_sort_key, _vertical_rows


class SuspectHighThresholdTests(unittest.TestCase):
    def test_band_boundaries(self):
        self.assertFalse(margin_is_suspect_high(0.20))
        self.assertFalse(margin_is_suspect_high(MARGIN_SUSPECT_HI - 0.001))
        self.assertTrue(margin_is_suspect_high(MARGIN_SUSPECT_HI))
        self.assertTrue(margin_is_suspect_high(0.28))
        self.assertTrue(margin_is_suspect_high(MARGIN_PLAUSIBLE_HI))
        # Above the hard ceiling is handled by the gate, not this helper.
        self.assertFalse(margin_is_suspect_high(0.45))

    def test_unknown_is_not_suspect(self):
        self.assertFalse(margin_is_suspect_high(None))
        self.assertFalse(margin_is_suspect_high(float("nan")))
        self.assertFalse(margin_is_suspect_high("x"))


class QualitySortKeyTests(unittest.TestCase):
    def test_tier_order_clean_then_suspect_then_missing(self):
        clean = {"q": 0.12}
        suspect = {"q": 0.28, "q_suspect": True}
        missing = {"q": None}
        keyed = sorted([missing, suspect, clean],
                       key=lambda r: _quality_sort_key(r, rev=True))
        self.assertEqual([id(r) for r in keyed],
                         [id(clean), id(suspect), id(missing)])

    def test_clean_outranks_higher_suspect(self):
        # A real 12% margin must rank ABOVE a 28% suspect one in the default
        # (desc) view — that's the whole point.
        clean = {"q": 0.12}
        suspect = {"q": 0.28, "q_suspect": True}
        self.assertLess(_quality_sort_key(clean, rev=True),
                        _quality_sort_key(suspect, rev=True))

    def test_non_hospital_rows_collapse_to_value_then_missing(self):
        # No q_suspect key → behaves like the original two-tier sort.
        a = {"q": 5}
        b = {"q": 3}
        none = {"q": None}
        keyed = sorted([none, b, a], key=lambda r: _quality_sort_key(r, rev=True))
        self.assertEqual([id(r) for r in keyed], [id(a), id(b), id(none)])


class FmtSuspectRenderTests(unittest.TestCase):
    def test_suspect_value_shows_verify_marker(self):
        out = _fmt_q({"q": 0.28, "q_suspect": True, "q_pct": True})
        self.assertIn("28.0%", out)
        self.assertIn("⚠", out)
        self.assertIn("verify", out)

    def test_clean_value_has_no_marker(self):
        out = _fmt_q({"q": 0.12, "q_suspect": False, "q_pct": True})
        self.assertIn("12.0%", out)
        self.assertNotIn("⚠", out)


class DefaultViewLeadsWithCleanTests(unittest.TestCase):
    def test_top_of_default_sort_is_not_suspect(self):
        rows = _vertical_rows("hospitals", limit=None)
        self.assertTrue(rows)
        # The first row of the pre-sorted view must be a clean value, not a
        # near-ceiling suspect artifact.
        self.assertIsNotNone(rows[0]["q"])
        self.assertFalse(rows[0].get("q_suspect"),
                         "default view led with a suspect-high margin")
        # And all suspect rows sit after all clean rows.
        first_suspect = next((i for i, r in enumerate(rows)
                              if r.get("q_suspect")), len(rows))
        last_clean = max((i for i, r in enumerate(rows)
                          if r["q"] is not None and not r.get("q_suspect")),
                         default=-1)
        self.assertLess(last_clean, first_suspect)


if __name__ == "__main__":
    unittest.main()
