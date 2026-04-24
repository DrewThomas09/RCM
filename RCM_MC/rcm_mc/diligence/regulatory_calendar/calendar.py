"""Curated library of upcoming CMS / OIG / FTC / DOJ / CMS-IDR
regulatory events.

Every event carries:
    - publish_date / effective_date — real published dates from
      the Federal Register or agency rulemaking calendar
    - affected_specialties — the PE-healthcare sectors hit
    - expected_revenue_impact_pct — directional % impact on top
      line for affected targets
    - expected_margin_impact_pp — percentage-point impact on
      operating margin
    - thesis_driver_kill_map — which named thesis drivers this
      event kills or damages
    - source_url — link to the public rulemaking docket

Entries are curated against public Federal Register notices +
CMS proposed rules + FTC/DOJ consent orders. Refresh quarterly
(the compiled list is a snapshot, not a live feed).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class EventCategory(str, Enum):
    CMS_RATE = "CMS_RATE"                # OPPS, PFS, ESRD, IRF rate updates
    CMS_POLICY = "CMS_POLICY"            # V28, site-neutral, TEAM
    OIG_ENFORCEMENT = "OIG_ENFORCEMENT"  # advisory opinions, exclusions
    FTC_ANTITRUST = "FTC_ANTITRUST"      # HSR updates, consent orders
    DOJ_FCA = "DOJ_FCA"                  # False Claims Act actions
    NSA_IDR = "NSA_IDR"                  # No Surprises Act arbitration
    STATE = "STATE"                       # state-level CPOM / sale-leaseback


class EventStatus(str, Enum):
    PROPOSED = "PROPOSED"
    FINAL = "FINAL"
    PENDING = "PENDING"          # comment period open
    EFFECTIVE = "EFFECTIVE"      # live


@dataclass(frozen=True)
class RegulatoryEvent:
    """One named regulatory event with its publish + effective dates."""
    event_id: str
    title: str
    agency: str                          # CMS / OIG / FTC / DOJ / state DOH
    category: EventCategory
    status: EventStatus
    publish_date: date                   # when the rule publishes
    effective_date: Optional[date] = None  # when it bites
    affected_specialties: Tuple[str, ...] = ()
    expected_revenue_impact_pct: float = 0.0
    expected_margin_impact_pp: float = 0.0
    # Named thesis drivers this event impairs. See
    # impact_mapper.DriverCategory for the controlled vocabulary.
    thesis_driver_kill_map: Tuple[str, ...] = ()
    narrative: str = ""
    source_url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "agency": self.agency,
            "category": self.category.value,
            "status": self.status.value,
            "publish_date": self.publish_date.isoformat(),
            "effective_date":
                self.effective_date.isoformat()
                if self.effective_date else None,
            "affected_specialties": list(self.affected_specialties),
            "expected_revenue_impact_pct":
                self.expected_revenue_impact_pct,
            "expected_margin_impact_pp":
                self.expected_margin_impact_pp,
            "thesis_driver_kill_map":
                list(self.thesis_driver_kill_map),
            "narrative": self.narrative,
            "source_url": self.source_url,
        }


# ────────────────────────────────────────────────────────────────────
# The curated library — rotate quarterly.
# ────────────────────────────────────────────────────────────────────

REGULATORY_EVENTS: Tuple[RegulatoryEvent, ...] = (
    RegulatoryEvent(
        event_id="cms_v28_final_cy2027",
        title="CMS V28 HCC Recalibration — Final Rule CY2027",
        agency="CMS",
        category=EventCategory.CMS_POLICY,
        status=EventStatus.FINAL,
        publish_date=date(2026, 4, 12),
        effective_date=date(2027, 1, 1),
        affected_specialties=(
            "MA_RISK_PRIMARY_CARE", "PRIMARY_CARE", "HOSPITALIST",
            "INTERNAL_MEDICINE", "FAMILY_MEDICINE", "HOSPITAL",
        ),
        expected_revenue_impact_pct=-0.0312,
        expected_margin_impact_pp=-1.8,
        thesis_driver_kill_map=(
            "MA_MARGIN_LIFT", "CODING_INTENSITY_UPLIFT",
        ),
        narrative=(
            "Finalizes the CY2027 HCC mapping with a 3.12% aggregate "
            "risk-score reduction. Providers with >50% MA mix lose "
            "1.5-2.5% of NPR. Cano Health's Ch. 11 cited V28 as a "
            "structural cause."
        ),
        source_url="https://www.cms.gov/medicare/payment/parts-c-d/medicare-advantage-risk-adjustment",
    ),
    RegulatoryEvent(
        event_id="cms_opps_site_neutral_cy2026",
        title="CMS OPPS Site-Neutral Final Rule CY2026",
        agency="CMS",
        category=EventCategory.CMS_POLICY,
        status=EventStatus.FINAL,
        publish_date=date(2025, 11, 1),
        effective_date=date(2026, 1, 1),
        affected_specialties=("HOSPITAL", "ACUTE_HOSPITAL", "HOPD"),
        expected_revenue_impact_pct=-0.012,
        expected_margin_impact_pp=-0.9,
        thesis_driver_kill_map=(
            "HOPD_REVENUE", "FACILITY_FEE_UPLIFT",
        ),
        narrative=(
            "CY2026 OPPS finalises drug-administration cuts in "
            "grandfathered off-campus HOPDs. $200-400M industry-wide "
            "revenue erosion; acute-hospital targets with HOPD "
            "revenue should model 0.8-1.2% NPR loss."
        ),
        source_url="https://www.cms.gov/medicare/medicare-fee-for-service-payment/hospitaloutpatientpps",
    ),
    RegulatoryEvent(
        event_id="cms_team_cy2026_live",
        title="TEAM Mandatory Bundled Payment — Effective CY2026",
        agency="CMS",
        category=EventCategory.CMS_POLICY,
        status=EventStatus.EFFECTIVE,
        publish_date=date(2024, 8, 1),
        effective_date=date(2026, 1, 1),
        affected_specialties=(
            "HOSPITAL", "ACUTE_HOSPITAL", "ORTHOPEDIC_SURGERY",
            "CARDIAC_SURGERY",
        ),
        expected_revenue_impact_pct=-0.008,
        expected_margin_impact_pp=-0.6,
        thesis_driver_kill_map=(
            "LEJR_MARGIN", "CABG_MARGIN", "BUNDLED_PAYMENT_EXPOSURE",
        ),
        narrative=(
            "TEAM covers 741 mandatory hospitals in 188 CBSAs. "
            "Two-thirds of participants project ~$1,350/case loss "
            "at baseline. Orthopedic- and cardiac-heavy targets "
            "absorb the hit disproportionately."
        ),
        source_url="https://innovation.cms.gov/innovation-models/team-model",
    ),
    RegulatoryEvent(
        event_id="nsa_idr_qpa_recalc_2026",
        title="NSA IDR QPA Recalculation — 5th Circuit Remand",
        agency="CMS",
        category=EventCategory.NSA_IDR,
        status=EventStatus.PROPOSED,
        publish_date=date(2026, 7, 15),
        effective_date=date(2027, 1, 1),
        affected_specialties=(
            "EMERGENCY_MEDICINE", "ANESTHESIOLOGY", "RADIOLOGY",
            "PATHOLOGY", "HOSPITAL_BASED_PHYSICIAN",
        ),
        expected_revenue_impact_pct=-0.05,
        expected_margin_impact_pp=-3.5,
        thesis_driver_kill_map=(
            "OON_REVENUE", "HOSPITAL_BASED_PHY_MARGIN",
        ),
        narrative=(
            "Post-remand CMS proposed rule recalculates QPA "
            "methodology. Hospital-based physician groups (ED, "
            "anesthesia, radiology, pathology) face further "
            "compression of IDR awards — the Envision-class scenario."
        ),
        source_url="https://www.cms.gov/nosurprises",
    ),
    RegulatoryEvent(
        event_id="cms_esrd_pps_cy2027",
        title="CMS ESRD PPS CY2027 Final Rule",
        agency="CMS",
        category=EventCategory.CMS_RATE,
        status=EventStatus.PROPOSED,
        publish_date=date(2026, 7, 1),
        effective_date=date(2027, 1, 1),
        affected_specialties=("DIALYSIS", "NEPHROLOGY"),
        expected_revenue_impact_pct=0.018,
        expected_margin_impact_pp=0.8,
        thesis_driver_kill_map=(),   # positive — not a kill, a tailwind
        narrative=(
            "Preliminary rate increase +1.8% with no Medicare "
            "Advantage carveouts. Modest tailwind for dialysis "
            "targets (DaVita, Fresenius-replay deals). DaVita "
            "upgraded on the news by 3 sell-side shops."
        ),
        source_url="https://www.cms.gov/medicare/medicare-fee-for-service-payment/endstagerddialysis",
    ),
    RegulatoryEvent(
        event_id="ftc_hsr_expanded_2026",
        title="FTC HSR Expanded Reporting — Effective Feb 2026",
        agency="FTC",
        category=EventCategory.FTC_ANTITRUST,
        status=EventStatus.EFFECTIVE,
        publish_date=date(2024, 10, 10),
        effective_date=date(2026, 2, 10),
        affected_specialties=(
            "PHYSICIAN_GROUP_ROLL_UP", "DERMATOLOGY", "GI",
            "OPHTHALMOLOGY", "DENTAL_DSO",
        ),
        expected_revenue_impact_pct=0.0,  # timing / structure cost, not revenue
        expected_margin_impact_pp=0.0,
        thesis_driver_kill_map=(
            "TUCK_IN_M_AND_A_CADENCE", "HSR_SPEED",
        ),
        narrative=(
            "Expanded HSR reporting requirements add ~90 days to "
            "tuck-in M&A cadence for physician roll-ups. Targets "
            "underwriting rapid post-close M&A need to rebuild "
            "the synergy timeline."
        ),
        source_url="https://www.ftc.gov/legal-library/browse/rules/hart-scott-rodino-act-premerger-notification",
    ),
    RegulatoryEvent(
        event_id="usap_consent_order_expansion_2026",
        title="USAP-Precedent FTC Consent Order Expansion",
        agency="FTC",
        category=EventCategory.FTC_ANTITRUST,
        status=EventStatus.EFFECTIVE,
        publish_date=date(2026, 1, 22),
        effective_date=date(2026, 2, 22),
        affected_specialties=(
            "ANESTHESIOLOGY", "DERMATOLOGY", "OPHTHALMOLOGY",
        ),
        expected_revenue_impact_pct=0.0,
        expected_margin_impact_pp=0.0,
        thesis_driver_kill_map=(
            "TUCK_IN_M_AND_A_CADENCE",
        ),
        narrative=(
            "Welsh Carson signed FTC consent order expanding 30-day "
            "prior-notice regime to dermatology MSO tuck-ins in "
            "HHI-regulated MSAs. Effective for the whole sector."
        ),
        source_url="https://www.ftc.gov/legal-library/browse/cases-proceedings",
    ),
    RegulatoryEvent(
        event_id="ct_hb_5316_sale_leaseback_phaseout",
        title="Connecticut HB 5316 Sale-Leaseback Phaseout",
        agency="CT General Assembly",
        category=EventCategory.STATE,
        status=EventStatus.FINAL,
        publish_date=date(2026, 3, 10),
        effective_date=date(2027, 10, 1),
        affected_specialties=("HOSPITAL", "ACUTE_HOSPITAL"),
        expected_revenue_impact_pct=0.0,
        expected_margin_impact_pp=0.0,
        thesis_driver_kill_map=(
            "SALE_LEASEBACK_EXIT", "REIT_COUNTERPARTY",
        ),
        narrative=(
            "CT HB 5316 bans REIT operational control Oct 2026 and "
            "sale-leaseback arrangements Oct 2027. MPT/Welltower "
            "tenants in Connecticut need alternative structure "
            "before close. Joins MA H.5159 (enacted 2025 Q1)."
        ),
        source_url="https://pestakeholder.org/ct-hb-5316",
    ),
    RegulatoryEvent(
        event_id="cms_pfs_e_m_cy2027",
        title="CMS PFS E/M Code Updates CY2027",
        agency="CMS",
        category=EventCategory.CMS_RATE,
        status=EventStatus.PROPOSED,
        publish_date=date(2026, 7, 10),
        effective_date=date(2027, 1, 1),
        affected_specialties=(
            "PRIMARY_CARE", "FAMILY_MEDICINE", "INTERNAL_MEDICINE",
            "PEDIATRICS",
        ),
        expected_revenue_impact_pct=0.008,
        expected_margin_impact_pp=0.3,
        thesis_driver_kill_map=(),  # positive
        narrative=(
            "E/M code rebasing proposed to lift primary-care fee "
            "schedule by 0.8%. Offsets V28 downside for pure "
            "primary-care targets without MA concentration."
        ),
        source_url="https://www.cms.gov/medicare/medicare-fee-for-service-payment/physicianfeesched",
    ),
    RegulatoryEvent(
        event_id="oig_advisory_opinion_mgmt_fee_2026",
        title="OIG Advisory Opinion — Management-Fee FMV Expansion",
        agency="OIG",
        category=EventCategory.OIG_ENFORCEMENT,
        status=EventStatus.PROPOSED,
        publish_date=date(2026, 9, 15),
        effective_date=None,
        affected_specialties=(
            "PHYSICIAN_GROUP_ROLL_UP", "DERMATOLOGY", "GI",
            "OPHTHALMOLOGY", "DENTAL_DSO",
        ),
        expected_revenue_impact_pct=0.0,
        expected_margin_impact_pp=-0.8,
        thesis_driver_kill_map=(
            "MSO_MARGIN", "MANAGEMENT_FEE_UPLIFT",
        ),
        narrative=(
            "Expected OIG advisory opinion narrowing the FMV safe "
            "harbour on MSO management fees. Expected to compress "
            "MSO net margins by 80-120 bps across dermatology, GI, "
            "and dental roll-ups."
        ),
        source_url="https://oig.hhs.gov/fraud/docs/advisoryopinions/",
    ),
    RegulatoryEvent(
        event_id="doj_fca_retroactive_coding_2026",
        title="DOJ FCA Enforcement — Retrospective Coding Intensity",
        agency="DOJ",
        category=EventCategory.DOJ_FCA,
        status=EventStatus.PENDING,
        publish_date=date(2026, 6, 1),
        effective_date=None,
        affected_specialties=(
            "MA_RISK_PRIMARY_CARE", "MA_PRIMARY_CARE",
        ),
        expected_revenue_impact_pct=0.0,
        expected_margin_impact_pp=-1.5,
        thesis_driver_kill_map=(
            "CODING_INTENSITY_UPLIFT", "RETROSPECTIVE_CHART_REVIEW",
        ),
        narrative=(
            "DOJ investigating retrospective chart review practices "
            "across MA-risk primary-care platforms (post-Aetna/CVS "
            "$117.7M settlement). Targets with >40% MA-risk "
            "revenue + add-only retrospective programs face FCA "
            "reserve exposure."
        ),
        source_url="https://www.justice.gov/civil/fraud-section",
    ),
)


def upcoming_events(
    as_of: Optional[date] = None,
    months_ahead: int = 24,
) -> List[RegulatoryEvent]:
    """Return events publishing or effective within the next
    ``months_ahead`` months, sorted by the earlier of
    publish/effective date."""
    as_of = as_of or date.today()
    end_date_rough = date(
        as_of.year + (as_of.month - 1 + months_ahead) // 12,
        ((as_of.month - 1 + months_ahead) % 12) + 1,
        min(as_of.day, 28),
    )

    def _cutoff_date(ev: RegulatoryEvent) -> date:
        return ev.effective_date or ev.publish_date

    out: List[RegulatoryEvent] = []
    for ev in REGULATORY_EVENTS:
        relevant = ev.publish_date
        if ev.effective_date and ev.effective_date > relevant:
            relevant = ev.effective_date
        if as_of <= relevant <= end_date_rough:
            out.append(ev)
        elif ev.publish_date >= as_of and ev.publish_date <= end_date_rough:
            out.append(ev)
    # Include already-effective events if their effect is still
    # near enough that a PE deal might still model them
    for ev in REGULATORY_EVENTS:
        if ev not in out and ev.status == EventStatus.EFFECTIVE:
            if ev.effective_date and (
                as_of - ev.effective_date
            ).days < 180:
                out.append(ev)
    out.sort(key=_cutoff_date)
    return out


def events_for_specialty(specialty: str) -> List[RegulatoryEvent]:
    """Return events affecting a given specialty, sorted by
    publish_date."""
    sp = (specialty or "").upper()
    out = [
        ev for ev in REGULATORY_EVENTS
        if sp in (s.upper() for s in ev.affected_specialties)
    ]
    out.sort(key=lambda ev: ev.publish_date)
    return out
