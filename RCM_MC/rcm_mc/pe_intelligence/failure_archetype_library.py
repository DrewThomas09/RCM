"""Failure archetype library — shape-level failure patterns.

Partner statement: "This deal doesn't match any single
blowup we've seen — but it matches the *shape* of three
different ones. That's worse, not better."

Distinct from:

- `historical_failure_library` — named, dated PE
  disasters (Envision 2023, Steward 2024, Prospect 2023,
  etc.).
- `bear_book` — heuristic pattern *templates*
  (rollup-integration-failure, covid-tailwind-fade).
- `partner_traps_library` — seller-pitch traps.

This module sits between the three: **archetype-level
failure shapes** — a deal's structural profile that
predicts failure before any specific named incident
applies. These are the patterns a senior partner
recognizes in 30 seconds from the one-pager, not after
three weeks of diligence.

Each archetype captures:

- The **shape** of the deal (not the name).
- The **structural reason** it tends to fail.
- **Signals** from a packet context that flag it.
- **Historical examples** (for pattern-matching
  reinforcement).
- **Partner-counter mitigation** — what to demand before
  proceeding.

### Archetypes included (10)

1. **serial_add_on_overhire** — rollup builds SG&A
   faster than acquired EBITDA.
2. **payer_shift_without_contract_renewal** — mix-shift
   thesis without open contracting windows.
3. **site_neutral_hostage** — HOPD-heavy with open
   regulatory clock.
4. **specialty_practice_succession_gap** — founder
   dependency without groomed successor.
5. **340b_dependent_tail** — tail of EBITDA from 340B
   arbitrage, exposed to ACA change.
6. **ma_pass_through_over_reliance** — Medicare Advantage
   that buyer assumes compensates for FFS cuts.
7. **rent_belowmarket_related_party** — seller-owned real
   estate at sub-market rent the buyer will eventually
   pay.
8. **back_office_integration_optimism** — "year 1"
   synergy plan on multi-EHR platform.
9. **turnaround_without_operator** — thesis requires
   ops lift, team lacks the operator to deliver it.
10. **covid_inflated_base** — base-year EBITDA
    structurally overstated by pandemic tailwind.

### Why this layer adds signal

Archetype matching is how partners reach a **first
impression** of a deal on intake. By the time the team
has modeled, they're already committed. The archetype
library forces the partner to name the shape first —
before committing underwriting resources.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class FailureArchetype:
    name: str
    shape_description: str
    structural_reason: str
    signals: List[str] = field(default_factory=list)
    historical_examples: List[str] = field(default_factory=list)
    partner_counter: str = ""


ARCHETYPES: List[FailureArchetype] = [
    FailureArchetype(
        name="serial_add_on_overhire",
        shape_description=(
            "Roll-up platform hiring central-services "
            "leadership faster than platform EBITDA scales."
        ),
        structural_reason=(
            "SG&A per dollar of platform EBITDA compounds "
            "faster than revenue compounds. By year 3, the "
            "platform is over-headed; synergies evaporate."
        ),
        signals=[
            "platform_ebitda_m < 60",
            "central_services_hires_per_yr >= 10",
            "integrated_acquisitions_pct < 0.70",
            "sga_growth_outpaces_revenue_growth",
        ],
        historical_examples=[
            "Mid-size physician roll-ups 2018-2021",
        ],
        partner_counter=(
            "Demand a per-acquisition SG&A absorption "
            "target before hiring; cap central-services "
            "run-rate at X bps of platform revenue."
        ),
    ),
    FailureArchetype(
        name="payer_shift_without_contract_renewal",
        shape_description=(
            "Payer-mix shift thesis with no top-5 payer "
            "contract expiring in the hold."
        ),
        structural_reason=(
            "Mix shift requires new contracts; if none are "
            "up, the seller is asserting a win the operator "
            "can't execute. Rate cards don't change outside "
            "renewals."
        ),
        signals=[
            "claimed_mix_shift_pct > 0.08",
            "top_payer_contracts_open_in_hold == 0",
        ],
        historical_examples=[
            "Specialty practice mix-shift deals 2019-2022",
        ],
        partner_counter=(
            "Price the thesis off existing contracts. Add "
            "earn-out tied to actually-renegotiated rates."
        ),
    ),
    FailureArchetype(
        name="site_neutral_hostage",
        shape_description=(
            "HOPD-heavy revenue mix with site-neutral "
            "rule finalization in the hold window."
        ),
        structural_reason=(
            "CMS site-neutral rules equalize HOPD to ASC "
            "rates (~22% cut on affected services). If the "
            "finalization lands in the hold, bridge math "
            "breaks mid-plan."
        ),
        signals=[
            "hopd_revenue_pct >= 0.20",
            "hold_includes_site_neutral_final_year",
        ],
        historical_examples=[
            "Outpatient cardiology / imaging rollups "
            "2021-2024",
        ],
        partner_counter=(
            "Model base case at post-site-neutral rates. "
            "Price-in the hit; don't hope for delay."
        ),
    ),
    FailureArchetype(
        name="specialty_practice_succession_gap",
        shape_description=(
            "Specialty physician practice where founder "
            "generates > 30% of revenue personally and no "
            "successor exists."
        ),
        structural_reason=(
            "Founder referrals + reputation are the asset. "
            "Post-close, founder winds down; referrals "
            "follow them out the door."
        ),
        signals=[
            "founder_rvu_pct > 0.30",
            "successor_identified == False",
            "founder_age_60_plus",
        ],
        historical_examples=[
            "Single-specialty rollups in dermatology, "
            "ophthalmology, orthopedics 2016-2022",
        ],
        partner_counter=(
            "Non-compete + 5-year employment agreement at "
            "signing; rollover equity structured so founder "
            "loses value on early exit."
        ),
    ),
    FailureArchetype(
        name="340b_dependent_tail",
        shape_description=(
            "Meaningful share of EBITDA from 340B drug "
            "pricing arbitrage."
        ),
        structural_reason=(
            "340B program is vulnerable to Congressional "
            "change, manufacturer pushback, and CMS "
            "contract-pharmacy restrictions. Tail revenue "
            "disappears in a single rulemaking."
        ),
        signals=[
            "ebitda_share_from_340b > 0.15",
            "340b_contract_pharmacy_exposure",
        ],
        historical_examples=[
            "FQHC-affiliated specialty pharmacies, safety-"
            "net hospital subsidiaries",
        ],
        partner_counter=(
            "Isolate 340B EBITDA; price at 1x, not a "
            "multiple. Structure earn-out if rules hold."
        ),
    ),
    FailureArchetype(
        name="ma_pass_through_over_reliance",
        shape_description=(
            "Medicare Advantage revenue share that buyer "
            "assumes offsets FFS cuts without MA-specific "
            "capability."
        ),
        structural_reason=(
            "MA rate benchmarks track FFS with lag. When "
            "FFS cuts, MA follows. Worse, MA plans "
            "increasingly push risk to providers — "
            "operator needs MA chassis or margin "
            "compresses faster than FFS."
        ),
        signals=[
            "medicare_advantage_pct > 0.20",
            "risk_contracts_pct < 0.05",
            "no_mssp_or_aco_track_record",
        ],
        historical_examples=[
            "Primary-care chains assuming MA tailwind "
            "2019-2023 (iVcare, Cano Health, etc.)",
        ],
        partner_counter=(
            "Price as FFS-correlated; don't give MA "
            "credit unless team has risk-contract track "
            "record."
        ),
    ),
    FailureArchetype(
        name="rent_belowmarket_related_party",
        shape_description=(
            "Seller owns the real estate; pays self sub-"
            "market rent; buyer inherits the below-market "
            "lease."
        ),
        structural_reason=(
            "Normalize to market rent and EBITDA drops "
            "materially. Partner's QofE will find it; "
            "better to price it in than discover at close."
        ),
        signals=[
            "related_party_rent_true",
            "rent_pct_revenue < 0.04",
            "real_estate_owned_by_seller",
        ],
        historical_examples=[
            "Family-owned practices, regional dental / "
            "ASC operators",
        ],
        partner_counter=(
            "Price off market-rent-adjusted EBITDA. Or "
            "acquire the real estate separately at a "
            "capped price."
        ),
    ),
    FailureArchetype(
        name="back_office_integration_optimism",
        shape_description=(
            "Multi-EHR / multi-ERP platform with 'year 1' "
            "synergy assumption in base case."
        ),
        structural_reason=(
            "EHR integration in healthcare takes 24-36 "
            "months. Year 1 synergies assumed here are "
            "fiction; by the time they materialize, "
            "integration cost has compounded."
        ),
        signals=[
            "num_ehr_systems >= 3",
            "synergy_timing_year == 1",
            "integration_cost_ratio < 0.20",
        ],
        historical_examples=[
            "Regional hospital rollups, multi-brand "
            "physician networks",
        ],
        partner_counter=(
            "Model synergy ramp Y2-Y4 with 40%+ "
            "integration-cost load. Year 1 is "
            "stabilization, not uplift."
        ),
    ),
    FailureArchetype(
        name="turnaround_without_operator",
        shape_description=(
            "Deal thesis requires a turnaround but the "
            "team on site is the team that created the "
            "problem."
        ),
        structural_reason=(
            "Asking the management team who got the "
            "business into this to lead the turnaround "
            "is the most common operator failure in PE."
        ),
        signals=[
            "thesis_requires_margin_turnaround",
            "ceo_tenure_years > 5",
            "prior_turnaround_attempts >= 1",
            "external_operator_not_identified",
        ],
        historical_examples=[
            "Hospital turnarounds without new CEO; "
            "distressed physician rollups",
        ],
        partner_counter=(
            "Ship with a search. Reserve $5M operator-"
            "placement budget. Don't close without a CEO "
            "candidate identified."
        ),
    ),
    FailureArchetype(
        name="covid_inflated_base",
        shape_description=(
            "Base-year EBITDA structurally overstated by "
            "pandemic-era tailwind."
        ),
        structural_reason=(
            "Elective volumes, ED volumes, mental-health "
            "demand, and selected specialty reimbursement "
            "all saw COVID-driven anomalies. Using 2021 "
            "or 2022 as base inflates the exit multiple "
            "application."
        ),
        signals=[
            "base_year_is_2020_through_2022",
            "volume_declined_post_2022",
            "covid_related_revenue_bucket_material",
        ],
        historical_examples=[
            "Virtual care hype (Teladoc-era), COVID "
            "testing / labs, behavioral-health surge "
            "operators",
        ],
        partner_counter=(
            "Use pre-COVID base or rolling 3-yr average. "
            "Price only off recurring run-rate."
        ),
    ),
]


@dataclass
class ArchetypeMatch:
    archetype: FailureArchetype
    signals_hit: List[str] = field(default_factory=list)
    match_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "archetype": {
                "name": self.archetype.name,
                "shape_description":
                    self.archetype.shape_description,
                "structural_reason":
                    self.archetype.structural_reason,
                "historical_examples":
                    list(self.archetype.historical_examples),
                "partner_counter":
                    self.archetype.partner_counter,
            },
            "signals_hit": list(self.signals_hit),
            "match_score": self.match_score,
        }


@dataclass
class FailureArchetypeReport:
    matches: List[ArchetypeMatch] = field(default_factory=list)
    dominant_archetype: Optional[str] = None
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "matches": [m.to_dict() for m in self.matches],
            "dominant_archetype": self.dominant_archetype,
            "partner_note": self.partner_note,
        }


def match_failure_archetypes(
    signals: Dict[str, Any],
) -> FailureArchetypeReport:
    """Scan a signal dict (bool-ish values per signal name)
    and rank archetypes by fraction of signals matched."""
    matches: List[ArchetypeMatch] = []
    for a in ARCHETYPES:
        hit = [s for s in a.signals
               if bool(signals.get(s, False))]
        if not hit:
            continue
        matches.append(ArchetypeMatch(
            archetype=a,
            signals_hit=hit,
            match_score=round(len(hit) / max(1, len(a.signals)), 3),
        ))
    matches.sort(key=lambda m: -m.match_score)

    dominant = matches[0].archetype.name if matches else None

    if not matches:
        note = ("No archetype-level failure shapes detected. "
                "Partner: deal's structural profile is "
                "unremarkable; proceed on merits.")
    elif len(matches) >= 3:
        note = (f"{len(matches)} archetype shapes fire — "
                f"dominant: {dominant}. Partner: this deal "
                "combines multiple failure shapes. Each "
                "requires specific mitigation; compound "
                "risk beats additive risk.")
    elif len(matches) == 2:
        note = (f"Two archetype shapes: "
                f"{', '.join(m.archetype.name for m in matches)}. "
                "Partner: document explicit mitigation in the "
                "IC memo.")
    else:
        note = (f"Dominant archetype: {dominant}. Partner: "
                "apply the named partner-counter; otherwise "
                "do not proceed.")

    return FailureArchetypeReport(
        matches=matches,
        dominant_archetype=dominant,
        partner_note=note,
    )


def render_failure_archetypes_markdown(
    r: FailureArchetypeReport,
) -> str:
    lines = [
        "# Failure archetype matches",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Dominant: {r.dominant_archetype or '—'}",
        f"- Matches: {len(r.matches)}",
        "",
    ]
    for m in r.matches:
        a = m.archetype
        lines.append(f"## {a.name} (score {m.match_score:.2f})")
        lines.append(f"- **Shape:** {a.shape_description}")
        lines.append(f"- **Why it fails:** {a.structural_reason}")
        lines.append(f"- **Historical:** "
                     f"{'; '.join(a.historical_examples)}")
        lines.append(f"- **Partner counter:** "
                     f"{a.partner_counter}")
        lines.append(f"- **Signals matched:** "
                     f"{', '.join(m.signals_hit)}")
        lines.append("")
    return "\n".join(lines)


def list_all_archetypes() -> List[str]:
    return [a.name for a in ARCHETYPES]
