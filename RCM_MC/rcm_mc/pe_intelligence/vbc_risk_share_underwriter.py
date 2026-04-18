"""VBC risk-share underwriter — model the MLR corridor, stop-loss, EBITDA volatility.

Partner statement: "Value-based care contracts look
like growth on the deck. The math is harder. We're
taking medical-loss risk on a population we don't
fully control. PMPM × lives = revenue. Medical
expense × lives = COGS. The corridor between them is
EBITDA. Move the corridor by 1% and EBITDA moves a
lot — sometimes from positive to negative. Before I
underwrite a VBC contract, I want the MLR breakeven,
the corridor sensitivity, and the stop-loss
attachment point in dollars."

Distinct from:
- `medicare_advantage_bridge_trap` — narrow on MA
  growth-vs-FFS narrative.
- `payer_mix_risk` — payer-mix concentration.

This module sizes the **EBITDA exposure of a single
VBC contract** given:
- attributed lives
- contracted PMPM
- target / expected MLR
- corridor structure (upside cap, downside floor)
- stop-loss attachment

### Output

- breakeven MLR
- expected EBITDA at target MLR
- bear-case EBITDA at +5pp MLR
- bull-case EBITDA at -5pp MLR
- effective stop-loss protection $
- volatility band ($M EBITDA at ±5pp MLR)
- partner verdict: profitable / breakeven / loss-zone
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class VBCContractInputs:
    contract_name: str = "VBC contract"
    attributed_lives: int = 25_000
    contracted_pmpm: float = 950.0
    target_mlr_pct: float = 0.85
    expected_actual_mlr_pct: float = 0.84
    admin_load_pct_of_pmpm: float = 0.05
    # corridor:
    upside_cap_mlr_delta_pct: float = 0.05
    downside_floor_mlr_delta_pct: float = 0.05
    upside_share_pct: float = 0.50
    downside_share_pct: float = 0.50
    # stop-loss attachment per member per year ($)
    individual_stop_loss_attachment_usd: float = 100_000.0
    individual_stop_loss_premium_pmpm: float = 12.0
    # population stop-loss as % of expected medical
    population_stop_loss_attachment_pct: float = 1.10
    population_stop_loss_premium_pmpm: float = 8.0


@dataclass
class VBCResult:
    label: str
    mlr_pct: float
    medical_expense_m: float
    revenue_m: float
    admin_m: float
    stop_loss_premium_m: float
    raw_corridor_share_m: float
    ebitda_m: float


@dataclass
class VBCRiskShareReport:
    contract_name: str = ""
    attributed_lives: int = 0
    revenue_m: float = 0.0
    admin_m: float = 0.0
    stop_loss_premium_m: float = 0.0
    breakeven_mlr_pct: float = 0.0
    expected_result: Optional[VBCResult] = None
    bear_result: Optional[VBCResult] = None
    bull_result: Optional[VBCResult] = None
    volatility_band_m: float = 0.0
    verdict: str = "profitable"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        def _dump(r: Optional[VBCResult]) -> Optional[Dict[str, Any]]:
            if r is None:
                return None
            return {
                "label": r.label,
                "mlr_pct": r.mlr_pct,
                "medical_expense_m":
                    r.medical_expense_m,
                "revenue_m": r.revenue_m,
                "admin_m": r.admin_m,
                "stop_loss_premium_m":
                    r.stop_loss_premium_m,
                "raw_corridor_share_m":
                    r.raw_corridor_share_m,
                "ebitda_m": r.ebitda_m,
            }
        return {
            "contract_name": self.contract_name,
            "attributed_lives":
                self.attributed_lives,
            "revenue_m": self.revenue_m,
            "admin_m": self.admin_m,
            "stop_loss_premium_m":
                self.stop_loss_premium_m,
            "breakeven_mlr_pct":
                self.breakeven_mlr_pct,
            "expected_result":
                _dump(self.expected_result),
            "bear_result": _dump(self.bear_result),
            "bull_result": _dump(self.bull_result),
            "volatility_band_m":
                self.volatility_band_m,
            "verdict": self.verdict,
            "partner_note": self.partner_note,
        }


def _compute_at_mlr(
    inputs: VBCContractInputs,
    label: str,
    actual_mlr_pct: float,
    revenue_m: float,
    admin_m: float,
    stop_loss_premium_m: float,
) -> VBCResult:
    medical_expense_m = revenue_m * actual_mlr_pct
    raw_gain = (
        revenue_m * (inputs.target_mlr_pct - actual_mlr_pct)
    )
    # apply corridor: if gain is positive, upside share
    # caps at upside_cap; if negative, downside share
    # caps at downside_floor.
    upside_cap_dollars = (
        revenue_m * inputs.upside_cap_mlr_delta_pct
    )
    downside_floor_dollars = (
        revenue_m * inputs.downside_floor_mlr_delta_pct
    )
    if raw_gain >= 0:
        capped = min(raw_gain, upside_cap_dollars)
        corridor_share = capped * inputs.upside_share_pct
    else:
        floored = max(raw_gain, -downside_floor_dollars)
        corridor_share = floored * inputs.downside_share_pct
    ebitda = (
        corridor_share - admin_m - stop_loss_premium_m
    )
    return VBCResult(
        label=label,
        mlr_pct=round(actual_mlr_pct, 4),
        medical_expense_m=round(medical_expense_m, 2),
        revenue_m=round(revenue_m, 2),
        admin_m=round(admin_m, 2),
        stop_loss_premium_m=round(stop_loss_premium_m, 2),
        raw_corridor_share_m=round(corridor_share, 2),
        ebitda_m=round(ebitda, 2),
    )


def underwrite_vbc_contract(
    inputs: VBCContractInputs,
) -> VBCRiskShareReport:
    lives = inputs.attributed_lives
    pmpm = inputs.contracted_pmpm
    revenue_m = lives * pmpm * 12 / 1_000_000
    admin_m = (
        revenue_m * inputs.admin_load_pct_of_pmpm
    )
    stop_loss_premium_m = (
        lives * (
            inputs.individual_stop_loss_premium_pmpm +
            inputs.population_stop_loss_premium_pmpm
        ) * 12 / 1_000_000
    )

    expected = _compute_at_mlr(
        inputs, "expected",
        inputs.expected_actual_mlr_pct,
        revenue_m, admin_m, stop_loss_premium_m,
    )
    bear = _compute_at_mlr(
        inputs, "bear (+5pp MLR)",
        inputs.expected_actual_mlr_pct + 0.05,
        revenue_m, admin_m, stop_loss_premium_m,
    )
    bull = _compute_at_mlr(
        inputs, "bull (-5pp MLR)",
        inputs.expected_actual_mlr_pct - 0.05,
        revenue_m, admin_m, stop_loss_premium_m,
    )

    volatility = bull.ebitda_m - bear.ebitda_m

    # Breakeven MLR: solve for MLR where EBITDA = 0
    # ebitda = corridor_share - admin - stop_loss
    # Within upside zone: corridor_share = (target - mlr) * revenue * upside_share
    # = admin + stop_loss
    # → target - mlr = (admin + stop_loss) / (revenue * upside_share)
    # → mlr = target - (admin + stop_loss) / (revenue * upside_share)
    if (revenue_m > 0 and inputs.upside_share_pct > 0):
        breakeven = inputs.target_mlr_pct - (
            (admin_m + stop_loss_premium_m) /
            (revenue_m * inputs.upside_share_pct)
        )
    else:
        breakeven = 0.0

    if expected.ebitda_m > revenue_m * 0.02:
        verdict = "profitable"
        note = (
            f"Expected EBITDA ${expected.ebitda_m:.1f}M "
            f"on ${revenue_m:.1f}M revenue. Breakeven "
            f"MLR {breakeven:.1%} vs. expected "
            f"{inputs.expected_actual_mlr_pct:.1%}. "
            "Solid margin; verify population risk-"
            "adjustment and prior-period MLR trend."
        )
    elif expected.ebitda_m > 0:
        verdict = "thin_margin"
        note = (
            f"Thin: only ${expected.ebitda_m:.1f}M "
            f"EBITDA. Volatility band ±5pp MLR is "
            f"${volatility:.1f}M — a single bad cohort "
            "wipes the year. Negotiate higher PMPM or "
            "wider corridor."
        )
    elif expected.ebitda_m > -volatility * 0.5:
        verdict = "breakeven_zone"
        note = (
            f"Near breakeven (${expected.ebitda_m:.1f}M "
            f"EBITDA). MLR breakeven is "
            f"{breakeven:.1%}; we're "
            f"{(inputs.expected_actual_mlr_pct - breakeven) * 100:+.1f}pp "
            "into loss territory before any volatility."
        )
    else:
        verdict = "loss_zone"
        note = (
            f"Loss zone: ${expected.ebitda_m:.1f}M EBITDA. "
            "Either renegotiate corridor / PMPM or do "
            "not assume EBITDA contribution from this "
            "contract."
        )

    return VBCRiskShareReport(
        contract_name=inputs.contract_name,
        attributed_lives=lives,
        revenue_m=round(revenue_m, 2),
        admin_m=round(admin_m, 2),
        stop_loss_premium_m=round(stop_loss_premium_m, 2),
        breakeven_mlr_pct=round(breakeven, 4),
        expected_result=expected,
        bear_result=bear,
        bull_result=bull,
        volatility_band_m=round(volatility, 2),
        verdict=verdict,
        partner_note=note,
    )


def render_vbc_underwrite_markdown(
    r: VBCRiskShareReport,
) -> str:
    lines = [
        "# VBC risk-share underwrite",
        "",
        f"_{r.contract_name} — verdict: **{r.verdict}**_",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Attributed lives: {r.attributed_lives:,}",
        f"- Revenue: ${r.revenue_m:.1f}M",
        f"- Admin: ${r.admin_m:.2f}M",
        f"- Stop-loss premium: "
        f"${r.stop_loss_premium_m:.2f}M",
        f"- Breakeven MLR: {r.breakeven_mlr_pct:.1%}",
        f"- Volatility band (±5pp MLR): "
        f"${r.volatility_band_m:.1f}M",
        "",
        "| Scenario | MLR | EBITDA |",
        "|---|---|---|",
    ]
    for res in [r.expected_result, r.bear_result, r.bull_result]:
        if res is None:
            continue
        lines.append(
            f"| {res.label} | {res.mlr_pct:.1%} | "
            f"${res.ebitda_m:+.2f}M |"
        )
    return "\n".join(lines)
