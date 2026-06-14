"""NEW-12 HCC/RAF risk-adjustment module (CMS-HCC V28).

Maps a member's ICD-10 diagnoses to HCCs through a deterministic crosswalk,
applies the HCC hierarchy (severe HCCs trump less severe ones in the same
family), adds the demographic factor, and sums to a RAF score. The mapping is a
pure lookup table; no LLM is on the path. Also projects a RAF trajectory and a
compression scenario (the MA risk-score normalization and coding-pattern
adjustment that compress scores over time).

RAF = demographic factor + sum of surviving HCC coefficients.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence

from . import v28_data
from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series
from .registry import CddFeature, register

FEATURE_ID = "NEW-12"


def _apply_hierarchy(hccs: set, hierarchy: Mapping[str, List[str]]) -> set:
    survivors = set(hccs)
    for parent, trumped in hierarchy.items():
        if parent in survivors:
            for t in trumped:
                survivors.discard(t)
    return survivors


def compute_raf(
    member: Mapping[str, Any],
    *,
    icd_to_hcc: Optional[Mapping[str, str]] = None,
    hcc_coefficients: Optional[Mapping[str, Mapping[str, Any]]] = None,
    hierarchy: Optional[Mapping[str, List[str]]] = None,
    trajectory_years: int = 3,
    coding_intensity: float = 0.02,
    compression_rate: float = 0.059,
    source: str = "Member diagnoses plus CMS-HCC V28 tables",
    vintage: str = "",
    audience: str = "both",
) -> Exhibit:
    """Compute a member's RAF and a compression trajectory under CMS-HCC V28.

    ``member``: {age, sex, eligibility (optional), icd10: [codes]}.
    """
    icd_map = dict(icd_to_hcc) if icd_to_hcc is not None else dict(v28_data.ICD_TO_HCC)
    coefs = dict(hcc_coefficients) if hcc_coefficients is not None else dict(v28_data.HCC_COEFFICIENTS)
    hier = dict(hierarchy) if hierarchy is not None else dict(v28_data.HCC_HIERARCHY)

    age = int(member["age"])
    sex = str(member["sex"]).upper()
    codes = [str(c).replace(".", "").upper() for c in member.get("icd10", [])]

    flags: List[Flag] = []
    mapped: Dict[str, str] = {}
    unmapped: List[str] = []
    for c in codes:
        if c in icd_map:
            mapped[c] = icd_map[c]
        else:
            unmapped.append(c)
    if unmapped:
        flags.append(Flag(
            code="unmapped_codes",
            severity="info",
            message=f"{len(unmapped)} diagnosis code(s) had no V28 HCC and were skipped.",
        ))

    raw_hccs = set(mapped.values())
    survivors = _apply_hierarchy(raw_hccs, hier)
    dropped = raw_hccs - survivors

    demo = v28_data.demographic_factor(sex, age)
    hcc_contrib = {h: float(coefs[h]["coef"]) for h in sorted(survivors) if h in coefs}
    missing_coef = [h for h in survivors if h not in coefs]
    if missing_coef:
        flags.append(Flag(
            code="hcc_without_coefficient",
            severity="warn",
            message=f"{len(missing_coef)} HCC(s) had no coefficient in the loaded table.",
        ))

    hcc_sum = sum(hcc_contrib.values())
    raf = demo + hcc_sum

    # RAF trajectory and compression scenario.
    trajectory: List[Dict[str, float]] = []
    compressed: List[Dict[str, float]] = []
    for y in range(trajectory_years + 1):
        base_y = raf * ((1.0 + coding_intensity) ** y)
        comp_y = base_y * ((1.0 - compression_rate) ** y)
        trajectory.append({"year": y, "raf": base_y})
        compressed.append({"year": y, "raf": comp_y})

    # Reconciliation: RAF equals demographic factor plus surviving HCC coefficients.
    reconciliations = [
        Reconciliation(
            identity="RAF == demographic factor + sum(surviving HCC coefficients)",
            lhs=raf,
            rhs=demo + hcc_sum,
            tolerance=1e-12,
        )
    ]

    series = [
        Series(name="RAF components", kind="bar", points=(
            [{"label": "Demographic", "value": demo}]
            + [{"label": h, "value": v} for h, v in hcc_contrib.items()]
        )),
        Series(name="RAF trajectory", kind="line",
               points=[{"label": f"Y{p['year']}", "value": p["raf"]} for p in trajectory]),
        Series(name="RAF after compression", kind="line",
               points=[{"label": f"Y{p['year']}", "value": p["raf"]} for p in compressed]),
        Series(name="HCC mapping detail", kind="bar", internal_only=True, points=[
            {"icd10": c, "hcc": h, "trumped": (h in dropped)} for c, h in mapped.items()
        ]),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or v28_data.VINTAGE,
        assumptions=[
            "RAF is the demographic factor plus surviving HCC coefficients after hierarchy.",
            "Crosswalk and coefficients are a deterministic lookup table, not a model inference.",
            f"Compression scenario applies {compression_rate*100:.1f} percent annual risk-score normalization.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="HCC RAF score (CMS-HCC V28)",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"RAF {raf:.3f}: demographic {demo:.3f} plus {len(hcc_contrib)} HCC(s) "
            f"totaling {hcc_sum:.3f}."
        ),
        meta={
            "raf": raf,
            "demographic_factor": demo,
            "hcc_sum": hcc_sum,
            "hcc_contributions": hcc_contrib,
            "surviving_hccs": sorted(survivors),
            "dropped_by_hierarchy": sorted(dropped),
            "unmapped_codes": unmapped,
            "trajectory": trajectory,
            "compressed_trajectory": compressed,
            "vintage": vintage or v28_data.VINTAGE,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    member = {"age": 72, "sex": "M", "eligibility": "CNA",
              "icd10": ["E11.9", "E11.22", "I50.9"]}
    return compute_raf(member, source="Demo member", vintage="")


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="HCC/RAF risk-adjustment module (CMS-HCC V28)",
        audience="both",
        demo=_demo,
    )
)
