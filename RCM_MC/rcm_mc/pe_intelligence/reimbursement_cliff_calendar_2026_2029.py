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


@dataclass
class PayerExposure:
    """Cumulative in-hold rate cut attributable to one payer channel."""
    payer: str
    total_bps: float
    event_count: int
    worst_event: str
    worst_bps: float

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class CliffExposure:
    """Decomposition of the in-hold cliff bps — by payer channel and
    as a cumulative erosion curve over the hold.

    Pure function of the report's hits: each payer total and each
    year's cumulative figure recomputes from the cited events, so the
    'is this a Medicare story or a commercial story?' read is
    auditable. Stays in basis points — no revenue base is assumed, so
    nothing is fabricated; the page translates to dollars only when
    the partner supplies a base.
    """
    by_payer: List[PayerExposure]
    cumulative_by_relative_year: List[tuple]   # (relative_year, cum_bps)
    dominant_payer: Optional[str]
    dominant_share: float                       # dominant payer bps / total
    note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "by_payer": [p.to_dict() for p in self.by_payer],
            "cumulative_by_relative_year": [
                {"relative_year": y, "cumulative_bps": b}
                for y, b in self.cumulative_by_relative_year
            ],
            "dominant_payer": self.dominant_payer,
            "dominant_share": self.dominant_share,
            "note": self.note,
        }


def analyze_cliff_exposure(report: CalendarReport) -> CliffExposure:
    """Group the in-hold cliffs by payer and build the cumulative
    erosion curve.

    The dominant-payer share answers the first CDD question on a
    reimbursement-exposed deal: which channel is the headwind
    concentrated in? A deal taking −500 bps all from Medicare is a
    different underwrite than one spread across four payers.
    """
    by_payer: Dict[str, Dict[str, Any]] = {}
    for h in report.hits:
        ev = h.event
        bucket = by_payer.setdefault(
            ev.affected_payer,
            {"total": 0.0, "n": 0, "worst": 0.0, "worst_name": ""})
        bucket["total"] += ev.rate_change_bps
        bucket["n"] += 1
        # "Worst" = most negative single event for that payer.
        if ev.rate_change_bps < bucket["worst"]:
            bucket["worst"] = ev.rate_change_bps
            bucket["worst_name"] = ev.name

    payers = [
        PayerExposure(
            payer=p, total_bps=round(b["total"], 1), event_count=b["n"],
            worst_event=b["worst_name"], worst_bps=round(b["worst"], 1),
        )
        for p, b in by_payer.items()
    ]
    # Most-cut payer first (most negative total bps).
    payers.sort(key=lambda p: p.total_bps)

    # Cumulative erosion curve keyed by relative year.
    cum_map: Dict[int, float] = {}
    for h in report.hits:
        cum_map[h.relative_year] = (
            cum_map.get(h.relative_year, 0.0) + h.event.rate_change_bps)
    cumulative: List[tuple] = []
    run = 0.0
    for ry in sorted(cum_map):
        run += cum_map[ry]
        cumulative.append((ry, round(run, 1)))

    total_neg = sum(p.total_bps for p in payers if p.total_bps < 0)
    dominant = None
    dom_share = 0.0
    if payers and payers[0].total_bps < 0 and total_neg < 0:
        dominant = payers[0].payer
        dom_share = payers[0].total_bps / total_neg

    if not payers:
        note = "No cliffs in the hold — no payer concentration to read."
    elif dominant and dom_share >= 0.70:
        note = (
            f"{dom_share*100:.0f}% of the in-hold rate cut is concentrated "
            f"in {dominant} ({payers[0].total_bps:+.0f} bps). This is a "
            f"single-channel reimbursement story — underwrite the "
            f"{dominant} exposure specifically."
        )
    elif dominant:
        note = (
            f"Rate cuts spread across {len(payers)} payer channels; "
            f"{dominant} carries the most ({payers[0].total_bps:+.0f} bps, "
            f"{dom_share*100:.0f}% of the total). Diversified headwind — "
            f"model each channel."
        )
    else:
        note = (
            f"{len(payers)} payer channel(s) affected; net rate change "
            f"is non-negative — no concentrated cut to underwrite."
        )

    return CliffExposure(
        by_payer=payers,
        cumulative_by_relative_year=cumulative,
        dominant_payer=dominant,
        dominant_share=dom_share,
        note=note,
    )


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
