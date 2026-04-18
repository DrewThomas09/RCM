"""Reimbursement cliff calendar 2026-2029 — pre-seeded events.

Partner statement: "I shouldn't have to type the CMS rules
into every deal I look at. The calendar is known; the
question is which ones hit *this* deal's hold window."

Complements `reimbursement_cliff.py` (takes partner-
supplied cliff lists) and `healthcare_regulatory_calendar`
(general event catalog). This module is a **pre-seeded
catalog** of specific known/anticipated rate events in
2026-2029 keyed to subsector, so a partner can scan
instantly.

All entries represent partner-level knowledge of the
healthcare regulatory calendar at the time of writing
(2026-04). Years and magnitudes are partner-judgment
approximations that should be refreshed as rules finalize.

### Events modeled

- **obbba_medicare_cut_phase1** — 2026, -3% Medicare FFS.
- **obbba_medicare_cut_phase2** — 2027, -2% cumulative.
- **sequestration_extension_2027** — 2027, -2% Medicare.
- **site_neutral_hopd_finalization** — 2028,
  -22% rate reset on affected HOPD services.
- **pama_lab_cuts_round_4** — 2026, -15% phased.
- **ma_benchmark_reset_yearly** — annual +/- 1-2%.
- **pdgm_behavioral_adjust_2027** — home health -1.5%.
- **pdpm_snf_recalibration_2027** — SNF -0.5%.
- **hospice_cap_tightening_2028** — -0.8% of revenue.
- **dme_competitive_bid_round_2028** — -30-50% on
  affected SKUs.
- **340b_manufacturer_restrictions_2026** — -5-8% of
  340B revenue.
- **wage_index_rural_floor_2027** — rural hospitals +1%.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CliffEvent:
    id: str
    name: str
    effective_year: int
    affected_payer: str              # medicare / medicaid / commercial / 340b
    rate_change_bps: float            # negative for cuts
    subsectors: List[str] = field(default_factory=list)
    partner_note: str = ""


CLIFF_CALENDAR: List[CliffEvent] = [
    CliffEvent(
        id="obbba_medicare_cut_phase1",
        name="OBBBA Medicare cut — phase 1",
        effective_year=2026,
        affected_payer="medicare",
        rate_change_bps=-300,
        subsectors=[
            "hospital_general", "home_health", "hospice",
            "ambulatory_surgery_center", "clinical_lab",
            "durable_medical_equipment",
        ],
        partner_note=(
            "OBBBA phase-1 cut hits every Medicare-exposed "
            "subsector. Model base case off post-cut rates."
        ),
    ),
    CliffEvent(
        id="obbba_medicare_cut_phase2",
        name="OBBBA Medicare cut — phase 2",
        effective_year=2027,
        affected_payer="medicare",
        rate_change_bps=-200,
        subsectors=[
            "hospital_general", "home_health", "hospice",
            "ambulatory_surgery_center", "clinical_lab",
            "durable_medical_equipment",
        ],
        partner_note=(
            "Phase-2 cumulative. Partners price hold-period "
            "Medicare revenue at combined -5% vs. 2025."
        ),
    ),
    CliffEvent(
        id="sequestration_extension_2027",
        name="Sequestration 2% extension",
        effective_year=2027,
        affected_payer="medicare",
        rate_change_bps=-200,
        subsectors=[
            "hospital_general", "specialty_physician_practice",
            "home_health", "hospice", "ambulatory_surgery_center",
            "clinical_lab", "durable_medical_equipment",
        ],
        partner_note=(
            "Likely 85% probability of extension through "
            "2027-2028. Stack with OBBBA — do not "
            "double-discount."
        ),
    ),
    CliffEvent(
        id="site_neutral_hopd_finalization",
        name="Site-neutral HOPD finalization",
        effective_year=2028,
        affected_payer="medicare",
        rate_change_bps=-2200,   # -22% rate reset
        subsectors=[
            "hospital_general",
            "ambulatory_surgery_center",
        ],
        partner_note=(
            "Equalizes HOPD rates to ASC / physician-office "
            "levels on affected services. Model at -22% on "
            "exposed HOPD revenue only."
        ),
    ),
    CliffEvent(
        id="pama_lab_cuts_round_4",
        name="PAMA lab-rate cuts — round 4",
        effective_year=2026,
        affected_payer="medicare",
        rate_change_bps=-1500,   # -15% compound over round
        subsectors=["clinical_lab"],
        partner_note=(
            "PAMA-based rate adjustment; commercial "
            "follows with lag. Clinical-lab EBITDA "
            "structurally compresses."
        ),
    ),
    CliffEvent(
        id="ma_benchmark_reset_2026",
        name="MA benchmark reset 2026",
        effective_year=2026,
        affected_payer="medicare",
        rate_change_bps=-150,
        subsectors=[
            "specialty_physician_practice", "hospital_general",
            "home_health",
        ],
        partner_note=(
            "Annual MA benchmark adjustment. Net -1.5% "
            "expected in 2026 after quality / risk-"
            "adjustment changes."
        ),
    ),
    CliffEvent(
        id="pdgm_behavioral_adjust_2027",
        name="PDGM behavioral adjustment 2027",
        effective_year=2027,
        affected_payer="medicare",
        rate_change_bps=-150,
        subsectors=["home_health"],
        partner_note=(
            "CMS applies periodic behavioral adjustments "
            "reflecting coding-intensity changes. Home "
            "health agencies with strong CDI lose less."
        ),
    ),
    CliffEvent(
        id="pdpm_snf_recalibration_2027",
        name="PDPM SNF parity recalibration",
        effective_year=2027,
        affected_payer="medicare",
        rate_change_bps=-50,
        subsectors=["home_health", "hospice"],
        partner_note=(
            "CMS recalibrates for PDPM budget neutrality. "
            "Minor headwind; factor into peer base but not "
            "thesis-breaker."
        ),
    ),
    CliffEvent(
        id="hospice_cap_tightening_2028",
        name="Hospice cap tightening",
        effective_year=2028,
        affected_payer="medicare",
        rate_change_bps=-80,
        subsectors=["hospice"],
        partner_note=(
            "Aggregate cap growth pegged to CPI-U. "
            "Long-LOS hospices compress most. Audit "
            "history is the partner's real signal."
        ),
    ),
    CliffEvent(
        id="dme_competitive_bid_round_2028",
        name="DME competitive bidding round 2028",
        effective_year=2028,
        affected_payer="medicare",
        rate_change_bps=-4000,   # -40% on affected SKUs
        subsectors=["durable_medical_equipment"],
        partner_note=(
            "Competitive-bid rounds historically cut "
            "Medicare rates 30-50% on affected product "
            "lines. Cover concentrated CPAP / oxygen / "
            "mobility exposure."
        ),
    ),
    CliffEvent(
        id="340b_manufacturer_restrictions_2026",
        name="340B manufacturer restriction expansion",
        effective_year=2026,
        affected_payer="340b",
        rate_change_bps=-700,
        subsectors=["hospital_general", "clinical_lab"],
        partner_note=(
            "Manufacturer contract-pharmacy restrictions "
            "expanding. 340B revenue tails compress 5-8% "
            "where contract-pharmacy share is high."
        ),
    ),
    CliffEvent(
        id="wage_index_rural_floor_2027",
        name="Rural wage index floor",
        effective_year=2027,
        affected_payer="medicare",
        rate_change_bps=+100,
        subsectors=["hospital_general"],
        partner_note=(
            "Rural wage-index floor implementation. +1% "
            "for rural hospitals; urban counterparts "
            "see neutral-to-slightly-negative."
        ),
    ),
]


@dataclass
class CalendarHit:
    event: CliffEvent
    relative_year: int            # years from hold start

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event": {
                "id": self.event.id,
                "name": self.event.name,
                "effective_year": self.event.effective_year,
                "affected_payer": self.event.affected_payer,
                "rate_change_bps": self.event.rate_change_bps,
                "subsectors": list(self.event.subsectors),
                "partner_note": self.event.partner_note,
            },
            "relative_year": self.relative_year,
        }


@dataclass
class CalendarReport:
    subsector: str
    hold_start_year: int
    hold_end_year: int
    hits: List[CalendarHit] = field(default_factory=list)
    total_bps_in_hold: float = 0.0
    partner_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsector": self.subsector,
            "hold_start_year": self.hold_start_year,
            "hold_end_year": self.hold_end_year,
            "hits": [h.to_dict() for h in self.hits],
            "total_bps_in_hold": self.total_bps_in_hold,
            "partner_note": self.partner_note,
        }


def scan_cliff_calendar_for_deal(
    subsector: str,
    hold_start_year: int,
    hold_years: int = 5,
) -> CalendarReport:
    """Return cliff events landing within a deal's hold
    window for the given subsector."""
    hold_end = hold_start_year + hold_years - 1
    hits: List[CalendarHit] = []
    total = 0.0
    for ev in CLIFF_CALENDAR:
        if subsector not in ev.subsectors:
            continue
        if ev.effective_year < hold_start_year:
            continue
        if ev.effective_year > hold_end:
            continue
        hits.append(CalendarHit(
            event=ev,
            relative_year=ev.effective_year - hold_start_year,
        ))
        total += ev.rate_change_bps

    # Sort by effective year.
    hits.sort(key=lambda h: h.event.effective_year)

    if not hits:
        note = (
            f"No cliff events in {subsector} for hold "
            f"{hold_start_year}-{hold_end}. Partner: still "
            "monitor rulemaking comment periods."
        )
    elif total <= -500:
        note = (
            f"{len(hits)} cliff events totaling "
            f"{total:+.0f} bps of rate. Partner: material "
            "headwind — bake into base case, not bear."
        )
    elif total <= -200:
        note = (
            f"{len(hits)} cliff events totaling "
            f"{total:+.0f} bps. Partner: meaningful but "
            "manageable; model explicitly."
        )
    else:
        note = (
            f"{len(hits)} cliff events totaling "
            f"{total:+.0f} bps. Partner: modest headwind."
        )

    return CalendarReport(
        subsector=subsector,
        hold_start_year=hold_start_year,
        hold_end_year=hold_end,
        hits=hits,
        total_bps_in_hold=round(total, 1),
        partner_note=note,
    )


def list_cliff_event_ids() -> List[str]:
    return [ev.id for ev in CLIFF_CALENDAR]


def render_cliff_calendar_markdown(
    r: CalendarReport,
) -> str:
    lines = [
        f"# Reimbursement cliff calendar — {r.subsector}",
        "",
        f"_{r.partner_note}_",
        "",
        f"- Hold: {r.hold_start_year}–{r.hold_end_year}",
        f"- Total in-hold bps: {r.total_bps_in_hold:+.0f}",
        f"- Hits: {len(r.hits)}",
        "",
        "| Year | Event | Payer | bps | Partner note |",
        "|---|---|---|---|---|",
    ]
    for h in r.hits:
        ev = h.event
        lines.append(
            f"| {ev.effective_year} | {ev.name} | "
            f"{ev.affected_payer} | {ev.rate_change_bps:+.0f} | "
            f"{ev.partner_note} |"
        )
    return "\n".join(lines)
