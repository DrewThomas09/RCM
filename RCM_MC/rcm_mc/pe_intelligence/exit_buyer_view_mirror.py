"""Exit-buyer view mirror — model the next sponsor's IC memo on us.

Partner statement: "Best discipline I learned: when
we're underwriting at entry, write the exit buyer's IC
memo. Year 5, deal-team-of-the-buyer is reading our
sale process. What's their thesis on us? What concerns
do they raise? What's their counter? If I can't write
the buyer's bull case in two sentences and bear case
in two sentences, I don't actually have a clear
exit. The exit isn't a multiple — it's another IC
voting."

Distinct from:
- `buyer_type_fit_analyzer` — 8 buyer profiles & fit
  scores.
- `exit_planning` — exit-readiness checklist.
- `exit_alternative_comparator` — 5 exit paths
  comparison.
- `exit_story` — narrative exit story.

This module is the **first-person mirror**: imagine
you ARE the exit buyer's deal team. Given the post-
hold profile of the asset (size, growth, CMI,
margins, EBITDA quality, payer mix evolution,
regulatory state), produce:

- the buyer's likely 3-line bull case
- the buyer's likely 3-line bear case
- buyer's likely entry multiple
- buyer's diligence focus list (what they'll dig
  into hardest)
- the gap between our exit assumption and the buyer's
  likely reality

### Buyer-profile parametrization

Default buyer profile is the **median PE healthcare
sponsor** in 2031 (assuming 2026 entry + 5-year
hold). The module accepts a buyer-archetype overlay
(strategic / sponsor / continuation / IPO) which
shifts the bull/bear emphasis.

### Output

The buyer's IC memo through-the-mirror. Plus the
"gap" — where our exit assumption diverges from the
buyer's likely entry case.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


BUYER_PROFILE_SPONSOR = "sponsor"
BUYER_PROFILE_STRATEGIC = "strategic"
BUYER_PROFILE_CONTINUATION = "continuation"
BUYER_PROFILE_IPO = "ipo"


@dataclass
class ExitBuyerInputs:
    # Asset profile at exit
    asset_npr_at_exit_m: float = 400.0
    asset_ebitda_at_exit_m: float = 60.0
    growth_rate_organic_pct: float = 0.06
    growth_rate_inorganic_pct: float = 0.04
    payer_mix_commercial_pct_at_exit: float = 0.45
    payer_mix_medicare_pct_at_exit: float = 0.30
    cmi_vs_peer: float = 1.05
    ebitda_quality_score: float = 0.80  # 0-1; QofE survival proxy
    customer_concentration_top_5_pct: float = 0.30
    leverage_at_exit: float = 4.0
    # Regulatory state at exit
    obbba_already_in_run_rate: bool = True
    site_neutral_remaining_arbitrage_m: float = 5.0
    # Our exit assumption
    our_assumed_exit_multiple: float = 12.0
    our_assumed_irr: float = 0.22
    # Buyer
    buyer_profile: str = BUYER_PROFILE_SPONSOR


@dataclass
class BuyerMirrorReport:
    buyer_profile: str = ""
    buyer_bull_case_lines: List[str] = field(
        default_factory=list)
    buyer_bear_case_lines: List[str] = field(
        default_factory=list)
    buyer_likely_entry_multiple: float = 0.0
    buyer_diligence_focus_list: List[str] = field(
        default_factory=list)
    our_exit_assumption_multiple: float = 0.0
    multiple_gap: float = 0.0
    multiple_gap_dollar_m: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "buyer_profile": self.buyer_profile,
            "buyer_bull_case_lines":
                self.buyer_bull_case_lines,
            "buyer_bear_case_lines":
                self.buyer_bear_case_lines,
            "buyer_likely_entry_multiple":
                self.buyer_likely_entry_multiple,
            "buyer_diligence_focus_list":
                self.buyer_diligence_focus_list,
            "our_exit_assumption_multiple":
                self.our_exit_assumption_multiple,
            "multiple_gap": self.multiple_gap,
            "multiple_gap_dollar_m":
                self.multiple_gap_dollar_m,
            "partner_note": self.partner_note,
        }


def _buyer_likely_multiple(
    inputs: ExitBuyerInputs,
) -> float:
    """Coarse buyer-multiple model.

    Base multiple by buyer profile + adjustments for
    EBITDA quality, growth, payer mix, concentration.
    """
    base = {
        BUYER_PROFILE_SPONSOR: 11.0,
        BUYER_PROFILE_STRATEGIC: 13.0,
        BUYER_PROFILE_CONTINUATION: 11.5,
        BUYER_PROFILE_IPO: 14.0,
    }.get(inputs.buyer_profile, 11.0)

    adj = 0.0
    # EBITDA quality (QofE survival proxy)
    if inputs.ebitda_quality_score >= 0.85:
        adj += 0.5
    elif inputs.ebitda_quality_score < 0.65:
        adj -= 1.0
    # Growth
    total_growth = (
        inputs.growth_rate_organic_pct +
        inputs.growth_rate_inorganic_pct
    )
    if total_growth >= 0.12:
        adj += 1.0
    elif total_growth < 0.05:
        adj -= 0.5
    # Payer mix
    if inputs.payer_mix_commercial_pct_at_exit < 0.35:
        adj -= 1.0
    elif inputs.payer_mix_commercial_pct_at_exit >= 0.55:
        adj += 0.5
    # Concentration
    if inputs.customer_concentration_top_5_pct > 0.45:
        adj -= 1.0
    # Leverage at exit (high leverage means need to
    # delever; lower equity offered)
    if inputs.leverage_at_exit > 5.5:
        adj -= 0.5
    return round(base + adj, 1)


def write_exit_buyer_mirror(
    inputs: ExitBuyerInputs,
) -> BuyerMirrorReport:
    bull: List[str] = []
    bear: List[str] = []
    diligence: List[str] = []

    total_growth = (
        inputs.growth_rate_organic_pct +
        inputs.growth_rate_inorganic_pct
    )

    # Bull case
    if total_growth >= 0.10:
        bull.append(
            f"{total_growth:.0%} blended growth "
            "(organic + inorganic) — durable demand and "
            "platform momentum."
        )
    if inputs.payer_mix_commercial_pct_at_exit >= 0.50:
        bull.append(
            f"{inputs.payer_mix_commercial_pct_at_exit:.0%} "
            "commercial payer mix — protected from "
            "Medicare reset risk over our hold."
        )
    if inputs.cmi_vs_peer >= 1.05:
        bull.append(
            f"CMI {inputs.cmi_vs_peer:.2f}× peer median — "
            "evidence of higher-acuity case mix or "
            "documentation discipline."
        )
    if inputs.ebitda_quality_score >= 0.85:
        bull.append(
            "EBITDA quality strong — QofE survives "
            "with minimal haircut."
        )
    if not bull:
        bull.append(
            "Profile is unremarkable — asset trades on "
            "size, not strategic appeal."
        )

    # Bear case
    if inputs.customer_concentration_top_5_pct > 0.40:
        bear.append(
            f"Top-5 customer concentration "
            f"{inputs.customer_concentration_top_5_pct:.0%} — "
            "single-customer exit risk."
        )
    if inputs.payer_mix_medicare_pct_at_exit > 0.40:
        bear.append(
            f"Medicare exposure "
            f"{inputs.payer_mix_medicare_pct_at_exit:.0%} — "
            "annual rate cycle compresses recurring "
            "EBITDA forward."
        )
    if inputs.leverage_at_exit > 5.0:
        bear.append(
            f"{inputs.leverage_at_exit:.1f}× leverage at "
            "exit — buyer absorbs refinancing into "
            "underwriting; discount to multiple."
        )
    if not inputs.obbba_already_in_run_rate:
        bear.append(
            "OBBBA / site-neutral impact still ahead — "
            "buyer must price residual exposure."
        )
    if inputs.site_neutral_remaining_arbitrage_m > 10:
        bear.append(
            f"${inputs.site_neutral_remaining_arbitrage_m:.0f}M "
            "of site-of-service arbitrage still in "
            "EBITDA — vulnerable to next CMS rule cycle."
        )
    if inputs.ebitda_quality_score < 0.70:
        bear.append(
            "EBITDA quality below threshold — buyer's "
            "QofE will haircut. Multiple compresses."
        )
    if total_growth < 0.06:
        bear.append(
            f"{total_growth:.0%} blended growth — below "
            "platform threshold; buyer questions "
            "durability of returns."
        )
    if not bear:
        bear.append(
            "No glaring bear case — but check buyer "
            "diligence focus list for hidden zoom areas."
        )

    # Diligence focus list — what the buyer will dig hardest into
    if inputs.ebitda_quality_score < 0.85:
        diligence.append(
            "Full QofE with line-item add-back review")
    if inputs.customer_concentration_top_5_pct > 0.30:
        diligence.append(
            "Top-5 customer reference calls and contract review")
    if inputs.payer_mix_medicare_pct_at_exit > 0.30:
        diligence.append(
            "CMS rule-cycle sensitivity (next 24 mo)")
    if inputs.cmi_vs_peer > 1.10:
        diligence.append(
            "RAC audit risk on CMI uplift through hold")
    if inputs.leverage_at_exit > 5.0:
        diligence.append(
            "Refi market depth and pricing for the "
            "expected debt package")
    diligence.append(
        "Management retention through close + 12 mo")
    if inputs.site_neutral_remaining_arbitrage_m > 5:
        diligence.append(
            "Service-line site-neutral residual exposure "
            "schedule")

    buyer_mult = _buyer_likely_multiple(inputs)
    multiple_gap = inputs.our_assumed_exit_multiple - buyer_mult
    gap_dollar = (
        multiple_gap * inputs.asset_ebitda_at_exit_m
    )

    if multiple_gap >= 1.5:
        note = (
            f"Our exit assumption ({inputs.our_assumed_exit_multiple:.1f}×) "
            f"materially above likely buyer entry "
            f"({buyer_mult:.1f}×) → ${gap_dollar:.0f}M gap. "
            "Either we have a bid we trust at our number, "
            "or we re-underwrite exit case down."
        )
    elif multiple_gap >= 0.5:
        note = (
            f"Modest gap "
            f"({inputs.our_assumed_exit_multiple:.1f}× vs "
            f"{buyer_mult:.1f}×) — defensible if "
            "platform attributes (growth, CMI) are "
            "strong; price sensitivity at exit."
        )
    elif multiple_gap >= -0.5:
        note = (
            "Exit multiple aligned with likely buyer "
            "entry — clean, no re-underwrite needed."
        )
    else:
        note = (
            "Buyer mirror suggests multiple ABOVE our "
            "exit assumption — under-monetizing. "
            "Either platform attributes are strong "
            "enough to push, or our exit case is "
            "conservative on purpose."
        )

    return BuyerMirrorReport(
        buyer_profile=inputs.buyer_profile,
        buyer_bull_case_lines=bull,
        buyer_bear_case_lines=bear,
        buyer_likely_entry_multiple=buyer_mult,
        buyer_diligence_focus_list=diligence,
        our_exit_assumption_multiple=(
            inputs.our_assumed_exit_multiple),
        multiple_gap=round(multiple_gap, 2),
        multiple_gap_dollar_m=round(gap_dollar, 1),
        partner_note=note,
    )


def render_exit_buyer_mirror_markdown(
    r: BuyerMirrorReport,
) -> str:
    lines = [
        "# Exit-buyer view mirror",
        "",
        f"_Buyer profile: **{r.buyer_profile}**_ — "
        f"{r.partner_note}",
        "",
        f"- Buyer likely entry multiple: "
        f"{r.buyer_likely_entry_multiple:.1f}×",
        f"- Our exit assumption: "
        f"{r.our_exit_assumption_multiple:.1f}×",
        f"- Multiple gap: {r.multiple_gap:+.1f}× = "
        f"${r.multiple_gap_dollar_m:+.0f}M",
        "",
        "## Buyer's bull case",
    ]
    for b in r.buyer_bull_case_lines:
        lines.append(f"- {b}")
    lines.append("")
    lines.append("## Buyer's bear case")
    for b in r.buyer_bear_case_lines:
        lines.append(f"- {b}")
    lines.append("")
    lines.append("## Buyer's diligence focus")
    for d in r.buyer_diligence_focus_list:
        lines.append(f"- {d}")
    return "\n".join(lines)
