"""Valuation sanity checks — WACC, EV walk, DCF terminal value.

Partners look at a DCF and ask three questions before they look at
anything else:

1. What's your WACC and how did you get there?
2. Does the equity value roll from EV correctly?
3. What fraction of EV is the terminal value — and is the implied
   exit multiple defensible?

These are deterministic checks with partner-defensible ranges. A
failing check is not necessarily a failing deal — it's a modeling
concern that needs resolution before IC.

Each check returns a :class:`ValuationCheck` with the same
``verdict`` / ``rationale`` / ``partner_note`` shape as the
reasonableness bands.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .reasonableness import (
    BandCheck,
    VERDICT_IMPLAUSIBLE,
    VERDICT_IN_BAND,
    VERDICT_OUT_OF_BAND,
    VERDICT_STRETCH,
    VERDICT_UNKNOWN,
)


# ── WACC ─────────────────────────────────────────────────────────────
# Healthcare PE WACC sits ~8-12% in the current rate environment.
# Below 7% is usually a model error (stale risk-free rate or zero
# equity premium). Above 14% suggests a distressed or cross-border
# comp — legitimate but should be called out.

WACC_IN_BAND = (0.08, 0.12)
WACC_STRETCH = (0.07, 0.14)
WACC_IMPLAUSIBLE_LOW = 0.05
WACC_IMPLAUSIBLE_HIGH = 0.18


def check_wacc(wacc: Optional[float]) -> BandCheck:
    """Classify a WACC against the partner-defensible range."""
    if wacc is None:
        return BandCheck(
            metric="wacc", observed=None, verdict=VERDICT_UNKNOWN,
            rationale="WACC not provided.",
        )
    if WACC_IN_BAND[0] <= wacc <= WACC_IN_BAND[1]:
        return BandCheck(
            metric="wacc", observed=wacc, verdict=VERDICT_IN_BAND,
            rationale=f"WACC of {wacc*100:.1f}% is within the 8–12% peer range.",
            partner_note="Reasonable cost of capital.",
        )
    if wacc < WACC_IMPLAUSIBLE_LOW or wacc > WACC_IMPLAUSIBLE_HIGH:
        return BandCheck(
            metric="wacc", observed=wacc, verdict=VERDICT_IMPLAUSIBLE,
            rationale=(
                f"WACC of {wacc*100:.1f}% is outside any defensible range. "
                "This is a model error, not a real number."
            ),
            partner_note="Rebuild the WACC calculation — probably a formula bug.",
        )
    if WACC_STRETCH[0] <= wacc <= WACC_STRETCH[1]:
        return BandCheck(
            metric="wacc", observed=wacc, verdict=VERDICT_STRETCH,
            rationale=f"WACC of {wacc*100:.1f}% is outside the tight 8–12% band but still defensible.",
            partner_note="Show me the CAPM or WACC build — what's the equity risk premium you used?",
        )
    return BandCheck(
        metric="wacc", observed=wacc, verdict=VERDICT_OUT_OF_BAND,
        rationale=f"WACC of {wacc*100:.1f}% is outside the peer range.",
        partner_note="Either the cost of debt is stale or the equity premium is wrong. Rebuild.",
    )


# ── EV walk reconciliation ───────────────────────────────────────────
# Equity value = EV − net debt − minorities − preferred + cash-like.
# Partners want the walk to reconcile to the penny; a mismatch over
# 1% of EV usually means a missing minority interest or a misclassified
# pension liability.

def check_ev_walk(
    *,
    enterprise_value: Optional[float],
    equity_value: Optional[float],
    net_debt: Optional[float] = None,
    minority_interest: Optional[float] = 0.0,
    preferred: Optional[float] = 0.0,
    cash_like: Optional[float] = 0.0,
) -> BandCheck:
    """Verify EV walk reconciles to equity value within 1% tolerance."""
    if enterprise_value is None or equity_value is None:
        return BandCheck(
            metric="ev_walk", observed=None, verdict=VERDICT_UNKNOWN,
            rationale="EV or equity value missing — cannot reconcile the walk.",
        )
    nd = net_debt or 0.0
    mi = minority_interest or 0.0
    pf = preferred or 0.0
    cl = cash_like or 0.0
    expected_equity = enterprise_value - nd - mi - pf + cl
    residual = equity_value - expected_equity
    residual_pct = abs(residual) / max(abs(enterprise_value), 1.0)
    if residual_pct <= 0.01:
        return BandCheck(
            metric="ev_walk", observed=residual, verdict=VERDICT_IN_BAND,
            rationale=f"EV walk reconciles to equity value within {residual_pct*100:.2f}%.",
            partner_note="Walk is clean.",
        )
    if residual_pct <= 0.03:
        return BandCheck(
            metric="ev_walk", observed=residual, verdict=VERDICT_STRETCH,
            rationale=(
                f"EV walk off by {residual_pct*100:.2f}% — may be rounding, "
                "but worth verifying."
            ),
            partner_note="Chase the residual. 2-3% usually means a missed pension or lease liability.",
        )
    verdict = (VERDICT_IMPLAUSIBLE if residual_pct > 0.10
               else VERDICT_OUT_OF_BAND)
    return BandCheck(
        metric="ev_walk", observed=residual, verdict=verdict,
        rationale=(
            f"EV walk off by {residual_pct*100:.2f}% (${residual:,.0f} residual). "
            "Something is missing from the bridge."
        ),
        partner_note=(
            "Do not present this walk at IC until it reconciles. The usual "
            "suspects are minority interest, preferred stock, or "
            "capitalized operating leases."
        ),
    )


# ── Terminal value share of DCF ──────────────────────────────────────
# Terminal value typically contributes 60-80% of DCF for a healthcare
# business with a 5-10 year explicit forecast. Above 85% means the
# model is telling you "the future is all about the terminal" —
# partners want to see the explicit forecast doing meaningful work.

TV_SHARE_IN_BAND = (0.55, 0.80)
TV_SHARE_STRETCH = (0.45, 0.88)
TV_SHARE_IMPLAUSIBLE_LOW = 0.30
TV_SHARE_IMPLAUSIBLE_HIGH = 0.95


def check_terminal_value_share(
    tv_pv: Optional[float],
    total_ev_pv: Optional[float],
) -> BandCheck:
    """Classify the share of DCF EV coming from terminal value."""
    if tv_pv is None or total_ev_pv is None or total_ev_pv == 0:
        return BandCheck(
            metric="terminal_value_share", observed=None, verdict=VERDICT_UNKNOWN,
            rationale="DCF component values not provided.",
        )
    share = tv_pv / total_ev_pv
    if TV_SHARE_IN_BAND[0] <= share <= TV_SHARE_IN_BAND[1]:
        return BandCheck(
            metric="terminal_value_share", observed=share, verdict=VERDICT_IN_BAND,
            rationale=f"Terminal value is {share*100:.0f}% of DCF EV — standard range.",
            partner_note="Explicit period is doing meaningful work.",
        )
    if share <= TV_SHARE_IMPLAUSIBLE_LOW or share >= TV_SHARE_IMPLAUSIBLE_HIGH:
        return BandCheck(
            metric="terminal_value_share", observed=share, verdict=VERDICT_IMPLAUSIBLE,
            rationale=(
                f"Terminal value is {share*100:.0f}% of DCF EV — "
                "outside any defensible range."
            ),
            partner_note="Model looks broken. Re-check the TV growth rate and discount method.",
        )
    if TV_SHARE_STRETCH[0] <= share <= TV_SHARE_STRETCH[1]:
        partner_note = (
            "High TV dependency — the deal is betting on perpetuity growth."
            if share > 0.80 else
            "Low TV share — explicit forecast is unusually front-loaded."
        )
        return BandCheck(
            metric="terminal_value_share", observed=share, verdict=VERDICT_STRETCH,
            rationale=f"Terminal value is {share*100:.0f}% of DCF EV.",
            partner_note=partner_note,
        )
    return BandCheck(
        metric="terminal_value_share", observed=share, verdict=VERDICT_OUT_OF_BAND,
        rationale=f"Terminal value is {share*100:.0f}% of DCF EV.",
        partner_note="Look at the TV growth rate — is it above steady-state GDP? If yes, haircut it.",
    )


# ── Terminal growth rate ─────────────────────────────────────────────
# Perpetuity growth should not exceed long-run nominal GDP (~2-3%).
# Healthcare has demographic tailwind but that's not a perpetuity.

def check_terminal_growth(g: Optional[float]) -> BandCheck:
    """Classify a terminal growth rate."""
    if g is None:
        return BandCheck(
            metric="terminal_growth", observed=None, verdict=VERDICT_UNKNOWN,
            rationale="Terminal growth rate not provided.",
        )
    if 0.015 <= g <= 0.030:
        return BandCheck(
            metric="terminal_growth", observed=g, verdict=VERDICT_IN_BAND,
            rationale=f"Terminal growth of {g*100:.1f}% is within long-run nominal GDP range.",
            partner_note="Reasonable.",
        )
    if 0.005 <= g <= 0.040:
        return BandCheck(
            metric="terminal_growth", observed=g, verdict=VERDICT_STRETCH,
            rationale=f"Terminal growth of {g*100:.1f}% is outside the 1.5–3.0% core range.",
            partner_note="Defend the rate — healthcare demographics aren't a perpetuity.",
        )
    if g < 0 or g > 0.055:
        return BandCheck(
            metric="terminal_growth", observed=g, verdict=VERDICT_IMPLAUSIBLE,
            rationale=f"Terminal growth of {g*100:.1f}% is outside any defensible range.",
            partner_note="A perpetuity cannot grow faster than the overall economy — cap at 3%.",
        )
    return BandCheck(
        metric="terminal_growth", observed=g, verdict=VERDICT_OUT_OF_BAND,
        rationale=f"Terminal growth of {g*100:.1f}% is outside the peer range.",
        partner_note="Lower to 2-3% or justify with a specific demographic thesis.",
    )


# ── Debt coverage / interest coverage ────────────────────────────────
# EBITDA / interest < 2.0 is covenant territory. < 1.5 means the deal
# is paying its debt from working-capital release, which doesn't
# compound.

def check_interest_coverage(coverage: Optional[float]) -> BandCheck:
    """Classify an EBITDA/interest coverage ratio."""
    if coverage is None:
        return BandCheck(
            metric="interest_coverage", observed=None, verdict=VERDICT_UNKNOWN,
            rationale="Interest coverage not provided.",
        )
    if coverage >= 3.0:
        return BandCheck(
            metric="interest_coverage", observed=coverage, verdict=VERDICT_IN_BAND,
            rationale=f"EBITDA/interest at {coverage:.1f}x — comfortable.",
            partner_note="Coverage is fine.",
        )
    if coverage >= 2.0:
        return BandCheck(
            metric="interest_coverage", observed=coverage, verdict=VERDICT_STRETCH,
            rationale=f"EBITDA/interest at {coverage:.1f}x — tight but serviceable.",
            partner_note="Watch the quarterly variance — one miss and we're in waiver territory.",
        )
    if coverage >= 1.5:
        return BandCheck(
            metric="interest_coverage", observed=coverage, verdict=VERDICT_OUT_OF_BAND,
            rationale=f"EBITDA/interest at {coverage:.1f}x — very tight.",
            partner_note="At this coverage a single bad quarter triggers a conversation with the lender.",
        )
    return BandCheck(
        metric="interest_coverage", observed=coverage, verdict=VERDICT_IMPLAUSIBLE,
        rationale=f"EBITDA/interest at {coverage:.1f}x — below covenant floor.",
        partner_note="Deal cannot service its debt at modeled EBITDA. Re-cap or pass.",
    )


# ── Equity check size sanity ─────────────────────────────────────────
# Equity cheque > 35% of fund size = concentration risk at fund level.

def check_equity_concentration(
    equity_check: Optional[float],
    fund_size: Optional[float],
) -> BandCheck:
    if equity_check is None or fund_size is None or fund_size <= 0:
        return BandCheck(
            metric="equity_concentration", observed=None, verdict=VERDICT_UNKNOWN,
            rationale="Equity check or fund size missing.",
        )
    share = equity_check / fund_size
    if share <= 0.15:
        return BandCheck(
            metric="equity_concentration", observed=share, verdict=VERDICT_IN_BAND,
            rationale=f"Equity is {share*100:.1f}% of fund — diversified.",
            partner_note="No concentration concern.",
        )
    if share <= 0.25:
        return BandCheck(
            metric="equity_concentration", observed=share, verdict=VERDICT_STRETCH,
            rationale=f"Equity is {share*100:.1f}% of fund — meaningful but acceptable.",
            partner_note="Make sure LP concentration language permits this.",
        )
    if share <= 0.35:
        return BandCheck(
            metric="equity_concentration", observed=share, verdict=VERDICT_OUT_OF_BAND,
            rationale=f"Equity is {share*100:.1f}% of fund — concentration risk.",
            partner_note="Consider co-invest syndication. LPs will notice at this size.",
        )
    return BandCheck(
        metric="equity_concentration", observed=share, verdict=VERDICT_IMPLAUSIBLE,
        rationale=f"Equity is {share*100:.1f}% of fund — fund concentration limit territory.",
        partner_note="Hard pass unless this is the fund's anchor deal by design.",
    )


# ── Aggregator ───────────────────────────────────────────────────────

@dataclass
class ValuationInputs:
    wacc: Optional[float] = None
    enterprise_value: Optional[float] = None
    equity_value: Optional[float] = None
    net_debt: Optional[float] = None
    minority_interest: Optional[float] = None
    preferred: Optional[float] = None
    cash_like: Optional[float] = None
    tv_pv: Optional[float] = None
    total_dcf_ev: Optional[float] = None
    terminal_growth: Optional[float] = None
    interest_coverage: Optional[float] = None
    equity_check: Optional[float] = None
    fund_size: Optional[float] = None


def run_valuation_checks(inputs: ValuationInputs) -> List[BandCheck]:
    """Run every available valuation check, skipping those without inputs."""
    out: List[BandCheck] = []
    out.append(check_wacc(inputs.wacc))
    out.append(check_ev_walk(
        enterprise_value=inputs.enterprise_value,
        equity_value=inputs.equity_value,
        net_debt=inputs.net_debt,
        minority_interest=inputs.minority_interest,
        preferred=inputs.preferred,
        cash_like=inputs.cash_like,
    ))
    out.append(check_terminal_value_share(inputs.tv_pv, inputs.total_dcf_ev))
    out.append(check_terminal_growth(inputs.terminal_growth))
    out.append(check_interest_coverage(inputs.interest_coverage))
    out.append(check_equity_concentration(inputs.equity_check, inputs.fund_size))
    return out
