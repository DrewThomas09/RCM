"""Auto-generate the diligence questionnaire for one deal.

Two inputs feed the generator:

1. The list of :class:`RiskFlag`s from :mod:`risk_flags` — each HIGH or
   CRITICAL flag gets a concrete follow-up question that cites the
   triggering number.
2. The completeness assessment — every missing metric ranked by EBITDA
   sensitivity becomes a P0 data request.

On top of those we emit a small set of "always ask" questions covering
contracts, systems, and CDI — the partner's standard homework list.

Design principles:
- **Cite numbers.** Every question that comes from a data pattern
  names the metric, its value, and (when relevant) the benchmark —
  partners want the analyst's conclusion visible in the question, not
  in a separate cell.
- **Prioritize ruthlessly.** P0 = blocker for IC; P1 = confirm before
  signing; P2 = nice-to-have. Flooding the seller with questions is
  an anti-pattern.
- **Deduplicate.** A single metric that triggered both a completeness
  gap and a risk flag produces one question, not two.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from .packet import (
    ComparableSet,
    DiligencePriority,
    DiligenceQuestion,
    HospitalProfile,
    ProfileMetric,
    RiskFlag,
    RiskSeverity,
)
from .completeness import (
    CompletenessAssessment,
    RCM_METRIC_REGISTRY,
    metric_display_name,
)
from .risk_flags import (
    CATEGORY_CODING,
    CATEGORY_DATA_QUALITY,
    CATEGORY_FINANCIAL,
    CATEGORY_OPERATIONAL,
    CATEGORY_PAYER,
    CATEGORY_REGULATORY,
)

logger = logging.getLogger(__name__)


# ── Static "always ask" questions ────────────────────────────────────

# These fire on every deal regardless of what the data says — partner
# standard homework. Keep small; new evergreen questions need
# partner-level sign-off before being added here.
_STANDARD_QUESTIONS: List[Dict[str, Any]] = [
    {
        "question": (
            "Are there any pending payer contract renegotiations or "
            "change-of-control provisions that could affect "
            "post-acquisition revenue?"
        ),
        "category": CATEGORY_PAYER,
        "priority": DiligencePriority.P1,
        "context": (
            "Change-of-control clauses can trigger rate renegotiation "
            "or termination rights — left undiscovered they destroy "
            "the underwriting case."
        ),
        "trigger": "standard",
    },
    {
        "question": (
            "What EHR and billing system(s) are in use? Are there "
            "planned technology transitions?"
        ),
        "category": CATEGORY_OPERATIONAL,
        "priority": DiligencePriority.P1,
        "context": (
            "EHR transitions and billing-system migrations routinely "
            "disrupt cash for 2-3 quarters — the investment committee "
            "needs a heads-up."
        ),
        "trigger": "standard",
    },
    {
        "question": "What is the current CDI program structure and staffing?",
        "category": CATEGORY_CODING,
        "priority": DiligencePriority.P1,
        "context": (
            "Most of our value-creation planning assumes a CDI "
            "program capable of lifting CMI by 0.05-0.10; need to "
            "know the baseline staffing."
        ),
        "trigger": "standard",
    },
    {
        "question": "Provide the charge description master (CDM) for review.",
        "category": CATEGORY_OPERATIONAL,
        "priority": DiligencePriority.P2,
        "context": (
            "Outdated CDMs leak revenue on high-volume service lines. "
            "A clean CDM review is cheap and catches errors that the "
            "operator has stopped noticing."
        ),
        "trigger": "standard",
    },
    {
        "question": (
            "What is the IT contract portfolio (managed services, "
            "outsourced coding, clearinghouse agreements)?"
        ),
        "category": CATEGORY_OPERATIONAL,
        "priority": DiligencePriority.P2,
        "context": (
            "Vendor lock-in on coding or clearinghouse agreements "
            "constrains the operational-improvement playbook; price "
            "the exit fees into the thesis."
        ),
        "trigger": "standard",
    },
]


# ── Flag → question mapping ──────────────────────────────────────────

def _flag_question(flag: RiskFlag) -> Optional[DiligenceQuestion]:
    """Convert one HIGH/CRITICAL risk flag into a concrete follow-up.

    The question text references the specific number that fired the
    flag (e.g., ``"At 14.5% denial rate..."``) — partners want to see
    the analyst's reasoning in the question, not hidden in metadata.
    """
    sev = flag.severity
    if sev not in (RiskSeverity.CRITICAL, RiskSeverity.HIGH):
        return None

    # Map category → question template.
    cat = flag.category
    tv = flag.trigger_value
    value_str = f"{float(tv):.1f}" if tv is not None else "n/a"
    priority = DiligencePriority.P0

    if cat == CATEGORY_OPERATIONAL and "denial_rate" in (flag.trigger_metrics or []):
        return DiligenceQuestion(
            question=(
                f"At {value_str}% denial rate, please provide the root-"
                f"cause breakdown of denials (eligibility, "
                f"authorization, coding, medical necessity, timely "
                f"filing). What denial-management initiatives are "
                f"currently in place? Has an external denial audit "
                f"been conducted in the last 24 months?"
            ),
            category=cat,
            priority=priority,
            trigger=f"denial_rate={value_str}%",
            context=flag.detail,
            trigger_metric="denial_rate",
            trigger_reason=flag.title,
        )

    if cat == CATEGORY_OPERATIONAL and "ar_over_90_pct" in (flag.trigger_metrics or []):
        return DiligenceQuestion(
            question=(
                f"With {value_str}% of A/R over 90 days, provide the "
                f"aging bucket breakdown (0-30 / 31-60 / 61-90 / 91-120"
                f" / 120+) split by payer, plus a sample of the largest "
                f"10 aged accounts and the reason code per bucket."
            ),
            category=cat,
            priority=priority,
            trigger=f"ar_over_90_pct={value_str}%",
            context=flag.detail,
            trigger_metric="ar_over_90_pct",
            trigger_reason=flag.title,
        )

    if cat == CATEGORY_OPERATIONAL and "clean_claim_rate" in (flag.trigger_metrics or []):
        return DiligenceQuestion(
            question=(
                f"Clean claim rate of {value_str}% — what are the top "
                f"three edit failures at front-end (eligibility, "
                f"authorization, registration) and at the clearinghouse"
                f" level? Include volume and dollars per edit category."
            ),
            category=cat,
            priority=priority,
            trigger=f"clean_claim_rate={value_str}%",
            context=flag.detail,
            trigger_metric="clean_claim_rate",
            trigger_reason=flag.title,
        )

    if cat == CATEGORY_REGULATORY and "payer_mix.medicaid" in (flag.trigger_metrics or []):
        return DiligenceQuestion(
            question=(
                f"Medicaid mix at {float(tv or 0.0)*100:.1f}% — what is "
                f"the projected coverage-loss exposure under OBBBA "
                f"work requirements effective Dec 31, 2026? Provide "
                f"enrollment trend by month and a stress scenario "
                f"showing 10% / 20% / 30% Medicaid coverage loss."
            ),
            category=cat,
            priority=DiligencePriority.P0,
            trigger=f"medicaid_pct={float(tv or 0.0)*100:.1f}%",
            context=flag.detail,
            trigger_metric="payer_mix.medicaid",
            trigger_reason=flag.title,
        )

    if cat == CATEGORY_PAYER and (flag.trigger_metric or "").startswith("payer_mix."):
        payer = (flag.trigger_metric or "").split(".", 1)[-1]
        return DiligenceQuestion(
            question=(
                f"{payer} represents {float(tv or 0.0)*100:.1f}% of net "
                f"revenue — provide the rate sheet, renewal schedule, "
                f"change-of-control provisions, and most recent three "
                f"years of rate escalators for that contract."
            ),
            category=cat,
            priority=DiligencePriority.P0,
            trigger=f"{flag.trigger_metric}={float(tv or 0.0)*100:.1f}%",
            context=flag.detail,
            trigger_metric=flag.trigger_metric,
            trigger_reason=flag.title,
        )

    if cat == CATEGORY_PAYER and "denial_rate_medicare_advantage" in (flag.trigger_metrics or []):
        return DiligenceQuestion(
            question=(
                f"Medicare Advantage denial rate at {value_str}% — "
                f"which MA plans are driving the volume? What "
                f"percentage of MA denials go through pre-"
                f"authorization AI tools (e.g., naviHealth, Cohere, "
                f"OptumRx)? Provide appeal overturn rate by MA plan."
            ),
            category=cat,
            priority=DiligencePriority.P0,
            trigger=f"denial_rate_medicare_advantage={value_str}%",
            context=flag.detail,
            trigger_metric="denial_rate_medicare_advantage",
            trigger_reason=flag.title,
        )

    if cat == CATEGORY_CODING and "case_mix_index" in (flag.trigger_metrics or []):
        return DiligenceQuestion(
            question=(
                f"CMI of {value_str} is below the comparable P25 "
                f"— provide documentation review samples, CDI "
                f"staffing (FTEs per 100 beds), query rate, and "
                f"query response rate. Include CMI trend by service "
                f"line for the last 24 months."
            ),
            category=cat,
            priority=DiligencePriority.P0,
            trigger=f"case_mix_index={value_str}",
            context=flag.detail,
            trigger_metric="case_mix_index",
            trigger_reason=flag.title,
        )

    if cat == CATEGORY_FINANCIAL and "current_ebitda" in (flag.trigger_metrics or []):
        return DiligenceQuestion(
            question=(
                "Current EBITDA is negative — provide the three-year "
                "EBITDA trend by major service line, fixed vs variable "
                "cost breakdown, and management's bridge-to-"
                "profitability plan including any cost-out initiatives "
                "already in motion."
            ),
            category=cat,
            priority=DiligencePriority.P0,
            trigger="current_ebitda<0",
            context=flag.detail,
            trigger_metric="current_ebitda",
            trigger_reason=flag.title,
        )

    if cat == CATEGORY_FINANCIAL and "ebitda_margin" in (flag.trigger_metrics or []):
        return DiligenceQuestion(
            question=(
                f"EBITDA margin of {value_str}% — provide a cost "
                f"breakdown by department and a three-year margin "
                f"trend. Which cost lines are management actively "
                f"managing?"
            ),
            category=cat,
            priority=DiligencePriority.P0,
            trigger=f"ebitda_margin={value_str}%",
            context=flag.detail,
            trigger_metric="ebitda_margin",
            trigger_reason=flag.title,
        )

    if cat == CATEGORY_DATA_QUALITY:
        return DiligenceQuestion(
            question=(
                "Request 24 months of RCM scorecard data covering "
                "denial volumes, days in A/R, cash collections, and "
                "clean-claim rate. Include payer-split where available."
            ),
            category=cat,
            priority=DiligencePriority.P0,
            trigger=flag.title,
            context=flag.detail,
            trigger_metric=flag.trigger_metric,
            trigger_reason=flag.title,
        )

    # Generic fallback — use the flag's detail as context.
    return DiligenceQuestion(
        question=(
            f"Please provide additional context on the '{flag.title}' "
            f"finding: underlying drivers, operator awareness, and "
            f"any remediation actions currently in motion."
        ),
        category=cat,
        priority=DiligencePriority.P0 if sev == RiskSeverity.CRITICAL
                 else DiligencePriority.P1,
        trigger=flag.title,
        context=flag.detail,
        trigger_metric=flag.trigger_metric,
        trigger_reason=flag.title,
    )


# ── Missing-metric questions ────────────────────────────────────────

def _missing_metric_question(
    metric_key: str,
    sensitivity_rank: int,
) -> DiligenceQuestion:
    display = metric_display_name(metric_key)
    meta = RCM_METRIC_REGISTRY.get(metric_key, {})
    category_map = {
        "denials": CATEGORY_OPERATIONAL,
        "collections": CATEGORY_OPERATIONAL,
        "ar": CATEGORY_OPERATIONAL,
        "claims": CATEGORY_OPERATIONAL,
        "coding": CATEGORY_CODING,
        "financial": CATEGORY_FINANCIAL,
    }
    cat = category_map.get(meta.get("category", ""), CATEGORY_OPERATIONAL)
    return DiligenceQuestion(
        question=(
            f"Please provide {display} data for the last 36 months. "
            f"This metric has the #{sensitivity_rank} highest impact "
            f"on EBITDA valuation among RCM KPIs."
        ),
        category=cat,
        priority=DiligencePriority.P0,
        trigger=f"missing:{metric_key}",
        context=(
            f"{display} is unobserved; without it the regression layer "
            f"falls back to benchmark P50 and the EBITDA bridge loses "
            f"this lever."
        ),
        trigger_metric=metric_key,
        trigger_reason=f"missing {display}",
    )


# ── Payer / data-breakout questions ─────────────────────────────────

def _payer_breakdown_gap_questions(
    rcm_profile: Dict[str, ProfileMetric],
) -> List[DiligenceQuestion]:
    """If denial_rate is present but payer-specific breakdowns aren't,
    ask for them. Same for reason codes.
    """
    out: List[DiligenceQuestion] = []
    payer_keys = [
        "denial_rate_medicare_ffs",
        "denial_rate_medicare_advantage",
        "denial_rate_commercial",
        "denial_rate_medicaid",
    ]
    has_parent = "denial_rate" in rcm_profile
    has_any_child = any(k in rcm_profile for k in payer_keys)
    if has_parent and not has_any_child:
        out.append(DiligenceQuestion(
            question=(
                "Please provide denial rates broken out by payer "
                "class (Medicare FFS, Medicare Advantage, Commercial, "
                "Medicaid). Include both claim count and dollar basis."
            ),
            category=CATEGORY_PAYER,
            priority=DiligencePriority.P0,
            trigger="missing:payer-specific-denials",
            context=(
                "Overall denial rate obscures which payer is driving "
                "the problem; remediation planning needs the split."
            ),
            # Distinct trigger_metric from the parent so dedup keeps
            # this question separate from any denial_rate risk flag.
            trigger_metric="denial_rate.payer_breakdown",
            trigger_reason="missing payer breakdown",
        ))

    reason_keys = [
        "denial_rate_eligibility",
        "denial_rate_authorization",
        "denial_rate_coding",
        "denial_rate_medical_necessity",
        "denial_rate_timely_filing",
    ]
    has_any_reason = any(k in rcm_profile for k in reason_keys)
    if has_parent and not has_any_reason:
        out.append(DiligenceQuestion(
            question=(
                "Please provide denial volumes by CARC/RARC reason "
                "code for the last 12 months."
            ),
            category=CATEGORY_OPERATIONAL,
            priority=DiligencePriority.P0,
            trigger="missing:denial-reason-codes",
            context=(
                "Reason-code breakdown drives the denial-management "
                "playbook; without it the remediation plan is a guess."
            ),
            trigger_metric="denial_rate.reason_codes",
            trigger_reason="missing reason-code breakdown",
        ))

    return out


# ── Outlier questions ───────────────────────────────────────────────

def _outlier_questions(
    rcm_profile: Dict[str, ProfileMetric],
    comparables: Optional[ComparableSet],
) -> List[DiligenceQuestion]:
    """For any metric >2σ from the comparable cohort mean."""
    out: List[DiligenceQuestion] = []
    if comparables is None or not comparables.peers:
        return out
    # Pool comparable values per metric.
    peer_values: Dict[str, List[float]] = {}
    for p in comparables.peers:
        for k, v in (p.fields or {}).items():
            try:
                peer_values.setdefault(k, []).append(float(v))
            except (TypeError, ValueError):
                continue
    for metric, pm in rcm_profile.items():
        pool = peer_values.get(metric)
        if not pool or len(pool) < 5:
            continue
        mean = sum(pool) / len(pool)
        # Population sd — no scipy.
        var = sum((x - mean) ** 2 for x in pool) / len(pool)
        sd = var ** 0.5
        if sd <= 1e-9:
            continue
        z = abs(pm.value - mean) / sd
        if z >= 2.0:
            out.append(DiligenceQuestion(
                question=(
                    f"Hospital's {metric_display_name(metric)} "
                    f"({pm.value:.2f}) is {z:.1f}σ from the comparable "
                    f"mean ({mean:.2f}). Please explain drivers and "
                    f"provide 24-month trend data."
                ),
                category=CATEGORY_OPERATIONAL,
                priority=DiligencePriority.P1,
                trigger=f"outlier:{metric}",
                context=(
                    f"Benchmark deviation that large is rarely "
                    f"explained by the reported variables alone."
                ),
                trigger_metric=metric,
                trigger_reason=f"{z:.1f}σ from cohort mean",
            ))
    return out


# ── Public entry point ──────────────────────────────────────────────

_PRIORITY_RANK = {
    DiligencePriority.P0: 0,
    DiligencePriority.P1: 1,
    DiligencePriority.P2: 2,
}


def generate_diligence_questions(
    profile: HospitalProfile,
    rcm_profile: Dict[str, ProfileMetric],
    risk_flags: List[RiskFlag],
    completeness: Optional[CompletenessAssessment],
    comparables: Optional[ComparableSet] = None,
) -> List[DiligenceQuestion]:
    """Compose the full diligence questionnaire.

    Dedup strategy: we key on ``trigger_metric`` + ``priority`` so a
    metric that both is missing (P0) and drove a risk flag (P0) only
    produces one question — the risk-flag version (which cites the
    specific value).
    """
    questions: List[DiligenceQuestion] = []
    seen_triggers: Set[str] = set()

    def _add(q: Optional[DiligenceQuestion]) -> None:
        if q is None or not q.question:
            return
        # Dedup key: the (metric, priority) pair. Trigger strings
        # differ so we don't dedup on trigger alone.
        key = f"{q.trigger_metric or ''}|{q.priority.value}"
        if key in seen_triggers:
            return
        seen_triggers.add(key)
        questions.append(q)

    # 1. Risk-flag-derived questions first (they carry specific numbers).
    for flag in sorted(risk_flags or [], key=lambda f: (
            0 if f.severity == RiskSeverity.CRITICAL else
            1 if f.severity == RiskSeverity.HIGH else 2,
            f.category,
    )):
        _add(_flag_question(flag))

    # 2. Missing-metric P0s, ranked by EBITDA sensitivity.
    if completeness is not None:
        for rank, metric_key in enumerate(completeness.missing_ranked_by_sensitivity[:5], start=1):
            _add(_missing_metric_question(metric_key, rank))

    # 3. Payer / reason-code breakout gaps.
    for q in _payer_breakdown_gap_questions(rcm_profile):
        _add(q)

    # 4. Benchmark outliers (P1).
    for q in _outlier_questions(rcm_profile, comparables):
        _add(q)

    # 5. Standard "always-ask" questions.
    for spec in _STANDARD_QUESTIONS:
        _add(DiligenceQuestion(
            question=spec["question"],
            category=spec["category"],
            priority=spec["priority"],
            trigger=spec["trigger"],
            context=spec["context"],
            trigger_metric="__standard__" + spec["question"][:40],
        ))

    questions.sort(key=lambda q: (_PRIORITY_RANK.get(q.priority, 9), q.category))
    # Strip the internal ``__standard__`` trigger markers before
    # returning so clients never see them.
    for q in questions:
        if (q.trigger_metric or "").startswith("__standard__"):
            q.trigger_metric = None
    return questions
