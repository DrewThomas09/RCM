"""US payer-system exhibits deck — /payer-system.

Surfaces the four payer-economics CDD exhibits built from the 2025-2026 US
payer reference report (NEW-27 MA bid/benchmark/rebate, NEW-28 star-rating QBP
sensitivity, NEW-29 Part D IRA redesign, NEW-30 ACA enhanced-APTC cliff) on one
page. Each section runs the registered exhibit in partner mode and renders its
headline series as a Chartis SVG, with the sourced footnote, diligence flags,
and the reconciliation badge that proves the numbers tie out.

This is a render-only surface: the math lives in ``rcm_mc.cdd`` and is exercised
by the golden tests. The page calls the registry so what it shows is exactly the
registered, tested exhibit. No data is recomputed here, no LLM on any path.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from rcm_mc.ui._chartis_kit import chartis_shell, ck_page_explainer, ck_page_title
from rcm_mc.ui.cdd_chart_kit import render_cdd_chart
from rcm_mc.cdd import registry

# (feature_id, headline series to chart, chart type, value suffix, blurb)
_EXHIBITS = [
    ("NEW-27", ["Payment vs FFS"], "column", "",
     "The core MA payment formula. A county benchmark is set as a percent of "
     "fee-for-service spending by quartile, a quality bonus is added for 4-plus "
     "star contracts, and a plan that bids below the benchmark keeps a star-tier "
     "share of the spread as a rebate that funds supplemental benefits."),
    ("NEW-28", ["Plan payment by star tier"], "column", "",
     "Star rating drives both the quality bonus and the rebate-retention tier, "
     "so plan payment can fall sharply on a half-star downgrade. This prices the "
     "payment across star scenarios, holding the bid and benchmark fixed."),
    ("NEW-29", ["Payer share of gross drug cost"], "column", "",
     "The IRA collapsed Part D into three phases and capped enrollee out-of-pocket "
     "spend. This allocates a member's annual brand drug cost across the enrollee, "
     "plan, manufacturer, and Medicare reinsurance, which now carries only 20 "
     "percent of the catastrophic tail."),
    ("NEW-30", ["Net premium under enhanced credits",
                "Net premium after enhanced credits expire"], "column", "",
     "The enhanced premium tax credits expire at the end of 2025. This compares "
     "the net benchmark premium under the enhanced and the restored schedules, "
     "where enrollees above 400 percent of poverty fall off the eligibility cliff."),
]

_SEV_COLOR = {"risk": "#b5321e", "warn": "#b8732a", "info": "#155752"}


def _table_from_series(exhibit: Dict[str, Any], names: List[str]) -> Dict[str, Any]:
    """Build a chart-kit table from one or more named series of {label, value}.

    Rows are keyed off the first series' labels so a multi-series exhibit (the
    ACA before/after comparison) renders as grouped columns aligned by label.
    """
    series_by_name = {s["name"]: s for s in exhibit.get("series", [])}
    chosen = [series_by_name[n] for n in names if n in series_by_name]
    if not chosen:
        return {"headers": [], "rows": []}
    labels = [str(p.get("label", "")) for p in chosen[0]["points"]]
    headers = [""] + names
    rows = []
    for i, label in enumerate(labels):
        vals = []
        for s in chosen:
            pts = s["points"]
            vals.append(float(pts[i]["value"]) if i < len(pts) and pts[i].get("value") is not None else None)
        rows.append((label, vals))
    return {"headers": headers, "rows": rows}


def _render_flags(flags: List[Dict[str, Any]]) -> str:
    if not flags:
        return '<p class="ps-noflags">No diligence flags fired for this scenario.</p>'
    items = []
    for f in flags:
        color = _SEV_COLOR.get(f.get("severity", "info"), "#465366")
        items.append(
            f'<li class="ps-flag"><span class="ps-flag-dot" style="background:{color}"></span>'
            f'<span class="ps-flag-sev" style="color:{color}">{_html.escape(f.get("severity", "").upper())}</span> '
            f'{_html.escape(f.get("message", ""))}</li>')
    return f'<ul class="ps-flags">{"".join(items)}</ul>'


def _render_section(fid: str, names: List[str], ctype: str, suffix: str, blurb: str) -> str:
    try:
        feature = registry.get(fid)
        exhibit = feature.demo().render(internal_mode=False)
    except Exception:  # noqa: BLE001 - a missing/broken feature must not break the page
        return ""

    title = exhibit.get("title", fid)
    summary = exhibit.get("summary", "")
    footnote = exhibit.get("footnote") or {}
    source = footnote.get("source", "")
    vintage = footnote.get("vintage", "")
    source_line = f"{source} ({vintage})" if source else ""

    table = _table_from_series(exhibit, names)
    opts = {
        "title": names[0],
        "palette": "Navy–Teal",
        "show_values": True,
        "suffix": suffix,
        "source": source_line,
        "legend": len(names) > 1,
    }
    chart = render_cdd_chart(ctype, table, opts)

    reconciled = exhibit.get("reconciled", False)
    badge_color = "#0a8a5f" if reconciled else "#b5321e"
    badge_text = "Reconciled" if reconciled else "Reconciliation gap"
    assumptions = footnote.get("assumptions", [])
    assum_html = "".join(f"<li>{_html.escape(a)}</li>" for a in assumptions)

    return f"""
<section class="ps-exhibit">
  <div class="ps-head">
    <span class="ps-id">{_html.escape(fid)}</span>
    <h2 class="ps-title">{_html.escape(title)}</h2>
    <span class="ps-badge" style="background:{badge_color}">{badge_text}</span>
  </div>
  <p class="ps-blurb">{_html.escape(blurb)}</p>
  <div class="ps-chart">{chart}</div>
  <p class="ps-summary">{_html.escape(summary)}</p>
  {_render_flags(exhibit.get("flags", []))}
  <details class="ps-assum"><summary>Source and assumptions</summary>
    <p class="ps-src">{_html.escape(source_line)}</p>
    <ul>{assum_html}</ul>
  </details>
</section>"""


def render_payer_system_page(params: Optional[dict] = None) -> str:
    sections = [
        _render_section(fid, names, ctype, suffix, blurb)
        for fid, names, ctype, suffix, blurb in _EXHIBITS
    ]
    sections = [s for s in sections if s]

    page_title = ck_page_title(
        "US Payer System",
        eyebrow="DILIGENCE · PAYER ECONOMICS",
        meta=("4 exhibits · Medicare Advantage · Part D · ACA marketplace · "
              "2025-2026 rules"),
    )
    explainer = ck_page_explainer(
        "How the risk-bearing payers actually get paid.",
        "Four exhibits built from the 2025-2026 US payer reference report, "
        "covering the actuarial core of the risk-bearing verticals: the Medicare "
        "Advantage bid, benchmark, and rebate formula; the star-rating payment "
        "cliff; the Inflation Reduction Act Part D redesign; and the enhanced-ACA "
        "subsidy cliff. Every number reconciles to its source and is reproduced "
        "in a golden test.",
    )
    css = """
<style>
.ps-exhibit { margin: 26px 0; padding: 18px 20px; background: #fffdf9;
              border: 1px solid #d8d2c4; border-radius: 8px; }
.ps-head { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.ps-id { font-family: 'JetBrains Mono', monospace; font-size: 12px;
         color: #155752; border: 1px solid #155752; border-radius: 4px;
         padding: 2px 7px; }
.ps-title { font-size: 20px; margin: 0; color: #0b2341; flex: 1; }
.ps-badge { color: #fff; font-size: 11px; font-weight: 600; border-radius: 4px;
            padding: 3px 9px; letter-spacing: 0.3px; }
.ps-blurb { margin: 8px 0 14px; color: #4a5568; max-width: 78ch; line-height: 1.5; }
.ps-chart { display: flex; justify-content: center; margin: 6px 0 12px; }
.ps-summary { font-size: 13.5px; color: #1a2332; font-weight: 600; margin: 6px 0; }
.ps-flags { list-style: none; padding: 0; margin: 10px 0; }
.ps-flag { font-size: 13px; color: #1a2332; margin: 5px 0; line-height: 1.45; }
.ps-flag-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
               margin-right: 7px; vertical-align: middle; }
.ps-flag-sev { font-family: 'JetBrains Mono', monospace; font-size: 11px;
               font-weight: 600; margin-right: 4px; }
.ps-noflags { font-size: 13px; color: #7a8699; font-style: italic; }
.ps-assum { margin-top: 10px; font-size: 12.5px; color: #465366; }
.ps-assum summary { cursor: pointer; color: #155752; font-weight: 600; }
.ps-src { font-style: italic; color: #7a8699; margin: 8px 0 4px; }
</style>"""
    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {explainer}
  {''.join(sections)}
</div>"""
    return chartis_shell(body, title="US Payer System", active_nav="/payer-system",
                         extra_css=css)
