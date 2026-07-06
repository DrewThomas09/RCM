"""Enriched lookup handlers: ``/v1/lookup/grant/{project_num}`` &
``/v1/lookup/grantee-org/{name}``.

These fan out one key across the canonical tables to return the full
funding picture for a grant or a grantee organization. They are provided
as **plain callables** plus a router-agnostic handler map
(:func:`v1_handlers`) so a router that supports plugin registration can
mount them *without editing its core*. If the core router can't accept
plugins, these stay usable directly (and via the CLI) and nothing in the
router is touched.

The grant lookup accepts either a full project number
(``5R37GM070977-24``) or a core project number (``R37GM070977``) and
returns every award year/subproject of that grant plus its linked
publications. The grantee-org lookup is a LIKE match over ``org_name``
returning an aggregate of awards per organization (RePORTER org names
are uppercase and inconsistently abbreviated — substring match is the
honest interface).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .tables import NihReporterStore

_AWARDS_LIMIT = 200
_PUBS_LIMIT = 200
_ORGS_LIMIT = 50


def lookup_grant(store: NihReporterStore, project_num: str) -> Dict[str, Any]:
    """Every award row for a grant + its linked PubMed publications.

    Matches ``project_num`` exactly *or* ``core_project_num`` exactly so
    both the fully qualified and the core form resolve; publications are
    joined on the core project number (that is the key RePORTER links
    papers by).
    """
    pnum = str(project_num).strip()
    awards = _rows(
        store,
        "SELECT * FROM nih_projects "
        "WHERE project_num = ? OR core_project_num = ? "
        "ORDER BY fiscal_year DESC, appl_id DESC LIMIT ?",
        (pnum, pnum, _AWARDS_LIMIT))
    core_nums = sorted({a["core_project_num"] for a in awards
                        if a.get("core_project_num") not in (None, "")})
    if not core_nums and pnum:
        core_nums = [pnum]  # still try the pubs edge on the raw key
    publications: List[Dict[str, Any]] = []
    if core_nums:
        placeholders = ", ".join("?" for _ in core_nums)
        publications = _rows(
            store,
            f"SELECT pub_key, pmid, appl_id, core_project_num "
            f"FROM nih_publications "
            f"WHERE core_project_num IN ({placeholders}) "
            f"ORDER BY pmid DESC LIMIT ?",
            (*core_nums, _PUBS_LIMIT))
    total_award = sum(_num(a.get("award_amount")) for a in awards)
    fiscal_years = sorted({a["fiscal_year"] for a in awards
                           if a.get("fiscal_year") not in (None, "")})
    return {
        "project_num": pnum,
        "core_project_nums": core_nums,
        "count": len(awards),
        "fiscal_years": fiscal_years,
        "total_award_amount": total_award,
        "awards": awards,
        "publications": {"count": len(publications), "rows": publications},
    }


def lookup_grantee_org(store: NihReporterStore, name: str,
                       limit: Any = _ORGS_LIMIT) -> Dict[str, Any]:
    """LIKE match over ``org_name`` → per-organization award aggregate.

    Returns one row per (org_name, org_city, org_state) with project
    count and summed award dollars, plus portfolio totals for the whole
    match. ``award_amount`` is stored TEXT (estate convention), so the
    sum casts explicitly.
    """
    q = str(name).strip()
    lim = _clamp(limit, _ORGS_LIMIT)
    pattern = f"%{q}%"
    organizations = _rows(
        store,
        "SELECT org_name, org_city, org_state, "
        "COUNT(*) AS n_projects, "
        "SUM(CAST(award_amount AS REAL)) AS total_award_amount, "
        "MIN(fiscal_year) AS first_fiscal_year, "
        "MAX(fiscal_year) AS last_fiscal_year "
        "FROM nih_projects WHERE org_name LIKE ? "
        "GROUP BY org_name, org_city, org_state "
        "ORDER BY total_award_amount DESC LIMIT ?",
        (pattern, lim))
    totals = _rows(
        store,
        "SELECT COUNT(*) AS n_projects, "
        "SUM(CAST(award_amount AS REAL)) AS total_award_amount "
        "FROM nih_projects WHERE org_name LIKE ?",
        (pattern,))
    return {
        "query": q,
        "count": len(organizations),
        "organizations": organizations,
        "totals": totals[0] if totals else
        {"n_projects": 0, "total_award_amount": None},
    }


# ── router-agnostic plugin surface ────────────────────────────────────
def v1_handlers(store: NihReporterStore) -> Dict[str, Callable[..., Dict[str, Any]]]:
    """Return ``{route_template: handler}`` for plugin registration.

    A router that accepts plugins can mount these without core edits::

        for route, fn in v1_handlers(store).items():
            router.register(route, fn)

    Each handler takes the path parameter(s) as leading positional args
    (further params carry defaults and bind from the query string) and
    returns a JSON-able dict. Kept deliberately framework-free so it
    binds to any router shape.
    """
    return {
        "/v1/lookup/grant/{project_num}":
            lambda pnum: lookup_grant(store, pnum),
        "/v1/lookup/grantee-org/{name}":
            lambda name, limit=_ORGS_LIMIT: lookup_grantee_org(store, name, limit),
    }


def _rows(store: NihReporterStore, sql: str, args: tuple) -> List[Dict[str, Any]]:
    return [dict(r) for r in store.fetchall(sql, args)]


def _num(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _clamp(value: Any, default: int, lo: int = 1, hi: int = 500) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(lo, min(n, hi))
