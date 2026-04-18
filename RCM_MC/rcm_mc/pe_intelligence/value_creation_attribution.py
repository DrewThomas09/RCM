"""Value creation attribution — where does the MOIC come from?

Partner statement: "I don't just want a 2.5x MOIC. I want
to know what's driving it. Forty percent multiple
expansion means I'm betting on the cycle, not the plan.
I'll take 40 percent from EBITDA growth over 40 percent
from multiple any day."

Distinct from:
- `roic_decomposition` — single-point operating ROIC.
- `exit_math` — entry-to-exit MOIC calculation.
- `rcm_lever_cascade` — lever-level EBITDA propagation.

This module **attributes** projected MOIC across lever
sources, telling the partner which dollars come from
execution vs. from market movement. The thesis dollars
partners trust are the ones they control.

### 6 attribution sources

1. **organic_ebitda_growth** — volume + price at stable
   margin.
2. **margin_expansion** — operating leverage; ops-driven.
3. **m_and_a_inorganic** — EBITDA added via acquisitions.
4. **multiple_expansion** — exit multiple > entry
   multiple.
5. **deleveraging** — debt paydown increases equity
   share of EV.
6. **tax_efficiency_other** — tax structuring, working-
   capital release, etc.

### Partner flags

- `multiple_expansion_share > 30%` — cycle-dependent;
  partner writes "this is a bet on the cycle."
- `m_and_a_share > 40%` — execution-dependent; partner
  writes "this is a roll-up thesis and must be
  priced as such."
- `organic_ebitda_growth > 50%` — partner-preferred;
  "this is an operating thesis."
- `all non-operating sources < 20%` — "the plan lives
  in execution."
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AttributionInputs:
    entry_ebitda_m: float
    entry_multiple: float
    entry_debt_m: float
    exit_ebitda_m: float
    exit_multiple: float
    exit_debt_m: float
    m_and_a_contributed_ebitda_m: float = 0.0
    margin_expansion_contributed_ebitda_m: float = 0.0
    tax_efficiency_other_proceeds_m: float = 0.0


@dataclass
class AttributionComponent:
    source: str
    dollar_contribution_m: float
    share_of_gain_pct: float
    partner_rationale: str


@dataclass
class AttributionReport:
    entry_equity_m: float
    exit_equity_m: float
    total_moic: float
    total_equity_gain_m: float
    components: List[AttributionComponent] = field(default_factory=list)
    multiple_expansion_share_pct: float = 0.0
    m_and_a_share_pct: float = 0.0
    organic_share_pct: float = 0.0
    partner_flags: List[str] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_equity_m": self.entry_equity_m,
            "exit_equity_m": self.exit_equity_m,
            "total_moic": self.total_moic,
            "total_equity_gain_m":
                self.total_equity_gain_m,
            "components": [
                {"source": c.source,
                 "dollar_contribution_m":
                     c.dollar_contribution_m,
                 "share_of_gain_pct": c.share_of_gain_pct,
                 "partner_rationale": c.partner_rationale}
                for c in self.components
            ],
            "multiple_expansion_share_pct":
                self.multiple_expansion_share_pct,
            "m_and_a_share_pct": self.m_and_a_share_pct,
            "organic_share_pct": self.organic_share_pct,
            "partner_flags": list(self.partner_flags),
            "partner_note": self.partner_note,
        }


def attribute_value_creation(
    inputs: AttributionInputs,
) -> AttributionReport:
    entry_ev = inputs.entry_ebitda_m * inputs.entry_multiple
    exit_ev = inputs.exit_ebitda_m * inputs.exit_multiple
    entry_equity = max(0.01,
                        entry_ev - inputs.entry_debt_m)
    exit_equity = max(0.0, exit_ev - inputs.exit_debt_m)
    equity_gain = exit_equity - entry_equity

    moic = exit_equity / entry_equity

    # Attribution by lever.
    # 1. Organic EBITDA growth = (exit - entry - MA - margin)
    organic_delta_ebitda = (
        inputs.exit_ebitda_m
        - inputs.entry_ebitda_m
        - inputs.m_and_a_contributed_ebitda_m
        - inputs.margin_expansion_contributed_ebitda_m
    )
    organic_contribution = max(
        0.0, organic_delta_ebitda * inputs.entry_multiple
    )

    # 2. Margin expansion contribution (at entry multiple).
    margin_contribution = (
        inputs.margin_expansion_contributed_ebitda_m
        * inputs.entry_multiple
    )

    # 3. M&A contribution (at entry multiple).
    ma_contribution = (
        inputs.m_and_a_contributed_ebitda_m
        * inputs.entry_multiple
    )

    # 4. Multiple expansion = exit_ebitda × (exit_mult -
    # entry_mult).
    multiple_contribution = (
        inputs.exit_ebitda_m
        * (inputs.exit_multiple - inputs.entry_multiple)
    )

    # 5. Deleveraging = entry_debt - exit_debt (increases
    # equity share of EV).
    deleveraging_contribution = (
        inputs.entry_debt_m - inputs.exit_debt_m
    )

    # 6. Tax efficiency / other.
    other_contribution = inputs.tax_efficiency_other_proceeds_m

    raw_components = [
        ("organic_ebitda_growth", organic_contribution),
        ("margin_expansion", margin_contribution),
        ("m_and_a_inorganic", ma_contribution),
        ("multiple_expansion", multiple_contribution),
        ("deleveraging", deleveraging_contribution),
        ("tax_efficiency_other", other_contribution),
    ]

    total_raw = sum(v for _, v in raw_components)
    denom = total_raw if abs(total_raw) > 0.01 else 1.0

    components: List[AttributionComponent] = []
    for name, val in raw_components:
        share_pct = round(val / denom * 100.0, 1)
        components.append(AttributionComponent(
            source=name,
            dollar_contribution_m=round(val, 2),
            share_of_gain_pct=share_pct,
            partner_rationale=_rationale(name, val, share_pct),
        ))

    multiple_share = next(
        c.share_of_gain_pct for c in components
        if c.source == "multiple_expansion"
    )
    ma_share = next(
        c.share_of_gain_pct for c in components
        if c.source == "m_and_a_inorganic"
    )
    organic_share = next(
        c.share_of_gain_pct for c in components
        if c.source == "organic_ebitda_growth"
    )
    margin_share = next(
        c.share_of_gain_pct for c in components
        if c.source == "margin_expansion"
    )

    flags: List[str] = []
    if multiple_share > 30:
        flags.append(
            f"Multiple-expansion share {multiple_share:.0f}% "
            "> 30% — cycle-dependent."
        )
    if ma_share > 40:
        flags.append(
            f"M&A share {ma_share:.0f}% > 40% — roll-up "
            "thesis; must be priced accordingly."
        )
    if (organic_share + margin_share) < 20:
        flags.append(
            "Operating sources < 20% of gain — plan "
            "does not live in execution."
        )

    # Partner note.
    if multiple_share > 40:
        note = (
            f"MOIC {moic:.2f}x with {multiple_share:.0f}% "
            "from multiple expansion. Partner: this is a "
            "bet on the cycle, not the plan."
        )
    elif organic_share + margin_share >= 50:
        note = (
            f"MOIC {moic:.2f}x with "
            f"{organic_share + margin_share:.0f}% from "
            "operating sources (organic + margin). "
            "Partner: this is an operating thesis — we "
            "control the outcome."
        )
    elif ma_share > 40:
        note = (
            f"MOIC {moic:.2f}x with {ma_share:.0f}% from "
            "M&A. Partner: this is a roll-up — price "
            "and underwrite as such."
        )
    else:
        note = (
            f"MOIC {moic:.2f}x with balanced attribution. "
            "Partner: proceed; no single source dominates "
            "the return."
        )

    return AttributionReport(
        entry_equity_m=round(entry_equity, 2),
        exit_equity_m=round(exit_equity, 2),
        total_moic=round(moic, 3),
        total_equity_gain_m=round(equity_gain, 2),
        components=components,
        multiple_expansion_share_pct=multiple_share,
        m_and_a_share_pct=ma_share,
        organic_share_pct=organic_share,
        partner_flags=flags,
        partner_note=note,
    )


def _rationale(name: str, val: float, share_pct: float) -> str:
    templates = {
        "organic_ebitda_growth": (
            "Volume + price at stable margin — ops "
            "discipline."
        ),
        "margin_expansion": (
            "Operating leverage from scale or cost-out."
        ),
        "m_and_a_inorganic": (
            "EBITDA added through acquisitions — "
            "execution-dependent."
        ),
        "multiple_expansion": (
            "Exit multiple above entry — cycle-"
            "dependent; partner should stress this."
        ),
        "deleveraging": (
            "Debt paid down during hold — increases "
            "equity share of EV."
        ),
        "tax_efficiency_other": (
            "Tax structuring + WC release."
        ),
    }
    return templates.get(name, "")


def render_attribution_markdown(
    r: AttributionReport,
) -> str:
    lines = [
        "# Value creation attribution",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Entry equity: ${r.entry_equity_m:,.1f}M",
        f"- Exit equity: ${r.exit_equity_m:,.1f}M",
        f"- MOIC: {r.total_moic:.2f}x",
        f"- Equity gain: ${r.total_equity_gain_m:,.1f}M",
        "",
        "| Source | $M | Share | Rationale |",
        "|---|---|---|---|",
    ]
    for c in r.components:
        lines.append(
            f"| {c.source} | "
            f"${c.dollar_contribution_m:,.1f}M | "
            f"{c.share_of_gain_pct:.1f}% | "
            f"{c.partner_rationale} |"
        )
    if r.partner_flags:
        lines.append("")
        lines.append("## Partner flags")
        lines.append("")
        for f in r.partner_flags:
            lines.append(f"- {f}")
    return "\n".join(lines)
