import argparse
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from cms_api_advisory_analytics import (
    apply_quality_filters,
    build_advisory_memo,
    build_run_summary,
    correlation_table,
    data_quality_report,
    enrich_features,
    filter_year_range,
    growth_volatility_watchlist,
    market_concentration_summary,
    make_outputs,
    parse_extra_params,
    provider_screen,
    provider_volatility,
    provider_trend_shift,
    provider_value_summary,
    provider_investability_summary,
    provider_stress_test,
    stress_scenario_grid,
    provider_state_benchmark_flags,
    provider_momentum_profile,
    detect_state_provider_anomalies,
    provider_regime_classification,
    state_portfolio_fit,
    provider_consensus_rank,
    state_provider_white_space,
    provider_geo_dependency,
    provider_trend_reliability,
    provider_operating_posture,
    standardize_columns,
    state_growth_summary,
    state_volatility_summary,
    state_provider_heatmap,
    state_provider_opportunities,
    validate_runtime_inputs,
    winsorize_metrics,
    yearly_trends,
)


class CmsApiAdvisoryAnalyticsTest(unittest.TestCase):

    def _sample_df(self):
        return pd.DataFrame(
            {
                "rndrng_prvdr_type": ["Cardiology", "Cardiology", "Dermatology", "Dermatology"],
                "nppes_provider_state": ["CA", "CA", "TX", "TX"],
                "year": [2022, 2023, 2022, 2023],
                "total_services": [100, 120, 80, 95],
                "total_unique_benes": [45, 52, 38, 44],
                "total_submitted_chrg_amt": [20000, 24000, 10000, 12000],
                "total_medicare_payment_amt": [10000, 13000, 6000, 7500],
                "Beneficiary_Average_Risk_Score": [1.1, 1.2, 0.9, 0.95],
                "beneficiary_average_age": [72, 73, 70, 71],
            }
        )

    def _standardized(self):
        args = argparse.Namespace(provider_col=None, state_col=None, year_col=None)
        return standardize_columns(self._sample_df(), args)

    def test_standardize_columns(self):
        standardized = self._standardized()
        self.assertIn("provider_type", standardized.columns)
        self.assertIn("beneficiary_average_risk_score", standardized.columns)

    def test_enrich_features(self):
        enriched = enrich_features(self._standardized())
        self.assertIn("payment_per_service", enriched.columns)
        self.assertIn("payment_per_bene", enriched.columns)
        self.assertIn("charge_to_payment_ratio", enriched.columns)
        self.assertIn("log_payment_per_bene", enriched.columns)
        self.assertAlmostEqual(enriched.loc[0, "payment_per_service"], 100)

    def test_provider_screen(self):
        scored = provider_screen(enrich_features(self._standardized()))
        self.assertIn("opportunity_score", scored.columns)
        self.assertIn("fragmentation_score", scored.columns)
        self.assertIn("opportunity_percentile", scored.columns)
        self.assertEqual(set(scored.index), {"Cardiology", "Dermatology"})

    def test_correlation_table(self):
        corr = correlation_table(enrich_features(self._standardized()))
        self.assertFalse(corr.empty)
        self.assertIn("total_services", corr.columns)

    def test_yearly_trends_and_volatility(self):
        trends = yearly_trends(enrich_features(self._standardized()))
        self.assertIn("payment_yoy_pct", trends.columns)
        cardio_2023 = trends[(trends["provider_type"] == "Cardiology") & (trends["year"] == 2023)]
        self.assertAlmostEqual(float(cardio_2023.iloc[0]["payment_yoy_pct"]), 0.3)

        vol = provider_volatility(trends)
        self.assertIn("yoy_payment_volatility", vol.columns)


    def test_filter_year_range(self):
        standardized = self._standardized()
        filtered = filter_year_range(standardized, min_year=2023, max_year=2023)
        self.assertTrue((filtered["year"] == 2023).all())
        self.assertEqual(len(filtered), 2)

    def test_state_provider_heatmap(self):
        heatmap = state_provider_heatmap(enrich_features(self._standardized()))
        self.assertFalse(heatmap.empty)
        self.assertIn("CA", heatmap.columns)

    def test_quality_filter_and_winsor(self):
        df = enrich_features(self._standardized())
        filtered = apply_quality_filters(df, min_services=90, min_benes=40)
        self.assertEqual(len(filtered), 3)
        win = winsorize_metrics(df, 0.5)
        self.assertLessEqual(win["payment_per_service"].max(), df["payment_per_service"].quantile(0.5))

    def test_state_summary_and_memo(self):
        enriched = enrich_features(self._standardized())
        state_summary = state_growth_summary(enriched)
        self.assertIn("state", state_summary.columns)

        scored = provider_screen(enriched)
        trends = yearly_trends(enriched)
        vol = provider_volatility(trends)
        watch = growth_volatility_watchlist(vol, min_growth=0.05, max_volatility=0.5)
        benchmark = provider_state_benchmark_flags(enriched, z_threshold=0.5, min_rows=1)
        value = provider_value_summary(enriched)
        investability = provider_investability_summary(scored, value, pd.DataFrame())
        stress = provider_stress_test(investability, downside_shock=0.2, upside_shock=0.1)
        summary = build_run_summary(enriched, scored, watch, pd.DataFrame(), benchmark, value, investability, stress, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
        self.assertIn("provider_type_count", summary)
        self.assertIn("top_provider_opportunity_percentile", summary)
        self.assertIn("min_year_in_data", summary)
        concentration = market_concentration_summary(enriched)
        shift = provider_trend_shift(trends, 2022, 2023)
        state_vol = state_volatility_summary(enriched)
        value = provider_value_summary(enriched)
        investability = provider_investability_summary(scored, value, vol)
        stress = provider_stress_test(investability, downside_shock=0.2, upside_shock=0.1)
        memo = build_advisory_memo(scored, vol, watch, state_summary, benchmark, concentration, shift, state_vol, value, investability, stress, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), top_n=2)
        self.assertIn("Watchlist Buckets", memo)
        self.assertIn("CMS Advisory Snapshot", memo)

    def test_watchlist_and_validation(self):
        vol = pd.DataFrame(
            {
                "provider_type": ["A", "B", "C"],
                "last_payment_growth": [0.2, 0.01, -0.1],
                "yoy_payment_volatility": [0.1, 0.2, 0.6],
            }
        )
        watch = growth_volatility_watchlist(vol, min_growth=0.05, max_volatility=0.35)
        self.assertIn("watchlist_bucket", watch.columns)
        self.assertEqual(str(watch.iloc[0]["watchlist_bucket"]), "priority")
        self.assertEqual(str(watch.iloc[-1]["watchlist_bucket"]), "high_risk")

        args = argparse.Namespace(
            limit=100,
            max_pages=5,
            top_n=10,
            min_services=0,
            min_benes=0,
            winsor_upper_quantile=0.95,
            watch_min_growth=0.05,
            watch_max_volatility=0.35,
            min_state_provider_rows=20,
            benchmark_z_threshold=1.5,
            retry_count=2,
            retry_backoff_s=1.0,
            min_year=None,
            max_year=None,
            baseline_year=None,
            compare_year=None,
            downside_shock=0.15,
            upside_shock=0.1,
            momentum_min_years=3,
            anomaly_z_threshold=2.5,
            anomaly_min_rows=10,
            regime_strong_growth=0.12,
            regime_high_volatility=0.35,
            white_space_min_percentile=0.70,
            scenario_downside_step=0.10,
            scenario_upside_step=0.10,
            geo_dependency_threshold=0.50,
            reliability_min_observations=3,
            scenario_min_win_share=0.30,
        )
        validate_runtime_inputs(args)

        bad_args = argparse.Namespace(
            limit=100,
            max_pages=5,
            top_n=10,
            min_services=0,
            min_benes=0,
            winsor_upper_quantile=0.95,
            watch_min_growth=0.05,
            watch_max_volatility=0,
            min_state_provider_rows=20,
            benchmark_z_threshold=1.5,
            retry_count=2,
            retry_backoff_s=1.0,
            min_year=None,
            max_year=None,
            baseline_year=None,
            compare_year=None,
            downside_shock=0.15,
            upside_shock=0.1,
            momentum_min_years=3,
            anomaly_z_threshold=2.5,
            anomaly_min_rows=10,
            regime_strong_growth=0.12,
            regime_high_volatility=0.35,
            white_space_min_percentile=0.70,
            scenario_downside_step=0.10,
            scenario_upside_step=0.10,
            geo_dependency_threshold=0.50,
            reliability_min_observations=3,
            scenario_min_win_share=0.30,
        )
        self.assertRaises(ValueError, validate_runtime_inputs, bad_args)

        bad_retry = argparse.Namespace(
            limit=100,
            max_pages=5,
            top_n=10,
            min_services=0,
            min_benes=0,
            winsor_upper_quantile=0.95,
            watch_min_growth=0.05,
            watch_max_volatility=0.35,
            min_state_provider_rows=20,
            benchmark_z_threshold=1.5,
            retry_count=-1,
            retry_backoff_s=1.0,
            min_year=None,
            max_year=None,
            baseline_year=None,
            compare_year=None,
            downside_shock=0.15,
            upside_shock=0.1,
            momentum_min_years=3,
            anomaly_z_threshold=2.5,
            anomaly_min_rows=10,
            regime_strong_growth=0.12,
            regime_high_volatility=0.35,
            white_space_min_percentile=0.70,
            scenario_downside_step=0.10,
            scenario_upside_step=0.10,
            geo_dependency_threshold=0.50,
            reliability_min_observations=3,
            scenario_min_win_share=0.30,
        )
        self.assertRaises(ValueError, validate_runtime_inputs, bad_retry)

        bad_year = argparse.Namespace(
            limit=100,
            max_pages=5,
            top_n=10,
            min_services=0,
            min_benes=0,
            winsor_upper_quantile=0.95,
            watch_min_growth=0.05,
            watch_max_volatility=0.35,
            min_state_provider_rows=20,
            benchmark_z_threshold=1.5,
            retry_count=2,
            retry_backoff_s=1.0,
            min_year=2024,
            max_year=2023,
            baseline_year=None,
            compare_year=None,
            downside_shock=0.15,
            upside_shock=0.1,
            momentum_min_years=3,
            anomaly_z_threshold=2.5,
            anomaly_min_rows=10,
            regime_strong_growth=0.12,
            regime_high_volatility=0.35,
            white_space_min_percentile=0.70,
            scenario_downside_step=0.10,
            scenario_upside_step=0.10,
            geo_dependency_threshold=0.50,
            reliability_min_observations=3,
            scenario_min_win_share=0.30,
        )
        self.assertRaises(ValueError, validate_runtime_inputs, bad_year)

        bad_compare = argparse.Namespace(
            limit=100,
            max_pages=5,
            top_n=10,
            min_services=0,
            min_benes=0,
            winsor_upper_quantile=0.95,
            watch_min_growth=0.05,
            watch_max_volatility=0.35,
            min_state_provider_rows=20,
            benchmark_z_threshold=1.5,
            retry_count=2,
            retry_backoff_s=1.0,
            min_year=None,
            max_year=None,
            baseline_year=2023,
            compare_year=2023,
            downside_shock=0.15,
            upside_shock=0.1,
            momentum_min_years=3,
            anomaly_z_threshold=2.5,
            anomaly_min_rows=10,
            regime_strong_growth=0.12,
            regime_high_volatility=0.35,
            white_space_min_percentile=0.70,
            scenario_downside_step=0.10,
            scenario_upside_step=0.10,
            geo_dependency_threshold=0.50,
            reliability_min_observations=3,
            scenario_min_win_share=0.30,
        )
        self.assertRaises(ValueError, validate_runtime_inputs, bad_compare)


        bad_shock = argparse.Namespace(
            limit=100,
            max_pages=5,
            top_n=10,
            min_services=0,
            min_benes=0,
            winsor_upper_quantile=0.95,
            watch_min_growth=0.05,
            watch_max_volatility=0.35,
            min_state_provider_rows=20,
            benchmark_z_threshold=1.5,
            retry_count=2,
            retry_backoff_s=1.0,
            min_year=None,
            max_year=None,
            baseline_year=None,
            compare_year=None,
            downside_shock=1.2,
            momentum_min_years=3,
            anomaly_z_threshold=2.5,
            anomaly_min_rows=10,
            upside_shock=0.1,
        )
        self.assertRaises(ValueError, validate_runtime_inputs, bad_shock)

        bad_regime = argparse.Namespace(
            limit=100,
            max_pages=5,
            top_n=10,
            min_services=0,
            min_benes=0,
            winsor_upper_quantile=0.95,
            watch_min_growth=0.05,
            watch_max_volatility=0.35,
            min_state_provider_rows=20,
            benchmark_z_threshold=1.5,
            retry_count=2,
            retry_backoff_s=1.0,
            min_year=None,
            max_year=None,
            baseline_year=None,
            compare_year=None,
            downside_shock=0.15,
            upside_shock=0.1,
            momentum_min_years=3,
            anomaly_z_threshold=2.5,
            anomaly_min_rows=10,
            regime_strong_growth=0.12,
            regime_high_volatility=0,
            white_space_min_percentile=0.70,
            scenario_downside_step=0.10,
            scenario_upside_step=0.10,
            geo_dependency_threshold=0.50,
            reliability_min_observations=3,
            scenario_min_win_share=0.30,
        )
        self.assertRaises(ValueError, validate_runtime_inputs, bad_regime)

        bad_white_space = argparse.Namespace(
            limit=100,
            max_pages=5,
            top_n=10,
            min_services=0,
            min_benes=0,
            winsor_upper_quantile=0.95,
            watch_min_growth=0.05,
            watch_max_volatility=0.35,
            min_state_provider_rows=20,
            benchmark_z_threshold=1.5,
            retry_count=2,
            retry_backoff_s=1.0,
            min_year=None,
            max_year=None,
            baseline_year=None,
            compare_year=None,
            downside_shock=0.15,
            upside_shock=0.1,
            momentum_min_years=3,
            anomaly_z_threshold=2.5,
            anomaly_min_rows=10,
            regime_strong_growth=0.12,
            regime_high_volatility=0.35,
            white_space_min_percentile=1.5,
            scenario_downside_step=0.10,
            scenario_upside_step=0.10,
            geo_dependency_threshold=0.50,
            reliability_min_observations=3,
            scenario_min_win_share=0.30,
        )
        self.assertRaises(ValueError, validate_runtime_inputs, bad_white_space)

        bad_scenario_step = argparse.Namespace(
            limit=100,
            max_pages=5,
            top_n=10,
            min_services=0,
            min_benes=0,
            winsor_upper_quantile=0.95,
            watch_min_growth=0.05,
            watch_max_volatility=0.35,
            min_state_provider_rows=20,
            benchmark_z_threshold=1.5,
            retry_count=2,
            retry_backoff_s=1.0,
            min_year=None,
            max_year=None,
            baseline_year=None,
            compare_year=None,
            downside_shock=0.15,
            upside_shock=0.1,
            momentum_min_years=3,
            anomaly_z_threshold=2.5,
            anomaly_min_rows=10,
            regime_strong_growth=0.12,
            regime_high_volatility=0.35,
            white_space_min_percentile=0.7,
            scenario_downside_step=0,
            scenario_upside_step=0.1,
            geo_dependency_threshold=0.50,
            reliability_min_observations=3,
            scenario_min_win_share=0.30,
        )
        self.assertRaises(ValueError, validate_runtime_inputs, bad_scenario_step)

        bad_geo_dep = argparse.Namespace(
            limit=100,
            max_pages=5,
            top_n=10,
            min_services=0,
            min_benes=0,
            winsor_upper_quantile=0.95,
            watch_min_growth=0.05,
            watch_max_volatility=0.35,
            min_state_provider_rows=20,
            benchmark_z_threshold=1.5,
            retry_count=2,
            retry_backoff_s=1.0,
            min_year=None,
            max_year=None,
            baseline_year=None,
            compare_year=None,
            downside_shock=0.15,
            upside_shock=0.1,
            momentum_min_years=3,
            anomaly_z_threshold=2.5,
            anomaly_min_rows=10,
            regime_strong_growth=0.12,
            regime_high_volatility=0.35,
            white_space_min_percentile=0.7,
            scenario_downside_step=0.1,
            scenario_upside_step=0.1,
            geo_dependency_threshold=1.5,
        )
        self.assertRaises(ValueError, validate_runtime_inputs, bad_geo_dep)

        bad_reliability = argparse.Namespace(
            limit=100,
            max_pages=5,
            top_n=10,
            min_services=0,
            min_benes=0,
            winsor_upper_quantile=0.95,
            watch_min_growth=0.05,
            watch_max_volatility=0.35,
            min_state_provider_rows=20,
            benchmark_z_threshold=1.5,
            retry_count=2,
            retry_backoff_s=1.0,
            min_year=None,
            max_year=None,
            baseline_year=None,
            compare_year=None,
            downside_shock=0.15,
            upside_shock=0.1,
            momentum_min_years=3,
            anomaly_z_threshold=2.5,
            anomaly_min_rows=10,
            regime_strong_growth=0.12,
            regime_high_volatility=0.35,
            white_space_min_percentile=0.7,
            scenario_downside_step=0.1,
            scenario_upside_step=0.1,
            geo_dependency_threshold=0.5,
            reliability_min_observations=1,
            scenario_min_win_share=0.30,
        )
        self.assertRaises(ValueError, validate_runtime_inputs, bad_reliability)

        bad_win_share = argparse.Namespace(
            limit=100,
            max_pages=5,
            top_n=10,
            min_services=0,
            min_benes=0,
            winsor_upper_quantile=0.95,
            watch_min_growth=0.05,
            watch_max_volatility=0.35,
            min_state_provider_rows=20,
            benchmark_z_threshold=1.5,
            retry_count=2,
            retry_backoff_s=1.0,
            min_year=None,
            max_year=None,
            baseline_year=None,
            compare_year=None,
            downside_shock=0.15,
            upside_shock=0.1,
            momentum_min_years=3,
            anomaly_z_threshold=2.5,
            anomaly_min_rows=10,
            regime_strong_growth=0.12,
            regime_high_volatility=0.35,
            white_space_min_percentile=0.7,
            scenario_downside_step=0.1,
            scenario_upside_step=0.1,
            geo_dependency_threshold=0.5,
            reliability_min_observations=3,
            scenario_min_win_share=1.2,
        )
        self.assertRaises(ValueError, validate_runtime_inputs, bad_win_share)



    def test_provider_value_summary(self):
        enriched = enrich_features(self._standardized())
        value = provider_value_summary(enriched)
        self.assertFalse(value.empty)
        self.assertIn("value_score", value.columns)
        self.assertIn("value_percentile", value.columns)


    def test_provider_investability_summary(self):
        enriched = enrich_features(self._standardized())
        scored = provider_screen(enriched)
        value = provider_value_summary(enriched)
        trends = yearly_trends(enriched)
        vol = provider_volatility(trends)
        inv = provider_investability_summary(scored, value, vol)
        self.assertFalse(inv.empty)
        self.assertIn("investability_score", inv.columns)


    def test_provider_stress_test(self):
        enriched = enrich_features(self._standardized())
        scored = provider_screen(enriched)
        value = provider_value_summary(enriched)
        trends = yearly_trends(enriched)
        vol = provider_volatility(trends)
        investability = provider_investability_summary(scored, value, vol)
        stress = provider_stress_test(investability, downside_shock=0.2, upside_shock=0.1)
        self.assertFalse(stress.empty)
        self.assertIn("stress_adjusted_score", stress.columns)

    def test_state_provider_opportunities(self):
        df = pd.DataFrame(
            {
                "provider_type": ["Cardiology"] * 25 + ["Dermatology"] * 25,
                "state": ["CA"] * 25 + ["TX"] * 25,
                "total_medicare_payment_amt": [1000] * 25 + [700] * 25,
                "payment_per_service": [120] * 25 + [90] * 25,
                "beneficiary_average_risk_score": [1.2] * 25 + [0.9] * 25,
            }
        )
        regional = state_provider_opportunities(df, min_rows=20)
        self.assertFalse(regional.empty)
        self.assertIn("regional_opportunity_score", regional.columns)
        self.assertIn("regional_opportunity_percentile", regional.columns)




    def test_state_volatility_summary(self):
        enriched = enrich_features(self._standardized())
        vol = state_volatility_summary(enriched)
        self.assertFalse(vol.empty)
        self.assertIn("yoy_volatility", vol.columns)

    def test_provider_trend_shift(self):
        trends = yearly_trends(enrich_features(self._standardized()))
        shift = provider_trend_shift(trends, baseline_year=2022, compare_year=2023)
        self.assertFalse(shift.empty)
        self.assertIn("payment_delta", shift.columns)

    def test_market_concentration_summary(self):
        df = pd.DataFrame(
            {
                "state": ["CA", "CA", "CA", "TX", "TX"],
                "year": [2023, 2023, 2023, 2023, 2023],
                "provider_type": ["Cardiology", "Dermatology", "Oncology", "Cardiology", "Dermatology"],
                "total_medicare_payment_amt": [1000, 500, 250, 900, 100],
            }
        )
        out = market_concentration_summary(df)
        self.assertFalse(out.empty)
        self.assertIn("hhi", out.columns)
        self.assertIn("cr3", out.columns)

    def test_provider_state_benchmark_flags(self):
        df = pd.DataFrame(
            {
                "provider_type": ["Cardiology"] * 25 + ["Cardiology"] * 25 + ["Dermatology"] * 25,
                "state": ["CA"] * 25 + ["TX"] * 25 + ["TX"] * 25,
                "payment_per_service": [200] * 25 + [100] * 25 + [90] * 25,
                "total_medicare_payment_amt": [1000] * 75,
            }
        )
        flags = provider_state_benchmark_flags(df, z_threshold=0.5, min_rows=20)
        self.assertFalse(flags.empty)
        self.assertIn("benchmark_flag", flags.columns)
        self.assertEqual(str(flags.iloc[0]["benchmark_flag"]), "high_price")


    def test_data_quality_report_and_run_summary_flags(self):
        enriched = enrich_features(self._standardized())
        report = data_quality_report(enriched)
        self.assertFalse(report.empty)
        self.assertIn("null_pct", report.columns)

        benchmark = pd.DataFrame(
            {
                "benchmark_flag": ["normal", "high_price", "low_price"],
                "provider_type": ["A", "B", "C"],
                "state": ["CA", "TX", "NY"],
            }
        )
        scored = provider_screen(enriched)
        watch = pd.DataFrame({"watchlist_bucket": ["priority"]})
        value = provider_value_summary(enriched)
        investability = provider_investability_summary(scored, value, pd.DataFrame())
        stress = provider_stress_test(investability, downside_shock=0.2, upside_shock=0.1)
        summary = build_run_summary(enriched, scored, watch, pd.DataFrame(), benchmark, value, investability, stress, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame())
        self.assertEqual(summary["benchmark_flag_count"], 2)
        self.assertIn("top_investability_provider", summary)
        self.assertIn("top_stress_adjusted_provider", summary)
        self.assertIn("durable_growth_provider_count", summary)


    def test_momentum_and_anomaly_analytics(self):
        trends_df = pd.DataFrame(
            {
                "year": [2021, 2022, 2023, 2021, 2022, 2023],
                "provider_type": ["A", "A", "A", "B", "B", "B"],
                "total_medicare_payment_amt": [100, 120, 150, 100, 90, 95],
                "payment_yoy_pct": [None, 0.2, 0.25, None, -0.1, 0.055],
                "payment_yoy_accel": [None, None, 0.05, None, None, 0.155],
            }
        )
        momentum = provider_momentum_profile(trends_df, min_years=3)
        self.assertFalse(momentum.empty)
        self.assertIn("consistency_score", momentum.columns)

        anomaly_df = pd.DataFrame(
            {
                "provider_type": ["A"] * 40 + ["A"] * 40,
                "state": ["CA"] * 40 + ["TX"] * 40,
                "year": [2023] * 80,
                "payment_per_service": [100] * 40 + [200] * 40,
                "total_medicare_payment_amt": [1000] * 80,
            }
        )
        anomalies = detect_state_provider_anomalies(anomaly_df, z_threshold=0.5, min_rows=20)
        self.assertFalse(anomalies.empty)
        self.assertIn("anomaly_flag", anomalies.columns)

    def test_make_outputs_no_plots_and_prefix(self):
        enriched = enrich_features(self._standardized())
        scores = provider_screen(enriched)
        trends = yearly_trends(enriched)
        volatility = provider_volatility(trends)
        watch = growth_volatility_watchlist(volatility, min_growth=0.05, max_volatility=0.5)
        state_summary = state_growth_summary(enriched)
        concentration = market_concentration_summary(enriched)
        value = provider_value_summary(enriched)
        investability = provider_investability_summary(scores, value, volatility)
        stress = provider_stress_test(investability, downside_shock=0.2, upside_shock=0.1)
        corr = correlation_table(enriched)
        quality = data_quality_report(enriched)
        state_vol = state_volatility_summary(enriched)
        heatmap = state_provider_heatmap(enriched)

        with TemporaryDirectory() as tmp:
            artifacts = make_outputs(
                enriched,
                scores,
                corr,
                trends,
                volatility,
                watch,
                state_summary,
                pd.DataFrame(),
                pd.DataFrame(),
                concentration,
                {},
                quality,
                pd.DataFrame(),
                state_vol,
                value,
                investability,
                stress,
                pd.DataFrame(),
                pd.DataFrame(),
                pd.DataFrame(),
                pd.DataFrame(),
                pd.DataFrame(),
                pd.DataFrame(),
                pd.DataFrame(),
                pd.DataFrame(),
                pd.DataFrame(),
                pd.DataFrame(),
                heatmap,
                Path(tmp),
                top_n=5,
                artifact_prefix="demo_",
                generate_plots=False,
            )
            self.assertIn("run_summary", artifacts)
            self.assertTrue(all(path.name.startswith("demo_") for path in artifacts.values()))
            self.assertFalse(any(path.suffix == ".png" for path in artifacts.values()))


    def test_provider_regime_and_state_fit(self):
        momentum = pd.DataFrame(
            {
                "provider_type": ["A", "B"],
                "consistency_score": [0.4, -0.1],
                "growth_cagr": [0.2, -0.05],
                "yoy_growth_volatility": [0.15, 0.5],
            }
        )
        volatility = pd.DataFrame(
            {
                "provider_type": ["A", "B"],
                "last_payment_growth": [0.22, -0.03],
                "yoy_payment_volatility": [0.2, 0.55],
            }
        )
        regimes = provider_regime_classification(momentum, volatility, strong_growth_threshold=0.12, high_vol_threshold=0.35)
        self.assertFalse(regimes.empty)
        self.assertIn("regime", regimes.columns)

        state_growth = pd.DataFrame(
            {
                "state": ["CA", "TX"],
                "avg_state_growth": [0.08, 0.02],
                "latest_state_growth": [0.12, -0.01],
                "latest_payment": [100000, 90000],
            }
        )
        state_vol = pd.DataFrame(
            {
                "state": ["CA", "TX"],
                "yoy_volatility": [0.2, 0.5],
            }
        )
        concentration = pd.DataFrame(
            {
                "state": ["CA", "TX"],
                "year": [2023, 2023],
                "hhi": [0.2, 0.45],
                "cr3": [0.5, 0.8],
                "provider_type_count": [8, 3],
            }
        )
        fit = state_portfolio_fit(state_growth, state_vol, concentration)
        self.assertFalse(fit.empty)
        self.assertIn("state_fit_score", fit.columns)



    def test_state_provider_white_space(self):
        regional = pd.DataFrame(
            {
                "provider_type": ["Cardiology", "Dermatology"],
                "state": ["CA", "TX"],
                "regional_opportunity_score": [0.9, 0.4],
                "regional_opportunity_percentile": [0.95, 0.55],
            }
        )
        state_fit = pd.DataFrame({"state": ["CA", "TX"], "state_fit_percentile": [0.9, 0.4]})
        bench = pd.DataFrame(
            {
                "provider_type": ["Cardiology", "Dermatology"],
                "state": ["CA", "TX"],
                "benchmark_flag": ["low_price", "high_price"],
            }
        )
        white_space = state_provider_white_space(regional, state_fit, bench, min_percentile=0.0)
        self.assertFalse(white_space.empty)
        self.assertIn("white_space_score", white_space.columns)
        self.assertEqual(str(white_space.iloc[0]["provider_type"]), "Cardiology")




    def test_provider_trend_reliability(self):
        trends = pd.DataFrame(
            {
                "provider_type": ["A", "A", "A", "B", "B", "B"],
                "payment_yoy_pct": [0.2, 0.15, 0.18, -0.1, 0.05, -0.02],
                "services_yoy_pct": [0.1, 0.08, 0.09, -0.03, 0.02, -0.01],
                "bene_yoy_pct": [0.12, 0.1, 0.11, -0.02, 0.01, -0.01],
                "payment_yoy_accel": [0.01, -0.02, 0.01, -0.01, 0.01, -0.02],
            }
        )
        rel = provider_trend_reliability(trends, min_observations=3)
        self.assertFalse(rel.empty)
        self.assertIn("reliability_score", rel.columns)
        self.assertIn("reliability_percentile", rel.columns)

    def test_provider_geo_dependency(self):
        df = pd.DataFrame(
            {
                "provider_type": ["A", "A", "A", "B", "B"],
                "state": ["CA", "CA", "TX", "TX", "WA"],
                "total_medicare_payment_amt": [600, 300, 100, 500, 500],
            }
        )
        dep = provider_geo_dependency(df, dependency_threshold=0.6)
        self.assertFalse(dep.empty)
        self.assertIn("top_state_share", dep.columns)
        self.assertTrue(bool(dep.iloc[0]["geo_dependency_flag"]))

    def test_stress_scenario_grid(self):
        investability = pd.DataFrame(
            {
                "provider_type": ["A", "B"],
                "investability_score": [0.8, 0.4],
                "total_payment": [1000, 800],
            }
        )
        grid = stress_scenario_grid(investability, downsides=[0.1, 0.2], upsides=[0.0, 0.1])
        self.assertFalse(grid.empty)
        self.assertIn("scenario_label", grid.columns)
        self.assertEqual(len(grid), 4)


    def test_provider_operating_posture(self):
        consensus = pd.DataFrame(
            {
                "provider_type": ["A", "B", "C"],
                "consensus_score": [0.9, 0.6, 0.5],
                "consensus_percentile": [1.0, 0.67, 0.33],
            }
        )
        reliability = pd.DataFrame(
            {
                "provider_type": ["A", "B", "C"],
                "reliability_score": [0.8, 0.4, 0.2],
                "reliability_percentile": [1.0, 0.67, 0.33],
            }
        )
        geo_dep = pd.DataFrame(
            {
                "provider_type": ["A", "B", "C"],
                "top_state_share": [0.4, 0.7, 0.5],
                "geo_dependency_flag": [False, True, False],
            }
        )
        scenario = pd.DataFrame(
            {
                "top_provider": ["A", "A", "B", "A"],
                "scenario_label": ["s1", "s2", "s3", "s4"],
            }
        )
        posture = provider_operating_posture(consensus, reliability, geo_dep, scenario, scenario_min_win_share=0.5)
        self.assertFalse(posture.empty)
        self.assertIn("operating_posture", posture.columns)
        self.assertIn("posture_score", posture.columns)

    def test_provider_consensus_rank(self):
        scores = pd.DataFrame(
            {
                "opportunity_score": [0.8, 0.4],
                "opportunity_percentile": [1.0, 0.5],
                "total_payment": [1000, 900],
            },
            index=["A", "B"],
        )
        value = pd.DataFrame({"provider_type": ["A", "B"], "value_percentile": [0.9, 0.4], "value_score": [0.7, 0.3]})
        investability = pd.DataFrame({"provider_type": ["A", "B"], "investability_score": [0.85, 0.45]})
        stress = pd.DataFrame({"provider_type": ["A", "B"], "stress_adjusted_score": [0.7, 0.35]})
        momentum = pd.DataFrame({"provider_type": ["A", "B"], "consistency_percentile": [0.95, 0.5], "consistency_score": [0.4, 0.1]})
        regimes = pd.DataFrame({"provider_type": ["A", "B"], "regime": ["durable_growth", "stagnant"]})

        consensus = provider_consensus_rank(scores, value, investability, stress, momentum, regimes)
        self.assertFalse(consensus.empty)
        self.assertIn("consensus_score", consensus.columns)
        self.assertEqual(str(consensus.iloc[0]["provider_type"]), "A")

    def test_parse_extra_params(self):
        params = parse_extra_params(["foo=bar", "x=1"])
        self.assertEqual(params["foo"], "bar")
        self.assertEqual(params["x"], "1")
        self.assertRaises(ValueError, parse_extra_params, ["=bad"])


if __name__ == "__main__":
    unittest.main()
