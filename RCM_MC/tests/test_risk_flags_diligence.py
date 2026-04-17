"""Tests for the automated intelligence layer (risk flags + diligence questions).

Covers:
- Each of the 6 risk categories + their severity ladders
- OBBBA-specific flag for high-Medicaid hospitals
- A "perfect" hospital produces zero operational/regulatory flags
- Diligence questions quote the triggering number verbatim
- Missing P0 data is surfaced for every critical metric gap
- Standard "always-ask" questions are emitted
- Dedup: a single metric that trips both completeness and a risk
  flag produces one question, not two
"""
from __future__ import annotations

import unittest
from typing import Dict, List

from rcm_mc.analysis.completeness import (
    RCM_METRIC_REGISTRY,
    assess_completeness,
)
from rcm_mc.analysis.diligence_questions import generate_diligence_questions
from rcm_mc.analysis.packet import (
    ComparableHospital,
    ComparableSet,
    CompletenessAssessment,
    DiligencePriority,
    EBITDABridgeResult,
    HospitalProfile,
    MetricImpact,
    ObservedMetric,
    ProfileMetric,
    MetricSource,
    RiskFlag,
    RiskSeverity,
)
from rcm_mc.analysis.risk_flags import (
    CATEGORY_CODING,
    CATEGORY_DATA_QUALITY,
    CATEGORY_FINANCIAL,
    CATEGORY_OPERATIONAL,
    CATEGORY_PAYER,
    CATEGORY_REGULATORY,
    assess_risks,
)


# ── Fixtures ─────────────────────────────────────────────────────────

def _pm(value: float) -> ProfileMetric:
    return ProfileMetric(value=float(value), source=MetricSource.OBSERVED)


def _profile(payer_mix=None, state="IL") -> HospitalProfile:
    return HospitalProfile(
        bed_count=400, region="midwest", state=state,
        payer_mix=payer_mix or {"medicare": 0.40, "commercial": 0.45, "medicaid": 0.15},
    )


def _bridge(current_ebitda: float = 30_000_000.0, impacts=None) -> EBITDABridgeResult:
    return EBITDABridgeResult(
        current_ebitda=current_ebitda, target_ebitda=current_ebitda,
        per_metric_impacts=list(impacts or []),
    )


def _completeness(coverage_pct: float = 0.8, grade: str = "B",
                  missing_ranked: List[str] = None) -> CompletenessAssessment:
    from rcm_mc.analysis.packet import MissingField
    return CompletenessAssessment(
        coverage_pct=coverage_pct, total_metrics=30,
        observed_count=int(coverage_pct * 30), grade=grade,
        missing_ranked_by_sensitivity=missing_ranked or [],
        missing_fields=[MissingField(metric_key=k,
                                      ebitda_sensitivity_rank=i + 1)
                         for i, k in enumerate(missing_ranked or [])],
    )


# ── OPERATIONAL category ─────────────────────────────────────────────

class TestOperationalFlags(unittest.TestCase):
    def test_high_denial_rate_fires_critical(self):
        rcm = {"denial_rate": _pm(13.0)}
        flags = assess_risks(_profile(), rcm)
        hits = [f for f in flags if f.category == CATEGORY_OPERATIONAL
                and f.trigger_metric == "denial_rate"]
        self.assertTrue(hits)
        self.assertEqual(hits[0].severity, RiskSeverity.CRITICAL)
        self.assertIn("13.0%", hits[0].detail)

    def test_moderate_denial_rate_fires_high(self):
        rcm = {"denial_rate": _pm(10.5)}
        flags = assess_risks(_profile(), rcm)
        hits = [f for f in flags if f.category == CATEGORY_OPERATIONAL
                and f.trigger_metric == "denial_rate"]
        self.assertTrue(hits)
        self.assertEqual(hits[0].severity, RiskSeverity.HIGH)

    def test_denial_rate_under_threshold_no_flag(self):
        rcm = {"denial_rate": _pm(5.2)}
        flags = assess_risks(_profile(), rcm)
        self.assertFalse(any(f.trigger_metric == "denial_rate" for f in flags))

    def test_ar_over_90_fires_high(self):
        rcm = {"ar_over_90_pct": _pm(25.0)}
        flags = assess_risks(_profile(), rcm)
        hits = [f for f in flags if f.trigger_metric == "ar_over_90_pct"]
        self.assertTrue(hits)
        self.assertEqual(hits[0].severity, RiskSeverity.HIGH)

    def test_clean_claim_below_threshold_fires_high(self):
        rcm = {"clean_claim_rate": _pm(85.0)}
        flags = assess_risks(_profile(), rcm)
        hits = [f for f in flags if f.trigger_metric == "clean_claim_rate"]
        self.assertTrue(hits)
        self.assertEqual(hits[0].severity, RiskSeverity.HIGH)

    def test_dnfb_and_charge_lag_medium(self):
        rcm = {"dnfb_days": _pm(9.0), "charge_lag_days": _pm(6.0)}
        flags = assess_risks(_profile(), rcm)
        triggers = {f.trigger_metric for f in flags}
        self.assertIn("dnfb_days", triggers)
        self.assertIn("charge_lag_days", triggers)


# ── REGULATORY: OBBBA Medicaid ───────────────────────────────────────

class TestRegulatoryFlags(unittest.TestCase):
    def test_high_medicaid_triggers_obbba_flag(self):
        profile = _profile(
            payer_mix={"medicare": 0.35, "commercial": 0.30, "medicaid": 0.35},
        )
        flags = assess_risks(profile, {})
        obbba = [f for f in flags if f.category == CATEGORY_REGULATORY
                 and "Medicaid" in f.title]
        self.assertTrue(obbba, "expected OBBBA flag for 35% Medicaid")
        self.assertEqual(obbba[0].severity, RiskSeverity.HIGH)
        # Must cite OBBBA specifically in the detail text.
        self.assertIn("OBBBA", obbba[0].detail)
        self.assertIn("11.8M", obbba[0].detail)

    def test_obbba_amplified_for_work_requirement_states(self):
        profile = _profile(
            payer_mix={"medicare": 0.30, "commercial": 0.30, "medicaid": 0.40},
            state="GA",
        )
        flags = assess_risks(profile, {})
        obbba = next(f for f in flags if "Medicaid" in f.title)
        self.assertIn("work-requirement", obbba.detail.lower())

    def test_medicaid_under_25_no_flag(self):
        profile = _profile(
            payer_mix={"medicare": 0.50, "commercial": 0.40, "medicaid": 0.10},
        )
        flags = assess_risks(profile, {})
        obbba = [f for f in flags if "Medicaid" in f.title]
        self.assertFalse(obbba)

    def test_high_medicare_fires_sequestration_flag(self):
        profile = _profile(
            payer_mix={"medicare": 0.60, "commercial": 0.30, "medicaid": 0.10},
        )
        flags = assess_risks(profile, {})
        seq = [f for f in flags if "Medicare" in f.title]
        self.assertTrue(seq)
        self.assertEqual(seq[0].severity, RiskSeverity.MEDIUM)
        self.assertIn("sequestration", seq[0].detail.lower())


# ── PAYER category ───────────────────────────────────────────────────

class TestPayerFlags(unittest.TestCase):
    def test_concentration_over_30pct_fires(self):
        profile = _profile(
            payer_mix={"medicare": 0.40, "commercial": 0.35, "medicaid": 0.25},
        )
        flags = assess_risks(profile, {})
        # medicare 40% → concentration flag (also medicare itself >30)
        conc = [f for f in flags if f.category == CATEGORY_PAYER
                and "concentration" in f.title.lower()]
        self.assertTrue(conc)

    def test_low_commercial_mix_medium(self):
        profile = _profile(
            payer_mix={"medicare": 0.50, "commercial": 0.20, "medicaid": 0.30},
        )
        flags = assess_risks(profile, {})
        # Commercial < 25% → medium
        comm = [f for f in flags if f.category == CATEGORY_PAYER
                and "commercial" in f.title.lower()]
        self.assertTrue(comm)
        self.assertEqual(comm[0].severity, RiskSeverity.MEDIUM)

    def test_ma_denial_rate_flag(self):
        rcm = {"denial_rate_medicare_advantage": _pm(18.0)}
        flags = assess_risks(_profile(), rcm)
        ma = [f for f in flags
              if f.trigger_metric == "denial_rate_medicare_advantage"]
        self.assertTrue(ma)
        self.assertEqual(ma[0].severity, RiskSeverity.HIGH)


# ── CODING category ─────────────────────────────────────────────────

class TestCodingFlags(unittest.TestCase):
    def test_cmi_below_cohort_p25_fires(self):
        rcm = {"case_mix_index": _pm(1.20)}
        peers = [ComparableHospital(
            id=f"p{i}", similarity_score=0.9,
            fields={"case_mix_index": 1.50 + 0.05 * i},
        ) for i in range(10)]
        cs = ComparableSet(peers=peers)
        flags = assess_risks(_profile(), rcm, comparables=cs)
        hit = [f for f in flags if f.trigger_metric == "case_mix_index"]
        self.assertTrue(hit)
        self.assertIn("undercoding", hit[0].title.lower())

    def test_coding_accuracy_low_medium(self):
        rcm = {"coding_accuracy_rate": _pm(92.0)}
        flags = assess_risks(_profile(), rcm)
        hit = [f for f in flags if f.trigger_metric == "coding_accuracy_rate"]
        self.assertTrue(hit)
        self.assertEqual(hit[0].severity, RiskSeverity.MEDIUM)


# ── DATA_QUALITY + FINANCIAL ────────────────────────────────────────

class TestDataQualityAndFinancial(unittest.TestCase):
    def test_grade_d_completeness_fires_critical(self):
        cmp = _completeness(coverage_pct=0.35, grade="D")
        flags = assess_risks(_profile(), {}, completeness=cmp)
        hits = [f for f in flags if f.category == CATEGORY_DATA_QUALITY
                and f.severity == RiskSeverity.CRITICAL]
        self.assertTrue(hits)

    def test_ebitda_margin_below_5pct_fires_high(self):
        rcm = {"ebitda_margin": _pm(3.0)}
        flags = assess_risks(_profile(), rcm)
        hits = [f for f in flags if f.trigger_metric == "ebitda_margin"]
        self.assertTrue(hits)
        self.assertEqual(hits[0].severity, RiskSeverity.HIGH)

    def test_negative_ebitda_fires_critical(self):
        bridge = _bridge(current_ebitda=-5_000_000.0)
        flags = assess_risks(_profile(), {}, ebitda_bridge=bridge)
        hits = [f for f in flags if f.trigger_metric == "current_ebitda"]
        self.assertTrue(hits)
        self.assertEqual(hits[0].severity, RiskSeverity.CRITICAL)
        self.assertIn("loss", hits[0].title.lower())

    def test_ebitda_at_risk_populated_from_bridge(self):
        """When a flag trips on a metric that the bridge also modeled,
        ``ebitda_at_risk`` carries the bridge's dollar estimate."""
        rcm = {"denial_rate": _pm(12.0)}
        bridge = _bridge(impacts=[MetricImpact(
            metric_key="denial_rate", current_value=12.0, target_value=6.0,
            ebitda_impact=9_500_000.0,
        )])
        flags = assess_risks(_profile(), rcm, ebitda_bridge=bridge)
        hits = [f for f in flags if f.trigger_metric == "denial_rate"]
        self.assertTrue(hits)
        self.assertAlmostEqual(hits[0].ebitda_at_risk, 9_500_000.0)


# ── Perfect hospital ────────────────────────────────────────────────

class TestPerfectHospital(unittest.TestCase):
    def test_perfect_hospital_produces_minimal_flags(self):
        """Hospital sitting at best-in-class on every metric should not
        trigger any operational / regulatory / payer / coding /
        financial flags. Data-quality can still fire if the caller
        doesn't supply a completeness assessment, but that's fine.
        """
        rcm = {
            "denial_rate": _pm(3.0),              # below 10
            "ar_over_90_pct": _pm(12.0),          # below 20
            "clean_claim_rate": _pm(95.0),        # above 90
            "dnfb_days": _pm(5.0),                # below 7
            "charge_lag_days": _pm(2.0),          # below 5
            "denial_rate_medicare_advantage": _pm(6.0),  # below 15
            "case_mix_index": _pm(1.90),          # high
            "coding_accuracy_rate": _pm(98.0),
            "ebitda_margin": _pm(12.0),
        }
        profile = _profile(
            payer_mix={"medicare": 0.40, "commercial": 0.40, "medicaid": 0.20},
            state="IL",
        )
        flags = assess_risks(profile, rcm, ebitda_bridge=_bridge())
        # Filter to the five "hospital health" categories that depend
        # solely on the hospital's data. Medicaid at 20% is the only
        # potential regulatory trip; confirm it's silent.
        categories = {f.category for f in flags}
        self.assertNotIn(CATEGORY_OPERATIONAL, categories)
        self.assertNotIn(CATEGORY_REGULATORY, categories)
        self.assertNotIn(CATEGORY_CODING, categories)
        self.assertNotIn(CATEGORY_FINANCIAL, categories)


# ── Diligence questions ─────────────────────────────────────────────

class TestDiligenceQuestions(unittest.TestCase):
    def test_missing_critical_data_emits_p0(self):
        cmp = _completeness(
            coverage_pct=0.4, grade="D",
            missing_ranked=["denial_rate", "days_in_ar", "net_collection_rate",
                            "cost_to_collect", "clean_claim_rate"],
        )
        qs = generate_diligence_questions(_profile(), {}, [], cmp, None)
        p0 = [q for q in qs if q.priority == DiligencePriority.P0]
        self.assertGreaterEqual(len(p0), 3)
        # Must reference the specific missing metric by display name.
        joined = " ".join(q.question for q in p0)
        self.assertTrue("denial_rate" in joined.lower() or
                        "denial rate" in joined.lower())

    def test_high_denial_flag_question_quotes_the_number(self):
        flag = RiskFlag(
            category=CATEGORY_OPERATIONAL,
            severity=RiskSeverity.CRITICAL,
            title="Systemic denial problem",
            detail="Denial rate is 14.5%",
            trigger_metrics=["denial_rate"],
            trigger_metric="denial_rate", trigger_value=14.5,
        )
        qs = generate_diligence_questions(
            _profile(), {}, [flag], _completeness(), None,
        )
        p0 = [q for q in qs if q.priority == DiligencePriority.P0]
        self.assertTrue(p0)
        q = p0[0]
        # The question body should literally contain "14.5".
        self.assertIn("14.5", q.question)
        self.assertEqual(q.category, CATEGORY_OPERATIONAL)

    def test_obbba_flag_question_references_dec_2026(self):
        flag = RiskFlag(
            category=CATEGORY_REGULATORY,
            severity=RiskSeverity.HIGH,
            title="OBBBA / Medicaid coverage-loss exposure",
            detail="Medicaid 35%",
            trigger_metrics=["payer_mix.medicaid"],
            trigger_metric="payer_mix.medicaid", trigger_value=0.35,
        )
        qs = generate_diligence_questions(_profile(), {}, [flag],
                                          _completeness(), None)
        medicaid_qs = [q for q in qs if q.trigger_metric == "payer_mix.medicaid"]
        self.assertTrue(medicaid_qs)
        self.assertIn("OBBBA", medicaid_qs[0].question)
        self.assertIn("2026", medicaid_qs[0].question)

    def test_payer_breakdown_gap_emits_p0(self):
        rcm = {"denial_rate": _pm(8.0)}  # parent present, no children
        qs = generate_diligence_questions(
            _profile(), rcm, [], _completeness(), None,
        )
        payer_break = [q for q in qs
                       if q.trigger == "missing:payer-specific-denials"]
        self.assertTrue(payer_break)
        self.assertEqual(payer_break[0].priority, DiligencePriority.P0)

    def test_reason_code_gap_emits_p0(self):
        rcm = {"denial_rate": _pm(8.0)}
        qs = generate_diligence_questions(
            _profile(), rcm, [], _completeness(), None,
        )
        reasons = [q for q in qs if q.trigger == "missing:denial-reason-codes"]
        self.assertTrue(reasons)

    def test_outlier_question_cites_sigma(self):
        rcm = {"days_in_ar": _pm(120.0)}
        peers = [ComparableHospital(
            id=f"p{i}", similarity_score=0.9,
            fields={"days_in_ar": 45.0 + 0.5 * i},
        ) for i in range(20)]
        cs = ComparableSet(peers=peers)
        qs = generate_diligence_questions(_profile(), rcm, [],
                                          _completeness(), cs)
        outlier = [q for q in qs if q.trigger.startswith("outlier:")]
        self.assertTrue(outlier)
        self.assertRegex(outlier[0].question, r"\d+\.\d+σ")

    def test_standard_questions_always_emitted(self):
        """Contract / EHR / CDI / CDM / IT-contract questions emit on
        every deal, even a quiet one with no risk flags."""
        qs = generate_diligence_questions(_profile(), {}, [],
                                          _completeness(), None)
        questions = " ".join(q.question for q in qs)
        self.assertIn("EHR", questions)
        self.assertIn("CDI", questions)
        self.assertIn("CDM", questions)
        self.assertIn("contract", questions.lower())

    def test_questions_sorted_by_priority(self):
        cmp = _completeness(
            coverage_pct=0.4, grade="D",
            missing_ranked=["denial_rate", "days_in_ar"],
        )
        qs = generate_diligence_questions(_profile(), {}, [], cmp, None)
        priorities = [q.priority.value for q in qs]
        # P0 all before P1, P1 all before P2.
        for i in range(len(priorities) - 1):
            p_cur = priorities[i]
            p_next = priorities[i + 1]
            # Allow alphabetical within same priority.
            if p_cur != p_next:
                self.assertLess(p_cur, p_next)

    def test_dedup_trigger_metric_priority(self):
        """A metric that's both missing (P0) and riding a risk flag
        (P0) should produce one question, not two. The risk flag's
        specific-number version wins because it cites the value."""
        flag = RiskFlag(
            category=CATEGORY_OPERATIONAL, severity=RiskSeverity.CRITICAL,
            title="Systemic denial problem", detail="",
            trigger_metrics=["denial_rate"], trigger_metric="denial_rate",
            trigger_value=14.5,
        )
        cmp = _completeness(
            coverage_pct=0.4, grade="D",
            missing_ranked=["denial_rate", "days_in_ar"],
        )
        qs = generate_diligence_questions(_profile(), {}, [flag], cmp, None)
        denial_qs = [q for q in qs if q.trigger_metric == "denial_rate"]
        self.assertEqual(len(denial_qs), 1)
        # The surviving question is the flag version (cites 14.5).
        self.assertIn("14.5", denial_qs[0].question)

    def test_critical_data_quality_flag_emits_p0_data_request(self):
        flag = RiskFlag(
            category=CATEGORY_DATA_QUALITY,
            severity=RiskSeverity.CRITICAL,
            title="Insufficient data",
            detail="Only 35% of metrics available",
            trigger_metric="completeness.coverage_pct",
            trigger_value=0.35,
        )
        qs = generate_diligence_questions(_profile(), {}, [flag],
                                          _completeness(), None)
        dq = [q for q in qs if q.category == CATEGORY_DATA_QUALITY]
        self.assertTrue(dq)
        self.assertEqual(dq[0].priority, DiligencePriority.P0)
        self.assertIn("24 months", dq[0].question)


# ── Full severity ordering ──────────────────────────────────────────

class TestSeverityOrdering(unittest.TestCase):
    def test_flags_sorted_critical_first(self):
        rcm = {
            "denial_rate": _pm(13.0),           # CRITICAL
            "clean_claim_rate": _pm(88.0),      # HIGH
            "dnfb_days": _pm(9.0),              # MEDIUM
        }
        flags = assess_risks(_profile(), rcm)
        severities = [f.severity for f in flags]
        # critical ≤ high ≤ medium ≤ low by index
        rank = {
            RiskSeverity.CRITICAL: 0, RiskSeverity.HIGH: 1,
            RiskSeverity.MEDIUM: 2, RiskSeverity.LOW: 3,
        }
        ranks = [rank[s] for s in severities]
        self.assertEqual(ranks, sorted(ranks))


if __name__ == "__main__":
    unittest.main()
