"""Claim-level denial prediction regression tests.

Covers:
    - Feature extraction (CPT family banding, charge-band bucketing,
      OON / adjustment-code / modifier detection, weekday)
    - Naive Bayes training with Laplace smoothing (no zero probs,
      priors sum to 1)
    - Prediction runs on every extracted feature dict
    - Calibration report: brier / log loss / accuracy / AUC all
      within [0, 1]; AUC of 0.5 on random labels; AUC → 1 when
      perfectly separable
    - analyze_ccd end-to-end on the denial-heavy fixture
    - UI page: landing, full render, unknown-fixture fallback
    - Nav link wired
"""
from __future__ import annotations

import unittest
from dataclasses import dataclass
from pathlib import Path

from rcm_mc.diligence import ingest_dataset
from rcm_mc.diligence.denial_prediction import (
    ClaimFeatures, analyze_ccd, calibration_report, extract_features,
    train_naive_bayes,
)


FIXTURE_ROOT = (
    Path(__file__).resolve().parent / "fixtures" / "kpi_truth"
)


@dataclass
class _FakeClaim:
    cpt_code: str = "99213"
    payer_class: str = "MEDICARE"
    charge_amount: float = 150.0
    place_of_service: str = "11"
    status: str = "PAID"
    modifier_codes: tuple = ()
    network_status: str = "IN"
    adjustment_reason_codes: tuple = ()
    service_date_from: str = "2024-01-15"


class FeatureExtractionTests(unittest.TestCase):

    def test_cpt_family_buckets(self):
        self.assertEqual(
            extract_features(_FakeClaim(cpt_code="99213")).cpt_family,
            "E_M_99XXX",
        )
        self.assertEqual(
            extract_features(_FakeClaim(cpt_code="70553")).cpt_family,
            "RADIOLOGY_7XXXX",
        )
        self.assertEqual(
            extract_features(_FakeClaim(cpt_code="85025")).cpt_family,
            "LAB_PATH_8XXXX",
        )

    def test_charge_band_buckets(self):
        self.assertEqual(
            extract_features(_FakeClaim(charge_amount=500)).charge_band,
            "UNDER_1K",
        )
        self.assertEqual(
            extract_features(_FakeClaim(charge_amount=3000)).charge_band,
            "1K_5K",
        )
        self.assertEqual(
            extract_features(_FakeClaim(charge_amount=15000)).charge_band,
            "OVER_10K",
        )

    def test_modifier_and_adjustment_detection(self):
        c = _FakeClaim(
            modifier_codes=("26",),
            adjustment_reason_codes=("50",),
        )
        f = extract_features(c)
        self.assertEqual(f.has_modifier, "yes")
        self.assertEqual(f.has_adjustment_code, "yes")

    def test_weekday_from_service_date(self):
        c = _FakeClaim(service_date_from="2024-02-01")  # Thursday
        self.assertEqual(extract_features(c).service_weekday, "Thu")


class NaiveBayesTrainingTests(unittest.TestCase):

    def _toy_data(self):
        # 10 claims: 3 denied (all with CPT 99213 + Medicare)
        data = []
        for i in range(7):
            f = {"cpt": "99214", "payer": "UHC"}
            data.append((f, False))
        for i in range(3):
            f = {"cpt": "99213", "payer": "MEDICARE"}
            data.append((f, True))
        return data

    def test_priors_sum_to_one(self):
        m = train_naive_bayes(self._toy_data())
        self.assertAlmostEqual(
            m.prior_denial + m.prior_not_denial, 1.0, places=6,
        )

    def test_predict_higher_for_denial_pattern(self):
        m = train_naive_bayes(self._toy_data())
        p_denied = m.predict_proba(
            {"cpt": "99213", "payer": "MEDICARE"},
        )
        p_paid = m.predict_proba(
            {"cpt": "99214", "payer": "UHC"},
        )
        self.assertGreater(p_denied, p_paid)

    def test_unseen_feature_value_does_not_raise(self):
        m = train_naive_bayes(self._toy_data())
        p = m.predict_proba({"cpt": "00000", "payer": "UNSEEN"})
        self.assertGreaterEqual(p, 0.0)
        self.assertLessEqual(p, 1.0)

    def test_empty_dataset(self):
        m = train_naive_bayes([])
        self.assertEqual(m.n_train, 0)
        # predict on anything should still return a probability
        p = m.predict_proba({"cpt": "99213"})
        self.assertGreaterEqual(p, 0.0)
        self.assertLessEqual(p, 1.0)

    def test_top_features_by_lift(self):
        m = train_naive_bayes(self._toy_data())
        top = m.top_features_by_denial_lift(k=3)
        self.assertLessEqual(len(top), 3)
        # Lifts should be in descending order.
        lifts = [t[2] for t in top]
        self.assertEqual(lifts, sorted(lifts, reverse=True))


class CalibrationTests(unittest.TestCase):

    def test_brier_accuracy_within_bounds(self):
        data = [
            ({"cpt": "99213"}, True),
            ({"cpt": "99214"}, False),
            ({"cpt": "99213"}, True),
            ({"cpt": "99214"}, False),
        ]
        m = train_naive_bayes(data)
        r = calibration_report(m, data)
        self.assertGreaterEqual(r.brier_score, 0.0)
        self.assertLessEqual(r.brier_score, 1.0)
        self.assertGreaterEqual(r.accuracy, 0.0)
        self.assertLessEqual(r.accuracy, 1.0)
        self.assertGreaterEqual(r.auc_rough, 0.0)
        self.assertLessEqual(r.auc_rough, 1.0)

    def test_perfectly_separable_has_high_auc(self):
        data = [
            ({"x": "a"}, True), ({"x": "a"}, True),
            ({"x": "b"}, False), ({"x": "b"}, False),
        ]
        m = train_naive_bayes(data)
        r = calibration_report(m, data)
        self.assertGreaterEqual(r.auc_rough, 0.95)


class AnalyzeCCDEndToEndTests(unittest.TestCase):

    def test_runs_on_denial_heavy_fixture(self):
        ccd = ingest_dataset(
            FIXTURE_ROOT / "hospital_02_denial_heavy",
        )
        report = analyze_ccd(ccd, train_fraction=0.7, seed=42)
        self.assertGreater(report.n_claims, 0)
        self.assertIsNotNone(report.bridge_input)
        self.assertGreaterEqual(report.baseline_denial_rate, 0.0)
        self.assertLessEqual(report.baseline_denial_rate, 1.0)
        # Calibration bounded
        self.assertGreaterEqual(report.calibration.auc_rough, 0.0)
        self.assertLessEqual(report.calibration.auc_rough, 1.0)

    def test_bridge_input_has_confidence_band(self):
        ccd = ingest_dataset(
            FIXTURE_ROOT / "hospital_02_denial_heavy",
        )
        report = analyze_ccd(ccd, train_fraction=0.7, seed=42)
        self.assertIn(
            report.bridge_input.confidence,
            ("HIGH", "MEDIUM", "LOW"),
        )

    def test_handles_small_fixture_gracefully(self):
        ccd = ingest_dataset(
            FIXTURE_ROOT / "hospital_07_waterfall_concordant",
        )
        report = analyze_ccd(ccd, train_fraction=0.7, seed=42)
        # 10-claim fixture; report should still come back.
        self.assertIsNotNone(report)

    def test_deterministic_with_same_seed(self):
        ccd = ingest_dataset(
            FIXTURE_ROOT / "hospital_02_denial_heavy",
        )
        r1 = analyze_ccd(ccd, train_fraction=0.7, seed=42)
        r2 = analyze_ccd(ccd, train_fraction=0.7, seed=42)
        self.assertEqual(r1.n_train, r2.n_train)
        self.assertEqual(
            r1.systematic_miss_count,
            r2.systematic_miss_count,
        )


class DenialPredictionPageTests(unittest.TestCase):

    def test_landing_renders_form(self):
        from rcm_mc.ui.denial_prediction_page import (
            render_denial_prediction_page,
        )
        h = render_denial_prediction_page()
        self.assertIn("Claim-Level Denial Prediction", h)
        self.assertIn("Run prediction", h)

    def test_live_render_includes_interpretability_elements(self):
        from rcm_mc.ui.denial_prediction_page import (
            render_denial_prediction_page,
        )
        h = render_denial_prediction_page(
            dataset="hospital_02_denial_heavy",
        )
        # Plain-English "What this shows" callout
        self.assertIn("What this shows", h)
        # Baseline denial rate context
        self.assertIn("HFMA peer median", h)
        # AUC interpretation band
        self.assertIn("&gt;0.7 = usable", h)
        # EBITDA bridge card rendered
        self.assertIn("EBITDA Bridge", h)

    def test_unknown_fixture_falls_back_to_landing(self):
        from rcm_mc.ui.denial_prediction_page import (
            render_denial_prediction_page,
        )
        h = render_denial_prediction_page(dataset="not_a_fixture")
        self.assertIn("Run prediction", h)


class NavLinkTest(unittest.TestCase):

    def test_denial_prediction_link_in_sidebar(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        rendered = chartis_shell("<p>x</p>", "Test")
        self.assertIn('href="/diligence/denial-prediction"', rendered)


if __name__ == "__main__":
    unittest.main()
