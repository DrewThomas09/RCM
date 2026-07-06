"""A standalone stdlib HTTP surface for the data.healthcare.gov slice.

Demonstrates the API contract concretely **without touching any `/v1`
router core**: this is a self-contained `http.server` app (the same
stdlib server the rest of the estate uses — no Flask/FastAPI) that
mounts every registered healthcare.gov dataset and the two lookup
handlers. If/when a central pluggable router exists, the same registry +
`v1_handlers` map drive it; until then this proves the surface and is
testable end to end.

Routes (all GET, JSON out):

    /health
    /v1/datasets                          → the registry (auto-exposed)
    /v1/query/{dataset}?<filters>&select=&sort=&limit=&offset=
    /v1/query/{dataset}/aggregate?group_by=a,b&<filters>&limit=
    /v1/lookup/marketplace-plan/{plan_id}[?limit=N]
    /v1/lookup/county-plans/{fips}[?limit=N]

Querystring → uniform query: reserved keys (`select`, `sort`, `limit`,
`offset`, `group_by`) are pulled out; every other key is a filter,
supporting the `field__op` grammar (`individualrate__lte=200`). The
caller never sees DKAN's native paging — it was absorbed at ingest.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Tuple
from urllib.parse import parse_qs, unquote, urlparse

from .lookup import v1_handlers
from .query import AggregateResult, QueryError, QueryResult, aggregate, query
from .registry import by_dataset_id, registry_as_dicts
from .tables import HealthcareGovStore

_RESERVED = {"select", "sort", "limit", "offset", "group_by"}


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
    }


def build_handler(store: HealthcareGovStore):
    """Build a request handler class bound to ``store``.

    A class factory (not a global) so multiple stores/servers can coexist
    in-process — the test suite spins one per case.
    """
    registry = by_dataset_id()
    lookups = v1_handlers(store)

    class HealthcareGovHandler(BaseHTTPRequestHandler):
        server_version = "healthcare-gov-connector/1.0"

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
                        filters=p["filters"], limit=p["limit"], registry=registry)
                    return self._send(200, res.as_dict())
                if len(parts) == 3:
                    qres: QueryResult = query(
                        store, dataset, filters=p["filters"], select=p["select"],
                        sort=p["sort"], limit=p["limit"], offset=p["offset"],
                        registry=registry)
                    return self._send(200, qres.as_dict())
            # /v1/lookup/marketplace-plan/{id} , /v1/lookup/county-plans/{fips}
            if len(parts) == 4 and parts[0] == "v1" and parts[1] == "lookup":
                key = parts[3]
                limit = qs.get("limit", [None])[0]
                if parts[2] == "marketplace-plan":
                    fn = lookups["/v1/lookup/marketplace-plan/{plan_id}"]
                    return self._send(
                        200, fn(key) if limit is None else fn(key, limit=limit))
                if parts[2] == "county-plans":
                    fn = lookups["/v1/lookup/county-plans/{fips}"]
                    return self._send(
                        200, fn(key) if limit is None else fn(key, limit=limit))
            self._send(404, {"error": f"no route for /{'/'.join(parts)}"})

    return HealthcareGovHandler


def make_server(store: HealthcareGovStore, *, host: str = "127.0.0.1",
                port: int = 0) -> Tuple[ThreadingHTTPServer, int]:
    """Build (but don't start) a threading HTTP server. ``port=0`` picks
    a free port; returns ``(server, port)``."""
    handler = build_handler(store)
    server = ThreadingHTTPServer((host, port), handler)
    return server, server.server_address[1]


def serve(db_path: str, *, host: str = "127.0.0.1", port: int = 8099) -> None:  # pragma: no cover
    """Open the store and serve forever (CLI entry)."""
    store = HealthcareGovStore(db_path)
    server, bound = make_server(store, host=host, port=port)
    print(f"healthcare.gov /v1 surface on http://{host}:{bound}  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
