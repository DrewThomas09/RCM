"""Zero-Based Budgeting / Waste Elimination Tracker.

Tracks ZBB cost-baseline rebuild and savings capture for PE platforms
undergoing operational transformation. Diligence-grade view into which
cost lines are locked, which are under-managed, and where incremental
savings remain.
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import List


@dataclass
class CostCategory:
    category: str
    pre_zbb_mm: float
    current_run_rate_mm: float
    target_run_rate_mm: float
    savings_captured_mm: float
    savings_potential_mm: float
    pct_of_revenue: float
    benchmark_pct: float


@dataclass
class SavingsInitiative:
    initiative: str
    category: str
    annualized_target_mm: float
    captured_ltm_mm: float
    capture_rate_pct: float
    owner: str
    status: str


@dataclass
class WasteAudit:
    waste_type: str
    description: str
    identified_mm: float
    eliminated_mm: float
    recurring: bool
    remediation_owner: str


@dataclass
class SpendPolicy:
    policy: str
    threshold: str
    approval_level: str
    enforcement_status: str
    violations_ltm: int
    savings_from_policy_mm: float


@dataclass
class VendorRationalization:
    category: str
    vendor_count_pre: int
    vendor_count_post: int
    spend_pre_mm: float
    spend_post_mm: float
    savings_mm: float
    quality_impact: str


@dataclass
class ZBBResult:
    total_baseline_mm: float
    current_run_rate_mm: float
    target_run_rate_mm: float
    total_savings_captured_mm: float
    total_savings_potential_mm: float
    capture_rate_pct: float
    categories: List[CostCategory]
    initiatives: List[SavingsInitiative]
    waste: List[WasteAudit]
    policies: List[SpendPolicy]
    vendors: List[VendorRationalization]
    corpus_deal_count: int


def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 110):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


def _build_categories() -> List[CostCategory]:
    items = [
        ("Salaries & Wages (non-clinical)", 58.5, 52.8, 48.5, 5.7, 4.3, 0.105, 0.096),
        ("Clinical Labor (MDs, Nurses)", 185.5, 182.0, 175.0, 3.5, 7.0, 0.365, 0.350),
        ("Benefits & Payroll Tax", 48.5, 44.2, 42.0, 4.3, 2.2, 0.088, 0.084),
        ("Technology / Software", 18.5, 14.8, 13.5, 3.7, 1.3, 0.030, 0.027),
        ("Professional Services / Consulting", 12.5, 8.5, 7.2, 4.0, 1.3, 0.017, 0.014),
        ("Medical Supplies", 28.5, 26.8, 25.5, 1.7, 1.3, 0.054, 0.051),
        ("Pharmaceuticals (Buy-and-Bill)", 35.5, 34.2, 33.5, 1.3, 0.7, 0.068, 0.067),
        ("Facilities / Rent", 18.5, 17.8, 17.5, 0.7, 0.3, 0.036, 0.035),
        ("Insurance (Malpractice + GL)", 8.5, 7.2, 6.8, 1.3, 0.4, 0.014, 0.014),
        ("Marketing & Brand", 8.2, 5.5, 4.8, 2.7, 0.7, 0.011, 0.010),
        ("Travel & Entertainment", 3.2, 1.8, 1.5, 1.4, 0.3, 0.004, 0.003),
        ("Legal & Compliance", 4.8, 3.8, 3.5, 1.0, 0.3, 0.008, 0.007),
        ("Utilities & Occupancy", 5.5, 5.2, 5.0, 0.3, 0.2, 0.010, 0.010),
        ("Contract / Locum Labor", 18.5, 13.2, 10.5, 5.3, 2.7, 0.026, 0.021),
        ("Other G&A", 12.5, 9.8, 8.5, 2.7, 1.3, 0.020, 0.017),
    ]
    rows = []
    for cat, pre, cur, tgt, cap, pot, pct, bench in items:
        rows.append(CostCategory(
            category=cat,
            pre_zbb_mm=pre,
            current_run_rate_mm=cur,
            target_run_rate_mm=tgt,
            savings_captured_mm=cap,
            savings_potential_mm=pot,
            pct_of_revenue=pct,
            benchmark_pct=bench,
        ))
    return rows


def _build_initiatives() -> List[SavingsInitiative]:
    return [
        SavingsInitiative("Locum conversion (MD/RN)", "Contract Labor", 5.3, 3.85, 0.73, "CHRO", "on track"),
        SavingsInitiative("GPO unification (Vizient primary)", "Medical Supplies", 2.2, 1.65, 0.75, "VP SCM", "on track"),
        SavingsInitiative("IT/SaaS rationalization", "Technology", 3.8, 2.85, 0.75, "CIO", "on track"),
        SavingsInitiative("Consulting spend freeze", "Professional Services", 4.0, 3.85, 0.96, "CFO", "completed"),
        SavingsInitiative("Marketing agency consolidation", "Marketing", 2.7, 2.0, 0.74, "CMO", "on track"),
        SavingsInitiative("Office space reduction (3 offices)", "Facilities", 0.7, 0.55, 0.79, "VP Real Estate", "on track"),
        SavingsInitiative("Benefits plan renegotiation", "Benefits", 4.3, 3.8, 0.88, "CHRO", "completed"),
        SavingsInitiative("Clinical productivity improvement", "Clinical Labor", 7.0, 2.2, 0.31, "CMO", "lagging"),
        SavingsInitiative("Malpractice pool consolidation", "Insurance", 1.3, 1.15, 0.88, "General Counsel", "completed"),
        SavingsInitiative("T&E policy tightening", "Travel", 1.4, 1.3, 0.93, "CFO", "completed"),
        SavingsInitiative("Legal panel rationalization", "Legal", 1.0, 0.85, 0.85, "General Counsel", "on track"),
        SavingsInitiative("Non-clinical overhead reduction", "Salaries", 5.7, 4.8, 0.84, "CFO", "on track"),
        SavingsInitiative("Back-office G&A reduction", "G&A", 2.7, 1.9, 0.70, "CFO", "on track"),
    ]


def _build_waste() -> List[WasteAudit]:
    return [
        WasteAudit("Duplicate SaaS Subscriptions", "18 overlapping SaaS tools eliminated",
                   1.85, 1.85, True, "CIO"),
        WasteAudit("Dormant Office Leases", "3 offices fully empty since COVID",
                   1.25, 1.25, True, "VP Real Estate"),
        WasteAudit("Overstaffed Non-Clinical Admin", "12 positions eliminated post-PMI",
                   2.85, 2.85, True, "CHRO"),
        WasteAudit("Expedited Shipping Abuse", "No-approval policy enforced",
                   0.28, 0.28, True, "VP SCM"),
        WasteAudit("Over-Prescribed Brand Drugs", "Formulary enforcement",
                   1.45, 0.88, True, "CMO"),
        WasteAudit("Redundant Consulting Engagements", "3 consulting firms doing overlap work",
                   1.85, 1.85, False, "CFO"),
        WasteAudit("Non-Formulary Medical Supplies", "Standardization to formulary",
                   0.85, 0.65, True, "VP SCM"),
        WasteAudit("Subscription Auto-Renewals", "Unused seats on renewed contracts",
                   0.62, 0.62, True, "CFO"),
        WasteAudit("Malpractice Excess Coverage", "Double-covered physicians",
                   0.55, 0.55, True, "General Counsel"),
        WasteAudit("Paper-Based Processes", "Manual claims / prior auth converted",
                   1.85, 0.95, True, "CIO"),
    ]


def _build_policies() -> List[SpendPolicy]:
    return [
        SpendPolicy("Expense Approval Authority", ">$1000 = VP; >$10000 = CFO", "strict",
                    "enforced via Concur", 42, 0.42),
        SpendPolicy("Vendor Onboarding", "New vendor requires 3 quotes", "strict",
                    "enforced via Coupa", 8, 0.28),
        SpendPolicy("T&E Per Diem Caps", "GSA rates + 10%", "moderate",
                    "monthly audit", 28, 0.18),
        SpendPolicy("SaaS / Software Spend Review", "Quarterly CIO sign-off required", "strict",
                    "enforced", 2, 0.85),
        SpendPolicy("Consulting Engagement Gate", "RFP for any $>50K engagement", "strict",
                    "enforced", 1, 0.65),
        SpendPolicy("Offsite / Event Spend", "$15k cap per event", "strict",
                    "enforced", 3, 0.22),
        SpendPolicy("Corporate Card Policy", "Auto-suspension after 2 audit failures", "strict",
                    "automated", 5, 0.12),
        SpendPolicy("Executive Discretionary", ">$25k requires board approval", "strict",
                    "quarterly reporting", 0, 0.0),
    ]


def _build_vendors() -> List[VendorRationalization]:
    return [
        VendorRationalization("Medical Supplies", 85, 32, 12.5, 10.8, 1.7, "improved — same quality"),
        VendorRationalization("SaaS / Software", 142, 68, 8.5, 5.8, 2.7, "same"),
        VendorRationalization("Professional Services", 28, 8, 4.5, 2.5, 2.0, "consolidated expertise"),
        VendorRationalization("Marketing Services", 22, 6, 4.8, 2.1, 2.7, "same"),
        VendorRationalization("Temp / Agency Staff", 18, 5, 12.5, 7.2, 5.3, "improved"),
        VendorRationalization("Pharmacy Wholesalers", 8, 2, 22.5, 21.2, 1.3, "same"),
        VendorRationalization("Legal Counsel", 15, 6, 4.8, 3.8, 1.0, "maintained"),
        VendorRationalization("Facilities Management", 12, 4, 3.2, 2.7, 0.5, "improved SLAs"),
    ]


def compute_zbb_tracker() -> ZBBResult:
    corpus = _load_corpus()

    categories = _build_categories()
    initiatives = _build_initiatives()
    waste = _build_waste()
    policies = _build_policies()
    vendors = _build_vendors()

    total_pre = sum(c.pre_zbb_mm for c in categories)
    current = sum(c.current_run_rate_mm for c in categories)
    target = sum(c.target_run_rate_mm for c in categories)
    captured = sum(c.savings_captured_mm for c in categories)
    potential = sum(c.savings_potential_mm for c in categories)

    total_opp = captured + potential
    capture_rate = captured / total_opp if total_opp else 0

    return ZBBResult(
        total_baseline_mm=round(total_pre, 2),
        current_run_rate_mm=round(current, 2),
        target_run_rate_mm=round(target, 2),
        total_savings_captured_mm=round(captured, 2),
        total_savings_potential_mm=round(potential, 2),
        capture_rate_pct=round(capture_rate, 4),
        categories=categories,
        initiatives=initiatives,
        waste=waste,
        policies=policies,
        vendors=vendors,
        corpus_deal_count=len(corpus),
    )
