"""Capex intensity stress — FCF bleed behind the EBITDA.

Partner statement: "Seller tells me EBITDA is $75M. Then
QofE shows capex has been below peer for three years —
they kicked the can. Now the $15M in deferred maintenance
is mine. That's EBITDA on paper that never converts to
cash."

Distinct from `ebitda_quality` (characterizes EBITDA
composition) and `cash_conversion` (models working-
capital cycle). This module stresses **capex** — the
other leg of the FCF bridge partners chronically
underwrite.

### Signals & adjustments

1. **Historical-capex-vs-peer gap** — if actual capex /
   revenue runs > 1% below peer median for multiple
   years, the delta represents *deferred maintenance*
   that compounds.
2. **Deferred maintenance backlog** — named repair /
   equipment / IT backlog the seller has disclosed or
   QofE has surfaced.
3. **New-site build pipeline** — partner counts capex
   planned (not just modeled maintenance).
4. **IT / EHR modernization** — forced upgrades that
   can't be deferred.
5. **Clinical equipment replacement** — typical 7-10
   year cycle; deals late in cycle carry near-term capex.
6. **Compliance / cyber capex** — non-discretionary
   post-HIPAA / ransomware / regulatory updates.

### Output

- **Projected 3-yr capex** = baseline + peer-gap
  make-up + deferred backlog + new sites + IT +
  clinical + compliance.
- **FCF vs. EBITDA haircut** = (cumulative capex /
  cumulative EBITDA) − peer ratio.
- Partner note: if haircut > 15%, "price in; FCF
  conversion below peer median."

### Why partners care

Deferred capex is a common seller-side optimism lever.
QofE sometimes catches it, often doesn't. Partners
demand a dedicated capex diligence workstream on assets
where historical capex ratio has been depressed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CapexStressInputs:
    revenue_m: float
    ebitda_m: float
    historical_capex_pct_revenue: float        # e.g., 0.035
    peer_median_capex_pct_revenue: float = 0.04
    years_below_peer: int = 0
    deferred_maintenance_backlog_m: float = 0.0
    new_sites_build_pipeline_m: float = 0.0
    it_ehr_modernization_needed_m: float = 0.0
    clinical_equipment_replacement_due_m: float = 0.0
    compliance_cyber_capex_m: float = 0.0
    forecast_horizon_years: int = 3


@dataclass
class CapexComponent:
    name: str
    amount_m: float
    partner_commentary: str


@dataclass
class CapexStressReport:
    projected_3yr_capex_m: float
    peer_ratio_gap_pct: float
    fcf_vs_ebitda_haircut_pct: float
    deferred_catchup_m: float
    components: List[CapexComponent] = field(default_factory=list)
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "projected_3yr_capex_m":
                self.projected_3yr_capex_m,
            "peer_ratio_gap_pct":
                self.peer_ratio_gap_pct,
            "fcf_vs_ebitda_haircut_pct":
                self.fcf_vs_ebitda_haircut_pct,
            "deferred_catchup_m":
                self.deferred_catchup_m,
            "components": [
                {"name": c.name, "amount_m": c.amount_m,
                 "partner_commentary": c.partner_commentary}
                for c in self.components
            ],
            "partner_note": self.partner_note,
        }


def stress_capex_intensity(
    inputs: CapexStressInputs,
) -> CapexStressReport:
    # Baseline = peer ratio × revenue × horizon.
    horizon = max(1, inputs.forecast_horizon_years)
    baseline_annual = (
        inputs.revenue_m * inputs.peer_median_capex_pct_revenue
    )
    baseline_total = baseline_annual * horizon

    # Peer-ratio gap: years_below_peer × annual gap.
    gap_pct = (
        inputs.peer_median_capex_pct_revenue
        - inputs.historical_capex_pct_revenue
    )
    deferred_catchup = max(
        0.0,
        inputs.revenue_m * gap_pct *
        max(1, inputs.years_below_peer),
    )

    components: List[CapexComponent] = [
        CapexComponent(
            name="baseline_peer_equivalent",
            amount_m=round(baseline_total, 2),
            partner_commentary=(
                f"Baseline peer-equivalent capex at "
                f"{inputs.peer_median_capex_pct_revenue*100:.1f}% "
                f"of revenue over {horizon} yrs."
            ),
        ),
        CapexComponent(
            name="deferred_maintenance_catchup",
            amount_m=round(
                deferred_catchup
                + inputs.deferred_maintenance_backlog_m,
                2,
            ),
            partner_commentary=(
                f"Catchup on "
                f"{inputs.years_below_peer} yrs below peer "
                f"({gap_pct*100:.1f}% gap) + disclosed "
                f"${inputs.deferred_maintenance_backlog_m:,.1f}M "
                "backlog."
                if inputs.years_below_peer > 0 or
                inputs.deferred_maintenance_backlog_m > 0
                else "No deferred-maintenance catchup flagged."
            ),
        ),
        CapexComponent(
            name="new_sites_build",
            amount_m=inputs.new_sites_build_pipeline_m,
            partner_commentary=(
                "New-site build pipeline — not maintenance, "
                "priced above baseline."
                if inputs.new_sites_build_pipeline_m > 0
                else "No new-site build pipeline flagged."
            ),
        ),
        CapexComponent(
            name="it_ehr_modernization",
            amount_m=inputs.it_ehr_modernization_needed_m,
            partner_commentary=(
                "IT / EHR modernization — non-deferrable."
                if inputs.it_ehr_modernization_needed_m > 0
                else "IT stack current; no mandatory "
                      "modernization."
            ),
        ),
        CapexComponent(
            name="clinical_equipment_replacement",
            amount_m=inputs.clinical_equipment_replacement_due_m,
            partner_commentary=(
                "Clinical equipment replacement — typical "
                "7-10yr cycle exposure."
                if inputs.clinical_equipment_replacement_due_m > 0
                else "Equipment cycle current."
            ),
        ),
        CapexComponent(
            name="compliance_cyber_capex",
            amount_m=inputs.compliance_cyber_capex_m,
            partner_commentary=(
                "Compliance / cyber capex — regulatory-"
                "driven; no deferral."
                if inputs.compliance_cyber_capex_m > 0
                else "No flagged compliance capex."
            ),
        ),
    ]

    projected_total = round(
        sum(c.amount_m for c in components), 2
    )

    # FCF vs. EBITDA haircut: cumulative capex / cumulative
    # EBITDA over horizon. Peer ratio as reference.
    cumulative_ebitda = max(0.01, inputs.ebitda_m * horizon)
    actual_ratio = projected_total / cumulative_ebitda
    # Peer reference: peer median capex / revenue × revenue
    # / EBITDA (peer-implied capex/EBITDA ratio).
    peer_ratio = (
        inputs.peer_median_capex_pct_revenue
        * inputs.revenue_m / max(0.01, inputs.ebitda_m)
    )
    haircut_pct = max(0.0, actual_ratio - peer_ratio)

    if haircut_pct >= 0.15:
        note = (
            f"Projected 3-yr capex $"
            f"{projected_total:,.1f}M vs. peer-median "
            f"baseline ${baseline_total:,.1f}M. "
            f"FCF-vs-EBITDA haircut "
            f"{haircut_pct*100:.1f}% — price in. "
            "Capex diligence workstream required."
        )
    elif haircut_pct >= 0.08:
        note = (
            f"Projected 3-yr capex $"
            f"{projected_total:,.1f}M. FCF haircut "
            f"{haircut_pct*100:.1f}% vs peer. Model "
            "explicit."
        )
    elif deferred_catchup > 0:
        note = (
            f"Deferred-maintenance catchup "
            f"${deferred_catchup:,.1f}M identified — "
            "closing-adjustment or retention item."
        )
    else:
        note = (
            f"Projected 3-yr capex $"
            f"{projected_total:,.1f}M in-line with peer "
            "median. No material capex stress."
        )

    return CapexStressReport(
        projected_3yr_capex_m=projected_total,
        peer_ratio_gap_pct=round(gap_pct, 4),
        fcf_vs_ebitda_haircut_pct=round(haircut_pct, 4),
        deferred_catchup_m=round(deferred_catchup, 2),
        components=components,
        partner_note=note,
    )


def render_capex_stress_markdown(
    r: CapexStressReport,
) -> str:
    lines = [
        "# Capex intensity stress",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Projected 3-yr capex: "
        f"${r.projected_3yr_capex_m:,.1f}M",
        f"- Peer-ratio gap: "
        f"{r.peer_ratio_gap_pct*100:.2f}%",
        f"- Deferred catchup: "
        f"${r.deferred_catchup_m:,.1f}M",
        f"- FCF-vs-EBITDA haircut: "
        f"{r.fcf_vs_ebitda_haircut_pct*100:.1f}%",
        "",
        "| Component | $M | Partner commentary |",
        "|---|---|---|",
    ]
    for c in r.components:
        lines.append(
            f"| {c.name} | ${c.amount_m:,.1f}M | "
            f"{c.partner_commentary} |"
        )
    return "\n".join(lines)
