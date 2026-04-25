"""Tests for the ManagementAssessmentPacket."""
from __future__ import annotations

import unittest


def _baseline_team():
    from rcm_mc.management import Executive, ManagementTeam
    return ManagementTeam(
        company_name="Hospital Co",
        executives=[
            Executive(person_id="E1", name="Alice CEO",
                      role="CEO", tenure_years=4.0,
                      direct_reports=7,
                      has_pe_experience=True,
                      rollover_equity_pct=0.25),
            Executive(person_id="E2", name="Bob CFO",
                      role="CFO", tenure_years=2.0,
                      direct_reports=6,
                      has_pe_experience=True,
                      rollover_equity_pct=0.10),
            Executive(person_id="E3", name="Carol COO",
                      role="COO", tenure_years=8.0,
                      direct_reports=8,
                      rollover_equity_pct=0.15),
        ],
        total_headcount=420,
        org_layers=5,
    )


# ── Scorecard ───────────────────────────────────────────────────

class TestScorecard(unittest.TestCase):
    def test_composite_with_role_weights(self):
        from rcm_mc.management import score_competencies
        team = _baseline_team()
        scores = {
            "E1": {d: 4.0 for d in (
                "financial_discipline", "payer_relationships",
                "ma_integration", "talent_retention",
                "regulatory_compliance", "operational_execution",
                "strategic_clarity", "external_credibility")},
            "E2": {"financial_discipline": 5.0,
                   "regulatory_compliance": 4.5},
            "E3": {"operational_execution": 4.5},
        }
        sc = score_competencies(team, scores)
        # E1 with all 4.0s → composite 4.0
        ceo = next(p for p in sc.per_executive
                   if p.person_id == "E1")
        self.assertAlmostEqual(ceo.composite, 4.0, places=2)
        # Team composite is the mean of per-exec composites
        team_composite = (
            sum(p.composite for p in sc.per_executive)
            / len(sc.per_executive))
        self.assertAlmostEqual(
            sc.team_composite, team_composite, places=2)
        # Bands valid
        for p in sc.per_executive:
            self.assertIn(p.band, (
                "standout", "above_avg", "average",
                "below_avg", "concerning"))


# ── Big Five ────────────────────────────────────────────────────

class TestPersonality(unittest.TestCase):
    def test_high_conscientiousness_high_score_for_cfo(self):
        from rcm_mc.management import assess_big_five
        # CFO with high C + low everything else
        prof = assess_big_five(
            "E1", "CFO",
            openness=2.0, conscientiousness=5.0,
            extraversion=2.0, agreeableness=3.0,
            emotional_stability=4.0,
        )
        # CFO weights C at 0.40 → score should be elevated
        self.assertGreater(prof.investability_score, 3.5)

    def test_high_agreeableness_flag_for_ceo(self):
        from rcm_mc.management import assess_big_five
        prof = assess_big_five(
            "E1", "CEO",
            openness=4.0, conscientiousness=4.0,
            extraversion=4.0, agreeableness=4.8,
            emotional_stability=4.0,
        )
        # Should produce a yellow-flag note
        self.assertIn("agreeableness", prof.notes.lower())

    def test_low_emotional_stability_flag(self):
        from rcm_mc.management import assess_big_five
        prof = assess_big_five(
            "E1", "COO",
            openness=3.0, conscientiousness=3.0,
            extraversion=3.0, agreeableness=3.0,
            emotional_stability=2.0,
        )
        self.assertIn("emotional stability", prof.notes.lower())


# ── Org design ─────────────────────────────────────────────────

class TestOrgDesign(unittest.TestCase):
    def test_healthy_span_and_layers(self):
        from rcm_mc.management import score_org_design
        team = _baseline_team()
        out = score_org_design(team, revenue_mm=200, sector="hospital")
        # Avg direct_reports = 7; 5 layers — both healthy
        self.assertGreater(out.composite, 3.5)
        # Hospital with no CMO triggers anti-pattern
        self.assertTrue(any("No CMO" in p
                            for p in out.anti_patterns))

    def test_dual_hat_anti_pattern_detected(self):
        from rcm_mc.management import (
            Executive, ManagementTeam, score_org_design,
        )
        team = ManagementTeam(
            company_name="Test",
            executives=[
                Executive(person_id="E", name="Dual",
                          role="CFO/CRO", direct_reports=5),
            ],
            org_layers=4,
        )
        out = score_org_design(team, revenue_mm=80,
                               sector="rcm")
        self.assertTrue(any("Dual-hat" in p
                            for p in out.anti_patterns))


# ── 360 feedback ───────────────────────────────────────────────

class TestFeedback(unittest.TestCase):
    def test_weighted_means_and_blind_spot(self):
        from rcm_mc.management import (
            aggregate_360_feedback, RaterFeedback, RaterRole,
        )
        feedback = [
            # Self gives 5.0 on every trait
            RaterFeedback(
                rater_id="self", rater_role=RaterRole.SELF,
                person_id="E1",
                trait_scores={"strategic_clarity": 5.0,
                              "operational_execution": 5.0}),
            # Boss gives 3.0
            RaterFeedback(
                rater_id="b1", rater_role=RaterRole.BOSS,
                person_id="E1",
                trait_scores={"strategic_clarity": 3.0,
                              "operational_execution": 3.0}),
            # Peers give 3.5
            RaterFeedback(
                rater_id="p1", rater_role=RaterRole.PEER,
                person_id="E1",
                trait_scores={"strategic_clarity": 3.5,
                              "operational_execution": 3.5}),
        ]
        agg = aggregate_360_feedback("E1", feedback)
        self.assertEqual(agg.n_raters, 3)
        # Self = 5, non-self mean ≈ 3.25 → blind spot ≈ 1.75
        self.assertGreater(agg.blind_spot_score, 1.0)
        # Yellow flag fired
        self.assertGreater(len(agg.yellow_flags), 0)


# ── Succession ─────────────────────────────────────────────────

class TestSuccession(unittest.TestCase):
    def test_register_sorted_by_impact(self):
        from rcm_mc.management import build_succession_register
        team = _baseline_team()
        reg = build_succession_register(
            team, target_ebitda_mm=80,
            bench_strengths={"E1": 1.5, "E2": 3.0, "E3": 4.0},
        )
        # CEO has highest concentration → highest impact
        self.assertEqual(reg.risks[0].role, "CEO")
        # Risks sorted descending by departure_impact_mm
        impacts = [r.departure_impact_mm for r in reg.risks]
        self.assertEqual(impacts,
                         sorted(impacts, reverse=True))
        # CEO with bench 1.5 + high impact → high severity
        ceo_risk = reg.risks[0]
        self.assertEqual(ceo_risk.severity, "high")

    def test_retention_levers_use_rollover(self):
        from rcm_mc.management import build_succession_register
        team = _baseline_team()
        reg = build_succession_register(team, target_ebitda_mm=80)
        # E2 has 10% rollover → flag to increase
        e2 = next(r for r in reg.risks if r.person_id == "E2")
        self.assertTrue(any("Increase rollover" in lever
                            for lever in e2.retention_levers))


# ── Optimize ──────────────────────────────────────────────────

class TestOptimize(unittest.TestCase):
    def test_recommendations_combine_inputs(self):
        from rcm_mc.management import (
            score_competencies, score_org_design,
            build_succession_register, recommend_team_actions,
        )
        team = _baseline_team()
        # Below-avg scores → expect COACH actions
        scores = {
            "E1": {d: 2.5 for d in (
                "financial_discipline", "payer_relationships",
                "ma_integration", "talent_retention",
                "regulatory_compliance", "operational_execution",
                "strategic_clarity", "external_credibility")},
        }
        sc = score_competencies(team, scores)
        org = score_org_design(team, revenue_mm=200,
                               sector="hospital")
        suc = build_succession_register(
            team, target_ebitda_mm=80,
            bench_strengths={"E1": 1.0, "E2": 4.0, "E3": 4.0},
        )
        recs = recommend_team_actions(team, sc, org, suc)
        action_types = {a.action_type for a in recs.actions}
        # Should include at least HIRE (CMO anti-pattern) +
        # something for the below-avg CEO.
        self.assertIn("HIRE", action_types)
        self.assertGreater(len(recs.actions), 0)
        self.assertGreater(recs.high_priority_count, 0)


if __name__ == "__main__":
    unittest.main()
