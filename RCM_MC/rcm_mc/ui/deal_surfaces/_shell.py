"""Shared chrome for every /deals/<ccn>/* surface.

The surface family is a tabbed deal-lens: a fixed identity header (who this
hospital is, in 6 stats) plus a 5-group sub-nav of 18 tabs. Each surface
renders its own body inside this shell. Honest empty states are the rule —
nothing here fabricates numbers; if HCRIS doesn't have a value for this CCN
the cell shows "—", never an invented figure.
"""
from __future__ import annotations

import html as _html
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .._chartis_kit import chartis_shell


@dataclass(frozen=True)
class DealSurface:
    """One tab in the deal-lens sub-nav."""
    number: int             # 1..18 (matches the handoff spec)
    slug: str               # URL segment (e.g. "profile")
    label: str              # display label (e.g. "Profile")
    group: str              # one of SURFACE_GROUPS
    built: bool             # True once the real surface ships
    description: str        # short tagline for the stub page


# Order, slug, label, group, and built-status per the handoff spec. Built
# flips to True one PR at a time as each surface lands. "Coming soon" pages
# render until then — never fake content.
SURFACES: Tuple[DealSurface, ...] = (
    # ── Diligence ──
    DealSurface(1,  "profile",     "Profile",         "Diligence",      True,
                "Front door — identity, headline financials, score."),
    DealSurface(2,  "ic-memo",     "IC Memo",         "Diligence",      False,
                "Auto-assembled IC memorandum (sections stream in)."),
    DealSurface(3,  "bridge",      "EBITDA Bridge",   "Diligence",      True,
                "7-lever RCM bridge to pro-forma EBITDA."),
    DealSurface(4,  "comp-intel",  "Comp Intel",      "Diligence",      True,
                "Percentile ranks across 12 metrics × 4 cohorts."),
    DealSurface(5,  "scenarios",   "Scenarios",       "Diligence",      False,
                "Toggle base/conservative/aggressive/downside."),
    DealSurface(6,  "ml",          "ML Analysis",     "Diligence",      True,
                "Margin · distress · opportunity from three models."),
    # ── Models ──
    DealSurface(7,  "dcf",         "DCF",             "Models",         True,
                "5-year explicit + Gordon-growth terminal."),
    DealSurface(8,  "lbo",         "LBO",             "Models",         True,
                "Sources & uses, debt schedule, returns waterfall."),
    DealSurface(9,  "stmt",        "3-Statement",     "Models",         False,
                "P&L, balance sheet, cash flow with source tags."),
    # ── Market & risk ──
    DealSurface(10, "market",      "Market",          "Market & risk",  False,
                "HHI, market share, top competitors, payer mix."),
    DealSurface(11, "denial",      "Denial",          "Market & risk",  True,
                "Root-cause decomposition of denial leakage."),
    DealSurface(12, "returns",     "Returns",         "Market & risk",  True,
                "IRR, MOIC, covenant headroom under stress."),
    # ── Value creation ──
    DealSurface(13, "levers",      "Levers",          "Value creation", False,
                "7-lever EBITDA bridge weighted by probability."),
    DealSurface(14, "waterfall",   "Waterfall",       "Value creation", False,
                "LP / GP split with pref + carry mechanics."),
    DealSurface(15, "playbook",    "Playbook",        "Value creation", False,
                "100-day operational playbook (impact × tractability)."),
    # ── Diagnostics ──
    DealSurface(16, "trends",      "Trends",          "Diagnostics",    True,
                "Per-metric time-series forecasts."),
    DealSurface(17, "predicted",   "Predicted vs Actual", "Diagnostics", False,
                "Diligence predictions vs current actuals."),
    DealSurface(18, "memo-auto",   "Memo (auto)",     "Diagnostics",    False,
                "Lightweight auto-generated IC memo."),
)

SURFACE_BY_PATH: Dict[str, DealSurface] = {s.slug: s for s in SURFACES}

SURFACE_GROUPS: Tuple[str, ...] = (
    "Diligence", "Models", "Market & risk", "Value creation", "Diagnostics",
)


# ───────────────────────── data fetch ─────────────────────────

def fetch_hospital(ccn: str) -> Optional[Dict[str, Any]]:
    """Return the latest HCRIS row for ``ccn`` as a dict, or None.

    Single source of truth for "who is this hospital?" across every surface in
    the family — keeps the identity header byte-identical from tab to tab.
    """
    try:
        from ..._chartis_kit import chartis_shell  # noqa: F401  (sanity)
    except Exception:  # noqa: BLE001
        pass
    try:
        from ...data.hcris import _get_latest_per_ccn
    except ImportError:
        from rcm_mc.data.hcris import _get_latest_per_ccn
    hdf = _get_latest_per_ccn()
    match = hdf[hdf["ccn"] == str(ccn)]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


# ───────────────────────── formatting ─────────────────────────

def _fmt_money(value: Optional[float]) -> str:
    """Compact USD ($1.2B / $345M / $12K / $—)."""
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "—"
    if v == 0:
        return "$0"
    a = abs(v)
    if a >= 1e9:
        return f"${v/1e9:.2f}B"
    if a >= 1e6:
        return f"${v/1e6:.1f}M"
    if a >= 1e3:
        return f"${v/1e3:.0f}K"
    return f"${v:.0f}"


def _fmt_pct(value: Optional[float], digits: int = 1) -> str:
    """Percentage from a 0..1 fraction. '—' for missing."""
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{v * 100:.{digits}f}%"


def _fmt_int(value: Optional[float]) -> str:
    if value is None:
        return "—"
    try:
        return f"{int(float(value)):,}"
    except (TypeError, ValueError):
        return "—"


# ───────────────────────── chrome rendering ─────────────────────────

def _identity_header(hospital: Dict[str, Any]) -> str:
    """Fixed 6-stat strip at the top of every surface — same across tabs.

    Every value is real HCRIS or "—"; nothing is invented. Margin is computed
    from net revenue and operating expenses only when both are present.
    """
    ccn = _html.escape(str(hospital.get("ccn", "")))
    name = _html.escape(str(hospital.get("name", "") or "(name not on file)"))
    state = _html.escape(str(hospital.get("state", "") or "—"))
    city = _html.escape(str(hospital.get("city", "") or ""))
    loc = f"{city}, {state}" if city and state and state != "—" else state
    beds = _fmt_int(hospital.get("beds") or hospital.get("bed_count"))
    npr_raw = hospital.get("net_patient_revenue")
    npr = _fmt_money(npr_raw)
    opex = hospital.get("operating_expenses")
    margin = None
    try:
        if npr_raw and float(npr_raw) > 1e5 and opex:
            margin = (float(npr_raw) - float(opex)) / float(npr_raw)
    except (TypeError, ValueError):
        margin = None
    margin_str = _fmt_pct(margin)
    return (
        '<header class="ds-id">'
        '<div class="ds-id-name">'
        f'<span class="ds-id-eyebrow">DEAL · CCN {ccn}</span>'
        f'<h1 class="ds-id-title">{name}</h1>'
        f'<span class="ds-id-loc">{loc}</span>'
        '</div>'
        '<dl class="ds-id-stats">'
        f'<div><dt>Beds</dt><dd>{beds}</dd></div>'
        f'<div><dt>NPR</dt><dd>{npr}</dd></div>'
        f'<div><dt>Op margin</dt><dd>{margin_str}</dd></div>'
        '</dl>'
        '</header>'
    )


def _sub_nav(ccn: str, active_slug: str) -> str:
    """Sub-nav: 5 groups, 18 tabs. Unbuilt tabs render as muted text-only links
    that still navigate (to honest "coming soon" stubs); never disabled.
    """
    ccn_safe = _html.escape(ccn, quote=True)
    parts: List[str] = ['<nav class="ds-nav" aria-label="Deal surfaces">']
    for group in SURFACE_GROUPS:
        items = [s for s in SURFACES if s.group == group]
        parts.append(f'<div class="ds-nav-group" data-group="{_html.escape(group)}">')
        parts.append(f'<span class="ds-nav-eyebrow">{_html.escape(group)}</span>')
        parts.append('<ul class="ds-nav-list">')
        for s in items:
            classes = ["ds-nav-link"]
            if not s.built:
                classes.append("ds-nav-link-soon")
            if s.slug == active_slug:
                classes.append("ds-nav-link-active")
            href = f"/deals/{ccn_safe}/{s.slug}"
            soon_badge = '<span class="ds-nav-soon" aria-hidden="true">soon</span>' \
                if not s.built else ''
            parts.append(
                f'<li><a class="{" ".join(classes)}" href="{href}"'
                f'{" aria-current=\"page\"" if s.slug == active_slug else ""}'
                f'>{_html.escape(s.label)}{soon_badge}</a></li>'
            )
        parts.append('</ul></div>')
    parts.append('</nav>')
    return ''.join(parts)


_DS_CSS = """
<style>
.ds-page{--ds-paper:#faf6ec;--ds-paper2:#f3eddb;--ds-ink:#15202b;
  --ds-ink2:#2a3a4a;--ds-muted:#6a7480;--ds-muted2:#8b94a0;--ds-rule:#c9c1ac;
  --ds-green:#1f7a5a;--ds-amber:#b8842e;--ds-coral:#b5321e;--ds-max:1320px;}
.ds-id{max-width:var(--ds-max);margin:0 auto;padding:24px 0 16px;
  display:grid;grid-template-columns:1.4fr 1fr;gap:32px;align-items:end;
  border-bottom:1px solid var(--ds-rule);}
.ds-id-eyebrow{font-family:var(--sc-mono,monospace);font-size:10.5px;
  letter-spacing:.2em;text-transform:uppercase;color:var(--ds-green);}
.ds-id-title{font-family:var(--sc-serif,Georgia,serif);font-weight:400;
  font-size:34px;line-height:1.05;letter-spacing:-.02em;margin:6px 0 4px;
  color:var(--ds-ink);}
.ds-id-loc{font-family:var(--sc-mono,monospace);font-size:11px;
  letter-spacing:.1em;text-transform:uppercase;color:var(--ds-muted);}
.ds-id-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));
  gap:18px;margin:0;}
.ds-id-stats dt{font-family:var(--sc-mono,monospace);font-size:9.5px;
  letter-spacing:.14em;text-transform:uppercase;color:var(--ds-muted);
  margin-bottom:4px;}
.ds-id-stats dd{font-family:var(--sc-serif,Georgia,serif);font-size:22px;
  letter-spacing:-.01em;margin:0;color:var(--ds-ink);
  font-variant-numeric:tabular-nums;}
/* sub-nav */
.ds-nav{max-width:var(--ds-max);margin:0 auto;padding:14px 0 18px;
  display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:28px;
  border-bottom:1px solid var(--ds-rule);}
.ds-nav-group{min-width:0;}
.ds-nav-eyebrow{font-family:var(--sc-mono,monospace);font-size:9.5px;
  letter-spacing:.18em;text-transform:uppercase;color:var(--ds-muted);
  display:block;margin-bottom:8px;}
.ds-nav-list{list-style:none;padding:0;margin:0;display:flex;
  flex-direction:column;gap:4px;}
.ds-nav-link{font-family:var(--sc-serif,Georgia,serif);font-size:13.5px;
  line-height:1.25;color:var(--ds-ink2);text-decoration:none;
  display:flex;align-items:baseline;gap:6px;padding:2px 0;}
.ds-nav-link:hover{color:var(--ds-green);}
.ds-nav-link-active{color:var(--ds-green);font-weight:500;
  border-left:2px solid var(--ds-green);padding-left:8px;}
.ds-nav-link-soon{color:var(--ds-muted2);}
.ds-nav-soon{font-family:var(--sc-mono,monospace);font-size:8.5px;
  letter-spacing:.14em;text-transform:uppercase;color:var(--ds-muted2);
  border:1px solid var(--ds-rule);padding:0 4px;background:var(--ds-paper2);}
/* surface body container */
.ds-body{max-width:var(--ds-max);margin:0 auto;padding:22px 0;}
@media (max-width:1180px){
  .ds-id{grid-template-columns:1fr;gap:14px;}
  .ds-nav{grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;}
}
@media (max-width:720px){
  .ds-nav{grid-template-columns:1fr;}
  .ds-id-stats{grid-template-columns:repeat(3,minmax(0,1fr));}
}
</style>
"""


def deal_shell(
    ccn: str,
    hospital: Dict[str, Any],
    *,
    active_slug: str,
    body_html: str,
    page_title: Optional[str] = None,
) -> str:
    """Wrap a surface body in the deal-lens chrome (identity header + sub-nav).

    ``active_slug`` controls which sub-nav tab is highlighted. ``page_title``
    is the browser tab title; defaults to "<surface label> · <hospital name>".
    """
    surface = SURFACE_BY_PATH.get(active_slug)
    nice_label = surface.label if surface else active_slug.title()
    hname = str(hospital.get("name", "") or f"CCN {ccn}")
    title = page_title or f"{nice_label} · {hname}"
    body = (
        '<div class="ds-page">'
        f'{_identity_header(hospital)}'
        f'{_sub_nav(ccn, active_slug)}'
        f'<div class="ds-body">{body_html}</div>'
        '</div>'
    )
    return chartis_shell(
        body, title=title, active_nav="/deals", extra_css=_DS_CSS,
    )
