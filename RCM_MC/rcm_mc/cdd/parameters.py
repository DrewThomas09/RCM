"""NEW-18 Defensible parameter library.

The single, auditable registry for the leaf parameters that drive every
market-sizing archetype in this package. The report that specified this engine
made one demand above all others: every numeric assumption must carry a named
source, a vintage, a "well established versus illustrative" flag, and, where it
feeds a simulation, the distribution family it should be sampled from. This
module is that registry.

Why a central registry rather than scattered constants
------------------------------------------------------
Before this module the defensible numbers lived in domain files
(``data_public/fee_schedule_2026.py`` for the conversion factor and the
commercial multipliers, ``v28_data.py`` for HCC coefficients) and many were
simply not encoded anywhere. A partner could not open one surface and ask
"where did this prevalence rate come from, when was it last refreshed, is it
payment grade or an anchor for method." The :class:`DefensibleParameter`
contract answers exactly that, and the conversion factor and commercial
multipliers are imported from the fee schedule so there is one source of truth.

Defensibility flag
------------------
``WELL_ESTABLISHED`` parameters are sourced to a named federal or peer-reviewed
dataset (CMS, MedPAC, RAND, KFF, CDC, USRDS) and are safe to defend in an IC
memo. ``ILLUSTRATIVE`` parameters are anchors for method (a stale vintage, a
single-practice figure, or a borrowed analogue) and must be refreshed or
calibrated before they carry a conclusion. The sensitivity layer should let the
illustrative inputs dominate the tornado.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from ..data_public.fee_schedule_2026 import (
    COMMERCIAL_TO_MEDICARE,
    FEE_SCHEDULE_BACKBONE_2026,
)
from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series
from .registry import CddFeature, register

FEATURE_ID = "NEW-18"

# Defensibility flags.
WELL_ESTABLISHED = "well_established"
ILLUSTRATIVE = "illustrative"
_FLAGS = (WELL_ESTABLISHED, ILLUSTRATIVE)


@dataclass(frozen=True)
class DistSpec:
    """A Monte Carlo distribution family for a parameter.

    Families match Section 5.3 of the spec. ``pert`` and ``triangular`` take
    ``low``/``mode``/``high``; ``beta`` takes shape ``a``/``b`` (optionally
    rescaled onto ``low``/``high``); ``lognormal`` takes the mean/sigma of the
    underlying normal (``mu``/``sigma``); ``normal`` takes ``mu``/``sigma``.
    """

    family: str
    low: Optional[float] = None
    mode: Optional[float] = None
    high: Optional[float] = None
    mu: Optional[float] = None
    sigma: Optional[float] = None
    a: Optional[float] = None
    b: Optional[float] = None

    def sample(self, rng: np.random.Generator, size: int) -> np.ndarray:
        """Draw ``size`` values. PERT uses the beta-PERT (mode weighted 4x)."""
        fam = self.family
        if fam == "triangular":
            return rng.triangular(self.low, self.mode, self.high, size=size)
        if fam == "pert":
            lo, mo, hi = float(self.low), float(self.mode), float(self.high)
            if not (lo < mo < hi):
                # Degenerate three-point estimate: fall back to the mode.
                return np.full(size, mo)
            # Beta-PERT shape params with the conventional lambda=4 weighting.
            alpha = 1.0 + 4.0 * (mo - lo) / (hi - lo)
            beta_ = 1.0 + 4.0 * (hi - mo) / (hi - lo)
            return lo + rng.beta(alpha, beta_, size=size) * (hi - lo)
        if fam == "beta":
            draws = rng.beta(self.a, self.b, size=size)
            if self.low is not None and self.high is not None:
                return self.low + draws * (self.high - self.low)
            return draws
        if fam == "lognormal":
            return rng.lognormal(self.mu, self.sigma, size=size)
        if fam == "normal":
            return rng.normal(self.mu, self.sigma, size=size)
        raise ValueError(f"unknown distribution family: {fam!r}")


@dataclass(frozen=True)
class DefensibleParameter:
    """One leaf parameter with full provenance and an optional sampling law.

    ``value`` is the central (deterministic / base-case) estimate. ``unit``
    names what the number measures. ``source`` and ``vintage`` are the named
    dataset and its release. ``defensibility`` is one of the module flags.
    ``dist`` is the Monte Carlo law, present only where the parameter carries
    estimation or market variance. ``category`` groups the registry for the UI.
    """

    key: str
    label: str
    value: float
    unit: str
    source: str
    vintage: str
    defensibility: str
    category: str
    dist: Optional[DistSpec] = None
    note: str = ""

    def __post_init__(self) -> None:
        if self.defensibility not in _FLAGS:
            raise ValueError(
                f"{self.key}: defensibility must be one of {_FLAGS}, "
                f"got {self.defensibility!r}"
            )

    @property
    def well_established(self) -> bool:
        return self.defensibility == WELL_ESTABLISHED

    def sample(self, rng: np.random.Generator, size: int) -> np.ndarray:
        """Draw from the parameter's law, or repeat ``value`` if deterministic."""
        if self.dist is None:
            return np.full(size, float(self.value))
        return self.dist.sample(rng, size)


# Conversion-factor base and commercial multipliers are imported from the fee
# schedule so the dollar constants have one source of truth across the package.
_PFS_CF = float(FEE_SCHEDULE_BACKBONE_2026["pfs_cf_nonqp"].value)


def _p(*args: Any, **kwargs: Any) -> DefensibleParameter:
    return DefensibleParameter(*args, **kwargs)


# ---------------------------------------------------------------------------
# The registry. Keys are stable; other modules and tests look them up.
# ---------------------------------------------------------------------------
_REGISTRY: Dict[str, DefensibleParameter] = {}


def _register(param: DefensibleParameter) -> None:
    if param.key in _REGISTRY:
        raise ValueError(f"duplicate parameter key: {param.key}")
    _REGISTRY[param.key] = param


for _param in [
    # --- Reimbursement multipliers (Section 2.4) ---
    _p(
        "comm_mult_professional",
        "Commercial-to-Medicare multiplier, physician professional",
        COMMERCIAL_TO_MEDICARE["professional"],
        "ratio",
        "KFF review of 19 studies; Milliman 2025",
        "2024",
        WELL_ESTABLISHED,
        "reimbursement",
        DistSpec("triangular", low=1.18, mode=1.43, high=1.79),
        note="Range 118% (Ginsburg 2010) to 179% (Song 2019). Primary care near 1.0x; procedural specialties far higher.",
    ),
    _p(
        "comm_mult_hospital_inpatient",
        "Commercial-to-Medicare multiplier, hospital inpatient facility",
        2.54,
        "ratio",
        "RAND Hospital Price Transparency Study Round 5.1 (RRA1144-2)",
        "2020-2022 data",
        WELL_ESTABLISHED,
        "reimbursement",
        DistSpec("triangular", low=1.62, mode=2.54, high=3.46),
        note="State variance 162% (AR) to 346% (FL). RAND represents ~6% of commercial hospital spend; treat as a distribution.",
    ),
    _p(
        "comm_mult_hospital_outpatient",
        "Commercial-to-Medicare multiplier, hospital outpatient facility",
        2.79,
        "ratio",
        "RAND Hospital Price Transparency Study Round 5.1 (RRA1144-2)",
        "2020-2022 data",
        WELL_ESTABLISHED,
        "reimbursement",
        DistSpec("triangular", low=2.0, mode=2.79, high=3.5),
    ),
    _p(
        "comm_mult_asc",
        "Commercial-to-Medicare multiplier, ASC outpatient",
        COMMERCIAL_TO_MEDICARE["asc_facility"],
        "ratio",
        "RAND Hospital Price Transparency Study Round 5.1",
        "2020-2022 data",
        WELL_ESTABLISHED,
        "reimbursement",
        DistSpec("triangular", low=1.5, mode=1.71, high=2.0),
    ),
    _p(
        "pfs_conversion_factor",
        "PFS conversion factor (non-QP)",
        _PFS_CF,
        "$ per total RVU",
        "CMS CY2026 PFS Final Rule (CMS-1832-F)",
        "CY2026",
        WELL_ESTABLISHED,
        "reimbursement",
        note="Deterministic given the finalized rule. QP CF is $33.5675.",
    ),
    _p(
        "mlr_floor",
        "Medical loss ratio regulatory floor",
        0.85,
        "share",
        "ACA / CMS (Medicaid managed care and MA)",
        "current statute",
        WELL_ESTABLISHED,
        "capitation",
        note="Below the floor triggers a remittance.",
    ),
    _p(
        "v28_diabetes_pvd_constrained_coef",
        "CMS-HCC V28 constrained coefficient, diabetes with PVD",
        0.166,
        "RAF coefficient",
        "CMS-HCC V28 community model",
        "PY2024-2026 phase-in",
        WELL_ESTABLISHED,
        "capitation",
        note="V24 gave additive 0.302 + 0.288; V28 constrains the disease family to a single 0.166.",
    ),
    # --- Disease epidemiology (Section 2.5) ---
    _p(
        "diabetes_prevalence_adult",
        "Total diabetes prevalence, US adults",
        0.147,
        "share",
        "CDC National Diabetes Statistics Report",
        "2024 release (2017-2020 data)",
        WELL_ESTABLISHED,
        "epidemiology",
        DistSpec("beta", a=147.0, b=853.0),
        note="38.1M adults. NCHS Data Brief 516 (NHANES 2021-23) reports 15.8%.",
    ),
    _p(
        "diabetes_diagnosed_share",
        "Diagnosed share of diabetes cases",
        0.772,
        "share",
        "CDC National Diabetes Statistics Report",
        "2024 release",
        WELL_ESTABLISHED,
        "epidemiology",
        DistSpec("beta", a=772.0, b=228.0),
        note="22.8% of cases undiagnosed (8.7M of 38.1M).",
    ),
    _p(
        "ckd_prevalence_adult",
        "Chronic kidney disease prevalence, US adults",
        0.14,
        "share",
        "CDC CKD surveillance system",
        "current",
        WELL_ESTABLISHED,
        "epidemiology",
        note="~35.5M adults; about 90% are unaware.",
    ),
    _p(
        "ckd_diagnosed_share",
        "Diagnosed (aware) share of CKD",
        0.10,
        "share",
        "CDC CKD surveillance system",
        "current",
        WELL_ESTABLISHED,
        "epidemiology",
        DistSpec("triangular", low=0.10, mode=0.12, high=0.14),
        note="About 90% of CKD is undiagnosed; the diagnosis rate is roughly 10-14%.",
    ),
    _p(
        "htn_awareness",
        "Hypertension awareness rate",
        0.85,
        "share",
        "CDC / NHANES hypertension cascade",
        "current",
        WELL_ESTABLISHED,
        "epidemiology",
    ),
    _p(
        "htn_treated_of_aware",
        "Hypertension treatment rate among aware",
        0.77,
        "share",
        "CDC / NHANES hypertension cascade",
        "current",
        WELL_ESTABLISHED,
        "epidemiology",
        note="Of aware patients, ~77% treated; ~48% controlled overall.",
    ),
    # --- Medication adherence / persistence (Section 2.6) ---
    _p(
        "statin_pdc80",
        "Statin adherence, share reaching PDC at least 80 percent",
        0.610,
        "share",
        "PLOS One 2025 statin-prevalent cohort (n=890,180)",
        "2025",
        WELL_ESTABLISHED,
        "adherence",
        DistSpec("beta", a=610.0, b=390.0),
        note="83.5% reached PDC>=50%. Scotland population study ~52.6%.",
    ),
    _p(
        "chronic_oral_persistence_12mo",
        "12-month persistence, chronic oral therapy",
        0.7828,
        "share",
        "Mixed-cohort persistence study",
        "current",
        WELL_ESTABLISHED,
        "adherence",
        DistSpec("beta", a=783.0, b=217.0),
        note="92.65% (3mo), 85.56% (6mo), 78.28% (12mo). Implies monthly hazard lambda ~0.0204.",
    ),
    _p(
        "pqa_pdc_threshold",
        "PQA / CMS Star adherence threshold",
        0.80,
        "share",
        "Pharmacy Quality Alliance / CMS Star Ratings",
        "current",
        WELL_ESTABLISHED,
        "adherence",
        note="90% threshold for antiretrovirals.",
    ),
    # --- Adoption / diffusion (Section 2.8) ---
    _p(
        "bass_p",
        "Bass coefficient of innovation (p)",
        0.03,
        "rate",
        "Sultan, Farley & Lehmann 1990 meta-analysis (213 applications)",
        "1990",
        ILLUSTRATIVE,
        "adoption",
        DistSpec("triangular", low=0.01, mode=0.03, high=0.05),
        note="Borrowed analogue for novel B2B health-IT; refit once 3+ internal data points exist.",
    ),
    _p(
        "bass_q",
        "Bass coefficient of imitation (q)",
        0.38,
        "rate",
        "Sultan, Farley & Lehmann 1990 meta-analysis (213 applications)",
        "1990",
        ILLUSTRATIVE,
        "adoption",
        DistSpec("triangular", low=0.20, mode=0.38, high=0.40),
        note="q > p for most innovations. Lilien et al report q~0.39.",
    ),
    _p(
        "nrr_b2b_saas_median",
        "Net revenue retention, B2B SaaS median",
        1.06,
        "ratio",
        "ChartMogul 2024 (n~2,100 venture-backed B2B)",
        "2024",
        WELL_ESTABLISHED,
        "adoption",
        note="Best-in-class >130%; enterprise 115-125%; SMB 90-105%.",
    ),
    # --- Capacity utilization (Section 2.9) ---
    _p(
        "hospital_occupancy",
        "National acute hospital occupancy",
        0.66,
        "share",
        "AHA-derived (Statista)",
        "2022",
        WELL_ESTABLISHED,
        "capacity",
        note="The 85% optimal figure is a heuristic with no original study.",
    ),
    _p(
        "infusion_chair_utilization_actual",
        "Infusion chair utilization, actual",
        0.70,
        "share",
        "2019 Infusion Center Volumes, Staffing, and Operations Survey",
        "2019",
        WELL_ESTABLISHED,
        "capacity",
        DistSpec("triangular", low=0.60, mode=0.70, high=0.80),
        note="Median scheduled utilization ~80%; full theoretical (chairs x hours) is unachievable.",
    ),
    _p(
        "dialysis_treatments_per_year",
        "Dialysis treatments per patient-year",
        156.0,
        "treatments/year",
        "Clinical convention (3x per week)",
        "current",
        WELL_ESTABLISHED,
        "capacity",
        note="3 sessions per week times 52 weeks.",
    ),
    # --- Utilization rates (Section 2.1) ---
    _p(
        "tka_discharges_per_1000_medicare",
        "Major joint replacement discharges per 1,000 Medicare (DRG 470)",
        12.2,
        "per 1,000",
        "CMS Inpatient PUF",
        "FY2013",
        ILLUSTRATIVE,
        "utilization",
        note="Anchor for method only. Refresh from the current Geographic Variation PUF.",
    ),
]:
    _register(_param)


# ---------------------------------------------------------------------------
# Lookup API
# ---------------------------------------------------------------------------
def get_parameter(key: str) -> DefensibleParameter:
    """Return one parameter by key, raising ``KeyError`` if unknown."""
    if key not in _REGISTRY:
        raise KeyError(f"unknown parameter: {key}")
    return _REGISTRY[key]


def value(key: str) -> float:
    """Convenience: the central value for a parameter key."""
    return float(get_parameter(key).value)


def all_parameters() -> List[DefensibleParameter]:
    """Every parameter, sorted by key for stable enumeration."""
    return [_REGISTRY[k] for k in sorted(_REGISTRY)]


def parameters_in(category: str) -> List[DefensibleParameter]:
    """Every parameter in one category, sorted by key."""
    return [p for p in all_parameters() if p.category == category]


def categories() -> List[str]:
    return sorted({p.category for p in _REGISTRY.values()})


def defensibility_summary() -> Dict[str, int]:
    """Count of parameters by defensibility flag."""
    out = {WELL_ESTABLISHED: 0, ILLUSTRATIVE: 0}
    for p in _REGISTRY.values():
        out[p.defensibility] += 1
    return out


def build_exhibit(
    *,
    audience: str = "both",
) -> Exhibit:
    """Render the parameter register as an auditable exhibit.

    The exhibit flags every illustrative parameter (the ones the sensitivity
    layer should let dominate) and reconciles the per-flag counts against the
    registry total so a test can prove no parameter is silently dropped.
    """
    params = all_parameters()
    summary = defensibility_summary()

    flags: List[Flag] = []
    for p in params:
        if p.defensibility == ILLUSTRATIVE:
            flags.append(
                Flag(
                    code=f"illustrative_{p.key}",
                    severity="warn",
                    message=(
                        f"{p.label} is illustrative ({p.source}, {p.vintage}). "
                        "Refresh or calibrate before it carries a conclusion."
                    ),
                    source=p.source,
                )
            )

    rows = [
        {
            "key": p.key,
            "label": p.label,
            "value": p.value,
            "unit": p.unit,
            "category": p.category,
            "defensibility": p.defensibility,
            "source": p.source,
            "vintage": p.vintage,
            "has_distribution": p.dist is not None,
        }
        for p in params
    ]

    by_category = [
        {"label": cat, "value": float(len(parameters_in(cat)))}
        for cat in categories()
    ]

    reconciliations = [
        Reconciliation(
            identity="well_established + illustrative == total parameters",
            lhs=float(summary[WELL_ESTABLISHED] + summary[ILLUSTRATIVE]),
            rhs=float(len(params)),
            tolerance=0.0,
        )
    ]

    series = [
        Series(name="Parameters by category", kind="bar", points=by_category),
        Series(name="Parameter register", kind="bar", points=rows, internal_only=True),
    ]

    footnote = Footnote(
        source="Defensible parameter library (CMS, MedPAC, RAND, KFF, CDC, USRDS, peer review)",
        vintage="see per-parameter vintage",
        assumptions=[
            "Every parameter carries a named source, a vintage, and a defensibility flag.",
            "Illustrative parameters are anchors for method and are flagged for refresh.",
            "Conversion factor and commercial multipliers are imported from the fee schedule.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Defensible parameter library",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"{len(params)} parameters across {len(categories())} categories. "
            f"{summary[WELL_ESTABLISHED]} well established, "
            f"{summary[ILLUSTRATIVE]} illustrative."
        ),
        meta={
            "total": len(params),
            "by_flag": summary,
            "categories": categories(),
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    return build_exhibit()


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Defensible parameter library",
        audience="both",
        demo=_demo,
    )
)
