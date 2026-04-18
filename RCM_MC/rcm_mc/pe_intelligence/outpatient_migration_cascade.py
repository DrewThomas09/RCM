"""Outpatient migration cascade — fourth canonical cross-module story.

Sister to RCM / payer-mix / labor cascades. When a hospital or
health-system thesis assumes procedures migrate from inpatient
to outpatient settings, the cascade has distinctive mechanics:

1. **Migration rate** — % of current IP procedures expected to
   shift to OP (ASC / HOPD / physician office) over hold.
2. **Rate differential** — OP rates are 55-75% of IP for the same
   service. Revenue per case drops.
3. **Capacity unlock** — IP capacity freed can absorb higher-
   acuity cases (if demand exists) OR sits idle as fixed-cost
   drag.
4. **Margin implication** — OP operations have different cost
   structure (no hospital overhead). Margin can RISE if
   migration stays in-network.
5. **Site-neutral regulatory risk** — CMS site-neutral rules
   continue narrowing the IP-OP rate premium for HOPDs, making
   the migration less value-accretive and potentially value-
   destructive if HOPD exposure is high.

Partner reflex: a migration thesis is NOT "shift 30% of cases
and the margin improves." It is a net of revenue loss vs cost
savings vs displaced capacity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class OPMigrationInputs:
    deal_name: str = "Deal"
    current_ip_revenue_m: float = 0.0
    current_op_revenue_m: float = 0.0
    migration_pct_of_ip: float = 0.15       # % of IP cases shifting
    ip_margin: float = 0.12
    op_margin: float = 0.22
    op_rate_as_pct_of_ip: float = 0.65      # rate differential
    ip_capacity_utilization: float = 0.75
    hopd_share_of_op: float = 0.40          # portion of OP at HOPD rates
    site_neutral_haircut_pct: float = 0.22
    expects_backfill_high_acuity: bool = True


@dataclass
class OPMigrationStep:
    step: int
    name: str
    description: str
    value: float
    unit: str
    partner_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step, "name": self.name,
            "description": self.description,
            "value": self.value, "unit": self.unit,
            "partner_note": self.partner_note,
        }


@dataclass
class OPMigrationReport:
    steps: List[OPMigrationStep] = field(default_factory=list)
    net_revenue_impact_m: float = 0.0
    net_ebitda_impact_m: float = 0.0
    site_neutral_exposure_m: float = 0.0
    net_of_site_neutral_m: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "net_revenue_impact_m": self.net_revenue_impact_m,
            "net_ebitda_impact_m": self.net_ebitda_impact_m,
            "site_neutral_exposure_m": self.site_neutral_exposure_m,
            "net_of_site_neutral_m": self.net_of_site_neutral_m,
            "partner_note": self.partner_note,
        }


def trace_op_migration(inputs: OPMigrationInputs) -> OPMigrationReport:
    steps: List[OPMigrationStep] = []

    # Step 1: Migration magnitude.
    migrating_rev_at_ip_rates = (
        inputs.current_ip_revenue_m * inputs.migration_pct_of_ip
    )
    steps.append(OPMigrationStep(
        step=1, name="migration_magnitude",
        description=(f"{inputs.migration_pct_of_ip*100:.0f}% of IP "
                     "cases migrate to OP settings"),
        value=round(migrating_rev_at_ip_rates, 2), unit="$M",
        partner_note=(
            f"${migrating_rev_at_ip_rates:,.1f}M of IP revenue is in "
            "motion. Migration rates above 20% in 5 years require "
            "infrastructure and physician-contract changes the deck "
            "often under-budgets."),
    ))

    # Step 2: Revenue at OP rates.
    migrating_rev_at_op_rates = (
        migrating_rev_at_ip_rates * inputs.op_rate_as_pct_of_ip
    )
    rev_loss_from_rate = (migrating_rev_at_ip_rates
                           - migrating_rev_at_op_rates)
    steps.append(OPMigrationStep(
        step=2, name="op_rate_differential",
        description=(f"OP rates at "
                     f"{inputs.op_rate_as_pct_of_ip*100:.0f}% of IP"),
        value=round(-rev_loss_from_rate, 2), unit="$M",
        partner_note=(
            f"${rev_loss_from_rate:,.1f}M revenue loss from moving to "
            "OP rates. The narrative 'higher margin outpatient' "
            "ignores that the top-line shrinks first."),
    ))

    # Step 3: Margin swap.
    ip_ebitda_lost = migrating_rev_at_ip_rates * inputs.ip_margin
    op_ebitda_gained = migrating_rev_at_op_rates * inputs.op_margin
    margin_swap = op_ebitda_gained - ip_ebitda_lost
    steps.append(OPMigrationStep(
        step=3, name="margin_swap",
        description=("EBITDA swap: OP margin vs IP margin on migrated "
                     "volume"),
        value=round(margin_swap, 2), unit="$M",
        partner_note=(
            f"${margin_swap:+,.1f}M net EBITDA from the mix swap. "
            "Positive when OP margin × rate-adjusted revenue > IP "
            "margin × original revenue. Not always positive — "
            "depends on rate differential vs margin differential."),
    ))

    # Step 4: Capacity unlock.
    if inputs.expects_backfill_high_acuity \
            and inputs.ip_capacity_utilization >= 0.70:
        # Backfill: freed IP slots used for higher-acuity (20% higher rate).
        backfill_rev = migrating_rev_at_ip_rates * 1.20 * 0.50  # 50% fill
        backfill_ebitda = backfill_rev * inputs.ip_margin
        backfill_note = (
            f"Backfill assumption contributes "
            f"${backfill_ebitda:,.1f}M EBITDA at 50% fill of "
            "displaced capacity with higher-acuity cases. Validate "
            "that demand exists.")
    else:
        backfill_rev = 0.0
        backfill_ebitda = 0.0
        backfill_note = (
            "No backfill assumed — displaced IP capacity sits as "
            "fixed-cost drag. Historical pattern: without named "
            "high-acuity demand, fixed costs are not absorbed.")
    steps.append(OPMigrationStep(
        step=4, name="capacity_unlock",
        description="IP capacity backfill with higher-acuity cases",
        value=round(backfill_ebitda, 2), unit="$M",
        partner_note=backfill_note,
    ))

    # Step 5: Site-neutral risk.
    hopd_exposed_rev = migrating_rev_at_op_rates * inputs.hopd_share_of_op
    site_neutral_rev_hit = hopd_exposed_rev * inputs.site_neutral_haircut_pct
    site_neutral_ebitda_hit = site_neutral_rev_hit * inputs.op_margin
    steps.append(OPMigrationStep(
        step=5, name="site_neutral_risk",
        description=(f"Site-neutral HOPD haircut at "
                     f"{inputs.site_neutral_haircut_pct*100:.0f}%"),
        value=round(-site_neutral_ebitda_hit, 2), unit="$M",
        partner_note=(
            f"${site_neutral_ebitda_hit:,.1f}M EBITDA exposed to "
            "site-neutral rulemaking. Bear case assumes this realizes "
            "mid-hold; base case assumes partial realization."),
    ))

    # Aggregates.
    net_revenue_impact = (-rev_loss_from_rate + backfill_rev
                           - site_neutral_rev_hit)
    net_ebitda_impact = (margin_swap + backfill_ebitda
                          - site_neutral_ebitda_hit)

    if net_ebitda_impact < 0:
        note = (f"Outpatient-migration thesis is net negative on "
                f"EBITDA (${net_ebitda_impact:,.1f}M). The revenue "
                "loss from lower OP rates dominates; the backfill "
                "and margin swap do not close the gap.")
    elif inputs.hopd_share_of_op >= 0.40 \
            and site_neutral_ebitda_hit >= net_ebitda_impact * 0.5:
        note = (f"Outpatient-migration thesis is modestly positive "
                f"(${net_ebitda_impact:,.1f}M) but ≥ 50% of the "
                "benefit is at HOPD rates vulnerable to site-neutral. "
                "The thesis is a regulatory bet, not an operational "
                "one.")
    else:
        note = (f"Outpatient migration is net positive on EBITDA "
                f"(${net_ebitda_impact:,.1f}M). Validate the "
                "backfill assumption and site-neutral exposure.")

    return OPMigrationReport(
        steps=steps,
        net_revenue_impact_m=round(net_revenue_impact, 2),
        net_ebitda_impact_m=round(net_ebitda_impact, 2),
        site_neutral_exposure_m=round(site_neutral_ebitda_hit, 2),
        net_of_site_neutral_m=round(net_ebitda_impact, 2),
        partner_note=note,
    )


def render_op_migration_markdown(r: OPMigrationReport) -> str:
    lines = [
        "# Outpatient migration cascade",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Net revenue impact: ${r.net_revenue_impact_m:,.2f}M",
        f"- Net EBITDA impact: ${r.net_ebitda_impact_m:,.2f}M",
        f"- Site-neutral EBITDA exposure: "
        f"${r.site_neutral_exposure_m:,.2f}M",
        "",
    ]
    for s in r.steps:
        lines.append(f"## Step {s.step}: {s.name}")
        lines.append(f"- **{s.description}**: {s.value:+}{s.unit}")
        lines.append(f"- {s.partner_note}")
        lines.append("")
    return "\n".join(lines)
