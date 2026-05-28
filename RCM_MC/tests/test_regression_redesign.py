"""Editorial redesign of /portfolio/regression — anatomy + honesty.

The redesign brief (handoff dated 2026-05-28) restructures the
masthead of the regression analysis page to lead with VISUALS not
numbers, and to make the page state honest about which blocks need
new compute. These tests pin the contract:

  · Spec §2 — single editorial page-title block with the eyebrow
    "STATISTICAL ANALYTICS" and a meta line describing the fit.
  · Spec §3 — slim diagnostic strip at the masthead.
  · Spec §4 — 6-tile headline metric strip, ALL six tiles present
    even when CV is off (the OOS tile renders the "Awaiting CV"
    pending pill per spec §4 Partial; never a fake number).
  · Spec §5 — 3-tile hero (calibration / residuals / drivers).
  · Spec §6 — 5-card verdict row, each card anchor-linked to the
    matching supporting block (#fit / #prediction / #cohort /
    #leverage / #next). Each card's lead phrase quotes a real
    number from the live fit.
  · _run_ols additive contract — ``residual_summary`` and
    ``calibration_deciles`` ship on every successful fit so the
    hero tiles don't have to fall back to the pending pill on a
    sufficiently-sized fit.
  · ONE <h1> per page (the #1036 accessibility invariant).
"""
from __future__ import annotations

import unittest

import numpy as np
import pandas as pd


def _synthetic_hcris(n: int = 220, seed: int = 42) -> pd.DataFrame:
    """A synthetic HCRIS frame just big enough for 5-fold CV with
    every editorial block populated. Mirrors the column conventions
    the regression page expects (ccn, name, state, segment_label
    isn't required — the universe filter falls back to "all" when
    it's missing)."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "ccn": [f"{i:06d}" for i in range(n)],
        "name": [f"Hospital {i}" for i in range(n)],
        "state": rng.choice(["CA", "NY", "TX", "FL", "OH", "PA"], n),
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


class RunOlsEditorialFieldsTests(unittest.TestCase):
    """The additive fields the editorial hero tiles wire to."""

    def setUp(self) -> None:
        from rcm_mc.ui.regression_page import _run_ols
        df = _synthetic_hcris()
        self.result = _run_ols(
            df, "net_patient_revenue",
            ["beds", "occupancy_rate", "medicare_day_pct",
             "medicaid_day_pct", "operating_expenses",
             "total_patient_days"],
            log_target=True,
        )

    def test_residual_summary_present(self) -> None:
        self.assertIn("residual_summary", self.result)
        rs = self.result["residual_summary"]
        self.assertIsNotNone(rs)
        # 14-bin histogram (spec §C)
        self.assertEqual(len(rs["histogram"]), 14)
        # Each bin carries the share + bounds the chart needs
        for b in rs["histogram"]:
            self.assertIn("x_lo", b)
            self.assertIn("x_hi", b)
            self.assertIn("share", b)
            self.assertGreaterEqual(b["share"], 0.0)
        # Shares roughly sum to 1 (small floating drift OK)
        self.assertAlmostEqual(
            sum(b["share"] for b in rs["histogram"]), 1.0, places=2,
        )
        # Skew + tail shares + percentile half-widths exist
        for key in (
            "skew", "kurtosis", "share_outside_2s",
            "share_outside_3s", "p50_abs", "p80_abs", "p95_abs",
        ):
            self.assertIn(key, rs)
        # The p80 absolute residual must be a non-negative number
        # (it feeds the headline 80% PI tile).
        self.assertGreaterEqual(rs["p80_abs"], 0.0)

    def test_calibration_deciles_present(self) -> None:
        deciles = self.result["calibration_deciles"]
        self.assertIsNotNone(deciles)
        self.assertEqual(len(deciles), 10)
        for d in deciles:
            self.assertIn("decile", d)
            self.assertIn("n", d)
            self.assertIn("mean_predicted", d)
            self.assertIn("mean_actual", d)
            # Predicted/actual are in raw target units (dollars), not
            # log space — partner reads "predicted $X, actual $Y".
            self.assertGreater(d["mean_predicted"], 0.0)
            self.assertGreater(d["mean_actual"], 0.0)
        # Deciles are monotone-non-decreasing on predicted (by
        # construction — they're built off np.argsort(y_hat)).
        preds = [d["mean_predicted"] for d in deciles]
        for i in range(1, len(preds)):
            self.assertGreaterEqual(preds[i], preds[i - 1])


class EditorialAnatomyTests(unittest.TestCase):
    """The spec's 20-section anatomy items §1-§6, rendered correctly."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.regression_page import render_regression_page
        df = _synthetic_hcris()
        # Two renderings: with CV on (so OOS R²/overfit gap quote real
        # numbers) and with CV off (so the awaiting-data path is
        # exercised).
        cls.html_cv = render_regression_page(
            hcris_df=df, log_target=True, cv=True,
        )
        cls.html_no_cv = render_regression_page(
            hcris_df=df, log_target=True, cv=False,
        )

    # ── Spec §2 — Page header ─────────────────────────────────────
    def test_eyebrow_present(self) -> None:
        # The spec's eyebrow over the H1.
        self.assertIn("STATISTICAL ANALYTICS", self.html_cv)

    def test_one_h1_per_page(self) -> None:
        # Accessibility invariant (#1036) — exactly one <h1> per page.
        count = self.html_cv.lower().count("<h1")
        self.assertEqual(
            count, 1,
            f"expected exactly one <h1> on the regression page, got {count}",
        )

    def test_meta_line_describes_fit(self) -> None:
        # The mono meta line per spec §2: OLS · TARGET · N · CV · ...
        self.assertIn("OLS", self.html_cv)
        self.assertIn("FEATURES", self.html_cv)
        self.assertIn("5-FOLD CV", self.html_cv)
        # With CV off, the "5-FOLD CV" segment should NOT appear in
        # the meta line.
        self.assertNotIn("5-FOLD CV", self.html_no_cv.split(
            'class="ck-page-title"', 1)[1].split("</header>", 1)[0])

    # ── Spec §3 — Diagnostic strip ────────────────────────────────
    def test_diagnostic_strip_present(self) -> None:
        self.assertIn("rge-diag", self.html_cv)
        self.assertIn("Read this", self.html_cv)
        self.assertIn("in-sample", self.html_cv)

    # ── Spec §4 — Headline metric strip ───────────────────────────
    def test_headline_strip_has_six_tiles(self) -> None:
        self.assertIn("rge-strip", self.html_cv)
        # Six labels per spec §4: R² · OOS R² · OVERFIT GAP · RMSE ·
        # 80% PI WIDTH · CONDITION #. Order is binding.
        for label in (
            ">R²<", "OOS R²", "Overfit gap", "RMSE",
            "80% PI width", "Condition #",
        ):
            self.assertIn(label, self.html_cv, f"missing tile: {label}")

    def test_oos_r2_awaits_cv_when_cv_off(self) -> None:
        # Spec §4 Partial state — no fake number when CV isn't on.
        self.assertIn("Awaiting CV", self.html_no_cv)

    def test_oos_r2_quotes_real_number_when_cv_on(self) -> None:
        # CV is on → OOS R² tile must NOT show "Awaiting CV".
        # Find the OOS R² tile body and check for a percentage.
        import re
        # The OOS R² tile renders as: <div class="label">OOS R²</div>
        # <div class="val">...
        m = re.search(
            r'OOS R²</div>\s*<div class="val">([^<]+)</div>',
            self.html_cv,
        )
        self.assertIsNotNone(m, "could not locate OOS R² tile body")
        body = m.group(1).strip()
        self.assertNotIn("Awaiting", body)
        # It should look like a percent — has '%' OR is the pending pill.
        self.assertIn("%", body)

    # ── Spec §5 — Hero dashboard ──────────────────────────────────
    def test_hero_has_three_tiles(self) -> None:
        self.assertIn("rge-hero", self.html_cv)
        # Three tile eyebrows per spec §5
        self.assertIn(">Calibration<", self.html_cv)
        self.assertIn(">Residuals<", self.html_cv)
        self.assertIn(">Drivers<", self.html_cv)

    def test_hero_drivers_wired_to_real_coefficients(self) -> None:
        # The drivers tile's bar rows must include real feature
        # names from the fit — never editorial placeholders.
        # Use a recognizable feature label.
        # ``Operating Expenses`` shows up only when the rendered tile
        # actually iterated over the coefficient list.
        self.assertIn("Operating Expenses", self.html_cv)

    def test_hero_calibration_renders_pts(self) -> None:
        # 10 decile points → 10 .pt spans on the calibration scatter.
        # Count the bare ``class="pt"`` substring AFTER the CSS block
        # (which also contains ``.rge-cal{...``). The actual tile body
        # is the second match for the substring ``rge-cal``.
        first = self.html_cv.find('class="rge-cal"')
        self.assertGreater(first, 0)
        cal_body = self.html_cv[first:first + 4000]
        n_pts = cal_body.count('class="pt"') + cal_body.count('class="pt out"')
        self.assertGreaterEqual(n_pts, 8,
                                f"expected ≥8 calibration pts, got {n_pts}")

    def test_hero_residual_histogram_renders_bars(self) -> None:
        # 14 bins → 14 bars inside the .rge-hist tile body.
        first = self.html_cv.find('class="rge-hist"')
        self.assertGreater(first, 0)
        hist_body = self.html_cv[first:first + 4000]
        # Tile uses <div class="b ..."> for each bin.
        n_bars = (
            hist_body.count('<div class="b mid"')
            + hist_body.count('<div class="b tail"')
            + hist_body.count('<div class="b tail-amber"')
            + hist_body.count('<div class="b"')
        )
        self.assertEqual(n_bars, 14, f"expected 14 hist bars, got {n_bars}")

    # ── Spec §6 — Verdict row ─────────────────────────────────────
    def test_verdict_row_has_five_anchor_cards(self) -> None:
        # Five anchor hrefs, in spec §6 order.
        for anchor in ("#fit", "#prediction", "#cohort", "#leverage", "#next"):
            self.assertIn(f'href="{anchor}"', self.html_cv,
                          f"missing verdict anchor: {anchor}")

    def test_verdict_anchor_targets_exist(self) -> None:
        # Spec §3 interaction contract — every anchor in the verdict
        # row must scroll to a real element on the page.
        for anchor_id in ("fit", "prediction", "cohort", "leverage", "next"):
            self.assertIn(f'id="{anchor_id}"', self.html_cv,
                          f"missing anchor target: id={anchor_id}")

    def test_verdict_signal_quotes_real_significance(self) -> None:
        # The SIGNAL card's lead phrase quotes "<sig>/<p> features
        # significant" from the live fit — never a fake number.
        import re
        # Match e.g. "5/6 features significant" anywhere in the verdict
        # row's body.
        m = re.search(r"(\d+)/(\d+) features significant", self.html_cv)
        self.assertIsNotNone(
            m, "signal card must quote a real <sig>/<p> count",
        )

    def test_verdict_role_status_attrs(self) -> None:
        # Spec §5 accessibility — every verdict card has role=status.
        self.assertGreaterEqual(self.html_cv.count('role="status"'), 5)


class RegressionPageStillWorksTests(unittest.TestCase):
    """Sanity — the existing analytical content is still on the page."""

    @classmethod
    def setUpClass(cls) -> None:
        from rcm_mc.ui.regression_page import render_regression_page
        cls.html = render_regression_page(
            hcris_df=_synthetic_hcris(), log_target=True, cv=False,
        )

    def test_existing_kpi_strip_still_present(self) -> None:
        # The legacy ck-kpi-strip (R² / Adj R² / Observations / ...)
        # is still emitted below the editorial top-block — partner
        # reads BOTH the editorial masthead AND the full analytical
        # detail. We never silently drop content.
        self.assertIn("ck-kpi-strip", self.html)

    def test_regression_inputs_form_still_present(self) -> None:
        # The Run Regression form survives.
        self.assertIn("Run Regression", self.html)

    def test_feature_leakage_section_still_present(self) -> None:
        self.assertIn("Feature Leakage", self.html)


if __name__ == "__main__":
    unittest.main()
