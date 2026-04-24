"""Physician Economic Unit analyzer + UI regression tests."""
from __future__ import annotations

import unittest

from rcm_mc.diligence.physician_comp.comp_ingester import Provider
from rcm_mc.diligence.physician_eu import (
    EconomicUnitReport, ProviderEconomicUnit, RosterOptimization,
    allocated_overhead_per_provider, analyze_roster_eu,
    compute_economic_unit, contribution_margin,
)


def _winner(pid: str = "W1") -> Provider:
    return Provider(
        provider_id=pid, specialty="ORTHOPEDIC_SURGERY",
        employment_status="PARTNER",
        base_salary_usd=550_000,
        productivity_bonus_usd=250_000,
        wrvus_annual=7500,
        collections_annual_usd=2_500_000,
    )


def _structural_loss(pid: str = "L1") -> Provider:
    """Collections too low to cover FMV comp + overhead — loss at
    any plausible comp structure.  INTERNAL_MEDICINE FMV p50 is
    ~$275k; collections of $180k can't cover even that plus
    overhead, so this provider remains negative at FMV."""
    return Provider(
        provider_id=pid, specialty="INTERNAL_MEDICINE",
        employment_status="W2",
        base_salary_usd=290_000,
        wrvus_annual=2500,
        collections_annual_usd=180_000,
    )


def _fixable_loss(pid: str = "F1") -> Provider:
    """Overpaid relative to collections but collections are okay —
    becomes profitable when comp is cut to FMV."""
    return Provider(
        provider_id=pid, specialty="FAMILY_MEDICINE",
        employment_status="W2",
        base_salary_usd=450_000,
        wrvus_annual=4500,
        collections_annual_usd=500_000,
    )


# ────────────────────────────────────────────────────────────────────
# Features module
# ────────────────────────────────────────────────────────────────────

class OverheadAllocationTests(unittest.TestCase):

    def test_revenue_weighted_sums_to_total(self):
        roster = [_winner("A"), _winner("B"), _fixable_loss("C")]
        alloc = allocated_overhead_per_provider(
            roster, overhead_pct=0.20,
        )
        total = sum(alloc.values())
        expected = 0.20 * sum(
            p.collections_annual_usd for p in roster
        )
        self.assertAlmostEqual(total, expected, places=2)

    def test_equal_share_flat(self):
        roster = [_winner("A"), _winner("B")]
        alloc = allocated_overhead_per_provider(
            roster, total_overhead_usd=200_000,
            method="equal_share",
        )
        for v in alloc.values():
            self.assertAlmostEqual(v, 100_000, places=2)

    def test_wrvu_weighted(self):
        roster = [
            Provider(provider_id="A", specialty="X",
                     wrvus_annual=1000,
                     collections_annual_usd=100_000),
            Provider(provider_id="B", specialty="X",
                     wrvus_annual=3000,
                     collections_annual_usd=100_000),
        ]
        alloc = allocated_overhead_per_provider(
            roster, total_overhead_usd=400_000,
            method="wrvu_weighted",
        )
        self.assertAlmostEqual(alloc["A"], 100_000, places=2)
        self.assertAlmostEqual(alloc["B"], 300_000, places=2)

    def test_zero_collections_falls_back_to_equal(self):
        roster = [
            Provider(provider_id="A", specialty="X"),
            Provider(provider_id="B", specialty="X"),
        ]
        alloc = allocated_overhead_per_provider(
            roster, total_overhead_usd=100_000,
        )
        # Both should split equally when revenue is zero
        self.assertAlmostEqual(alloc["A"], 50_000, places=2)
        self.assertAlmostEqual(alloc["B"], 50_000, places=2)


class EconomicUnitComputeTests(unittest.TestCase):

    def test_positive_contribution_winner(self):
        p = _winner()
        u = compute_economic_unit(p, overhead_usd=500_000)
        # 2_500_000 - (550_000 + 250_000) - 500_000 = 1_200_000
        self.assertEqual(u.contribution_usd, 1_200_000)
        self.assertFalse(u.is_loss_maker_observed)

    def test_structural_loss_negative_at_fmv(self):
        p = _structural_loss()
        u = compute_economic_unit(p, overhead_usd=40_000)
        self.assertTrue(u.is_loss_maker_observed)
        # Internal Medicine FMV p50 is known (~275k). At 180k
        # collections and 40k overhead, contribution at FMV is
        # 180k - 275k - 40k = -135k. Should be loss at FMV.
        self.assertIsNotNone(u.fmv_p50_comp_usd)
        self.assertTrue(u.is_loss_maker_at_fmv)

    def test_fixable_loss_profitable_at_fmv(self):
        p = _fixable_loss()
        u = compute_economic_unit(p, overhead_usd=80_000)
        # Current contribution: 500k - 450k - 80k = -30k (loss)
        self.assertTrue(u.is_loss_maker_observed)
        # At FMV (FAMILY_MEDICINE hospital_employed p50 ~280k),
        # contribution would be 500k - 280k - 80k = +140k → NOT
        # loss at FMV
        self.assertFalse(u.is_loss_maker_at_fmv)


# ────────────────────────────────────────────────────────────────────
# Analyzer
# ────────────────────────────────────────────────────────────────────

class AnalyzerTests(unittest.TestCase):

    def test_empty_roster_returns_empty_report(self):
        r = analyze_roster_eu([])
        self.assertEqual(r.roster_size, 0)
        self.assertEqual(r.units, [])
        self.assertIsNone(r.optimization)

    def test_winners_only_no_drop_candidates(self):
        roster = [_winner(f"W{i}") for i in range(5)]
        r = analyze_roster_eu(roster)
        self.assertEqual(r.loss_makers_at_fmv_comp, 0)
        self.assertEqual(len(r.optimization.candidates), 0)

    def test_structural_loss_triggers_drop_candidate(self):
        roster = [
            _winner("W1"), _winner("W2"),
            _structural_loss("L1"),
        ]
        r = analyze_roster_eu(roster)
        self.assertGreaterEqual(len(r.optimization.candidates), 1)
        candidate_ids = [c.provider_id for c in r.optimization.candidates]
        self.assertIn("L1", candidate_ids)

    def test_ranked_by_contribution_descending(self):
        roster = [
            _winner("W1"),
            _fixable_loss("F1"),
            _winner("W2"),
            _structural_loss("L1"),
        ]
        r = analyze_roster_eu(roster)
        contribs = [u.contribution_usd for u in r.units]
        self.assertEqual(contribs, sorted(contribs, reverse=True))
        self.assertEqual(r.units[0].contribution_rank, 1)
        self.assertEqual(r.units[-1].contribution_rank, 4)

    def test_aggregate_margin_computed_correctly(self):
        roster = [_winner("W1"), _winner("W2")]
        r = analyze_roster_eu(roster, overhead_pct=0.20)
        # 2 winners: 2×2.5M = 5M collections; 2×800k = 1.6M comp;
        # overhead = 0.2 × 5M = 1M; contribution = 5M - 1.6M - 1M = 2.4M;
        # margin = 2.4M / 5M = 48%
        self.assertAlmostEqual(
            r.aggregate_contribution_margin_pct, 0.48, places=2,
        )

    def test_optimization_ebitda_uplift_positive_when_candidates(self):
        roster = [
            _winner("W1"), _winner("W2"), _winner("W3"),
            _structural_loss("L1"),
        ]
        r = analyze_roster_eu(roster)
        if r.optimization.candidates:
            self.assertGreater(r.optimization.ebitda_uplift_usd, 0)

    def test_confidence_band(self):
        roster = [_winner("W1"), _winner("W2"), _structural_loss("L1")]
        r = analyze_roster_eu(roster)
        self.assertIn(
            r.optimization.confidence,
            ("LOW", "MEDIUM", "HIGH"),
        )

    def test_to_dict_round_trip(self):
        roster = [_winner("W1"), _structural_loss("L1")]
        r = analyze_roster_eu(roster)
        d = r.to_dict()
        self.assertIn("units", d)
        self.assertIn("optimization", d)

    def test_top_decile_share_in_unit_range(self):
        roster = [_winner(f"W{i}") for i in range(10)]
        r = analyze_roster_eu(roster)
        self.assertGreaterEqual(r.top_decile_contribution_share, 0.0)
        self.assertLessEqual(r.top_decile_contribution_share, 1.0)


# ────────────────────────────────────────────────────────────────────
# UI page
# ────────────────────────────────────────────────────────────────────

class PhysicianEUPageTests(unittest.TestCase):

    def _render(self, **qs):
        from rcm_mc.ui.physician_eu_page import (
            render_physician_eu_page,
        )
        wrapped = {k: [v] for k, v in qs.items()}
        return render_physician_eu_page(qs=wrapped)

    def test_landing_renders(self):
        h = self._render()
        self.assertIn("Physician Economic Units", h)
        self.assertIn("What this shows", h)

    def test_hero_kpis_present(self):
        h = self._render()
        self.assertIn("Roster collections", h)
        self.assertIn("Aggregate contribution", h)
        self.assertIn("Loss-makers", h)

    def test_roster_table_present(self):
        h = self._render()
        self.assertIn("Full roster", h)
        self.assertIn("data-sortable", h)
        self.assertIn("data-filterable", h)

    def test_optimization_block_renders_when_candidates(self):
        h = self._render()
        # The demo roster includes P007 (pediatrics) which is a
        # structural loss-maker; optimization should appear
        self.assertIn("Roster Optimization", h)

    def test_crosslink_to_ppam(self):
        h = self._render()
        self.assertIn("/diligence/physician-attrition", h)
        self.assertIn("Physician Attrition", h)

    def test_target_name_from_query(self):
        h = self._render(target_name="Acme Clinic Group")
        self.assertIn("Acme Clinic Group", h)

    def test_overhead_method_selector_respected(self):
        h = self._render(overhead_method="wrvu_weighted")
        self.assertIn("wrvu weighted", h)


class NavLinkTests(unittest.TestCase):

    def test_sidebar_has_physician_eu(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        rendered = chartis_shell("<p>x</p>", "Test")
        self.assertIn('href="/diligence/physician-eu"', rendered)

    def test_deal_profile_exposes_physician_eu(self):
        from rcm_mc.ui.deal_profile_page import _ANALYTICS
        ids = [a.get("href") for a in _ANALYTICS]
        self.assertIn("/diligence/physician-eu", ids)


class EdgeCaseTests(unittest.TestCase):

    def test_zero_collections_whole_roster(self):
        roster = [
            Provider(provider_id="Z1", specialty="FAMILY_MEDICINE",
                     base_salary_usd=280_000),
            Provider(provider_id="Z2", specialty="INTERNAL_MEDICINE",
                     base_salary_usd=290_000),
        ]
        r = analyze_roster_eu(roster)
        self.assertEqual(r.total_collections_usd, 0.0)
        # All negative contribution (comp without revenue)
        self.assertEqual(r.loss_makers_at_current_comp, 2)

    def test_no_fmv_coverage_still_ranks(self):
        """Specialties with no FMV anchor still rank; they just
        can't be flagged as loss-at-FMV."""
        roster = [
            Provider(provider_id="A", specialty="NONEXISTENT_SPECIALTY",
                     base_salary_usd=300_000,
                     collections_annual_usd=800_000),
            Provider(provider_id="B", specialty="NONEXISTENT_SPECIALTY",
                     base_salary_usd=300_000,
                     collections_annual_usd=500_000),
        ]
        r = analyze_roster_eu(roster)
        self.assertEqual(r.roster_size, 2)
        for u in r.units:
            self.assertIsNone(u.fmv_p50_comp_usd)
            self.assertFalse(u.is_loss_maker_at_fmv)
        # Can still identify observed loss-makers
        self.assertLessEqual(r.loss_makers_at_current_comp, 2)

    def test_large_roster_performance(self):
        """Score 100 providers — confirm compute stays under 1s."""
        import time
        roster = [_winner(f"P{i:03d}") for i in range(100)]
        t0 = time.time()
        r = analyze_roster_eu(roster)
        elapsed = time.time() - t0
        self.assertEqual(r.roster_size, 100)
        self.assertLess(elapsed, 1.0,
                        msg=f"100-provider scoring took {elapsed:.3f}s")

    def test_custom_overhead_dollars(self):
        """When total_overhead_usd is supplied explicitly, should
        override the default overhead_pct computation."""
        roster = [_winner("A"), _winner("B")]
        r = analyze_roster_eu(roster, total_overhead_usd=500_000)
        self.assertAlmostEqual(r.total_overhead_usd, 500_000, places=2)


class PipelineIntegrationTests(unittest.TestCase):

    def test_pipeline_runs_eu_when_roster_supplied(self):
        from rcm_mc.diligence.thesis_pipeline import (
            PipelineInput, run_thesis_pipeline,
        )
        roster = [
            _winner("W1"), _winner("W2"),
            _structural_loss("L1"),
        ]
        inp = PipelineInput(
            dataset="hospital_02_denial_heavy",
            deal_name="Pipeline-EU test",
            providers=roster,
            n_runs=300,
        )
        report = run_thesis_pipeline(inp)
        self.assertIsNotNone(report.eu_report)
        # Headline numbers propagated
        self.assertIsNotNone(report.eu_ebitda_uplift_usd)
        self.assertIsNotNone(report.eu_drop_candidate_count)

    def test_pipeline_skips_eu_without_roster(self):
        from rcm_mc.diligence.thesis_pipeline import (
            PipelineInput, run_thesis_pipeline,
        )
        inp = PipelineInput(dataset="hospital_02_denial_heavy")
        report = run_thesis_pipeline(inp)
        # With no roster, both PPAM and EU should be skipped
        self.assertIsNone(report.attrition_report)
        self.assertIsNone(report.eu_report)

    def test_pipeline_observations_include_fmv_check(self):
        """Running the EU analyzer should auto-mark the Stark / FMV
        checklist item (since EU is an FMV-derived check)."""
        from rcm_mc.diligence.thesis_pipeline import (
            PipelineInput, pipeline_observations, run_thesis_pipeline,
        )
        inp = PipelineInput(
            dataset="hospital_02_denial_heavy",
            providers=[_winner("W1"), _winner("W2")],
            n_runs=200,
        )
        report = run_thesis_pipeline(inp)
        obs = pipeline_observations(report)
        self.assertTrue(obs.get("physician_comp_fmv_run", False))


class ICPacketIntegrationTests(unittest.TestCase):

    def _build_report_with_candidates(self):
        roster = [
            _winner("W1"), _winner("W2"), _winner("W3"),
            _structural_loss("L1"),
            _structural_loss("L2"),
        ]
        return analyze_roster_eu(roster)

    def test_ic_packet_renders_roster_optimization_section(self):
        from rcm_mc.exports import (
            ICPacketMetadata, render_ic_packet_html,
        )
        r = self._build_report_with_candidates()
        html_str = render_ic_packet_html(
            metadata=ICPacketMetadata(deal_name="Test"),
            eu_report=r,
        )
        if r.optimization and r.optimization.candidates:
            self.assertIn("Roster Optimization", html_str)
            self.assertIn("uneconomic at any comp", html_str)
        else:
            # Defensive — if no candidates, section should not appear
            self.assertNotIn("Roster Optimization", html_str)

    def test_ic_packet_silent_when_no_eu_report(self):
        from rcm_mc.exports import (
            ICPacketMetadata, render_ic_packet_html,
        )
        html_str = render_ic_packet_html(
            metadata=ICPacketMetadata(deal_name="Test"),
            eu_report=None,
        )
        self.assertNotIn("Roster Optimization", html_str)

    def test_ic_packet_silent_when_no_drop_candidates(self):
        from rcm_mc.exports import (
            ICPacketMetadata, render_ic_packet_html,
        )
        # Winners-only roster → no candidates → no section
        roster = [_winner(f"W{i}") for i in range(3)]
        r = analyze_roster_eu(roster)
        html_str = render_ic_packet_html(
            metadata=ICPacketMetadata(deal_name="Test"),
            eu_report=r,
        )
        self.assertNotIn("Roster Optimization", html_str)


if __name__ == "__main__":
    unittest.main()
