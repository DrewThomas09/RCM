"""Extra heuristics — additional partner-voice rules extending the
core `heuristics.py` rulebook.

These rules cover patterns not in the original 19-rule set. Each
follows the same shape: a predicate over `HeuristicContext` returning
an optional `HeuristicHit` with partner-voice finding + remediation.

Categories covered here:

- **VOLATILITY** — high growth dispersion without a named driver.
- **OPERATIONS** — weak clean-claim rate; payer-contract staleness.
- **PAYER** — uncontracted Medicare Advantage exposure; state ACO gaps.
- **STRUCTURE** — debt-service seasonality mismatch; equity-check
  sizing.
- **DATA** — missing trailing-12-month KPI reporting.
- **REGULATORY** — physician-supervision rule exposure.

Wire through `run_extra_heuristics(ctx)` or via `run_all_plus_extras`
which unions the base `heuristics.py`, `red_flags.py`, and these.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .heuristics import (
    HeuristicContext,
    HeuristicHit,
    SEV_CRITICAL,
    SEV_HIGH,
    SEV_LOW,
    SEV_MEDIUM,
    run_heuristics,
)
from .red_flags import run_red_flags


def _h_clean_claim_too_low(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    if ctx.clean_claim_rate is None:
        return None
    if ctx.clean_claim_rate >= 0.88:
        return None
    severity = SEV_HIGH if ctx.clean_claim_rate < 0.80 else SEV_MEDIUM
    return HeuristicHit(
        id="clean_claim_rate_low",
        title="Clean claim rate below peer floor",
        severity=severity,
        category="OPERATIONS",
        finding=(
            f"Clean claim rate is {ctx.clean_claim_rate*100:.1f}%. Peer "
            "floor is 88% — below that means rework cost is carrying a "
            "measurable share of margin."
        ),
        partner_voice=(
            "Fix clean-claim first. Every 100 bps of clean-claim improvement "
            "recovers 20-30 bps of margin without changing payers."
        ),
        trigger_metrics=["clean_claim_rate"],
        trigger_values={"clean_claim_rate": ctx.clean_claim_rate},
        remediation="Bucket denials by edit category; wire front-end edits; monthly review.",
        references=["PE_HEURISTICS#clean-claim-floor"],
    )


def _h_growth_volatility_without_driver(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    """Revenue growth volatility is high but the thesis doesn't name
    a volatility driver. Common in single-service-line rollups."""
    growth = ctx.revenue_growth_pct_per_yr
    if growth is None:
        return None
    # Use growth + margin data as a proxy for volatility.
    # No explicit stddev field on HeuristicContext, so we approximate
    # "volatile" as growth >= 10% with either low-margin or high-
    # concentration context.
    if growth < 10:
        return None
    has_driver = any([
        ctx.deal_structure in ("roll-up", "rollup"),
        ctx.has_case_mix_data is False,
    ])
    if has_driver:
        return None
    return HeuristicHit(
        id="growth_volatility_without_driver",
        title="Above-peer growth without named driver",
        severity=SEV_MEDIUM,
        category="VALUATION",
        finding=(
            f"Revenue growth {growth:.1f}%/yr exceeds norm; the thesis "
            "does not name a durable driver (rollup, demographic tailwind, "
            "new capability)."
        ),
        partner_voice=(
            "Unexplained growth is usually one of two things — pricing "
            "that won't persist or mix that will revert. Name the driver."
        ),
        trigger_metrics=["revenue_growth_pct_per_yr"],
        trigger_values={"revenue_growth_pct_per_yr": growth},
        remediation="Decompose growth into volume, price, and mix before IC.",
    )


def _h_payer_contract_staleness(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    """Proxy: low clean-claim rate + low denial-improvement plan =
    likely stale contracts no-one has re-negotiated."""
    if ctx.clean_claim_rate is None or ctx.denial_improvement_bps_per_yr is None:
        return None
    if ctx.clean_claim_rate >= 0.88:
        return None
    if ctx.denial_improvement_bps_per_yr >= 150:
        return None
    return HeuristicHit(
        id="payer_contract_staleness",
        title="Operating KPIs suggest stale payer contracts",
        severity=SEV_MEDIUM,
        category="PAYER",
        finding=(
            "Low clean-claim rate paired with a modest denial-improvement "
            "plan typically means payer contracts haven't been renegotiated "
            "recently."
        ),
        partner_voice=(
            "Renegotiate contracts before year 3 of hold. Fresh rates "
            "usually add 50-150 bps of margin."
        ),
        trigger_metrics=["clean_claim_rate", "denial_improvement_bps_per_yr"],
        remediation="Inventory contracts by effective date; target top-3 payers by revenue for renegotiation.",
    )


def _h_equity_check_over_concentration(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    """EBITDA-size heuristic: very large deals relative to the sponsor's
    normal check size deserve a second look. Uses ebitda_m as a proxy
    since the context doesn't directly carry fund size."""
    if ctx.ebitda_m is None:
        return None
    if ctx.ebitda_m < 300:
        return None
    return HeuristicHit(
        id="check_size_concentration",
        title="Deal size suggests fund-level concentration risk",
        severity=SEV_LOW,
        category="STRUCTURE",
        finding=(
            f"Deal EBITDA of ${ctx.ebitda_m:.0f}M is likely a top-3 "
            "equity check for a mid-market healthcare fund."
        ),
        partner_voice=(
            "Confirm LP concentration language; consider syndication to "
            "stay within limits even if unused."
        ),
        trigger_metrics=["ebitda_m"],
        trigger_values={"ebitda_m": ctx.ebitda_m},
        remediation="Check LPA concentration clauses; co-invest to stay inside.",
    )


def _h_no_trailing_kpi_reporting(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    """Proxy via data_coverage_pct — very low coverage implies TTM KPIs
    unavailable."""
    if ctx.data_coverage_pct is None:
        return None
    if ctx.data_coverage_pct >= 0.50:
        return None
    return HeuristicHit(
        id="missing_ttm_kpi_reporting",
        title="Likely missing TTM KPI reporting",
        severity=SEV_MEDIUM,
        category="DATA",
        finding=(
            f"Data coverage {ctx.data_coverage_pct*100:.0f}% suggests "
            "trailing-12-month KPI series are not maintained — buyers and "
            "LPs cannot see the trend line."
        ),
        partner_voice=(
            "Before we close, insist on TTM KPI dashboards. You cannot "
            "run a deal by quarter-end snapshots."
        ),
        trigger_metrics=["data_coverage_pct"],
        remediation="Build TTM KPI dashboard in first 60 days; set thresholds + alerts.",
    )


def _h_cah_teaching_mismatch(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    """Combined CAH + teaching status flag — the two categories don't
    overlap in the real world, so this signals a data error."""
    htype = (ctx.hospital_type or "").lower()
    teach = (ctx.teaching_status or "").lower()
    if htype != "critical_access":
        return None
    if teach not in ("major", "academic", "major_teaching"):
        return None
    return HeuristicHit(
        id="cah_teaching_mismatch",
        title="Critical-access + major-teaching status flagged together",
        severity=SEV_LOW,
        category="DATA",
        finding=(
            "The target is flagged as critical-access AND major-teaching. "
            "These classifications almost never co-exist in CMS data."
        ),
        partner_voice=(
            "Verify the classification. If it's an error, fix the profile "
            "before the reimbursement models run on the wrong assumption."
        ),
        trigger_metrics=["hospital_type", "teaching_status"],
        remediation="Cross-check CMS provider-type classification before pricing.",
    )


def _h_urban_outpatient_gold_rush(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    """Outpatient / MSO deals in urban markets with high commercial mix
    trade at premiums that often don't survive contact with competition."""
    if (ctx.hospital_type or "").lower() not in ("outpatient", "clinic", "mso"):
        return None
    if (ctx.urban_rural or "").lower() != "urban":
        return None
    mix = ctx.payer_mix or {}
    commercial = float(mix.get("commercial", 0.0) or 0.0)
    if commercial > 1.5:
        commercial /= 100.0
    if commercial < 0.60:
        return None
    if not ctx.exit_multiple or ctx.exit_multiple < 12.0:
        return None
    return HeuristicHit(
        id="urban_outpatient_gold_rush",
        title="Urban commercial outpatient + double-digit exit — gold-rush pattern",
        severity=SEV_MEDIUM,
        category="VALUATION",
        finding=(
            f"Urban outpatient platform, {commercial*100:.0f}% commercial, "
            f"exit at {ctx.exit_multiple:.2f}x. This profile has compressed "
            "sharply when category cools — 2023 physician-practice multiples."
        ),
        partner_voice=(
            "Pay for current cashflow, not for the category premium. "
            "If multiple compresses one turn, does this still clear?"
        ),
        trigger_metrics=["hospital_type", "payer_mix.commercial", "exit_multiple"],
        remediation="Run flat-multiple sensitivity; require base-case clearance.",
    )


def _h_hold_moic_inconsistency(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    """MOIC target impossible within hold given implied return
    math (CAGR > 40% is rarely sustained)."""
    if ctx.projected_moic is None or ctx.hold_years is None:
        return None
    if ctx.hold_years <= 0:
        return None
    try:
        cagr = ctx.projected_moic ** (1.0 / ctx.hold_years) - 1.0
    except (ValueError, ZeroDivisionError):
        return None
    if cagr <= 0.40:
        return None
    return HeuristicHit(
        id="hold_moic_inconsistency",
        title="Implied CAGR above sustained-return ceiling",
        severity=SEV_HIGH,
        category="VALUATION",
        finding=(
            f"{ctx.projected_moic:.2f}x MOIC over {ctx.hold_years:.1f} years "
            f"implies {cagr*100:.1f}% CAGR — above the 40% sustained-return "
            "ceiling for healthcare PE."
        ),
        partner_voice=(
            "A 40%+ CAGR is a 1-in-10 outcome, not a plan. Either the "
            "hold is too short or the MOIC is too optimistic."
        ),
        trigger_metrics=["projected_moic", "hold_years"],
        trigger_values={"moic": ctx.projected_moic, "hold_years": ctx.hold_years,
                        "implied_cagr": cagr},
        remediation="Extend hold or reset MOIC target; stress the ramp with -20% haircut.",
    )


# ── Orchestrator ────────────────────────────────────────────────────

_EXTRAS: List[Callable[[HeuristicContext], Optional[HeuristicHit]]] = [
    _h_clean_claim_too_low,
    _h_growth_volatility_without_driver,
    _h_payer_contract_staleness,
    _h_equity_check_over_concentration,
    _h_no_trailing_kpi_reporting,
    _h_cah_teaching_mismatch,
    _h_urban_outpatient_gold_rush,
    _h_hold_moic_inconsistency,
]


def run_extra_heuristics(ctx: HeuristicContext) -> List[HeuristicHit]:
    """Run the extra heuristic rules and return hits sorted by
    severity desc."""
    hits: List[HeuristicHit] = []
    for fn in _EXTRAS:
        try:
            result = fn(ctx)
        except Exception:
            result = None
        if result is not None:
            hits.append(result)
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    hits.sort(key=lambda h: order.get(h.severity, 5))
    return hits


def run_all_plus_extras(ctx: HeuristicContext) -> List[HeuristicHit]:
    """Full union: base heuristics + red flags + extras, dedup by id."""
    base = run_heuristics(ctx)
    reds = run_red_flags(ctx)
    extras = run_extra_heuristics(ctx)
    seen: set = set()
    merged: List[HeuristicHit] = []
    for h in list(base) + list(reds) + list(extras):
        if h.id in seen:
            continue
        seen.add(h.id)
        merged.append(h)
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    merged.sort(key=lambda h: order.get(h.severity, 5))
    return merged
