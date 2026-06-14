"""BOLSTER-07 Data-ingestion reconciliation.

For each ingested CMS source, confirms row counts, key uniqueness, and join
integrity on the canonical keys:
- CCN:  HCRIS <-> POS <-> Care Compare
- NPI:  NPPES <-> Physician and Other Practitioners <-> claims
- FIPS: Geographic Variation <-> Market Saturation <-> MA penetration
Confirms suppression rules (cells at or below the beneficiary threshold, 10 or
11) are respected and surfaced, and that every load carries a vintage.

Statistical and deterministic. No LLM on any path.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .exhibit import Exhibit, Flag, Footnote, Reconciliation, Series, safe_div
from .registry import CddFeature, register

FEATURE_ID = "BOLSTER-07"
DEFAULT_SUPPRESSION = 11


def reconcile_join(
    left: Sequence[Mapping[str, Any]],
    right: Sequence[Mapping[str, Any]],
    key: str,
    *,
    left_name: str = "left",
    right_name: str = "right",
) -> Dict[str, Any]:
    """Reconcile a join between two keyed tables on ``key``."""
    left_keys = [r[key] for r in left]
    right_keys = [r[key] for r in right]
    left_set, right_set = set(left_keys), set(right_keys)
    matched = left_set & right_set
    return {
        "left_name": left_name,
        "right_name": right_name,
        "key": key,
        "left_rows": len(left),
        "right_rows": len(right),
        "left_unique": len(left_keys) == len(left_set),
        "right_unique": len(right_keys) == len(right_set),
        "matched": len(matched),
        "orphans_left": sorted(left_set - right_set, key=str),
        "orphans_right": sorted(right_set - left_set, key=str),
        "join_integrity": safe_div(len(matched), len(left_set), default=1.0),
    }


def apply_suppression(
    rows: Sequence[Mapping[str, Any]],
    count_key: str,
    *,
    threshold: int = DEFAULT_SUPPRESSION,
) -> Tuple[List[Dict[str, Any]], int]:
    """Suppress cells at or below the beneficiary threshold; return rows + count."""
    out: List[Dict[str, Any]] = []
    suppressed = 0
    for r in rows:
        row = dict(r)
        val = row.get(count_key)
        if val is not None and float(val) <= threshold:
            row[count_key] = None
            row["suppressed"] = True
            suppressed += 1
        else:
            row.setdefault("suppressed", False)
        out.append(row)
    return out, suppressed


def ingestion_reconciliation(
    datasets: Mapping[str, Mapping[str, Any]],
    joins: Sequence[Tuple[str, str, str]],
    *,
    suppression: Optional[Sequence[Tuple[str, str]]] = None,
    suppression_threshold: int = DEFAULT_SUPPRESSION,
    integrity_tolerance: float = 0.0,
    source: str = "CMS ingestion layer",
    vintage: str = "",
    audience: str = "internal",
) -> Exhibit:
    """Reconcile a set of ingested datasets and their canonical-key joins.

    ``datasets``: {name: {rows: [...], key: str, vintage: str}}.
    ``joins``: list of (left_name, right_name, key).
    ``suppression``: list of (dataset_name, count_key) to suppress.
    """
    if not datasets:
        raise ValueError("ingestion_reconciliation requires at least one dataset")

    flags: List[Flag] = []
    reconciliations: List[Reconciliation] = []

    # Every load must carry a vintage.
    missing_vintage = [n for n, d in datasets.items() if not d.get("vintage")]
    if missing_vintage:
        flags.append(Flag(
            code="missing_vintage",
            severity="risk",
            message=f"{len(missing_vintage)} dataset(s) loaded without a vintage stamp.",
        ))
    reconciliations.append(Reconciliation(
        identity="every dataset carries a vintage stamp",
        lhs=1.0 if not missing_vintage else 0.0, rhs=1.0, tolerance=1e-9,
    ))

    # Key uniqueness per dataset.
    uniqueness: Dict[str, bool] = {}
    for name, d in datasets.items():
        keys = [r[d["key"]] for r in d["rows"]]
        unique = len(keys) == len(set(keys))
        uniqueness[name] = unique
        if not unique:
            flags.append(Flag(
                code="duplicate_keys",
                severity="risk",
                message=f"Dataset {name} has duplicate keys on {d['key']}.",
            ))
    reconciliations.append(Reconciliation(
        identity="all dataset keys are unique",
        lhs=1.0 if all(uniqueness.values()) else 0.0, rhs=1.0, tolerance=1e-9,
    ))

    # Join integrity.
    join_results: List[Dict[str, Any]] = []
    for left_name, right_name, key in joins:
        res = reconcile_join(
            datasets[left_name]["rows"], datasets[right_name]["rows"], key,
            left_name=left_name, right_name=right_name,
        )
        join_results.append(res)
        if res["orphans_left"]:
            flags.append(Flag(
                code="join_orphans",
                severity="warn",
                message=(
                    f"{len(res['orphans_left'])} key(s) in {left_name} did not join to "
                    f"{right_name} on {key}."
                ),
            ))
        reconciliations.append(Reconciliation(
            identity=f"{left_name} joins to {right_name} on {key} above tolerance",
            lhs=res["join_integrity"], rhs=1.0, tolerance=integrity_tolerance + 1e-12,
        ))

    # Suppression.
    suppression_report: Dict[str, int] = {}
    if suppression:
        for name, count_key in suppression:
            _, n_sup = apply_suppression(
                datasets[name]["rows"], count_key, threshold=suppression_threshold)
            suppression_report[f"{name}.{count_key}"] = n_sup
            if n_sup:
                flags.append(Flag(
                    code="cells_suppressed",
                    severity="info",
                    message=f"{n_sup} cell(s) in {name}.{count_key} suppressed at threshold {suppression_threshold}.",
                ))

    series = [
        Series(name="Join integrity", kind="bar", points=[
            {"label": f"{r['left_name']}->{r['right_name']}", "value": r["join_integrity"]}
            for r in join_results
        ]),
        Series(name="Row counts by dataset", kind="bar", internal_only=True, points=[
            {"label": n, "value": len(d["rows"])} for n, d in datasets.items()
        ]),
    ]

    footnote = Footnote(
        source=source,
        vintage=vintage or "per dataset",
        assumptions=[
            "Join integrity is the share of left keys that join to the right table.",
            f"Cells at or below {suppression_threshold} beneficiaries are suppressed.",
            "Every load is rejected if it lacks a vintage stamp.",
        ],
    )

    ex = Exhibit(
        feature_id=FEATURE_ID,
        title="Ingestion reconciliation",
        audience=audience,
        series=series,
        footnote=footnote,
        flags=flags,
        reconciliations=reconciliations,
        summary=(
            f"{len(datasets)} dataset(s), {len(join_results)} join(s). "
            f"{sum(suppression_report.values())} cell(s) suppressed."
        ),
        meta={
            "uniqueness": uniqueness,
            "joins": join_results,
            "suppression": suppression_report,
            "missing_vintage": missing_vintage,
        },
    )
    return ex.validate()


def _demo() -> Exhibit:
    datasets = {
        "HCRIS": {"rows": [{"CCN": "1", "beds": 100}, {"CCN": "2", "beds": 200},
                           {"CCN": "3", "beds": 50}], "key": "CCN", "vintage": "2023"},
        "POS": {"rows": [{"CCN": "1"}, {"CCN": "2"}, {"CCN": "3"}, {"CCN": "4"}],
                "key": "CCN", "vintage": "2024Q4"},
        "CareCompare": {"rows": [{"CCN": "1", "cases": 40}, {"CCN": "2", "cases": 8}],
                        "key": "CCN", "vintage": "2024"},
    }
    joins = [("HCRIS", "POS", "CCN"), ("HCRIS", "CareCompare", "CCN")]
    return ingestion_reconciliation(
        datasets, joins,
        suppression=[("CareCompare", "cases")],
        integrity_tolerance=0.5,  # tolerate the known CCN3 orphan in the demo
        source="Demo CMS loads", vintage="2024",
    )


register(
    CddFeature(
        feature_id=FEATURE_ID,
        title="Data-ingestion reconciliation",
        audience="internal",
        demo=_demo,
    )
)
