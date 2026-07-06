"""The Census ACS connector: ``discover()`` + ``fetch()`` + ``refresh()``.

The ACS API is **unpaged** — one GET returns every geography row for the
``for=`` clause (all ~3,200 counties fit in a single response), so there
is no native paging to absorb; ``fetch`` is a single step whose
``next_cursor`` is always ``None`` (kept on :class:`FetchResult` so the
result shape matches the estate's paged connectors).

What *is* absorbed here is the two-call join: every profile needs the
detail (B-table) dataset **and** the subject (S-table) dataset for the
same vintage + geography. ``fetch`` issues both GETs and returns the two
raw array-of-arrays payloads; :mod:`connectors.census_acs.normalize`
turns them into joined canonical rows. Callers never build a Census URL.

``refresh`` is the fetch → normalize → upsert convenience the CLI (and a
future estate pipeline) drives; it returns row counts per table.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .endpoints import (DEFAULT_YEAR, DETAIL_VARIABLES, ENDPOINTS,
                        SUBJECT_VARIABLES, EndpointSpec, get_endpoint)
from .transport import CensusAcsTransport, Opener


@dataclass
class FetchResult:
    """One ``fetch``'s output: both raw array-of-arrays payloads.

    ``detail`` / ``subject`` include the API's header row first.
    ``next_cursor`` is always ``None`` — the ACS API is unpaged — but the
    field keeps this shape drop-in compatible with the estate's paged
    connectors' fetch results.
    """

    detail: List[List[Any]]
    subject: List[List[Any]]
    endpoint: str
    year: int
    requests: int = 0
    next_cursor: Optional[Dict[str, Any]] = field(default=None)

    @property
    def done(self) -> bool:
        return True


class CensusAcsConnector:
    """Stateless-per-call connector over an injected transport.

    All network I/O flows through ``self.transport``; pass ``opener`` on
    each call so tests drive both GETs against a fake server.
    """

    def __init__(
        self,
        transport: Optional[CensusAcsTransport] = None,
        *,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.transport = transport or CensusAcsTransport.from_env()
        self._sleep = sleep

    # ── discovery ─────────────────────────────────────────────────────
    def discover(self) -> List[EndpointSpec]:
        """Enumerate the geography profiles this connector ingests."""
        return list(ENDPOINTS.values())

    # ── fetch: two GETs (detail + subject), no paging to absorb ───────
    def fetch(
        self,
        endpoint: "EndpointSpec | str",
        params: Optional[Dict[str, Any]] = None,
        *,
        year: Optional[int] = None,
        state: Optional[str] = None,
        opener: Optional[Opener] = None,
    ) -> FetchResult:
        """Fetch one profile's raw payloads for a vintage.

        ``state`` narrows the pull to one state's FIPS code:
        ``in=state:XX`` for counties, ``for=state:XX`` for states. CBSAs
        do not nest in states, so passing ``state`` there is an error
        rather than a silent no-op. ``params`` may also carry
        ``year``/``state`` (CLI convenience); explicit kwargs win.
        """
        spec = endpoint if isinstance(endpoint, EndpointSpec) else get_endpoint(endpoint)
        merged = dict(spec.default_params)
        merged.update(params or {})
        yr = int(year if year is not None else merged.get("year", DEFAULT_YEAR))
        st = state if state is not None else merged.get("state")
        geo = self._geo_params(spec, st)
        start = self.transport.requests_made

        detail = self.transport.get_rows(
            spec.detail_path(yr),
            {"get": "NAME," + ",".join(DETAIL_VARIABLES), **geo},
            opener=opener)
        subject = self.transport.get_rows(
            spec.subject_path(yr),
            {"get": "NAME," + ",".join(SUBJECT_VARIABLES), **geo},
            opener=opener)

        return FetchResult(
            detail=detail, subject=subject, endpoint=spec.key, year=yr,
            requests=self.transport.requests_made - start)

    def refresh(
        self,
        store: Any,
        endpoint: "EndpointSpec | str",
        *,
        year: Optional[int] = None,
        state: Optional[str] = None,
        opener: Optional[Opener] = None,
    ) -> Dict[str, Any]:
        """Fetch + normalize + upsert one profile; return counts.

        ``store`` is duck-typed (``upsert(table, rows) -> int``) so this
        stays import-light; in practice it is a
        :class:`connectors.census_acs.tables.CensusAcsStore`.
        """
        from .normalize import normalize  # local import keeps module load lazy

        result = self.fetch(endpoint, year=year, state=state, opener=opener)
        spec = endpoint if isinstance(endpoint, EndpointSpec) else get_endpoint(endpoint)
        norm = normalize(spec, result)
        counts: Dict[str, int] = {}
        for table, rows in norm.rows.items():
            counts[table] = store.upsert(table, rows)
        return {
            "dataset_id": spec.dataset_id,
            "endpoint": spec.key,
            "year": result.year,
            "state": state,
            "requests": result.requests,
            "fetched": max(len(result.detail) - 1, 0),
            "upserted": counts,
            "unmapped": dict(norm.unmapped),
        }

    @staticmethod
    def _geo_params(spec: EndpointSpec, state: Optional[str]) -> Dict[str, str]:
        """Build the ``for=``/``in=`` clause for a spec + optional state."""
        if state in (None, ""):
            return {"for": spec.geo_for}
        st = str(state).zfill(2)
        if spec.supports_in_state:
            return {"for": spec.geo_for, "in": f"state:{st}"}
        if spec.key == "state_profile":
            return {"for": f"state:{st}"}
        raise ValueError(
            f"{spec.key} does not support a state filter (CBSAs do not "
            "nest in states); drop --state or use county_profile")
