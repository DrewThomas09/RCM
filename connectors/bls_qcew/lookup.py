"""Enriched lookup handlers: ``/v1/lookup/labor-market/{area_fips}`` &
``/v1/lookup/industry-employment/{naics}``.

These answer the two questions RCM diligence actually asks of QCEW:

  * **labor-market** — "what does the healthcare labor market look like
    in this county?": every NAICS-62* observation for one area in one
    quarter (employment, establishments, average weekly wage), broken
    down by industry and ownership.
  * **industry-employment** — "where is this industry's employment?":
    the top areas by employment for one NAICS code in one quarter, with
    ownership/aggregation-level breakdowns.

Both default to the most recent quarter present in the store for the
requested slice and accept ``?year=&qtr=`` to pin an earlier one — the
lookup never touches the network; ``fetch`` must have ingested the data
first.

Dedup note: the two datasets share one physical table and the SAME
observation can legitimately arrive through both slices (an
industry-622 fetch and an area-48453 fetch overlap on Travis County's
hospital rows), stored under different composed keys so neither
dataset's slice loses rows. Lookups therefore collapse duplicates by
grouping on the natural observation key (area x ownership x industry x
quarter) and taking MAX of each measure — the duplicate values are
identical, so MAX is just "the value".

Rows with QCEW disclosure code ``N`` are suppressed at the source
(employment/wage cells published as 0); they are returned as-is because
hiding them would misreport "no data" as "zero establishments".

Route nouns are unique to this domain (``labor-market``,
``industry-employment``) — the estate's taken nouns (drug, device,
provider, contractor, shortage-area, …) are avoided so the unified
server can mount every connector's lookups side by side.

They are provided as **plain callables** plus a router-agnostic handler
map (:func:`v1_handlers`) so a router that supports plugin registration
can mount them without editing its core.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from .tables import BlsQcewStore

_SAMPLE_LIMIT = 25
_MAX_SAMPLE_LIMIT = 200

# QCEW ownership codes → titles (stable BLS vocabulary; decoded here so
# lookup responses read without a codebook).
OWN_TITLES: Dict[str, str] = {
    "0": "Total Covered",
    "1": "Federal Government",
    "2": "State Government",
    "3": "Local Government",
    "5": "Private",
}

# Measures returned in lookup rows; MAX() collapses cross-slice
# duplicates of the same observation (values are identical).
_MEASURES = ("qtrly_estabs", "month1_emplvl", "month2_emplvl",
             "month3_emplvl", "total_qtrly_wages", "avg_wkly_wage",
             "disclosure_code")
_MEASURE_SQL = ", ".join(f"MAX({m}) AS {m}" for m in _MEASURES)


def _clamp_limit(limit: Any) -> int:
    try:
        n = int(limit)
    except (TypeError, ValueError):
        return _SAMPLE_LIMIT
    return max(1, min(n, _MAX_SAMPLE_LIMIT))


def _period(store: BlsQcewStore, where: str, args: Tuple[Any, ...],
            year: Any, qtr: Any) -> Optional[Tuple[str, str]]:
    """Resolve the (year, qtr) to report: caller-pinned, else the latest
    ingested period matching ``where``. None when nothing matches."""
    if year and qtr:
        return str(year).strip(), str(qtr).strip()
    rows = store.fetchall(
        f"SELECT year, qtr FROM qcew_industry_area WHERE {where} "
        f"GROUP BY year, qtr "
        f"ORDER BY CAST(year AS INTEGER) DESC, CAST(qtr AS INTEGER) DESC "
        f"LIMIT 1", args)
    if not rows:
        return None
    return rows[0]["year"], rows[0]["qtr"]


def _decorate(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for r in rows:
        r["own_title"] = OWN_TITLES.get(str(r.get("own_code", "")), "")
    return rows


def lookup_labor_market(store: BlsQcewStore, area_fips: str,
                        year: Any = None, qtr: Any = None,
                        limit: Any = _SAMPLE_LIMIT) -> Dict[str, Any]:
    """One area's healthcare labor market (NAICS 62*) for one quarter.

    ``area_fips`` is a QCEW area code (``48453`` county, ``48000``
    state, ``C4266`` MSA, ``US000`` national). Healthcare is pinned by
    ``industry_code LIKE '62%'`` — every NAICS code starting with 62 is
    Health Care and Social Assistance, so the prefix is exact, not
    fuzzy.
    """
    area = str(area_fips).strip()
    lim = _clamp_limit(limit)
    base_where = "area_fips = ? AND industry_code LIKE '62%'"
    period = _period(store, base_where, (area,), year, qtr)
    if period is None:
        return {"area_fips": area, "year": None, "qtr": None,
                "observations": 0, "by_ownership": [], "industries": [],
                "note": "no healthcare rows ingested for this area; "
                        "run fetch first"}
    y, q = period
    where = base_where + " AND year = ? AND qtr = ?"
    args = (area, y, q)
    industries = _decorate(_rows(
        store,
        f"SELECT industry_code, own_code, agglvl_code, {_MEASURE_SQL} "
        f"FROM qcew_industry_area WHERE {where} "
        f"GROUP BY industry_code, own_code "
        f"ORDER BY CAST(MAX(month3_emplvl) AS INTEGER) DESC, "
        f"industry_code, own_code LIMIT ?",
        (*args, lim)))
    by_ownership = _decorate(_rows(
        store,
        f"SELECT own_code, COUNT(DISTINCT industry_code) AS industries "
        f"FROM qcew_industry_area WHERE {where} "
        f"GROUP BY own_code ORDER BY own_code", args))
    observations = store.fetchall(
        f"SELECT COUNT(*) AS n FROM (SELECT 1 FROM qcew_industry_area "
        f"WHERE {where} GROUP BY industry_code, own_code)", args)[0]["n"]
    return {
        "area_fips": area,
        "year": y,
        "qtr": q,
        "observations": int(observations),
        "by_ownership": by_ownership,
        "industries": industries,
    }


def lookup_industry_employment(store: BlsQcewStore, naics: str,
                               year: Any = None, qtr: Any = None,
                               limit: Any = _SAMPLE_LIMIT) -> Dict[str, Any]:
    """One industry's employment footprint across areas for one quarter.

    ``naics`` is matched exactly (``622`` is hospitals; ``62`` the whole
    sector). Areas nest (national ⊃ state ⊃ county), so the breakdowns
    are counts per group, never sums across areas — summing would
    double-count every county into its state and the nation.
    """
    code = str(naics).strip()
    lim = _clamp_limit(limit)
    base_where = "industry_code = ?"
    period = _period(store, base_where, (code,), year, qtr)
    if period is None:
        return {"industry_code": code, "year": None, "qtr": None,
                "observations": 0, "by_ownership": [], "top_areas": [],
                "note": "no rows ingested for this industry; run fetch first"}
    y, q = period
    where = base_where + " AND year = ? AND qtr = ?"
    args = (code, y, q)
    top_areas = _decorate(_rows(
        store,
        f"SELECT area_fips, own_code, agglvl_code, {_MEASURE_SQL} "
        f"FROM qcew_industry_area WHERE {where} "
        f"GROUP BY area_fips, own_code "
        f"ORDER BY CAST(MAX(month3_emplvl) AS INTEGER) DESC, "
        f"area_fips, own_code LIMIT ?",
        (*args, lim)))
    by_ownership = _decorate(_rows(
        store,
        f"SELECT own_code, COUNT(DISTINCT area_fips) AS areas "
        f"FROM qcew_industry_area WHERE {where} "
        f"GROUP BY own_code ORDER BY own_code", args))
    observations = store.fetchall(
        f"SELECT COUNT(*) AS n FROM (SELECT 1 FROM qcew_industry_area "
        f"WHERE {where} GROUP BY area_fips, own_code)", args)[0]["n"]
    return {
        "industry_code": code,
        "year": y,
        "qtr": q,
        "observations": int(observations),
        "by_ownership": by_ownership,
        "top_areas": top_areas,
    }


# ── router-agnostic plugin surface ────────────────────────────────────
def v1_handlers(store: BlsQcewStore
                ) -> Dict[str, Callable[..., Dict[str, Any]]]:
    """Return ``{route_template: handler}`` for plugin registration.

    A router that accepts plugins can mount these without core edits::

        for route, fn in v1_handlers(store).items():
            router.register(route, fn)

    Each handler takes the path parameter as its leading positional
    argument; ``year``/``qtr``/``limit`` have defaults so they bind
    from the query string. Kept deliberately framework-free so it binds
    to any router shape.
    """
    return {
        "/v1/lookup/labor-market/{area_fips}":
            lambda area_fips, year=None, qtr=None, limit=_SAMPLE_LIMIT:
                lookup_labor_market(store, area_fips, year, qtr, limit),
        "/v1/lookup/industry-employment/{naics}":
            lambda naics, year=None, qtr=None, limit=_SAMPLE_LIMIT:
                lookup_industry_employment(store, naics, year, qtr, limit),
    }


def _rows(store: BlsQcewStore, sql: str, args: tuple) -> List[Dict[str, Any]]:
    return [dict(r) for r in store.fetchall(sql, args)]
