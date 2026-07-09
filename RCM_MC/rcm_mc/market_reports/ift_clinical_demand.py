"""IFT Clinical Acute-Transfer Demand Engine — the volume/growth backbone.

Interfacility Transport (IFT) demand *is* clinical acute transfers: a ground-IFT
operator's volume equals the count of acute patients who must MOVE between
facilities. This module models that demand at the clinical-case level. Each
acute scenario maps:

    presenting picture  ->  validated ICD-10-CM + MS-DRG codes
                        ->  transfer TYPE (up / down / lateral)
                        ->  destination CAPABILITY + post-acute SETTING
                        ->  national annual VOLUME (published figure)
                        ->  demographic GROWTH outlook (demand_forecast model)

It covers all three families the owner listed:

  * **Escalation (up)** — transfer OUT to a higher level of care (chest pain/MI,
    stroke, sepsis, respiratory failure, trauma, GI bleed, behavioral-health
    crisis, pediatric/neonatal, high-risk OB, surgical complication, hip fx).
  * **Step-down / Recovery (down)** — transfer DOWN to post-acute (ICU
    step-down, post-vent -> LTACH, post-stroke -> IRF, med-surg -> SNF/home
    health, hip-fx -> IRF/SNF, comfort -> hospice).
  * **Direct-admit / Load-balancing (lateral)** — physician-to-physician direct
    admits, ED interfacility up-transfers, inter-hospital ICU/bed
    load-balancing, and repatriation/back-transfer.

────────────────────────────────────────────────────────────────────────────
HONESTY LABELS  (the load-bearing invariant — this is a diligence tool)
────────────────────────────────────────────────────────────────────────────
Every figure carries a basis label:

  * ``SOURCED``      — computed from OUR data. Here: the ICD-10-CM code
                       validation (against the vendored FY2025/FY2026 billability
                       seed) and the destination-SUPPLY counts (SNF/IRF/LTACH/
                       HHA/hospice provider CSVs).
  * ``GOV``          — a real published CMS / AHRQ HCUP / CDC / MedPAC / NCHS
                       figure. National condition VOLUMES are GOV literals: NIS
                       rows are NOT vendored offline (``rcm_mc/data/ahrq_hcup.py``
                       is a store-backed loader needing records), so this module
                       does NOT compute volumes and does NOT import that loader.
  * ``ACADEMIC``     — a real peer-reviewed / epidemiologic figure (e.g. the
                       Stefan NIS acute-respiratory-failure series).
  * ``ILLUSTRATIVE`` — modeled with a stated basis. The per-condition GROWTH
                       CAGR is computed from ``demand_forecast._POP_GROWTH_BY_AGE``
                       age-band population CAGRs weighted by each condition's
                       authored age skew; the projection is ILLUSTRATIVE and
                       holds age-specific incidence constant (population-only
                       tailwind).

Two things are AUTHORED CLINICAL REFERENCE, not SOURCED: (1) the up-transfer
``destination_capability`` designations (Comprehensive Stroke Center, Level I
Trauma, PCI/cath, NICU III/IV) are NOT in any vendored file; (2) ICD-10-PCS
procedure codes are reference-only because no offline PCS validity table exists
in the repo (only ICD-10-CM is vendored). ``validate_codes()`` surfaces PCS
under a separate ``pcs_reference`` bucket and never asserts them billable.

The module is pure, cached, offline, and degrades gracefully (a missing CSV or
a demand_forecast import failure returns an honest empty/zero rather than
raising). No new runtime dependencies (stdlib + a read-only import of
``rcm_mc.data_public.demand_forecast``).
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths + honesty-label constants
# ---------------------------------------------------------------------------

_PKG = Path(__file__).resolve().parents[1]                     # rcm_mc/
_SEED = _PKG / "npi_cleaner" / "vendor_v49" / "npi_recovery" / "reference" / "icd10cm_validity_seed.csv"
_DATA = _PKG / "data"

# Post-acute destination settings -> real provider CSV (the SOURCED supply).
_SETTING_CSV = {
    "SNF": "snf_providers.csv",
    "IRF": "irf_providers.csv",
    "LTACH": "ltch_providers.csv",
    "HHA": "home_health_providers.csv",
    "Hospice": "hospice_providers.csv",
}

LABEL_SOURCED = "SOURCED"
LABEL_GOV = "GOV"
LABEL_ACADEMIC = "ACADEMIC"
LABEL_ILLUSTRATIVE = "ILLUSTRATIVE"
_HONESTY_TAGS = (LABEL_SOURCED, LABEL_GOV, LABEL_ACADEMIC, LABEL_ILLUSTRATIVE)

# Families + transfer directions (kept as constants so callers/tests don't
# hand-type the strings).
FAMILY_ESCALATION = "Escalation"
FAMILY_STEPDOWN = "Step-down/Recovery"
FAMILY_LOADBALANCE = "Direct-admit/Load-balancing"

TRANSFER_UP = "up"
TRANSFER_DOWN = "down"
TRANSFER_LATERAL = "lateral"

# Transport-acuity tiers (Medicare ambulance ladder + specialty teams). The
# escalation book skews toward the high-acuity CCT/SCT + specialty tiers, which
# is the headline IFT mission-mix result. ``_HIGH_ACUITY_TIERS`` classifies the
# tiers that require a critical-care crew / specialty team.
TIER_CCT_SCT = "CCT/SCT"                 # critical-care / specialty-care transport
TIER_NEONATAL = "Neonatal team"          # dedicated hospital-based team + isolette
TIER_PEDS = "Peds-critical team"         # pediatric critical-care transport
TIER_ALS2 = "ALS2"                       # >=3 med admins or an ALS procedure (drips)
TIER_ALS = "ALS"                         # advanced life support
TIER_BLS = "BLS stretcher"               # basic, bedbound stable
TIER_NEMT = "Wheelchair-van/NEMT"        # non-emergency, ambulatory
TIER_BH = "Behavioral-ALS"              # low medical acuity, restraint/monitoring

_HIGH_ACUITY_TIERS = frozenset({TIER_CCT_SCT, TIER_NEONATAL, TIER_PEDS})
_MID_ACUITY_TIERS = frozenset({TIER_ALS2, TIER_ALS})
_LOW_ACUITY_TIERS = frozenset({TIER_BLS, TIER_NEMT, TIER_BH})


# ---------------------------------------------------------------------------
# ICD-10-CM validation (SOURCED, offline) against the vendored billability seed
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _valid_icd10() -> frozenset:
    """Frozenset of billable ICD-10-CM leaf codes (dot-stripped, upper-cased).

    Loaded once from the vendored FY2025/FY2026 validity seed. This is the
    offline source of truth: membership makes a registry code SOURCED, not
    asserted. The seed is the BILLABLE-LEAF set — bare 3-char category stems
    (e.g. ``A41`` / ``I21`` / ``J96``) that need further subclassification are
    absent, so the registry stores representative billable *leaves* only.

    Degrades gracefully: a missing/unreadable seed returns an empty set so a
    caller can still render the (unvalidated) taxonomy rather than crash.
    """
    codes: set = set()
    try:
        with _SEED.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                if str(row.get("billable", "1")).strip() == "1":
                    code = (row.get("code") or "").replace(".", "").strip().upper()
                    if code:
                        codes.add(code)
    except (OSError, csv.Error):
        return frozenset()
    return frozenset(codes)


def _norm(code: str) -> str:
    return code.replace(".", "").strip().upper()


# ---------------------------------------------------------------------------
# Growth model (ILLUSTRATIVE projection off the SOURCED demand_forecast model)
# ---------------------------------------------------------------------------

# Published US age-band 5-yr population CAGRs (Census projections magnitude) —
# the labelled fallback used when the demand_forecast model can't be imported
# (its package __init__ pulls in the deals corpus, which needs pandas and is
# absent in lightweight/offline environments). Kept in sync with
# demand_forecast._POP_GROWTH_BY_AGE so condition growth is REAL, not zero,
# everywhere. Basis ILLUSTRATIVE (Census-projection magnitude).
_POP_GROWTH_FALLBACK: Dict[str, Dict[str, float]] = {
    "0-17":  {"cagr_5yr": 0.002},
    "18-44": {"cagr_5yr": 0.008},
    "45-64": {"cagr_5yr": 0.012},
    "65-74": {"cagr_5yr": 0.032},
    "75-84": {"cagr_5yr": 0.048},
    "85+":   {"cagr_5yr": 0.045},
}


@lru_cache(maxsize=1)
def _pop_growth() -> Dict[str, Dict[str, float]]:
    """Age-band 5-yr population CAGRs from the real demand_forecast model, with a
    labelled published fallback.

    Read-only import at call time (never at module import). The demand_forecast
    module lives under a package whose ``__init__`` imports the deals corpus
    (pandas-dependent), so the import fails in offline/lightweight environments —
    previously that zeroed every condition's growth. We now fall back to the
    published Census age-band CAGRs so the demographic trend is real everywhere.
    """
    try:
        from rcm_mc.data_public.demand_forecast import _POP_GROWTH_BY_AGE
        if _POP_GROWTH_BY_AGE:
            return dict(_POP_GROWTH_BY_AGE)
    except Exception:  # noqa: BLE001
        pass
    return {k: dict(v) for k, v in _POP_GROWTH_FALLBACK.items()}


def compute_condition_cagr(age_skew: Tuple[Tuple[str, float], ...], horizon: int = 10) -> float:
    """Population-only demographic volume CAGR for a condition.

    ``age_skew`` is the fraction of the condition's cases in each age band
    (need not sum to exactly 1 — the ratio normalizes it). Holding age-specific
    incidence constant, each band's case count grows at that band's population
    CAGR; the condition's projected case count is the skew-weighted sum:

        V0 = Σ w_b ;  V1 = Σ w_b · (1 + cagr_b)**horizon ;  cagr = (V1/V0)**(1/horizon) − 1

    This isolates the pure demographic tailwind — the conditions that skew to
    the 75-84 / 85+ bands (hip fx, sepsis, stroke, heart failure) grow fastest.
    Basis SOURCED from the model; the projection is ILLUSTRATIVE.
    """
    bands = _pop_growth()
    v0 = 0.0
    v1 = 0.0
    for band, weight in age_skew:
        cagr_b = float(bands.get(band, {}).get("cagr_5yr", 0.0))
        v0 += weight
        v1 += weight * ((1.0 + cagr_b) ** horizon)
    if v0 <= 0:
        return 0.0
    return (v1 / v0) ** (1.0 / horizon) - 1.0


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NationalVolume:
    """A published national annual count with its provenance.

    ``source_label`` starts with a honesty tag (GOV / ACADEMIC / ILLUSTRATIVE).
    ``measure`` names exactly what is counted (inpatient stays vs incidence vs
    ED visits vs births vs post-acute cases) so pools are never silently
    conflated. ``value == 0`` means "not separately enumerated nationally" — the
    ``measure``/``note`` explain why (e.g. load-balancing has no defensible
    single count).
    """
    value: int
    year: int
    source_label: str
    measure: str
    note: str = ""


@dataclass(frozen=True)
class Growth:
    """Per-condition demographic growth outlook."""
    cagr: float
    drivers: str
    age_skew: Tuple[Tuple[str, float], ...]
    index_10yr: float
    basis: str = (
        "ILLUSTRATIVE · demand_forecast._POP_GROWTH_BY_AGE age-band population "
        "CAGRs weighted by the condition's age skew (incidence held constant)"
    )


@dataclass(frozen=True)
class Condition:
    """One acute clinical scenario = one IFT demand stream."""
    name: str
    family: str
    presenting: str
    transfer_type: str
    acuity: str
    transport_acuity: str
    origin_setting: str
    destination_capability: str          # authored clinical reference
    destination_setting: str             # post-acute supply key OR hub type
    icd10: Tuple[str, ...]               # billable ICD-10-CM leaves (SOURCED-validated)
    ms_drg: Tuple[str, ...]              # CMS MS-DRG Definitions Manual (reference)
    national_volume: NationalVolume
    growth: Growth
    pcs: Tuple[str, ...] = ()            # ICD-10-PCS (reference only, no offline validity set)
    time_window: str = ""


# ---------------------------------------------------------------------------
# Registry authoring helpers
# ---------------------------------------------------------------------------

def _growth(drivers: str, age_skew: Tuple[Tuple[str, float], ...]) -> Growth:
    cagr = compute_condition_cagr(age_skew)
    return Growth(
        cagr=round(cagr, 4),
        drivers=drivers,
        age_skew=age_skew,
        index_10yr=round((1.0 + cagr) ** 10, 3),
    )


# Age-skew shorthands (fraction of a condition's cases per band). Authored from
# published inpatient age distributions; the basis is ILLUSTRATIVE.
_SKEW_ELDERLY_CARDIAC = (("45-64", 0.25), ("65-74", 0.30), ("75-84", 0.28), ("85+", 0.17))
_SKEW_SHOCK = (("45-64", 0.15), ("65-74", 0.30), ("75-84", 0.35), ("85+", 0.20))
_SKEW_AORTA = (("45-64", 0.25), ("65-74", 0.30), ("75-84", 0.30), ("85+", 0.15))
_SKEW_STROKE = (("45-64", 0.15), ("65-74", 0.28), ("75-84", 0.35), ("85+", 0.22))
_SKEW_ICH = (("45-64", 0.20), ("65-74", 0.28), ("75-84", 0.32), ("85+", 0.20))
_SKEW_SEPSIS = (("18-44", 0.08), ("45-64", 0.20), ("65-74", 0.28), ("75-84", 0.28), ("85+", 0.16))
_SKEW_RESP = (("45-64", 0.22), ("65-74", 0.30), ("75-84", 0.30), ("85+", 0.18))
_SKEW_PNEUMONIA = (("0-17", 0.05), ("18-44", 0.10), ("45-64", 0.20), ("65-74", 0.25), ("75-84", 0.25), ("85+", 0.15))
_SKEW_COPD = (("45-64", 0.30), ("65-74", 0.35), ("75-84", 0.25), ("85+", 0.10))
_SKEW_GIB = (("45-64", 0.25), ("65-74", 0.28), ("75-84", 0.28), ("85+", 0.19))
_SKEW_TRAUMA = (("0-17", 0.08), ("18-44", 0.30), ("45-64", 0.22), ("65-74", 0.15), ("75-84", 0.15), ("85+", 0.10))
_SKEW_BH = (("0-17", 0.12), ("18-44", 0.45), ("45-64", 0.28), ("65-74", 0.10), ("75-84", 0.03), ("85+", 0.02))
_SKEW_PEDS = (("0-17", 1.0),)
_SKEW_NEONATAL = (("0-17", 1.0),)
_SKEW_OB = (("18-44", 0.97), ("45-64", 0.03))
_SKEW_SURGCOMP = (("45-64", 0.30), ("65-74", 0.30), ("75-84", 0.25), ("85+", 0.15))
_SKEW_HIPFX = (("45-64", 0.08), ("65-74", 0.15), ("75-84", 0.37), ("85+", 0.40))
_SKEW_DKA = (("18-44", 0.40), ("45-64", 0.30), ("65-74", 0.18), ("75-84", 0.09), ("85+", 0.03))
_SKEW_SEIZURE = (("0-17", 0.15), ("18-44", 0.35), ("45-64", 0.25), ("65-74", 0.15), ("75-84", 0.07), ("85+", 0.03))
_SKEW_DEBILITY = (("45-64", 0.15), ("65-74", 0.25), ("75-84", 0.32), ("85+", 0.28))
_SKEW_MEDSURG = (("18-44", 0.05), ("45-64", 0.20), ("65-74", 0.28), ("75-84", 0.28), ("85+", 0.19))
_SKEW_RESP_RECOVERY = (("45-64", 0.20), ("65-74", 0.30), ("75-84", 0.28), ("85+", 0.22))
_SKEW_HOSPICE = (("65-74", 0.20), ("75-84", 0.35), ("85+", 0.45))
_SKEW_ACUTE_BLEND = (("18-44", 0.10), ("45-64", 0.20), ("65-74", 0.28), ("75-84", 0.25), ("85+", 0.17))


# ---------------------------------------------------------------------------
# The registry — ALL acute scenarios (families A / B / C)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _registry() -> Tuple[Condition, ...]:
    C = Condition
    conds: List[Condition] = [
        # ================= A. ESCALATION (transfer OUT / up) =================
        C(
            name="Acute MI / chest pain",
            family=FAMILY_ESCALATION, presenting="Ischemic chest pain, ST-elevation or positive troponin at a non-PCI hospital",
            transfer_type=TRANSFER_UP, acuity="critical", transport_acuity=TIER_CCT_SCT,
            origin_setting="Community/CAH ED",
            destination_capability="24/7 PCI/cath lab + CICU (cardiogenic-shock/ECMO for shock)",
            destination_setting="Tertiary cardiac center",
            icd10=("I219", "I2102", "I21A1", "I214"),
            ms_drg=("280-282 (AMI, discharged alive)", "283-285 (AMI, expired)", "246-251 (PCI +/- stent)"),
            pcs=("02703DZ", "02703ZZ"),
            time_window="Door-to-balloon <=90 min; FMC-to-device <=120 min for transfers",
            national_volume=NationalVolume(658600, 2018, "GOV · AHRQ HCUP SB#277 (2018 NIS)",
                                           "acute-MI inpatient stays (principal dx)",
                                           "CDC/AHA ~805,000 MI events/yr"),
            growth=_growth("65-84 skew (75-84 +4.8%, 65-74 +3.2%/yr)", _SKEW_ELDERLY_CARDIAC),
        ),
        C(
            name="Cardiogenic shock / complex cardiac",
            family=FAMILY_ESCALATION, presenting="Pump failure / refractory shock exceeding community CICU capability",
            transfer_type=TRANSFER_UP, acuity="critical", transport_acuity=TIER_CCT_SCT,
            origin_setting="Community hospital ED/ICU",
            destination_capability="Shock team, IABP / Impella / VA-ECMO, advanced heart failure",
            destination_setting="Quaternary cardiac center",
            icd10=("R570", "I5021", "I219"),
            ms_drg=("291-293 (heart failure & shock)", "216-221 (cardiac valve/other cardiothoracic)"),
            time_window="Time-critical mechanical-support cannulation",
            national_volume=NationalVolume(1135900, 2018, "GOV · AHRQ HCUP SB#277 (2018 NIS)",
                                           "heart-failure inpatient stays (parent pool)",
                                           "cardiogenic-shock/complex-cardiac is the high-acuity transfer subset; HF is the #2 US inpatient condition"),
            growth=_growth("65-84/85+ skew", _SKEW_SHOCK),
        ),
        C(
            name="Aortic emergency (dissection / rupture)",
            family=FAMILY_ESCALATION, presenting="Tearing chest/back pain, dissection or rupture on CT at a hospital without CT/vascular surgery",
            transfer_type=TRANSFER_UP, acuity="critical", transport_acuity=TIER_CCT_SCT,
            origin_setting="Community/CAH ED",
            destination_capability="Cardiothoracic/vascular surgery + hybrid OR",
            destination_setting="Tertiary aortic center",
            icd10=("I71010", "I7102", "I7113"),
            ms_drg=("237-238 (major cardiovascular procedures)",),
            time_window="Type-A dissection: emergent operative repair",
            national_volume=NationalVolume(13000, 2020, "ACADEMIC · epidemiologic incidence estimate",
                                           "acute aortic dissection cases/yr (modeled from ~4/100,000)",
                                           "low-volume, highest-acuity escalation"),
            growth=_growth("45-84 skew", _SKEW_AORTA),
        ),
        C(
            name="Ischemic stroke",
            family=FAMILY_ESCALATION, presenting="Sudden focal deficit / high NIHSS within the thrombolytic/thrombectomy window",
            transfer_type=TRANSFER_UP, acuity="emergent", transport_acuity=TIER_CCT_SCT,
            origin_setting="Primary/non-stroke hospital ED",
            destination_capability="Thrombectomy-capable Comprehensive Stroke Center + neuro-ICU",
            destination_setting="Comprehensive Stroke Center",
            icd10=("I639", "I6350", "I63512", "I63411"),
            ms_drg=("061-063 (acute ischemic stroke w/ thrombolytic)", "064-066 (intracranial hemorrhage or cerebral infarction, medical)", "023-024 (endovascular thrombectomy, no hemorrhage PDX)"),
            pcs=("03CG3ZZ", "03CH3ZZ"),
            time_window="Door-to-needle <=60 min; thrombectomy in the DAWN/DEFUSE-3 window (<=24h LKW selected)",
            national_volume=NationalVolume(533400, 2018, "GOV · AHRQ HCUP SB#277 (2018 NIS)",
                                           "cerebral-infarction inpatient stays",
                                           "CDC >795,000 strokes/yr, ~87% ischemic (~690k)"),
            growth=_growth("75-84 skew (+4.8%/yr) dominant", _SKEW_STROKE),
        ),
        C(
            name="Hemorrhagic stroke (ICH / SAH)",
            family=FAMILY_ESCALATION, presenting="Thunderclap headache / depressed GCS, hemorrhage on CT at a hospital without neurosurgery",
            transfer_type=TRANSFER_UP, acuity="critical", transport_acuity=TIER_CCT_SCT,
            origin_setting="Community/CAH ED",
            destination_capability="Neurosurgery + neuro-ICU (clip/coil, EVD, hematoma evacuation)",
            destination_setting="Comprehensive Stroke Center w/ neurosurgery",
            icd10=("I619", "I609"),
            ms_drg=("020-022 (intracranial vascular procedures w/ hemorrhage PDX)", "025-027 (craniotomy w/o major device)", "064-066 (intracranial hemorrhage, medical)"),
            time_window="Aneurysm securing within 24-72h to prevent rebleed",
            national_volume=NationalVolume(110000, 2022, "GOV · CDC-derived (ICH+SAH ~13% of >795,000 strokes)",
                                           "hemorrhagic-stroke cases/yr",
                                           "ICH ~80k + SAH ~30k"),
            growth=_growth("65-84 skew", _SKEW_ICH),
        ),
        C(
            name="Severe sepsis / septic shock",
            family=FAMILY_ESCALATION, presenting="Infection + organ dysfunction/hypotension exceeding a community ICU",
            transfer_type=TRANSFER_UP, acuity="critical", transport_acuity=TIER_CCT_SCT,
            origin_setting="Community/CAH ED/ICU",
            destination_capability="MICU with vasopressors + source control (IR drainage / surgery), CRRT",
            destination_setting="Tertiary ICU",
            icd10=("A419", "R6520", "R6521"),
            ms_drg=("870 (septicemia/severe sepsis w/ MV>96h)", "871-872 (septicemia w/wo MCC)"),
            time_window="Surviving Sepsis Hour-1 bundle (lactate, cultures, abx, fluids, pressors)",
            national_volume=NationalVolume(1700000, 2023, "GOV · CDC Sepsis",
                                           "adults developing sepsis/yr",
                                           "AHRQ HCUP: septicemia is the #1 US inpatient condition (2,218,800 stays, $41.5B, 2018)"),
            growth=_growth("65-84/85+ skew + immunosenescence", _SKEW_SEPSIS),
        ),
        C(
            name="Acute respiratory failure / ARDS",
            family=FAMILY_ESCALATION, presenting="Hypoxemic/hypercapnic failure, intubation beyond origin vent/ICU capacity",
            transfer_type=TRANSFER_UP, acuity="critical", transport_acuity=TIER_CCT_SCT,
            origin_setting="Community hospital ED/ICU",
            destination_capability="Ventilator-capable ICU; refractory ARDS -> VV-ECMO center",
            destination_setting="Tertiary / ECMO center",
            icd10=("J9600", "J9601", "J9621", "J80"),
            ms_drg=("189 (pulmonary edema & respiratory failure)", "207-208 (respiratory dx w/ vent 96+/<=96h)"),
            pcs=("5A1955Z",),
            time_window="Time-critical ECMO cannulation (center-limited)",
            national_volume=NationalVolume(1917910, 2009, "ACADEMIC · Stefan et al., NIS 2001-2009",
                                           "hospitalizations with acute respiratory failure dx",
                                           "rose from ~1,007,549 (2001); also in HCUP SB#277 top-20"),
            growth=_growth("65-84 skew", _SKEW_RESP),
        ),
        C(
            name="Pneumonia (escalating)",
            family=FAMILY_ESCALATION, presenting="Severe CAP with rising O2/vasopressor needs beyond origin capability",
            transfer_type=TRANSFER_UP, acuity="emergent", transport_acuity=TIER_ALS,
            origin_setting="Community/CAH ED",
            destination_capability="ICU / higher level of care",
            destination_setting="Tertiary ICU",
            icd10=("J189", "J13", "J15212", "J159"),
            ms_drg=("193-195 (simple pneumonia & pleurisy w/wo MCC/CC)",),
            national_volume=NationalVolume(740700, 2018, "GOV · AHRQ HCUP SB#277 (2018 NIS)",
                                           "pneumonia inpatient stays",
                                           "CDC ~1.4M pneumonia ED visits/yr"),
            growth=_growth("bimodal but 65+ dominant", _SKEW_PNEUMONIA),
        ),
        C(
            name="COPD exacerbation",
            family=FAMILY_ESCALATION, presenting="Acute exacerbation with NIV/vent need beyond origin capacity",
            transfer_type=TRANSFER_UP, acuity="urgent", transport_acuity=TIER_ALS,
            origin_setting="Community/CAH ED",
            destination_capability="ICU / NIV / ventilator",
            destination_setting="Tertiary ICU",
            icd10=("J440", "J441", "J449"),
            ms_drg=("190-192 (COPD w/wo MCC/CC)",),
            national_volume=NationalVolume(569600, 2018, "GOV · AHRQ HCUP SB#277 (2018 NIS)",
                                           "COPD/bronchiectasis inpatient stays",
                                           "CDC: COPD ~6th leading cause of death"),
            growth=_growth("45-74 peak (lower tailwind)", _SKEW_COPD),
        ),
        C(
            name="GI hemorrhage",
            family=FAMILY_ESCALATION, presenting="Hematemesis/melena/hematochezia needing urgent endoscopy/IR/surgery",
            transfer_type=TRANSFER_UP, acuity="emergent", transport_acuity=TIER_ALS,
            origin_setting="Community/CAH ED",
            destination_capability="Therapeutic endoscopy (GI on call), IR embolization, surgical backup, ICU",
            destination_setting="Tertiary center w/ endoscopy+IR",
            icd10=("K922", "K254", "K264", "I8501"),
            ms_drg=("377-379 (GI hemorrhage w/wo MCC/CC)",),
            pcs=("0DJ08ZZ",),
            time_window="Active bleeding + instability; variceal bleeds time-critical",
            national_volume=NationalVolume(400000, 2020, "ACADEMIC · StatPearls / GI-bleed literature",
                                           "GI-bleed hospital admissions/yr",
                                           ">300k UGIB + lower GIB"),
            growth=_growth("45-84 skew (anticoagulants, diverticulosis)", _SKEW_GIB),
        ),
        C(
            name="Major trauma / polytrauma",
            family=FAMILY_ESCALATION, presenting="High-energy mechanism / severe injury at a non-trauma or lower-level center",
            transfer_type=TRANSFER_UP, acuity="critical", transport_acuity=TIER_CCT_SCT,
            origin_setting="Non-trauma / lower-level ED",
            destination_capability="Level I/II Trauma Center (trauma surgery, neurosurgery, OR, blood bank, IR)",
            destination_setting="Level I/II Trauma Center",
            icd10=("S065X0A", "S270XXA", "S72001A", "T07XXXA"),
            ms_drg=("955-959 (O.R. proc for multiple significant trauma)", "963-965 (other multiple significant trauma)", "082-087 (traumatic stupor & coma)"),
            time_window="Golden hour — definitive hemorrhage/surgical control within ~60 min",
            national_volume=NationalVolume(223050, 2018, "GOV · CDC/MMWR (NIS 2018)",
                                           "nonfatal TBI-related hospitalizations",
                                           "CDC WISQARS ~2.8M trauma admissions/yr; transfer subset is the severe fraction"),
            growth=_growth("bimodal (young MVC + fast-growing elderly falls)", _SKEW_TRAUMA),
        ),
        C(
            name="Behavioral-health crisis",
            family=FAMILY_ESCALATION, presenting="Acute psychosis / suicidality / agitation boarding in a medical ED with no psych bed",
            transfer_type=TRANSFER_UP, acuity="emergent", transport_acuity=TIER_BH,
            origin_setting="Medical ED (boarding)",
            destination_capability="Inpatient psychiatric unit / dedicated psych hospital (post medical clearance)",
            destination_setting="Psychiatric facility",
            icd10=("F29", "F319", "F329", "F10239"),
            ms_drg=("885 (psychoses)", "880-884, 886-887 (other mental-health DRGs)"),
            national_volume=NationalVolume(6000000, 2021, "GOV · CDC/SAMHSA ED utilization",
                                           "mental-health-related ED visits/yr",
                                           "~1 in 8 ED visits MH/SUD; DRG 885 among the highest-volume DRGs"),
            growth=_growth("18-44 skew (low demographic tailwind, high boarding intensity)", _SKEW_BH),
        ),
        C(
            name="Pediatric acute deterioration",
            family=FAMILY_ESCALATION, presenting="Critically ill/injured child (status asthmaticus, DKA, sepsis, seizure) at a general ED",
            transfer_type=TRANSFER_UP, acuity="emergent", transport_acuity=TIER_PEDS,
            origin_setting="General ED (no peds critical care)",
            destination_capability="PICU (pediatric intensivists, peds anesthesia/surgery), pediatric trauma center",
            destination_setting="Children's hospital / PICU",
            icd10=("J210", "J050", "R569", "E1010"),
            ms_drg=("pediatric medical DRGs by principal dx (e.g. 137-139, 871-872)",),
            national_volume=NationalVolume(200000, 2020, "ACADEMIC · PICU admission estimate",
                                           "PICU admissions/yr (est)",
                                           "concentrated into referral children's hospitals"),
            growth=_growth("0-17 band (flattest, +0.2%/yr)", _SKEW_PEDS),
        ),
        C(
            name="Neonatal deterioration",
            family=FAMILY_ESCALATION, presenting="Preterm / respiratory distress / sick newborn at a Level I/II nursery",
            transfer_type=TRANSFER_UP, acuity="critical", transport_acuity=TIER_NEONATAL,
            origin_setting="Level I/II nursery",
            destination_capability="NICU Level III/IV (ventilation, surgery, subspecialty)",
            destination_setting="Regional NICU III/IV",
            icd10=("P0730", "P220", "P369"),
            ms_drg=("789-795 (neonates; 789 = 'died or transferred to another acute care facility')",),
            national_volume=NationalVolume(380000, 2022, "GOV · CDC/NCHS Births 2022",
                                           "preterm births/yr (10.38% of 3,667,758)",
                                           "NICU admissions ~10-15% of births; outborn/escalated are the transfer subset"),
            growth=_growth("0-17 band (flat); demand acuity- not population-driven", _SKEW_NEONATAL),
        ),
        C(
            name="High-risk pregnancy / obstetric emergency",
            family=FAMILY_ESCALATION, presenting="Severe pre-eclampsia/eclampsia, antepartum hemorrhage, preterm labor at a hospital without high-level OB/NICU",
            transfer_type=TRANSFER_UP, acuity="emergent", transport_acuity=TIER_CCT_SCT,
            origin_setting="Community hospital OB",
            destination_capability="Maternal-Fetal Medicine, Level III/IV maternal care + co-located NICU III/IV",
            destination_setting="MFM / Level III-IV OB",
            icd10=("O1490", "O721", "O6014X0"),
            ms_drg=("783-788 (cesarean section)", "817-819 (other antepartum dx w/ O.R. procedure)", "831-834 (other antepartum dx w/o O.R. procedure)"),
            time_window="Eclampsia/hemorrhage time-critical; prefer in-utero maternal transport before delivery",
            national_volume=NationalVolume(3667758, 2022, "GOV · CDC/NCHS Births 2022",
                                           "US births/yr",
                                           "~8-10% high-risk; 32.1% cesarean (~1.18M)"),
            growth=_growth("18-44 band (modest); rising maternal age/morbidity", _SKEW_OB),
        ),
        C(
            name="Complex surgical complication",
            family=FAMILY_ESCALATION, presenting="Post-op hemorrhage / anastomotic leak / sepsis / dehiscence beyond origin subspecialty surgery",
            transfer_type=TRANSFER_UP, acuity="urgent", transport_acuity=TIER_CCT_SCT,
            origin_setting="Community hospital post-op",
            destination_capability="Surgical ICU + subspecialty surgery (vascular, colorectal, CT, transplant) + IR",
            destination_setting="Tertiary surgical center",
            icd10=("T8140XA", "T8131XA", "K651"),
            ms_drg=("853-858 (postoperative & post-traumatic infection w/ O.R. proc)", "981-989 (O.R. proc unrelated to principal dx)"),
            national_volume=NationalVolume(0, 2018, "ACADEMIC · not separately enumerated nationally",
                                           "post-procedural complication cohort",
                                           "steady inter-hospital referral stream that scales with surgical volume"),
            growth=_growth("aging surgical population (45-84)", _SKEW_SURGCOMP),
        ),
        C(
            name="Hip fracture (acute ortho-trauma)",
            family=FAMILY_ESCALATION, presenting="Older-adult ground-level fall with femoral-neck/pertrochanteric fracture needing operative repair",
            transfer_type=TRANSFER_UP, acuity="urgent", transport_acuity=TIER_ALS,
            origin_setting="Community/CAH ED",
            destination_capability="Ortho-trauma OR (ORIF / arthroplasty), geriatric co-management",
            destination_setting="Trauma / ortho center",
            icd10=("S72001A", "S72011A", "S72141A"),
            ms_drg=("480-482 (hip & femur procedures exc major joint)", "533-535 (fractures of femur)"),
            pcs=("0QS", "0SR"),
            national_volume=NationalVolume(319000, 2022, "GOV · CDC older-adult falls",
                                           "hip-fracture hospitalizations/yr (age 65+)",
                                           "~88% fall-caused"),
            growth=_growth("85+ skew (highest tailwind, +4.5%/yr)", _SKEW_HIPFX),
        ),
        C(
            name="DKA / endocrine crisis",
            family=FAMILY_ESCALATION, presenting="Diabetic ketoacidosis / HHS needing ICU insulin infusion beyond origin capability",
            transfer_type=TRANSFER_UP, acuity="emergent", transport_acuity=TIER_ALS2,
            origin_setting="Community/CAH ED",
            destination_capability="ICU (insulin drip, electrolyte management)",
            destination_setting="Tertiary ICU",
            icd10=("E1010", "E1110", "E871"),
            ms_drg=("637-639 (diabetes w/wo MCC/CC)",),
            national_volume=NationalVolume(230000, 2020, "GOV · CDC diabetes surveillance",
                                           "DKA hospitalizations/yr",
                                           ""),
            growth=_growth("18-64 skew (broad age)", _SKEW_DKA),
        ),
        C(
            name="Status epilepticus",
            family=FAMILY_ESCALATION, presenting="Refractory seizure needing neuro-ICU + continuous EEG beyond origin capability",
            transfer_type=TRANSFER_UP, acuity="emergent", transport_acuity=TIER_CCT_SCT,
            origin_setting="Community/CAH ED",
            destination_capability="Neuro-ICU + continuous EEG",
            destination_setting="Tertiary neuro center",
            icd10=("G40911", "G40901", "G40919"),
            ms_drg=("100-101 (seizures w/wo MCC)",),
            national_volume=NationalVolume(150000, 2020, "ACADEMIC · status epilepticus incidence estimate",
                                           "status epilepticus episodes/yr (est)",
                                           ""),
            growth=_growth("mixed-age (bimodal)", _SKEW_SEIZURE),
        ),

        # ================ B. STEP-DOWN / RECOVERY (down) ====================
        C(
            name="Post-ventilator recovery -> LTACH",
            family=FAMILY_STEPDOWN, presenting="Prolonged mechanical ventilation / failure to wean past the DRG-efficient point",
            transfer_type=TRANSFER_DOWN, acuity="urgent", transport_acuity=TIER_CCT_SCT,
            origin_setting="Acute ICU",
            destination_capability="LTACH vent-weaning/pulmonary program (>=96h vent auto-qualifies full site-neutral-exempt LTCH rate)",
            destination_setting="LTACH",
            icd10=("Z9911", "J9600", "J9611"),
            ms_drg=("207 (respiratory dx w/ vent >96h)", "208 (<=96h)", "189 (pulmonary edema & resp failure)"),
            time_window="Frees weeks of ICU capacity (LTACH >25-day ALOS)",
            national_volume=NationalVolume(90000, 2022, "GOV · MedPAC LTCH",
                                           "Medicare LTCH cases/yr (~90-100k across ~320 LTCHs)",
                                           "site-neutral rule + moratorium cap realized volume flat-to-down"),
            growth=_growth("65-84 skew (offset by LTCH supply cap)", _SKEW_RESP),
        ),
        C(
            name="Stable sepsis recovery -> LTACH/SNF",
            family=FAMILY_STEPDOWN, presenting="Survived septic shock, needs prolonged antibiotics / recovery / rehab-to-tolerate",
            transfer_type=TRANSFER_DOWN, acuity="stable", transport_acuity=TIER_BLS,
            origin_setting="Acute ICU / med-surg",
            destination_capability="LTACH (if ex-ICU >=3d or vent >=96h) else SNF for lower-intensity recovery",
            destination_setting="LTACH",
            icd10=("A419", "R6521"),
            ms_drg=("870 (severe sepsis w/ MV>96h -> LTACH-qualifying)", "871-872 (septicemia w/wo MCC)"),
            national_volume=NationalVolume(1700000, 2023, "GOV · CDC Sepsis",
                                           "adult sepsis cases/yr (survivor post-acute pool)",
                                           "septicemia is the #1 and costliest inpatient condition"),
            growth=_growth("65-84/85+ skew", _SKEW_SEPSIS),
        ),
        C(
            name="Post-stroke recovery -> IRF",
            family=FAMILY_STEPDOWN, presenting="Ischemic/ICH survivor needing intensive inpatient rehab (3-hour therapy tolerance)",
            transfer_type=TRANSFER_DOWN, acuity="stable", transport_acuity=TIER_BLS,
            origin_setting="Acute stroke unit",
            destination_capability="IRF — stroke is the #1 named 60%-rule qualifying condition; routes to IRF over SNF when 3h/day tolerated",
            destination_setting="IRF",
            icd10=("I69351", "I69320", "Z5189"),
            ms_drg=("945-946 (rehabilitation)",),
            national_volume=NationalVolume(383000, 2022, "GOV · MedPAC IRF",
                                           "IRF stays/yr (stroke the leading CMG)",
                                           "~1,180 Medicare-certified IRFs"),
            growth=_growth("75-84 skew", _SKEW_STROKE),
        ),
        C(
            name="Cardiac recovery -> IRF/SNF",
            family=FAMILY_STEPDOWN, presenting="Post-AMI/CABG/valve or decompensated-HF recovery, deconditioned",
            transfer_type=TRANSFER_DOWN, acuity="stable", transport_acuity=TIER_BLS,
            origin_setting="Acute cardiac unit",
            destination_capability="IRF for intensive cardiac rehab (complex/deconditioned); SNF for lower-intensity reconditioning",
            destination_setting="IRF",
            icd10=("I509", "Z5189"),
            ms_drg=("280-282 (AMI disch alive)", "291-293 (HF & shock)", "231-236 (CABG)"),
            national_volume=NationalVolume(1135900, 2018, "GOV · AHRQ HCUP SB#277 (2018 NIS)",
                                           "heart-failure inpatient stays (post-acute pool)",
                                           "HF is the #2 US inpatient condition"),
            growth=_growth("65-84 skew", _SKEW_ELDERLY_CARDIAC),
        ),
        C(
            name="Long ICU stay / debility -> LTACH",
            family=FAMILY_STEPDOWN, presenting="Extended acute course, complex wounds, multi-organ recovery not yet SNF-ready",
            transfer_type=TRANSFER_DOWN, acuity="urgent", transport_acuity=TIER_CCT_SCT,
            origin_setting="Acute ICU",
            destination_capability="LTACH (>=3-ICU-day preceding stay qualifies the full LTCH rate)",
            destination_setting="LTACH",
            icd10=("R296", "M6281", "E43"),
            ms_drg=("high-weight surgical/medical MCC DRGs -> MS-LTC-DRG",),
            time_window="Longest acute stays; LTACH >25-day ALOS purpose-built to absorb them",
            national_volume=NationalVolume(90000, 2022, "GOV · MedPAC LTCH",
                                           "Medicare LTCH cases/yr (complex/debility remainder)",
                                           "same site-neutral + moratorium supply cap"),
            growth=_growth("85+ skew (offset by LTCH supply cap)", _SKEW_DEBILITY),
        ),
        C(
            name="Med-surg discharge -> SNF/home health",
            family=FAMILY_STEPDOWN, presenting="General post-acute recovery not meeting IRF intensity / LTACH acuity (the highest-volume down bucket)",
            transfer_type=TRANSFER_DOWN, acuity="stable", transport_acuity=TIER_NEMT,
            origin_setting="Acute med-surg floor",
            destination_capability="SNF (if >=3-day qualifying inpatient stay) for skilled nursing/rehab; home health for homebound-stable",
            destination_setting="SNF",
            icd10=("Z4789", "Z5189"),
            ms_drg=("full med-surg spectrum",),
            national_volume=NationalVolume(1800000, 2022, "GOV · MedPAC SNF",
                                           "Medicare-covered SNF stays/yr (~1.3M FFS beneficiaries)",
                                           "~14,700 SNFs; TEAM 3-day-rule waiver modestly expands SNF-routed volume"),
            growth=_growth("65-84/85+ skew", _SKEW_MEDSURG),
        ),
        C(
            name="Pneumonia / COPD recovery -> SNF/home health",
            family=FAMILY_STEPDOWN, presenting="Resolved acute respiratory infection/exacerbation, deconditioned, needs O2 titration / reconditioning",
            transfer_type=TRANSFER_DOWN, acuity="stable", transport_acuity=TIER_BLS,
            origin_setting="Acute med-surg floor",
            destination_capability="SNF for skilled reconditioning/O2 management, or home health for homebound-stable",
            destination_setting="SNF",
            icd10=("J189", "J441", "Z5189"),
            ms_drg=("193-195 (pneumonia)", "190-192 (COPD)"),
            national_volume=NationalVolume(740700, 2018, "GOV · AHRQ HCUP SB#277 (2018 NIS)",
                                           "pneumonia inpatient stays (post-acute pool)",
                                           "COPD ~700k+ stays/yr"),
            growth=_growth("65-84 skew", _SKEW_RESP_RECOVERY),
        ),
        C(
            name="Hip-fracture / post-surgical rehab -> IRF/SNF",
            family=FAMILY_STEPDOWN, presenting="Post-operative fracture repair or major-joint procedure needing rehab (fastest-growing recovery cohort)",
            transfer_type=TRANSFER_DOWN, acuity="stable", transport_acuity=TIER_BLS,
            origin_setting="Acute ortho floor",
            destination_capability="IRF — hip fracture is a named 60%-rule condition; joint replacement qualifies if bilateral/BMI>=50/age>=85; else SNF",
            destination_setting="IRF",
            icd10=("S72001D", "Z471"),
            ms_drg=("480-482 (hip & femur procedures) -> 945-946 (rehabilitation)",),
            national_volume=NationalVolume(319000, 2022, "GOV · CDC older-adult falls",
                                           "hip-fracture hospitalizations/yr (age 65+)",
                                           "TEAM 3-day-rule waiver covers surgical hip/femur + joint-replacement episodes"),
            growth=_growth("85+ skew (highest recovery-cohort tailwind)", _SKEW_HIPFX),
        ),
        C(
            name="End-stage / comfort transition -> hospice",
            family=FAMILY_STEPDOWN, presenting="Goals-of-care transition to comfort-focused care (inpatient or home hospice)",
            transfer_type=TRANSFER_DOWN, acuity="stable", transport_acuity=TIER_BLS,
            origin_setting="Acute floor / ICU",
            destination_capability="Hospice (inpatient unit or home hospice)",
            destination_setting="Hospice",
            icd10=("Z515",),
            ms_drg=("varies by principal dx",),
            national_volume=NationalVolume(1700000, 2022, "GOV · CMS/MedPAC hospice",
                                           "Medicare hospice enrollees/yr",
                                           ""),
            growth=_growth("85+ skew", _SKEW_HOSPICE),
        ),

        # =========== C. DIRECT ADMITS + SYSTEM LOAD-BALANCING (lateral) ===========
        C(
            name="Physician-to-physician direct admit",
            family=FAMILY_LOADBALANCE, presenting="PCP/specialist/SNF calls a transfer center; patient goes straight to the right floor/ICU bed, bypassing the ED",
            transfer_type=TRANSFER_LATERAL, acuity="urgent", transport_acuity=TIER_ALS,
            origin_setting="Community / clinic / SNF",
            destination_capability="Correct subspecialty service line or ICU at the receiving hub ('right facility first time')",
            destination_setting="Right-capability facility/service",
            icd10=(),  # condition-agnostic: routed by UB-04 point-of-origin (code 1), not a dx
            ms_drg=("whatever the admitting condition is (e.g. 291 HF, 690 kidney/UTI, 871 sepsis)",),
            national_volume=NationalVolume(0, 2019, "ILLUSTRATIVE · non-ED share of ~33,700,000 inpatient stays (AHRQ HCUP NIS 2019)",
                                           "direct-admit share (not separately counted)",
                                           "no clean national direct-admit count; each is a scheduled/urgent ground-IFT leg"),
            growth=_growth("acute-transfer blended cohort (~70% 65+)", _SKEW_ACUTE_BLEND),
        ),
        C(
            name="ED interfacility up-transfer to acute care",
            family=FAMILY_LOADBALANCE, presenting="Community ED stabilizes and ships to a tertiary/quaternary center for definitive care",
            transfer_type=TRANSFER_UP, acuity="emergent", transport_acuity=TIER_CCT_SCT,
            origin_setting="Community ED",
            destination_capability="PCI cath lab / Comprehensive Stroke Center / Level I-II Trauma / MICU",
            destination_setting="Tertiary/quaternary hub",
            icd10=("I219", "A419", "I639"),  # representative index dx; volume is the aggregate flow
            ms_drg=("follows the definitive dx",),
            national_volume=NationalVolume(1900000, 2009, "GOV · AHRQ HCUP SB#155 (1.5% x 128,885,040 ED encounters)",
                                           "ED encounters transferred to another short-term acute hospital/yr",
                                           "Kindermann 2015 Acad Emerg Med; critical-procedure IFTs are increasing"),
            growth=_growth("acute-transfer blended cohort", _SKEW_ACUTE_BLEND),
        ),
        C(
            name="Inter-hospital ICU/bed load-balancing",
            family=FAMILY_LOADBALANCE, presenting="Transfer center decompresses a full hub / boarding ED by moving patients to a same-system community bed",
            transfer_type=TRANSFER_LATERAL, acuity="emergent", transport_acuity=TIER_ALS,
            origin_setting="Full quaternary hub / boarding ED",
            destination_capability="Lower-acuity same-IDN facility that can safely hold the patient",
            destination_setting="Same-system community hospital",
            icd10=("A419", "J189", "J9600", "N179"),  # empirical load-balance mix; census is the driver
            ms_drg=("least specific — census-driven (empirically 870-872 sepsis ~15%, 193-195 pneumonia ~8%, 189 resp ~5%)",),
            national_volume=NationalVolume(0, 2024, "ILLUSTRATIVE · anchored to the HHS/HCRIS occupancy signal",
                                           "load-balancing transfers (no defensible single national count)",
                                           "Intermountain diverted >5,100 quaternary bed-days over 4yr; 3-4 patients/hospital/day"),
            growth=_growth("fastest-growing leg — command-center adoption + structural ED-boarding crisis", _SKEW_ACUTE_BLEND),
        ),
        C(
            name="Repatriation / back-transfer",
            family=FAMILY_LOADBALANCE, presenting="Stabilized patient sent back to the origin community hospital to free the tertiary bed (the return leg)",
            transfer_type=TRANSFER_LATERAL, acuity="stable", transport_acuity=TIER_BLS,
            origin_setting="Tertiary/quaternary hub",
            destination_capability="Origin community hospital or a step-down/med-surg bed",
            destination_setting="Origin community hospital",
            icd10=(),  # post-acute-stable version of the index dx
            ms_drg=("post-acute-stable version of the index dx",),
            national_volume=NationalVolume(0, 2024, "ILLUSTRATIVE · mirrors each up-transfer",
                                           "back-transfers (~1:1 with escalations)",
                                           "roughly doubles the ground-IFT mission count per escalation episode"),
            growth=_growth("sticky — tracks up-transfer volume 1:1, rises with IDN integration", _SKEW_ACUTE_BLEND),
        ),
    ]
    return tuple(conds)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def all_conditions() -> List[Condition]:
    """The full acute-transfer taxonomy (families A / B / C), ~32 conditions."""
    return list(_registry())


def get_condition(name: str) -> Optional[Condition]:
    for c in _registry():
        if c.name == name:
            return c
    return None


def transfer_matrix() -> List[Dict]:
    """Scenario x destination grid — one row per condition (the cases->destination view)."""
    rows: List[Dict] = []
    for c in _registry():
        rows.append({
            "condition": c.name,
            "family": c.family,
            "presenting": c.presenting,
            "transfer_type": c.transfer_type,
            "acuity": c.acuity,
            "transport_acuity": c.transport_acuity,
            "origin_setting": c.origin_setting,
            "destination_capability": c.destination_capability,
            "destination_setting": c.destination_setting,
            "time_window": c.time_window,
            "national_volume": c.national_volume.value,
            "volume_measure": c.national_volume.measure,
            "volume_label": c.national_volume.source_label,
            "cagr": c.growth.cagr,
            "growth_label": c.growth.basis,
        })
    return rows


def growth_ranked() -> List[Condition]:
    """Conditions sorted by projected demographic volume CAGR, fastest first.

    The 75-84 / 85+ conditions (hip fx, comfort/hospice, sepsis, stroke, HF)
    top the list — the thesis mechanic that the fastest-growing IFT demand is
    the fastest-aging clinical cohort.
    """
    return sorted(_registry(), key=lambda c: c.growth.cagr, reverse=True)


# ---------------------------------------------------------------------------
# Year-over-year demand projection — per condition and in aggregate
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class YoYPoint:
    year: int
    volume: int
    yoy_growth_pct: float        # vs the prior year (= the CAGR for a geometric run)
    added_cases: int             # absolute case adds vs the prior year


@dataclass(frozen=True)
class ConditionYoY:
    name: str
    family: str
    transfer_type: str
    transport_acuity: str
    measure: str
    base_year: int
    base_volume: int
    cagr: float
    points: Tuple[YoYPoint, ...]
    end_volume: int
    added_cases: int             # end − base over the horizon
    basis: str


def condition_yoy_projection(horizon: int = 5) -> Tuple[ConditionYoY, ...]:
    """Per-condition YoY case trajectory: each condition's published base national
    volume grown forward at its demographic CAGR (incidence held constant), with
    the implied YoY growth (% and absolute adds) each year. Conditions with no
    separately-enumerated national count (value<=0) are skipped. Sorted by CAGR
    descending. The base year is the condition's own volume vintage — this is a
    forward demographic projection, not observed multi-year history (which needs a
    HCUP time series, a to-source item). Never raises."""
    out: List[ConditionYoY] = []
    for c in _registry():
        v0 = int(getattr(c.national_volume, "value", 0) or 0)
        if v0 <= 0:
            continue
        cagr = float(c.growth.cagr)
        base_year = int(getattr(c.national_volume, "year", 0) or 0)
        pts: List[YoYPoint] = []
        prev: Optional[int] = None
        for k in range(0, horizon + 1):
            vol = int(round(v0 * ((1.0 + cagr) ** k)))
            if prev is None or prev == 0:
                yoy = 0.0
                add = 0
            else:
                yoy = round((vol / prev - 1.0) * 100.0, 2)
                add = vol - prev
            pts.append(YoYPoint(year=base_year + k, volume=vol,
                                yoy_growth_pct=yoy, added_cases=add))
            prev = vol
        end = pts[-1].volume
        out.append(ConditionYoY(
            name=c.name, family=c.family, transfer_type=c.transfer_type,
            transport_acuity=c.transport_acuity,
            measure=getattr(c.national_volume, "measure", ""),
            base_year=base_year, base_volume=v0, cagr=round(cagr, 4),
            points=tuple(pts), end_volume=end, added_cases=end - v0,
            basis=getattr(c.growth, "basis", "")))
    out.sort(key=lambda x: x.cagr, reverse=True)
    return tuple(out)


@dataclass(frozen=True)
class AggregateYoY:
    available: bool
    horizon: int = 0
    base_volume: int = 0
    points: Tuple[YoYPoint, ...] = ()      # index 0 = Y+0 (relative)
    blended_cagr: float = 0.0
    end_volume: int = 0
    n_conditions: int = 0
    source_label: str = ""
    note: str = ""


def aggregate_demand_yoy(horizon: int = 5, family: Optional[str] = None) -> AggregateYoY:
    """The whole book's YoY demand trajectory — every condition's volume grown at
    its own CAGR and summed per RELATIVE year offset (Y+0..Y+horizon), with the
    blended YoY growth. ``family`` optionally restricts to one family (e.g.
    ``FAMILY_ESCALATION``). Never raises."""
    projs = condition_yoy_projection(horizon)
    if family:
        projs = tuple(p for p in projs if p.family == family)
    if not projs:
        return AggregateYoY(available=False, horizon=horizon)
    totals = [0] * (horizon + 1)
    for p in projs:
        for i, pt in enumerate(p.points):
            if i <= horizon:
                totals[i] += pt.volume
    pts: List[YoYPoint] = []
    prev: Optional[int] = None
    for i, tot in enumerate(totals):
        if prev is None or prev == 0:
            yoy = 0.0
            add = 0
        else:
            yoy = round((tot / prev - 1.0) * 100.0, 2)
            add = tot - prev
        pts.append(YoYPoint(year=i, volume=tot, yoy_growth_pct=yoy,
                            added_cases=add))
        prev = tot
    base = totals[0]
    end = totals[-1]
    blended = ((end / base) ** (1.0 / horizon) - 1.0) if base > 0 and horizon else 0.0
    return AggregateYoY(
        available=True, horizon=horizon, base_volume=base, points=tuple(pts),
        blended_cagr=round(blended, 4), end_volume=end, n_conditions=len(projs),
        source_label=("GOV/ACADEMIC base volumes × ILLUSTRATIVE demographic CAGRs "
                      "(Census age-band growth, incidence held constant)"),
        note=("Volume-weighted forward trajectory across the enumerated conditions "
              "— the demand book compounds at the blended demographic CAGR as the "
              "75-84 / 85+ cohorts age in. Relative-year (Y+0..Y+N) because the "
              "conditions carry different base-year vintages."))


@lru_cache(maxsize=None)
def _supply_rows(csv_name: str) -> Tuple[Tuple[str, ...], ...]:
    """Cached (state,) rows for a provider CSV — read once, degrade to empty."""
    path = _DATA / csv_name
    out: List[Tuple[str, ...]] = []
    try:
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                out.append(((row.get("state") or "").strip().upper(),))
    except (OSError, csv.Error):
        return tuple()
    return tuple(out)


def destination_supply(setting: Optional[str] = None, state: Optional[str] = None) -> Dict:
    """Real post-acute destination SUPPLY (SOURCED) from our provider CSVs.

    Counts SNF / IRF / LTACH / HHA / hospice providers nationally and, if
    ``state`` is given, for that state. Up-transfer hub types (Comprehensive
    Stroke Center, Level I Trauma, PCI, NICU III/IV) are NOT in any vendored
    file, so a non-post-acute setting returns ``national=None`` with an honest
    authored-reference label rather than a fabricated count.

    Called with **no ``setting``** it returns the national post-acute supply
    roll-up (``national`` = total across every SOURCED destination file, plus a
    ``by_setting`` breakdown) — the "all destinations" snapshot. This keeps
    ``destination_supply()`` a valid no-arg call so callers/health-checks can
    ask for the whole supply universe without hand-listing every setting key.
    """
    if setting is None:
        by_setting: Dict[str, int] = {}
        per_state_all: Dict[str, int] = {}
        for name, csv_name in _SETTING_CSV.items():
            rows = _supply_rows(csv_name)
            by_setting[name] = len(rows)
            for (st,) in rows:
                per_state_all[st] = per_state_all.get(st, 0) + 1
        result = {
            "setting": None,
            "national": sum(by_setting.values()),
            "by_setting": by_setting,
            "per_state": per_state_all,
            "source_label": "SOURCED · CMS Care Compare / Provider-of-Services facility file",
        }
        if state is not None:
            st = state.strip().upper()
            result["state"] = st
            result["state_count"] = per_state_all.get(st, 0)
        return result

    csv_name = _SETTING_CSV.get(setting)
    if csv_name is None:
        return {
            "setting": setting,
            "national": None,
            "per_state": {},
            "source_label": "authored clinical reference — capability designation not vendored (not in our data)",
        }
    rows = _supply_rows(csv_name)
    national = len(rows)
    per_state: Dict[str, int] = {}
    for (st,) in rows:
        per_state[st] = per_state.get(st, 0) + 1
    result = {
        "setting": setting,
        "national": national,
        "per_state": per_state,
        "source_label": "SOURCED · CMS Care Compare / Provider-of-Services facility file",
    }
    if state is not None:
        st = state.strip().upper()
        result["state"] = st
        result["state_count"] = per_state.get(st, 0)
    return result


def validate_codes() -> Dict[str, Dict[str, List[str]]]:
    """Validate every registry ICD-10-CM code against the offline billability seed.

    Returns per condition ``{icd10_ok, icd10_miss, pcs_reference}``. Because the
    registry stores billable leaves, ``icd10_miss`` is expected empty — a
    non-empty miss means a code drifted out of billability and the build should
    fail. PCS codes are surfaced as reference-only (no offline PCS validity set
    exists in the repo).
    """
    valid = _valid_icd10()
    out: Dict[str, Dict[str, List[str]]] = {}
    for c in _registry():
        ok: List[str] = []
        miss: List[str] = []
        for code in c.icd10:
            (ok if _norm(code) in valid else miss).append(code)
        out[c.name] = {
            "icd10_ok": ok,
            "icd10_miss": miss,
            "pcs_reference": list(c.pcs),
        }
    return out


def mission_mix() -> Dict:
    """Escalation-book transport-acuity split, weighted by national volume.

    Aggregates each condition's ``transport_acuity`` tier weighted by its GOV
    national volume (value>0 only) across the ESCALATION family, then reports
    the high-acuity (CCT/SCT + neonatal + peds teams) vs mid (ALS + ALS2) vs low
    (BLS/NEMT + behavioral) share. To prevent the workbook mislabel that conflated
    these, the split is reported BOTH ways: ``high_acuity_share`` EXCLUDES
    behavioral (CCT/SCT + neonatal + peds only), ``cct_sct_share`` is the CCT/SCT
    tier ALONE, and ``high_acuity_incl_behavioral_share`` adds behavioral back in.
    Acute escalation skews heavily toward the high-acuity, high-reimbursement
    CCT/SCT tier.
    """
    by_tier: Dict[str, int] = {}
    total = 0
    for c in _registry():
        if c.family != FAMILY_ESCALATION:
            continue
        v = c.national_volume.value
        if v <= 0:
            continue
        by_tier[c.transport_acuity] = by_tier.get(c.transport_acuity, 0) + v
        total += v
    high = sum(v for t, v in by_tier.items() if t in _HIGH_ACUITY_TIERS)
    mid = sum(v for t, v in by_tier.items() if t in _MID_ACUITY_TIERS)
    low = sum(v for t, v in by_tier.items() if t in _LOW_ACUITY_TIERS)
    cct_sct = by_tier.get(TIER_CCT_SCT, 0)
    behavioral = by_tier.get(TIER_BH, 0)
    def share(x: int) -> float:
        return round(x / total, 3) if total else 0.0
    return {
        "family": FAMILY_ESCALATION,
        "volume_weighted": True,
        "total_weighting_volume": total,
        "by_tier_volume": dict(sorted(by_tier.items(), key=lambda kv: kv[1], reverse=True)),
        "high_acuity_share": share(high),   # CCT/SCT + neonatal + peds (EXCLUDES behavioral)
        "cct_sct_share": share(cct_sct),    # CCT/SCT tier ALONE (< high_acuity_share)
        "high_acuity_incl_behavioral_share": share(high + behavioral),  # + behavioral
        "behavioral_share": share(behavioral),
        "mid_acuity_share": share(mid),     # ALS + ALS2
        "low_acuity_share": share(low),     # BLS / NEMT + behavioral
        "basis": "GOV volumes x authored transport-acuity tiering (Medicare ambulance ladder)",
    }


def registry_summary() -> Dict:
    """Roll-up: counts by family/transfer-type, growth leaders, addressable volume."""
    reg = _registry()
    by_family: Dict[str, int] = {}
    by_transfer: Dict[str, int] = {}
    for c in reg:
        by_family[c.family] = by_family.get(c.family, 0) + 1
        by_transfer[c.transfer_type] = by_transfer.get(c.transfer_type, 0) + 1

    # Volume-weighted growth across the escalation book (distinct GOV pools,
    # value>0). Kept to one family to avoid double-counting shared pools (e.g.
    # sepsis appears in both escalation and step-down).
    esc = [c for c in reg if c.family == FAMILY_ESCALATION and c.national_volume.value > 0]
    tot_v = sum(c.national_volume.value for c in esc)
    w_cagr = (sum(c.national_volume.value * c.growth.cagr for c in esc) / tot_v) if tot_v else 0.0

    top = growth_ranked()[:6]
    return {
        "n_conditions": len(reg),
        "n_by_family": by_family,
        "n_by_transfer_type": by_transfer,
        "fastest_growth": [(c.name, c.growth.cagr, c.growth.index_10yr) for c in top],
        "escalation_addressable_volume": tot_v,
        "escalation_volume_weighted_cagr": round(w_cagr, 4),
        "destination_supply_national": {k: destination_supply(k)["national"] for k in _SETTING_CSV},
        "honesty": {
            "volumes": "GOV (published CMS/AHRQ/CDC/MedPAC/NCHS) or ACADEMIC; never computed here",
            "growth": "ILLUSTRATIVE projection off the SOURCED demand_forecast age-band model",
            "codes": "SOURCED — ICD-10-CM validated against the vendored billability seed",
            "supply": "SOURCED — real provider-file counts",
            "capabilities_and_pcs": "authored clinical reference (not in our data)",
        },
    }
