"""The QPP connector: ``discover()`` + ``fetch()``.

Two fetch shapes, matching the two public QPP API families:

Eligibility (per-NPI)
---------------------
``/eligibility/npis/{npi}?year=`` answers one clinician at a time, so a
pull is driven by a caller-supplied NPI roster — ``params['npis']`` (a
list or a comma-joined string), mirroring the NPI Registry connector's
manual-ingest contract. ``fetch`` is a single *step*: it drains up to
``MAX_NPIS_PER_STEP`` NPIs, returns those raw payloads plus a
``next_cursor`` describing where in the roster to resume, and ``None``
when the roster is exhausted. An NPI with no QPP record (API 404 → empty
payload) is recorded as a skip, not an error, so one bad roster entry
never aborts a sweep. The ``organizations`` dataset shares this fetch —
same payload, second normalization grain.

Benchmarks (per-year)
---------------------
``/submissions/public/benchmarks?year=`` answers the whole benchmark
file for one performance year in one response; ``fetch`` returns its
rows with ``next_cursor=None`` immediately.

Every cursor is JSON-serialisable so a run can persist it and resume
exactly where it stopped.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .endpoints import DEFAULT_YEAR, ENDPOINTS, EndpointSpec
from .transport import Opener, QppTransport

MAX_NPIS_PER_STEP = 25         # bound the work (and rows) one fetch() returns


@dataclass
class FetchResult:
    """One ``fetch`` step's output."""

    rows: List[Dict[str, Any]]
    next_cursor: Optional[Dict[str, Any]]
    endpoint: str
    year: str = ""
    skipped_npis: List[str] = field(default_factory=list)  # no QPP record
    requests: int = 0

    @property
    def done(self) -> bool:
        return self.next_cursor is None


class QppConnector:
    """Stateless-per-call connector over an injected transport.

    All network I/O flows through ``self.transport``; pass ``opener`` on
    each call (or via the transport) so tests drive the full state
    machine with a fake server.
    """

    def __init__(self, transport: Optional[QppTransport] = None, *,
                 max_npis_per_step: int = MAX_NPIS_PER_STEP) -> None:
        self.transport = transport or QppTransport.from_env()
        self.max_npis_per_step = max_npis_per_step

    # ── discovery ─────────────────────────────────────────────────────
    def discover(self) -> List[EndpointSpec]:
        """Enumerate the endpoints this connector ingests."""
        return list(ENDPOINTS.values())

    # ── the fetch state machine ───────────────────────────────────────
    def fetch(
        self,
        endpoint: EndpointSpec,
        params: Optional[Dict[str, Any]] = None,
        cursor: Optional[Dict[str, Any]] = None,
        *,
        opener: Optional[Opener] = None,
    ) -> FetchResult:
        """Advance one step; ``next_cursor=None`` when exhausted."""
        params = dict(params or {})
        year = str(params.get("year") or
                   endpoint.default_params.get("year") or DEFAULT_YEAR)
        if endpoint.kind == "benchmarks":
            return self._fetch_benchmarks(endpoint, year, opener)
        return self._fetch_eligibility(endpoint, params, year, cursor, opener)

    # ── benchmarks: one request per year ──────────────────────────────
    def _fetch_benchmarks(self, spec: EndpointSpec, year: str,
                          opener: Optional[Opener]) -> FetchResult:
        doc = self.transport.get_json(spec.path, {"year": year}, opener=opener)
        data = doc.get("data") if isinstance(doc.get("data"), dict) else doc
        benchmarks = data.get("benchmarks") if isinstance(data, dict) else None
        rows: List[Dict[str, Any]] = []
        for b in benchmarks or []:
            if isinstance(b, dict):
                rows.append({"kind": "benchmark", "year": year, "payload": b})
        return FetchResult(rows, None, spec.key, year=year, requests=1)

    # ── eligibility: roster-driven, resumable ─────────────────────────
    def _fetch_eligibility(self, spec: EndpointSpec, params: Dict[str, Any],
                           year: str, cursor: Optional[Dict[str, Any]],
                           opener: Optional[Opener]) -> FetchResult:
        npis = self._roster(params)
        if not npis:
            raise ValueError(
                "eligibility fetch needs params['npis'] (list or "
                "comma-joined string) — the QPP Eligibility API is per-NPI")
        idx = int((cursor or {}).get("idx", 0))
        rows: List[Dict[str, Any]] = []
        skipped: List[str] = []
        requests = 0
        stop = min(len(npis), idx + self.max_npis_per_step)
        for i in range(idx, stop):
            npi = npis[i]
            path = spec.path.format(npi=npi)
            doc = self.transport.get_json(path, {"year": year}, opener=opener)
            requests += 1
            data = doc.get("data") if isinstance(doc.get("data"), dict) else doc
            if not data:
                skipped.append(npi)
                continue
            rows.append({"kind": "eligibility", "npi": npi, "year": year,
                         "payload": data})
        nxt = {"idx": stop} if stop < len(npis) else None
        return FetchResult(rows, nxt, spec.key, year=year,
                           skipped_npis=skipped, requests=requests)

    @staticmethod
    def _roster(params: Dict[str, Any]) -> List[str]:
        raw = params.get("npis") or params.get("npi") or ""
        if isinstance(raw, (list, tuple)):
            vals = [str(v) for v in raw]
        else:
            vals = str(raw).split(",")
        return [v.strip() for v in vals if v.strip()]
