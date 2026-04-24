"""Curated realization priors for banker EBITDA-bridge levers.

Every sell-side RCM bridge is decomposed into lever categories
(denial workflow, coding uplift, vendor consolidation, etc.).
This module ships a library of *realization priors* — empirical
distributions of how much of a claimed lever value actually shows
up in year-2 EBITDA.

Priors are sourced from:
    * ~3,000 RCM initiative outcomes from our autopsy / VCP library
    * PE sector surveys (Bain, McKinsey published data)
    * Historical bankruptcy filings where bridges never realized
      (Steward, Cano, Envision — forensic accounting)

The library ships 20 canonical categories.  Each carries:
    * ``realization_median`` — 0..1+  (50th pctile of claimed→realized ratio)
    * ``realization_p25`` / ``realization_p75`` — dispersion
    * ``realization_n_samples`` — evidence strength
    * ``failure_rate`` — fraction of deals that realized <50% of claim
    * ``duration_months_median`` — time to hit run-rate realization
    * ``gating_signals`` — target characteristics that boost or
      depress realization (e.g. denial-rate band, payer mix)

The auditor uses these priors + target profile to rebuild a
risk-adjusted bridge.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Tuple


class LeverCategory(str, Enum):
    # Revenue-cycle classic levers
    DENIAL_WORKFLOW = "DENIAL_WORKFLOW"
    CODING_INTENSITY = "CODING_INTENSITY"
    UNDERPAYMENT_RECOVERY = "UNDERPAYMENT_RECOVERY"
    CHARGE_CAPTURE = "CHARGE_CAPTURE"
    AR_AGING_LIQUIDATION = "AR_AGING_LIQUIDATION"
    BAD_DEBT_REDUCTION = "BAD_DEBT_REDUCTION"
    CREDIT_BALANCE_RELEASE = "CREDIT_BALANCE_RELEASE"
    CLEAN_CLAIM_RATE = "CLEAN_CLAIM_RATE"
    # Cost / operational levers
    VENDOR_CONSOLIDATION = "VENDOR_CONSOLIDATION"
    LABOR_PRODUCTIVITY = "LABOR_PRODUCTIVITY"
    FTE_REDUCTION = "FTE_REDUCTION"
    REGSTAFF_PRODUCTIVITY = "REGSTAFF_PRODUCTIVITY"
    # Commercial levers
    PAYER_CONTRACT_REPRICE = "PAYER_CONTRACT_REPRICE"
    ASC_MIGRATION = "ASC_MIGRATION"
    SERVICE_LINE_EXPANSION = "SERVICE_LINE_EXPANSION"
    PHYSICIAN_PRODUCTIVITY = "PHYSICIAN_PRODUCTIVITY"
    # Structural / one-timers
    TUCK_IN_M_AND_A_SYNERGY = "TUCK_IN_M_AND_A_SYNERGY"
    SITE_NEUTRAL_MITIGATION = "SITE_NEUTRAL_MITIGATION"
    MA_CODING_UPLIFT = "MA_CODING_UPLIFT"
    WORKING_CAPITAL_RELEASE = "WORKING_CAPITAL_RELEASE"
    # Catch-all
    OTHER = "OTHER"


@dataclass(frozen=True)
class LeverPrior:
    """Empirical realization distribution for one lever category."""
    category: LeverCategory
    label: str
    realization_median: float            # 1.0 = fully realized
    realization_p25: float
    realization_p75: float
    realization_n_samples: int
    failure_rate: float                  # fraction with realization < 0.5
    duration_months_median: int
    # Target-condition gating: each key is a characteristic name,
    # value is a boost/drag (in pct points of realization) when
    # the condition is met.
    conditional_boosts: Tuple[Tuple[str, float], ...] = ()
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "label": self.label,
            "realization_median": self.realization_median,
            "realization_p25": self.realization_p25,
            "realization_p75": self.realization_p75,
            "realization_n_samples": self.realization_n_samples,
            "failure_rate": self.failure_rate,
            "duration_months_median": self.duration_months_median,
            "conditional_boosts": [
                list(b) for b in self.conditional_boosts
            ],
            "notes": self.notes,
        }


# ────────────────────────────────────────────────────────────────────
# The curated library — refreshed as autopsy library grows
# ────────────────────────────────────────────────────────────────────

LEVER_PRIORS: Tuple[LeverPrior, ...] = (
    LeverPrior(
        category=LeverCategory.DENIAL_WORKFLOW,
        label="Denial workflow overhaul",
        realization_median=0.85, realization_p25=0.45,
        realization_p75=1.05, realization_n_samples=412,
        failure_rate=0.18, duration_months_median=14,
        conditional_boosts=(
            ("denial_rate_over_8pct", 0.12),
            ("denial_rate_over_12pct", 0.20),
            ("has_epic_or_cerner", 0.08),
            ("prior_denial_initiative_failed", -0.25),
        ),
        notes=(
            "Most reliable RCM lever. Realization strongly tied to "
            "starting denial-rate headroom. Deals with <6% initial "
            "denial rate rarely capture >40% of claim."
        ),
    ),
    LeverPrior(
        category=LeverCategory.CODING_INTENSITY,
        label="Coding / CDI uplift",
        realization_median=0.62, realization_p25=0.25,
        realization_p75=0.95, realization_n_samples=381,
        failure_rate=0.28, duration_months_median=10,
        conditional_boosts=(
            ("has_ma_mix_over_40pct", 0.18),
            ("prior_coding_audit_found_gaps", 0.15),
            ("doj_fca_investigation_active", -0.45),
            ("already_top_decile_cmi", -0.30),
        ),
        notes=(
            "Attractive on paper, punished by regulators in "
            "practice. Post-DOJ chart-review focus makes this "
            "lever materially riskier than the bridge suggests."
        ),
    ),
    LeverPrior(
        category=LeverCategory.UNDERPAYMENT_RECOVERY,
        label="Underpayment recovery",
        realization_median=0.72, realization_p25=0.35,
        realization_p75=0.95, realization_n_samples=246,
        failure_rate=0.22, duration_months_median=8,
        conditional_boosts=(
            ("commercial_mix_over_40pct", 0.15),
            ("has_in_house_underpayment_team", -0.18),
        ),
        notes=(
            "One-time recovery effect; realization is high but "
            "not compounding — the lever is front-loaded."
        ),
    ),
    LeverPrior(
        category=LeverCategory.CHARGE_CAPTURE,
        label="Charge capture improvement",
        realization_median=0.55, realization_p25=0.20,
        realization_p75=0.85, realization_n_samples=198,
        failure_rate=0.32, duration_months_median=12,
        notes=(
            "Heavily dependent on clinical-documentation culture. "
            "Targets that have already run a charge-capture "
            "initiative in the last 3 years rarely see meaningful "
            "incremental lift."
        ),
    ),
    LeverPrior(
        category=LeverCategory.AR_AGING_LIQUIDATION,
        label="AR aging liquidation",
        realization_median=0.78, realization_p25=0.40,
        realization_p75=1.00, realization_n_samples=312,
        failure_rate=0.15, duration_months_median=6,
        conditional_boosts=(
            ("days_in_ar_over_55", 0.15),
            ("days_in_ar_under_40", -0.25),
        ),
        notes=(
            "Highly realization-predictable. Diminishes rapidly "
            "after Year 1 — a one-time event, not a compounding "
            "value-creation source."
        ),
    ),
    LeverPrior(
        category=LeverCategory.BAD_DEBT_REDUCTION,
        label="Bad debt reduction",
        realization_median=0.50, realization_p25=0.18,
        realization_p75=0.80, realization_n_samples=189,
        failure_rate=0.35, duration_months_median=16,
        conditional_boosts=(
            ("self_pay_share_over_10pct", 0.12),
            ("hospital_in_low_income_msa", -0.18),
        ),
        notes=(
            "Structural bad-debt is mostly economic — PE buyers "
            "consistently overstate workflow-lever impact on a "
            "metric driven by patient income."
        ),
    ),
    LeverPrior(
        category=LeverCategory.CREDIT_BALANCE_RELEASE,
        label="Credit balance release",
        realization_median=0.92, realization_p25=0.60,
        realization_p75=1.05, realization_n_samples=134,
        failure_rate=0.08, duration_months_median=4,
        notes=(
            "Mechanical one-timer; high realization but non-"
            "compounding. Often double-counted with WC release."
        ),
    ),
    LeverPrior(
        category=LeverCategory.CLEAN_CLAIM_RATE,
        label="Clean claim rate improvement",
        realization_median=0.68, realization_p25=0.30,
        realization_p75=0.95, realization_n_samples=218,
        failure_rate=0.25, duration_months_median=10,
        notes=(
            "Overlaps with denial workflow — banker bridges "
            "frequently double-count. Auditor should cap the "
            "combined denial + clean-claim at the denial lever's "
            "ceiling."
        ),
    ),
    LeverPrior(
        category=LeverCategory.VENDOR_CONSOLIDATION,
        label="Vendor / clearinghouse consolidation",
        realization_median=0.38, realization_p25=0.10,
        realization_p75=0.65, realization_n_samples=263,
        failure_rate=0.42, duration_months_median=18,
        conditional_boosts=(
            ("multi_site_platform_over_5_locations", 0.12),
            ("recent_ehr_migration", -0.20),
        ),
        notes=(
            "Known myth. 42% of deals realize <50% of claim. "
            "Switching costs + change-management friction kill "
            "most vendor-consolidation theses."
        ),
    ),
    LeverPrior(
        category=LeverCategory.LABOR_PRODUCTIVITY,
        label="Revenue-cycle labor productivity",
        realization_median=0.60, realization_p25=0.25,
        realization_p75=0.90, realization_n_samples=301,
        failure_rate=0.30, duration_months_median=14,
        conditional_boosts=(
            ("unionized_workforce", -0.30),
            ("remote_rcm_staff_already", -0.18),
        ),
    ),
    LeverPrior(
        category=LeverCategory.FTE_REDUCTION,
        label="FTE reduction / automation",
        realization_median=0.45, realization_p25=0.15,
        realization_p75=0.80, realization_n_samples=276,
        failure_rate=0.38, duration_months_median=15,
        conditional_boosts=(
            ("unionized_workforce", -0.35),
            ("cfo_tenure_under_18_months", -0.15),
        ),
        notes=(
            "Highly culture-sensitive. Targets with recent "
            "leadership change resist cuts; unionized shops "
            "produce almost nothing on this lever."
        ),
    ),
    LeverPrior(
        category=LeverCategory.REGSTAFF_PRODUCTIVITY,
        label="Registration / pre-service productivity",
        realization_median=0.58, realization_p25=0.25,
        realization_p75=0.85, realization_n_samples=156,
        failure_rate=0.28, duration_months_median=9,
    ),
    LeverPrior(
        category=LeverCategory.PAYER_CONTRACT_REPRICE,
        label="Payer contract repricing",
        realization_median=0.55, realization_p25=0.10,
        realization_p75=0.95, realization_n_samples=223,
        failure_rate=0.34, duration_months_median=18,
        conditional_boosts=(
            ("top_1_payer_share_over_30pct", -0.20),
            ("multi_hospital_system", 0.15),
            ("state_dominant_payer_market", -0.22),
        ),
        notes=(
            "Realization is bimodal: ~50% of deals get material "
            "repricing, ~50% get refused. Dominant-payer markets "
            "(Blues-heavy states) reprice down the target, not up."
        ),
    ),
    LeverPrior(
        category=LeverCategory.ASC_MIGRATION,
        label="ASC / outpatient migration",
        realization_median=0.68, realization_p25=0.30,
        realization_p75=0.98, realization_n_samples=142,
        failure_rate=0.25, duration_months_median=20,
        conditional_boosts=(
            ("hospital_over_200_beds", 0.18),
            ("site_neutral_rule_active", -0.25),
        ),
    ),
    LeverPrior(
        category=LeverCategory.SERVICE_LINE_EXPANSION,
        label="Service line expansion",
        realization_median=0.40, realization_p25=0.10,
        realization_p75=0.75, realization_n_samples=98,
        failure_rate=0.45, duration_months_median=26,
        notes=(
            "Long realization timeline, high execution risk; "
            "most bankers claim year-2 realization while actual "
            "realization is year-3/4 for these levers."
        ),
    ),
    LeverPrior(
        category=LeverCategory.PHYSICIAN_PRODUCTIVITY,
        label="Physician productivity / wRVU",
        realization_median=0.50, realization_p25=0.15,
        realization_p75=0.85, realization_n_samples=204,
        failure_rate=0.34, duration_months_median=14,
        conditional_boosts=(
            ("employed_physician_model", 0.10),
            ("contracted_physician_model", -0.20),
        ),
    ),
    LeverPrior(
        category=LeverCategory.TUCK_IN_M_AND_A_SYNERGY,
        label="Tuck-in M&A synergy",
        realization_median=0.55, realization_p25=0.20,
        realization_p75=0.85, realization_n_samples=178,
        failure_rate=0.30, duration_months_median=16,
        conditional_boosts=(
            ("hsr_expanded_reporting_active", -0.22),
            ("platform_over_10_tuck_ins_history", 0.15),
        ),
    ),
    LeverPrior(
        category=LeverCategory.SITE_NEUTRAL_MITIGATION,
        label="Site-neutral payment mitigation",
        realization_median=0.35, realization_p25=0.08,
        realization_p75=0.60, realization_n_samples=89,
        failure_rate=0.48, duration_months_median=20,
        notes=(
            "Structurally hard — site-neutral rules are not "
            "something a buyer can 'mitigate' via better ops. "
            "Bankers frequently inflate this lever."
        ),
    ),
    LeverPrior(
        category=LeverCategory.MA_CODING_UPLIFT,
        label="Medicare Advantage coding uplift",
        realization_median=0.48, realization_p25=0.10,
        realization_p75=0.82, realization_n_samples=167,
        failure_rate=0.38, duration_months_median=12,
        conditional_boosts=(
            ("v28_rule_finalized", -0.30),
            ("doj_retrospective_chart_review_investigation", -0.40),
        ),
        notes=(
            "Aggressive lever in a tightening regulatory "
            "environment. V28 mechanically caps this lever at "
            "the policy level; the realization prior has fallen "
            "0.15 pp/yr 2022-2026."
        ),
    ),
    LeverPrior(
        category=LeverCategory.WORKING_CAPITAL_RELEASE,
        label="Working capital release",
        realization_median=0.80, realization_p25=0.45,
        realization_p75=1.00, realization_n_samples=145,
        failure_rate=0.15, duration_months_median=8,
        notes=(
            "High realization but one-timer; often already "
            "captured by the seller pre-close (WC peg fight)."
        ),
    ),
    LeverPrior(
        category=LeverCategory.OTHER,
        label="Other / uncategorized",
        realization_median=0.40, realization_p25=0.10,
        realization_p75=0.75, realization_n_samples=0,
        failure_rate=0.40, duration_months_median=18,
        notes=(
            "Uncategorized bridge items receive a conservative "
            "prior. Request the banker to categorize."
        ),
    ),
)


# ────────────────────────────────────────────────────────────────────
# Classifier — maps free-text lever names → category via keyword match
# ────────────────────────────────────────────────────────────────────

_CATEGORY_KEYWORDS: Dict[LeverCategory, Tuple[str, ...]] = {
    LeverCategory.DENIAL_WORKFLOW: (
        "denial", "denials", "appeals", "rejection",
    ),
    LeverCategory.CODING_INTENSITY: (
        "coding", "cdi", "clinical documentation", "dx capture",
        "case mix", "cmi",
    ),
    LeverCategory.UNDERPAYMENT_RECOVERY: (
        "underpayment", "variance", "contract compliance",
    ),
    LeverCategory.CHARGE_CAPTURE: (
        "charge capture", "charge master", "missed charges",
    ),
    LeverCategory.AR_AGING_LIQUIDATION: (
        "ar aging", "aged ar", "ar liquidation", "old receivables",
        "ar days",
    ),
    LeverCategory.BAD_DEBT_REDUCTION: (
        "bad debt", "write-off", "writeoff", "uncompensated",
    ),
    LeverCategory.CREDIT_BALANCE_RELEASE: (
        "credit balance", "credits",
    ),
    LeverCategory.CLEAN_CLAIM_RATE: (
        "clean claim", "first-pass", "first pass", "cc rate",
    ),
    LeverCategory.VENDOR_CONSOLIDATION: (
        "vendor", "clearinghouse", "consolidation", "contract",
        "software", "it systems",
    ),
    LeverCategory.LABOR_PRODUCTIVITY: (
        "labor productivity", "productivity", "efficiency",
    ),
    LeverCategory.FTE_REDUCTION: (
        "fte", "headcount", "automation", "offshore", "outsource",
        "reduction",
    ),
    LeverCategory.REGSTAFF_PRODUCTIVITY: (
        "registration", "pre-service", "front-end", "pre-reg",
    ),
    LeverCategory.PAYER_CONTRACT_REPRICE: (
        "payer contract", "repricing", "reprice", "managed care",
        "commercial reprice", "rate uplift",
    ),
    LeverCategory.ASC_MIGRATION: (
        "asc migration", "outpatient migration", "site of service",
        "site-of-service", "ambulatory",
    ),
    LeverCategory.SERVICE_LINE_EXPANSION: (
        "service line", "new service", "expansion",
    ),
    LeverCategory.PHYSICIAN_PRODUCTIVITY: (
        "physician productivity", "wrvu", "rvus", "provider productivity",
    ),
    LeverCategory.TUCK_IN_M_AND_A_SYNERGY: (
        "tuck-in", "tuck in", "roll-up", "roll up", "m&a", "acquisition",
    ),
    LeverCategory.SITE_NEUTRAL_MITIGATION: (
        "site-neutral", "site neutral", "opps", "facility fee",
    ),
    LeverCategory.MA_CODING_UPLIFT: (
        "ma coding", "risk adjustment", "hcc", "v28", "medicare advantage",
    ),
    LeverCategory.WORKING_CAPITAL_RELEASE: (
        "working capital", "wc release", "wc improvement",
    ),
}


# Specialized categories must beat generic ones when both match.
# Score boost per category: higher = more specific = wins ties.
_CATEGORY_PRIORITY: Dict[LeverCategory, int] = {
    LeverCategory.MA_CODING_UPLIFT: 10,
    LeverCategory.SITE_NEUTRAL_MITIGATION: 10,
    LeverCategory.TUCK_IN_M_AND_A_SYNERGY: 10,
    LeverCategory.ASC_MIGRATION: 10,
    LeverCategory.CLEAN_CLAIM_RATE: 5,
    LeverCategory.UNDERPAYMENT_RECOVERY: 5,
    LeverCategory.AR_AGING_LIQUIDATION: 5,
    LeverCategory.CREDIT_BALANCE_RELEASE: 5,
    LeverCategory.WORKING_CAPITAL_RELEASE: 5,
    LeverCategory.DENIAL_WORKFLOW: 3,
    LeverCategory.REGSTAFF_PRODUCTIVITY: 3,
    LeverCategory.FTE_REDUCTION: 3,
}


def classify_lever(name: str) -> LeverCategory:
    """Keyword-based classifier.  Falls back to OTHER when no
    keyword matches.  Deterministic — same input always produces
    the same category.

    Disambiguation rule: when multiple categories' keywords match,
    we pick by (priority, keyword length) — specialized categories
    (MA_CODING, SITE_NEUTRAL, TUCK_IN) beat generic ones
    (CODING_INTENSITY, FTE_REDUCTION) so "MA HCC coding uplift"
    classifies as MA_CODING_UPLIFT, not CODING_INTENSITY.
    """
    low = (name or "").lower()
    candidates: List[Tuple[int, int, LeverCategory]] = []
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        best_kw_len = 0
        for kw in keywords:
            if kw in low and len(kw) > best_kw_len:
                best_kw_len = len(kw)
        if best_kw_len > 0:
            priority = _CATEGORY_PRIORITY.get(cat, 1)
            candidates.append((priority, best_kw_len, cat))
    if not candidates:
        return LeverCategory.OTHER
    candidates.sort(reverse=True)
    return candidates[0][2]


def prior_for(category: LeverCategory) -> LeverPrior:
    """Lookup prior for a category.  Guaranteed to return — falls
    back to the OTHER prior."""
    for p in LEVER_PRIORS:
        if p.category == category:
            return p
    # Fallback — OTHER is always in the library
    return next(p for p in LEVER_PRIORS if p.category == LeverCategory.OTHER)
