"""Enriched lookup handlers: ``/v1/lookup/shortage-area/{state}`` &
``/v1/lookup/health-center/{state}``.

These fan one state code out across the canonical tables to return the
full shortage / access picture for that state. They are provided as
**plain callables** plus a router-agnostic handler map
(:func:`v1_handlers`) so a router that supports plugin registration can
mount them *without editing its core*. If the core router can't accept
plugins, these stay usable directly (and via the CLI) and nothing in the
router is touched.

The shortage-area lookup returns the state's HPSA component rows
(top-scored sample across all three disciplines) plus discipline/status
breakdowns and the state's MUA/P designation count — one call answers
"how underserved is this state and where". The health-center lookup
returns the state's Health Center Program sites (count, status/type
breakdowns, sample) — the FQHC footprint that serves those shortage
areas.

Route nouns are unique to this domain (``shortage-area``,
``health-center``) — the estate's taken nouns (drug, device, provider,
contractor, …) are avoided so the unified server can mount every
connector's lookups side by side.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List

from .tables import HrsaDataStore

_SAMPLE_LIMIT = 25
_MAX_SAMPLE_LIMIT = 200

# Columns worth returning in a lookup sample (the full rows are 65+
# columns wide; /v1/query serves those — lookups are summaries).
_HPSA_SAMPLE_COLS = (
    "hpsa_key, hpsa_id, hpsa_name, hpsa_discipline_class, hpsa_score, "
    "designation_type, hpsa_status, hpsa_designation_date, "
    "common_county_name, common_state_abbreviation, "
    "hpsa_estimated_underserved_population, source_endpoint")
_SITE_SAMPLE_COLS = (
    "site_key, site_name, health_center_name, health_center_type, "
    "site_city, site_state_abbreviation, site_postal_code, "
    "site_telephone_number, fqhc_site_npi_number, site_status_description")


def _clamp_limit(limit: Any) -> int:
    try:
        n = int(limit)
    except (TypeError, ValueError):
        return _SAMPLE_LIMIT
    return max(1, min(n, _MAX_SAMPLE_LIMIT))


def lookup_shortage_area(store: HrsaDataStore, state: str,
                         limit: Any = _SAMPLE_LIMIT) -> Dict[str, Any]:
    """A state's shortage picture: HPSA rows + MUA/P designation counts.

    ``state`` is a two-letter postal code (case-insensitive). HPSA rows
    are matched on ``common_state_abbreviation`` (the component
    geography's state — a multi-state designation shows up in every
    state it touches, which is what a state-level view wants).
    """
    st = str(state).strip().upper()
    lim = _clamp_limit(limit)
    by_discipline = _rows(
        store,
        "SELECT hpsa_discipline_class, COUNT(*) AS count FROM hrsa_hpsa "
        "WHERE common_state_abbreviation = ? "
        "GROUP BY hpsa_discipline_class ORDER BY count DESC", (st,))
    by_status = _rows(
        store,
        "SELECT hpsa_status, COUNT(*) AS count FROM hrsa_hpsa "
        "WHERE common_state_abbreviation = ? "
        "GROUP BY hpsa_status ORDER BY count DESC", (st,))
    sample = _rows(
        store,
        f"SELECT {_HPSA_SAMPLE_COLS} FROM hrsa_hpsa "
        f"WHERE common_state_abbreviation = ? "
        f"ORDER BY CAST(hpsa_score AS INTEGER) DESC, hpsa_id LIMIT ?",
        (st, lim))
    mua_count = store.count("hrsa_mua", "state_abbreviation = ?", (st,))
    return {
        "state": st,
        "hpsa": {
            "count": store.count("hrsa_hpsa",
                                 "common_state_abbreviation = ?", (st,)),
            "by_discipline": by_discipline,
            "by_status": by_status,
            "top_scored_sample": sample,
        },
        "mua": {"count": mua_count},
    }


def lookup_health_center(store: HrsaDataStore, state: str,
                         limit: Any = _SAMPLE_LIMIT) -> Dict[str, Any]:
    """A state's Health Center Program footprint (delivery + look-alike
    sites), matched on the site's own state."""
    st = str(state).strip().upper()
    lim = _clamp_limit(limit)
    by_status = _rows(
        store,
        "SELECT site_status_description, COUNT(*) AS count "
        "FROM hrsa_health_center_sites WHERE site_state_abbreviation = ? "
        "GROUP BY site_status_description ORDER BY count DESC", (st,))
    by_type = _rows(
        store,
        "SELECT health_center_type, COUNT(*) AS count "
        "FROM hrsa_health_center_sites WHERE site_state_abbreviation = ? "
        "GROUP BY health_center_type ORDER BY count DESC", (st,))
    sample = _rows(
        store,
        f"SELECT {_SITE_SAMPLE_COLS} FROM hrsa_health_center_sites "
        f"WHERE site_state_abbreviation = ? ORDER BY site_name LIMIT ?",
        (st, lim))
    return {
        "state": st,
        "count": store.count("hrsa_health_center_sites",
                             "site_state_abbreviation = ?", (st,)),
        "by_status": by_status,
        "by_type": by_type,
        "sites": sample,
    }


# ── router-agnostic plugin surface ────────────────────────────────────
def v1_handlers(store: HrsaDataStore) -> Dict[str, Callable[..., Dict[str, Any]]]:
    """Return ``{route_template: handler}`` for plugin registration.

    A router that accepts plugins can mount these without core edits::

        for route, fn in v1_handlers(store).items():
            router.register(route, fn)

    Each handler takes the path parameter as its leading positional
    argument; ``limit`` has a default so it binds from the query string.
    Kept deliberately framework-free so it binds to any router shape.
    """
    return {
        "/v1/lookup/shortage-area/{state}":
            lambda state, limit=_SAMPLE_LIMIT:
                lookup_shortage_area(store, state, limit),
        "/v1/lookup/health-center/{state}":
            lambda state, limit=_SAMPLE_LIMIT:
                lookup_health_center(store, state, limit),
    }


def _rows(store: HrsaDataStore, sql: str, args: tuple) -> List[Dict[str, Any]]:
    return [dict(r) for r in store.fetchall(sql, args)]
