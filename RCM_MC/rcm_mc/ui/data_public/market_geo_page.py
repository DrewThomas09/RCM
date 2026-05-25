"""PEdesk Market Intelligence (geographic) — /market-intel/geo[/<fips>].

Renders the licensed SimplyAnalytics-derived market data (loaded from
``rcm_mc.data.market_intel``) as a PEdesk-native choropleth + ranked tables and
per-geography profile cards. The state map reuses the existing
``us_geo_map.render_us_geo_map`` geometry — the screenshots are design
references only and are never embedded as the production map.

Honesty: this is market/area context (state/county by FIPS), NOT provider-
specific; demographic/payer mix should be combined with CMS/HCRIS/provider data
before a decision. Variables without an underlying export render as
EXPORT REQUIRED — never fabricated. Real percentiles only.
"""
from __future__ import annotations

import html as _html
from typing import Dict, Optional

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block, ck_page_title, ck_source_purpose
from rcm_mc.ui.us_geo_map import render_us_geo_map
from rcm_mc.data import market_intel as _mi

# FIPS (2-digit) → USPS abbreviation (50 states + DC; territories shown in
# tables only since the state map covers the 50 states + DC).
_FIPS_ABBR = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO",
    "09": "CT", "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI",
    "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
    "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
    "54": "WV", "55": "WI", "56": "WY", "72": "PR",
}

# Export-backlog variables (shown in screenshots, no export yet → not fabricated)
_BACKLOG = [
    ("Median Household Income, 2025", "INCOME"),
    ("% Private Health Insurance (B27002), 2023", "INSURANCE"),
    ("% No Health Insurance, 2025", "INSURANCE"),
    ("NAICS 621111 provider supply", "PROVIDER_SUPPLY"),
]

_LICENSE_CHIP = (
    f'<span style="display:inline-block;background:{P["accent"]};color:#fff;'
    f'font-size:9px;font-weight:700;letter-spacing:0.08em;padding:2px 8px;'
    f'border-radius:3px;text-transform:uppercase">Licensed market data derived</span>'
)


def _fmt(value: Optional[float], unit: str) -> str:
    if value is None:
        return "—"
    if unit == "pct":
        return f"{value*100:.1f}%"
    if unit == "usd":
        return f"${value:,.0f}"
    return f"{value:,.1f}"


_ABBR_FIPS = {v: k for k, v in _FIPS_ABBR.items()}


def market_context_panel(state, P_=None) -> str:
    """Reusable 'Market context' panel for diligence/provider pages.

    ``state`` may be a 2-letter abbreviation (e.g. 'CA') or a FIPS string. Shows
    the real market variables on record for that state + the partial market
    score, with an honest caveat. Returns '' if the geography isn't on record
    (so callers can drop it in unconditionally). Variables not yet exported are
    listed as EXPORT REQUIRED — never fabricated.
    """
    pal = P_ or P
    s = str(state or "").strip().upper()
    fips = _ABBR_FIPS.get(s, s if s.isdigit() else "")
    if not fips:
        return ""
    prof = _mi.market_profile_for_geo(fips)
    if not prof:
        return ""
    score = _mi.market_demand_score(fips)
    rows = ""
    for vid, d in prof["variables"].items():
        v = _mi.load_market_variable(vid) or {}
        rows += (f'<tr><td style="padding:3px 10px">{_html.escape(v.get("display_name", vid))}</td>'
                 f'<td style="padding:3px 10px;text-align:right;font-variant-numeric:tabular-nums">{_fmt(d.get("value"), d.get("unit",""))}</td>'
                 f'<td style="padding:3px 10px;text-align:right;font-variant-numeric:tabular-nums;color:{pal["text_dim"]}">{d.get("percentile_national","—")}</td></tr>')
    # Real Medicare provider-supply density (CMS FFS enrollment) for this state.
    supply_line = ""
    try:
        from rcm_mc.data import provider_supply as _ps
        st_abbr = _FIPS_ABBR.get(fips, "")
        tot = _ps.total_supply_for_state(st_abbr) if st_abbr else 0
        pc = _ps.primary_care_supply_for_state(st_abbr) if st_abbr else 0
        if tot:
            supply_line = (
                f'<p style="font-size:11px;color:{pal["text_dim"]};margin:6px 0 0">'
                f'Provider supply (CMS FFS, real): <b style="color:{pal["text"]}">{tot:,}</b> '
                f'Medicare-enrolled providers, <b style="color:{pal["text"]}">{pc:,}</b> '
                f'primary-care (approx). Density signal, not all providers.</p>')
    except Exception:
        supply_line = ""

    # Real SNF consolidation velocity (CMS Change-of-Ownership) for this state.
    chow_line = ""
    try:
        from rcm_mc.data import snf_chow as _chow
        st_abbr2 = _FIPS_ABBR.get(fips, "")
        n_chow = _chow.total_chows_for_state(st_abbr2) if st_abbr2 else 0
        if n_chow:
            sm = _chow.chow_summary()
            chow_line = (
                f'<p style="font-size:11px;color:{pal["text_dim"]};margin:6px 0 0">'
                f'SNF consolidation (CMS, real): <b style="color:{pal["text"]}">{n_chow:,}</b> '
                f'nursing-home ownership changes {sm.get("year_min","")}–{sm.get("year_max","")}. '
                f'M&A/consolidation signal — not a PE-specific flag.</p>')
    except Exception:
        chow_line = ""

    miss = ", ".join(score.get("missing_export_required", [])) if score else ""
    score_line = ""
    if score and score.get("overall_market_score") is not None:
        score_line = (f'<p style="font-size:11px;color:{pal["text_dim"]};margin:6px 0 0">'
                      f'Market score <b style="color:{pal["text"]}">{score["overall_market_score"]:.0f}</b> '
                      f'(partial — {miss or "none"} EXPORT REQUIRED).</p>')
    return (
        f'<div style="background:{pal["panel"]};border:1px solid {pal["border"]};'
        f'border-left:3px solid {pal["accent"]};padding:14px 16px;margin-bottom:16px">'
        f'<div style="font-size:11px;font-weight:600;letter-spacing:0.08em;'
        f'text-transform:uppercase;color:{pal["text_dim"]};margin-bottom:6px">'
        f'Market context · {_html.escape(prof["geo_name"])} · SimplyAnalytics-derived</div>'
        f'<table style="border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px;width:100%;max-width:420px">'
        f'<thead><tr style="border-bottom:1px solid {pal["border"]};color:{pal["text_dim"]}">'
        f'<th style="padding:3px 10px;text-align:left">Variable</th>'
        f'<th style="padding:3px 10px;text-align:right">Value</th>'
        f'<th style="padding:3px 10px;text-align:right">Pctile</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>{score_line}{supply_line}{chow_line}'
        f'<p style="font-size:11px;color:{pal["text_dim"]};margin:6px 0 0">'
        f'Market/area context — <b>not</b> provider-specific. Combine with CMS/HCRIS/'
        f'provider data before a decision. <a href="/market-intel/geo/{_html.escape(fips)}" '
        f'style="color:{pal["accent"]}">Full market profile &rarr;</a></p></div>')


def _default_variable() -> Optional[dict]:
    vs = _mi.load_market_variables()
    return vs[0] if vs else None


def render_market_geo_index(params: dict = None) -> str:
    params = params or {}
    variables = _mi.load_market_variables()
    var = next((v for v in variables if v["variable_id"] == params.get("var")),
               _default_variable())
    rep = _mi.report()

    if not var:
        body = ck_page_title("Market Intelligence — Geographic", eyebrow="MARKET INTEL") + \
            f'<p style="color:{P["text_dim"]}">No market data loaded yet.</p>'
        return chartis_shell(body, "Market Intelligence", active_nav="/market-intel")

    vid, unit = var["variable_id"], var.get("unit", "")
    rows = _mi.rank_markets(vid, "state")

    # Choropleth (reuse existing US state geometry); map FIPS→abbr.
    vals: Dict[str, float] = {}
    for r in rows:
        abbr = _FIPS_ABBR.get(r["fips"])
        v = r.get("value")
        if abbr and v not in (None, ""):
            vals[abbr] = float(v)
    fmt = (lambda x: f"{x*100:.1f}%") if unit == "pct" else (
        (lambda x: f"${x:,.0f}") if unit == "usd" else (lambda x: f"{x:,.1f}"))
    cmap = render_us_geo_map(
        vals, metric_label=var["display_name"], value_format=fmt,
        state_link_template="/market-intel/geo/{fips}",
        empty_message="No state data for this variable.")

    # Variable selector
    opts = "".join(
        f'<option value="{_html.escape(v["variable_id"])}"'
        f'{" selected" if v["variable_id"]==vid else ""}>{_html.escape(v["display_name"])}</option>'
        for v in variables)
    selector = (f'<form method="GET" action="/market-intel/geo" style="margin-bottom:14px">'
                f'<label style="font-size:11px;color:{P["text_dim"]}">Variable '
                f'<select name="var" onchange="this.form.submit()" style="margin-left:6px;'
                f'font-size:12px;padding:3px 6px">{opts}</select></label></form>')

    # Top markets table (real values + percentiles)
    trows = "".join(
        f'<tr style="border-bottom:1px solid {P["border"]}">'
        f'<td style="padding:5px 10px"><a href="/market-intel/geo/{_html.escape(r["fips"])}" '
        f'style="color:{P["accent"]};text-decoration:none">{_html.escape(r["geo_name"])}</a></td>'
        f'<td style="padding:5px 10px;text-align:right;font-variant-numeric:tabular-nums">{_fmt(float(r["value"]), unit)}</td>'
        f'<td style="padding:5px 10px;text-align:right;font-variant-numeric:tabular-nums;color:{P["text_dim"]}">{float(r.get("percentile_national") or 0):.0f}</td></tr>'
        for r in rows[:15])
    table = (f'<table style="width:100%;border-collapse:collapse;background:{P["panel"]};'
             f'border:1px solid {P["border"]}"><thead>'
             f'<tr style="text-align:left;color:{P["text_dim"]};font-size:11px;text-transform:uppercase;border-bottom:2px solid {P["border"]}">'
             f'<th style="padding:6px 10px">Market</th><th style="padding:6px 10px;text-align:right">{_html.escape(var["display_name"])}</th>'
             f'<th style="padding:6px 10px;text-align:right">Pctile</th></tr></thead><tbody>{trows}</tbody></table>')

    backlog = "".join(f'<li>{_html.escape(n)} <span style="color:{P["text_dim"]}">· {c}</span></li>'
                      for n, c in _BACKLOG)
    cell = f"background:{P['panel']};border:1px solid {P['border']};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{P['text_dim']};text-transform:uppercase;margin-bottom:10px"

    body = (
        ck_page_title("Market Intelligence — Geographic", eyebrow="MARKET INTEL",
                      meta=f'{len(variables)} variable(s) · {rep.get("state_values",0)} state values · SimplyAnalytics-derived')
        + ck_source_purpose(
            purpose="Score and rank geographic markets for diligence: senior "
                    "demand, payer mix, income, provider supply — then validate "
                    "with CMS/HCRIS/provider data.",
            universe="licensed-market-derived", confidence="derived",
            source="Licensed SimplyAnalytics exports (FIPS-keyed); market/area "
                   "context, not provider-specific. Verify source/year.",
            next_action="Open a market for its profile, or use Target Screener")
        + f'<p style="margin:6px 0 14px">{_LICENSE_CHIP}</p>'
        + selector
        + f'<div style="{cell}"><div style="{h3}">{_html.escape(var["display_name"])} by state</div>{cmap}</div>'
        + f'<div style="{cell}"><div style="{h3}">Top markets — {_html.escape(var["display_name"])}</div>{table}'
        + f'<p style="font-size:11px;color:{P["text_dim"]};margin:8px 0 0">Percentile = national rank among states with real values. '
        + f'{_html.escape(var.get("diligence_use",""))}</p></div>'
        + f'<div style="{cell}"><div style="{h3}">Export backlog (design refs, not yet data)</div>'
        + f'<p style="font-size:12px;color:{P["text_dim"]};margin:0 0 8px">The map screenshots show these variables; they render '
        + f'as EXPORT REQUIRED until the underlying SimplyAnalytics export is ingested (never fabricated):</p>'
        + f'<ul style="margin:0;padding-left:18px;font-size:12px;color:{P["text"]}">{backlog}</ul></div>')
    return chartis_shell(body, "Market Intelligence — Geographic", active_nav="/market-intel",
                         editorial_intro={
                             "eyebrow": "MARKET INTELLIGENCE",
                             "headline": "Which markets carry the demand.",
                             "italic_word": "demand",
                             "body": "Licensed SimplyAnalytics-derived demographic, payer, and "
                                     "supply context by FIPS — connected to PEdesk diligence so you "
                                     "can rank markets and validate them against real CMS/HCRIS data."})


def render_market_geo_detail(fips: str, params: dict = None) -> str:
    prof = _mi.market_profile_for_geo(fips)
    if not prof:
        body = ck_page_title("Market not found", eyebrow="MARKET INTEL") + \
            f'<p style="color:{P["text_dim"]}">No market data for FIPS "{_html.escape(str(fips))}". ' \
            f'<a href="/market-intel/geo" style="color:{P["accent"]}">Back to Market Intelligence</a>.</p>'
        return chartis_shell(body, "Market", active_nav="/market-intel")

    kpis = ""
    score = _mi.market_demand_score(fips)
    if score.get("overall_market_score") is not None:
        kpis += ck_kpi_block("Market Score", f'{score["overall_market_score"]:.0f}',
                             f'{len(score["components"])} of {len(score["components"])+len(score["missing_export_required"])} components', "")
    for vid, d in prof["variables"].items():
        v = _mi.load_market_variable(vid) or {}
        kpis += ck_kpi_block(v.get("display_name", vid), _fmt(d.get("value"), d.get("unit", "")),
                             f'pctile {d.get("percentile_national","—")} · {d.get("year","")}', "")
    # Export-required variables for transparency
    backlog = "".join(f'<li>{_html.escape(n)} <span style="color:{P["text_dim"]}">· EXPORT REQUIRED</span></li>'
                      for n, _ in _BACKLOG)
    cell = f"background:{P['panel']};border:1px solid {P['border']};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{P['text_dim']};text-transform:uppercase;margin-bottom:10px"

    body = (
        ck_page_title(f'{prof["geo_name"]} — Market Profile', eyebrow="MARKET INTEL",
                      meta=f'FIPS {prof["fips"]} · {prof["geo_level"]} · SimplyAnalytics-derived')
        + ck_source_purpose(
            purpose="Market context for this geography — combine with CMS/HCRIS/"
                    "provider data before a decision.",
            universe="licensed-market-derived", confidence="derived",
            source="Licensed SimplyAnalytics export; market/area context, not "
                   "provider-specific; county values can mask submarket variation.",
            next_action="Cross-reference HCRIS X-Ray / provider profiles in this market")
        + f'<p style="margin:6px 0 14px">{_LICENSE_CHIP}</p>'
        + f'<div class="ck-kpi-grid" style="margin-bottom:16px">{kpis}</div>'
        + (f'<div style="{cell}"><div style="{h3}">Market score — formula</div>'
           f'<p style="font-size:12px;color:{P["text_dim"]};margin:0">'
           f'{_html.escape(score.get("formula",""))} Components present: '
           f'{_html.escape(", ".join(score.get("components",{}).keys()) or "none")}. '
           f'EXPORT REQUIRED: {_html.escape(", ".join(score.get("missing_export_required",[])) or "none")}.'
           f'</p></div>' if score.get("overall_market_score") is not None else "")
        + f'<div style="{cell}"><div style="{h3}">Diligence questions</div>'
        + f'<ul style="margin:0;padding-left:18px;font-size:12px;line-height:1.7;color:{P["text"]}">'
        + '<li>Is this market older / higher-demand than the national median?</li>'
        + '<li>Does the payer mix favor commercial reimbursement?</li>'
        + '<li>Is provider supply dense or sparse relative to demand?</li>'
        + '<li>What do CMS/HCRIS provider data show for targets in this market?</li></ul></div>'
        + f'<div style="{cell}"><div style="{h3}">Not yet on record (export required)</div>'
        + f'<ul style="margin:0;padding-left:18px;font-size:12px;color:{P["text_dim"]}">{backlog}</ul></div>')
    return chartis_shell(body, f'{prof["geo_name"]} Market', active_nav="/market-intel")
