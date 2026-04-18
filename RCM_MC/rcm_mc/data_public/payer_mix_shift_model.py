"""Payer mix shift model — project payer mix evolution over hold period.

Answers the IC question: "If commercial payers keep declining, what does
that do to our EBITDA margin by exit year?"

The model uses corpus-calibrated empirical transition rates for the
healthcare PE universe (2010-2024):
  - Commercial → Medicare:  aging population + Medicare Advantage growth
  - Commercial → Medicaid:  ACA expansion, state-specific coverage cycles
  - Commercial → Self-pay:  high-deductible plan growth, ACA churn
  - Medicare → Medicaid:    dual-eligibles (slow, ~0.5%/yr)
  - Medicaid → Self-pay:    Medicaid unwinding / state redeterminations

Each payer type carries an empirical reimbursement index relative to
commercial (= 1.0):
    Medicare:   0.82  (inpatient acute), 0.75 (physician), 0.79 (blended)
    Medicaid:   0.62  (acute), 0.52 (physician), 0.58 (blended)
    Self-pay:   0.15  (net of bad debt / charity)
    Commercial: 1.00  (baseline)

EBITDA margin impact is computed from revenue-per-unit changes assuming
cost structure is ~70% fixed, so a 10% revenue decline → ~7% EBITDA decline.

Public API:
    PayerMixProjection          dataclass (year, mix, revenue_index, ebitda_delta_pct)
    PayerMixShiftResult         dataclass (base_mix, projections, ebitda_at_risk_pct, signal)
    project_payer_mix(payer_mix, hold_years, sector, assumptions) -> PayerMixShiftResult
    payer_shift_report(result) -> str
    payer_shift_table(results) -> str
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Empirical constants (calibrated from 2010-2024 corpus)
# ---------------------------------------------------------------------------

# Reimbursement index vs. commercial (commercial = 1.0)
REIMB_INDEX: Dict[str, float] = {
    "commercial": 1.000,
    "medicare": 0.790,    # blended MA + FFS; MA growing share improves rate stability
    "medicaid": 0.580,    # blended; state variation is high (±0.15)
    "self_pay": 0.150,    # net collectible after bad debt/charity care
}

# Annual transition rates by sector (from → to : pct of from-payer/year)
# Format: {sector: {from_payer: {to_payer: annual_rate}}}
_BASE_TRANSITIONS: Dict[str, float] = {
    # commercial loses to each other payer annually
    "commercial_to_medicare": 0.008,    # ~0.8%/yr — aging + MA enrollment
    "commercial_to_medicaid": 0.005,    # ~0.5%/yr — Medicaid expansion, ACA churn
    "commercial_to_self_pay": 0.006,    # ~0.6%/yr — HDHP growth, ACA premium exits
    "medicare_to_medicaid": 0.004,      # dual-eligible growth
    "medicaid_to_self_pay": 0.010,      # Medicaid unwinding post-COVID (2023+ elevated)
    "self_pay_to_medicaid": 0.015,      # ACA/Medicaid expansion enrollment
}

# Sector-specific multipliers on base transition rates
_SECTOR_MULTIPLIERS: Dict[str, Dict[str, float]] = {
    "Behavioral Health": {
        "medicaid_to_self_pay": 2.5,    # high churn, prior auth denials
        "commercial_to_medicaid": 1.8,  # frequent payer mix degradation observed
    },
    "Physician Practices": {
        "commercial_to_medicare": 1.5,  # specialist panels older than average
        "commercial_to_self_pay": 0.8,
    },
    "Home Health": {
        "commercial_to_medicare": 1.8,  # home health inherently Medicare-heavy
        "medicare_to_medicaid": 1.5,
    },
    "Skilled Nursing": {
        "commercial_to_medicare": 2.0,
        "medicare_to_medicaid": 2.0,    # SNF Medicaid tail is long
    },
    "Dental": {
        "commercial_to_self_pay": 1.5,  # dental elective; discretionary spend
        "commercial_to_medicaid": 1.2,
    },
    "Primary Care": {
        "commercial_to_medicare": 1.3,  # VBC contracts increasing MA share
        "commercial_to_medicaid": 1.4,
    },
    "Revenue Cycle Management": {
        "commercial_to_medicare": 0.6,  # RCM follows customer payer mix, slightly less volatile
        "commercial_to_medicaid": 0.6,
    },
    "Digital Health": {
        "commercial_to_self_pay": 0.5,  # digital health typically commercial/employer
        "commercial_to_medicaid": 0.3,
    },
}

# Fixed cost fraction — what fraction of costs are fixed?
# A 10% revenue drop causes (fixed_cost_fraction * 10%) EBITDA margin compression.
_FIXED_COST_FRACTION = 0.70  # typical healthcare services operator


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PayerMixProjection:
    """Payer mix state at a specific year in the hold period."""
    year: int                           # 0 = entry, N = hold year N
    mix: Dict[str, float]              # payer → fraction (sums to ~1.0)
    revenue_index: float               # relative to entry year (1.0 = flat)
    ebitda_margin_delta_pct: float     # % pts EBITDA margin change vs. entry
    net_revenue_delta_pct: float       # % revenue change vs. entry


@dataclass
class PayerMixShiftResult:
    """Full payer mix shift scenario output."""
    deal_name: str
    sector: str
    base_mix: Dict[str, float]
    projections: List[PayerMixProjection] = field(default_factory=list)
    exit_mix: Optional[Dict[str, float]] = None
    ebitda_at_risk_pct: float = 0.0    # EBITDA margin pts lost by exit year
    revenue_at_risk_pct: float = 0.0   # % net revenue lost by exit year
    signal: str = "green"              # "green" / "yellow" / "red"
    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_transitions(sector: str) -> Dict[str, float]:
    """Return sector-adjusted annual transition rates."""
    rates = dict(_BASE_TRANSITIONS)
    mults = _SECTOR_MULTIPLIERS.get(sector, {})
    for key, mult in mults.items():
        if key in rates:
            rates[key] = rates[key] * mult
    return rates


def _step_mix(mix: Dict[str, float], rates: Dict[str, float]) -> Dict[str, float]:
    """Advance payer mix by one year using transition rates."""
    c = mix.get("commercial", 0.0)
    m = mix.get("medicare", 0.0)
    mc = mix.get("medicaid", 0.0)
    sp = mix.get("self_pay", 0.0)

    # Compute outflows
    c_to_mcare = c * rates["commercial_to_medicare"]
    c_to_mcaid = c * rates["commercial_to_medicaid"]
    c_to_sp = c * rates["commercial_to_self_pay"]
    mcare_to_mcaid = m * rates["medicare_to_medicaid"]
    mcaid_to_sp = mc * rates["medicaid_to_self_pay"]
    sp_to_mcaid = sp * rates["self_pay_to_medicaid"]

    new_c = c - c_to_mcare - c_to_mcaid - c_to_sp
    new_m = m + c_to_mcare - mcare_to_mcaid
    new_mc = mc + c_to_mcaid + mcare_to_mcaid + sp_to_mcaid - mcaid_to_sp
    new_sp = sp + c_to_sp + mcaid_to_sp - sp_to_mcaid

    # Clamp negatives and normalize
    new_c = max(0.0, new_c)
    new_m = max(0.0, new_m)
    new_mc = max(0.0, new_mc)
    new_sp = max(0.0, new_sp)
    total = new_c + new_m + new_mc + new_sp
    if total > 0:
        new_c /= total
        new_m /= total
        new_mc /= total
        new_sp /= total

    return {
        "commercial": round(new_c, 4),
        "medicare": round(new_m, 4),
        "medicaid": round(new_mc, 4),
        "self_pay": round(new_sp, 4),
    }


def _revenue_index(mix: Dict[str, float]) -> float:
    """Compute revenue index for a payer mix (commercial=1.0 baseline)."""
    return sum(REIMB_INDEX.get(payer, 0.50) * frac for payer, frac in mix.items())


def _ebitda_margin_impact(revenue_delta_pct: float, fixed_cost_fraction: float = _FIXED_COST_FRACTION) -> float:
    """
    Operating leverage: a revenue_delta_pct decline compresses EBITDA margin by
    (fixed_cost_fraction * |revenue_delta_pct|) percentage points.
    """
    return revenue_delta_pct * fixed_cost_fraction


# ---------------------------------------------------------------------------
# Main projection function
# ---------------------------------------------------------------------------

def project_payer_mix(
    payer_mix: Dict[str, float],
    hold_years: int = 5,
    sector: str = "",
    deal_name: str = "",
    assumptions: Optional[Dict[str, Any]] = None,
) -> PayerMixShiftResult:
    """Project payer mix evolution over hold period.

    Args:
        payer_mix:    Entry payer mix dict (keys: commercial, medicare, medicaid, self_pay)
        hold_years:   Number of years to project
        sector:       Healthcare sector (drives transition rate multipliers)
        deal_name:    For display purposes
        assumptions:  Optional overrides: fixed_cost_fraction, rate_multiplier

    Returns:
        PayerMixShiftResult with year-by-year projections and risk signal
    """
    ass = assumptions or {}
    fixed_cost = float(ass.get("fixed_cost_fraction", _FIXED_COST_FRACTION))
    rate_mult = float(ass.get("rate_multiplier", 1.0))  # global stress lever

    # Normalize payer mix to sum to 1.0
    total = sum(payer_mix.values())
    if total <= 0:
        payer_mix = {"commercial": 1.0}
        total = 1.0
    norm_mix = {k: v / total for k, v in payer_mix.items()}

    rates = _get_transitions(sector)
    if rate_mult != 1.0:
        rates = {k: v * rate_mult for k, v in rates.items()}

    base_rev = _revenue_index(norm_mix)
    notes = []
    projections = []
    current_mix = dict(norm_mix)

    # Year 0 — entry
    projections.append(PayerMixProjection(
        year=0,
        mix=dict(current_mix),
        revenue_index=1.0,
        ebitda_margin_delta_pct=0.0,
        net_revenue_delta_pct=0.0,
    ))

    for yr in range(1, hold_years + 1):
        current_mix = _step_mix(current_mix, rates)
        rev = _revenue_index(current_mix)
        rev_delta_pct = (rev - base_rev) / base_rev * 100.0
        ebitda_delta = _ebitda_margin_impact(rev_delta_pct, fixed_cost)
        projections.append(PayerMixProjection(
            year=yr,
            mix=dict(current_mix),
            revenue_index=round(rev / base_rev, 4),
            ebitda_margin_delta_pct=round(ebitda_delta, 2),
            net_revenue_delta_pct=round(rev_delta_pct, 2),
        ))

    exit_proj = projections[-1]
    ebitda_at_risk = abs(min(0.0, exit_proj.ebitda_margin_delta_pct))
    rev_at_risk = abs(min(0.0, exit_proj.net_revenue_delta_pct))

    # Risk signal
    if ebitda_at_risk < 1.5:
        signal = "green"
    elif ebitda_at_risk < 4.0:
        signal = "yellow"
    else:
        signal = "red"

    # Generate notes
    entry_comm = norm_mix.get("commercial", 0.0)
    exit_comm = exit_proj.mix.get("commercial", 0.0)
    if entry_comm - exit_comm > 0.05:
        notes.append(
            f"Commercial mix erodes from {entry_comm:.0%} → {exit_comm:.0%} "
            f"over {hold_years}yr hold ({(entry_comm-exit_comm)*100:.1f} pts)"
        )
    if exit_proj.mix.get("medicaid", 0.0) > 0.35:
        notes.append(
            f"Medicaid concentration reaches {exit_proj.mix.get('medicaid',0):.0%} "
            f"by exit — state budget rate risk elevated"
        )
    if ebitda_at_risk > 2.0:
        notes.append(
            f"Payer mix shift compresses EBITDA margin {ebitda_at_risk:.1f} pts "
            f"by year {hold_years} — build rate in exit multiple assumptions"
        )
    if sector in ("Behavioral Health", "Skilled Nursing", "Home Health"):
        notes.append(
            f"Sector '{sector}' has above-average Medicaid drift risk — "
            "verify state-rate escalator clauses in contracts"
        )

    return PayerMixShiftResult(
        deal_name=deal_name,
        sector=sector,
        base_mix=dict(norm_mix),
        projections=projections,
        exit_mix=exit_proj.mix,
        ebitda_at_risk_pct=round(ebitda_at_risk, 2),
        revenue_at_risk_pct=round(rev_at_risk, 2),
        signal=signal,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Scenario analysis
# ---------------------------------------------------------------------------

def stress_payer_shift(
    payer_mix: Dict[str, float],
    hold_years: int = 5,
    sector: str = "",
    deal_name: str = "",
) -> Dict[str, PayerMixShiftResult]:
    """Run base / bear / bull payer mix scenarios.

    Returns:
        dict with keys "base", "bear", "bull" → PayerMixShiftResult
    """
    return {
        "base": project_payer_mix(payer_mix, hold_years, sector, deal_name),
        "bear": project_payer_mix(
            payer_mix, hold_years, sector, deal_name,
            assumptions={"rate_multiplier": 2.0},
        ),
        "bull": project_payer_mix(
            payer_mix, hold_years, sector, deal_name,
            assumptions={"rate_multiplier": 0.3},
        ),
    }


# ---------------------------------------------------------------------------
# Corpus-level analytics
# ---------------------------------------------------------------------------

def corpus_payer_shift_risk(
    corpus_deals: List[Dict[str, Any]],
    hold_years: int = 5,
) -> List[Tuple[str, PayerMixShiftResult]]:
    """Score payer mix shift risk for every corpus deal with payer_mix data.

    Returns:
        List of (deal_name, PayerMixShiftResult) sorted by ebitda_at_risk desc
    """
    results = []
    for deal in corpus_deals:
        pm = deal.get("payer_mix")
        if not pm:
            continue
        name = deal.get("deal_name", deal.get("source_id", "unknown"))
        sector = deal.get("sector", "")
        h = hold_years if deal.get("hold_years") is None else int(deal.get("hold_years") or hold_years)
        result = project_payer_mix(pm, h, sector, name)
        results.append((name, result))

    results.sort(key=lambda x: x[1].ebitda_at_risk_pct, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def payer_shift_report(result: PayerMixShiftResult) -> str:
    """Formatted payer mix shift report for IC packet."""
    sig_map = {"green": "GREEN ✓", "yellow": "YELLOW ⚠", "red": "RED ✗"}
    lines = [
        f"Payer Mix Shift Analysis: {result.deal_name}",
        "=" * 60,
        f"  Sector: {result.sector or 'n/a'}",
        f"  Signal: {sig_map.get(result.signal, result.signal.upper())}",
        f"  EBITDA at Risk (exit yr): {result.ebitda_at_risk_pct:.1f} margin pts",
        f"  Net Revenue at Risk:      {result.revenue_at_risk_pct:.1f}%",
        "",
        f"  {'Year':<6} {'Comm':>7} {'Mcare':>7} {'Mcaid':>7} {'SP':>7} {'Rev Idx':>9} {'EBITDA Δ':>10}",
        "  " + "-" * 55,
    ]
    for p in result.projections:
        comm = p.mix.get("commercial", 0.0)
        mcare = p.mix.get("medicare", 0.0)
        mcaid = p.mix.get("medicaid", 0.0)
        sp = p.mix.get("self_pay", 0.0)
        lines.append(
            f"  {p.year:<6} {comm:>6.1%} {mcare:>7.1%} {mcaid:>7.1%} {sp:>7.1%} "
            f"{p.revenue_index:>9.3f} {p.ebitda_margin_delta_pct:>+9.1f}pp"
        )
    lines.append("")

    if result.notes:
        lines += ["Key Flags:"]
        for n in result.notes:
            lines.append(f"  • {n}")

    return "\n".join(lines) + "\n"


def payer_shift_table(results: List[PayerMixShiftResult]) -> str:
    """Compact table comparing payer mix shift risk across deals."""
    hdr = f"{'Deal':<35} {'Signal':<8} {'EBITDA Risk':>12} {'Rev Risk':>10} {'Exit Comm':>10}"
    sep = "-" * 80
    lines = [hdr, sep]
    for r in sorted(results, key=lambda x: x.ebitda_at_risk_pct, reverse=True):
        name = r.deal_name[:33]
        exit_comm = r.exit_mix.get("commercial", 0.0) if r.exit_mix else 0.0
        lines.append(
            f"{name:<35} [{r.signal:<6}] {r.ebitda_at_risk_pct:>9.1f}pp "
            f"{r.revenue_at_risk_pct:>9.1f}% {exit_comm:>9.1%}"
        )
    return "\n".join(lines) + "\n"
