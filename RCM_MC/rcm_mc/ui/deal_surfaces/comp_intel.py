"""Surface 04 · Comp Intel — percentile ranks across operating metrics.

For 12 operating metrics, computes the target's percentile rank against 4
cohorts (national / state / size-matched / state + size-matched). Drives the
"where does this hospital actually sit?" diligence question. Also surfaces
the top size-matched peers (the same engine Profile uses).

All percentile math is from real HCRIS data; nothing is fabricated. When the
target is missing a metric value, the row renders "—" for the target and
greys the bars — never an invented placement.

Components shipped (3 of the 4 in the handoff):
1. Hero strip            — net rev, op margin, beds, national universe count,
                           size-matched peer count
2. Percentile table      — 12 metrics × 4 cohorts, per-cell bar; direction
                           arrow (▲ higher better / ▼ lower better / ▶ neutral)
3. Top size-matched peers — top 8 from `ml.comparable_finder`, sortable

The "value-creation gaps" component (size each below-cohort metric by est.
EBITDA impact) is deferred to Phase 5b — sizing the gap belongs on the
Bridge surface, which already does this from research-band coefficients.
This surface keeps a cross-link to Bridge for the dollar conversion.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional, Tuple

from ._shell import _fmt_int, _fmt_money, _fmt_pct, deal_shell


def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


# ───────────────────────── metric definitions ─────────────────────────
# Each metric: (key, label, direction, formatter, accessor)
# - direction: "higher" / "lower" / "neutral"
# - accessor returns a real value or None; NEVER invents one
def _op_margin(h: Dict[str, Any]) -> Optional[float]:
    npr = _safe_float(h.get("net_patient_revenue"))
    opex = _safe_float(h.get("operating_expenses"))
    if not npr or not opex or npr <= 1e4:
        return None
    return (npr - opex) / npr


def _rev_per_bed(h: Dict[str, Any]) -> Optional[float]:
    npr = _safe_float(h.get("net_patient_revenue"))
    beds = _safe_float(h.get("beds"))
    if not npr or not beds or beds <= 0:
        return None
    return npr / beds


def _occupancy(h: Dict[str, Any]) -> Optional[float]:
    pd = _safe_float(h.get("total_patient_days"))
    bda = _safe_float(h.get("bed_days_available"))
    if not pd or not bda or bda <= 0:
        return None
    return pd / bda


def _contractual_pct(h: Dict[str, Any]) -> Optional[float]:
    ca = _safe_float(h.get("contractual_allowances"))
    gross = _safe_float(h.get("gross_patient_revenue"))
    if not ca or not gross or gross <= 0:
        return None
    return ca / gross


def _just(key: str):
    def _g(h: Dict[str, Any]) -> Optional[float]:
        return _safe_float(h.get(key))
    return _g


METRICS: Tuple[Tuple[str, str, str, str, Any], ...] = (
    # (key, label, direction, format, accessor)
    ("net_patient_revenue",   "Net patient revenue",  "neutral", "money", _just("net_patient_revenue")),
    ("operating_margin",      "Operating margin",     "higher",  "pct",   _op_margin),
    ("net_income",            "Net income",           "higher",  "money", _just("net_income")),
    ("beds",                  "Beds",                 "neutral", "int",   _just("beds")),
    ("revenue_per_bed",       "Revenue per bed",      "higher",  "money", _rev_per_bed),
    ("operating_expenses",    "Operating expenses",   "neutral", "money", _just("operating_expenses")),
    ("total_patient_days",    "Total patient days",   "neutral", "int",   _just("total_patient_days")),
    ("bed_days_available",    "Bed days available",   "neutral", "int",   _just("bed_days_available")),
    ("occupancy_rate",        "Occupancy",            "higher",  "pct",   _occupancy),
    ("medicare_day_pct",      "Medicare day %",       "neutral", "pct01", _just("medicare_day_pct")),
    ("medicaid_day_pct",      "Medicaid day %",       "neutral", "pct01", _just("medicaid_day_pct")),
    ("contractual_pct",       "Contractual allowance %", "lower", "pct",  _contractual_pct),
)


DIRECTION_GLYPH = {
    "higher":  ("▲", "#1f7a5a"),
    "lower":   ("▼", "#b8842e"),
    "neutral": ("▶", "#6a7480"),
}


COHORTS: Tuple[str, ...] = ("National", "State", "Size-matched", "State + size")


def _format_value(val: Optional[float], fmt: str) -> str:
    if val is None:
        return "—"
    if fmt == "money":
        return _fmt_money(val)
    if fmt == "int":
        return _fmt_int(val)
    if fmt == "pct":
        return _fmt_pct(val)
    if fmt == "pct01":
        # HCRIS payer-day percents already in 0..1 or already in 0..100
        v = float(val)
        if v > 1.5:
            v = v / 100.0
        return _fmt_pct(v)
    return "—"


# ───────────────────────── cohort + percentile math ─────────────────────────

def _cohort_filters(target: Dict[str, Any], pool: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    state = (target.get("state") or "").strip().upper()
    beds = _safe_float(target.get("beds"))
    bed_lo = beds * 0.5 if beds else None
    bed_hi = beds * 2.0 if beds else None
    out: Dict[str, List[Dict[str, Any]]] = {
        "National": pool,
        "State": [h for h in pool
                  if str(h.get("state", "")).strip().upper() == state] if state else [],
    }
    if bed_lo is not None and bed_hi is not None:
        out["Size-matched"] = [
            h for h in pool
            if (_safe_float(h.get("beds")) or 0) >= bed_lo
            and (_safe_float(h.get("beds")) or 0) <= bed_hi
        ]
        if state:
            out["State + size"] = [
                h for h in out["Size-matched"]
                if str(h.get("state", "")).strip().upper() == state
            ]
        else:
            out["State + size"] = []
    else:
        out["Size-matched"] = []
        out["State + size"] = []
    return out


def _percentile(target_val: Optional[float], peer_vals: List[float]) -> Optional[float]:
    """Return target's percentile rank in peers (0..1), excluding the target.

    Uses the "share strictly less than" convention, then averages with the
    "share less-or-equal" — standard for percentile ranks when there are ties.
    None when the target has no value or no peers.
    """
    if target_val is None or not peer_vals:
        return None
    n = len(peer_vals)
    below = sum(1 for v in peer_vals if v < target_val)
    at_or_below = sum(1 for v in peer_vals if v <= target_val)
    return (below + at_or_below) / (2.0 * n)


# ───────────────────────── rendering ─────────────────────────

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


def _hero(target: Dict[str, Any], cohorts: Dict[str, List[Dict[str, Any]]]) -> str:
    rows = [
        ("Net revenue",       _fmt_money(target.get("net_patient_revenue"))),
        ("Operating margin",  _fmt_pct(_op_margin(target))),
        ("Beds",              _fmt_int(target.get("beds"))),
        ("National universe", f"{len(cohorts['National']):,} hospitals"),
        ("State peers",       f"{len(cohorts['State']):,}"),
        ("Size-matched",      f"{len(cohorts['Size-matched']):,}"),
    ]
    cells = "".join(
        '<div style="border:1px solid #c9c1ac;background:#faf6ec;'
        'padding:12px 14px;">'
        f'<dt style="font-family:var(--sc-mono);font-size:9.5px;'
        f'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;'
        f'margin:0 0 4px;">{_html.escape(label)}</dt>'
        '<dd style="font-family:var(--sc-serif);font-size:20px;margin:0;'
        'color:#15202b;font-variant-numeric:tabular-nums;">'
        f'{value}</dd></div>'
        for label, value in rows
    )
    return (
        '<dl style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));'
        f'gap:12px;margin:0;">{cells}</dl>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'COHORTS: NATIONAL = ALL HCRIS · STATE = SAME STATE · SIZE-MATCHED '
        '= ½×–2× BEDS · STATE + SIZE = INTERSECTION.</p>'
    )


def _pct_cell(pct: Optional[float], direction: str) -> str:
    """Render one percentile cell as a slim bar + numeric label.

    The bar fills from the left to the target's percentile. Color reflects
    DIRECTION: a high percentile on a "higher better" metric is green; on a
    "lower better" metric it's coral. Neutral metrics stay ink-grey so the
    table doesn't pretend a normative reading where there isn't one.
    """
    if pct is None:
        return ('<div style="font-family:var(--sc-mono);font-size:10.5px;'
                'color:#6a7480;text-align:center;">—</div>')
    pct_label = f"{int(round(pct * 100))}"
    if direction == "higher":
        good = pct >= 0.5
        color = "#1f7a5a" if good else "#b8842e"
    elif direction == "lower":
        good = pct <= 0.5
        color = "#1f7a5a" if good else "#b8842e"
    else:
        color = "#5a6f7a"
    bar_w = max(2.0, min(100.0, pct * 100.0))
    return (
        '<div style="display:flex;align-items:center;gap:6px;">'
        '<div style="flex:1;background:#f3eddb;border:1px solid #ece6d7;'
        'height:8px;overflow:hidden;">'
        f'<div style="background:{color};height:100%;width:{bar_w:.0f}%;"></div>'
        '</div>'
        '<span style="font-family:var(--sc-mono);font-size:10.5px;color:#2a3a4a;'
        f'font-variant-numeric:tabular-nums;min-width:22px;text-align:right;">'
        f'{pct_label}</span></div>'
    )


def _percentile_table(target: Dict[str, Any],
                      cohorts: Dict[str, List[Dict[str, Any]]]) -> str:
    rows: List[str] = []
    for key, label, direction, fmt, accessor in METRICS:
        target_val = accessor(target)
        cells = [
            f'<td><div style="display:flex;align-items:center;gap:6px;">'
            f'<span style="color:{DIRECTION_GLYPH[direction][1]};">'
            f'{DIRECTION_GLYPH[direction][0]}</span>'
            f'<span style="font-family:var(--sc-serif);font-size:14px;">'
            f'{_html.escape(label)}</span></div></td>',
            f'<td class="num" style="font-family:var(--sc-mono);font-size:11px;'
            f'color:#2a3a4a;">{_format_value(target_val, fmt)}</td>',
        ]
        for cohort_name in COHORTS:
            peer_vals: List[float] = []
            for peer in cohorts[cohort_name]:
                if peer.get("ccn") == target.get("ccn"):
                    continue
                v = accessor(peer)
                if v is not None:
                    peer_vals.append(float(v))
            pct = _percentile(target_val, peer_vals)
            cells.append(f'<td style="padding:6px 10px;">{_pct_cell(pct, direction)}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        '<thead><tr>'
        '<th>Metric</th><th class="num">Target</th>'
        + "".join(f'<th>{_html.escape(c)}</th>' for c in COHORTS) +
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'BAR = TARGET&rsquo;S PERCENTILE WITHIN THAT COHORT. GREEN = FAVORABLE '
        '(▲ HIGH OR ▼ LOW), AMBER = UNFAVORABLE, INK = NEUTRAL (NO NORMATIVE '
        'READING).</p>'
    )


def _peers_table(target: Dict[str, Any], pool: List[Dict[str, Any]]) -> str:
    try:
        from ...ml.comparable_finder import find_comparables
    except ImportError:                                # pragma: no cover
        from rcm_mc.ml.comparable_finder import find_comparables
    peers = find_comparables(target, pool, max_results=8) or []
    if not peers:
        return ('<p style="font-family:var(--sc-serif);font-style:italic;'
                'color:#6a7480;font-size:13px;margin:0;">No comparable peers '
                'returned from the matcher.</p>')
    rows = []
    for p in peers:
        peer_ccn = _html.escape(str(p.get("ccn", "")), quote=True)
        peer_name = _html.escape(str(p.get("name", "") or f"CCN {peer_ccn}"))
        state = _html.escape(str(p.get("state", "") or "—"))
        beds = _fmt_int(p.get("beds"))
        npr = _fmt_money(p.get("net_patient_revenue"))
        margin = _fmt_pct(_op_margin(p))
        sim = p.get("similarity_score")
        sim_str = f"{float(sim):.2f}" if sim is not None else "—"
        rows.append(
            '<tr>'
            f'<td><a href="/deals/{peer_ccn}/profile" '
            f'style="color:#1f7a5a;text-decoration:none;">{peer_name}</a></td>'
            f'<td>{state}</td><td class="num">{beds}</td>'
            f'<td class="num">{npr}</td><td class="num">{margin}</td>'
            f'<td class="num">{sim_str}</td></tr>'
        )
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        '<thead><tr>'
        '<th>Hospital</th><th>State</th>'
        '<th class="num">Beds</th><th class="num">NPR</th>'
        '<th class="num">Op margin</th><th class="num">Similarity</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'TOP 8 FROM <code>ml.comparable_finder</code> · CLICK A PEER FOR THAT '
        'HOSPITAL&rsquo;S DEAL.</p>'
    )


def render_deal_comp_intel(ccn: str, hospital: Dict[str, Any]) -> str:
    """Render Surface 04 (Comp Intel) for ``ccn``.

    Loads the full HCRIS pool once, partitions into 4 cohorts, computes
    percentiles for the target on each cohort across the 12 metrics, and
    renders the size-matched peer list. When HCRIS has no data at all (the
    fetch returned nothing) the surface renders an honest empty state.
    """
    try:
        from ...data.hcris import _get_latest_per_ccn
    except ImportError:                                # pragma: no cover
        from rcm_mc.data.hcris import _get_latest_per_ccn
    try:
        hdf = _get_latest_per_ccn()
        pool = hdf.to_dict("records") if hdf is not None else []
    except Exception:                                  # noqa: BLE001
        pool = []
    if not pool:
        body = (
            '<section style="background:#faf6ec;border:1px solid #c9c1ac;'
            'padding:24px 26px;">'
            '<span style="font-family:var(--sc-mono);font-size:10px;'
            'letter-spacing:.18em;text-transform:uppercase;color:#b8842e;">'
            'Comp Intel cannot run</span>'
            '<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
            'margin:6px 0 12px;color:#15202b;">HCRIS pool is empty</h3>'
            '<p style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
            'color:#2a3a4a;margin:0;">Percentile ranking and comparable peers '
            'both need the broader HCRIS dataset, which is not loaded in this '
            'environment. No fabricated cohort is shown.</p>'
            '</section>'
        )
        return deal_shell(ccn, hospital, active_slug="comp-intel", body_html=body)

    cohorts = _cohort_filters(hospital, pool)
    panels = [
        _panel("01 · HERO", "Cohort counts at a glance", _hero(hospital, cohorts)),
        _panel("02 · PERCENTILE RANKING",
               "12 metrics × 4 cohorts",
               _percentile_table(hospital, cohorts)),
        _panel("03 · TOP SIZE-MATCHED PEERS",
               "Closest matches from the comparable finder",
               _peers_table(hospital, pool)),
        _panel("04 · WHAT'S NEXT", "Coming in Phase 5b",
               '<p style="font-family:var(--sc-serif);font-size:14.5px;'
               'line-height:1.55;color:#2a3a4a;margin:0;">'
               'Sizing each below-cohort metric in dollars (the spec\'s '
               '"Value-creation gaps" component) belongs on the '
               f'<a href="/deals/{_html.escape(ccn, quote=True)}/bridge" '
               'style="color:#1f7a5a;">EBITDA Bridge</a> surface — it already '
               'translates lever gaps into dollar impact via the calibrated '
               'research-band coefficients. Comp Intel keeps the ranks honest '
               'and points there for the dollar conversion.</p>'),
    ]
    body = "".join(panels)
    return deal_shell(
        ccn, hospital, active_slug="comp-intel", body_html=body,
        page_title=f"Comp Intel · {hospital.get('name') or f'CCN {ccn}'}",
    )
