"""Medicare Advantage bridge — does the MA math actually cover FFS pressure?

Partner statement: "The 'Medicare Advantage will make
it up' line is reflex narrative. Sellers use it to
paper over FFS rate cuts, sponsors use it to justify
growth assumptions in the exit case. Force the math:
how many MA lives do you need at the PMPM you're
actually contracted at to replace a 2% FFS rate cut?
Usually: a lot more than the CIM claims. And the
PMPM includes cap-at-risk, which is smaller than
gross billed. Run the bridge."

Distinct from:
- `payer_mix_risk` — static pie chart.
- `payer_renegotiation_timing_model` — commercial
  payer contract calendar.
- `reimbursement_cliff_calendar_2026_2029` — reg
  events.

This module computes the explicit question: **does
projected MA growth offset projected FFS pressure at
realistic contracted PMPMs, or is the seller / model
selling a bridge that doesn't clear?**

### The MA bridge math

FFS pressure annual $ impact:
`ffs_revenue × ffs_annual_rate_cut_pct`

MA gross-up annual $ impact from growth:
`ma_lives_added × net_pmpm_per_life × 12`

The hit: `net_pmpm` is typically 55-75% of gross
Medicare FFS billing because MA plans push into
cap-at-risk, MLR rebates, STAR bonuses with withhold.

Partner's skeptic lens: if the claim is "we'll grow
MA by 15% a year and that covers it," check:

- Are MA lives currently known? Is growth extrapolated
  or driven by a named contract?
- Is the PMPM gross or net? Contractually fixed or
  subject to STAR / quality adjustments?
- Does the MA growth cannibalize FFS? Gross
  adjustment is wrong — only net-new lives count.

### The trap patterns

1. **ma_growth_too_aggressive** — implied MA life
   growth > 20% annually without named contract
   evidence.
2. **pmpm_gross_not_net** — PMPM reported in model is
   gross Medicare, not net after risk-sharing.
3. **ffs_cannibalization_ignored** — MA growth pulls
   from existing FFS panel rather than adds new lives.
4. **ma_pmpm_below_ffs_net** — MA net PMPM is
   actually lower than FFS per-patient net, so growing
   MA reduces per-patient margin.

### Output

- Bridge coverage ratio: `ma_annual_gain / ffs_annual_loss`.
- Required MA lives to close the gap at the
  realistic net PMPM.
- Trap list (which of 4 traps applies).
- Partner note: "bridge clears" / "bridge underwater"
  / "bridge is a story."
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MABridgeInputs:
    # Current state
    ffs_annual_revenue_m: float = 60.0
    ffs_annual_rate_cut_pct: float = 0.02
    ma_lives_current: int = 8000
    # Assumed / claimed
    ma_lives_growth_rate_annual: float = 0.12
    ma_pmpm_claimed: float = 900.0     # $/mo/life
    # Realism adjustments
    pmpm_is_gross: bool = True          # if True, apply net-down
    net_pmpm_realization_pct: float = 0.65
    ma_contract_is_named: bool = False   # named contract or just pipeline
    ma_cannibalization_pct: float = 0.40  # share of MA growth that was FFS
    ffs_pmpm_net: float = 700.0          # per-life FFS net
    projection_years: int = 3


@dataclass
class MABridgeReport:
    ffs_annual_loss_m: float = 0.0
    ma_net_pmpm: float = 0.0
    ma_annual_gain_m: float = 0.0
    bridge_coverage_ratio: float = 0.0
    required_ma_lives_to_close: int = 0
    traps_triggered: List[str] = field(default_factory=list)
    verdict: str = "bridge_clears"
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ffs_annual_loss_m": self.ffs_annual_loss_m,
            "ma_net_pmpm": self.ma_net_pmpm,
            "ma_annual_gain_m": self.ma_annual_gain_m,
            "bridge_coverage_ratio":
                self.bridge_coverage_ratio,
            "required_ma_lives_to_close":
                self.required_ma_lives_to_close,
            "traps_triggered": self.traps_triggered,
            "verdict": self.verdict,
            "partner_note": self.partner_note,
        }


def analyze_ma_bridge(
    inputs: MABridgeInputs,
) -> MABridgeReport:
    # FFS annual loss
    ffs_loss = (
        inputs.ffs_annual_revenue_m *
        inputs.ffs_annual_rate_cut_pct
    )

    # Net PMPM realization
    net_pmpm = (
        inputs.ma_pmpm_claimed *
        inputs.net_pmpm_realization_pct
        if inputs.pmpm_is_gross
        else inputs.ma_pmpm_claimed
    )

    # Annual new-life additions (net of cannibalization)
    annual_new_lives_gross = int(
        inputs.ma_lives_current *
        inputs.ma_lives_growth_rate_annual
    )
    annual_net_new_lives = int(
        annual_new_lives_gross *
        (1.0 - inputs.ma_cannibalization_pct)
    )

    # Annual gain = net new lives × net PMPM × 12
    ma_gain_annual_m = (
        annual_net_new_lives * net_pmpm * 12 / 1_000_000
    )

    # If cannibalization exists, also subtract FFS
    # revenue lost from that cannibalization —
    # cannibalized FFS lives walked, they lose that
    # ffs_pmpm_net × 12.
    cannibalized_lives = (
        annual_new_lives_gross - annual_net_new_lives
    )
    cannibalization_drag_m = (
        cannibalized_lives * inputs.ffs_pmpm_net * 12 /
        1_000_000
    )
    ma_gain_net_of_cann_m = (
        ma_gain_annual_m - cannibalization_drag_m
    )

    # Coverage ratio
    coverage = (
        ma_gain_net_of_cann_m / ffs_loss
        if ffs_loss > 0 else float("inf")
    )

    # Required MA lives to close gap:
    required_lives = int(
        (ffs_loss * 1_000_000) / (net_pmpm * 12)
        if net_pmpm > 0 else 0
    )

    # Traps
    traps: List[str] = []

    # 1. aggressive growth without named contract
    if (inputs.ma_lives_growth_rate_annual > 0.20 and
            not inputs.ma_contract_is_named):
        traps.append("ma_growth_too_aggressive")

    # 2. gross PMPM reported
    if inputs.pmpm_is_gross:
        traps.append("pmpm_gross_not_net")

    # 3. significant cannibalization
    if inputs.ma_cannibalization_pct >= 0.30:
        traps.append("ffs_cannibalization_ignored")

    # 4. MA net PMPM below FFS net per-patient
    if net_pmpm * 12 < inputs.ffs_pmpm_net * 12:
        traps.append("ma_pmpm_below_ffs_net")

    if coverage >= 1.20:
        verdict = "bridge_clears"
        note = (
            f"MA gain "
            f"${ma_gain_net_of_cann_m:.1f}M/yr covers "
            f"FFS loss ${ffs_loss:.1f}M/yr (coverage "
            f"{coverage:.1f}×). Bridge holds — "
            "but verify the named MA contract exists and "
            "cannibalization assumption is conservative."
        )
    elif coverage >= 0.75:
        verdict = "bridge_tight"
        note = (
            f"MA gain covers "
            f"{coverage:.0%} of FFS loss. Bridge is "
            "tight — any haircut to growth, PMPM, or "
            "cannibalization numbers makes it underwater. "
            f"Need {required_lives:,} net-new MA lives "
            "per year to fully close."
        )
    else:
        verdict = "bridge_underwater"
        note = (
            f"MA gain "
            f"${ma_gain_net_of_cann_m:.2f}M/yr does not "
            f"cover FFS loss ${ffs_loss:.2f}M/yr "
            f"(coverage {coverage:.0%}). "
            f"Need {required_lives:,} MA lives/yr to "
            "close — check the seller's claim against "
            "the contracted PMPM reality. This is the "
            "'MA will make it up' trap."
        )

    if "ma_growth_too_aggressive" in traps:
        note += (
            " Growth rate assumption > 20% without "
            "named contract is not diligence-defensible."
        )
    if "pmpm_gross_not_net" in traps and verdict == "bridge_clears":
        note += (
            " PMPM in the model is gross — actual net "
            "after risk-sharing and STAR adjustments "
            "is typically 55-75% of gross. Re-check with "
            "contracted net."
        )

    return MABridgeReport(
        ffs_annual_loss_m=round(ffs_loss, 2),
        ma_net_pmpm=round(net_pmpm, 2),
        ma_annual_gain_m=round(ma_gain_net_of_cann_m, 2),
        bridge_coverage_ratio=round(coverage, 3),
        required_ma_lives_to_close=required_lives,
        traps_triggered=traps,
        verdict=verdict,
        partner_note=note,
    )


def render_ma_bridge_markdown(r: MABridgeReport) -> str:
    flag = (
        "⚠ underwater" if r.verdict == "bridge_underwater"
        else ("tight" if r.verdict == "bridge_tight"
              else "clears")
    )
    lines = [
        "# Medicare Advantage bridge trap",
        "",
        f"_**{flag}**_ — {r.partner_note}",
        "",
        f"- FFS annual loss: ${r.ffs_annual_loss_m:.2f}M",
        f"- MA annual gain (net of cann.): "
        f"${r.ma_annual_gain_m:.2f}M",
        f"- Bridge coverage: {r.bridge_coverage_ratio:.0%}",
        f"- Net PMPM used: ${r.ma_net_pmpm:.0f}",
        f"- Required MA lives to close: "
        f"{r.required_ma_lives_to_close:,}",
        "",
        "## Traps triggered",
    ]
    if r.traps_triggered:
        for t in r.traps_triggered:
            lines.append(f"- {t}")
    else:
        lines.append("- None")
    return "\n".join(lines)
