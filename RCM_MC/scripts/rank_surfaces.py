#!/usr/bin/env python3
"""Rank PEdesk's user-facing surfaces for front-facing promotion.

Scores every route that maps to a UI page module on two axes the partner
asked for:

  • EFFORT / DEPTH (0-5) — how much real work went into the page, proxied by
    the renderer's size (LOC) plus a test-coverage bump. A big, tested page is
    a page someone invested in.
  • PE / CHARTIS-ADVISORY USEFULNESS (0-5) — how useful it is to a PE partner
    or Chartis PE advisory team, from: data honesty tier (real CMS/own-data
    LIVE pages score highest), a declared source/purpose header, and whether
    it sits in a core deal-workflow section (Source/Diligence/Portfolio/
    Pipeline).

TOTAL = effort + usefulness (0-10). The script is deterministic and reads only
real signals from the codebase — no hand-tuned per-page scores. Regenerate with
``python scripts/rank_surfaces.py`` (writes docs/rankings/PEDESK_SURFACE_RANKINGS.md).

The point: rank to find the strongest pages per category AND the "buried gems"
(high score, but not surfaced in the nav) that are the migration candidates.
"""
from __future__ import annotations

import pathlib
import re
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_UI = _ROOT / "rcm_mc" / "ui"
_TESTS = _ROOT / "tests"
_SERVER = _ROOT / "rcm_mc" / "server.py"

_TIER_USE = {"green": 3.0, "navy": 2.0, "data_required": 1.5, "yellow": 1.0, "red": 0.0}
_CORE_SECTIONS = {"source", "diligence", "portfolio", "pipeline"}
# Shared chrome/kit modules are not "pages" — exclude so they don't rank.
_EXCLUDE_MODULES = {"_chartis_kit", "_ui_kit", "_web_components", "brand",
                    "_html_polish", "_workbook_style", "csv_to_html",
                    "json_to_html", "text_to_html"}

# Usefulness weighted above raw effort (agreed rubric): a real-data page a
# partner actually uses beats a big page nobody needs. Total = useful*1.5 +
# effort*1.0, scaled to a 0-10 range (max 5*1.5 + 5 = 12.5 → normalize).
_USEFUL_WEIGHT = 1.5
_EFFORT_WEIGHT = 1.0
_TOTAL_MAX = 5.0 * _USEFUL_WEIGHT + 5.0 * _EFFORT_WEIGHT  # 12.5


def _handler_module_map(src: str) -> Dict[str, str]:
    """``_route_<name>`` handler → ui module stem it renders. Most diligence
    (and many other) routes dispatch via ``return self._route_X()`` rather than
    an inline import — without following that hop the ranking silently drops
    them (the crossover bug). Scans each handler body for its ui import."""
    out: Dict[str, str] = {}
    for h in re.finditer(r'def (_route_\w+)\(self', src):
        body = src[h.end():h.end() + 1200]  # handler body window
        imp = re.search(r'from \.ui(?:\.[\w.]+)?\.([\w]+) import', body)
        if imp:
            out[h.group(1)] = imp.group(1)
    return out


def _route_module_map() -> Dict[str, str]:
    """route → ui module stem, from the GET dispatch in server.py.

    Resolves both forms: an inline ``from .ui...import render_X`` near the path,
    AND the handler indirection ``return self._route_X()`` (→ that handler's ui
    import). The second hop surfaces the diligence namespace + ~100 other pages
    the inline-only scan missed (the crossover bug).
    """
    src = _SERVER.read_text(errors="replace")
    mod_by_fn = {fn: mod for mod, fn in
                 re.findall(r'from \.ui(?:\.[\w.]+)?\.([\w]+) import (render_\w+)', src)}
    handler_mod = _handler_module_map(src)
    out: Dict[str, str] = {}
    for m in re.finditer(r'path == "(/[\w\-./]+)"', src):
        seg = src[m.end():m.end() + 400]
        imp = re.search(r'from \.ui(?:\.[\w.]+)?\.([\w]+) import', seg)
        fn = re.search(r'(render_\w+)\(', seg)
        handler = re.search(r'self\.(_route_\w+)\(', seg)
        mod = (imp.group(1) if imp
               else mod_by_fn.get(fn.group(1)) if fn
               else handler_mod.get(handler.group(1)) if handler else None)
        if mod is None:
            # Additive fallback: a few page routes (the diligence ._pages /
            # snapshot_page set, plus pages whose import sits just past the
            # 400-char window after a long comment) still resolve to None above.
            # Recover them — but conservatively, to avoid grabbing a neighbour's
            # import (which silently mis-ranks pages). Two safeguards:
            #   * bound the block to this route's own preamble — the earlier of
            #     the next routing branch (`if/elif path...`) or its first
            #     `return`. Real page routes import-then-render (the
            #     `from .. import render_X` precedes the return, so it survives
            #     the cut); routes that render inline or fan out to a
            #     multi-renderer dict yield an empty preamble and stay None.
            #   * require the import to bind a ``render_*`` name (the same
            #     signal the .ui resolver uses) and accept .diligence.* too.
            #     This rejects helper imports (``from .portfolio_monitor import
            #     PortfolioAsset``) and non-page modules (``surface_status``).
            rest = src[m.end():]
            bounds = [mm.start() for mm in (
                re.search(r'\n\s+(?:el)?if path[ .]', rest),
                re.search(r'\n\s+return ', rest)) if mm]
            block = rest[: min(bounds) if bounds else 600]
            own = re.search(
                r'from \.(?:ui|diligence)(?:\.[\w.]+)?\.([\w]+) import '
                r'(?:\(\s*)?(render_\w+)', block)
            if own:
                mod = own.group(1)
        route = m.group(1)
        if mod and not route.endswith(".csv") and not route.startswith("/api"):
            out.setdefault(route, mod)
    return out


def _module_path(stem: str) -> Optional[pathlib.Path]:
    # .ui first; the diligence page modules (_pages, snapshot_page) live
    # outside ui/ and are searched last so a ui stem always wins a name clash.
    for cand in (_UI / f"{stem}.py", _UI / "data_public" / f"{stem}.py",
                 _UI / "chartis" / f"{stem}.py",
                 _ROOT / "rcm_mc" / "diligence" / f"{stem}.py"):
        if cand.is_file():
            return cand
    return None


def _module_signals(stem: str) -> Tuple[int, bool, bool]:
    """(loc, real_data_backed, has_source_purpose) for a page module."""
    p = _module_path(stem)
    if p is None:
        return 0, False, False
    txt = p.read_text(errors="replace")
    loc = txt.count("\n")
    real = bool(re.search(r"from \.\.data|load_\w+|hcris|cms_|classify_surface|"
                          r"_real|ck_source_purpose|ck_data_universe", txt))
    src_purpose = "ck_source_purpose" in txt
    return loc, real, src_purpose


def _has_test(stem: str) -> bool:
    needle = stem.encode()
    for t in _TESTS.glob("test_*.py"):
        try:
            if needle in t.read_bytes():
                return True
        except OSError:
            continue
    return False


def _effort_score(loc: int, tested: bool) -> float:
    base = (5.0 if loc >= 1500 else 4.0 if loc >= 800 else 3.0 if loc >= 450
            else 2.0 if loc >= 250 else 1.0 if loc >= 100 else 0.5)
    if tested:
        base = min(5.0, base + 0.5)
    return base


def _usefulness_score(tier: str, section: str, src_purpose: bool, real: bool) -> float:
    s = _TIER_USE.get(tier, 0.5)
    if section in _CORE_SECTIONS:
        s += 1.0
    if src_purpose:
        s += 0.5
    if real:
        s += 0.5
    return min(5.0, s)


def build_rankings():
    from rcm_mc.diligence.surface_status import classify_surface
    try:
        from rcm_mc.ui._chartis_kit import _resolve_sub_section
    except Exception:  # noqa: BLE001
        _resolve_sub_section = lambda r: "uncategorized"  # noqa: E731

    rmap = _route_module_map()
    rows = []
    for route, stem in rmap.items():
        if stem in _EXCLUDE_MODULES:
            continue
        loc, real, src_purpose = _module_signals(stem)
        if loc == 0:
            continue
        tier = classify_surface(route).get("tier", "yellow")
        section = _resolve_sub_section(route) or "uncategorized"
        tested = _has_test(stem)
        effort = _effort_score(loc, tested)
        useful = _usefulness_score(tier, section, src_purpose, real)
        rows.append({
            "route": route, "module": stem, "loc": loc, "tier": tier,
            "section": section, "tested": tested, "src_purpose": src_purpose,
            "effort": effort, "useful": useful,
            "total": round(
                (useful * _USEFUL_WEIGHT + effort * _EFFORT_WEIGHT) * 10.0 / _TOTAL_MAX, 1),
        })
    rows.sort(key=lambda r: (-r["total"], -r["loc"]))
    return rows


def _label_map() -> Dict[str, str]:
    """route → human label, from the existing nav rails where available."""
    out: Dict[str, str] = {}
    try:
        from rcm_mc.ui._chartis_kit import _SUB_NAV
        for items in _SUB_NAV.values():
            for it in items:
                if isinstance(it, dict) and it.get("href"):
                    out.setdefault(it["href"], it.get("label", ""))
    except Exception:  # noqa: BLE001
        pass
    return out


# Acronyms / proper casings so front-facing labels read clean, not "Ic Packet".
_ACRONYMS = {
    "ic": "IC", "cms": "CMS", "hcris": "HCRIS", "lp": "LP", "qoe": "QoE",
    "ebitda": "EBITDA", "moic": "MOIC", "snf": "SNF", "irf": "IRF",
    "ltch": "LTCH", "roi": "ROI", "ar": "AR", "rcm": "RCM", "mc": "MC",
    "xray": "X-Ray", "x-ray": "X-Ray", "eu": "EU", "apm": "APM", "ma": "MA",
    "us": "US", "dpi": "DPI", "nav": "NAV", "esg": "ESG",
}


def _derive_label(route: str, labels: Dict[str, str]) -> str:
    if labels.get(route):
        return labels[route]
    seg = route.rstrip("/").split("/")[-1] or route
    words = seg.replace("-", " ").replace("_", " ").split()
    return " ".join(_ACRONYMS.get(w.lower(), w.title()) for w in words)


def _write_manifest(rows: List[dict]) -> pathlib.Path:
    """Emit a cheap, import-only ranked manifest for runtime use by the nav
    rails + section-index pages (so the UI never re-runs the scan)."""
    labels = _label_map()
    by_section: Dict[str, List[dict]] = defaultdict(list)
    for r in rows:
        by_section[r["section"]].append(r)
    lines = [
        '"""AUTO-GENERATED by scripts/rank_surfaces.py — do not edit by hand.',
        "",
        "Ranked PEdesk surfaces per nav section (usefulness-weighted). The nav",
        "rails show the top entries; /best/<section> shows the full ranked list.",
        '"""',
        "from __future__ import annotations",
        "",
        "RANKINGS = {",
    ]
    order = ["source", "pipeline", "diligence", "library", "research",
             "portfolio", "home", "uncategorized"]
    for sec in order:
        secrows = by_section.get(sec) or []
        if not secrows:
            continue
        lines.append(f"    {sec!r}: [")
        for r in secrows:
            lines.append(
                f"        {{'route': {r['route']!r}, "
                f"'label': {_derive_label(r['route'], labels)!r}, "
                f"'total': {r['total']}, 'tier': {r['tier']!r}, "
                f"'effort': {r['effort']}, 'useful': {r['useful']}}},")
        lines.append("    ],")
    lines.append("}")
    lines.append("")
    dest = _ROOT / "rcm_mc" / "ui" / "_surface_rankings.py"
    dest.write_text("\n".join(lines), encoding="utf-8")
    return dest


def _table(rows: List[dict]) -> str:
    head = ("| Route | Page | Tier | Effort | PE-use | **Total** | LOC | Tests |\n"
            "|---|---|---|---:|---:|---:|---:|:--:|\n")
    body = "".join(
        f'| `{r["route"]}` | {r["module"]} | {r["tier"]} | {r["effort"]:.1f} | '
        f'{r["useful"]:.1f} | **{r["total"]:.1f}** | {r["loc"]:,} | '
        f'{"✓" if r["tested"] else "—"} |\n'
        for r in rows
    )
    return head + body


def main() -> int:
    rows = build_rankings()
    by_section: Dict[str, List[dict]] = defaultdict(list)
    for r in rows:
        by_section[r["section"]].append(r)

    out = ["# PEdesk surface rankings\n",
           "_Generated by `scripts/rank_surfaces.py` — do not hand-edit; "
           "rerun to refresh. Deterministic, from real codebase signals._\n",
           "\n## Scoring\n",
           "- **Effort / depth (0-5)** — renderer LOC (≥1500→5, ≥800→4, ≥450→3, "
           "≥250→2, ≥100→1) + 0.5 if it has tests.\n",
           "- **PE / Chartis-advisory usefulness (0-5)** — data-honesty tier "
           "(green 3 · navy 2 · data-required 1.5 · yellow 1) + 1 for a core "
           "deal-workflow section (Source/Diligence/Portfolio/Pipeline) + 0.5 "
           "for a declared source/purpose header + 0.5 for real-data wiring.\n",
           "- **Total = (usefulness × 1.5 + effort × 1.0), normalized to 0-10** (usefulness weighted above effort).**\n",
           f"\nRanked {len(rows)} route-backed page modules.\n"]

    out.append("\n## Top 25 overall (front-facing candidates)\n\n")
    out.append(_table(rows[:25]))

    # Buried gems: strong score but not in a nav section → migration candidates.
    buried = [r for r in rows if r["section"] in ("uncategorized", None)
              and r["total"] >= 7.0]
    out.append(f"\n## Buried gems — strong but not in the nav ({len(buried)})\n")
    out.append("_High-scoring pages that aren't surfaced in a nav section — "
               "the prime candidates to migrate into the bars._\n\n")
    out.append(_table(buried[:25]))

    order = ["source", "pipeline", "diligence", "library", "research",
             "portfolio", "home", "uncategorized"]
    for sec in order:
        secrows = by_section.get(sec) or []
        if not secrows:
            continue
        out.append(f"\n## {sec.title()} ({len(secrows)})\n\n")
        out.append(_table(secrows[:30]))

    dest = _ROOT / "docs" / "rankings" / "PEDESK_SURFACE_RANKINGS.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("".join(out), encoding="utf-8")
    manifest = _write_manifest(rows)
    print(f"Wrote {len(rows)} ranked surfaces → {dest}")
    print(f"Wrote runtime manifest → {manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
