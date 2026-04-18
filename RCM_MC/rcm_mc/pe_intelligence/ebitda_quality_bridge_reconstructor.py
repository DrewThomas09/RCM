"""EBITDA quality bridge — seller stated → partner run-rate.

Partner statement: "Seller says $75M EBITDA. By the time
QofE is done, physician comp is normalized, COVID
tailwind is stripped, and pro-forma acquisitions are
haircut, the number I underwrite against is $58M. The
difference isn't a spreadsheet error — it's the entire
deal math."

Connective tissue across four existing layers:
- `qofe_prescreen` — add-back survival.
- `physician_comp_normalization_check` — comp
  adjustments.
- `recurring_vs_onetime_ebitda` — recurring vs cash.
- `capex_intensity_stress` — FCF leg (separately).

This module builds the **explicit bridge** from stated
EBITDA to partner's run-rate EBITDA, showing each
adjustment as a named line.

### Adjustment categories (partner sequence)

1. **Stated** — seller's headline.
2. **QofE add-back haircut** — from qofe_prescreen.
3. **Physician comp normalization haircut** — from
   physician_comp_normalization_check (walk-through
   delta).
4. **COVID / one-time tailwind** — structural
   one-time that isn't an add-back but is in base.
5. **Recurring vs. cash release** — strip cash-release
   share if Y1 / Y2 over 30% of claimed gain.
6. **Pro-forma acquisition haircut** — TTM-ize unclosed
   pro-forma.
7. **Partner run-rate EBITDA** — the number partner
   underwrites off.

### Output

Full bridge with each line's $ delta + partner note on
the biggest line + the exit-multiple impact.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BridgeInputs:
    stated_ebitda_m: float
    qofe_haircut_m: float = 0.0
    physician_comp_normalization_haircut_m: float = 0.0
    covid_tailwind_strip_m: float = 0.0
    cash_release_share_in_y1_gain: float = 0.0  # 0-1
    y1_claimed_ebitda_gain_m: float = 0.0
    pro_forma_acquisition_haircut_m: float = 0.0
    entry_multiple: float = 11.0


@dataclass
class BridgeLine:
    source: str
    delta_m: float                        # negative for haircut
    running_ebitda_m: float
    partner_commentary: str


@dataclass
class BridgeReport:
    stated_ebitda_m: float
    partner_run_rate_ebitda_m: float
    total_haircut_m: float
    total_haircut_pct: float
    ev_delta_m: float                    # at entry multiple
    lines: List[BridgeLine] = field(default_factory=list)
    biggest_haircut_source: str = ""
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stated_ebitda_m": self.stated_ebitda_m,
            "partner_run_rate_ebitda_m":
                self.partner_run_rate_ebitda_m,
            "total_haircut_m": self.total_haircut_m,
            "total_haircut_pct": self.total_haircut_pct,
            "ev_delta_m": self.ev_delta_m,
            "lines": [
                {"source": l.source,
                 "delta_m": l.delta_m,
                 "running_ebitda_m": l.running_ebitda_m,
                 "partner_commentary": l.partner_commentary}
                for l in self.lines
            ],
            "biggest_haircut_source":
                self.biggest_haircut_source,
            "partner_note": self.partner_note,
        }


def build_ebitda_quality_bridge(
    inputs: BridgeInputs,
) -> BridgeReport:
    running = inputs.stated_ebitda_m
    lines: List[BridgeLine] = [BridgeLine(
        source="stated_ebitda",
        delta_m=0.0,
        running_ebitda_m=running,
        partner_commentary="Seller's headline number.",
    )]

    # 1. QofE haircut.
    if inputs.qofe_haircut_m > 0:
        running -= inputs.qofe_haircut_m
        lines.append(BridgeLine(
            source="qofe_addback_haircut",
            delta_m=-round(inputs.qofe_haircut_m, 2),
            running_ebitda_m=round(running, 2),
            partner_commentary=(
                "QofE strips non-surviving add-backs "
                "(COVID windfall, deferred capex-as-opex, "
                "pro-forma acquisitions)."
            ),
        ))

    # 2. Physician comp normalization.
    if inputs.physician_comp_normalization_haircut_m > 0:
        running -= inputs.physician_comp_normalization_haircut_m
        lines.append(BridgeLine(
            source="physician_comp_normalization",
            delta_m=-round(
                inputs.physician_comp_normalization_haircut_m,
                2,
            ),
            running_ebitda_m=round(running, 2),
            partner_commentary=(
                "Comp-normalization adjustments that don't "
                "survive operator reality (churn + market "
                "rate variance)."
            ),
        ))

    # 3. COVID / one-time strip.
    if inputs.covid_tailwind_strip_m > 0:
        running -= inputs.covid_tailwind_strip_m
        lines.append(BridgeLine(
            source="covid_tailwind_strip",
            delta_m=-round(inputs.covid_tailwind_strip_m, 2),
            running_ebitda_m=round(running, 2),
            partner_commentary=(
                "COVID-era structural one-time; not in "
                "QofE add-backs but still not recurring."
            ),
        ))

    # 4. Cash-release share.
    if (inputs.cash_release_share_in_y1_gain > 0.30
            and inputs.y1_claimed_ebitda_gain_m > 0):
        # Strip 50% of the cash-release portion — partner
        # doesn't credit it toward run-rate.
        cash_strip = (
            inputs.y1_claimed_ebitda_gain_m
            * inputs.cash_release_share_in_y1_gain
            * 0.5
        )
        running -= cash_strip
        lines.append(BridgeLine(
            source="cash_release_strip",
            delta_m=-round(cash_strip, 2),
            running_ebitda_m=round(running, 2),
            partner_commentary=(
                f"Y1 claimed gain "
                f"${inputs.y1_claimed_ebitda_gain_m:,.1f}M "
                f"is "
                f"{inputs.cash_release_share_in_y1_gain*100:.0f}% "
                "cash release; strip half — exit "
                "multiple only applies to recurring."
            ),
        ))

    # 5. Pro-forma acquisition haircut.
    if inputs.pro_forma_acquisition_haircut_m > 0:
        running -= inputs.pro_forma_acquisition_haircut_m
        lines.append(BridgeLine(
            source="pro_forma_acquisition_haircut",
            delta_m=-round(
                inputs.pro_forma_acquisition_haircut_m, 2
            ),
            running_ebitda_m=round(running, 2),
            partner_commentary=(
                "Pro-forma acquisitions haircut to TTM-"
                "actual basis (40% retention typical)."
            ),
        ))

    partner_run_rate = round(running, 2)
    total_haircut = round(
        inputs.stated_ebitda_m - partner_run_rate, 2
    )
    haircut_pct = (
        total_haircut / max(0.01, inputs.stated_ebitda_m)
    )

    # EV impact at entry multiple.
    ev_delta = round(total_haircut * inputs.entry_multiple, 2)

    # Biggest haircut source.
    biggest_line = max(
        (l for l in lines if l.delta_m < 0),
        key=lambda l: -l.delta_m,
        default=None,
    )
    biggest = biggest_line.source if biggest_line else ""

    if haircut_pct >= 0.20:
        note = (
            f"Partner run-rate ${partner_run_rate:,.1f}M vs. "
            f"seller stated ${inputs.stated_ebitda_m:,.1f}M "
            f"({haircut_pct*100:.0f}% haircut, "
            f"${ev_delta:,.1f}M of EV impact at entry "
            f"multiple {inputs.entry_multiple:.1f}x). "
            "Partner: do not underwrite off stated EBITDA."
        )
    elif haircut_pct >= 0.10:
        note = (
            f"Material haircut: stated "
            f"${inputs.stated_ebitda_m:,.1f}M → run-rate "
            f"${partner_run_rate:,.1f}M "
            f"({haircut_pct*100:.0f}%). Biggest line: "
            f"{biggest}. Price at run-rate × exit mult."
        )
    elif haircut_pct > 0:
        note = (
            f"Modest haircut "
            f"${total_haircut:,.1f}M "
            f"({haircut_pct*100:.1f}%). Partner "
            f"run-rate ${partner_run_rate:,.1f}M."
        )
    else:
        note = (
            "No material EBITDA quality adjustments. "
            "Partner run-rate = stated EBITDA."
        )

    return BridgeReport(
        stated_ebitda_m=round(inputs.stated_ebitda_m, 2),
        partner_run_rate_ebitda_m=partner_run_rate,
        total_haircut_m=total_haircut,
        total_haircut_pct=round(haircut_pct, 4),
        ev_delta_m=ev_delta,
        lines=lines,
        biggest_haircut_source=biggest,
        partner_note=note,
    )


def render_ebitda_bridge_markdown(
    r: BridgeReport,
) -> str:
    lines = [
        "# EBITDA quality bridge",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Stated EBITDA: ${r.stated_ebitda_m:,.1f}M",
        f"- Partner run-rate EBITDA: "
        f"${r.partner_run_rate_ebitda_m:,.1f}M",
        f"- Haircut: ${r.total_haircut_m:,.1f}M "
        f"({r.total_haircut_pct*100:.1f}%)",
        f"- EV impact at entry multiple: "
        f"${r.ev_delta_m:,.1f}M",
        f"- Biggest haircut source: {r.biggest_haircut_source or 'none'}",
        "",
        "| Source | Δ ($M) | Running ($M) | "
        "Partner commentary |",
        "|---|---|---|---|",
    ]
    for l in r.lines:
        delta_str = (
            f"{l.delta_m:+.1f}"
            if l.delta_m != 0 else "—"
        )
        lines.append(
            f"| {l.source} | {delta_str} | "
            f"${l.running_ebitda_m:,.1f}M | "
            f"{l.partner_commentary} |"
        )
    return "\n".join(lines)
