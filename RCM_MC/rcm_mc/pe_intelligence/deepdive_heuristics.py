"""Deep-dive heuristics — ten more partner rules for mature diligence.

Each rule targets a pattern a partner only catches after they've
seen enough deals. These complement `heuristics.py`, `red_flags.py`,
and `extra_heuristics.py`.

- `entry_equals_exit_same_year` — flat-multiple thesis with no
  multiple arbitrage argued.
- `hospital_in_rural_concentration` — rural catchment plus payer
  concentration combo.
- `mgmt_ownership_too_high` — >30% rollover implies founder-led
  operating, insufficient for scale.
- `teacher_cmi_mismatch` — teaching hospital but low CMI
  (inconsistent with the premium category).
- `staff_turnover_trend_up` — rising staff turnover trend.
- `gp_valuation_too_aggressive` — GP mark above peer + below recent
  comp indicates aggressive mark-to-market.
- `ebitda_growth_no_volume` — EBITDA growing faster than revenue
  with no named cost takeout.
- `long_hold_with_thin_cashflow` — 7yr+ hold on an asset with
  sub-50% cash conversion.
- `no_operating_partner_assigned` — operating-lever thesis without
  named operating partner.
- `reg_pending_cms_rule` — pending CMS rulemaking specifically
  relevant to the thesis.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from .heuristics import (
    HeuristicContext, HeuristicHit,
    SEV_CRITICAL, SEV_HIGH, SEV_LOW, SEV_MEDIUM,
)


def _h_entry_equals_exit_same_year(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    if ctx.entry_multiple is None or ctx.exit_multiple is None:
        return None
    if abs(ctx.exit_multiple - ctx.entry_multiple) > 0.25:
        return None
    if ctx.hold_years is None or ctx.hold_years > 3:
        return None
    return HeuristicHit(
        id="entry_equals_exit_same_year",
        title="Flat-multiple thesis with short hold",
        severity=SEV_MEDIUM, category="VALUATION",
        finding=(f"Entry {ctx.entry_multiple:.2f}x ≈ exit {ctx.exit_multiple:.2f}x "
                 f"over {ctx.hold_years:.1f}yr hold. All return has to come "
                 "from EBITDA growth."),
        partner_voice=("Short hold + flat multiples means we need the "
                       "lever program perfectly. Any slippage and IRR "
                       "falls below the hurdle."),
        trigger_metrics=["entry_multiple", "exit_multiple", "hold_years"],
        remediation="Extend hold or require +1 turn multiple thesis with a named comp.",
    )


def _h_rural_payer_concentration(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    if (ctx.urban_rural or "").lower() not in ("rural", "critical_access"):
        return None
    mix = ctx.payer_mix or {}
    norm = {str(k).lower(): float(v) for k, v in mix.items() if v is not None}
    total = sum(norm.values())
    if total > 1.5:
        norm = {k: v / 100.0 for k, v in norm.items()}
    govt = norm.get("medicare", 0.0) + norm.get("medicaid", 0.0)
    if govt < 0.60:
        return None
    return HeuristicHit(
        id="rural_govt_concentration",
        title="Rural + government-heavy — double concentration",
        severity=SEV_HIGH, category="PAYER",
        finding=(f"Rural hospital with {govt*100:.0f}% government payer mix. "
                 "Catchment area concentration stacks with payer concentration."),
        partner_voice=("Rural + govt-heavy is the toughest underwrite in "
                       "healthcare PE. Be sure the CAH reimbursement "
                       "mechanics are fully modeled."),
        trigger_metrics=["urban_rural", "payer_mix"],
        remediation="Model the deal under CMS rate-freeze scenario for 2 consecutive years.",
    )


def _h_teaching_cmi_mismatch(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    teach = (ctx.teaching_status or "").lower()
    if teach not in ("major", "academic", "major_teaching"):
        return None
    if ctx.case_mix_index is None:
        return None
    if ctx.case_mix_index >= 1.50:
        return None
    return HeuristicHit(
        id="teaching_cmi_mismatch",
        title="Major teaching + CMI below teaching-hospital norm",
        severity=SEV_MEDIUM, category="DATA",
        finding=(f"Teaching status={teach}, CMI {ctx.case_mix_index:.2f}. "
                 "Major teaching hospitals typically carry CMI ≥ 1.60."),
        partner_voice=("Either the teaching classification is wrong or "
                       "the CMI is mis-captured. Resolve before pricing."),
        trigger_metrics=["teaching_status", "case_mix_index"],
        remediation="Verify teaching classification + pull CMI from HCRIS.",
    )


def _h_ebitda_growth_no_volume(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    # If margin expansion > revenue growth by wide margin, cost-takeout
    # must be named.
    m = ctx.margin_expansion_bps_per_yr
    r = ctx.revenue_growth_pct_per_yr
    if m is None or r is None:
        return None
    if m < 250:
        return None
    if r >= 5:
        return None
    return HeuristicHit(
        id="ebitda_growth_no_volume",
        title="EBITDA growth faster than revenue — requires cost story",
        severity=SEV_MEDIUM, category="OPERATIONS",
        finding=(f"Margin expansion {m:.0f} bps/yr with revenue growth "
                 f"{r:.1f}%/yr. Without named cost takeout, this is "
                 "repricing or mix — neither is durable."),
        partner_voice=("Margin without volume is a short-lived trick. "
                       "Name the cost program."),
        trigger_metrics=["margin_expansion_bps_per_yr",
                         "revenue_growth_pct_per_yr"],
        remediation="Attribute margin expansion to specific cost categories; haircut if generic.",
    )


def _h_long_hold_thin_conversion(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    if ctx.hold_years is None or ctx.hold_years < 7:
        return None
    # Use ebitda_margin as a rough conversion proxy (absence of direct field).
    if ctx.ebitda_margin is None or ctx.ebitda_margin >= 0.10:
        return None
    return HeuristicHit(
        id="long_hold_thin_conversion",
        title="Long hold on thin-margin asset",
        severity=SEV_MEDIUM, category="STRUCTURE",
        finding=(f"{ctx.hold_years:.1f}yr hold on {ctx.ebitda_margin*100:.1f}% margin "
                 "asset. Thin cash conversion + long hold compounds patience risk."),
        partner_voice=("Long holds on thin-margin assets are how funds "
                       "end up with carry valuations they can't realize."),
        trigger_metrics=["hold_years", "ebitda_margin"],
        remediation="Target a shorter hold or restructure for accelerated dividend recap.",
    )


def _h_no_operating_partner(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    has_rcm_lever = any((
        ctx.denial_improvement_bps_per_yr or 0,
        ctx.ar_reduction_days_per_yr or 0,
    ))
    if not has_rcm_lever:
        return None
    # Proxy: if no explicit operator flag on the context (via hasattr).
    op_signal = getattr(ctx, "has_operating_partner", None)
    if op_signal is not False:
        return None
    return HeuristicHit(
        id="no_operating_partner_assigned",
        title="RCM thesis without named operating partner",
        severity=SEV_HIGH, category="STRUCTURE",
        finding=("RCM-heavy thesis without a named operating partner. "
                 "Operating levers do not land without a dedicated owner."),
        partner_voice=("Name the operating partner before IC. Otherwise "
                       "the lever plan is aspirational."),
        trigger_metrics=["has_operating_partner",
                         "denial_improvement_bps_per_yr"],
        remediation="Assign an operating partner pre-close; budget their time 20%+ to this asset.",
    )


def _h_mgmt_rollover_too_high(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    value = getattr(ctx, "equity_rollover_pct", None)
    if value is None:
        return None
    try:
        r = float(value)
    except (TypeError, ValueError):
        return None
    if r > 1.5:
        r /= 100.0
    if r <= 0.30:
        return None
    return HeuristicHit(
        id="mgmt_rollover_too_high",
        title="Management rollover > 30% — founder-scale limits",
        severity=SEV_LOW, category="STRUCTURE",
        finding=(f"Management equity rollover {r*100:.0f}%. High rollover "
                 "means founder retains material control — scale thesis "
                 "is harder."),
        partner_voice=("Big rollover is great for alignment but limits "
                       "scale moves. Plan for founder-to-CEO transition "
                       "in the operating plan."),
        trigger_metrics=["equity_rollover_pct"],
        remediation="Negotiate step-down mechanic or CEO-succession plan.",
    )


def _h_staff_turnover_trend(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    value = getattr(ctx, "staff_turnover_trend_pct", None)
    if value is None:
        return None
    try:
        t = float(value)
    except (TypeError, ValueError):
        return None
    if t <= 0.02:
        return None
    sev = SEV_HIGH if t >= 0.05 else SEV_MEDIUM
    return HeuristicHit(
        id="staff_turnover_trend_up",
        title="Staff turnover trending up",
        severity=sev, category="OPERATIONS",
        finding=(f"Turnover +{t*100:.1f} pp YoY. Rising turnover compounds "
                 "contract-labor costs and quality risk."),
        partner_voice=("Turnover is a leading indicator. If it's climbing, "
                       "the lever plan assumes people who are walking out "
                       "the door."),
        trigger_metrics=["staff_turnover_trend_pct"],
        remediation="Diagnose top-3 turnover drivers; build retention interventions.",
    )


def _h_pending_cms_rule(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    value = getattr(ctx, "pending_cms_rule", None)
    if not value:
        return None
    return HeuristicHit(
        id="pending_cms_rule",
        title="Pending CMS rulemaking affects thesis",
        severity=SEV_HIGH, category="REGULATORY",
        finding=(f"Specific pending CMS rule applies: {value}. Outcome "
                 "materially affects pricing assumptions."),
        partner_voice=("Track the rule and understand the comment-period "
                       "timeline. Either price the adverse outcome or "
                       "structure around it."),
        trigger_metrics=["pending_cms_rule"],
        remediation="Engage regulatory counsel; price the adverse scenario.",
    )


def _h_gp_valuation_aggressive(ctx: HeuristicContext) -> Optional[HeuristicHit]:
    value = getattr(ctx, "gp_mark_vs_peer_multiple", None)
    if value is None:
        return None
    try:
        delta = float(value)
    except (TypeError, ValueError):
        return None
    if delta < 1.5:
        return None
    return HeuristicHit(
        id="gp_valuation_too_aggressive",
        title="GP mark above peer multiple benchmark",
        severity=SEV_MEDIUM, category="VALUATION",
        finding=(f"GP mark is {delta:.1f}x above peer average. "
                 "Mark-to-market is aggressive relative to public comps."),
        partner_voice=("GP marks drift. LP mark-up + later realization "
                       "shortfall is the pattern to avoid."),
        trigger_metrics=["gp_mark_vs_peer_multiple"],
        remediation="Stress the mark using current public comp multiples; document the gap.",
    )


_DETECTORS: List[Callable[[HeuristicContext], Optional[HeuristicHit]]] = [
    _h_entry_equals_exit_same_year,
    _h_rural_payer_concentration,
    _h_teaching_cmi_mismatch,
    _h_ebitda_growth_no_volume,
    _h_long_hold_thin_conversion,
    _h_no_operating_partner,
    _h_mgmt_rollover_too_high,
    _h_staff_turnover_trend,
    _h_pending_cms_rule,
    _h_gp_valuation_aggressive,
]


DEEP_DIVE_FIELDS = (
    "has_operating_partner",
    "equity_rollover_pct",
    "staff_turnover_trend_pct",
    "pending_cms_rule",
    "gp_mark_vs_peer_multiple",
)


def run_deepdive_heuristics(ctx: HeuristicContext) -> List[HeuristicHit]:
    """Run every deep-dive rule; return hits sorted by severity desc."""
    hits: List[HeuristicHit] = []
    for fn in _DETECTORS:
        try:
            h = fn(ctx)
        except Exception:
            h = None
        if h is not None:
            hits.append(h)
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    hits.sort(key=lambda h: order.get(h.severity, 5))
    return hits
