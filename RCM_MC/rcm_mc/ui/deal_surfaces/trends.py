"""Surface 16 · Trends — per-metric time-series trajectory + forecast.

Wired to `data.hcris.get_trend` — the same multi-year HCRIS loader the
existing /hospital/<ccn>/history page uses. Computes least-squares slope
per year and a one-year-ahead point forecast for each metric the deal team
typically tracks. The spec calls for QUARTERLY slope, but HCRIS only
publishes annual filings — the surface labels the cadence explicitly ("per
year") so partners aren't misled.

Components shipped (all 4 in the spec, adapted from quarterly → annual
since HCRIS is annual):
1. Hero strip       — metrics tracked, improving count, declining count
2. Trend rows       — direction arrow + bar + slope per year + confidence
3. Detail table     — same metrics with direction badge, slope, next-year
                      forecast, confidence
4. Action row       — cross-links to /hospital/<ccn>/history, Bridge, Predicted
"""
from __future__ import annotations

import html as _html
import math
from typing import Any, Dict, List, Optional, Tuple

from ._shell import _fmt_money, _fmt_pct, deal_shell


def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if (f != f or math.isinf(f)) else f


def _panel(eyebrow: str, title: str, body_html: str) -> str:
    return (
        '<section style="background:#fff;border:1px solid #c9c1ac;'
        'padding:20px 22px;margin:0 0 18px;">'
        f'<span style="font-family:var(--sc-mono);font-size:10px;'
        f'letter-spacing:.18em;text-transform:uppercase;color:#1f7a5a;">'
        f'{_html.escape(eyebrow)}</span>'
        f'<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
        f'line-height:1.15;margin:6px 0 14px;color:#15202b;">'
        f'{_html.escape(title)}</h3>'
        f'{body_html}</section>'
    )


def _empty(reason: str) -> str:
    return (
        '<section style="background:#faf6ec;border:1px solid #c9c1ac;'
        'padding:24px 26px;">'
        '<span style="font-family:var(--sc-mono);font-size:10px;'
        'letter-spacing:.18em;text-transform:uppercase;color:#b8842e;">'
        'Trends cannot run</span>'
        '<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
        'margin:6px 0 12px;color:#15202b;">'
        'Insufficient HCRIS history for this hospital</h3>'
        f'<p style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;">{_html.escape(reason)} Trends needs at '
        'least two fiscal-year filings to compute a slope; until management '
        'supplies quarterly operating data, the surface is HCRIS-bound.</p>'
        '</section>'
    )


# ── Metric registry ────────────────────────────────────────────────────
# Per-metric: label, accessor from a single trend-row dict, "is higher
# favorable?" (True/False/None). The direction arrow is independent of
# slope sign — it answers "is this MOVEMENT favorable?".
def _op_margin_row(row: Dict[str, Any]) -> Optional[float]:
    npr = _safe_float(row.get("net_patient_revenue"))
    opex = _safe_float(row.get("operating_expenses"))
    if not npr or not opex or npr <= 1e4:
        return None
    return (npr - opex) / npr


def _occupancy_row(row: Dict[str, Any]) -> Optional[float]:
    pd = _safe_float(row.get("total_patient_days"))
    bda = _safe_float(row.get("bed_days_available"))
    if not pd or not bda or bda <= 0:
        return None
    return pd / bda


METRICS: Tuple[Tuple[str, str, str, Any, Optional[bool]], ...] = (
    # (key, label, value_format, accessor, higher_is_better)
    ("net_patient_revenue", "Net patient revenue", "money",
     lambda r: _safe_float(r.get("net_patient_revenue")), True),
    ("operating_expenses", "Operating expenses", "money",
     lambda r: _safe_float(r.get("operating_expenses")), None),
    ("op_margin", "Operating margin", "pct",
     _op_margin_row, True),
    ("net_income", "Net income", "money",
     lambda r: _safe_float(r.get("net_income")), True),
    ("beds", "Beds", "int",
     lambda r: _safe_float(r.get("beds")), None),
    ("total_patient_days", "Total patient days", "int",
     lambda r: _safe_float(r.get("total_patient_days")), True),
    ("occupancy", "Occupancy", "pct",
     _occupancy_row, True),
)


def _format_value(val: Optional[float], fmt: str) -> str:
    if val is None:
        return "—"
    if fmt == "money":
        return _fmt_money(val)
    if fmt == "pct":
        return _fmt_pct(val)
    if fmt == "int":
        return f"{int(val):,}"
    return f"{val:,.2f}"


# ── Slope math (least-squares) ─────────────────────────────────────────

def _ols_slope(xs: List[float], ys: List[float]) -> Tuple[Optional[float], Optional[float]]:
    """Return (slope, R²) for y vs x. None if too few points or no x-variance."""
    if len(xs) < 2 or len(ys) != len(xs):
        return None, None
    n = len(xs)
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    sxx = sum((x - x_mean) ** 2 for x in xs)
    if sxx == 0:
        return None, None
    sxy = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n))
    syy = sum((y - y_mean) ** 2 for y in ys)
    slope = sxy / sxx
    r2 = (sxy ** 2) / (sxx * syy) if syy > 0 else 0.0
    return slope, max(0.0, min(1.0, r2))


def _trend_row(metric_key: str, label: str, fmt: str, accessor: Any,
               higher_better: Optional[bool],
               trend_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute one metric's trend over the multi-year HCRIS panel."""
    years: List[float] = []
    values: List[float] = []
    for r in trend_rows:
        yr = _safe_float(r.get("fiscal_year"))
        v = accessor(r)
        if yr is None or v is None:
            continue
        years.append(yr)
        values.append(v)
    if len(years) < 2:
        return {"key": metric_key, "label": label, "fmt": fmt,
                "n": len(years), "slope": None, "r2": None,
                "current": values[-1] if values else None,
                "next": None, "higher_better": higher_better,
                "status": "building"}
    slope, r2 = _ols_slope(years, values)
    current = values[-1]
    forecast = current + slope if slope is not None else None
    # Direction: is movement favorable?
    if slope is None or higher_better is None:
        direction = "neutral"
    elif (slope > 0 and higher_better) or (slope < 0 and not higher_better):
        direction = "improving"
    elif (slope > 0 and not higher_better) or (slope < 0 and higher_better):
        direction = "declining"
    else:
        direction = "stable"
    return {"key": metric_key, "label": label, "fmt": fmt,
            "n": len(years), "slope": slope, "r2": r2,
            "current": current, "next": forecast,
            "higher_better": higher_better, "direction": direction,
            "status": "ok"}


DIRECTION_GLYPH = {
    "improving": ("▲", "improving", "#1f7a5a"),
    "declining": ("▼", "declining", "#b5321e"),
    "stable":    ("▶", "stable",    "#6a7480"),
    "neutral":   ("▶", "neutral",   "#6a7480"),
    "building":  ("·", "building",  "#b8842e"),
}


# ── Rendering ──────────────────────────────────────────────────────────

def _hero(rows: List[Dict[str, Any]]) -> str:
    tracked = len(rows)
    improving = sum(1 for r in rows if r.get("direction") == "improving")
    declining = sum(1 for r in rows if r.get("direction") == "declining")
    building = sum(1 for r in rows if r.get("status") == "building")
    years_set: set = set()
    for r in rows:
        years_set.add(r["n"])
    years_max = max(years_set) if years_set else 0
    cells_data = [
        ("Metrics tracked",      f"{tracked}"),
        ("Improving",            f"{improving}"),
        ("Declining",            f"{declining}"),
        ("Building (need more)", f"{building}"),
        ("Fiscal years observed",f"{years_max}"),
        ("Forecast cadence",     "Per year"),
    ]
    cells = "".join(
        '<div style="border:1px solid #c9c1ac;background:#faf6ec;padding:12px 14px;">'
        f'<dt style="font-family:var(--sc-mono);font-size:9.5px;'
        f'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;'
        f'margin:0 0 4px;">{_html.escape(label)}</dt>'
        '<dd style="font-family:var(--sc-serif);font-size:20px;margin:0;'
        'color:#15202b;font-variant-numeric:tabular-nums;">'
        f'{_html.escape(value)}</dd></div>'
        for label, value in cells_data
    )
    return (
        '<dl style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));'
        f'gap:12px;margin:0;">{cells}</dl>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'CADENCE IS ANNUAL BECAUSE HCRIS PUBLISHES ANNUAL FILINGS. THE SPEC\'S '
        '"PER-QUARTER" CADENCE REQUIRES MANAGEMENT-SUPPLIED OPERATING METRICS.</p>'
    )


def _trend_row_render(row: Dict[str, Any]) -> str:
    glyph, label, color = DIRECTION_GLYPH.get(row.get("direction", "neutral"),
                                              DIRECTION_GLYPH["neutral"])
    if row["status"] == "building":
        glyph, label, color = DIRECTION_GLYPH["building"]
    # Slope display
    slope = row.get("slope")
    fmt = row.get("fmt", "money")
    if slope is None:
        slope_str = "—"
    elif fmt == "money":
        slope_str = f"{_fmt_money(slope)}/yr"
    elif fmt == "pct":
        slope_str = f"{slope*100:+.2f} pp/yr"
    elif fmt == "int":
        slope_str = f"{slope:+,.0f}/yr"
    else:
        slope_str = f"{slope:+,.2f}/yr"
    # Confidence (R² × n-factor) — bar width
    r2 = row.get("r2")
    conf = 0.0
    if r2 is not None:
        conf = float(r2)
        # Penalize confidence when n is small (only 2 years observed → 0.5x)
        n = int(row.get("n", 0))
        if n < 4:
            conf *= n / 4.0
    conf_w = max(2.0, min(100.0, conf * 100.0))
    return (
        '<div style="display:grid;grid-template-columns:1.4fr 0.7fr 1.4fr 1.2fr 0.9fr;'
        'gap:14px;align-items:center;padding:8px 0;border-bottom:1px solid #ece6d7;">'
        '<div>'
        f'<div style="font-family:var(--sc-serif);font-size:14px;'
        f'color:#15202b;">{_html.escape(row["label"])}</div>'
        f'<div style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        f'text-transform:uppercase;color:#6a7480;margin-top:2px;">'
        f'{_html.escape(label)} · n={row["n"]}</div></div>'
        f'<div style="font-family:var(--sc-serif);font-size:18px;color:{color};'
        f'text-align:center;">{glyph}</div>'
        f'<div style="font-family:var(--sc-mono);font-size:11px;color:#2a3a4a;'
        f'text-align:right;font-variant-numeric:tabular-nums;">{slope_str}</div>'
        '<div style="background:#f3eddb;border:1px solid #ece6d7;'
        'height:10px;overflow:hidden;">'
        f'<div style="background:#155752;height:100%;width:{conf_w:.0f}%;"></div>'
        '</div>'
        '<div style="font-family:var(--sc-mono);font-size:10.5px;color:#6a7480;'
        f'text-align:right;font-variant-numeric:tabular-nums;">'
        f'R² {r2:.2f}</div>' if r2 is not None else
        '<div style="font-family:var(--sc-mono);font-size:10.5px;color:#6a7480;'
        'text-align:right;">—</div>'
        '</div>'
    )


def _trend_rows(rows: List[Dict[str, Any]]) -> str:
    head = (
        '<div style="display:grid;grid-template-columns:1.4fr 0.7fr 1.4fr 1.2fr 0.9fr;'
        'gap:14px;padding:0 0 6px;font-family:var(--sc-mono);font-size:9.5px;'
        'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;">'
        '<div>Metric</div><div style="text-align:center;">Dir</div>'
        '<div style="text-align:right;">Slope</div>'
        '<div>Confidence</div><div style="text-align:right;">R²</div></div>'
    )
    return head + "".join(_trend_row_render(r) for r in rows)


def _detail_table(rows: List[Dict[str, Any]]) -> str:
    out = []
    for r in rows:
        glyph, label, color = DIRECTION_GLYPH.get(r.get("direction", "neutral"),
                                                  DIRECTION_GLYPH["neutral"])
        if r["status"] == "building":
            glyph, label, color = DIRECTION_GLYPH["building"]
        fmt = r.get("fmt", "money")
        current = _format_value(r.get("current"), fmt)
        nxt = _format_value(r.get("next"), fmt)
        out.append(
            '<tr>'
            f'<td><div style="font-family:var(--sc-serif);font-size:14px;'
            f'color:#15202b;">{_html.escape(r["label"])}</div></td>'
            f'<td><span style="font-family:var(--sc-mono);font-size:10.5px;'
            f'letter-spacing:.12em;text-transform:uppercase;color:{color};">'
            f'{glyph} {_html.escape(label)}</span></td>'
            f'<td class="num">{current}</td>'
            f'<td class="num">{nxt}</td>'
            f'<td class="num" style="font-size:11px;color:#6a7480;">'
            f'{("R² " + format(r["r2"], ".2f")) if r.get("r2") is not None else "—"}'
            f'</td>'
            f'<td class="num" style="font-size:11px;color:#6a7480;">'
            f'n={r.get("n", 0)} fy</td>'
            '</tr>'
        )
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        '<thead><tr>'
        '<th>Metric</th><th>Direction</th>'
        '<th class="num">Latest</th><th class="num">Next-year</th>'
        '<th class="num">Fit</th><th class="num">History</th>'
        '</tr></thead>'
        f'<tbody>{"".join(out)}</tbody></table>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'SLOPE = OLS · DIRECTION ARROW REFLECTS WHETHER MOVEMENT IS FAVORABLE, '
        'NOT THE SIGN OF THE SLOPE (e.g. OPERATING EXPENSES UP = NEUTRAL HERE).'
        '</p>'
    )


def _actions_row(ccn: str) -> str:
    ccn_safe = _html.escape(ccn, quote=True)
    targets = [
        (f"/hospital/{ccn_safe}/history",         "Annual financial timeline"),
        (f"/deals/{ccn_safe}/bridge",             "EBITDA bridge"),
        (f"/deals/{ccn_safe}/predicted",          "Predicted vs actual (soon)"),
        (f"/deals/{ccn_safe}/profile",            "Profile"),
    ]
    return "".join(
        f'<a href="{href}" style="display:inline-block;'
        f'padding:8px 14px;border:1px solid #c9c1ac;background:#faf6ec;'
        f'color:#15202b;text-decoration:none;font-family:var(--sc-mono);'
        f'font-size:11px;letter-spacing:.12em;text-transform:uppercase;'
        f'margin:0 8px 8px 0;">{_html.escape(label)}</a>'
        for href, label in targets
    )


def render_deal_trends(ccn: str, hospital: Dict[str, Any]) -> str:
    """Render Surface 16 (Trends) for ``ccn``.

    Uses multi-year HCRIS history (`data.hcris.get_trend`) to compute a
    per-metric annual slope and one-year-ahead forecast. The cadence note
    in the hero makes the annual basis explicit.
    """
    try:
        from ...data.hcris import get_trend
    except ImportError:                                # pragma: no cover
        from rcm_mc.data.hcris import get_trend
    try:
        trend = get_trend(ccn)
    except Exception:                                  # noqa: BLE001
        trend = None

    if trend is None or trend.empty:
        return deal_shell(
            ccn, hospital, active_slug="trends",
            body_html=_empty(
                f"No multi-year HCRIS data on file for CCN {ccn}."),
            page_title=f"Trends · {hospital.get('name') or f'CCN {ccn}'}",
        )

    trend_records: List[Dict[str, Any]] = trend.sort_values("fiscal_year").to_dict("records")
    rows: List[Dict[str, Any]] = [
        _trend_row(key, label, fmt, accessor, higher, trend_records)
        for key, label, fmt, accessor, higher in METRICS
    ]

    panels = [
        _panel("01 · HERO", "How many metrics, moving which way",
               _hero(rows)),
        _panel("02 · TREND DETECTION",
               "Per-metric direction + slope + confidence",
               _trend_rows(rows)),
        _panel("03 · DETAIL TABLE",
               "Latest value, next-year forecast, fit quality",
               _detail_table(rows)),
        _panel("04 · ACTIONS",
               "Where to go next from here",
               _actions_row(ccn)),
    ]
    body = "".join(panels)
    return deal_shell(
        ccn, hospital, active_slug="trends", body_html=body,
        page_title=f"Trends · {hospital.get('name') or f'CCN {ccn}'}",
    )
