"""``rcm-mc taxonomy`` — browse the healthcare-subsector taxonomy.

A read-only window onto :mod:`rcm_mc.taxonomy.registry`. No store, no network:
every subcommand just renders the in-memory map, so an analyst can answer "what
do we diligence for a home-health target?" without opening the UI. ``--json`` on
any subcommand emits the same data machine-readably for scripting.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import List

from .models import Grouping, Subsector
from . import registry


def _subsector_dict(s: Subsector) -> dict:
    """JSON-friendly view — flatten the enum to its label so the payload reads
    the same as the human output."""
    d = asdict(s)
    d["grouping"] = s.grouping.value
    return d


def _print_card(s: Subsector) -> None:
    """Full diligence card for one subsector — the `show` view."""
    print(f"{s.name}  [{s.id}]")
    print(f"  Grouping     : {s.grouping.value}")
    if s.central:
        print("  Central      : yes (Part D deep-dive archetype)")
    print(f"  Business model: {s.business_model}")
    if s.kpis:
        print("  KPIs:")
        for k in s.kpis:
            unit = f" ({k.unit})" if k.unit else ""
            bench = f" — {k.benchmark}" if k.benchmark else ""
            print(f"    - {k.name}{unit}{bench}")
    if s.reimbursement_mechanics:
        print(f"  Reimbursement: {s.reimbursement_mechanics}")
    if s.reimbursement_codes:
        print(f"  Codes        : {', '.join(s.reimbursement_codes)}")
    if s.data_sources:
        print(f"  Data sources : {', '.join(s.data_sources)}")
    if s.thesis:
        print(f"  Thesis       : {s.thesis}")
    if s.risks:
        print(f"  Risks        : {s.risks}")
    if s.exhibits:
        print(f"  Exhibits     : {', '.join(s.exhibits)}")
    if s.vertical:
        print(f"  Vertical     : {s.vertical}")
    if s.nucc_verticals:
        print(f"  NUCC supply  : {', '.join(s.nucc_verticals)}")
    if s.deep_dive:
        print(f"  Deep dive    : {s.deep_dive}")


def _print_rows(subs: List[Subsector]) -> None:
    """One line per subsector — the `list`/`search`/`central` view."""
    if not subs:
        print("(no matching subsectors)")
        return
    width = max(len(s.id) for s in subs)
    for s in subs:
        star = " *" if s.central else "  "
        print(f"{star} {s.id.ljust(width)}  {s.name}")


def main(argv: list, prog: str = "rcm-mc taxonomy") -> int:
    ap = argparse.ArgumentParser(
        prog=prog,
        description="Browse the ~55-subsector healthcare taxonomy "
                    "(KPI packs, codes, data sources, exhibits).",
    )
    sub = ap.add_subparsers(dest="action", required=True)

    g = sub.add_parser("groupings", help="List the six groupings + counts")
    g.add_argument("--json", action="store_true")

    ls = sub.add_parser("list", help="List subsectors (optionally one grouping)")
    ls.add_argument("--grouping", default="",
                    help="Filter to one grouping (label or ENUM_NAME)")
    ls.add_argument("--json", action="store_true")

    sh = sub.add_parser("show", help="Full diligence card for one subsector")
    sh.add_argument("subsector_id", help="Subsector slug, e.g. 'home_health'")
    sh.add_argument("--json", action="store_true")

    se = sub.add_parser("search", help="Match id/name/business-model/thesis/risks")
    se.add_argument("query", help="Free-text query")
    se.add_argument("--json", action="store_true")

    c = sub.add_parser("central", help="The seven most-central archetypes")
    c.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)

    if args.action == "groupings":
        counts = registry.grouping_counts()
        if args.json:
            print(json.dumps({g.value: counts[g] for g in Grouping}, indent=2))
        else:
            total = sum(counts.values())
            for grp in Grouping:
                print(f"  {counts[grp]:2d}  {grp.value}")
            print(f"  {total:2d}  TOTAL")
        return 0

    if args.action == "list":
        if args.grouping:
            try:
                subs = registry.by_grouping(args.grouping)
            except ValueError as e:
                ap.error(str(e))
        else:
            subs = registry.all_subsectors()
        if args.json:
            print(json.dumps([_subsector_dict(s) for s in subs], indent=2))
        else:
            _print_rows(subs)
        return 0

    if args.action == "show":
        s = registry.by_id(args.subsector_id)
        if s is None:
            ap.error(f"unknown subsector id: {args.subsector_id!r} "
                     f"(try `{prog} list`)")
        if args.json:
            print(json.dumps(_subsector_dict(s), indent=2))
        else:
            _print_card(s)
        return 0

    if args.action == "search":
        subs = registry.search(args.query)
        if args.json:
            print(json.dumps([_subsector_dict(s) for s in subs], indent=2))
        else:
            _print_rows(subs)
        return 0

    if args.action == "central":
        subs = registry.central_subsectors()
        if args.json:
            print(json.dumps([_subsector_dict(s) for s in subs], indent=2))
        else:
            _print_rows(subs)
        return 0

    ap.error(f"unknown action: {args.action!r}")
    return 2  # unreachable; ap.error exits


__all__ = ["main"]
