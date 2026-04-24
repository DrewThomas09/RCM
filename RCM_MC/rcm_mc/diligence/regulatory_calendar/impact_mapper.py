"""Maps a ``RegulatoryEvent`` to a target's named thesis drivers.

A thesis driver is a partner-claimed source of value-creation
("MA margin lift", "sale-leaseback at exit", "tuck-in M&A
cadence").  Each regulatory event is curated with a
``thesis_driver_kill_map`` tuple that names which of these
categories the event damages.  This module provides:

    * ``DriverCategory`` — the controlled vocabulary (shared with
      ``calendar.py`` kill-map strings).
    * ``ThesisDriver`` — an instance of a driver for a specific
      target with its expected lift size.
    * ``ThesisImpact`` — the per-event per-driver verdict
      (KILLED / DAMAGED / UNAFFECTED) with residual lift.
    * ``DEFAULT_THESIS_DRIVERS`` — a generic set used when no
      target-specific drivers are supplied.
    * ``map_event_to_drivers(event, drivers, target_profile)`` —
      the core mapping function.

Why the mapping is non-trivial: a CMS V28 event that affects
MA-risk primary care *damages* a driver named "MA_MARGIN_LIFT"
for every MA-concentrated target, but the severity depends on
the target's MA mix.  A 90%-MA platform is killed; a 30%-MA
hybrid is damaged.  The mapper does that gradient math.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .calendar import RegulatoryEvent


class DriverCategory(str, Enum):
    """Controlled vocabulary for thesis-driver kill-map strings."""
    # Revenue / margin drivers
    MA_MARGIN_LIFT = "MA_MARGIN_LIFT"
    CODING_INTENSITY_UPLIFT = "CODING_INTENSITY_UPLIFT"
    HOPD_REVENUE = "HOPD_REVENUE"
    FACILITY_FEE_UPLIFT = "FACILITY_FEE_UPLIFT"
    LEJR_MARGIN = "LEJR_MARGIN"
    CABG_MARGIN = "CABG_MARGIN"
    BUNDLED_PAYMENT_EXPOSURE = "BUNDLED_PAYMENT_EXPOSURE"
    OON_REVENUE = "OON_REVENUE"
    HOSPITAL_BASED_PHY_MARGIN = "HOSPITAL_BASED_PHY_MARGIN"
    MSO_MARGIN = "MSO_MARGIN"
    MANAGEMENT_FEE_UPLIFT = "MANAGEMENT_FEE_UPLIFT"
    RETROSPECTIVE_CHART_REVIEW = "RETROSPECTIVE_CHART_REVIEW"
    # Structure / process drivers
    TUCK_IN_M_AND_A_CADENCE = "TUCK_IN_M_AND_A_CADENCE"
    HSR_SPEED = "HSR_SPEED"
    SALE_LEASEBACK_EXIT = "SALE_LEASEBACK_EXIT"
    REIT_COUNTERPARTY = "REIT_COUNTERPARTY"


@dataclass(frozen=True)
class ThesisDriver:
    """A partner-claimed value-creation driver for a target.

    ``expected_lift_pct`` is the partner's claimed contribution to
    EBITDA lift over the hold (e.g. 0.12 = 12 pp EBITDA margin
    lift from this driver alone).  The impact mapper uses the lift
    size to size the verdict.
    """
    driver_id: str                       # one of DriverCategory values
    label: str
    expected_lift_pct: float = 0.0       # 0.05 = 5 pp EBITDA margin lift
    gating_specialties: Tuple[str, ...] = ()
    # Target exposure conditions.  None = driver applies regardless.
    requires_ma_mix_above: Optional[float] = None
    requires_commercial_mix_above: Optional[float] = None
    requires_hopd_revenue: bool = False
    requires_reit_landlord: bool = False
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "driver_id": self.driver_id,
            "label": self.label,
            "expected_lift_pct": self.expected_lift_pct,
            "gating_specialties": list(self.gating_specialties),
            "requires_ma_mix_above": self.requires_ma_mix_above,
            "requires_commercial_mix_above":
                self.requires_commercial_mix_above,
            "requires_hopd_revenue": self.requires_hopd_revenue,
            "requires_reit_landlord": self.requires_reit_landlord,
            "notes": self.notes,
        }


class ImpactVerdict(str, Enum):
    KILLED = "KILLED"          # > 50% impairment of the driver's lift
    DAMAGED = "DAMAGED"        # 10-50% impairment
    UNAFFECTED = "UNAFFECTED"  # < 10% impairment


@dataclass(frozen=True)
class ThesisImpact:
    """Per-event per-driver verdict."""
    event_id: str
    driver_id: str
    verdict: ImpactVerdict
    impairment_pct: float                # fraction of lift lost (0..1)
    residual_lift_pct: float             # post-event lift remaining
    effective_date: Optional[str]
    narrative: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "driver_id": self.driver_id,
            "verdict": self.verdict.value,
            "impairment_pct": self.impairment_pct,
            "residual_lift_pct": self.residual_lift_pct,
            "effective_date": self.effective_date,
            "narrative": self.narrative,
        }


# ────────────────────────────────────────────────────────────────────
# Default drivers for the generic hospital / physician-group thesis
# ────────────────────────────────────────────────────────────────────

DEFAULT_THESIS_DRIVERS: Tuple[ThesisDriver, ...] = (
    ThesisDriver(
        driver_id=DriverCategory.MA_MARGIN_LIFT.value,
        label="Medicare Advantage margin lift",
        expected_lift_pct=0.055,
        requires_ma_mix_above=0.30,
        notes=(
            "Risk-adjusted capitation arbitrage on MA-concentrated "
            "patient panels."
        ),
    ),
    ThesisDriver(
        driver_id=DriverCategory.CODING_INTENSITY_UPLIFT.value,
        label="Coding intensity / chart review uplift",
        expected_lift_pct=0.030,
        requires_ma_mix_above=0.30,
    ),
    ThesisDriver(
        driver_id=DriverCategory.HOPD_REVENUE.value,
        label="HOPD facility-fee revenue",
        expected_lift_pct=0.025,
        gating_specialties=("HOSPITAL", "ACUTE_HOSPITAL", "HOPD"),
        requires_hopd_revenue=True,
    ),
    ThesisDriver(
        driver_id=DriverCategory.LEJR_MARGIN.value,
        label="LEJR bundled-case margin",
        expected_lift_pct=0.020,
        gating_specialties=(
            "ORTHOPEDIC_SURGERY", "HOSPITAL", "ACUTE_HOSPITAL",
        ),
    ),
    ThesisDriver(
        driver_id=DriverCategory.OON_REVENUE.value,
        label="Out-of-network / surprise-billing upside",
        expected_lift_pct=0.035,
        gating_specialties=(
            "EMERGENCY_MEDICINE", "ANESTHESIOLOGY", "RADIOLOGY",
            "PATHOLOGY", "HOSPITAL_BASED_PHYSICIAN",
        ),
        requires_commercial_mix_above=0.30,
    ),
    ThesisDriver(
        driver_id=DriverCategory.TUCK_IN_M_AND_A_CADENCE.value,
        label="Tuck-in M&A cadence (roll-up synergy)",
        expected_lift_pct=0.040,
        gating_specialties=(
            "PHYSICIAN_GROUP_ROLL_UP", "DERMATOLOGY", "GI",
            "OPHTHALMOLOGY", "DENTAL_DSO",
        ),
    ),
    ThesisDriver(
        driver_id=DriverCategory.MSO_MARGIN.value,
        label="MSO management-fee margin",
        expected_lift_pct=0.025,
        gating_specialties=(
            "PHYSICIAN_GROUP_ROLL_UP", "DERMATOLOGY", "GI",
            "OPHTHALMOLOGY", "DENTAL_DSO",
        ),
    ),
    ThesisDriver(
        driver_id=DriverCategory.SALE_LEASEBACK_EXIT.value,
        label="Sale-leaseback unlock at exit",
        expected_lift_pct=0.030,
        gating_specialties=("HOSPITAL", "ACUTE_HOSPITAL"),
        requires_reit_landlord=True,
    ),
)


# ────────────────────────────────────────────────────────────────────
# Mapping logic
# ────────────────────────────────────────────────────────────────────

def _target_exposure_multiplier(
    driver: ThesisDriver,
    target: Mapping[str, Any],
) -> float:
    """Return 0..1 scaling the impact based on target exposure.

    A CMS V28 event kills MA_MARGIN_LIFT harder for a 90%-MA panel
    than for a 35%-MA panel.  We scale impairment linearly above
    the requires_* threshold.
    """
    scale = 1.0
    ma_mix = float(target.get("ma_mix_pct", 0.0) or 0.0)
    comm_mix = float(
        target.get("commercial_payer_share", 0.0) or 0.0
    )

    if driver.requires_ma_mix_above is not None:
        if ma_mix < driver.requires_ma_mix_above:
            return 0.0
        # Scale the severity: at exactly the threshold = 0.5,
        # at 2× the threshold or full MA = 1.0
        over = ma_mix - driver.requires_ma_mix_above
        headroom = max(1.0 - driver.requires_ma_mix_above, 0.01)
        scale = min(1.0, 0.5 + 0.5 * (over / headroom))

    if driver.requires_commercial_mix_above is not None:
        if comm_mix < driver.requires_commercial_mix_above:
            return 0.0
        over = comm_mix - driver.requires_commercial_mix_above
        headroom = max(
            1.0 - driver.requires_commercial_mix_above, 0.01,
        )
        scale = min(
            scale,
            min(1.0, 0.5 + 0.5 * (over / headroom)),
        )

    if driver.requires_hopd_revenue:
        if not target.get("has_hopd_revenue", False):
            return 0.0

    if driver.requires_reit_landlord:
        if not target.get("has_reit_landlord", False):
            return 0.0

    return scale


def _specialty_match(
    driver: ThesisDriver,
    event: RegulatoryEvent,
    target: Mapping[str, Any],
) -> bool:
    """Driver fires only when the target's specialty intersects the
    driver's gating specialties AND the event's affected specialties.

    Two-sided gating keeps a dialysis-only target from having
    LEJR_MARGIN killed by a hospital-orthopedic event — even though
    the event lists ORTHOPEDIC_SURGERY, the target isn't a hospital.
    If no target specialty information is supplied we fall back to
    matching the event (universe view)."""
    if not driver.gating_specialties:
        return True
    target_sp = {
        s.upper() for s in (
            target.get("specialties") or
            ([target["specialty"]] if target.get("specialty") else [])
        )
    }
    event_sp = {s.upper() for s in event.affected_specialties}
    gating = {s.upper() for s in driver.gating_specialties}
    if not target_sp:
        return bool(gating & event_sp)
    return bool(gating & target_sp) and bool(gating & event_sp)


def _verdict_from_impairment(impairment: float) -> ImpactVerdict:
    if impairment >= 0.50:
        return ImpactVerdict.KILLED
    if impairment >= 0.10:
        return ImpactVerdict.DAMAGED
    return ImpactVerdict.UNAFFECTED


def map_event_to_drivers(
    event: RegulatoryEvent,
    drivers: Sequence[ThesisDriver] = DEFAULT_THESIS_DRIVERS,
    target_profile: Optional[Mapping[str, Any]] = None,
) -> List[ThesisImpact]:
    """Map one event to its per-driver impact on the target.

    ``target_profile`` keys (all optional):
        ``ma_mix_pct``, ``commercial_payer_share``,
        ``has_hopd_revenue``, ``has_reit_landlord``,
        ``specialty`` / ``specialties``.

    Drivers not named in ``event.thesis_driver_kill_map`` are
    returned with UNAFFECTED so the UI can show the full grid.
    """
    target = dict(target_profile or {})
    out: List[ThesisImpact] = []

    # Baseline impairment the curated event claims against each
    # named driver.  We use a flat 0.70 for "killed" targets on
    # the kill-list and scale down by exposure multiplier.  The
    # mapping makes a deliberate choice: the curated kill_map
    # names the drivers that get *damaged to some degree*, and
    # exposure scales it from DAMAGED → KILLED based on mix.
    base_impairment_on_list = 0.70

    kill_set = {
        d.upper() for d in event.thesis_driver_kill_map
    }

    for driver in drivers:
        driver_key = driver.driver_id.upper()
        named = driver_key in kill_set

        if not named:
            out.append(ThesisImpact(
                event_id=event.event_id,
                driver_id=driver.driver_id,
                verdict=ImpactVerdict.UNAFFECTED,
                impairment_pct=0.0,
                residual_lift_pct=driver.expected_lift_pct,
                effective_date=(
                    event.effective_date.isoformat()
                    if event.effective_date else None
                ),
                narrative="Not in this event's kill-map.",
            ))
            continue

        # Driver is named in the kill-map.  Scale by target
        # exposure + specialty match.
        if not _specialty_match(driver, event, target):
            out.append(ThesisImpact(
                event_id=event.event_id,
                driver_id=driver.driver_id,
                verdict=ImpactVerdict.UNAFFECTED,
                impairment_pct=0.0,
                residual_lift_pct=driver.expected_lift_pct,
                effective_date=(
                    event.effective_date.isoformat()
                    if event.effective_date else None
                ),
                narrative=(
                    "Driver named but target specialty does not "
                    "intersect event's affected specialties."
                ),
            ))
            continue

        exposure = _target_exposure_multiplier(driver, target)
        if exposure <= 0.0:
            out.append(ThesisImpact(
                event_id=event.event_id,
                driver_id=driver.driver_id,
                verdict=ImpactVerdict.UNAFFECTED,
                impairment_pct=0.0,
                residual_lift_pct=driver.expected_lift_pct,
                effective_date=(
                    event.effective_date.isoformat()
                    if event.effective_date else None
                ),
                narrative=(
                    "Target exposure below threshold — driver "
                    "not in scope for this event."
                ),
            ))
            continue

        impairment = base_impairment_on_list * exposure
        verdict = _verdict_from_impairment(impairment)
        residual = driver.expected_lift_pct * (1.0 - impairment)

        narrative = (
            f"{event.title} {('kills' if verdict == ImpactVerdict.KILLED else 'damages')} "
            f"{driver.label.lower()} by "
            f"{impairment*100:.0f}% of its claimed lift "
            f"(residual {residual*100:.1f} pp EBITDA margin)."
        )

        out.append(ThesisImpact(
            event_id=event.event_id,
            driver_id=driver.driver_id,
            verdict=verdict,
            impairment_pct=impairment,
            residual_lift_pct=residual,
            effective_date=(
                event.effective_date.isoformat()
                if event.effective_date else None
            ),
            narrative=narrative,
        ))

    return out
