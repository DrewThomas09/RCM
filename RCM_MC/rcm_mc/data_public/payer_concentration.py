"""Payer Concentration Tracker.

Measures payer-side concentration risk on a target — one of the top-3
diligence concerns on any healthcare platform. If a single commercial
carrier accounts for >40% of revenue, or the top-3 carriers for >75%,
that's a material risk at renewal and a basis for price-reset leverage
against the target.

Outputs:
- Payer roster with net revenue, YoY delta, contract expiry
- Top-payer share, HHI (Herfindahl) index, CR3, CR5
- Contract expiry calendar
- Renewal-risk scoring
- Denials-rate heatmap by payer
- Out-of-network volume exposure
- Platform benchmarks vs corpus
"""
from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Dict, List


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PayerDetail:
    payer_name: str
    payer_type: str
    annual_net_rev_mm: float
    revenue_share_pct: float
    yoy_delta_pct: float
    contract_expiry: str
    denial_rate_pct: float
    days_in_ar: int
    renewal_risk_score: int
    status: str


@dataclass
class ConcentrationMetric:
    metric: str
    value: float
    benchmark: float
    variance: float
    interpretation: str


@dataclass
class ContractRenewal:
    payer_name: str
    expiry_quarter: str
    annual_revenue_mm: float
    contract_type: str
    rate_reset_clause: str
    exposure_pct: float
    priority: str


@dataclass
class DenialAnalysis:
    payer_name: str
    denials_pct: float
    top_denial_reason: str
    days_to_overturn: int
    overturn_success_pct: float
    write_off_exposure_mm: float


@dataclass
class OONExposure:
    service_line: str
    oon_volume_pct: float
    avg_collection_rate: float
    balance_bill_risk_mm: float
    no_surprises_act_impact: str


@dataclass
class PayerConcentrationResult:
    total_revenue_mm: float
    top_payer_share_pct: float
    top3_share_pct: float
    top5_share_pct: float
    hhi_index: int
    commercial_pct: float
    medicare_pct: float
    medicaid_pct: float
    self_pay_pct: float
    payers: List[PayerDetail]
    concentration_metrics: List[ConcentrationMetric]
    renewals: List[ContractRenewal]
    denials: List[DenialAnalysis]
    oon_exposure: List[OONExposure]
    corpus_deal_count: int
    concentration_risk_label: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 86):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    try:
        from rcm_mc.data_public.deals_corpus import _SEED_DEALS
        deals = _SEED_DEALS + deals
    except Exception:
        pass
    return deals


def _build_payers(revenue_mm: float, top_payer_pct: float) -> List[PayerDetail]:
    import hashlib
    # Distribute across 12 payers with a declining tail
    payer_specs = [
        ("BlueCross BlueShield Assoc", "Commercial National", top_payer_pct),
        ("UnitedHealthcare", "Commercial National", top_payer_pct * 0.72),
        ("Aetna / CVS Health", "Commercial National", top_payer_pct * 0.48),
        ("Medicare FFS", "Federal", 0.18),
        ("Medicare Advantage (Blended)", "MA Risk", 0.12),
        ("Cigna", "Commercial National", top_payer_pct * 0.32),
        ("State Medicaid FFS", "Medicaid FFS", 0.08),
        ("Medicaid Managed Care (Blended)", "Medicaid MMC", 0.11),
        ("Humana MA", "MA Risk", 0.06),
        ("Anthem / Elevance", "Commercial Regional", top_payer_pct * 0.22),
        ("Tricare / VA", "Federal", 0.02),
        ("Self-Pay / Private", "Self-Pay", 0.03),
    ]
    # Normalize to sum ~1.0
    total_specs = sum(s[2] for s in payer_specs)
    rows = []
    for i, (name, ptype, raw_share) in enumerate(payer_specs):
        share = raw_share / total_specs
        h = int(hashlib.md5(name.encode()).hexdigest()[:6], 16)
        rev = share * revenue_mm
        yoy = (h % 18 - 6) / 100   # -6% to +12%
        days_exp = (h % 24)        # 0-24 months
        exp_q = 2026 + days_exp // 12
        exp_m = (h % 4) + 1
        expiry = f"{exp_q}Q{exp_m}"
        denial_rate = 0.04 + (h % 11) / 100
        dar = 34 + (h % 22)
        renewal_risk = min(95, max(5, int(share * 200 + (h % 30))))
        status = "at renewal" if days_exp < 12 else ("long contract" if days_exp > 20 else "mid-term")
        rows.append(PayerDetail(
            payer_name=name,
            payer_type=ptype,
            annual_net_rev_mm=round(rev, 2),
            revenue_share_pct=round(share, 4),
            yoy_delta_pct=round(yoy, 4),
            contract_expiry=expiry,
            denial_rate_pct=round(denial_rate, 4),
            days_in_ar=dar,
            renewal_risk_score=renewal_risk,
            status=status,
        ))
    return sorted(rows, key=lambda p: p.revenue_share_pct, reverse=True)


def _calc_hhi(payers: List[PayerDetail]) -> int:
    # HHI = sum of (share * 100)^2
    return int(sum((p.revenue_share_pct * 100) ** 2 for p in payers))


def _build_concentration_metrics(payers: List[PayerDetail], hhi: int,
                                 top1: float, top3: float, top5: float) -> List[ConcentrationMetric]:
    return [
        ConcentrationMetric(
            metric="Top Payer Share",
            value=round(top1, 4),
            benchmark=0.25,
            variance=round(top1 - 0.25, 4),
            interpretation="above 40% is material concentration risk"),
        ConcentrationMetric(
            metric="Top 3 Payer Share (CR3)",
            value=round(top3, 4),
            benchmark=0.60,
            variance=round(top3 - 0.60, 4),
            interpretation="above 75% signals oligopolistic exposure"),
        ConcentrationMetric(
            metric="Top 5 Payer Share (CR5)",
            value=round(top5, 4),
            benchmark=0.82,
            variance=round(top5 - 0.82, 4),
            interpretation="above 90% is typical for mid-market HC"),
        ConcentrationMetric(
            metric="Herfindahl Index (HHI)",
            value=hhi,
            benchmark=1800,
            variance=hhi - 1800,
            interpretation="HHI >2500 = concentrated; >1800 = moderate"),
        ConcentrationMetric(
            metric="Payer Count",
            value=len(payers),
            benchmark=10,
            variance=len(payers) - 10,
            interpretation="healthy diversification above 10 payers"),
        ConcentrationMetric(
            metric="Weighted Denial Rate",
            value=round(sum(p.denial_rate_pct * p.revenue_share_pct for p in payers), 4),
            benchmark=0.08,
            variance=round(sum(p.denial_rate_pct * p.revenue_share_pct for p in payers) - 0.08, 4),
            interpretation="target <8%; >12% is a red flag"),
        ConcentrationMetric(
            metric="Weighted Days in AR",
            value=round(sum(p.days_in_ar * p.revenue_share_pct for p in payers), 1),
            benchmark=42.0,
            variance=round(sum(p.days_in_ar * p.revenue_share_pct for p in payers) - 42.0, 1),
            interpretation="target <42 days blended"),
    ]


def _build_renewals(payers: List[PayerDetail]) -> List[ContractRenewal]:
    rows = []
    for p in sorted(payers, key=lambda x: x.contract_expiry)[:10]:
        rate_reset = "CPI+1.5% floor, max 4%" if "Commercial" in p.payer_type else ("fee schedule reset" if "Medicare" in p.payer_type else "state-set")
        priority = "critical" if p.revenue_share_pct > 0.12 else ("high" if p.revenue_share_pct > 0.06 else "standard")
        rows.append(ContractRenewal(
            payer_name=p.payer_name,
            expiry_quarter=p.contract_expiry,
            annual_revenue_mm=p.annual_net_rev_mm,
            contract_type=p.payer_type,
            rate_reset_clause=rate_reset,
            exposure_pct=p.revenue_share_pct,
            priority=priority,
        ))
    return rows


def _build_denials(payers: List[PayerDetail]) -> List[DenialAnalysis]:
    import hashlib
    reasons = ["Prior Auth Missing", "Medical Necessity", "Coding Error",
               "Eligibility Lapse", "Timely Filing", "Duplicate Claim",
               "No Referral", "Place-of-Service Mismatch"]
    rows = []
    for p in payers[:8]:
        h = int(hashlib.md5(p.payer_name.encode()).hexdigest()[:6], 16)
        reason = reasons[h % len(reasons)]
        overturn_days = 22 + (h % 28)
        overturn_pct = 0.55 + (h % 25) / 100
        write_off = p.annual_net_rev_mm * p.denial_rate_pct * (1 - overturn_pct)
        rows.append(DenialAnalysis(
            payer_name=p.payer_name,
            denials_pct=round(p.denial_rate_pct, 4),
            top_denial_reason=reason,
            days_to_overturn=overturn_days,
            overturn_success_pct=round(overturn_pct, 3),
            write_off_exposure_mm=round(write_off, 2),
        ))
    return rows


def _build_oon_exposure() -> List[OONExposure]:
    return [
        OONExposure("Emergency Medicine", 0.12, 0.48, 1.85, "NSA-protected; arbitrage risk"),
        OONExposure("Anesthesia (hospital-based)", 0.18, 0.52, 2.40, "NSA-protected; QPA disputes"),
        OONExposure("Radiology (hospital-based)", 0.08, 0.55, 0.85, "NSA-protected"),
        OONExposure("Pathology", 0.14, 0.50, 1.20, "NSA-protected; arbitrage ongoing"),
        OONExposure("Ground Ambulance", 0.22, 0.42, 0.95, "NSA-excluded state balance bill"),
        OONExposure("Air Ambulance", 0.68, 0.35, 0.45, "NSA-protected; very high dispute rate"),
        OONExposure("Specialty Drug Administration", 0.06, 0.58, 0.55, "buy-and-bill; minimal OON"),
        OONExposure("Outpatient Surgery", 0.04, 0.62, 0.40, "NSA-protected for non-elective"),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_payer_concentration(
    revenue_mm: float = 250.0,
    top_payer_pct: float = 0.32,
) -> PayerConcentrationResult:
    corpus = _load_corpus()

    payers = _build_payers(revenue_mm, top_payer_pct)
    sorted_payers = sorted(payers, key=lambda p: p.revenue_share_pct, reverse=True)
    top1 = sorted_payers[0].revenue_share_pct if sorted_payers else 0
    top3 = sum(p.revenue_share_pct for p in sorted_payers[:3])
    top5 = sum(p.revenue_share_pct for p in sorted_payers[:5])
    hhi = _calc_hhi(payers)

    # Category breakdown
    comm_pct = sum(p.revenue_share_pct for p in payers if p.payer_type in ("Commercial National", "Commercial Regional"))
    medicare_pct = sum(p.revenue_share_pct for p in payers if p.payer_type in ("Federal", "MA Risk") and "Medicare" in p.payer_name or p.payer_type == "MA Risk")
    medicaid_pct = sum(p.revenue_share_pct for p in payers if "Medicaid" in p.payer_type)
    sp_pct = sum(p.revenue_share_pct for p in payers if p.payer_type == "Self-Pay")

    metrics = _build_concentration_metrics(payers, hhi, top1, top3, top5)
    renewals = _build_renewals(payers)
    denials = _build_denials(payers)
    oon = _build_oon_exposure()

    if hhi >= 2500 or top1 >= 0.40:
        risk_label = "concentrated"
    elif hhi >= 1800 or top1 >= 0.28:
        risk_label = "moderate"
    else:
        risk_label = "diversified"

    return PayerConcentrationResult(
        total_revenue_mm=round(revenue_mm, 2),
        top_payer_share_pct=round(top1, 4),
        top3_share_pct=round(top3, 4),
        top5_share_pct=round(top5, 4),
        hhi_index=hhi,
        commercial_pct=round(comm_pct, 4),
        medicare_pct=round(medicare_pct, 4),
        medicaid_pct=round(medicaid_pct, 4),
        self_pay_pct=round(sp_pct, 4),
        payers=payers,
        concentration_metrics=metrics,
        renewals=renewals,
        denials=denials,
        oon_exposure=oon,
        corpus_deal_count=len(corpus),
        concentration_risk_label=risk_label,
    )
