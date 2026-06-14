"""CY2026 Medicare fee-schedule backbone + procedure-level site-of-service reference.

The single source of truth for the *dollar* constants that drive every
PE healthcare-subsector revenue model: the finalized CY2026 conversion
factors and prospective-payment base rates, plus a procedure-level
site-of-service reference (physician / ASC / HOPD Medicare allowed
amounts) for the highest-deal-flow subsectors.

Why this module exists
----------------------
``rate_updates.yaml`` carries the headline net *update percentages* per
care setting. That answers "which way is the rate going" but not "what
is the actual dollar at stake per procedure." Site-of-service
differentials — not professional fees — are the dominant value driver
in ASC-migration theses (GI office endoscopy, ortho total-joint
migration, cardiology OBL/cardiac-ASC, urology office UroLift), so the
deal team needs the actual facility-fee gaps, hard-coded and citable.

Sourcing & precision
--------------------
Constants are finalized CY2026 figures (CMS-1832-F PFS, 10/31/2025;
CMS-1834-FC OPPS/ASC, 11/21/2025; CMS-1830-F ESRD; CMS-1828-F Home
Health; CMS-1835-F Hospice; CMS-1827-F SNF). The procedure-level
allowed amounts are diligence-grade reference figures — national,
un-GPCI-adjusted, rounded to the dollar — suitable for sizing, NOT for
claim-level repricing. For a specific filing, confirm against the MPFS
Look-Up Tool, OPPS/ASC Addendum B, and the quarterly ASP Pricing File.
Every figure carries the same caveat the rate_updates.yaml header does.

Public API::

    from rcm_mc.data_public.fee_schedule_2026 import (
        FEE_SCHEDULE_BACKBONE_2026,    # dict of named backbone constants
        BackboneConstant,
        PROCEDURE_RATES_2026,          # dict: HCPCS -> ProcedureRate
        ProcedureRate,
        COMMERCIAL_TO_MEDICARE,        # payer-grossing multipliers
        pfs_payment,                   # RVU triplet -> $ allowed
        site_of_service_arbitrage,     # volume + setting shift -> $ delta
        SiteOfServiceArbitrage,
        gross_up_all_payer,            # FFS -> all-payer revenue
    )
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

# ---------------------------------------------------------------------------
# Section 1.0 — the fee-schedule backbone (hard-coded CY2026 constants)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BackboneConstant:
    """One finalized CY2026 payment constant.

    ``value`` is the dollar amount (or, for SNF where CMS publishes an
    aggregate update rather than a single base rate, ``None`` with the
    update carried in ``update_pct``). ``prior_value`` is the CY2025 /
    FY2025 figure so a model can show the year-over-year step. ``unit``
    names what the dollar buys (per-RVU CF, per-treatment, per-30-day
    period, etc.). ``rule`` is the finalizing CMS rule id.
    """

    key: str
    label: str
    value: Optional[float]
    prior_value: Optional[float]
    update_pct: float           # net YoY update, percent (3.26 = +3.26%)
    unit: str
    rule: str
    note: str = ""


# The keys are stable (other modules + tests key off them); do not rename
# without a migration. Figures are finalized CY2026 / FY2026.
FEE_SCHEDULE_BACKBONE_2026: Dict[str, BackboneConstant] = {
    "pfs_cf_nonqp": BackboneConstant(
        key="pfs_cf_nonqp",
        label="PFS conversion factor — non-QP",
        value=33.4009,
        prior_value=32.3465,
        update_pct=3.26,
        unit="$ per total RVU",
        rule="CMS-1832-F",
        note=(
            "Includes the statutory +2.5% (OBBBA), MACRA updates, "
            "+0.49% budget-neutrality, and a finalized -2.5% efficiency "
            "adjustment to work RVUs / intraservice time on most "
            "non-time-based services."
        ),
    ),
    "pfs_cf_qp": BackboneConstant(
        key="pfs_cf_qp",
        label="PFS conversion factor — qualifying APM participant",
        value=33.5675,
        prior_value=32.3465,
        update_pct=3.77,
        unit="$ per total RVU",
        rule="CMS-1832-F",
        note="Higher of the two CFs; applies to qualifying APM participants.",
    ),
    "opps_cf": BackboneConstant(
        key="opps_cf",
        label="OPPS conversion factor (non-340B)",
        value=91.415,
        prior_value=89.169,
        update_pct=2.6,
        unit="$ per relative weight",
        rule="CMS-1834-FC",
        note="340B-reduced CF is $90.970. +2.6% = 3.3% market basket - 0.7% productivity.",
    ),
    "asc_cf": BackboneConstant(
        key="asc_cf",
        label="ASC conversion factor (quality-reporting)",
        value=56.322,
        prior_value=54.895,
        update_pct=2.6,
        unit="$ per relative weight",
        rule="CMS-1834-FC",
        note=(
            "Non-reporting CF is $55.224. ASC CF is ~62% of the OPPS CF — "
            "the structural source of the HOPD-to-ASC facility-fee gap."
        ),
    ),
    "esrd_base": BackboneConstant(
        key="esrd_base",
        label="ESRD PPS base rate",
        value=281.71,
        prior_value=273.82,
        update_pct=2.2,
        unit="$ per treatment",
        rule="CMS-1830-F",
        note="AKI rate equals the base rate. ~156 treatments/patient/yr.",
    ),
    "hh_30day_base": BackboneConstant(
        key="hh_30day_base",
        label="Home Health 30-day standardized base",
        value=2038.22,
        prior_value=2057.35,
        update_pct=-0.1,
        unit="$ per 30-day period",
        rule="CMS-1828-F",
        note=(
            "Net cut despite +2.4% market basket: permanent -1.023% PDGM "
            "behavioral adjustment + -3.0% temporary adjustment dominate."
        ),
    ),
    "hospice_cap": BackboneConstant(
        key="hospice_cap",
        label="Hospice aggregate cap",
        value=35361.44,
        prior_value=34465.34,
        update_pct=2.6,
        unit="$ per beneficiary (annual aggregate)",
        rule="CMS-1835-F",
        note="Cap-liability management matters more than the headline rate for high-ALOS books.",
    ),
    "snf_update": BackboneConstant(
        key="snf_update",
        label="SNF PPS net update",
        value=None,
        prior_value=None,
        update_pct=3.2,
        unit="aggregate update (no single base rate)",
        rule="CMS-1827-F",
        note="+3.2% = 3.3% market basket + 0.6% forecast-error - 0.7% productivity; +$1.16B.",
    ),
}


# ---------------------------------------------------------------------------
# Commercial / all-payer grossing-up multipliers (Section 3 of the brief)
# Commercial-to-Medicare price ratios as a fraction (1.45 = 145% of Medicare).
# Milliman 2025 (professional / inpatient / outpatient) + RAND 5.1 (ASC).
# ---------------------------------------------------------------------------

COMMERCIAL_TO_MEDICARE: Dict[str, float] = {
    "professional": 1.44,      # Milliman 2025: 139-148% of Medicare FFS
    "asc_facility": 1.71,      # RAND 5.1: ASC at 171% of Medicare
    "hopd_outpatient": 2.60,   # Milliman 2025: 257-263% of Medicare
    "inpatient": 2.07,         # Milliman 2025: 205-209% of Medicare
    "drug_asp": 2.05,          # RAND 5.1: physician-administered drugs ~205% of ASP
}


# ---------------------------------------------------------------------------
# Section 1.1-1.5 — procedure-level site-of-service reference
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProcedureRate:
    """A procedure's CY2026 Medicare allowed amounts by site of service.

    ``physician_fee`` is the professional fee (setting-invariant in most
    cases — the surgeon earns it regardless of where the case is done).
    ``asc_facility`` / ``hopd_facility`` are the *facility* fees the ASC
    or hospital outpatient department bills on top — this gap, not the
    professional fee, is the value driver. ``office_nonfacility`` is the
    all-in office (non-facility) PFS amount where an office setting is
    viable (it bundles the practice-expense the facility would otherwise
    bill separately). ``None`` means "not a typical setting for this
    code" or "not separately published in the brief." All amounts are
    national, un-GPCI-adjusted, diligence-grade dollars.
    """

    code: str
    descr: str
    subsector: str
    work_rvu: Optional[float]
    physician_fee: Optional[float]
    asc_facility: Optional[float]
    hopd_facility: Optional[float]
    office_nonfacility: Optional[float] = None
    note: str = ""


# Hand-curated from the CY2026 reimbursement brief. Where the brief gives
# a range, the midpoint is used and the range is noted.
PROCEDURE_RATES_2026: Dict[str, ProcedureRate] = {
    # --- Gastroenterology (1.1) ---
    "45378": ProcedureRate(
        code="45378", descr="Diagnostic colonoscopy", subsector="gastroenterology",
        work_rvu=3.36, physician_fee=216.0, asc_facility=375.0, hopd_facility=710.0,
        note="Facility fee HOPD ~1.8-1.9x ASC. ASC range $369.84-380.16.",
    ),
    "45380": ProcedureRate(
        code="45380", descr="Colonoscopy with biopsy", subsector="gastroenterology",
        work_rvu=3.67, physician_fee=None, asc_facility=None, hopd_facility=None,
        note="Commercial facility fee ~$1,034 ASC vs $1,760 hospital (Turquoise).",
    ),
    "45385": ProcedureRate(
        code="45385", descr="Colonoscopy with snare lesion removal", subsector="gastroenterology",
        work_rvu=4.57, physician_fee=None, asc_facility=None, hopd_facility=None,
        note="Commercial facility fee ~$1,030 ASC vs $1,761 hospital (Turquoise).",
    ),
    # --- Ophthalmology (1.2) ---
    "66984": ProcedureRate(
        code="66984", descr="Cataract surgery with IOL (phaco)", subsector="ophthalmology",
        work_rvu=None, physician_fee=528.0, asc_facility=1255.73, hopd_facility=None,
        note=(
            "~11% facility-professional cut in 2026 (largest single-year cut "
            "in three decades). ASC rate corrected up +3.4% after CMS IOL-cost "
            "error. IOL packaged into the facility payment."
        ),
    ),
    "66982": ProcedureRate(
        code="66982", descr="Complex cataract surgery with IOL", subsector="ophthalmology",
        work_rvu=None, physician_fee=None, asc_facility=1255.73, hopd_facility=None,
        note="Professional ~30% above 66984.",
    ),
    # --- Orthopedics / MSK (1.3) ---
    "27447": ProcedureRate(
        code="27447", descr="Total knee arthroplasty (TKA)", subsector="orthopedics",
        work_rvu=20.99, physician_fee=None, asc_facility=8610.0, hopd_facility=None,
        note=(
            "Total RVU 47.82. Inpatient MS-DRG 469/470; outpatient C-APC 5115. "
            "ASC fee ~$8,610 (2020 basis). Anesthesia 01402 packaged."
        ),
    ),
    "27130": ProcedureRate(
        code="27130", descr="Total hip arthroplasty (THA)", subsector="orthopedics",
        work_rvu=22.44, physician_fee=None, asc_facility=None, hopd_facility=None,
        note="MS-DRG 469/470; C-APC 5115 outpatient.",
    ),
    # --- Cardiology (1.4) ---
    "93458": ProcedureRate(
        code="93458", descr="Diagnostic left heart cath w/ coronary angiography",
        subsector="cardiology",
        work_rvu=None, physician_fee=277.0, asc_facility=1546.0, hopd_facility=3312.0,
        note="Physician fee setting-invariant. HOPD APC 5191 Level 1 Endovascular.",
    ),
    "92928": ProcedureRate(
        code="92928", descr="PCI with stent, single vessel", subsector="cardiology",
        work_rvu=None, physician_fee=557.0, asc_facility=7309.0, hopd_facility=11794.0,
        note=(
            "All PCI added to ASC-CPL for 2026 — OBL/cardiac-ASC tailwind. "
            "HOPD APC 5193 Level 3. New complex-PCI code 92930 eff. 1/1/2026."
        ),
    ),
    "93306": ProcedureRate(
        code="93306", descr="Complete transthoracic echocardiogram (TTE)",
        subsector="cardiology",
        work_rvu=None, physician_fee=235.0, asc_facility=None, hopd_facility=None,
        note="Global Medicare ~$235 (range $210-240); professional ~40% / technical ~60%.",
    ),
    # --- Urology (1.5) ---
    "52000": ProcedureRate(
        code="52000", descr="Diagnostic cystoscopy", subsector="urology",
        work_rvu=None, physician_fee=71.0, asc_facility=311.0, hopd_facility=712.0,
        office_nonfacility=216.0,
        note="'Separate procedure'; bundled into 52204/52332/52287. HOPD APC 5372.",
    ),
    "52441": ProcedureRate(
        code="52441", descr="UroLift transprostatic implant (first)", subsector="urology",
        work_rvu=None, physician_fee=None, asc_facility=None, hopd_facility=None,
        office_nonfacility=4110.0,
        note=(
            "Office non-facility fee INCLUDES implant cost (~4-implant case ~$4,110 "
            "gross, ~$3,400 device) — office captures the bundled device margin. "
            "In ASC/HOPD the physician bills professional only; facility bills the "
            "device via C9739 (1-3 implants) / C9740 (4+). +52442 each additional."
        ),
    ),
}


# ---------------------------------------------------------------------------
# Payment math
# ---------------------------------------------------------------------------


def pfs_payment(
    work_rvu: float,
    pe_rvu: float,
    mp_rvu: float,
    *,
    gpci_work: float = 1.0,
    gpci_pe: float = 1.0,
    gpci_mp: float = 1.0,
    qp: bool = False,
) -> float:
    """Compute a PFS allowed amount from an RVU triplet.

    payment = (work_RVU*wGPCI + PE_RVU*peGPCI + MP_RVU*mpGPCI) * CF

    ``qp=True`` uses the qualifying-APM-participant conversion factor;
    otherwise the non-QP CF. GPCIs default to 1.0 (national / un-localized).
    """
    cf = FEE_SCHEDULE_BACKBONE_2026["pfs_cf_qp" if qp else "pfs_cf_nonqp"].value
    assert cf is not None  # both CFs are populated; guard for type-checkers
    adjusted = (
        work_rvu * gpci_work + pe_rvu * gpci_pe + mp_rvu * gpci_mp
    )
    return round(adjusted * cf, 2)


# ---------------------------------------------------------------------------
# Site-of-service arbitrage — the core diligence calculator
# ---------------------------------------------------------------------------

_SETTING_FIELD = {
    "physician": "physician_fee",
    "asc": "asc_facility",
    "hopd": "hopd_facility",
    "office": "office_nonfacility",
}

_VALID_SETTINGS = tuple(_SETTING_FIELD)


@dataclass
class SiteOfServiceArbitrage:
    """Result of migrating a procedure's volume between settings."""

    code: str
    descr: str
    subsector: str
    annual_volume: int
    from_setting: str
    to_setting: str
    payer: str
    from_rate: float
    to_rate: float
    per_case_delta: float       # to_rate - from_rate (positive = capture/uplift)
    annual_delta: float         # per_case_delta * annual_volume
    note: str = ""


def _rate_for(proc: ProcedureRate, setting: str, payer: str) -> Optional[float]:
    """Return the Medicare (or commercial-grossed) rate for a setting."""
    base = getattr(proc, _SETTING_FIELD[setting])
    if base is None:
        return None
    if payer == "medicare":
        return float(base)
    if payer == "commercial":
        mult = {
            "physician": COMMERCIAL_TO_MEDICARE["professional"],
            "office": COMMERCIAL_TO_MEDICARE["professional"],
            "asc": COMMERCIAL_TO_MEDICARE["asc_facility"],
            "hopd": COMMERCIAL_TO_MEDICARE["hopd_outpatient"],
        }[setting]
        return round(float(base) * mult, 2)
    raise ValueError(f"payer must be 'medicare' or 'commercial', got {payer!r}")


def site_of_service_arbitrage(
    code: str,
    annual_volume: int,
    from_setting: str,
    to_setting: str,
    *,
    payer: str = "medicare",
) -> SiteOfServiceArbitrage:
    """Size the dollar swing from moving a procedure between settings.

    The canonical use is a migration thesis: HOPD -> ASC (system saves /
    ASC captures the facility-fee gap), or HOPD/ASC -> office (office
    captures the bundled non-facility amount). ``per_case_delta`` is
    ``to_rate - from_rate`` so a positive number is the capture/uplift to
    the *destination* setting and the saving to the payer.

    Raises ``ValueError`` for an unknown code, an unknown setting, or a
    setting that has no published rate for this code (so the caller never
    silently sizes off a missing field).
    """
    proc = PROCEDURE_RATES_2026.get(str(code).strip().upper())
    if proc is None:
        raise ValueError(f"no CY2026 reference rate for code {code!r}")
    if from_setting not in _VALID_SETTINGS:
        raise ValueError(f"from_setting must be one of {_VALID_SETTINGS}, got {from_setting!r}")
    if to_setting not in _VALID_SETTINGS:
        raise ValueError(f"to_setting must be one of {_VALID_SETTINGS}, got {to_setting!r}")
    if annual_volume < 0:
        raise ValueError("annual_volume must be non-negative")

    from_rate = _rate_for(proc, from_setting, payer)
    to_rate = _rate_for(proc, to_setting, payer)
    if from_rate is None:
        raise ValueError(f"code {code} has no {from_setting} rate published")
    if to_rate is None:
        raise ValueError(f"code {code} has no {to_setting} rate published")

    per_case = round(to_rate - from_rate, 2)
    return SiteOfServiceArbitrage(
        code=proc.code,
        descr=proc.descr,
        subsector=proc.subsector,
        annual_volume=annual_volume,
        from_setting=from_setting,
        to_setting=to_setting,
        payer=payer,
        from_rate=round(from_rate, 2),
        to_rate=round(to_rate, 2),
        per_case_delta=per_case,
        annual_delta=round(per_case * annual_volume, 2),
        note=proc.note,
    )


# ---------------------------------------------------------------------------
# Grossing-up engine (Section 3): FFS Medicare -> all-payer
# ---------------------------------------------------------------------------


def gross_up_all_payer(
    ffs_medicare_revenue: float,
    ma_penetration: float,
    *,
    commercial_share: float = 0.0,
    commercial_multiplier: float = 1.0,
) -> float:
    """Gross FFS-Medicare revenue up toward an all-payer figure.

    The Physician & Other Practitioners file is 100% final-action FFS
    Part B — it *excludes* Medicare Advantage and all commercial volume,
    so it understates true volume, badly in MA-heavy markets.

    Two-step gross-up:
      1. all-Medicare = FFS / (1 - MA_penetration)
      2. blend in commercial at its price multiple:
         all-payer = all-Medicare * (1 + commercial_share*(mult - 1))

    ``ma_penetration`` and ``commercial_share`` are fractions in [0, 1).
    With both at their defaults the function returns ``ffs_medicare_revenue``
    unchanged. Raises ``ValueError`` on an MA penetration of 1.0 (would
    divide by zero) or out-of-range inputs.
    """
    if not 0.0 <= ma_penetration < 1.0:
        raise ValueError("ma_penetration must be in [0, 1)")
    if not 0.0 <= commercial_share <= 1.0:
        raise ValueError("commercial_share must be in [0, 1]")
    all_medicare = ffs_medicare_revenue / (1.0 - ma_penetration)
    blended = all_medicare * (1.0 + commercial_share * (commercial_multiplier - 1.0))
    return round(blended, 2)


__all__ = [
    "BackboneConstant",
    "FEE_SCHEDULE_BACKBONE_2026",
    "COMMERCIAL_TO_MEDICARE",
    "ProcedureRate",
    "PROCEDURE_RATES_2026",
    "pfs_payment",
    "SiteOfServiceArbitrage",
    "site_of_service_arbitrage",
    "gross_up_all_payer",
]
