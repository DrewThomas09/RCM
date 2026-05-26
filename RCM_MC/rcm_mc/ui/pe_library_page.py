"""PE Intelligence Library — /diligence/pe-library.

The unified catalog of the pe_intelligence analytic toolkit (~222 modules).
Most of these tools were built and tested but never linked to any UI — this
page makes the whole toolkit discoverable: grouped by category, searchable,
each row showing its purpose, input contract, depth (LOC), and whether it's
already surfaced live. Tools that have a dedicated live page (e.g. the
Reimbursement Cliff Calendar) link straight to it.

Honesty: these are analytic *calculators* — they compute from inputs over
curated/illustrative defaults (the codebase's NAVY convention), not a live
data feed. The page says so up front so a partner never mistakes the library
for sourced evidence. Inline per-tool rendering is wired incrementally (each
tool has a bespoke typed input); this catalog is the backbone they light up in.
"""
from __future__ import annotations

import html as _html
from typing import Dict, List, Optional

from ..pe_intelligence._catalog import CATALOG
from ._chartis_kit import (
    P,
    chartis_shell,
    ck_illustrative_note,
    ck_kpi_block,
    ck_page_title,
    ck_section_header,
    ck_source_purpose,
)

# Tools that already have a dedicated live page — link the title straight there.
_LIVE_ROUTES: Dict[str, str] = {
    "reimbursement_cliff_calendar_2026_2029": "/diligence/cliff-calendar",
    "historical_failure_library": "/diligence/pe-reference?library=failures",
    "partner_traps_library": "/diligence/pe-reference?library=traps",
    "seller_motivation_decoder": "/diligence/pe-reference?library=motivations",
    "failure_archetype_library": "/diligence/pe-reference?library=archetypes",
    "bidder_landscape_reader": "/diligence/pe-reference?library=bidders",
    "banker_narrative_decoder": "/diligence/pe-reference?library=narratives",
}


def _runnable() -> Dict[str, str]:
    """slug → /diligence/pe-tool run URL for tools wired to run on a real deal."""
    try:
        from .pe_tool_page import PE_TOOL_REGISTRY
        return {s: f"/diligence/pe-tool?tool={s}" for s in PE_TOOL_REGISTRY}
    except Exception:  # noqa: BLE001
        return {}


def _categories() -> List[str]:
    seen: List[str] = []
    for r in CATALOG:
        if r["category"] not in seen:
            seen.append(r["category"])
    return sorted(seen)


def _matches(row: Dict, q: str) -> bool:
    if not q:
        return True
    hay = f"{row['title']} {row['purpose']} {row['slug']} {row['category']}".lower()
    return q.lower() in hay


def _tool_row(row: Dict, runnable: Dict[str, str]) -> str:
    run_url = runnable.get(row["slug"])
    live = _LIVE_ROUTES.get(row["slug"])
    if run_url and not live:
        # Wired to run on a real deal — link the title to the tool runner.
        title_cell = (
            f'<a href="{_html.escape(run_url)}" style="color:{P["accent"]};'
            f'text-decoration:none;font-weight:600;">'
            f'{_html.escape(row["title"])} &rarr;</a>'
            f'<span style="font-family:var(--ck-mono);font-size:8.5px;'
            f'font-weight:700;letter-spacing:0.08em;color:{P["accent"]};'
            f'border:1px solid {P["accent"]};border-radius:2px;padding:1px 4px;'
            f'margin-left:7px;">RUN ON DEAL</span>'
        )
    elif live:
        title_cell = (
            f'<a href="{_html.escape(live)}" style="color:{P["accent"]};'
            f'text-decoration:none;font-weight:600;">'
            f'{_html.escape(row["title"])} &rarr;</a>'
            f'<span style="font-family:var(--ck-mono);font-size:8.5px;'
            f'font-weight:700;letter-spacing:0.08em;color:{P["accent"]};'
            f'border:1px solid {P["accent"]};border-radius:2px;padding:1px 4px;'
            f'margin-left:7px;">LIVE</span>'
        )
    elif row["wired"]:
        title_cell = (
            f'<span style="color:{P["text"]};font-weight:600;">'
            f'{_html.escape(row["title"])}</span>'
            f'<span style="font-family:var(--ck-mono);font-size:8.5px;'
            f'letter-spacing:0.08em;color:{P["text_dim"]};border:1px solid '
            f'{P["border"]};border-radius:2px;padding:1px 4px;margin-left:7px;">'
            f'IN DEAL VIEW</span>'
        )
    else:
        title_cell = (
            f'<span style="color:{P["text"]};font-weight:600;">'
            f'{_html.escape(row["title"])}</span>'
            f'<span style="font-family:var(--ck-mono);font-size:8.5px;'
            f'letter-spacing:0.08em;color:{P["text_faint"]};border:1px solid '
            f'{P["border_dim"]};border-radius:2px;padding:1px 4px;margin-left:7px;">'
            f'AVAILABLE</span>'
        )
    in_type = row["input_type"] or "—"
    return (
        f'<tr style="border-bottom:1px solid {P["border_dim"]};">'
        f'<td style="padding:7px 10px;font-size:12px;vertical-align:top;'
        f'white-space:nowrap;">{title_cell}</td>'
        f'<td style="padding:7px 10px;font-size:11.5px;color:{P["text_dim"]};'
        f'line-height:1.5;">{_html.escape(row["purpose"])}</td>'
        f'<td style="padding:7px 10px;font-family:var(--ck-mono);font-size:10px;'
        f'color:{P["text_faint"]};vertical-align:top;white-space:nowrap;">'
        f'{_html.escape(in_type[:28])}</td>'
        f'<td style="padding:7px 10px;font-family:var(--ck-mono);font-size:10.5px;'
        f'color:{P["text_dim"]};text-align:right;vertical-align:top;'
        f'font-variant-numeric:tabular-nums;">{row["loc"]:,}</td>'
        f'</tr>'
    )


def _category_block(category: str, rows: List[Dict],
                    runnable: Dict[str, str]) -> str:
    head = ck_section_header(category.upper(), f"{len(rows)} tools",
                             count=len(rows))
    body = "".join(_tool_row(r, runnable) for r in rows)
    table = (
        f'<div class="ck-panel"><div style="overflow-x:auto;padding:4px 6px;">'
        f'<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr style="border-bottom:2px solid {P["border"]};text-align:left;">'
        + "".join(
            f'<th style="padding:6px 10px;font-family:var(--ck-mono);font-size:9px;'
            f'letter-spacing:0.08em;color:{P["text_faint"]};text-transform:uppercase;'
            f'{al}">{h}</th>'
            for h, al in (("Tool", ""), ("What it does", ""),
                          ("Input", ""), ("LOC", "text-align:right;")))
        + f'</tr></thead><tbody>{body}</tbody></table></div></div>'
    )
    return head + table


def render_pe_library_page(q: str = "", category: str = "") -> str:
    """Render the unified PE Intelligence tool catalog."""
    q = (q or "").strip()
    cats = _categories()
    category = category if category in cats else ""

    rows = [r for r in CATALOG if _matches(r, q)
            and (not category or r["category"] == category)]
    runnable = _runnable()
    live_n = sum(1 for r in CATALOG if r["slug"] in _LIVE_ROUTES)
    run_n = sum(1 for r in CATALOG if r["slug"] in runnable)

    kpis = (
        ck_kpi_block("Tools in toolkit", f"{len(CATALOG):,}",
                     f"{len(cats)} categories")
        + ck_kpi_block("Runnable now", str(live_n + run_n),
                       f"{live_n} dedicated page · {run_n} run on a deal")
        + ck_kpi_block("Showing", f"{len(rows):,}",
                       (f'filtered: "{_html.escape(q)}"' if q else
                        category or "all tools"))
        + ck_kpi_block("Total depth", f"{sum(r['loc'] for r in CATALOG):,}",
                       "lines of analytic code")
    )

    source_purpose = ck_source_purpose(
        purpose=(
            "Browse the full PE-intelligence analytic toolkit — partner reflexes, "
            "calculators, and reference libraries — most of which were built but "
            "never linked. Find the tool you need; live ones open in place."
        ),
        universe="derived",
        confidence="illustrative",
        source="rcm_mc.pe_intelligence (auto-cataloged) — analytic calculators "
               "over curated/illustrative defaults, not a live data feed",
        next_action="Cliff Calendar (live)",
        next_href="/diligence/cliff-calendar",
    )

    # Search + category filter (GET form; read-only filtering).
    cat_links = (
        f'<a href="/diligence/pe-library{("?q="+_html.escape(q)) if q else ""}" '
        f'style="font-family:var(--ck-mono);font-size:10.5px;padding:4px 9px;'
        f'margin:0 5px 5px 0;display:inline-block;border-radius:3px;'
        f'text-decoration:none;border:1px solid '
        f'{P["border"] if category else P["accent"]};'
        f'background:{P["panel"] if category else P["accent"]};'
        f'color:{P["text_dim"] if category else "#fff"};">All</a>'
    )
    for c in cats:
        on = c == category
        href = f"/diligence/pe-library?category={_html.escape(c)}"
        if q:
            href += f"&q={_html.escape(q)}"
        cat_links += (
            f'<a href="{href}" style="font-family:var(--ck-mono);font-size:10.5px;'
            f'padding:4px 9px;margin:0 5px 5px 0;display:inline-block;'
            f'border-radius:3px;text-decoration:none;border:1px solid '
            f'{P["accent"] if on else P["border"]};'
            f'background:{P["accent"] if on else P["panel"]};'
            f'color:{"#fff" if on else P["text_dim"]};">{_html.escape(c)}</a>'
        )
    search = (
        f'<form method="get" action="/diligence/pe-library" '
        f'style="margin:10px 0 6px;">'
        f'<input type="text" name="q" value="{_html.escape(q)}" '
        f'placeholder="Search tools — e.g. covenant, exit, physician, denial…" '
        f'style="width:100%;max-width:460px;padding:8px 12px;font-size:13px;'
        f'border:1px solid {P["border"]};border-radius:3px;'
        f'background:{P["panel"]};color:{P["text"]};font-family:var(--sc-sans);">'
        + (f'<input type="hidden" name="category" value="{_html.escape(category)}">'
           if category else "")
        + f'</form>'
        f'<div style="margin:4px 0 14px;">{cat_links}</div>'
    )

    # Group the (filtered) rows by category, preserving manifest order.
    by_cat: Dict[str, List[Dict]] = {}
    for r in rows:
        by_cat.setdefault(r["category"], []).append(r)
    if by_cat:
        blocks = "".join(_category_block(c, by_cat[c], runnable)
                         for c in sorted(by_cat))
    else:
        blocks = (
            f'<div class="ck-panel" style="padding:24px;text-align:center;'
            f'color:{P["text_dim"]};">No tool matches '
            f'"<b>{_html.escape(q)}</b>". Try a broader term, or clear the '
            f'<a href="/diligence/pe-library" style="color:{P["accent"]};">'
            f'filter</a>.</div>'
        )

    body = (
        ck_page_title(
            "PE Intelligence Library",
            eyebrow="DILIGENCE · TOOLKIT",
            meta=f"{len(CATALOG):,} analytic tools · {len(cats)} categories",
        )
        + ck_illustrative_note("analytic calculators (compute from inputs over "
                               "curated/illustrative defaults — not live data)")
        + source_purpose
        + f'<div class="ck-kpi-grid">{kpis}</div>'
        + search
        + blocks
    )

    return chartis_shell(
        body,
        title="PE Intelligence Library",
        active_nav="/diligence",
    )
