"""Tests for the DealComparablesEngine."""
from __future__ import annotations

import unittest
from typing import Any, Dict, List


def _synthetic_corpus() -> List[Dict[str, Any]]:
    """A small synthetic corpus with structure: 12 hospital deals
    of varying size + vintage + state, plus 8 physician-group
    deals and 4 ASC deals so PSM has signal to learn from."""
    corpus: List[Dict[str, Any]] = []
    for i in range(12):
        corpus.append({
            "source_id": f"hosp_{i:02d}",
            "deal_name": f"Hospital {i}",
            "sector": "hospital",
            "ev_mm": 200 + i * 50,
            "ebitda_at_entry_mm": 25 + i * 4,
            "year": 2018 + (i % 6),
            "state": "TX" if i % 2 == 0 else "FL",
            "buyer": "Sponsor A",
            "realized_moic": 1.8 + 0.1 * i,
            "ebitda_margin_at_entry": 0.13,
            "ebitda_margin_at_exit": 0.18,
            "payer_mix": {"medicare": 0.45, "medicaid": 0.20,
                          "commercial": 0.30, "self_pay": 0.05},
        })
    for i in range(8):
        corpus.append({
            "source_id": f"pg_{i:02d}",
            "deal_name": f"Physician Group {i}",
            "sector": "physician_group",
            "ev_mm": 80 + i * 30,
            "ebitda_at_entry_mm": 10 + i * 3,
            "year": 2019 + (i % 5),
            "state": "TX" if i % 3 == 0 else "CA",
            "buyer": "Sponsor B",
            "realized_moic": 2.4 + 0.15 * i,
            "ebitda_margin_at_entry": 0.16,
            "ebitda_margin_at_exit": 0.22,
            "payer_mix": {"medicare": 0.20, "medicaid": 0.10,
                          "commercial": 0.65, "self_pay": 0.05},
        })
    for i in range(4):
        corpus.append({
            "source_id": f"asc_{i:02d}",
            "deal_name": f"ASC {i}",
            "sector": "asc",
            "ev_mm": 150 + i * 40,
            "ebitda_at_entry_mm": 20 + i * 5,
            "year": 2020 + i,
            "state": "TX",
            "buyer": "Sponsor C",
            "realized_moic": 2.8 + 0.1 * i,
            "ebitda_margin_at_entry": 0.20,
            "ebitda_margin_at_exit": 0.25,
            "payer_mix": {"medicare": 0.15, "medicaid": 0.05,
                          "commercial": 0.75, "self_pay": 0.05},
        })
    return corpus


# ── Feature extraction ─────────────────────────────────────────

class TestFeatures(unittest.TestCase):
    def test_extracts_uniform_dimensionality(self):
        from rcm_mc.comparables import extract_features
        target = {
            "source_id": "TARGET", "sector": "hospital",
            "ev_mm": 300, "year": 2022, "state": "TX",
            "payer_mix": {"medicare": 0.45, "medicaid": 0.20,
                          "commercial": 0.30, "self_pay": 0.05},
        }
        corpus_fvs, target_fv = extract_features(
            _synthetic_corpus(), target)
        # All vectors must share the same shape
        d = target_fv.vector.size
        for fv in corpus_fvs:
            self.assertEqual(fv.vector.size, d)
        # Target's normalized features should be finite numbers
        import math
        for v in target_fv.vector:
            self.assertFalse(math.isnan(v))


# ── Logistic regression ────────────────────────────────────────

class TestLogistic(unittest.TestCase):
    def test_separable_classifies_correctly(self):
        import numpy as np
        from rcm_mc.comparables import fit_logistic
        rng = np.random.default_rng(0)
        # Linearly separable: y = 1 if x > 0 (mostly)
        X_pos = rng.normal(loc=2.0, scale=0.5, size=(50, 2))
        X_neg = rng.normal(loc=-2.0, scale=0.5, size=(50, 2))
        X = np.vstack([X_pos, X_neg])
        y = np.concatenate([np.ones(50), np.zeros(50)])
        model = fit_logistic(
            X, y, learning_rate=0.1, l2_penalty=0.001,
            max_iter=500,
        )
        preds = (model.predict_proba(X) > 0.5).astype(int)
        accuracy = float((preds == y).mean())
        self.assertGreater(accuracy, 0.95)


# ── PSM ────────────────────────────────────────────────────────

class TestPSM(unittest.TestCase):
    def test_psm_returns_matches(self):
        from rcm_mc.comparables import (
            extract_features, psm_match, PSMConfig,
        )
        target = {
            "source_id": "TARGET", "sector": "hospital",
            "ev_mm": 280, "year": 2021, "state": "TX",
            "payer_mix": {"medicare": 0.45, "medicaid": 0.20,
                          "commercial": 0.30, "self_pay": 0.05},
        }
        corpus_fvs, target_fv = extract_features(
            _synthetic_corpus(), target)
        result = psm_match(
            corpus_fvs, target_fv,
            config=PSMConfig(k_matches=5, caliper=0.5),
        )
        self.assertGreater(len(result.matches), 0)
        # Each match has (deal, distance, weight)
        for fv, dist, weight in result.matches:
            self.assertGreaterEqual(dist, 0)
            self.assertGreaterEqual(weight, 0)
            self.assertLessEqual(weight, 1.0)


# ── Mahalanobis ────────────────────────────────────────────────

class TestMahalanobis(unittest.TestCase):
    def test_mahalanobis_distances_non_negative(self):
        from rcm_mc.comparables import (
            extract_features, mahalanobis_distance_matrix,
        )
        target = {
            "source_id": "TARGET", "sector": "hospital",
            "ev_mm": 300, "year": 2022, "state": "TX",
            "payer_mix": {"medicare": 0.45},
        }
        corpus_fvs, target_fv = extract_features(
            _synthetic_corpus(), target)
        d = mahalanobis_distance_matrix(corpus_fvs, target_fv)
        self.assertEqual(d.size, len(corpus_fvs))
        for v in d:
            self.assertGreaterEqual(v, 0)

    def test_mahalanobis_match_returns_top_k(self):
        from rcm_mc.comparables import (
            extract_features, mahalanobis_match,
        )
        target = {
            "source_id": "TARGET", "sector": "hospital",
            "ev_mm": 300, "year": 2022, "state": "TX",
            "payer_mix": {"medicare": 0.45},
        }
        corpus_fvs, target_fv = extract_features(
            _synthetic_corpus(), target)
        matches = mahalanobis_match(
            corpus_fvs, target_fv, k_matches=10)
        self.assertEqual(len(matches), 10)
        # Distances should be non-decreasing
        distances = [m[1] for m in matches]
        self.assertEqual(distances, sorted(distances))


# ── End-to-end engine ──────────────────────────────────────────

class TestEngine(unittest.TestCase):
    def test_psm_engine_returns_full_result(self):
        from rcm_mc.comparables import run_comparables_engine
        target = {
            "source_id": "TARGET", "sector": "hospital",
            "ev_mm": 300, "year": 2022, "state": "TX",
            "payer_mix": {"medicare": 0.45, "medicaid": 0.20,
                          "commercial": 0.30, "self_pay": 0.05},
        }
        result = run_comparables_engine(
            _synthetic_corpus(), target, method="psm",
            k_matches=10,
        )
        self.assertEqual(result.method, "psm")
        self.assertGreater(result.n_matches, 0)
        # Each match has a weight in the weight_matrix
        for m in result.matches:
            self.assertIn(m["deal_id"], result.weight_matrix)
        # Multiple distributions must include at least the target
        # quantiles when matches have entry/exit data.
        self.assertIn("p50", result.entry_multiple_distribution)
        self.assertIn("p50", result.exit_multiple_distribution)
        self.assertIn("p50", result.margin_expansion_distribution)

    def test_mahalanobis_method_runs(self):
        from rcm_mc.comparables import run_comparables_engine
        target = {
            "source_id": "TARGET", "sector": "hospital",
            "ev_mm": 300, "year": 2022, "state": "TX",
            "payer_mix": {"medicare": 0.45},
        }
        result = run_comparables_engine(
            _synthetic_corpus(), target,
            method="mahalanobis", k_matches=8,
        )
        self.assertEqual(result.method, "mahalanobis")
        self.assertEqual(result.n_matches, 8)

    def test_unknown_method_raises(self):
        from rcm_mc.comparables import run_comparables_engine
        with self.assertRaises(ValueError):
            run_comparables_engine(
                _synthetic_corpus(),
                {"sector": "hospital"},
                method="randomforest",
            )


class TestConsensusMatch(unittest.TestCase):
    def setUp(self):
        self.target = {
            "source_id": "TARGET", "sector": "hospital",
            "ev_mm": 300, "year": 2022, "state": "TX",
            "payer_mix": {"medicare": 0.45, "medicaid": 0.20,
                          "commercial": 0.30, "self_pay": 0.05},
        }

    def test_consensus_returns_combined_view(self):
        from rcm_mc.comparables import consensus_match
        result = consensus_match(
            _synthetic_corpus(), self.target, k_matches=8)
        # Membership counts add up
        total = (result.n_psm_only + result.n_mahalanobis_only
                 + result.n_consensus)
        self.assertEqual(total, len(result.matches))
        # Each match has the membership flags + weights
        for m in result.matches:
            self.assertIsNotNone(m.in_psm)
            self.assertIsNotNone(m.in_mahalanobis)
            self.assertGreaterEqual(m.consensus_weight, 0)
            self.assertLessEqual(m.consensus_weight, 1.0)
        # Consensus matches sort first (largest weight)
        weights = [m.consensus_weight for m in result.matches]
        self.assertEqual(weights, sorted(weights, reverse=True))

    def test_balance_diagnostics_present(self):
        from rcm_mc.comparables import consensus_match
        result = consensus_match(
            _synthetic_corpus(), self.target, k_matches=10)
        # SMDs computed for every feature
        self.assertGreater(len(result.balance), 0)
        for d in result.balance:
            # Bands valid
            self.assertIn(d.band,
                          ("excellent", "acceptable", "concerning"))
            # SMD non-negative
            self.assertGreaterEqual(
                d.standardized_mean_difference, 0)

    def test_balance_excellent_for_well_matched(self):
        """A target very close to the synthetic hospital cluster
        should produce mostly excellent / acceptable balance for
        the sector + region one-hots."""
        from rcm_mc.comparables import consensus_match
        result = consensus_match(
            _synthetic_corpus(), self.target, k_matches=10)
        # At least one feature should hit excellent balance —
        # sector_hospital is a perfect indicator (1.0 vs ~1.0).
        excellent = [d for d in result.balance
                     if d.band == "excellent"]
        self.assertGreater(len(excellent), 0)


class TestBalanceDiagnosticsDirect(unittest.TestCase):
    def test_constant_feature_zero_smd(self):
        """If every comp has the same value as the target on a
        feature, SMD is 0 (excellent)."""
        from rcm_mc.comparables import (
            balance_diagnostics, extract_features,
        )
        target = {"source_id": "T", "sector": "hospital",
                  "ev_mm": 300, "year": 2022, "state": "TX"}
        comps = [
            {"source_id": f"c{i}", "sector": "hospital",
             "ev_mm": 300, "year": 2022, "state": "TX"}
            for i in range(5)
        ]
        corpus_fvs, target_fv = extract_features(comps, target)
        diag = balance_diagnostics(target_fv, corpus_fvs)
        # The sector_hospital + state_south features should be
        # identical → SMD = 0 → excellent
        bands = [d.band for d in diag]
        self.assertGreater(bands.count("excellent"), 0)


if __name__ == "__main__":
    unittest.main()
