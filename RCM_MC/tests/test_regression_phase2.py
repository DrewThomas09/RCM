"""Phase 2 of the regression editorial redesign — the spec §8 / §11 /
§14 / §16 / §18 components shipped on top of #1055.

These tests pin the data contract + honesty rules for:

  · Empirical PI coverage (CVResult.pi_coverage)  — conformal, not
    parametric; ``Awaiting CV`` pending pill when CV is off.
  · Cohort R² grids (bed_size / segment / region) — same within-
    bucket construction as ``state_r2``; ``Awaiting data`` empty
    state when the source column is missing on the frame.
  · Learning curve — 10 points at increasing train fractions vs a
    fixed held-out 20% eval set; plateau verdict is honest.
  · Leverage × residual scatter — uses ``result["outliers"][]``
    data directly; no new compute path.
  · Interpretation block — every line keys off a real fit
    characteristic (R², overfit gap, p80 PI half-width, BP p-value,
    max VIF, cohort delta-vs-headline). Never editorial filler.
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd


def _synthetic_hcris(n: int = 420, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(n)],
        "name": [f"Hospital {i}" for i in range(n)],
        "state": rng.choice(
            ["CA", "NY", "TX", "FL", "OH", "PA", "MA", "IL", "GA", "WA"], n,
        ),
        "beds": rng.integers(20, 800, n),
        "occupancy_rate": rng.uniform(0.3, 0.95, n),
        "medicare_day_pct": rng.uniform(0.2, 0.7, n),
        "medicaid_day_pct": rng.uniform(0.05, 0.4, n),
        "operating_expenses": rng.uniform(1e7, 5e9, n),
        "total_patient_days": rng.integers(1000, 250000, n),
    })
    df["net_patient_revenue"] = (
        df["operating_expenses"] * rng.uniform(0.85, 1.2, n)
        + rng.normal(0, 5e7, n)
    ).clip(lower=1e6)
    return df


# ── _run_ols additive Phase-2 fields ─────────────────────────────────
class RunOlsPhase2FieldsTests(unittest.TestCase):
    """Cohort grids + learning curve land on every successful fit."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.regression_page import _run_ols
        cls.result = _run_ols(
            _synthetic_hcris(),
            "net_patient_revenue",
            ["beds", "occupancy_rate", "medicare_day_pct",
             "operating_expenses", "total_patient_days"],
            log_target=True,
        )

    def test_cohort_r2_by_bed_size_shape(self) -> None:
        rows = self.result["cohort_r2_by_bed_size"]
        self.assertIsInstance(rows, list)
        # At least 3 of the 5 bed buckets should be populated on
        # n=420.
        self.assertGreaterEqual(len(rows), 3)
        for r in rows:
            for key in ("bucket", "n", "r2", "delta_vs_headline"):
                self.assertIn(key, r)
            self.assertGreater(r["n"], 0)
            self.assertGreaterEqual(r["r2"], -1.0)
            self.assertLessEqual(r["r2"], 1.0)

    def test_cohort_r2_by_region_covers_us(self) -> None:
        regs = {r["bucket"] for r in self.result["cohort_r2_by_region"]}
        # Synthetic frame draws from all four census regions — every
        # populated bucket must use the spec-mandated label.
        self.assertTrue(
            regs.issubset({"Northeast", "Midwest", "South", "West"}),
            f"unexpected region labels: {regs}",
        )
        self.assertGreaterEqual(len(regs), 3)

    def test_cohort_segment_absent_when_no_segment_label(self) -> None:
        # The synthetic frame has no segment_label column → the
        # segment cohort grid is honestly empty (no fake data).
        self.assertEqual(
            self.result["cohort_r2_by_segment"], [],
        )

    def test_delta_vs_headline_is_signed(self) -> None:
        # The delta is real-valued; on a synthetic universe at least
        # one cohort must differ from headline.
        deltas = [
            abs(r["delta_vs_headline"])
            for r in self.result["cohort_r2_by_bed_size"]
        ]
        self.assertGreater(max(deltas), 0.0)

    def test_learning_curve_ten_points(self) -> None:
        lc = self.result["learning_curve"]
        self.assertIsInstance(lc, list)
        self.assertEqual(len(lc), 10)
        # Train fractions step 0.1 → 1.0
        fracs = [pt["train_fraction"] for pt in lc]
        self.assertEqual(fracs, [0.1, 0.2, 0.3, 0.4, 0.5,
                                 0.6, 0.7, 0.8, 0.9, 1.0])
        for pt in lc:
            self.assertIn("n_train", pt)
            self.assertIn("train_r2", pt)
            self.assertIn("test_r2", pt)
            self.assertIn("gap", pt)
            # Each n_train must be larger than the previous (monotone
            # growth — the curve isn't shuffled).
        n_trains = [pt["n_train"] for pt in lc]
        for i in range(1, len(n_trains)):
            self.assertGreaterEqual(n_trains[i], n_trains[i - 1])


# ── CVResult.pi_coverage (conformal) ─────────────────────────────────
class ConformalPiCoverageTests(unittest.TestCase):
    """run_cv_regression now returns split-conformal coverage stats."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.finance.cross_validation import run_cv_regression
        df = _synthetic_hcris(n=600)
        cls.cv = run_cv_regression(
            df, "net_patient_revenue",
            ["beds", "occupancy_rate", "medicare_day_pct",
             "operating_expenses", "total_patient_days"],
            k=5, log_transform_target=True,
        )

    def test_pi_coverage_present_for_three_levels(self) -> None:
        self.assertEqual(len(self.cv.pi_coverage), 3)
        nominals = sorted(p["nominal"] for p in self.cv.pi_coverage)
        self.assertEqual(nominals, [0.5, 0.8, 0.95])

    def test_empirical_in_bounds_and_close_to_nominal(self) -> None:
        # Conformal: empirical ∈ [0, 1] and reasonably near nominal
        # (within ±10pp) on a clean synthetic fit.
        for p in self.cv.pi_coverage:
            self.assertGreaterEqual(p["empirical"], 0.0)
            self.assertLessEqual(p["empirical"], 1.0)
            self.assertLess(
                abs(p["empirical"] - p["nominal"]), 0.10,
                f"empirical={p['empirical']} vs nominal={p['nominal']}",
            )

    def test_median_half_width_is_non_negative(self) -> None:
        for p in self.cv.pi_coverage:
            self.assertGreaterEqual(p["median_half_width"], 0.0)

    def test_to_dict_round_trip_includes_pi_coverage(self) -> None:
        # Backward-compat — CVResult.to_dict() now carries the new
        # field but does not drop any existing key.
        d = self.cv.to_dict()
        for key in ("k", "mean_test_r2", "overfit_gap", "folds",
                    "pi_coverage"):
            self.assertIn(key, d)


# ── Page renders all five Phase-2 sections ───────────────────────────
class Phase2RenderTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.regression_page import render_regression_page
        cls.html_cv = render_regression_page(
            hcris_df=_synthetic_hcris(), log_target=True, cv=True,
        )
        cls.html_no_cv = render_regression_page(
            hcris_df=_synthetic_hcris(), log_target=True, cv=False,
        )

    # PI coverage strip --------------------------------------------------
    def test_pi_strip_three_nominal_levels(self) -> None:
        for label in ("Nominal 50%", "Nominal 80%", "Nominal 95%"):
            self.assertIn(label, self.html_cv)

    def test_pi_strip_awaits_cv_when_cv_off(self) -> None:
        # Spec §4 Partial state on PI strip when CV is off.
        # Four cells × "Awaiting CV" pill.
        # (The headline strip also has 2 awaiting-CV pills; we just
        # assert the PI strip count is at least 4.)
        pi_html = self.html_no_cv.split('class="rge-pi', 1)[1]
        pi_html = pi_html.split("</div>\n\n")[0]
        self.assertGreaterEqual(pi_html.count("Awaiting CV"), 4)

    def test_pi_strip_real_numbers_when_cv_on(self) -> None:
        import re
        # The 80% PI tile must quote a percent or pending pill — when
        # CV is on it should be a real percent, not "Awaiting CV".
        m = re.search(
            r"Nominal 80%</div>\s*<div class=\"val\">([^<]+)</div>",
            self.html_cv,
        )
        self.assertIsNotNone(m, "could not locate PI 80% tile body")
        self.assertNotIn("Awaiting", m.group(1))
        self.assertIn("%", m.group(1))

    # Cohort grids -------------------------------------------------------
    def test_three_cohort_sections_render(self) -> None:
        # The cohort block has 3 sub-blocks: bed size, segment, region.
        # We count the cohort-block header class.
        n_blocks = self.html_cv.count('class="rge-cohort-block')
        self.assertEqual(n_blocks, 3,
                         f"expected 3 cohort blocks, got {n_blocks}")

    def test_cohort_block_quotes_real_headline_r2(self) -> None:
        # Each cohort block heading reads "national R² = XX.X%" with
        # the real headline number.
        import re
        m = re.search(
            r"national R² = (\d+\.\d+)%", self.html_cv,
        )
        self.assertIsNotNone(m, "cohort block must quote headline R²")
        self.assertGreater(float(m.group(1)), 0.0)

    # Learning curve -----------------------------------------------------
    def test_learning_curve_svg_present(self) -> None:
        self.assertIn('class="rge-lc-svg"', self.html_cv)
        # 20 dots total (10 train + 10 test)
        circles = self.html_cv.split('class="rge-lc-svg"', 1)[1]
        circles = circles.split("</svg>", 1)[0]
        n_circles = circles.count("<circle")
        self.assertEqual(n_circles, 20, f"expected 20 LC dots, got {n_circles}")

    def test_learning_curve_verdict_present(self) -> None:
        # Either plateau or "still moving" must show
        self.assertTrue(
            "plateau" in self.html_cv
            or "still moving" in self.html_cv,
            "learning curve must render a plateau verdict",
        )

    # Leverage scatter ---------------------------------------------------
    def test_leverage_scatter_svg_present(self) -> None:
        self.assertIn('class="rge-lev-svg"', self.html_cv)

    def test_leverage_scatter_has_legend(self) -> None:
        # The 4-class legend: Normal / High leverage / Outlier /
        # Possible opportunity.
        for label in ("Normal", "Outlier", "Possible opportunity"):
            self.assertIn(label, self.html_cv)

    # Interpretation block -----------------------------------------------
    def test_interpretation_two_columns(self) -> None:
        self.assertIn('class="col use"', self.html_cv)
        self.assertIn('class="col skip"', self.html_cv)

    def test_interpretation_has_bullets_each_side(self) -> None:
        # Each column must render at least one <li>.
        use_block = self.html_cv.split('class="col use"', 1)[1]
        use_block = use_block.split('class="col skip"', 1)[0]
        skip_block = self.html_cv.split('class="col skip"', 1)[1]
        skip_block = skip_block.split("</div>", 1)[0]
        self.assertGreaterEqual(use_block.count("<li>"), 1)
        self.assertGreaterEqual(skip_block.count("<li>"), 1)

    def test_interpretation_anchor_next_present(self) -> None:
        # Verdict-row "DO NEXT" card jumps here.
        self.assertIn('id="next"', self.html_cv)

    # Anchor invariants --------------------------------------------------
    def test_all_verdict_anchor_targets_still_exist(self) -> None:
        # Verdict row still scrolls to a real element — Phase 2
        # didn't break the spec §3 anchor contract.
        for anchor_id in ("fit", "prediction", "cohort",
                          "leverage", "next"):
            self.assertIn(f'id="{anchor_id}"', self.html_cv)


if __name__ == "__main__":
    unittest.main()
