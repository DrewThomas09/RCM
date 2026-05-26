"""State Comparison — /state-compare.

A new cross-dataset analysis mode: pick 2–4 states and compare them side by
side across every real state-keyed public dataset PEdesk has ingested —
provider supply (CMS), SNF consolidation (CHOW), Medicare Advantage (CMS),
social determinants (CDC PLACES), patient experience (CMS HCAHPS),
demographics (Census/ACS), and provider shortage (HRSA HPSA).

100% real public data, each row source-labelled. No synthetic values; states
with no data on record render "—".
"""
from __future__ import annotations

import html as _html
from typing import Dict, List

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_page_title

_DEFAULT = ["CA", "TX", "FL"]
_VALID = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL","IN",
    "IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH",
    "NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT",
    "VT","VA","WA","WV","WI","WY",
}


def _parse_states(params: Dict) -> List[str]:
    raw = (params or {}).get("states", "")
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    out = [s.strip().upper() for s in str(raw).split(",") if s.strip()]
    out = [s for s in out if s in _VALID]
    return (out or _DEFAULT)[:4]


def _collect(state: str) -> Dict[str, str]:
    """Pull real metrics for one state from the committed public-data loaders.
    Every value is real or '—' (never fabricated)."""
    def _num(v, fmt):
        try:
            return fmt(v) if v is not None and v == v else "—"
        except Exception:
            return "—"
    row: Dict[str, str] = {}
    try:
        from rcm_mc.data import county_demographics as _d
        dm = _d.demographics_state(state)
        row["Population"] = _num(dm.get("population"), lambda x: f"{int(x):,}")
        row["Age 65+"] = _num(dm.get("pct_age_65_plus"), lambda x: f"{x*100:.1f}%")
        row["Median HH income"] = _num(dm.get("median_household_income"), lambda x: f"${x:,.0f}")
        row["Uninsured (ACS)"] = _num(dm.get("uninsured_rate"), lambda x: f"{x*100:.1f}%")
    except Exception:
        pass
    try:
        from rcm_mc.data import provider_supply as _ps
        tot = _ps.total_supply_for_state(state); pc = _ps.primary_care_supply_for_state(state)
        row["Provider supply (CMS FFS)"] = f"{tot:,}" if tot else "—"
        row["Primary-care supply (approx)"] = f"{pc:,}" if pc else "—"
    except Exception:
        pass
    try:
        from rcm_mc.data import snf_chow as _c
        n = _c.total_chows_for_state(state)
        row["SNF ownership changes (CHOW)"] = f"{n:,}" if n else "—"
    except Exception:
        pass
    try:
        from rcm_mc.data import ma_data as _ma
        ma = _ma.ma_state(state)
        row["MA enrollment (CMS)"] = _num(ma.get("ma_enrollment"), lambda x: f"{int(x):,}")
        row["Dual-eligible % (MA)"] = _num(ma.get("dual_eligible_pct"), lambda x: f"{x*100:.1f}%")
    except Exception:
        pass
    try:
        from rcm_mc.data import cdc_places_agg as _pl
        pl = _pl.places_equity_state(state)
        row["Uninsured 18–64 (PLACES)"] = _num(pl.get("uninsured_18_64"), lambda x: f"{x:.1f}%")
        row["Food insecurity (PLACES)"] = _num(pl.get("food_insecurity"), lambda x: f"{x:.1f}%")
        row["Obesity (PLACES)"] = _num(pl.get("obesity"), lambda x: f"{x:.1f}%")
    except Exception:
        pass
    try:
        from rcm_mc.data import hcahps_data as _h
        hc = _h.hcahps_state(state)
        row["Would recommend (HCAHPS)"] = _num(hc.get("would_definitely_recommend"), lambda x: f"{x:.0f}%")
        row["Overall 9–10 (HCAHPS)"] = _num(hc.get("overall_rating_9_10"), lambda x: f"{x:.0f}%")
    except Exception:
        pass
    try:
        from rcm_mc.data import hrsa_data as _hr
        hp = _hr.hpsa_state(state)
        row["PC shortage areas (HRSA HPSA)"] = _num(hp.get("designated_pc_hpsas"), lambda x: f"{int(x):,}")
    except Exception:
        pass
    return row


_ROW_ORDER = [
    "Population", "Age 65+", "Median HH income", "Uninsured (ACS)",
    "Provider supply (CMS FFS)", "Primary-care supply (approx)",
    "PC shortage areas (HRSA HPSA)", "SNF ownership changes (CHOW)",
    "MA enrollment (CMS)", "Dual-eligible % (MA)",
    "Uninsured 18–64 (PLACES)", "Food insecurity (PLACES)", "Obesity (PLACES)",
    "Would recommend (HCAHPS)", "Overall 9–10 (HCAHPS)",
]


def render_state_compare(params: Dict = None) -> str:
    states = _parse_states(params)
    data = {s: _collect(s) for s in states}
    border = P["border"]; tp = P["text"]; td = P["text_dim"]; fa = P.get("text_faint", td); ac = P["accent"]

    inp = (f'background:{P["panel_alt"]};color:{tp};border:1px solid {border};'
           f'padding:6px 8px;font-family:JetBrains Mono,monospace;font-size:12px;border-radius:2px')
    form = (
        f'<form method="get" action="/state-compare" style="margin-bottom:16px;display:flex;gap:10px;align-items:center">'
        f'<label style="font-size:11px;color:{td}">States (comma-separated, max 4)'
        f'<input name="states" value="{_html.escape(",".join(states))}" style="{inp};margin-left:6px;width:200px"></label>'
        f'<button type="submit" style="background:{ac};color:#fff;border:none;padding:7px 16px;'
        f'font-family:JetBrains Mono,monospace;font-size:12px;border-radius:2px;cursor:pointer">Compare</button></form>'
    )

    th = (f'<th style="text-align:left;padding:6px 10px;border-bottom:2px solid {border};'
          f'font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">Metric</th>')
    for s in states:
        th += (f'<th style="text-align:right;padding:6px 10px;border-bottom:2px solid {border};'
               f'font-family:JetBrains Mono,monospace;font-size:13px;color:{tp}">{_html.escape(s)}</th>')
    rows = ""
    for i, metric in enumerate(_ROW_ORDER):
        bg = P["panel_alt"] if i % 2 else P["panel"]
        cells = (f'<td style="padding:5px 10px;font-size:11px;color:{td};background:{bg}">{_html.escape(metric)}</td>')
        for s in states:
            v = data[s].get(metric, "—")
            cells += (f'<td style="padding:5px 10px;text-align:right;font-family:JetBrains Mono,monospace;'
                      f'font-size:12px;font-variant-numeric:tabular-nums;color:{tp};background:{bg}">{_html.escape(str(v))}</td>')
        rows += f"<tr>{cells}</tr>"

    body = f"""
<div class="ck-page-wrap">
  {ck_page_title("State Comparison", eyebrow="MARKET INTEL", meta="Side-by-side across every real state-keyed public dataset — CMS · CDC · HRSA · Census")}
  <p style="font-size:13px;color:{td};max-width:72ch;margin:0 0 14px">
    Compare states across PEdesk's real public-data layers. Every figure is sourced
    (CMS provider supply / CHOW / MA · CDC PLACES · CMS HCAHPS · Census/ACS · HRSA HPSA);
    nothing is fabricated, and states without data on record show &ldquo;&mdash;&rdquo;.
  </p>
  {form}
  <div style="overflow-x:auto;border:1px solid {border};border-radius:3px">
  <table style="width:100%;border-collapse:collapse"><thead><tr>{th}</tr></thead><tbody>{rows}</tbody></table>
  </div>
  <p style="font-size:10px;color:{fa};margin-top:10px">
    Sources: CMS FFS provider enrollment · CMS SNF CHOW · CMS MA geographic enrollment ·
    CDC PLACES (model-based, full-population) · CMS HCAHPS (state) · Census/ACS via County
    Health Rankings · HRSA HPSA. Area-level — combine with deal-specific data before a decision.
  </p>
</div>"""
    return chartis_shell(body, "State Comparison", active_nav="/state-compare")
