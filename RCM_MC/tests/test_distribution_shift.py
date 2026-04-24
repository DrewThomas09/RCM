"""Distribution-shift check.

A dental-DSO CCD scored against an acute-hospital corpus must come
back OUT_OF_DISTRIBUTION. A fresh acute-hospital CCD against the
same corpus must come back IN_DISTRIBUTION or DRIFTING.
"""
from __future__ import annotations

import random
import unittest
from pathlib import Path

from rcm_mc.diligence import ingest_dataset, score_distribution
from rcm_mc.diligence.integrity.distribution_shift import (
    DistributionScore, classify_shift, features_from_ccd,
)


FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "kpi_truth"


def _simulate_acute_corpus(seed: int = 0, n: int = 2000) -> dict:
    """Synthetic corpus distribution representing the acute-hospital
    population the brain was calibrated on. Used as the
    ``corpus_features`` against which new CCDs are compared."""
    r = random.Random(seed)
    return {
        "charge_amount": [r.gauss(1500, 400) for _ in range(n)],
        "paid_amount":   [r.gauss(1100, 350) for _ in range(n)],
        "days_in_ar":    [max(0, r.gauss(30, 10)) for _ in range(n)],
        # Acute corpus is ~50% Medicare.
        "medicare_share": [1.0 if r.random() < 0.5 else 0.0 for _ in range(n)],
    }


class DistributionShiftTests(unittest.TestCase):

    def test_classify_shift_thresholds(self):
        self.assertEqual(
            classify_shift(psi=0.05, ks_d=0.05),
            DistributionScore.IN_DISTRIBUTION,
        )
        self.assertEqual(
            classify_shift(psi=0.12, ks_d=0.08),
            DistributionScore.DRIFTING,
        )
        self.assertEqual(
            classify_shift(psi=0.30, ks_d=0.05),
            DistributionScore.OUT_OF_DISTRIBUTION,
        )
        self.assertEqual(
            classify_shift(psi=0.05, ks_d=0.25),
            DistributionScore.OUT_OF_DISTRIBUTION,
        )

    def test_dental_dso_is_out_of_distribution(self):
        corpus = _simulate_acute_corpus()
        ds = ingest_dataset(FIXTURE_ROOT / "hospital_05_dental_dso")
        new_features = features_from_ccd(ds)
        # Pad with synthetic rows so we clear the min_samples gate —
        # the fixture only has 40 claims and the check wants 30+ per
        # feature; 40 is tight. We oversample by duplication to
        # exercise the branch semantics without importing scipy.
        padded = {k: list(v) * 4 for k, v in new_features.items()}
        report = score_distribution(padded, corpus)
        self.assertEqual(report.overall, DistributionScore.OUT_OF_DISTRIBUTION,
                         msg=f"expected OOD for DSO; got {report.overall}: "
                             f"worst_feat={report.worst_feature} "
                             f"psi={report.worst_psi:.3f}")

    def test_acute_like_ccd_is_in_distribution_or_drifting(self):
        """A synthetic acute-like CCD (charge ~1500, paid ~1100,
        DAR ~30, ~50% Medicare share) against an acute corpus with
        matching parameters should land IN_DISTRIBUTION or at worst
        DRIFTING — a distribution that looks like the corpus cannot
        be OOD."""
        corpus = _simulate_acute_corpus(seed=0)
        # Synthetic acute-like sample drawn from the same
        # distribution family (different seed so it isn't identical).
        r = random.Random(42)
        new_features = {
            "charge_amount":  [r.gauss(1500, 400) for _ in range(500)],
            "paid_amount":    [r.gauss(1100, 350) for _ in range(500)],
            "days_in_ar":     [max(0, r.gauss(30, 10)) for _ in range(500)],
            "medicare_share": [1.0 if r.random() < 0.5 else 0.0 for _ in range(500)],
        }
        report = score_distribution(new_features, corpus)
        self.assertIn(
            report.overall,
            (DistributionScore.IN_DISTRIBUTION, DistributionScore.DRIFTING),
            msg=f"acute-like sample should not be OOD; got {report.overall} "
                f"worst={report.worst_feature} psi={report.worst_psi:.3f}",
        )

    def test_empty_ccd_flags_out_of_distribution(self):
        """No rows → insufficient_samples → OOD (safe failure)."""
        corpus = _simulate_acute_corpus()
        report = score_distribution(
            {"charge_amount": [], "paid_amount": [], "days_in_ar": [],
             "medicare_share": []},
            corpus,
        )
        self.assertEqual(report.overall, DistributionScore.OUT_OF_DISTRIBUTION)


if __name__ == "__main__":
    unittest.main()
