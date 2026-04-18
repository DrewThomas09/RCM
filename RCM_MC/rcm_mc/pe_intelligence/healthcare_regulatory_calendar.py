"""Healthcare regulatory calendar — 2026-2028 events partners track.

Partners carry a mental calendar of regulatory events. "Is the
physician-fee-schedule cut finalized yet? When does the
site-neutral parity phase in? What's CMS proposing for
home-health PDGM year 2?" This module codifies the calendar.

Each event has:

- **Name** (short, partner-recognizable).
- **Effective year-quarter.**
- **Affected subsectors.**
- **Directional impact** (revenue up/down, EBITDA up/down).
- **Partner note** — what to underwrite.

For a given deal (subsector + hold period), the module returns
the events that land mid-hold with their partner-commentary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class RegulatoryEvent:
    name: str
    description: str
    effective_year: int
    effective_quarter: int                  # 1-4
    affected_subsectors: Set[str]
    revenue_impact_pct: float               # -1.0 to 1.0
    direction: str                          # "tailwind" / "headwind"
    partner_note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "effective_year": self.effective_year,
            "effective_quarter": self.effective_quarter,
            "affected_subsectors": sorted(self.affected_subsectors),
            "revenue_impact_pct": self.revenue_impact_pct,
            "direction": self.direction,
            "partner_note": self.partner_note,
        }


# Partner-approximated events 2026-2028. Dates and specifics are
# illustrative for codification; partners refresh against actual
# regulatory docket before IC.
CALENDAR: List[RegulatoryEvent] = [
    RegulatoryEvent(
        name="physician_fee_schedule_2026",
        description=("CMS physician fee schedule cut of 2.8% for "
                      "calendar year 2026."),
        effective_year=2026, effective_quarter=1,
        affected_subsectors={"specialty_practice",
                               "physician_staffing", "outpatient_asc"},
        revenue_impact_pct=-0.028,
        direction="headwind",
        partner_note=("Physician-office rates drop 2.8% Jan 2026. "
                      "If thesis models rate growth 2026+, the "
                      "net needs to include this cut."),
    ),
    RegulatoryEvent(
        name="sequestration_extension_2026",
        description=("2% Medicare sequestration cut remains in "
                      "effect; proposed extension to 4% not yet "
                      "adopted."),
        effective_year=2026, effective_quarter=1,
        affected_subsectors={"hospital", "home_health",
                               "outpatient_asc", "dme_supplier",
                               "specialty_practice",
                               "safety_net_hospital"},
        revenue_impact_pct=-0.020,
        direction="headwind",
        partner_note=("Sequestration is already baked into rate cards; "
                      "the risk is the 4% proposal realizing in 2027-"
                      "2028."),
    ),
    RegulatoryEvent(
        name="site_neutral_hopd_phase2",
        description=("Site-neutral rulemaking phase 2: extends rate "
                      "parity to more HOPD services (evaluation + "
                      "management, specific drug administration)."),
        effective_year=2026, effective_quarter=3,
        affected_subsectors={"hospital", "safety_net_hospital",
                               "outpatient_asc"},
        revenue_impact_pct=-0.06,
        direction="headwind",
        partner_note=("22% rate cut extends to broader HOPD service "
                      "mix. Hospital-outpatient-heavy books must "
                      "model this."),
    ),
    RegulatoryEvent(
        name="home_health_pdgm_recalibration_2026",
        description=("PDGM weights recalibrated — downward for "
                      "routine episodes, slight uplift for complex."),
        effective_year=2026, effective_quarter=1,
        affected_subsectors={"home_health"},
        revenue_impact_pct=-0.035,
        direction="headwind",
        partner_note=("Home-health per-episode revenue drops on "
                      "routine mix; thesis should model 3-4% rate "
                      "compression before volume."),
    ),
    RegulatoryEvent(
        name="medicare_advantage_risk_adjustment_v28",
        description=("MA risk-adjustment model v28 removes codes "
                      "from trigger list; plans have less to pay "
                      "upstream providers."),
        effective_year=2026, effective_quarter=1,
        affected_subsectors={"specialty_practice",
                               "home_health", "physician_staffing",
                               "hospital"},
        revenue_impact_pct=-0.015,
        direction="headwind",
        partner_note=("MA plans compress rates passed to providers "
                      "as their risk-adjustment upstream shrinks. "
                      "Do not assume MA absorbs FFS rate cuts."),
    ),
    RegulatoryEvent(
        name="no_surprises_act_idr_cycle_2026",
        description=("IDR (independent dispute resolution) volume "
                      "continues; final-offer arbitration continues "
                      "to compress OON billing economics."),
        effective_year=2026, effective_quarter=2,
        affected_subsectors={"physician_staffing"},
        revenue_impact_pct=-0.04,
        direction="headwind",
        partner_note=("NSA IDR outcomes favor plans over providers "
                      "65-70% of the time. Any OON-dependent book "
                      "is compressing by ~4% annually until in-"
                      "network."),
    ),
    RegulatoryEvent(
        name="medicaid_state_redetermination_wave_2",
        description=("State Medicaid eligibility re-determinations "
                      "continue; enrollment down 6-10% in targeted "
                      "states."),
        effective_year=2026, effective_quarter=2,
        affected_subsectors={"safety_net_hospital", "hospital",
                               "home_health"},
        revenue_impact_pct=-0.025,
        direction="headwind",
        partner_note=("State-heavy Medicaid books will lose "
                      "enrollees to uninsured; uncompensated care "
                      "rises; net EBITDA drag 2-3%."),
    ),
    RegulatoryEvent(
        name="asc_covered_procedures_expansion",
        description=("CMS expands ASC-covered-procedures list to "
                      "include additional ortho + cardiology "
                      "procedures."),
        effective_year=2026, effective_quarter=1,
        affected_subsectors={"outpatient_asc"},
        revenue_impact_pct=0.05,
        direction="tailwind",
        partner_note=("ASC volume tailwind as more procedures shift "
                      "out of IP. Underwrite ramp slowly — "
                      "credentialing + facility readiness take 12mo."),
    ),
    RegulatoryEvent(
        name="oig_antikickback_enforcement_bump",
        description=("DOJ/OIG continues increased enforcement "
                      "activity; whistleblower filings up."),
        effective_year=2026, effective_quarter=2,
        affected_subsectors={"specialty_practice",
                               "physician_staffing", "dme_supplier",
                               "hospital"},
        revenue_impact_pct=0.0,
        direction="headwind",
        partner_note=("Not a rate event — a litigation-exposure "
                      "event. Forensic billing diligence is not "
                      "optional in any subsector with material "
                      "Medicare revenue."),
    ),
    RegulatoryEvent(
        name="340b_program_integrity_rule_2027",
        description=("340B contract-pharmacy restrictions tightened; "
                      "payment methodology revisited."),
        effective_year=2027, effective_quarter=1,
        affected_subsectors={"safety_net_hospital",
                               "home_health", "hospital"},
        revenue_impact_pct=-0.02,
        direction="headwind",
        partner_note=("340B margin contribution compresses for "
                      "hospitals and the pharmacy partners they "
                      "use. If 340B is in the thesis, stress test."),
    ),
    RegulatoryEvent(
        name="hospital_payment_advisory_2027",
        description=("MedPAC advises CMS to adjust hospital IPPS "
                      "update; outcome uncertain."),
        effective_year=2027, effective_quarter=3,
        affected_subsectors={"hospital", "safety_net_hospital"},
        revenue_impact_pct=-0.015,
        direction="headwind",
        partner_note=("Timing + magnitude uncertain, but 2027 "
                      "hospital rate profile is a known downside."),
    ),
    RegulatoryEvent(
        name="commercial_rate_transparency_rule_2028",
        description=("Price-transparency rule enforcement ramps; "
                      "commercial rate bands become visible."),
        effective_year=2028, effective_quarter=1,
        affected_subsectors={"specialty_practice", "hospital",
                               "outpatient_asc",
                               "safety_net_hospital"},
        revenue_impact_pct=-0.01,
        direction="headwind",
        partner_note=("Rate transparency compresses the tails of "
                      "commercial pricing. Asymmetric — it hurts "
                      "high-priced outliers more than median."),
    ),
]


@dataclass
class CalendarHit:
    event: RegulatoryEvent
    hold_year: int                         # fund hold-year (1-N) it hits
    affects_this_deal: bool


@dataclass
class CalendarReport:
    subsector: str
    hold_start_year: int
    hold_years: int
    hits: List[CalendarHit] = field(default_factory=list)
    cumulative_revenue_impact_pct: float = 0.0
    tailwind_count: int = 0
    headwind_count: int = 0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsector": self.subsector,
            "hold_start_year": self.hold_start_year,
            "hold_years": self.hold_years,
            "hits": [
                {"event": h.event.to_dict(),
                 "hold_year": h.hold_year,
                 "affects_this_deal": h.affects_this_deal}
                for h in self.hits
            ],
            "cumulative_revenue_impact_pct": self.cumulative_revenue_impact_pct,
            "tailwind_count": self.tailwind_count,
            "headwind_count": self.headwind_count,
            "partner_note": self.partner_note,
        }


def events_for_deal(subsector: str, hold_start_year: int,
                    hold_years: int) -> CalendarReport:
    hits: List[CalendarHit] = []
    end_year = hold_start_year + hold_years
    for ev in CALENDAR:
        affects = subsector in ev.affected_subsectors \
                  and hold_start_year <= ev.effective_year <= end_year
        if affects:
            hold_year = ev.effective_year - hold_start_year + 1
            hits.append(CalendarHit(
                event=ev, hold_year=hold_year,
                affects_this_deal=True,
            ))

    tailwinds = sum(1 for h in hits if h.event.direction == "tailwind")
    headwinds = sum(1 for h in hits if h.event.direction == "headwind")
    cum_impact = sum(h.event.revenue_impact_pct for h in hits)

    if cum_impact <= -0.10:
        note = (f"Cumulative regulatory drag of "
                f"{cum_impact*100:.1f}% over hold. This is a "
                "regulatory-headwind subsector right now — thesis "
                "should not rely on rate growth unless specifically "
                "contracted.")
    elif cum_impact <= -0.05:
        note = (f"Net regulatory headwind of {cum_impact*100:.1f}%. "
                "Model flat real rates in base case.")
    elif cum_impact > 0:
        note = (f"Net tailwind of {cum_impact*100:.1f}%, mostly from "
                f"{tailwinds} event(s). Confirm ramp assumptions "
                "against regulatory timelines.")
    else:
        note = (f"Cumulative regulatory impact ~{cum_impact*100:.1f}% "
                "— manageable. Monitor ongoing MedPAC + CMS docket.")

    return CalendarReport(
        subsector=subsector,
        hold_start_year=hold_start_year,
        hold_years=hold_years,
        hits=sorted(hits, key=lambda h: (h.event.effective_year,
                                          h.event.effective_quarter)),
        cumulative_revenue_impact_pct=round(cum_impact, 4),
        tailwind_count=tailwinds,
        headwind_count=headwinds,
        partner_note=note,
    )


def render_calendar_markdown(r: CalendarReport) -> str:
    lines = [
        f"# Regulatory calendar — {r.subsector} "
        f"({r.hold_start_year}-{r.hold_start_year + r.hold_years})",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Events hitting mid-hold: {len(r.hits)} "
        f"({r.tailwind_count} tailwinds / {r.headwind_count} headwinds)",
        f"- Cumulative revenue impact: "
        f"{r.cumulative_revenue_impact_pct*100:+.1f}%",
        "",
        "| Year | Quarter | Event | Direction | Rev impact | Note |",
        "|---:|---:|---|---|---:|---|",
    ]
    for h in r.hits:
        lines.append(
            f"| {h.event.effective_year} | Q{h.event.effective_quarter} | "
            f"{h.event.name} | {h.event.direction} | "
            f"{h.event.revenue_impact_pct*100:+.1f}% | "
            f"{h.event.partner_note} |"
        )
    return "\n".join(lines)


def list_all_events() -> List[RegulatoryEvent]:
    return list(CALENDAR)
