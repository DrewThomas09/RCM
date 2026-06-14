"""NEW-23 Procedure / claims bottom-up TAM.

The procedure archetype is the most parameter-intensive. It builds market size
from the population through utilization, site of care, payer, and price:

    volume   = population x (utilization per 1,000 / 1,000) x procedures/patient
    revenue  = volume x sum over sites of [ site share
                 x sum over payers of [ payer share x allowed(site, payer) ] ]

The allowed amount per site is the Medicare-allowed base (which may itself
decompose into professional, facility, anesthesia, and drug components); the
commercial price is that base times a site-specific commercial-to-Medicare
multiplier. The multipliers default to the values in the fee-schedule backbone
so the dollar constants stay consistent with the rest of the package.

The exhibit reconciles each segment's site-mix and payer-mix shares to one (a
silent mix that does not sum to one is the classic way a bottom-up build drifts)
and rolls the segments into TAM.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Union

from ..data_public.fee_schedule_2026 import COMMERCIAL_TO_MEDICARE
from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series
from .registry import CddFeature, register

FEATURE_ID = "NEW-23"

# Map a site label to its commercial-to-Medicare multiplier key.
_SITE_MULT_KEY = {
    "hopd": "hopd_outpatient",
    "outpatient": "hopd_outpatient",
    "asc": "asc_facility",
    "office": "professional",
    "physician": "professional",
    "inpatient": "inpatient",
    "ip": "inpatient",
}

AllowedSpec = Union[float, Mapping[str, float]]


def _allowed_base(spec: AllowedSpec) -> float:
    """A site's Medicare allowed amount, summing components if given as a dict.

    A scalar is the all-in allowed amount. A dict decomposes into named
    components (professional, facility, anesthesia, drug) that are summed, which
    is how a real fee-schedule build assembles the allowed amount.
    """
    if isinstance(spec, Mapping):
        return float(sum(float(v) for v in spec.values()))
    return float(spec)


def _commercial_multiplier(site: str, overrides: Mapping[str, float]) -> float:
    if site in overrides:
        return float(overrides[site])
    key = _SITE_MULT_KEY.get(site)
    if key is None:
        raise ValueError(
            f"no commercial multiplier for site {site!r}; pass it in "
            "commercial_multipliers"
        )
    return float(COMMERCIAL_TO_MEDICARE[key])


def _segment_revenue(
    seg: Mapping[str, Any], overrides: Mapping[str, float]
) -> Dict[str, float]:
    population = float(seg["population"])
    util = float(seg["utilization_per_1000"])
    ppp = float(seg.get("procedures_per_patient", 1.0))
    site_mix: Mapping[str, float] = seg["site_mix"]
    payer_mix: Mapping[str, float] = seg["payer_mix"]
    allowed: Mapping[str, AllowedSpec] = seg["allowed"]

    if population < 0 or util < 0 or ppp < 0:
        raise ValueError("population, utilization, and procedures/patient must be non-negative")

    volume = population * (util / 1000.0) * ppp

    per_procedure = 0.0
    for site, site_share in site_mix.items():
        if site not in allowed:
            raise ValueError(f"site {site!r} in site_mix has no allowed amount")
        base = _allowed_base(allowed[site])
        mult = _commercial_multiplier(site, overrides)
        payer_weighted = 0.0
        for payer, payer_share in payer_mix.items():
            if payer == "medicare":
                price = base
            elif payer == "commercial":
                price = base * mult
            else:
                raise ValueError(f"payer must be 'medicare' or 'commercial', got {payer!r}")
            payer_weighted += float(payer_share) * price
        per_procedure += float(site_share) * payer_weighted

    return {
        "volume": volume,
        "per_procedure_allowed": per_procedure,
        "revenue": volume * per_procedure,
    }


def _mix_sum(mix: Mapping[str, float]) -> float:
    return float(sum(float(v) for v in mix.values()))


def procedure_buildup(
    segments: Sequence[Mapping[str, Any]],
    *,
    commercial_multipliers: Mapping[str, float] = {},
    mix_tolerance: float = 1e-6,
    source: str = "CMS Geographic Variation PUF and fee schedules",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Roll procedure segments into a bottom-up TAM with full provenance.

    Each segment is a dict of {label, population, utilization_per_1000,
    procedures_per_patient, site_mix, payer_mix, allowed}. ``allowed`` maps each
    site to a Medicare allowed amount (scalar or a component dict). Commercial
    prices apply the site's commercial-to-Medicare multiplier.
    """
    if not segments:
        raise ValueError("procedure_buildup requires at least one segment")

    flags: List[Flag] = []
    reconciliations: List[Reconciliation] = []
    seg_rows: List[Dict[str, Any]] = []
    tam = 0.0

    for seg in segments:
        label = str(seg["label"])
        site_sum = _mix_sum(seg["site_mix"])
        payer_sum = _mix_sum(seg["payer_mix"])
        reconciliations.append(
            Reconciliation(
                identity=f"site-mix shares sum to one [{label}]",
                lhs=site_sum,
                rhs=1.0,
                tolerance=mix_tolerance,
            )
        )
        reconciliations.append(
            Reconciliation(
                identity=f"payer-mix shares sum to one [{label}]",
                lhs=payer_sum,
                rhs=1.0,
                tolerance=mix_tolerance,
            )
        )
        if abs(site_sum - 1.0) > mix_tolerance or abs(payer_sum - 1.0) > mix_tolerance:
            flags.append(
                Flag(
                    code=f"mix_not_normalized_{label}",
                    severity="risk",
                    message=(
                        f"Segment {label} mix shares do not sum to one "
                        f"(site {site_sum:.4f}, payer {payer_sum:.4f}). The build "
                        "will understate or overstate this segment."
                    ),
                    source=source,
                )
            )

        r = _segment_revenue(seg, commercial_multipliers)
        tam += r["revenue"]
        seg_rows.append(
            {
                "segment": label,
                "volume": r["volume"],
                "per_procedure_allowed": r["per_procedure_allowed"],
                "revenue": r["revenue"],
            }
        )

    # Roll-up reconciliation: the TAM equals the sum of segment revenues.
    reconciliations.append(
        Reconciliation(
            identity="TAM == sum of segment revenues",
            lhs=tam,
            rhs=sum(row["revenue"] for row in seg_rows),
            tolerance=max(1.0, tam * 1e-9),
        )
    )

    series = [
        Series(
            name="Procedure TAM by segment",
            kind="bar",
            points=[{"label": row["segment"], "value": row["revenue"]} for row in seg_rows],
        ),
        Series(name="Segment build detail", kind="bar", points=seg_rows, internal_only=True),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "not stated",
        assumptions=[
            "Volume is population times utilization per 1,000 times procedures per patient.",
            "Allowed amount is the Medicare base by site; commercial applies the site multiplier.",
            "Commercial multipliers default to the fee-schedule backbone.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Procedure bottom-up TAM",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"Bottom-up TAM {tam:,.0f} across {len(seg_rows)} segment(s)."
        ),
        meta={
            "tam": tam,
            "segments": seg_rows,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    segments = [
        {
            "label": "Colonoscopy, metro CBSA",
            "population": 500_000,
            "utilization_per_1000": 25.0,
            "procedures_per_patient": 1.0,
            "site_mix": {"hopd": 0.45, "asc": 0.55},
            "payer_mix": {"medicare": 0.55, "commercial": 0.45},
            "allowed": {"hopd": 710.0, "asc": 375.0},
        },
    ]
    return procedure_buildup(segments, source="Demo CBSA build", vintage="2026")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Procedure / claims bottom-up TAM",
        audience="both",
        demo=_demo,
    )
)
