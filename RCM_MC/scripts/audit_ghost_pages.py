#!/usr/bin/env python3
"""Ghost-page audit — find rendered pages that aren't front-facing.

A "ghost page" renders 200 but a partner can't *discover* it by browsing the
product, because it is absent from every front-facing surface:

  * ranking manifest   ``_surface_rankings.RANKINGS``  → feeds sub-nav backfill
                                                         + ``/best/<section>``
  * Cmd+K palette       ``_DEFAULT_PALETTE_MODULES``
  * curated sub-nav     ``_SUB_NAV`` / ``_NAV_FLAGSHIPS``
  * /tools catalog      (= ``_discover_all_routes`` minus illustrative/hidden)

It also reports the two structural causes behind the long tail of buried work:

  1. ``_TOOLS_ILLUSTRATIVE_ROUTES`` — real pages gated OUT of /tools because
     they render an illustrative strip. Bucketed here by the codebase's own
     data-honesty tier (``surface_status.classify_surface``) so the honest
     calculators (navy / data_required) are separated from the seed-corpus
     (yellow) and synthetic (red) pages that genuinely need data work.
  2. ``uncategorized`` manifest rows — pages the ranker could not assign to a
     nav section (``_resolve_sub_section`` → None), so they render in NO
     ``/best/<section>`` catalog. ``server._heuristic_section`` can recover
     most of them.

Run:  PYTHONPATH=. python scripts/audit_ghost_pages.py
No writes; prints a report. See docs/GHOST_PAGE_MIGRATION_PLAN.md for the plan.
"""
from __future__ import annotations

import pathlib
import re

from rcm_mc.server import RCMHandler
from rcm_mc.ui import _chartis_kit as ck
from rcm_mc.ui import _surface_visibility as sv
from rcm_mc.ui._surface_rankings import RANKINGS
from rcm_mc.diligence.surface_status import classify_surface

_NAV_SECTIONS = {"home", "source", "pipeline", "diligence",
                 "library", "research", "portfolio"}
_SERVER = pathlib.Path(__file__).resolve().parents[1] / "rcm_mc" / "server.py"


def _norm(r: str) -> str:
    return (r or "").split("?", 1)[0].strip().rstrip("/") or "/"


def _raw_page_routes() -> list[str]:
    """Every exact ``path == "/x"`` literal in server.py that is a page
    (drops /api, /static, file-download, and well-known infra routes)."""
    src = _SERVER.read_text(errors="replace")
    raw = sorted(set(re.findall(r'path\s*==\s*["\'](/[^"\']+)["\']', src)))
    infra = {"/favicon.ico", "/robots.txt", "/healthz", "/manifest.json",
             "/sw.js", "/openapi.json", "/openapi.yaml", "/swagger",
             "/X", "/x", "/foo"}
    return [r for r in raw
            if not r.startswith(("/api/", "/static/", "/oauth/", "/.well-known/"))
            and not r.endswith((".csv", ".xlsx", ".json"))
            and r not in infra]


def _front_facing_sets():
    rank = {_norm(r["route"]) for rows in RANKINGS.values() for r in rows}
    pal = {_norm(m["route"]) for m in ck._DEFAULT_PALETTE_MODULES
           if isinstance(m, dict) and m.get("route")}
    subnav = {_norm(it["href"]) for items in ck._SUB_NAV.values()
              for it in items if isinstance(it, dict) and it.get("href")}
    flag = {_norm(rt) for items in ck._NAV_FLAGSHIPS.values() for rt in items}
    return rank, pal, subnav, flag


def main() -> int:
    raw = _raw_page_routes()
    discovered = set(RCMHandler._discover_all_routes())      # /tools front set
    illus = set(RCMHandler._TOOLS_ILLUSTRATIVE_ROUTES)
    hidden = set(RCMHandler._TOOLS_HIDDEN_ROUTES)
    rank, pal, subnav, flag = _front_facing_sets()
    front = rank | pal | subnav | flag

    print("=" * 72)
    print("GHOST-PAGE AUDIT")
    print("=" * 72)
    print(f"  page routes (exact path==/x)         : {len(raw)}")
    print(f"  front-facing in /tools               : {len(discovered)}")
    print(f"  gated as illustrative                : {len(illus)}")
    print(f"  legitimately hidden (POST/param/auth): {len(hidden)}")

    # ---- true ghosts: render, but on NO discoverable surface ----------
    true_ghosts = [r for r in sorted(discovered)
                   if _norm(r) not in front
                   and not (sv.is_internal(r) or sv.is_internal(r + "/"))]
    print(f"\n  TRUE GHOSTS (no surface at all)      : {len(true_ghosts)}")
    for r in true_ghosts:
        print(f"      {r}")

    # ---- illustrative-gated pages by data-honesty tier ---------------
    buckets: dict[str, list[str]] = {}
    for r in sorted(illus):
        buckets.setdefault(classify_surface(r)["tier"], []).append(r)
    print("\n" + "-" * 72)
    print("ILLUSTRATIVE-GATED PAGES BY DATA-HONESTY TIER")
    print("  (navy/data_required = honest by the codebase's own definition)")
    print("-" * 72)
    for tier in ("green", "navy", "data_required", "yellow", "red"):
        rs = buckets.get(tier, [])
        if rs:
            print(f"  {tier:<14} {len(rs):>3}")
    honest = len(buckets.get("navy", [])) + len(buckets.get("data_required", []))
    print(f"\n  → honest (navy+data_required) gated  : {honest}")
    print(f"  → real GREEN mislabeled illustrative : {len(buckets.get('green', []))}")
    print(f"  → seed-corpus YELLOW (needs data)    : {len(buckets.get('yellow', []))}")
    print(f"  → synthetic RED (needs data/relabel) : {len(buckets.get('red', []))}")

    # ---- uncategorized: ranked but no /best/<section> ----------------
    unc = [r["route"] for r in RANKINGS.get("uncategorized", [])]
    recover = [r for r in unc if RCMHandler._heuristic_section(r) in _NAV_SECTIONS]
    print("\n" + "-" * 72)
    print("UNCATEGORIZED MANIFEST ROWS (render in no /best/<section>)")
    print("-" * 72)
    print(f"  uncategorized ranked pages           : {len(unc)}")
    print(f"  recoverable via _heuristic_section   : {len(recover)}")
    print(f"  remaining (mostly internal/download) : {len(unc) - len(recover)}")

    # ---- full categorized dump (for the plan appendix) ---------------
    print("\n" + "=" * 72)
    print("APPENDIX — illustrative-gated routes, by tier")
    print("=" * 72)
    for tier in ("green", "navy", "data_required", "yellow", "red"):
        rs = buckets.get(tier, [])
        if not rs:
            continue
        print(f"\n[{tier.upper()}] ({len(rs)})")
        for r in rs:
            print(f"  {r:<34} {RCMHandler._title_from_route(r)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
