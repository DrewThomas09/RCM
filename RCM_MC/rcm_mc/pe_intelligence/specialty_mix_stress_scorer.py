"""Specialty mix stress — revenue concentration within specialties.

Partner statement: "A practice doing 80% spine surgery
with 4 surgeons is not a specialty practice — it's a
single-service line. Lose 2 surgeons and the revenue is
gone."

Distinct from:
- `referral_flow_dependency_scorer` — upstream referral
  sources.
- `customer_concentration_drilldown` — downstream payer /
  customer concentration.

This module measures **revenue mix within specialties /
procedures** — the third concentration axis. Common in
physician practices, ASCs, labs, imaging centers.

### 5 dimensions scored

1. **top_specialty_revenue_pct** — % of revenue from the
   single largest specialty.
2. **top_procedure_revenue_pct** — % from the single
   largest procedure / CPT.
3. **n_physicians_generating_top_specialty_revenue** —
   concentration within the specialty.
4. **commercial_vs_total_mix_in_top_specialty** —
   whether top specialty is commercial-heavy (better) or
   Medicare-heavy (worse).
5. **ancillary_integration_tied_to_specialty** — lose
   the specialty → lose the ancillary (DI, lab, etc.).

### Tier ladder

- **well_diversified** (0-1 flags) — no material
  concentration risk.
- **moderately_concentrated** (2 flags) — retention
  focus on specialty leaders.
- **heavily_concentrated** (3 flags) — haircut
  underwrite, closing-condition retention.
- **single_service_line** (4+ flags) — this is a
  single-service business; price as such (add-on, not
  platform).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SpecialtyMixFlag:
    name: str
    triggered: bool
    partner_comment: str


@dataclass
class SpecialtyMixInputs:
    top_specialty_revenue_pct: float = 0.0
    top_procedure_revenue_pct: float = 0.0
    n_physicians_generating_top_specialty_revenue: int = 0
    top_specialty_commercial_pct: float = 0.0
    ancillary_integration_tied_to_top_specialty: bool = False
    ebitda_m: float = 0.0


@dataclass
class SpecialtyMixReport:
    tier: str                              # well_diversified / moderate /
                                            # heavy / single_service_line
    flags: List[SpecialtyMixFlag] = field(default_factory=list)
    triggered_count: int = 0
    concentration_risk_m: float = 0.0      # partner-estimated EBITDA exposure
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tier": self.tier,
            "flags": [
                {"name": f.name,
                 "triggered": f.triggered,
                 "partner_comment": f.partner_comment}
                for f in self.flags
            ],
            "triggered_count": self.triggered_count,
            "concentration_risk_m": self.concentration_risk_m,
            "partner_note": self.partner_note,
        }


def score_specialty_mix_stress(
    inputs: SpecialtyMixInputs,
) -> SpecialtyMixReport:
    flags: List[SpecialtyMixFlag] = []

    # Flag 1: top specialty > 60% revenue.
    top_specialty = inputs.top_specialty_revenue_pct >= 0.60
    flags.append(SpecialtyMixFlag(
        name="top_specialty_revenue_gt_60pct",
        triggered=top_specialty,
        partner_comment=(
            f"Top specialty "
            f"{inputs.top_specialty_revenue_pct*100:.0f}% "
            "of revenue — single-service-line exposure."
            if top_specialty else
            f"Top specialty "
            f"{inputs.top_specialty_revenue_pct*100:.0f}% "
            "of revenue — diversified."
        ),
    ))

    # Flag 2: top procedure > 35% revenue.
    top_proc = inputs.top_procedure_revenue_pct >= 0.35
    flags.append(SpecialtyMixFlag(
        name="top_procedure_revenue_gt_35pct",
        triggered=top_proc,
        partner_comment=(
            f"Top procedure "
            f"{inputs.top_procedure_revenue_pct*100:.0f}% "
            "of revenue — single-CPT / single-procedure "
            "exposure."
            if top_proc else
            "Procedure mix diversified."
        ),
    ))

    # Flag 3: fewer than 4 physicians driving top specialty.
    thin_bench = (
        inputs.n_physicians_generating_top_specialty_revenue <= 3
    )
    flags.append(SpecialtyMixFlag(
        name="thin_physician_bench_in_top_specialty",
        triggered=thin_bench,
        partner_comment=(
            f"Only "
            f"{inputs.n_physicians_generating_top_specialty_revenue} "
            "physician(s) drive top specialty — thin "
            "bench."
            if thin_bench else
            "Physician bench in top specialty adequate."
        ),
    ))

    # Flag 4: top specialty is Medicare-heavy.
    commercial_heavy = inputs.top_specialty_commercial_pct >= 0.55
    medicare_heavy = inputs.top_specialty_commercial_pct <= 0.30
    flags.append(SpecialtyMixFlag(
        name="top_specialty_medicare_heavy",
        triggered=medicare_heavy,
        partner_comment=(
            f"Top specialty Medicare-heavy "
            f"({(1 - inputs.top_specialty_commercial_pct)*100:.0f}% "
            "non-commercial) — reimbursement exposure "
            "concentrates in the concentration."
            if medicare_heavy else
            "Top specialty has reasonable commercial share."
        ),
    ))

    # Flag 5: ancillary tied to top specialty.
    ancillary = inputs.ancillary_integration_tied_to_top_specialty
    flags.append(SpecialtyMixFlag(
        name="ancillary_tied_to_top_specialty",
        triggered=ancillary,
        partner_comment=(
            "Ancillary revenue (DI / lab / surgery) tied "
            "to top specialty — lose the specialty, lose "
            "ancillary."
            if ancillary else
            "Ancillary revenue diversified across "
            "specialties."
        ),
    ))

    triggered = sum(1 for f in flags if f.triggered)

    # Tier ladder.
    if triggered >= 4:
        tier = "single_service_line"
        concentration_m = round(
            inputs.ebitda_m *
            inputs.top_specialty_revenue_pct *
            0.45,      # ~45% of top-specialty EBITDA
            2,
        )
        note = (
            f"{triggered} specialty-mix flags — this is a "
            f"single-service business. Partner: price as "
            f"an add-on, not a platform. ~${concentration_m:,.1f}M "
            "EBITDA at risk if specialty falters."
        )
    elif triggered >= 3:
        tier = "heavily_concentrated"
        concentration_m = round(
            inputs.ebitda_m *
            inputs.top_specialty_revenue_pct *
            0.30,
            2,
        )
        note = (
            f"{triggered} flags — heavily concentrated in "
            "top specialty. Partner: haircut underwrite by "
            f"${concentration_m:,.1f}M and make specialty-"
            "leader retention a closing condition."
        )
    elif triggered == 2:
        tier = "moderately_concentrated"
        concentration_m = round(
            inputs.ebitda_m *
            inputs.top_specialty_revenue_pct *
            0.15,
            2,
        )
        note = (
            f"{triggered} flags — moderate concentration. "
            "Partner: 100-day plan prioritizes specialty-"
            "leader retention + horizontal diversification."
        )
    else:
        tier = "well_diversified"
        concentration_m = 0.0
        note = (
            "Specialty mix well-diversified. No material "
            "concentration gating."
        )

    return SpecialtyMixReport(
        tier=tier,
        flags=flags,
        triggered_count=triggered,
        concentration_risk_m=concentration_m,
        partner_note=note,
    )


def render_specialty_mix_markdown(
    r: SpecialtyMixReport,
) -> str:
    lines = [
        "# Specialty mix stress",
        "",
        f"**Tier:** `{r.tier}`",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Triggered flags: {r.triggered_count} / "
        f"{len(r.flags)}",
        f"- Concentration-risk EBITDA: "
        f"${r.concentration_risk_m:,.1f}M",
        "",
        "| Flag | Triggered | Partner comment |",
        "|---|---|---|",
    ]
    for f in r.flags:
        check = "✓" if f.triggered else "—"
        lines.append(
            f"| {f.name} | {check} | {f.partner_comment} |"
        )
    return "\n".join(lines)
