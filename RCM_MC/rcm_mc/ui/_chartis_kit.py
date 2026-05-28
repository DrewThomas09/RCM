"""PE Desk — Chartis Kit (UI v2, editorial rework).

Drop-in replacement for ``rcm_mc/ui/_chartis_kit.py``.

This module is the shared shell used by every page renderer in
``rcm_mc/ui/*.py``. It provides:

- ``chartis_shell(body_html, title, *, active_nav=None, breadcrumbs=None, code=None)``
- ``ck_panel(body_html, *, title=None, code=None)``
- ``ck_table(rows, columns, *, dense=False)``
- ``ck_kpi_block(label, value, *, trend=None, sub=None, code=None)``
- ``ck_signal_badge(text, *, tone='neutral')``  # tone in: positive/warning/negative/critical/neutral
- ``ck_section_header(title, *, eyebrow=None, code=None)``
- ``ck_fmt_currency``, ``ck_fmt_percent``, ``ck_fmt_number``
- ``ck_command_palette(modules)``  # new — ⌘K jump
- Navigation data: ``_CORPUS_NAV`` (active), ``_LEGACY_NAV`` (deprecated)

All public signatures match the previous version. Only the internal
palette, CSS block, top-bar markup, and panel chrome change.
"""

from __future__ import annotations

import html as _html
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# Feature flag — set CHARTIS_UI_V2=0 to fall back to the legacy dark shell.
# ---------------------------------------------------------------------------

# Always-on editorial chrome. The legacy sidebar shell (which the
# CHARTIS_UI_V2=0 env path used to switch to) is no longer reachable
# through the dispatcher — kept as the constant ``True`` so any
# downstream code that still reads the flag for a different purpose
# (e.g. brand.py palette resolution) continues to read True.
UI_V2_ENABLED = True

# ---------------------------------------------------------------------------
# Palette — editorial navy / teal / parchment
# ---------------------------------------------------------------------------

P = {
    # Surfaces
    "bg":          "#f2ede3",   # parchment page bg
    "panel":       "#ffffff",   # white data panels
    "panel_alt":   "#ece5d6",   # bone tint
    "navy":        "#0b2341",   # primary dark
    "ink":         "#061626",   # deepest
    "navy_2":      "#132e53",   # hover / elevated
    "navy_3":      "#1d3c69",   # divider on navy
    "rule":        "#d6cfc0",   # hairline on parchment
    "rule_2":      "#bfb6a2",

    # Text on light
    "text":        "#1a2332",
    "text_dim":    "#465366",
    "text_faint":  "#7a8699",

    # Text on navy
    "on_navy":       "#e9eef5",
    "on_navy_dim":   "#a5b4ca",
    "on_navy_faint": "#6e7e99",

    # Accent — D2: "teal" flipped from bright #2fb3ad mint to
    # #155752 (same as teal_ink) so the Python-side PALETTE
    # mirrors the CSS variable change in chartis_tokens.css.
    # Consolidates accent + ink to one editorial deep teal.
    "teal":     "#155752",
    "teal_2":   "#66c8c3",
    "teal_ink": "#155752",

    # Status
    "positive": "#0a8a5f",
    "warning":  "#b8732a",
    "negative": "#b5321e",
    "critical": "#8a1e0e",
}

# Compatibility aliases — every renderer that was written against
# the legacy P dict (border, accent, brand, etc.) keeps working
# without 500ing on KeyError. The aliases map to the closest
# editorial-palette equivalent. Adding new aliases here is the
# right way to unblock pages that were partially-migrated.
P.update({
    "border":        P["rule"],        # legacy hairline → editorial rule
    "border_dim":    P["rule_2"],
    "accent":        P["teal"],        # legacy accent → editorial teal
    "brand":         P["navy"],        # legacy brand   → editorial navy
    "brand_accent":  P["teal"],        # second legacy alias for brand accent
    "bg_secondary":  P["panel_alt"],
    "row_stripe":    P["panel_alt"],
    # Text aliases used by older renderers
    "text_secondary": P["text_dim"],
    "text_muted":    P["text_dim"],
})

# ---------------------------------------------------------------------------
# Font-family constants — referenced by SVG text elements that
# need a font-family attr (CSS classes don't apply inside SVG
# unless the document's CSS reaches into it). Cycle 29 restores
# these constants that 12 data_public pages still import.
# ---------------------------------------------------------------------------

_MONO = "JetBrains Mono,monospace"
_SANS = "Inter Tight,-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif"


# Cycle 29 — backward-compat helpers for pre-cycle-22 helper names
# that 12+ data_public pages still import directly. ``ck_fmt_moic``
# is a thin formatter; ``ck_fmt_num`` / ``ck_fmt_pct`` aliases get
# defined later (after the underlying ``ck_fmt_number`` /
# ``ck_fmt_percent`` are defined further down in this file).


def ck_fmt_moic(v: Optional[float], *, dash: str = "—") -> str:
    """Backward-compat MOIC formatter — pre-cycle-22 helper name.

    Several data_public pages (ic_memo_page, lp_dashboard_page, and
    siblings) call ``ck_fmt_moic(value)`` to produce ``2.40x`` style
    multiplier text. The helper got renamed during the cycle 6 kit
    refresh; cycle 29 restores it as a thin alias on top of
    ``ck_fmt_number``.
    """
    if v is None:
        return dash
    try:
        return f"{float(v):.2f}x"
    except (TypeError, ValueError):
        return dash

# ---------------------------------------------------------------------------
# Navigation — top bar primary + Platform Index secondary
# ---------------------------------------------------------------------------

# Each section's nav click lands on its grouped catalog (the /diligence
# pattern) — "they should all have pages like this when you click on that".
# Diligence keeps its dedicated /diligence catalog; the others use the section
# catalog at /best/<key>. The functional pages (target-screener, pipeline,
# portfolio, …) remain the first links inside each catalog and in the mega-menu.
_CORPUS_NAV = [
    {"label": "Home",      "href": "/home",      "key": "home"},
    {"label": "Source",    "href": "/best/source", "key": "source"},
    {"label": "Pipeline",  "href": "/best/pipeline",  "key": "pipeline"},
    {"label": "Diligence", "href": "/diligence", "key": "diligence"},
    {"label": "Library",   "href": "/best/library",   "key": "library"},
    {"label": "Research",  "href": "/best/research",   "key": "research"},
    {"label": "Portfolio", "href": "/best/portfolio", "key": "portfolio"},
]

# Per-section sub-nav. Surfaces the most-clicked second-level pages
# directly under the topbar so a partner doesn't have to drill into
# section landing pages to find common surfaces.
_SUB_NAV = {
    "home": [
        {"label": "Command Center",      "href": "/app"},
        {"label": "My Dashboard",        "href": "/my/AT"},
        {"label": "Alerts",              "href": "/alerts"},
        {"label": "Escalations",         "href": "/escalations"},
        {"label": "Watchlist",           "href": "/watchlist"},
    ],
    # Source = target/opportunity discovery (CMS/market). Deal Sourcing anchors
    # it; PR E folds Hospital + Predictive screeners into a unified Target
    # Screener here. Conferences moved in from Pipeline (it's a sourcing surface).
    "source": [
        {"label": "Target Screener",     "href": "/target-screener"},
        {"label": "Deal Sourcing",       "href": "/source"},
        {"label": "Geographic Intel",    "href": "/geo-intel"},
        {"label": "Thesis Screening",    "href": "/deal-screening"},
        {"label": "Conferences",         "href": "/conferences"},
    ],
    # Pipeline = real opportunities/deals only — the deal-workflow surfaces.
    # Market-discovery screeners live in Source (Target Screener); the
    # CMS/HCRIS screener routes (/screen, /predictive-screener) are unchanged
    # and reached from there. PE Intelligence moved to Research.
    "pipeline": [
        {"label": "Deal Pipeline",       "href": "/pipeline"},
        {"label": "New Deal / Import",   "href": "/new-deal"},
        {"label": "Deal Quality",        "href": "/deal-quality"},
        {"label": "Deal Risk",           "href": "/deal-risk-scores"},
        {"label": "Deal-Flow Heatmap",   "href": "/deal-flow-heatmap"},
        {"label": "EBITDA Bridge",       "href": "/pipeline/bridge"},
    ],
    "library": [
        {"label": "Deal Library",        "href": "/deal-library"},
        {"label": "Deals Library",       "href": "/deals-library"},
        {"label": "Methodology",         "href": "/methodology"},
        {"label": "Metric Glossary",     "href": "/metric-glossary"},
        {"label": "RCM Benchmarks",      "href": "/rcm-benchmarks"},
        {"label": "Data Catalog",        "href": "/data"},
        {"label": "Comparables",         "href": "/comparables"},
        {"label": "Market Rates",        "href": "/market-rates"},
    ],
    # Research — 10 analytical + catalog surfaces. Mirrors the
    # diligence trim: rendering all ten in the sub-nav strip
    # crowded the topbar to the point of wrapping on common
    # laptop widths. Trimmed to the five daily-driver workbench
    # surfaces (analyst voice + the four most-read benchmarking
    # / momentum reads) plus an "All Research →" link to the
    # /research index, which now surfaces every dropped item
    # (Comparable Outcomes, Bear Cases, Reg Calendar, Corpus
    # Backtest, Backtest) alongside the original catalog.
    "research": [
        {"label": "Industry Intelligence", "href": "/industry"},
        {"label": "Market Intel (Geographic)", "href": "/market-intel/geo"},
        {"label": "Deal Corpus Analytics", "href": "/deal-corpus-analytics"},
        {"label": "Find Comps",          "href": "/find-comps"},
        {"label": "Sponsor Track Record","href": "/sponsor-track-record"},
        {"label": "Payer Intelligence",  "href": "/payer-intelligence"},
        {"label": "PE Intelligence",     "href": "/pe-intelligence"},
        {"label": "Notes",               "href": "/notes"},
        {"label": "Sector Momentum",     "href": "/sector-momentum"},
        {"label": "Market Intel",        "href": "/market-intel"},
        {"label": "All Research →",      "href": "/research"},
    ],
    # Portfolio = the user's actual book. "Portfolio Analytics" was a 655-deal
    # benchmark CORPUS mislabeled as portfolio — moved to Research as
    # "Deal Corpus Analytics" (/portfolio-analytics redirects there).
    # Portfolio = the user's actual book only. Sponsor Track Record + Payer
    # Intelligence are reference/corpus data (not user-specific) — moved to
    # Research. Deal Corpus Analytics moved to Research in PR C.
    "portfolio": [
        {"label": "Portfolio Map",       "href": "/portfolio/map"},
        {"label": "Heatmap",             "href": "/portfolio/heatmap"},
        {"label": "Risk Scan",           "href": "/portfolio/risk-scan"},
        {"label": "LP Update",           "href": "/lp-update"},
    ],
    # Diligence — RCM analyst playbook surfaces. The full diligence
    # tab carries 25 pages spanning the four-phase flow (intake →
    # analysis → risk → output); rendering all of them in the sub-nav
    # strip created an unreadable wall of links that wrapped or
    # overflowed in the topbar. Trimmed to the five highest-traffic
    # workbench surfaces (covering identity → ingest → baseline →
    # drill-down → deliverable) plus an "All Diligence →" link that
    # routes to /diligence (the existing diligence_index_page which
    # already grids every tab). The Cmd-K palette (_DEFAULT_PALETTE_
    # MODULES) and the breadcrumb resolver (_SUB_SECTION_MAP) still
    # cover the full surface; sub-nav is only the daily-driver shortcut.
    "diligence": [
        {"label": "Deal Profile",       "href": "/diligence/deal"},
        {"label": "Ingestion",          "href": "/diligence/ingest"},
        {"label": "Benchmarks",         "href": "/diligence/benchmarks"},
        {"label": "CMS X-Ray",          "href": "/diligence/xray"},
        {"label": "HCRIS X-Ray",        "href": "/diligence/hcris-xray"},
        {"label": "QoE Memo",           "href": "/diligence/qoe-memo"},
        {"label": "Cliff Calendar",     "href": "/diligence/cliff-calendar"},
        {"label": "PE Intel Library",   "href": "/diligence/pe-library"},
        {"label": "All Diligence →",    "href": "/diligence"},
    ],
}

# Featured left panel for each section's mega-menu — the "what is this section"
# card. Honest, descriptive copy only (no fabricated stats). `href` points at
# the section landing so the panel doubles as the "open the whole section" CTA.
_SECTION_FEATURE = {
    "home": {"eyebrow": "SECTION · HOME", "title": "Operations",
             "blurb": "Your daily driver — alerts, escalations, watchlist, and "
                      "the Command Center in one canvas.", "href": "/app"},
    "source": {"eyebrow": "SECTION · SOURCE", "title": "Target discovery",
               "blurb": "Find targets across every public CMS/provider universe "
                        "— the Target Screener workbench (map, table, compare, "
                        "just-missed, saved screens) plus conferences.",
               "href": "/target-screener"},
    "pipeline": {"eyebrow": "SECTION · PIPELINE", "title": "Live deals",
                 "blurb": "Track real opportunities once promoted from Source — "
                          "screen, score, and move deals toward IC.",
                 "href": "/pipeline"},
    "diligence": {"eyebrow": "SECTION · DILIGENCE", "title": "The analyst playbook",
                  "blurb": "Run a live deal end to end: identity, ingestion, "
                           "benchmarks, the CMS / HCRIS X-Ray, and the QoE memo.",
                  "href": "/diligence"},
    "library": {"eyebrow": "SECTION · LIBRARY", "title": "Reference desk",
                "blurb": "Methodology, the metric glossary, RCM benchmarks, the "
                         "data catalog, comps, and market rates.", "href": "/library"},
    "research": {"eyebrow": "SECTION · RESEARCH", "title": "House views",
                 "blurb": "The analyst notebook plus sector momentum, IRR "
                          "dispersion, hold analysis, and market intel.",
                 "href": "/research"},
    "portfolio": {"eyebrow": "SECTION · PORTFOLIO", "title": "The active book",
                  "blurb": "Monitor holdings by geography and risk — map, "
                           "heatmap, risk scan, analytics, and LP reporting.",
                  "href": "/portfolio"},
}

# Routes that appear in the ranking manifest but are NOT navigable bare-GET
# pages (form-POST targets / redirects that 303 on a plain click). They must
# never become a mega-menu leaf — clicking would bounce. The canonical page is
# surfaced instead (e.g. /new-deal, not its /new-deal/manual POST target).
_NAV_NONNAVIGABLE = frozenset({
    "/new-deal/manual",   # manual-entry POST target → 303 on GET; use /new-deal
})


def _ranked_subnav_items(sect: str):
    """The section's top-6 surfaces by the surface ranking, for the nav bar.
    Returns (items, has_more) where each item is {label, href}.

    Drawn from the FULL ranked manifest (not just the hand-curated _SUB_NAV) so
    a bar genuinely leads with its best pages — including strong pages that were
    never wired into the curated rail (the diligence crossover gap). Front-
    facing gate: only green/navy/data-required tiers (illustrative/placeholder
    demoted to the ranked /best/<section> index, reachable via "More →").
    Curated labels/descriptions win where available (vetted copy); otherwise the
    manifest's derived label is used. Falls back to the curated rail if the
    manifest has no entry, so a bar is never empty.
    """
    cur = {s["href"]: s for s in _SUB_NAV.get(sect, []) if isinstance(s, dict)}
    try:
        from ._surface_rankings import RANKINGS
        ranked = list(RANKINGS.get(sect, []))
    except Exception:  # noqa: BLE001
        ranked = []
    strong = [r for r in ranked
              if r.get("tier") in ("green", "navy", "data_required")]
    pool = strong or ranked
    # Dedupe alias routes for the same page (e.g. /regulatory-calendar and
    # /diligence/regulatory-calendar) by label, keeping the highest-ranked —
    # so a bar never shows the same destination twice. Skip "All X →" sentinel
    # links (they aren't real leaves; the mega-menu has its own all-tools CTA).
    top, seen = [], set()

    def _add(label: str, href: str) -> None:
        label = (label or "").strip()
        key = label.lower()
        if (not label or not href or key in seen or "→" in label
                or href in _NAV_NONNAVIGABLE):
            return
        seen.add(key)
        top.append({"label": label, "href": href})

    for r in pool:
        c = cur.get(r["route"], {})
        _add(c.get("label") or r.get("label") or r["route"], r["route"])
        if len(top) >= 6:
            break
    # Backfill to a fuller bar (target 4-6 destinations) from the curated rail
    # when the strong-ranked pool is short, so every section button opens a
    # populated mega-menu rather than 2-3 lonely links. GATED to real tiers
    # (green / navy / data_required): never pad the prime nav with yellow
    # (illustrative seed-corpus) or red (synthetic) pages — that honesty gate is
    # foundational ("front facing shows real things"); illustrative surfaces
    # stay demoted to the ranked /best/<section> index with their tier dot.
    if len(top) < 6:
        try:
            from rcm_mc.diligence.surface_status import classify_surface as _cls
        except Exception:  # noqa: BLE001
            _cls = None
        for s in _SUB_NAV.get(sect, []):
            if not isinstance(s, dict):
                continue
            href = s.get("href", "")
            if _cls is not None and _cls(href).get("tier") not in (
                    "green", "navy", "data_required"):
                continue
            _add(s.get("label", ""), href)
            if len(top) >= 6:
                break
    if not top:  # manifest + curated both empty — nothing to show
        top = [s for s in _SUB_NAV.get(sect, []) if isinstance(s, dict)][:6]
    has_more = len(ranked) > len(top) or len(cur) > len(top)
    return top, has_more


# One-line description per sub-nav page, keyed by href (used in the mega-menu
# items so each link reads like a real destination, not a bare label). Kept
# separate from _SUB_NAV so that structure stays untouched.
_NAV_DESC = {
    "/app": "Glance-level morning brief", "/my/AT": "Your owned deals & pulse",
    "/alerts": "Fire / ack / snooze lifecycle", "/escalations": "What needs a partner",
    "/watchlist": "Starred deals to track",
    "/target-screener": "Target screening workbench — 9 universes", "/source": "Thesis-driven sourcing",
    "/screen": "Hospital target screener",
    "/predictive-screener": "Model-ranked candidates", "/pe-intelligence": "Sponsor & deal intel",
    "/deal-screening": "Thesis-testing workspace", "/find-comps": "Comparable transactions",
    "/conferences": "Industry conference tracker",
    "/new-deal": "Create opportunity / import", "/deal-quality": "Score a target",
    "/deal-risk-scores": "What can go wrong", "/deal-flow-heatmap": "Flow by stage",
    "/pipeline/bridge": "Value-creation bridge",
    "/deal-library": "Licensed sponsor-backed company universe",
    "/deals-library": "The deal archive", "/methodology": "How the models work",
    "/metric-glossary": "Every metric, defined", "/rcm-benchmarks": "RCM performance bands",
    "/data": "CMS public-data catalog", "/comparables": "Comp sets & multiples",
    "/market-rates": "Payer & Medicare rates",
    "/notes": "The analyst notebook", "/sector-momentum": "Where sectors are moving",
    "/irr-dispersion": "Return dispersion reads", "/hold-analysis": "Hold-period analytics",
    "/market-intel": "Market structure & HHI", "/research": "Every research surface →",
    "/portfolio/map": "Exposure by geography", "/portfolio/heatmap": "Risk × dimension grid",
    "/portfolio/risk-scan": "Portfolio-wide risk flags",
    "/deal-corpus-analytics": "Benchmark corpus scorecard",
    "/sponsor-track-record": "Sponsor performance", "/payer-intelligence": "Payer mix & leverage",
    "/lp-update": "LP-ready digest",
    "/diligence/deal": "Deal profile & identity", "/diligence/ingest": "835/837 ingestion",
    "/diligence/benchmarks": "Peer benchmark grid", "/diligence/xray": "CMS provider X-Ray",
    "/diligence/hcris-xray": "HCRIS hospital X-Ray", "/diligence/qoe-memo": "Quality-of-earnings memo",
    "/diligence": "Every diligence surface →",
}

# Legacy navigation kept for callers that haven't migrated.
_LEGACY_NAV = [
    {"label": "Deals",        "href": "/deals",        "key": "deals"},
    {"label": "Analysis",     "href": "/analysis",     "key": "analysis"},
    {"label": "Portfolio",    "href": "/portfolio",    "key": "portfolio"},
    {"label": "Market",       "href": "/market",       "key": "market"},
    {"label": "PE Intel",     "href": "/pe-intelligence", "key": "pe"},
    {"label": "Corpus",       "href": "/corpus-backtest", "key": "corpus"},
    {"label": "Telehealth Econ", "href": "/telehealth-econ", "key": "tele"},
    {"label": "Admin",        "href": "/users",        "key": "admin"},
]

# ---------------------------------------------------------------------------
# Formatting helpers — signatures unchanged
# ---------------------------------------------------------------------------

def ck_fmt_currency(v: Optional[float], *, precision: int = 0, dash: str = "—") -> str:
    if v is None:
        return dash
    try:
        if abs(v) >= 1e9:
            return f"${v / 1e9:.2f}B"
        if abs(v) >= 1e6:
            return f"${v / 1e6:.1f}M"
        if abs(v) >= 1e3:
            return f"${v / 1e3:.0f}K"
        return f"${v:,.{precision}f}"
    except Exception:
        return dash


def ck_fmt_percent(v: Optional[float], *, precision: int = 1, dash: str = "—") -> str:
    """Format a RATIO as a percent string. ``0.05`` → ``"5.0%"``.

    NOTE the semantic split with ``_ui_kit.fmt_pct`` — that helper
    treats its input as already-percent-scaled (``5.0`` → ``"5.0%"``).
    If a page mixes the two on the same value, partners will see the
    metric rendered 100× off in one cell. Use ``ck_fmt_percent`` for
    raw ratios; reach for ``fmt_pct`` only when you already have a
    pre-multiplied percent value in hand.
    """
    if v is None:
        return dash
    try:
        return f"{v * 100:.{precision}f}%"
    except Exception:
        return dash


def ck_fmt_number(v: Optional[float], *, precision: int = 0, dash: str = "—") -> str:
    if v is None:
        return dash
    try:
        return f"{v:,.{precision}f}"
    except Exception:
        return dash


# Cycle 29 — backward-compat aliases for pre-cycle-22 names. Defined
# AFTER the underlying functions so the rebind succeeds. 12+
# data_public pages import these names directly; renaming each call
# site is a future-cycle cleanup.
ck_fmt_num = ck_fmt_number
ck_fmt_pct = ck_fmt_percent


# ---------------------------------------------------------------------------
# Panel primitives
# ---------------------------------------------------------------------------

class SafeHtml(str):
    """Marker that says: this string is already safe HTML — skip escape.

    Kit helpers that emit pre-escaped markup (provenance tooltip,
    arrow links, etc.) return this so downstream call sites that pass
    the value through ``_esc`` don't double-escape the inner tags.
    """


def _esc(x) -> str:
    if x is None:
        return ""
    if isinstance(x, SafeHtml):
        return str(x)
    return _html.escape(str(x), quote=True)


def ck_panel(
    body_html: str,
    *,
    title: Optional[str] = None,
    code: Optional[str] = None,
    anchor_id: Optional[str] = None,
) -> str:
    """White panel with navy header strip and optional [CODE] tag.

    ``anchor_id`` adds an ``id="..."`` to the wrapping ``<section>`` so
    ``ck_sticky_toc`` can link directly to this panel via ``#<id>``.
    Pages with sticky TOCs pass slugified versions of their section
    titles ("1-target-overview"); ck_panel emits the id literally so
    callers control the URL fragment.
    """
    head = ""
    if title or code:
        # Pre-build the code chip outside the f-string so the
        # nested quotes don't trip Python 3.11/3.12's parser
        # ("SyntaxError: f-string expression part cannot include
        # a backslash"). 3.12.0+ relaxed this via PEP 701, but
        # CI runs against 3.11 too — keep this stdlib-safe.
        title_html = _esc(title) if title else ""
        code_chip = (
            '<div class="ck-panel-code">[' + _esc(code) + ']</div>'
            if code else ""
        )
        head = (
            '<div class="ck-panel-head">'
            f'<div class="ck-panel-title">{title_html}</div>'
            f'{code_chip}'
            "</div>"
        )
    id_attr = f' id="{_esc(anchor_id)}"' if anchor_id else ""
    return (
        f'<section class="ck-panel"{id_attr}>'
        f'{head}<div class="ck-panel-body">{body_html}</div>'
        '</section>'
    )


def ck_section_header(
    title: str,
    eyebrow: Optional[str] = None,
    count: Optional[Any] = None,
    *,
    code: Optional[str] = None,
) -> str:
    """Editorial section header — eyebrow + title + optional count badge.

    Accepts the legacy 3-positional form
    ``ck_section_header(title, subtitle, count)`` used by ~30 page
    renderers carried over from the Bloomberg-era kit (the legacy
    ``subtitle`` argument is rendered as the editorial eyebrow row),
    plus the keyword form ``ck_section_header(title, eyebrow=..., count=...)``.
    ``code`` remains keyword-only for debug overlays.
    """
    eb = f'<div class="sc-eyebrow">{_esc(eyebrow)}</div>' if eyebrow else ""
    cd = f'<div class="ck-section-code">[{_esc(code)}]</div>' if code else ""
    count_html = (
        f'<span class="ck-section-count">{_esc(count)}</span>'
        if count is not None and count != "" else ""
    )
    return (
        '<header class="ck-section-header">'
        f'{eb}<h2 class="sc-h2">{_esc(title)}{count_html}</h2>{cd}'
        "</header>"
    )


def ck_table(
    rows: Sequence[Mapping[str, object]],
    columns: Sequence[Mapping[str, str]],
    *,
    dense: bool = False,
) -> str:
    """Emit a Bloomberg-density table with tabular-nums numerics.

    ``columns`` is a list of ``{"key": "ebitda", "label": "EBITDA",
    "align": "right", "kind": "currency"}`` dicts. ``kind`` is optional
    and hints at cell formatting.
    """
    cls = "ck-table" + (" ck-dense" if dense else "")
    header_cells = "".join(
        f'<th class="align-{_esc(c.get("align", "left"))}">{_esc(c.get("label", ""))}</th>'
        for c in columns
    )
    body_rows = []
    for r in rows:
        cells = []
        for c in columns:
            key = c.get("key", "")
            raw = r.get(key) if hasattr(r, "get") else None
            kind = c.get("kind", "")
            if kind == "currency":
                val = ck_fmt_currency(raw)
            elif kind == "percent":
                val = ck_fmt_percent(raw)
            elif kind == "number":
                val = ck_fmt_number(raw)
            else:
                val = _esc(raw if raw is not None else "—")
            num_cls = " sc-num" if kind in ("currency", "percent", "number") else ""
            cells.append(
                f'<td class="align-{_esc(c.get("align", "left"))}{num_cls}">{val}</td>'
            )
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        f'<table class="{cls}">'
        f"<thead><tr>{header_cells}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


def ck_kpi_block(
    label: str,
    value: str,
    sub: Optional[str] = None,
    trend: Optional[str] = None,
    *,
    code: Optional[str] = None,
    unit: Optional[str] = None,    # legacy alias for ``sub``
    delta: Optional[str] = None,   # legacy alias for ``trend``
    help: Optional[Mapping[str, str]] = None,
    chart: Optional[str] = None,
) -> str:
    """Editorial KPI block — label / value / optional sub / optional trend.

    Accepts the legacy 4-positional form ``ck_kpi_block(label, value,
    sub, trend)`` used by ~80 page renderers carried over from the
    Bloomberg-era kit, as well as the keyword form
    ``ck_kpi_block(label, value, sub=..., trend=...)``. Empty strings
    in ``sub`` / ``trend`` render as no-ops — legacy callers pass ``""``
    rather than ``None`` when a slot is unused. ``code`` remains
    keyword-only; only debug overlays use it.

    A handful of legacy callers used ``unit=``/``delta=`` instead of
    ``sub=``/``trend=`` (cycle 40-45 prod-bug fixes). Accept both so a
    forgotten file doesn't 500 the page — sub/trend take precedence
    when both are provided.

    ``help`` is an optional mapping with keys ``definition`` (required
    when help is set) and ``citation`` (optional). When provided, the
    KPI label is wrapped in ``ck_help_tooltip`` so partners hovering
    or focusing the ``[?]`` affordance see an editorial gloss. Use it
    on jargon-heavy labels (NPR, EV/EBITDA TTM, conformal band).

    ``chart`` is optional pre-rendered HTML (typically a ``ck_sparkline``
    call) that renders below the value/sub. Use on KPIs where the
    trajectory matters as much as the headline number (revenue CAGR,
    margin trend, denial-rate slope).
    """
    if sub is None and unit is not None:
        sub = unit
    if trend is None and delta is not None:
        trend = delta
    # B2 EXEMPT: value, sub, and trend fields are server-rendered
    # trusted markup (inline styling spans for color/pos/neg/warn,
    # source_tag badges, formatted numerics). _esc() is NOT applied
    # to these three fields — partner pages routinely pass HTML like
    # `<span style="color:var(--cad-pos);">+$42M</span>` or
    # `<span class="mn">365</span>` for inline formatting. Pre-B2,
    # _esc on these fields was rendering the markup as literal text
    # on EBITDA Bridge, Market Rates, Sponsor League, CMS Sources,
    # etc. — the audit's "literal HTML in stat values" symptom.
    # User input MUST NEVER reach value/sub/trend; verify all call
    # sites pass only server-generated strings. Two call sites that
    # passed deal_name were patched to escape upstream as part of
    # this PR (ic_memo_generator_page.py:155-156,
    # deal_postmortem_page.py:161). label + code remain escaped —
    # plain-text fields, no HTML pattern. See CLAUDE.md
    # "html.escape every user input" guardrail — this is the
    # documented exception.
    trend_html = ""
    if trend:
        tone = "positive" if trend.startswith("+") else "negative" if trend.startswith("-") else "neutral"
        trend_html = f'<span class="ck-kpi-trend tone-{tone}">{trend}</span>'
    sub_html = f'<div class="ck-kpi-sub">{sub}</div>' if sub else ""
    code_html = f'<div class="ck-kpi-code">[{_esc(code)}]</div>' if code else ""
    if help and help.get("definition"):
        label_html = ck_help_tooltip(
            label,
            help["definition"],
            citation=help.get("citation"),
        )
    else:
        label_html = _esc(label)
    chart_html = (
        f'<div class="ck-kpi-chart">{chart}</div>' if chart else ""
    )
    return (
        '<div class="ck-kpi">'
        f'{code_html}'
        f'<div class="ck-kpi-label">{label_html}</div>'
        f'<div class="ck-kpi-value sc-num">{value}{trend_html}</div>'
        f'{sub_html}'
        f'{chart_html}'
        "</div>"
    )


def ck_signal_badge(text: str, *, tone: str = "neutral") -> str:
    tone = tone if tone in ("positive", "warning", "negative", "critical", "neutral") else "neutral"
    return f'<span class="ck-badge tone-{tone}">{_esc(text)}</span>'


# Data-universe label chips. Every confusing page should declare WHICH data
# universe it shows so a partner never mistakes a benchmark corpus for their
# own portfolio (see docs/PEDESK_ROUTE_TAXONOMY.md). Self-describing tooltip.
_DATA_UNIVERSE = {
    "user-deals":     ("USER DEALS", "deals",
                       "Your fund's actual opportunity/deal records."),
    "user-portfolio": ("USER PORTFOLIO", "port",
                       "Your fund's actual owned portfolio holdings."),
    "cms":            ("CMS PUBLIC DATA", "cms",
                       "Public CMS provider/facility data — the market, not your deals."),
    "corpus":         ("BENCHMARK CORPUS", "corpus",
                       "Historical benchmark deal corpus for comparison — NOT your portfolio."),
    "research":       ("RESEARCH REFERENCE", "ref",
                       "Reference intelligence (payer/sponsor/sector) — not user-specific."),
    "mixed":          ("MIXED DATA", "mixed",
                       "Combines universes — each section is labeled separately."),
    # HCRIS is CMS public data, called out separately because the HCRIS X-Ray
    # gold-standard pulls it directly.
    "hcris":          ("HCRIS PUBLIC DATA", "cms",
                       "CMS HCRIS Medicare cost-report data — public, not your deals."),
    # Diligence-reform confidence states (data-source matrix).
    "derived":        ("DERIVED", "deals",
                       "Computed from real values (assumptions labeled)."),
    "illustrative":   ("ILLUSTRATIVE", "illus",
                       "Hardcoded demo values — NOT a real source. Illustrative "
                       "framework until a live data source is connected."),
    "data-required":  ("DATA REQUIRED", "datareq",
                       "Needs a user upload / CCD / internal file to activate."),
    "experimental":   ("EXPERIMENTAL", "exp",
                       "Real source exists but coverage/method is partial — caveated."),
    # Licensed third-party data, used only as derived/structured facts (raw
    # reports/exports never served). Distinct from public CMS/research.
    "licensed-report-derived": ("LICENSED REPORT", "ref",
                       "Derived from a licensed industry report (e.g. IBISWorld) — "
                       "structured facts only; the raw report is never served."),
    "licensed-market-derived": ("LICENSED MARKET DATA", "ref",
                       "Derived from a licensed market-data export (e.g. "
                       "SimplyAnalytics) — area-level, not your deals; unexported "
                       "variables show EXPORT REQUIRED, never fabricated."),
}


def ck_data_universe(kind: str) -> str:
    """A small mono chip naming the page's data universe / confidence.

    ``kind`` ∈ user-deals · user-portfolio · cms · hcris · corpus · research ·
    mixed · derived · illustrative · data-required · experimental ·
    licensed-report-derived · licensed-market-derived. Renders
    nothing for an unknown kind (fail-safe). Style lives in the global shell
    CSS (`.ck-universe`)."""
    rec = _DATA_UNIVERSE.get(kind)
    if rec is None:
        return ""
    label, cls, tip = rec
    return (f'<span class="ck-universe ck-universe-{cls}" title="{_esc(tip)}">'
            f'{_esc(label)}</span>')


def ck_source_purpose(*, purpose: str, universe: str, source: str,
                      confidence: str = "", next_action: str = "",
                      next_href: str = "") -> str:
    """Diligence source-and-purpose header band.

    Declares, for any analyzer/diligence page: what decision it supports
    (purpose), which data universe + confidence it uses (chips), the named
    source, and the next action. The reform contract requires every Diligence
    page to carry one so a deal team never mistakes an illustrative model for
    live evidence. ``universe``/``confidence`` are ck_data_universe kinds."""
    chips = ck_data_universe(universe)
    if confidence and confidence != universe:
        chips += ck_data_universe(confidence)
    src = (f'<span class="ck-sp-src"><b>Source:</b> {_esc(source)}</span>'
           if source else "")
    nxt = ""
    if next_action:
        nxt = (f'<a class="ck-sp-next" href="{_esc(next_href or "#")}">'
               f'{_esc(next_action)} &rarr;</a>') if next_href else (
               f'<span class="ck-sp-next">{_esc(next_action)}</span>')
    return (
        '<div class="ck-sp">'
        f'<div class="ck-sp-chips">{chips}</div>'
        f'<p class="ck-sp-purpose">{_esc(purpose)}</p>'
        f'<div class="ck-sp-meta">{src}{nxt}</div>'
        '</div>'
    )


def ck_illustrative_note(what: str = "figures") -> str:
    """Honest provenance marker for curated / illustrative tracker pages.

    Many ``data_public`` tracker pages render realistic-looking numbers
    built from hardcoded dataclass lists — the analytic *surface* built
    ahead of the live-data wiring (see docs/PEDESK_UNDERSTANDING/08).
    This marker states that plainly so a partner / LP never mistakes an
    illustrative template for this portfolio's sourced, live data.

    ``what`` names the kind of figure shown (e.g. "savings figures",
    "fund cashflows") for a slightly more specific sentence. Renders a
    calm, non-alarming disclosure strip (a note, not an error) with a
    self-contained style block — call it once per page, near the title.
    """
    return (
        "<style>"
        ".ck-illus-note{display:flex;align-items:baseline;gap:10px;"
        "flex-wrap:wrap;margin:0 0 var(--sc-s-5,16px);padding:9px 14px;"
        "background:var(--sc-parchment-2,#efe9dd);"
        "border:1px solid var(--sc-rule,#d6cfc0);"
        "border-left:3px solid var(--sc-warning,#b8732a);border-radius:2px;}"
        ".ck-illus-note-tag{font-family:var(--sc-mono,monospace);font-size:10px;"
        "font-weight:700;letter-spacing:0.1em;text-transform:uppercase;"
        "color:var(--sc-warning,#b8732a);white-space:nowrap;}"
        ".ck-illus-note-body{font-family:var(--sc-sans,sans-serif);font-size:12px;"
        "line-height:1.5;color:var(--sc-text-dim,#465366);}"
        "</style>"
        '<div class="ck-illus-note" role="note">'
        '<span class="ck-illus-note-tag">Illustrative template</span>'
        f'<span class="ck-illus-note-body">Representative {_esc(what)} for '
        "layout and methodology — not this portfolio's live, sourced data.</span>"
        "</div>"
    )


# ── Route-level illustrative banner ──────────────────────────────────
#
# The ``data_public`` analyzer surface (~158 routes) renders realistic-looking
# numbers from the bundled illustrative deal corpus (``data_public``
# ``_SEED_DEALS`` / ``extended_seed*``) or modeled assumptions — NOT the
# user's ingested portfolio. ``chartis_shell`` auto-injects ONE honest
# disclosure per page for any route in this registry so a partner never
# mistakes the template for live, sourced data.
#
# Idempotent: ``chartis_shell`` skips injection when the page already rendered
# its own ``ck-illus-note`` (e.g. the per-page labels in PRs 7/9/10).
# DELIBERATELY EXCLUDED (they carry their own per-state provenance):
#   /payer-stress, /cost-structure, /debt-service — show real HCRIS data when a
#     CCN is attached, illustrative only on degrade;
#   /cms-apm — curated public CMMI catalog + its own scoped illustrative overlay.
#   /scenario-mc — a live Monte-Carlo calculator on user inputs (deep-traced);
#   /tax-structure-analyzer — a pure calculator on user inputs (deep-traced);
#   /base-rates — a live/calc page (deep-traced).
# Genuinely-real reference pages are excluded — /cms-sources (real CMS API
# catalog), /cms-data-browser (real HCRIS/DRG samples), /module-index (nav),
# /data-sources-admin (loaded-data status). NOTE: /corpus-dashboard and
# /corpus-coverage ARE included — they present analytics over the illustrative
# seed corpus, so they carry the disclosure too.
# (The scenario-mc / tax-structure-analyzer exclusions match the prior
# deep-trace pinned by tests/test_curated_illustrative_note.py.)
#
# Regenerate the set with the scan in tests/test_route_illustrative_banner.py.
_ILLUSTRATIVE_ANALYZER_ROUTES = frozenset({
    "/aco-economics", "/acq-timing", "/ai-operating-model", "/antitrust-screener",
    "/backtest", "/backtester", "/biosimilars",
    "/board-governance", "/bolton-analyzer", "/cap-structure", "/capex-budget",
    "/capital-call", "/capital-efficiency", "/capital-pacing", "/capital-schedule",
    "/cin-analyzer", "/clinical-ai", "/clinical-outcomes", "/coinvest-pipeline",
    "/comparables", "/competitive-intel", "/compliance-attestation", "/concentration-risk",
    "/continuation-vehicle", "/corpus-coverage", "/corpus-dashboard", "/corpus-ic-memo",
    "/covenant-headroom", "/covenant-monitor",
    "/cyber-risk", "/deal-flow-heatmap", "/deal-origination", "/deal-pipeline",
    "/deal-postmortem", "/deal-quality", "/deal-risk-scores", "/deal-search",
    "/deal-sourcing", "/debt-financing", "/demand-forecast", "/denovo-expansion",
    "/digital-front-door", "/diligence-vendors", "/direct-employer", "/direct-lending",
    "/dividend-recap", "/dpi-tracker", "/drug-shortage", "/earnout",
    "/entry-multiple", "/escrow-earnout", "/esg-dashboard", "/esg-impact",
    "/exit-multiple", "/exit-readiness", "/exit-timing", "/find-comps",
    "/fraud-detection", "/fund-attribution", "/fundraising", "/geo-market",
    "/gp-benchmarking", "/gpo-supply", "/growth-runway", "/hcit-platform",
    "/health-equity", "/hold-analysis", "/hold-optimizer", "/hospital-anchor",
    "/ic-memo-gen", "/insurance-tracker", "/irr-dispersion", "/key-person",
    "/lbo-stress", "/leverage-intel", "/library", "/litigation",
    "/locum-tracker", "/lp-dashboard", "/lp-reporting", "/ma-contracts",
    "/ma-star", "/market-rates", "/medicaid-unwinding", "/medical-realestate",
    "/mgmt-comp", "/mgmt-fee-tracker", "/msa-concentration", "/multiple-decomp",
    "/nav-loan-tracker", "/nsa-tracker", "/operating-partners", "/partner-economics",
    "/patient-experience", "/payer-concentration", "/payer-contracts", "/payer-intel",
    "/payer-rate-trends", "/payer-shift", "/peer-transactions", "/peer-valuation",
    "/phys-comp-plan", "/physician-labor", "/physician-productivity", "/platform-maturity",
    "/pmi-integration", "/pmi-playbook", "/portfolio-optimizer", "/portfolio-sim",
    "/provider-network", "/provider-retention", "/qoe-analyzer", "/quality-scorecard",
    "/rcm-red-flags", "/real-estate", "/redflag-scanner", "/ref-pricing",
    "/refi-optimizer", "/regulatory-risk", "/reinvestment", "/reit-analyzer",
    "/return-attribution", "/revenue-leakage", "/risk-adjustment", "/risk-matrix",
    "/rollup-economics", "/rw-insurance", "/secondaries-tracker",
    "/sector-correlation", "/sector-intel", "/sector-momentum", "/sellside-process",
    "/size-intel", "/specialty-benchmarks", "/sponsor-heatmap", "/sponsor-league",
    "/supply-chain", "/tax-credits", "/tax-structure",
    "/tech-stack", "/telehealth-econ", "/transition-services", "/treasury",
    "/trial-site-econ", "/underwriting", "/underwriting-model", "/unit-economics",
    "/value-creation", "/value-creation-plan", "/vcp-tracker", "/vdr-tracker",
    "/vintage-cohorts", "/vintage-perf", "/workforce-planning", "/workforce-retention",
    "/working-capital", "/zbb-tracker",
})

_ILLUSTRATIVE_ROUTE_NOTE = ("analyzer figures (built from the bundled "
                            "illustrative seed corpus / modeled assumptions, "
                            "not your ingested portfolio)")


def _is_illustrative_route(active_nav: Optional[str]) -> bool:
    """True if ``active_nav`` is a registered illustrative analyzer route.

    Normalizes a trailing slash and strips any query/fragment so
    ``/lbo-stress?ev=200`` and ``/lbo-stress/`` both resolve."""
    if not active_nav:
        return False
    p = str(active_nav).split("?", 1)[0].split("#", 1)[0].rstrip("/") or "/"
    return p in _ILLUSTRATIVE_ANALYZER_ROUTES


# ── Action button primitive ─────────────────────────────────────────
#
# Single editorial primary-action button for the workbench. Emits
# markup that consumes the existing ``.cad-btn .cad-btn-primary``
# class pair from ``/static/v3/chartis.css`` (the brighter teal
# ``#1F7A75`` already used by Deal Profile and the rest of the
# authenticated surface).
#
# Why a primitive rather than direct ``class="cad-btn cad-btn-primary"``
# in every page: four pages (compare, counterfactual, denial-prediction,
# deal-autopsy) previously emitted bespoke inline-styled buttons with
# ``background:P["accent"]`` (``#155752``) — a *third* color that
# matched neither the workbench teal nor the marketing near-black-navy.
# Each used a different pattern (inline style, page-scoped class).
# The primitive gives every future page one obvious call-site to use,
# stops the four-pages-invent-a-fifth-pattern drift, and lets later
# variants (secondary / destructive) land as a dict addition rather
# than a call-site sweep.
#
# Color scope of this PR: ``variant="primary"`` maps to the existing
# ``.cad-btn .cad-btn-primary`` workbench teal (``#1F7A75``). The
# marketing ``.cta-btn`` near-black-navy stays untouched — the
# marketing/workbench color split is intentional (formal entry vs.
# active interior) and the cross-surface unification is a separate
# Tier B ticket ("button primitive unification — pick one design").

_ACTION_BUTTON_VARIANT_CLASS: Dict[str, str] = {
    # Today: only "primary". Reserve slots for future variants so
    # adding them is a one-line dict addition, not a call-site
    # refactor. Each future entry needs (a) the CSS class pair it
    # emits, (b) the color/semantic intent, (c) a TODO marker so
    # future agents know the slot is reserved-but-not-shipped.
    "primary":     "cad-btn cad-btn-primary",   # workbench teal #1F7A75
    # "secondary":   "cad-btn",                  # neutral outline, no fill — TODO ship when first caller needs it
    # "destructive": "cad-btn cad-btn-destructive",  # red TBD; needs new CSS class — TODO design + ship together
}


def ck_action_button(
    text: str,
    *,
    type: str = "submit",
    form_target: Optional[str] = None,
    variant: str = "primary",
) -> str:
    """Editorial primary-action button.

    Args:
        text: Visible label. HTML-escaped before rendering.
        type: ``"submit"`` (default) or ``"button"``. Anything else
            falls back to ``"submit"`` so a typo doesn't break form
            submission silently.
        form_target: Optional ``form`` attribute value when the button
            sits OUTSIDE the form it submits (HTML5 form-association).
            Omit for the common case of a button nested inside its form.
        variant: ``"primary"`` (default). Unknown variants fall back
            to ``"primary"`` — a typo renders a styled button rather
            than an unstyled one, so the visual mistake is loud.

    Why no ``onclick`` / ``href`` parameters: this primitive is for
    form-submit buttons (the case the four-page regression covered).
    For navigation, use an ``<a class="cad-btn cad-btn-primary">``
    or wait for the ``ck_action_link`` sibling primitive when that
    pattern is canonicalized.
    """
    if type not in ("submit", "button"):
        type = "submit"
    cls = _ACTION_BUTTON_VARIANT_CLASS.get(variant) \
        or _ACTION_BUTTON_VARIANT_CLASS["primary"]
    attrs = [f'type="{type}"', f'class="{cls}"']
    if form_target:
        attrs.append(f'form="{_esc(form_target)}"')
    return f'<button {" ".join(attrs)}>{_esc(text)}</button>'


# ── Prediction diagnostic chip ──────────────────────────────────────
#
# Renders the visual signal for ``PredictedMetric.failure_reason``
# (the enum defined in :mod:`rcm_mc.ml.ridge_predictor`). Three chip
# variants map onto three mental models the partner needs:
#
#   - INSUFFICIENT_DATA (gray)   → "data doesn't support a prediction"
#   - UNSTABLE_FIT (amber)       → "model ran, don't lean on it hard"
#   - FIT_ERROR (red)            → "math broke, don't use this number"
#
# A.1 scope: chip renders all three variants but only UNSTABLE_FIT
# fires from real predictor paths today. INSUFFICIENT_DATA and
# FIT_ERROR are wired here in anticipation of the Tier B orchestrator
# refactor that will emit them on fallback / hard-failure paths. The
# helper is intentionally tolerant of the wider taxonomy now so the
# Tier B PR is a one-line predictor change, not a chip rewrite.

# Map of FailureReason string values → (tone, label, default tooltip).
# Kept as plain strings (not the Enum) so this module doesn't import
# from rcm_mc.ml — the enum's value attribute is the wire format.
_PREDICTION_CHIP_MAP: Dict[str, Tuple[str, str, str]] = {
    "insufficient_comparables": ("na",    "— insufficient comparables", "No prediction — too few peer hospitals to fit a model."),
    "target_features_missing":  ("na",    "— missing input features",    "Target hospital missing one or more required input metrics."),
    "no_benchmark":             ("na",    "— no benchmark available",    "No registry fallback for this metric; nothing to render."),
    "pinv_fallback":            ("warn",  "⚠ fit unstable",              "Ridge solver fell back to pseudoinverse — coefficients unstable."),
    "ci_unstable":              ("warn",  "⚠ fit unstable",              "Confidence interval wider than 2× point estimate — signal is noise-dominated."),
    "r2_negative":              ("warn",  "⚠ fit unstable",              "Cross-validated R² is negative — model predicts worse than the cohort mean."),
    "fit_exception":            ("error", "✕ prediction failed",          "Predictor raised an exception that could not be recovered. Treat the displayed value as unavailable."),
    # ── B.1 diagnostic variants (all Tier 2 / amber) ──
    "multicollinear":           ("warn",  "⚠ multicollinear features",   "Features are linearly redundant (max VIF > 10). Top-driver attribution may be misleading — multiple features jointly carry the signal."),
    "influential_outlier":      ("warn",  "⚠ outlier-driven fit",        "One peer hospital exerts outsized influence on the fit (Cook's D > 4/N). Verify the outlier is a genuine peer; consider excluding it for robustness."),
    "heteroscedastic":          ("warn",  "⚠ uncalibrated CI width",     "Residual variance depends on feature values (Breusch-Pagan p < 0.05). The confidence interval is sized correctly on average but may be too tight or too loose at this specific prediction point."),
    "high_leverage":            ("warn",  "⚠ high-leverage peer",        "One peer hospital sits at the edge of the cohort's feature space (max hat > 2p/N). Predictions extrapolating toward that peer are less trustworthy."),
    "nonlinear_pattern":        ("warn",  "⚠ nonlinear residuals",       "Residuals show systematic structure vs fitted values (|t-slope| > 2). The linear ridge is missing curvature — predictions at the high or low end may be biased."),
    "diagnostic_suspect":       ("warn",  "⚠ multiple diagnostic flags", "Two or more diagnostics flagged this fit. Each individually is recoverable; together they suggest the cohort or feature set isn't well-suited to ridge regression here."),
    "alpha_at_boundary":        ("warn",  "⚠ α at search boundary",      "RidgeCV picked the lowest or highest α in the search grid — the cohort may need a wider regularization range than the current grid covers."),
}


def ck_prediction_chip(pm: Any) -> str:
    """Render a diagnostic chip for a PredictedMetric (or anything with a
    ``failure_reason`` attribute) whose value should NOT be trusted as-is.

    Returns ``''`` (empty string) for None / for sources with
    ``failure_reason is None`` — clean fits don't render a chip.

    Accepts any object with a ``failure_reason`` attribute. Works for
    three shapes today:

      - ridge-flavor :class:`PredictedMetric` (enum-valued ``failure_reason``)
      - packet :class:`PredictedMetric` (string-valued ``failure_reason``)
      - :class:`AggregatedFailure` from A.10 (string-valued
        ``failure_reason`` + ``contributing_sources`` list)

    When the input is an ``AggregatedFailure`` carrying contributing
    sources, the tooltip is enhanced with the per-source detail so a
    partner hovering the chip sees which specific upstream prediction
    drove the diagnostic state (e.g. "Fit unstable — denial_rate
    (ci_unstable); payer_mix (pinv_fallback)"). For single-source
    inputs the default tooltip stays unchanged.

    Defensive against unexpected reason values — falls back to the
    FIT_ERROR rendering with the raw reason in the tooltip so a typo
    or new enum variant degrades gracefully rather than silently.

    Audit-history note: original A.1 audit framed this as "remove
    silent zero-fill" on r_squared. Grep revealed the actual bug is
    that 0.0 is used as a "method N/A" sentinel by weighted_median
    and benchmark_fallback paths, indistinguishable from a genuine
    R²=0. ``failure_reason`` is the authoritative diagnostic channel
    that resolves the conflation; the chip is its visual manifestation.
    A.10 extends that channel one architectural seam further down
    (PredictedMetric → ProfileMetric), where the conversion in
    ``_merge_rcm_profile`` had been silently dropping the field.
    """
    if pm is None:
        return ""
    fr = getattr(pm, "failure_reason", None)
    if fr is None:
        return ""
    # Normalize: enum → its string value; anything else → str(fr)
    fr_key = fr.value if hasattr(fr, "value") else str(fr)
    tone, label, default_tip = _PREDICTION_CHIP_MAP.get(
        fr_key,
        ("error", "✕ prediction failed", f"Unknown failure reason: {fr_key}"),
    )
    # A.10 — when the source is an AggregatedFailure with named
    # contributors, surface them in the tooltip so the partner can
    # see which specific upstream prediction caused the chip. Falls
    # back to the default tip for non-aggregated inputs.
    sources = getattr(pm, "contributing_sources", None)
    if sources:
        tip = f"{default_tip} — Sources: " + "; ".join(str(s) for s in sources)
    else:
        tip = default_tip
    return (
        f'<span class="ck-pred-chip ck-pred-chip-{tone}" '
        f'title="{_esc(tip)}">{_esc(label)}</span>'
    )


# ── A.10 chip propagation — aggregator pattern ──────────────────────
#
# When a single KPI consumes multiple upstream predictions, the chip
# must reflect the *worst* diagnostic state across all of them — and
# the tooltip should name which specific upstream caused the chip,
# so the partner can debug actionably rather than guess.
#
# Severity ordering (locked in this PR; future variants land in the
# tier map below):
#
#   Tier 3 (worst): FIT_EXCEPTION              → red ✕ "math broke"
#   Tier 2:         PINV_FALLBACK,
#                   CI_UNSTABLE,
#                   R2_NEGATIVE                → amber ⚠ "fit suspect"
#   Tier 1:         INSUFFICIENT_COMPARABLES,
#                   TARGET_FEATURES_MISSING,
#                   NO_BENCHMARK               → gray — "no model fit"
#   Tier 0 (clean): None                       → (no chip)
#
# Aggregator returns the highest tier seen. ck_prediction_chip already
# accepts anything with a ``failure_reason`` attribute, so the
# AggregatedFailure dataclass composes naturally:
#
#     chip = ck_prediction_chip(ck_aggregate(pm_a, pm_b, pm_c))
#
# Scope note: only Tier 2 reasons fire from real predictor paths
# today. Tier 1 / Tier 3 are wired but require the orchestrator-emit
# refactor (Tier B item) to be load-bearing in production. Partners
# will see only amber chips on pedesk.app until that lands.

_FAILURE_REASON_TIER: Dict[str, int] = {
    # Tier 3 — math broke
    "fit_exception":            3,
    # Tier 2 — fit ran but diagnostics flag it
    "pinv_fallback":            2,
    "ci_unstable":              2,
    "r2_negative":              2,
    # ── B.1 additions (all Tier 2) ──
    "multicollinear":           2,
    "influential_outlier":      2,
    "heteroscedastic":          2,
    "high_leverage":            2,
    "nonlinear_pattern":        2,
    "diagnostic_suspect":       2,
    "alpha_at_boundary":        2,
    # Tier 1 — no model fit; what's shown is a fallback
    "insufficient_comparables": 1,
    "target_features_missing":  1,
    "no_benchmark":             1,
}


@dataclass
class AggregatedFailure:
    """Output of :func:`ck_aggregate` — composes across multiple PMs.

    Shaped like a PredictedMetric for ``ck_prediction_chip`` to accept
    it without a separate code path. Carries:

    - ``failure_reason``: string value of the worst-tier reason seen
      across inputs, or ``None`` if every input is clean.
    - ``tier``: numeric severity tier (0 = clean, 3 = worst). Useful
      for callers that want to gate rendering on severity (e.g.
      "only show chip for tier ≥ 2").
    - ``contributing_sources``: per-input "label (reason_key)" strings
      for tooltip context. Empty when no input contributed a failure.

    The shape is intentionally minimal — no methods, no behavior. The
    aggregator does the work; AggregatedFailure is just a data carrier.
    """
    failure_reason: Optional[str] = None
    tier: int = 0
    contributing_sources: List[str] = field(default_factory=list)


def ck_aggregate(
    *sources: Any,
    labels: Optional[Sequence[str]] = None,
) -> AggregatedFailure:
    """Aggregate ``failure_reason`` from multiple PM-shaped inputs.

    Each ``source`` is anything with a ``failure_reason`` attribute, OR
    ``None``. None inputs are skipped (no PM = no failure contribution).

    Severity is composed by taking the max tier across inputs per the
    ordering documented above. Within a tier, the first-seen reason
    wins for the ``failure_reason`` field; ``contributing_sources``
    lists every non-clean input so the tooltip can name them all.

    ``labels`` is an optional sequence of human-readable names, one
    per source. When provided, ``contributing_sources`` uses
    ``"<label> (<reason>)"``. When omitted, contributors are labeled
    ``"source[<index>] (<reason>)"`` so the tooltip still parses.

    Returns an :class:`AggregatedFailure` with ``failure_reason=None``,
    ``tier=0``, and empty ``contributing_sources`` if every input is
    clean / None — ``ck_prediction_chip`` then renders no chip.

    Unknown reason values are defensively treated as Tier 3 (worst-
    case) so a typo or new enum variant doesn't accidentally pass
    through as Tier 0 / clean.
    """
    worst_tier = 0
    worst_reason: Optional[str] = None
    contributing: List[str] = []

    for i, src in enumerate(sources):
        if src is None:
            continue
        fr = getattr(src, "failure_reason", None)
        if fr is None:
            continue
        fr_key = fr.value if hasattr(fr, "value") else str(fr)
        tier = _FAILURE_REASON_TIER.get(fr_key, 3)
        label = (
            labels[i] if (labels is not None and i < len(labels))
            else f"source[{i}]"
        )
        contributing.append(f"{label} ({fr_key})")
        if tier > worst_tier:
            worst_tier = tier
            worst_reason = fr_key

    return AggregatedFailure(
        failure_reason=worst_reason,
        tier=worst_tier,
        contributing_sources=contributing,
    )


# ── Claude Design handoff primitives ────────────────────────────────
# Ported from the marketing / home / module-directory handoffs
# (React/JSX prototypes). These three are the composition primitives
# the handoffs introduce — DataPanel chrome, the BarRow, and the
# signature paired-viz+dataset block. They read existing --sc-* CSS
# vars so they inherit any later palette refinement automatically.


def ck_data_panel(
    code: str,
    title: str,
    body: str,
    *,
    live: bool = True,
) -> str:
    """Bordered data panel with a navy header — the platform's
    signature surface chrome (3-letter mono code + title + LIVE badge).

    Ported from the Claude Design ``DataPanel`` primitive in the
    home / module-directory handoffs. ``body`` is pre-rendered HTML
    (the panel's content); ``code`` is the short mono identifier
    shown in teal at the header's left edge (e.g. ``FNL``, ``ALR``).
    """
    live_html = (
        '<span class="ck-data-panel-live">LIVE</span>' if live else ""
    )
    return (
        '<section class="ck-data-panel">'
        '<header class="ck-data-panel-head">'
        f'<span class="ck-data-panel-code">{_esc(code)}</span>'
        f'<span class="ck-data-panel-title">{_esc(title)}</span>'
        f'{live_html}'
        '</header>'
        f'<div class="ck-data-panel-body">{body}</div>'
        '</section>'
    )


def ck_bar_row(
    label: str,
    value: str,
    pct: float,
    *,
    tone: str = "teal",
    unit: str = "",
) -> str:
    """Compact labelled bar row — label, value, proportional bar, %.

    Ported from the Claude Design ``BarRow`` primitive. ``pct`` is
    0-100; ``tone`` ∈ {teal, positive, warning, negative, navy}. The
    bar floors at 2% width so a near-zero value still reads as a row.
    """
    tone_var = {
        "teal": "var(--sc-teal)",
        "positive": "var(--sc-positive)",
        "warning": "var(--sc-warning)",
        "negative": "var(--sc-negative)",
        "navy": "var(--sc-navy)",
    }.get(tone, "var(--sc-teal)")
    pct_clamped = max(0.0, min(100.0, pct))
    return (
        '<div class="ck-bar-row">'
        f'<span class="ck-bar-row-label">{_esc(label)}</span>'
        f'<span class="ck-bar-row-value">{_esc(value)}{_esc(unit)}</span>'
        '<span class="ck-bar-row-track">'
        f'<span class="ck-bar-row-fill" '
        f'style="width:{max(2.0, pct_clamped):.1f}%;background:{tone_var};">'
        '</span></span>'
        f'<span class="ck-bar-row-pct">{pct_clamped:.1f}%</span>'
        '</div>'
    )


def ck_scatter(
    points,
    *,
    x_label: str = "",
    y_label: str = "",
    x_ref=None,
    y_ref=None,
    height: int = 230,
    caption: str = "",
) -> str:
    """Scatter / quadrant chart for interpreting a 2-metric dense table.

    ``points`` is a list of ``(x, y, label, tone)`` tuples (tone ∈
    {teal, positive, warning, negative, navy}); each renders as a dot
    with a hover ``<title>`` of ``label`` + the two values. A 5th tuple
    element, ``href``, makes the dot a link to its drill-down (the dot
    is wrapped in an SVG ``<a>`` and gets a pointer cursor) — so a
    partner can click a point straight through to that row's detail
    page. Optional ``x_ref`` / ``y_ref`` draw dashed quadrant reference
    lines (e.g. a benchmark median) so a partner reads quadrant
    membership — the "big + risky" cluster — straight off a table that
    otherwise hides it in columns. Pure inline SVG, editorial palette,
    responsive width. Returns '' when fewer than 2 finite points exist
    (caller can fall back to the table alone)."""
    tone_var = {
        "teal": "var(--sc-teal,#1F7A75)", "positive": "var(--sc-positive,#0a8a5f)",
        "warning": "var(--sc-warning,#b8732a)", "negative": "var(--sc-negative,#b5321e)",
        "navy": "var(--sc-navy,#0b2341)",
    }
    pts = []
    for p in points:
        try:
            x = float(p[0]); y = float(p[1])
        except (TypeError, ValueError, IndexError):
            continue
        if x != x or y != y:  # NaN guard
            continue
        lab = str(p[2]) if len(p) > 2 and p[2] is not None else ""
        tn = p[3] if len(p) > 3 and p[3] in tone_var else "teal"
        href = str(p[4]) if len(p) > 4 and p[4] else None
        pts.append((x, y, lab, tn, href))
    if len(pts) < 2:
        return ""
    W, H = 480.0, float(height)
    L, R, T, B = 46.0, 14.0, 14.0, 30.0
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    xmin, xmax = min(xs), max(xs); ymin, ymax = min(ys), max(ys)
    # Pull any quadrant reference into the data range so the threshold
    # line is always visible inside the plot and points read as
    # above/below it — even when every point sits on one side (e.g. all
    # sponsors above the 2.0x MOIC bar). Otherwise sx()/sy() would map
    # the ref off the axes and the line would draw outside the frame.
    try:
        if x_ref is not None:
            _xr = float(x_ref); xmin = min(xmin, _xr); xmax = max(xmax, _xr)
    except (TypeError, ValueError):
        pass
    try:
        if y_ref is not None:
            _yr = float(y_ref); ymin = min(ymin, _yr); ymax = max(ymax, _yr)
    except (TypeError, ValueError):
        pass
    if xmax == xmin: xmax += 1.0; xmin -= 1.0
    if ymax == ymin: ymax += 1.0; ymin -= 1.0
    xpad = (xmax - xmin) * 0.06; ypad = (ymax - ymin) * 0.08
    xmin -= xpad; xmax += xpad; ymin -= ypad; ymax += ypad

    def sx(x): return L + (x - xmin) / (xmax - xmin) * (W - L - R)
    def sy(y): return (H - B) - (y - ymin) / (ymax - ymin) * (H - B - T)

    def fnum(v):
        a = abs(v)
        if a >= 100: return f"{v:,.0f}"
        if a >= 1: return f"{v:,.1f}"
        return f"{v:,.2f}"

    parts = [f'<svg viewBox="0 0 {W:.0f} {H:.0f}" width="100%" '
             f'style="max-width:520px;font-family:var(--sc-mono,JetBrains Mono,monospace)" '
             f'role="img" aria-label="scatter plot">']
    # frame axes
    parts.append(f'<line x1="{L}" y1="{T}" x2="{L}" y2="{H-B}" stroke="var(--sc-rule,#d6cfc0)" stroke-width="1"/>')
    parts.append(f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" stroke="var(--sc-rule,#d6cfc0)" stroke-width="1"/>')
    # quadrant reference lines
    if x_ref is not None:
        try:
            xr = sx(float(x_ref))
            parts.append(f'<line x1="{xr:.1f}" y1="{T}" x2="{xr:.1f}" y2="{H-B}" stroke="var(--sc-text-faint,#7a8699)" stroke-width="1" stroke-dasharray="3 3" opacity="0.7"/>')
        except (TypeError, ValueError): pass
    if y_ref is not None:
        try:
            yr = sy(float(y_ref))
            parts.append(f'<line x1="{L}" y1="{yr:.1f}" x2="{W-R}" y2="{yr:.1f}" stroke="var(--sc-text-faint,#7a8699)" stroke-width="1" stroke-dasharray="3 3" opacity="0.7"/>')
        except (TypeError, ValueError): pass
    # axis min/max ticks
    parts.append(f'<text x="{L}" y="{H-B+14}" font-size="8" fill="var(--sc-text-faint,#7a8699)">{_esc(fnum(xmin))}</text>')
    parts.append(f'<text x="{W-R}" y="{H-B+14}" font-size="8" text-anchor="end" fill="var(--sc-text-faint,#7a8699)">{_esc(fnum(xmax))}</text>')
    parts.append(f'<text x="{L-4}" y="{H-B}" font-size="8" text-anchor="end" fill="var(--sc-text-faint,#7a8699)">{_esc(fnum(ymin))}</text>')
    parts.append(f'<text x="{L-4}" y="{T+8}" font-size="8" text-anchor="end" fill="var(--sc-text-faint,#7a8699)">{_esc(fnum(ymax))}</text>')
    # axis labels
    if x_label:
        parts.append(f'<text x="{(L+W-R)/2:.0f}" y="{H-2}" font-size="9" text-anchor="middle" fill="var(--sc-text-dim,#465366)">{_esc(x_label)}</text>')
    if y_label:
        cy = (T + H - B) / 2
        parts.append(f'<text x="11" y="{cy:.0f}" font-size="9" text-anchor="middle" fill="var(--sc-text-dim,#465366)" transform="rotate(-90 11 {cy:.0f})">{_esc(y_label)}</text>')
    # dots
    for x, y, lab, tn, href in pts:
        cx = sx(x); cy = sy(y)
        title = (lab + " · " if lab else "") + f"{fnum(x)}, {fnum(y)}"
        cursor = ';cursor:pointer' if href else ''
        circle = (
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="4" fill="{tone_var[tn]}" '
            f'fill-opacity="0.78" stroke="var(--sc-bg,#faf7f0)" stroke-width="0.8" '
            f'style="transition:r .1s{cursor}">'
            f'<title>{_esc(title)}</title></circle>'
        )
        if href:
            parts.append(f'<a href="{_esc(href)}">{circle}</a>')
        else:
            parts.append(circle)
    parts.append('</svg>')
    cap = (f'<div style="font-size:10px;color:var(--sc-text-faint);margin-top:4px;'
           f'font-family:JetBrains Mono,monospace">{_esc(caption)}</div>') if caption else ""
    return '<div style="margin-bottom:14px">' + "".join(parts) + cap + '</div>'


def ck_value_anchor(
    label: str,
    value: str,
    *,
    delta: str = "",
    opportunity: str = "",
    target: str = "",
    tone: str = "teal",
) -> str:
    """Value-anchor band — leads an analytic section with the iVantage
    pattern: a headline metric anchored to *benchmark delta → dollar
    opportunity → target*, so a partner reads the financial stakes
    before any chart or table.

    ``label`` is the eyebrow (e.g. "CYBER POSTURE"); ``value`` is the
    headline metric (e.g. "72 / 100"). The three optional facts render
    as a labelled row — ``opportunity`` is emphasised in the tone color
    because it is the load-bearing number. ``tone`` ∈ {teal, positive,
    warning, negative, navy}.

    DEFENSIBILITY: callers pass only computed figures. Pass ``opportunity``
    empty when no defensible dollar value exists — the band still anchors
    on the real metric + ``delta`` rather than inventing one. ``value``,
    ``delta``, ``opportunity`` and ``target`` are escaped here, so callers
    pass plain strings (not pre-built markup).
    """
    tone_var = {
        "teal": "var(--sc-teal)",
        "positive": "var(--sc-positive)",
        "warning": "var(--sc-warning)",
        "negative": "var(--sc-negative)",
        "navy": "var(--sc-navy)",
    }.get(tone, "var(--sc-teal)")
    facts = []
    if delta:
        facts.append(
            '<div class="ck-va-fact">'
            '<span class="ck-va-fact-label">vs benchmark</span>'
            f'<span class="ck-va-fact-value">{_esc(delta)}</span></div>'
        )
    if opportunity:
        facts.append(
            '<div class="ck-va-fact ck-va-fact-hero">'
            '<span class="ck-va-fact-label">opportunity</span>'
            f'<span class="ck-va-fact-value" style="color:{tone_var}">'
            f'{_esc(opportunity)}</span></div>'
        )
    if target:
        facts.append(
            '<div class="ck-va-fact">'
            '<span class="ck-va-fact-label">target</span>'
            f'<span class="ck-va-fact-value">{_esc(target)}</span></div>'
        )
    facts_html = (
        f'<div class="ck-va-facts">{"".join(facts)}</div>' if facts else ""
    )
    return (
        f'<div class="ck-value-anchor" style="--ck-va-tone:{tone_var}">'
        '<div class="ck-va-head">'
        f'<span class="ck-va-eyebrow">{_esc(label)}</span>'
        f'<span class="ck-va-value">{_esc(value)}</span>'
        '</div>'
        f'{facts_html}'
        '</div>'
    )


def ck_paired_block(
    viz_html: str,
    *,
    data_label: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    data_source: str = "",
    hot_rows: Sequence[int] = (),
) -> str:
    """The signature paired viz + dataset block — a chart on the left,
    its raw dataset on the right, both inside one outer rule.

    Ported from the Claude Design "paired viz + dataset" pattern in
    the marketing handoff. ``viz_html`` is pre-rendered (SVG chart,
    funnel, etc.). ``headers`` is the column labels — the first column
    left-aligns as a label, the rest right-align as values. ``rows``
    is the table body, one sequence of cells per row, same column
    order as ``headers``. ``hot_rows`` marks row indices to highlight
    (left amber rule + tinted background).

    Per the handoff convention: a chart without its paired dataset
    is not considered done.
    """
    hot = set(hot_rows)
    head_cells = "".join(
        f'<th>{_esc(h)}</th>' if i == 0
        else f'<th class="ck-pair-r">{_esc(h)}</th>'
        for i, h in enumerate(headers)
    )
    body_rows = ""
    for ridx, row in enumerate(rows):
        row_cls = ' class="ck-pair-hot"' if ridx in hot else ""
        cells = "".join(
            f'<td class="ck-pair-lbl">{_esc(c)}</td>' if i == 0
            else f'<td class="ck-pair-r">{_esc(c)}</td>'
            for i, c in enumerate(row)
        )
        body_rows += f'<tr{row_cls}>{cells}</tr>'
    src_html = (
        f'<span class="ck-pair-src">{_esc(data_source)}</span>'
        if data_source else ""
    )
    return (
        '<div class="ck-pair">'
        f'<div class="ck-pair-viz">{viz_html}</div>'
        '<div class="ck-pair-data">'
        '<div class="ck-pair-data-h">'
        f'<span>{_esc(data_label)}</span>{src_html}'
        '</div>'
        f'<table><thead><tr>{head_cells}</tr></thead>'
        f'<tbody>{body_rows}</tbody></table>'
        '</div>'
        '</div>'
    )


def ck_confidence_band(
    point: str,
    lo: Optional[str] = None,
    hi: Optional[str] = None,
    *,
    label: str = "P10–P90",
    low_confidence: bool = False,
) -> str:
    """Editorial confidence-band render for predictive outputs.

    Shape: ``2.5x [1.8x – 3.2x P10–P90]`` — the point estimate in
    headline weight, the band in muted mono with a label naming the
    interval shape (P10-P90, 95% CI, ±1σ, etc.).

    When ``low_confidence=True`` (e.g. AUC < 0.70, n < 20 calibration
    samples, or wide band relative to point), the band renders in
    warning tone to flag that the partner should verify externally
    before relying on the headline number.

    Both ``lo`` and ``hi`` must be pre-formatted strings (the caller
    knows the units — $M, x, %, days, etc.). Pass ``None`` for either
    bound to render only the point with no bracket.
    """
    if lo is None or hi is None:
        return f'<span class="ck-conf">{_esc(point)}</span>'
    tone = "warning" if low_confidence else "neutral"
    return (
        f'<span class="ck-conf tone-{tone}">'
        f'{_esc(point)}'
        f' <span class="ck-conf-band" style="font-family:var(--sc-mono,monospace);'
        f'font-size:0.85em;color:var(--sc-text-faint,#6e7787);'
        f'letter-spacing:0.02em;font-weight:400;">'
        f'[{_esc(lo)} – {_esc(hi)} <span class="ck-conf-label" '
        f'style="font-size:0.85em;letter-spacing:0.06em;'
        f'text-transform:uppercase;">{_esc(label)}</span>]'
        f'</span></span>'
    )


def ck_sticky_toc(
    sections: Sequence[Mapping[str, str]],
    *,
    eyebrow: str = "Contents",
) -> str:
    """Editorial right-rail Table of Contents.

    ``sections`` is an ordered sequence of mappings with two keys:

      - ``id``:    the anchor id, matches ``ck_panel(anchor_id=...)``
      - ``title``: the link label (will be html-escaped)

    Renders a sticky-positioned aside with an eyebrow + numbered list
    of section anchors. Inline JS attaches an IntersectionObserver so
    the link of the currently-visible section gets the ``is-active``
    state class. Hidden on screens narrower than 1100px (the editorial
    layout collapses to single-column there).

    Usage from a page renderer::

        sections = [
            {"id": "1-overview",  "title": "1. Target Overview"},
            {"id": "2-market",    "title": "2. Market Context"},
            ...
        ]
        toc = ck_sticky_toc(sections)
        body = '<div class="ck-toc-layout">' + toc + (
            '<div class="ck-toc-content">'
            + ck_panel(s1_html, title="1. Target Overview",
                       anchor_id="1-overview")
            + ...
            + '</div></div>'
        )
    """
    items = "".join(
        '<li class="ck-toc-item">'
        f'<a class="ck-toc-link" href="#{_esc(s["id"])}" '
        f'data-ck-toc-target="{_esc(s["id"])}">'
        f'{_esc(s["title"])}'
        '</a></li>'
        for s in sections
    )
    return (
        '<aside class="ck-toc" role="navigation" '
        'aria-label="Page contents">'
        f'<div class="ck-toc-eyebrow">{_esc(eyebrow)}</div>'
        f'<ol class="ck-toc-list">{items}</ol>'
        '</aside>'
        '<script>'
        '(function(){var links=document.querySelectorAll('
        '"[data-ck-toc-target]");if(!links.length||!("IntersectionObserver" '
        'in window))return;var byId={};links.forEach(function(a){'
        'byId[a.getAttribute("data-ck-toc-target")]=a;});'
        'var io=new IntersectionObserver(function(entries){'
        'entries.forEach(function(e){var a=byId[e.target.id];if(!a)return;'
        'if(e.isIntersecting){links.forEach(function(x){'
        'x.classList.remove("is-active");});a.classList.add("is-active");}'
        '});},{rootMargin:"-30% 0px -55% 0px",threshold:0});'
        'Object.keys(byId).forEach(function(id){var el=document.getElementById(id);'
        'if(el)io.observe(el);});}());'
        '</script>'
    )


def ck_help_tooltip(
    term: str,
    definition: str,
    *,
    citation: Optional[str] = None,
) -> str:
    """Inline editorial help affordance — ``term [?]`` that opens a
    small popover with a serif definition and optional citation.

    Use it to gloss jargon partners may not know on first encounter
    (covenant headroom, conformal band, EV/EBITDA TTM, P10/P50/P90).
    The popover is purely CSS-driven (focus-within + click-toggle
    via ck-help-open class) so it works without JS and doesn't
    require any state machine on the page.

    Rendered shape::

        <span class="ck-help">
          term
          <button class="ck-help-trigger" aria-expanded="false">?</button>
          <span class="ck-help-popover" role="tooltip">
            <span class="ck-help-term">term</span>
            <span class="ck-help-def">definition prose</span>
            <span class="ck-help-cite">— citation</span>
          </span>
        </span>

    Pages can opt out of the inline ``term`` rendering and just emit
    the popover by themselves; this helper is the canonical version.
    """
    cite_html = (
        f'<span class="ck-help-cite">— {_esc(citation)}</span>'
        if citation else ""
    )
    return (
        '<span class="ck-help">'
        f'{_esc(term)}'
        '<button type="button" class="ck-help-trigger" '
        'aria-expanded="false" tabindex="0">?</button>'
        '<span class="ck-help-popover" role="tooltip">'
        f'<span class="ck-help-term">{_esc(term)}</span>'
        f'<span class="ck-help-def">{_esc(definition)}</span>'
        f'{cite_html}'
        '</span>'
        '</span>'
    )


def ck_sparkline(
    values: Sequence[float],
    *,
    label: Optional[str] = None,
    last_value: Optional[str] = None,
    tone: Optional[str] = None,
    width: int = 72,
    height: int = 22,
) -> str:
    """Inline editorial sparkline — small SVG trend with optional
    serif label and mono numeric end-value, tinted with the
    severity-palette tone the caller specifies.

    ``values`` is a sequence of points (length 2+ to render; 0 or 1
    points return an empty string so callers can blindly hand off
    sparse data). When ``tone`` is not given, the helper picks
    positive when the last value >= first, negative when below
    first, neutral otherwise — same heuristic the older
    portfolio_overview._sparkline_svg used, but on the desaturated
    editorial palette instead of vibrant Tailwind.

    ``last_value`` (e.g. "$24.4M") renders to the right of the
    spark in JetBrains Mono with tabular-nums.

    ``label`` (e.g. "Health 12-wk") renders to the left in Inter
    Tight 9px caps with letter-spacing.

    The whole composition is one ``<span class="ck-spark">`` so it
    can sit inline in table cells or beside KPI values.
    """
    if not values or len(values) < 2:
        return ""
    try:
        nums = [float(v) for v in values]
    except (TypeError, ValueError):
        return ""
    mn, mx = min(nums), max(nums)
    rng = mx - mn if mx != mn else 1.0
    pts = []
    for i, v in enumerate(nums):
        x = i / (len(nums) - 1) * width
        y = height - ((v - mn) / rng) * height
        pts.append(f"{x:.1f},{y:.1f}")
    poly = " ".join(pts)
    # Editorial palette — desaturated for print.
    palette = {
        "positive": "#0a8a5f",
        "warning":  "#b8732a",
        "negative": "#b5321e",
        "neutral":  "#155752",
    }
    if tone not in palette:
        # Auto-pick by trend direction
        tone = ("positive" if nums[-1] > nums[0]
                else "negative" if nums[-1] < nums[0]
                else "neutral")
    stroke = palette[tone]
    label_html = (
        f'<span class="ck-spark-lbl">{_esc(label)}</span>'
        if label else ""
    )
    value_html = (
        f'<span class="ck-spark-val">{_esc(last_value)}</span>'
        if last_value else ""
    )
    svg = (
        f'<svg class="ck-spark-svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="trend sparkline">'
        f'<polyline points="{poly}" fill="none" stroke="{stroke}" '
        f'stroke-width="1.5" stroke-linecap="round" '
        f'stroke-linejoin="round"/>'
        '</svg>'
    )
    return (
        '<span class="ck-spark">'
        + label_html
        + svg
        + value_html
        + '</span>'
    )


def ck_progress_checklist(items: Sequence[Mapping[str, str]]) -> str:
    """Editorial 'your platform journey' progress checklist.

    Each item is a mapping with these keys:

      - ``id``:    a stable identifier, used as the storage-check key
      - ``title``: serif heading for the row
      - ``body``:  short editorial paragraph (optional)
      - ``check``: one of ``"recent_deals"``, ``"tour_started"``,
                   ``"tour_completed"``, ``"any_tool_visited"``,
                   ``"ic_memo_visited"``, ``"any"``. Inline JS
                   evaluates the check on DOMContentLoaded and flips
                   the row into the ``is-done`` state when satisfied.

    The checklist renders as a serif numbered list with a small
    circular state marker on each row — empty circle for incomplete,
    filled with a positive-tone check for done. Hidden in print.
    """
    rows = []
    for i, item in enumerate(items, start=1):
        rows.append(
            f'<li class="ck-checklist-row" data-ck-check="{_esc(item["check"])}">'
            f'<span class="ck-checklist-marker" aria-hidden="true"></span>'
            '<span class="ck-checklist-number">'
            + f"{i:02d}"
            + '</span>'
            '<div class="ck-checklist-body">'
            f'<div class="ck-checklist-title">{_esc(item["title"])}</div>'
            + (
                f'<div class="ck-checklist-prose">{_esc(item["body"])}</div>'
                if item.get("body") else ""
            )
            + '</div>'
            '</li>'
        )
    return (
        '<div class="ck-checklist-wrap">'
        '<ol class="ck-checklist">'
        + "".join(rows)
        + '</ol>'
        '</div>'
        '<script>'
        '(function(){'
        'function hasTour(){try{var s=JSON.parse(localStorage.getItem("rcm_tour_v1")||"null");return s||null;}catch(e){return null;}}'
        'function recentCount(){try{var r=JSON.parse(localStorage.getItem("rcm_recent_deals")||"[]");return Array.isArray(r)?r.length:0;}catch(e){return 0;}}'
        'function anyToolVisited(){try{for(var i=0;i<localStorage.length;i++){var k=localStorage.key(i);if(k&&/_visited$/.test(k)){var v=JSON.parse(localStorage.getItem(k)||"{}");if(v&&Object.keys(v).length)return true;}}return false;}catch(e){return false;}}'
        'function icMemoVisited(){try{for(var i=0;i<localStorage.length;i++){var k=localStorage.key(i);if(k&&/_visited$/.test(k)){var v=JSON.parse(localStorage.getItem(k)||"{}");for(var t in v){if(/ic-memo/i.test(t)||/ic-packet/i.test(t))return true;}}}return false;}catch(e){return false;}}'
        'function checkRow(row){var c=row.getAttribute("data-ck-check");'
        'if(c==="recent_deals")return recentCount()>0;'
        'var s=hasTour();'
        'if(c==="tour_started")return !!(s&&(s.lastViewed>0||(s.completed&&s.completed.length>0)));'
        'if(c==="tour_completed")return !!(s&&s.completed&&s.completed.length>=7);'
        'if(c==="any_tool_visited")return anyToolVisited();'
        'if(c==="ic_memo_visited")return icMemoVisited();'
        'return false;}'
        'function paint(){document.querySelectorAll("[data-ck-check]").forEach(function(row){'
        'if(checkRow(row))row.classList.add("is-done");else row.classList.remove("is-done");});}'
        'document.addEventListener("DOMContentLoaded",paint);'
        '}());'
        '</script>'
    )


# ---------------------------------------------------------------------------
# Editorial primitives — eyebrow, section intro, arrow link, image card.
# These mirror the patterns on chartis.com so partner-facing pages
# feel continuous with the marketing landing.
# ---------------------------------------------------------------------------

def ck_eyebrow(text: str, *, on_navy: bool = False) -> str:
    """Caps eyebrow + thin teal rule. Primary section anchor pattern."""
    cls = "ck-eyebrow on-navy" if on_navy else "ck-eyebrow"
    return f'<div class="{cls}">{_esc(text)}</div>'


def ck_section_intro(
    eyebrow: str,
    headline: str,
    *,
    body: Optional[str] = None,
    italic_word: Optional[str] = None,
    on_navy: bool = False,
) -> str:
    """Editorial section intro — eyebrow + serif headline + optional body.

    If ``italic_word`` is provided it is wrapped in ``<em>`` inside the
    headline (case-insensitive substring match), reproducing the
    "Reasons to *believe* in better" cadence on chartis.com.

    A small ``×`` close button in the corner hides the block; the
    dismissal is persisted in ``localStorage`` keyed off the eyebrow
    so it stays dismissed across page navigation.
    """
    h = _esc(headline)
    if italic_word:
        for cand in (italic_word, italic_word.capitalize(), italic_word.upper()):
            e_cand = _esc(cand)
            if e_cand in h:
                h = h.replace(e_cand, f"<em>{e_cand}</em>", 1)
                break
    body_html = (
        f'<p class="ck-section-body">{_esc(body)}</p>' if body else ""
    )
    # Stable per-section key so dismissals don't bleed across pages
    # (a partner who hides /app's intro should still see /pipeline's).
    dismiss_key = _esc(eyebrow.lower().replace(" ", "-"))
    return (
        f'<div class="ck-section-intro" data-ck-intro="{dismiss_key}">'
        '<button type="button" class="ck-section-intro-dismiss" '
        'aria-label="Hide section intro" '
        f'data-ck-intro-dismiss="{dismiss_key}">&times;</button>'
        f'{ck_eyebrow(eyebrow, on_navy=on_navy)}'
        f'<h2>{h}</h2>'
        f'{body_html}'
        '</div>'
    )


_NARRATIVE_CSS = (
    "<style>"
    # Memo-intro paragraph: the opening line of a section, drafted from
    # the underlying data, in the editorial register (italic serif,
    # muted ink, generous measure). Deliberately a plain paragraph — no
    # card, no shadow, no fill, no color decoration — so it reads like
    # the first sentence of a memo section, not a marketing callout.
    ".ck-narrative{font-family:var(--sc-serif,Georgia,serif);"
    "font-style:italic;font-size:15px;line-height:1.55;"
    "color:var(--sc-text-dim,#465366);margin:0 0 var(--sc-s-5,16px) 0;"
    "max-width:74ch;}"
    # Empty state is the same paragraph in a quieter ink so an
    # un-populated section still reads as intentional, not broken.
    ".ck-narrative.is-empty{color:var(--sc-text-faint,#7a8699);}"
    "</style>"
)


def ck_narrative_band(
    text: str = "",
    *,
    empty_copy: str = "",
    inject_css: bool = True,
) -> str:
    """Narrative summary band — the opening paragraph of a memo section.

    Renders ``text`` (drafted upstream from the section's underlying
    data) as an italic serif memo-intro paragraph. When ``text`` is
    empty, falls back to ``empty_copy`` rendered in a quieter ink so an
    un-populated section still reads as intentional. With neither,
    returns ``""`` (the band is silent by default — callers opt in by
    passing drafted copy).

    Tone contract for callers: declarative, no exclamation, no
    marketing language. This is the first sentence of a memo section,
    not a headline.

    ``text``/``empty_copy`` are HTML-escaped here, so callers pass plain
    strings. ``inject_css`` emits the shared ``.ck-narrative`` stylesheet
    once per page; pass ``inject_css=False`` on subsequent bands on the
    same page to avoid duplicate ``<style>`` blocks (mirrors the
    ``ck_provenance_tooltip`` idiom).

    Distinct from ``ck_section_intro`` (eyebrow + serif headline chrome)
    and ``ck_value_anchor`` (the dollar-anchor band): this is body prose,
    not a header or a metric strip.
    """
    css = _NARRATIVE_CSS if inject_css else ""
    if text:
        return f'{css}<p class="ck-narrative">{_esc(text)}</p>'
    if empty_copy:
        return f'{css}<p class="ck-narrative is-empty">{_esc(empty_copy)}</p>'
    return ""


def ck_next_section(
    label: str,
    href: str,
    *,
    eyebrow: str = "Up next",
    italic_word: Optional[str] = None,
) -> str:
    """Editorial 'Up next' footer — eyebrow + serif arrow-link.

    Sits below the last section on a page and points partners at the
    next logical step in the diligence flow. The cadence mirrors
    chartis.com's chapter footers (eyebrow + italic emphasis word +
    arrow). Use it instead of bare "Back to dashboard" links so a
    partner walking through diligence chronologically has a footer
    rail to follow:

      Pipeline → Screening → Diligence → Risk → Financial → Delivery

    If ``italic_word`` is provided it is wrapped in ``<em>`` inside
    the link label, e.g.::

        ck_next_section("Continue to the Risk Workbench",
                        "/diligence/risk-workbench",
                        italic_word="Risk")
    """
    label_html = _esc(label)
    if italic_word:
        for cand in (italic_word, italic_word.capitalize(), italic_word.upper()):
            e_cand = _esc(cand)
            if e_cand in label_html:
                label_html = label_html.replace(
                    e_cand, f"<em>{e_cand}</em>", 1)
                break
    return (
        '<div class="ck-next-section">'
        f'<div class="ck-next-eyebrow">{_esc(eyebrow)}</div>'
        f'<a class="ck-next-link" href="{_esc(href)}">'
        f'{label_html}'
        ' <span class="ck-next-arrow" aria-hidden="true">→</span>'
        '</a>'
        '</div>'
    )


# ---------------------------------------------------------------------------
# Editorial tour overlay — "The Atlas"
# ---------------------------------------------------------------------------
#
# A guided walkthrough of the platform rendered as an editorial modal
# rather than a SaaS spotlight overlay. Each volume is a chapter with
# an eyebrow + serif title + body copy + optional "Try it" link to
# the matching feature. Reads / writes ``localStorage["rcm_tour_v1"]``
# so dismissals persist across sessions.
#
# Entry points:
#   - ``?tour=1`` query param on any page (opens at volume 1, or the
#     value of ``?tour=N`` for direct volume jump)
#   - JS: ``window.ckTour.open(volumeIndex)``
#   - Settings → "Restart tour"
#
# Storage shape:
#   { "version": 1, "completed": [1,2,3], "lastViewed": 3,
#     "skipped": false }


def ck_tour_overlay(volumes: List[Dict[str, Any]]) -> str:
    """Editorial tour overlay primitive.

    ``volumes`` is an ordered list of dicts with these keys:

      - ``eyebrow``: short caps label e.g. "Volume I"
      - ``title``: serif headline (italic word marked with ``<em>``
        in the source string is honoured)
      - ``body``: long-form HTML (paragraphs welcome, will not be
        escaped — author is responsible for clean markup)
      - ``try_it``: optional dict ``{"label": "...", "href": "/..."}``
        rendering a primary CTA that lands the partner in the feature

    Returns a self-contained block: scoped CSS, hidden markup, and
    the JS controller. Drop into ``chartis_shell``'s body or any
    page that wants the tour. Safe to inject on every page — the
    controller only opens when ``?tour`` is present or
    ``ckTour.open()`` is called.
    """
    if not volumes:
        return ""
    volumes_json = json.dumps(volumes, ensure_ascii=False)
    total = len(volumes)
    return (
        _CK_TOUR_CSS
        + (
            '<div class="ck-tour" id="ck-tour" hidden role="dialog" '
            'aria-modal="true" aria-labelledby="ck-tour-title">'
            '<div class="ck-tour-backdrop" data-ck-tour-close></div>'
            '<div class="ck-tour-card" role="document">'
            '<button class="ck-tour-close" data-ck-tour-close '
            'aria-label="Close tour" type="button">&times;</button>'
            '<div class="ck-tour-progress">'
            '<span id="ck-tour-progress-current">I</span>'
            f' of {_roman(total)}'
            '</div>'
            '<div class="ck-tour-eyebrow" id="ck-tour-eyebrow"></div>'
            '<h2 class="ck-tour-title" id="ck-tour-title"></h2>'
            '<div class="ck-tour-body" id="ck-tour-body"></div>'
            '<div class="ck-tour-footer">'
            '<button class="ck-tour-skip" data-ck-tour-skip '
            'type="button">Skip the tour</button>'
            '<div class="ck-tour-nav">'
            '<button class="ck-tour-prev" data-ck-tour-prev '
            'type="button">← Back</button>'
            '<button class="ck-tour-next" data-ck-tour-next '
            'type="button">Continue →</button>'
            '</div>'
            '</div>'
            '<a class="ck-tour-tryit" id="ck-tour-tryit" hidden '
            'href="#">Try it now →</a>'
            '</div>'
            '</div>'
        )
        + f'<script>window.CK_TOUR_VOLUMES={volumes_json};</script>'
        + _CK_TOUR_JS
    )


def _roman(n: int) -> str:
    """Convert 1..20 to Roman numerals for editorial pagination."""
    table = [
        (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
    ]
    out = ""
    for value, sym in table:
        while n >= value:
            out += sym
            n -= value
    return out


_CK_TOUR_CSS = """
<style>
.ck-tour { position: fixed; inset: 0; z-index: 10000; }
.ck-tour[hidden] { display: none !important; }
.ck-tour-backdrop {
  position: absolute; inset: 0;
  background: rgba(11, 35, 65, 0.42);
  backdrop-filter: blur(2px);
}
.ck-tour-card {
  position: relative; max-width: 640px; width: calc(100% - 32px);
  margin: 7vh auto; background: var(--sc-bone, #f2ede3);
  border: 1px solid var(--sc-rule, #d8d3c8); border-radius: 4px;
  padding: 44px 48px 32px; box-shadow: 0 24px 60px rgba(0,0,0,0.2);
  font-family: "Source Serif 4", Georgia, serif;
  color: var(--sc-text, #1a2332); line-height: 1.55;
}
.ck-tour-close {
  position: absolute; top: 14px; right: 16px;
  background: none; border: 0; cursor: pointer; padding: 4px 8px;
  font-size: 24px; line-height: 1; color: var(--sc-text-faint, #6e7787);
  transition: color 120ms ease;
}
.ck-tour-close:hover { color: var(--sc-text, #1a2332); }
.ck-tour-progress {
  font-family: "JetBrains Mono", monospace; font-size: 10px;
  letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--sc-text-faint, #6e7787); margin-bottom: 16px;
}
.ck-tour-eyebrow {
  font-family: "Inter Tight", sans-serif; font-size: 11px;
  font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--sc-teal-ink, #0e3e3a); margin-bottom: 10px;
}
.ck-tour-title {
  font-family: "Source Serif 4", serif; font-weight: 400;
  font-size: clamp(28px, 4vw, 36px); line-height: 1.1;
  letter-spacing: -0.018em; color: var(--sc-navy, #0b2341);
  margin: 0 0 18px;
}
.ck-tour-title em {
  font-style: italic; color: var(--sc-teal-ink, #0e3e3a);
  font-weight: 400;
}
.ck-tour-body {
  font-size: 15px; line-height: 1.65;
  color: var(--sc-text-dim, #37495e); max-width: 56ch;
}
.ck-tour-body p { margin: 0 0 14px; }
.ck-tour-body p:last-child { margin-bottom: 0; }
.ck-tour-body em {
  font-style: italic; color: var(--sc-teal-ink, #0e3e3a);
}
.ck-tour-body strong {
  color: var(--sc-navy, #0b2341); font-weight: 600;
}
.ck-tour-footer {
  display: flex; align-items: center; justify-content: space-between;
  gap: 16px; margin-top: 28px; padding-top: 18px;
  border-top: 1px solid var(--sc-rule, #d8d3c8);
}
.ck-tour-skip {
  background: none; border: 0; cursor: pointer; padding: 0;
  font-family: "Source Serif 4", serif; font-style: italic;
  font-size: 13px; color: var(--sc-text-faint, #6e7787);
  text-decoration: underline; text-underline-offset: 3px;
  text-decoration-color: transparent;
  transition: text-decoration-color 120ms ease;
}
.ck-tour-skip:hover {
  text-decoration-color: var(--sc-text-faint, #6e7787);
}
.ck-tour-nav { display: flex; gap: 8px; }
.ck-tour-prev, .ck-tour-next {
  font-family: "Inter Tight", sans-serif; font-weight: 600;
  font-size: 12px; letter-spacing: 0.04em;
  padding: 8px 14px; border-radius: 2px; cursor: pointer;
  transition: filter 120ms ease, border-color 120ms ease;
}
.ck-tour-prev {
  background: transparent; color: var(--sc-text-dim, #37495e);
  border: 1px solid var(--sc-rule, #d8d3c8);
}
.ck-tour-prev:hover { border-color: var(--sc-text, #1a2332); }
.ck-tour-prev[disabled] { opacity: 0.4; cursor: not-allowed; }
.ck-tour-next {
  background: var(--sc-navy, #0b2341); color: #fff; border: 0;
}
.ck-tour-next:hover { filter: brightness(1.12); }
.ck-tour-tryit {
  display: block; margin-top: 14px; text-align: right;
  font-family: "Inter Tight", sans-serif; font-size: 12px;
  font-weight: 600; letter-spacing: 0.04em;
  color: var(--sc-teal-ink, #0e3e3a); text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color 120ms ease;
}
.ck-tour-tryit:hover {
  border-bottom-color: var(--sc-teal-ink, #0e3e3a);
}
.ck-tour-tryit[hidden] { display: none !important; }
@media (max-width: 540px) {
  .ck-tour-card { padding: 32px 24px 24px; margin: 4vh auto; }
  .ck-tour-title { font-size: 24px; }
  .ck-tour-footer { flex-direction: column; align-items: stretch; }
  .ck-tour-nav { justify-content: space-between; }
}
@media print { .ck-tour { display: none !important; } }
</style>
"""

_CK_TOUR_JS = """
<script>
(function() {
  var STORAGE_KEY = "rcm_tour_v1";
  var ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII",
               "IX", "X", "XI", "XII"];
  var volumes = window.CK_TOUR_VOLUMES || [];
  if (!volumes.length) return;
  var idx = 0;
  function loadState() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return { version: 1, completed: [], lastViewed: 0,
                         skipped: false };
      var s = JSON.parse(raw);
      if (s.version !== 1) {
        return { version: 1, completed: [], lastViewed: 0,
                 skipped: false };
      }
      return s;
    } catch (e) {
      return { version: 1, completed: [], lastViewed: 0,
               skipped: false };
    }
  }
  function saveState(s) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(s)); }
    catch (e) { /* quota / disabled storage — ignore */ }
  }
  function paint() {
    var vol = volumes[idx];
    if (!vol) return;
    var $ = document.getElementById.bind(document);
    $("ck-tour-progress-current").textContent = ROMAN[idx + 1] || (idx + 1);
    $("ck-tour-eyebrow").textContent = vol.eyebrow || "";
    $("ck-tour-title").innerHTML = vol.title || "";
    $("ck-tour-body").innerHTML = vol.body || "";
    var prev = document.querySelector("[data-ck-tour-prev]");
    if (prev) prev.disabled = (idx === 0);
    var next = document.querySelector("[data-ck-tour-next]");
    if (next) {
      next.textContent = (idx === volumes.length - 1)
        ? "Finish ✓" : "Continue →";
    }
    var tryit = $("ck-tour-tryit");
    if (vol.try_it && vol.try_it.label && vol.try_it.href) {
      tryit.textContent = vol.try_it.label + " →";
      tryit.href = vol.try_it.href;
      tryit.hidden = false;
    } else {
      tryit.hidden = true;
    }
  }
  function open(volumeIdx) {
    idx = Math.max(0, Math.min(volumes.length - 1, (volumeIdx || 1) - 1));
    paint();
    var el = document.getElementById("ck-tour");
    if (el) {
      el.hidden = false;
      var s = loadState();
      s.lastViewed = idx + 1;
      s.skipped = false;
      saveState(s);
    }
  }
  function close() {
    var el = document.getElementById("ck-tour");
    if (el) el.hidden = true;
  }
  function next() {
    var s = loadState();
    if (!s.completed.includes(idx + 1)) s.completed.push(idx + 1);
    saveState(s);
    if (idx >= volumes.length - 1) {
      close();
      return;
    }
    idx += 1;
    paint();
    s = loadState(); s.lastViewed = idx + 1; saveState(s);
  }
  function prev() {
    if (idx === 0) return;
    idx -= 1;
    paint();
    var s = loadState(); s.lastViewed = idx + 1; saveState(s);
  }
  function skip() {
    var s = loadState(); s.skipped = true; saveState(s);
    close();
  }
  window.ckTour = {
    open: open, close: close, next: next, prev: prev, skip: skip,
  };
  document.addEventListener("click", function(e) {
    var t = e.target;
    if (!t.closest) return;
    if (t.closest("[data-ck-tour-close]")) { close(); }
    if (t.closest("[data-ck-tour-skip]"))  { skip();  }
    if (t.closest("[data-ck-tour-next]"))  { next();  }
    if (t.closest("[data-ck-tour-prev]"))  { prev();  }
  });
  document.addEventListener("keydown", function(e) {
    var el = document.getElementById("ck-tour");
    if (!el || el.hidden) return;
    if (e.key === "Escape")     { close(); }
    if (e.key === "ArrowRight" || e.key === "Enter") { next(); }
    if (e.key === "ArrowLeft")  { prev();  }
  });
  // Auto-open via ?tour=1 (or ?tour=N for direct volume jump)
  document.addEventListener("DOMContentLoaded", function() {
    try {
      var params = new URLSearchParams(window.location.search);
      var t = params.get("tour");
      if (t !== null) {
        var n = parseInt(t, 10);
        open(isNaN(n) || n < 1 ? 1 : n);
      }
    } catch (e) { /* old browsers — ignore */ }
  });
})();
</script>
"""


# Default tour content — seven editorial volumes covering every
# surface a partner needs to navigate. Stored as module-level data so
# chartis_shell can inject the tour on every page without each
# renderer authoring its own. Each volume reads as a short research
# note rather than SaaS onboarding copy.
_TOUR_VOLUMES: List[Dict[str, Any]] = [
    {
        "eyebrow": "Volume I",
        "title": "The <em>Pipeline</em>.",
        "body": (
            "<p>Every engagement begins at the same surface — the "
            "deal pipeline. Hospitals enter as candidates from "
            "screening; advance through outreach, LOI, diligence, "
            "and IC; exit either to your portfolio or to the "
            "watchlist for next quarter.</p>"
            "<p>Click any deal to open its <strong>profile</strong> "
            "— the single source of truth for every analytic on "
            "the platform. The profile carries your deal parameters "
            "(NPR, EBITDA, specialty, state) into every downstream "
            "tool so you never re-type them.</p>"
            "<p>The funnel on the left of <strong>/app</strong> "
            "shows stage counts at a glance. The activity panel on "
            "the right shows what changed in the last seven days.</p>"
        ),
        "try_it": {"label": "Open the pipeline", "href": "/pipeline"},
    },
    {
        "eyebrow": "Volume II",
        "title": "<em>Diligence</em>.",
        "body": (
            "<p>The diligence layer is where the platform earns its "
            "keep. Six analytics ladder up to a complete RCM and PE "
            "picture:</p>"
            "<p><strong>CCD ingestion</strong> converts the seller's "
            "data room into structured records. <strong>HFMA "
            "benchmarks</strong> compare every initiative to "
            "industry priors with conformal confidence bands. "
            "<strong>Denial prediction</strong> projects per-payer "
            "write-off rates against the seller's actuals.</p>"
            "<p><strong>HCRIS Peer X-Ray</strong> surfaces what "
            "cost-report data says about competitive position. "
            "<strong>Counterfactual analysis</strong> answers "
            "<em>what would EBITDA have been without this "
            "initiative</em>. The <strong>diligence checklist</strong> "
            "gates IC approval — items must be cleared before the "
            "deal advances.</p>"
            "<p>Click any tool from the deal profile and your deal "
            "parameters pre-fill. No re-typing.</p>"
        ),
        "try_it": {
            "label": "Open the diligence index",
            "href": "/diligence",
        },
    },
    {
        "eyebrow": "Volume III",
        "title": "The <em>Risk</em> Workbench.",
        "body": (
            "<p>The Risk Workbench groups every risk surface into "
            "three tiers of attention.</p>"
            "<p><strong>Tier 1</strong> — bankruptcy survival, "
            "covenant headroom, payer concentration. Existential "
            "risks that kill deals at IC.</p>"
            "<p><strong>Tier 2</strong> — physician attrition, "
            "denial rate, regulatory exposure, cyber posture. "
            "Material risks that erode EBITDA.</p>"
            "<p><strong>Tier 3</strong> — management bench depth, "
            "IT modernization debt, M&amp;A integration drag. "
            "Slow-burn risks that show up in year three.</p>"
            "<p>Each panel cites its source — HCRIS, CMS, public "
            "filings — so you can audit the chain from claim to "
            "conclusion.</p>"
        ),
        "try_it": {
            "label": "Open the risk workbench",
            "href": "/diligence/risk-workbench",
        },
    },
    {
        "eyebrow": "Volume IV",
        "title": "Financial <em>Synthesis</em>.",
        "body": (
            "<p>Once diligence is complete, the platform synthesises "
            "a financial story:</p>"
            "<p>The <strong>7-lever EBITDA bridge</strong> "
            "decomposes year-0 to year-3 EBITDA into "
            "initiative-specific contributions. The <strong>two-"
            "source Monte Carlo</strong> runs N=1,000+ paths "
            "combining historical claim variance and forward-looking "
            "initiative impact, returning P10/P50/P90 EBITDA "
            "distributions.</p>"
            "<p><strong>Public-market overlay</strong> pulls "
            "EV/EBITDA bands from healthcare peers and prices your "
            "deal against the band. <strong>Covenant headroom math</strong> "
            "projects the post-close credit stack against bank "
            "covenants with stress paths.</p>"
            "<p>Every number on the synthesis pages carries a "
            "provenance tooltip showing which inputs produced it.</p>"
        ),
        "try_it": {
            "label": "Open the EBITDA bridge",
            "href": "/pipeline/bridge",
        },
    },
    {
        "eyebrow": "Volume V",
        "title": "The <em>Portfolio</em>.",
        "body": (
            "<p>After close, deals move to the portfolio surface. "
            "<strong>Alerts</strong> fire when covenant headroom "
            "narrows, EBITDA misses plan, or initiative variance "
            "crosses thresholds. Acknowledge them, snooze them, or "
            "escalate to the partner.</p>"
            "<p><strong>Watchlists</strong> slice the portfolio by "
            "sector, vintage, owner, or arbitrary tag. The "
            "<strong>health score</strong> is a composite 0-100 per "
            "deal with a trend sparkline. The "
            "<strong>/my/&lt;owner&gt;</strong> page shows your "
            "personal queue.</p>"
            "<p><strong>Cohorts</strong> group deals by structural "
            "similarity so you can ask <em>how have all my friendly "
            "PC deals performed since 2024</em> and see the answer "
            "in one chart.</p>"
        ),
        "try_it": {
            "label": "Open the portfolio",
            "href": "/portfolio",
        },
    },
    {
        "eyebrow": "Volume VI",
        "title": "<em>Delivery</em>.",
        "body": (
            "<p>Every engagement ends in deliverables. The platform "
            "generates IC packets, exit memos, and LP digests as "
            "editorial HTML — partner-ready, print-friendly, "
            "share-friendly.</p>"
            "<p><strong>IC memos</strong> pull from the analysis "
            "packet automatically. The <strong>bear case</strong> is "
            "generated from the risk workbench. The "
            "<strong>LP digest</strong> aggregates portfolio-level "
            "performance into a quarterly narrative.</p>"
            "<p>Exports are CSV (sanitised against Excel formula "
            "injection), HTML, JSON, or — for the IC memo and "
            "packet — print-PDF. Every export caps the chain of "
            "citation so the LP can audit any number back to its "
            "source.</p>"
        ),
        "try_it": {
            "label": "Open the LP digest",
            "href": "/lp-update",
        },
    },
    {
        "eyebrow": "Volume VII",
        "title": "Settings &amp; <em>Workflow</em>.",
        "body": (
            "<p>A handful of details that compound over time:</p>"
            "<p><strong>Cmd+K</strong> opens the command palette — "
            "every analytic surface is one keystroke away. The "
            "<strong>deal slug</strong> (e.g. "
            "<em>/diligence/deal/aurora</em>) is bookmarkable and "
            "shareable; deal parameters persist in your browser "
            "localStorage so a refresh or returning tomorrow picks "
            "up where you left off.</p>"
            "<p>State-changing actions <strong>flash a toast</strong> "
            "so you have confirmation. The <strong>?legacy=1</strong> "
            "query parameter falls back to the legacy dashboard if "
            "you preferred it; <strong>?v2=1</strong> the older "
            "modern view.</p>"
            "<p>You can restart this tour any time from "
            "<strong>Settings → Platform Tutorial</strong>. "
            "Welcome to the platform.</p>"
        ),
        "try_it": {
            "label": "Open settings",
            "href": "/settings",
        },
    },
]


def ck_quick_capture() -> str:
    """Global 'Quick capture' modal — Shift+Q anywhere on the
    platform pops a small editorial overlay where a partner can jot
    a diligence question without leaving the surface they're on.

    The modal:
      - Auto-fills the deal slug from rcm_recent_deals[0] so the
        most-recent deal is the default target. Slug is editable.
      - Carries the same six categories as the deal-profile
        question editor (financial / clinical / regulatory / legal
        / operational / other).
      - Persists onto rcm_deal_<slug>_questions in the same shape
        as the deal-profile editor — partners see the captured
        question next time they open that deal's profile.

    Auto-injected by chartis_shell so the shortcut works on every
    page. Esc closes; submit saves + closes. No server roundtrip.
    """
    return _CK_QC_CSS + _CK_QC_HTML + _CK_QC_JS


_CK_QC_CSS = """
<style>
.ck-qc { position: fixed; inset: 0; z-index: 10001; }
.ck-qc[hidden] { display: none !important; }
.ck-qc-backdrop {
  position: absolute; inset: 0;
  background: rgba(11, 35, 65, 0.42);
  backdrop-filter: blur(2px);
}
.ck-qc-card {
  position: relative; max-width: 520px; width: calc(100% - 32px);
  margin: 14vh auto; background: var(--sc-bone, #f2ede3);
  border: 1px solid var(--sc-rule, #d8d3c8); border-radius: 4px;
  padding: 32px 36px 24px; box-shadow: 0 24px 60px rgba(0,0,0,0.2);
  font-family: "Source Serif 4", Georgia, serif;
  color: var(--sc-text, #1a2332);
}
.ck-qc-eyebrow {
  font-family: "Inter Tight", sans-serif;
  font-size: 10px; font-weight: 700; letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--sc-teal-ink, #0e3e3a); margin-bottom: 8px;
}
.ck-qc-title {
  font-family: "Source Serif 4", serif; font-weight: 400;
  font-size: 24px; line-height: 1.15; letter-spacing: -0.012em;
  color: var(--sc-navy, #0b2341); margin: 0 0 6px;
}
.ck-qc-title em {
  font-style: italic; color: var(--sc-teal-ink, #0e3e3a);
}
.ck-qc-prose {
  font-family: "Source Serif 4", serif; font-style: italic;
  font-size: 13px; line-height: 1.5;
  color: var(--sc-text-dim, #37495e); margin: 0 0 16px;
}
.ck-qc-row {
  display: grid; grid-template-columns: 1fr 130px;
  gap: 10px; margin-bottom: 12px;
}
.ck-qc-field { display: flex; flex-direction: column; gap: 4px; }
.ck-qc-label {
  font-family: "Inter Tight", sans-serif; font-size: 9px;
  font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--sc-text-faint, #6e7787);
}
.ck-qc-input, .ck-qc-textarea, .ck-qc-select {
  background: #fff; color: var(--sc-text, #1a2332);
  border: 1px solid var(--sc-rule, #d8d3c8); border-radius: 3px;
  padding: 8px 10px; font-size: 13px;
  font-family: "Source Serif 4", serif;
  transition: border-color 120ms ease, box-shadow 120ms ease;
}
.ck-qc-select {
  font-family: "Inter Tight", sans-serif; font-size: 11px;
  font-weight: 600; letter-spacing: 0.06em;
  appearance: none; -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath fill='%236e7787' d='M0 0l5 6 5-6z'/%3E%3C/svg%3E");
  background-repeat: no-repeat; background-position: right 8px center;
  padding-right: 26px;
}
.ck-qc-textarea { min-height: 84px; resize: vertical; }
.ck-qc-input:focus, .ck-qc-textarea:focus, .ck-qc-select:focus {
  outline: none; border-color: var(--sc-teal-ink, #0e3e3a);
  box-shadow: 0 0 0 2px rgba(21,87,82,0.18);
}
.ck-qc-footer {
  display: flex; align-items: center; justify-content: space-between;
  gap: 14px; margin-top: 18px; padding-top: 14px;
  border-top: 1px solid var(--sc-rule, #d8d3c8);
}
.ck-qc-hint {
  font-family: "Source Serif 4", serif; font-style: italic;
  font-size: 11px; color: var(--sc-text-faint, #6e7787);
}
.ck-qc-hint kbd {
  display: inline-block; padding: 1px 5px;
  background: #fff; border: 1px solid var(--sc-rule, #d8d3c8);
  border-radius: 2px; font-family: "JetBrains Mono", monospace;
  font-size: 10px; font-style: normal; color: var(--sc-text, #1a2332);
  vertical-align: 1px;
}
.ck-qc-actions { display: flex; gap: 8px; }
.ck-qc-cancel, .ck-qc-save {
  font-family: "Inter Tight", sans-serif; font-weight: 600;
  font-size: 12px; letter-spacing: 0.04em;
  padding: 8px 14px; border-radius: 2px; cursor: pointer;
  transition: filter 120ms ease, border-color 120ms ease;
}
.ck-qc-cancel {
  background: transparent; color: var(--sc-text-dim, #37495e);
  border: 1px solid var(--sc-rule, #d8d3c8);
}
.ck-qc-cancel:hover { border-color: var(--sc-text, #1a2332); }
.ck-qc-save {
  background: var(--sc-navy, #0b2341); color: #fff; border: 0;
}
.ck-qc-save:hover { filter: brightness(1.12); }
.ck-qc-toast {
  position: absolute; bottom: -36px; left: 0; right: 0;
  text-align: center;
  font-family: "Source Serif 4", serif; font-style: italic;
  font-size: 12px; color: var(--sc-positive, #0a8a5f);
  opacity: 0; transition: opacity 200ms ease;
}
.ck-qc-toast.is-visible { opacity: 1; }
@media print { .ck-qc { display: none !important; } }
</style>
"""

_CK_QC_HTML = """
<div class="ck-qc" id="ck-qc" hidden role="dialog" aria-modal="true"
     aria-labelledby="ck-qc-title">
  <div class="ck-qc-backdrop" data-ck-qc-close></div>
  <div class="ck-qc-card" role="document">
    <div class="ck-qc-eyebrow">Quick capture · Shift+Q</div>
    <h2 class="ck-qc-title" id="ck-qc-title">
      Jot a <em>diligence</em> question.
    </h2>
    <p class="ck-qc-prose">
      Saves to the deal's question list. You'll see it next time
      you open that deal profile.
    </p>
    <form data-ck-qc-form>
      <div class="ck-qc-row">
        <div class="ck-qc-field">
          <label class="ck-qc-label" for="ck-qc-slug">Deal slug</label>
          <input class="ck-qc-input" id="ck-qc-slug"
                 data-ck-qc-slug autocomplete="off"/>
        </div>
        <div class="ck-qc-field">
          <label class="ck-qc-label" for="ck-qc-cat">Category</label>
          <select class="ck-qc-select" id="ck-qc-cat" data-ck-qc-cat>
            <option value="financial">Financial</option>
            <option value="clinical">Clinical</option>
            <option value="regulatory">Regulatory</option>
            <option value="legal">Legal</option>
            <option value="operational">Operational</option>
            <option value="other">Other</option>
          </select>
        </div>
      </div>
      <div class="ck-qc-field">
        <label class="ck-qc-label" for="ck-qc-text">Question</label>
        <textarea class="ck-qc-textarea" id="ck-qc-text"
                  data-ck-qc-text maxlength="280"
                  placeholder="e.g. What share of NPR comes from out-of-network rates?"></textarea>
      </div>
      <div class="ck-qc-footer">
        <span class="ck-qc-hint">
          <kbd>Esc</kbd> close · <kbd>⌘</kbd><kbd>Enter</kbd> save
        </span>
        <div class="ck-qc-actions">
          <button type="button" class="ck-qc-cancel"
                  data-ck-qc-close>Cancel</button>
          <button type="submit" class="ck-qc-save"
                  data-ck-qc-save>Save question →</button>
        </div>
      </div>
    </form>
    <div class="ck-qc-toast" data-ck-qc-toast></div>
  </div>
</div>
"""

_CK_QC_JS = """
<script>
(function() {
  function el(sel) { return document.querySelector(sel); }
  function open() {
    var qc = el("#ck-qc"); if (!qc) return;
    var slugIn = qc.querySelector("[data-ck-qc-slug]");
    var textIn = qc.querySelector("[data-ck-qc-text]");
    if (slugIn && !slugIn.value) {
      // Auto-fill from rcm_recent_deals[0] so the most-recent deal
      // is the default target. Partner can edit before saving.
      try {
        var raw = localStorage.getItem("rcm_recent_deals");
        var rows = raw ? JSON.parse(raw) : [];
        if (Array.isArray(rows) && rows.length && rows[0].slug) {
          slugIn.value = rows[0].slug;
        }
      } catch (e) { /* ignore */ }
    }
    // Restore the last-used category so partners doing several
    // captures in the same area (e.g. four Regulatory questions
    // in a row) don't reset to Financial each time. localStorage
    // key persists across sessions.
    var catIn = qc.querySelector("[data-ck-qc-cat]");
    if (catIn) {
      try {
        var last = localStorage.getItem("rcm_qc_last_cat");
        if (last) {
          var opts = catIn.options;
          for (var i = 0; i < opts.length; i++) {
            if (opts[i].value === last) { catIn.value = last; break; }
          }
        }
      } catch (e) { /* ignore */ }
    }
    qc.hidden = false;
    if (textIn) setTimeout(function() { textIn.focus(); }, 0);
  }
  function close() {
    var qc = el("#ck-qc"); if (qc) qc.hidden = true;
  }
  function toast(msg, tone) {
    var t = el("[data-ck-qc-toast]"); if (!t) return;
    t.textContent = msg;
    t.style.color = (tone === "neg") ? "#b5321e" : "";
    t.classList.add("is-visible");
    setTimeout(function() { t.classList.remove("is-visible"); }, 1500);
  }
  function save() {
    var qc = el("#ck-qc"); if (!qc) return;
    var slug = (qc.querySelector("[data-ck-qc-slug]").value || "")
      .trim().toLowerCase();
    var text = (qc.querySelector("[data-ck-qc-text]").value || "").trim();
    var cat = qc.querySelector("[data-ck-qc-cat]").value || "financial";
    if (!slug) { toast("Need a deal slug.", "neg"); return; }
    if (!text) { toast("Need a question.", "neg"); return; }
    try {
      var key = "rcm_deal_" + slug + "_questions";
      var raw = localStorage.getItem(key);
      var rows = raw ? JSON.parse(raw) : [];
      if (!Array.isArray(rows)) rows = [];
      rows.unshift({
        id: "q" + Date.now() + Math.random().toString(36).slice(2, 6),
        text: text, ts: Date.now(), asked: false, category: cat,
      });
      localStorage.setItem(key, JSON.stringify(rows));
      // Persist last-used category so the next Quick-capture
      // opens with it pre-selected.
      try { localStorage.setItem("rcm_qc_last_cat", cat); }
      catch (e) { /* ignore */ }
      toast("Saved to " + slug + ".");
      qc.querySelector("[data-ck-qc-text]").value = "";
      // Auto-close after a beat so partner sees the confirmation
      setTimeout(close, 850);
    } catch (e) { toast("Save failed.", "neg"); }
  }
  window.ckQuickCapture = { open: open, close: close };
  document.addEventListener("keydown", function(e) {
    if (e.target && (e.target.tagName === "INPUT"
        || e.target.tagName === "TEXTAREA"
        || e.target.isContentEditable)) {
      // While the QC modal is open we DO want keystrokes to flow
      // into the inputs, but ⌘+Enter must still save and Esc must
      // still close.
      var qc = el("#ck-qc");
      if (qc && !qc.hidden) {
        if (e.key === "Escape") { e.preventDefault(); close(); }
        if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
          e.preventDefault(); save();
        }
      }
      return;
    }
    if (e.shiftKey && (e.key === "Q" || e.key === "q")
        && !e.metaKey && !e.ctrlKey && !e.altKey) {
      e.preventDefault();
      var qcEl = el("#ck-qc");
      if (qcEl && qcEl.hidden) open(); else close();
    }
    if (e.key === "Escape") {
      var qc2 = el("#ck-qc");
      if (qc2 && !qc2.hidden) { e.preventDefault(); close(); }
    }
  });
  document.addEventListener("click", function(e) {
    if (e.target.closest && e.target.closest("[data-ck-qc-close]")) {
      close();
    }
  });
  document.addEventListener("submit", function(e) {
    if (e.target.closest && e.target.closest("[data-ck-qc-form]")) {
      e.preventDefault();
      save();
    }
  });
}());
</script>
"""


def ck_default_tour() -> str:
    """Return the editorial tour overlay rendered with the seven
    default volumes. Injected by ``chartis_shell`` so the tour
    works on every page via ``?tour=1`` or ``window.ckTour.open()``.
    """
    return ck_tour_overlay(_TOUR_VOLUMES)


def ck_empty_state(
    title: str,
    body: Optional[str] = None,
    *,
    eyebrow: Optional[str] = None,
    cta_label: Optional[str] = None,
    cta_href: Optional[str] = None,
    icon: Optional[str] = None,
    tone: str = "neutral",
) -> str:
    """Editorial empty-state card — eyebrow + serif title + body + CTA.

    The "no data here yet" surface every page reaches for when its
    table / list / chart has nothing to show. Replaces the various
    legacy ``<p class="muted">No items.</p>`` one-liners that read
    as bare and unfinished.

    Args:
        title:      Serif headline. e.g. "No starred deals yet."
        body:       Optional paragraph explaining what to do next.
        eyebrow:    Optional small mono caps line above title.
        cta_label:  If provided with cta_href, renders a primary
                    button — the recommended action that fills the
                    empty state.
        cta_href:   Destination for the CTA.
        icon:       Optional unicode glyph or HTML snippet rendered
                    in a circular bone-tinted slot above the eyebrow.
                    e.g. "★" for watchlist, "✓" for done states.
        tone:       "neutral" (default), "positive" (green left
                    accent — useful for "all clear" empty-as-success
                    states like "no active alerts"), or "warning".
    """
    tone = tone if tone in ("neutral", "positive", "warning") else "neutral"
    eyebrow_html = (
        f'<div class="ck-eyebrow">{_esc(eyebrow)}</div>' if eyebrow else ""
    )
    icon_html = (
        f'<div class="ck-empty-state-icon">{icon}</div>'  # pre-escaped/glyph
        if icon else ""
    )
    body_html = (
        f'<p class="ck-empty-state-body">{_esc(body)}</p>' if body else ""
    )
    cta_html = ""
    if cta_label and cta_href:
        cta_html = (
            '<div class="ck-empty-state-actions">'
            f'<a class="ck-empty-state-cta" '
            f'href="{_esc(cta_href)}">{_esc(cta_label)}</a>'
            '</div>'
        )
    return (
        f'<div class="ck-empty-state ck-empty-state-{tone}">'
        f'{icon_html}'
        f'{eyebrow_html}'
        f'<h2 class="ck-empty-state-title">{_esc(title)}</h2>'
        f'{body_html}'
        f'{cta_html}'
        '</div>'
    )


def ck_arrow_link(text: str, href: str, *, on_navy: bool = False) -> str:
    """Teal "VIEW MORE ↗" arrow link, the primary editorial CTA."""
    cls = "ck-arrow on-navy" if on_navy else "ck-arrow"
    return f'<a class="{cls}" href="{_esc(href)}">{_esc(text)}</a>'


# ╔══════════════════════════════════════════════════════════════════╗
# ║  2026-05-28 usability helpers · ck_copy_share_link_button +      ║
# ║  ck_recently_viewed_rail                                          ║
# ║                                                                   ║
# ║  Two small reusable primitives extracted from covenant_lab +     ║
# ║  payer_stress sweeps (#1072) so any page can opt-in to the       ║
# ║  same Copy share link button without duplicating the JS install. ║
# ║  ck_recently_viewed_rail hydrates from the rcm_recent_deals      ║
# ║  localStorage key that deal_profile_page already populates.      ║
# ╚══════════════════════════════════════════════════════════════════╝


# Install JS once per page — guards against the duplicate install
# that happens when two helpers co-emit the snippet (e.g. share
# button + recently-viewed rail on the same page).
_CK_SHARE_LINK_JS = """
<script>
(function(){
  if (window.__rcmCopyShareLinkInstalled) return;
  window.__rcmCopyShareLinkInstalled = true;
  function bind(){
    document.querySelectorAll('[data-rcm-share-link]').forEach(function(btn){
      btn.addEventListener('click', function(ev){
        ev.preventDefault();
        var url = window.location.href;
        var original = btn.textContent;
        var ok = function(){
          btn.textContent = 'Copied ✓';
          setTimeout(function(){ btn.textContent = original; }, 1800);
        };
        var fail = function(){
          btn.textContent = 'Copy failed';
          setTimeout(function(){ btn.textContent = original; }, 1800);
        };
        if (navigator.clipboard && navigator.clipboard.writeText){
          navigator.clipboard.writeText(url).then(ok, fail);
        } else {
          try {
            var ta = document.createElement('textarea');
            ta.value = url; document.body.appendChild(ta);
            ta.select(); document.execCommand('copy');
            document.body.removeChild(ta); ok();
          } catch(e){ fail(); }
        }
      });
    });
  }
  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', bind);
  } else { bind(); }
})();
</script>
"""

_CK_SHARE_LINK_CSS = """
<style>
.ck-share-btn{font:500 11px/1 var(--sc-sans,Inter),sans-serif;
  letter-spacing:.08em;text-transform:uppercase;
  color:var(--ink,#16263a);background:var(--paper-card,#fefcf3);
  border:1px solid var(--rule,#c9bf9c);border-radius:2px;
  padding:9px 14px;text-decoration:none;cursor:pointer;
  transition:background .12s,border-color .12s;}
.ck-share-btn:hover{background:var(--paper-hi,#fbf6e8);
  border-color:var(--rule-hi,#b6a87f);}
.ck-share-btn:focus-visible{outline:2px solid var(--green-deep,#154e36);
  outline-offset:-1px;}
</style>
"""


def ck_copy_share_link_button(label: str = "Copy share link") -> str:
    """Reusable Copy-share-link button.

    Returns CSS + JS + button HTML. The JS is idempotent —
    ``window.__rcmCopyShareLinkInstalled`` guards against duplicate
    install when multiple helpers emit the snippet on one page. Wire
    the button anywhere a deep-link is useful (analytic report
    masthead, scenario page header, etc.).
    """
    return (
        _CK_SHARE_LINK_CSS
        + _CK_SHARE_LINK_JS
        + (
            f'<button type="button" class="ck-share-btn" '
            f'data-rcm-share-link>{_esc(label)}</button>'
        )
    )


_CK_RECENT_CSS = """
<style>
.ck-recent{background:var(--paper-card,#fefcf3);
  border:1px solid var(--rule,#c9bf9c);
  padding:20px 22px;margin:0 0 24px;}
.ck-recent .head{display:flex;justify-content:space-between;
  align-items:baseline;gap:14px;margin:0 0 14px;}
.ck-recent .eyebrow{font:500 10.5px/1 var(--sc-mono,monospace);
  letter-spacing:.18em;text-transform:uppercase;
  color:var(--green-deep,#154e36);display:flex;align-items:center;
  gap:10px;}
.ck-recent .eyebrow .dash{width:20px;height:1px;
  background:var(--green-deep,#154e36);}
.ck-recent .head .count{font:500 10.5px/1 var(--sc-mono,monospace);
  letter-spacing:.14em;text-transform:uppercase;
  color:var(--muted,#7a8595);}
.ck-recent ol{list-style:none;padding:0;margin:0;
  display:flex;flex-wrap:wrap;gap:8px;}
.ck-recent ol li{display:contents;}
.ck-recent a.pill{display:inline-flex;align-items:center;gap:8px;
  font:500 12.5px/1.2 var(--sc-sans,Inter),sans-serif;
  color:var(--ink,#16263a);background:var(--bg,#efeadd);
  border:1px solid var(--rule,#c9bf9c);border-radius:2px;
  padding:6px 12px;text-decoration:none;
  transition:background .12s,border-color .12s;}
.ck-recent a.pill:hover{background:var(--paper-hi,#fbf6e8);
  border-color:var(--rule-hi,#b6a87f);}
.ck-recent a.pill .slug{font-family:var(--sc-mono,monospace);
  font-size:10.5px;letter-spacing:.06em;
  color:var(--muted,#7a8595);}
.ck-recent .empty{font:400 italic 14px/1.5 var(--sc-serif,Georgia),serif;
  color:var(--ink-3,#506478);margin:0;max-width:64ch;}
</style>
"""

_CK_RECENT_JS = """
<script>
(function(){
  if (window.__rcmRecentlyViewedInstalled) return;
  window.__rcmRecentlyViewedInstalled = true;
  function paint(){
    var root = document.querySelector('[data-rcm-recent-deals]');
    if (!root) return;
    var raw = null;
    try { raw = localStorage.getItem('rcm_recent_deals'); }
    catch (e) { raw = null; }
    var rows = [];
    if (raw) { try { rows = JSON.parse(raw); } catch (e) { rows = []; } }
    if (!Array.isArray(rows)) rows = [];
    rows = rows.filter(function(r){
      return r && typeof r.slug === 'string';
    }).slice(0, 5);
    if (!rows.length){
      root.innerHTML = '<p class="empty">' +
        '<em>Visit a deal profile to populate this rail.</em> ' +
        'Open /diligence/deal/&lt;slug&gt; from anywhere ' +
        '(the screener, the pipeline funnel, the workbench) ' +
        'and it lands here for one-click re-entry.</p>';
      return;
    }
    var lis = rows.map(function(r){
      var slug = String(r.slug).replace(/[^a-z0-9-]/gi, '');
      var name = (r.name || slug).toString().slice(0, 40);
      var href = '/diligence/deal/' + encodeURIComponent(slug);
      return '<li><a class="pill" href="' + href + '">' +
        '<span>' + name.replace(/[<>&"]/g, '') + '</span>' +
        '<span class="slug">' + slug + '</span></a></li>';
    }).join('');
    root.innerHTML = '<ol>' + lis + '</ol>';
  }
  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', paint);
  } else { paint(); }
})();
</script>
"""


_CK_BACK_TO_TOP_CSS = """
<style>
.ck-back-to-top{position:fixed;bottom:24px;right:24px;
  font:500 11px/1 var(--sc-sans,Inter),sans-serif;
  letter-spacing:.08em;text-transform:uppercase;
  color:var(--ink,#16263a);background:var(--paper-card,#fefcf3);
  border:1px solid var(--rule,#c9bf9c);border-radius:2px;
  padding:9px 14px;text-decoration:none;cursor:pointer;
  display:none;opacity:0;
  transition:background .12s,border-color .12s,opacity .2s;
  z-index:50;}
.ck-back-to-top.ck-back-to-top-visible{display:inline-block;opacity:1;}
.ck-back-to-top:hover{background:var(--paper-hi,#fbf6e8);
  border-color:var(--rule-hi,#b6a87f);}
.ck-back-to-top:focus-visible{outline:2px solid var(--green-deep,#154e36);
  outline-offset:-1px;}
@media (max-width:720px){
  .ck-back-to-top{bottom:14px;right:14px;padding:7px 11px;
    font-size:10.5px;}
}
@media print{.ck-back-to-top{display:none!important;}}
</style>
"""

_CK_BACK_TO_TOP_JS = """
<script>
(function(){
  if (window.__rcmBackToTopInstalled) return;
  window.__rcmBackToTopInstalled = true;
  function install(){
    var btn = document.querySelector('[data-rcm-back-to-top]');
    if (!btn) return;
    var threshold = 600;
    function update(){
      var y = window.pageYOffset || document.documentElement.scrollTop;
      if (y > threshold) btn.classList.add('ck-back-to-top-visible');
      else btn.classList.remove('ck-back-to-top-visible');
    }
    btn.addEventListener('click', function(ev){
      ev.preventDefault();
      window.scrollTo({top:0, behavior:'smooth'});
    });
    window.addEventListener('scroll', update, {passive:true});
    update();
  }
  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', install);
  } else { install(); }
})();
</script>
"""


_CK_EDITORIAL_HEAD_CSS = """
<style>
/* 2026-05-28 batch-19 · universal strict Tier-1 5-block head. The
 * same shape ten separate page-local helpers had been emitting
 * (po-head / pp-head / lib-head / ss-head / home-head / do-head /
 *  bc-head / cv-head / ps-head / hp-head / dp-head / ap-head /
 *  sb-head / cl-head). Extracted to one helper so the remaining
 * ~270 pages can adopt the same masthead with one call. Scoped to
 * `.ck-eh` so it doesn't collide with any page-local head class. */
.ck-eh{padding:0 0 28px;margin:0 0 24px;
  border-bottom:1px solid var(--rule-soft,#ddd1ac);}
.ck-eh .ck-eh-row{display:flex;justify-content:space-between;
  align-items:flex-start;gap:32px;}
.ck-eh .ck-eh-left{flex:1;min-width:0;}
.ck-eh .ck-eh-actions{display:flex;gap:8px;flex-shrink:0;
  align-items:flex-start;}
.ck-eh .ck-eh-actions a,.ck-eh .ck-eh-actions button{
  font:500 11px/1 var(--sc-sans,Inter),sans-serif;letter-spacing:.08em;
  text-transform:uppercase;color:var(--ink,#16263a);
  background:var(--paper-card,#fefcf3);
  border:1px solid var(--rule,#c9bf9c);border-radius:2px;
  padding:9px 14px;text-decoration:none;cursor:pointer;
  transition:background .12s,border-color .12s;}
.ck-eh .ck-eh-actions a:hover,.ck-eh .ck-eh-actions button:hover{
  background:var(--paper-hi,#fbf6e8);
  border-color:var(--rule-hi,#b6a87f);}
.ck-eh .ck-eh-eyebrow{font:500 11px/1 var(--sc-mono,monospace);
  letter-spacing:.18em;text-transform:uppercase;
  color:var(--green-deep,#154e36);display:flex;align-items:center;
  gap:12px;margin:0 0 18px;}
.ck-eh .ck-eh-eyebrow .ck-eh-dash{width:24px;height:1px;
  background:var(--green-deep,#154e36);}
.ck-eh h1{font:400 44px/1.05 var(--sc-serif,Georgia),serif;
  letter-spacing:-.015em;color:var(--ink,#16263a);margin:0 0 14px;}
.ck-eh .ck-eh-meta{font:500 11px/1 var(--sc-mono,monospace);
  letter-spacing:.14em;text-transform:uppercase;
  color:var(--muted,#7a8595);margin:0 0 18px;}
.ck-eh .ck-eh-lede{font:400 italic 16.5px/1.55
  var(--sc-serif,Georgia),serif;
  color:var(--ink-2,#2b3e54);max-width:68ch;margin:0 0 18px;}
.ck-eh .ck-eh-lede em{color:var(--green-deep,#154e36);
  font-style:italic;}
.ck-eh .ck-eh-source{font:500 10px/1.4 var(--sc-mono,monospace);
  letter-spacing:.14em;text-transform:uppercase;
  color:var(--muted-2,#9a9e8a);margin:0 0 16px;max-width:62ch;}
.ck-eh .ck-eh-legend{display:flex;gap:24px;list-style:none;padding:0;
  margin:0;font:400 12.5px/1 var(--sc-sans,Inter),sans-serif;
  color:var(--ink-2,#2b3e54);flex-wrap:wrap;}
.ck-eh .ck-eh-legend li{display:flex;align-items:center;}
.ck-eh .ck-eh-legend .ck-eh-dot{width:8px;height:8px;border-radius:50%;
  display:inline-block;margin-right:10px;}
.ck-eh .ck-eh-legend .ck-eh-dot.live{background:var(--green-deep,#154e36);}
.ck-eh .ck-eh-legend .ck-eh-dot.computed{background:var(--ink-deep,#0e1a29);}
.ck-eh .ck-eh-legend .ck-eh-dot.needs{background:var(--coral,#b04a3a);}
.ck-eh .ck-eh-legend .ck-eh-dot.illustrative{background:var(--gold,#a08227);}
@media (max-width:960px){
  .ck-eh h1{font-size:36px;}
  .ck-eh .ck-eh-row{flex-direction:column;}
}
@media (max-width:720px){
  .ck-eh h1{font-size:32px;}
}
</style>
"""


def ck_editorial_head(
    eyebrow: str,
    title: str,
    *,
    meta: str = "",
    lede_italic_phrase: str = "",
    lede_body: str = "",
    source_note: str = "",
    actions_html: str = "",
    show_legend: bool = True,
) -> str:
    """Universal strict Tier-1 5-block head — one helper, all pages.

    Consolidates the ten page-local head builders shipped across
    batches 1-18 into a single reusable primitive. Pages adopting
    this helper get the exact same masthead shape that already
    lives on /portfolio, /pipeline, /home, /library, /diligence,
    /bear-cases, /covenant-stress, /payer-stress, the sector
    family, the hospital-profile family, and the analytics family.

    Anatomy (Tier-1 5-block):
      · eyebrow + 24×1px --green-deep dash glyph
      · serif <h1> (the page title)
      · mono uppercase meta-line (real counts; never hard-coded)
      · italic-first-phrase serif lede in --green-deep, with the
        body in --ink-2 (Tier-2 §2.3)
      · optional mono source-note line
      · 4-bucket status-dot legend (live / computed / needs /
        illustrative) — Tier-2 §2.4

    Args:
      eyebrow: short uppercase tag for the section the page lives
        in (e.g. "DEAL MONTE CARLO", "PORTFOLIO MONITOR").
      title: H1 text — the page name, serif 44px. Caller passes
        ALREADY-ESCAPED markup if it embeds tags (e.g. spans).
      meta: mono uppercase strip; caller supplies the real count
        string (e.g. "12 SCENARIOS · 5 ACTIVE · LIVE"). Empty
        string omits the strip entirely.
      lede_italic_phrase: the deck-style first phrase that lands
        in --green-deep italic. Caller supplies escaped text;
        helper wraps it in <em>.
      lede_body: the roman body that follows the italic phrase.
        Caller supplies pre-escaped HTML.
      source_note: optional "Source: ..." style line that lands
        under the lede in mono uppercase. Caller supplies escaped
        text.
      actions_html: optional right-side actions block (Copy share
        link button, Open IC memo link, etc.). Caller supplies
        pre-rendered HTML.
      show_legend: include the 4-bucket status-dot legend. Default
        True; pages that don't need it (e.g. login) can suppress.

    Returns the full CSS + header block. The CSS is namespaced
    to .ck-eh so it doesn't collide with any page-local head
    class. The h1 anchor lives at the page's natural masthead
    position; auto-h1 inject from chartis_shell is skipped because
    a real <h1> is present.
    """
    meta_html = (
        f'<div class="ck-eh-meta">{_esc(meta)}</div>' if meta else ""
    )
    lede_html = ""
    if lede_italic_phrase or lede_body:
        italic = (
            f'<em>{_esc(lede_italic_phrase)}</em> '
            if lede_italic_phrase else ""
        )
        lede_html = f'<p class="ck-eh-lede">{italic}{lede_body}</p>'
    source_html = (
        f'<p class="ck-eh-source">Source: {_esc(source_note)}</p>'
        if source_note else ""
    )
    actions_block = (
        f'<div class="ck-eh-actions">{actions_html}</div>'
        if actions_html else ""
    )
    legend_html = (
        '<ul class="ck-eh-legend">'
        '<li><span class="ck-eh-dot live"></span>Live data</li>'
        '<li><span class="ck-eh-dot computed"></span>Computed</li>'
        '<li><span class="ck-eh-dot needs"></span>Needs data</li>'
        '<li><span class="ck-eh-dot illustrative"></span>Illustrative</li>'
        '</ul>'
        if show_legend else ""
    )
    return (
        _CK_EDITORIAL_HEAD_CSS
        + '<header class="ck-eh">'
        '<div class="ck-eh-row">'
        '<div class="ck-eh-left">'
        f'<div class="ck-eh-eyebrow">'
        f'<span class="ck-eh-dash"></span>{_esc(eyebrow)}</div>'
        f'<h1>{title}</h1>'
        f'{meta_html}'
        f'{lede_html}'
        f'{source_html}'
        '</div>'
        f'{actions_block}'
        '</div>'
        f'{legend_html}'
        '</header>'
    )


def ck_back_to_top_button(label: str = "↑ Back to top") -> str:
    """Floating "back to top" button — appears after the partner
    scrolls more than 600px down. Click smooth-scrolls to top.
    Useful on long screener tables / detail pages where the partner
    deep-scrolls.

    Renders the CSS + JS + button. Idempotent JS install guarded
    by ``window.__rcmBackToTopInstalled``.
    """
    return (
        _CK_BACK_TO_TOP_CSS
        + _CK_BACK_TO_TOP_JS
        + (
            f'<button type="button" class="ck-back-to-top" '
            f'data-rcm-back-to-top aria-label="Back to top of page">'
            f'{_esc(label)}</button>'
        )
    )


def ck_recently_viewed_rail(
    *,
    eyebrow: str = "Recently viewed",
    placeholder_label: str = "Loading recent deals…",
) -> str:
    """Recently-viewed deals rail — hydrated from localStorage.

    Renders an inline <section> that JS fills with the most recent
    5 deal-profile visits (stored under ``rcm_recent_deals`` by
    deal_profile_page on every open). Empty state when the partner
    hasn't visited any deal yet honestly says so.

    The helper is server-friendly — emits a placeholder; JS hydrates
    after page-load. No SSR call needed; localStorage is per-browser.
    """
    return (
        _CK_RECENT_CSS
        + _CK_RECENT_JS
        + '<section class="ck-recent" data-rcm-recent-wrap>'
        '<div class="head">'
        '<div class="eyebrow"><span class="dash"></span>'
        f'{_esc(eyebrow)}</div>'
        '<span class="count">UP TO 5</span>'
        '</div>'
        f'<div data-rcm-recent-deals>'
        f'<p class="empty"><em>{_esc(placeholder_label)}</em></p>'
        '</div>'
        '</section>'
    )


def ck_page_title(
    title: str,
    *,
    eyebrow: Optional[str] = None,
    meta: Optional[str] = None,
) -> str:
    """Editorial page title — small mono eyebrow, navy serif title,
    optional mono meta line. Sits at the top of a content page above
    KPIs / search / table to give the page a clear identity. Bigger
    than ck_section_intro's headline (which acts more like an article
    deck) — this is the equivalent of an H1.

    ``meta`` renders as a faint mono row beneath the title, useful for
    "655 deals · 99 sectors · sorted by entry_year desc" style page
    state without ballooning the title block.
    """
    eyebrow_html = (
        f'<div class="ck-eyebrow">{_esc(eyebrow)}</div>' if eyebrow else ""
    )
    meta_html = (
        f'<div class="ck-page-title-meta">{_esc(meta)}</div>' if meta else ""
    )
    return (
        '<header class="ck-page-title">'
        f'{eyebrow_html}'
        f'<h1>{_esc(title)}</h1>'
        f'{meta_html}'
        '</header>'
    )


def ck_page_explainer(
    headline: str,
    body: str,
    *,
    source: Optional[str] = None,
) -> str:
    """Editorial explainer paragraph rendered below ck_page_title.

    Mirrors the Portfolio Heatmap style: italic teal headline
    sentence followed by a body paragraph. Use this on data /
    analysis pages where the partner needs to know (a) what data
    drives the page, (b) what the page is telling them, (c) what
    they'd use it for, and (d) whether the data is live or
    illustrative.

    ``headline`` becomes the italic teal lead sentence.
    ``body`` is the explainer paragraph proper.
    ``source`` (optional) appends a small mono "Source: …" line —
    useful for naming the upstream dataset (HCRIS, CMS-MA, APCD,
    synthetic fixture, etc.).

    All three parameters are HTML-escaped — pass plain text only.
    Styling comes from ``.ck-page-explainer`` in the shared
    chartis stylesheet (no extra_css needed).
    """
    source_html = (
        f'<span class="ck-page-explainer-source">'
        f'Source: {_esc(source)}</span>'
        if source else ""
    )
    return (
        '<p class="ck-page-explainer">'
        f'<em>{_esc(headline)}</em> '
        f'{_esc(body)}'
        f'{source_html}'
        '</p>'
    )


def ck_image_card(
    *,
    image_html: str,
    eyebrow: str,
    title: str,
    body: str,
    cta_text: str = "Read more",
    cta_href: str = "#",
) -> str:
    """Image-top editorial card — eyebrow / title / body / arrow CTA.

    ``image_html`` is the inner ``<img>`` or SVG; the card wrapper
    supplies the 4:3 aspect frame and the bottom teal border that
    pairs cards across a row visually.
    """
    return (
        '<article class="ck-image-card">'
        f'<div class="ck-image-card-img">{image_html}</div>'
        '<div class="ck-image-card-body">'
        f'{ck_eyebrow(eyebrow)}'
        f'<h3 class="ck-image-card-title">{_esc(title)}</h3>'
        f'<p>{_esc(body)}</p>'
        f'{ck_arrow_link(cta_text, cta_href)}'
        '</div>'
        '</article>'
    )


def ck_severity_panel(
    *,
    tone: str,
    label: str,
    count: int,
    rows_html: str,
) -> str:
    """Severity-toned panel for /alerts and /escalations.

    Replaces the legacy ``<div class="card"><h2>RED (1)</h2>`` pattern
    with a Chartis-style left-rule-toned panel. ``rows_html`` is the
    pre-rendered ``<li>`` content.
    """
    valid = {"red", "amber", "info", "positive", "neutral"}
    t = tone if tone in valid else "neutral"
    return (
        f'<section class="ck-severity-panel tone-{t}">'
        '<header class="ck-severity-panel-head">'
        f'<h3>{_esc(label)}</h3>'
        f'<span class="count">{int(count):d} item{"" if count == 1 else "s"}</span>'
        '</header>'
        f'<ul class="ck-severity-list">{rows_html}</ul>'
        '</section>'
    )


def ck_search_hero(
    *,
    label: str = "Search",
    placeholder: str = "Keyword",
    action: str,
    name: str = "q",
    initial: Optional[str] = None,
    method: str = "GET",
    extra_hidden: Optional[Mapping[str, str]] = None,
) -> str:
    """Navy search hero with italic-serif label + circular submit
    + teal chevron-cut bottom-right corner. Mirrors the Chartis
    Insights page hero exactly. Drop above any content-listing
    page (``/library``, ``/research``, ``/notes``, ``/search``)
    so the partner's first read is the same as on chartis.com.

    ``extra_hidden`` round-trips other URL state (current filter
    selections etc.) through the search form so submitting the
    keyword input doesn't drop the active filter sidebar state.

    Spec: ``docs/CHARTIS_MATCH_NOTES.md`` pattern 01.
    """
    initial_attr = (
        f' value="{_esc(initial)}"' if initial else ""
    )
    hidden_html = ""
    if extra_hidden:
        hidden_html = "".join(
            f'<input type="hidden" name="{_esc(k)}" value="{_esc(v)}">'
            for k, v in extra_hidden.items() if v
        )
    return (
        '<section class="ck-search-hero">'
        '<div class="ck-search-hero-inner">'
        f'<span class="ck-search-hero-label">{_esc(label)}</span>'
        f'<form class="ck-search-hero-form" method="{_esc(method)}" '
        f'action="{_esc(action)}" role="search">'
        f'{hidden_html}'
        f'<input class="ck-search-hero-input" type="search" '
        f'name="{_esc(name)}" placeholder="{_esc(placeholder)}" '
        f'aria-label="{_esc(label)}"{initial_attr}>'
        '<button class="ck-search-hero-submit" type="submit" '
        'aria-label="Run search">'
        '<svg viewBox="0 0 24 24" width="18" height="18" '
        'aria-hidden="true">'
        '<circle cx="10" cy="10" r="6" fill="none" '
        'stroke="currentColor" stroke-width="1.5"/>'
        '<line x1="14.5" y1="14.5" x2="20" y2="20" '
        'stroke="currentColor" stroke-width="1.5"/>'
        '</svg>'
        '</button>'
        '</form>'
        '</div>'
        '<span class="ck-search-hero-chevron" aria-hidden="true"></span>'
        '</section>'
    )


def ck_filter_sidebar(
    *,
    groups: Sequence[Mapping[str, Any]],
    title: str = "Filter",
    form_action: Optional[str] = None,
    form_method: str = "GET",
    extra_hidden: Optional[Mapping[str, str]] = None,
    submit_label: Optional[str] = None,
    auto_submit: bool = True,
    more_threshold: int = 8,
) -> str:
    """Editorial filter sidebar — eyebrow rail with grouped checkbox
    or radio rows and a ``<details>`` 'More' expander when a group
    exceeds ``more_threshold`` options. Mirrors the chartis.com
    Insights left rail.

    Each group is a mapping with:
      - ``title`` (str) — group header label, e.g. ``"By sector"``
      - ``name`` (str) — input ``name`` attribute
      - ``input_type`` (str) — ``"radio"`` or ``"checkbox"``
        (defaults to ``"checkbox"``)
      - ``options`` (Sequence) — each ``{"label": str, "value": str,
        "checked": bool}``

    When ``form_action`` is provided the sidebar wraps in a ``<form>``
    so the partner can change facets without leaving the page; the
    inputs auto-submit on change unless ``submit_label`` is provided
    or ``auto_submit=False``. Pass ``extra_hidden`` to round-trip
    URL state that lives on a sibling form (e.g. the search hero's
    ``q`` parameter) so toggling a filter doesn't drop the keyword.

    Spec: ``docs/CHARTIS_MATCH_NOTES.md`` pattern 02.
    """
    title_html = f'<h2 class="ck-filter-rail-title">{_esc(title)}</h2>'

    auto_attr = (
        ' onchange="this.form.submit()"'
        if (form_action and auto_submit and not submit_label)
        else ""
    )

    def _render_li(opt: Mapping[str, Any], gtype: str, gname: str) -> str:
        ovalue = _esc(opt.get("value", ""))
        olabel = _esc(opt.get("label", ""))
        checked = " checked" if opt.get("checked") else ""
        return (
            '<li><label>'
            f'<input type="{gtype}" name="{gname}" '
            f'value="{ovalue}"{checked}{auto_attr}>'
            f'<span>{olabel}</span>'
            '</label></li>'
        )

    group_parts = []
    for grp in groups:
        gtitle = _esc(grp.get("title", ""))
        gname = _esc(grp.get("name", ""))
        gtype = grp.get("input_type", "checkbox")
        if gtype not in ("checkbox", "radio"):
            gtype = "checkbox"
        options = list(grp.get("options", []))
        head = options[:more_threshold]
        tail = options[more_threshold:]
        head_lis = "".join(_render_li(o, gtype, gname) for o in head)
        overflow_html = ""
        if tail:
            tail_lis = "".join(_render_li(o, gtype, gname) for o in tail)
            overflow_html = (
                '<details class="ck-filter-overflow">'
                '<summary>More</summary>'
                f'<ul class="ck-filter-list">{tail_lis}</ul>'
                '</details>'
            )
        group_parts.append(
            '<section class="ck-filter-group">'
            f'<header class="ck-filter-group-head">{gtitle}</header>'
            f'<ul class="ck-filter-list">{head_lis}</ul>'
            f'{overflow_html}'
            '</section>'
        )

    submit_html = (
        f'<button class="ck-filter-submit" type="submit">{_esc(submit_label)}</button>'
        if submit_label and form_action else ""
    )

    hidden_html = ""
    if extra_hidden and form_action:
        hidden_html = "".join(
            f'<input type="hidden" name="{_esc(k)}" value="{_esc(v)}">'
            for k, v in extra_hidden.items() if v
        )

    inner = f'{title_html}{"".join(group_parts)}{submit_html}'

    if form_action:
        return (
            '<aside class="ck-filter-rail">'
            f'<form method="{_esc(form_method)}" action="{_esc(form_action)}">'
            f'{hidden_html}{inner}'
            '</form>'
            '</aside>'
        )
    return f'<aside class="ck-filter-rail">{inner}</aside>'


def ck_results_header(
    *,
    count: Any,
    label: str = "Results",
    chips: Optional[Sequence[Mapping[str, str]]] = None,
    clear_all_href: Optional[str] = None,
) -> str:
    """Editorial N-RESULTS header with active-filter chips + clear-all.

    Mirrors the chartis.com/insights ``46 RESULTS`` row above the
    results list — serif count + caps RESULTS label + a row of chips
    showing active facets, each chip an anchor that drops just that
    one facet on click. ``clear_all_href`` should point at the same
    page with all filter params stripped so partner can reset to the
    full corpus in one click. Drop in below ck_filter_sidebar +
    ck_search_hero on /library, /research, /notes for the full
    Insights pattern triplet.

    Each chip dict supports:
      - ``label`` (str) — visible chip text, e.g. ``"Behavioral Health"``
      - ``remove_href`` (str) — anchor href that drops the facet

    Spec: ``docs/CHARTIS_MATCH_NOTES.md`` pattern 03.
    """
    chips_html = ""
    if chips:
        chip_parts = []
        for ch in chips:
            chip_parts.append(
                f'<a class="ck-chip" href="{_esc(ch.get("remove_href", "#"))}">'
                f'{_esc(ch.get("label", ""))} '
                '<span class="ck-chip-x" aria-hidden="true">×</span>'
                '<span class="sr-only"> remove filter</span>'
                '</a>'
            )
        clear_html = (
            f'<a class="ck-arrow" href="{_esc(clear_all_href)}">Clear all</a>'
            if clear_all_href else ""
        )
        chips_html = (
            '<div class="ck-results-chips">'
            f'{"".join(chip_parts)}{clear_html}'
            '</div>'
        )
    return (
        '<header class="ck-results-header">'
        '<div class="ck-results-count">'
        f'<span class="ck-results-num sc-num">{_esc(count)}</span>'
        f'<span class="ck-results-label">{_esc(label)}</span>'
        '</div>'
        f'{chips_html}'
        '</header>'
    )


def render_insights_page(
    *,
    action: str,
    state: Mapping[str, str],
    facets: Sequence[Mapping[str, Any]],
    count: Any,
    body_html: str,
    title: str,
    keyword_name: str = "q",
    keyword_label: str = "Search",
    keyword_placeholder: str = "Keyword",
    intro: Optional[Mapping[str, Any]] = None,
    section_title: Optional[str] = None,
    section_eyebrow: Optional[str] = None,
    count_label: str = "Results",
    active_nav: Optional[str] = None,
    subtitle: Optional[str] = None,
    breadcrumbs: Optional[Sequence[Any]] = None,
    chip_label_overrides: Optional[Mapping[str, Any]] = None,
    extra_chips: Optional[Sequence[Mapping[str, str]]] = None,
    omit_auto_chips: Optional[Sequence[str]] = None,
    prelude_html: str = "",
    prelude_position: str = "after",
    next_section_html: str = "",
) -> str:
    """Compose the chartis Insights triplet around a body of items.

    Replaces the ~200 LOC of triplet wiring that cycles 6, 8, 9
    each shipped (search hero + filter sidebar + results header +
    chip URL building + extra_hidden round-trip + Clear all)
    with one call. The caller pre-renders the items as
    ``body_html`` (table / cards / list) and passes:

      - ``action``    — page URL, e.g. ``"/library"``
      - ``state``     — current URL params as a ``{name: value}``
                        dict; empty values are dropped
      - ``facets``    — list of facet specs, each a mapping with
                        ``name`` / ``label`` / ``input_type`` /
                        ``options`` per ``ck_filter_sidebar``
      - ``count``     — the row count to surface in the results
                        header
      - ``intro``     — optional ``{eyebrow, headline, ...}`` kwargs
                        passed to ``ck_section_intro``
      - ``next_section_html`` — optional pre-rendered ``ck_next_section``
                        HTML appended after the rail layout, before
                        the shell. Lets insights-helper callers (e.g.
                        /research, /notes) join the Up-next cue ladder
                        — without it, the cue would land outside the
                        body since this helper wraps ``chartis_shell``.

    For each active facet (state value present), a chip is added
    to the results header whose ``remove_href`` reconstructs the
    URL with that facet stripped. The keyword (default ``q``)
    becomes a chip too when set, with a wrapping ``"value"``
    label. ``chip_label_overrides`` lets the caller swap the
    default chip label for a specific facet — e.g. /notes uses
    ``deal: hca-001`` for the deal-id chip rather than the bare
    value.

    Spec: ``docs/CHARTIS_MATCH_NOTES.md`` patterns 01-03 composed.
    """
    facet_names = {f["name"] for f in facets}
    overrides = chip_label_overrides or {}
    skip_auto = set(omit_auto_chips or ())

    # Build extra_hidden for the search hero — every state field
    # except the keyword itself round-trips so submitting q
    # preserves active filters.
    state_except_kw = {
        k: v for k, v in state.items()
        if k != keyword_name and v
    }
    search_hero = ck_search_hero(
        action=action,
        name=keyword_name,
        initial=state.get(keyword_name, ""),
        label=keyword_label,
        placeholder=keyword_placeholder,
        extra_hidden=state_except_kw,
    )

    # Filter sidebar — caller provides the facet groups directly;
    # extra_hidden round-trips q (and any non-facet state).
    state_except_facets = {
        k: v for k, v in state.items()
        if k not in facet_names and v
    }
    filter_rail = ck_filter_sidebar(
        title="Filter",
        form_action=action,
        groups=list(facets),
        extra_hidden=state_except_facets,
    )

    # Build chips: one per active facet + one for active keyword.
    # Each chip's remove_href reconstructs ``action?...`` with that
    # one field stripped, so partner can drop facets one at a time.
    chips: List[Mapping[str, str]] = []
    nonempty = {k: v for k, v in state.items() if v}

    def _url_omit(name: str) -> str:
        kept = [(k, v) for k, v in nonempty.items() if k != name]
        if not kept:
            return action
        import urllib.parse as _up
        return action + "?" + _up.urlencode(kept)

    for name, value in nonempty.items():
        if name in skip_auto:
            # Caller supplies its own chip(s) for this name via
            # ``extra_chips`` (e.g. multi-value tag filters where
            # each tag drops independently — the auto-builder can't
            # know how to drop one tag from a list-valued URL state).
            continue
        if name == keyword_name:
            label = f'"{value}"'
        elif name in facet_names or name in overrides:
            # Either a facet or a name with an explicit chip-label
            # override (e.g. /notes' ``deal_id`` — not a sidebar
            # facet but partner sees it as an active scope chip).
            override = overrides.get(name)
            if callable(override):
                label = override(value)
            elif override:
                label = override
            else:
                label = value
        else:
            # Non-facet state (e.g. sort_by) doesn't surface as a
            # chip — partner controls those via column headers,
            # not the chip row.
            continue
        chips.append({
            "label": label,
            "remove_href": _url_omit(name),
        })

    # Caller-supplied chips for cases the auto-builder can't handle
    # (multi-value facets, computed labels, etc.). Appended after
    # auto-chips so the visual order is "main facets → extras → q".
    if extra_chips:
        chips.extend(extra_chips)

    results_head = ck_results_header(
        count=count,
        label=count_label,
        chips=chips or None,
        clear_all_href=action if chips else None,
    )

    # 2026-05-28 style-sweep · strict Tier-1 5-block head when intro
    # is supplied. Replaces the legacy ck_section_intro (h2 deck) +
    # shell-auto-injected ck_page_title (h1 with mono eyebrow) — two
    # stacked headers — with a single in-body 5-block head:
    #   eyebrow + dash → serif h1 (uses page ``title``) → mono meta
    #   line (the ``intro['eyebrow']`` value + the page subtitle if
    #   any) → italic-first-phrase serif lede (built from the
    #   ``headline`` + ``italic_word`` + ``body`` fields each caller
    #   already provides) → 4-bucket status-dot legend.
    # Marked class="ck-page-title" so the shell skips its own
    # auto-inject (avoids the double-h1 trap).
    intro_html = ""
    if intro:
        _eb = _esc(str(intro.get("eyebrow") or ""))
        _headline = str(intro.get("headline") or "")
        _italic = intro.get("italic_word")
        _body = str(intro.get("body") or "")
        # Italicize the headline word OR the first phrase up to the
        # period (spec §2.3 — italic FIRST PHRASE in --green-deep).
        _hl_html = _esc(_headline)
        if _italic:
            for _cand in (_italic, _italic.capitalize(), _italic.upper()):
                _eh = _esc(_cand)
                if _eh in _hl_html:
                    _hl_html = _hl_html.replace(
                        _eh, f'<em>{_eh}</em>', 1,
                    )
                    break
        elif "." in _headline:
            _first, _rest = _headline.split(".", 1)
            _hl_html = (
                f'<em>{_esc(_first.strip())}.</em>{_esc(_rest)}'
            )
        else:
            _hl_html = f'<em>{_hl_html}</em>'

        intro_html = (
            '<style>'
            '.ip-head{padding:0 0 28px;margin:0 0 24px;'
            'border-bottom:1px solid var(--rule-soft,#ddd1ac);}'
            '.ip-head .eyebrow{font:500 11px/1 var(--sc-mono,monospace);'
            'letter-spacing:.18em;text-transform:uppercase;'
            'color:var(--green-deep,#154e36);display:flex;'
            'align-items:center;gap:12px;margin:0 0 18px;}'
            '.ip-head .eyebrow .dash{width:24px;height:1px;'
            'background:var(--green-deep,#154e36);}'
            '.ip-head h1{font:400 44px/1.05 var(--sc-serif,Georgia),serif;'
            'letter-spacing:-.015em;color:var(--ink,#16263a);'
            'margin:0 0 14px;}'
            '.ip-head .deck{font:400 italic 18px/1.45 '
            'var(--sc-serif,Georgia),serif;color:var(--ink-2,#2b3e54);'
            'max-width:62ch;margin:0 0 12px;}'
            '.ip-head .deck em{color:var(--green-deep,#154e36);'
            'font-style:italic;}'
            '.ip-head .lede{font:400 15.5px/1.55 var(--sc-sans,Inter),sans-serif;'
            'color:var(--ink-2,#2b3e54);max-width:64ch;margin:0 0 18px;}'
            '.ip-head .legend{display:flex;gap:24px;list-style:none;'
            'padding:0;margin:0;font:400 12.5px/1 '
            'var(--sc-sans,Inter),sans-serif;'
            'color:var(--ink-2,#2b3e54);flex-wrap:wrap;}'
            '.ip-head .legend li{display:flex;align-items:center;}'
            '.ip-head .legend .dot{width:8px;height:8px;border-radius:50%;'
            'display:inline-block;margin-right:10px;}'
            '.ip-head .legend .dot.live{background:var(--green-deep,#154e36);}'
            '.ip-head .legend .dot.computed{background:var(--ink-deep,#0e1a29);}'
            '.ip-head .legend .dot.needs{background:var(--coral,#b04a3a);}'
            '.ip-head .legend .dot.illustrative{background:var(--gold,#a08227);}'
            '@media (max-width:960px){.ip-head h1{font-size:36px;}}'
            '</style>'
            # The wrapper class must include "ck-page-title" so the
            # shell's auto-inject skips this (it checks for the
            # substring in the body before adding its own h1).
            f'<header class="ip-head ck-page-title">'
            f'<div class="eyebrow"><span class="dash"></span>{_eb}</div>'
            f'<h1>{_esc(title)}</h1>'
            f'<p class="deck">{_hl_html}</p>'
            + (f'<p class="lede">{_esc(_body)}</p>' if _body else '')
            + '<ul class="legend">'
            '<li><span class="dot live"></span>Live data</li>'
            '<li><span class="dot computed"></span>Computed</li>'
            '<li><span class="dot needs"></span>Needs data</li>'
            '<li><span class="dot illustrative"></span>Illustrative</li>'
            '</ul>'
            '</header>'
        )

    section_html = ""
    if section_title:
        section_html = ck_section_header(
            section_title, eyebrow=section_eyebrow,
        )

    rail_layout = (
        '<div class="ck-rail-layout">'
        f'{filter_rail}'
        '<div class="ck-rail-content">'
        f'{section_html}{results_head}{body_html}'
        '</div>'
        '</div>'
    )

    # ``prelude_html`` is full-width content the caller wants between
    # the search hero and the rail layout (default) — e.g. a KPI
    # strip + explainer card. Set ``prelude_position="before"`` to
    # render it above the search bar instead, which makes the search
    # feel like part of one continuous header that flows into the
    # results table.
    if prelude_position == "before":
        full_body = (
            intro_html + prelude_html + search_hero + rail_layout
        )
    else:
        full_body = (
            intro_html + search_hero + prelude_html + rail_layout
        )

    full_body = full_body + next_section_html

    return chartis_shell(
        full_body,
        title=title,
        active_nav=active_nav,
        subtitle=subtitle,
        breadcrumbs=breadcrumbs,
    )


def ck_data_cell(
    value: str,
    *,
    align: str = "left",
    mono: bool = False,
    tone: Optional[str] = None,
    weight: Optional[int] = None,
    is_header: bool = False,
) -> str:
    """One styled ``<td>`` (or ``<th>``) for the data_public table
    archetype. Replaces the ~1200 hand-rolled inline-styled cells
    that the cycle-22 audit identified as the dominant inline-style
    source.

    Each cell is rendered with utility classes:
      - ``ck-cell``               — base padding + 11px font
      - ``ck-cell-mono``          — JetBrains Mono + tabular-nums
      - ``ck-cell-r`` / ``ck-cell-c`` — right / center alignment
      - ``tone-dim`` / ``tone-pos`` / ``tone-neg`` / ``tone-acc`` —
        dim / positive / negative / accent text color
      - ``ck-cell-w-700`` / ``ck-cell-w-600`` — weight modifiers

    The caller supplies ``value`` already pre-formatted (with $, %,
    x suffixes etc.) — the cell wrapper does not format. For
    auto-formatted cells use the existing ``ck_fmt_*`` helpers.

    Args:
      value: HTML-safe pre-formatted display string.
      align: ``left`` / ``right`` / ``center``.
      mono: Use mono font + tabular-nums.
      tone: Optional ``dim`` / ``pos`` / ``neg`` / ``acc``.
      weight: Optional 600 or 700 (CSS font-weight).
      is_header: Render as ``<th>`` instead of ``<td>``.
    """
    cls_parts = ["ck-cell"]
    if is_header:
        # Header cells get the cycle-27 ck-data-table-head class
        # which carries: caps + 10px + letter-spacing + border-bottom.
        # Lets ck_data_cell(..., is_header=True) replace the
        # ~720 hand-rolled <th style="..."> attributes that the
        # cycle-30 audit identified as the next inline-style hotspot.
        cls_parts.append("ck-data-table-head")
    if mono:
        cls_parts.append("ck-cell-mono")
    if align == "right":
        cls_parts.append("ck-cell-r")
    elif align == "center":
        cls_parts.append("ck-cell-c")
    if tone in ("dim", "pos", "neg", "acc"):
        cls_parts.append(f"tone-{tone}")
    if weight in (600, 700):
        cls_parts.append(f"ck-cell-w-{weight}")
    tag = "th" if is_header else "td"
    cls = " ".join(cls_parts)
    return f'<{tag} class="{cls}">{value}</{tag}>'


def ck_data_table(
    *,
    headers: Sequence[Mapping[str, str]],
    rows_html: str,
    scrollable: bool = True,
) -> str:
    """Wrap an editorial data table in chartis-grade chrome.

    Cycle 27 helper for the second-most-common inline-style cluster
    (after the cycle 22 cell migration): the table container,
    scroll wrapper, header row, and alternating-row background
    boilerplate that ~120 data_public pages still hand-roll. Each
    page emits ~5 inline-styled wrappers per table; this helper
    replaces all of them with class-based markup.

    Caller supplies the body via ``rows_html`` — typically a string
    of ``<tr>`` elements built from ``ck_data_cell`` calls in the
    page's render loop (so each row's tone-coloring stays at the
    caller's discretion). The helper handles the surrounding chrome:
    scroll wrapper, ``<table>`` + class, ``<thead>`` row, alternating
    body-row backgrounds via CSS.

    Args:
      headers: list of ``{"label": "Deal", "align": "left"}`` dicts.
        ``align`` ∈ ``left`` / ``right`` / ``center`` (default
        ``left``).
      rows_html: pre-rendered ``<tr>...</tr>`` strings concatenated.
        The helper wraps these in ``<tbody>``.
      scrollable: wrap in ``<div class="ck-data-table-scroll">``.
        Set False to skip the wrapper for inline / non-overflow
        contexts.
    """
    head_cells = []
    for h in headers:
        align = h.get("align", "left")
        align_cls = (
            f" ck-cell-r" if align == "right"
            else f" ck-cell-c" if align == "center"
            else ""
        )
        head_cells.append(
            f'<th class="ck-cell ck-data-table-head{align_cls}">'
            f'{_esc(h.get("label", ""))}</th>'
        )
    head_html = "<thead><tr>" + "".join(head_cells) + "</tr></thead>"
    body_html = f"<tbody>{rows_html}</tbody>"
    table = (
        '<table class="ck-data-table">'
        + head_html + body_html + "</table>"
    )
    if scrollable:
        return f'<div class="ck-data-table-scroll">{table}</div>'
    return table


def ck_provenance_tooltip(
    label: str,
    value: str,
    *,
    explainer: Optional[str] = None,
    graph: Optional[Any] = None,
    metric_key: Optional[str] = None,
    inject_css: bool = True,
) -> str:
    """Wrap a partner-facing value in an "explain this number" hover.

    Cycle 34 entry point — the kit-level helper that pages should
    call. Two paths:

    1. ``explainer`` provided: renders a simple hover card with the
       methodology string. Useful for any page (data_public,
       editorial ports) where each numeric has a fixed "what it
       means / where it came from" sentence. No per-deal graph
       needed.

    2. ``graph`` + ``metric_key`` provided: defers to
       ``rcm_mc/ui/_provenance_tooltip.py::provenance_tooltip``
       which pulls the explanation from a real provenance graph
       (Phase 4C of the v3 transformation).

    With neither, the value is returned escape-safely without a
    tooltip — same fall-through pattern as the existing helper.

    Args:
        label: User-visible name of the metric (HTML-escaped).
        value: Pre-formatted display string — TRUSTED server markup
            (not escaped), same exemption as ``ck_kpi_block``. May be a
            plain number or a color ``<span>``. Escape user-supplied
            strings upstream.
        explainer: Optional plain-text methodology / source line.
            When set, a hover card with this text appears on the
            value's info icon.
        graph: Optional provenance graph for graph-driven mode.
        metric_key: Optional metric key for graph-driven mode.
        inject_css: When True, inline the tooltip <style> on first
            call. Pass False on subsequent calls in one render.
    """
    if graph is not None and metric_key:
        # Defer to the graph-driven implementation. This is the
        # Phase 4C path used by /alerts, /my/<owner>, etc.
        from rcm_mc.ui._provenance_tooltip import provenance_tooltip
        return provenance_tooltip(
            label, value,
            graph=graph, metric_key=metric_key,
            inject_css=inject_css,
        )
    # ``value`` is a trusted server-rendered display string — a formatted
    # numeric optionally wrapped in a color <span> (denial rate, MOIC,
    # IRR, scores). Same exemption as ``ck_kpi_block``/``ck_data_cell``:
    # the kit does NOT escape it, so the color spans render as markup
    # rather than as literal `&lt;span…&gt;` text (the bug fixed here).
    # Callers passing a user-supplied string (deal/payer name) as the
    # value MUST escape it upstream, exactly like ck_kpi_block. ``label``
    # and ``explainer`` below remain escaped.
    safe_value = str(value)
    if not explainer:
        return SafeHtml(safe_value)
    safe_label = _html.escape(label)
    safe_explainer = _html.escape(explainer)
    css = ""
    if inject_css:
        css = (
            '<style>'
            '.ck-prov-tt{position:relative;display:inline-flex;'
            'align-items:baseline;gap:4px;}'
            '.ck-prov-tt-icon{display:inline-flex;align-items:center;'
            'justify-content:center;width:14px;height:14px;border-radius:50%;'
            'border:1px solid var(--sc-text-faint);'
            'color:var(--sc-text-faint);font-size:10px;font-weight:600;'
            'cursor:help;font-family:var(--sc-mono);}'
            '.ck-prov-tt-card{position:absolute;left:0;top:calc(100% + 6px);'
            'min-width:240px;max-width:340px;padding:12px 14px;'
            'background:#fff;border:1px solid var(--sc-rule);'
            'box-shadow:var(--sc-shadow-2);border-radius:2px;'
            'font-family:var(--sc-sans);font-size:12px;line-height:1.5;'
            'color:var(--sc-text);z-index:50;'
            'visibility:hidden;opacity:0;transition:opacity 0.1s;}'
            '.ck-prov-tt:hover .ck-prov-tt-card,'
            '.ck-prov-tt:focus-within .ck-prov-tt-card{visibility:visible;'
            'opacity:1;}'
            '.ck-prov-tt-label{font-family:var(--sc-mono);font-size:11px;'
            'font-weight:600;letter-spacing:0.06em;text-transform:uppercase;'
            'color:var(--sc-text-dim);margin-bottom:4px;display:block;}'
            '</style>'
        )
    return SafeHtml(
        f'{css}'
        '<span class="ck-prov-tt" tabindex="0">'
        f'<span class="ck-prov-tt-value">{safe_value}</span>'
        '<span class="ck-prov-tt-icon" aria-hidden="true">i</span>'
        '<span class="ck-prov-tt-card" role="tooltip">'
        f'<span class="ck-prov-tt-label">{safe_label}</span>'
        f'{safe_explainer}'
        '</span>'
        '</span>'
    )


def ck_affirm_empty(
    *,
    headline: str,
    body: str,
    cta_text: Optional[str] = None,
    cta_href: Optional[str] = None,
) -> str:
    """Editorial 'all clear' empty state — affirmative, not blank.

    Chartis-style positive band with optional teal arrow CTA. Used
    when /alerts has zero active items so the partner sees a real
    signal of health, not a void.
    """
    cta = (
        ck_arrow_link(cta_text, cta_href)
        if cta_text and cta_href else ""
    )
    return (
        '<section class="ck-affirm-empty">'
        f'<h3>{_esc(headline)}</h3>'
        f'<p>{_esc(body)}</p>'
        f'{cta}'
        '</section>'
    )


# ---------------------------------------------------------------------------
# Command palette (⌘K) — feed it the module catalog
# ---------------------------------------------------------------------------

# Default Cmd+K palette — the full platform tools index. Lets a
# partner jump to ANY surface (the long-tail of ~70 analytic
# tools beyond the editorial top-nav) without trawling URLs.
# Every entry must resolve to a real route; verified by the audit
# in tests/test_palette_routes.py.
_DEFAULT_PALETTE_MODULES = [
    # Home + ops
    {"id": "home",        "title": "Command Center",       "route": "/app"},
    {"id": "day-one",     "title": "Day One · Monday brief", "route": "/day-one"},
    {"id": "my",          "title": "My Dashboard",         "route": "/my/AT"},
    {"id": "alerts",      "title": "Alerts",               "route": "/alerts"},
    {"id": "escalations", "title": "Escalations",          "route": "/escalations"},
    {"id": "watchlist",   "title": "Watchlist",            "route": "/watchlist"},
    {"id": "questions-ledger", "title": "Diligence Questions · ledger",
        "route": "/diligence/questions"},
    # Pipeline / sourcing
    {"id": "pipeline",    "title": "Pipeline",             "route": "/pipeline"},
    {"id": "target-screener","title": "Target Screener",    "route": "/target-screener"},
    {"id": "source",      "title": "Deal Sourcing",        "route": "/source"},
    {"id": "screen",      "title": "Hospital Screener",    "route": "/screen"},
    {"id": "predictive",  "title": "Predictive Screener",  "route": "/predictive-screener"},
    {"id": "pe-intel",    "title": "PE Intelligence",      "route": "/pe-intelligence"},
    {"id": "deal-screen", "title": "Deal Screening",       "route": "/deal-screening"},
    {"id": "find-comps",  "title": "Find Comps",           "route": "/find-comps"},
    {"id": "conferences", "title": "Conferences",          "route": "/conferences"},
    # Diligence playbook
    {"id": "deal-profile",  "title": "Deal Profile",       "route": "/diligence/deal"},
    {"id": "cliff-calendar","title": "Reimbursement Cliff Calendar · 2026-2029 Medicare/340B rate events by subsector", "route": "/diligence/cliff-calendar"},
    {"id": "pe-library",    "title": "PE Intelligence Library · the full ~222-tool analytic toolkit, searchable", "route": "/diligence/pe-library"},
    {"id": "pe-tool",       "title": "Run PE Tool on a Deal · run an analytic tool against a real deal's packet", "route": "/diligence/pe-tool"},
    {"id": "pe-reference",  "title": "PE Reference Libraries · historical failures + partner traps (curated knowledge)", "route": "/diligence/pe-reference"},
    {"id": "thesis-pipe",   "title": "Thesis Pipeline",    "route": "/diligence/thesis-pipeline"},
    {"id": "checklist",     "title": "Diligence Checklist","route": "/diligence/checklist"},
    {"id": "data-activation","title": "Data Activation Center · activate analyses with your data", "route": "/data-activation"},
    {"id": "geo-intel",     "title": "Geographic Intelligence · real-data state analysis hub", "route": "/geo-intel"},
    {"id": "state-compare", "title": "State Comparison · compare states across real public data", "route": "/state-compare"},
    {"id": "state-rankings","title": "State Rankings · rank all states on one real metric", "route": "/state-rankings"},
    {"id": "state-profile", "title": "State Profile · one state's metrics + national ranks", "route": "/state-profile"},
    {"id": "state-peers",   "title": "Similar States · states most like a chosen state (real data)", "route": "/state-peers"},
    {"id": "county-explorer","title": "County Explorer · drill into a state's counties (real ACS data)", "route": "/county-explorer"},
    {"id": "geo-metrics",   "title": "Geo Metrics & Sources · what every geo metric measures + coverage", "route": "/geo-metrics"},
    {"id": "metro-markets", "title": "Metro Markets · real CBSA/metro demographics (Census ACS)", "route": "/metro-markets"},
    {"id": "geo-map",       "title": "Geo Map · US choropleth of any real state metric", "route": "/geo-map"},
    {"id": "ingest",        "title": "Ingestion",          "route": "/diligence/ingest"},
    {"id": "benchmarks",    "title": "Benchmarks",         "route": "/diligence/benchmarks"},
    {"id": "cms-xray",      "title": "CMS X-Ray · Provider scanner", "route": "/diligence/xray"},
    {"id": "hcris-xray",    "title": "HCRIS X-Ray",        "route": "/diligence/hcris-xray"},
    {"id": "root-cause",    "title": "Root Cause",         "route": "/diligence/root-cause"},
    {"id": "value-create",  "title": "Value Creation",     "route": "/diligence/value"},
    {"id": "risk-bench",    "title": "Risk Workbench",     "route": "/diligence/risk-workbench?demo=steward"},
    {"id": "counterfact",   "title": "Counterfactual",     "route": "/diligence/counterfactual"},
    {"id": "compare",       "title": "Compare Deals",      "route": "/diligence/compare"},
    {"id": "bankruptcy",    "title": "Bankruptcy Scan",    "route": "/screening/bankruptcy-survivor"},
    {"id": "qoe-memo",      "title": "QoE Memo",           "route": "/diligence/qoe-memo"},
    {"id": "denial-pred",   "title": "Denial Prediction",  "route": "/diligence/denial-prediction"},
    {"id": "deal-autopsy",  "title": "Deal Autopsy",       "route": "/diligence/deal-autopsy"},
    {"id": "phys-attr",     "title": "Physician Attrition","route": "/diligence/physician-attrition"},
    {"id": "phys-eu",       "title": "Provider Economics", "route": "/diligence/physician-eu"},
    {"id": "management",    "title": "Management",         "route": "/diligence/management"},
    {"id": "deal-mc",       "title": "Deal Monte Carlo",   "route": "/diligence/deal-mc"},
    {"id": "exit-timing",   "title": "Exit Timing",        "route": "/diligence/exit-timing"},
    {"id": "covenant-stress","title":"Covenant Stress",    "route": "/diligence/covenant-stress"},
    {"id": "bridge-audit",  "title": "Bridge Audit",       "route": "/diligence/bridge-audit"},
    {"id": "payer-stress",  "title": "Payer Stress",       "route": "/diligence/payer-stress"},
    {"id": "ic-packet",     "title": "IC Packet",          "route": "/diligence/ic-packet"},
    {"id": "engagements",   "title": "Engagements",        "route": "/engagements"},
    {"id": "sector-intel",  "title": "Sector Intelligence","route": "/sector-intelligence"},
    {"id": "home-health",   "title": "Home Health",        "route": "/home-health"},
    {"id": "hospice",       "title": "Hospice",            "route": "/hospice"},
    {"id": "nursing-homes", "title": "Nursing Homes (SNF)", "route": "/nursing-homes"},
    {"id": "dialysis",      "title": "Dialysis Facilities", "route": "/dialysis"},
    {"id": "inpatient-rehab", "title": "Inpatient Rehab (IRF)", "route": "/inpatient-rehab"},
    {"id": "long-term-care-hospital", "title": "Long-Term Care Hospitals (LTCH)", "route": "/long-term-care-hospital"},
    # Library / reference
    {"id": "deal-library",  "title": "Deal Library (licensed)", "route": "/deal-library"},
    {"id": "library",       "title": "Deals Library",      "route": "/library"},
    {"id": "deals-library", "title": "Deals Library (alt)","route": "/deals-library"},
    {"id": "methodology",   "title": "Methodology",        "route": "/methodology"},
    {"id": "metric-glos",   "title": "Metric Glossary",    "route": "/metric-glossary"},
    {"id": "rcm-bench",     "title": "RCM Benchmarks",     "route": "/rcm-benchmarks"},
    {"id": "data",          "title": "Data Catalog",       "route": "/data"},
    {"id": "comparables",   "title": "Comparables",        "route": "/comparables"},
    {"id": "market-rates",  "title": "Market Rates",       "route": "/market-rates"},
    {"id": "market-state",  "title": "Market Data · State (CA)",
        "route": "/market-data/state/CA"},
    # Research
    {"id": "research",      "title": "Research Hub",       "route": "/research"},
    {"id": "industry",      "title": "Industry Intelligence", "route": "/industry"},
    {"id": "market-geo",    "title": "Market Intel · Geographic", "route": "/market-intel/geo"},
    {"id": "notes",         "title": "Notes",              "route": "/notes"},
    {"id": "sector-mom",    "title": "Sector Momentum",    "route": "/sector-momentum"},
    {"id": "irr-disp",      "title": "IRR Dispersion",     "route": "/irr-dispersion"},
    {"id": "hold-analysis", "title": "Hold Analysis",      "route": "/hold-analysis"},
    {"id": "comp-outcomes", "title": "Comparable Outcomes","route": "/comparable-outcomes"},
    {"id": "bear-cases",    "title": "Bear Cases",         "route": "/bear-cases"},
    {"id": "reg-cal",       "title": "Regulatory Calendar","route": "/regulatory-calendar"},
    {"id": "market-intel",  "title": "Market Intelligence","route": "/market-intel"},
    {"id": "corpus-back",   "title": "Corpus Backtest",    "route": "/corpus-backtest"},
    {"id": "backtest",      "title": "Backtest",           "route": "/backtest"},
    # Portfolio
    {"id": "portfolio",     "title": "Portfolio",          "route": "/portfolio"},
    {"id": "port-map",      "title": "Portfolio Map",      "route": "/portfolio/map"},
    {"id": "port-heat",     "title": "Portfolio Heatmap",  "route": "/portfolio/heatmap"},
    {"id": "port-risk",     "title": "Portfolio Risk Scan","route": "/portfolio/risk-scan"},
    {"id": "port-mon",      "title": "Portfolio Monitor",  "route": "/portfolio/monitor"},
    {"id": "port-an",       "title": "Deal Corpus Analytics","route": "/deal-corpus-analytics"},
    {"id": "sponsor-tr",    "title": "Sponsor Track Record","route": "/sponsor-track-record"},
    {"id": "payer-intel",   "title": "Payer Intelligence", "route": "/payer-intelligence"},
    {"id": "lp-update",     "title": "LP Update",          "route": "/lp-update"},
    # Admin / system
    {"id": "audit",         "title": "Audit Log",          "route": "/audit"},
    {"id": "users",         "title": "Users",              "route": "/users"},
    {"id": "import",        "title": "Import Deal",        "route": "/import"},
]


def ck_command_palette(modules: Iterable[Mapping[str, str]]) -> str:
    items = "".join(
        f'<li data-key="{_esc(m.get("id", ""))}" data-route="{_esc(m.get("route", ""))}">'
        f'<span class="cp-title">{_esc(m.get("title", ""))}</span>'
        f'<span class="cp-route">{_esc(m.get("route", ""))}</span>'
        "</li>"
        for m in modules
    )
    return (
        '<div class="ck-palette" id="ck-palette" hidden>'
        '<div class="ck-palette-box">'
        '<input class="ck-palette-input" type="text" placeholder="Jump to… (⌘K)" />'
        f'<ul class="ck-palette-list">{items}'
        # Editorial empty state when filter matches nothing —
        # surfaced by _PALETTE_JS toggling the [hidden] flag.
        '<li class="cp-noresults" data-rcm-palette-empty hidden>'
        '<span class="cp-noresults-text">'
        '<em>Nothing matched.</em> Try a shorter prefix, or '
        '<kbd>Esc</kbd> to close.'
        '</span></li>'
        '</ul>'
        "</div></div>"
    )


# ---------------------------------------------------------------------------
# Shell
# ---------------------------------------------------------------------------

# Two stylesheets:
#   chartis_tokens.css — CSS custom-property tokens (--sc-navy, --cad-bg, ...)
#   v3/chartis.css — actual class definitions (.cad-card, .cad-kpi, .cad-btn,
#                    .cad-table, etc.) that ~25 pages still emit. Without
#                    this second link, those pages fall back to unstyled
#                    browser defaults and look broken under the editorial
#                    chrome wrapper.
_CSS_LINK = (
    '<link rel="stylesheet" href="/static/chartis_tokens.css">'
    '<link rel="stylesheet" href="/static/v3/chartis.css">'
)

# Inline fallback — if static serving of chartis_tokens.css isn't wired up,
# the class names defined here keep pages readable. Prefer the linked file.
_CSS_INLINE_FALLBACK = """
<style>
  /* Panel + data chrome layered on top of chartis_tokens.css */
  /* 2026-05-28 style-sweep · removed `box-shadow:var(--sc-shadow-1)`
     from .ck-panel. The static v3/chartis.css already renders panels
     without a shadow (line 1510); this inline fallback was emitting
     a shadow when the static file wasn't served, drifting from the
     canonical chrome. Depth on content panels comes from paper-tone
     stacking + hairlines (Tier-4 don'ts: no shadows anywhere). */
  .ck-panel { background:#fff; border:1px solid var(--sc-rule); border-radius:2px; margin:0 0 var(--sc-s-5); }
  .ck-panel-head { display:flex; align-items:center; justify-content:space-between; background:var(--sc-navy); color:var(--sc-on-navy); padding:10px 16px; border-radius:2px 2px 0 0; }
  .ck-panel-title { font-family:var(--sc-sans); font-weight:600; font-size:13px; letter-spacing:0.04em; text-transform:uppercase; }
  .ck-panel-code { font-family:var(--sc-mono); font-size:10px; letter-spacing:0.1em; color:var(--sc-on-navy-dim); }
  .ck-panel-body { padding:var(--sc-s-6); }
  /* Default link affordance inside editorial chrome — every <a> nested
   * in a panel body or section-intro body picks up teal-ink + hover
   * underline so dozens of inline-styled anchors still feel clickable
   * without each page hand-rolling its own. cad-link/ck-link explicit
   * classes still win via specificity. */
  .ck-panel-body a:not([class]),
  .ck-section-body a:not([class]),
  .ck-section-intro a:not([class]) {
    color: var(--sc-teal-ink); text-decoration: none;
    border-bottom: 1px solid transparent;
    transition: border-color 120ms ease, color 120ms ease;
  }
  .ck-panel-body a:not([class]):hover,
  .ck-section-body a:not([class]):hover,
  .ck-section-intro a:not([class]):hover {
    border-bottom-color: var(--sc-teal-ink);
  }
  /* Empty-row cell — partner-visible empty states inside data
   * tables that don't fit the block-level ck_empty_state component.
   * Italic Source-Serif framing with a soft bone tint pulls the row
   * out of the prose stream without shouting. */
  .ck-empty-row {
    padding: 14px 16px;
    background: var(--sc-bone, #f2ede3);
    font-family: "Source Serif 4", serif;
    font-size: 13px;
    color: var(--sc-text-dim, #37495e);
    line-height: 1.55;
  }
  .ck-empty-row em {
    font-style: italic;
    color: var(--sc-teal-ink, #0e3e3a);
  }
  /* Inline editorial sparkline — small SVG trend with optional
   * caps label + mono numeric end-value. Used in deals tables,
   * KPI strips, and anywhere a single inline trend needs to read
   * as part of running prose. */
  .ck-spark {
    display: inline-flex; align-items: center; gap: 8px;
    vertical-align: middle;
  }
  .ck-spark-svg { display: block; }
  .ck-spark-lbl {
    font-family: "Inter Tight", sans-serif; font-size: 9px;
    font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--sc-text-faint, #6e7787);
  }
  .ck-spark-val {
    font-family: "JetBrains Mono", monospace; font-size: 11px;
    font-weight: 600; font-variant-numeric: tabular-nums;
    color: var(--sc-text, #1a2332);
  }
  @media print {
    .ck-spark-svg polyline { stroke: #000 !important; }
  }

  /* Progress checklist — "your platform journey" editorial roster.
   * Numbered serif rows with a circular state marker that fills with
   * a positive-tone check when JS confirms the underlying condition
   * (recent deals, tour progress, tools visited) from localStorage. */
  .ck-checklist-wrap {
    background: var(--sc-bone, #f2ede3);
    border: 1px solid var(--sc-rule, #d8d3c8); border-radius: 3px;
    padding: 20px 24px; margin-bottom: var(--sc-s-5);
  }
  .ck-checklist { list-style: none; margin: 0; padding: 0; }
  .ck-checklist-row {
    display: grid; grid-template-columns: 24px 32px 1fr;
    gap: 14px; align-items: baseline;
    padding: 12px 0; border-bottom: 1px solid var(--sc-rule, #d8d3c8);
    font-family: "Source Serif 4", serif;
  }
  .ck-checklist-row:last-child { border-bottom: 0; }
  .ck-checklist-marker {
    width: 16px; height: 16px; border-radius: 50%;
    border: 1.5px solid var(--sc-text-faint, #6e7787);
    background: transparent;
    transition: background 160ms ease, border-color 160ms ease;
    align-self: center;
  }
  .ck-checklist-row.is-done .ck-checklist-marker {
    background: var(--sc-positive, #0a8a5f);
    border-color: var(--sc-positive, #0a8a5f);
    position: relative;
  }
  .ck-checklist-row.is-done .ck-checklist-marker::after {
    content: "✓"; position: absolute; top: -1px; left: 2px;
    font-size: 12px; color: #fff; font-weight: 700; line-height: 1;
    font-family: "Inter Tight", sans-serif;
  }
  .ck-checklist-number {
    font-family: "JetBrains Mono", monospace;
    font-size: 10px; font-weight: 700; letter-spacing: 0.12em;
    color: var(--sc-text-faint, #6e7787);
    align-self: center;
  }
  .ck-checklist-row.is-done .ck-checklist-number {
    color: var(--sc-positive, #0a8a5f);
  }
  .ck-checklist-title {
    font-size: 15px; font-weight: 500; line-height: 1.3;
    color: var(--sc-navy, #0b2341); margin-bottom: 2px;
  }
  .ck-checklist-row.is-done .ck-checklist-title {
    color: var(--sc-text-dim, #37495e);
  }
  .ck-checklist-prose {
    font-size: 13px; line-height: 1.55;
    color: var(--sc-text-dim, #37495e); max-width: 60ch;
  }
  .ck-checklist-prose em {
    font-style: italic; color: var(--sc-teal-ink, #0e3e3a);
  }
  @media print { .ck-checklist-wrap { display: none; } }

  /* Sticky right-rail table of contents — editorial chapter index.
   * The host page wraps its panels in .ck-toc-layout > .ck-toc-content
   * and the aside sits next to them, sticking to the viewport while
   * the partner scrolls. IntersectionObserver flips the .is-active
   * link as sections scroll into the upper third of the viewport. */
  .ck-toc-layout {
    display: grid; grid-template-columns: 240px 1fr;
    gap: var(--sc-s-7); align-items: start;
  }
  .ck-toc-content { min-width: 0; }
  .ck-toc {
    /* top == 58px topbar + ~14px breathing room. Was 90px (pre-#1014 76px
       topbar), which left the TOC floating ~18px too low. */
    position: sticky; top: 72px;
    max-height: calc(100vh - 92px); overflow-y: auto;
    padding: 18px 4px 24px;
    font-family: "Inter Tight", sans-serif;
  }
  .ck-toc-eyebrow {
    font-size: 10px; font-weight: 700; letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--sc-text-faint, #6e7787);
    padding: 0 14px 10px;
    border-bottom: 1px solid var(--sc-rule, #d8d3c8);
    margin-bottom: 8px;
  }
  .ck-toc-list {
    list-style: none; margin: 0; padding: 0;
    counter-reset: ck-toc-counter;
  }
  .ck-toc-item { margin: 0; padding: 0;
                 counter-increment: ck-toc-counter; }
  .ck-toc-link {
    display: block; position: relative;
    padding: 8px 14px 8px 18px;
    font-family: "Source Serif 4", serif;
    font-size: 13px; font-weight: 400; line-height: 1.4;
    color: var(--sc-text-dim, #37495e);
    text-decoration: none;
    border-left: 2px solid transparent;
    transition: color 120ms ease, border-color 120ms ease,
                background 120ms ease;
  }
  .ck-toc-link:hover {
    color: var(--sc-text, #1a2332);
    background: var(--sc-bone, #f2ede3);
  }
  .ck-toc-link.is-active {
    color: var(--sc-teal-ink, #0e3e3a);
    border-left-color: var(--sc-teal-ink, #0e3e3a);
    font-weight: 500;
  }
  @media (max-width: 1100px) {
    .ck-toc-layout { display: block; }
    .ck-toc { display: none; }
  }
  @media print { .ck-toc { display: none; } }

  /* Inline help affordance — `term [?]` opens an editorial popover */
  .ck-help {
    position: relative; display: inline-flex; align-items: baseline;
    gap: 4px; white-space: nowrap;
  }
  .ck-help-trigger {
    display: inline-flex; align-items: center; justify-content: center;
    width: 16px; height: 16px;
    background: transparent;
    border: 1px solid var(--sc-rule, #d8d3c8); border-radius: 50%;
    color: var(--sc-text-faint, #6e7787);
    font-family: "Inter Tight", sans-serif;
    font-size: 10px; font-weight: 700; line-height: 1;
    cursor: pointer; padding: 0;
    transition: border-color 120ms ease, color 120ms ease,
                background 120ms ease;
  }
  .ck-help-trigger:hover,
  .ck-help-trigger:focus,
  .ck-help-trigger[aria-expanded="true"] {
    background: var(--sc-teal-ink, #0e3e3a); color: #fff;
    border-color: var(--sc-teal-ink, #0e3e3a); outline: none;
  }
  .ck-help-popover {
    position: absolute; bottom: calc(100% + 8px); left: 50%;
    transform: translateX(-50%);
    min-width: 260px; max-width: 360px;
    padding: 14px 16px;
    background: var(--sc-bone, #f2ede3);
    border: 1px solid var(--sc-rule, #d8d3c8);
    border-radius: 3px;
    box-shadow: 0 12px 28px rgba(11, 35, 65, 0.18);
    z-index: 50;
    font-family: "Source Serif 4", serif;
    white-space: normal; text-align: left;
    opacity: 0; visibility: hidden;
    transition: opacity 120ms ease, visibility 120ms ease;
    pointer-events: none;
  }
  .ck-help:focus-within .ck-help-popover,
  .ck-help:hover .ck-help-popover {
    opacity: 1; visibility: visible; pointer-events: auto;
  }
  .ck-help-popover::after {
    content: ""; position: absolute; top: 100%; left: 50%;
    transform: translateX(-50%);
    border: 6px solid transparent;
    border-top-color: var(--sc-bone, #f2ede3);
  }
  .ck-help-term {
    display: block;
    font-family: "Inter Tight", sans-serif;
    font-size: 10px; font-weight: 700;
    letter-spacing: 0.14em; text-transform: uppercase;
    color: var(--sc-teal-ink, #0e3e3a); margin-bottom: 6px;
  }
  .ck-help-def {
    display: block;
    font-size: 13px; line-height: 1.55;
    color: var(--sc-text-dim, #37495e);
  }
  .ck-help-cite {
    display: block; margin-top: 8px;
    font-family: "Source Serif 4", serif; font-style: italic;
    font-size: 11px; color: var(--sc-text-faint, #6e7787);
  }
  @media print { .ck-help-trigger { display: none; }
                 .ck-help-popover { display: none; } }
  /* Up next — editorial chapter footer */
  .ck-next-section {
    padding: 28px 24px;
    margin: 28px 0 0;
    border-top: 1px solid var(--sc-rule);
    text-align: center;
  }
  .ck-next-eyebrow {
    font-family: var(--sc-sans); font-size: 10px; font-weight: 700;
    letter-spacing: 0.16em; text-transform: uppercase;
    color: var(--sc-text-faint); margin-bottom: 10px;
  }
  .ck-next-link {
    display: inline-block;
    font-family: var(--sc-serif); font-weight: 400; font-size: 22px;
    line-height: 1.2; letter-spacing: -0.005em;
    color: var(--sc-teal-ink); text-decoration: none;
    border-bottom: 1px solid transparent;
    transition: border-color 120ms ease;
  }
  .ck-next-link em {
    font-style: italic; color: var(--sc-teal-ink); font-weight: 400;
  }
  .ck-next-link:hover {
    border-bottom-color: var(--sc-teal-ink);
  }
  .ck-next-arrow {
    display: inline-block; margin-left: 6px;
    transition: transform 160ms ease;
  }
  .ck-next-link:hover .ck-next-arrow {
    transform: translateX(4px);
  }
  .ck-table { width:100%; border-collapse:collapse; font-size:13px; }
  /* B5 — tbody td vertical padding bumped 8px → 10px and horizontal
   * 12px → 14px for editorial breathing room. thead th padding kept
   * in lockstep (header still aligns visually with body). Dense
   * variant unchanged — pages opting into ck-dense explicitly want
   * the tighter packing. */
  .ck-table thead th { background:var(--sc-bone); color:var(--sc-text-dim); font-family:var(--sc-sans); font-weight:600; font-size:11px; letter-spacing:0.1em; text-transform:uppercase; padding:10px 14px; border-bottom:1px solid var(--sc-rule); text-align:left; }
  /* 2026-05-28 usability lift · opt-in sticky thead. Pages that
   * render long result tables (predictive-screener, hospital-screener,
   * sector screeners, pipeline hospitals) opt-in by adding the
   * `ck-table-sticky-head` class to the <table>. The thead row then
   * stays pinned to the topbar (-1px overlap avoids a hairline gap
   * on scroll). Background fill ensures rows scrolling under the
   * thead don't bleed through. */
  /* Depth on the pinned thead comes from the existing hairline
   * border-bottom + opaque --sc-bone background. No box-shadow
   * (Tier-4 don'ts forbid shadows; the hairline carries the
   * visual separation). */
  .ck-table.ck-table-sticky-head thead th { position:sticky; top:0; z-index:5; background:var(--sc-bone); }
  .ck-table tbody td { padding:10px 14px; border-bottom:1px solid var(--sc-rule); }
  .ck-table.ck-dense tbody td { padding:5px 10px; font-size:12px; }
  .ck-table .sc-num { font-family:var(--sc-mono); font-variant-numeric:tabular-nums; }
  .ck-table .align-right { text-align:right; }
  .ck-table .align-center { text-align:center; }
  .ck-kpi { padding:var(--sc-s-4) 0; border-top:1px solid var(--sc-rule); position:relative; }
  /* B3 — forgotten migration. .ck-kpi-grid is referenced by
   * deal_dashboard.py, market_rates_page.py, etc., but the rule
   * lived only in _chartis_kit_legacy.py — modern shell had no
   * definition, so children stacked vertically (default
   * display:block on div). Mirrors .ck-pulse-grid below. Auto-fit
   * minmax means N stats per row at typical viewport, wraps to
   * additional rows for thick-stat strips (8-stat sponsor heatmap
   * fits one row on wide; wraps to two on narrower viewports).
   *
   * B10 — same root cause, second forgotten primitive. .ck-kpi-strip
   * is used by pipeline_page.py:118 and thesis_pipeline_page.py:252;
   * the only existing rule was print-only (.ck-kpi-strip
   * break-inside:avoid further down the file). Children were
   * stacking vertically just like .ck-kpi-grid pre-B3. Combined
   * selector here so both classes share the editorial grid display.
   */
  .ck-kpi-grid,
  .ck-kpi-strip { display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:0; border-top:1px solid var(--sc-rule); }
  .ck-kpi-grid .ck-kpi,
  .ck-kpi-strip .ck-kpi { padding:14px 18px; border-top:0; border-right:1px solid var(--sc-rule); }
  .ck-kpi-grid .ck-kpi:last-child,
  .ck-kpi-strip .ck-kpi:last-child { border-right:0; }
  .ck-kpi-label { font-family:var(--sc-sans); font-size:11px; letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-text-dim); margin-bottom:4px; }
  .ck-kpi-value { font-family:var(--sc-serif); font-size:22px; font-weight:500; color:var(--sc-navy); display:flex; align-items:baseline; gap:8px; }
  .ck-kpi-trend { font-family:var(--sc-mono); font-size:12px; }
  .ck-kpi-trend.tone-positive { color:var(--sc-positive); }
  .ck-kpi-trend.tone-negative { color:var(--sc-negative); }
  .ck-kpi-trend.tone-neutral  { color:var(--sc-text-faint); }
  .ck-kpi-sub { font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); margin-top:4px; }
  .ck-kpi-code { position:absolute; top:var(--sc-s-4); right:0; font-family:var(--sc-mono); font-size:10px; color:var(--sc-text-faint); letter-spacing:0.1em; }
  /* Data-universe label chips (ck_data_universe) — declare which data
   * universe a page shows so corpus is never mistaken for portfolio. */
  .ck-universe { display:inline-flex; align-items:center; gap:6px; padding:3px 9px;
    font-family:var(--sc-mono); font-size:10px; font-weight:600; letter-spacing:0.12em;
    text-transform:uppercase; border:1px solid currentColor; border-radius:2px;
    cursor:help; vertical-align:middle; }
  .ck-universe::before { content:""; width:6px; height:6px; border-radius:50%;
    background:currentColor; flex:none; }
  .ck-universe-deals  { color:var(--sc-navy,#15202b); }
  .ck-universe-port   { color:var(--sc-positive,#0a8a5f); }
  .ck-universe-cms    { color:var(--sc-teal-ink,#155752); }
  .ck-universe-corpus { color:var(--sc-warning,#b8732a); }
  .ck-universe-ref    { color:var(--sc-text-dim,#6a7480); }
  .ck-universe-mixed  { color:var(--sc-text-faint,#8b94a0); }
  .ck-universe-illus  { color:var(--sc-warning,#b8732a); }   /* illustrative — amber */
  .ck-universe-datareq{ color:var(--sc-critical,#b5321e); } /* data required — red */
  .ck-universe-exp    { color:var(--sc-teal-ink,#155752); } /* experimental */
  /* Diligence source-and-purpose header band */
  .ck-sp { border:1px solid var(--sc-rule); border-left:3px solid var(--sc-teal,#155752);
    background:var(--sc-paper,#faf6ec); padding:12px 16px; margin:0 0 var(--sc-s-5,20px); }
  .ck-sp-chips { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:8px; }
  .ck-sp-purpose { font-family:var(--sc-serif); font-size:14.5px; line-height:1.5;
    color:var(--sc-text,#2a3a4a); margin:0 0 6px; max-width:80ch; }
  .ck-sp-meta { display:flex; gap:18px; flex-wrap:wrap; font-family:var(--sc-mono);
    font-size:10.5px; letter-spacing:.04em; color:var(--sc-text-dim,#6a7480); }
  .ck-sp-src b { color:var(--sc-text,#2a3a4a); font-weight:600; }
  .ck-sp-next { color:var(--sc-teal,#155752); text-decoration:none; text-transform:uppercase;
    letter-spacing:.1em; }
  .ck-sp-next:hover { color:var(--sc-teal-ink,#155752); }
  .ck-badge { display:inline-flex; align-items:center; padding:3px 8px; font-family:var(--sc-sans); font-size:11px; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; border:1px solid currentColor; border-radius:2px; }
  .ck-badge.tone-positive { color:var(--sc-positive); }
  .ck-badge.tone-warning  { color:var(--sc-warning); }
  .ck-badge.tone-negative { color:var(--sc-negative); }
  .ck-badge.tone-critical { color:var(--sc-critical); }
  .ck-badge.tone-neutral  { color:var(--sc-text-dim); }
  /* Prediction diagnostic chip — visual signal for
   * PredictedMetric.failure_reason. Three variants keyed by tone:
   * na = muted gray ("data doesn't support a prediction"),
   * warn = amber ("model ran, don't lean on it hard"),
   * error = red ("math broke, don't use this number").
   * Smaller and less visually loud than ck-badge — these sit next to
   * a numeric value, not on a card eyebrow. */
  .ck-pred-chip { display:inline-flex; align-items:center; gap:4px; margin-left:6px; padding:1px 6px; font-family:var(--sc-sans); font-size:10.5px; font-weight:500; letter-spacing:0.02em; border:1px solid transparent; border-radius:2px; vertical-align:middle; cursor:help; }
  .ck-pred-chip-na    { color:var(--sc-text-dim); background:transparent; border-color:var(--sc-rule); }
  .ck-pred-chip-warn  { color:var(--sc-warning);  background:rgba(184,115,42,0.06); border-color:var(--sc-warning); }
  .ck-pred-chip-error { color:var(--sc-critical); background:rgba(181,50,30,0.06);  border-color:var(--sc-critical); }
  /* B9 — pre-fix used flex-row + justify-content:space-between which
   * pushed the eyebrow to the left edge and the h2 title to the
   * right edge of the section. User direction: left-align titles
   * globally. Switched to flex-direction:column (vertical stack —
   * eyebrow on top, title below, both left-aligned) so section
   * headers match the editorial pattern ck_page_title already uses.
   * Cascades to 131 call sites across 68 files including
   * gold-standard pages — editorial register change, not layout
   * break: title gets its own row, eyebrow sits above it. */
  .ck-section-header { display:flex; flex-direction:column; align-items:flex-start; gap:6px; margin:var(--sc-s-8) 0 var(--sc-s-5); }
  .ck-section-code { font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); letter-spacing:0.1em; }
  .ck-section-count { display:inline-block; font-family:var(--sc-mono); font-size:13px; font-weight:500; color:var(--sc-text-faint); margin-left:12px; vertical-align:baseline; letter-spacing:0.04em; }

  /* ── Editorial paper top bar (2026-05-24 redesign) ──
     Single 76px paper-toned bar with an ink bottom rule and serif nav
     (green active state). Handoff tokens are inlined as --tb-* locals so
     the bar is deterministic regardless of theme vars. Class names are
     preserved so the topbar JS (user dropdown, Guide trigger, command
     palette, q-pill) keeps working unchanged. Scoped to .ck-topbar* so no
     other page surface is affected. */
  /* Positioning: the topbar is sticky and ONLY sticky — one mode, top:0, no
     transforms and no JS scroll-repositioning, so it pins cleanly with no
     upward jitter/glitch on momentum (trackpad) scroll. Do not add `position:
     fixed` or a `transform` here: a transform makes the bar its own containing
     block and was a known source of sub-pixel jitter on sticky bars. The
     legacy second-line `.ck-subnav` rail is no longer rendered, so there is no
     competing sticky element below this one. */
  .ck-topbar { --tb-paper:#faf6ec; --tb-paper2:#f3eddb; --tb-ink:#15202b;
    --tb-ink2:#2a3a4a; --tb-muted:#6a7480; --tb-rule:#c9c1ac; --tb-green:#1f7a5a;
    --tb-green-deep:#18573f; --tb-green-soft:#d6e8df; --tb-amber:#b8842e;
    position:sticky; top:0; z-index:50; background:var(--tb-paper);
    border-bottom:2px solid var(--tb-ink); }
  /* Full-bleed editorial bar (handoff is full-width with 32px gutters — the
     old max-width:min(1920px,95vw) centering made it read narrow/compressed
     and squeezed the right rail). */
  /* One row, never wrap. `flex-wrap:nowrap` is the default but is declared
     explicitly because the bug it guards against — at narrower-than-fullscreen
     widths the nav links wrapped to a line ABOVE the wordmark and were clipped
     by the fixed 76px height — is a wrap/clip interaction. `min-height` (not a
     hard `height`) means that if anything ever does grow, the bar grows rather
     than clipping its top edge. */
  .ck-topbar-inner { display:flex; flex-wrap:nowrap; align-items:center; gap:0;
    min-height:58px; padding:0 32px; width:100%; box-sizing:border-box; }
  .ck-wordmark { display:inline-flex; align-items:center; gap:0.5rem;
    font-family:var(--sc-serif,'Source Serif 4',Georgia,serif); font-weight:400;
    font-size:20px; color:var(--tb-ink); letter-spacing:-0.018em;
    text-decoration:none; line-height:1; padding-right:32px;
    border-right:1px solid var(--tb-rule); margin-right:16px; }
  .ck-wordmark-text { display:inline-flex; align-items:baseline; }
  .ck-brand-mark { display:none; }   /* text wordmark only, per handoff */
  .ck-wordmark em { font-style:italic; font-weight:400; color:var(--tb-green); margin-left:0.18em; }
  /* `min-width:0` lets the nav shrink inside the flex row instead of forcing
     the inner past 100% (which pushed the right-rail off and triggered the
     wrap/clip). No `overflow` here — the mega-menu panels must be free to
     escape the bar — so the responsive padding steps below keep the links
     fitting at common laptop window widths. */
  /* flex:0 1 auto (NOT 1 1 auto): the nav must size to its content, never
     force-grow to fill the row. Force-growing consumed all free space, which
     defeated `margin-left:auto` on the right zone and let the last nav item
     ("Portfolio") butt up against / overlap the mode chip ("PE PARTNER").
     Content-sized + a non-shrinking right zone keeps a real gap between them. */
  .ck-nav { display:flex; flex-wrap:nowrap; gap:0; flex:0 1 auto; min-width:0; }
  /* Flex-centre the label inside a fixed-height anchor so the text stays
     vertically centred even if the bar grows past 76px (a tall right-rail
     control used to leave the link text floating high because the old
     line-height:76px only centres when the bar is exactly 76px). */
  .ck-nav a { font-family:var(--sc-serif,'Source Serif 4',Georgia,serif);
    font-size:14.5px; font-weight:400; letter-spacing:0; text-transform:none;
    color:var(--tb-ink2); padding:0 18px;
    display:inline-flex; align-items:center; height:58px; line-height:1.1;
    white-space:nowrap;
    border-bottom:2px solid transparent; text-decoration:none; transition:color 0.15s; }
  /* Tighten the nav row before the full-width right rail (mode chip + search +
     Guide + New Deal) collides with it. Steps chosen so the 7 links + wordmark
     + right rail fit without wrapping down to common laptop widths. */
  @media (max-width:1480px){ .ck-nav a { padding:0 13px; } }
  @media (max-width:1320px){ .ck-nav a { padding:0 10px; font-size:13.5px; }
    .ck-topbar-inner { padding:0 22px; } }
  @media (max-width:1180px){ .ck-nav a { padding:0 8px; font-size:13px; } }
  .ck-nav a:hover { color:var(--tb-green); }
  .ck-nav a.active { color:var(--tb-green); font-style:italic;
    border-bottom-color:var(--tb-green); margin-bottom:-1px; }
  .ck-nav a:focus-visible { outline:2px solid var(--tb-green); outline-offset:2px; }
  /* Chevron on nav items that open a section sub-nav (matches handoff). */
  .ck-nav-caret { margin-left:7px; font-size:9px; line-height:1; opacity:.5;
    display:inline-block; transition:opacity .15s, color .15s; }
  .ck-nav a:hover .ck-nav-caret, .ck-nav a.active .ck-nav-caret {
    opacity:1; color:var(--tb-green); }
  /* Hover/focus dropdown menus (replace the old persistent second-line rail).
     Each section nav item carries a paper panel of its sub-pages that opens on
     hover or keyboard focus and overlays the page (no layout shift). */
  .ck-nav-group { position:relative; display:inline-flex; align-items:stretch; }
  .ck-nav-group > a .ck-nav-caret { transition:transform .15s, opacity .15s, color .15s; }
  .ck-nav-group:hover > a .ck-nav-caret,
  .ck-nav-group.is-open > a .ck-nav-caret { opacity:1; color:var(--tb-green); transform:rotate(180deg); }
  .ck-nav-menu { position:absolute; top:100%; left:0;
    background:var(--tb-paper); border:1px solid var(--tb-rule);
    border-top:2px solid var(--tb-green); box-shadow:0 14px 30px rgba(13,35,54,.18);
    z-index:70; display:none; }
  /* Invisible hover bridge spanning the nav-item↔panel seam. The panel sits at
     top:100% (flush) but sub-pixel rounding can leave a 1px dead zone that
     drops the hover and closes the menu mid-travel; this 8px transparent strip
     (a panel descendant, so still inside `.ck-nav`) keeps the pointer "in" the
     region while moving diagonally from the nav item into the panel. Only
     rendered while the panel is shown (parent is display:none otherwise). */
  .ck-nav-menu::before { content:""; position:absolute; left:0; right:0;
    top:-8px; height:8px; background:transparent; }
  /* JS authoritative open state (.is-open) enforces ONE open menu at a time
   * and reliable dismissal. :hover is a no-JS fallback — it can only ever
   * match the single hovered group, so it cannot stack. (The old
   * :focus-within rule kept a panel "stuck" open after a nav item was
   * clicked/focused, letting a focused menu + a hovered menu show at once.) */
  .ck-nav-group:hover > .ck-nav-menu,
  .ck-nav-group.is-open > .ck-nav-menu { display:block; }
  /* When JS has taken control (topbar marked data-menu-js), hover no longer
   * opens panels — only .is-open does — so there is exactly one source of
   * truth and no hover/focus stacking. */
  .ck-topbar[data-menu-js] .ck-nav-group:hover > .ck-nav-menu { display:none; }
  .ck-topbar[data-menu-js] .ck-nav-group.is-open > .ck-nav-menu { display:block; }
  /* Horizontal mega-menu: featured left panel + numbered destination grid.
   * CRITICAL: the base rule must NOT set `display`, so the panel inherits
   * `.ck-nav-menu{display:none}` and stays hidden by default. A previous
   * `display:grid` here overrode that and made EVERY mega-menu visible at once
   * (the stacking-over-the-dashboard bug). Display is now owned solely by the
   * show rules below, so only the hovered / .is-open panel renders. */
  /* `minmax(0,1fr)` (not bare `1fr`) on the items track is REQUIRED: a bare
     `1fr` track carries an implicit `min-width:auto` sized to its widest
     content, so a wide destinations grid forces the whole panel past
     `min-width` and off the right edge of the viewport (the "panel runs off
     screen / text doesn't wrap" bug). minmax(0,…) lets the track shrink so
     the inner cells wrap instead. `max-width` clamps to the viewport on
     narrow windows (overrides min-width when smaller). */
  /* Full-bleed editorial mega-menu (design handoff v2 · 2026-05-27).
     The panel is a full-width paper backdrop pinned under the 76px bar (a true
     mega-menu, not a compact dropdown); its inner content (.ck-mega-inner) is
     constrained to --content-max and centered so the lede's left edge aligns
     with the wordmark and the listing's right edge with the right rail.
     position:fixed lives ONLY on .ck-nav-mega (the single-positioning-mode
     guard isolates the .ck-topbar base rule, which is untouched) and the bar
     carries no transform, so fixed resolves against the viewport — true
     full-bleed with one continuous ink underline reading as the bar's. */
  .ck-nav-mega { --content-max:1320px;
    position:fixed; top:58px; left:0; right:0; width:auto; max-width:none;
    padding:0; overflow:visible; background:var(--tb-paper);
    border:0; border-top:1px solid var(--tb-rule);
    border-bottom:2px solid var(--tb-ink);
    box-shadow:0 30px 50px -20px rgba(13,35,54,.18);
    animation:ckMegaIn .14s ease-out; }
  @media (prefers-reduced-motion: reduce){ .ck-nav-mega { animation:none; } }
  @keyframes ckMegaIn { from{opacity:0; transform:translateY(-4px);}
    to{opacity:1; transform:translateY(0);} }
  .ck-mega-inner { max-width:var(--content-max); margin:0 auto;
    padding:20px 32px 16px; display:grid; grid-template-columns:2fr 3fr;
    column-gap:40px; row-gap:0; align-items:start; }
  /* Shown mega = block (the centered 2fr/3fr grid lives on .ck-mega-inner). */
  .ck-nav-group:hover > .ck-nav-mega,
  .ck-nav-group.is-open > .ck-nav-mega { display:block; }
  .ck-topbar[data-menu-js] .ck-nav-group:hover > .ck-nav-mega { display:none; }
  .ck-topbar[data-menu-js] .ck-nav-group.is-open > .ck-nav-mega { display:block; }
  /* Full-bleed → no per-group right-edge anchoring needed (the panel already
     spans the viewport); pin every group's panel to the same full width. */
  .ck-nav-group:last-of-type .ck-nav-mega,
  .ck-nav-group:nth-last-of-type(2) .ck-nav-mega,
  .ck-nav-group:nth-last-of-type(3) .ck-nav-mega { left:0; right:0; }
  /* LEDE column (2fr) — editorial: kicker · headline · pull-quote · anchored
     all-tools CTA. min-width:0 keeps a long blurb wrapping in-column (guarded);
     the right rule + 48px pad separate it from the listing. */
  .ck-mega-lede { display:flex; flex-direction:column; min-width:0;
    padding-right:36px; border-right:1px solid var(--tb-rule); }
  .ck-mega-feat { display:flex; flex-direction:column; gap:8px; padding:0;
    min-width:0; overflow:visible; background:transparent; border:0;
    text-decoration:none; }
  .ck-mega-kicker { font-family:var(--sc-mono,monospace); font-size:9px;
    letter-spacing:.14em; text-transform:uppercase; color:var(--tb-green);
    display:inline-flex; align-items:center; gap:8px; }
  .ck-mega-dot { width:5px; height:5px; border-radius:50%;
    background:var(--tb-green); display:inline-block; flex-shrink:0; }
  .ck-mega-feat-eyebrow { font-family:var(--sc-mono,monospace); font-size:9px;
    letter-spacing:.14em; text-transform:uppercase; color:var(--tb-green); }
  .ck-mega-feat-title { font-family:var(--sc-serif,Georgia,serif); font-weight:400;
    font-size:22px; line-height:1.06; letter-spacing:-.018em; color:var(--tb-ink);
    text-wrap:balance; max-width:100%;
    white-space:normal; overflow-wrap:anywhere; word-break:break-word; }
  .ck-mega-feat-title em { font-style:italic; color:var(--tb-green); }
  .ck-mega-feat-blurb { font-family:var(--sc-serif,Georgia,serif); font-style:italic;
    font-size:12.5px; line-height:1.4; color:var(--tb-ink2); max-width:42ch;
    border-left:2px solid var(--tb-green); padding-left:14px;
    white-space:normal; overflow-wrap:anywhere; word-break:break-word; }
  /* Right column = the leaves grid + the all-tools link beneath it, aligned to
     the column's FAR RIGHT. The link lives INSIDE the listing box (not a
     separate full-width footer chunk) and reads in green so it's the visible
     "see everything" affordance. It sits in normal flow below the leaves, so
     it can never overlap the lede pull-quote or the leaves. */
  .ck-mega-listing { display:flex; flex-direction:column; min-width:0; }
  .ck-mega-all { align-self:flex-end; margin-top:18px;
    font-family:var(--sc-mono,monospace); font-size:11px; font-weight:600;
    letter-spacing:.14em; text-transform:uppercase; color:var(--tb-green);
    text-decoration:none; display:inline-flex; align-items:center; gap:7px;
    padding:6px 10px; border-radius:2px; transition:color .12s, background .12s; }
  .ck-mega-all:hover { color:var(--tb-green-deep); background:var(--tb-green-soft); }
  .ck-mega-all-arr { font-size:13px; }
  /* LISTING column (3fr) — 3 columns × 2 rows for the 6 ranked leaves.
     repeat(3, minmax(0,1fr)) + per-item min-width:0 + overflow-wrap below keeps
     a long description wrapping in-column instead of bleeding across (the v3
     overflow bug). */
  .ck-mega-items { display:grid; grid-template-columns:repeat(3, minmax(0,1fr));
    column-gap:36px; row-gap:22px; padding:0; align-content:start; min-width:0; }
  .ck-mega-item { display:grid; grid-template-columns:28px minmax(0,1fr);
    column-gap:12px; padding:0; text-decoration:none;
    align-items:baseline; min-width:0; }
  .ck-mega-item:hover { background:transparent; }
  /* Mono counter, baseline-aligned to the 17px serif title's first line. */
  .ck-mega-idx { font-family:var(--sc-mono,monospace); font-size:10.5px;
    letter-spacing:.1em; color:var(--tb-muted); line-height:1.4; padding-top:3px;
    flex-shrink:0; transition:color .12s; }
  .ck-mega-item:hover .ck-mega-idx { color:var(--tb-green); }
  .ck-mega-it-body { display:flex; flex-direction:column; gap:3px; min-width:0;
    flex:1 1 auto; }
  /* overflow-wrap:anywhere guarantees even a long unbroken token wraps inside
     its column instead of bleeding into the neighbour. */
  .ck-mega-it-label { font-family:var(--sc-serif,Georgia,serif); font-size:14px;
    color:var(--tb-ink); line-height:1.2; letter-spacing:-.005em;
    overflow-wrap:anywhere; transition:color .12s; }
  .ck-mega-item:hover .ck-mega-it-label { color:var(--tb-green); }
  .ck-mega-it-desc { font-family:var(--sc-serif,Georgia,serif); font-style:italic;
    font-size:11.5px; color:var(--tb-muted); line-height:1.4; overflow-wrap:anywhere; }
  /* Responsive: stack the lede above the listing, then collapse the listing
     columns. The backdrop stays full-bleed; only .ck-mega-inner reflows. */
  @media (max-width:1100px){
    .ck-mega-inner { grid-template-columns:1fr; gap:28px; padding:24px 22px; }
    .ck-mega-lede { padding-right:0; border-right:0;
      border-bottom:1px solid var(--tb-rule); padding-bottom:22px; }
    .ck-mega-items { grid-template-columns:1fr 1fr; }
    .ck-mega-feat-title { font-size:19px; } }
  @media (max-width:680px){ .ck-mega-items { grid-template-columns:1fr; } }
  /* Legacy single-column dropdown links (kept for .ck-subnav-link reuse). */
  .ck-nav-menu .ck-subnav-link { display:block; padding:9px 20px; border:0;
    border-bottom:0; white-space:nowrap; color:var(--tb-ink2);
    border-left:2px solid transparent; }
  .ck-nav-menu .ck-subnav-link:hover { color:var(--tb-green);
    background:var(--tb-paper2); border-bottom:0; border-left-color:var(--tb-green); }
  .ck-topbar-right { margin-left:auto; flex:0 0 auto; display:flex;
    align-items:center; gap:14px;
    padding-left:24px; border-left:1px solid var(--tb-rule); }
  /* Workspace-mode chip — green (partner) / amber (consulting) underline. */
  .ck-mode-chip { font-family:var(--sc-mono,'JetBrains Mono',monospace); font-size:10px;
    font-weight:600; letter-spacing:0.1em; text-transform:uppercase; text-decoration:none;
    padding:4px 2px 3px; border-radius:0; white-space:nowrap; border:0;
    border-bottom:2px solid var(--tb-green); color:var(--tb-muted);
    background:transparent; transition:color 0.15s, border-color 0.15s; }
  .ck-mode-chip:hover { color:var(--tb-ink); }
  .ck-mode-chip[data-mode="consulting"] { border-bottom-color:var(--tb-amber); }
  .ck-mode-chip[data-mode="consulting"]:hover { color:var(--tb-ink); }
  /* The mode chip is redundant with the user dropdown, so it's the first thing
     to shed when the row gets crowded — hiding it by 1360px keeps the 7 nav
     items from colliding with the right zone on common laptops. */
  @media (max-width:1360px){ .ck-mode-chip { display:none; } }
  .ck-search-form { margin:0; position:relative; display:flex; align-items:center; }
  .ck-search { border:1px solid var(--tb-ink); padding:7px 44px 7px 12px; font-size:14px;
    width:220px; border-radius:2px; background:var(--tb-paper2);
    font-family:var(--sc-serif,'Source Serif 4',Georgia,serif); font-style:italic;
    color:var(--tb-ink); letter-spacing:0; }
  /* Shrink the search field before it crowds the nav into the right zone. */
  @media (max-width:1480px){ .ck-search { width:150px; } }
  .ck-search::placeholder { color:var(--tb-muted); font-style:italic; }
  .ck-search:focus { outline:none; border-color:var(--tb-green); box-shadow:0 0 0 3px rgba(31,122,90,.12); }
  .ck-search-kbd { position:absolute; right:8px; font-family:var(--sc-mono,'JetBrains Mono',monospace);
    font-size:10.5px; color:var(--tb-muted); border:1px solid var(--tb-rule); border-radius:3px;
    padding:1px 5px; pointer-events:none; background:var(--tb-paper); }
  @media (max-width:1280px){ .ck-search { width:160px; } }
  /* Guide trigger — outlined ink button, green on hover. */
  .ck-guide-trigger { display:inline-flex; align-items:center; gap:6px;
    font-family:var(--sc-mono,'JetBrains Mono',monospace); font-size:11px;
    font-weight:600; letter-spacing:0.12em; text-transform:uppercase; color:var(--tb-ink);
    background:transparent; border:1px solid var(--tb-ink); border-radius:2px; padding:7px 14px;
    cursor:pointer; transition:background .15s, color .15s, border-color .15s; }
  /* Green italic-serif "?" accent — the handoff detail that keeps Guide
     from reading as washed-out/disabled against the busy right zone. */
  .ck-guide-glyph { font-family:var(--sc-serif,'Source Serif 4',Georgia,serif);
    font-style:italic; font-size:13px; line-height:1; color:var(--tb-green); }
  .ck-guide-trigger:hover { background:var(--tb-paper2); color:var(--tb-green); border-color:var(--tb-green); }
  .ck-guide-trigger:hover .ck-guide-glyph { color:var(--tb-green); }
  .ck-guide-trigger:focus-visible { outline:2px solid var(--tb-green); outline-offset:2px; }
  @media (max-width:1280px){ .ck-guide-trigger { display:none; } }  /* Guide stays in the avatar dropdown */
  /* + New deal — primary CTA, solid ink, green-deep on hover. */
  .ck-newdeal-cta { display:inline-flex; align-items:center; gap:6px;
    font-family:var(--sc-mono,'JetBrains Mono',monospace); font-size:11px; font-weight:600;
    letter-spacing:0.12em; text-transform:uppercase; color:var(--tb-paper); background:var(--tb-ink);
    border:1px solid var(--tb-ink); border-radius:2px; padding:8px 14px; text-decoration:none;
    white-space:nowrap; transition:background .15s, border-color .15s; }
  .ck-newdeal-cta:hover { background:var(--tb-green-deep); border-color:var(--tb-green-deep); }
  .ck-newdeal-cta:focus-visible { outline:2px solid var(--tb-green); outline-offset:2px; }
  /* Legacy generic CTA (used on other surfaces) — unchanged. */
  .ck-cta { display:inline-flex; align-items:center; gap:8px; font-family:var(--sc-sans); font-size:12px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:var(--sc-on-navy); border:1px solid var(--sc-on-navy); padding:8px 14px; border-radius:2px; text-decoration:none; transition:background 0.15s, color 0.15s; }
  .ck-cta:hover { background:var(--sc-teal); border-color:var(--sc-teal); color:var(--sc-navy); }
  .ck-cta-arrow { display:inline-block; width:10px; height:10px; }
  .ck-user-chip { width:38px; height:38px; border-radius:50%; background:var(--tb-green);
    color:var(--tb-paper); display:flex; align-items:center; justify-content:center;
    font-family:var(--sc-mono,'JetBrains Mono',monospace); font-weight:600; font-size:12.5px;
    letter-spacing:0.04em; cursor:pointer; border:1px solid var(--tb-green-deep); padding:0;
    transition:transform .12s, box-shadow .12s; }
  .ck-user-chip:hover { transform:scale(1.04); box-shadow:0 0 0 3px var(--tb-green-soft); }
  .ck-user-chip:focus-visible { outline:2px solid var(--tb-green); outline-offset:2px; }
  @media (prefers-reduced-motion: reduce){ .ck-user-chip:hover { transform:none; } }
  /* Portfolio-wide diligence-questions pill in the topbar. JS
   * hydrates from rcm_deal_*_questions on DOMContentLoaded; hidden
   * when zero open across the portfolio. Warning-tone numeric +
   * italic Source-Serif label, matches the row-level Q-chips on
   * the recently-viewed rails so partners read the signal the same
   * way wherever they encounter it. */
  .ck-topbar-qpill {
    display:inline-flex; align-items:baseline; gap:6px;
    padding:5px 10px;
    background:transparent;
    border:1px solid var(--sc-warning, #b8732a);
    border-radius:999px;
    text-decoration:none;
    color:var(--sc-warning, #b8732a);
    transition:background 120ms ease, color 120ms ease;
  }
  .ck-topbar-qpill[hidden] { display:none !important; }
  .ck-topbar-qpill:hover {
    background:var(--sc-warning, #b8732a); color:#fff;
  }
  .ck-topbar-qpill-num {
    font-family:var(--sc-mono); font-weight:700; font-size:11px;
    font-variant-numeric:tabular-nums;
    letter-spacing:0.04em;
  }
  .ck-topbar-qpill-label {
    font-family:var(--sc-serif); font-style:italic; font-size:11px;
  }
  @media print { .ck-topbar-qpill { display:none !important; } }
  .ck-user-menu { position:relative; }
  .ck-user-dropdown { position:absolute; top:calc(100% + 10px); right:0; min-width:200px; background:#fff; border:1px solid var(--sc-rule); box-shadow:var(--sc-shadow-2,0 8px 24px rgba(11,32,55,0.14)); border-radius:2px; padding:6px 0; z-index:60; }
  .ck-user-dropdown[hidden] { display:none !important; }
  .ck-user-dropdown-item { display:block; width:100%; text-align:left; padding:9px 16px; font-family:var(--sc-sans); font-size:13px; color:var(--sc-text); text-decoration:none; background:transparent; border:0; cursor:pointer; letter-spacing:0; text-transform:none; font-weight:500; }
  .ck-user-dropdown-item:hover { background:var(--sc-bone,#f2ede3); color:var(--sc-teal-ink); }
  .ck-user-dropdown-divider { height:1px; background:var(--sc-rule); margin:4px 0; }
  .ck-user-recent { padding:6px 0 4px; border-bottom:1px solid var(--sc-rule); margin-bottom:4px; }
  .ck-user-recent[hidden] { display:none !important; }
  .ck-user-recent-head { padding:4px 16px 6px; font-family:var(--sc-mono); font-size:10px; font-weight:700; letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-text-faint); }
  .ck-user-recent-item { display:flex; flex-direction:column; padding:6px 16px; text-decoration:none; color:var(--sc-text); font-size:13px; }
  .ck-user-recent-item:hover { background:var(--sc-bone); color:var(--sc-teal-ink); }
  .ck-user-recent-name { font-weight:500; color:var(--sc-navy); }
  .ck-user-recent-item:hover .ck-user-recent-name { color:var(--sc-teal-ink); }
  .ck-user-recent-slug { font-family:var(--sc-mono); font-size:10.5px; color:var(--sc-text-faint); letter-spacing:0.04em; }
  .ck-user-dropdown-form { margin:0; }
  .ck-user-dropdown-logout { color:var(--sc-negative,#c0392b); }
  /* Sub-nav rail — parchment strip with section pills, sits sticky
   * just below the navy topbar. Lets a partner click into a common
   * second-level page (Alerts, Heatmap, Find Comps, etc.) without
   * landing on a section index first. */
  .ck-subnav { background:#f3eddb; border-bottom:1px solid #c9c1ac; position:sticky; top:58px; z-index:40; }
  /* Subnav rail aligns to the full-width top bar's 32px gutter (so its first
     pill sits under the wordmark) instead of the old centered max-width. */
  .ck-subnav-inner { display:flex; gap:var(--sc-s-5); align-items:center; padding:10px 32px; width:100%; box-sizing:border-box; overflow-x:auto; }
  .ck-subnav-link { font-family:var(--sc-sans); font-size:12px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:#6a7480; text-decoration:none; padding:6px 1px; border-bottom:2px solid transparent; border-radius:0; white-space:nowrap; transition:color 0.15s, border-color 0.15s; }
  .ck-subnav-link:hover { color:#1f7a5a; border-bottom-color:#c9c1ac; }
  .ck-subnav-link.active { color:#1f7a5a; border-bottom-color:#1f7a5a; }
  /* Breadcrumbs are subtle inline wayfinding above the page title — NOT a
   * second nav bar. The old full-width bottom-border strip read as a second
   * bar under the topbar (partner-flagged as unprofessional); section
   * navigation now lives entirely in the topbar mega-menu dropdowns. */
  .ck-breadcrumbs { display:flex; gap:8px; padding:18px var(--sc-s-7) 0; max-width:min(1920px, 95vw); margin:0 auto; font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); letter-spacing:0.08em; text-transform:uppercase; }
  .ck-breadcrumbs a { color:var(--sc-text-dim); text-decoration:none; }
  .ck-breadcrumbs a:hover { color:var(--sc-teal-ink); }
  .ck-breadcrumbs .sep { color:var(--sc-rule-2); }

  /* Editorial primitives — eyebrow + section intro + arrow link */
  .ck-eyebrow { display:inline-flex; align-items:center; gap:12px; font-family:var(--sc-mono); font-size:11px; font-weight:600; letter-spacing:0.16em; text-transform:uppercase; color:var(--sc-text-dim); }
  .ck-eyebrow::before { content:''; display:inline-block; width:24px; height:2px; background:var(--sc-teal); }
  .ck-eyebrow.on-navy { color:var(--sc-on-navy-dim); }
  .ck-eyebrow.on-navy::before { background:var(--sc-teal); }
  /* Empty state — the "no data here yet" surface every page reaches
   * for. Reads as a deliberate editorial card, not a forgotten gap. */
  /* 2026-05-28 style-sweep · shadow removed from .ck-empty-state.
     Same depth-by-paper-tone rule as .ck-panel. The .tone-* variants
     below still carry a 3px colored left-border as a SEMANTIC tone
     signal (positive / warning), not decoration — kept per spec
     Tier-2 §2.12 (tag/badge color carries category, allowed). */
  .ck-empty-state { background:#fff; border:1px solid var(--sc-rule); border-radius:2px; padding:48px 40px; max-width:640px; margin:24px auto; text-align:center; display:flex; flex-direction:column; align-items:center; gap:14px; }
  .ck-empty-state.ck-empty-state-positive { border-left:3px solid var(--sc-positive); }
  .ck-empty-state.ck-empty-state-warning { border-left:3px solid var(--sc-warning); }
  .ck-empty-state-icon { width:56px; height:56px; border-radius:50%; background:var(--sc-bone); display:flex; align-items:center; justify-content:center; font-size:24px; color:var(--sc-teal-ink); margin-bottom:4px; }
  .ck-empty-state .ck-eyebrow { margin-bottom:2px; }
  .ck-empty-state-title { font-family:var(--sc-serif); font-weight:500; font-size:22px; color:var(--sc-navy); letter-spacing:-0.01em; line-height:1.2; margin:0; max-width:32ch; }
  .ck-empty-state-body { font-family:var(--sc-serif); font-size:14.5px; line-height:1.6; color:var(--sc-text-dim); max-width:48ch; margin:0; }
  .ck-empty-state-actions { display:flex; gap:10px; margin-top:8px; }
  .ck-empty-state-cta { font-family:var(--sc-sans); font-size:12px; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; color:#fff; background:var(--sc-navy); padding:10px 18px; border:1px solid var(--sc-navy); border-radius:2px; text-decoration:none; transition:background 0.12s, border-color 0.12s; }
  .ck-empty-state-cta:hover { background:var(--sc-teal); border-color:var(--sc-teal); }
  .ck-section-intro { position:relative; margin:var(--sc-s-6) 0 var(--sc-s-5); padding-right:32px; }
  .ck-section-intro h2 { font-family:var(--sc-serif); font-weight:400; font-size:clamp(20px, 2.2vw, 26px); line-height:1.2; letter-spacing:-0.01em; color:var(--sc-navy); margin:var(--sc-s-3) 0 0; max-width:32ch; }
  .ck-section-intro h2 em { font-style:italic; font-weight:400; color:var(--sc-teal-ink); }
  .ck-section-intro .ck-section-body { font-family:var(--sc-serif); font-size:14px; line-height:1.55; color:var(--sc-text-dim); margin-top:var(--sc-s-3); max-width:64ch; }
  .ck-section-intro-dismiss { position:absolute; top:0; right:0; width:24px; height:24px; padding:0; background:transparent; border:0; color:var(--sc-text-faint); font-size:20px; line-height:1; cursor:pointer; border-radius:50%; transition:color 0.12s, background 0.12s; }
  .ck-section-intro-dismiss:hover { color:var(--sc-navy); background:var(--sc-bone,#ece5d6); }
  .ck-section-intro[hidden] { display:none !important; }
  .ck-arrow { display:inline-flex; align-items:center; gap:6px; font-family:var(--sc-sans); font-size:12px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; color:var(--sc-teal-ink); text-decoration:none; }
  .ck-arrow::after { content:'\\2197'; font-size:14px; line-height:1; }
  .ck-arrow:hover { color:var(--sc-navy); }
  .ck-arrow.on-navy { color:var(--sc-teal); }
  .ck-arrow.on-navy:hover { color:var(--sc-on-navy); }

  /* Editorial card — image-top with eyebrow / title / body / arrow */
  .ck-card-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:var(--sc-s-7); margin:var(--sc-s-6) 0; }
  .ck-image-card { display:flex; flex-direction:column; gap:var(--sc-s-4); padding:0; background:transparent; border:0; }
  .ck-image-card-img { width:100%; aspect-ratio:4/3; background:var(--sc-bone); border-bottom:2px solid var(--sc-teal); object-fit:cover; }
  .ck-image-card-body { padding:var(--sc-s-4) 0 var(--sc-s-3); }
  .ck-image-card-title { font-family:var(--sc-serif); font-weight:500; font-size:21px; line-height:1.25; color:var(--sc-navy); margin:var(--sc-s-3) 0 var(--sc-s-3); }
  .ck-image-card-body p { font-family:var(--sc-sans); font-size:14px; line-height:1.6; color:var(--sc-text-dim); margin:0 0 var(--sc-s-4); }

  /* Severity panels — replace legacy <div class="card"> in alerts/etc.
     2026-05-28 sweep · shadow removed (Tier-4 don'ts). The 4px
     `border-left` is RETAINED here because it's SEMANTIC — the
     tone-red / tone-amber / tone-info / tone-positive classes
     below recolor it to encode severity (a tag/badge use, per
     spec Tier-2 §2.12). Without it, the alert-severity surface
     loses its only at-a-glance category cue. */
  .ck-severity-panel { background:#fff; border:1px solid var(--sc-rule); border-left:4px solid var(--sc-rule-2); border-radius:2px; margin:0 0 var(--sc-s-5); }
  .ck-severity-panel.tone-red { border-left-color:var(--sc-negative); }
  .ck-severity-panel.tone-amber { border-left-color:var(--sc-warning); }
  .ck-severity-panel.tone-info { border-left-color:var(--sc-teal); }
  .ck-severity-panel.tone-positive { border-left-color:var(--sc-positive); }
  .ck-severity-panel-head { display:flex; align-items:baseline; justify-content:space-between; gap:var(--sc-s-4); padding:14px 18px 6px; border-bottom:1px solid var(--sc-rule); }
  .ck-severity-panel-head h3 { font-family:var(--sc-sans); font-weight:700; font-size:13px; letter-spacing:0.12em; text-transform:uppercase; color:var(--sc-navy); }
  .ck-severity-panel-head .count { font-family:var(--sc-mono); font-size:13px; color:var(--sc-text-faint); }
  .ck-severity-list { list-style:none; padding:0; margin:0; }
  .ck-severity-list li { padding:14px 18px; border-bottom:1px solid var(--sc-rule); display:flex; flex-direction:column; gap:6px; }
  .ck-severity-list li:last-child { border-bottom:0; }
  .ck-severity-row { display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
  .ck-severity-row .deal { font-family:var(--sc-sans); font-weight:600; color:var(--sc-teal-ink); text-decoration:none; }
  .ck-severity-row .deal:hover { color:var(--sc-navy); text-decoration:underline; text-decoration-thickness:1px; text-underline-offset:3px; }
  .ck-severity-row .title { color:var(--sc-text); font-size:14px; }
  .ck-severity-row .age { font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); margin-left:auto; }
  .ck-severity-detail { font-family:var(--sc-sans); font-size:13px; line-height:1.5; color:var(--sc-text-dim); margin-left:0; }
  .ck-severity-actions { display:flex; align-items:center; gap:8px; margin-top:4px; }
  .ck-severity-actions select { font-family:var(--sc-sans); font-size:12px; padding:4px 8px; border:1px solid var(--sc-rule); border-radius:2px; background:#fff; color:var(--sc-text); }
  .ck-severity-actions button { font-family:var(--sc-sans); font-size:12px; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; padding:6px 12px; border:1px solid var(--sc-navy); background:var(--sc-navy); color:var(--sc-on-navy); border-radius:2px; cursor:pointer; }
  .ck-severity-actions button:hover { background:var(--sc-navy-2); border-color:var(--sc-navy-2); }
  /* 2026-05-28 sweep · .ck-affirm-empty was the "everything's
     clear" affirmative state on alert/notes/etc. surfaces. Was
     emitting BOTH a shadow AND a decorative 4px positive-tone
     left-border accent. Both removed: depth is now paper-tone +
     hairline, and the positive tone is conveyed by the h3 color
     (var(--sc-positive)) which is already in the rule below.
     Unlike .ck-severity-panel above, this one carries no
     multi-tone semantic — only the single positive flavor — so
     the colored bar was pure decoration. */
  .ck-affirm-empty { background:#fff; border:1px solid var(--sc-rule); border-radius:2px; padding:20px 24px; }
  .ck-affirm-empty h3 { font-family:var(--sc-serif); font-weight:500; font-size:20px; color:var(--sc-positive); margin:0 0 6px; }
  .ck-affirm-empty p { font-family:var(--sc-sans); font-size:14px; line-height:1.6; color:var(--sc-text-dim); margin:0; max-width:64ch; }
  .ck-affirm-empty .ck-arrow { margin-top:var(--sc-s-4); }

  /* Search hero — navy panel + italic-serif label + circular submit
   * + teal chevron-cut bottom-right corner. Mirrors chartis.com/insights. */
  /* Page title — H1-equivalent header for content pages
   * (/library, /research, /pipeline). Sits above KPIs and search. */
  .ck-page-title { margin:0 0 var(--sc-s-6); display:flex; flex-direction:column; gap:8px; }
  .ck-page-title h1 { font-family:var(--sc-serif); font-weight:400; font-size:clamp(28px, 3.4vw, 40px); line-height:1.1; letter-spacing:-0.015em; color:var(--sc-navy); margin:0; }
  .ck-page-title h1 em { font-style:italic; font-weight:400; color:var(--sc-teal-ink); }
  .ck-page-title-meta { font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); letter-spacing:0.08em; text-transform:uppercase; }
  /* Page explainer — italic-teal lead + serif body, rendered below
   * ck_page_title. Mirrors the Portfolio Heatmap intro. */
  .ck-page-explainer { font-family:var(--sc-serif); font-size:15px; line-height:1.6;
    color:var(--sc-text-dim); max-width:72ch; margin:var(--sc-s-4) 0 var(--sc-s-6); }
  .ck-page-explainer em { color:var(--sc-teal-ink); font-style:italic; }
  .ck-page-explainer-source { display:block; margin-top:8px;
    font-family:var(--sc-mono); font-size:10.5px; letter-spacing:0.06em;
    color:var(--sc-text-faint); text-transform:uppercase; }

  /* Search hero — full-bleed navy panel with italic-serif label and
   * teal chevron. Sits in the page-header stack, between the KPI
   * strip (above) and the filter rail + table (below). */
  .ck-search-hero { position:relative; background:var(--sc-navy); color:var(--sc-on-navy); padding:48px 0 56px; margin:0 0 var(--sc-s-7); overflow:hidden; }
  .ck-search-hero-inner { max-width:min(1920px, 95vw); margin:0 auto; padding:0 var(--sc-s-7); display:flex; align-items:baseline; gap:var(--sc-s-7); }
  .ck-search-hero-label { font-family:var(--sc-serif); font-size:36px; font-weight:400; font-style:italic; letter-spacing:-0.01em; color:var(--sc-on-navy); flex-shrink:0; }
  .ck-search-hero-form { flex:1; display:flex; align-items:center; gap:14px; border-bottom:1px solid var(--sc-on-navy-dim); padding-bottom:8px; transition:border-color 0.15s; }
  .ck-search-hero-form:focus-within { border-bottom-color:var(--sc-teal); }
  .ck-search-hero-input { flex:1; background:transparent; border:0; font-family:var(--sc-serif); font-size:22px; color:var(--sc-on-navy); padding:8px 0; outline:none; min-width:0; }
  .ck-search-hero-input::placeholder { color:var(--sc-on-navy-faint); font-style:italic; }
  .ck-search-hero-submit { background:transparent; border:1px solid var(--sc-on-navy-dim); border-radius:50%; width:36px; height:36px; display:inline-flex; align-items:center; justify-content:center; color:var(--sc-on-navy); cursor:pointer; flex-shrink:0; transition:color 0.15s, border-color 0.15s; }
  .ck-search-hero-submit:hover { color:var(--sc-teal); border-color:var(--sc-teal); }
  .ck-search-hero-chevron { position:absolute; right:0; bottom:0; width:0; height:0; border-style:solid; border-width:0 0 64px 64px; border-color:transparent transparent var(--sc-teal) transparent; pointer-events:none; }

  /* Filter sidebar — chartis.com/insights left rail. Eyebrow-style
   * group headers, radio/checkbox rows, progressive-disclosure More
   * expander when a group has more than ~8 options. Pairs with
   * ck-search-hero (above) and ck-rail-layout (below) for the full
   * Insights triplet on /library, /research, /notes. */
  .ck-rail-layout { display:grid; grid-template-columns:240px 1fr; gap:var(--sc-s-7); align-items:start; margin:0 0 var(--sc-s-6); }
  @media (max-width: 880px) { .ck-rail-layout { grid-template-columns:1fr; } }
  /* top == 58px topbar + 12px. Was 88px (pre-#1014 76px topbar). */
  .ck-filter-rail { font-family:var(--sc-sans); position:sticky; top:70px; }
  .ck-filter-rail form { margin:0; }
  .ck-filter-rail-title { font-family:var(--sc-mono); font-size:11px; font-weight:600; letter-spacing:0.16em; text-transform:uppercase; color:var(--sc-text-dim); margin:0 0 var(--sc-s-5); display:flex; align-items:center; gap:12px; }
  .ck-filter-rail-title::before { content:''; display:inline-block; width:24px; height:2px; background:var(--sc-teal); flex-shrink:0; }
  .ck-filter-group { margin:0 0 var(--sc-s-6); border-top:1px solid var(--sc-rule); padding-top:var(--sc-s-4); }
  .ck-filter-group:first-of-type { border-top:0; padding-top:0; }
  .ck-filter-group-head { font-family:var(--sc-sans); font-size:11px; font-weight:700; letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-navy); margin:0 0 var(--sc-s-3); }
  .ck-filter-list { list-style:none; padding:0; margin:0; }
  .ck-filter-list li { padding:5px 0; }
  .ck-filter-list label { display:flex; align-items:center; gap:8px; cursor:pointer; font-family:var(--sc-sans); font-size:13px; line-height:1.35; color:var(--sc-text); }
  .ck-filter-list label:hover { color:var(--sc-teal-ink); }
  .ck-filter-list input[type="radio"], .ck-filter-list input[type="checkbox"] { accent-color:var(--sc-teal); cursor:pointer; flex-shrink:0; margin:0; }
  .ck-filter-overflow { margin-top:4px; }
  .ck-filter-overflow > summary { font-family:var(--sc-sans); font-size:11px; font-weight:600; letter-spacing:0.1em; text-transform:uppercase; color:var(--sc-teal-ink); cursor:pointer; padding:6px 0; list-style:none; outline:none; }
  .ck-filter-overflow > summary::-webkit-details-marker { display:none; }
  .ck-filter-overflow > summary::after { content:' \\25BC'; font-size:9px; margin-left:4px; }
  .ck-filter-overflow[open] > summary::after { content:' \\25B2'; }
  .ck-filter-overflow > summary:hover { color:var(--sc-navy); }
  .ck-filter-submit { font-family:var(--sc-sans); font-size:12px; font-weight:600; letter-spacing:0.08em; text-transform:uppercase; padding:8px 14px; border:1px solid var(--sc-navy); background:var(--sc-navy); color:var(--sc-on-navy); border-radius:2px; cursor:pointer; margin-top:var(--sc-s-4); width:100%; transition:background 0.15s, color 0.15s; }
  .ck-filter-submit:hover { background:var(--sc-teal); border-color:var(--sc-teal); color:var(--sc-navy); }

  /* Results header — N RESULTS + active-filter chips + Clear all.
   * Sits between the filter sidebar / search hero and the results
   * table on /library, /research, /notes. Mirrors chartis.com/insights. */
  .ck-results-header { display:flex; align-items:baseline; justify-content:space-between; gap:var(--sc-s-5); margin:0 0 var(--sc-s-4); padding-bottom:var(--sc-s-3); border-bottom:1px solid var(--sc-rule); flex-wrap:wrap; }
  .ck-results-count { font-family:var(--sc-serif); font-weight:500; color:var(--sc-navy); display:inline-flex; align-items:baseline; gap:10px; }
  .ck-results-num { font-size:28px; font-variant-numeric:tabular-nums; letter-spacing:-0.01em; }
  .ck-results-label { font-family:var(--sc-mono); font-size:11px; font-weight:600; letter-spacing:0.16em; text-transform:uppercase; color:var(--sc-text-dim); }
  .ck-results-chips { display:flex; align-items:center; gap:8px; flex-wrap:wrap; }
  .ck-chip { display:inline-flex; align-items:center; gap:6px; padding:4px 10px; background:var(--sc-bone); border:1px solid var(--sc-rule); border-radius:14px; font-family:var(--sc-sans); font-size:12px; color:var(--sc-text); text-decoration:none; transition:background 0.15s, border-color 0.15s, color 0.15s; }
  .ck-chip:hover { background:#fff; border-color:var(--sc-teal); color:var(--sc-navy); }
  .ck-chip-x { font-size:14px; line-height:1; color:var(--sc-text-faint); }
  .ck-chip:hover .ck-chip-x { color:var(--sc-teal-ink); }
  .sr-only { position:absolute; width:1px; height:1px; padding:0; margin:-1px; overflow:hidden; clip:rect(0,0,0,0); border:0; }

  /* Notes list — used by /notes editorial port. ck-chip pills here
   * double as tag-filter shortcuts. */
  .ck-note-list { list-style:none; padding:0; margin:0; }
  .ck-note-row { padding:14px 0; border-bottom:1px solid var(--sc-rule); display:flex; flex-direction:column; gap:6px; }
  .ck-note-row:last-child { border-bottom:0; }
  .ck-note-meta { display:flex; align-items:center; gap:10px; flex-wrap:wrap; font-family:var(--sc-sans); font-size:12px; color:var(--sc-text-faint); }
  .ck-note-deal { font-weight:600; color:var(--sc-teal-ink); text-decoration:none; }
  .ck-note-deal:hover { color:var(--sc-navy); text-decoration:underline; text-decoration-thickness:1px; text-underline-offset:3px; }
  .ck-note-ts { font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); }
  .ck-note-author { color:var(--sc-text-dim); }
  .ck-note-pills { display:inline-flex; gap:6px; margin-left:auto; flex-wrap:wrap; }
  .ck-note-body { font-family:var(--sc-serif); font-size:14px; line-height:1.5; color:var(--sc-text); white-space:pre-wrap; }
  .ck-mark { background:#fff5d6; padding:0 2px; border-radius:1px; }

  /* Data table cells — utility classes that replace the ~1200
   * hand-rolled inline-styled <td> attrs across data_public/.
   * Use ck_data_cell() to emit cells; or apply classes directly
   * for one-off cases. The cycle-22 lift consolidates these so
   * future cycles can mechanically migrate inline-styled tables. */
  .ck-cell { padding:5px 10px; font-size:11px; color:var(--sc-text); }
  .ck-cell-mono { font-family:var(--sc-mono); font-variant-numeric:tabular-nums; }
  .ck-cell-r { text-align:right; }
  .ck-cell-c { text-align:center; }
  .ck-cell.tone-dim { color:var(--sc-text-dim); }
  .ck-cell.tone-pos { color:var(--sc-positive); }
  .ck-cell.tone-neg { color:var(--sc-negative); }
  .ck-cell.tone-acc { color:var(--sc-teal-ink); }
  .ck-cell-w-600 { font-weight:600; }
  .ck-cell-w-700 { font-weight:700; }

  /* Page-header chrome — replaces the per-page page-wrapper that
   * data_public pages used to roll by hand with an inline-styled
   * padded container, a margin-bottom header block, an 18px/700 title,
   * and a 12px subtitle. Cycle 31 migration replaces those inline
   * styles with these utility classes. ~500 inline-style instances
   * eliminated. (Example tags kept out of this comment so they never
   * ship as literal markup inside the served stylesheet.) */
  .ck-page-wrap { padding:20px; max-width:min(1920px, 95vw); margin:0 auto; }
  .ck-page-head { margin-bottom:20px; }
  .ck-page-h1 { font-size:18px; font-weight:700; color:var(--sc-text); letter-spacing:0.02em; }
  .ck-page-sub { font-size:12px; color:var(--sc-text-dim); margin-top:4px; }

  /* Data-table chrome — wraps the second-most-common inline-style
   * cluster (cycle 27): the <table>+<thead>+<tbody> container with
   * scroll-wrapper + alternating row backgrounds. Use ck_data_table
   * to compose the chrome around ck_data_cell rows. */
  .ck-data-table-scroll { overflow-x:auto; margin-top:12px; }
  .ck-data-table { width:100%; border-collapse:collapse; font-size:11px; }
  .ck-data-table thead tr { background:var(--sc-bone); }
  .ck-data-table tbody tr:nth-child(even) { background:var(--sc-panel-alt, #ece5d6); }
  .ck-data-table-head { padding:6px 10px; border-bottom:1px solid var(--sc-rule); font-size:10px; color:var(--sc-text-dim); letter-spacing:0.05em; font-weight:600; text-transform:uppercase; }

  /* Personal dashboard /my/<owner> — pulse strip uses the existing
   * ck-kpi-grid; health-mix bar is the only bespoke chrome. */
  .ck-pulse-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:0; border-top:1px solid var(--sc-rule); }
  .ck-pulse-grid .ck-kpi { padding:14px 18px; border-right:1px solid var(--sc-rule); }
  .ck-pulse-grid .ck-kpi:last-child { border-right:0; }
  .ck-pulse-grid .ck-kpi-value .neg { color:var(--sc-negative); }
  .ck-pulse-grid .ck-kpi-value .warn { color:var(--sc-warning); }
  /* 2026-05-28 sweep · .ck-health-mix shadow removed.
     Depth-by-paper-tone same as .ck-panel. */
  .ck-health-mix { background:#fff; border:1px solid var(--sc-rule); border-radius:2px; margin:0 0 var(--sc-s-5); padding:18px; }
  .ck-health-mix-head { display:flex; align-items:baseline; justify-content:space-between; gap:var(--sc-s-4); margin-bottom:14px; }
  .ck-health-mix-head h3 { font-family:var(--sc-sans); font-weight:700; font-size:13px; letter-spacing:0.12em; text-transform:uppercase; color:var(--sc-navy); margin:0; }
  .ck-health-mix-head .count { font-family:var(--sc-mono); font-size:13px; color:var(--sc-text-faint); }
  .ck-health-bar { display:flex; height:18px; border-radius:2px; overflow:hidden; border:1px solid var(--sc-rule); margin-bottom:10px; }
  .ck-health-bar .seg.green { background:var(--sc-positive); }
  .ck-health-bar .seg.amber { background:var(--sc-warning); }
  .ck-health-bar .seg.red   { background:var(--sc-negative); }
  .ck-health-legend { display:flex; gap:18px; font-family:var(--sc-mono); font-size:11px; letter-spacing:0.06em; }
  .ck-health-legend .lg.green { color:var(--sc-positive); }
  .ck-health-legend .lg.amber { color:var(--sc-warning); }
  .ck-health-legend .lg.red   { color:var(--sc-negative); }
  .ck-health-cell.tone-positive { color:var(--sc-positive); font-weight:700; }
  .ck-health-cell.tone-warning  { color:var(--sc-warning); font-weight:700; }
  .ck-health-cell.tone-negative { color:var(--sc-negative); font-weight:700; }
  .ck-health-cell.tone-neutral  { color:var(--sc-text-faint); font-weight:600; }
  .ck-health-cell.faint { color:var(--sc-text-faint); }
  .ck-deal-link { color:var(--sc-teal-ink); font-weight:600; text-decoration:none; }
  .ck-deal-link:hover { color:var(--sc-navy); text-decoration:underline; text-decoration-thickness:1px; text-underline-offset:3px; }

  /* Research grid — one editorial card per research entry. Pairs
   * with the Insights triplet on /research. */
  .ck-research-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)); gap:var(--sc-s-6) var(--sc-s-7); margin:0 0 var(--sc-s-6); }
  .ck-research-card { display:flex; flex-direction:column; gap:var(--sc-s-3); padding:0 0 var(--sc-s-5); border-bottom:1px solid var(--sc-rule); }
  .ck-research-card .ck-eyebrow { margin-bottom:var(--sc-s-2); }
  .ck-research-card-title { font-family:var(--sc-serif); font-weight:500; font-size:22px; line-height:1.2; margin:0; color:var(--sc-navy); }
  .ck-research-card-title a { color:inherit; text-decoration:none; transition:color 0.15s; }
  .ck-research-card-title a:hover { color:var(--sc-teal-ink); }
  .ck-research-card-body { font-family:var(--sc-serif); font-size:15px; line-height:1.55; color:var(--sc-text-dim); margin:0; max-width:48ch; }

  /* Command palette */
  .ck-palette { position:fixed; inset:0; background:rgba(6,22,38,0.4); display:flex; align-items:flex-start; justify-content:center; padding-top:12vh; z-index:100; }
  .ck-palette[hidden] { display:none; }
  .ck-palette-box { width:min(680px, 92vw); background:#fff; border:1px solid var(--sc-rule); box-shadow:var(--sc-shadow-3); border-radius:2px; }
  .ck-palette-input { width:100%; padding:16px 20px; font-family:var(--sc-serif); font-size:18px; border:0; border-bottom:1px solid var(--sc-rule); outline:none; }
  .ck-palette-list { list-style:none; margin:0; padding:0; max-height:52vh; overflow:auto; }
  .ck-palette-list li { display:flex; justify-content:space-between; padding:10px 20px; font-size:13px; cursor:pointer; border-bottom:1px solid var(--sc-bone); }
  .ck-palette-list li:hover { background:var(--sc-bone); }
  .ck-palette-list li.is-highlighted {
    background:var(--sc-bone);
    box-shadow:inset 3px 0 0 var(--sc-teal-ink);
  }
  .ck-palette-list li.is-highlighted .cp-route { color:var(--sc-teal-ink); }
  .ck-palette-list li.cp-noresults {
    display:flex; justify-content:flex-start; padding:18px 20px;
    font-family:var(--sc-serif); font-size:13px;
    color:var(--sc-text-dim); cursor:default;
    background:var(--sc-bone);
  }
  .ck-palette-list li.cp-noresults:hover { background:var(--sc-bone); }
  .ck-palette-list li.cp-noresults em {
    font-style:italic; color:var(--sc-teal-ink);
  }
  .ck-palette-list li.cp-noresults kbd {
    display:inline-block; padding:1px 5px;
    background:#fff; border:1px solid var(--sc-rule);
    border-radius:2px; font-family:var(--sc-mono);
    font-size:10px; color:var(--sc-text);
    vertical-align:1px;
  }
  .ck-palette-list li.cp-noresults[hidden] { display:none !important; }
  .ck-palette-list li.cp-section { display:block; padding:10px 20px 6px; cursor:default; background:transparent; border-bottom:0; font-family:var(--sc-mono); font-size:10px; font-weight:700; letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-text-faint); }
  .ck-palette-list li.cp-section:hover { background:transparent; }
  .ck-palette-list li.cp-recent { background:linear-gradient(90deg, rgba(21,87,82,0.04) 0%, transparent 100%); }
  .ck-palette-list li.cp-recent:hover { background:var(--sc-bone); }
  .cp-route { font-family:var(--sc-mono); font-size:11px; color:var(--sc-text-faint); }

  /* Toast / flash notifications — bottom-right slide-in stack */
  .ck-toast-host { position:fixed; bottom:24px; right:24px; display:flex; flex-direction:column; gap:10px; z-index:120; pointer-events:none; max-width:380px; }
  .ck-toast { pointer-events:auto; display:flex; align-items:center; gap:14px; padding:13px 18px; background:#fff; border:1px solid var(--sc-rule); border-left:3px solid var(--sc-teal); border-radius:2px; box-shadow:var(--sc-shadow-2); font-family:var(--sc-sans); font-size:13.5px; color:var(--sc-text); transform:translateX(20px); opacity:0; transition:transform 0.22s ease-out, opacity 0.22s ease-out; }
  .ck-toast.ck-toast-show { transform:translateX(0); opacity:1; }
  .ck-toast-success { border-left-color:var(--sc-positive); }
  .ck-toast-info    { border-left-color:var(--sc-teal); }
  .ck-toast-warning { border-left-color:var(--sc-warning); }
  .ck-toast-error   { border-left-color:var(--sc-negative); }
  .ck-toast-close { margin-left:auto; flex-shrink:0; width:22px; height:22px; padding:0; background:transparent; border:0; color:var(--sc-text-faint); font-size:16px; line-height:1; cursor:pointer; border-radius:50%; }
  .ck-toast-close:hover { background:var(--sc-bone); color:var(--sc-navy); }

  /* Keyboard shortcut help dialog (press ?) */
  .ck-shortcuts { position:fixed; inset:0; background:rgba(11,35,65,0.45); display:flex; align-items:flex-start; justify-content:center; padding-top:10vh; z-index:110; }
  .ck-shortcuts[hidden] { display:none; }
  .ck-shortcuts-box { width:min(540px, 92vw); background:#fff; border:1px solid var(--sc-rule); box-shadow:var(--sc-shadow-3); border-radius:2px; max-height:80vh; overflow:auto; }
  .ck-shortcuts-head { display:flex; align-items:baseline; gap:14px; padding:18px 22px 10px; border-bottom:1px solid var(--sc-rule); position:relative; }
  .ck-shortcuts-eyebrow { font-family:var(--sc-mono); font-size:11px; font-weight:700; letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-teal-ink, var(--sc-teal)); }
  .ck-shortcuts-title { font-family:var(--sc-serif); font-weight:500; font-size:24px; color:var(--sc-navy); margin:0; letter-spacing:-0.01em; }
  .ck-shortcuts-close { position:absolute; top:14px; right:14px; width:28px; height:28px; border:0; background:transparent; font-size:22px; line-height:1; color:var(--sc-text-faint); cursor:pointer; border-radius:50%; }
  .ck-shortcuts-close:hover { background:var(--sc-bone); color:var(--sc-navy); }
  .ck-shortcuts-body { padding:18px 22px 22px; display:grid; gap:18px; }
  .ck-shortcuts-body section h3 { font-family:var(--sc-mono); font-size:11px; font-weight:700; letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-text-dim); margin:0 0 8px; }
  .ck-shortcuts-body dl { display:grid; grid-template-columns:max-content 1fr; gap:6px 16px; margin:0; }
  .ck-shortcuts-body dt { display:flex; align-items:center; gap:4px; font-family:var(--sc-sans); font-size:12px; color:var(--sc-text-dim); }
  .ck-shortcuts-body dd { font-family:var(--sc-serif); font-size:13.5px; line-height:1.45; color:var(--sc-text); margin:0; }
  .ck-shortcuts-body kbd { display:inline-block; padding:2px 7px; background:var(--sc-bone); border:1px solid var(--sc-rule); border-bottom-width:2px; border-radius:3px; font-family:var(--sc-mono); font-size:11px; font-weight:600; color:var(--sc-navy); min-width:14px; text-align:center; }

  /* Main content frame */
  .ck-main { padding:var(--sc-s-7); max-width:min(1920px, 95vw); margin:0 auto; }

  /* Print preview mode — partners hit ?print=1 to see the LP-facing
   * deliverable before they print. Hides shell chrome inside the
   * wrapper so the page reads exactly like the print pathway. */
  .ck-print-preview {
    max-width: 880px; margin: 0 auto; padding: 32px 24px;
    background: #fff;
    box-shadow: 0 0 0 1px var(--sc-rule, #d8d3c8),
                0 8px 28px rgba(11, 35, 65, 0.08);
  }
  .ck-print-preview-bar {
    display: flex; align-items: baseline;
    justify-content: space-between; gap: 14px;
    padding: 8px 14px; margin: -32px -24px 24px;
    background: var(--sc-bone, #f2ede3);
    border-bottom: 1px solid var(--sc-rule, #d8d3c8);
    font-family: "Inter Tight", sans-serif;
    font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase;
  }
  .ck-print-preview-meta {
    color: var(--sc-text-faint, #6e7787); font-weight: 700;
  }
  .ck-print-preview-exit {
    color: var(--sc-teal-ink, #0e3e3a); text-decoration: none;
    border-bottom: 1px solid transparent;
    transition: border-color 120ms ease;
  }
  .ck-print-preview-exit:hover {
    border-bottom-color: var(--sc-teal-ink, #0e3e3a);
  }
  .ck-print-preview-cta {
    text-align: right; margin: 0 0 12px;
    font-family: "Source Serif 4", serif; font-style: italic;
    font-size: 13px;
  }
  @media print {
    .ck-print-preview-bar { display: none; }
    .ck-print-preview-cta { display: none; }
    .ck-print-preview {
      max-width: none; margin: 0; padding: 0; box-shadow: none;
    }
  }

  /* Print — for /memo/<id>, /ic-packet/<id>. Partners save these as
   * PDFs to share with LPs / IC; the editorial layout should survive
   * the print path with chrome stripped, panels kept whole, and the
   * cadence headings staying with their following body copy. */
  @media print {
    .ck-topbar, .ck-breadcrumbs, .ck-palette,
    .ck-sidebar, .ck-toast, .no-print { display:none !important; }
    body { background:#fff !important; color:#000 !important;
           font-size:11pt; }
    a { color:inherit !important; text-decoration:none !important; }
    .ck-panel { box-shadow:none; break-inside:avoid;
                page-break-inside:avoid;
                border:1px solid #cfcec7; }
    .ck-panel-head { background:#f2ede3 !important;
                     color:#0b2341 !important; }
    .ck-section-intro, .ck-section-header,
    .ck-kpi-strip { break-inside:avoid; page-break-inside:avoid; }
    h1, h2, h3 { break-after:avoid; page-break-after:avoid; }
    .ck-main { max-width:none; padding:0; }
    /* Legacy cad-* chrome hide for pages still on the legacy shell */
    .cad-nav, .cad-topbar, .cad-ticker { display:none !important; }
  }

  /* ---- Claude Design handoff primitives ---- */
  /* DataPanel — bordered surface, navy header w/ mono code + LIVE badge */
  .ck-data-panel { background:#fff; border:1px solid var(--sc-rule);
    border-radius:2px; margin:0 0 var(--sc-s-5); }
  .ck-data-panel-head { background:var(--sc-navy); color:var(--sc-on-navy);
    padding:9px 14px; display:flex; align-items:center; gap:10px;
    font-family:var(--sc-mono); font-size:10.5px; letter-spacing:0.14em;
    text-transform:uppercase; }
  .ck-data-panel-code { color:var(--sc-teal-2); font-weight:700; flex:0 0 auto; }
  .ck-data-panel-title { color:var(--sc-on-navy); flex:1 1 auto; min-width:0;
    overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .ck-data-panel-live { color:var(--sc-on-navy-faint); font-size:9px; flex:0 0 auto; }
  .ck-data-panel-body { padding:14px; }

  /* BarRow — label / value / proportional bar / pct */
  .ck-bar-row { display:grid; grid-template-columns:120px 48px 1fr 56px;
    gap:10px; align-items:center; padding:5px 0; font-size:12px;
    font-family:var(--sc-mono); font-variant-numeric:tabular-nums; }
  .ck-bar-row-label { color:var(--sc-text-dim); overflow:hidden;
    text-overflow:ellipsis; white-space:nowrap; }
  .ck-bar-row-value { text-align:right; color:var(--sc-text); font-weight:600; }
  .ck-bar-row-track { height:5px; background:var(--sc-bone); position:relative; }
  .ck-bar-row-fill { position:absolute; left:0; top:0; bottom:0; }
  .ck-bar-row-pct { text-align:right; color:var(--sc-text-faint); font-size:11px; }

  /* Value-anchor band — headline metric + benchmark delta / $ opportunity / target */
  .ck-value-anchor { display:flex; flex-wrap:wrap; align-items:center;
    justify-content:space-between; gap:var(--sc-s-5); margin-bottom:var(--sc-s-5);
    padding:14px 18px; background:var(--sc-bone);
    border:1px solid var(--sc-rule); border-left:3px solid var(--ck-va-tone, var(--sc-teal)); }
  .ck-va-head { display:flex; flex-direction:column; gap:4px; min-width:0; }
  .ck-va-eyebrow { font-family:var(--sc-mono); font-size:10px; letter-spacing:0.12em;
    text-transform:uppercase; color:var(--sc-text-dim); }
  .ck-va-value { font-family:var(--sc-serif); font-weight:600; font-size:26px;
    line-height:1; color:var(--sc-text); font-variant-numeric:tabular-nums; }
  .ck-va-facts { display:flex; flex-wrap:wrap; gap:var(--sc-s-6);
    align-items:flex-end; }
  .ck-va-fact { display:flex; flex-direction:column; gap:4px; }
  .ck-va-fact-label { font-family:var(--sc-mono); font-size:9.5px; letter-spacing:0.1em;
    text-transform:uppercase; color:var(--sc-text-faint); }
  .ck-va-fact-value { font-family:var(--sc-mono); font-size:13px; font-weight:600;
    color:var(--sc-text); font-variant-numeric:tabular-nums; }
  .ck-va-fact-hero .ck-va-fact-value { font-size:18px; font-weight:700; }

  /* Paired viz + dataset — the signature block (chart left, data right) */
  .ck-pair { display:grid; grid-template-columns:1.4fr 1fr; gap:0;
    background:#fff; border:1px solid var(--sc-rule-2); margin:var(--sc-s-5) 0; }
  .ck-pair-viz { padding:var(--sc-s-7); border-right:1px solid var(--sc-rule); }
  .ck-pair-data { background:var(--sc-parchment); }
  .ck-pair-data-h { padding:14px 20px; border-bottom:1px solid var(--sc-rule);
    font-family:var(--sc-sans); font-size:10.5px; font-weight:700;
    letter-spacing:0.14em; text-transform:uppercase; color:var(--sc-text-dim);
    display:flex; justify-content:space-between; align-items:center; }
  .ck-pair-src { font-family:var(--sc-mono); text-transform:none;
    letter-spacing:0; color:var(--sc-teal-ink); font-size:11px; }
  .ck-pair table { width:100%; border-collapse:collapse;
    font-family:var(--sc-mono); font-size:12.5px; }
  .ck-pair th { text-align:left; padding:8px 20px; color:var(--sc-text-faint);
    font-weight:600; font-size:9.5px; letter-spacing:0.12em;
    text-transform:uppercase; border-bottom:1px solid var(--sc-rule);
    font-family:var(--sc-sans); }
  .ck-pair td { padding:8px 20px; border-bottom:1px solid var(--sc-rule);
    color:var(--sc-text); font-variant-numeric:tabular-nums; }
  .ck-pair tr:last-child td { border-bottom:none; }
  .ck-pair th.ck-pair-r, .ck-pair td.ck-pair-r { text-align:right; }
  .ck-pair td.ck-pair-lbl { color:var(--sc-text-dim);
    font-family:var(--sc-sans); font-size:13px; }
  .ck-pair tr.ck-pair-hot td { background:var(--sc-bone); }
  .ck-pair tr.ck-pair-hot td:first-child { border-left:2px solid var(--sc-warning); }
  @media (max-width:1100px) {
    .ck-pair { grid-template-columns:1fr; }
    .ck-pair-viz { border-right:none; border-bottom:1px solid var(--sc-rule); }
  }
</style>
"""

_CSRF_JS = """
<script>
/* CSRF token patcher — reads rcm_csrf cookie and:
 *   1. Injects csrf_token hidden input into every POST form
 *   2. Sets X-CSRF-Token header on every non-GET fetch()
 * Without this, every "Acknowledge alert", "Save note", "Create deal",
 * etc. fails silently with 403. Drop-in safe — harmless if cookie absent.
 */
(function(){
  function c(n){var m=document.cookie.match(new RegExp('(?:^|; )'+n+'=([^;]*)'));
    return m?decodeURIComponent(m[1]):null;}
  document.addEventListener('submit',function(e){
    var t=c('rcm_csrf');if(!t)return;
    var f=e.target;if(!f||f.tagName!=='FORM')return;
    if(f.method&&f.method.toLowerCase()!=='post')return;
    var x=f.querySelector('input[name=csrf_token]');
    if(!x){x=document.createElement('input');x.type='hidden';
      x.name='csrf_token';f.appendChild(x);}
    x.value=t;
  },true);
  var of=window.fetch;
  if(of){window.fetch=function(u,o){
    o=o||{};var t=c('rcm_csrf');
    if(t&&o.method&&o.method.toUpperCase()!=='GET'){
      o.headers=o.headers||{};
      if(!o.headers['X-CSRF-Token'])o.headers['X-CSRF-Token']=t;
    }
    return of(u,o);
  };}
})();
</script>
"""


_TOAST_HTML = """
<div class="ck-toast-host" id="ck-toast-host" aria-live="polite"></div>
"""


# ── PEdesk Guide sidebar (read-only) ─────────────────────────────────
# Closed-by-default right-side panel. Explains the current page from the
# GuideContextPacket (/api/guide/context) and asks read-only questions via
# the local-Ollama endpoint (/api/guide/ask). No uploads, no actions, no
# mutation, no persistence — the deterministic page guide always works;
# Q&A is gated on /api/guide/ollama-health.
_GUIDE_PANEL_HTML = """
<aside id="ck-guide-panel" class="ck-guide-panel" hidden role="dialog"
       aria-modal="false" aria-label="PEdesk Guide">
  <header class="ck-guide-head">
    <span class="ck-guide-eyebrow">PEdesk Guide</span>
    <h2 class="ck-guide-title" data-ck-guide-page-title tabindex="-1">PEdesk Guide</h2>
    <div class="ck-guide-meta">
      <span class="ck-guide-ctx-badge" data-ck-guide-quality hidden>
        <span class="ck-guide-ctx-dot"></span><span data-ck-guide-quality-label></span>
      </span>
      <span class="ck-guide-meta-sep" data-ck-guide-meta-sep hidden>&middot;</span>
      <code class="ck-guide-route" data-ck-guide-route></code>
    </div>
    <button class="ck-guide-close" type="button" data-ck-guide-close
            aria-label="Close PEdesk Guide">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M18 6L6 18M6 6l12 12"/></svg>
    </button>
  </header>
  <div class="ck-guide-tabs" role="tablist" aria-label="PEdesk Guide sections">
    <button class="ck-guide-tab" role="tab" id="ck-guide-tab-overview"
            aria-controls="ck-guide-panel-overview" aria-selected="true"
            data-ck-guide-tab="overview" type="button" tabindex="0">Overview</button>
    <button class="ck-guide-tab" role="tab" id="ck-guide-tab-metrics"
            aria-controls="ck-guide-panel-metrics" aria-selected="false"
            data-ck-guide-tab="metrics" type="button" tabindex="-1">Metrics<span
            class="ck-guide-count" data-ck-guide-count-metrics hidden></span></button>
    <button class="ck-guide-tab" role="tab" id="ck-guide-tab-sources"
            aria-controls="ck-guide-panel-sources" aria-selected="false"
            data-ck-guide-tab="sources" type="button" tabindex="-1">Sources<span
            class="ck-guide-count" data-ck-guide-count-sources hidden></span></button>
    <button class="ck-guide-tab" role="tab" id="ck-guide-tab-ask"
            aria-controls="ck-guide-panel-ask" aria-selected="false"
            data-ck-guide-tab="ask" type="button" tabindex="-1">Ask</button>
  </div>
  <div class="ck-guide-body">
    <p class="ck-guide-loading" data-ck-guide-loading>Loading page context&hellip;</p>
    <div class="ck-guide-error" data-ck-guide-error hidden>
      <p data-ck-guide-error-msg>Couldn&rsquo;t load page context.</p>
      <button type="button" class="ck-guide-btn" data-ck-guide-retry-context>Retry</button>
    </div>
    <div class="ck-guide-content" data-ck-guide-content hidden>
      <section class="ck-guide-tabpanel" role="tabpanel" id="ck-guide-panel-overview"
               aria-labelledby="ck-guide-tab-overview" data-ck-guide-panel="overview"
               tabindex="0">
        <div data-ck-guide-overview></div>
        <div class="ck-guide-caveat" data-ck-guide-caveat hidden>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2" aria-hidden="true"><path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/></svg>
          <div data-ck-guide-caveat-text></div>
        </div>
        <div class="ck-guide-kicker">Try asking<span class="ck-guide-rule-line"></span></div>
        <div class="ck-guide-chips" data-ck-guide-suggested-overview></div>
      </section>
      <section class="ck-guide-tabpanel" role="tabpanel" id="ck-guide-panel-metrics"
               aria-labelledby="ck-guide-tab-metrics" data-ck-guide-panel="metrics"
               tabindex="0" hidden>
        <div data-ck-guide-metrics></div>
      </section>
      <section class="ck-guide-tabpanel" role="tabpanel" id="ck-guide-panel-sources"
               aria-labelledby="ck-guide-tab-sources" data-ck-guide-panel="sources"
               tabindex="0" hidden>
        <div data-ck-guide-sources></div>
      </section>
      <section class="ck-guide-tabpanel" role="tabpanel" id="ck-guide-panel-ask"
               aria-labelledby="ck-guide-tab-ask" data-ck-guide-panel="ask"
               tabindex="0" hidden>
        <p class="ck-guide-ask-intro">Ask anything about this page. The model is
          grounded in the local guide, metric registry, and data source registry.</p>
        <div class="ck-guide-ask-state" data-ck-guide-ask-state hidden></div>
        <div class="ck-guide-history" data-ck-guide-history aria-live="polite"></div>
        <div class="ck-guide-kicker">Suggestions<span class="ck-guide-rule-line"></span></div>
        <div class="ck-guide-chips" data-ck-guide-suggested-ask></div>
        <details class="ck-guide-policy">
          <summary class="ck-guide-policy-summary">PEdesk Guide is read-only</summary>
          <p class="ck-guide-muted">It can explain pages, metrics, data sources,
            model intent, and limitations. It cannot change assumptions, run
            models, create tasks, export files, or make final investment
            recommendations.</p>
        </details>
      </section>
    </div>
  </div>
  <form class="ck-guide-composer" data-ck-guide-ask-form>
    <div class="ck-guide-composer-row">
      <textarea class="ck-guide-input" data-ck-guide-input rows="1"
                aria-label="Ask a question about this page"
                placeholder="Ask about this page&hellip;"></textarea>
      <button type="submit" class="ck-guide-ask-btn" data-ck-guide-send>Ask
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2" aria-hidden="true"><path d="M5 12h14M13 5l7 7-7 7"/></svg>
      </button>
    </div>
    <div class="ck-guide-foot">
      <span>PEdesk &middot; read-only</span>
      <span class="ck-guide-foot-right">
        <span class="ck-guide-rag" data-ck-guide-rag-status></span>
        <span data-ck-guide-model></span>
      </span>
    </div>
  </form>
</aside>
"""

_GUIDE_CSS = """
<style>
/* PEdesk Guide — "Variant B" tabbed sidebar (design handoff). Editorial
   hierarchy: Source Serif 4 headlines, Inter Tight body, JetBrains Mono
   labels/meta — all already loaded by the shell, so NO external/Google
   font is added here. Tokens + component anatomy are scoped to the panel
   so the main app typography/theme is untouched. */
/* NOTE: the Guide TRIGGER button is styled by the paper-topbar block
   (.ck-guide-trigger near the .ck-topbar rules) — ink text + green "?" glyph,
   visible on the paper bar. The earlier white-on-navy override that lived here
   washed the button out against the paper topbar and has been removed; only
   the Guide PANEL styles remain below. */
.ck-guide-panel{
  --ck-g-navy:#0d2336;--ck-g-cream:#f4ecd9;--ck-g-cream2:#efe5cc;--ck-g-cream3:#e8dab8;
  --ck-g-paper:#fbf7ee;--ck-g-ink:#15202b;--ck-g-ink2:#2a3a4a;--ck-g-muted:#6a7480;
  --ck-g-muted2:#8b94a0;--ck-g-rule:#d9cfb8;--ck-g-rule-soft:#e6dec8;--ck-g-green:#1f7a5a;
  --ck-g-green2:#2e8c6c;--ck-g-amber:#c2853a;--ck-g-amber-soft:#f3e2bc;--ck-g-mint:#6ed3a8;
  --ck-g-serif:'Source Serif 4',Georgia,serif;
  --ck-g-sans:'Inter Tight',Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  --ck-g-mono:'JetBrains Mono',ui-monospace,monospace;
  position:fixed;top:16px;right:16px;bottom:16px;width:min(440px,94vw);z-index:1200;
  background:var(--ck-g-paper);color:var(--ck-g-ink);border:1px solid rgba(0,0,0,.06);
  border-radius:14px;overflow:hidden;
  box-shadow:0 24px 60px rgba(0,0,0,.18),0 2px 0 rgba(0,0,0,.06);
  display:flex;flex-direction:column;font-family:var(--ck-g-sans);font-size:14px;line-height:1.5;}
.ck-guide-panel[hidden]{display:none;}
/* Layout safety: long answers / unbroken tokens (URLs, ids) must wrap,
   never force horizontal overflow. */
.ck-guide-panel,.ck-guide-panel *{overflow-wrap:break-word;word-break:break-word;max-width:100%;}
/* HEADER (navy) */
.ck-guide-head{background:var(--ck-g-navy);color:#e7eef5;padding:18px 22px 14px;position:relative;}
.ck-guide-eyebrow{display:block;font-family:var(--ck-g-mono);font-size:10.5px;letter-spacing:.14em;
  text-transform:uppercase;color:#8aa8c4;margin-bottom:8px;}
.ck-guide-title{font-family:var(--ck-g-serif);font-weight:500;font-size:26px;line-height:1.15;
  letter-spacing:-.01em;margin:0 0 12px;color:#fbf7ee;outline:none;}
.ck-guide-meta{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
  font-family:var(--ck-g-mono);font-size:11px;color:#b9c7d5;}
.ck-guide-route{font-family:var(--ck-g-mono);font-size:11px;color:#b9c7d5;opacity:.85;overflow-wrap:anywhere;}
.ck-guide-ctx-badge{display:inline-flex;align-items:center;gap:6px;background:rgba(46,140,108,.22);
  color:#6ed3a8;border:1px solid rgba(110,211,168,.35);padding:2px 8px;border-radius:999px;
  font-size:10px;letter-spacing:.1em;text-transform:uppercase;font-weight:600;}
.ck-guide-ctx-dot{width:6px;height:6px;border-radius:50%;background:#6ed3a8;
  box-shadow:0 0 0 3px rgba(110,211,168,.22);}
.ck-guide-ctx-badge[data-q="partial"]{background:rgba(194,133,58,.20);color:#e0ab63;border-color:rgba(194,133,58,.40);}
.ck-guide-ctx-badge[data-q="partial"] .ck-guide-ctx-dot{background:#e0ab63;box-shadow:0 0 0 3px rgba(194,133,58,.20);}
.ck-guide-ctx-badge[data-q="placeholder"],.ck-guide-ctx-badge[data-q="missing"]{
  background:rgba(255,255,255,.12);color:#c3cedb;border-color:rgba(255,255,255,.22);}
.ck-guide-ctx-badge[data-q="placeholder"] .ck-guide-ctx-dot,
.ck-guide-ctx-badge[data-q="missing"] .ck-guide-ctx-dot{background:#c3cedb;box-shadow:0 0 0 3px rgba(255,255,255,.12);}
.ck-guide-close{position:absolute;top:14px;right:14px;width:28px;height:28px;border-radius:8px;
  display:grid;place-items:center;color:#8aa8c4;background:transparent;border:1px solid transparent;cursor:pointer;}
.ck-guide-close:hover{background:rgba(255,255,255,.06);color:#fff;}
.ck-guide-close:focus-visible{outline:2px solid var(--ck-g-mint);outline-offset:2px;}
/* TABS (live in the navy block) */
.ck-guide-tabs{display:flex;gap:2px;padding:0 14px;background:var(--ck-g-navy);
  border-bottom:1px solid rgba(255,255,255,.06);}
.ck-guide-tab{appearance:none;border:0;background:transparent;color:#8aa8c4;font-family:var(--ck-g-sans);
  font-size:12.5px;font-weight:500;padding:10px 12px 12px;cursor:pointer;border-bottom:2px solid transparent;
  margin-bottom:-1px;letter-spacing:.01em;}
.ck-guide-tab[aria-selected="true"]{color:#fbf7ee;border-bottom-color:var(--ck-g-mint);}
.ck-guide-tab:focus-visible{outline:2px solid var(--ck-g-mint);outline-offset:-2px;border-radius:3px;}
.ck-guide-count{font-family:var(--ck-g-mono);font-size:10px;color:#6a7c8f;margin-left:4px;}
.ck-guide-tab[aria-selected="true"] .ck-guide-count{color:#b9c7d5;}
/* BODY (paper, scrolls) */
.ck-guide-body{flex:1;overflow-y:auto;overflow-x:hidden;padding:22px 22px 12px;background:var(--ck-g-paper);}
.ck-guide-body::-webkit-scrollbar{width:8px;}
.ck-guide-body::-webkit-scrollbar-thumb{background:var(--ck-g-rule);border-radius:4px;}
.ck-guide-tabpanel[hidden]{display:none;}
.ck-guide-tabpanel:focus-visible{outline:none;}
.ck-guide-loading{color:var(--ck-g-muted);font-style:italic;}
.ck-guide-muted{color:var(--ck-g-muted);}
.ck-guide-panel p{margin:0 0 10px;line-height:1.5;}
.ck-guide-panel p:last-child{margin-bottom:0;}
/* Overview typography */
.ck-guide-lede{font-family:var(--ck-g-serif);font-size:17px;line-height:1.45;color:var(--ck-g-ink);
  margin:0 0 14px;letter-spacing:-.005em;}
.ck-guide-lede em{font-style:italic;color:var(--ck-g-ink2);}
.ck-guide-p{margin:0 0 10px;color:var(--ck-g-ink2);}
.ck-guide-p:last-child{margin-bottom:0;}
.ck-guide-sub{margin:0 0 12px;}
.ck-guide-sub:last-child{margin-bottom:0;}
.ck-guide-sub-label{display:block;font-family:var(--ck-g-mono);font-size:10.5px;letter-spacing:.12em;
  text-transform:uppercase;color:var(--ck-g-muted);font-weight:500;margin-bottom:4px;}
.ck-guide-sub-body{color:var(--ck-g-ink2);line-height:1.5;}
.ck-guide-sub code{font-family:var(--ck-g-mono);font-size:12.5px;color:var(--ck-g-green);}
/* Caveat callout */
.ck-guide-caveat{background:var(--ck-g-amber-soft);border-left:3px solid var(--ck-g-amber);
  padding:10px 12px;color:#4a3210;font-size:13px;border-radius:0 6px 6px 0;
  display:flex;gap:10px;align-items:flex-start;margin:0 0 18px;}
.ck-guide-caveat svg{flex:0 0 14px;margin-top:2px;color:var(--ck-g-amber);}
.ck-guide-caveat b{color:#7a5418;}
/* Kicker (label + rule line) */
.ck-guide-kicker{font-family:var(--ck-g-mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--ck-g-muted);margin-bottom:10px;display:flex;align-items:baseline;gap:8px;}
.ck-guide-rule-line{flex:1;height:1px;background:var(--ck-g-rule);transform:translateY(-3px);}
/* Metric */
.ck-guide-metric{margin-bottom:20px;}
.ck-guide-metric:last-child{margin-bottom:0;}
.ck-guide-metric-head{display:grid;grid-template-columns:1fr auto;align-items:baseline;gap:6px 14px;margin-bottom:8px;}
.ck-guide-metric-name{font-family:var(--ck-g-serif);font-size:22px;font-weight:500;letter-spacing:-.01em;color:var(--ck-g-ink);}
.ck-guide-metric-formula{font-family:var(--ck-g-mono);font-size:12px;color:var(--ck-g-green);
  background:rgba(31,122,90,.07);padding:3px 8px;border-radius:6px;}
.ck-guide-metric-pill{font-family:var(--ck-g-mono);font-size:10.5px;color:var(--ck-g-muted);
  background:var(--ck-g-cream2);padding:3px 8px;border-radius:6px;}
.ck-guide-metric-desc{color:var(--ck-g-ink2);font-size:14px;margin:0 0 6px;}
.ck-guide-metric-why{color:var(--ck-g-muted);font-size:13px;border-left:2px solid var(--ck-g-rule);
  padding-left:10px;margin:0;}
.ck-guide-metric-cav{color:var(--ck-g-amber);font-size:12px;margin-top:6px;}
/* Data source row */
.ck-guide-ds{display:grid;grid-template-columns:auto 1fr;column-gap:12px;row-gap:4px;
  padding:12px 0;border-top:1px dashed var(--ck-g-rule);}
.ck-guide-ds:first-child{border-top:0;padding-top:4px;}
.ck-guide-ds-gem{width:8px;height:8px;background:var(--ck-g-green);transform:rotate(45deg);margin-top:8px;}
.ck-guide-ds-name{font-weight:600;color:var(--ck-g-ink);font-size:14px;}
.ck-guide-ds-meta{grid-column:2;font-family:var(--ck-g-mono);font-size:11px;color:var(--ck-g-muted);letter-spacing:.02em;}
.ck-guide-ds-meta b{color:var(--ck-g-ink2);font-weight:500;}
.ck-guide-ds-desc{grid-column:2;color:var(--ck-g-ink2);font-size:13px;margin-top:4px;}
.ck-guide-ds-lim{grid-column:2;color:var(--ck-g-amber);font-size:12px;margin-top:4px;
  display:flex;gap:6px;align-items:flex-start;}
.ck-guide-ds-lim svg{flex:0 0 12px;margin-top:2px;}
/* Chips */
.ck-guide-chips{display:flex;flex-wrap:wrap;gap:6px;}
.ck-guide-chip{appearance:none;border:1px solid var(--ck-g-rule);background:var(--ck-g-paper);
  color:var(--ck-g-ink2);padding:6px 11px 7px;border-radius:999px;font-size:12.5px;font-family:inherit;
  cursor:pointer;line-height:1.2;text-align:left;transition:background .15s,border-color .15s,color .15s;}
.ck-guide-chip:hover{background:var(--ck-g-cream2);border-color:var(--ck-g-cream3);color:var(--ck-g-ink);}
.ck-guide-chip:focus-visible{outline:2px solid var(--ck-g-green);outline-offset:1px;}
.ck-guide-chip .ck-guide-chip-arr{color:var(--ck-g-muted);margin-left:4px;}
.ck-guide-empty{color:var(--ck-g-muted);font-size:13px;}
.ck-guide-list{margin:0;padding-left:18px;color:var(--ck-g-ink2);}
.ck-guide-list li{margin-bottom:5px;line-height:1.45;}
/* Ask tab */
.ck-guide-ask-intro{color:var(--ck-g-ink2);margin:0 0 16px;}
.ck-guide-ask-state{background:var(--ck-g-amber-soft);border:1px solid var(--ck-g-cream3);border-radius:8px;
  padding:10px 12px;font-size:12.5px;line-height:1.5;color:#4a3210;margin-bottom:14px;}
.ck-guide-state-ready{font-weight:600;color:var(--ck-g-green);font-size:12.5px;letter-spacing:.01em;
  background:var(--ck-g-green-soft,#d6e8df);}
.ck-guide-ask-state .ck-guide-state-ready{display:block;background:transparent;}
.ck-guide-state-primary{font-weight:600;color:var(--ck-g-ink);font-size:14px;}
.ck-guide-state-secondary{margin:3px 0 6px;}
.ck-guide-setup summary{cursor:pointer;font-size:11px;font-weight:600;color:var(--ck-g-green);}
.ck-guide-setup summary:focus-visible{outline:2px solid var(--ck-g-green);outline-offset:2px;}
.ck-guide-setup-pre{background:var(--ck-g-paper);border:1px solid var(--ck-g-rule);border-radius:6px;
  padding:7px 9px;font-family:var(--ck-g-mono);font-size:10.5px;white-space:pre-wrap;margin:6px 0;}
.ck-guide-history{display:flex;flex-direction:column;gap:12px;margin-bottom:16px;}
.ck-guide-history:empty{margin-bottom:0;}
.ck-guide-q{font-family:var(--ck-g-serif);font-weight:500;font-size:18px;color:var(--ck-g-ink);line-height:1.3;}
.ck-guide-a{background:var(--ck-g-paper);border:1px solid var(--ck-g-rule);border-left:3px solid var(--ck-g-green);
  border-radius:0 8px 8px 0;padding:12px 14px;line-height:1.55;margin-top:6px;color:var(--ck-g-ink2);}
/* Parsed-markdown answer body (renderer escapes first, then whitelists tags) */
.ck-guide-a-body p{margin:0 0 9px;}
.ck-guide-a-body p:last-child{margin-bottom:0;}
.ck-guide-a-body ul,.ck-guide-a-body ol{margin:0 0 9px;padding-left:20px;}
.ck-guide-a-body li{margin-bottom:4px;}
.ck-guide-a-body code{font-family:var(--ck-g-mono);font-size:12.5px;background:var(--ck-g-cream2);
  padding:1px 5px;border-radius:4px;color:var(--ck-g-ink);}
.ck-guide-a-body strong{font-weight:700;color:var(--ck-g-ink);}
/* Retrieved-source provenance block under an answer. */
.ck-guide-sources{margin-top:10px;padding-top:9px;border-top:1px solid var(--ck-g-rule-soft);}
.ck-guide-src-head{font-family:var(--ck-g-mono);font-size:10.5px;text-transform:uppercase;letter-spacing:.1em;
  font-weight:500;color:var(--ck-g-muted);margin-bottom:6px;}
.ck-guide-src-group{margin-top:8px;}
.ck-guide-src-group:first-child{margin-top:0;}
.ck-guide-src-list{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:4px;}
.ck-guide-src-item{display:flex;align-items:baseline;gap:7px;font-size:12.5px;line-height:1.4;}
.ck-guide-src-title{font-weight:600;color:var(--ck-g-ink);}
.ck-guide-src-type{display:block;font-family:var(--ck-g-mono);font-size:10px;text-transform:uppercase;
  letter-spacing:.08em;color:var(--ck-g-muted);margin-bottom:3px;}
.ck-guide-src-score{margin-left:auto;font-family:var(--ck-g-mono);font-size:10.5px;color:var(--ck-g-muted);}
.ck-guide-a-meta{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-top:10px;font-size:10px;
  font-family:var(--ck-g-mono);color:var(--ck-g-muted);}
.ck-guide-badge{padding:1px 6px;border-radius:3px;background:var(--ck-g-green);color:#fff;letter-spacing:.05em;}
.ck-guide-copy{margin-left:auto;background:transparent;border:1px solid var(--ck-g-rule);
  border-radius:4px;color:var(--ck-g-muted);font-family:inherit;font-size:10px;
  letter-spacing:.04em;text-transform:uppercase;padding:1px 7px;cursor:pointer;}
.ck-guide-copy:hover{border-color:var(--ck-g-green);color:var(--ck-g-green);}
.ck-guide-copy:focus-visible{outline:2px solid var(--ck-g-green);outline-offset:1px;}
.ck-guide-thinking{font-style:italic;color:var(--ck-g-muted);}
.ck-guide-thinking::after{content:'';animation:ckguidedots 1.2s steps(4,end) infinite;}
@keyframes ckguidedots{0%{content:'';}25%{content:'.';}50%{content:'..';}75%{content:'...';}}
/* Read-only policy — quiet collapsible at the foot of the Ask tab. */
.ck-guide-policy{margin-top:18px;border-top:1px solid var(--ck-g-rule-soft);padding-top:12px;}
.ck-guide-policy-summary{cursor:pointer;font-family:var(--ck-g-mono);font-size:10.5px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--ck-g-muted);font-weight:500;}
.ck-guide-policy[open] .ck-guide-policy-summary{margin-bottom:8px;}
.ck-guide-policy-summary:focus-visible{outline:2px solid var(--ck-g-green);outline-offset:2px;}
/* COMPOSER (cream, sticky footer) */
.ck-guide-composer{border-top:1px solid var(--ck-g-rule);background:var(--ck-g-cream);
  padding:14px 18px 16px;display:flex;flex-direction:column;gap:8px;}
.ck-guide-composer-row{display:grid;grid-template-columns:1fr auto;gap:8px;align-items:stretch;}
.ck-guide-input{width:100%;box-sizing:border-box;appearance:none;border:1px solid var(--ck-g-rule);
  background:var(--ck-g-paper);border-radius:10px;padding:10px 12px;font-family:inherit;font-size:13.5px;
  color:var(--ck-g-ink);resize:none;min-height:42px;}
.ck-guide-input::placeholder{color:var(--ck-g-muted2);}
.ck-guide-input:focus{outline:none;border-color:var(--ck-g-green);box-shadow:0 0 0 3px rgba(31,122,90,.12);}
.ck-guide-input:disabled{opacity:.6;cursor:not-allowed;}
.ck-guide-ask-btn{appearance:none;border:0;background:var(--ck-g-green);color:#fff;padding:0 16px;
  border-radius:10px;font-family:inherit;font-weight:600;font-size:13px;cursor:pointer;
  display:flex;align-items:center;gap:6px;}
.ck-guide-ask-btn:hover{background:var(--ck-g-green2);}
.ck-guide-ask-btn:disabled{opacity:.5;cursor:not-allowed;}
.ck-guide-ask-btn:focus-visible{outline:2px solid var(--ck-g-green);outline-offset:2px;}
.ck-guide-foot{display:flex;justify-content:space-between;align-items:center;font-family:var(--ck-g-mono);
  font-size:10.5px;color:var(--ck-g-muted);letter-spacing:.04em;}
.ck-guide-foot-right{display:flex;gap:10px;}
.ck-guide-foot-right span{display:inline-flex;align-items:center;gap:5px;}
.ck-guide-rag[data-state="ready"]{color:var(--ck-g-green);}
.ck-guide-rag[data-state="thinking"]{color:var(--ck-g-green);}
.ck-guide-rag[data-state="off"]{color:var(--ck-g-muted);}
/* Generic small button (retry, etc.) */
.ck-guide-btn{background:var(--ck-g-green);color:#fff;border:none;border-radius:8px;
  padding:8px 14px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;}
.ck-guide-btn:hover{background:var(--ck-g-green2);}
.ck-guide-btn:disabled{opacity:.5;cursor:not-allowed;}
.ck-guide-btn:focus-visible{outline:2px solid var(--ck-g-green);outline-offset:2px;}
/* Narrow viewports: full-width sheet, square edges. */
@media (max-width:960px){
  .ck-guide-panel{top:0;right:0;bottom:0;width:100vw;border-radius:0;border:none;}
}
@media print{.ck-guide-panel,.ck-guide-trigger{display:none !important;}}
</style>
"""

_GUIDE_JS = """
<script>
/* PEdesk Guide sidebar — read-only. Builds the page guide from
 * /api/guide/context and answers questions via /api/guide/ask. No
 * uploads, no actions, no mutation, no persistence. The global CSRF
 * fetch-patch adds X-CSRF-Token on the POST in authenticated mode. */
(function(){
  var panel=document.getElementById('ck-guide-panel');
  if(!panel) return;
  var $=function(sel){return panel.querySelector(sel);};
  var loadedRoute=null, health=null, lastQuestion=null, lastFocus=null, pending=false;
  /* Stale-response protection: every ask captures reqSeq; close and
   * route-change bump it (and abort the fetch) so a late response with a
   * mismatched seq renders nothing. */
  var reqSeq=0, activeAbort=null, activeTimer=null;

  function esc(s){var d=document.createElement('div');d.textContent=(s==null?'':String(s));return d.innerHTML;}
  function escAttr(s){return esc(s).replace(/"/g,'&quot;').replace(/'/g,'&#39;');}
  function route(){return location.pathname+location.search;}  /* omit hash */
  /* Scrape the live figures the user is looking at so the Guide can analyze
   * the actual on-screen numbers. Captures, in priority order: the page's
   * value-anchor band (the headline metric + benchmark delta / dollar
   * opportunity / target — the load-bearing number on analytic pages), then
   * the .ck-kpi blocks. Read-only: collects visible text only, never
   * page-private data; skips anything inside the Guide panel; bounded to 24
   * (server re-caps and re-sanitizes — this is a convenience, not a trust
   * boundary). */
  function scrapeOnscreen(){
    try{
      var panel=document.getElementById('ck-guide-panel');
      var out=[], seen={};
      var clean=function(s){return (s||'').replace(/\\s+/g,' ').trim();};
      var push=function(label,value){
        label=clean(label); value=clean(value);
        if(!label||!value)return;
        var key=label+'\\u0001'+value;
        if(seen[key])return;                                 /* de-dupe repeats */
        seen[key]=1;
        out.push({label:label.slice(0,80), value:value.slice(0,60)});
      };
      /* Value-anchor band first — it's the page's headline number. */
      var anchors=document.querySelectorAll('.ck-value-anchor');
      for(var a=0;a<anchors.length && out.length<24;a++){
        var an=anchors[a];
        if(panel && panel.contains(an))continue;
        var eyebrow=clean((an.querySelector('.ck-va-eyebrow')||{}).textContent);
        push(eyebrow||'Headline', (an.querySelector('.ck-va-value')||{}).textContent);
        var facts=an.querySelectorAll('.ck-va-fact');
        for(var f=0;f<facts.length && out.length<24;f++){
          var fl=clean((facts[f].querySelector('.ck-va-fact-label')||{}).textContent);
          var fv=(facts[f].querySelector('.ck-va-fact-value')||{}).textContent;
          push((eyebrow?eyebrow+' \\u2014 ':'')+(fl||'fact'), fv);
        }
      }
      /* Then the KPI blocks. */
      var kpis=document.querySelectorAll('.ck-kpi');
      for(var i=0;i<kpis.length && out.length<24;i++){
        var k=kpis[i];
        if(panel && panel.contains(k))continue;             /* skip our own UI */
        var lEl=k.querySelector('.ck-kpi-label'), vEl=k.querySelector('.ck-kpi-value');
        if(!lEl||!vEl)continue;
        push(lEl.textContent, vEl.textContent);
      }
      return out;
    }catch(e){return [];}                                    /* never block an ask */
  }
  function show(el){if(el)el.hidden=false;}
  function hide(el){if(el)el.hidden=true;}
  function askable(){return !!(health&&health.enabled&&health.reachable);}

  /* Invalidate any in-flight ask (close / route change). Bumps reqSeq so
   * the pending response returns stale, aborts the fetch if supported,
   * clears the slow-timer, and resets the pending/send state. */
  function invalidateInFlight(){
    reqSeq++;
    if(activeAbort){try{activeAbort.abort();}catch(e){} activeAbort=null;}
    if(activeTimer){clearTimeout(activeTimer); activeTimer=null;}
    pending=false;
    var send=$('[data-ck-guide-send]'); if(send) send.disabled=!askable();
  }
  function clearHistory(){var h=$('[data-ck-guide-history]'); if(h)h.innerHTML='';}

  var NEEDS='Needs source documentation.';
  function isNeeds(v){return /needs source documentation/i.test(String(v||''));}
  function emptyMsg(t){return '<p class="ck-guide-empty">'+esc(t)+'</p>';}
  function subRow(label,val){
    if(!val||isNeeds(val))return '';
    return '<div class="ck-guide-sub"><span class="ck-guide-sub-label">'+esc(label)+
      '</span><div class="ck-guide-sub-body">'+esc(val)+'</div></div>';
  }

  /* Tiny safe markdown renderer for model answers. HTML is escaped FIRST,
   * then a whitelisted set of inline marks (**bold**, *italic*, `code`) and
   * blocks (-, *, 1. lists + blank-line paragraphs) become tags. No raw
   * model HTML ever reaches innerHTML, so it stays XSS-safe while killing
   * the raw "**bold**" literals the old textContent path showed. No
   * external markdown dependency is added. */
  function mdInline(s){
    return s
      .replace(/\\*\\*([^*]+)\\*\\*/g,'<strong>$1</strong>')
      .replace(/(^|[^*])\\*([^*\\n]+)\\*/g,'$1<em>$2</em>')
      .replace(/`([^`]+)`/g,'<code>$1</code>');
  }
  function mdToHtml(src){
    var text=esc(src==null?'':String(src));   /* escape everything up front */
    var lines=text.split(/\\r?\\n/), out=[], list=null, para=[];
    function flushPara(){ if(para.length){out.push('<p>'+mdInline(para.join(' '))+'</p>');para=[];} }
    function flushList(){ if(list){out.push('<'+list.tag+'>'+list.items.join('')+'</'+list.tag+'>');list=null;} }
    lines.forEach(function(ln){
      var t=ln.trim();
      var ul=/^[-*]\\s+(.*)$/.exec(t), ol=/^\\d+[.)]\\s+(.*)$/.exec(t);
      if(ul){ flushPara(); if(!list||list.tag!=='ul'){flushList();list={tag:'ul',items:[]};}
        list.items.push('<li>'+mdInline(ul[1])+'</li>'); return; }
      if(ol){ flushPara(); if(!list||list.tag!=='ol'){flushList();list={tag:'ol',items:[]};}
        list.items.push('<li>'+mdInline(ol[1])+'</li>'); return; }
      if(t===''){ flushPara(); flushList(); return; }
      flushList(); para.push(t);
    });
    flushPara(); flushList();
    return out.join('')||'<p></p>';
  }

  function renderOverview(d){
    var pc=d.page_context, ov=$('[data-ck-guide-overview]');
    if(!pc){ ov.innerHTML=emptyMsg(d.fallback_message||'No documented context for this page yet.');
      renderCaveat(d); return; }
    var html='';
    if(pc.short_description&&!isNeeds(pc.short_description))
      html+='<p class="ck-guide-lede">'+esc(pc.short_description)+'</p>';
    html+=subRow('Purpose', pc.primary_purpose)+subRow('Why it matters', pc.why_it_matters);
    ov.innerHTML=html||emptyMsg('No overview documented yet.');
    renderCaveat(d);
  }

  /* Overview caveat callout — collapses page + known limitations + the
   * needs-documentation sentinel into one calm amber note (was a separate
   * "Limitations & caveats" card in the old single-scroll layout). */
  function renderCaveat(d){
    var box=$('[data-ck-guide-caveat]'), txt=$('[data-ck-guide-caveat-text]');
    if(!box||!txt)return;
    var pc=d.page_context, items=[];
    if(pc&&pc.limitations)items=items.concat(pc.limitations);
    if(d.known_limitations)items=items.concat(d.known_limitations);
    if(d.missing_context_notes)items=items.concat(d.missing_context_notes);
    var hadNeeds=false, seen={}, vals=[];
    items.forEach(function(x){
      if(!x||!String(x).trim())return;
      if(isNeeds(x)){hadNeeds=true;return;}
      if(seen[x])return; seen[x]=1; vals.push(x);
    });
    if(hadNeeds)vals.push('Some formulas or source-lineage details still need source documentation.');
    if(!vals.length){hide(box); txt.innerHTML=''; return;}
    txt.innerHTML='<b>Caveats.</b> '+vals.map(esc).join(' \\u00b7 ');
    show(box);
  }

  function metricCard(m){
    var html='<div class="ck-guide-metric"><div class="ck-guide-metric-head">'+
      '<span class="ck-guide-metric-name">'+esc(m.label)+'</span>';
    if(m.formula&&!isNeeds(m.formula))
      html+='<span class="ck-guide-metric-formula">'+esc(m.formula)+'</span>';
    else
      html+='<span class="ck-guide-metric-pill">formula not documented</span>';
    html+='</div>';
    if(m.definition&&!isNeeds(m.definition))
      html+='<div class="ck-guide-metric-desc">'+esc(m.definition)+'</div>';
    if(m.why_it_matters&&!isNeeds(m.why_it_matters))
      html+='<div class="ck-guide-metric-why">'+esc(m.why_it_matters)+'</div>';
    var cav=(m.caveats||[]).filter(function(c){return c&&!isNeeds(c);});
    if(cav.length) html+='<div class="ck-guide-metric-cav">'+esc(cav.join(' \\u00b7 '))+'</div>';
    return html+'</div>';
  }

  var WARN_SVG='<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" '+
    'stroke-width="2" aria-hidden="true"><path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 0 0 '+
    '1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/></svg>';
  function sourceCard(s){
    var typ=String(s.source_type||'').replace(/_/g,' ');
    var meta=[];
    if(typ&&!isNeeds(typ))meta.push('<b>'+esc(typ)+'</b>');
    if(s.update_cadence&&!isNeeds(s.update_cadence))meta.push(esc(s.update_cadence));
    if(s.freshness_lag&&!isNeeds(s.freshness_lag))meta.push(esc(s.freshness_lag));
    var lim=(s.limitations||[]).filter(function(x){return x&&!isNeeds(x);});
    var html='<div class="ck-guide-ds"><div class="ck-guide-ds-gem"></div>'+
      '<div class="ck-guide-ds-name">'+esc(s.label)+'</div>';
    if(meta.length)html+='<div class="ck-guide-ds-meta">'+meta.join(' &middot; ')+'</div>';
    if(s.description&&!isNeeds(s.description))
      html+='<div class="ck-guide-ds-desc">'+esc(s.description)+'</div>';
    if(lim.length)
      html+='<div class="ck-guide-ds-lim">'+WARN_SVG+'<span>'+esc(lim.join(' \\u00b7 '))+'</span></div>';
    return html+'</div>';
  }

  function chipHtml(x){
    return '<button type="button" class="ck-guide-chip" data-q="'+escAttr(x)+'" '+
      'title="Fills the question box">'+esc(x)+
      '<span class="ck-guide-chip-arr" aria-hidden="true">\\u2197</span></button>';
  }
  /* Chip click drops its text into the composer + focuses it — never
   * auto-submits (the user reviews, then presses Ask). */
  function wireChips(host){
    if(!host)return;
    Array.prototype.forEach.call(host.querySelectorAll('.ck-guide-chip'),function(b){
      b.addEventListener('click',function(){
        var inp=$('[data-ck-guide-input]'); if(!inp)return;
        inp.value=b.getAttribute('data-q')||'';
        inp.focus();
      });
    });
  }

  function setCount(sel, n){
    var el=$(sel); if(!el)return;
    if(n>0){el.textContent=String(n); show(el);}else{hide(el); el.textContent='';}
  }

  function renderContext(d){
    $('[data-ck-guide-page-title]').textContent=(d.page_context&&d.page_context.title)||'PEdesk Guide';
    var q=$('[data-ck-guide-quality]'), ql=$('[data-ck-guide-quality-label]'),
        sep=$('[data-ck-guide-meta-sep]');
    if(d.context_quality){
      q.setAttribute('data-q',d.context_quality);
      if(ql)ql.textContent=d.context_quality+' context';
      show(q); show(sep);
    }else{hide(q); hide(sep);}
    $('[data-ck-guide-route]').textContent=d.normalized_route||'';
    renderOverview(d);
    var metrics=d.metric_contexts||[], sources=d.data_source_contexts||[];
    var mh=$('[data-ck-guide-metrics]'), sh=$('[data-ck-guide-sources]');
    if(mh)mh.innerHTML=metrics.length?metrics.map(metricCard).join(''):
      emptyMsg('No metric context has been linked for this page yet.');
    if(sh)sh.innerHTML=sources.length?sources.map(sourceCard).join(''):
      emptyMsg('No data source context has been linked for this page yet.');
    setCount('[data-ck-guide-count-metrics]', metrics.length);
    setCount('[data-ck-guide-count-sources]', sources.length);
    var qs=d.suggested_questions||[];
    var ov=$('[data-ck-guide-suggested-overview]'), ak=$('[data-ck-guide-suggested-ask]');
    /* Overview shows the first four "try asking" prompts; Ask shows the full set. */
    if(ov){ov.innerHTML=qs.slice(0,4).map(chipHtml).join(''); wireChips(ov);}
    if(ak){ak.innerHTML=qs.map(chipHtml).join(''); wireChips(ak);}
  }

  function aiReason(h){
    if(!h) return 'Could not check local AI status.';
    if(!(h.ollama_enabled||h.enabled)) return 'Local AI is turned off.';
    if(!(h.ollama_reachable||h.reachable)) return 'Ollama is not running.';
    if(h.chat_model_installed===false)
      return 'The chat model ('+(h.chat_model||h.default_model)+') is not installed.';
    if(!h.rag_enabled) return 'RAG is turned off.';
    if(!h.rag_index_exists) return 'The RAG index has not been built.';
    if(!h.rag_chunk_count||!h.rag_embedded_count) return 'The RAG index is empty.';
    if(h.embed_model_installed===false)
      return 'The embedding model ('+h.embed_model+') is not installed.';
    return 'Local AI mode is not fully configured.';
  }

  /* Composer footer chrome — model id + the "● RAG ready / off" pill. The
     pill flips to "● Thinking…" while an ask is in flight (see ask()). */
  function setRag(state, label){
    var rag=$('[data-ck-guide-rag-status]'); if(!rag)return;
    rag.setAttribute('data-state', state); rag.textContent='\\u25cf '+label;
  }
  function applyFooter(h){
    var model=$('[data-ck-guide-model]');
    if(model)model.textContent=(h&&(h.chat_model||h.default_model))||'';
    if(h&&h.ai_ready)setRag('ready','RAG ready'); else setRag('off','RAG off');
  }

  function applyHealth(h){
    var stateEl=$('[data-ck-guide-ask-state]'), input=$('[data-ck-guide-input]'), send=$('[data-ck-guide-send]');
    applyFooter(h);
    /* Full AI mode = Ollama + chat model + RAG index all ready. The ask
       box is active only then; otherwise the page guide still renders and
       a calm status card explains exactly what's missing. */
    var ready=!!(h&&h.ai_ready);
    input.disabled=!ready; send.disabled=!ready;
    if(ready){
      stateEl.innerHTML='<div class="ck-guide-state-ready">AI Q&amp;A ready &middot; RAG enabled</div>';
      show(stateEl);
      return;
    }
    var fix=(h&&h.suggested_fix)||'';
    var cmds=(h&&h.setup_commands)||[];
    var cmdHtml=cmds.length?'<pre class="ck-guide-setup-pre">'+esc(cmds.join('\\n'))+'</pre>':'';
    stateEl.innerHTML=
      '<div class="ck-guide-state-primary">Ask PEdesk Guide is not fully configured.</div>'+
      '<div class="ck-guide-state-secondary">'+esc(aiReason(h))+' The page guide still works.</div>'+
      '<details class="ck-guide-setup"><summary>Setup details</summary>'+
      (fix?'<p class="ck-guide-muted">'+esc(fix)+'</p>':'')+
      '<p class="ck-guide-muted">Full local AI mode:</p>'+cmdHtml+
      '</details>';
    show(stateEl);
  }

  function loadContext(force){
    if(loadedRoute===route()&&!force) return;
    var r=route();
    /* Route changed (or forced reload): drop any in-flight answer and the
     * previous page's Q&A so nothing leaks across pages. */
    invalidateInFlight();
    clearHistory();
    hide($('[data-ck-guide-content]')); hide($('[data-ck-guide-error]'));
    show($('[data-ck-guide-loading]'));
    Promise.all([
      fetch('/api/guide/context?route='+encodeURIComponent(r)).then(function(x){return x.json();}),
      fetch('/api/guide/ollama-health').then(function(x){return x.json();}).catch(function(){return null;})
    ]).then(function(res){
      loadedRoute=r; health=res[1];
      hide($('[data-ck-guide-loading]'));
      renderContext(res[0]); applyHealth(health);
      show($('[data-ck-guide-content]'));
    }).catch(function(){
      hide($('[data-ck-guide-loading]'));
      $('[data-ck-guide-error-msg]').textContent="Couldn't load page context. Check your connection and retry.";
      show($('[data-ck-guide-error]'));
    });
  }

  function addHistory(q){
    var h=$('[data-ck-guide-history]');
    var wrap=document.createElement('div');
    wrap.innerHTML='<div class="ck-guide-q">'+esc(q)+'</div>'+
      '<div class="ck-guide-a"><span class="ck-guide-thinking">PEdesk Guide is answering from the page context</span></div>';
    h.appendChild(wrap);
    h.scrollTop=h.scrollHeight;
    return wrap.querySelector('.ck-guide-a');
  }

  function failBubble(aEl, msg){
    aEl.innerHTML='<p class="ck-guide-muted"></p>'+
      '<button type="button" class="ck-guide-btn" data-ck-guide-retry-ask>Retry</button>';
    aEl.querySelector('p').textContent=msg;  /* safe text */
    aEl.querySelector('[data-ck-guide-retry-ask]').addEventListener('click',function(){
      if(pending)return;                    /* don't stack a retry on a live request */
      if(aEl.parentNode)aEl.parentNode.remove();
      ask(lastQuestion);
    });
  }

  function ask(q){
    /* Duplicate-submit guard: one request at a time. Blocks Enter,
     * the send button, chips, and retry from firing a second request. */
    if(pending||!q.trim())return;
    pending=true; lastQuestion=q;
    var myseq=++reqSeq;                      /* claim this request */
    var t0=Date.now();                       /* for elapsed-time feedback */
    var send=$('[data-ck-guide-send]'); if(send) send.disabled=true;
    setRag('thinking','Thinking\\u2026');     /* footer pill: live ask in flight */
    var aEl=addHistory(q);
    var thinkEl=aEl.querySelector('.ck-guide-thinking');
    /* Long-response copy after 10s — only if this request is still the
     * active one. */
    activeTimer=setTimeout(function(){
      if(myseq===reqSeq && thinkEl){
        thinkEl.textContent='Local model responses can take a little while on this machine';
      }
    },10000);
    var ctrl=(window.AbortController)?new AbortController():null;
    activeAbort=ctrl;
    function settle(){
      if(activeTimer){clearTimeout(activeTimer); activeTimer=null;}
      /* Stale guard: a newer request, a close, or a route change bumped
       * reqSeq — drop this response entirely. */
      if(myseq!==reqSeq) return false;
      pending=false; activeAbort=null;
      if(send) send.disabled=!askable();
      applyFooter(health);                    /* restore footer RAG pill */
      return true;
    }
    fetch('/api/guide/ask',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({route:route(),question:q,onscreen_figures:scrapeOnscreen()}),
      signal:ctrl?ctrl.signal:undefined})
      .then(function(resp){return resp.json().then(function(j){return {status:resp.status,body:j};},
        function(){return {status:resp.status,body:{}};});})
      .then(function(r){
        if(!settle())return;
        if(r.status===200){
          var b=r.body||{};
          /* mdToHtml escapes the model text FIRST, then whitelists a few
           * markdown marks — XSS-safe, and no raw "**bold**" literals. */
          aEl.innerHTML='<div class="ck-guide-a-body">'+mdToHtml(b.answer||'')+'</div>';
          var secs=((Date.now()-t0)/1000).toFixed(1);   /* elapsed, local model */
          var meta='<div class="ck-guide-a-meta"><span class="ck-guide-badge">read-only</span>'+
            (b.model?'<span>'+esc(b.model)+'</span>':'')+
            '<span>'+secs+'s</span>'+
            (b.context_quality?'<span>quality: '+esc(b.context_quality)+'</span>':'')+
            '<button type="button" class="ck-guide-copy" data-ck-guide-copy>Copy</button>'+
            '</div>';
          var notes=(b.missing_context_notes&&b.missing_context_notes.length)?
            '<div class="ck-guide-metric-cav">Missing context: '+esc(b.missing_context_notes.join('; '))+'</div>':'';
          /* RAG provenance: group retrieved sources by registry type so the
             grounding is scannable (Page context / Metric Registry / Data
             Source Registry / Guide policy / Methodology · docs), each with
             title + score. When no RAG source was used, state plainly that
             the answer came from the current page packet alone. */
          var prov='';
          var srcs=(b.rag_sources_used&&b.rag_sources_used.length)?b.rag_sources_used:null;
          if(srcs){
            var GROUPS=[['page_context','Page context'],['metric','Metric Registry'],
              ['data_source','Data Source Registry'],['guide_policy','Guide policy'],
              ['doc','Methodology · docs']];
            var byType={};
            srcs.forEach(function(s){var t=(s.source_type||'other');(byType[t]=byType[t]||[]).push(s);});
            var srcLi=function(s){
              var sc=(typeof s.score==='number')?'<span class="ck-guide-src-score">'+esc(s.score.toFixed(2))+'</span>':'';
              return '<li class="ck-guide-src-item"><span class="ck-guide-src-title">'+esc(s.title)+'</span>'+sc+'</li>';
            };
            var grp=function(label,arr){
              return '<div class="ck-guide-src-group"><div class="ck-guide-src-type">'+esc(label)+
                '</div><ul class="ck-guide-src-list">'+arr.map(srcLi).join('')+'</ul></div>';
            };
            var groupsHtml='';
            GROUPS.forEach(function(g){
              if(byType[g[0]]&&byType[g[0]].length){groupsHtml+=grp(g[1],byType[g[0]]);delete byType[g[0]];}
            });
            Object.keys(byType).forEach(function(t){groupsHtml+=grp(t.replace(/_/g,' '),byType[t]);});
            prov='<div class="ck-guide-sources"><div class="ck-guide-src-head">Also used local Guide RAG sources</div>'+groupsHtml+'</div>';
          } else {
            prov='<div class="ck-guide-sources"><div class="ck-guide-src-head">Answered from current page context.</div></div>';
          }
          var ragWarn=b.rag_warning?'<div class="ck-guide-metric-cav">'+esc(b.rag_warning)+'</div>':'';
          aEl.insertAdjacentHTML('beforeend', notes+prov+ragWarn+meta);
          /* Copy-answer: browser clipboard only, no persistence/telemetry.
             Hidden when the Clipboard API is unavailable (e.g. non-secure
             context). Copies the plain answer text held in this closure. */
          var copyBtn=aEl.querySelector('[data-ck-guide-copy]');
          if(copyBtn){
            if(navigator.clipboard&&navigator.clipboard.writeText){
              copyBtn.addEventListener('click',function(){
                navigator.clipboard.writeText(b.answer||'').then(function(){
                  copyBtn.textContent='Copied';
                  setTimeout(function(){copyBtn.textContent='Copy';},1500);
                },function(){});
              });
            } else { copyBtn.hidden=true; }
          }
        } else if(r.status===503){
          aEl.classList.remove('ck-guide-a');
          failBubble(aEl, (r.body&&r.body.error)||'PEdesk Guide local model is unavailable.');
        } else {
          aEl.classList.remove('ck-guide-a');
          failBubble(aEl, (r.body&&r.body.error)||'Something went wrong. Please try again.');
        }
        var h=$('[data-ck-guide-history]'); if(h)h.scrollTop=h.scrollHeight;
      }).catch(function(){
        /* Abort (from invalidateInFlight) or network error. settle()
         * returns false on stale/abort so we never render an old error. */
        if(!settle())return;
        aEl.classList.remove('ck-guide-a');
        failBubble(aEl, 'PEdesk Guide local model is unavailable.');
      });
  }

  /* ── Tabs: ARIA tablist with roving tabindex + arrow-key navigation
     (Left/Right/Up/Down move + select, Home/End jump, Enter/Space select).
     Switching only toggles the body panels — the composer footer never
     unmounts, so a question can be asked from any tab. ── */
  var tabs=Array.prototype.slice.call(panel.querySelectorAll('[data-ck-guide-tab]'));
  function activateTab(id, focusBtn){
    tabs.forEach(function(btn){
      var on=btn.getAttribute('data-ck-guide-tab')===id;
      btn.setAttribute('aria-selected', on?'true':'false');
      btn.tabIndex=on?0:-1;
      if(on&&focusBtn)btn.focus();
    });
    Array.prototype.forEach.call(panel.querySelectorAll('[data-ck-guide-panel]'),function(p){
      p.hidden=p.getAttribute('data-ck-guide-panel')!==id;
    });
  }
  tabs.forEach(function(btn, i){
    btn.addEventListener('click',function(){activateTab(btn.getAttribute('data-ck-guide-tab'));});
    btn.addEventListener('keydown',function(e){
      var idx=null;
      if(e.key==='ArrowRight'||e.key==='ArrowDown')idx=(i+1)%tabs.length;
      else if(e.key==='ArrowLeft'||e.key==='ArrowUp')idx=(i-1+tabs.length)%tabs.length;
      else if(e.key==='Home')idx=0;
      else if(e.key==='End')idx=tabs.length-1;
      else if(e.key==='Enter'||e.key===' '){e.preventDefault();activateTab(btn.getAttribute('data-ck-guide-tab'));return;}
      if(idx!==null){e.preventDefault();activateTab(tabs[idx].getAttribute('data-ck-guide-tab'), true);}
    });
  });

  function open(){
    lastFocus=document.activeElement;
    panel.hidden=false;
    activateTab('overview');           /* always open on Overview */
    loadContext(false);
    var t=$('[data-ck-guide-page-title]'); if(t)t.focus();
  }
  function close(){
    /* Drop any in-flight answer + the session Q&A so a late response
     * cannot render after the panel is dismissed. */
    invalidateInFlight();
    clearHistory();
    panel.hidden=true;
    if(lastFocus&&lastFocus.focus)lastFocus.focus();
  }

  document.addEventListener('click',function(e){
    var o=e.target.closest('[data-ck-guide-open]'); if(o){e.preventDefault();open();return;}
    if(e.target.closest('[data-ck-guide-close]')){e.preventDefault();close();}
  });
  document.addEventListener('keydown',function(e){
    if(e.key==='Escape'&&!panel.hidden){close();}
  });
  var retry=$('[data-ck-guide-retry-context]'); if(retry)retry.addEventListener('click',function(){loadContext(true);});
  var form=$('[data-ck-guide-ask-form]');
  function submitQuestion(){
    var inp=$('[data-ck-guide-input]'); if(!inp)return;
    var v=inp.value; if(!v.trim()||pending)return;   /* duplicate-submit guard */
    inp.value=''; activateTab('ask'); ask(v);        /* show the answer in Ask */
  }
  if(form)form.addEventListener('submit',function(e){e.preventDefault();submitQuestion();});
  var input=$('[data-ck-guide-input]');
  if(input)input.addEventListener('keydown',function(e){
    /* Cmd/Ctrl+Enter submits (design-spec composer shortcut). Plain Enter
     * also submits; Shift+Enter inserts a newline. The pending guard in
     * submitQuestion/ask blocks duplicate presses. */
    if(e.key==='Enter'&&(e.metaKey||e.ctrlKey)){e.preventDefault();submitQuestion();return;}
    if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();submitQuestion();}
  });
})();
</script>
"""


_SORT_JS = """
<style>
table.ck-data-table th[data-sortable]:hover{color:var(--sc-teal,#155752);}
table.ck-data-table th[data-sort-dir]{color:var(--sc-teal,#155752);}
.ck-sort-ind{font-size:9px;opacity:0.75;}
</style>
<script>
/* Click-to-sort for every editorial data table. Hooks all
 * table.ck-data-table that carry a <thead> + <tbody> with >=2 rows.
 * Click (or Enter/Space) on a header sorts the body rows by that
 * column, toggling asc/desc. Numeric cells ($1,204.50 / 12.3% /
 * 2.50x / +4.1% / (1.2) negatives) sort numerically; everything else
 * lexically (locale, numeric-aware). Blank / "—" cells sink to the
 * bottom. Whole <tr> nodes are re-ordered so cell styling + color
 * spans survive. Purely additive: with JS off the table is unchanged.
 * Opt out per table with data-no-sort. */
(function(){
  function parseNum(t){
    if(t==null) return null;
    var s=String(t).trim();
    if(s===''||s==='\\u2014'||s==='-'||s==='n/a'||s==='N/A') return null;
    var neg=/^\\(.*\\)$/.test(s);
    s=s.replace(/[(),$%x\\u00d7\\s]/g,'').replace(/\\+/g,'');
    if(s==='') return null;
    var v=parseFloat(s);
    return isNaN(v)?null:(neg?-v:v);
  }
  function cellText(row,idx){var c=row.children[idx];return c?(c.textContent||'').trim():'';}
  function sortTable(table,idx,th){
    var tbody=table.tBodies[0];
    if(!tbody) return;
    var rows=Array.prototype.slice.call(tbody.rows);
    if(rows.length<2) return;
    var dir=th.getAttribute('data-sort-dir')==='asc'?'desc':'asc';
    var heads=th.parentNode.children;
    for(var i=0;i<heads.length;i++){
      heads[i].removeAttribute('data-sort-dir');
      var pi=heads[i].querySelector('.ck-sort-ind');
      if(pi) pi.textContent='';
    }
    th.setAttribute('data-sort-dir',dir);
    var mul=dir==='asc'?1:-1;
    var dec=rows.map(function(r,i){var t=cellText(r,idx);return {r:r,i:i,t:t,n:parseNum(t)};});
    dec.sort(function(a,b){
      if(a.n!=null&&b.n!=null){return a.n!==b.n?(a.n-b.n)*mul:a.i-b.i;}
      if(a.n!=null) return -1;
      if(b.n!=null) return 1;
      var c=a.t.localeCompare(b.t,void 0,{numeric:true});
      return c!==0?c*mul:a.i-b.i;
    });
    var frag=document.createDocumentFragment();
    dec.forEach(function(d){frag.appendChild(d.r);});
    tbody.appendChild(frag);
    var ind=th.querySelector('.ck-sort-ind');
    if(ind) ind.textContent=dir==='asc'?' \\u25B2':' \\u25BC';
  }
  function init(){
    var tables=document.querySelectorAll('table.ck-data-table');
    Array.prototype.forEach.call(tables,function(table){
      if(table.getAttribute('data-no-sort')!=null) return;
      var head=table.tHead, tbody=table.tBodies[0];
      if(!head||!tbody||tbody.rows.length<2) return;
      var hrow=head.rows[head.rows.length-1];
      if(!hrow) return;
      Array.prototype.forEach.call(hrow.cells,function(th,idx){
        if(th.getAttribute('data-sortable')!=null) return;
        th.setAttribute('data-sortable','');
        th.style.cursor='pointer';
        th.setAttribute('role','button');
        th.setAttribute('tabindex','0');
        if(!th.title) th.title='Sort';
        var ind=document.createElement('span');
        ind.className='ck-sort-ind';
        th.appendChild(ind);
        var h=function(e){e.preventDefault();sortTable(table,idx,th);};
        th.addEventListener('click',h);
        th.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' ')h(e);});
      });
    });
  }
  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',init);}
  else{init();}
})();
</script>
"""


_BARROW_HOVER_CSS = """
<style>
/* Hover emphasis for ck_bar_row charts — pure CSS, makes the ranked
 * bar lists feel interactive: the hovered row lifts with a faint wash
 * and its fill brightens so a partner can track a single series. */
.ck-bar-row{transition:background .12s ease;border-radius:2px;}
.ck-bar-row:hover{background:rgba(31,122,117,0.07);}
.ck-bar-row:hover .ck-bar-row-fill{filter:saturate(1.3) brightness(1.05);}
.ck-bar-row:hover .ck-bar-row-label{color:var(--sc-teal-ink,#155752);}
</style>
"""


_TABLE_TOTALS_JS = """
<style>
.ck-ttotals{position:absolute;top:4px;right:110px;z-index:3;opacity:0;transition:opacity .12s;
  font:9px var(--sc-mono,'JetBrains Mono',monospace);letter-spacing:.04em;text-transform:uppercase;
  padding:2px 7px;border:1px solid var(--sc-rule,#d6cfc0);background:var(--sc-bg,#faf7f0);
  color:var(--sc-text-dim,#465366);border-radius:2px;cursor:pointer;}
.ck-data-table-scroll:hover .ck-ttotals{opacity:0.9;}
.ck-ttotals:hover,.ck-ttotals[aria-pressed="true"]{border-color:var(--sc-teal,#155752);color:var(--sc-teal,#155752);}
tfoot.ck-totals-foot td{border-top:2px solid var(--sc-teal,#155752);font-weight:700;
  background:var(--sc-bone,#ece5d6);font-family:var(--sc-mono,'JetBrains Mono',monospace);
  font-variant-numeric:tabular-nums;padding:6px 10px;font-size:11px;}
</style>
<script>
/* Totals / averages summary row for editorial tables — a hover toggle
 * (\\u03a3) that appends a footer aggregating each numeric column over the
 * currently-visible rows: $ and count columns sum; % and x (multiple)
 * columns average; text columns blank. Format mirrors the column (prefix
 * $, suffix B/M/k, decimals). Recomputes live when the row-filter changes
 * so the summary always matches what's on screen. Off by default;
 * additive; opt out with data-no-totals. */
(function(){
  function parseNum(t){
    if(t==null) return null;
    var s=String(t).trim();
    if(s===''||s==='\\u2014'||s==='-'||s==='n/a'||s==='N/A') return null;
    var neg=/^\\(.*\\)$/.test(s);
    s=s.replace(/[(),$%x\\u00d7\\s]/g,'').replace(/\\+/g,'');
    if(s==='') return null;
    var v=parseFloat(s);
    return isNaN(v)?null:(neg?-v:v);
  }
  function comma(x,d){return x.toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});}
  function decimals(arr){var d=0;arr.forEach(function(s){var m=String(s).match(/\\.(\\d+)/);if(m)d=Math.max(d,m[1].length);});return Math.min(d,2);}
  function aggColumn(texts){
    var present=texts.filter(function(t){return t!=null&&String(t).trim()!=='';});
    var nums=[]; texts.forEach(function(t){var n=parseNum(t);if(n!=null)nums.push(n);});
    if(nums.length<Math.max(2,Math.ceil(present.length*0.6))) return '';
    var sample=''; for(var i=0;i<texts.length;i++){if(parseNum(texts[i])!=null){sample=String(texts[i]).trim();break;}}
    var hasDollar=sample.indexOf('$')>=0,hasPct=sample.indexOf('%')>=0,hasX=/x$/i.test(sample);
    var suf=''; if(/[0-9]B$/.test(sample))suf='B'; else if(/[0-9]M$/.test(sample))suf='M'; else if(/[0-9]k$/.test(sample))suf='k';
    var dec=decimals(texts);
    var sum=nums.reduce(function(a,b){return a+b;},0);
    if(hasPct) return comma(sum/nums.length,1)+'%';
    if(hasX) return comma(sum/nums.length,2)+'x';
    if(hasDollar) return '$'+comma(sum,dec||(suf?1:2))+suf;
    if(dec===0) return comma(sum,0);
    return comma(sum,dec)+suf;
  }
  function build(table){
    var tb=table.tBodies[0]; if(!tb) return null;
    var rows=Array.prototype.slice.call(tb.rows).filter(function(r){return r.style.display!=='none';});
    if(rows.length<2) return null;
    var ncols=0; rows.forEach(function(r){if(r.cells.length>ncols)ncols=r.cells.length;});
    var tr=document.createElement('tr');
    for(var c=0;c<ncols;c++){
      var texts=rows.map(function(r){var cell=r.cells[c];return cell?(cell.textContent||''):'';});
      var v=aggColumn(texts);
      if(c===0&&v==='') v='\\u03a3 Total / avg';
      var td=document.createElement('td');
      var s=rows[0].cells[c];
      if(s&&s.classList.contains('ck-cell-r')) td.style.textAlign='right';
      else if(s&&s.classList.contains('ck-cell-c')) td.style.textAlign='center';
      td.textContent=v; tr.appendChild(td);
    }
    return tr;
  }
  function render(table,on){
    var f=table.querySelector('tfoot.ck-totals-foot'); if(f) f.parentNode.removeChild(f);
    if(!on) return;
    var tr=build(table); if(!tr) return;
    var foot=document.createElement('tfoot'); foot.className='ck-totals-foot'; foot.appendChild(tr);
    table.appendChild(foot);
  }
  function init(){
    Array.prototype.forEach.call(document.querySelectorAll('table.ck-data-table'),function(table){
      if(table.getAttribute('data-no-totals')!=null) return;
      if(table.getAttribute('data-totalable')!=null) return;
      var tb=table.tBodies[0]; if(!tb||tb.rows.length<2) return;
      table.setAttribute('data-totalable','');
      var host=table.closest('.ck-data-table-scroll'); if(!host) return;
      var btn=document.createElement('button'); btn.type='button'; btn.className='ck-ttotals';
      btn.textContent='\\u03a3 Totals'; btn.setAttribute('aria-pressed','false');
      btn.setAttribute('aria-label','Toggle totals / averages row');
      btn.addEventListener('click',function(e){
        e.preventDefault();
        var on=btn.getAttribute('aria-pressed')!=='true';
        btn.setAttribute('aria-pressed',on?'true':'false');
        render(table,on);
      });
      host.appendChild(btn);
      var fi=host.parentNode?host.parentNode.querySelector('.ck-tfilter input'):null;
      if(fi) fi.addEventListener('input',function(){
        if(btn.getAttribute('aria-pressed')==='true') render(table,true);
      });
    });
  }
  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',init);}
  else{init();}
})();
</script>
"""


_TABLE_BARS_JS = """
<style>
.ck-tbars{position:absolute;top:4px;right:52px;z-index:3;opacity:0;transition:opacity .12s;
  font:9px var(--sc-mono,'JetBrains Mono',monospace);letter-spacing:.04em;text-transform:uppercase;
  padding:2px 7px;border:1px solid var(--sc-rule,#d6cfc0);background:var(--sc-bg,#faf7f0);
  color:var(--sc-text-dim,#465366);border-radius:2px;cursor:pointer;}
.ck-data-table-scroll:hover .ck-tbars{opacity:0.9;}
.ck-tbars:hover,.ck-tbars[aria-pressed="true"]{border-color:var(--sc-teal,#155752);color:var(--sc-teal,#155752);}
td.ck-bar-cell{background-repeat:no-repeat;}
</style>
<script>
/* Inline magnitude bars for editorial tables — a hover toggle that
 * paints a proportional data-bar behind each numeric cell so a partner
 * reads a column's distribution in place (no separate chart needed).
 * Diverging: teal for positive, red for negative, scaled to the column's
 * max absolute value; bar anchors to the cell's text edge (right for
 * right-aligned numerics). Toggle is off by default, so the default look
 * is unchanged. Additive; opt out with data-no-bars. */
(function(){
  function parseNum(t){
    if(t==null) return null;
    var s=String(t).trim();
    if(s===''||s==='\\u2014'||s==='-'||s==='n/a'||s==='N/A') return null;
    var neg=/^\\(.*\\)$/.test(s);
    s=s.replace(/[(),$%x\\u00d7\\s]/g,'').replace(/\\+/g,'');
    if(s==='') return null;
    var v=parseFloat(s);
    return isNaN(v)?null:(neg?-v:v);
  }
  function paint(table,on){
    var tb=table.tBodies[0]; if(!tb) return;
    var rows=Array.prototype.slice.call(tb.rows);
    var ncols=0;
    rows.forEach(function(r){ if(r.cells.length>ncols) ncols=r.cells.length; });
    for(var c=0;c<ncols;c++){
      var vals=[], cells=[];
      rows.forEach(function(r){
        var cell=r.cells[c]; if(!cell) return;
        var n=parseNum(cell.textContent||'');
        cells.push({cell:cell,n:n}); if(n!=null) vals.push(n);
      });
      var numeric=vals.length>=Math.max(2,Math.ceil(cells.length*0.6));
      var distinct={}; vals.forEach(function(v){distinct[v]=1;});
      var mx=0; vals.forEach(function(v){ if(Math.abs(v)>mx) mx=Math.abs(v); });
      cells.forEach(function(o){
        var cell=o.cell;
        cell.classList.remove('ck-bar-cell'); cell.style.backgroundImage='';
        if(!on||!numeric||mx<=0||Object.keys(distinct).length<2||o.n==null) return;
        var w=Math.max(0,Math.min(100,Math.abs(o.n)/mx*100));
        var col=o.n<0?'rgba(181,50,30,0.16)':'rgba(31,122,117,0.18)';
        var rightAnchored=cell.classList.contains('ck-cell-r');
        var dir=rightAnchored?'270deg':'90deg';
        cell.classList.add('ck-bar-cell');
        cell.style.backgroundImage='linear-gradient('+dir+','+col+' '+w+'%,transparent '+w+'%)';
      });
    }
  }
  function init(){
    Array.prototype.forEach.call(document.querySelectorAll('table.ck-data-table'),function(table){
      if(table.getAttribute('data-no-bars')!=null) return;
      if(table.getAttribute('data-barable')!=null) return;
      var tb=table.tBodies[0]; if(!tb||tb.rows.length<2) return;
      table.setAttribute('data-barable','');
      var host=table.closest('.ck-data-table-scroll'); if(!host) return;
      var btn=document.createElement('button'); btn.type='button'; btn.className='ck-tbars';
      btn.textContent='\\u25A6 Bars'; btn.setAttribute('aria-pressed','false');
      btn.setAttribute('aria-label','Toggle inline magnitude bars');
      btn.addEventListener('click',function(e){
        e.preventDefault();
        var on=btn.getAttribute('aria-pressed')!=='true';
        btn.setAttribute('aria-pressed',on?'true':'false');
        paint(table,on);
      });
      host.appendChild(btn);
    });
  }
  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',init);}
  else{init();}
})();
</script>
"""


_TABLE_COPY_JS = """
<style>
.ck-data-table-scroll{position:relative;}
.ck-tcopy{position:absolute;top:4px;right:4px;z-index:3;opacity:0;transition:opacity .12s;
  font:9px var(--sc-mono,'JetBrains Mono',monospace);letter-spacing:.04em;text-transform:uppercase;
  padding:2px 7px;border:1px solid var(--sc-rule,#d6cfc0);background:var(--sc-bg,#faf7f0);
  color:var(--sc-text-dim,#465366);border-radius:2px;cursor:pointer;}
.ck-data-table-scroll:hover .ck-tcopy{opacity:0.9;}
.ck-tcopy:hover{border-color:var(--sc-teal,#155752);color:var(--sc-teal,#155752);}
</style>
<script>
/* Hover copy-to-clipboard for editorial tables. A small Copy button
 * (revealed on table hover) copies the header + currently-visible body
 * rows as TSV — Excel/Sheets paste-ready, and respects the active row
 * filter. Strips the sort indicator from header text. Additive; opt out
 * with data-no-copy. */
(function(){
  function txt(cell){
    var c=cell.cloneNode(true);
    var ind=c.querySelector('.ck-sort-ind'); if(ind&&ind.parentNode) ind.parentNode.removeChild(ind);
    return (c.textContent||'').trim().replace(/\\s+/g,' ');
  }
  function copyTable(table,btn){
    var rows=[];
    if(table.tHead){
      var hr=table.tHead.rows[table.tHead.rows.length-1];
      if(hr) rows.push(Array.prototype.map.call(hr.cells,txt).join('\\t'));
    }
    var tb=table.tBodies[0];
    if(tb) Array.prototype.forEach.call(tb.rows,function(r){
      if(r.style.display==='none') return;
      rows.push(Array.prototype.map.call(r.cells,txt).join('\\t'));
    });
    var data=rows.join('\\n');
    var done=function(){var o=btn.getAttribute('data-label');btn.textContent='Copied';
      setTimeout(function(){btn.textContent=o;},1100);};
    if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(data).then(done,done);}
    else{var ta=document.createElement('textarea');ta.value=data;document.body.appendChild(ta);
      ta.select();try{document.execCommand('copy');}catch(e){}document.body.removeChild(ta);done();}
  }
  function init(){
    Array.prototype.forEach.call(document.querySelectorAll('table.ck-data-table'),function(table){
      if(table.getAttribute('data-no-copy')!=null) return;
      if(table.getAttribute('data-copyable')!=null) return;
      table.setAttribute('data-copyable','');
      var host=table.closest('.ck-data-table-scroll'); if(!host) return;
      var btn=document.createElement('button'); btn.type='button'; btn.className='ck-tcopy';
      btn.textContent='Copy'; btn.setAttribute('data-label','Copy');
      btn.setAttribute('aria-label','Copy table to clipboard');
      btn.addEventListener('click',function(e){e.preventDefault();copyTable(table,btn);});
      host.appendChild(btn);
    });
  }
  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',init);}
  else{init();}
})();
</script>
"""


_TABLE_FILTER_JS = """
<style>
.ck-tfilter{display:flex;justify-content:flex-end;align-items:center;gap:8px;margin-bottom:6px;}
.ck-tfilter input{font:11px/1.4 var(--sc-mono,'JetBrains Mono',monospace);
  padding:3px 9px;border:1px solid var(--sc-rule,#d6cfc0);background:var(--sc-bg,#faf7f0);
  color:var(--sc-ink,#1a2332);border-radius:2px;width:190px;}
.ck-tfilter input:focus{outline:none;border-color:var(--sc-teal,#155752);}
.ck-tfilter-count{font:10px var(--sc-mono,'JetBrains Mono',monospace);
  color:var(--sc-text-faint,#7a8699);}
</style>
<script>
/* Live row-filter for long editorial tables (>=8 body rows). Inserts a
 * compact filter box above the table; typing hides rows whose visible
 * text doesn't contain the query (case-insensitive). Pairs with the
 * sort shim (sort re-orders all rows; filter toggles row display).
 * Additive; degrades to a plain table with JS off; opt out per table
 * with data-no-filter. */
(function(){
  function attach(table){
    var tbody=table.tBodies[0];
    if(!tbody||tbody.rows.length<8) return;
    if(table.getAttribute('data-no-filter')!=null) return;
    if(table.getAttribute('data-filtered')!=null) return;
    table.setAttribute('data-filtered','');
    var host=table.closest('.ck-data-table-scroll')||table;
    if(!host.parentNode) return;
    var wrap=document.createElement('div'); wrap.className='ck-tfilter';
    var input=document.createElement('input');
    input.type='search'; input.placeholder='Filter rows\\u2026';
    input.setAttribute('aria-label','Filter table rows');
    var count=document.createElement('span'); count.className='ck-tfilter-count';
    var total=tbody.rows.length;
    function upd(){
      var q=input.value.trim().toLowerCase(); var shown=0;
      Array.prototype.forEach.call(tbody.rows,function(r){
        var m=q===''||(r.textContent||'').toLowerCase().indexOf(q)>=0;
        r.style.display=m?'':'none'; if(m) shown++;
      });
      count.textContent=q===''?'':(shown+' of '+total);
    }
    input.addEventListener('input',upd);
    wrap.appendChild(input); wrap.appendChild(count);
    host.parentNode.insertBefore(wrap,host);
  }
  function init(){
    Array.prototype.forEach.call(document.querySelectorAll('table.ck-data-table'),attach);
  }
  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',init);}
  else{init();}
})();
</script>
"""


_TOAST_JS = """
<script>
/* Toast / flash notification system.
 *   Any page can fire one via:
 *     window.ckToast('Saved', 'success')   // success | info | warning | error
 *   Or embed a one-shot at render time:
 *     <meta name="ck-flash" content="Alert acknowledged">
 *     <meta name="ck-flash-kind" content="success">
 *   Or via query string after a redirect:
 *     /alerts?flash=Acknowledged&kind=success
 *   The query-string variant scrubs ?flash + ?kind from history so a
 *   partner refreshing the page doesn't see the toast again. */
(function(){
  var host = document.getElementById('ck-toast-host');
  if (!host) return;

  function show(msg, kind){
    if (!msg) return;
    var t = document.createElement('div');
    t.className = 'ck-toast ck-toast-' + (kind || 'info');
    t.setAttribute('role', 'status');
    t.textContent = msg;
    var x = document.createElement('button');
    x.type = 'button';
    x.className = 'ck-toast-close';
    x.setAttribute('aria-label', 'Dismiss');
    x.innerHTML = '&times;';
    x.addEventListener('click', function(){ dismiss(t); });
    t.appendChild(x);
    host.appendChild(t);
    /* Slide in on next frame so transition fires */
    requestAnimationFrame(function(){ t.classList.add('ck-toast-show'); });
    /* Auto-dismiss after 3.6s (5.5s for warning/error) */
    var ms = (kind === 'warning' || kind === 'error') ? 5500 : 3600;
    setTimeout(function(){ dismiss(t); }, ms);
  }
  function dismiss(t){
    if (!t || !t.parentNode) return;
    t.classList.remove('ck-toast-show');
    setTimeout(function(){
      if (t.parentNode) t.parentNode.removeChild(t);
    }, 220);
  }
  window.ckToast = show;

  /* Render meta-tag flashes on load */
  var meta = document.querySelector('meta[name="ck-flash"]');
  if (meta && meta.getAttribute('content')) {
    var kind = (document.querySelector('meta[name="ck-flash-kind"]') || {}).content || 'info';
    show(meta.getAttribute('content'), kind);
  }

  /* Render query-string flashes on load + clean history */
  try {
    var sp = new URLSearchParams(window.location.search);
    var qmsg = sp.get('flash');
    if (qmsg) {
      var qkind = sp.get('kind') || 'info';
      show(qmsg, qkind);
      sp.delete('flash');
      sp.delete('kind');
      var qs = sp.toString();
      var newUrl = window.location.pathname + (qs ? ('?' + qs) : '') + window.location.hash;
      window.history.replaceState({}, '', newUrl);
    }
  } catch (e) {}
})();
</script>
"""


_SHORTCUTS_HTML = """
<div class="ck-shortcuts" id="ck-shortcuts" hidden>
  <div class="ck-shortcuts-box" role="dialog" aria-label="Keyboard shortcuts">
    <header class="ck-shortcuts-head">
      <span class="ck-shortcuts-eyebrow">Keyboard</span>
      <h2 class="ck-shortcuts-title">Shortcuts</h2>
      <button type="button" class="ck-shortcuts-close" aria-label="Close">&times;</button>
    </header>
    <div class="ck-shortcuts-body">
      <section>
        <h3>Navigation</h3>
        <dl>
          <dt><kbd>⌘</kbd><kbd>K</kbd> &middot; <kbd>Ctrl</kbd><kbd>K</kbd></dt>
            <dd>Open command palette &mdash; jump to any tool</dd>
          <dt><kbd>Enter</kbd></dt>
            <dd>In palette: open the first matching tool</dd>
          <dt><kbd>Esc</kbd></dt>
            <dd>Close palette / dialog / dropdown</dd>
        </dl>
      </section>
      <section>
        <h3>Quick jump (vim-style)</h3>
        <dl>
          <dt><kbd>g</kbd> <kbd>h</kbd></dt><dd>Home</dd>
          <dt><kbd>g</kbd> <kbd>p</kbd></dt><dd>Pipeline</dd>
          <dt><kbd>g</kbd> <kbd>d</kbd></dt><dd>Diligence (deal profile)</dd>
          <dt><kbd>g</kbd> <kbd>l</kbd></dt><dd>Library</dd>
          <dt><kbd>g</kbd> <kbd>r</kbd></dt><dd>Research</dd>
          <dt><kbd>g</kbd> <kbd>o</kbd></dt><dd>Portfolio</dd>
          <dt><kbd>g</kbd> <kbd>a</kbd></dt><dd>Alerts</dd>
          <dt><kbd>g</kbd> <kbd>w</kbd></dt><dd>Watchlist</dd>
          <dt><kbd>g</kbd> <kbd>m</kbd></dt><dd>My Dashboard</dd>
        </dl>
      </section>
      <section>
        <h3>Workbench</h3>
        <dl>
          <dt><kbd>1</kbd>&ndash;<kbd>8</kbd></dt>
            <dd>Switch tabs on /analysis/&lt;deal&gt; (Overview &rarr; Provenance)</dd>
          <dt><kbd>Alt</kbd><kbd>&larr;</kbd> / <kbd>Alt</kbd><kbd>&rarr;</kbd></dt>
            <dd>Previous / next tab</dd>
        </dl>
      </section>
      <section>
        <h3>Discovery</h3>
        <dl>
          <dt><kbd>?</kbd></dt><dd>Show / hide this list</dd>
          <dt><kbd>/</kbd></dt>
            <dd>Focus the topbar search field</dd>
          <dt><kbd>T</kbd></dt>
            <dd>Open <em>The Atlas</em> &mdash; the editorial tour</dd>
          <dt><kbd>Shift</kbd><kbd>Q</kbd></dt>
            <dd>Quick capture &mdash; jot a diligence question
                without leaving the page</dd>
        </dl>
      </section>
    </div>
  </div>
</div>
"""


_SHORTCUTS_JS = """
<script>
/* Keyboard shortcut help dialog: press '?' to toggle, Esc to close.
 * Shift+/ (the unshifted "?" key on most US keyboards) is what the
 * browser actually delivers — listen for it explicitly so the
 * shortcut works without relying on e.key === '?'.
 *
 * Also implements vim/Linear-style "g + letter" jump:
 *   g h → /home          g p → /pipeline       g d → /diligence/deal
 *   g l → /library       g r → /research       g o → /portfolio
 *   g a → /alerts        g w → /watchlist      g k → opens palette
 */
(function(){
  /* g+letter prefix-jump table. Keep separate from shortcut dialog
   * so future expansion (g + I = ic packet, etc.) lives in one place. */
  var GO_TARGETS = {
    h: '/home', p: '/pipeline', d: '/diligence/deal',
    l: '/library', r: '/research', o: '/portfolio',
    a: '/alerts', w: '/watchlist', m: '/my/AT',
  };
  var goPending = false;
  var goTimer = null;
  function clearGo(){ goPending = false; if (goTimer){clearTimeout(goTimer); goTimer=null;} }
  document.addEventListener('keydown', function(e){
    if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable)) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (goPending) {
      var k = (e.key || '').toLowerCase();
      if (GO_TARGETS[k]) {
        e.preventDefault();
        clearGo();
        window.location.href = GO_TARGETS[k];
        return;
      }
      if (k === 'k') {
        /* Alias g+k → command palette to match the docs */
        clearGo();
        var p = document.getElementById('ck-palette');
        if (p) { p.hidden = false; var inp = p.querySelector('.ck-palette-input'); if (inp) setTimeout(function(){ inp.focus(); }, 0); }
        e.preventDefault();
        return;
      }
      clearGo();
      return;
    }
    if (e.key === 'g' && !e.shiftKey) {
      goPending = true;
      goTimer = setTimeout(clearGo, 1500);
      e.preventDefault();
    }
  });
})();

(function(){
  var dlg = document.getElementById('ck-shortcuts');
  if (!dlg) return;
  function show(){ dlg.hidden = false; }
  function hide(){ dlg.hidden = true; }
  document.addEventListener('keydown', function(e){
    if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable)) return;
    if (e.key === '?' || (e.shiftKey && e.key === '/')) {
      e.preventDefault();
      if (dlg.hidden) show(); else hide();
    }
    /* "/" (without Shift) focuses the topbar search input — common
     * Stripe/Linear/GitHub pattern. Skipped when the dialog is
     * open (since "/" is the underlying char of "?") and when
     * an input is already focused. */
    if (e.key === '/' && !e.shiftKey && !e.metaKey && !e.ctrlKey
        && !e.altKey && dlg.hidden) {
      var search = document.querySelector(".ck-search");
      if (search) { e.preventDefault(); search.focus(); search.select(); }
    }
    if (e.key === 'Escape' && !dlg.hidden) { e.preventDefault(); hide(); }
    /* "T" launches the editorial tour. Hide the shortcuts dialog
     * first so the tour modal isn't stacked on top of it. */
    if ((e.key === 't' || e.key === 'T') && !e.shiftKey
        && window.ckTour && typeof window.ckTour.open === 'function') {
      e.preventDefault();
      if (!dlg.hidden) hide();
      window.ckTour.open(1);
    }
  });
  /* Close button + click-outside */
  var close = dlg.querySelector('.ck-shortcuts-close');
  if (close) close.addEventListener('click', hide);
  dlg.addEventListener('click', function(e){
    if (e.target === dlg) hide();
  });
  /* Open from the user-dropdown menu item */
  document.addEventListener('click', function(e){
    var btn = e.target && e.target.closest && e.target.closest('[data-ck-shortcuts-open]');
    if (btn) { e.preventDefault(); show(); }
  });
})();
</script>
"""


_INTRO_DISMISS_JS = """
<script>
/* Editorial section-intro behaviour:
 *   - Hidden by default. A partner only sees them when they opt into
 *     "tutorial mode" via the user dropdown → "Tutorial intros".
 *   - When tutorial mode IS on, the × button still dismisses an
 *     individual intro per-page (writes ck-intro-dismissed:<key>).
 *   - The global toggle is the localStorage flag `ck-intro-mode`;
 *     value "on" shows intros, anything else hides them. */
(function(){
  var GLOBAL_KEY = 'ck-intro-mode';
  var STORAGE_PREFIX = 'ck-intro-dismissed:';
  var enabled = (function(){
    try { return localStorage.getItem(GLOBAL_KEY) === 'on'; }
    catch (e) { return false; }
  })();
  var intros = document.querySelectorAll('[data-ck-intro]');
  intros.forEach(function(el){
    if (!enabled) { el.hidden = true; return; }
    var key = el.getAttribute('data-ck-intro');
    if (key && localStorage.getItem(STORAGE_PREFIX + key) === '1') {
      el.hidden = true;
    }
  });
  document.addEventListener('click', function(e){
    var btn = e.target.closest && e.target.closest('[data-ck-intro-dismiss]');
    if (btn) {
      var key = btn.getAttribute('data-ck-intro-dismiss');
      var host = btn.closest('[data-ck-intro]');
      if (host) host.hidden = true;
      if (key) {
        try { localStorage.setItem(STORAGE_PREFIX + key, '1'); } catch (e) {}
      }
      return;
    }
    var tog = e.target.closest && e.target.closest('[data-ck-intro-toggle]');
    if (tog) {
      e.preventDefault();
      try {
        var now = localStorage.getItem(GLOBAL_KEY) === 'on' ? 'off' : 'on';
        localStorage.setItem(GLOBAL_KEY, now);
        // Reflect in the menu label without a full reload
        tog.textContent = (now === 'on'
          ? 'Tutorial intros: on'
          : 'Tutorial intros: off');
        // Show / hide intros immediately
        document.querySelectorAll('[data-ck-intro]').forEach(function(el){
          el.hidden = (now !== 'on');
        });
      } catch (e) {}
    }
  });
  /* On load, set the menu-item label to match current state. */
  var label = document.querySelector('[data-ck-intro-toggle]');
  if (label) {
    label.textContent = enabled ? 'Tutorial intros: on'
                                : 'Tutorial intros: off';
  }
})();
</script>
"""


_QPILL_JS = """
<script>
/* Topbar diligence-questions pill — counts opens across every
 * rcm_deal_*_questions entry in localStorage and surfaces the
 * total as a single editorial chip in the topbar. Hidden when zero
 * so a fresh partner never sees an empty pill. Click navigates to
 * the portfolio question ledger. Repaints every 30s so partners
 * leaving the tab on a page see the chip update in the background. */
(function() {
  function paintQpill() {
    var el = document.querySelector("[data-ck-qpill]");
    if (!el) return;
    var num = el.querySelector("[data-ck-qpill-num]");
    var total = 0;
    try {
      for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i);
        if (!k || !/_questions$/.test(k)) continue;
        if (!/^rcm_deal_/.test(k)) continue;
        try {
          var rows = JSON.parse(localStorage.getItem(k) || "[]");
          if (!Array.isArray(rows)) continue;
          for (var j = 0; j < rows.length; j++) {
            if (rows[j] && !rows[j].asked) total += 1;
          }
        } catch (e) { /* skip malformed row */ }
      }
    } catch (e) { /* storage disabled — leave hidden */ return; }
    if (total <= 0) { el.hidden = true; return; }
    if (num) num.textContent = String(total);
    el.hidden = false;
  }
  document.addEventListener("DOMContentLoaded", paintQpill);
  // Repaint when the partner returns to the tab — quick-capture
  // from another tab is unlikely but cheap to support.
  document.addEventListener("visibilitychange", function() {
    if (!document.hidden) paintQpill();
  });
}());
</script>
"""


_USER_MENU_JS = """
<script>
/* User dropdown — click chip to open, click-outside or Escape to close.
 * Marks aria-expanded for screen readers. Drop-in safe; renders nothing
 * if a page omits the chip entirely.
 *
 * Also populates the "Recent deals" group from localStorage on every
 * page load. Storage key: rcm-mc-recent-deals-v1, written by the deal
 * page (server.py) as [{id, name}, ...] (legacy entries are bare strings;
 * we tolerate both shapes). */
(function(){
  var btn = document.querySelector('[data-ck-user-toggle]');
  if (!btn) return;
  var menu = btn.parentElement.querySelector('.ck-user-dropdown');
  if (!menu) return;
  function open(){ menu.hidden = false; btn.setAttribute('aria-expanded','true'); }
  function close(){ menu.hidden = true; btn.setAttribute('aria-expanded','false'); }
  btn.addEventListener('click', function(e){
    e.stopPropagation();
    if (menu.hidden) open(); else close();
  });
  document.addEventListener('click', function(e){
    if (menu.hidden) return;
    if (!menu.contains(e.target) && e.target !== btn) close();
  });
  document.addEventListener('keydown', function(e){
    if (e.key === 'Escape' && !menu.hidden) close();
  });

  /* Hydrate recent-deals group */
  try {
    var REC_KEY = 'rcm-mc-recent-deals-v1';
    var MAX_DROPDOWN = 5;
    var box = menu.querySelector('[data-ck-recent-deals]');
    var list = menu.querySelector('[data-ck-recent-list]');
    if (box && list) {
      var arr = [];
      try { arr = JSON.parse(localStorage.getItem(REC_KEY) || '[]'); }
      catch (e) { arr = []; }
      arr = arr.map(function(x) {
        return (typeof x === 'string') ? {id: x, name: x} : x;
      }).filter(function(x) { return x && x.id; });
      if (arr.length) {
        box.hidden = false;
        list.innerHTML = '';
        arr.slice(0, MAX_DROPDOWN).forEach(function(d) {
          var a = document.createElement('a');
          a.className = 'ck-user-recent-item';
          a.href = '/deal/' + encodeURIComponent(d.id);
          var nm = document.createElement('span');
          nm.className = 'ck-user-recent-name';
          nm.textContent = d.name || d.id;
          a.appendChild(nm);
          if (d.name && d.name !== d.id) {
            var sl = document.createElement('span');
            sl.className = 'ck-user-recent-slug';
            sl.textContent = d.id;
            a.appendChild(sl);
          }
          list.appendChild(a);
        });
      }
    }
  } catch (e) { /* storage unavailable — skip */ }
})();
</script>
"""


# Topbar mega-menu controller. Enforces ONE open menu at a time and reliable
# dismissal (the CSS :focus-within fallback could leave a focused panel stuck
# open alongside a hovered one). Marks the topbar [data-menu-js] so CSS hands
# the open state entirely to .is-open. Drop-in safe; no-ops without a topbar.
_NAV_MENU_JS = """
<script>
/* Topbar mega-menu controller — hover-intent + grace close.
 *
 * Goals (see fix/topbar-megamenu-stability): the menu must not require
 * pixel-perfect movement, must not flicker when a trackpad sweeps across the
 * nav, and must stay open long enough to travel diagonally into a panel item.
 *
 *   - OPEN_DELAY: hover intent. A pointer must dwell on a nav item briefly
 *     before its panel opens, so brushing across the bar (or passing a
 *     neighbour while aiming for a panel item) never thrashes menus open.
 *     Leaving the item before the delay cancels the pending open.
 *   - CLOSE_DELAY: grace period. The panels are DOM descendants of `.ck-nav`,
 *     so moving from a nav item INTO its panel never leaves `.ck-nav`; the
 *     close timer only arms when the pointer leaves the whole nav+panel
 *     region, and re-entering cancels it.
 *   - Keyboard (focusin) opens immediately; Escape / outside-click / focus-out
 *     close. One panel open at a time.
 *   - Coarse pointers (touch/most trackpads report hover:none): the nav item's
 *     first tap opens its panel instead of navigating; a second tap follows
 *     the link. Mouse/precise-hover devices keep click-to-navigate.
 */
(function(){
  var bar = document.querySelector('.ck-topbar');
  if (!bar) return;
  var nav = bar.querySelector('.ck-nav');
  if (!nav) return;
  var groups = Array.prototype.slice.call(bar.querySelectorAll('.ck-nav-group'));
  if (!groups.length) return;
  bar.setAttribute('data-menu-js', '1');   // CSS: open state via .is-open only

  var OPEN_DELAY = 90;     // ms of hover intent before a panel opens
  var CLOSE_DELAY = 220;   // ms grace before closing once the pointer leaves
  var openTimer = null, closeTimer = null, current = null;
  var coarse = false;
  try {
    coarse = !!(window.matchMedia &&
      window.matchMedia('(hover: none), (pointer: coarse)').matches);
  } catch (e) { coarse = false; }

  function cancelOpen(){ if (openTimer){ clearTimeout(openTimer); openTimer = null; } }
  function cancelClose(){ if (closeTimer){ clearTimeout(closeTimer); closeTimer = null; } }
  function closeAll(){
    cancelOpen(); cancelClose();
    groups.forEach(function(g){ g.classList.remove('is-open'); });
    current = null;
  }
  function openOnly(g){            // one panel open at a time
    if (current === g) return;
    groups.forEach(function(x){ if (x !== g) x.classList.remove('is-open'); });
    g.classList.add('is-open');
    current = g;
  }

  groups.forEach(function(g){
    g.addEventListener('mouseenter', function(){
      cancelClose();
      if (current === g) return;
      cancelOpen();
      openTimer = setTimeout(function(){ openOnly(g); }, OPEN_DELAY);
    });
    // Leaving a single group cancels a pending open for it, but does NOT close
    // an already-open panel — that is the nav-region's job (below), so diagonal
    // travel into the panel survives.
    g.addEventListener('mouseleave', cancelOpen);
    g.addEventListener('focusin', function(){ cancelClose(); cancelOpen(); openOnly(g); });

    if (coarse){
      var trigger = g.querySelector('a');
      if (trigger){
        trigger.addEventListener('click', function(e){
          // First tap opens the panel (no navigation); tapping the same item
          // again (panel already open) follows the link.
          if (current !== g){ e.preventDefault(); cancelClose(); openOnly(g); }
        });
      }
    }
  });

  // The whole nav region (nav items + their absolutely-positioned panels, which
  // are DOM descendants of `.ck-nav`) — leaving it arms the grace close,
  // re-entering cancels it.
  nav.addEventListener('mouseleave', function(){
    cancelClose();
    closeTimer = setTimeout(closeAll, CLOSE_DELAY);
  });
  nav.addEventListener('mouseenter', cancelClose);

  // Escape closes everything.
  document.addEventListener('keydown', function(e){ if (e.key === 'Escape') closeAll(); });
  // Any pointer-down NOT inside a nav group closes the menus — covers clicking
  // outside the topbar AND clicking the in-topbar Guide / Search / +New /
  // avatar controls (so a panel never stays stuck over their surfaces).
  document.addEventListener('pointerdown', function(e){
    var t = e.target;
    if (!t || !t.closest || !t.closest('.ck-nav-group')) closeAll();
  });
  // Focus leaving the topbar entirely closes the menus.
  bar.addEventListener('focusout', function(e){ if (!bar.contains(e.relatedTarget)) closeAll(); });
})();
</script>
"""


_PALETTE_JS = """
<script>
/* Cmd+K palette behaviour:
 *   - Cmd/Ctrl+K opens, Esc closes.
 *   - Recent visits (last 8) bubble to the top with a "Recent" header
 *     so a partner can grab yesterday's tool in one keystroke.
 *   - Arrow keys move the highlight; Enter navigates.
 *   - Selecting an item records it in localStorage.ck-palette-recent.
 */
(function(){
  var p = document.getElementById('ck-palette');
  if (!p) return;
  var RECENT_KEY = 'ck-palette-recent';
  var MAX_RECENT = 8;
  var input = p.querySelector('.ck-palette-input');
  var list  = p.querySelector('.ck-palette-list');
  var allItems = Array.from(p.querySelectorAll('li'));
  function loadRecent(){
    try {
      var s = localStorage.getItem(RECENT_KEY);
      return s ? JSON.parse(s) : [];
    } catch (e) { return []; }
  }
  function saveRecent(routes){
    try { localStorage.setItem(RECENT_KEY, JSON.stringify(routes.slice(0, MAX_RECENT))); }
    catch (e) {}
  }
  function rebuild(){
    var recent = loadRecent();
    if (!list) return;
    /* Remove any prior recent header + clones */
    Array.from(list.querySelectorAll('[data-recent-marker]')).forEach(function(el){
      el.parentNode.removeChild(el);
    });
    if (!recent.length) return;
    var header = document.createElement('li');
    header.className = 'cp-section';
    header.setAttribute('data-recent-marker', 'header');
    header.textContent = 'Recent';
    var firstChild = list.firstChild;
    list.insertBefore(header, firstChild);
    /* Insert a clone of each recent item right after header, in order */
    var cursor = header;
    recent.slice().reverse().forEach(function(route){
      var src = allItems.filter(function(li){ return li.getAttribute('data-route') === route; })[0];
      if (!src) return;
      var clone = src.cloneNode(true);
      clone.setAttribute('data-recent-marker', 'item');
      clone.classList.add('cp-recent');
      header.parentNode.insertBefore(clone, header.nextSibling);
    });
    /* Wire clones to the same click + nav behaviour */
    Array.from(list.querySelectorAll('[data-recent-marker="item"]')).forEach(function(li){
      li.addEventListener('click', function(){ navTo(li); });
    });
  }
  function navTo(li){
    var r = li.getAttribute('data-route');
    if (!r) return;
    var rec = loadRecent().filter(function(x){ return x !== r; });
    rec.unshift(r);
    saveRecent(rec);
    window.location.href = r;
  }
  function show(){ rebuild(); p.hidden = false; setTimeout(function(){ input.focus(); }, 0); }
  function hide(){ p.hidden = true; input.value = ''; filter(''); }
  function filter(q){
    q = (q || '').toLowerCase();
    var anyVisible = false;
    Array.from(p.querySelectorAll('li')).forEach(function(li){
      if (li.classList.contains('cp-noresults')) return;
      if (li.classList.contains('cp-section')) {
        /* Show the "Recent" header only when no query is active */
        li.style.display = q ? 'none' : '';
        return;
      }
      var t = li.textContent.toLowerCase();
      var match = t.indexOf(q) >= 0;
      li.style.display = match ? '' : 'none';
      if (match) anyVisible = true;
    });
    /* Toggle the "Nothing matched" row — only when partner has
     * typed something and zero items are visible. */
    var empty = p.querySelector('[data-rcm-palette-empty]');
    if (empty) empty.hidden = !(q && !anyVisible);
  }
  function visibleItems(){
    return Array.from(p.querySelectorAll('li:not([style*="display: none"])'))
      .filter(function(li){
        return !li.classList.contains('cp-section')
            && !li.classList.contains('cp-noresults');
      });
  }
  function highlightAt(idx){
    var items = visibleItems();
    items.forEach(function(li, i){
      if (i === idx) {
        li.classList.add('is-highlighted');
        /* Keep highlighted row in view inside the scrollable list */
        if (li.scrollIntoView) {
          li.scrollIntoView({ block: 'nearest' });
        }
      } else {
        li.classList.remove('is-highlighted');
      }
    });
  }
  function moveHighlight(delta){
    var items = visibleItems();
    if (!items.length) return;
    var cur = items.findIndex(function(li){
      return li.classList.contains('is-highlighted');
    });
    var next = ((cur < 0 ? 0 : cur + delta) + items.length) % items.length;
    highlightAt(next);
  }
  function pickHighlighted(){
    var items = visibleItems();
    var hit = items.find(function(li){
      return li.classList.contains('is-highlighted');
    }) || items[0];
    if (hit) navTo(hit);
  }
  input.addEventListener('input', function(e){
    filter(e.target.value);
    /* Reset highlight to first visible after any filter change */
    highlightAt(0);
  });
  allItems.forEach(function(li){
    li.addEventListener('click', function(){ navTo(li); });
    li.addEventListener('mouseenter', function(){
      var items = visibleItems();
      highlightAt(items.indexOf(li));
    });
  });
  document.addEventListener('keydown', function(e){
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      show();
      /* Highlight first visible on open so Enter has a target */
      setTimeout(function(){ highlightAt(0); }, 0);
    }
    if (e.key === 'Escape' && !p.hidden) { e.preventDefault(); hide(); }
    if (!p.hidden) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        moveHighlight(1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        moveHighlight(-1);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        pickHighlighted();
      }
    }
  });
})();
</script>
"""


# Map raw active_nav values (as passed by page renderers) to a sub-nav
# section key. Keys can arrive as bare-key ("home"), leading-slash
# ("/portfolio"), or a sub-path ("/portfolio/monitor", "/analysis").
# Mapping is intentionally explicit so a typo doesn't silently route to
# the wrong section.
_SUB_SECTION_MAP = {
    # bare keys
    "home": "home", "pipeline": "pipeline", "library": "library",
    "research": "research", "portfolio": "portfolio",
    "diligence": "diligence", "source": "source",
    "alerts": "home", "escalations": "home", "watchlist": "home",
    # All /diligence/* sub-paths land in the Diligence section so
    # the RCM playbook flow keeps a consistent active subnav.
    "/diligence": "diligence",
    "/screening/bankruptcy-survivor": "diligence",
    "/engagements": "diligence",
    # leading-slash forms
    "/home": "home", "/app": "home", "/alerts": "home",
    "/escalations": "home", "/watchlist": "home", "/my": "home",
    # Source = target discovery. Target Screener anchors it; Deal Sourcing +
    # Conferences live here now.
    # Source = target discovery (incl. the CMS screeners + thesis screening).
    "/target-screener": "source", "/source": "source", "/conferences": "source",
    "/screen": "source", "/predictive-screener": "source",
    "/deal-screening": "source",
    # Geographic Intelligence trio — real-data origination screening.
    "/geo-intel": "source", "/state-compare": "source",
    "/state-rankings": "source", "/state-profile": "source",
    "/state-peers": "source", "/county-explorer": "source",
    "/geo-metrics": "source", "/metro-markets": "source",
    "/geo-map": "source",
    # Pipeline = real deal-workflow surfaces only.
    "/pipeline": "pipeline", "/new-deal": "pipeline", "/deal-pipeline": "pipeline",
    "/deal-quality": "pipeline", "/deal-risk-scores": "pipeline",
    "/deal-flow-heatmap": "pipeline", "/pipeline/bridge": "pipeline",
    # Moved to Research: Find Comps (corpus comps) + PE Intelligence (generic).
    "/find-comps": "research", "/pe-intelligence": "research",
    "/library": "library", "/deals-library": "library", "/deal-library": "library",
    "/deal-library/sponsors": "library", "/deal-library/comps": "library",
    "/methodology": "library", "/metric-glossary": "library",
    "/data": "library", "/comparables": "library",
    "/market-rates": "library", "/data-catalog": "library",
    "/rcm-benchmarks": "library",
    "/research": "research", "/notes": "research", "/industry": "research",
    "/market-intel/geo": "research",
    "/sector-momentum": "research", "/irr-dispersion": "research",
    "/hold-analysis": "research", "/backtest": "research",
    "/comparable-outcomes": "research", "/bear-cases": "research",
    "/regulatory-calendar": "research", "/market-intel": "research",
    "/corpus-backtest": "research",
    # Some renderers still pass legacy /diligence/* active_nav values;
    # map them to the same editorial section the wired URL belongs to.
    "/diligence/comparable-outcomes": "research",
    "/diligence/regulatory-calendar": "research",
    "/diligence/bear-case": "research",
    "/diligence/bear-cases": "research",
    "/portfolio": "portfolio", "/lp-update": "portfolio",
    # Moved to Research as Deal Corpus Analytics (benchmark corpus, not portfolio).
    "/deal-corpus-analytics": "research",
    "/portfolio-analytics": "research",
    # Moved to Research — reference/corpus data, not the user's portfolio.
    "/sponsor-track-record": "research",
    "/payer-intelligence": "research",
    # cross-section common deep paths
    "/analysis": "research", "/quant-lab": "research",
    "/market-data/map": "library",
}


def _resolve_sub_section(active_nav: Optional[str]) -> Optional[str]:
    """Pick the sub-nav section key for an active_nav value.

    Resolution order:
      1. Exact match in ``_SUB_SECTION_MAP``.
      2. First path segment match (``/portfolio/monitor`` → ``/portfolio``).
      3. Path-prefix match — any path starting with a key in the map
         resolves to that section. Used so every ``/diligence/*``
         renderer lands the user in the Diligence subnav without
         each file having to enumerate the active_nav string.
    """
    if not active_nav:
        return None
    key = str(active_nav).strip().lower()
    if key in _SUB_SECTION_MAP:
        return _SUB_SECTION_MAP[key]
    if key.startswith("/"):
        first = "/" + key.lstrip("/").split("/", 1)[0]
        if first in _SUB_SECTION_MAP:
            return _SUB_SECTION_MAP[first]
        # Path-prefix fallback (longest match wins) so e.g.
        # "/diligence/deal-mc" → "/diligence" → "diligence" without
        # listing every sub-path.
        for prefix in sorted(
            (k for k in _SUB_SECTION_MAP if k.startswith("/") and "/" in k[1:]),
            key=len, reverse=True,
        ):
            if key.startswith(prefix):
                return _SUB_SECTION_MAP[prefix]
    return None


def _topbar(active_nav: Optional[str], user_initials: str = "AT") -> str:
    """Editorial topbar mirroring chartis.com chrome.

    Navy background, white wordmark with italic ``Chartis``, uppercase
    nav links with teal active underline, search anchored to the
    right with a teal-on-navy user chip. The thin teal stripe on the
    bottom edge is a Chartis signature.

    When ``active_nav`` matches a key in ``_SUB_NAV``, a parchment
    sub-nav rail renders directly below with the section's most-clicked
    second-level pages — saves a partner the click into a section
    landing page just to find a common surface.
    """
    # Nav labels are workspace-mode-aware so a viewer sees the
    # vocabulary shift (Deals → Engagements, Portfolio → Engagement Book)
    # the moment they toggle to the Chartis-consulting workspace.
    from ._workspace_mode import term as _ws_term
    from .brand import BRAND_MARK_SVG as _BRAND_MARK_SVG
    _NAV_TERM = {"Deals": "deals", "Portfolio": "portfolio"}

    def _nav_label(lbl: str) -> str:
        return _ws_term(_NAV_TERM[lbl]) if lbl in _NAV_TERM else lbl

    # Chevron on nav items that open a section sub-nav (per handoff). A caret
    # appears when the item's key resolves to a _SUB_NAV section.
    def _section_of(item):
        # The section key whose sub-nav this item opens, or None (Home is the
        # dashboard root and never opens a dropdown).
        if item.get("key") == "home":
            return None
        sect = _resolve_sub_section(item.get("key") or item.get("href"))
        return sect if (sect and sect in _SUB_NAV) else None

    def _nav_item(item) -> str:
        # Each section item is a hover/focus group: the nav anchor plus a
        # dropdown menu of its sub-pages. The anchor markup is kept identical
        # to the legacy bare-link form (label + caret inside the <a>) so the
        # active/caret fidelity guards still hold; the dropdown replaces the
        # old persistent second-line sub-nav rail.
        sect = _section_of(item)
        caret = ('<span class="ck-nav-caret" aria-hidden="true">▾</span>'
                 if sect else "")
        anchor = (
            f'<a href="{_esc(item["href"])}" '
            f'class="{"active" if item["key"] == active_nav else ""}">'
            f'{_esc(_nav_label(item["label"]))}{caret}</a>'
        )
        if not sect:
            return anchor
        # Numbered destination items (right grid) — each reads like a real
        # destination: index · label · one-line description. Ordered by the
        # surface ranking (usefulness-weighted) and capped at the top 6, with a
        # "More →" to the full ranked /best/<section> index — so each bar leads
        # with its strongest pages and "show more" opens the ranked catalogue.
        _top, _has_more = _ranked_subnav_items(sect)
        # Exactly the 6 ranked leaves fill the 3×2 listing grid (real routes +
        # vetted one-line descriptions — no fabricated copy).
        items = "".join(
            f'<a href="{_esc(s["href"])}" class="ck-mega-item" role="menuitem">'
            f'<span class="ck-mega-idx">{i:02d}.</span>'
            f'<span class="ck-mega-it-body"><span class="ck-mega-it-label">'
            f'{_esc(s["label"])}</span>'
            f'<span class="ck-mega-it-desc">{_esc(_NAV_DESC.get(s["href"], ""))}</span>'
            f'</span></a>'
            for i, s in enumerate(_top, start=1)
        )
        # Featured left panel — the "what is this section" card. Honest,
        # descriptive copy only (eyebrow / title / blurb from _SECTION_FEATURE,
        # no fabricated stats). The headline italicises + greens its last word
        # (design treatment) using only the real section title.
        feat = _SECTION_FEATURE.get(sect, {})
        _title = str(feat.get("title") or item["label"])
        _head, _, _tail = _title.rpartition(" ")
        _title_html = (
            f'{_esc(_head)} <em>{_esc(_tail)}</em>' if _head
            else f'<em>{_esc(_title)}</em>'
        )
        # The lede card is one clickable link to the section landing (kicker ·
        # headline · pull-quote); the explicit CTA below it is "All X tools".
        # No separate "Open X →" line — it stacked awkwardly with the all-tools
        # CTA and cluttered the column.
        feature = (
            '<a class="ck-mega-feat" href="' + _esc(feat.get("href", item["href"])) + '">'
            '<span class="ck-mega-kicker">'
            '<span class="ck-mega-dot" aria-hidden="true"></span>'
            f'<span class="ck-mega-feat-eyebrow">{_esc(feat.get("eyebrow", ""))}</span></span>'
            f'<span class="ck-mega-feat-title">{_title_html}</span>'
            f'<span class="ck-mega-feat-blurb">{_esc(feat.get("blurb", ""))}</span>'
            '</a>'
        )
        # All-tools link — sits at the FAR-RIGHT bottom of the listing column,
        # inside the links box (not a separate full-width footer chunk), in
        # green. Normal flow below the leaves → never overlaps anything.
        all_tools = (
            f'<a href="/best/{_esc(sect)}" class="ck-mega-all" role="menuitem">'
            f'All {_esc(_nav_label(item["label"]))} tools '
            '<span class="ck-mega-all-arr" aria-hidden="true">&rarr;</span></a>'
        )
        return (
            '<div class="ck-nav-group" aria-haspopup="true">'
            f'{anchor}'
            f'<div class="ck-nav-menu ck-nav-mega" role="menu" '
            f'aria-label="{_esc(_nav_label(item["label"]))} menu">'
            '<div class="ck-mega-inner">'
            f'<div class="ck-mega-lede">{feature}</div>'
            '<div class="ck-mega-listing">'
            f'<div class="ck-mega-items">{items}</div>'
            f'{all_tools}'
            '</div>'
            '</div>'
            '</div>'
            '</div>'
        )

    links = "".join(_nav_item(item) for item in _CORPUS_NAV)

    # Sub-nav rail. Page renderers historically pass active_nav in
    # mixed conventions: bare key ("home"), leading-slash path
    # ("/portfolio"), or a sub-path ("/portfolio/monitor",
    # "/analysis"). Normalise to a section key so we can look up
    # _SUB_NAV regardless of caller. Falls back to nothing if the
    # section has no entry (e.g. /login, /admin, debug pages).
    # Workspace-mode label for the user-dropdown quick-switch item.
    from ._workspace_mode import current_workspace_mode, MODE_LABELS
    _ws_mode_label = MODE_LABELS.get(
        current_workspace_mode(), "PE Partner",
    )

    # The section sub-nav now lives in the hover/focus dropdown built per nav
    # item above (no persistent second-line rail under the topbar).
    return (
        '<header class="ck-topbar">'
        '<div class="ck-topbar-inner">'
        '<a href="/" class="ck-wordmark" aria-label="PE Desk home">'
        f'{_BRAND_MARK_SVG}'
        '<span class="ck-wordmark-text">PE<em>Desk</em></span>'
        '</a>'
        f'<nav class="ck-nav" aria-label="Primary">{links}</nav>'
        '<div class="ck-topbar-right">'
        # Always-visible workspace-mode chip so the active interface
        # (PE Partner vs Chartis Consulting) is obvious on every page,
        # not buried in the user dropdown. data-mode drives the accent.
        f'<a class="ck-mode-chip" href="/settings/workspace" '
        f'data-mode="{_esc(current_workspace_mode())}" '
        f'title="Workspace: {_esc(_ws_mode_label)} — click to switch">'
        f'{_esc(_ws_mode_label)}</a>'
        # Portfolio-wide diligence-questions pill. JS-hydrated from
        # all rcm_deal_*_questions entries on DOMContentLoaded;
        # hidden when zero open across the portfolio. Click → ledger.
        '<a class="ck-topbar-qpill" data-ck-qpill href="/diligence/questions" '
        'aria-label="Open diligence questions ledger" hidden>'
        '<span class="ck-topbar-qpill-num" data-ck-qpill-num>0</span>'
        '<span class="ck-topbar-qpill-label">open Qs</span>'
        '</a>'
        # Search launcher first, then Guide — matching the handoff's
        # search · Guide · +New · avatar right-zone order. Visible
        # placeholder is short so it never truncates in the 220px field;
        # the descriptive label stays on aria-label for screen readers.
        '<form class="ck-search-form" action="/search" method="get" role="search">'
        '<input class="ck-search" type="search" name="q" '
        'placeholder="Search…" '
        'aria-label="Search deals, hospitals, routes" />'
        '<kbd class="ck-search-kbd" aria-hidden="true">⌘K</kbd>'
        '</form>'
        # PEdesk Guide trigger — opens the read-only context sidebar. The
        # green italic-serif "?" glyph is the handoff accent that makes the
        # button read as live, not washed out. Panel + behavior are injected
        # at shell level (see _GUIDE_*).
        '<button class="ck-guide-trigger" type="button" data-ck-guide-open '
        'aria-haspopup="dialog" aria-controls="ck-guide-panel" '
        'title="PEdesk Guide — explain this page">'
        '<span class="ck-guide-glyph" aria-hidden="true">?</span>Guide</button>'
        # + New deal — primary CTA. No dedicated /deals/new route exists yet,
        # so it routes to the Pipeline section (deal sourcing/origination)
        # rather than inventing a flow or shipping a broken link.
        '<a class="ck-newdeal-cta" href="/pipeline" '
        'title="Start a new deal in the pipeline">+ New deal</a>'
        '<div class="ck-user-menu">'
        f'<button class="ck-user-chip" type="button" aria-haspopup="true" '
        f'aria-expanded="false" title="Signed in" '
        f'data-ck-user-toggle>{_esc(user_initials)}</button>'
        '<div class="ck-user-dropdown" hidden>'
        # Recently-viewed deals — populated client-side from
        # localStorage by _USER_MENU_JS. Hidden when empty.
        '<div class="ck-user-recent" data-ck-recent-deals hidden>'
        '<div class="ck-user-recent-head">Recent deals</div>'
        '<div class="ck-user-recent-list" data-ck-recent-list></div>'
        '</div>'
        '<a href="/my/AT" class="ck-user-dropdown-item">My Dashboard</a>'
        '<a href="/tools" class="ck-user-dropdown-item">All Tools &middot; ⌘K</a>'
        '<a href="/methodology" class="ck-user-dropdown-item">Methodology</a>'
        f'<a href="/settings/workspace" class="ck-user-dropdown-item">'
        f'Workspace: {_esc(_ws_mode_label)}</a>'
        '<a href="/users" class="ck-user-dropdown-item">Admin</a>'
        '<a href="/audit" class="ck-user-dropdown-item">Audit Log</a>'
        '<div class="ck-user-dropdown-divider"></div>'
        '<button type="button" class="ck-user-dropdown-item" '
        'data-ck-intro-toggle>Tutorial intros: off</button>'
        '<button type="button" class="ck-user-dropdown-item" '
        'data-ck-shortcuts-open>Keyboard shortcuts &middot; ?</button>'
        '<div class="ck-user-dropdown-divider"></div>'
        '<form action="/api/logout" method="post" class="ck-user-dropdown-form">'
        '<button type="submit" class="ck-user-dropdown-item ck-user-dropdown-logout">'
        'Sign out</button>'
        '</form>'
        '</div>'
        '</div>'
        "</div>"
        "</div>"
        "</header>"
    )


def _breadcrumbs(crumbs: Optional[Sequence[Any]]) -> str:
    """Render breadcrumb nav from either tuple-shape or dict-shape crumbs.

    Callers pass either ``[("Home", "/"), ("Page", None)]`` (login_page,
    app_page) or ``[{"label": "Home", "href": "/"}, ...]`` (older
    convention). Normalise to a label/href pair before rendering so
    GET /app stops 500ing on tuple-shaped breadcrumbs.
    """
    if not crumbs:
        return ""
    parts = []
    for i, c in enumerate(crumbs):
        # Normalise to (label, href)
        if isinstance(c, tuple) or isinstance(c, list):
            label = c[0] if len(c) > 0 else ""
            href = c[1] if len(c) > 1 else None
        elif isinstance(c, Mapping):
            label = c.get("label", "")
            href = c.get("href")
        else:
            # Unknown shape — render as plain text rather than crash
            label, href = str(c), None
        if i:
            parts.append('<span class="sep">/</span>')
        if href:
            parts.append(f'<a href="{_esc(href)}">{_esc(label)}</a>')
        else:
            parts.append(_esc(label))
    return f'<nav class="ck-breadcrumbs">{"".join(parts)}</nav>'


# Global ~2% size trim ("everything a little too big"). A single root zoom
# scales fonts, spacing, and chrome uniformly — far safer than re-tuning
# hundreds of px values. Screen-only so print output is unaffected; loaded
# AFTER the base CSS and BEFORE per-page extra_css so a page can still override
# if it ever needs to. Modern browsers (Chrome/Edge/Safari/Firefox 126+)
# support `zoom`; older engines simply render at 100% (graceful).
_GLOBAL_SCALE_CSS = "<style>@media screen{html{zoom:0.98;}}</style>"


def chartis_shell(
    body_html: Optional[str] = None,
    title: Optional[str] = None,
    *,
    body: Optional[str] = None,  # legacy alias for body_html — accept
                                  # so partially-migrated callers don't
                                  # 500 with "missing positional argument"
    active_nav: Optional[str] = None,
    breadcrumbs: Optional[Sequence[Mapping[str, str]]] = None,
    code: Optional[str] = None,           # e.g. "[EBT-07]" for debug overlay
    user_initials: str = "AT",
    include_palette: bool = True,
    palette_modules: Optional[Iterable[Mapping[str, str]]] = None,
    # Compatibility kwargs accepted by partially-migrated callers.
    # Forwarded to the legacy shell when v2 is off; rendered as
    # best-effort no-ops or simple chrome additions in v2 mode.
    subtitle: Optional[str] = None,
    show_chrome: bool = True,
    show_sidebar: bool = False,
    # Page-specific styles injected into <head>. login_page and
    # forgot_page rely on this to land their grid + panel CSS;
    # without it, content stacks as one unstyled column.
    extra_css: Optional[str] = None,
    # Page-specific JS injected before </body>. analysis_workbench
    # ships its tab-switching + scenario-form + explain-panel
    # handlers via this kwarg — without it the RCM Profile tab
    # (and every other workbench tab) was inert.
    extra_js: Optional[str] = None,
    # Editorial PHI-banner toggle (consumed by the editorial
    # variant). No-op in this v2 shell.
    show_phi_banner: bool = False,
    phi_mode: Optional[str] = None,
    # Cycle 20 — convenience kwarg that auto-prepends
    # ``ck_section_intro(**editorial_intro)`` to ``body_html`` so a
    # page can adopt the chartis cadence (italic-serif headline +
    # eyebrow + body) with one kwarg instead of restructuring its
    # render function. Use cases: every legacy renderer that's
    # already on chartis_shell but missing the editorial-cadence
    # intro signal.
    editorial_intro: Optional[Mapping[str, Any]] = None,
    **_extra: Any,
) -> str:
    """Render a full page. Drop-in replacement for the legacy dark shell.

    All kwargs are optional and match or extend the previous signature.
    Unknown kwargs (\\*\\*_extra) are accepted silently for forward-compat
    with partially-migrated callers — every page renders rather than 500.
    """
    # Accept legacy ``body=`` kwarg as an alias for ``body_html``.
    # A handful of pages were ported with the wrong kwarg name and
    # 500'd with "missing positional argument" until 2026-04-29.
    if body_html is None and body is not None:
        body_html = body
    if body_html is None:
        body_html = ""
    if title is None:
        title = "PE Desk"

    fonts = (
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?'
        'family=Source+Serif+4:ital,wght@0,400;0,500;0,600;1,400&'
        'family=Inter+Tight:wght@400;500;600;700&'
        'family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">'
    )
    palette_html = ""
    if include_palette:
        # Use the platform-wide default tools index if the caller
        # didn't pass a curated list. Lets every editorial page jump
        # to any tool via Cmd+K without each renderer having to
        # re-enumerate the palette.
        modules_to_use = palette_modules or _DEFAULT_PALETTE_MODULES
        palette_html = ck_command_palette(modules_to_use)
    debug_tag = f'<div class="ck-debug-code">[{_esc(code)}]</div>' if code else ""
    # show_chrome=False: bare pages (login / forgot) without topnav
    chrome_html = (
        f"{_topbar(active_nav, user_initials)}"
        f"{_breadcrumbs(breadcrumbs)}"
    ) if show_chrome else ""
    # subtitle: render under the page heading inside <main>. Note —
    # when the shell auto-injects ck_page_title (because the page
    # passed editorial_intro= and/or ck_section_intro in the body),
    # the subtitle text gets folded into the title's meta line.
    # In that case the standalone subtitle_html below is suppressed
    # so the same string doesn't render twice (an italic line at the
    # very top + a duplicate inside the title meta).
    subtitle_consumed_by_title = False
    main_class = "ck-main ck-with-sidebar" if show_sidebar else "ck-main"
    # PHI-mode marker for compliance tooling. The /app route forwards
    # RCM_MC_PHI_MODE as phi_mode=; emit it as a data-attribute on the
    # main element (the shell migration to this module had dropped the
    # attribute that _chartis_kit_editorial.py used to render).
    _phi_attr = (
        f' data-phi-mode="{_esc(phi_mode)}"' if phi_mode else ""
    )
    # ``editorial_intro`` auto-prepends a ck_section_intro block to
    # the page body. Lets a legacy renderer adopt the chartis cadence
    # (italic-serif headline) with a single kwarg instead of
    # restructuring its render function — much lower-friction port
    # for the 60-69 fidelity-tier.
    #
    # Missing-title bugfix: 74 pages pass editorial_intro= without
    # also calling ck_page_title() in their body, so they render
    # WITHOUT a page H1 (just the section-intro italic headline).
    # When editorial_intro is provided AND the body doesn't already
    # carry a ck-page-title, auto-prepend a real page title using
    # the page's `title` + the editorial_intro's eyebrow + the
    # subtitle. The original ck_section_intro still renders below,
    # acting as the editorial deck under the H1.
    intro_html = ""
    if editorial_intro:
        if 'class="ck-page-title"' not in body_html:
            page_eyebrow = editorial_intro.get("eyebrow")
            intro_html += ck_page_title(
                title,
                eyebrow=page_eyebrow,
                meta=subtitle if subtitle else None,
            )
            if subtitle:
                subtitle_consumed_by_title = True
        intro_html += ck_section_intro(**editorial_intro)
    # Second pass — pages that call ck_section_intro DIRECTLY in
    # their body (instead of via the editorial_intro kwarg) still
    # render without an H1: bear_case, covenant_lab, payer_stress,
    # bridge_audit, regulatory_calendar, ic_memo, day_one,
    # portfolio_monitor, regression — partners see a bare italic
    # deck headline floating at the top with no page title above
    # it. Auto-inject ck_page_title using the shell's `title` arg
    # when the body clearly signals editorial cadence
    # (ck-section-intro) but has no ck-page-title yet.
    if (
        title
        and title != "PE Desk"
        and 'class="ck-page-title"' not in body_html
        and 'class="ck-section-intro"' in body_html
        and not intro_html
    ):
        intro_html = ck_page_title(
            title,
            meta=subtitle if subtitle else None,
        )
        if subtitle:
            subtitle_consumed_by_title = True
    body_html = intro_html + body_html

    # Route-level illustrative disclosure. Pages on the data_public analyzer
    # surface render realistic numbers from the bundled seed corpus / modeled
    # assumptions, not the user's ingested data. Auto-inject one honest banner
    # for any registered route — idempotent: skip if the page already rendered
    # its own ck-illus-note (per-page labels) so we never double-disclose.
    if (_is_illustrative_route(active_nav)
            and "ck-illus-note" not in body_html):
        body_html = ck_illustrative_note(_ILLUSTRATIVE_ROUTE_NOTE) + body_html

    # Render the standalone subtitle_html only when the shell did
    # NOT auto-inject the subtitle into a ck_page_title AND the
    # body doesn't already carry a ck_page_title (which carries
    # its own meta line). Otherwise the subtitle text rendered
    # both as an italic line at the very top AND inside the title
    # meta — the duplicate partners flagged on physician-eu /
    # market-analysis / many other pages.
    body_has_page_title = 'class="ck-page-title"' in body_html
    subtitle_html = (
        f'<div class="ck-subtitle" style="font-size:13px;'
        f'color:var(--ck-text-muted,#5C6878);margin:0 0 14px;'
        f'font-style:italic;">{_esc(subtitle)}</div>'
    ) if (
        subtitle
        and not subtitle_consumed_by_title
        and not body_has_page_title
    ) else ""
    # Page-specific CSS goes AFTER the kit's CSS so page styles
    # win specificity ties — matches the contract login_page.py
    # and forgot_page.py expect (grid layout, panel chrome, etc.)
    extra_css_html = (
        f"<style>{extra_css}</style>" if extra_css else ""
    )
    # Page-specific JS sits at the end of body so the kit's
    # standard handlers (CSRF, user-menu, etc.) load first and
    # the page can rely on the DOM being parsed.
    extra_js_html = (
        f"<script>{extra_js}</script>" if extra_js else ""
    )
    # PEdesk Guide sidebar rides on the global chrome only (it needs the
    # topbar trigger). Login / forgot / bare pages don't get it.
    guide_html = (
        f"{_GUIDE_CSS}{_GUIDE_PANEL_HTML}{_GUIDE_JS}" if show_chrome else ""
    )
    return (
        "<!doctype html>"
        '<html lang="en"><head>'
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{_esc(title)} · PE Desk</title>"
        '<link rel="icon" type="image/svg+xml" href="/favicon.svg">'
        f"{fonts}"
        f"{_CSS_LINK}"
        f"{_CSS_INLINE_FALLBACK}"
        f"{_GLOBAL_SCALE_CSS}"
        f"{extra_css_html}"
        "</head><body>"
        f"{chrome_html}"
        f'<main class="{main_class}"{_phi_attr}>{debug_tag}{subtitle_html}{body_html}</main>'
        f"{palette_html}"
        f"{_SHORTCUTS_HTML}"
        f"{_TOAST_HTML}"
        f"{ck_default_tour()}"
        f"{ck_quick_capture()}"
        f"{_CSRF_JS}"
        f"{_USER_MENU_JS}"
        f"{_NAV_MENU_JS}"
        f"{_QPILL_JS}"
        f"{_INTRO_DISMISS_JS}"
        f"{_PALETTE_JS}"
        f"{_SHORTCUTS_JS}"
        f"{_TOAST_JS}"
        f"{_SORT_JS}"
        f"{_TABLE_FILTER_JS}"
        f"{_TABLE_COPY_JS}"
        f"{_TABLE_BARS_JS}"
        f"{_TABLE_TOTALS_JS}"
        f"{_BARROW_HOVER_CSS}"
        f"{guide_html}"
        f"{extra_js_html}"
        "</body></html>"
    )


__all__ = [
    "P",
    "UI_V2_ENABLED",
    "_CORPUS_NAV",
    "_LEGACY_NAV",
    "chartis_shell",
    "ck_panel",
    "ck_section_header",
    "ck_table",
    "ck_empty_state",
    "ck_kpi_block",
    "ck_value_anchor",
    "ck_scatter",
    "ck_narrative_band",
    "ck_page_title",
    "ck_signal_badge",
    "ck_command_palette",
    "ck_fmt_currency",
    "ck_fmt_percent",
    "ck_fmt_number",
]

# Compatibility alias for partially-migrated chartis pages
editorial_chartis_shell = chartis_shell
