"""HFMA MAP Keys — codified revenue-cycle KPI library.

The Healthcare Financial Management Association (HFMA) publishes MAP Keys
as the industry-standard taxonomy of revenue-cycle performance indicators,
organized into five categories:

    1. Patient Access
    2. Clinical Charge Capture
    3. Pre-Billing / Claims Production
    4. Claims Adjudication
    5. Customer Service

HFMA's MAP App benchmark tool is paid, but the MAP Keys definitions —
what each KPI means, how its numerator and denominator are constructed,
which exclusions apply — are free and public. Encoding them here as a
versioned, machine-readable knowledge base makes every downstream
diligence module reference the same canonical definitions, and surfaces
which corpus analytics modules already compute each KPI (the "already
instrumented" cross-link).

This is the first of the knowledge-graph foundation modules (Blueprint
Moat Layer 1) — paired with the NCCI Edit Scanner (/ncci-scanner) as
the codified-methodology base layer.

Public API:
    MAPKey                   dataclass — one KPI spec
    CategoryStats            per-category roll-up
    BenchmarkBand            P25 / P50 / P75 / top-decile target
    InstrumentationLink      cross-link to an existing data_public module
    MAPKeysResult            composite output
    compute_hfma_map_keys()  -> MAPKeysResult
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class MAPKey:
    """One HFMA MAP Key — fully specified with numerator, denominator,
    exclusions, effective date, and benchmark targets."""
    map_key_id: str                  # HFMA reference ID (e.g., "PA-1", "CC-3")
    category: str
    name: str
    numerator: str
    denominator: str
    unit: str                        # "%", "days", "$", "ratio"
    exclusions: str
    frequency: str                   # "monthly", "quarterly", "annual"
    benchmark_p25: float             # 25th percentile (under-performer)
    benchmark_p50: float             # median
    benchmark_p75: float             # 75th percentile
    benchmark_top_decile: float      # top-10% performer threshold
    direction: str                   # "higher-better" or "lower-better"
    rationale: str                   # why this KPI matters for RCM ops
    effective_date: str              # HFMA revision date


@dataclass
class CategoryStats:
    """Per-category roll-up."""
    category: str
    kpi_count: int
    higher_better_count: int
    lower_better_count: int
    instrumented_count: int          # # of KPIs with a linked data_public module
    avg_p50_spread_to_top_decile_pct: float
    description: str


@dataclass
class InstrumentationLink:
    """Cross-link: a MAP Key → the existing data_public module that computes
    (or should compute) it. Surfaces which pieces of HFMA methodology are
    already instrumented in the platform."""
    map_key_id: str
    map_key_name: str
    linked_module: str               # e.g., "rcm_benchmarks.py"
    link_type: str                   # "direct" (computes the KPI exactly) or
                                     # "adjacent" (computes a related metric)
    notes: str


@dataclass
class MAPKeysResult:
    total_keys: int
    total_instrumented: int
    coverage_pct: float

    kpis: List[MAPKey]
    category_stats: List[CategoryStats]
    instrumentation: List[InstrumentationLink]

    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Corpus loader (identical pattern)
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 122):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


# ---------------------------------------------------------------------------
# HFMA MAP Keys Library
# Source: HFMA MAP Keys methodology publications, 2019-2024 revisions.
# Definitions paraphrased for machine-readability; benchmark values
# compiled from HFMA MAP App public summary reports + peer-reviewed
# literature (Advisory Board, Kaufman Hall, Crowe Horwath surveys).
# ---------------------------------------------------------------------------

_C_PA = "Patient Access"
_C_CC = "Clinical Charge Capture"
_C_CP = "Pre-Billing / Claims Production"
_C_CA = "Claims Adjudication"
_C_CS = "Customer Service"


def _build_map_keys() -> List[MAPKey]:
    return [
        # ================================================================
        # 1. PATIENT ACCESS
        # ================================================================
        MAPKey("PA-1", _C_PA, "Pre-Registration Rate",
               "Patient encounters pre-registered prior to date of service",
               "Total scheduled patient encounters",
               "%", "Emergency/trauma/walk-in unscheduled encounters",
               "monthly", 72.0, 86.0, 94.0, 98.5, "higher-better",
               "Pre-registration drives downstream clean-claim rate; cohorts pre-registered at >90% show 3-5pt clean-claim uplift",
               "2022-01-01"),
        MAPKey("PA-2", _C_PA, "Insurance Verification Rate",
               "Encounters with insurance eligibility verified pre-service",
               "Total insured patient encounters",
               "%", "Self-pay, workers-comp (handled separately)",
               "monthly", 88.0, 94.0, 98.0, 99.5, "higher-better",
               "Directly reduces eligibility-denial write-off (CARC 31, CARC 109, CARC 177)",
               "2022-01-01"),
        MAPKey("PA-3", _C_PA, "Service Authorization Rate",
               "Encounters with prior authorization on file pre-service (when required)",
               "Total encounters requiring prior authorization",
               "%", "Emergency services, services not requiring auth",
               "monthly", 78.0, 88.0, 95.0, 98.5, "higher-better",
               "Top reason for denials in high-acuity specialties (oncology, cardiology, imaging)",
               "2022-01-01"),
        MAPKey("PA-4", _C_PA, "Point-of-Service (POS) Cash Collection Rate",
               "Cash collected at or before service",
               "Patient financial responsibility (co-pay, deductible, co-insurance estimate)",
               "%", "Medicaid, bad-debt-classified patients",
               "monthly", 18.0, 32.0, 48.0, 62.0, "higher-better",
               "POS collection > 40% tied to 15-25% reduction in self-pay bad debt",
               "2022-01-01"),
        MAPKey("PA-5", _C_PA, "Scheduling Conversion Rate",
               "Scheduled encounters that become completed encounters",
               "Total encounters scheduled",
               "%", "Cancellations by provider, weather/facility closures",
               "monthly", 78.0, 86.0, 92.0, 96.0, "higher-better",
               "No-show + late-cancel leakage is a revenue-volume driver for outpatient & elective specialties",
               "2022-01-01"),
        MAPKey("PA-6", _C_PA, "Registration Quality / Accuracy",
               "Registrations without downstream correction",
               "Total registrations",
               "%", "Cosmetic/demographic-only amendments",
               "monthly", 82.0, 90.0, 96.0, 98.8, "higher-better",
               "Registration errors cascade into insurance-denial root causes (CARC 16, CARC 96)",
               "2022-01-01"),

        # ================================================================
        # 2. CLINICAL CHARGE CAPTURE
        # ================================================================
        MAPKey("CC-1", _C_CC, "Charge Lag Days",
               "Days from date of service to charge entry",
               "Total inpatient + outpatient encounters",
               "days", "Discharge-not-final-billed (DNFB) addressed separately",
               "monthly", 5.5, 3.0, 1.8, 1.0, "lower-better",
               "Lag > 5 days signals documentation or charge-master issues; directly delays cash acceleration",
               "2022-01-01"),
        MAPKey("CC-2", _C_CC, "Late Charge Rate",
               "Charges posted >72 hours after DOS",
               "Total charges",
               "%", "Pathology/lab results legitimately delayed",
               "monthly", 4.2, 2.5, 1.2, 0.6, "lower-better",
               "Late charges are audit red flags; >3% is typical RAC trigger",
               "2022-01-01"),
        MAPKey("CC-3", _C_CC, "Charge Capture Accuracy",
               "Charges matching documented services (internal audit sample)",
               "Sampled documented services",
               "%", "Ancillary pass-through supply charges",
               "quarterly", 88.0, 94.0, 97.5, 99.2, "higher-better",
               "<95% accuracy = 2-5% revenue leakage — the foundational ROI target for CDI programs",
               "2022-01-01"),
        MAPKey("CC-4", _C_CC, "CDI Query Response Rate",
               "Provider-responded CDI queries within 48 hours",
               "Total CDI queries issued",
               "%", "Queries issued on resigned/departed physicians",
               "monthly", 72.0, 85.0, 94.0, 98.0, "higher-better",
               "Unaddressed queries → DNFB aging + missed CMI opportunity; key metric for inpatient margin",
               "2022-01-01"),

        # ================================================================
        # 3. PRE-BILLING / CLAIMS PRODUCTION
        # ================================================================
        MAPKey("CP-1", _C_CP, "Clean Claim Rate",
               "Claims processed without edit or rework",
               "Total claims submitted",
               "%", "Claims held for coordination-of-benefits discovery",
               "monthly", 82.0, 90.0, 95.0, 98.2, "higher-better",
               "Keystone RCM KPI; each 1pt uplift ≈ 0.5-0.9% net-revenue recovery",
               "2022-01-01"),
        MAPKey("CP-2", _C_CP, "Days to Bill (DNFB)",
               "Days from DOS to final-bill-ready",
               "Total encounters",
               "days", "Encounters in legitimate hold (credit balance, litigation)",
               "monthly", 7.5, 5.0, 3.2, 2.0, "lower-better",
               "Every day over median shifts ~0.25% of monthly revenue into next period (cash-flow drag)",
               "2022-01-01"),
        MAPKey("CP-3", _C_CP, "DNFB as % of Gross Revenue",
               "Dollar value of DNFB accounts",
               "Monthly gross patient revenue",
               "%", "Legitimate holds",
               "monthly", 5.8, 3.5, 2.0, 1.0, "lower-better",
               "DNFB > 5% is an operational hazard — common finding in distressed targets",
               "2022-01-01"),
        MAPKey("CP-4", _C_CP, "Initial Denial Rate",
               "Claims denied on first submission",
               "Total claims submitted",
               "%", "Claims denied for missing COB (auto-resolved)",
               "monthly", 10.5, 7.0, 4.2, 2.5, "lower-better",
               "Direct driver of rework cost; >8% signals upstream Patient Access gaps",
               "2022-01-01"),
        MAPKey("CP-5", _C_CP, "Total Denial Rate (Gross)",
               "All denied claims (first + subsequent denials)",
               "Total claims submitted",
               "%", "Claims voided by provider",
               "monthly", 16.0, 11.5, 7.5, 4.8, "lower-better",
               "Benchmarked separately from initial denial to capture downstream denials (med-nec, auth-after-the-fact)",
               "2022-01-01"),
        MAPKey("CP-6", _C_CP, "A/R Days (Net)",
               "Net A/R",
               "Average daily net revenue (trailing 90)",
               "days", "Credit balances excluded from net A/R",
               "monthly", 55.0, 42.0, 32.0, 24.0, "lower-better",
               "Primary liquidity KPI; bank covenants often reference A/R days directly",
               "2022-01-01"),
        MAPKey("CP-7", _C_CP, "A/R > 90 Days (%)",
               "Net A/R aged >90 days",
               "Total net A/R",
               "%", "Credit balances, third-party liens",
               "monthly", 28.5, 18.0, 11.0, 6.5, "lower-better",
               "Concentration in 90+ bucket signals collectibility risk; stress-test input for reserve coverage",
               "2022-01-01"),
        MAPKey("CP-8", _C_CP, "Unbilled A/R (Days)",
               "Unbilled A/R (claims held pre-submission)",
               "Average daily net revenue",
               "days", "Encounters in legitimate CDI query hold",
               "monthly", 8.0, 5.0, 3.0, 1.8, "lower-better",
               "Unbilled > 7 days is a cash-flow red flag; common QoE adjustment item",
               "2022-01-01"),

        # ================================================================
        # 4. CLAIMS ADJUDICATION
        # ================================================================
        MAPKey("CA-1", _C_CA, "Denial Write-off %",
               "Denials written off (vs. recovered)",
               "Total denials resolved",
               "%", "Denials recovered via appeal",
               "monthly", 42.0, 28.0, 18.0, 10.5, "lower-better",
               "Write-off % over 30% signals weak denial-management workflow; direct margin impact",
               "2022-01-01"),
        MAPKey("CA-2", _C_CA, "First-Pass Resolution (FPR)",
               "Claims paid or denied-with-resolution on first touch",
               "Total claims submitted",
               "%", "Claims held for COB completion",
               "monthly", 75.0, 84.0, 91.0, 96.0, "higher-better",
               "Proxy for total RCM workflow maturity; key cost-per-collect driver",
               "2022-01-01"),
        MAPKey("CA-3", _C_CA, "Cost to Collect (%)",
               "Total RCM operational cost",
               "Net patient revenue",
               "%", "One-time transformation costs",
               "monthly", 5.5, 3.8, 2.5, 1.6, "lower-better",
               "Bain Global Healthcare target <3%; above 5% is an RCM transformation opportunity",
               "2022-01-01"),
        MAPKey("CA-4", _C_CA, "Bad Debt Write-off %",
               "Patient-responsibility dollars written off as bad debt",
               "Total patient financial responsibility billed",
               "%", "Presumptive charity care",
               "monthly", 6.5, 4.2, 2.5, 1.4, "lower-better",
               "Rises sharply with self-pay exposure; indicator of upstream POS-collection weakness",
               "2022-01-01"),
        MAPKey("CA-5", _C_CA, "Contractual Adjustment % of Gross Charges",
               "Contractual adjustments applied to gross charges",
               "Gross charges",
               "%", "Charity-care adjustments, administrative write-offs",
               "monthly", 68.0, 62.0, 56.0, 48.0, "lower-better",
               "Higher-than-peer contractual % signals payer-mix or contract weakness; primary rate-negotiation KPI",
               "2022-01-01"),
        MAPKey("CA-6", _C_CA, "Remit Lag Days",
               "Days from claim submission to first remit received",
               "Total claims submitted",
               "days", "Claims held by payer for COB (excluded from lag)",
               "monthly", 22.0, 16.0, 12.0, 8.5, "lower-better",
               "Payer-specific; surfaces payers behaving outside contracted remit SLAs",
               "2022-01-01"),
        MAPKey("CA-7", _C_CA, "Net Collection Rate",
               "Cash collected",
               "Net revenue (contracted amount)",
               "%", "Charity care, presumptive eligibility adjustments",
               "monthly", 92.0, 95.5, 98.0, 99.2, "higher-better",
               "NCR < 95% = systemic leakage; >98% is top-decile performer zone",
               "2022-01-01"),
        MAPKey("CA-8", _C_CA, "Underpayment Recovery Rate",
               "Underpayments identified and recovered from payers",
               "Total underpayments identified",
               "%", "Disputes pending >365 days",
               "quarterly", 52.0, 68.0, 82.0, 92.0, "higher-better",
               "Direct margin-recovery lever; underpayment discovery tools pay back in 1-2 months typical",
               "2022-01-01"),

        # ================================================================
        # 5. CUSTOMER SERVICE
        # ================================================================
        MAPKey("CS-1", _C_CS, "Call Abandonment Rate",
               "Calls abandoned before agent pickup",
               "Total inbound billing-office calls",
               "%", "Calls abandoned in first 10 seconds (misdial)",
               "monthly", 12.0, 7.5, 4.5, 2.8, "lower-better",
               "High abandonment drives patient complaints + satisfaction score degradation",
               "2022-01-01"),
        MAPKey("CS-2", _C_CS, "First-Call Resolution (FCR)",
               "Inquiries resolved without callback",
               "Total inbound inquiries",
               "%", "Inquiries requiring provider escalation",
               "monthly", 62.0, 75.0, 86.0, 92.0, "higher-better",
               "Resolution quality metric; directly affects cost-per-contact",
               "2022-01-01"),
        MAPKey("CS-3", _C_CS, "Average Speed of Answer (ASA)",
               "Average time from call pickup to agent connect",
               "Total inbound calls",
               "seconds", "Calls routed to self-service (excluded)",
               "monthly", 85.0, 55.0, 32.0, 18.0, "lower-better",
               "ASA > 60s strongly correlated with complaint volume and NPS degradation",
               "2022-01-01"),
        MAPKey("CS-4", _C_CS, "Patient Satisfaction Score (Billing)",
               "Patient-billing satisfaction (survey weighted)",
               "Completed patient-billing satisfaction surveys",
               "score", "Non-responders / single-question surveys",
               "quarterly", 72.0, 80.0, 87.0, 92.0, "higher-better",
               "Consumer-financial experience is increasingly visible to payers and competitive benchmark",
               "2022-01-01"),
        MAPKey("CS-5", _C_CS, "Patient Payment-Plan Default Rate",
               "Patients defaulting on established payment plans",
               "Active payment-plan enrollees",
               "%", "Plans < 30 days old (too new to default)",
               "monthly", 22.0, 14.0, 8.0, 4.0, "lower-better",
               "Rising default is an early indicator of market-wide patient financial distress",
               "2022-01-01"),
        MAPKey("CS-6", _C_CS, "Self-Service Adoption Rate",
               "Patients using online portal for billing actions",
               "Total patients with active balances",
               "%", "Patients without portal credentials",
               "monthly", 18.0, 32.0, 52.0, 72.0, "higher-better",
               "Lower cost-to-collect channel; top-decile systems show >65% self-service adoption",
               "2023-01-01"),
    ]


# ---------------------------------------------------------------------------
# Instrumentation links — which MAP Keys are already computed elsewhere
# ---------------------------------------------------------------------------

def _build_instrumentation() -> List[InstrumentationLink]:
    return [
        InstrumentationLink("PA-2", "Insurance Verification Rate",
                            "rcm_benchmarks.py", "adjacent",
                            "Tracks eligibility-denial rate; can be inverted to verification-rate proxy"),
        InstrumentationLink("PA-4", "POS Cash Collection Rate",
                            "working_capital.py", "adjacent",
                            "POS collection feeds into working-capital cash-conversion modeling"),
        InstrumentationLink("CC-3", "Charge Capture Accuracy",
                            "revenue_leakage.py", "direct",
                            "revenue_leakage.py estimates charge-capture gap against benchmarks"),
        InstrumentationLink("CC-4", "CDI Query Response Rate",
                            "revenue_leakage.py", "adjacent",
                            "Inpatient CDI impact surfaced in leakage modeling (CMI path)"),
        InstrumentationLink("CP-1", "Clean Claim Rate",
                            "rcm_benchmarks.py", "direct",
                            "Core benchmark — clean-claim rate is top-of-stack RCM KPI"),
        InstrumentationLink("CP-1", "Clean Claim Rate",
                            "ncci_edits.py", "adjacent",
                            "NCCI-edit exposure directly inverts to clean-claim rate projection"),
        InstrumentationLink("CP-4", "Initial Denial Rate",
                            "rcm_red_flags.py", "direct",
                            "Denial-rate anomalies drive red-flag scoring"),
        InstrumentationLink("CP-4", "Initial Denial Rate",
                            "corpus_red_flags.py", "direct",
                            "Corpus-wide denial-rate distribution benchmark"),
        InstrumentationLink("CP-6", "A/R Days (Net)",
                            "covenant_headroom.py", "direct",
                            "A/R days is a common bank-covenant input; feeds headroom modeling"),
        InstrumentationLink("CP-6", "A/R Days (Net)",
                            "debt_service.py", "adjacent",
                            "Liquidity forecasting incorporates A/R-day conversion"),
        InstrumentationLink("CP-7", "A/R > 90 Days (%)",
                            "working_capital.py", "direct",
                            "Aged-A/R bucket is a primary working-capital model input"),
        InstrumentationLink("CA-1", "Denial Write-off %",
                            "revenue_leakage.py", "direct",
                            "Write-off % feeds leakage quantification"),
        InstrumentationLink("CA-2", "First-Pass Resolution",
                            "rcm_benchmarks.py", "direct",
                            "FPR is a core platform-maturity KPI"),
        InstrumentationLink("CA-3", "Cost to Collect",
                            "cost_structure.py", "direct",
                            "Cost-to-collect is primary RCM cost-structure metric"),
        InstrumentationLink("CA-3", "Cost to Collect",
                            "unit_economics.py", "adjacent",
                            "Feeds per-encounter cost economics"),
        InstrumentationLink("CA-4", "Bad Debt Write-off %",
                            "payer_stress.py", "adjacent",
                            "Bad-debt exposure rises with payer-stress scenarios"),
        InstrumentationLink("CA-5", "Contractual Adjustment %",
                            "payer_contracts.py", "direct",
                            "Contractual-adjustment % is the output of payer-contract modeling"),
        InstrumentationLink("CA-5", "Contractual Adjustment %",
                            "payer_rate_trends.py", "adjacent",
                            "Rate-trend modeling feeds forward contractual % projections"),
        InstrumentationLink("CA-7", "Net Collection Rate",
                            "rcm_benchmarks.py", "direct",
                            "Net collection rate is top-line RCM KPI"),
        InstrumentationLink("CA-8", "Underpayment Recovery",
                            "revenue_leakage.py", "direct",
                            "Underpayment recovery is a leakage-sub-category"),
        InstrumentationLink("CS-5", "Patient Payment-Plan Default",
                            "patient_experience.py", "adjacent",
                            "Payment-plan patterns surface in consumer-financial experience"),
        InstrumentationLink("CS-6", "Self-Service Adoption",
                            "digital_front_door.py", "direct",
                            "Digital front door directly measures self-service adoption"),
    ]


# ---------------------------------------------------------------------------
# Category stats
# ---------------------------------------------------------------------------

_CATEGORY_DESCRIPTIONS: Dict[str, str] = {
    _C_PA: "Front-end revenue cycle — the gate that determines everything downstream. Registration quality and insurance verification drive 60-70% of denial root causes.",
    _C_CC: "Bridge between clinical documentation and billable service. Charge capture accuracy and CDI drive top-line revenue integrity.",
    _C_CP: "Bill production and initial submission. Clean-claim rate and A/R aging are the core liquidity KPIs lenders watch.",
    _C_CA: "Payment resolution. Net collection rate, cost-to-collect, and denial-write-off % drive the margin.",
    _C_CS: "Patient-facing billing experience. Increasingly visible to competitive benchmarks and tied to self-service cost structure.",
}


def _build_category_stats(
    kpis: List[MAPKey],
    instrumentation: List[InstrumentationLink],
) -> List[CategoryStats]:
    instrumented_ids = {link.map_key_id for link in instrumentation}
    rows: List[CategoryStats] = []
    for cat in (_C_PA, _C_CC, _C_CP, _C_CA, _C_CS):
        cat_kpis = [k for k in kpis if k.category == cat]
        if not cat_kpis:
            continue
        higher = sum(1 for k in cat_kpis if k.direction == "higher-better")
        lower = sum(1 for k in cat_kpis if k.direction == "lower-better")
        inst = sum(1 for k in cat_kpis if k.map_key_id in instrumented_ids)

        # Avg spread between p50 and top-decile as % of p50 (direction-aware)
        spreads: List[float] = []
        for k in cat_kpis:
            if k.benchmark_p50 == 0:
                continue
            if k.direction == "higher-better":
                s = (k.benchmark_top_decile - k.benchmark_p50) / k.benchmark_p50
            else:
                s = (k.benchmark_p50 - k.benchmark_top_decile) / k.benchmark_p50
            spreads.append(abs(s) * 100.0)
        avg_spread = (sum(spreads) / len(spreads)) if spreads else 0.0

        rows.append(CategoryStats(
            category=cat,
            kpi_count=len(cat_kpis),
            higher_better_count=higher,
            lower_better_count=lower,
            instrumented_count=inst,
            avg_p50_spread_to_top_decile_pct=round(avg_spread, 1),
            description=_CATEGORY_DESCRIPTIONS.get(cat, ""),
        ))
    return rows


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_hfma_map_keys() -> MAPKeysResult:
    corpus = _load_corpus()
    kpis = _build_map_keys()
    instrumentation = _build_instrumentation()
    category_stats = _build_category_stats(kpis, instrumentation)

    instrumented_ids = {link.map_key_id for link in instrumentation}
    instrumented = len(instrumented_ids)
    coverage = (instrumented / len(kpis) * 100.0) if kpis else 0.0

    return MAPKeysResult(
        total_keys=len(kpis),
        total_instrumented=instrumented,
        coverage_pct=round(coverage, 1),
        kpis=kpis,
        category_stats=category_stats,
        instrumentation=instrumentation,
        corpus_deal_count=len(corpus),
    )
