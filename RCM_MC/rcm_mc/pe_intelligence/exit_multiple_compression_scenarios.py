"""Exit-multiple compression scenarios — partner stress test.

Partner statement: "Entry multiples are at cycle-high. If
exit reverts one turn, I lose the thesis. Two turns and
I'm pitching a deal that never works. I want that math
on my desk before I sign the LOI."

Existing `exit_math` computes EV / MOIC / IRR at point
assumptions. This module stress-tests the **exit multiple**
assumption specifically — the one input partners chronically
mis-estimate.

### Compression ladder

Four scenarios are modeled by default: base, -1 turn,
-2 turns, -3 turns on exit multiple. Each produces:

- Exit EV
- Equity proceeds
- MOIC
- IRR

And the module names the **compression turn at which MOIC
falls below 2.0x** — the partner's "can we still invest?"
line.

### Partner commentary

- **None of the compression cases breach 2.0x MOIC** →
  "thesis is robust to multiple-cycle mean reversion."
- **Base MOIC < 2.0x** → "at current entry we're buying
  into a sub-2x even before compression. Walk."
- **-1 turn breaches 2.0x MOIC** → "thesis assumes exit
  multiple holds. Do not sign unless we believe cycle
  stays."
- **-2 turn breaches 2.0x MOIC** → "thesis survives one
  turn of compression. Typical partner comfort zone."
- **-3 turn breaches 2.0x MOIC** → "thesis survives two
  turns. Strong margin of safety."

### Inputs

- `entry_ebitda_m`, `entry_multiple` — entry price = their
  product.
- `equity_check_m` — equity at entry (what partner "puts in").
- `ebitda_growth_pct_per_yr` — annual compound growth.
- `hold_years`.
- `base_exit_multiple` — assumption.
- `compression_turns` — list of turn-reductions to simulate
  (default [0, -1, -2, -3]).

### Worked example

Entry: $75M EBITDA × 11x = $825M EV. Equity $400M (debt
$425M @ 5.67x). Growth 6%/yr. Hold 5 yrs. Base exit 11x.

- Base (0 turns): exit EBITDA $100.4M × 11 = $1,104M;
  equity $679M (ignore debt paydown for simplicity);
  MOIC 1.70x, IRR 11.2%.
- -1 turn: exit $1,004M, MOIC 1.45x.
- -2 turn: exit $904M, MOIC 1.20x.

Partner: "Base isn't even 2x. Walk or cut 1.5 turns off
entry."
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CompressionInputs:
    entry_ebitda_m: float
    entry_multiple: float
    equity_check_m: float
    ebitda_growth_pct_per_yr: float
    hold_years: float
    base_exit_multiple: float
    compression_turns: List[float] = field(
        default_factory=lambda: [0.0, -1.0, -2.0, -3.0]
    )
    debt_paydown_pct_per_yr: float = 0.0   # fraction of debt per year
    moic_comfort_threshold: float = 2.0


@dataclass
class CompressionScenario:
    turns_compression: float
    exit_multiple: float
    exit_ebitda_m: float
    exit_ev_m: float
    equity_proceeds_m: float
    moic: float
    irr_pct: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turns_compression": self.turns_compression,
            "exit_multiple": self.exit_multiple,
            "exit_ebitda_m": self.exit_ebitda_m,
            "exit_ev_m": self.exit_ev_m,
            "equity_proceeds_m": self.equity_proceeds_m,
            "moic": self.moic,
            "irr_pct": self.irr_pct,
        }


@dataclass
class CompressionReport:
    scenarios: List[CompressionScenario] = field(default_factory=list)
    base_moic: float = 0.0
    base_irr_pct: float = 0.0
    compression_turns_to_break_moic: Optional[float] = None
    margin_of_safety_turns: Optional[float] = None
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenarios": [s.to_dict() for s in self.scenarios],
            "base_moic": self.base_moic,
            "base_irr_pct": self.base_irr_pct,
            "compression_turns_to_break_moic":
                self.compression_turns_to_break_moic,
            "margin_of_safety_turns":
                self.margin_of_safety_turns,
            "partner_note": self.partner_note,
        }


def _irr_from_moic(moic: float, hold_years: float) -> float:
    if moic <= 0 or hold_years <= 0:
        return 0.0
    return (moic ** (1.0 / hold_years) - 1.0) * 100.0


def stress_exit_multiple_compression(
    inputs: CompressionInputs,
) -> CompressionReport:
    entry_ev = inputs.entry_ebitda_m * inputs.entry_multiple
    entry_debt = entry_ev - inputs.equity_check_m
    # Exit EBITDA at base growth.
    exit_ebitda = (
        inputs.entry_ebitda_m
        * (1.0 + inputs.ebitda_growth_pct_per_yr)
            ** inputs.hold_years
    )
    # Residual debt after paydown.
    paydown_pct_total = min(
        1.0,
        inputs.debt_paydown_pct_per_yr * inputs.hold_years,
    )
    exit_debt = entry_debt * (1.0 - paydown_pct_total)

    scenarios: List[CompressionScenario] = []
    for turns in inputs.compression_turns:
        exit_mult = max(1.0, inputs.base_exit_multiple + turns)
        exit_ev = exit_ebitda * exit_mult
        equity_proceeds = max(0.0, exit_ev - exit_debt)
        moic = equity_proceeds / max(0.01, inputs.equity_check_m)
        irr_pct = _irr_from_moic(moic, inputs.hold_years)
        scenarios.append(CompressionScenario(
            turns_compression=turns,
            exit_multiple=round(exit_mult, 2),
            exit_ebitda_m=round(exit_ebitda, 2),
            exit_ev_m=round(exit_ev, 2),
            equity_proceeds_m=round(equity_proceeds, 2),
            moic=round(moic, 3),
            irr_pct=round(irr_pct, 2),
        ))

    base = next((s for s in scenarios if s.turns_compression == 0.0),
                 scenarios[0])
    base_moic = base.moic
    base_irr = base.irr_pct

    # Compression turns where MOIC falls below threshold. Iterate
    # from least compressed to most. First turn that is < threshold
    # is the "break" point; the prior turn (more compressed means
    # more negative) defines margin of safety.
    sorted_down = sorted(scenarios,
                          key=lambda s: -s.turns_compression)
    # sorted_down is ordered largest turns (0) → smallest (-3).
    break_turns: Optional[float] = None
    mos: Optional[float] = None
    for s in sorted_down:
        if s.moic < inputs.moic_comfort_threshold:
            break_turns = s.turns_compression
            break
    # Margin of safety = most negative turns where MOIC still ≥
    # threshold (= abs value of that turn count).
    safe_turns = [s.turns_compression for s in scenarios
                   if s.moic >= inputs.moic_comfort_threshold]
    if safe_turns:
        mos = -min(safe_turns)  # worst still safe

    # Partner note.
    if base_moic < inputs.moic_comfort_threshold:
        note = (f"Base MOIC {base_moic:.2f}x already below "
                f"{inputs.moic_comfort_threshold:.1f}x "
                "comfort line. Walk or cut entry 1-1.5x to "
                "restore.")
    elif break_turns is None:
        note = (f"Thesis robust: MOIC holds ≥ "
                f"{inputs.moic_comfort_threshold:.1f}x through "
                f"{-min(s.turns_compression for s in scenarios):.0f} "
                "turns of compression. Strong margin of safety.")
    elif break_turns == 0.0:
        # Should not happen (base already would be below).
        note = (f"Base breaches at {base_moic:.2f}x.")
    elif break_turns == -1.0:
        note = ("One-turn compression breaks 2.0x MOIC. "
                "Thesis assumes exit multiple holds — do "
                "not sign unless we believe cycle stays.")
    elif break_turns == -2.0:
        note = ("Two-turn compression breaks 2.0x. Thesis "
                "survives one turn — typical partner comfort "
                "zone.")
    elif break_turns == -3.0:
        note = ("Three-turn compression breaks 2.0x. Thesis "
                "survives two turns — strong margin of safety.")
    else:
        note = (f"Compression turn {break_turns:+.1f} breaks "
                f"{inputs.moic_comfort_threshold:.1f}x MOIC line.")

    return CompressionReport(
        scenarios=scenarios,
        base_moic=base_moic,
        base_irr_pct=base_irr,
        compression_turns_to_break_moic=break_turns,
        margin_of_safety_turns=mos,
        partner_note=note,
    )


def render_compression_markdown(
    r: CompressionReport,
) -> str:
    lines = [
        "# Exit-multiple compression stress",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Base MOIC: {r.base_moic:.2f}x",
        f"- Base IRR: {r.base_irr_pct:.1f}%",
        f"- Break-MOIC compression turns: "
        f"{r.compression_turns_to_break_moic if r.compression_turns_to_break_moic is not None else '—'}",
        f"- Margin of safety turns: "
        f"{r.margin_of_safety_turns if r.margin_of_safety_turns is not None else '—'}",
        "",
        "| Compression | Exit multiple | Exit EV | Equity | "
        "MOIC | IRR |",
        "|---|---|---|---|---|---|",
    ]
    for s in r.scenarios:
        lines.append(
            f"| {s.turns_compression:+.1f}t | "
            f"{s.exit_multiple:.2f}x | "
            f"${s.exit_ev_m:,.0f}M | "
            f"${s.equity_proceeds_m:,.0f}M | "
            f"{s.moic:.2f}x | "
            f"{s.irr_pct:.1f}% |"
        )
    return "\n".join(lines)
