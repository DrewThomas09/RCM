"""Connect the dots — trace packet signals through their downstream implications.

Partner statement: "The thing a senior partner does
that a model doesn't: we connect dots. A denial rate
change has coding implications, which have CMI
implications, which change the Medicare bridge math.
A payer-mix shift has case-mix implications, which
have CMI implications, which have IP margin
implications. A DSO jump has working-capital
implications, which have covenant implications, which
have dividend-recap-timing implications. The packet
reports each number in isolation. The brain reads the
chain."

Distinct from:
- `cross_module_connective_tissue` — integrates module
  outputs (summaries).
- `thesis_implications_chain` — thesis-pillar level.

This module traces **packet-level signals** through
named causal chains. Each chain is a partner's head-
model: `X → Y → Z` with dollar / basis-point /
margin impacts estimated at each step. The output is
a set of fired chains that the partner would narrate
at IC: "if denials fall 150 bps, don't cheer yet —
the CMI propped by denials appeals will fall with
it, and the Medicare bridge loses $2M."

### 6 dot-connect chains

1. **denial_fix_to_cmi_to_medicare_bridge** — denial
   fix → coding exposure → CMI reversal → Medicare $.
2. **payer_shift_to_case_mix_to_cmi_to_ip_margin** —
   payer mix shift → case-mix change → CMI → IP margin.
3. **wage_step_to_physcomp_to_ebitda_to_addback_risk**
   — wage step → physician comp → EBITDA → add-back
   stress.
4. **volume_decline_to_fixed_cost_to_covenant_headroom**
   — volume decline → fixed-cost deleverage → EBITDA
   margin → covenant headroom.
5. **dso_rise_to_wc_to_fcf_to_div_recap_timing** — DSO
   rise → working-capital absorption → FCF → recap
   delay.
6. **reg_event_to_service_line_to_volume_to_ebitda** —
   reg event → service-line impact → volume → EBITDA.

### Output

Per fired chain: ordered list of (step, effect_detail,
quantified_impact) tuples + partner summary sentence
connecting the dots explicitly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class PacketSignals:
    # Denial / coding
    denial_rate_change_bps: float = 0.0   # negative = improving
    cmi_propped_by_appeals: bool = False
    medicare_npr_m: float = 100.0
    # Payer mix
    commercial_mix_change_pct: float = 0.0  # + = more commercial
    medicare_mix_change_pct: float = 0.0
    # Wage / comp
    wage_inflation_bps: float = 0.0
    physician_comp_of_npr_pct: float = 0.40
    comp_normalization_addback_m: float = 0.0
    # Volume
    volume_change_pct: float = 0.0
    fixed_cost_share_pct: float = 0.55
    ebitda_base_m: float = 40.0
    covenant_headroom_pct: float = 0.20
    # Working capital
    dso_change_days: float = 0.0
    wc_required_as_pct_of_npr: float = 0.12
    npr_m: float = 300.0
    planned_div_recap_year: Optional[int] = None
    # Reg event
    upcoming_reg_event_name: str = ""
    service_line_exposed_pct_of_npr: float = 0.0
    service_line_price_cut_pct: float = 0.0


@dataclass
class ChainStep:
    step: str
    effect_detail: str
    quantified_impact: str


@dataclass
class FiredChain:
    name: str
    steps: List[ChainStep] = field(default_factory=list)
    partner_summary: str = ""


@dataclass
class DotConnectReport:
    chains: List[FiredChain] = field(default_factory=list)
    headline: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chains": [
                {"name": c.name,
                 "steps": [
                     {"step": s.step,
                      "effect_detail": s.effect_detail,
                      "quantified_impact":
                          s.quantified_impact}
                     for s in c.steps],
                 "partner_summary": c.partner_summary}
                for c in self.chains
            ],
            "headline": self.headline,
        }


def _denial_fix_to_medicare_bridge(
    s: PacketSignals,
) -> Optional[FiredChain]:
    """If denials fall AND CMI was propped by appeals,
    Medicare $ moves DOWN with denial fix.
    """
    if abs(s.denial_rate_change_bps) < 50:
        return None
    if not s.cmi_propped_by_appeals:
        return None

    # Denial drop of 150 bps reduces appeals-driven CMI
    # by roughly ~2% (partner rule of thumb); Medicare
    # NPR down by same %.
    denial_drop_bps = abs(s.denial_rate_change_bps)
    cmi_impact_pct = min(
        0.04, denial_drop_bps / 7500.0
    )  # 150 bps → 2% CMI reversal
    medicare_bridge_delta_m = (
        s.medicare_npr_m * cmi_impact_pct * -1.0
    )

    return FiredChain(
        name="denial_fix_to_cmi_to_medicare_bridge",
        steps=[
            ChainStep(
                step="denial_rate_drop",
                effect_detail=(
                    f"Initial-denial rate improves "
                    f"{denial_drop_bps:.0f} bps"),
                quantified_impact=(
                    f"{denial_drop_bps:.0f} bps cleaner claims"),
            ),
            ChainStep(
                step="coding_accuracy_rises",
                effect_detail=(
                    "More claims survive first-pass → "
                    "coding-accuracy gap becomes visible"),
                quantified_impact=(
                    "exposes over-coding via appeals"),
            ),
            ChainStep(
                step="cmi_reversal",
                effect_detail=(
                    "CMI propped by appeals-driven "
                    "re-coding falls"),
                quantified_impact=(
                    f"~{cmi_impact_pct:.1%} CMI "
                    "reversal"),
            ),
            ChainStep(
                step="medicare_bridge_impact",
                effect_detail=(
                    "Medicare per-case revenue falls "
                    "with CMI"),
                quantified_impact=(
                    f"${medicare_bridge_delta_m:+.1f}M "
                    "Medicare NPR"),
            ),
        ],
        partner_summary=(
            f"Denial fix of {denial_drop_bps:.0f} bps "
            f"reverses appeals-propped CMI "
            f"(~{cmi_impact_pct:.1%}); Medicare bridge "
            f"loses ${abs(medicare_bridge_delta_m):.1f}M. "
            "Don't cheer the denial improvement until "
            "the Medicare leg is re-modeled."
        ),
    )


def _payer_shift_to_ip_margin(
    s: PacketSignals,
) -> Optional[FiredChain]:
    if abs(s.commercial_mix_change_pct) < 0.02:
        return None

    # + commercial share → case-mix toward surgery → CMI +
    cmi_shift = s.commercial_mix_change_pct * 0.4
    margin_bps = cmi_shift * 500.0  # 1% CMI ≈ 50 bps margin
    return FiredChain(
        name="payer_shift_to_case_mix_to_cmi_to_ip_margin",
        steps=[
            ChainStep(
                step="payer_mix_shifts",
                effect_detail=(
                    f"Commercial share moves "
                    f"{s.commercial_mix_change_pct:+.1%}"),
                quantified_impact=(
                    f"{s.commercial_mix_change_pct:+.1%} "
                    "commercial mix"),
            ),
            ChainStep(
                step="case_mix_reweights",
                effect_detail=(
                    "Commercial patients skew toward "
                    "surgery / higher-acuity elective"),
                quantified_impact=(
                    f"~{cmi_shift:+.1%} CMI shift"),
            ),
            ChainStep(
                step="cmi_impact",
                effect_detail=(
                    "CMI × Medicare base rate × "
                    "volume = IP revenue"),
                quantified_impact=(
                    f"IP margin {margin_bps:+.0f} bps"),
            ),
            ChainStep(
                step="ip_margin_flows_through",
                effect_detail=(
                    "IP margin change flows to total "
                    "EBITDA margin via IP share"),
                quantified_impact=(
                    "partial offset on cost-side "
                    "scaling"),
            ),
        ],
        partner_summary=(
            f"Commercial mix "
            f"{s.commercial_mix_change_pct:+.1%} → CMI "
            f"shift {cmi_shift:+.1%} → IP margin "
            f"{margin_bps:+.0f} bps. Don't model payer-"
            "mix shift in isolation; CMI is the "
            "transmission."
        ),
    )


def _wage_to_addback_risk(
    s: PacketSignals,
) -> Optional[FiredChain]:
    if s.wage_inflation_bps < 100:
        return None

    comp_drag_bps = (
        s.wage_inflation_bps * s.physician_comp_of_npr_pct
    )
    ebitda_drag_m = (
        s.ebitda_base_m * comp_drag_bps / 10000.0
    )
    addback_at_risk = (
        s.comp_normalization_addback_m > 0 and
        comp_drag_bps > 80
    )
    return FiredChain(
        name=(
            "wage_step_to_physcomp_to_ebitda_to_addback_risk"),
        steps=[
            ChainStep(
                step="wage_inflation",
                effect_detail=(
                    f"{s.wage_inflation_bps:.0f} bps wage "
                    "inflation in local MSA"),
                quantified_impact=(
                    f"{s.wage_inflation_bps:.0f} bps "
                    "labor cost step"),
            ),
            ChainStep(
                step="physician_comp_pressure",
                effect_detail=(
                    f"Physician comp at "
                    f"{s.physician_comp_of_npr_pct:.0%} "
                    "of NPR moves proportionally"),
                quantified_impact=(
                    f"{comp_drag_bps:.0f} bps NPR drag"),
            ),
            ChainStep(
                step="ebitda_margin_hit",
                effect_detail=(
                    "Comp pressure flows to EBITDA"),
                quantified_impact=(
                    f"${ebitda_drag_m:.2f}M EBITDA drag"),
            ),
            ChainStep(
                step="addback_stress",
                effect_detail=(
                    "Seller comp-normalization add-back "
                    "is now under pressure" if addback_at_risk
                    else "Add-back claim not materially "
                         "affected"),
                quantified_impact=(
                    f"${s.comp_normalization_addback_m:.1f}M "
                    "add-back at risk" if addback_at_risk
                    else "low stress"),
            ),
        ],
        partner_summary=(
            f"Wage inflation {s.wage_inflation_bps:.0f} "
            f"bps → physician comp drag "
            f"{comp_drag_bps:.0f} bps → "
            f"${ebitda_drag_m:.2f}M EBITDA. "
            + (
                "Seller's comp-normalization add-back "
                "becomes stressed — QofE will call it."
                if addback_at_risk else
                "Add-back claim still defensible."
            )
        ),
    )


def _volume_to_covenant(
    s: PacketSignals,
) -> Optional[FiredChain]:
    if s.volume_change_pct > -0.03:
        return None

    fixed_cost_drag_bps = (
        abs(s.volume_change_pct) *
        s.fixed_cost_share_pct * 10000.0
    )
    ebitda_margin_hit_pct = fixed_cost_drag_bps / 10000.0
    ebitda_loss_m = s.ebitda_base_m * ebitda_margin_hit_pct
    new_headroom = (
        s.covenant_headroom_pct - ebitda_margin_hit_pct
    )
    covenant_trip = new_headroom < 0.10
    return FiredChain(
        name=(
            "volume_decline_to_fixed_cost_to_covenant_headroom"),
        steps=[
            ChainStep(
                step="volume_decline",
                effect_detail=(
                    f"Volume down "
                    f"{s.volume_change_pct:+.1%}"),
                quantified_impact=(
                    f"{s.volume_change_pct:+.1%} volume"),
            ),
            ChainStep(
                step="fixed_cost_deleverage",
                effect_detail=(
                    f"Fixed-cost share "
                    f"{s.fixed_cost_share_pct:.0%} → "
                    "doesn't scale down"),
                quantified_impact=(
                    f"{fixed_cost_drag_bps:.0f} bps "
                    "margin drag"),
            ),
            ChainStep(
                step="ebitda_margin_hit",
                effect_detail=(
                    "Margin hit from deleverage"),
                quantified_impact=(
                    f"${ebitda_loss_m:.2f}M EBITDA"),
            ),
            ChainStep(
                step="covenant_headroom",
                effect_detail=(
                    f"Covenant headroom falls to "
                    f"{new_headroom:.1%}"),
                quantified_impact=(
                    "TRIP" if covenant_trip
                    else f"{new_headroom:.0%} "
                         "remaining"),
            ),
        ],
        partner_summary=(
            f"Volume {s.volume_change_pct:+.1%} → "
            f"fixed-cost drag "
            f"{fixed_cost_drag_bps:.0f} bps → "
            f"${ebitda_loss_m:.2f}M EBITDA loss → "
            + (
                "covenant headroom trips below 10%. "
                "Call the bank in Q3."
                if covenant_trip else
                "covenant headroom tight but holds."
            )
        ),
    )


def _dso_to_div_recap(
    s: PacketSignals,
) -> Optional[FiredChain]:
    if abs(s.dso_change_days) < 5:
        return None

    dso_to_wc_m = (
        s.dso_change_days / 365.0 * s.npr_m
    )
    recap_delay = dso_to_wc_m > 3.0 and s.planned_div_recap_year
    return FiredChain(
        name="dso_rise_to_wc_to_fcf_to_div_recap_timing",
        steps=[
            ChainStep(
                step="dso_change",
                effect_detail=(
                    f"DSO moves "
                    f"{s.dso_change_days:+.1f} days"),
                quantified_impact=(
                    f"{s.dso_change_days:+.1f} days"),
            ),
            ChainStep(
                step="wc_absorbs",
                effect_detail=(
                    "Working-capital requirement rises"),
                quantified_impact=(
                    f"${dso_to_wc_m:+.1f}M additional "
                    "WC"),
            ),
            ChainStep(
                step="fcf_compression",
                effect_detail=(
                    "FCF falls by the WC delta"),
                quantified_impact=(
                    f"${dso_to_wc_m:+.1f}M FCF hit"),
            ),
            ChainStep(
                step="recap_timing",
                effect_detail=(
                    "Dividend recap needs more FCF "
                    "headroom" if s.planned_div_recap_year
                    else "No recap planned; partner "
                         "eats cash drag in year"),
                quantified_impact=(
                    "recap delay likely"
                    if recap_delay else "neutral"),
            ),
        ],
        partner_summary=(
            f"DSO {s.dso_change_days:+.1f} days → WC "
            f"${dso_to_wc_m:+.1f}M → FCF hit. "
            + (
                f"Planned {s.planned_div_recap_year} "
                "recap likely slips — rebuild the recap "
                "model or give up a turn of leverage."
                if recap_delay else
                "No recap on the books; monitor cash "
                "drift each quarter."
            )
        ),
    )


def _reg_event_to_ebitda(
    s: PacketSignals,
) -> Optional[FiredChain]:
    if not s.upcoming_reg_event_name:
        return None
    if s.service_line_exposed_pct_of_npr <= 0:
        return None

    npr_at_risk = (
        s.npr_m *
        s.service_line_exposed_pct_of_npr *
        s.service_line_price_cut_pct
    )
    ebitda_at_risk = npr_at_risk * 0.4  # contribution margin
    return FiredChain(
        name="reg_event_to_service_line_to_volume_to_ebitda",
        steps=[
            ChainStep(
                step="reg_event",
                effect_detail=(
                    f"{s.upcoming_reg_event_name} "
                    "effective in hold"),
                quantified_impact=(
                    f"{s.service_line_price_cut_pct:.1%} "
                    "rate cut"),
            ),
            ChainStep(
                step="service_line_exposure",
                effect_detail=(
                    f"Exposed service line = "
                    f"{s.service_line_exposed_pct_of_npr:.0%} "
                    "of NPR"),
                quantified_impact=(
                    f"${s.npr_m * s.service_line_exposed_pct_of_npr:.0f}M "
                    "exposed NPR"),
            ),
            ChainStep(
                step="volume_or_price_hit",
                effect_detail=(
                    "Provider price taker — straight "
                    "rate hit"),
                quantified_impact=(
                    f"${npr_at_risk:.1f}M NPR at risk"),
            ),
            ChainStep(
                step="ebitda_flow_through",
                effect_detail=(
                    "Contribution margin × NPR loss"),
                quantified_impact=(
                    f"${ebitda_at_risk:.1f}M EBITDA hit"),
            ),
        ],
        partner_summary=(
            f"{s.upcoming_reg_event_name}: "
            f"{s.service_line_exposed_pct_of_npr:.0%} "
            "of NPR exposed → "
            f"${ebitda_at_risk:.1f}M EBITDA hit. "
            "Price into bridge or exit multiple "
            "contracts."
        ),
    )


_CHAIN_FNS = [
    _denial_fix_to_medicare_bridge,
    _payer_shift_to_ip_margin,
    _wage_to_addback_risk,
    _volume_to_covenant,
    _dso_to_div_recap,
    _reg_event_to_ebitda,
]


def connect_the_dots(
    signals: PacketSignals,
) -> DotConnectReport:
    fired: List[FiredChain] = []
    for fn in _CHAIN_FNS:
        chain = fn(signals)
        if chain is not None:
            fired.append(chain)

    if not fired:
        headline = (
            "No cross-module implication chains fire on "
            "the current signal set. Packet reads as "
            "additive, not interactive."
        )
    else:
        headline = (
            f"{len(fired)} dot-connect chain(s) active "
            "— packet signals are not independent. "
            "Partner read below is cross-module, not "
            "per-line."
        )

    return DotConnectReport(
        chains=fired,
        headline=headline,
    )


def render_dot_connect_markdown(
    r: DotConnectReport,
) -> str:
    lines = [
        "# Connect-the-dots packet read",
        "",
        f"_{r.headline}_",
        "",
    ]
    for c in r.chains:
        lines.append(f"## {c.name}")
        lines.append("")
        lines.append(f"_{c.partner_summary}_")
        lines.append("")
        for i, s in enumerate(c.steps, start=1):
            lines.append(
                f"{i}. **{s.step}** — {s.effect_detail} "
                f"→ _{s.quantified_impact}_"
            )
        lines.append("")
    return "\n".join(lines)
