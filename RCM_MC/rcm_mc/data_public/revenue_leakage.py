"""Revenue Leakage Analyzer — denials, underpayment, coding gaps, charge capture.

Quantifies every dollar that should have been collected but wasn't.
Core RCM diligence deliverable:
- Initial denial rate and final write-off
- Underpayment vs contracted rate
- Charge capture / missing CPTs
- Modifier misuse (Modifier 25 red flag)
- Bad-debt on self-pay and patient liability
- Timely filing write-offs
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Sector leakage benchmarks (% of revenue)
# ---------------------------------------------------------------------------

_SECTOR_LEAKAGE = {
    "Physician Services": {"initial_denial": 0.125, "final_writeoff": 0.045, "underpayment": 0.018,
                           "charge_capture_gap": 0.012, "bad_debt": 0.024, "timely_filing": 0.004},
    "Dermatology":        {"initial_denial": 0.098, "final_writeoff": 0.032, "underpayment": 0.022,
                           "charge_capture_gap": 0.018, "bad_debt": 0.022, "timely_filing": 0.003},
    "Orthopedics":        {"initial_denial": 0.148, "final_writeoff": 0.058, "underpayment": 0.025,
                           "charge_capture_gap": 0.015, "bad_debt": 0.028, "timely_filing": 0.005},
    "Gastroenterology":   {"initial_denial": 0.135, "final_writeoff": 0.048, "underpayment": 0.020,
                           "charge_capture_gap": 0.014, "bad_debt": 0.022, "timely_filing": 0.004},
    "Ophthalmology":      {"initial_denial": 0.110, "final_writeoff": 0.040, "underpayment": 0.019,
                           "charge_capture_gap": 0.015, "bad_debt": 0.020, "timely_filing": 0.003},
    "ASC":                {"initial_denial": 0.155, "final_writeoff": 0.062, "underpayment": 0.032,
                           "charge_capture_gap": 0.010, "bad_debt": 0.025, "timely_filing": 0.006},
    "Home Health":        {"initial_denial": 0.195, "final_writeoff": 0.072, "underpayment": 0.028,
                           "charge_capture_gap": 0.008, "bad_debt": 0.018, "timely_filing": 0.008},
    "Hospice":            {"initial_denial": 0.140, "final_writeoff": 0.055, "underpayment": 0.022,
                           "charge_capture_gap": 0.006, "bad_debt": 0.010, "timely_filing": 0.005},
    "Skilled Nursing":    {"initial_denial": 0.185, "final_writeoff": 0.068, "underpayment": 0.035,
                           "charge_capture_gap": 0.012, "bad_debt": 0.020, "timely_filing": 0.010},
    "Behavioral Health":  {"initial_denial": 0.168, "final_writeoff": 0.062, "underpayment": 0.025,
                           "charge_capture_gap": 0.015, "bad_debt": 0.032, "timely_filing": 0.006},
    "ABA Therapy":        {"initial_denial": 0.138, "final_writeoff": 0.054, "underpayment": 0.022,
                           "charge_capture_gap": 0.010, "bad_debt": 0.030, "timely_filing": 0.005},
    "Radiology":          {"initial_denial": 0.148, "final_writeoff": 0.058, "underpayment": 0.028,
                           "charge_capture_gap": 0.016, "bad_debt": 0.022, "timely_filing": 0.006},
    "Laboratory":         {"initial_denial": 0.162, "final_writeoff": 0.065, "underpayment": 0.030,
                           "charge_capture_gap": 0.008, "bad_debt": 0.020, "timely_filing": 0.008},
    "Urgent Care":        {"initial_denial": 0.118, "final_writeoff": 0.042, "underpayment": 0.020,
                           "charge_capture_gap": 0.020, "bad_debt": 0.055, "timely_filing": 0.004},
    "Cardiology":         {"initial_denial": 0.140, "final_writeoff": 0.052, "underpayment": 0.024,
                           "charge_capture_gap": 0.012, "bad_debt": 0.022, "timely_filing": 0.005},
    "Oncology":           {"initial_denial": 0.165, "final_writeoff": 0.062, "underpayment": 0.028,
                           "charge_capture_gap": 0.010, "bad_debt": 0.018, "timely_filing": 0.007},
    "Dialysis":           {"initial_denial": 0.175, "final_writeoff": 0.065, "underpayment": 0.038,
                           "charge_capture_gap": 0.004, "bad_debt": 0.014, "timely_filing": 0.009},
    "Dental":             {"initial_denial": 0.085, "final_writeoff": 0.028, "underpayment": 0.015,
                           "charge_capture_gap": 0.015, "bad_debt": 0.040, "timely_filing": 0.002},
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class LeakageBucket:
    category: str
    description: str
    annual_leakage_pct: float
    annual_leakage_mm: float
    recoverable_pct: float
    recoverable_mm: float
    benchmark_best_pct: float
    gap_vs_best_mm: float


@dataclass
class DenialReason:
    reason_code: str
    name: str
    pct_of_denials: float
    recovery_rate: float
    annual_impact_mm: float


@dataclass
class PayerLeakage:
    payer: str
    denial_rate: float
    underpayment_rate: float
    total_leakage_mm: float
    top_reason: str


@dataclass
class RecoveryInitiative:
    initiative: str
    target_bucket: str
    expected_recovery_mm: float
    one_time_cost_mm: float
    annual_cost_mm: float
    timeline_months: int
    roi: float
    priority: str


@dataclass
class RevenueLeakageResult:
    sector: str
    gross_charges_mm: float
    net_revenue_mm: float
    total_leakage_mm: float
    total_leakage_pct: float
    recoverable_mm: float
    buckets: List[LeakageBucket]
    denial_reasons: List[DenialReason]
    payer_leakage: List[PayerLeakage]
    initiatives: List[RecoveryInitiative]
    net_recovery_yr1_mm: float
    annualized_ebitda_uplift_mm: float
    ev_impact_mm: float
    corpus_deal_count: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 66):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    try:
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS, EXTENDED_SEED_DEALS
        deals = _SEED_DEALS + EXTENDED_SEED_DEALS + deals
    except Exception:
        pass
    return deals


def _get_profile(sector: str) -> Dict:
    return _SECTOR_LEAKAGE.get(sector, _SECTOR_LEAKAGE["Physician Services"])


def _build_buckets(sector: str, net_revenue_mm: float) -> List[LeakageBucket]:
    p = _get_profile(sector)
    # Best-in-class: 50% of sector median
    best = {k: v * 0.50 for k, v in p.items()}

    items = [
        ("Initial Denials (Unappealed)", "Claims denied at first submission, never reworked",
         p["initial_denial"] * 0.35, 0.65, best["initial_denial"] * 0.35),
        ("Final Write-offs", "Uncollectable after denial/appeal process",
         p["final_writeoff"], 0.35, best["final_writeoff"]),
        ("Contractual Underpayment", "Paid below negotiated rate; requires variance analytics",
         p["underpayment"], 0.80, best["underpayment"]),
        ("Charge Capture Gaps", "Services delivered but not billed (EHR-charge master disconnect)",
         p["charge_capture_gap"], 0.75, best["charge_capture_gap"]),
        ("Bad Debt / Self-Pay", "Patient liability, high-deductible accounts",
         p["bad_debt"], 0.28, best["bad_debt"]),
        ("Timely Filing Write-offs", "Claims filed after payer deadline",
         p["timely_filing"], 0.92, best["timely_filing"]),
        ("Coding Downcoding", "E/M level downcoded by payer or under-coded by provider",
         0.008, 0.55, 0.003),
        ("Modifier Misuse", "Mod 25/59/51 errors causing denials",
         0.005, 0.70, 0.002),
    ]
    rows = []
    for cat, desc, pct, recov, best_pct in items:
        leak_mm = net_revenue_mm * pct
        recov_mm = leak_mm * recov
        gap_vs_best = (pct - best_pct) * net_revenue_mm
        rows.append(LeakageBucket(
            category=cat,
            description=desc,
            annual_leakage_pct=round(pct, 4),
            annual_leakage_mm=round(leak_mm, 2),
            recoverable_pct=round(recov, 3),
            recoverable_mm=round(recov_mm, 2),
            benchmark_best_pct=round(best_pct, 4),
            gap_vs_best_mm=round(max(0, gap_vs_best), 2),
        ))
    return rows


def _build_denials(net_revenue_mm: float, denial_rate: float) -> List[DenialReason]:
    denial_volume = net_revenue_mm * denial_rate
    reasons = [
        ("CO-22", "Coordination of Benefits / COB", 0.18, 0.72),
        ("CO-96", "Non-covered Charges", 0.12, 0.28),
        ("CO-197", "Prior Auth Required", 0.16, 0.55),
        ("CO-16", "Claim/Service Missing Info", 0.11, 0.82),
        ("CO-109", "Not Covered by Payer", 0.08, 0.18),
        ("CO-150", "Payer Deemed Info Inadequate", 0.09, 0.70),
        ("CO-45", "Charges Exceed Fee Schedule", 0.10, 0.15),
        ("CO-29", "Timely Filing", 0.06, 0.08),
        ("CO-23", "Prior Payer Adjudication", 0.05, 0.65),
        ("Other", "Various", 0.05, 0.40),
    ]
    rows = []
    for code, name, pct, recov in reasons:
        impact = denial_volume * pct * (1 - recov)
        rows.append(DenialReason(
            reason_code=code, name=name,
            pct_of_denials=round(pct, 3),
            recovery_rate=round(recov, 3),
            annual_impact_mm=round(impact, 2),
        ))
    return rows


def _build_payer_leakage(net_revenue_mm: float) -> List[PayerLeakage]:
    payers = [
        ("Commercial (Aggregated)", 0.08, 0.022, "CO-22 COB", 0.48),
        ("Medicare FFS", 0.06, 0.015, "CO-16 Missing Info", 0.20),
        ("Medicare Advantage", 0.14, 0.028, "CO-197 Prior Auth", 0.12),
        ("Medicaid FFS", 0.16, 0.032, "CO-150 Info Inadequate", 0.08),
        ("Medicaid Managed", 0.18, 0.036, "CO-197 Prior Auth", 0.07),
        ("Self-Pay / Patient", 0.08, 0.001, "Bad Debt", 0.05),
    ]
    rows = []
    for payer, denial_r, underpay_r, top_reason, rev_pct in payers:
        revenue_share = net_revenue_mm * rev_pct
        leakage = revenue_share * (denial_r + underpay_r)
        rows.append(PayerLeakage(
            payer=payer,
            denial_rate=round(denial_r, 3),
            underpayment_rate=round(underpay_r, 3),
            total_leakage_mm=round(leakage, 2),
            top_reason=top_reason,
        ))
    return rows


def _build_initiatives(
    net_revenue_mm: float, buckets: List[LeakageBucket], ebitda_margin: float,
    exit_multiple: float,
) -> List[RecoveryInitiative]:
    total_recoverable = sum(b.recoverable_mm for b in buckets)

    items = [
        ("Denial Management Team + Tech", "Initial Denials (Unappealed)",
         total_recoverable * 0.18, 0.25, 0.65, 4, "high"),
        ("Charge Capture Automation (EHR integration)", "Charge Capture Gaps",
         total_recoverable * 0.12, 0.45, 0.12, 6, "high"),
        ("Contract Management / Underpayment Analytics", "Contractual Underpayment",
         total_recoverable * 0.22, 0.18, 0.22, 3, "high"),
        ("Self-Pay Patient Engagement Platform", "Bad Debt / Self-Pay",
         total_recoverable * 0.08, 0.15, 0.18, 5, "medium"),
        ("Prior Auth Workflow Automation", "Initial Denials (Unappealed)",
         total_recoverable * 0.14, 0.35, 0.15, 8, "medium"),
        ("Coding Quality Program (CDI)", "Coding Downcoding",
         total_recoverable * 0.09, 0.22, 0.28, 9, "medium"),
        ("Payer Credentialing / Roster Audit", "Final Write-offs",
         total_recoverable * 0.07, 0.08, 0.04, 3, "high"),
        ("Modifier Governance Program", "Modifier Misuse",
         total_recoverable * 0.05, 0.04, 0.06, 2, "low"),
    ]
    rows = []
    for init, bucket, rec, one_time, annual, months, prio in items:
        # ROI: net recovery year 1 / total investment year 1
        year1_net = rec - annual - (one_time * 0.5)
        roi = year1_net / (one_time + annual) if (one_time + annual) else 0
        rows.append(RecoveryInitiative(
            initiative=init,
            target_bucket=bucket,
            expected_recovery_mm=round(rec, 2),
            one_time_cost_mm=round(one_time, 2),
            annual_cost_mm=round(annual, 2),
            timeline_months=months,
            roi=round(roi, 1),
            priority=prio,
        ))
    return rows


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_revenue_leakage(
    sector: str = "Physician Services",
    net_revenue_mm: float = 80.0,
    ebitda_margin: float = 0.18,
    exit_multiple: float = 11.0,
) -> RevenueLeakageResult:
    corpus = _load_corpus()
    profile = _get_profile(sector)

    gross_charges = net_revenue_mm / (1 - 0.45)   # Rough: 45% contractual adjustment

    buckets = _build_buckets(sector, net_revenue_mm)
    total_leakage = sum(b.annual_leakage_mm for b in buckets)
    total_recoverable = sum(b.recoverable_mm for b in buckets)

    denials = _build_denials(net_revenue_mm, profile["initial_denial"])
    payer_leak = _build_payer_leakage(net_revenue_mm)
    initiatives = _build_initiatives(net_revenue_mm, buckets, ebitda_margin, exit_multiple)

    # Year 1 net recovery: high-priority initiatives, 65% realization
    high_init = [i for i in initiatives if i.priority == "high"]
    yr1_recovery = sum(i.expected_recovery_mm for i in high_init) * 0.65
    yr1_cost = sum(i.annual_cost_mm + i.one_time_cost_mm * 0.8 for i in high_init)
    yr1_net = yr1_recovery - yr1_cost

    # Annualized uplift (steady-state, all initiatives)
    ss_recovery = total_recoverable * 0.70
    ss_cost = sum(i.annual_cost_mm for i in initiatives)
    annual_ebitda_uplift = ss_recovery - ss_cost

    ev_impact = annual_ebitda_uplift * exit_multiple

    return RevenueLeakageResult(
        sector=sector,
        gross_charges_mm=round(gross_charges, 1),
        net_revenue_mm=round(net_revenue_mm, 1),
        total_leakage_mm=round(total_leakage, 2),
        total_leakage_pct=round(total_leakage / net_revenue_mm, 4),
        recoverable_mm=round(total_recoverable, 2),
        buckets=buckets,
        denial_reasons=denials,
        payer_leakage=payer_leak,
        initiatives=initiatives,
        net_recovery_yr1_mm=round(yr1_net, 2),
        annualized_ebitda_uplift_mm=round(annual_ebitda_uplift, 2),
        ev_impact_mm=round(ev_impact, 1),
        corpus_deal_count=len(corpus),
    )
