"""SeekingChartis — Chartis Kit (editorial port).

The editorial-style replacement for the dark Bloomberg shell in
``_chartis_kit_legacy``. Produces parchment + serif + teal markup
matching the four reference HTML files in
``docs/design-handoff/reference/``.

This module is the v3 port of the (deleted) ``_chartis_kit_v2.py``,
which held the OLD reverted reskin's palette. The values here come
from ``docs/design-handoff/EDITORIAL_STYLE_PORT.md`` §3 + §4.

Public API (must match ``_chartis_kit_legacy`` 1:1 — every existing
page renderer imports through ``_chartis_kit.py`` which dispatches
between legacy and editorial based on ``CHARTIS_UI_V2`` / per-request
flag added in commit 5):

Re-exported from legacy (unchanged):
  _CORPUS_NAV, _LEGACY_NAV, _MONO, _SANS
  ck_table, ck_kpi_block, ck_section_header
  ck_signal_badge, ck_grade_badge, ck_regime_badge
  ck_fmt_num, ck_fmt_pct, ck_fmt_moic, ck_fmt_currency, ck_fmt_irr

Editorial-defined (this module):
  P                            editorial palette dict
  ck_panel(body, *, title, code) → str
                               white card using .editorial-panel CSS
  ck_command_palette(modules) → str
                               placeholder ("" until ⌘K wires up)
  ck_fmt_number(value, precision)  v2-named alias for ck_fmt_num
  ck_fmt_percent(value, precision) v2-named alias for ck_fmt_pct
  chartis_shell(body, title, *, active_nav, subtitle, extra_css,
                extra_js, breadcrumbs, code,
                show_chrome, show_phi_banner, phi_mode) → str

  pair_block(viz_html, *, label, source, data_table) → str
                               paired viz+dataset block (spec §5)
  phi_banner(mode) → str       §7.5 banner. Pure of `mode`; caller
                               reads RCM_MC_PHI_MODE in handler and
                               passes the trimmed lower value here.
  editorial_topbar(active_nav) → str
  editorial_crumbs(items) → str
  editorial_page_head(*, eyebrow, title, lede, meta) → str
                               eyebrow is Sequence[(text, kind)]
                               where kind is None or 'slug' (mono).
                               · separators rendered centrally so
                               every page's eyebrow is consistent.

Atoms (drop-in equivalents of cc-components.jsx):

  covenant_pill(status) → str         SAFE/WATCH/TRIP → green/amber/red
  stage_pill(stage) → str             Hold/IOI/LOI/SPA/Closed/Exit
  number_maybe(v, *, format, tone) → str
                                       formats: moic, pct, ev, drift
  sparkline_svg(values, *, color) → str
                                       100×22 inline SVG path

ck_related_views(items) is defined in the dispatcher
(_chartis_kit.py) at module level, NOT here — it's available in
both shells because its visual treatment uses palette tokens that
exist in both. No editorial override is needed.

For the heavy helpers (ck_table, ck_kpi_block, ck_section_header,
ck_signal_badge, ck_grade_badge, ck_regime_badge), this module
re-exports the legacy implementations unchanged. As later phases
port specific page surfaces, those surfaces will use the editorial
chrome (chartis_shell + pair_block + atoms) and gradually replace
ck_table calls with editorial-native markup. The mixed state during
the transition is acceptable: the editorial shell + .pair pattern
produces the visual identity; the older helpers render their cells
with legacy ck_* CSS that the editorial CSS doesn't fight (different
class namespaces).
"""
from __future__ import annotations

import html as _html
import os as _os
from datetime import datetime, timezone
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple, Union

# ── Re-exports from legacy (heavy helpers, unchanged in Phase 1) ────

from ._chartis_kit_legacy import (  # noqa: F401
    _CORPUS_NAV,
    _CORPUS_NAV_LEGACY as _LEGACY_NAV,
    _MONO,
    _SANS,
    ck_fmt_currency,
    ck_fmt_irr,
    ck_fmt_moic,
    ck_fmt_num,
    ck_fmt_pct,
    ck_grade_badge,
    ck_kpi_block,
    ck_regime_badge,
    ck_section_header,
    ck_signal_badge,
    ck_table,
)


# ── ck_panel: editorial implementation ────────────────────────────
#
# Renders a white card inside the parchment page using the
# .editorial-panel CSS class (defined in /static/v3/chartis.css).
# Class is namespaced as `editorial-panel`, NOT plain `.panel`,
# because the dashboard reference HTML (04-command-center.html) has
# its own .panel with different padding behavior. Both classes
# coexist; ck_panel picks the editorial one.
#
# Why a class, not inline styles: inline styles are uneditable from
# CSS, can't grow hover/responsive variants without Python changes,
# and don't compose with the rest of the editorial type/spacing
# scale. The class costs ~20 lines of CSS and pays for itself the
# first time anyone wants a visual variant.

def ck_panel(
    body_html: str,
    *,
    title: Optional[str] = None,
    code: Optional[str] = None,
) -> str:
    """Editorial panel: white card inside the parchment page.

    Args:
        body_html: Inner HTML. Already HTML-safe.
        title: Optional uppercase eyebrow above the body.
        code: Optional source-file path rendered in mono teal.

    All visual styling lives in .editorial-panel CSS.
    """
    head_html = ""
    if title or code:
        title_span = (
            f'<span class="ttl">{_html.escape(title)}</span>'
            if title else '<span class="ttl"></span>'
        )
        code_span = (
            f'<span class="src">{_html.escape(code)}</span>'
            if code else ""
        )
        head_html = f'<div class="head">{title_span}{code_span}</div>'
    return (
        '<section class="editorial-panel">'
        f'{head_html}'
        f'<div class="body">{body_html}</div>'
        '</section>'
    )


# ── Editorial palette (mirrors :root in chartis.css) ───────────────

P: dict = {
    # surfaces
    "bg":            "#F2EDE3",
    "bg_alt":        "#ECE5D6",
    "bg_tint":       "#E8E0D0",
    "paper":         "#FAF7F0",
    "paper_pure":    "#FFFFFF",
    # rules
    "border":        "#D6CFC0",
    "border_strong": "#C2B9A6",
    "rule":          "#BFB6A2",
    # ink
    "ink":           "#0F1C2E",
    "ink_2":         "#1A2840",
    "muted":         "#5C6878",
    "faint":         "#8A92A0",
    # accent
    "teal":          "#1F7A75",
    "teal_soft":     "#D4E4E2",
    "teal_deep":     "#155752",
    # status
    "green":         "#3F7D4D",
    "green_soft":    "#DCE6D9",
    "amber":         "#B7791F",
    "amber_soft":    "#EFE2BC",
    "red":           "#A53A2D",
    "red_soft":      "#EBD3CD",
    "blue":          "#2C5C84",
    "blue_soft":     "#D6E1EB",
    # legacy aliases — callers from the dark-shell era reach for P["panel"],
    # P["positive"] etc. Editorial doesn't conceptualize the same way (no
    # dark cards, no separate "positive" status), but the keys must
    # resolve to SOMETHING or every dark-era page crashes with KeyError
    # when CHARTIS_UI_V2=1 flips the dispatcher. Each alias maps to the
    # closest editorial visual role.
    #
    # Phase 5 cleanup sweeps these once every page has been ported to
    # native editorial keys (Q5.1, registered in UI_REWORK_PLAN.md when
    # Phase 5 begins).
    #
    # Audit 2026-04-25 found 193 of 291 routes 500'd in editorial mode
    # with KeyError on these keys. Adding the alias block fixed it.
    "accent":        "#155752",      # → teal_deep
    "accent_soft":   "#D4E4E2",      # → teal_soft
    "panel":         "#FFFFFF",      # → paper_pure (white card on parchment)
    "panel_alt":     "#FAF7F0",      # → paper (slightly off-white)
    "border_dim":    "#D6CFC0",      # → border (editorial has one border weight)
    "text":          "#0F1C2E",      # → ink (primary editorial text)
    "text_dim":      "#5C6878",      # → muted
    "text_faint":    "#8A92A0",      # → faint
    "positive":      "#3F7D4D",      # → green
    "negative":      "#A53A2D",      # → red
    "warning":       "#B7791F",      # → amber
    "critical":      "#A53A2D",      # → red (editorial has one severity-red, not two)
    "row_stripe":    "#E8E0D0",      # → bg_tint (subtle parchment stripe)
}


# ── v2-named formatter aliases (callers that import them by either name) ──

def ck_fmt_number(value, precision: int = 1) -> str:
    """v2-named alias for ck_fmt_num."""
    return ck_fmt_num(value, decimals=precision)


def ck_fmt_percent(value, precision: int = 1) -> str:
    """v2-named alias for ck_fmt_pct."""
    return ck_fmt_pct(value, decimals=precision)


def ck_command_palette(modules: Optional[Iterable] = None) -> str:
    """Editorial ⌘K palette — empty placeholder in Phase 1.

    Wired for real in a later phase. Returning "" here keeps callers
    that always invoke it from emitting a stray <div>.
    """
    return ""


# ── PHI banner per spec §7.5 ───────────────────────────────────────

def phi_banner(mode: Optional[str]) -> str:
    """Editorial PHI banner — pure function of ``mode``.

    Args:
        mode: One of "disallowed", "restricted", or None.
              The CALLER reads ``RCM_MC_PHI_MODE`` from env (once,
              in the request handler) and passes the lowercased
              trimmed value here. Helpers don't read globals — that
              way unit tests pass mode explicitly and don't have
              to mutate process env.

    Returns:
        Banner HTML using ``.phi-banner`` CSS class, or "" for None
        (or unrecognised mode).
    """
    if mode == "disallowed":
        return (
            '<div class="phi-banner" data-testid="phi-banner" '
            'data-phi-mode="disallowed">'
            '🛡 Public data only — no PHI'
            '</div>'
        )
    if mode == "restricted":
        return (
            '<div class="phi-banner restricted" data-testid="phi-banner" '
            'data-phi-mode="restricted">'
            '⚠ PHI-eligible deployment — access audit-logged. '
            'Do not export outside BAA scope.'
            '</div>'
        )
    return ""


# ── Editorial chrome ───────────────────────────────────────────────

def editorial_link(path: str) -> str:
    """Build a v3-aware URL for internal anchors inside the editorial chrome.

    Per "Discovered during local testing 2026-04-25" §1 in
    ``docs/UI_REWORK_PLAN.md``: clicking the SeekingChartis logo from
    ``/app?ui=v3`` was dropping users back into the legacy shell
    because every internal anchor rebuilt its href without the
    ``?ui=v3`` flag.

    This helper preserves the flag on internal absolute paths.
    External URLs (anything starting with a scheme), in-page anchors
    (``#…``), and paths that already carry their own query string are
    passed through untouched — the helper only adds ``?ui=v3`` when
    it's safe to do so.

    Phase 4 (Q4.1 cutover) will replace this with a session-attribute
    or env-driven flag so anchors don't need rewriting at all. Until
    then, sticky-flag-on-anchors is the smallest-blast-radius fix.
    """
    if not path:
        return path
    if path.startswith(("http://", "https://", "mailto:", "tel:", "#",
                         "data:", "//")):
        return path
    if "?" in path or "&" in path:
        return path
    if not path.startswith("/"):
        return path
    return f"{path}?ui=v3"


# Section-classifier prefix table — maps URL prefixes to topnav
# section names. Used by ``_resolve_active_section`` so callers can
# pass a route path (legacy convention) OR a section name (post-2026-04-26
# convention) and the active-state matching just works. Audit
# 2026-04-26 found that 200+ pages were passing route paths like
# "/rcm-benchmarks" to ``active_nav`` — those never matched the
# section-name comparison (DEALS/ANALYSIS/PORTFOLIO/MARKET/TOOLS), so
# no page ever showed an active state. This table closes the gap.
_SECTION_PREFIXES: dict = {
    "DEALS":     ("/deals", "/diligence/", "/deal/", "/screening", "/screen", "/find-comps"),
    "ANALYSIS":  ("/analysis", "/insights", "/ml-insights", "/quant-lab"),
    "PORTFOLIO": ("/app", "/dashboard", "/home", "/portfolio", "/lp-",
                   "/cohorts", "/alerts", "/pipeline"),
    "MARKET":    ("/market", "/payer-intelligence", "/payer-intel",
                   "/competitive-intel", "/sponsor-", "/seeking-alpha",
                   "/sector-"),
    "TOOLS":     ("/methodology", "/library", "/tools/", "/rcm-benchmarks",
                   "/exports", "/backtest", "/benchmarks", "/calibration",
                   "/models/", "/data/", "/data-", "/admin/", "/audit",
                   "/api", "/conferences", "/news"),
}

_SECTION_NAMES = ("DEALS", "ANALYSIS", "PORTFOLIO", "MARKET", "TOOLS")


def _resolve_active_section(active_nav: Optional[str]) -> str:
    """Map an ``active_nav`` value to a topnav section name.

    Accepts either:
      - A section name (DEALS / ANALYSIS / PORTFOLIO / MARKET / TOOLS),
        case-insensitive
      - A route path (e.g. "/rcm-benchmarks", "/diligence/deal-mc"),
        classified via _SECTION_PREFIXES

    Returns "" when no section matches — caller renders no active
    underline. Empty/None input returns "".
    """
    if not active_nav:
        return ""
    upper = active_nav.upper()
    if upper in _SECTION_NAMES:
        return upper
    # Route-path classifier
    lower = active_nav.lower()
    for section, prefixes in _SECTION_PREFIXES.items():
        for prefix in prefixes:
            if lower.startswith(prefix):
                return section
    return ""


# ── Mega-menu dropdown data ──────────────────────────────────────────
#
# Each top-level section opens a panel listing its surfaces with a
# brief 2-4-word descriptor. The "All [SECTION] surfaces →" footer link
# routes to the section's primary landing page. Surface order = priority
# order (most-used first). When adding a surface: keep the descriptor
# under ~40 chars so the panel doesn't blow out width.
_DROPDOWN_SURFACES: Dict[str, List[Tuple[str, str, str]]] = {
    "DEALS": [
        ("Screener",            "/screen",                       "discover targets"),
        ("Source",              "/import",                       "ingested deals"),
        ("New deal",            "/diligence/deal",               "start diligence"),
        ("Deal dashboard",      "/portfolio",                    "active portfolio"),
        ("Pipeline",            "/pipeline",                     "funnel & stages"),
        ("Predictive screener", "/diligence/denial-prediction",  "ML sourcing"),
        ("Thesis card",         "/diligence/thesis-pipeline",    "30-sec answer"),
        ("Compare",             "/diligence/compare",            "side-by-side"),
    ],
    "ANALYSIS": [
        ("Workbench",           "/analysis",                     "deal-level diligence"),
        ("EBITDA bridge",       "/diligence/bridge-audit",       "value-creation walk"),
        ("Monte Carlo",         "/diligence/deal-mc",            "probabilistic outcomes"),
        ("Scenarios",           "/scenarios",                    "shock-and-recover"),
        ("Risk workbench",      "/diligence/risk-workbench",     "named-failure scan"),
        ("Counterfactual",      "/diligence/counterfactual",     "what-if surrogate"),
        ("HCRIS X-Ray",         "/diligence/hcris-xray",         "Medicare cost-report"),
        ("ML insights",         "/ml-insights",                  "predictor diagnostics"),
    ],
    "PORTFOLIO": [
        ("Command center",      "/app",                          "hold-period rollup"),
        ("Alerts",              "/alerts",                       "fire / ack / age"),
        ("Cohorts",             "/cohorts",                      "peer comparisons"),
        ("LP update",           "/lp-update",                    "partner-ready memo"),
        ("Health score",        "/portfolio/risk-scan",          "cross-deal scan"),
        ("Engagements",         "/engagements",                  "ops workspace"),
        ("Pipeline bridge",     "/pipeline/bridge",              "cross-portfolio"),
        ("Fund learning",       "/fund-learning",                "post-close miss-rate"),
    ],
    "MARKET": [
        ("Market intel",        "/market-intel",                 "PE deal flow"),
        ("Seeking Alpha",       "/market-intel/seeking-alpha",   "public-eq diligence"),
        ("Payer intelligence",  "/payer-intelligence",           "rate-shock map"),
        ("Competitive intel",   "/competitive-intel",            "sponsor tracking"),
        ("Sector heatmap",      "/portfolio/regression",         "national OLS"),
        ("Conferences",         "/conferences",                  "PE event calendar"),
        ("News",                "/news",                         "deal-flow feed"),
        ("Sector library",      "/library",                      "playbook archive"),
    ],
    "TOOLS": [
        ("Methodology",         "/methodology",                  "model reference"),
        ("Calibration",         "/calibration",                  "prior posteriors"),
        ("Backtest harness",    "/models/quality",               "ML model quality"),
        ("Data catalog",        "/data/catalog",                 "public-data ingest"),
        ("Exports",             "/exports",                      "report manifest"),
        ("API",                 "/api",                          "OpenAPI surface"),
        ("Audit log",           "/audit",                        "user activity"),
        ("Admin",               "/admin",                        "users + settings"),
    ],
}

# Primary landing for each section's "All <SECTION> surfaces →" link.
# Diverges from `nav_items` defaults only where a curated landing
# exists — falls back to the section's first dropdown surface.
_SECTION_LANDING: Dict[str, str] = {
    "DEALS":     "/screen",
    "ANALYSIS":  "/analysis",
    "PORTFOLIO": "/app",
    "MARKET":    "/market-intel",
    "TOOLS":     "/methodology",
}


def editorial_topbar(active_nav: Optional[str] = None) -> str:
    """Render the editorial topbar with mega-menu dropdowns.

    5-section topnav (DEALS / ANALYSIS / PORTFOLIO / MARKET / TOOLS).
    Each section opens a dropdown listing its surfaces with brief
    descriptors — replaces the left-sidebar pattern per the 2026-04-26
    design direction (top-nav dropdowns are more functional than a
    left rail because every page gets the full width).

    Click to toggle, click outside or Escape to close, no hover-open
    (avoids accidental opens; matches the screenshot reference).

    ``active_nav`` may be either a section name (DEALS/ANALYSIS/etc.)
    or a route path — see _resolve_active_section.
    """
    active_section = _resolve_active_section(active_nav)
    nav_buttons: List[str] = []
    for section in _SECTION_NAMES:
        surfaces = _DROPDOWN_SURFACES.get(section, [])
        landing = editorial_link(_SECTION_LANDING.get(section, "/"))
        active_class = "active" if section == active_section else ""
        # Surface list inside the panel
        surface_html = "".join(
            f'<a class="dd-item" href="{_html.escape(editorial_link(href))}">'
            f'<span class="dd-label">{_html.escape(label)}</span>'
            f'<span class="dd-desc">{_html.escape(desc)}</span>'
            f'</a>'
            for label, href, desc in surfaces
        )
        count_text = f"{len(surfaces)} surface" + ("s" if len(surfaces) != 1 else "")
        nav_buttons.append(
            f'<div class="topnav-item {active_class}">'
            f'<button type="button" class="topnav-trigger" '
            f'aria-haspopup="true" aria-expanded="false" '
            f'data-section="{section}">'
            f'{section}<span class="caret">▾</span>'
            f'</button>'
            f'<div class="topnav-dropdown" role="menu">'
            f'<div class="dd-eyebrow">{section} · {count_text}</div>'
            f'<div class="dd-list">{surface_html}</div>'
            f'<a class="dd-all" href="{_html.escape(landing)}">'
            f'All {section.lower()} surfaces →</a>'
            f'</div>'
            f'</div>'
        )
    nav_html = "".join(nav_buttons)
    return (
        '<header class="topbar">'
        '<a href="/app?ui=v3" class="brand">'
        '<div class="brand-mark">SC</div>'
        '<div class="brand-name">Seeking<em>Chartis</em></div>'
        '</a>'
        f'<nav class="topnav">{nav_html}</nav>'
        '<div class="topbar-right">'
        '<form class="search" method="GET" action="/global-search" '
        'role="search">'
        '<span class="ico">⌕</span>'
        '<input name="q" placeholder="Search deals, alerts, exports…" '
        'aria-label="Search" autocomplete="off">'
        '<span class="kbd">⏎</span>'
        '</form>'
        '<form method="POST" action="/api/logout" style="display:inline">'
        '<button type="submit" class="signin">SIGN OUT</button>'
        '</form>'
        '</div>'
        '</header>'
    )


def editorial_crumbs(items: Sequence[Tuple[str, Optional[str]]]) -> str:
    """Render breadcrumb trail per spec §6.1.

    ``items`` is a sequence of ``(label, href_or_None)`` tuples.
    The last item is rendered as the current page (no link).

    Internal hrefs are routed through ``editorial_link()`` so the
    ``?ui=v3`` flag stays sticky as the user navigates back up the
    crumb trail — same fix shape as the brand link.
    """
    if not items:
        return ""
    parts: List[str] = []
    for i, (label, href) in enumerate(items):
        is_last = i == len(items) - 1
        esc_label = _html.escape(str(label))
        if is_last or not href:
            parts.append(f'<span class="here">{esc_label}</span>')
        else:
            v3_href = editorial_link(href)
            parts.append(f'<a href="{_html.escape(v3_href)}">{esc_label}</a>')
        if not is_last:
            parts.append('<span class="sep">›</span>')
    return f'<div class="crumbs">{"".join(parts)}</div>'


def editorial_page_head(
    *,
    eyebrow: Optional[Sequence[Tuple[str, Optional[str]]]] = None,
    title: str = "",
    lede: Optional[str] = None,
    meta: Optional[Sequence[Tuple[str, str]]] = None,
) -> str:
    """Render the editorial page header per spec §6.2.

    Args:
        eyebrow: Sequence of (text, kind) tuples. ``kind`` is one of:
            None    → plain uppercase span
            "slug"  → mono span (e.g. "/COMMAND-CENTER" source path)
            Items are joined by `· ` separators rendered centrally so
            the dot character + spacing stay consistent across pages.

            Example: [("PORTFOLIO", None), ("FUND II", None),
                      ("/COMMAND-CENTER", "slug")]

        title: Page title — Source Serif 4, weight 400.
        lede: Optional descriptive paragraph below the title.
        meta: Right-column list of (label, value) pairs rendered in
            JetBrains Mono.
    """
    eb_html = ""
    if eyebrow:
        parts: List[str] = []
        for i, (text, kind) in enumerate(eyebrow):
            if i > 0:
                parts.append('<span class="dot">·</span>')
            esc = _html.escape(str(text))
            if kind == "slug":
                parts.append(f'<span class="slug">{esc}</span>')
            else:
                parts.append(f'<span>{esc}</span>')
        eb_html = f'<div class="eyebrow">{"".join(parts)}</div>'
    title_h = (
        f'<h1 class="title">{_html.escape(title)}</h1>'
        if title else ""
    )
    lede_p = (
        f'<p class="lede">{_html.escape(lede)}</p>'
        if lede else ""
    )
    meta_html = ""
    if meta:
        meta_rows = "".join(
            f'<div>{_html.escape(label)} <span class="dot">·</span> '
            f'<span class="v">{_html.escape(str(value))}</span></div>'
            for label, value in meta
        )
        meta_html = f'<div class="meta-col">{meta_rows}</div>'
    return (
        '<div class="pg-head">'
        f'<div>{eb_html}{title_h}{lede_p}</div>'
        f'{meta_html}'
        '</div>'
    )


# ── Signature pair pattern per spec §5 ────────────────────────────

def pair_block(
    viz_html: str,
    *,
    label: str,
    source: str,
    data_table: str,
) -> str:
    """Wrap a viz + its underlying data table in one outer rule.

    Per spec §5: every analytical section renders as a .pair —
    visualization left (1.4fr), live dataset right (1fr), one rule
    around both. **No chart is ever shown without its underlying
    numbers.**

    Args:
        viz_html: pre-rendered chart / sparkline / heatmap HTML
        label: section label (uppercase; rendered to upper internally
               by the .data-h CSS)
        source: source-file path, rendered in mono teal
                (e.g., "portfolio.db", "summary.csv")
        data_table: pre-rendered <table> HTML for the data column
    """
    return (
        '<div class="pair">'
        f'<div class="viz">{viz_html}</div>'
        '<div class="data">'
        '<div class="data-h">'
        f'<span>{_html.escape(label)}</span>'
        f'<span class="src">{_html.escape(source)}</span>'
        '</div>'
        f'{data_table}'
        '</div>'
        '</div>'
    )


# ── Atoms (cc-components.jsx equivalents) ──────────────────────────

def covenant_pill(status: str) -> str:
    """SAFE / WATCH / TRIP → green / amber / red pill."""
    s = (status or "").upper()
    if s == "SAFE":
        return '<span class="pill green"><span class="dot"></span>Safe</span>'
    if s == "WATCH":
        return '<span class="pill amber"><span class="dot"></span>Watch</span>'
    if s == "TRIP":
        return '<span class="pill red"><span class="dot"></span>Trip</span>'
    return '<span class="pill muted">—</span>'


def stage_pill(stage: str) -> str:
    """Deal-stage pill per cc-components.jsx StagePill."""
    tone_map = {
        "Hold": "blue", "IOI": "amber", "LOI": "amber",
        "Sourced": "muted", "SPA": "blue",
        "Closed": "green", "Exit": "green", "Screened": "muted",
    }
    tone = tone_map.get(stage, "muted")
    return f'<span class="pill {tone}">{_html.escape(stage)}</span>'


def number_maybe(
    v: Union[int, float, None],
    *,
    format: Optional[str] = None,
    tone: Optional[str] = None,
) -> str:
    """Format a number per cc-components.jsx NumberMaybe.

    formats:
      moic   → "2.69x"
      pct    → "21.9%" (input is fraction 0..1)
      ev     → "$450M"
      drift  → "+/-X.X%" (input is signed percent)

    tone:
      green / amber / red → colored output via inline style
                            (atomic CSS would be nicer; inline is
                            fewer moving parts in Phase 1)

    Returns "—" when v is None.
    """
    if v is None:
        return '<span style="color:var(--faint)">—</span>'
    try:
        f = float(v)
    except (TypeError, ValueError):
        return '<span style="color:var(--faint)">—</span>'
    # NaN check: pandas + numpy use float('nan') for missing values,
    # which passes float() but crashes int(). Treat as missing.
    # NaN is the only float that doesn't equal itself, so the test
    # works without importing math.
    if f != f:
        return '<span style="color:var(--faint)">—</span>'
    if format == "moic":
        s = f"{f:.2f}x"
    elif format == "pct":
        s = f"{f * 100:.1f}%"
    elif format == "ev":
        # Unit-aware: callers pass either raw dollars (450000000) or
        # already-scaled millions (450.0). Strip trailing ".0" so a
        # round value renders "$450M" not "$450.0M".
        def _trim(v: float, suffix: str) -> str:
            t = f"{v:.1f}"
            if t.endswith(".0"):
                t = t[:-2]
            return f"${t}{suffix}"
        af = abs(f)
        if af >= 1_000_000_000:
            s = _trim(f / 1_000_000_000, "B")
        elif af >= 1_000_000:
            s = _trim(f / 1_000_000, "M")
        elif af >= 1_000:
            # 1k–999k: assume already-scaled millions (the dev/seed.py
            # convention). 999k raw dollars is below PE-EV magnitude
            # so this branch effectively means "value is in millions".
            s = _trim(f, "M")
        else:
            s = f"${f:,.0f}"
    elif format == "drift":
        s = f"{'+' if f >= 0 else ''}{f:.1f}%"
    else:
        s = str(v)
    color_map = {
        "green": "var(--green)",
        "amber": "var(--amber)",
        "red": "var(--red)",
    }
    color = color_map.get(tone or "")
    if color:
        weight = "600" if tone else "500"
        return f'<span style="color:{color};font-weight:{weight}">{_html.escape(s)}</span>'
    return _html.escape(s)


def sparkline_svg(
    values: Sequence[float],
    *,
    color: str = "var(--teal)",
) -> str:
    """100×22 inline SVG sparkline matching cc-components.jsx Sparkline.

    Auto-scales y-range to (min, max). Returns "" for empty input
    (callers can use the cell-empty state).
    """
    if not values:
        return ""
    w, h, pad = 100, 22, 2
    vmin, vmax = min(values), max(values)
    rng = (vmax - vmin) or 1.0
    n = len(values)
    pts: List[str] = []
    for i, v in enumerate(values):
        x = pad + (i * (w - pad * 2)) / max(n - 1, 1)
        y = h - pad - ((v - vmin) / rng) * (h - pad * 2)
        cmd = "M" if i == 0 else "L"
        pts.append(f"{cmd}{x:.1f} {y:.1f}")
    path = " ".join(pts)
    return (
        f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none" '
        f'style="width:100%;height:100%;display:block">'
        f'<path d="{path}" stroke="{color}" stroke-width="1.25" '
        f'fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
        '</svg>'
    )


# ── Sidebar (editorial spec §7.4) ──────────────────────────────────

# 28 modules per spec §7.4, with their canonical destinations from
# IA_MAP.md / the route audit. Tuple shape: (label, href, group).
# Groups separate the rail visually:
#   diligence   — per-deal analytical modules (most of the list)
#   market      — cross-portfolio market intel
#   screening   — pre-deal scans
#   ops         — engagements + workflow
#
# Active state: callers pass active_path as the current route; the
# helper highlights any module whose href matches as a prefix.
_SIDEBAR_MODULES: List[Tuple[str, str, str]] = [
    # Diligence — per-deal analytical surfaces
    ("Deal Profile",      "/diligence/deal",                "diligence"),
    ("Thesis Pipeline",   "/diligence/thesis-pipeline",     "diligence"),
    ("Checklist",         "/diligence/checklist",           "diligence"),
    ("Ingestion",         "/import",                        "diligence"),
    ("Benchmarks",        "/diligence/benchmarks",          "diligence"),
    ("HCRIS X-Ray",       "/diligence/hcris-xray",          "diligence"),
    ("Root Cause",        "/diligence/root-cause",          "diligence"),
    ("Value Creation",    "/diligence/value",               "diligence"),
    ("Risk Workbench",    "/diligence/risk-workbench",      "diligence"),
    ("Counterfactual",    "/diligence/counterfactual",      "diligence"),
    ("Compare",           "/diligence/compare",             "diligence"),
    ("QoE Memo",          "/diligence/qoe-memo",            "diligence"),
    ("Denial Predict",    "/diligence/denial-prediction",   "diligence"),
    ("Deal Autopsy",      "/diligence/deal-autopsy",        "diligence"),
    ("Physician Attrition", "/diligence/physician-attrition", "diligence"),
    ("Provider Economics", "/diligence/physician-eu",       "diligence"),
    ("Management",        "/diligence/management",          "diligence"),
    ("Deal MC",           "/diligence/deal-mc",             "diligence"),
    ("Exit Timing",       "/diligence/exit-timing",         "diligence"),
    ("Reg Calendar",      "/diligence/regulatory-calendar", "diligence"),
    ("Covenant Stress",   "/diligence/covenant-stress",     "diligence"),
    ("Bridge Audit",      "/diligence/bridge-audit",        "diligence"),
    ("Bear Case",         "/diligence/bear-case",           "diligence"),
    ("Payer Stress",      "/diligence/payer-stress",        "diligence"),
    ("IC Packet",         "/diligence/ic-packet",           "diligence"),
    # Market intel
    ("Market Intel",      "/market-intel",                  "market"),
    ("Seeking Alpha",     "/market-intel/seeking-alpha",    "market"),
    # Screening
    ("Bankruptcy Scan",   "/screening/bankruptcy-survivor", "screening"),
    # Operations
    ("Engagements",       "/engagements",                   "ops"),
]

_SIDEBAR_GROUP_LABELS: Mapping[str, str] = {
    "diligence": "RCM DILIGENCE",
    "market":    "MARKET INTEL",
    "screening": "PRE-SCREENING",
    "ops":       "OPERATIONS",
}


def editorial_sidebar(active_path: Optional[str] = None) -> str:
    """Render the editorial left-rail sidebar per spec §7.4.

    28 modules grouped by category (diligence / market / screening /
    ops). Active link is highlighted by prefix-match against
    ``active_path`` — if the current route starts with a module's
    href, that module gets the .active class (teal left border + bold
    label).

    All hrefs route through ``editorial_link()`` so the ``?ui=v3``
    flag stays sticky as the user navigates between modules.

    Sidebar opt-in via ``chartis_shell(show_sidebar=True)`` — defaults
    to off so existing callers don't get an unexpected layout shift.
    """
    active_lower = (active_path or "").lower()

    sections: List[str] = []
    last_group: Optional[str] = None
    for label, href, group in _SIDEBAR_MODULES:
        if group != last_group:
            heading = _SIDEBAR_GROUP_LABELS.get(group, group.upper())
            sections.append(f'<div class="rail-h">{_html.escape(heading)}</div>')
            last_group = group

        is_active = (
            active_lower.startswith(href.lower()) and len(href) > 1
        )
        cls = "active" if is_active else ""
        v3_href = editorial_link(href)
        sections.append(
            f'<a href="{_html.escape(v3_href)}" class="{cls}">'
            f'<span class="rail-label">{_html.escape(label)}</span>'
            f'</a>'
        )

    return f'<aside class="rail">{"".join(sections)}</aside>'


# ── The shell ──────────────────────────────────────────────────────

def chartis_shell(
    body: str,
    title: str,
    *,
    active_nav: str = "",
    subtitle: str = "",
    extra_css: str = "",
    extra_js: str = "",
    breadcrumbs: Optional[Sequence[Tuple[str, Optional[str]]]] = None,
    code: Optional[str] = None,
    show_chrome: bool = True,
    show_phi_banner: bool = True,
    phi_mode: Optional[str] = None,
    show_sidebar: bool = False,
    sidebar_active_path: Optional[str] = None,
) -> str:
    """Editorial page shell.

    Renders the parchment + serif + teal frame around `body`. Links
    /static/v3/chartis.css for tokens + base typography + utilities.

    Backwards-compat with the legacy shell signature: same kwargs
    (``subtitle``, ``extra_css``, ``extra_js``, ``active_nav``) so
    page renderers in rcm_mc/ui/chartis/* don't change as they're
    ported. New kwargs (``breadcrumbs``, ``code``) supply the
    editorial-only chrome elements.

    Args:
        body: Inner HTML of the page.
        title: <title> tag content + topbar title.
        active_nav: One of DEALS / ANALYSIS / PORTFOLIO / MARKET /
                    TOOLS to underline in the topnav.
        subtitle: Legacy compat — folded into breadcrumbs if no
                  breadcrumbs given.
        extra_css: <style> block injected into <head>.
        extra_js: <script> block appended at the end of <body>.
        breadcrumbs: Sequence of (label, href|None) for the .crumbs row.
        code: Source-file path for the page header (mono teal).
        show_chrome: Set False on bare pages (login, forgot) that
                     don't need the topnav. Banner + footer still ok.
        show_phi_banner: Set False on unauthenticated pages.
        phi_mode: PHI posture — caller reads RCM_MC_PHI_MODE env in
                  the handler and passes the value here. None (default)
                  means no banner, even when show_phi_banner is True.
                  This keeps env reads in handlers, not helpers.
    """
    safe_title = _html.escape(title or "SeekingChartis")
    chrome = (
        editorial_topbar(active_nav)
        if show_chrome else (
            # No-chrome brand for unauthenticated pages (login, forgot).
            # Points at /?ui=v3 so the logo keeps the user inside the
            # editorial shell at the marketing splash, instead of
            # dropping back to legacy /. Same fix as chrome'd brand.
            '<header class="topbar">'
            '<a href="/?ui=v3" class="brand">'
            '<div class="brand-mark">SC</div>'
            '<div class="brand-name">Seeking<em>Chartis</em></div>'
            '</a>'
            '</header>'
        )
    )
    crumbs_html = ""
    if breadcrumbs:
        crumbs_html = editorial_crumbs(breadcrumbs)
    elif subtitle and show_chrome:
        crumbs_html = editorial_crumbs([(subtitle, None)])
    banner_html = phi_banner(phi_mode) if show_phi_banner else ""
    extra_css_block = f"<style>{extra_css}</style>" if extra_css else ""
    extra_js_block = f"<script>{extra_js}</script>" if extra_js else ""
    # Built-in JS — runs on every editorial page. Currently:
    # 1) topnav-dropdown toggle: click to open, outside-click / Escape
    #    to close, single-open invariant (opening one closes others).
    builtin_js = (
        "<script>"
        "(function(){"
        "var items=document.querySelectorAll('.topnav-item');"
        "if(!items.length)return;"
        "function closeAll(){items.forEach(function(it){it.classList.remove('open');"
        "var t=it.querySelector('.topnav-trigger');"
        "if(t)t.setAttribute('aria-expanded','false');});}"
        "items.forEach(function(it){"
        "var trig=it.querySelector('.topnav-trigger');"
        "if(!trig)return;"
        "trig.addEventListener('click',function(e){"
        "e.stopPropagation();"
        "var wasOpen=it.classList.contains('open');"
        "closeAll();"
        "if(!wasOpen){it.classList.add('open');trig.setAttribute('aria-expanded','true');}"
        "});});"
        "document.addEventListener('click',function(e){"
        "if(!e.target.closest('.topnav-item'))closeAll();});"
        "document.addEventListener('keydown',function(e){"
        "if(e.key==='Escape')closeAll();});"
        "})();"
        "</script>"
    )

    # Sidebar opt-in — when show_sidebar=True, wrap (crumbs + banner +
    # main) in a 2-column flex layout with the editorial rail on the
    # left. Sidebar lives BELOW the topbar and SPANS only the main
    # content area below it. Default off; existing callers see no
    # layout change.
    if show_sidebar:
        sidebar_html = editorial_sidebar(sidebar_active_path)
        layout_html = (
            f'<div class="layout-with-rail">'
            f'{sidebar_html}'
            f'<div class="layout-main">'
            f'{crumbs_html}'
            f'{banner_html}'
            f'<main>{body}</main>'
            f'</div>'
            f'</div>'
        )
    else:
        layout_html = (
            f'{crumbs_html}'
            f'{banner_html}'
            f'<main>{body}</main>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{safe_title} — SeekingChartis</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="/static/v3/chartis.css">
{extra_css_block}
</head>
<body>
{chrome}
{layout_html}
{builtin_js}
{extra_js_block}
</body>
</html>"""


__all__ = [
    # Palette + nav
    "P", "_CORPUS_NAV", "_LEGACY_NAV", "_MONO", "_SANS",
    # Shell
    "chartis_shell", "editorial_topbar", "editorial_crumbs",
    "editorial_page_head", "editorial_link", "editorial_sidebar",
    "phi_banner", "_resolve_active_section",
    # Pair pattern
    "pair_block",
    # Atoms
    "covenant_pill", "stage_pill", "number_maybe", "sparkline_svg",
    # Heavy helpers (re-exported from legacy)
    "ck_panel", "ck_table", "ck_kpi_block", "ck_section_header",
    "ck_signal_badge", "ck_grade_badge", "ck_regime_badge",
    "ck_command_palette",
    # Formatters
    "ck_fmt_num", "ck_fmt_pct", "ck_fmt_moic", "ck_fmt_currency",
    "ck_fmt_irr", "ck_fmt_number", "ck_fmt_percent",
]
