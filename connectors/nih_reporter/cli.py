"""CLI for the NIH RePORTER connector.

Stdlib ``argparse`` only, mirroring the rest of RCM-MC's CLIs.
Subcommands::

    python -m connectors.nih_reporter.cli datasets
    python -m connectors.nih_reporter.cli discover
    python -m connectors.nih_reporter.cli fetch [--dataset projects|publications]
        [--fiscal-year 2025 ...] [--state TX ...] [--org NAME ...] [--pi NAME ...]
        [--activity-code R01 ...] [--text QUERY]
        [--core-project-num N ...] [--appl-id N ...] [--pmid N ...]
        [--criteria k=v ...] [--max-pages N] [--page-size N]
    python -m connectors.nih_reporter.cli query <dataset_id> [--filter f=v ...]
        [--select c,c] [--sort -c] [--limit N] [--offset N]
    python -m connectors.nih_reporter.cli lookup-grant <project_num>
    python -m connectors.nih_reporter.cli lookup-grantee-org <name> [--limit N]
    python -m connectors.nih_reporter.cli serve [--host H] [--port P]

``--db`` (top level) is the SQLite path and defaults to ``:memory:`` —
handy for smoke runs; point it at a file to keep the rows. ``fetch`` is
capped at ``--max-pages`` (default 5, ≤ 2,500 rows) because empty
criteria match *all* of RePORTER; raising the cap is a deliberate act.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

from .connector import MAX_PAGES_DEFAULT, NihReporterConnector, PAGE_LIMIT
from .lookup import lookup_grant, lookup_grantee_org
from .query import QueryError, aggregate, query
from .registry import registry_as_dicts
from .tables import NihReporterStore


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _parse_kv(pairs: Optional[List[str]], flag: str) -> Dict[str, Any]:
    """Parse repeated ``k=v`` flags. Values are JSON when they parse as
    JSON, comma-split lists otherwise (RePORTER criteria are mostly
    lists), and plain strings as the fallback."""
    out: Dict[str, Any] = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise SystemExit(f"bad {flag} {pair!r}; expected key=value")
        k, v = pair.split("=", 1)
        try:
            out[k] = json.loads(v)
        except json.JSONDecodeError:
            out[k] = v.split(",") if "," in v else v
    return out


def _criteria_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    """Assemble the RePORTER criteria object from the domain flags."""
    if args.dataset == "projects":
        crit = NihReporterConnector.project_criteria(
            fiscal_years=args.fiscal_year or None,
            org_states=args.state or None,
            org_names=args.org or None,
            pi_names=args.pi or None,
            activity_codes=args.activity_code or None,
            advanced_text_search=args.text or None,
        )
    else:
        crit = NihReporterConnector.publication_criteria(
            core_project_nums=args.core_project_num or None,
            appl_ids=args.appl_id or None,
            pmids=args.pmid or None,
        )
    crit.update(_parse_kv(args.criteria, "--criteria"))
    return crit


def cmd_datasets(_args: argparse.Namespace) -> int:
    _print(registry_as_dicts())
    return 0


def cmd_discover(_args: argparse.Namespace) -> int:
    conn = NihReporterConnector()
    _print([{"key": s.key, "path": s.path, "target_table": s.target_table,
             "id_fields": list(s.id_fields), "date_field": s.date_field,
             "refresh_cadence": s.refresh_cadence}
            for s in conn.discover()])
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    store = NihReporterStore(args.db)
    conn = NihReporterConnector(page_limit=args.page_size)
    criteria = _criteria_from_args(args)
    result = conn.refresh(store, args.dataset, criteria,
                          max_pages=args.max_pages)
    result["criteria"] = criteria
    result["db"] = args.db
    _print(result)
    store.close()
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    store = NihReporterStore(args.db)
    try:
        filters = _parse_kv(args.filter, "--filter")
    except SystemExit as exc:
        print(exc, file=sys.stderr)
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

def cmd_aggregate(args: argparse.Namespace) -> int:
    store = NihReporterStore(args.db)
    try:
        filters = _parse_kv(args.filter, "--filter")
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 2
    try:
        res = aggregate(store, args.dataset, group_by=args.group_by.split(","),
                        filters=filters, metrics=args.metric, limit=args.limit)
    except QueryError as exc:
        print(f"aggregate error: {exc}", file=sys.stderr)
        return 2
    _print(res.as_dict())
    return 0


def cmd_lookup_grant(args: argparse.Namespace) -> int:
    _print(lookup_grant(NihReporterStore(args.db), args.project_num))
    return 0


def cmd_lookup_grantee_org(args: argparse.Namespace) -> int:
    _print(lookup_grantee_org(NihReporterStore(args.db), args.name, args.limit))
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .api_server import serve
    serve(args.db, host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="connectors.nih_reporter.cli",
        description="NIH RePORTER v2 (projects + publications) connector")
    p.add_argument("--db", default=":memory:",
                   help="SQLite db path (default :memory:)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("datasets").set_defaults(func=cmd_datasets)
    sub.add_parser("discover").set_defaults(func=cmd_discover)

    f = sub.add_parser("fetch", help="fetch + normalize + upsert one dataset")
    f.add_argument("--dataset", choices=["projects", "publications"],
                   default="projects")
    f.add_argument("--fiscal-year", action="append", type=int,
                   help="repeatable; criteria fiscal_years")
    f.add_argument("--state", action="append",
                   help="repeatable; criteria org_states (e.g. TX)")
    f.add_argument("--org", action="append",
                   help="repeatable; criteria org_names (substring match)")
    f.add_argument("--pi", action="append",
                   help="repeatable; criteria pi_names any_name")
    f.add_argument("--activity-code", action="append",
                   help="repeatable; criteria activity_codes (e.g. R01)")
    f.add_argument("--text", help="advanced_text_search over title/terms/abstract")
    f.add_argument("--core-project-num", action="append",
                   help="publications: repeatable core_project_nums")
    f.add_argument("--appl-id", action="append", type=int,
                   help="publications: repeatable appl_ids")
    f.add_argument("--pmid", action="append", type=int,
                   help="publications: repeatable pmids")
    f.add_argument("--criteria", action="append", metavar="K=V",
                   help="extra native criteria entries (JSON or comma lists)")
    f.add_argument("--max-pages", type=int, default=MAX_PAGES_DEFAULT,
                   help=f"page cap (default {MAX_PAGES_DEFAULT}; 500 rows/page)")
    f.add_argument("--page-size", type=int, default=PAGE_LIMIT,
                   help="rows per request (API max 500)")
    f.set_defaults(func=cmd_fetch)

    q = sub.add_parser("query")
    q.add_argument("dataset")
    q.add_argument("--filter", action="append")
    q.add_argument("--select")
    q.add_argument("--sort")
    q.add_argument("--limit", type=int, default=50)
    q.add_argument("--offset", type=int, default=0)
    q.set_defaults(func=cmd_query)

    agg = sub.add_parser("aggregate")
    agg.add_argument("dataset")
    agg.add_argument("--group-by", required=True, help="comma-separated columns")
    agg.add_argument("--filter", action="append")
    agg.add_argument("--metric", action="append",
                     help="func:field metric (sum/avg/min/max; repeatable)")
    agg.add_argument("--limit", type=int, default=50)
    agg.set_defaults(func=cmd_aggregate)

    lg = sub.add_parser("lookup-grant")
    lg.add_argument("project_num")
    lg.set_defaults(func=cmd_lookup_grant)

    lo = sub.add_parser("lookup-grantee-org")
    lo.add_argument("name")
    lo.add_argument("--limit", type=int, default=50)
    lo.set_defaults(func=cmd_lookup_grantee_org)

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
