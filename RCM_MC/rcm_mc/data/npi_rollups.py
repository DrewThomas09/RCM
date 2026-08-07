"""Long-form NPI tables and the rollups you group them by.

Why the wide file is not enough
-------------------------------
:mod:`master_provider_file` is one wide row per NPI, and its
``taxonomy_codes`` column is a pipe-joined string. That is the right
shape for "tell me about this NPI" and the wrong shape for every
question that starts "how many" — you cannot group by a cell containing
``"332B00000X|251E00000X"``, and a provider enrolled under three
taxonomies is one row no matter which of the three you are counting.

The rOpenSci ``npi`` package calls the fix ``npi_flatten()``: unnest
each nested block into its own tidy table keyed by NPI, so the thing you
want to count is a row. That is what :func:`npi_taxonomies_long` does,
and the rollups below are the reason it is worth doing.

The counting rule, stated once
------------------------------
A provider with three taxonomies appears three times in the long table
and is counted three times in a taxonomy rollup. That is correct — it
*is* enrolled three ways — but it means taxonomy counts sum to more than
the provider count, and a reader who assumes otherwise will conclude the
file is double-counting. Every rollup here reports ``npis`` (distinct)
alongside ``rows``, so the gap between them is visible rather than
something to be discovered.

Rollups that group on a per-NPI attribute — state, status, entity type,
final parent — have no such gap, and their ``rows`` equals their
``npis``. A test asserts that, because it is the cheapest way to catch a
join that has quietly fanned out.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import pandas as pd

from .nucc_categories import classify_taxonomy

TAXONOMY_LONG_COLUMNS: Tuple[str, ...] = (
    "npi", "taxonomy_code", "taxonomy_category", "taxonomy_level_i",
    "is_primary", "entity_label", "state", "status", "final_parent",
)

ROLLUP_COLUMNS: Tuple[str, ...] = ("key", "npis", "rows", "share")


def _frame(frame: Optional[pd.DataFrame]) -> pd.DataFrame:
    if frame is not None:
        return frame
    from .master_provider_file import cached_master_file

    return cached_master_file()


def npi_taxonomies_long(frame: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """One row per (NPI, taxonomy) — the shape you can actually count.

    ``is_primary`` marks the code the wide file carries in
    ``taxonomy_code``. NPPES lets a provider reorder its slots between
    updates, so "primary" is the switched one rather than the first, and
    that distinction is already resolved upstream in the ingest — this
    just preserves it.
    """
    rows = _frame(frame)
    if rows.empty:
        return pd.DataFrame(columns=list(TAXONOMY_LONG_COLUMNS))

    out = []
    for rec in rows.to_dict("records"):
        npi = str(rec.get("npi") or "")
        if not npi:
            continue
        primary = str(rec.get("taxonomy_code") or "").strip()
        joined = str(rec.get("taxonomy_codes") or "").strip()
        codes = [c for c in joined.split("|") if c] or ([primary] if primary else [])
        if not codes:
            codes = [""]
        for code in codes:
            klass = classify_taxonomy(code)
            out.append({
                "npi": npi,
                "taxonomy_code": code,
                "taxonomy_category": klass.category,
                "taxonomy_level_i": klass.level_i,
                "is_primary": 1 if code and code == primary else 0,
                "entity_label": str(rec.get("entity_label") or ""),
                "state": str(rec.get("state") or ""),
                "status": str(rec.get("status") or ""),
                "final_parent": str(rec.get("final_parent") or ""),
            })
    if not out:
        return pd.DataFrame(columns=list(TAXONOMY_LONG_COLUMNS))
    return pd.DataFrame(out, columns=list(TAXONOMY_LONG_COLUMNS))


def _rollup(rows: pd.DataFrame, column: str, *, blank: str = "") -> pd.DataFrame:
    """Group ``rows`` on ``column``, reporting distinct NPIs and rows.

    Both numbers, always. On a per-NPI attribute they are equal and the
    second is redundant; on the long taxonomy table they diverge, and
    only showing one of them is how a multi-enrolled provider becomes an
    apparent double-count.
    """
    if rows.empty or column not in rows.columns:
        return pd.DataFrame(columns=list(ROLLUP_COLUMNS))
    keyed = rows.copy()
    keyed["key"] = keyed[column].astype(str).replace("", blank or "(none)")
    grouped = keyed.groupby("key", as_index=False).agg(
        npis=("npi", "nunique"), rows=("npi", "size"))
    total = int(grouped["npis"].sum()) or 1
    grouped["share"] = grouped["npis"] / total
    return grouped.sort_values(["npis", "key"], ascending=[False, True]
                               ).reset_index(drop=True)


def rollup_by_category(frame: Optional[pd.DataFrame] = None, *,
                       long_form: bool = True) -> pd.DataFrame:
    """Providers by PE category.

    ``long_form`` counts every enrolment, so an infusion pharmacy that
    is also a DME supplier lands in both — which is the honest answer to
    "how many infusion providers are there". Pass False to count each
    NPI once, under its primary taxonomy only.

    Both paths go through the long table, one of them filtered to the
    primary row. The first cut had the primary path group the wide frame
    on its ``taxonomy_category`` column instead, which meant the two
    answers came from different inputs: a caller whose frame carried
    taxonomy codes but no derived category got a populated answer one
    way and an empty one the other.
    """
    long_rows = npi_taxonomies_long(_frame(frame))
    if not long_form:
        long_rows = long_rows[long_rows["is_primary"] == 1]
    return _rollup(long_rows, "taxonomy_category", blank="unclassified")


def rollup_by_state(frame: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    return _rollup(_frame(frame), "state", blank="(no state)")


def rollup_by_status(frame: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    return _rollup(_frame(frame), "status")


def rollup_by_entity(frame: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    return _rollup(_frame(frame), "entity_label")


def rollup_by_cbsa(frame: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    return _rollup(_frame(frame), "cbsa_title", blank="(outside a CBSA)")


def rollup_by_parent(frame: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Providers by resolved final parent — the operator roll-up.

    Rows with no parent group under "(no parent)" rather than being
    dropped. They are the majority in most slices, and a ranking that
    hides them makes the resolved operators look like the whole market.
    """
    return _rollup(_frame(frame), "final_parent", blank="(no parent)")


def rollup_by_parent_tier(frame: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """How the parents were reached, not just how many.

    A coverage number cannot be read without this: 10,000 NPIs reaching
    an operator through CMS's own PECOS grouping is a different claim
    from 10,000 reaching one through a name match.
    """
    return _rollup(_frame(frame), "parent_tier", blank="(no parent)")


def rollup_summary(frame: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """Every rollup at once, plus the totals they should reconcile to.

    ``taxonomy_rows`` exceeding ``npis`` is expected and is the
    multi-enrolment gap, stated here so nobody has to infer it.
    """
    rows = _frame(frame)
    if rows.empty:
        return {"npis": 0}
    long_form = npi_taxonomies_long(rows)
    return {
        "npis": int(rows["npi"].nunique()),
        "taxonomy_rows": len(long_form),
        "multi_taxonomy_npis": int(
            (long_form.groupby("npi").size() > 1).sum()),
        "by_entity": rollup_by_entity(rows).to_dict("records"),
        "by_status": rollup_by_status(rows).to_dict("records"),
        "by_category": rollup_by_category(rows).head(20).to_dict("records"),
        "by_state": rollup_by_state(rows).head(20).to_dict("records"),
        "by_parent": rollup_by_parent(rows).head(20).to_dict("records"),
        "by_parent_tier": rollup_by_parent_tier(rows).to_dict("records"),
    }
