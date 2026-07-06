"""Enriched lookup handlers: ``/v1/lookup/county-demographics/{fips5}`` &
``/v1/lookup/state-demographics/{fips2}``.

These fan out one geography key across the canonical tables to return
the full demographic picture — every ingested vintage for the geography
plus context (a county's parent state; a state's largest counties). They
are provided as **plain callables** plus a router-agnostic handler map
(:func:`v1_handlers`) so a router that supports plugin registration can
mount them *without editing its core*. The nouns are unique to this
domain — no other connector in the estate claims ``county-demographics``
or ``state-demographics``.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .tables import CensusAcsStore

_TOP_COUNTIES_LIMIT = 10


def lookup_county_demographics(store: CensusAcsStore, fips5: str) -> Dict[str, Any]:
    """Every vintage for one county (5-digit FIPS) + its state context."""
    fips = str(fips5).strip().zfill(5)
    profiles = _rows(
        store,
        "SELECT * FROM census_acs_county WHERE fips5 = ? "
        "ORDER BY year DESC", (fips,))
    state_fips = fips[:2]
    state = _rows(
        store,
        "SELECT * FROM census_acs_state WHERE state_fips = ? "
        "ORDER BY year DESC", (state_fips,))
    return {
        "fips5": fips,
        "name": profiles[0]["name"] if profiles else None,
        "count": len(profiles),
        "profiles": profiles,
        "state": {
            "state_fips": state_fips,
            "count": len(state),
            "profiles": state,
        },
    }


def lookup_state_demographics(store: CensusAcsStore, fips2: str) -> Dict[str, Any]:
    """Every vintage for one state (2-digit FIPS) + its largest counties.

    ``CAST(... AS INTEGER)`` orders the TEXT-stored population numerically;
    jam values were normalized to NULL at ingest so the cast is safe.
    """
    fips = str(fips2).strip().zfill(2)
    profiles = _rows(
        store,
        "SELECT * FROM census_acs_state WHERE state_fips = ? "
        "ORDER BY year DESC", (fips,))
    top_counties = _rows(
        store,
        "SELECT fips5, name, year, total_pop, median_hh_income, "
        "pop_65_plus, uninsured_rate FROM census_acs_county "
        "WHERE state_fips = ? AND year = ("
        "  SELECT MAX(year) FROM census_acs_county WHERE state_fips = ?) "
        "ORDER BY CAST(total_pop AS INTEGER) DESC LIMIT ?",
        (fips, fips, _TOP_COUNTIES_LIMIT))
    return {
        "state_fips": fips,
        "name": profiles[0]["name"] if profiles else None,
        "count": len(profiles),
        "profiles": profiles,
        "counties": {
            "count": _count(store, "census_acs_county", "state_fips", fips),
            "largest": top_counties,
        },
    }


# ── router-agnostic plugin surface ────────────────────────────────────
def v1_handlers(store: CensusAcsStore) -> Dict[str, Callable[[str], Dict[str, Any]]]:
    """Return ``{route_template: handler}`` for plugin registration.

    A router that accepts plugins can mount these without core edits::

        for route, fn in v1_handlers(store).items():
            router.register(route, fn)

    Each handler takes the single path parameter and returns a JSON-able
    dict. Kept deliberately framework-free so it binds to any router shape.
    """
    return {
        "/v1/lookup/county-demographics/{fips5}":
            lambda fips5: lookup_county_demographics(store, fips5),
        "/v1/lookup/state-demographics/{fips2}":
            lambda fips2: lookup_state_demographics(store, fips2),
    }


def _rows(store: CensusAcsStore, sql: str, args: tuple) -> List[Dict[str, Any]]:
    return [dict(r) for r in store.fetchall(sql, args)]


def _count(store: CensusAcsStore, table: str, col: str, value: str) -> int:
    return store.count(table, f"{col} = ?", (value,))
