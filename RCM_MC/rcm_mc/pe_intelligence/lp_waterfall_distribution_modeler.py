"""LP waterfall distribution modeler — preferred / catch-up / carry.

Partner statement: "Every IC pitches a gross MOIC.
LPs see net. Between the two sits the 8% preferred,
the GP catch-up, and the 20% carry split. A 2.5x
gross at 18% IRR often lands at 2.05x net; that's a
big gap when you're pitching LPs on next fund. Model
the waterfall before I send the pitch deck."

Distinct from:
- `fund_level_vintage_impact_scorer` — deal impact on
  fund TVPI.
- `lp_pitch` — raise-era narrative.

This module implements the **standard European-style
waterfall** (deal-by-deal carry not modeled —
aggregate fund view):
1. Return of capital to LPs
2. LP preferred return (8% annual)
3. GP catch-up (100%)
4. Profit split (80/20)

### Output

- LP gross / net MOIC and IRR
- GP carry dollars
- Waterfall step breakdown
- Partner note on LP-net-vs-gross gap
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LPWaterfallInputs:
    committed_capital_m: float = 100.0
    total_proceeds_m: float = 250.0
    hold_years: float = 5.0
    preferred_return_pct: float = 0.08
    carry_pct: float = 0.20
    gp_catchup_pct: float = 1.00  # 100% catch-up to GP
    management_fee_pct_per_year: float = 0.015


@dataclass
class WaterfallStep:
    step: str
    amount_m: float
    to_lp_m: float
    to_gp_m: float


@dataclass
class LPWaterfallReport:
    committed_capital_m: float = 0.0
    total_proceeds_m: float = 0.0
    gross_moic: float = 0.0
    net_lp_moic: float = 0.0
    gross_irr: float = 0.0
    net_lp_irr: float = 0.0
    gp_carry_m: float = 0.0
    gp_mgmt_fees_m: float = 0.0
    steps: List[WaterfallStep] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "committed_capital_m":
                self.committed_capital_m,
            "total_proceeds_m": self.total_proceeds_m,
            "gross_moic": self.gross_moic,
            "net_lp_moic": self.net_lp_moic,
            "gross_irr": self.gross_irr,
            "net_lp_irr": self.net_lp_irr,
            "gp_carry_m": self.gp_carry_m,
            "gp_mgmt_fees_m": self.gp_mgmt_fees_m,
            "steps": [
                {"step": s.step,
                 "amount_m": s.amount_m,
                 "to_lp_m": s.to_lp_m,
                 "to_gp_m": s.to_gp_m}
                for s in self.steps
            ],
            "partner_note": self.partner_note,
        }


def _moic_to_irr(moic: float, years: float) -> float:
    if moic <= 0 or years <= 0:
        return 0.0
    return moic ** (1.0 / years) - 1.0


def model_lp_waterfall(
    inputs: LPWaterfallInputs,
) -> LPWaterfallReport:
    capital = inputs.committed_capital_m
    proceeds = inputs.total_proceeds_m

    # Management fees (reduce LP net)
    mgmt_fees = (
        capital * inputs.management_fee_pct_per_year *
        inputs.hold_years
    )

    # Step 1: return of capital to LP
    step1_amount = min(proceeds, capital)
    proceeds_after_roc = proceeds - step1_amount

    # Step 2: LP preferred return
    # Pref = capital × (1+pref)^years − capital
    target_pref = (
        capital *
        ((1 + inputs.preferred_return_pct) **
         inputs.hold_years) -
        capital
    )
    step2_amount = min(proceeds_after_roc, target_pref)
    proceeds_after_pref = (
        proceeds_after_roc - step2_amount
    )

    # Step 3: GP catch-up — GP gets 100% until they
    # have `carry_pct` of (pref + catchup).
    # Solve: gp_catchup / (step2 + gp_catchup) = carry_pct
    # → gp_catchup = step2 × carry_pct / (1 - carry_pct)
    if step2_amount > 0:
        target_catchup = (
            step2_amount * inputs.carry_pct /
            max(0.01, 1.0 - inputs.carry_pct)
        )
    else:
        target_catchup = 0.0
    step3_amount = min(
        proceeds_after_pref, target_catchup)
    proceeds_after_catchup = (
        proceeds_after_pref - step3_amount
    )

    # Step 4: profit split 80/20
    step4_lp = proceeds_after_catchup * (
        1 - inputs.carry_pct)
    step4_gp = proceeds_after_catchup * inputs.carry_pct

    lp_gross_distribution = (
        step1_amount + step2_amount + step4_lp
    )
    gp_carry = step3_amount + step4_gp

    # Net LP = gross LP distribution − mgmt fees
    net_lp = lp_gross_distribution - mgmt_fees

    gross_moic = proceeds / max(0.01, capital)
    net_lp_moic = net_lp / max(0.01, capital)
    gross_irr = _moic_to_irr(
        gross_moic, inputs.hold_years)
    net_lp_irr = _moic_to_irr(
        net_lp_moic, inputs.hold_years)

    steps = [
        WaterfallStep(
            step="return_of_capital",
            amount_m=round(step1_amount, 2),
            to_lp_m=round(step1_amount, 2),
            to_gp_m=0.0,
        ),
        WaterfallStep(
            step="lp_preferred_return",
            amount_m=round(step2_amount, 2),
            to_lp_m=round(step2_amount, 2),
            to_gp_m=0.0,
        ),
        WaterfallStep(
            step="gp_catchup",
            amount_m=round(step3_amount, 2),
            to_lp_m=0.0,
            to_gp_m=round(step3_amount, 2),
        ),
        WaterfallStep(
            step="80_20_split",
            amount_m=round(
                proceeds_after_catchup, 2),
            to_lp_m=round(step4_lp, 2),
            to_gp_m=round(step4_gp, 2),
        ),
        WaterfallStep(
            step="management_fees_deducted_from_lp",
            amount_m=round(mgmt_fees, 2),
            to_lp_m=round(-mgmt_fees, 2),
            to_gp_m=round(mgmt_fees, 2),
        ),
    ]

    gap_moic = gross_moic - net_lp_moic
    if gap_moic > 0.50:
        note = (
            f"Gross MOIC {gross_moic:.2f}× → LP net "
            f"{net_lp_moic:.2f}× ({gap_moic:+.2f}x gap). "
            "Meaningful carry + fee drag; LP-facing "
            "pitch must lead with net numbers."
        )
    elif gap_moic > 0.25:
        note = (
            f"Gross-net gap {gap_moic:+.2f}x — standard "
            "for the fee/carry structure. Partner "
            "discusses LP-net explicitly."
        )
    else:
        note = (
            f"Thin gross-net gap {gap_moic:+.2f}x — "
            "short hold or low gross return compresses "
            "carry."
        )

    return LPWaterfallReport(
        committed_capital_m=round(capital, 2),
        total_proceeds_m=round(proceeds, 2),
        gross_moic=round(gross_moic, 3),
        net_lp_moic=round(net_lp_moic, 3),
        gross_irr=round(gross_irr, 4),
        net_lp_irr=round(net_lp_irr, 4),
        gp_carry_m=round(gp_carry, 2),
        gp_mgmt_fees_m=round(mgmt_fees, 2),
        steps=steps,
        partner_note=note,
    )


def render_lp_waterfall_markdown(
    r: LPWaterfallReport,
) -> str:
    lines = [
        "# LP waterfall distribution",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Committed: ${r.committed_capital_m:.0f}M",
        f"- Proceeds: ${r.total_proceeds_m:.0f}M",
        f"- Gross MOIC: {r.gross_moic:.2f}× "
        f"(IRR {r.gross_irr:.1%})",
        f"- Net LP MOIC: {r.net_lp_moic:.2f}× "
        f"(IRR {r.net_lp_irr:.1%})",
        f"- GP carry: ${r.gp_carry_m:.1f}M",
        f"- GP mgmt fees: ${r.gp_mgmt_fees_m:.1f}M",
        "",
        "| Step | Amount $M | To LP | To GP |",
        "|---|---|---|---|",
    ]
    for s in r.steps:
        lines.append(
            f"| {s.step} | ${s.amount_m:.1f} | "
            f"${s.to_lp_m:+.1f} | "
            f"${s.to_gp_m:+.1f} |"
        )
    return "\n".join(lines)
