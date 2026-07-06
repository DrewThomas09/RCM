"""Declarative specs for the NIH RePORTER v2 endpoints this connector ingests.

The NIH RePORTER API (``api.reporter.nih.gov``) is a **POST-driven search
API**: every dataset is one ``/v2/{family}/search`` endpoint taking a JSON
body ``{"criteria": {...}, "offset": N, "limit": M}`` and returning
``{"meta": {"total": ...}, "results": [...]}``. There is no GET catalog —
you ask a question (fiscal years, states, PIs, free text) and page the
answer by ``offset``.

One :class:`EndpointSpec` per search family:

  * ``projects``      → ``/v2/projects/search``      → ``nih_projects``
  * ``publications``  → ``/v2/publications/search``  → ``nih_publications``

Why specs and not code branches: adding or retuning an endpoint is a data
edit here, never new routing logic elsewhere. The registry rows
(:mod:`connectors.nih_reporter.registry`) and the connector both read
these.

Live-verified paging limits (probed 2026-07; also documented at
https://api.reporter.nih.gov):

  * ``limit`` maxes at **500** records per request — a larger value is a
    hard 400 ("System doesn't support limit value greater than 500");
  * ``offset`` maxes at **14,999** — deeper paging is a hard 400 ("Please
    narrow down your search criteria"), so one criteria set can surface at
    most ~15.5k rows (offset 14,999 + limit 500). Broader pulls must be
    sliced (per fiscal year, per state, per IC).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Base of the public NIH RePORTER v2 API. No key, no auth.
NIH_REPORTER_BASE = "https://api.reporter.nih.gov"

# Live-verified hard API limits (see module docstring).
PAGE_LIMIT_MAX = 500          # max "limit" per request
OFFSET_CAP = 14_999           # max "offset" the API accepts


@dataclass(frozen=True)
class EndpointSpec:
    """One NIH RePORTER search endpoint.

    Attributes
    ----------
    key:
        Short dataset id, also the ``/v1/query/{dataset}`` slug suffix and
        the value written into each row's ``source_endpoint`` column.
    path:
        POST path under ``api.reporter.nih.gov``
        (e.g. ``/v2/projects/search``).
    target_table:
        Canonical table the normalizer upserts into.
    id_fields:
        Ordered native id fields the idempotent upsert key is composed
        from in the normalizer (``appl_id`` alone for projects;
        ``pmid`` + ``applid`` for publications, whose rows are join
        edges, not documents).
    date_field:
        Field usable for recency ordering / registry ``date_field``;
        ``None`` when the endpoint returns none (publications rows carry
        only ids).
    default_criteria:
        Baseline ``criteria`` object merged under caller criteria. Kept
        empty by default — RePORTER treats an empty criteria object as
        "everything", and the connector's ``max_pages`` cap keeps an
        accidental unbounded pull polite.
    """

    key: str
    path: str
    target_table: str
    id_fields: Tuple[str, ...]
    date_field: Optional[str] = None
    join_keys: Tuple[str, ...] = ()
    refresh_cadence: str = "weekly"
    default_criteria: Dict[str, Any] = field(default_factory=dict)
    default_params: Dict[str, str] = field(default_factory=dict)

    @property
    def dataset_id(self) -> str:
        return f"nih_reporter_{self.key}"

    @property
    def base_url(self) -> str:
        return NIH_REPORTER_BASE


_SPECS: List[EndpointSpec] = [
    EndpointSpec(
        key="projects",
        path="/v2/projects/search",
        target_table="nih_projects",
        id_fields=("appl_id",),
        date_field="date_added",
        join_keys=("core_project_num", "org_name"),
        # NIH refreshes RePORTER weekly (Mondays).
        refresh_cadence="weekly",
    ),
    EndpointSpec(
        key="publications",
        path="/v2/publications/search",
        target_table="nih_publications",
        id_fields=("pmid", "applid"),
        date_field=None,
        join_keys=("pmid", "core_project_num"),
        refresh_cadence="weekly",
    ),
]

ENDPOINTS: Dict[str, EndpointSpec] = {s.key: s for s in _SPECS}


def get_endpoint(key: str) -> EndpointSpec:
    """Look up an endpoint spec by key, raising a clear error if absent."""
    try:
        return ENDPOINTS[key]
    except KeyError as exc:
        raise KeyError(
            f"unknown NIH RePORTER endpoint {key!r}; known: {sorted(ENDPOINTS)}"
        ) from exc
