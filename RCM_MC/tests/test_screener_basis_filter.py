"""Regression: target-screener Basis filter (live / verify / flagged / missing).

The screener is all live CMS data — predicted margins live on
/predictive-screener. The Basis filter lets a partner slice the live data by
how much to trust each value: verified-live, suspect (⚠ ≥24%), flagged (⚑
implausible), or not-reported. See target_screener_page._row_basis and the
`?basis=` query param.
"""
import unittest

from rcm_mc.ui.target_screener_page import _row_basis, render_target_screener


class RowBasisTests(unittest.TestCase):
    def test_live_is_clean_in_band_value(self):
        self.assertEqual(_row_basis({"q": 0.12}), "live")

    def test_verify_is_suspect_high(self):
        self.assertEqual(_row_basis({"q": 0.28, "q_suspect": True}), "verify")

    def test_flagged_takes_priority_over_missing(self):
        # A gated row has q=None AND q_flag set — it must read as flagged,
        # not merely missing.
        self.assertEqual(_row_basis({"q": None, "q_flag": "high"}), "flagged")

    def test_missing_is_none_without_flag(self):
        self.assertEqual(_row_basis({"q": None, "q_flag": None}), "missing")


class BasisFilterRenderTests(unittest.TestCase):
    def _render(self, **extra):
        qs = {"vertical": ["hospitals"]}
        qs.update({k: [v] for k, v in extra.items()})
        return render_target_screener(qs)

    def test_basis_control_and_options_present(self):
        h = self._render()
        self.assertIn('name="basis"', h)
        for label in ("Verified live", "Verify (⚠", "Flagged (⚑", "Not reported"):
            self.assertIn(label, h)
        # Honest pointer to where predicted values actually live.
        self.assertIn('/predictive-screener', h)

    def test_flagged_basis_shows_only_flagged_rows(self):
        h = self._render(basis="flagged", limit="150")
        # Flagged rows render the ⚑ gated marker and no real percentages.
        self.assertIn("⚑", h)
        # The flagged-cell marker (">30%" / "−40%") should appear in the body.
        self.assertTrue("&gt;30%" in h or "−40%" in h)

    def test_live_basis_shows_real_margins(self):
        h = self._render(basis="live", limit="150")
        # A real percentage value renders; the ACTUAL basis badge is intact.
        self.assertIn("ACTUAL</span>", h)
        self.assertRegex(h, r"tabular-nums;\">-?\d+\.\d%")

    def test_invalid_basis_is_a_noop(self):
        # A stale/hostile basis must not crash or filter everything out.
        h = self._render(basis="../etc/passwd")
        self.assertIn("ts-screen-table", h)


class NonHospitalBasisTests(unittest.TestCase):
    def test_star_rating_vertical_has_no_margin_tiers(self):
        # SNF star ratings are reported-or-not; no verify/flagged tiers, so the
        # control offers only the buckets that exist (no ⚑/⚠ options).
        from rcm_mc.ui.target_screener_page import _vertical_rows
        bases = {_row_basis(r) for r in _vertical_rows("snf", limit=None)}
        self.assertEqual(bases & {"verify", "flagged"}, set())


if __name__ == "__main__":
    unittest.main()
