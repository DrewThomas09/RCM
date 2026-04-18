"""Site-neutral / OBBBA impact — specific $ exposure by service line.

Partner statement: "Site-neutral isn't a vague risk.
It's a specific set of codes, on a specific schedule,
with a specific rate delta. OBBBA expanded the
services that pay the same rate regardless of site —
and the arbitrage between HOPD and freestanding is
gone for those codes. I need to know: which of the
seller's HOPD codes are now site-neutral, what was
the HOPD-to-freestanding rate delta, how many dollars
of NPR does that represent, and does the thesis
assume the pre-OBBBA arbitrage continues? If it does,
the thesis is wrong."

Distinct from:
- `regulatory_stress` — generic rate shocks.
- `regulatory_watch` — calendar of events.
- `reimbursement_cliff_calendar_2026_2029` — broader
  CMS/state calendar.

This module is narrow on purpose: given a seller's
service-line NPR and HOPD/freestanding share, compute
the specific dollar impact of the site-neutral codes
expanding over the hold.

### Site-neutral service line bands (OBBBA-era)

Typical HOPD-to-freestanding rate delta by service
family (CMS OPPS vs MPFS rates). The arbitrage is
what collapses as CMS expands site-neutral scope.

| Service family | HOPD premium pre | Site-neutral by year |
|---|---|---|
| clinic_visit_E_M | 40-60% | 2022 (done) |
| drug_admin | 25-40% | 2022 (done) |
| imaging_diagnostic | 20-35% | 2025 (proposed) |
| imaging_advanced | 30-50% | 2026 (likely) |
| procedures_intermediate | 15-30% | 2027 (plausible) |
| gi_endoscopy | 20-40% | 2027 (plausible) |
| cardiac_diagnostic | 25-45% | 2028 (exposed) |
| orthopedic_procedure | 30-55% | 2028 (exposed) |

### Output

Per-service-line impact: NPR at risk, realized rate
delta × exposure fraction × NPR × years remaining =
cumulative EBITDA-level exposure (contribution
margin applied).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


SERVICE_LINE_BANDS: Dict[str, Dict[str, Any]] = {
    "clinic_visit_E_M": {
        "premium_pct_pre": 0.50,
        "site_neutral_year": 2022,
        "note": "Already site-neutral — any remaining premium is grandfathered.",
    },
    "drug_admin": {
        "premium_pct_pre": 0.30,
        "site_neutral_year": 2022,
        "note": "Already site-neutral.",
    },
    "imaging_diagnostic": {
        "premium_pct_pre": 0.25,
        "site_neutral_year": 2025,
        "note": "Proposed rule — 50% probability of finalization.",
    },
    "imaging_advanced": {
        "premium_pct_pre": 0.40,
        "site_neutral_year": 2026,
        "note": "Likely — CMS signaling via proposed rule.",
    },
    "procedures_intermediate": {
        "premium_pct_pre": 0.22,
        "site_neutral_year": 2027,
        "note": "Plausible — next CMS rulemaking cycle.",
    },
    "gi_endoscopy": {
        "premium_pct_pre": 0.30,
        "site_neutral_year": 2027,
        "note": "Plausible — AdvaMed lobbying may delay.",
    },
    "cardiac_diagnostic": {
        "premium_pct_pre": 0.35,
        "site_neutral_year": 2028,
        "note": "Exposed — actively discussed in rule preamble.",
    },
    "orthopedic_procedure": {
        "premium_pct_pre": 0.42,
        "site_neutral_year": 2028,
        "note": "Exposed — ASC alternative exists.",
    },
}


@dataclass
class ServiceLineExposure:
    service_line: str
    npr_m: float
    hopd_share_pct: float       # 0..1, HOPD as % of service-line NPR
    grandfathered: bool = False


@dataclass
class SiteNeutralInputs:
    service_lines: List[ServiceLineExposure] = field(
        default_factory=list)
    hold_start_year: int = 2026
    hold_years: int = 5
    contribution_margin_pct: float = 0.35


@dataclass
class ServiceLineImpact:
    service_line: str
    hits_in_hold: bool
    site_neutral_effective_year: int
    years_affected: int
    annual_npr_at_risk_m: float
    annual_ebitda_at_risk_m: float
    cumulative_ebitda_m: float
    note: str


@dataclass
class SiteNeutralReport:
    impacts: List[ServiceLineImpact] = field(
        default_factory=list)
    total_cumulative_ebitda_m: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "impacts": [
                {"service_line": i.service_line,
                 "hits_in_hold": i.hits_in_hold,
                 "site_neutral_effective_year":
                     i.site_neutral_effective_year,
                 "years_affected": i.years_affected,
                 "annual_npr_at_risk_m":
                     i.annual_npr_at_risk_m,
                 "annual_ebitda_at_risk_m":
                     i.annual_ebitda_at_risk_m,
                 "cumulative_ebitda_m":
                     i.cumulative_ebitda_m,
                 "note": i.note}
                for i in self.impacts
            ],
            "total_cumulative_ebitda_m":
                self.total_cumulative_ebitda_m,
            "partner_note": self.partner_note,
        }


def compute_site_neutral_exposure(
    inputs: SiteNeutralInputs,
) -> SiteNeutralReport:
    impacts: List[ServiceLineImpact] = []
    total_cumulative = 0.0
    hold_end_year = (
        inputs.hold_start_year + inputs.hold_years
    )

    for sl in inputs.service_lines:
        band = SERVICE_LINE_BANDS.get(sl.service_line)
        if band is None:
            impacts.append(ServiceLineImpact(
                service_line=sl.service_line,
                hits_in_hold=False,
                site_neutral_effective_year=0,
                years_affected=0,
                annual_npr_at_risk_m=0.0,
                annual_ebitda_at_risk_m=0.0,
                cumulative_ebitda_m=0.0,
                note="Service line not in catalog.",
            ))
            continue

        effective_year = band["site_neutral_year"]
        note = band["note"]
        premium = band["premium_pct_pre"]

        if sl.grandfathered:
            impacts.append(ServiceLineImpact(
                service_line=sl.service_line,
                hits_in_hold=False,
                site_neutral_effective_year=effective_year,
                years_affected=0,
                annual_npr_at_risk_m=0.0,
                annual_ebitda_at_risk_m=0.0,
                cumulative_ebitda_m=0.0,
                note=note + " Grandfathered at site-level.",
            ))
            continue

        hits = effective_year < hold_end_year
        # Years affected in hold; if effective year is
        # before hold start, all hold years affected.
        if effective_year <= inputs.hold_start_year:
            years_affected = inputs.hold_years
        else:
            years_affected = max(
                0, hold_end_year - effective_year)

        hopd_npr_m = sl.npr_m * sl.hopd_share_pct
        # Rate collapse: HOPD premium goes to 0;
        # realized NPR drop = hopd_npr × premium / (1+premium)
        annual_npr_risk = (
            hopd_npr_m * premium / (1 + premium)
        )
        annual_ebitda_risk = (
            annual_npr_risk *
            inputs.contribution_margin_pct
        )
        cumulative = annual_ebitda_risk * years_affected
        total_cumulative += cumulative

        impacts.append(ServiceLineImpact(
            service_line=sl.service_line,
            hits_in_hold=hits and years_affected > 0,
            site_neutral_effective_year=effective_year,
            years_affected=years_affected,
            annual_npr_at_risk_m=round(
                annual_npr_risk, 2),
            annual_ebitda_at_risk_m=round(
                annual_ebitda_risk, 2),
            cumulative_ebitda_m=round(cumulative, 2),
            note=note,
        ))

    # Partner note
    if total_cumulative > 20:
        pn = (
            f"Site-neutral exposure over hold: "
            f"${total_cumulative:.1f}M cumulative EBITDA. "
            "Material — bake into exit-case EBITDA or "
            "expect exit buyer to model it against us. "
            "Price into purchase multiple now, not after "
            "LOI."
        )
    elif total_cumulative > 5:
        pn = (
            f"Site-neutral exposure: "
            f"${total_cumulative:.1f}M cumulative. "
            "Manageable but not zero — include in the "
            "base-case bridge and track CMS rulemaking."
        )
    elif total_cumulative > 0:
        pn = (
            f"Minor site-neutral exposure "
            f"(${total_cumulative:.1f}M). Monitor but "
            "does not re-price the deal."
        )
    else:
        pn = (
            "No material site-neutral exposure — "
            "service lines are already site-neutral or "
            "out of scope in hold window."
        )

    return SiteNeutralReport(
        impacts=impacts,
        total_cumulative_ebitda_m=round(
            total_cumulative, 2),
        partner_note=pn,
    )


def render_site_neutral_markdown(
    r: SiteNeutralReport,
) -> str:
    lines = [
        "# Site-neutral / OBBBA exposure",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Total cumulative EBITDA at risk: "
        f"${r.total_cumulative_ebitda_m:.1f}M",
        "",
        "| Service line | Effective year | Hits in hold | "
        "Years affected | Annual NPR at risk | "
        "Cumulative EBITDA | Note |",
        "|---|---|---|---|---|---|---|",
    ]
    for i in r.impacts:
        lines.append(
            f"| {i.service_line} | "
            f"{i.site_neutral_effective_year} | "
            f"{'✓' if i.hits_in_hold else '—'} | "
            f"{i.years_affected} | "
            f"${i.annual_npr_at_risk_m:.2f}M | "
            f"${i.cumulative_ebitda_m:.2f}M | "
            f"{i.note} |"
        )
    return "\n".join(lines)
