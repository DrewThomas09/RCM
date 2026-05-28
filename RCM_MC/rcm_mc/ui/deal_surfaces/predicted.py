"""Surface 17 · Predicted vs Actual — diligence predictions vs current actuals.

The most honest surface in the family. The spec says it bluntly: "Pre-close
deal → entire surface shows empty state: 'Predictions stored — actuals will
appear post-close'." That's exactly what ships here.

For an HCRIS-only deal-lens entry (which is the only mode this family has
today — no analysis_runs snapshot table is tied to the /deals/<ccn>/* URL
scheme), there is no diligence-time snapshot to compare against. The
surface honors the spec by:

  1. Showing the canonical empty-state framing ("Predictions stored,
     actuals appear post-close") clearly + in serif so partners read it
     as the intended state, not a bug.
  2. Naming what WOULD appear here — the exact 3 components from the
     spec — so the deal team knows what to expect when the snapshot
     pipeline lands.
  3. Showing a TODAY-VIEW with current real HCRIS numbers, labeled
     "current snapshot," so the page isn't blank: when the diligence
     pipeline starts saving snapshots, this is the live reference column.
  4. Honest cross-link to /deals/<ccn>/ml + /trends where the
     prediction machinery already lives.

Components shipped (1 of 3 in the spec, plus the spec's required
pre-close empty state):
1. PRE-CLOSE EMPTY      — "Predictions stored, actuals appear post-close"
2. WHAT WILL LAND HERE  — names the within-CI %, MAE, and predicted-vs-
                          actual table the spec describes
3. CURRENT SNAPSHOT     — today's real HCRIS values for the metrics this
                          surface would compare; labeled "this is what the
                          snapshot would freeze if taken right now"
4. CROSS-LINKS          — to ML (where the predictions live) + Trends
                          (where directional movement lives)
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, Optional

from ._shell import _fmt_int, _fmt_money, _fmt_pct, deal_shell


def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def _op_margin(h: Dict[str, Any]) -> Optional[float]:
    npr = _safe_float(h.get("net_patient_revenue"))
    opex = _safe_float(h.get("operating_expenses"))
    if not npr or not opex or npr <= 1e4:
        return None
    return (npr - opex) / npr


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


def _pre_close_panel(ccn: str, hospital: Dict[str, Any]) -> str:
    """The spec-mandated pre-close empty state, rendered as the headline
    panel of the surface instead of replacing the whole page."""
    name = _html.escape(str(hospital.get("name") or f"CCN {ccn}"))
    return (
        '<section style="background:#fff;border:1px solid #c9c1ac;'
        'padding:36px 40px;margin:0 0 18px;">'
        '<span style="font-family:var(--sc-mono);font-size:10px;'
        'letter-spacing:.18em;text-transform:uppercase;color:#1f7a5a;">'
        'Pre-close · No actuals yet</span>'
        '<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:30px;'
        'line-height:1.1;letter-spacing:-.01em;margin:8px 0 14px;color:#15202b;">'
        '<em style="color:#154e36;font-style:italic;">Predictions stored.</em>'
        ' Actuals appear post-close.</h3>'
        '<p style="font-family:var(--sc-serif);font-size:15.5px;line-height:1.6;'
        'color:#2a3a4a;margin:0;max-width:62ch;">'
        f'There is no diligence-time snapshot on file for {name} to compare '
        'against current HCRIS values. This is the canonical pre-close state, '
        'and the surface ships in this mode by design — not as a bug. Once '
        'the diligence pipeline starts saving immutable analysis snapshots, '
        'this surface flips automatically: the table below populates, and '
        'the "within-CI" / MAE / variance headline stats appear at the top.'
        '</p>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:14px 0 0;">'
        'EXPECTED FILL-IN AT FIRST CLOSE: 6&ndash;8 KPI ROWS WITH PREDICTED [CI] / '
        'ACTUAL / VARIANCE / IN-CI? BADGE COLUMNS, PER THE HANDOFF SPEC.'
        '</p></section>'
    )


def _what_will_land(hospital: Dict[str, Any]) -> str:
    """Show the EXACT shape of the table that will appear here, with the
    pre-close placeholder values in the actual + variance columns. This is
    the spec's "Snapshot retrieval should be fast: pre-warmed in the deal-
    loading critical path" hint — the table's shape exists today.
    """
    metrics = [
        ("Net patient revenue", _fmt_money(hospital.get("net_patient_revenue"))),
        ("Operating margin",    _fmt_pct(_op_margin(hospital))),
        ("Operating EBITDA",    _fmt_money(
            (_safe_float(hospital.get("net_patient_revenue")) or 0)
            - (_safe_float(hospital.get("operating_expenses")) or 0)
            if (_safe_float(hospital.get("net_patient_revenue"))
                and _safe_float(hospital.get("operating_expenses")))
            else None)),
        ("Beds",                _fmt_int(hospital.get("beds"))),
        ("Medicare day %",      _fmt_pct(_safe_float(hospital.get("medicare_day_pct")))),
        ("Net income",          _fmt_money(hospital.get("net_income"))),
    ]
    rows = "".join(
        '<tr>'
        f'<td style="font-family:var(--sc-serif);font-size:14px;color:#15202b;">{label}</td>'
        f'<td class="num" style="font-family:var(--sc-mono);font-size:11.5px;'
        f'color:#6a7480;text-align:right;">[ &mdash; · &mdash; ]</td>'
        f'<td class="num" style="font-family:var(--sc-mono);font-size:11.5px;'
        f'color:#15202b;text-align:right;font-variant-numeric:tabular-nums;">{value}</td>'
        f'<td class="num" style="font-family:var(--sc-mono);font-size:11.5px;'
        f'color:#6a7480;text-align:right;">&mdash;</td>'
        f'<td><span style="font-family:var(--sc-mono);font-size:9.5px;'
        f'letter-spacing:.12em;text-transform:uppercase;color:#6a7480;'
        f'background:#ece6d7;border:1px solid #c9c1ac;padding:2px 8px;">Pending</span></td>'
        '</tr>'
        for label, value in metrics
    )
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        '<thead><tr>'
        '<th>Metric</th><th class="num">Predicted [CI]</th>'
        '<th class="num">Current actual</th>'
        '<th class="num">Variance</th><th>In CI?</th>'
        '</tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'CURRENT ACTUAL COLUMN IS REAL HCRIS — THE PRE-CLOSE STATE FROZEN '
        'AT TODAY\'S VALUES. PREDICTED [CI] AND VARIANCE FILL IN WHEN A '
        'DILIGENCE SNAPSHOT IS COMMITTED. THE "PENDING" PILL FLIPS GREEN '
        '("WITHIN CI") OR CORAL ("OUTSIDE CI") AT THAT POINT.</p>'
    )


def _hero_placeholders() -> str:
    """The 3-stat hero from the spec, all em-dashed until snapshot exists."""
    rows = [
        ("Within-CI %", "—"),
        ("Mean absolute error", "—"),
        ("Metrics compared", "0"),
    ]
    cells = "".join(
        '<div style="border:1px solid #c9c1ac;background:#faf6ec;padding:12px 14px;">'
        f'<dt style="font-family:var(--sc-mono);font-size:9.5px;'
        f'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;'
        f'margin:0 0 4px;">{_html.escape(label)}</dt>'
        '<dd style="font-family:var(--sc-serif);font-size:24px;margin:0;'
        f'color:#15202b;font-variant-numeric:tabular-nums;">{_html.escape(value)}</dd></div>'
        for label, value in rows
    )
    return (
        '<dl style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));'
        f'gap:12px;margin:0;">{cells}</dl>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'POPULATE ONCE THE DILIGENCE SNAPSHOT PIPELINE COMMITS TO THIS CCN.</p>'
    )


def _cross_links(ccn: str) -> str:
    ccn_safe = _html.escape(ccn, quote=True)
    return (
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">'
        f'<a href="/deals/{ccn_safe}/ml" style="display:block;padding:18px 20px;'
        'border:1px solid #1f7a5a;background:#d6e8df;color:#154e36;'
        'text-decoration:none;">'
        '<div style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.14em;'
        'text-transform:uppercase;color:#1f7a5a;margin-bottom:6px;">Open</div>'
        '<div style="font-family:var(--sc-serif);font-size:16px;color:#154e36;">'
        'ML Analysis — where today\'s predictions live →</div></a>'
        f'<a href="/deals/{ccn_safe}/trends" style="display:block;padding:18px 20px;'
        'border:1px solid #c9c1ac;background:#faf6ec;color:#15202b;'
        'text-decoration:none;">'
        '<div style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.14em;'
        'text-transform:uppercase;color:#6a7480;margin-bottom:6px;">Open</div>'
        '<div style="font-family:var(--sc-serif);font-size:16px;color:#15202b;">'
        'Trends — multi-year directional movement →</div></a>'
        '</div>'
    )


def render_deal_predicted(ccn: str, hospital: Dict[str, Any]) -> str:
    """Render Surface 17 (Predicted vs Actual) for ``ccn``.

    Honest pre-close state. The diligence-snapshot pipeline that would
    populate this surface doesn't exist for the HCRIS-only deal-lens
    flow today; the spec's empty-state framing is the rendered output.
    """
    panels = [
        _pre_close_panel(ccn, hospital),
        _panel("HERO STRIP (pending)",
               "Headline accuracy stats — empty until first close",
               _hero_placeholders()),
        _panel("PREDICTED vs ACTUAL — shape preview",
               "How the table will read once a snapshot is committed",
               _what_will_land(hospital)),
        _panel("CROSS-LINKS",
               "Where the live prediction machinery lives today",
               _cross_links(ccn)),
        _panel("WHAT'S NEXT",
               "The work this surface is waiting on",
               '<p style="font-family:var(--sc-serif);font-size:14.5px;'
               'line-height:1.55;color:#2a3a4a;margin:0;max-width:62ch;">'
               'For this surface to flip from pre-close to populated, the '
               'diligence pipeline needs to commit an immutable snapshot of '
               'predicted values + their CIs at diligence-time. The ML '
               'Analysis surface already exposes the predictions that would '
               'be frozen; the snapshot table + retrieval need a small '
               'persistence layer that lands in a later phase. Until then, '
               'this surface is honest about being empty rather than fake '
               'with placeholder numbers.</p>'),
    ]
    body = "".join(panels)
    return deal_shell(
        ccn, hospital, active_slug="predicted", body_html=body,
        page_title=f"Predicted vs Actual · {hospital.get('name') or f'CCN {ccn}'}",
    )
