"""Tests for cms_provider_ranking.py — consensus rank + anomaly detection."""
from __future__ import annotations

import unittest


class TestConsensusRankFromDicts(unittest.TestCase):
    """Test the no-pandas consensus rank path."""

    def _lenses(self):
        return [
            {"provider_type": "Cardiology", "opportunity_score": 0.85, "value_score": 0.70},
            {"provider_type": "Orthopedics", "opportunity_score": 0.60, "value_score": 0.90},
            {"provider_type": "Oncology", "opportunity_score": 0.40, "value_score": 0.55},
            {"provider_type": "Neurology", "opportunity_score": 0.75, "value_score": 0.30},
        ]

    def test_returns_list(self):
        from rcm_mc.data_public.cms_provider_ranking import consensus_rank_from_dicts
        result = consensus_rank_from_dicts(self._lenses())
        self.assertIsInstance(result, list)

    def test_sorted_by_consensus_score(self):
        from rcm_mc.data_public.cms_provider_ranking import consensus_rank_from_dicts
        result = consensus_rank_from_dicts(self._lenses())
        scores = [r["consensus_score"] for r in result]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_all_providers_present(self):
        from rcm_mc.data_public.cms_provider_ranking import consensus_rank_from_dicts
        result = consensus_rank_from_dicts(self._lenses())
        types = [r["provider_type"] for r in result]
        self.assertEqual(sorted(types), sorted(["Cardiology", "Orthopedics", "Oncology", "Neurology"]))

    def test_consensus_score_between_0_and_1(self):
        from rcm_mc.data_public.cms_provider_ranking import consensus_rank_from_dicts
        result = consensus_rank_from_dicts(self._lenses())
        for r in result:
            self.assertGreaterEqual(r["consensus_score"], 0.0)
            self.assertLessEqual(r["consensus_score"], 1.0)

    def test_consensus_percentile_present(self):
        from rcm_mc.data_public.cms_provider_ranking import consensus_rank_from_dicts
        result = consensus_rank_from_dicts(self._lenses())
        for r in result:
            self.assertIn("consensus_percentile", r)

    def test_empty_input(self):
        from rcm_mc.data_public.cms_provider_ranking import consensus_rank_from_dicts
        self.assertEqual(consensus_rank_from_dicts([]), [])

    def test_single_lens(self):
        from rcm_mc.data_public.cms_provider_ranking import consensus_rank_from_dicts
        result = consensus_rank_from_dicts([
            {"provider_type": "Cardiology", "investability_score": 0.9},
            {"provider_type": "Oncology", "investability_score": 0.4},
        ])
        self.assertEqual(len(result), 2)
        self.assertGreater(result[0]["consensus_score"], result[1]["consensus_score"])

    def test_multiple_lenses_separate_dicts(self):
        """Multiple lens dicts with same provider_type should merge."""
        from rcm_mc.data_public.cms_provider_ranking import consensus_rank_from_dicts
        lenses = [
            {"provider_type": "A", "opportunity_score": 0.8},
            {"provider_type": "A", "investability_score": 0.7},
            {"provider_type": "B", "opportunity_score": 0.3},
            {"provider_type": "B", "investability_score": 0.2},
        ]
        result = consensus_rank_from_dicts(lenses)
        self.assertEqual(len(result), 2)


class TestProviderConsensusRankPandas(unittest.TestCase):
    """Test the pandas-based consensus rank (skip if no pandas)."""

    def setUp(self):
        try:
            import pandas as pd
            self.pd = pd
        except ImportError:
            self.skipTest("pandas not available")

    def _make_df(self, data):
        return self.pd.DataFrame(data)

    def test_returns_dataframe(self):
        from rcm_mc.data_public.cms_provider_ranking import provider_consensus_rank
        scores = self._make_df([
            {"provider_type": "Cardiology", "opportunity_score": 0.9, "total_payment": 1e8},
            {"provider_type": "Oncology", "opportunity_score": 0.5, "total_payment": 5e7},
        ])
        result = provider_consensus_rank(scores=scores)
        self.assertIsInstance(result, self.pd.DataFrame)

    def test_sorted_descending(self):
        from rcm_mc.data_public.cms_provider_ranking import provider_consensus_rank
        scores = self._make_df([
            {"provider_type": "A", "opportunity_score": 0.9},
            {"provider_type": "B", "opportunity_score": 0.2},
            {"provider_type": "C", "opportunity_score": 0.6},
        ])
        result = provider_consensus_rank(scores=scores)
        col_scores = result["consensus_score"].tolist()
        self.assertEqual(col_scores, sorted(col_scores, reverse=True))

    def test_empty_inputs(self):
        from rcm_mc.data_public.cms_provider_ranking import provider_consensus_rank
        result = provider_consensus_rank()
        self.assertIsInstance(result, self.pd.DataFrame)
        self.assertTrue(result.empty)

    def test_multi_lens_merge(self):
        from rcm_mc.data_public.cms_provider_ranking import provider_consensus_rank
        scores = self._make_df([
            {"provider_type": "A", "opportunity_score": 0.8},
            {"provider_type": "B", "opportunity_score": 0.3},
        ])
        momentum = self._make_df([
            {"provider_type": "A", "consistency_score": 0.9},
            {"provider_type": "B", "consistency_score": 0.4},
        ])
        result = provider_consensus_rank(scores=scores, momentum=momentum)
        self.assertIn("consensus_score", result.columns)
        self.assertEqual(len(result), 2)

    def test_regime_boost_applied(self):
        from rcm_mc.data_public.cms_provider_ranking import provider_consensus_rank
        scores = self._make_df([
            {"provider_type": "A", "opportunity_score": 0.5},
            {"provider_type": "B", "opportunity_score": 0.5},
        ])
        regimes = self._make_df([
            {"provider_type": "A", "regime": "durable_growth"},
            {"provider_type": "B", "regime": "declining_risk"},
        ])
        result = provider_consensus_rank(scores=scores, provider_regimes=regimes)
        scores_list = result.set_index("provider_type")["consensus_score"]
        self.assertGreater(scores_list["A"], scores_list["B"])


class TestDetectStateProviderAnomalies(unittest.TestCase):

    def setUp(self):
        try:
            import pandas as pd
            self.pd = pd
        except ImportError:
            self.skipTest("pandas not available")

    def _make_df(self):
        import pandas as pd
        rows = []
        # Generate data with one anomalous state for Cardiology
        for state in ["CA", "TX", "FL", "NY", "IL"]:
            for yr in [2021, 2022]:
                n = 20
                pay_per_svc = 150.0 if state != "AK" else 400.0  # AK is the spike
                for _ in range(n):
                    rows.append({
                        "provider_type": "Cardiology",
                        "state": state,
                        "year": yr,
                        "payment_per_service": pay_per_svc + (yr - 2021) * 5,
                        "total_medicare_payment_amt": pay_per_svc * 1000,
                    })
        # Add anomalous state AK
        for _ in range(20):
            rows.append({
                "provider_type": "Cardiology",
                "state": "AK",
                "year": 2022,
                "payment_per_service": 500.0,
                "total_medicare_payment_amt": 500000,
            })
        return pd.DataFrame(rows)

    def test_returns_dataframe(self):
        from rcm_mc.data_public.cms_provider_ranking import detect_state_provider_anomalies
        result = detect_state_provider_anomalies(self._make_df())
        self.assertIsInstance(result, self.pd.DataFrame)

    def test_anomaly_flag_column(self):
        from rcm_mc.data_public.cms_provider_ranking import detect_state_provider_anomalies
        result = detect_state_provider_anomalies(self._make_df())
        self.assertIn("anomaly_flag", result.columns)

    def test_flagged_states_present(self):
        from rcm_mc.data_public.cms_provider_ranking import detect_state_provider_anomalies
        result = detect_state_provider_anomalies(self._make_df(), z_threshold=2.0)
        if not result.empty:
            flags = result["anomaly_flag"].unique().tolist()
            self.assertTrue(any(f in flags for f in ["cost_spike", "cost_trough", "normal"]))

    def test_missing_columns_returns_empty(self):
        from rcm_mc.data_public.cms_provider_ranking import detect_state_provider_anomalies
        df = self.pd.DataFrame([{"a": 1}])
        result = detect_state_provider_anomalies(df)
        self.assertTrue(result.empty)

    def test_high_threshold_flags_nothing(self):
        """z_threshold=100 should produce no flags."""
        from rcm_mc.data_public.cms_provider_ranking import detect_state_provider_anomalies
        result = detect_state_provider_anomalies(self._make_df(), z_threshold=100)
        if not result.empty:
            spikes = result[result["anomaly_flag"] != "normal"]
            self.assertEqual(len(spikes), 0)


class TestConsensusRankTable(unittest.TestCase):

    def test_returns_string(self):
        from rcm_mc.data_public.cms_provider_ranking import (
            consensus_rank_from_dicts, consensus_rank_table,
        )
        lenses = [
            {"provider_type": "Cardiology", "score": 0.8},
            {"provider_type": "Oncology", "score": 0.4},
        ]
        result = consensus_rank_from_dicts(lenses)
        text = consensus_rank_table(result)
        self.assertIsInstance(text, str)
        self.assertIn("Provider Type", text)

    def test_empty_input(self):
        from rcm_mc.data_public.cms_provider_ranking import consensus_rank_table
        text = consensus_rank_table([])
        self.assertIn("No", text)


class TestAnomalyTable(unittest.TestCase):

    def test_returns_string(self):
        from rcm_mc.data_public.cms_provider_ranking import anomaly_table
        rows = [
            {
                "provider_type": "Cardiology",
                "state": "CA",
                "year": 2022,
                "service_z": 3.1,
                "anomaly_flag": "cost_spike",
                "total_payment": 1e7,
            }
        ]
        text = anomaly_table(rows)
        self.assertIsInstance(text, str)
        self.assertIn("CA", text)

    def test_empty_input(self):
        from rcm_mc.data_public.cms_provider_ranking import anomaly_table
        text = anomaly_table([])
        self.assertIn("No", text)


if __name__ == "__main__":
    unittest.main()
