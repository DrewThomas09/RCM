"""Roll-up arbitrage math — platform multiple × tuck-in arbitrage.

Partner statement: "Roll-ups are sold as synergy
stories. The truth is the math is mostly multiple
arbitrage — we buy the platform at 11x, tuck in at
5-6x, and the exit values both blocks at the higher
multiple. If the multiple arbitrage evaporates — same-
multiple exit — most roll-up decks don't clear a 2x.
Show me blended entry, blended exit, and the
decomposition of MOIC into multiple arbitrage vs. real
EBITDA growth vs. financial engineering. If multiple
arbitrage is more than half the MOIC, we're betting on
the multiple, not the company."

Distinct from:
- `deal_archetype` — identifies the archetype.
- `synergy_modeler` — models specific synergy lines.
- `exit_math` — general MOIC/IRR math.
- `value_creation_attribution` — 6-source attribution
  (includes multiple expansion but at a different
  granularity).

This module is roll-up-specific and decomposes MOIC
into four explicit drivers:

1. **Tuck-in multiple arbitrage** — platform paid 11x,
   tuck-ins bought at 6x, both valued at exit at 12x.
   The 5-6 turn delta × tuck-in EBITDA is pure
   arbitrage.
2. **Platform multiple expansion** — platform entered
   at 11x, exits at 12x regardless of tuck-ins. The
   1-turn delta × platform EBITDA is platform-only.
3. **EBITDA growth** — real organic + synergy-realized
   EBITDA beyond tuck-in EBITDA at acquisition run-
   rate.
4. **Financial engineering** — leverage amplification,
   dividend recap, debt paydown.

### The partner skeptic test

If (arbitrage + platform expansion) / MOIC > 0.50,
**this is a multiple bet, not an operating bet.** The
exit thesis depends on the multiple not
compressing. Stress-test with exit multiple = entry
multiple.

### Output

Entry blended multiple, exit blended multiple, MOIC
decomposition, multiple-bet flag, same-multiple-exit
MOIC.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class TuckInDeal:
    name: str
    entry_ebitda_m: float
    entry_multiple: float
    post_synergy_ebitda_m: float = 0.0  # if zero, no synergy uplift


@dataclass
class RollupArbitrageInputs:
    platform_entry_ebitda_m: float = 30.0
    platform_entry_multiple: float = 11.0
    platform_entry_equity_m: float = 120.0  # check + coinvest
    platform_entry_debt_m: float = 210.0
    tuck_ins: List[TuckInDeal] = field(default_factory=list)
    # exit assumptions
    exit_year: int = 5
    exit_ebitda_m: float = 75.0          # at exit, blended
    exit_multiple: float = 12.0
    exit_debt_m: float = 50.0            # paid down


@dataclass
class RollupArbitrageReport:
    blended_entry_multiple: float = 0.0
    blended_entry_ev_m: float = 0.0
    blended_entry_ebitda_m: float = 0.0
    exit_ev_m: float = 0.0
    exit_equity_m: float = 0.0
    base_moic: float = 0.0
    same_multiple_moic: float = 0.0
    tuck_in_arbitrage_m: float = 0.0
    platform_multiple_expansion_m: float = 0.0
    ebitda_growth_m: float = 0.0
    financial_engineering_m: float = 0.0
    moic_pct_from_arbitrage: float = 0.0
    moic_pct_from_multiple_expansion: float = 0.0
    moic_pct_from_ebitda_growth: float = 0.0
    moic_pct_from_financial_engineering: float = 0.0
    multiple_bet_flag: bool = False
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blended_entry_multiple":
                self.blended_entry_multiple,
            "blended_entry_ev_m":
                self.blended_entry_ev_m,
            "blended_entry_ebitda_m":
                self.blended_entry_ebitda_m,
            "exit_ev_m": self.exit_ev_m,
            "exit_equity_m": self.exit_equity_m,
            "base_moic": self.base_moic,
            "same_multiple_moic":
                self.same_multiple_moic,
            "tuck_in_arbitrage_m":
                self.tuck_in_arbitrage_m,
            "platform_multiple_expansion_m":
                self.platform_multiple_expansion_m,
            "ebitda_growth_m": self.ebitda_growth_m,
            "financial_engineering_m":
                self.financial_engineering_m,
            "moic_pct_from_arbitrage":
                self.moic_pct_from_arbitrage,
            "moic_pct_from_multiple_expansion":
                self.moic_pct_from_multiple_expansion,
            "moic_pct_from_ebitda_growth":
                self.moic_pct_from_ebitda_growth,
            "moic_pct_from_financial_engineering":
                self.moic_pct_from_financial_engineering,
            "multiple_bet_flag":
                self.multiple_bet_flag,
            "partner_note": self.partner_note,
        }


def _safe_div(n: float, d: float) -> float:
    return n / d if d else 0.0


def compute_rollup_arbitrage(
    inputs: RollupArbitrageInputs,
) -> RollupArbitrageReport:
    # 1. Blended entry
    total_ebitda_at_entry = inputs.platform_entry_ebitda_m
    total_ev_at_entry = (
        inputs.platform_entry_ebitda_m *
        inputs.platform_entry_multiple
    )
    for t in inputs.tuck_ins:
        total_ebitda_at_entry += t.entry_ebitda_m
        total_ev_at_entry += (
            t.entry_ebitda_m * t.entry_multiple
        )
    blended_multiple = _safe_div(
        total_ev_at_entry, total_ebitda_at_entry
    )

    # 2. Initial sponsor equity — platform equity for
    # simplicity. In practice tuck-ins usually fund from
    # platform balance sheet (debt or follow-on equity),
    # but the partner's lens is sponsor cash deployed.
    sponsor_equity_in = inputs.platform_entry_equity_m

    # 3. Exit EV & exit equity
    exit_ev = inputs.exit_ebitda_m * inputs.exit_multiple
    exit_equity = exit_ev - inputs.exit_debt_m
    base_moic = _safe_div(exit_equity, sponsor_equity_in)

    # 4. Same-multiple exit test
    same_multiple_ev = (
        inputs.exit_ebitda_m * blended_multiple
    )
    same_multiple_equity = (
        same_multiple_ev - inputs.exit_debt_m
    )
    same_multiple_moic = _safe_div(
        same_multiple_equity, sponsor_equity_in
    )

    # 5. Decomposition (all in $M of equity value
    # contribution). Reference frame: platform-only,
    # no tuck-ins, exit at entry multiple, no debt pay-
    # down.
    # (a) Tuck-in arbitrage = tuck-in EBITDA at exit
    # multiple - tuck-in EBITDA at their entry multiple.
    arbitrage = 0.0
    for t in inputs.tuck_ins:
        post = (t.post_synergy_ebitda_m
                if t.post_synergy_ebitda_m > 0
                else t.entry_ebitda_m)
        # held at exit multiple vs. bought at entry
        # multiple — using the acquisition-era ebitda
        # to isolate pure arbitrage, not synergy growth.
        arbitrage += (
            t.entry_ebitda_m *
            (inputs.exit_multiple - t.entry_multiple)
        )
        # synergy growth is attributed to ebitda_growth
        # below via exit_ebitda (which includes post-
        # synergy run-rate).
    # (b) Platform multiple expansion = platform entry
    # EBITDA × (exit_multiple - platform_entry_multiple).
    platform_expansion = (
        inputs.platform_entry_ebitda_m *
        (inputs.exit_multiple -
         inputs.platform_entry_multiple)
    )
    # (c) EBITDA growth = (exit_ebitda - blended entry
    # EBITDA) × exit_multiple, i.e. the EBITDA dollars
    # created after all acquisitions, valued at exit
    # multiple.
    ebitda_delta = max(
        0.0,
        inputs.exit_ebitda_m - total_ebitda_at_entry,
    )
    ebitda_growth = ebitda_delta * inputs.exit_multiple
    # (d) Financial engineering = debt paydown (entry
    # debt - exit debt). Negative if relevered.
    fin_engineering = (
        inputs.platform_entry_debt_m - inputs.exit_debt_m
    )

    # MOIC dollar = exit equity - entry equity
    moic_dollars = exit_equity - sponsor_equity_in
    total_attributed = (
        arbitrage + platform_expansion +
        ebitda_growth + fin_engineering
    )

    # Scale attribution to actual MOIC dollars to close
    # rounding; if attribution exceeds MOIC, cap the
    # pct shares.
    if total_attributed > 0 and moic_dollars > 0:
        scale = moic_dollars / total_attributed
    else:
        scale = 1.0
    arbitrage *= scale
    platform_expansion *= scale
    ebitda_growth *= scale
    fin_engineering *= scale

    def pct(x: float) -> float:
        return round(_safe_div(x, moic_dollars), 4)

    report = RollupArbitrageReport(
        blended_entry_multiple=round(blended_multiple, 2),
        blended_entry_ev_m=round(total_ev_at_entry, 2),
        blended_entry_ebitda_m=round(
            total_ebitda_at_entry, 2),
        exit_ev_m=round(exit_ev, 2),
        exit_equity_m=round(exit_equity, 2),
        base_moic=round(base_moic, 2),
        same_multiple_moic=round(same_multiple_moic, 2),
        tuck_in_arbitrage_m=round(arbitrage, 2),
        platform_multiple_expansion_m=round(
            platform_expansion, 2),
        ebitda_growth_m=round(ebitda_growth, 2),
        financial_engineering_m=round(fin_engineering, 2),
        moic_pct_from_arbitrage=pct(arbitrage),
        moic_pct_from_multiple_expansion=pct(
            platform_expansion),
        moic_pct_from_ebitda_growth=pct(ebitda_growth),
        moic_pct_from_financial_engineering=pct(
            fin_engineering),
    )

    multiple_bet = (
        report.moic_pct_from_arbitrage +
        report.moic_pct_from_multiple_expansion
    )
    report.multiple_bet_flag = multiple_bet > 0.50

    # Partner note
    if report.multiple_bet_flag:
        note = (
            f"{multiple_bet:.0%} of MOIC comes from "
            "multiple arbitrage + platform expansion. "
            "This is a multiple bet, not an operating "
            "bet. Same-multiple-exit MOIC is "
            f"{report.same_multiple_moic:.2f}x — stress "
            "the IC model against a flat exit multiple "
            "before underwriting; do not let the deal "
            "live or die on the multiple not "
            "compressing."
        )
    elif report.moic_pct_from_ebitda_growth > 0.50:
        note = (
            f"{report.moic_pct_from_ebitda_growth:.0%} "
            "of MOIC is real EBITDA growth. This deal "
            "earns its return operationally — "
            "same-multiple-exit MOIC is "
            f"{report.same_multiple_moic:.2f}x, still a "
            "credible case if the exit multiple "
            "compresses."
        )
    elif report.moic_pct_from_financial_engineering > 0.40:
        note = (
            "Financial engineering "
            f"({report.moic_pct_from_financial_engineering:.0%}) "
            "is the biggest MOIC driver. Partner: "
            "acceptable in a stable-cash-flow platform "
            "with low covenant risk; dangerous if "
            "EBITDA is cyclical. Debt-paydown thesis "
            "needs its own stress test."
        )
    else:
        note = (
            "Balanced MOIC decomposition — no single "
            "driver > 50%. Proceed to standard "
            "diligence. Same-multiple-exit MOIC is "
            f"{report.same_multiple_moic:.2f}x."
        )
    report.partner_note = note
    return report


def render_rollup_arbitrage_markdown(
    r: RollupArbitrageReport,
) -> str:
    flag = "⚠ multiple bet" if r.multiple_bet_flag else "balanced"
    lines = [
        "# Roll-up arbitrage math",
        "",
        f"_**{flag}**_ — {r.partner_note}",
        "",
        f"- Blended entry multiple: "
        f"{r.blended_entry_multiple:.2f}x on "
        f"${r.blended_entry_ebitda_m:.1f}M EBITDA",
        f"- Exit EV: ${r.exit_ev_m:.0f}M; "
        f"sponsor equity out: ${r.exit_equity_m:.0f}M",
        f"- Base MOIC: {r.base_moic:.2f}x; "
        f"same-multiple-exit MOIC: "
        f"{r.same_multiple_moic:.2f}x",
        "",
        "| Driver | $M | % of MOIC |",
        "|---|---|---|",
        f"| Tuck-in arbitrage | ${r.tuck_in_arbitrage_m:.1f} | "
        f"{r.moic_pct_from_arbitrage:.0%} |",
        f"| Platform multiple expansion | "
        f"${r.platform_multiple_expansion_m:.1f} | "
        f"{r.moic_pct_from_multiple_expansion:.0%} |",
        f"| EBITDA growth | ${r.ebitda_growth_m:.1f} | "
        f"{r.moic_pct_from_ebitda_growth:.0%} |",
        f"| Financial engineering | "
        f"${r.financial_engineering_m:.1f} | "
        f"{r.moic_pct_from_financial_engineering:.0%} |",
    ]
    return "\n".join(lines)
