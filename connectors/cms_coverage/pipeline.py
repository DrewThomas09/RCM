"""Wire fetch → normalize → store for the CMS Coverage connector.

Every other connector in the estate has a CLI path from the live API to
its canonical tables; cms_coverage shipped ``fetch()`` and ``normalize()``
but nothing that connected them — its nine registered datasets could
never be populated by any documented command. This module owns that
wiring (mirroring the sibling connectors' fetch verbs): drive the
connector's cursor state machine page by page, normalize each page, and
upsert the canonical rows idempotently.

Page-capped by design: ``max_pages`` bounds one endpoint's pull the same
way the estate refresh plan caps every connector (polite slices, never
unbounded). The transport ``opener`` is injectable end to end so the
whole path is testable against :class:`tests.fakes.FakeCmsCoverage`
without a socket.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .connector import MAX_PAGES_TOTAL, CmsCoverageConnector
from .endpoints import ENDPOINTS, EndpointSpec
from .normalize import normalize
from .tables import CmsCoverageStore
from .transport import Opener


@dataclass
class IngestResult:
    """One endpoint's ingest outcome (rows in, rows written, drift audit)."""

    endpoint: str
    rows_fetched: int = 0
    rows_written: int = 0
    requests: int = 0
    pages: int = 0
    exhausted: bool = False
    unmapped: Dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "rows_fetched": self.rows_fetched,
            "rows_written": self.rows_written,
            "requests": self.requests,
            "pages": self.pages,
            "exhausted": self.exhausted,
            "unmapped": dict(self.unmapped),
        }


def resolve_endpoint(name: str) -> EndpointSpec:
    """Endpoint spec for a key (``national_ncd``) or a full dataset id.

    Accepting both spellings keeps the CLI forgiving: the registry
    advertises ``cms_coverage_national_ncd`` while the specs key on the
    short form.
    """
    key = name
    if key.startswith("cms_coverage_"):
        key = key[len("cms_coverage_"):]
    spec = ENDPOINTS.get(key)
    if spec is None:
        raise KeyError(
            f"unknown cms_coverage endpoint {name!r}; "
            f"one of: {', '.join(sorted(ENDPOINTS))}")
    return spec


def ingest_endpoint(
    store: CmsCoverageStore,
    spec: EndpointSpec,
    *,
    connector: Optional[CmsCoverageConnector] = None,
    params: Optional[Dict[str, Any]] = None,
    opener: Optional[Opener] = None,
    max_pages: Optional[int] = None,
) -> IngestResult:
    """Fetch one endpoint page by page into the canonical tables."""
    conn = connector or CmsCoverageConnector()
    cap = max_pages if (max_pages and max_pages > 0) else MAX_PAGES_TOTAL
    res = IngestResult(endpoint=spec.key)
    cursor: Optional[Dict[str, Any]] = None
    for _ in range(cap):
        step = conn.fetch(spec, params, cursor, opener=opener)
        res.pages += 1
        res.requests += step.requests
        res.rows_fetched += len(step.rows)
        nres = normalize(spec, step.rows)
        for table, rows in nres.rows.items():
            res.rows_written += store.upsert(table, rows)
        for key, n in nres.unmapped.items():
            res.unmapped[key] = res.unmapped.get(key, 0) + n
        if step.next_cursor is None:
            res.exhausted = True
            break
        cursor = step.next_cursor
    return res


def ingest(
    store: CmsCoverageStore,
    dataset: Optional[str] = None,
    *,
    connector: Optional[CmsCoverageConnector] = None,
    params: Optional[Dict[str, Any]] = None,
    opener: Optional[Opener] = None,
    max_pages: Optional[int] = None,
) -> List[IngestResult]:
    """Ingest one endpoint (by key or dataset id) or, with no
    ``dataset``, every registered endpoint in declaration order."""
    specs = ([resolve_endpoint(dataset)] if dataset
             else list(ENDPOINTS.values()))
    return [
        ingest_endpoint(store, spec, connector=connector, params=params,
                        opener=opener, max_pages=max_pages)
        for spec in specs
    ]
