"""A standalone stdlib HTTP surface for the Census ACS slice.

Demonstrates the API contract concretely **without touching any `/v1`
router core**: this is a self-contained `http.server` app (the same
stdlib server the rest of RCM-MC uses — no Flask/FastAPI) that mounts
every registered Census ACS dataset and the two lookup handlers. If/when
a central pluggable router exists, the same registry + `v1_handlers` map
drive it; until then this proves the surface and is testable end to end.

Routes (all GET, JSON out):

    /health
    /v1/status                            → fetch state (rows + vintage)
    /v1/datasets                          → the registry (auto-exposed)
    /v1/query/{dataset}?<filters>&select=&sort=&limit=&offset=
    /v1/query/{dataset}/aggregate?group_by=a,b&metric=sum:f&<filters>&limit=
    /v1/lookup/county-demographics/{fips5}
    /v1/lookup/state-demographics/{fips2}

Querystring → uniform query: reserved keys (`select`, `sort`, `limit`,
`offset`, `group_by`) are pulled out; every other key is a filter,
supporting the `field__op` grammar (`year__gte=2022`). The caller never
sees the Census API's native URL grammar — it was absorbed at ingest.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Tuple
from urllib.parse import parse_qs, unquote, urlparse

from .lookup import v1_handlers
from .query import AggregateResult, QueryError, QueryResult, aggregate, query
from .registry import by_dataset_id, registry_as_dicts
from .tables import TABLES, CensusAcsStore

_RESERVED = {"select", "sort", "limit", "offset", "group_by", "metric"}


def _parse_query(qs: Dict[str, List[str]]) -> Dict[str, Any]:
    """Pull reserved params out; the rest become filters."""
    flat = {k: v[0] for k, v in qs.items()}
    filters = {k: v for k, v in flat.items() if k not in _RESERVED}
    return {
        "filters": filters,
        "select": flat["select"].split(",") if flat.get("select") else None,
        "sort": flat["sort"].split(",") if flat.get("sort") else None,
        "limit": flat.get("limit", 50),
        "offset": flat.get("offset", 0),
        "group_by": flat["group_by"].split(",") if flat.get("group_by") else None,
        "metrics": flat["metric"].split(",") if flat.get("metric") else None,
    }


_VINTAGE_COLS = ("ingested_at", "fetched_at")
_CONNECTOR_NAME = "census_acs"
_CONNECTOR_LABEL = "US Census ACS 5-year (demographics)"


def connector_status(store: CensusAcsStore) -> Dict[str, Any]:
    """Fetch state for this connector, in the estate's ``/v1/status`` row shape.

    Same keys as one entry of the unified server's ``/v1/status``
    (``connector``/``label``/``db_path``/``db_present``/``total_rows``/
    ``last_ingested_at``), plus a per-table row-count breakdown — so
    "never fetched" (0 rows, no vintage) is distinguishable from
    "fetched, empty" and from a year-stale pull on this standalone
    surface too. Interpolated identifiers all come from the module's own
    ``TABLES`` constant, never from the request.
    """
    total = 0
    last = ""
    tables: Dict[str, int] = {}
    for tname, tdef in TABLES.items():
        n = int(store.count(tname))
        tables[tname] = n
        total += n
        for col in tdef.columns:
            if col not in _VINTAGE_COLS:
                continue
            rows = store.fetchall(f"SELECT MAX({col}) AS m FROM {tname}")
            val = rows[0]["m"] if rows else None
            if val and str(val) > last:
                last = str(val)
    db_path = str(getattr(store, "db_path", ":memory:"))
    return {
        "connector": _CONNECTOR_NAME,
        "label": _CONNECTOR_LABEL,
        "db_path": db_path,
        "db_present": db_path != ":memory:",
        "total_rows": total,
        "last_ingested_at": last or None,
        "tables": tables,
    }

def build_handler(store: CensusAcsStore):
    """Build a request handler class bound to ``store``.

    A class factory (not a global) so multiple stores/servers can coexist
    in-process — the test suite spins one per case.
    """
    registry = by_dataset_id()
    lookups = v1_handlers(store)

    class CensusAcsHandler(BaseHTTPRequestHandler):
        server_version = "census-acs-connector/1.0"

        def log_message(self, *_args: Any) -> None:  # quiet in tests
            pass

        def _send(self, status: int, body: Any) -> None:
            payload = json.dumps(body, default=str).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802 (stdlib casing)
            parsed = urlparse(self.path)
            parts = [unquote(p) for p in parsed.path.strip("/").split("/") if p]
            qs = parse_qs(parsed.query, keep_blank_values=True)
            try:
                self._route(parts, qs)
            except QueryError as exc:
                self._send(400, {"error": str(exc)})
            except Exception as exc:  # never leak a stack trace to the client
                self._send(500, {"error": f"{type(exc).__name__}: {exc}"})

        def _route(self, parts: List[str], qs: Dict[str, List[str]]) -> None:
            if parts == ["health"]:
                return self._send(200, {"status": "ok"})
            if parts == ["v1", "status"]:
                # Same envelope as the unified estate surface: a list of
                # status rows (of one, here).
                return self._send(
                    200, {"connectors": [connector_status(store)]})
            if parts == ["v1", "datasets"]:
                return self._send(200, {"datasets": registry_as_dicts()})
            # /v1/query/{dataset}[/aggregate]
            if len(parts) >= 3 and parts[0] == "v1" and parts[1] == "query":
                dataset = parts[2]
                p = _parse_query(qs)
                if len(parts) == 4 and parts[3] == "aggregate":
                    if not p["group_by"]:
                        raise QueryError("aggregate requires group_by")
                    res: AggregateResult = aggregate(
                        store, dataset, group_by=p["group_by"],
                        filters=p["filters"], limit=p["limit"],
                        metrics=p.get("metrics"), registry=registry)
                    return self._send(200, res.as_dict())
                if len(parts) == 3:
                    qres: QueryResult = query(
                        store, dataset, filters=p["filters"], select=p["select"],
                        sort=p["sort"], limit=p["limit"], offset=p["offset"],
                        registry=registry)
                    return self._send(200, qres.as_dict())
            # /v1/lookup/county-demographics/{fips5} , /state-demographics/{fips2}
            if len(parts) == 4 and parts[0] == "v1" and parts[1] == "lookup":
                key = parts[3]
                if parts[2] == "county-demographics":
                    return self._send(
                        200,
                        lookups["/v1/lookup/county-demographics/{fips5}"](key))
                if parts[2] == "state-demographics":
                    return self._send(
                        200,
                        lookups["/v1/lookup/state-demographics/{fips2}"](key))
            self._send(404, {"error": f"no route for /{'/'.join(parts)}"})

    return CensusAcsHandler


def make_server(store: CensusAcsStore, *, host: str = "127.0.0.1", port: int = 0
                ) -> Tuple[ThreadingHTTPServer, int]:
    """Build (but don't start) a threading HTTP server. ``port=0`` picks
    a free port; returns ``(server, port)``."""
    handler = build_handler(store)
    server = ThreadingHTTPServer((host, port), handler)
    return server, server.server_address[1]


def serve(db_path: str, *, host: str = "127.0.0.1", port: int = 8099) -> None:  # pragma: no cover
    """Open the store and serve forever (CLI entry)."""
    store = CensusAcsStore(db_path)
    server, bound = make_server(store, host=host, port=port)
    print(f"Census ACS /v1 surface on http://{host}:{bound}  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
