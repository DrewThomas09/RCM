"""Banker narrative decoder — recognize the pitch tactic.

Partner statement: "Every banker runs the same 8 plays.
Once you name the play, the counter writes itself."

Sell-side bankers in healthcare-services PE use a finite
catalog of narrative tactics to shape the buyer's framing.
Partners recognize these tactics in 30 seconds from the
CIM or management-meeting script. This module catalogs the
common ones, the **tell** (what triggers recognition), and
the **partner counter** (what to say or ask to defuse).

Distinct from:

- `partner_traps_library` — seller-pitch traps on
  specific thesis claims (e.g., "fix denials 12 months").
- `letter_to_seller` — our outbound draft reply.

### 10 banker narratives

1. **the_hook** — top-of-deck tagline that overshadows
   diligence gaps.
2. **the_comp_deck** — carefully curated transaction comps
   anchoring price.
3. **the_momentum_story** — "process is very competitive;
   others closing fast."
4. **the_scarcity_pitch** — "very few quality assets in
   the subsector."
5. **the_payer_renegotiation_tease** — "we're about to
   sign MA at premium rates."
6. **the_synergy_promise** — "platform unlocks 300 bps
   margin lift."
7. **the_secondary_angle** — "we've been to market before
   at a higher number."
8. **the_once_in_a_generation** — only used when
   fundamentals are shaky.
9. **the_teaser_without_financials** — early info-control.
10. **the_management_is_rockstar** — preempts operator-
    risk pushback.

### Matching logic

A caller supplies a dict of observed narrative signals
(strings seen in CIM / mgmt deck / banker outreach). The
decoder matches these against each tactic's tell-list and
returns:

- Tactics detected.
- Per-tactic partner counter.
- Overall partner note: "banker is leaning on X, Y, Z —
  counter with: ..."

### Why this module matters

A partner who can **name** the banker's play ends the
meeting having set the agenda rather than followed it.
Naming = control.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BankerNarrative:
    name: str
    what_banker_says: str
    tells: List[str] = field(default_factory=list)
    why_it_works: str = ""
    partner_counter: str = ""


NARRATIVE_LIBRARY: List[BankerNarrative] = [
    BankerNarrative(
        name="the_hook",
        what_banker_says=(
            "Top-of-deck tagline: 'Leading specialty "
            "platform with 30% CAGR and recurring-revenue "
            "model.' Everything else buries."
        ),
        tells=[
            "top_of_deck_cagr_30",
            "recurring_revenue_framing_prominent",
            "diligence_section_understated",
        ],
        why_it_works=(
            "Anchors partner on upside before diligence "
            "surfaces payer mix, regulatory tail, or "
            "volume concentration."
        ),
        partner_counter=(
            "Ignore the hook. Start diligence on the "
            "*explicit* bear case — payer concentration, "
            "regulatory tail, and volume mix — before "
            "scheduling the bull-case dive."
        ),
    ),
    BankerNarrative(
        name="the_comp_deck",
        what_banker_says=(
            "'Recent deals in the space have cleared "
            "13-15x. Here are 5 comps, all at premium.'"
        ),
        tells=[
            "comps_selected_to_support_premium",
            "no_broken_process_comps_included",
            "absolute_scale_normalization_missing",
        ],
        why_it_works=(
            "Comps shape the anchor. Partner's base case "
            "is now 13x+ before looking at the asset."
        ),
        partner_counter=(
            "Request full comps list including broken "
            "processes. Ask for scale-adjusted comps "
            "(same bed count, same revenue band). The 15x "
            "comp is always 3x our asset's size."
        ),
    ),
    BankerNarrative(
        name="the_momentum_story",
        what_banker_says=(
            "'We have 4 parties through IOI. Expect best-"
            "and-final next Friday.' Timeline pressure "
            "compressed."
        ),
        tells=[
            "urgency_without_specifics",
            "multiple_buyers_cited_unnamed",
            "short_decision_window_imposed",
        ],
        why_it_works=(
            "Partner fears losing the deal, pre-commits "
            "resources, can't conduct real diligence."
        ),
        partner_counter=(
            "Ignore the timeline. Say 'we'll work to your "
            "process but won't skip diligence.' If seller "
            "walks because of that, we didn't want the "
            "deal anyway."
        ),
    ),
    BankerNarrative(
        name="the_scarcity_pitch",
        what_banker_says=(
            "'There are only 3 quality platforms in this "
            "subsector. You don't do this, you lose a "
            "decade.'"
        ),
        tells=[
            "subsector_market_universe_under_5",
            "generational_framing_used",
            "no_recent_failed_process_acknowledged",
        ],
        why_it_works=(
            "Triggers FOMO. Partner overweights asset "
            "scarcity, underweights structural risk."
        ),
        partner_counter=(
            "List every failed process in the subsector "
            "over the past 3 years. Scarcity arguments "
            "only hold if buyers aren't walking — ask "
            "why they walked."
        ),
    ),
    BankerNarrative(
        name="the_payer_renegotiation_tease",
        what_banker_says=(
            "'Top 2 payers come up for renewal in Q3. "
            "We're seeing 8% rate lift in early "
            "discussions.'"
        ),
        tells=[
            "payer_renegotiation_cited",
            "rate_lift_claimed_above_5pct",
            "no_signed_term_sheet_yet",
        ],
        why_it_works=(
            "Positions upside as imminent. Partner models "
            "higher rates as 'probable' in forward EBITDA."
        ),
        partner_counter=(
            "Price off current rates. Add earn-out tied to "
            "actually-signed rate lift. If banker resists "
            "earn-out structure, the rate lift isn't real."
        ),
    ),
    BankerNarrative(
        name="the_synergy_promise",
        what_banker_says=(
            "'Platform rollup unlocks 300 bps of margin "
            "lift in Y1 from central services.'"
        ),
        tells=[
            "synergy_bps_specific_claimed",
            "y1_synergy_timing_claimed",
            "integration_cost_not_discussed",
        ],
        why_it_works=(
            "Partner's base case now shows 300 bps uplift. "
            "Even at 50% realization, seller gets credit "
            "for 150."
        ),
        partner_counter=(
            "Ask for integration-cost ratio. Model synergy "
            "ramp Y2-Y4 net of cost. In healthcare, Y1 is "
            "almost never positive."
        ),
    ),
    BankerNarrative(
        name="the_secondary_angle",
        what_banker_says=(
            "'Seller previously went to market at $950M. "
            "We're at $875M today — this is a discount.'"
        ),
        tells=[
            "prior_process_cited_as_anchor",
            "prior_process_price_higher_than_current",
            "why_prior_broken_not_explained",
        ],
        why_it_works=(
            "Anchors partner on higher prior number, "
            "frames current as a discount."
        ),
        partner_counter=(
            "Ask why the prior process broke. Every "
            "breakage is information — usually diligence-"
            "related. Price off today's asset, not "
            "yesterday's narrative."
        ),
    ),
    BankerNarrative(
        name="the_once_in_a_generation",
        what_banker_says=(
            "'This is a once-in-a-generation asset.'"
        ),
        tells=[
            "generational_language_used",
            "unique_asset_framing_dominant",
            "bench_comps_weak_or_cherry_picked",
        ],
        why_it_works=(
            "Banker uses this when fundamentals don't "
            "support price and they need emotional lift."
        ),
        partner_counter=(
            "Instant flag. If banker needs to call it "
            "generational, the numbers don't support the "
            "price. Ask for the peer comparison that shows "
            "what makes it generational; usually empty."
        ),
    ),
    BankerNarrative(
        name="the_teaser_without_financials",
        what_banker_says=(
            "'Teaser is 4 pages — full CIM available on "
            "NDA execution.' No EBITDA, no growth."
        ),
        tells=[
            "teaser_omits_key_metrics",
            "nda_gate_before_any_math",
            "info_flow_heavily_controlled",
        ],
        why_it_works=(
            "Partner commits to NDA before seeing "
            "disqualifying data. Once we're in, we want "
            "to justify the time."
        ),
        partner_counter=(
            "Ask for top-line, EBITDA, and payer mix "
            "pre-NDA. Any banker worth their fee has that. "
            "If not provided, decline the NDA."
        ),
    ),
    BankerNarrative(
        name="the_management_is_rockstar",
        what_banker_says=(
            "'CEO is a legend in the subsector. She built "
            "two prior platforms and exited at 4x MOIC.'"
        ),
        tells=[
            "ceo_track_record_framed_first",
            "prior_platforms_cited",
            "current_team_succession_not_discussed",
        ],
        why_it_works=(
            "Pre-empts operator-risk pushback. Partner "
            "less likely to ask 'what if CEO leaves?'"
        ),
        partner_counter=(
            "Ask about rollover equity size for the CEO. "
            "If the rock-star CEO isn't rolling "
            "meaningfully, she knows something. Check "
            "employment terms + non-compete term at close."
        ),
    ),
]


@dataclass
class NarrativeMatch:
    narrative: BankerNarrative
    tells_hit: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "narrative": {
                "name": self.narrative.name,
                "what_banker_says":
                    self.narrative.what_banker_says,
                "why_it_works": self.narrative.why_it_works,
                "partner_counter":
                    self.narrative.partner_counter,
            },
            "tells_hit": list(self.tells_hit),
        }


@dataclass
class NarrativeDecodeReport:
    matches: List[NarrativeMatch] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matches": [m.to_dict() for m in self.matches],
            "partner_note": self.partner_note,
        }


def decode_banker_narrative(
    signals: Dict[str, Any],
) -> NarrativeDecodeReport:
    matches: List[NarrativeMatch] = []
    for n in NARRATIVE_LIBRARY:
        hit = [t for t in n.tells if bool(signals.get(t, False))]
        if not hit:
            continue
        matches.append(NarrativeMatch(
            narrative=n,
            tells_hit=hit,
        ))
    # Rank by number of tells hit.
    matches.sort(key=lambda m: -len(m.tells_hit))

    if not matches:
        note = (
            "No banker-narrative tactics detected in signals. "
            "Partner: either the banker is unusually direct "
            "(rare) or we haven't read the deck yet."
        )
    elif len(matches) >= 3:
        dom = ", ".join(m.narrative.name for m in matches[:3])
        note = (
            f"Banker leaning on multiple tactics: {dom}. "
            "Partner: name each play in the next call. "
            "Bankers stop running tactics once we name them."
        )
    else:
        dom = matches[0].narrative.name
        note = (
            f"Dominant banker tactic: {dom}. "
            "Partner: apply the named counter and re-ground "
            "the conversation in numbers."
        )

    return NarrativeDecodeReport(
        matches=matches,
        partner_note=note,
    )


def render_narrative_decode_markdown(
    r: NarrativeDecodeReport,
) -> str:
    lines = [
        "# Banker narrative decode",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Matches: {len(r.matches)}",
        "",
    ]
    for m in r.matches:
        n = m.narrative
        lines.append(f"## {n.name}")
        lines.append(f"- **Banker says:** {n.what_banker_says}")
        lines.append(f"- **Why it works:** {n.why_it_works}")
        lines.append(f"- **Partner counter:** {n.partner_counter}")
        lines.append(f"- **Tells hit:** {', '.join(m.tells_hit)}")
        lines.append("")
    return "\n".join(lines)


def list_banker_narratives() -> List[str]:
    return [n.name for n in NARRATIVE_LIBRARY]
