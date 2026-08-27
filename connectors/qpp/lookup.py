"""QPP lookup handlers: clinician, organizations, and measure benchmarks.

Three router-agnostic handlers over the canonical QPP tables, provided
as plain callables plus a handler map (:func:`v1_handlers`) so a router
that supports plugin registration can mount them *without editing its
core*.

  * :func:`lookup_clinician`     — a clinician's eligibility rows (all
    ingested years) plus their practice organizations, by NPI.
  * :func:`lookup_organizations` — just the organization grain, by NPI.
  * :func:`lookup_benchmarks`    — every benchmark row for a MIPS
    quality measure id (e.g. ``001``), optionally one year.

Route templates are estate-unique (``qpp``-prefixed nouns) so the
unified server's first-match-wins router can never confuse them with the
NPI Registry's ``/v1/lookup/provider/{npi}`` or any other slice.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .tables import QppStore


def lookup_clinician(store: QppStore, npi: str) -> Dict[str, Any]:
    """Eligibility + organizations for one NPI, across ingested years."""
    n = str(npi).strip()
    clin = _rows(store,
                 "SELECT * FROM qpp_clinician WHERE npi = ? ORDER BY year",
                 (n,))
    orgs = _rows(store,
                 "SELECT * FROM qpp_organization WHERE npi = ? "
                 "ORDER BY year, CAST(org_idx AS INTEGER)", (n,))
    return {
        "npi": n,
        "years": sorted({r["year"] for r in clin}),
        "clinician": clin,
        "organizations": orgs,
    }


def lookup_organizations(store: QppStore, npi: str) -> Dict[str, Any]:
    """The practice-organization rows for one NPI."""
    n = str(npi).strip()
    rows = _rows(store,
                 "SELECT * FROM qpp_organization WHERE npi = ? "
                 "ORDER BY year, CAST(org_idx AS INTEGER)", (n,))
    return {"npi": n, "count": len(rows), "organizations": rows}


def lookup_benchmarks(store: QppStore, measure_id: str, year: str = ""
                      ) -> Dict[str, Any]:
    """Every benchmark row for a measure id, optionally one performance year."""
    m = str(measure_id).strip()
    if year:
        rows = _rows(store,
                     "SELECT * FROM qpp_benchmark WHERE measure_id = ? "
                     "AND performance_year = ? ORDER BY submission_method",
                     (m, str(year).strip()))
    else:
        rows = _rows(store,
                     "SELECT * FROM qpp_benchmark WHERE measure_id = ? "
                     "ORDER BY performance_year, submission_method", (m,))
    return {"measure_id": m, "count": len(rows), "benchmarks": rows}


# ── router-agnostic plugin surface ────────────────────────────────────
def v1_handlers(store: QppStore) -> Dict[str, Callable[..., Any]]:
    """Return ``{route_template: handler}`` for plugin registration.

    A router that accepts plugins can mount these without core edits::

        for route, fn in v1_handlers(store).items():
            router.register(route, fn)

    Each handler takes the path parameter(s) plus optional query params
    (``year``) and returns a JSON-able value. Kept framework-free (no
    request/response objects) so it binds to any router shape.
    """
    return {
        "/v1/lookup/qpp-clinician/{npi}":
            lambda npi: lookup_clinician(store, npi),
        "/v1/lookup/qpp-organizations/{npi}":
            lambda npi: lookup_organizations(store, npi),
        "/v1/lookup/qpp-benchmarks/{measure_id}":
            lambda measure_id, year="": lookup_benchmarks(store, measure_id,
                                                          year),
    }


def _rows(store: QppStore, sql: str, args: tuple) -> List[Dict[str, Any]]:
    return [dict(r) for r in store.fetchall(sql, args)]
