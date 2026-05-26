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


def _raw(state: str) -> Dict[str, float]:
    """Pull every real state-keyed metric as a raw number (or absent).

    One source of truth shared by the comparison table (/state-compare) and the
    rankings leaderboard (/state-rankings). A loader miss or non-finite value is
    simply omitted from the dict — it is never replaced with a fabricated number.
    """
    out: Dict[str, float] = {}

    def _set(key, fn):
        try:
            v = fn()
            if v is not None and v == v:  # not None, not NaN
                out[key] = float(v)
        except Exception:
            pass

    try:
        from rcm_mc.data import county_demographics as _d
        dm = _d.demographics_state(state)
        _set("population", lambda: dm.get("population"))
        _set("age_65_plus", lambda: dm.get("pct_age_65_plus"))
        _set("median_income", lambda: dm.get("median_household_income"))
        _set("uninsured_acs", lambda: dm.get("uninsured_rate"))
    except Exception:
        pass
    try:
        from rcm_mc.data import provider_supply as _ps
        _set("provider_supply", lambda: _ps.total_supply_for_state(state) or None)
        _set("pc_supply", lambda: _ps.primary_care_supply_for_state(state) or None)
    except Exception:
        pass
    try:
        from rcm_mc.data import snf_chow as _c
        _set("snf_chow", lambda: _c.total_chows_for_state(state) or None)
    except Exception:
        pass
    try:
        from rcm_mc.data import ma_data as _ma
        ma = _ma.ma_state(state)
        _set("ma_enrollment", lambda: ma.get("ma_enrollment"))
        _set("dual_pct", lambda: ma.get("dual_eligible_pct"))
    except Exception:
        pass
    try:
        from rcm_mc.data import cdc_places_agg as _pl
        pl = _pl.places_equity_state(state)
        _set("uninsured_places", lambda: pl.get("uninsured_18_64"))
        _set("food_insecurity", lambda: pl.get("food_insecurity"))
        _set("obesity", lambda: pl.get("obesity"))
    except Exception:
        pass
    try:
        from rcm_mc.data import hcahps_data as _h
        hc = _h.hcahps_state(state)
        _set("hcahps_recommend", lambda: hc.get("would_definitely_recommend"))
        _set("hcahps_overall", lambda: hc.get("overall_rating_9_10"))
    except Exception:
        pass
    try:
        from rcm_mc.data import hrsa_data as _hr
        hp = _hr.hpsa_state(state)
        _set("hpsa_pc", lambda: hp.get("designated_pc_hpsas"))
    except Exception:
        pass
    try:
        from rcm_mc.data import mssp_aco_data as _aco
        _set("mssp_acos", lambda: _aco.acos_for_state(state) or None)
    except Exception:
        pass
    try:
        from rcm_mc.data import oig_leie as _leie
        _set("oig_exclusions", lambda: _leie.exclusions_for_state(state) or None)
    except Exception:
        pass
    # Derived: Medicare-FFS-enrolled providers per 1,000 residents — a real
    # capacity signal computed from two real values already pulled above.
    if out.get("provider_supply") and out.get("population"):
        out["providers_per_1k"] = out["provider_supply"] / (out["population"] / 1000.0)
    return out


# Single metric registry: (key, label, source, formatter, higher_is_better).
# Order here drives both the comparison rows and the ranking metric picker.
_METRICS = [
    ("population",       "Population",                    "Census/ACS",  lambda x: f"{int(x):,}",     True),
    ("age_65_plus",      "Age 65+",                       "Census/ACS",  lambda x: f"{x*100:.1f}%",   True),
    ("median_income",    "Median HH income",              "Census/ACS",  lambda x: f"${x:,.0f}",      True),
    ("uninsured_acs",    "Uninsured (ACS)",               "Census/ACS",  lambda x: f"{x*100:.1f}%",   False),
    ("provider_supply",  "Provider supply (CMS FFS)",     "CMS FFS",     lambda x: f"{int(x):,}",     True),
    ("pc_supply",        "Primary-care supply (approx)",  "CMS FFS",     lambda x: f"{int(x):,}",     True),
    ("hpsa_pc",          "PC shortage areas (HRSA HPSA)", "HRSA HPSA",   lambda x: f"{int(x):,}",     False),
    ("snf_chow",         "SNF ownership changes (CHOW)",  "CMS CHOW",    lambda x: f"{int(x):,}",     None),
    ("ma_enrollment",    "MA enrollment (CMS)",           "CMS MA",      lambda x: f"{int(x):,}",     True),
    ("dual_pct",         "Dual-eligible % (MA)",          "CMS MA",      lambda x: f"{x*100:.1f}%",   None),
    ("uninsured_places", "Uninsured 18–64 (PLACES)",      "CDC PLACES",  lambda x: f"{x:.1f}%",       False),
    ("food_insecurity",  "Food insecurity (PLACES)",      "CDC PLACES",  lambda x: f"{x:.1f}%",       False),
    ("obesity",          "Obesity (PLACES)",              "CDC PLACES",  lambda x: f"{x:.1f}%",       False),
    ("hcahps_recommend", "Would recommend (HCAHPS)",      "CMS HCAHPS",  lambda x: f"{x:.0f}%",       True),
    ("hcahps_overall",   "Overall 9–10 (HCAHPS)",         "CMS HCAHPS",  lambda x: f"{x:.0f}%",       True),
    ("mssp_acos",        "MSSP ACOs (CMS)",               "CMS MSSP",    lambda x: f"{int(x):,}",     True),
    ("oig_exclusions",   "OIG exclusions (count)",        "OIG LEIE",    lambda x: f"{int(x):,}",     None),
    ("providers_per_1k", "Providers per 1k (CMS FFS)",    "CMS FFS",     lambda x: f"{x:.2f}",        True),
]
_METRIC_BY_KEY = {m[0]: m for m in _METRICS}
_ROW_ORDER = [m[1] for m in _METRICS]


def _fmt(key: str, v) -> str:
    """Format a raw metric value with its registered formatter, or '—'."""
    m = _METRIC_BY_KEY.get(key)
    if m is None or v is None or v != v:
        return "—"
    try:
        return m[3](v)
    except Exception:
        return "—"


def _collect(state: str) -> Dict[str, str]:
    """Real metrics for one state, keyed by display label. Every value is real
    or '—' (never fabricated). Derived from the shared :func:`_raw` extractor."""
    raw = _raw(state)
    return {m[1]: _fmt(m[0], raw.get(m[0])) for m in _METRICS}


def _direction(higher) -> str:
    return "higher_better" if higher else "lower_better" if higher is False else "neutral"


def geo_states_payload(only_state: str = "") -> Dict:
    """JSON-serializable view of the shared real-metric layer for the API.

    Raw numeric values per state (``None`` where a state has no value on record
    — never fabricated), plus metric metadata and the national median. If
    ``only_state`` is given and valid, restricts ``states`` to that one.
    """
    sel = (only_state or "").strip().upper()
    states = [sel] if sel in _VALID else sorted(_VALID)
    meds = national_medians()
    metrics_meta = [
        {"key": k, "label": lbl, "source": src, "direction": _direction(h)}
        for k, lbl, src, _f, h in _METRICS
    ]
    data: Dict[str, Dict] = {}
    for s in states:
        r = _raw(s)
        data[s] = {
            k: (float(r[k]) if (r.get(k) is not None and r.get(k) == r.get(k)) else None)
            for k, *_rest in _METRICS
        }
    return {
        "source": "PEdesk Geographic Intelligence — shared real public-data metric registry",
        "jurisdictions": len(_VALID),
        "metrics": metrics_meta,
        "national_median": {k: meds.get(k) for k, *_rest in _METRICS},
        "states": data,
    }


def compare_dataframe(states: List[str]):
    """Raw (unformatted) metric×state table for CSV export — numbers a partner
    can compute on. Missing values are blank cells, never fabricated."""
    import pandas as _pd
    raws = {s: _raw(s) for s in states}
    meds = national_medians()
    rows = []
    for key, label, source, _f, _h in _METRICS:
        row = {"Metric": label, "Source": source}
        for s in states:
            v = raws[s].get(key)
            row[s] = v if (v is not None and v == v) else ""
        row["US_Median"] = meds.get(key, "")
        rows.append(row)
    return _pd.DataFrame(rows, columns=["Metric", "Source"] + list(states) + ["US_Median"])


def national_medians() -> Dict[str, float]:
    """National median per metric across all reporting states (50 + DC) — the
    benchmark column. Robust to outliers; states with no value are ignored,
    and a metric no state reports is simply absent (never fabricated)."""
    raws = [_raw(s) for s in sorted(_VALID)]
    out: Dict[str, float] = {}
    for key, *_rest in _METRICS:
        vals = sorted(r[key] for r in raws
                      if r.get(key) is not None and r[key] == r[key])
        k = len(vals)
        if k:
            mid = k // 2
            out[key] = vals[mid] if k % 2 else (vals[mid - 1] + vals[mid]) / 2.0
    return out


def render_state_compare(params: Dict = None) -> str:
    states = _parse_states(params)
    data = {s: _collect(s) for s in states}
    raws = {s: _raw(s) for s in states}
    meds = national_medians()
    border = P["border"]; tp = P["text"]; td = P["text_dim"]; fa = P.get("text_faint", td); ac = P["accent"]
    pos_c = P["positive"]; warn_c = P["warning"]

    inp = (f'background:{P["panel_alt"]};color:{tp};border:1px solid {border};'
           f'padding:6px 8px;font-family:JetBrains Mono,monospace;font-size:12px;border-radius:2px')
    form = (
        f'<form method="get" action="/state-compare" style="margin-bottom:16px;display:flex;gap:10px;align-items:center">'
        f'<label style="font-size:11px;color:{td}">States (comma-separated, max 4)'
        f'<input name="states" value="{_html.escape(",".join(states))}" style="{inp};margin-left:6px;width:200px"></label>'
        f'<button type="submit" style="background:{ac};color:#fff;border:none;padding:7px 16px;'
        f'font-family:JetBrains Mono,monospace;font-size:12px;border-radius:2px;cursor:pointer">Compare</button>'
        f'<a href="/state-compare.csv?states={_html.escape(",".join(states))}" '
        f'style="font-size:11px;color:{ac};text-decoration:none;margin-left:4px">Export CSV &#8595;</a></form>'
    )

    th = (f'<th style="text-align:left;padding:6px 10px;border-bottom:2px solid {border};'
          f'font-size:10px;color:{td};text-transform:uppercase;letter-spacing:0.06em">Metric</th>')
    for s in states:
        th += (f'<th style="text-align:right;padding:6px 10px;border-bottom:2px solid {border};'
               f'font-family:JetBrains Mono,monospace;font-size:13px;color:{tp}">{_html.escape(s)}</th>')
    # trailing benchmark column
    th += (f'<th style="text-align:right;padding:6px 10px;border-bottom:2px solid {border};'
           f'border-left:1px solid {border};font-size:10px;color:{td};text-transform:uppercase;'
           f'letter-spacing:0.06em">U.S. median</th>')
    rows = ""
    for i, (key, metric, _src, _f, higher) in enumerate(_METRICS):
        bg = P["panel_alt"] if i % 2 else P["panel"]
        cells = (f'<td style="padding:5px 10px;font-size:11px;color:{td};background:{bg}">{_html.escape(metric)}</td>')
        # direction-aware best/worst across the selected states (only when the
        # metric has a good/bad direction and there's a real spread to call)
        present = [(s, raws[s][key]) for s in states
                   if raws[s].get(key) is not None and raws[s][key] == raws[s][key]]
        best_s = worst_s = None
        if higher is not None and len(present) >= 2:
            vals = [v for _, v in present]
            if max(vals) != min(vals):
                best_v = max(vals) if higher else min(vals)
                worst_v = min(vals) if higher else max(vals)
                best_s = next(s for s, v in present if v == best_v)
                worst_s = next(s for s, v in present if v == worst_v)
        for s in states:
            v = data[s].get(metric, "—")
            col = tp; weight = "normal"
            if s == best_s:
                col = pos_c; weight = "600"
            elif s == worst_s:
                col = warn_c
            cells += (f'<td style="padding:5px 10px;text-align:right;font-family:JetBrains Mono,monospace;'
                      f'font-size:12px;font-variant-numeric:tabular-nums;color:{col};font-weight:{weight};'
                      f'background:{bg}">{_html.escape(str(v))}</td>')
        med_str = _fmt(key, meds.get(key))
        cells += (f'<td style="padding:5px 10px;text-align:right;font-family:JetBrains Mono,monospace;'
                  f'font-size:12px;font-variant-numeric:tabular-nums;color:{td};background:{bg};'
                  f'border-left:1px solid {border}">{_html.escape(med_str)}</td>')
        rows += f"<tr>{cells}</tr>"

    body = f"""
<div class="ck-page-wrap">
  {ck_page_title("State Comparison", eyebrow="MARKET INTEL", meta="Side-by-side across every real state-keyed public dataset — CMS · CDC · HRSA · Census")}
  <p style="font-size:13px;color:{td};max-width:72ch;margin:0 0 14px">
    Compare states across PEdesk's real public-data layers, with a trailing
    U.S.-median column for national context. Per metric, the
    <b style="color:{pos_c}">best</b> selected state is highlighted and the
    <b style="color:{warn_c}">weakest</b> tinted (directional metrics only).
    Every figure is sourced
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
    Health Rankings · HRSA HPSA · CMS MSSP ACOs. Area-level — combine with deal-specific data before a decision.
  </p>
</div>"""
    return chartis_shell(body, "State Comparison", active_nav="/state-compare")
