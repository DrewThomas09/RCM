"""One stdlib ``/v1`` surface over every connector — the easy-to-use estate.

Each connector already ships its own standalone ``/v1`` server. This module
mounts them all behind a *single* endpoint so a caller hits one base URL and
transparently reaches any of the ~two-dozen datasets, plus every connector's
lookups, without knowing which connector owns what.

Routing is uniform where the contract is uniform, and delegated where it is
connector-specific:

    /health
    /v1/connectors                          → the estate: one row per connector
    /v1/datasets                            → every dataset (merged registries)
    /v1/query/{dataset}                     → dispatched to the owning connector
    /v1/query/{dataset}/aggregate           → dispatched to the owning connector
    /v1/lookup/{noun}/{id}                  → delegated to the owning connector
    /v1/validate/npi/{npi}                  → delegated (NPI connector)
    /v1/search/{code_type}?q=&limit=        → delegated (ICD-10 connector)

Same stdlib ``http.server`` the connectors and the rest of RCM-MC use — no
Flask/FastAPI. A class factory binds the handler to a set of open stores, so
several estates can coexist in-process (the test suite builds one per case).
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

from . import registry as estate
from ._spi import (
    CONNECTOR_NAMES, Adapter, invoke_handler, load_all, match_template,
)

_RESERVED = {"select", "sort", "limit", "offset", "group_by"}


def _parse_query(qs: Dict[str, List[str]]) -> Dict[str, Any]:
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


def open_stores(db_path: str = ":memory:") -> Dict[str, Any]:
    """Open one store per connector.

    ``:memory:`` (default) gives every connector its own in-memory DB — handy
    for a demo/health surface. A directory path opens ``{dir}/{name}.db`` per
    connector so a real ingest persists.
    """
    adapters = load_all()
    stores: Dict[str, Any] = {}
    for name in CONNECTOR_NAMES:
        if db_path == ":memory:":
            path = ":memory:"
        else:
            path = f"{db_path.rstrip('/')}/{name}.db"
        stores[name] = adapters[name].open_store(path)
    return stores


def build_handler(stores: Dict[str, Any],
                  adapters: Optional[Dict[str, Adapter]] = None):
    """Build a request handler bound to ``{connector: store}``."""
    adapters = adapters or estate.adapters()
    owner = {}
    for name in CONNECTOR_NAMES:
        for did in adapters[name].dataset_ids():
            owner[did] = name
    # Pre-bind every connector's lookup handlers to its store, tagged by owner.
    lookup_routes: List[Tuple[str, str, Callable[..., Any]]] = []
    for name in CONNECTOR_NAMES:
        store = stores.get(name)
        if store is None:
            continue
        for template, fn in adapters[name].lookup_handlers(store).items():
            lookup_routes.append((name, template, fn))

    class EstateHandler(BaseHTTPRequestHandler):
        server_version = "rcm-connectors/1.0"

        def log_message(self, *_a: Any) -> None:  # quiet in tests
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
            except Exception as exc:  # QueryError → 400, else 500
                if type(exc).__name__ == "QueryError":
                    return self._send(400, {"error": str(exc)})
                self._send(500, {"error": f"{type(exc).__name__}: {exc}"})

        def _route(self, parts: List[str], qs: Dict[str, List[str]]) -> None:
            if parts == ["health"]:
                return self._send(200, {"status": "ok",
                                        "connectors": list(CONNECTOR_NAMES)})
            if parts == ["v1", "connectors"]:
                return self._send(200, {"connectors": estate.connectors_summary()})
            if parts == ["v1", "datasets"]:
                return self._send(200, {"datasets": estate.all_registry_rows()})
            # /v1/query/{dataset}[/aggregate] → owning connector
            if len(parts) >= 3 and parts[0] == "v1" and parts[1] == "query":
                return self._route_query(parts, qs)
            # everything else (lookups / validate / search) → delegate
            if self._route_lookup(parts, qs):
                return
            self._send(404, {"error": f"no route for /{'/'.join(parts)}"})

        def _route_query(self, parts: List[str], qs: Dict[str, List[str]]) -> None:
            dataset = parts[2]
            name = owner.get(dataset)
            if name is None:
                return self._send(404, {"error": f"unknown dataset {dataset!r}"})
            adapter = adapters[name]
            store = stores[name]
            p = _parse_query(qs)
            if len(parts) == 4 and parts[3] == "aggregate":
                if not p["group_by"]:
                    return self._send(400, {"error": "aggregate requires group_by"})
                res = adapter.aggregate(store, dataset, group_by=p["group_by"],
                                        filters=p["filters"], limit=p["limit"])
                return self._send(200, res.as_dict())
            if len(parts) == 3:
                res = adapter.query(store, dataset, filters=p["filters"],
                                    select=p["select"], sort=p["sort"],
                                    limit=p["limit"], offset=p["offset"])
                return self._send(200, res.as_dict())
            self._send(404, {"error": f"no route for /{'/'.join(parts)}"})

        def _route_lookup(self, parts: List[str],
                          qs: Dict[str, List[str]]) -> bool:
            """Delegate to the first connector whose lookup template matches."""
            for _name, template, fn in lookup_routes:
                params = match_template(template, parts)
                if params is None:
                    continue
                self._send(200, invoke_handler(fn, params, qs))
                return True
            return False

    return EstateHandler


def make_server(stores: Dict[str, Any], *, host: str = "127.0.0.1", port: int = 0,
                adapters: Optional[Dict[str, Adapter]] = None
                ) -> Tuple[ThreadingHTTPServer, int]:
    """Build (but don't start) the unified server. ``port=0`` picks a free port."""
    handler = build_handler(stores, adapters=adapters)
    server = ThreadingHTTPServer((host, port), handler)
    return server, server.server_address[1]


def serve(db_path: str = ":memory:", *, host: str = "127.0.0.1", port: int = 8100
          ) -> None:  # pragma: no cover
    """Open all connector stores and serve the unified surface forever."""
    stores = open_stores(db_path)
    server, bound = make_server(stores, host=host, port=port)
    n = len(estate.all_registry_rows())
    print(f"RCM connectors /v1 surface on http://{host}:{bound} "
          f"({len(CONNECTOR_NAMES)} connectors, {n} datasets) — Ctrl-C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
