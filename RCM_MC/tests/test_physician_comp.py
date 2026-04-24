"""Physician compensation FMV + drift regression tests (Prompt J)."""
from __future__ import annotations

import unittest

from rcm_mc.diligence.physician_comp import (
    Provider, check_stark_redline, comp_per_wrvu, comp_per_wrvu_band,
    get_benchmark, ingest_providers, percentile_placement,
    recommend_earnout_structure, simulate_productivity_drift,
)


class CompIngesterTests(unittest.TestCase):

    def test_total_comp_aggregates(self):
        p = Provider(
            provider_id="P1", specialty="FAMILY_MEDICINE",
            base_salary_usd=200_000, productivity_bonus_usd=60_000,
            stipend_usd=10_000, call_coverage_usd=5_000,
            admin_usd=5_000, wrvus_annual=5_000,
            collections_annual_usd=500_000,
        )
        self.assertEqual(p.total_comp_usd, 280_000)
        self.assertAlmostEqual(comp_per_wrvu(p), 56.0, places=2)

    def test_roster_aggregates(self):
        ps = [
            Provider(
                provider_id=f"P{i}", specialty="FAMILY_MEDICINE",
                base_salary_usd=250_000, wrvus_annual=5200,
                collections_annual_usd=600_000,
            )
            for i in range(3)
        ]
        m = ingest_providers(ps)
        self.assertEqual(m.total_comp_usd, 750_000)
        self.assertEqual(m.total_wrvus, 15_600)
        self.assertAlmostEqual(
            m.aggregate_comp_per_wrvu, 48.08, places=2,
        )


class BenchmarkTests(unittest.TestCase):

    def test_family_medicine_p50_band(self):
        bench = get_benchmark("FAMILY_MEDICINE", "hospital_employed")
        self.assertIsNotNone(bench)
        self.assertGreater(bench["p50"], bench["p25"])
        self.assertGreater(bench["p75"], bench["p50"])

    def test_percentile_placement_high_comp(self):
        """$450k FM hospital-employed is above p90 ($395k)."""
        self.assertEqual(
            percentile_placement(
                450_000, specialty="FAMILY_MEDICINE",
                ownership_type="hospital_employed",
            ),
            "above_p90",
        )

    def test_percentile_placement_low_comp(self):
        self.assertEqual(
            percentile_placement(
                180_000, specialty="FAMILY_MEDICINE",
            ),
            "below_p25",
        )

    def test_unknown_specialty_returns_none(self):
        self.assertIsNone(
            percentile_placement(300_000, specialty="WIDGET_CARE"),
        )

    def test_comp_per_wrvu_band(self):
        # Anesthesia median $40/wRVU, p75 $46 → $42 sits in p50-p75
        self.assertEqual(
            comp_per_wrvu_band(42.0, specialty="ANESTHESIOLOGY"),
            "p50_to_p75",
        )
        # $38 is between p25 $35 and p50 $40 → p25_to_p50
        self.assertEqual(
            comp_per_wrvu_band(38.0, specialty="ANESTHESIOLOGY"),
            "p25_to_p50",
        )


class StarkRedLineTests(unittest.TestCase):

    def test_stacked_above_p90_fires_critical(self):
        """Provider at $440k FM with >35% directed-comp hits
        CRITICAL stacked-above-p90 flag."""
        p = Provider(
            provider_id="P1", specialty="FAMILY_MEDICINE",
            base_salary_usd=250_000,
            productivity_bonus_usd=100_000,
            stipend_usd=40_000, call_coverage_usd=30_000,
            admin_usd=20_000,
            wrvus_annual=6200,
            collections_annual_usd=800_000,
        )
        findings = check_stark_redline([p])
        self.assertTrue(findings)
        codes = {f.finding_code for f in findings}
        self.assertIn("STACKED_ABOVE_P90", codes)
        critical = next(
            f for f in findings
            if f.finding_code == "STACKED_ABOVE_P90"
        )
        self.assertEqual(critical.severity, "CRITICAL")
        self.assertIn("Stark", critical.statutory_cite)

    def test_collections_pass_through_fires(self):
        """65% comp-as-%-collections + no directed comp → volume/
        value concern (Tuomey pattern)."""
        p = Provider(
            provider_id="P2", specialty="ORTHOPEDICS",
            base_salary_usd=650_000,
            wrvus_annual=9000,
            collections_annual_usd=1_000_000,
        )
        findings = check_stark_redline([p])
        codes = {f.finding_code for f in findings}
        self.assertIn("COLLECTIONS_PASS_THROUGH", codes)

    def test_clean_provider_no_findings(self):
        p = Provider(
            provider_id="P3", specialty="FAMILY_MEDICINE",
            base_salary_usd=260_000,
            productivity_bonus_usd=20_000,
            wrvus_annual=5200,
            collections_annual_usd=600_000,
        )
        findings = check_stark_redline([p])
        self.assertEqual(findings, [])


class DriftSimulatorTests(unittest.TestCase):

    def _providers(self, n=10):
        return [
            Provider(
                provider_id=f"P{i}", specialty="FAMILY_MEDICINE",
                base_salary_usd=260_000,
                wrvus_annual=5200,
                collections_annual_usd=600_000,
            )
            for i in range(n)
        ]

    def test_hold_firm_attrition_rises_with_cut_size(self):
        small_cut = simulate_productivity_drift(
            self._providers(), buyer_proposed_reduction_pct=0.05,
            n_runs=120,
        )
        big_cut = simulate_productivity_drift(
            self._providers(), buyer_proposed_reduction_pct=0.25,
            n_runs=120,
        )
        small_med = next(
            s for s in small_cut.scenarios if s.scenario == "hold_firm"
        ).median_attrition_pct
        big_med = next(
            s for s in big_cut.scenarios if s.scenario == "hold_firm"
        ).median_attrition_pct
        self.assertGreater(big_med, small_med)

    def test_capitulate_dollar_drag_equals_cut_amount(self):
        res = simulate_productivity_drift(
            self._providers(n=5),
            buyer_proposed_reduction_pct=0.10,
            wrvu_inflation_pct=0.0,
            n_runs=50,
        )
        capit = next(
            s for s in res.scenarios if s.scenario == "capitulate"
        )
        # 5 providers × $260k × 0.10 = $130k drag
        self.assertAlmostEqual(
            capit.ebitda_at_risk_usd, 130_000, delta=1,
        )

    def test_cy2021_echo_flag_sets_when_inflation_high(self):
        res = simulate_productivity_drift(
            self._providers(n=3),
            buyer_proposed_reduction_pct=0.10,
            wrvu_inflation_pct=0.10,     # CY 2021 anchor
            n_runs=40,
        )
        self.assertTrue(res.cy2021_echo_risk)
        capit = next(
            s for s in res.scenarios if s.scenario == "capitulate"
        )
        # Seller total 3 × $260k = $780k
        # Capitulate drag = 780k * 0.10 + 780k * 0.10 = 156k
        self.assertAlmostEqual(
            capit.ebitda_at_risk_usd, 156_000, delta=1,
        )


class EarnoutAdvisorTests(unittest.TestCase):

    def test_high_concentration_recommends_retention_bond(self):
        # 1 big + 9 small providers: top5 > 40%
        ps = [Provider(
            provider_id="BIG",
            specialty="ORTHOPEDICS",
            base_salary_usd=800_000,
            collections_annual_usd=3_000_000,
        )] + [
            Provider(
                provider_id=f"S{i}",
                specialty="ORTHOPEDICS",
                base_salary_usd=300_000,
                collections_annual_usd=300_000,
            )
            for i in range(9)
        ]
        rec = recommend_earnout_structure(ps)
        self.assertEqual(rec.recommended_structure, "RETENTION_BOND")
        self.assertGreater(rec.top5_concentration_pct, 0.40)
        self.assertEqual(rec.attach_to_top_n, 5)

    def test_diversified_roster_recommends_wrvu(self):
        """30-provider roster with equal collections → top5 = 16.7%
        → WRVU_BASED (below 25% HYBRID threshold)."""
        ps = [
            Provider(
                provider_id=f"P{i}", specialty="FAMILY_MEDICINE",
                collections_annual_usd=500_000,
            )
            for i in range(30)
        ]
        rec = recommend_earnout_structure(ps)
        self.assertEqual(rec.recommended_structure, "WRVU_BASED")
        self.assertEqual(rec.attach_to_top_n, 0)


if __name__ == "__main__":
    unittest.main()
