"""IFT three-lever GROWTH TRACKER — the offline, honestly-labelled read on *why*
interfacility-transport revenue grows, split into the three levers a PE desk
actually underwrites.

Kevin's framing (and the framing the claims-understatement cleaner already files
findings under — :mod:`rcm_mc.npi_cleaner.understatement` LEVER_PRICE /
LEVER_VOLUME / LEVER_SCALE) is that a healthcare-services target grows on three
independent things, and these are the three things to TRACK:

  1. **PRICE / reimbursement inflation** — the realized rate per transport drifts
     up. The GOV anchor is the Medicare Ambulance Fee Schedule *Ambulance
     Inflation Factor* (AIF) annual update; on top sit the statutory ground
     add-ons, commercial out-of-network (OON) leverage (ground ambulance is
     EXCLUDED from the No Surprises Act, so it keeps its balance-billing power),
     and CPI-linked facility-contract escalators. Composite ~+2-4%/yr.

  2. **VOLUME / demographic + acuity growth** — more transports, and higher-acuity
     ones. The demographic tailwind is computed off the SOURCED clinical-demand
     model (``ift_clinical_demand`` — the 65-84/85+ aging cohorts that generate
     the fastest-growing acute-transfer demand), layered with ED-boarding /
     capacity load-balancing (anchored to the SOURCED HCRIS occupancy signal),
     post-acute utilization (anchored to the SOURCED destination-supply rolls),
     and hub-and-spoke regionalization. Composite ~+2-4%/yr.

  3. **CONSOLIDATION / big systems getting bigger** — health-system M&A pulls IFT
     to system hubs and to preferred/sole-source contracts, and an outsourced
     platform that holds the transfer-center first-call captures a rising share
     of that wallet. This is a **platform multiplier / share-shift, NOT organic
     market growth** — it does not grow the TAM, it grows the operator's share of
     it. Magnitudes ILLUSTRATIVE. Reuses ``health_system_sam`` for the
     multi-hospital-system share of IFT $, the addressable (outsourceable) share,
     and the SAM/SOM headroom multiple.

:func:`growth_bridge` combines the three: price × volume COMPOUND into an organic
market-growth read; consolidation is layered on top as an explicit share-shift to
give a share-gaining platform's growth.

────────────────────────────────────────────────────────────────────────────
HONESTY LABELS  (the load-bearing invariant — a prior review caught a
fabricated-GOV bug, so every figure carries exactly one basis)
────────────────────────────────────────────────────────────────────────────
  * ``GOV``          — a published government figure: the Medicare AIF annual
                       updates, the statutory ground add-on percentages
                       (42 U.S.C. 1395m(l)(12)-(13)), the No Surprises Act
                       ground-ambulance exclusion.
  * ``SOURCED``      — computed from OUR vendored data: the HCRIS inpatient-
                       occupancy signal and the CMS post-acute destination-supply
                       counts (both via ``ift_analytics`` / ``ift_clinical_demand``),
                       and the footprint bed-share (via ``ift_geo``).
  * ``ACADEMIC``     — a published peer-reviewed / epidemiologic figure (unused
                       here directly; the volume demographics flow through the
                       demand model).
  * ``ILLUSTRATIVE`` — modeled with a stated basis: every composite %/yr, the
                       pay-mix blend, the commercial-growth band, the consolidation
                       share-shift, and the SAM ratios inherited from
                       ``health_system_sam``.

Operator / health-system NAMES (MMT, AmeriPro, GMR/AMR, CommonSpirit, …) are
PUBLIC-WEB knowledge, named honestly — they carry a public-web note, never a data
chip, and live in ``ConsolidationLever.named_consolidators`` rather than as
labelled figures.

Every ``source_label`` leads with its DOMINANT honest basis (the composites are
modeled, so they lead ``ILLUSTRATIVE``) and names the GOV/SOURCED anchors INSIDE,
separated by `` · `` so the UI chip helper splits BASIS from the remainder.

Design contract (mirrors ``ift_analytics``): pure, no runtime network, cached,
frozen dataclasses, real ``ift_geo`` / ``ift_analytics`` / ``ift_clinical_demand``
data (never a hardcoded parallel copy), and every function **degrades — never
raises**, returning a typed record with ``available`` + ``source_label`` so the
report renders an honest label instead of crashing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import List, Optional, Tuple

# ── Honesty labels (the only four allowed bases) ─────────────────────────────
LABEL_GOV = "GOV"
LABEL_SOURCED = "SOURCED"
LABEL_ACADEMIC = "ACADEMIC"
LABEL_ILLUSTRATIVE = "ILLUSTRATIVE"
_BASES = (LABEL_GOV, LABEL_SOURCED, LABEL_ACADEMIC, LABEL_ILLUSTRATIVE)

# The three levers, named to line up 1:1 with the claims-understatement cleaner's
# LEVER_PRICE / LEVER_VOLUME / LEVER_SCALE so the tracker and the cleaner speak the
# same language (consolidation == SCALE). We do NOT import understatement to avoid
# coupling a report module to the npi_cleaner package; the crosswalk is documented.
LEVER_PRICE = "PRICE"
LEVER_VOLUME = "VOLUME"
LEVER_CONSOLIDATION = "CONSOLIDATION"          # == understatement.LEVER_SCALE
LEVERS = (LEVER_PRICE, LEVER_VOLUME, LEVER_CONSOLIDATION)


# ── PRICE lever constants ────────────────────────────────────────────────────
# The Medicare Ambulance Inflation Factor (AIF) — the annual Ambulance-Fee-Schedule
# update = CPI-U (12 mo ending prior June) minus a multifactor-productivity (MFP)
# adjustment. These are the PUBLISHED (GOV) annual factors; CY2023's 8.7% was the
# post-COVID inflation spike. The last three updates DECELERATE — CY2024 2.6%
# (CPI-U 3.0% − MFP 0.4%), CY2025 2.4%, CY2026 2.0% (CPI-U 2.7% − MFP 0.7%) — so
# any price lever above ~2.0-2.6% now sits ABOVE the GOV floor and is carried by
# commercial OON + escalators, not the AIF.
_AIF_TREND: Tuple[Tuple[int, float], ...] = (
    (2020, 0.9), (2021, 0.2), (2022, 5.1), (2023, 8.7), (2024, 2.6), (2025, 2.4),
    (2026, 2.0),
)

# The statutory temporary ground add-ons (a LEVEL effect on the base rate, not an
# annual growth rate) — 42 U.S.C. 1395m(l)(12)-(13), repeatedly extended by
# Congress. GOV percentages; their extension is a recurring policy-risk item.
_GROUND_ADDON_URBAN = 2.0            # GOV — urban ground add-on (%)
_GROUND_ADDON_RURAL = 3.0           # GOV — rural ground add-on (%)
# Super-rural: a +22.6% increase to the ground BASE RATE where the point of pickup
# is in the lowest 25% of rural population by density (42 CFR 414 Subpart H) — a
# base-rate bump, not a per-mile bump.
_GROUND_ADDON_SUPERRURAL = 22.6     # GOV — super-rural base-rate increase (%)

# Illustrative pay-mix blend for the composite. Medicare/Medicaid/MA grow ~at the
# AIF; commercial grows faster via OON leverage (ground ambulance is NSA-excluded)
# + facility-contract escalators. Shares are ILLUSTRATIVE (IFT payer mix skews more
# government than 911 because facilities order it for admitted/Medicare patients).
_GOVT_PAY_SHARE = 0.55              # ILLUSTRATIVE — Medicare+Medicaid+MA share of IFT $
_COMMERCIAL_PAY_SHARE = 0.45       # ILLUSTRATIVE — commercial + self-pay residual
_MEDICARE_GROWTH_LO_HI_PCT = (2.0, 3.0)      # ILLUSTRATIVE band around the GOV AIF anchor
_COMMERCIAL_GROWTH_PCT = (3.0, 4.0, 4.8)     # ILLUSTRATIVE — commercial rate growth (low/central/high)
_COMMERCIAL_MEDICARE_MULTIPLE = (2.0, 4.0)   # ILLUSTRATIVE — commercial pays ~2-4x Medicare
_CONTRACT_ESCALATOR_PCT = (2.0, 4.0)         # ILLUSTRATIVE — facility contract CPI escalator band


# ── VOLUME lever constants ───────────────────────────────────────────────────
# Non-demographic structural volume uplift (ED boarding, post-acute utilization,
# hub-and-spoke regionalization) layered ON TOP of the pure demographic tailwind.
_INTENSITY_UPLIFT_PCT = (0.0, 0.9, 1.8)      # ILLUSTRATIVE (low/central/high)
_DEMOGRAPHIC_FALLBACK_PCT = 2.2              # ILLUSTRATIVE — used only if the demand model is unreadable
_VOLUME_AGE_BANDS = ("65-74", "75-84", "85+")   # the aging cohorts that drive IFT demand


# ── CONSOLIDATION lever constants ────────────────────────────────────────────
_SHARE_SHIFT_PCT = (0.5, 1.0, 2.0)   # ILLUSTRATIVE — annual share-of-wallet shift toward the
#   consolidating outsourced platform. A SHARE-SHIFT, not organic market growth.
_AHA_SYSTEM_HOSPITAL_SHARE = 0.68    # AHA 2023 Annual Survey — share of community hospitals in a
#   system (an industry-census magnitude; carried ILLUSTRATIVE, named honestly).


def _clamp_share(x: float) -> float:
    return max(0.0, min(1.0, x))


def _pctw(x: float) -> str:
    """Worded signed annual percent, 1dp (the house style: pct → 1 decimal)."""
    return f"{x:+.1f}%/yr"


# ── Typed records (frozen — immutable, cache-safe) ───────────────────────────
@dataclass(frozen=True)
class LeverComponent:
    """One tracked driver within a lever. ``basis`` is exactly one of ``_BASES``;
    ``value`` is pre-worded (e.g. ``"+2.4%/yr"``, ``"$278.00"``, ``"60%"``) so the
    renderer never re-formats a number and lose its house-style precision."""
    name: str
    value: str
    basis: str
    detail: str = ""


@dataclass(frozen=True)
class PriceLever:
    """Reimbursement-inflation lever — GOV AIF anchor + modeled composite."""
    available: bool
    components: Tuple[LeverComponent, ...] = ()
    aif_trend: Tuple[Tuple[int, float], ...] = ()
    aif_latest_year: Optional[int] = None
    aif_latest_pct: Optional[float] = None
    aif_trailing3_avg_pct: Optional[float] = None
    aif_full_avg_pct: Optional[float] = None
    conversion_factor: Optional[float] = None
    composite_low_pct: float = 0.0
    composite_central_pct: float = 0.0
    composite_high_pct: float = 0.0
    source_label: str = ""
    headline: str = ""
    note: str = ""


@dataclass(frozen=True)
class VolumeLever:
    """Demographic + acuity + utilization volume-growth lever."""
    available: bool
    components: Tuple[LeverComponent, ...] = ()
    demographic_cagr_pct: float = 0.0
    demographic_is_modeled_fallback: bool = False
    age_band_cagr_pct: Tuple[Tuple[str, float], ...] = ()
    occupancy_pct: Optional[float] = None
    occupancy_delta_pp: Optional[float] = None
    postacute_supply_total: Optional[int] = None
    high_acuity_share: Optional[float] = None
    composite_low_pct: float = 0.0
    composite_central_pct: float = 0.0
    composite_high_pct: float = 0.0
    source_label: str = ""
    headline: str = ""
    note: str = ""


@dataclass(frozen=True)
class ConsolidationLever:
    """Big-systems-getting-bigger lever — a platform multiplier / SHARE-SHIFT,
    NOT organic market growth (``is_share_shift`` is always True)."""
    available: bool
    is_share_shift: bool = True
    components: Tuple[LeverComponent, ...] = ()
    multi_system_ift_share: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    addressable_share: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    sam_over_som_multiple: Optional[float] = None
    footprint_bed_share: Optional[float] = None
    share_shift_low_pct: float = 0.0
    share_shift_central_pct: float = 0.0
    share_shift_high_pct: float = 0.0
    named_consolidators: Tuple[str, ...] = ()
    consolidators_note: str = ""
    source_label: str = ""
    headline: str = ""
    note: str = ""


@dataclass(frozen=True)
class GrowthBridge:
    """The three levers combined: price × volume compound into an organic
    market-growth read; consolidation layered on as an explicit share-shift to
    give a share-gaining platform's total growth."""
    available: bool
    contributions: Tuple[LeverComponent, ...] = ()
    price_central_pct: float = 0.0
    volume_central_pct: float = 0.0
    # organic market growth = (1+price)(1+volume) - 1  (price × volume compound)
    market_growth_low_pct: float = 0.0
    market_growth_central_pct: float = 0.0
    market_growth_high_pct: float = 0.0
    # consolidation share-shift (platform-level, NOT market growth)
    consolidation_share_shift_low_pct: float = 0.0
    consolidation_share_shift_central_pct: float = 0.0
    consolidation_share_shift_high_pct: float = 0.0
    # platform growth = organic market growth + consolidation share-shift
    platform_growth_low_pct: float = 0.0
    platform_growth_central_pct: float = 0.0
    platform_growth_high_pct: float = 0.0
    price: Optional[PriceLever] = None
    volume: Optional[VolumeLever] = None
    consolidation: Optional[ConsolidationLever] = None
    source_label: str = ""
    headline: str = ""
    note: str = ""


# ── PRICE lever ──────────────────────────────────────────────────────────────
def _price_from(cf: Optional[float]) -> PriceLever:
    """Build the price lever from the GOV AIF trend + the (reused) conversion
    factor. Pure and always available — the AIF trend is a published constant, so
    even a missing conversion factor only drops one worked-dollar figure. ``cf``
    is ``ift_analytics.fee_schedule().conversion_factor`` (or ``None``)."""
    trend = _AIF_TREND
    latest_year, latest_pct = trend[-1]
    last3 = [p for _, p in trend[-3:]]
    avg3 = round(sum(last3) / len(last3), 1)
    avg_full = round(sum(p for _, p in trend) / len(trend), 1)

    # Composite = pay-mix blend of (Medicare ~AIF anchor) and (commercial faster).
    med_lo, med_hi = _MEDICARE_GROWTH_LO_HI_PCT
    med_c = latest_pct                      # the GOV AIF anchor drives the Medicare component
    com_lo, com_c, com_hi = _COMMERCIAL_GROWTH_PCT
    g, c = _GOVT_PAY_SHARE, _COMMERCIAL_PAY_SHARE
    comp_lo = round(g * med_lo + c * com_lo, 1)
    comp_c = round(g * med_c + c * com_c, 1)
    comp_hi = round(g * med_hi + c * com_hi, 1)

    comps: List[LeverComponent] = [
        LeverComponent(
            "Medicare Ambulance Inflation Factor (AIF) — latest",
            _pctw(latest_pct), LABEL_GOV,
            f"CY{latest_year} AFS update = CPI-U minus the productivity "
            f"adjustment; trailing-3yr avg {avg3:+.1f}%, {len(trend)}-yr avg "
            f"{avg_full:+.1f}% (the CY2023 {trend[3][1]:+.1f}% spike was the "
            "post-COVID CPI peak)."),
        LeverComponent(
            "Conversion factor (base-rate multiplier)",
            (f"${cf:,.2f}" if cf is not None else "n/a"), LABEL_ILLUSTRATIVE,
            "reused from ift_analytics.fee_schedule(); RVU × CF = base rate. The "
            "exact CF ships in the CMS AFS public-use file and is updated each "
            "year by the GOV AIF, so CF growth ≈ the AIF."),
        LeverComponent(
            "Temporary ground add-ons",
            f"+{_GROUND_ADDON_URBAN:.0f}% urban / +{_GROUND_ADDON_RURAL:.0f}% "
            f"rural / +{_GROUND_ADDON_SUPERRURAL:.1f}% super-rural", LABEL_GOV,
            "42 U.S.C. 1395m(l)(12)-(13) statutory add-ons on the base rate — a "
            "recurring must-extend rider; a level effect, not an annual growth "
            "rate. Most recently extended by Section 6203 of the Consolidated "
            "Appropriations Act, 2026 through Dec 31, 2027 (from the prior Jan 31, "
            "2026 expiry); absent new legislation they lapse Jan 1, 2028 — a dated "
            "policy-risk cliff to track."),
        LeverComponent(
            "Commercial out-of-network (OON) leverage",
            f"~{_COMMERCIAL_MEDICARE_MULTIPLE[0]:.0f}-"
            f"{_COMMERCIAL_MEDICARE_MULTIPLE[1]:.0f}× Medicare", LABEL_ILLUSTRATIVE,
            "ground ambulance is EXCLUDED from the No Surprises Act (GOV — only "
            "AIR is covered), so it keeps balance-billing / OON pricing power; "
            "commercial pays a multiple of Medicare. Some states cap ground OON, "
            "so the leverage is uneven."),
        LeverComponent(
            "Facility-contract escalators",
            f"~+{_CONTRACT_ESCALATOR_PCT[0]:.0f}-{_CONTRACT_ESCALATOR_PCT[1]:.0f}%/yr",
            LABEL_ILLUSTRATIVE,
            "hospital/health-system IFT contracts commonly carry CPI-linked annual "
            "rate escalators; magnitude modeled."),
        LeverComponent(
            "Composite reimbursement inflation",
            _pctw(comp_c), LABEL_ILLUSTRATIVE,
            f"range {comp_lo:+.1f}-{comp_hi:+.1f}%/yr — a {g*100:.0f}/"
            f"{c*100:.0f} government/commercial pay-mix blend of the GOV AIF "
            "anchor and the faster (modeled) commercial rate growth."),
    ]

    headline = (
        f"Reimbursement inflation ≈ {_pctw(comp_c)} composite "
        f"({comp_lo:+.1f}-{comp_hi:+.1f}%/yr): the GOV Medicare AIF anchors the "
        f"government book at {_pctw(latest_pct)} (CY{latest_year}), commercial OON "
        "leverage + facility escalators lift the blend. ILLUSTRATIVE composite; "
        "GOV AIF + statutory add-ons named.")

    return PriceLever(
        available=True, components=tuple(comps), aif_trend=trend,
        aif_latest_year=latest_year, aif_latest_pct=latest_pct,
        aif_trailing3_avg_pct=avg3, aif_full_avg_pct=avg_full,
        conversion_factor=cf,
        composite_low_pct=comp_lo, composite_central_pct=comp_c,
        composite_high_pct=comp_hi,
        source_label=(
            "ILLUSTRATIVE · composite reimbursement-inflation read; GOV anchors = "
            "Medicare Ambulance Inflation Factor (AIF) annual updates + statutory "
            "ground add-ons (42 U.S.C. 1395m(l)) + the No Surprises Act ground "
            "exclusion; commercial OON leverage + facility escalators modeled"),
        headline=headline,
        note=("The AIF trend and the statutory add-ons are GOV; the conversion "
              "factor, the commercial multiple, the pay-mix blend, and the "
              "composite %/yr are ILLUSTRATIVE (named basis). Add-ons are a LEVEL "
              "effect on the base rate, not part of the annual growth composite."))


@lru_cache(maxsize=1)
def price_lever() -> PriceLever:
    """PRICE lever — reimbursement inflation, GOV-AIF-anchored composite ~+2-4%/yr.

    Reuses ``ift_analytics.fee_schedule`` for the conversion factor. Degrades to an
    AIF-only build (still available — the AIF is a published constant) if the fee
    schedule cannot be read; never raises."""
    cf: Optional[float] = None
    try:
        from . import ift_analytics
        fs = ift_analytics.fee_schedule()
        if fs.available:
            cf = fs.conversion_factor
    except Exception:  # noqa: BLE001 — degrade, never raise
        cf = None
    try:
        return _price_from(cf)
    except Exception:  # noqa: BLE001
        return PriceLever(
            available=False,
            source_label=("ILLUSTRATIVE · composite reimbursement inflation; GOV "
                          "anchor = Medicare Ambulance Inflation Factor"),
            note="Price-lever composite could not be built offline.")


# ── VOLUME lever ─────────────────────────────────────────────────────────────
def _volume_from(demographic_cagr_pct: Optional[float],
                 age_band_cagr_pct: Tuple[Tuple[str, float], ...],
                 occupancy_pct: Optional[float],
                 occupancy_delta_pp: Optional[float],
                 postacute_supply_total: Optional[int],
                 high_acuity_share: Optional[float]) -> VolumeLever:
    """Build the volume lever from the demographic tailwind (percent, from the
    SOURCED demand model) plus the SOURCED occupancy / supply anchors. Pure;
    every optional input degrades to an honest note (a ``None`` demographic falls
    back to a labelled ILLUSTRATIVE constant), so it never raises."""
    is_fallback = demographic_cagr_pct is None
    demo_c = _DEMOGRAPHIC_FALLBACK_PCT if is_fallback else round(float(demographic_cagr_pct), 1)

    up_lo, up_c, up_hi = _INTENSITY_UPLIFT_PCT
    comp_lo = round(demo_c + up_lo, 1)
    comp_c = round(demo_c + up_c, 1)
    comp_hi = round(demo_c + up_hi, 1)

    demo_basis = LABEL_ILLUSTRATIVE
    demo_detail = (
        "volume-weighted demographic CAGR across the escalation book "
        "(ift_clinical_demand.registry_summary) — population-only, incidence held "
        "constant; the 65-84/85+ aging cohorts drive it."
        + (" [demand model unavailable offline — labelled ILLUSTRATIVE fallback]"
           if is_fallback else ""))

    comps: List[LeverComponent] = [
        LeverComponent(
            "Aging demographic tailwind (volume-weighted)",
            _pctw(demo_c), demo_basis, demo_detail),
    ]
    for band, cagr in age_band_cagr_pct:
        comps.append(LeverComponent(
            f"Population CAGR — {band}", _pctw(cagr), LABEL_ILLUSTRATIVE,
            "demand_forecast._POP_GROWTH_BY_AGE age-band population CAGR "
            "(Census-projection-anchored); the oldest bands grow fastest and "
            "generate the most acute interfacility transfers."))
    if high_acuity_share is not None:
        comps.append(LeverComponent(
            "Acuity mix-shift (CCT/SCT share of escalation)",
            f"{high_acuity_share * 100:.1f}%", LABEL_ILLUSTRATIVE,
            "GOV national volumes × authored transport-acuity tiers "
            "(ift_clinical_demand.mission_mix); the escalation book skews to the "
            "high-acuity, high-reimbursement CCT/SCT tier and that mix is "
            "growing — a volume-quality lever on top of raw counts."))
    if occupancy_pct is not None:
        delta = f", {occupancy_delta_pp:+.1f}pp across the window" if occupancy_delta_pp is not None else ""
        comps.append(LeverComponent(
            "ED boarding & capacity load-balancing",
            f"occupancy {occupancy_pct * 100:.1f}%{delta}", LABEL_SOURCED,
            "national inpatient occupancy from the vendored CMS HCRIS panel "
            "(ift_analytics.occupancy_trend) — the throughput engine: when beds "
            "fill, ED-boarding builds and capacity/load-balancing transfers rise."))
    if postacute_supply_total is not None:
        comps.append(LeverComponent(
            "Post-acute utilization (destination supply)",
            f"{postacute_supply_total:,} post-acute destinations", LABEL_SOURCED,
            "real SNF/IRF/LTACH/HHA/hospice provider counts "
            "(ift_clinical_demand.destination_supply); more discharges routed to "
            "post-acute by stretcher = more down-transfer volume."))
    comps.append(LeverComponent(
        "Hub-and-spoke regionalization",
        "structural", LABEL_ILLUSTRATIVE,
        "transfer-center command centers concentrate up-transfers at "
        "tertiary/quaternary hubs and repatriate the return leg — a structural "
        "volume multiplier (each escalation ≈ a paired back-transfer); magnitude "
        "modeled."))
    comps.append(LeverComponent(
        "Composite volume growth", _pctw(comp_c), LABEL_ILLUSTRATIVE,
        f"range {comp_lo:+.1f}-{comp_hi:+.1f}%/yr — the demographic tailwind "
        f"({_pctw(demo_c)}) plus the modeled non-demographic intensity uplift "
        "(ED boarding, post-acute utilization, regionalization)."))

    headline = (
        f"Volume + demographic growth ≈ {_pctw(comp_c)} composite "
        f"({comp_lo:+.1f}-{comp_hi:+.1f}%/yr): a {_pctw(demo_c)} aging-cohort "
        "demographic tailwind (SOURCED demand model) lifted by ED-boarding, "
        "post-acute utilization, and hub-and-spoke regionalization. ILLUSTRATIVE "
        "composite; demographic CAGRs from the demand model, occupancy/supply "
        "anchors SOURCED.")

    return VolumeLever(
        available=True, components=tuple(comps),
        demographic_cagr_pct=demo_c, demographic_is_modeled_fallback=is_fallback,
        age_band_cagr_pct=age_band_cagr_pct,
        occupancy_pct=occupancy_pct, occupancy_delta_pp=occupancy_delta_pp,
        postacute_supply_total=postacute_supply_total,
        high_acuity_share=high_acuity_share,
        composite_low_pct=comp_lo, composite_central_pct=comp_c,
        composite_high_pct=comp_hi,
        source_label=(
            "ILLUSTRATIVE · composite volume-growth read; SOURCED anchors = "
            "ift_clinical_demand demographic CAGRs (demand_forecast age bands) + "
            "HCRIS inpatient occupancy + CMS post-acute destination supply; "
            "non-demographic intensity uplift modeled"),
        headline=headline,
        note=("The demographic CAGRs are labelled ILLUSTRATIVE from the SOURCED "
              "demand model (population-only, incidence held constant); the "
              "occupancy and destination-supply anchors are SOURCED from our "
              "vendored CMS files; the intensity uplift and the composite %/yr "
              "are ILLUSTRATIVE."))


@lru_cache(maxsize=1)
def volume_lever() -> VolumeLever:
    """VOLUME lever — demographic + acuity + utilization growth, composite ~+2-4%/yr.

    Reuses ``ift_clinical_demand`` (the volume-weighted demographic CAGR, the
    per-age-band population CAGRs, the acuity mix, and the SOURCED destination
    supply) and ``ift_analytics.occupancy_trend`` (the SOURCED HCRIS occupancy
    signal). Degrades to a labelled ILLUSTRATIVE fallback if the demand model is
    unreadable; never raises."""
    demo_pct: Optional[float] = None
    bands: Tuple[Tuple[str, float], ...] = ()
    supply_total: Optional[int] = None
    high_share: Optional[float] = None
    occ_pct: Optional[float] = None
    occ_delta: Optional[float] = None
    try:
        from . import ift_clinical_demand as cd
        rs = cd.registry_summary()
        demo = rs.get("escalation_volume_weighted_cagr")
        if isinstance(demo, (int, float)) and demo > 0:
            demo_pct = float(demo) * 100.0
        pop = cd._pop_growth()
        bands = tuple(
            (b, round(float(pop.get(b, {}).get("cagr_5yr", 0.0)) * 100.0, 1))
            for b in _VOLUME_AGE_BANDS if b in pop)
        mm = cd.mission_mix()
        hs = mm.get("high_acuity_share")
        if isinstance(hs, (int, float)):
            high_share = float(hs)
        sup = cd.destination_supply()
        nat = sup.get("national")
        if isinstance(nat, int):
            supply_total = nat
    except Exception:  # noqa: BLE001
        pass
    try:
        from . import ift_analytics
        occ = ift_analytics.occupancy_trend()
        if occ.available and occ.latest_occupancy is not None:
            occ_pct = occ.latest_occupancy
            occ_delta = occ.delta_pp
    except Exception:  # noqa: BLE001
        pass
    try:
        return _volume_from(demo_pct, bands, occ_pct, occ_delta,
                            supply_total, high_share)
    except Exception:  # noqa: BLE001
        return VolumeLever(
            available=False,
            source_label=("ILLUSTRATIVE · composite volume growth; SOURCED anchor "
                          "= ift_clinical_demand demographic model"),
            note="Volume-lever composite could not be built offline.")


# ── CONSOLIDATION lever ──────────────────────────────────────────────────────
def _consolidation_from(multi_share: Optional[Tuple[float, float, float]],
                        addressable: Optional[Tuple[float, float, float]],
                        sam_over_som: Optional[float],
                        footprint_bed_share: Optional[float],
                        named: Tuple[str, ...]) -> ConsolidationLever:
    """Build the consolidation lever. Pure; every reused figure is ILLUSTRATIVE
    (inherited from ``health_system_sam``), the footprint bed-share is the one
    SOURCED anchor, and named consolidators carry a public-web note rather than a
    data chip. Degrades gracefully when the SAM spine is unavailable — never
    raises."""
    ms = multi_share or (0.50, 0.60, 0.70)
    addr = addressable or (0.68, 0.75, 0.82)
    sh_lo, sh_c, sh_hi = _SHARE_SHIFT_PCT

    comps: List[LeverComponent] = [
        LeverComponent(
            "Multi-hospital-system share of IFT $",
            f"{ms[0] * 100:.0f}-{ms[2] * 100:.0f}% (central {ms[1] * 100:.0f}%)",
            LABEL_ILLUSTRATIVE,
            "reused from ift_analytics.health_system_sam — AHA 2023 puts "
            f"~{_AHA_SYSTEM_HOSPITAL_SHARE * 100:.0f}% of community hospitals in a "
            "system, and acute up-transfers concentrate at system-owned "
            "tertiary/quaternary hubs, so IFT $ over-indexes on system involvement."),
        LeverComponent(
            "Addressable (outsourceable) share",
            f"{addr[0] * 100:.0f}-{addr[2] * 100:.0f}% (central {addr[1] * 100:.0f}%)",
            LABEL_ILLUSTRATIVE,
            "1 − the health-system-biller insource ceiling (health_system_sam); "
            "hospitals rarely own ground fleets, so most system IFT $ is winnable "
            "by an outsourced platform."),
    ]
    if sam_over_som is not None:
        comps.append(LeverComponent(
            "SAM / SOM headroom multiple",
            f"~{sam_over_som:.1f}×", LABEL_ILLUSTRATIVE,
            "structural SAM (multi-hospital health systems) vs the operator's "
            "current-footprint SOM (health_system_sam) — built off the "
            "GOV-anchored TAM and the SOURCED HCRIS/ift_geo bed structure; the "
            "consolidation runway is structural, not just in-footprint."))
    if footprint_bed_share is not None:
        comps.append(LeverComponent(
            "Footprint share of national beds",
            f"{footprint_bed_share * 100:.1f}%", LABEL_SOURCED,
            "the operator footprint's HCRIS bed share of the national base "
            "(ift_geo/HCRIS) — the SOURCED spine the ILLUSTRATIVE consolidation "
            "ratios are scaled against."))
    comps.append(LeverComponent(
        "Annual share-of-wallet shift",
        f"+{sh_lo:.1f} to +{sh_hi:.1f}pp/yr (central +{sh_c:.1f}pp)",
        LABEL_ILLUSTRATIVE,
        "as systems consolidate they move IFT to preferred/sole-source contracts; "
        "a platform holding the transfer-center first-call converts insourced / "
        "fragmented volume into share. A SHARE-SHIFT, not organic market growth — "
        "modeled magnitude."))

    headline = (
        f"Consolidation is a platform multiplier / SHARE-SHIFT (not organic "
        f"market growth): ~{ms[1] * 100:.0f}% of IFT $ sits inside multi-hospital "
        f"systems, ~{addr[1] * 100:.0f}% of it is outsourceable"
        + (f", and the structural SAM is ~{sam_over_som:.0f}× the current SOM"
           if sam_over_som is not None else "")
        + f". A share-gaining platform captures ~+{sh_c:.1f}pp/yr of wallet. "
        "Magnitudes ILLUSTRATIVE.")

    return ConsolidationLever(
        available=True, is_share_shift=True, components=tuple(comps),
        multi_system_ift_share=ms, addressable_share=addr,
        sam_over_som_multiple=sam_over_som, footprint_bed_share=footprint_bed_share,
        share_shift_low_pct=sh_lo, share_shift_central_pct=sh_c,
        share_shift_high_pct=sh_hi,
        named_consolidators=named,
        consolidators_note=("Named consolidators are PUBLIC-WEB knowledge, named "
                            "honestly (health-system M&A + operator roll-up) — "
                            "not a data-derived figure."),
        source_label=(
            "ILLUSTRATIVE · consolidation is a platform SHARE-SHIFT, not organic "
            "market growth; ratios reused from ift_analytics.health_system_sam "
            "(GOV-anchored TAM × ILLUSTRATIVE system/insource shares), footprint "
            "bed-share SOURCED (ift_geo/HCRIS); consolidator names public-web"),
        headline=headline,
        note=("CRITICAL FRAMING: consolidation does NOT grow the TAM — it grows a "
              "platform's SHARE of it. The multi-system share, the addressable "
              "share, and the SAM/SOM multiple are ILLUSTRATIVE ratios inherited "
              "from health_system_sam; the footprint bed-share is SOURCED; the "
              "annual share-shift is a modeled magnitude. Keep it OUT of the "
              "organic price×volume compound in growth_bridge."))


@lru_cache(maxsize=1)
def consolidation_lever() -> ConsolidationLever:
    """CONSOLIDATION lever — big health systems getting bigger, expressed as a
    platform multiplier / SHARE-SHIFT (never as organic market growth).

    Reuses ``ift_analytics.health_system_sam`` for the multi-hospital-system share
    of IFT $, the addressable share, and the SAM/SOM headroom, and ``ift_geo``
    ``named_operators`` for the PUBLIC-WEB consolidator names. Degrades to the
    documented ILLUSTRATIVE bands if the SAM spine or ift_geo is unavailable;
    never raises."""
    multi: Optional[Tuple[float, float, float]] = None
    addr: Optional[Tuple[float, float, float]] = None
    sam_over_som: Optional[float] = None
    bed_share: Optional[float] = None
    named: Tuple[str, ...] = ()
    try:
        from . import ift_analytics
        hs = ift_analytics.health_system_sam()
        if hs.available:
            multi = hs.multi_system_ift_share
            addr = hs.addressable_share
            sam_over_som = hs.sam_over_som_multiple
            bed_share = hs.footprint_bed_share
    except Exception:  # noqa: BLE001
        pass
    try:
        named = _named_consolidators()
    except Exception:  # noqa: BLE001
        named = ()
    try:
        return _consolidation_from(multi, addr, sam_over_som, bed_share, named)
    except Exception:  # noqa: BLE001
        return ConsolidationLever(
            available=False,
            source_label=("ILLUSTRATIVE · consolidation share-shift; ratios from "
                          "ift_analytics.health_system_sam"),
            note="Consolidation-lever build failed offline.")


_CONSOLIDATOR_BRANDS: Tuple[Tuple[Tuple[str, ...], str], ...] = (
    # (match-tags in the ift_geo operator string, canonical public-web label)
    (("ameripro",),
     "AmeriPro Health (regional ground-IFT roll-up — e.g. its Priority Medical "
     "Transport acquisition)"),
    (("global medical response", "gmr", "amr"),
     "Global Medical Response / AMR (GMR — the national ground-transport platform)"),
    (("midwest medical transport",),
     "Midwest Medical Transport (MMT — the reference incumbent)"),
)


def _named_consolidators() -> Tuple[str, ...]:
    """The PUBLIC-WEB platform consolidators, named honestly. Harvests which
    roll-up brands actually appear in the ift_geo ``named_operators`` and emits ONE
    canonical label per brand (so the marquee names aren't repeated per metro),
    then adds the marquee integrating health systems (the consolidation side of
    the lever). Public-web knowledge, not a data-derived figure."""
    present: set = set()
    try:
        from . import ift_geo
        for md in ift_geo.MARKETS:
            for op in md.named_operators:
                low = op.lower()
                for i, (tags, _label) in enumerate(_CONSOLIDATOR_BRANDS):
                    if any(tag in low for tag in tags):
                        present.add(i)
    except Exception:  # noqa: BLE001
        pass
    out: List[str] = [label for i, (_tags, label) in enumerate(_CONSOLIDATOR_BRANDS)
                      if i in present]
    # Marquee integrating systems (public-web; the health-system consolidation side).
    out.extend((
        "CommonSpirit Health / CHI (national multi-state system w/ captive "
        "intra-system transfer lanes)",
        "Cleveland Clinic (captive Critical Care Transport — the insource ceiling)",
        "HCA Healthcare / Bon Secours Mercy Health (multi-market integrating systems)"))
    return tuple(out)


# ── The bridge — combine the three levers ────────────────────────────────────
def _compound_pct(a_pct: float, b_pct: float) -> float:
    """Compound two annual percents: (1+a)(1+b) − 1, back in percent (1dp)."""
    return round(((1.0 + a_pct / 100.0) * (1.0 + b_pct / 100.0) - 1.0) * 100.0, 1)


def _assemble_bridge(price: PriceLever, volume: VolumeLever,
                     cons: ConsolidationLever) -> GrowthBridge:
    """Combine the three levers. Pure; degrades if a sub-lever is unavailable (a
    missing price or volume lever zeroes only its own contribution, and the bridge
    is marked unavailable only if BOTH organic levers are missing). Never raises.

    Price × Volume COMPOUND into organic market growth; consolidation is layered
    on top as an EXPLICIT share-shift (platform growth), never folded into the
    organic compound."""
    p_ok = bool(price and price.available)
    v_ok = bool(volume and volume.available)
    c_ok = bool(cons and cons.available)

    p_lo = price.composite_low_pct if p_ok else 0.0
    p_c = price.composite_central_pct if p_ok else 0.0
    p_hi = price.composite_high_pct if p_ok else 0.0
    v_lo = volume.composite_low_pct if v_ok else 0.0
    v_c = volume.composite_central_pct if v_ok else 0.0
    v_hi = volume.composite_high_pct if v_ok else 0.0

    mkt_lo = _compound_pct(p_lo, v_lo)
    mkt_c = _compound_pct(p_c, v_c)
    mkt_hi = _compound_pct(p_hi, v_hi)

    ss_lo = cons.share_shift_low_pct if c_ok else 0.0
    ss_c = cons.share_shift_central_pct if c_ok else 0.0
    ss_hi = cons.share_shift_high_pct if c_ok else 0.0

    plat_lo = round(mkt_lo + ss_lo, 1)
    plat_c = round(mkt_c + ss_c, 1)
    plat_hi = round(mkt_hi + ss_hi, 1)

    contributions = (
        LeverComponent(
            "PRICE — reimbursement inflation", _pctw(p_c),
            LABEL_ILLUSTRATIVE if p_ok else LABEL_ILLUSTRATIVE,
            "GOV Medicare AIF anchor + commercial OON leverage + facility "
            "escalators (price_lever)." if p_ok else "price lever unavailable."),
        LeverComponent(
            "VOLUME — demographic + acuity growth", _pctw(v_c),
            LABEL_ILLUSTRATIVE,
            "SOURCED aging-cohort demand model + ED-boarding / post-acute / "
            "regionalization (volume_lever)." if v_ok else "volume lever unavailable."),
        LeverComponent(
            "Organic market growth (PRICE × VOLUME compound)", _pctw(mkt_c),
            LABEL_ILLUSTRATIVE,
            f"range {mkt_lo:+.1f}-{mkt_hi:+.1f}%/yr — price and volume COMPOUND "
            "(not add) into the organic market tailwind."),
        LeverComponent(
            "CONSOLIDATION — share-shift (NOT market growth)",
            f"+{ss_c:.1f}pp/yr", LABEL_ILLUSTRATIVE,
            "big systems getting bigger → a platform captures share of wallet "
            "(consolidation_lever). Layered ON TOP of organic growth, never inside "
            "the compound." if c_ok else "consolidation lever unavailable."),
        LeverComponent(
            "Platform growth (organic + share-shift)", _pctw(plat_c),
            LABEL_ILLUSTRATIVE,
            f"range {plat_lo:+.1f}-{plat_hi:+.1f}%/yr — what a share-gaining "
            "consolidating platform can compound; organic market growth plus the "
            "consolidation share-shift."),
    )

    headline = (
        f"Organic IFT market growth ≈ {_pctw(mkt_c)} ({mkt_lo:+.1f}-{mkt_hi:+.1f}"
        f"%/yr) = price {_pctw(p_c)} × volume {_pctw(v_c)} COMPOUND. Consolidation "
        f"adds ~+{ss_c:.1f}pp/yr of SHARE-SHIFT on top → a share-gaining platform "
        f"compounds ≈ {_pctw(plat_c)} ({plat_lo:+.1f}-{plat_hi:+.1f}%/yr). All "
        "composites ILLUSTRATIVE; GOV AIF + SOURCED demand anchors named in the "
        "levers.")

    available = p_ok or v_ok
    return GrowthBridge(
        available=available, contributions=contributions,
        price_central_pct=p_c, volume_central_pct=v_c,
        market_growth_low_pct=mkt_lo, market_growth_central_pct=mkt_c,
        market_growth_high_pct=mkt_hi,
        consolidation_share_shift_low_pct=ss_lo,
        consolidation_share_shift_central_pct=ss_c,
        consolidation_share_shift_high_pct=ss_hi,
        platform_growth_low_pct=plat_lo, platform_growth_central_pct=plat_c,
        platform_growth_high_pct=plat_hi,
        price=price if p_ok else None,
        volume=volume if v_ok else None,
        consolidation=cons if c_ok else None,
        source_label=(
            "ILLUSTRATIVE · three-lever growth bridge; price × volume COMPOUND is "
            "organic market growth (GOV AIF + SOURCED demand anchors, named in the "
            "levers), consolidation is an explicit ILLUSTRATIVE share-shift layered "
            "on top — never folded into the organic compound"),
        headline=headline,
        note=("The bridge keeps the honest distinction the thesis rests on: PRICE "
              "and VOLUME compound into ORGANIC market growth; CONSOLIDATION is a "
              "platform SHARE-SHIFT (big systems getting bigger, a platform "
              "capturing their wallet), added separately to give platform growth. "
              "Every composite is ILLUSTRATIVE; the GOV AIF and the SOURCED "
              "demographic/occupancy/supply anchors live inside the individual "
              "levers."))


@lru_cache(maxsize=1)
def growth_bridge() -> GrowthBridge:
    """Combine the three levers into an overall market-growth read.

    Price × Volume compound into organic market growth (~+4-8%/yr); consolidation
    is layered on as an explicit share-shift to give a share-gaining platform's
    total growth. Reuses ``price_lever`` / ``volume_lever`` / ``consolidation_lever``
    (each carrying its own GOV/SOURCED anchors). Degrades if the organic levers
    are unavailable; never raises."""
    try:
        return _assemble_bridge(price_lever(), volume_lever(),
                                consolidation_lever())
    except Exception:  # noqa: BLE001
        return GrowthBridge(
            available=False,
            source_label=("ILLUSTRATIVE · three-lever growth bridge (price × "
                          "volume compound + consolidation share-shift)"),
            note="Growth bridge could not be assembled offline.")


def all_levers() -> List[object]:
    """The three levers as a list (price, volume, consolidation) for the report /
    page to iterate. Degrade-safe — each element is a typed result carrying its
    own ``available`` flag."""
    return [price_lever(), volume_lever(), consolidation_lever()]
