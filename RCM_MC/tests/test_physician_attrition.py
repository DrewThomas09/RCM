"""Physician Attrition Model (P-PAM) regression tests.

Covers:
    - Features: all 9 dimensions in [0, 1]; provenance recorded;
      component extractors behave correctly at boundaries
    - Model: sigmoid stability; base rate ~4% at fully-zero vector;
      monotone in each feature; feature_contributions sums cleanly
    - Bands: threshold math on CRITICAL / HIGH / MEDIUM / LOW
    - Analyzer: end-to-end roster scoring; bridge lever produced;
      scores sorted by $ at risk; Stark overlap correctly picked up;
      confidence banding works; empty roster handled
    - UI page: landing renders; hero banner content keyed off band
      counts; bridge lever card present; sortable roster table
    - Server route + sidebar nav link + Deal Profile tile
"""
from __future__ import annotations

import math
import unittest

from rcm_mc.diligence.physician_attrition import (
    AttritionFeatures, AttritionReport, FlightRiskBand,
    ProviderAttritionScore, analyze_roster, band_for,
    extract_features, flight_risk_probability,
)
from rcm_mc.diligence.physician_attrition.model import (
    DEFAULT_INTERCEPT, DEFAULT_COEFFICIENTS, feature_contributions,
)
from rcm_mc.diligence.physician_comp.comp_ingester import Provider


# ────────────────────────────────────────────────────────────────────
# Feature extraction
# ────────────────────────────────────────────────────────────────────

class FeatureExtractionTests(unittest.TestCase):

    def test_all_dimensions_in_unit_range(self):
        p = Provider(
            provider_id="P1", specialty="FAMILY_MEDICINE",
            employment_status="W2",
            base_salary_usd=280_000,
            collections_annual_usd=800_000, wrvus_annual=5000,
        )
        f = extract_features(
            p,
            years_at_facility=5, age_years=42,
            yoy_collections_slope=-0.03,
            local_competitors=40, roster_size=20,
            roster_collections_total=20_000_000,
            has_stark_overlap=False,
        )
        for val in f.as_tuple():
            self.assertGreaterEqual(val, 0.0)
            self.assertLessEqual(val, 1.0)

    def test_tenure_short_at_extremes(self):
        p = Provider(provider_id="P", specialty="INTERNAL_MEDICINE",
                     base_salary_usd=250_000,
                     collections_annual_usd=800_000)
        new = extract_features(p, years_at_facility=0.5)
        veteran = extract_features(p, years_at_facility=15)
        self.assertEqual(new.tenure_short, 1.0)
        self.assertEqual(veteran.tenure_short, 0.0)

    def test_age_inflection_u_shape(self):
        p = Provider(provider_id="P", specialty="INTERNAL_MEDICINE",
                     base_salary_usd=250_000,
                     collections_annual_usd=800_000)
        early = extract_features(p, age_years=34).age_inflection
        mid = extract_features(p, age_years=48).age_inflection
        late = extract_features(p, age_years=64).age_inflection
        self.assertEqual(mid, 0.0)
        self.assertGreater(early, 0.5)
        self.assertGreater(late, 0.5)

    def test_productivity_decline_feature(self):
        p = Provider(provider_id="P", specialty="INTERNAL_MEDICINE",
                     base_salary_usd=250_000,
                     collections_annual_usd=800_000)
        steep = extract_features(p, yoy_collections_slope=-0.20)
        mild = extract_features(p, yoy_collections_slope=-0.05)
        stable = extract_features(p, yoy_collections_slope=0.02)
        self.assertEqual(steep.productivity_decline, 1.0)
        self.assertAlmostEqual(mild.productivity_decline, 1/3, places=5)
        self.assertEqual(stable.productivity_decline, 0.0)

    def test_employment_status_risk_ordering(self):
        partner = Provider(provider_id="X", specialty="X",
                           employment_status="PARTNER",
                           base_salary_usd=600_000)
        w2 = Provider(provider_id="X", specialty="X",
                      employment_status="W2",
                      base_salary_usd=300_000)
        locum = Provider(provider_id="X", specialty="X",
                         employment_status="LOCUM",
                         base_salary_usd=500_000)
        self.assertLess(
            extract_features(partner).employment_status_risk,
            extract_features(w2).employment_status_risk,
        )
        self.assertLess(
            extract_features(w2).employment_status_risk,
            extract_features(locum).employment_status_risk,
        )

    def test_solo_line_concentration(self):
        p = Provider(provider_id="P", specialty="CARDIOLOGY",
                     base_salary_usd=500_000,
                     collections_annual_usd=3_000_000)
        low_conc = extract_features(p, roster_collections_total=30_000_000)
        high_conc = extract_features(p, roster_collections_total=5_000_000)
        self.assertLess(
            low_conc.solo_line_revenue_share,
            high_conc.solo_line_revenue_share,
        )

    def test_specialty_mobility_prior(self):
        ortho = Provider(provider_id="P", specialty="ORTHOPEDIC_SURGERY",
                         base_salary_usd=500_000,
                         collections_annual_usd=2_000_000)
        fm = Provider(provider_id="P", specialty="FAMILY_MEDICINE",
                      base_salary_usd=280_000,
                      collections_annual_usd=800_000)
        self.assertGreater(
            extract_features(ortho).specialty_mobility,
            extract_features(fm).specialty_mobility,
        )

    def test_provenance_recorded(self):
        p = Provider(provider_id="P", specialty="FAMILY_MEDICINE",
                     employment_status="W2",
                     base_salary_usd=280_000,
                     collections_annual_usd=800_000)
        f = extract_features(
            p, years_at_facility=3, age_years=40,
            has_stark_overlap=True,
        )
        self.assertIn("tenure_short", f.provenance)
        self.assertIn("age_inflection", f.provenance)
        self.assertIn("employment_status_risk", f.provenance)
        self.assertIn("Stark red-line hit", f.provenance["stark_overlap_flag"])


# ────────────────────────────────────────────────────────────────────
# Model
# ────────────────────────────────────────────────────────────────────

class ModelTests(unittest.TestCase):

    def test_base_rate_at_zero_vector(self):
        """Default AttritionFeatures has employment=W2 (0.3) and
        specialty=unknown (0.40) baked in as priors, so the default
        base rate lands around ~9% (MGMA 5yr turnover ~5% annualised,
        compounded out is in this range)."""
        p = flight_risk_probability(AttritionFeatures())
        self.assertGreater(p, 0.04)
        self.assertLess(p, 0.14)

    def test_true_zero_vector_very_low(self):
        """All features truly zero → sigmoid(-3.2) ≈ 0.039."""
        f = AttritionFeatures(
            employment_status_risk=0.0,
            specialty_mobility=0.0,
        )
        p = flight_risk_probability(f)
        self.assertGreater(p, 0.02)
        self.assertLess(p, 0.06)

    def test_probability_in_unit_range(self):
        f = AttritionFeatures(
            comp_gap_normalized=1.0, tenure_short=1.0,
            age_inflection=1.0, productivity_decline=1.0,
            local_competitor_density=1.0, stark_overlap_flag=1.0,
            employment_status_risk=1.0, solo_line_revenue_share=1.0,
            specialty_mobility=1.0,
        )
        p = flight_risk_probability(f)
        self.assertGreaterEqual(p, 0.0)
        self.assertLessEqual(p, 1.0)
        self.assertGreater(p, 0.95)

    def test_monotone_in_each_feature(self):
        """Increasing any single feature (holding others at 0) must
        increase the probability — the coefficients are all positive."""
        base = flight_risk_probability(AttritionFeatures())
        for name in AttritionFeatures.FEATURE_NAMES:
            f = AttritionFeatures(**{name: 1.0})
            p = flight_risk_probability(f)
            self.assertGreater(p, base, msg=f"feature {name} should lift prob")

    def test_numerical_stability_large_z(self):
        """Sigmoid should not overflow for extreme inputs."""
        f = AttritionFeatures(
            comp_gap_normalized=1.0, tenure_short=1.0,
            age_inflection=1.0, productivity_decline=1.0,
            local_competitor_density=1.0, stark_overlap_flag=1.0,
            employment_status_risk=1.0, solo_line_revenue_share=1.0,
            specialty_mobility=1.0,
        )
        # Inflate coefficients to drive z very large
        coeffs = tuple(c * 100 for c in DEFAULT_COEFFICIENTS)
        p = flight_risk_probability(f, coefficients=coeffs)
        self.assertFalse(math.isnan(p))
        self.assertAlmostEqual(p, 1.0, places=6)

    def test_feature_contributions_sum_logodds(self):
        f = AttritionFeatures(comp_gap_normalized=0.5, tenure_short=1.0)
        contribs = feature_contributions(f)
        total = sum(contribs.values())
        # Compare sigmoid(total) to flight_risk_probability(f)
        expected = 1.0 / (1.0 + math.exp(-total))
        self.assertAlmostEqual(flight_risk_probability(f), expected, places=6)

    def test_coefficient_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            flight_risk_probability(
                AttritionFeatures(),
                coefficients=(1.0, 2.0),
            )


class BandForTests(unittest.TestCase):

    def test_thresholds(self):
        self.assertEqual(band_for(0.0), FlightRiskBand.LOW)
        self.assertEqual(band_for(0.29), FlightRiskBand.LOW)
        self.assertEqual(band_for(0.30), FlightRiskBand.MEDIUM)
        self.assertEqual(band_for(0.59), FlightRiskBand.MEDIUM)
        self.assertEqual(band_for(0.60), FlightRiskBand.HIGH)
        self.assertEqual(band_for(0.84), FlightRiskBand.HIGH)
        self.assertEqual(band_for(0.85), FlightRiskBand.CRITICAL)
        self.assertEqual(band_for(1.00), FlightRiskBand.CRITICAL)

    def test_clamps_out_of_range(self):
        self.assertEqual(band_for(-0.5), FlightRiskBand.LOW)
        self.assertEqual(band_for(1.5), FlightRiskBand.CRITICAL)


# ────────────────────────────────────────────────────────────────────
# Analyzer
# ────────────────────────────────────────────────────────────────────

def _mixed_roster():
    return [
        Provider(provider_id="CRIT1", specialty="ANESTHESIOLOGY",
                 employment_status="LOCUM",
                 base_salary_usd=500_000, wrvus_annual=6500,
                 collections_annual_usd=1_900_000),
        Provider(provider_id="CRIT2", specialty="EMERGENCY_MEDICINE",
                 employment_status="1099",
                 base_salary_usd=420_000, wrvus_annual=8000,
                 collections_annual_usd=1_600_000),
        Provider(provider_id="HIGH1", specialty="ORTHOPEDIC_SURGERY",
                 employment_status="W2",
                 base_salary_usd=450_000, wrvus_annual=7500,
                 collections_annual_usd=2_400_000),
        Provider(provider_id="MED1", specialty="CARDIOLOGY",
                 employment_status="W2",
                 base_salary_usd=550_000, wrvus_annual=9000,
                 collections_annual_usd=2_800_000),
        Provider(provider_id="LOW1", specialty="FAMILY_MEDICINE",
                 employment_status="PARTNER",
                 base_salary_usd=300_000, wrvus_annual=6000,
                 collections_annual_usd=1_000_000),
    ]


class AnalyzerTests(unittest.TestCase):

    def test_empty_roster_returns_empty_report(self):
        r = analyze_roster([])
        self.assertEqual(r.roster_size, 0)
        self.assertEqual(r.scores, [])
        self.assertIsNone(r.bridge_input)

    def test_scores_sorted_by_collections_at_risk(self):
        r = analyze_roster(_mixed_roster())
        at_risks = [s.expected_collections_at_risk_usd for s in r.scores]
        self.assertEqual(at_risks, sorted(at_risks, reverse=True))

    def test_band_counts_match_roster(self):
        r = analyze_roster(
            _mixed_roster(),
            years_at_facility={"CRIT1": 0.5, "CRIT2": 1, "HIGH1": 2,
                               "MED1": 10, "LOW1": 18},
            ages={"CRIT1": 36, "CRIT2": 32, "HIGH1": 42,
                  "MED1": 48, "LOW1": 55},
        )
        self.assertEqual(
            r.critical_count + r.high_count +
            r.medium_count + r.low_count,
            len(_mixed_roster()),
        )

    def test_bridge_input_fields_populated(self):
        r = analyze_roster(_mixed_roster())
        self.assertIsNotNone(r.bridge_input)
        self.assertGreaterEqual(r.bridge_input.ebitda_at_risk_usd, 0.0)
        self.assertGreaterEqual(r.bridge_input.expected_collections_lost_usd, 0.0)
        self.assertIn(
            r.bridge_input.confidence,
            ("LOW", "MEDIUM", "HIGH"),
        )

    def test_retention_bond_sizing(self):
        r = analyze_roster(
            _mixed_roster(),
            years_at_facility={"CRIT1": 0.3, "CRIT2": 0.5, "HIGH1": 1,
                               "MED1": 10, "LOW1": 18},
            ages={"CRIT1": 33, "CRIT2": 31, "HIGH1": 32,
                  "MED1": 48, "LOW1": 55},
            yoy_collections_slopes={"CRIT1": -0.18, "CRIT2": -0.15,
                                    "HIGH1": -0.10},
        )
        for s in r.scores:
            rec = s.recommendation
            if s.band == FlightRiskBand.CRITICAL:
                self.assertIsNotNone(rec.suggested_bond_usd)
                self.assertEqual(rec.retention_years, 3)
            elif s.band == FlightRiskBand.HIGH:
                self.assertIsNotNone(rec.suggested_bond_usd)
                self.assertEqual(rec.retention_years, 2)
            else:
                self.assertIsNone(rec.suggested_bond_usd)

    def test_deterministic_with_same_inputs(self):
        r1 = analyze_roster(_mixed_roster())
        r2 = analyze_roster(_mixed_roster())
        self.assertEqual(
            [s.probability for s in r1.scores],
            [s.probability for s in r2.scores],
        )

    def test_top_at_risk_concentration_fraction(self):
        r = analyze_roster(_mixed_roster())
        self.assertGreaterEqual(r.top_at_risk_contributors_pct_of_roster, 0.0)
        self.assertLessEqual(r.top_at_risk_contributors_pct_of_roster, 1.0)

    def test_high_or_critical_filter(self):
        r = analyze_roster(
            _mixed_roster(),
            years_at_facility={"CRIT1": 0.3, "CRIT2": 0.5},
        )
        for s in r.high_or_critical_scores:
            self.assertIn(
                s.band,
                (FlightRiskBand.HIGH, FlightRiskBand.CRITICAL),
            )


# ────────────────────────────────────────────────────────────────────
# UI page
# ────────────────────────────────────────────────────────────────────

class PhysicianAttritionPageTests(unittest.TestCase):

    def test_landing_renders(self):
        from rcm_mc.ui.physician_attrition_page import (
            render_physician_attrition_page,
        )
        h = render_physician_attrition_page()
        self.assertIn("Physician Attrition", h)
        self.assertIn("What this shows", h)

    def test_hero_contains_band_counts(self):
        from rcm_mc.ui.physician_attrition_page import (
            render_physician_attrition_page,
        )
        h = render_physician_attrition_page()
        self.assertIn("critical", h.lower())
        self.assertIn("high", h.lower())

    def test_bridge_lever_card_rendered(self):
        from rcm_mc.ui.physician_attrition_page import (
            render_physician_attrition_page,
        )
        h = render_physician_attrition_page()
        self.assertIn("EBITDA Bridge", h)
        self.assertIn("Physician-Attrition Lever", h)
        self.assertIn("physician_attrition_pct", h)

    def test_roster_table_rendered(self):
        from rcm_mc.ui.physician_attrition_page import (
            render_physician_attrition_page,
        )
        h = render_physician_attrition_page()
        self.assertIn("Full roster", h)
        # Demo roster provider IDs should appear
        self.assertIn("P001", h)
        self.assertIn("P005", h)

    def test_target_name_from_query(self):
        from rcm_mc.ui.physician_attrition_page import (
            render_physician_attrition_page,
        )
        h = render_physician_attrition_page(
            qs={"target_name": ["Acme Physician Group"]},
        )
        self.assertIn("Acme Physician Group", h)


class NavLinkTests(unittest.TestCase):

    def test_sidebar_has_physician_attrition(self):
        from rcm_mc.ui._chartis_kit import chartis_shell
        rendered = chartis_shell("<p>x</p>", "Test")
        self.assertIn('href="/diligence/physician-attrition"', rendered)

    def test_deal_profile_exposes_physician_attrition(self):
        from rcm_mc.ui.deal_profile_page import _ANALYTICS
        ids = [a.get("href") for a in _ANALYTICS]
        self.assertIn("/diligence/physician-attrition", ids)


# ────────────────────────────────────────────────────────────────────
# Edge cases + performance
# ────────────────────────────────────────────────────────────────────

class EdgeCaseTests(unittest.TestCase):

    def test_zero_collections_provider_handled(self):
        """A provider with zero collections should not crash the
        analyzer and should not count toward revenue concentration."""
        p = Provider(
            provider_id="ZC", specialty="INTERNAL_MEDICINE",
            employment_status="W2", base_salary_usd=250_000,
            collections_annual_usd=0,
        )
        r = analyze_roster([p])
        self.assertEqual(r.roster_size, 1)
        # Zero collections → zero at-risk — pass through cleanly.
        self.assertEqual(r.total_expected_collections_at_risk_usd, 0.0)
        self.assertEqual(r.scores[0].expected_collections_at_risk_usd, 0.0)

    def test_empty_specialty_uses_defaults(self):
        """A provider with empty specialty should use neutral priors
        rather than crashing on FMV lookup."""
        p = Provider(
            provider_id="NS", specialty="",
            employment_status="W2", base_salary_usd=300_000,
            collections_annual_usd=900_000,
        )
        f = extract_features(p)
        # specialty_mobility defaults to the unknown prior 0.40
        self.assertEqual(f.specialty_mobility, 0.40)
        # comp_gap_normalized degrades to 0.0 when no FMV benchmark
        self.assertEqual(f.comp_gap_normalized, 0.0)

    def test_unknown_specialty_uses_default_mobility(self):
        p = Provider(
            provider_id="UX", specialty="UNKNOWN_SPECIALTY",
            employment_status="W2", base_salary_usd=350_000,
            collections_annual_usd=1_000_000,
        )
        f = extract_features(p)
        self.assertEqual(f.specialty_mobility, 0.40)

    def test_negative_collections_clamped(self):
        p = Provider(
            provider_id="NEG", specialty="FAMILY_MEDICINE",
            employment_status="W2", base_salary_usd=280_000,
            collections_annual_usd=-100,
        )
        r = analyze_roster([p])
        self.assertGreaterEqual(
            r.total_expected_collections_at_risk_usd, 0.0,
        )
        self.assertGreaterEqual(r.total_collections_usd, 0.0)

    def test_large_roster_performance(self):
        """Score 120 providers — confirm compute stays well under 1s
        so the workbench integration doesn't slow down the page."""
        import time
        providers = [
            Provider(
                provider_id=f"P{i:03d}",
                specialty="INTERNAL_MEDICINE",
                employment_status="W2",
                base_salary_usd=300_000,
                collections_annual_usd=900_000,
            )
            for i in range(120)
        ]
        t0 = time.time()
        r = analyze_roster(providers)
        elapsed = time.time() - t0
        self.assertEqual(r.roster_size, 120)
        self.assertLess(elapsed, 1.0,
                        msg=f"120-provider scoring took {elapsed:.3f}s")

    def test_all_partner_roster_mostly_low(self):
        """All-PARTNER roster with long tenure and good productivity
        should skew toward LOW band."""
        providers = [
            Provider(
                provider_id=f"PART{i}", specialty="FAMILY_MEDICINE",
                employment_status="PARTNER",
                base_salary_usd=320_000,
                collections_annual_usd=1_100_000,
            )
            for i in range(8)
        ]
        r = analyze_roster(
            providers,
            years_at_facility={f"PART{i}": 14 for i in range(8)},
            ages={f"PART{i}": 48 for i in range(8)},
            yoy_collections_slopes={f"PART{i}": 0.04 for i in range(8)},
        )
        # Expect no CRITICAL; majority should be LOW or MEDIUM.
        self.assertEqual(r.critical_count, 0)
        self.assertGreaterEqual(r.low_count + r.medium_count, 6)


# ────────────────────────────────────────────────────────────────────
# Integration — Risk Workbench + Counterfactual + IC Packet
# ────────────────────────────────────────────────────────────────────

class RiskWorkbenchIntegrationTests(unittest.TestCase):

    def test_workbench_surfaces_attrition_rows(self):
        """When the workbench receives a provider roster, the
        physician_comp panel must include the PPAM flight-risk
        band counts."""
        from rcm_mc.ui.risk_workbench_page import (
            render_risk_workbench, WorkbenchInput,
        )
        roster = [
            Provider(provider_id="P1", specialty="ANESTHESIOLOGY",
                     employment_status="LOCUM",
                     base_salary_usd=500_000,
                     collections_annual_usd=1_900_000),
            Provider(provider_id="P2", specialty="CARDIOLOGY",
                     employment_status="PARTNER",
                     base_salary_usd=600_000,
                     collections_annual_usd=3_000_000),
            Provider(provider_id="P3", specialty="FAMILY_MEDICINE",
                     employment_status="W2",
                     base_salary_usd=280_000,
                     collections_annual_usd=800_000),
        ]
        h = render_risk_workbench(WorkbenchInput(
            target_name="Attrition Test",
            providers=roster,
        ))
        self.assertIn("Flight-risk bands", h)
        self.assertIn("EBITDA at risk", h)
        # Link to deep-dive page.
        self.assertIn('href="/diligence/physician-attrition"', h)


class CounterfactualIntegrationTests(unittest.TestCase):

    def test_for_physician_attrition_none_when_no_focus(self):
        from rcm_mc.diligence.counterfactual import (
            for_physician_attrition,
        )
        # Empty-ish report
        class _Stub:
            critical_count = 0
            high_count = 0
            scores = []
            bridge_input = None
        self.assertIsNone(for_physician_attrition(_Stub()))

    def test_for_physician_attrition_returns_bond_counterfactual(self):
        from rcm_mc.diligence.counterfactual import (
            for_physician_attrition,
        )
        roster = [
            Provider(provider_id="CRIT1", specialty="ANESTHESIOLOGY",
                     employment_status="LOCUM",
                     base_salary_usd=500_000,
                     collections_annual_usd=1_900_000),
            Provider(provider_id="HIGH1", specialty="ORTHOPEDIC_SURGERY",
                     employment_status="W2",
                     base_salary_usd=450_000,
                     collections_annual_usd=2_400_000),
        ]
        report = analyze_roster(
            roster,
            years_at_facility={"CRIT1": 0.3, "HIGH1": 1},
            yoy_collections_slopes={"CRIT1": -0.18, "HIGH1": -0.08},
        )
        cf = for_physician_attrition(report)
        self.assertIsNotNone(cf)
        self.assertEqual(cf.module, "PHYSICIAN_ATTRITION")
        self.assertEqual(cf.lever, "RETENTION_BONDS")
        self.assertGreater(cf.estimated_dollar_impact_usd, 0)
        # Change description should name the providers.
        self.assertTrue(
            "CRIT1" in cf.change_description or
            "HIGH1" in cf.change_description,
        )

    def test_advise_all_includes_attrition(self):
        from rcm_mc.diligence.counterfactual import advise_all
        roster = [
            Provider(provider_id="P1", specialty="EMERGENCY_MEDICINE",
                     employment_status="1099",
                     base_salary_usd=420_000,
                     collections_annual_usd=1_600_000),
        ]
        report = analyze_roster(
            roster,
            years_at_facility={"P1": 0.5},
            yoy_collections_slopes={"P1": -0.15},
        )
        cfs = advise_all(physician_attrition=report)
        modules = [c.module for c in cfs.items]
        self.assertIn("PHYSICIAN_ATTRITION", modules)


class ICPacketIntegrationTests(unittest.TestCase):

    def _sample_attrition_report(self):
        roster = [
            Provider(provider_id="CRIT1", specialty="ANESTHESIOLOGY",
                     employment_status="LOCUM",
                     base_salary_usd=500_000,
                     collections_annual_usd=1_900_000),
            Provider(provider_id="HIGH1", specialty="ORTHOPEDIC_SURGERY",
                     employment_status="W2",
                     base_salary_usd=450_000,
                     collections_annual_usd=2_400_000),
        ]
        return analyze_roster(
            roster,
            years_at_facility={"CRIT1": 0.3, "HIGH1": 1},
            yoy_collections_slopes={"CRIT1": -0.18, "HIGH1": -0.08},
        )

    def test_ic_packet_renders_physician_retention_section(self):
        from rcm_mc.exports import (
            ICPacketMetadata, render_ic_packet_html,
        )
        html_str = render_ic_packet_html(
            metadata=ICPacketMetadata(deal_name="Test Target"),
            attrition_report=self._sample_attrition_report(),
        )
        self.assertIn("Physician Retention Plan", html_str)
        # Provider ID named
        self.assertIn("CRIT1", html_str)
        self.assertIn("retention bond", html_str.lower())

    def test_ic_packet_silent_when_no_focus_providers(self):
        """If all providers are LOW band, the section should not
        render — we don't announce 'no retention action needed'."""
        from rcm_mc.exports import (
            ICPacketMetadata, render_ic_packet_html,
        )
        roster = [
            Provider(provider_id="STABLE", specialty="FAMILY_MEDICINE",
                     employment_status="PARTNER",
                     base_salary_usd=320_000,
                     collections_annual_usd=1_100_000),
        ]
        report = analyze_roster(
            roster,
            years_at_facility={"STABLE": 14},
            ages={"STABLE": 48},
            yoy_collections_slopes={"STABLE": 0.04},
        )
        html_str = render_ic_packet_html(
            metadata=ICPacketMetadata(deal_name="Stable Target"),
            attrition_report=report,
        )
        self.assertNotIn("Physician Retention Plan", html_str)

    def test_ic_packet_silent_when_report_is_none(self):
        from rcm_mc.exports import (
            ICPacketMetadata, render_ic_packet_html,
        )
        html_str = render_ic_packet_html(
            metadata=ICPacketMetadata(deal_name="Test"),
            attrition_report=None,
        )
        self.assertNotIn("Physician Retention Plan", html_str)


# ────────────────────────────────────────────────────────────────────
# Power-UI features on the page
# ────────────────────────────────────────────────────────────────────

class PowerUIFeatureTests(unittest.TestCase):

    def _render(self, **qs):
        from rcm_mc.ui.physician_attrition_page import (
            render_physician_attrition_page,
        )
        wrapped = {k: [v] for k, v in qs.items()}
        return render_physician_attrition_page(qs=wrapped)

    def test_hero_numbers_have_inline_provenance(self):
        """Every hero KPI number should carry a data-provenance
        tooltip source so partners can hover to audit."""
        h = self._render()
        self.assertIn("data-provenance", h)
        # At least 4 hero KPIs + 1 "recoverable" in Denial-style card = 4
        self.assertGreaterEqual(h.count("data-provenance"), 4)

    def test_json_export_wrapper_present(self):
        """Hero + bridge card must be wrapped in export_json_panel
        so the power_ui JS injects a JSON-export button."""
        h = self._render()
        self.assertIn('data-export-json', h)
        self.assertIn('physician_attrition_report', h)

    def test_roster_table_is_sortable_filterable_exportable(self):
        h = self._render()
        # sortable_table stamps these attributes
        self.assertIn("data-sortable", h)
        self.assertIn("data-filterable", h)
        self.assertIn("data-export", h)

    def test_band_filter_chips_present(self):
        h = self._render()
        self.assertIn("Quick filter:", h)
        for label in ("All bands", "Critical", "High", "Medium", "Low"):
            self.assertIn(label, h, msg=f"chip {label} missing")

    def test_band_filter_critical_limits_focus_cards(self):
        h = self._render(band="CRITICAL")
        # The focus-card rail should still render for CRITICAL-only
        self.assertIn("retention action required", h)

    def test_band_filter_low_shows_empty_state(self):
        """When the filter keeps no HIGH/CRITICAL providers, the
        empty-state callout should render instead of focus cards."""
        h = self._render(band="LOW")
        self.assertTrue(
            "LOW" in h and
            ("No providers are in the" in h or
             "No providers are in HIGH" in h),
        )

    def test_feature_vector_drilldown_present(self):
        """Each focus card should carry a details-summary drilldown
        that exposes the full 9-feature vector with β·x."""
        h = self._render()
        self.assertIn("Full feature vector", h)
        self.assertIn("click to expand", h)
        self.assertIn("β·x", h)

    def test_add_to_compare_link_present(self):
        h = self._render()
        self.assertIn("Add to compare", h)
        self.assertIn("?compare=", h)

    def test_keyboard_hint_rendered(self):
        h = self._render()
        self.assertIn("<kbd", h)


class CompareViewTests(unittest.TestCase):

    def _render_compare(self, ids):
        from rcm_mc.ui.physician_attrition_page import (
            render_physician_attrition_page,
        )
        return render_physician_attrition_page(
            qs={"compare": [",".join(ids)]},
        )

    def test_two_way_comparison_renders(self):
        h = self._render_compare(["P001", "P005"])
        self.assertIn("2-way comparison", h)
        self.assertIn("P001", h)
        self.assertIn("P005", h)
        self.assertIn("Back to full roster", h)

    def test_three_way_comparison_renders(self):
        h = self._render_compare(["P001", "P004", "P005"])
        self.assertIn("3-way comparison", h)

    def test_unknown_providers_show_fallback(self):
        h = self._render_compare(["NOT_A_PROVIDER"])
        self.assertIn("None of the provided provider IDs", h)

    def test_compare_cap_at_four(self):
        from rcm_mc.ui.physician_attrition_page import (
            _parse_compare_ids,
        )
        ids = _parse_compare_ids({
            "compare": ["A,B,C,D,E,F,G"],
        })
        self.assertEqual(len(ids), 4)

    def test_compare_duplicates_dropped(self):
        from rcm_mc.ui.physician_attrition_page import (
            _parse_compare_ids,
        )
        ids = _parse_compare_ids({"compare": ["A,B,A,C"]})
        self.assertEqual(ids, ["A", "B", "C"])


if __name__ == "__main__":
    unittest.main()
