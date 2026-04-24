"""Curated 36-item RCM due-diligence checklist.

Organized by phase (screening → benchmarks → predictive → risk →
financial → deliverable → manual). Each item is a partner-
readable question plus metadata driving auto-completion.

The checklist is deliberately exhaustive — a partner can hide
items they don't care about, but they shouldn't discover missing
coverage the morning of IC. Every P0 item must be addressed
before IC; P1 items should have an assigned owner + target date
even when not yet done.

``auto_check_key`` is a free-form string the tracker uses to
decide whether an observable in :class:`DealObservations`
satisfies the item. The tracker maintains the mapping — items
just declare intent here.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple


class Priority(str, Enum):
    """Partner-facing priority."""
    P0 = "P0"   # must-have, blocks IC
    P1 = "P1"   # should-have, typically blocks IC without owner
    P2 = "P2"   # nice-to-have, post-close work


class Owner(str, Enum):
    """Default owner bucket for the item."""
    ANALYST = "ANALYST"
    PARTNER = "PARTNER"
    LEGAL = "LEGAL"
    EXTERNAL = "EXTERNAL"       # banker / seller-side advisor / 3rd-party firm
    MANAGEMENT = "MANAGEMENT"   # seller management answering a question


class Category(str, Enum):
    """Functional grouping — drives the dashboard layout."""
    SCREENING = "SCREENING"
    INGEST = "INGEST"
    BENCHMARKS = "BENCHMARKS"
    PREDICTIVE = "PREDICTIVE"
    RISK = "RISK"
    FINANCIAL = "FINANCIAL"
    MARKET = "MARKET"
    DELIVERABLE = "DELIVERABLE"
    MANUAL = "MANUAL"


@dataclass(frozen=True)
class ChecklistItem:
    """One diligence question with auto-completion linkage."""
    item_id: str
    phase: int                         # 1..5 (screening → IC)
    category: Category
    priority: Priority
    question: str
    default_owner: Owner
    # Free-form key the tracker uses to match against
    # DealObservations fields. None = manual-only item.
    auto_check_key: Optional[str] = None
    # Deep-link to the analytic page that covers this item.
    # Rendered as "Open →" in the checklist UI.
    evidence_url: Optional[str] = None
    # Partner-facing guidance on what "done" means.
    completion_criteria: str = ""


# ────────────────────────────────────────────────────────────────────
# The lattice — 36 items across 5 phases
# ────────────────────────────────────────────────────────────────────

CHECKLIST_ITEMS: Tuple[ChecklistItem, ...] = (
    # ─── Phase 1: Pre-NDA screening ─────────────────────────────────
    ChecklistItem(
        item_id="scan_bankruptcy_survivor",
        phase=1, category=Category.SCREENING, priority=Priority.P0,
        question="Has the Bankruptcy-Survivor Scan been run against "
                 "the 12 named failure patterns?",
        default_owner=Owner.ANALYST,
        auto_check_key="bankruptcy_scan_run",
        evidence_url="/screening/bankruptcy-survivor",
        completion_criteria=(
            "Scan has produced a verdict (GREEN / YELLOW / RED / "
            "CRITICAL) with the matching pattern list."
        ),
    ),
    ChecklistItem(
        item_id="scan_deal_autopsy",
        phase=1, category=Category.SCREENING, priority=Priority.P0,
        question="Has a historical-analog signature match been run "
                 "(Deal Autopsy)?",
        default_owner=Owner.ANALYST,
        auto_check_key="deal_autopsy_run",
        evidence_url="/diligence/deal-autopsy",
        completion_criteria=(
            "Top-3 historical matches identified, with similarity "
            "% and named partner lessons."
        ),
    ),
    ChecklistItem(
        item_id="scan_sector_sentiment",
        phase=1, category=Category.SCREENING, priority=Priority.P1,
        question="Is the sector sentiment from the market-intel feed "
                 "consistent with the deal thesis?",
        default_owner=Owner.ANALYST,
        auto_check_key="sector_sentiment_reviewed",
        evidence_url="/market-intel",
        completion_criteria=(
            "Sector's trailing-30-day sentiment rolled up and either "
            "confirmed or reconciled against the thesis."
        ),
    ),

    # ─── Phase 2: CCD ingestion + HFMA benchmarks ───────────────────
    ChecklistItem(
        item_id="ingest_ccd",
        phase=2, category=Category.INGEST, priority=Priority.P0,
        question="Has the Canonical Claims Dataset been ingested from "
                 "the seller's 837/835 files?",
        default_owner=Owner.ANALYST,
        auto_check_key="ccd_ingested",
        evidence_url="/diligence/ingest",
        completion_criteria=(
            "CCD builds without ERROR-severity transformation log "
            "entries; claim count matches seller-reported volume."
        ),
    ),
    ChecklistItem(
        item_id="benchmark_days_in_ar",
        phase=2, category=Category.BENCHMARKS, priority=Priority.P0,
        question="Days in A/R benchmarked against HFMA peer median?",
        default_owner=Owner.ANALYST,
        auto_check_key="hfma_days_in_ar_computed",
        evidence_url="/diligence/benchmarks",
        completion_criteria=(
            "HFMA band (top quartile ≤35d / median 45d / bottom "
            "quartile ≥55d) identified, with peer-delta computed."
        ),
    ),
    ChecklistItem(
        item_id="benchmark_denial_rate",
        phase=2, category=Category.BENCHMARKS, priority=Priority.P0,
        question="First-pass denial rate benchmarked against HFMA "
                 "peer median?",
        default_owner=Owner.ANALYST,
        auto_check_key="hfma_denial_rate_computed",
        evidence_url="/diligence/benchmarks",
        completion_criteria=(
            "FPDR computed on CCD; HFMA band (top quartile ≤5% / "
            "median 10% / bottom quartile ≥15%) identified."
        ),
    ),
    ChecklistItem(
        item_id="benchmark_ar_aging",
        phase=2, category=Category.BENCHMARKS, priority=Priority.P0,
        question="A/R aging > 90 days benchmarked?",
        default_owner=Owner.ANALYST,
        auto_check_key="hfma_ar_aging_computed",
        evidence_url="/diligence/benchmarks",
        completion_criteria=(
            "A/R aging bucket > 90 days computed with peer-delta."
        ),
    ),
    ChecklistItem(
        item_id="benchmark_cost_to_collect",
        phase=2, category=Category.BENCHMARKS, priority=Priority.P1,
        question="Cost to collect benchmarked against HFMA peer "
                 "median?",
        default_owner=Owner.ANALYST,
        auto_check_key="hfma_cost_to_collect_computed",
        evidence_url="/diligence/benchmarks",
    ),
    ChecklistItem(
        item_id="benchmark_net_revenue_realization",
        phase=2, category=Category.BENCHMARKS, priority=Priority.P0,
        question="Net revenue realization benchmarked?",
        default_owner=Owner.ANALYST,
        auto_check_key="hfma_nrr_computed",
        evidence_url="/diligence/benchmarks",
    ),
    ChecklistItem(
        item_id="benchmark_cohort_liquidation",
        phase=2, category=Category.BENCHMARKS, priority=Priority.P1,
        question="Cohort liquidation curve computed (shows cohort "
                 "censoring + liquidation tail)?",
        default_owner=Owner.ANALYST,
        auto_check_key="cohort_liquidation_computed",
        evidence_url="/diligence/benchmarks",
    ),
    ChecklistItem(
        item_id="benchmark_denial_pareto",
        phase=2, category=Category.BENCHMARKS, priority=Priority.P1,
        question="Denial Pareto root-cause table produced?",
        default_owner=Owner.ANALYST,
        auto_check_key="denial_pareto_computed",
        evidence_url="/diligence/root-cause",
    ),
    ChecklistItem(
        item_id="benchmark_qor_waterfall",
        phase=2, category=Category.BENCHMARKS, priority=Priority.P0,
        question="Quality-of-Revenue waterfall reconciliation run "
                 "against management revenue?",
        default_owner=Owner.ANALYST,
        auto_check_key="qor_waterfall_computed",
        evidence_url="/diligence/benchmarks",
        completion_criteria=(
            "Total divergence status (IMMATERIAL / MATERIAL / "
            "CRITICAL) produced; per-payer-class divergence visible."
        ),
    ),

    # ─── Phase 2b: Predictive RCM analytics ─────────────────────────
    ChecklistItem(
        item_id="predictive_denial_model",
        phase=2, category=Category.PREDICTIVE, priority=Priority.P0,
        question="Claim-level denial prediction model trained and "
                 "calibrated?",
        default_owner=Owner.ANALYST,
        auto_check_key="denial_prediction_run",
        evidence_url="/diligence/denial-prediction",
        completion_criteria=(
            "Per-claim Naive Bayes model has AUC > 0.60; systematic "
            "misses flagged and quantified in $."
        ),
    ),
    ChecklistItem(
        item_id="predictive_physician_attrition",
        phase=2, category=Category.PREDICTIVE, priority=Priority.P0,
        question="Physician flight-risk (P-PAM) scored across the "
                 "roster?",
        default_owner=Owner.ANALYST,
        auto_check_key="physician_attrition_run",
        evidence_url="/diligence/physician-attrition",
        completion_criteria=(
            "Per-provider probability + band + retention-bond "
            "recommendation produced for every CRITICAL / HIGH "
            "provider."
        ),
    ),

    # ─── Phase 3: Risk workbench (Tier 1-3) ─────────────────────────
    ChecklistItem(
        item_id="risk_cpom",
        phase=3, category=Category.RISK, priority=Priority.P1,
        question="Corporate Practice of Medicine (CPOM) state "
                 "exposure assessed?",
        default_owner=Owner.LEGAL,
        auto_check_key="cpom_run",
        evidence_url="/diligence/risk-workbench?demo=steward",
    ),
    ChecklistItem(
        item_id="risk_nsa",
        phase=3, category=Category.RISK, priority=Priority.P0,
        question="No Surprises Act exposure assessed (OON share + "
                 "IDR arbitration exposure)?",
        default_owner=Owner.ANALYST,
        auto_check_key="nsa_run",
        evidence_url="/diligence/risk-workbench?demo=steward",
    ),
    ChecklistItem(
        item_id="risk_steward",
        phase=3, category=Category.RISK, priority=Priority.P0,
        question="Real-estate Steward Score computed (sale-leaseback "
                 "risk + EBITDAR coverage)?",
        default_owner=Owner.ANALYST,
        auto_check_key="steward_run",
        evidence_url="/diligence/risk-workbench?demo=steward",
    ),
    ChecklistItem(
        item_id="risk_team",
        phase=3, category=Category.RISK, priority=Priority.P1,
        question="TEAM (CMS Transforming Episode Accountability) "
                 "exposure reviewed?",
        default_owner=Owner.ANALYST,
        auto_check_key="team_run",
    ),
    ChecklistItem(
        item_id="risk_antitrust",
        phase=3, category=Category.RISK, priority=Priority.P0,
        question="Antitrust / HHI concentration check for the "
                 "target's footprint?",
        default_owner=Owner.LEGAL,
        auto_check_key="antitrust_run",
    ),
    ChecklistItem(
        item_id="risk_cyber",
        phase=3, category=Category.RISK, priority=Priority.P0,
        question="Cyber posture composite + BI-loss estimate "
                 "produced?",
        default_owner=Owner.ANALYST,
        auto_check_key="cyber_run",
        evidence_url="/diligence/risk-workbench?demo=steward",
    ),
    ChecklistItem(
        item_id="risk_ma_v28",
        phase=3, category=Category.RISK, priority=Priority.P0,
        question="Medicare Advantage V28 recalibration impact "
                 "computed?",
        default_owner=Owner.ANALYST,
        auto_check_key="ma_v28_run",
    ),
    ChecklistItem(
        item_id="risk_physician_comp_fmv",
        phase=3, category=Category.RISK, priority=Priority.P0,
        question="Physician comp benchmarked against FMV p25/p50/p75 "
                 "+ Stark red-lines checked?",
        default_owner=Owner.LEGAL,
        auto_check_key="physician_comp_fmv_run",
    ),
    ChecklistItem(
        item_id="risk_labor_referral",
        phase=3, category=Category.RISK, priority=Priority.P1,
        question="Labor + referral leakage reviewed (synthetic FTE, "
                 "wage inflation, referral concentration)?",
        default_owner=Owner.ANALYST,
        auto_check_key="labor_referral_run",
    ),
    ChecklistItem(
        item_id="risk_patient_pay",
        phase=3, category=Category.RISK, priority=Priority.P2,
        question="Patient-pay + reputational overlays reviewed?",
        default_owner=Owner.ANALYST,
        auto_check_key="patient_pay_run",
    ),

    # ─── Phase 4: Financial synthesis ───────────────────────────────
    ChecklistItem(
        item_id="fin_ebitda_bridge",
        phase=4, category=Category.FINANCIAL, priority=Priority.P0,
        question="EBITDA bridge with 7 levers built "
                 "(denial reduction, coding uplift, contract yield, "
                 "WC optimization, labor inflation, reg-headwind, "
                 "cyber reserve)?",
        default_owner=Owner.ANALYST,
        auto_check_key="ebitda_bridge_built",
        evidence_url="/diligence/ebitda-bridge",
    ),
    ChecklistItem(
        item_id="fin_deal_mc",
        phase=4, category=Category.FINANCIAL, priority=Priority.P0,
        question="Deal Monte Carlo run (3000 trials, 5-year forward "
                 "MOIC/IRR distribution, variance attribution, "
                 "sensitivity tornado)?",
        default_owner=Owner.ANALYST,
        auto_check_key="deal_mc_run",
        evidence_url="/diligence/deal-mc",
    ),
    ChecklistItem(
        item_id="fin_counterfactual",
        phase=4, category=Category.FINANCIAL, priority=Priority.P0,
        question="Counterfactual Advisor — offer-shape modifications "
                 "to flip every RED/CRITICAL finding?",
        default_owner=Owner.PARTNER,
        auto_check_key="counterfactual_run",
        evidence_url="/diligence/counterfactual",
    ),
    ChecklistItem(
        item_id="fin_market_intel",
        phase=4, category=Category.MARKET, priority=Priority.P1,
        question="Public-operator comps + transaction multiples "
                 "pulled for the target's category?",
        default_owner=Owner.ANALYST,
        auto_check_key="market_intel_run",
        evidence_url="/market-intel",
    ),
    ChecklistItem(
        item_id="fin_working_capital_peg",
        phase=4, category=Category.FINANCIAL, priority=Priority.P1,
        question="Normalised working-capital target estimated + "
                 "reconciled to seller's proposed peg?",
        default_owner=Owner.ANALYST,
    ),

    # ─── Phase 5: Partner deliverables ──────────────────────────────
    ChecklistItem(
        item_id="deliver_qoe",
        phase=5, category=Category.DELIVERABLE, priority=Priority.P0,
        question="Quality-of-Earnings memo drafted and reviewed?",
        default_owner=Owner.PARTNER,
        auto_check_key="qoe_memo_generated",
        evidence_url="/diligence/qoe-memo",
    ),
    ChecklistItem(
        item_id="deliver_ic_packet",
        phase=5, category=Category.DELIVERABLE, priority=Priority.P0,
        question="IC Packet assembled (12 sections with partner "
                 "synthesis + walkaway + open questions)?",
        default_owner=Owner.PARTNER,
        auto_check_key="ic_packet_assembled",
        evidence_url="/diligence/ic-packet",
    ),

    # ─── Manual items (always manual-owned) ─────────────────────────
    ChecklistItem(
        item_id="manual_mgmt_references",
        phase=3, category=Category.MANUAL, priority=Priority.P1,
        question="Management team reference calls (CEO / CFO / "
                 "RCM-ops director) completed?",
        default_owner=Owner.PARTNER,
        completion_criteria=(
            "Minimum 3 references per C-suite executive; discrepancy "
            "with management narrative flagged in memo."
        ),
    ),
    ChecklistItem(
        item_id="manual_legal_review",
        phase=3, category=Category.MANUAL, priority=Priority.P0,
        question="Seller legal review — corporate structure, equity "
                 "rollover, reps + warranties — signed off?",
        default_owner=Owner.LEGAL,
        completion_criteria=(
            "External counsel has delivered the legal diligence memo "
            "with no unresolved P0 items."
        ),
    ),
    ChecklistItem(
        item_id="manual_commercial_contract_review",
        phase=3, category=Category.MANUAL, priority=Priority.P0,
        question="Commercial payer contract review — top-5 payer "
                 "contracts' carveouts, escalators, termination "
                 "clauses, auto-renewal?",
        default_owner=Owner.LEGAL,
        completion_criteria=(
            "External counsel has reviewed the top-5 commercial "
            "payer contracts and produced a term-sheet summary."
        ),
    ),
    ChecklistItem(
        item_id="manual_real_estate_title",
        phase=3, category=Category.MANUAL, priority=Priority.P1,
        question="Real estate title + environmental + survey report "
                 "for every owned facility?",
        default_owner=Owner.EXTERNAL,
    ),
    ChecklistItem(
        item_id="manual_seller_disclosure",
        phase=3, category=Category.MANUAL, priority=Priority.P1,
        question="Seller disclosure schedule review — pending "
                 "litigation, regulatory audits, DOJ/OIG matters?",
        default_owner=Owner.LEGAL,
    ),
    # ─── Automated items linking new diligence modules ─────────────
    ChecklistItem(
        item_id="regulatory_calendar_scan",
        phase=3, category=Category.RISK, priority=Priority.P0,
        question="Has the Regulatory Calendar × Thesis Kill-Switch "
                 "been run to map upcoming CMS / OIG / FTC / DOJ / "
                 "NSA-IDR events to the target's thesis drivers?",
        default_owner=Owner.ANALYST,
        auto_check_key="regulatory_calendar_run",
        evidence_url="/diligence/regulatory-calendar",
        completion_criteria=(
            "Kill-switch verdict produced, EBITDA overlay computed, "
            "driver timelines ordered by first-kill date."
        ),
    ),
    ChecklistItem(
        item_id="covenant_stress_simulation",
        phase=4, category=Category.FINANCIAL, priority=Priority.P0,
        question="Has the Covenant & Capital Stack Stress Lab been "
                 "run to quantify per-quarter covenant-breach "
                 "probability and equity-cure sizing?",
        default_owner=Owner.ANALYST,
        auto_check_key="covenant_stress_run",
        evidence_url="/diligence/covenant-stress",
        completion_criteria=(
            "Breach probability curves across hold, 50 %-first-at "
            "quarter identified, median + P75 equity cure sized."
        ),
    ),
    ChecklistItem(
        item_id="hcris_peer_xray",
        phase=1, category=Category.SCREENING, priority=Priority.P0,
        question="Has the HCRIS-Native Peer X-Ray benchmarked the "
                 "target against 25-50 filed Medicare cost reports?",
        default_owner=Owner.ANALYST,
        auto_check_key="hcris_xray_run",
        evidence_url="/diligence/hcris-xray",
        completion_criteria=(
            "Target vs peer P25/median/P75 on 15 derived RCM / "
            "cost / margin / payer-mix metrics, 3-year trend "
            "direction confirmed."
        ),
    ),
    ChecklistItem(
        item_id="payer_mix_stress",
        phase=3, category=Category.RISK, priority=Priority.P1,
        question="Has the Payer Mix Stress Lab stress-tested the "
                 "target's commercial + government payer portfolio?",
        default_owner=Owner.ANALYST,
        auto_check_key="payer_stress_run",
        evidence_url="/diligence/payer-stress",
        completion_criteria=(
            "Per-payer rate-shock MC complete, Top-1 concentration "
            "below 40 %, P10 cumulative NPR drag sized."
        ),
    ),
)


def build_checklist() -> List[ChecklistItem]:
    """Return a list copy so callers can safely sort/filter."""
    return list(CHECKLIST_ITEMS)
