"""CLI for the data.medicaid.gov connector.

Stdlib ``argparse`` only, mirroring the rest of RCM-MC's CLIs.
Subcommands::

    python -m connectors.medicaid_data.cli datasets
    python -m connectors.medicaid_data.cli discover        [--db PATH]
    python -m connectors.medicaid_data.cli fetch --dataset KEY_OR_UUID
                                          [--filter col=v ...] [--max-pages N]
                                          [--db PATH]
    python -m connectors.medicaid_data.cli query <dataset_id> [--filter f=v ...]
                                          [--select c,c] [--sort -c] [--limit N]
    python -m connectors.medicaid_data.cli catalog-search --q TEXT [--limit N]
    python -m connectors.medicaid_data.cli serve [--host H] [--port P] [--db PATH]

``--db`` defaults to ``:memory:`` — handy for smoke tests, but pass a
file path when you want ``discover``/``fetch`` output to persist for
``query``/``serve``.

``fetch --dataset`` accepts either a curated endpoint key
(``nadac_2026``, ``sdud_2025``, … → its canonical table) or ANY DKAN
dataset UUID from the catalog (→ generic ``medicaid_data_rows``).
``--max-pages`` defaults to 5 (× 500 rows/page) as a guard: several
curated datasets are millions of rows, and a full drain must be an
explicit choice.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from .connector import MAX_PAGES_DEFAULT, MedicaidDataConnector
from .lookup import lookup_medicaid_dataset, lookup_ndc_cost, lookup_state_drug
from .query import QueryError, query
from .registry import registry_as_dicts
from .tables import MedicaidDataStore


def _store(args: argparse.Namespace) -> MedicaidDataStore:
    return MedicaidDataStore(args.db)


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _parse_filters(pairs: Optional[List[str]]) -> Optional[Dict[str, str]]:
    filters: Dict[str, str] = {}
    for f in pairs or []:
        if "=" not in f:
            raise ValueError(
                f"bad --filter {f!r}; expected field=value or field__op=value")
        k, v = f.split("=", 1)
        filters[k] = v
    return filters or None


def cmd_datasets(_args: argparse.Namespace) -> int:
    _print(registry_as_dicts())
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    """Sync the full DKAN catalog (~541 datasets) into the store."""
    store = _store(args)
    counts = MedicaidDataConnector().refresh_catalog(store)
    _print({"dataset": "medicaid_data_catalog", **counts,
            "rows_in_table": store.count("medicaid_data_catalog")})
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    store = _store(args)
    try:
        filters = _parse_filters(args.filter)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    params = {"filters": filters} if filters else None
    counts = MedicaidDataConnector().refresh(
        store, args.dataset, params, max_pages=args.max_pages)
    _print({"dataset": args.dataset, **counts})
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    store = _store(args)
    try:
        filters = _parse_filters(args.filter) or {}
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    select = args.select.split(",") if args.select else None
    sort = args.sort.split(",") if args.sort else None
    try:
        res = query(store, args.dataset, filters=filters, select=select,
                    sort=sort, limit=args.limit, offset=args.offset)
    except QueryError as exc:
        print(f"query error: {exc}", file=sys.stderr)
        return 2
    _print(res.as_dict())
    return 0


def cmd_catalog_search(args: argparse.Namespace) -> int:
    """LIKE-search the synced catalog (title/description/keywords/themes).

    Searches the local ``medicaid_data_catalog`` table — run ``discover``
    first. Kept local (not a live API call) so search is instant and
    works offline once synced.
    """
    store = _store(args)
    like = f"%{args.q}%"
    rows = [dict(r) for r in store.fetchall(
        "SELECT identifier, title, themes, modified, api_url "
        "FROM medicaid_data_catalog "
        "WHERE title LIKE ? OR description LIKE ? OR keywords LIKE ? "
        "OR themes LIKE ? ORDER BY modified DESC LIMIT ?",
        (like, like, like, like, args.limit))]
    _print({"q": args.q, "count": len(rows), "rows": rows})
    return 0


def cmd_lookup_ndc_cost(args: argparse.Namespace) -> int:
    _print(lookup_ndc_cost(_store(args), args.ndc))
    return 0


def cmd_lookup_state_drug(args: argparse.Namespace) -> int:
    _print(lookup_state_drug(_store(args), args.state))
    return 0


def cmd_lookup_dataset(args: argparse.Namespace) -> int:
    _print(lookup_medicaid_dataset(_store(args), args.identifier))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .api_server import serve
    serve(args.db, host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="connectors.medicaid_data.cli",
        description="data.medicaid.gov (DKAN) connector")
    p.add_argument("--db", default=":memory:",
                   help="SQLite db path (default :memory:)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("datasets").set_defaults(func=cmd_datasets)
    sub.add_parser("discover").set_defaults(func=cmd_discover)

    f = sub.add_parser("fetch")
    f.add_argument("--dataset", required=True,
                   help="curated endpoint key (e.g. nadac_2026) or DKAN UUID")
    f.add_argument("--filter", action="append",
                   help="equality condition pushed down to DKAN (col=value)")
    f.add_argument("--max-pages", type=int, default=MAX_PAGES_DEFAULT,
                   help=f"page cap, {MAX_PAGES_DEFAULT} by default (guard "
                        "against multi-million-row drains)")
    f.set_defaults(func=cmd_fetch)

    q = sub.add_parser("query")
    q.add_argument("dataset")
    q.add_argument("--filter", action="append")
    q.add_argument("--select")
    q.add_argument("--sort")
    q.add_argument("--limit", type=int, default=50)
    q.add_argument("--offset", type=int, default=0)
    q.set_defaults(func=cmd_query)

    cs = sub.add_parser("catalog-search")
    cs.add_argument("--q", required=True)
    cs.add_argument("--limit", type=int, default=20)
    cs.set_defaults(func=cmd_catalog_search)

    ln = sub.add_parser("lookup-ndc-cost")
    ln.add_argument("ndc")
    ln.set_defaults(func=cmd_lookup_ndc_cost)

    ls = sub.add_parser("lookup-state-drug")
    ls.add_argument("state")
    ls.set_defaults(func=cmd_lookup_state_drug)

    ld = sub.add_parser("lookup-dataset")
    ld.add_argument("identifier")
    ld.set_defaults(func=cmd_lookup_dataset)

    srv = sub.add_parser("serve")
    srv.add_argument("--host", default="127.0.0.1")
    srv.add_argument("--port", type=int, default=8099)
    srv.set_defaults(func=cmd_serve)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
