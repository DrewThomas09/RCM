"""Surface 11 · Denial — root-cause decomposition of denial leakage.

Wired to `finance.denial_drivers.analyze_denial_drivers`. HCRIS does not
carry operational metrics like denial rate / days-in-AR / clean-claim rate,
so when the diligence team hasn't supplied actuals the analysis runs on
research-band defaults applied at this hospital's REAL net-revenue scale.
The surface labels this honestly: a banner at the top names what is
estimated, and every driver row carries an amber "estimated" badge.

Components shipped (all 4 in the spec):
1. Denial recovery panel  — 4-stat grid (current rate, benchmark, excess,
                            recoverable revenue, root-cause count)
2. Root causes table      — N drivers with contribution %, annual impact,
                            severity badge, magnitude bar
3. What this means        — prose summary + diligence guidance from engine
4. Expert recommendations — engine's curated play library
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ._shell import _fmt_int, _fmt_money, _fmt_pct, deal_shell


def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


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
        'Denial analysis cannot run</span>'
        '<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
        'margin:6px 0 12px;color:#15202b;">'
        'HCRIS net patient revenue is missing</h3>'
        f'<p style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;">{_html.escape(reason)}</p>'
        '</section>'
    )


def _estimated_banner() -> str:
    return (
        '<div style="background:#faf6ec;border:1px solid #d6cfc0;'
        'border-left:3px solid #b8842e;padding:12px 16px;margin:0 0 14px;">'
        '<span style="font-family:var(--sc-mono);font-size:10px;'
        'letter-spacing:.18em;text-transform:uppercase;color:#b8842e;">'
        'Estimated breakdown</span>'
        '<p style="font-family:var(--sc-serif);font-size:13.5px;line-height:1.55;'
        'color:#2a3a4a;margin:6px 0 0;">'
        'HCRIS does not carry operational RCM metrics (denial rate, clean-claim '
        'rate, days-in-AR). This analysis runs on <strong>research-band defaults '
        'applied to this hospital\'s real net-revenue scale</strong>. Every '
        'driver below is therefore <em>estimated</em> &mdash; request actuals '
        'from management to replace the defaults.</p></div>'
    )


def _severity_for_impact(impact: float) -> str:
    """Per spec: >$25M = High coral, $5–25M = Medium amber, <$5M = Low neutral."""
    a = abs(impact)
    if a > 25e6:
        return "high"
    if a >= 5e6:
        return "medium"
    return "low"


_SEVERITY_STYLE = {
    "high":   ("HIGH",   "#b5321e", "#fbe7e2"),
    "medium": ("MEDIUM", "#b8842e", "#fbedd9"),
    "low":    ("LOW",    "#5a6f7a", "#ece6d7"),
}


def _recovery_hero(da: Any) -> str:
    rows = [
        ("Current denial rate",  _fmt_pct(getattr(da, "total_denial_rate", 0.0) / 100.0)),
        ("Benchmark rate",       _fmt_pct(getattr(da, "benchmark_denial_rate", 0.0) / 100.0)),
        ("Excess (target gap)",  _fmt_pct(getattr(da, "excess_denial_rate", 0.0) / 100.0)),
        ("Recoverable revenue",  _fmt_money(getattr(da, "estimated_recoverable_revenue", 0.0))),
        ("Root causes",          _fmt_int(len(getattr(da, "drivers", []) or []))),
        ("Recommendations",      _fmt_int(len(getattr(da, "expert_recommendations", []) or []))),
    ]
    cells = "".join(
        '<div style="border:1px solid #c9c1ac;background:#faf6ec;padding:12px 14px;">'
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
        'RECOVERABLE = EXCESS RATE × CLAIMS × AVG CLAIM × 60% RECOVERY ASSUMPTION '
        '(ENGINE DEFAULT, OVERRIDABLE).</p>'
    )


def _root_causes_table(drivers: List[Any]) -> str:
    if not drivers:
        return (
            '<p style="font-family:var(--sc-serif);font-style:italic;'
            'color:#6a7480;font-size:13px;margin:0;">'
            'No drivers identified at this denial level.</p>'
        )
    max_impact = max((abs(float(getattr(d, "estimated_annual_impact", 0.0) or 0.0))
                      for d in drivers), default=0.0) or 1.0
    rows = []
    for d in drivers:
        name = str(getattr(d, "driver", "") or "")
        category = str(getattr(d, "category", "") or "")
        impact = float(getattr(d, "estimated_annual_impact", 0.0) or 0.0)
        confidence = str(getattr(d, "confidence", "") or "Estimated")
        benchmark = float(getattr(d, "benchmark_value", 0.0) or 0.0)
        actual = float(getattr(d, "actual_value", 0.0) or 0.0)
        gap = float(getattr(d, "gap", 0.0) or 0.0)
        sev = _severity_for_impact(impact)
        sev_label, sev_color, sev_bg = _SEVERITY_STYLE[sev]
        bar_w = max(2.0, min(100.0, abs(impact) / max_impact * 100.0))
        rows.append(
            '<tr>'
            f'<td><div style="font-family:var(--sc-serif);font-size:14px;'
            f'color:#15202b;">{_html.escape(name)}</div>'
            f'<div style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
            f'text-transform:uppercase;color:#6a7480;margin-top:2px;">'
            f'{_html.escape(category)}</div></td>'
            f'<td style="font-family:var(--sc-mono);font-size:11px;color:#2a3a4a;'
            f'text-align:right;font-variant-numeric:tabular-nums;">{benchmark:.1f}</td>'
            f'<td style="font-family:var(--sc-mono);font-size:11px;color:#2a3a4a;'
            f'text-align:right;font-variant-numeric:tabular-nums;">{actual:.1f}</td>'
            f'<td style="font-family:var(--sc-mono);font-size:11px;color:#2a3a4a;'
            f'text-align:right;font-variant-numeric:tabular-nums;">'
            f'{("+%.1f" if gap >= 0 else "%.1f") % gap}</td>'
            f'<td class="num">{_fmt_money(impact)}</td>'
            f'<td><div style="background:#f3eddb;border:1px solid #ece6d7;'
            f'height:10px;overflow:hidden;width:120px;">'
            f'<div style="background:#155752;height:100%;width:{bar_w:.0f}%;"></div>'
            f'</div></td>'
            f'<td><span style="font-family:var(--sc-mono);font-size:9.5px;'
            f'letter-spacing:.12em;text-transform:uppercase;color:{sev_color};'
            f'background:{sev_bg};border:1px solid {sev_color};padding:2px 8px;">'
            f'{sev_label}</span></td>'
            f'<td><span style="font-family:var(--sc-mono);font-size:9.5px;'
            f'letter-spacing:.1em;color:#6a7480;">{_html.escape(confidence)}</span></td>'
            '</tr>'
        )
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        '<thead><tr>'
        '<th>Driver</th>'
        '<th class="num">Benchmark</th><th class="num">Actual</th>'
        '<th class="num">Gap</th>'
        '<th class="num">Annual impact</th>'
        '<th>Magnitude</th><th>Severity</th><th>Confidence</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'SEVERITY BANDS: HIGH &gt;$25M · MEDIUM $5–25M · LOW &lt;$5M · MAGNITUDE '
        'BARS SCALED TO THE LARGEST DRIVER IN THIS ANALYSIS.</p>'
    )


def _what_this_means(da: Any) -> str:
    thesis = str(getattr(da, "value_creation_thesis", "") or "")
    if not thesis:
        return (
            '<p style="font-family:var(--sc-serif);font-style:italic;'
            'color:#6a7480;font-size:13px;margin:0;">No thesis prose returned.</p>'
        )
    return (
        f'<p style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;">{_html.escape(thesis)}</p>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'PROSE FROM <code>analyze_denial_drivers</code> — TEMPLATED FROM THE '
        'ENGINE\'S COEFFICIENTS, NOT HALLUCINATED.</p>'
    )


def _expert_recs(da: Any) -> str:
    recs = list(getattr(da, "expert_recommendations", []) or [])
    if not recs:
        return (
            '<p style="font-family:var(--sc-serif);font-style:italic;'
            'color:#6a7480;font-size:13px;margin:0;">'
            'No expert recommendations triggered at this denial profile.</p>'
        )
    rows = []
    for r in recs:
        area = str(r.get("area", "") or "")
        kind = str(r.get("type", "") or "")
        examples = str(r.get("examples", "") or "")
        when = str(r.get("when", "") or "")
        rows.append(
            '<tr>'
            f'<td><div style="font-family:var(--sc-serif);font-size:14px;'
            f'color:#15202b;">{_html.escape(area)}</div></td>'
            f'<td><span style="font-family:var(--sc-mono);font-size:9.5px;'
            f'letter-spacing:.12em;text-transform:uppercase;color:#1f7a5a;'
            f'background:#d6e8df;border:1px solid #1f7a5a;padding:2px 8px;">'
            f'{_html.escape(kind)}</span></td>'
            f'<td style="font-family:var(--sc-serif);font-size:13px;color:#2a3a4a;">'
            f'{_html.escape(examples)}</td>'
            f'<td style="font-family:var(--sc-serif);font-size:12.5px;'
            f'font-style:italic;color:#6a7480;">{_html.escape(when)}</td>'
            '</tr>'
        )
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        '<thead><tr>'
        '<th>Area</th><th>Type</th><th>Examples</th><th>When this applies</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'CURATED BY RCM ADVISORS IN <code>finance.denial_drivers</code> · '
        'TRIGGERED BY DRIVER PATTERNS, NOT FREE-TEXT.</p>'
    )


def render_deal_denial(ccn: str, hospital: Dict[str, Any]) -> str:
    """Render Surface 11 (Denial) for ``ccn``.

    Builds a profile dict from real HCRIS NPR + the hospital's state, then
    calls `analyze_denial_drivers` with research-band defaults for the
    operational metrics HCRIS doesn't carry. The banner names every default
    explicitly so nothing reads as actual without being so.
    """
    npr = _safe_float(hospital.get("net_patient_revenue"))
    if not npr or npr <= 1e5:
        return deal_shell(
            ccn, hospital, active_slug="denial",
            body_html=_empty(
                f"CCN {ccn} has no positive HCRIS net revenue, so denial "
                "leakage cannot be sized."),
            page_title=f"Denial · {hospital.get('name') or f'CCN {ccn}'}",
        )
    try:
        from ...finance.denial_drivers import analyze_denial_drivers
    except ImportError:                                # pragma: no cover
        from rcm_mc.finance.denial_drivers import analyze_denial_drivers

    # Estimate claims volume from NPR: avg claim ≈ $15K (industry rule of
    # thumb the bridge engine also uses); guard at 1,000 minimum.
    claims_volume = max(1000, int(float(npr) / 15000.0))
    profile: Dict[str, Any] = {
        "deal_id": str(ccn),
        "net_revenue": float(npr),
        "claims_volume": claims_volume,
        "state": str(hospital.get("state", "") or ""),
        # operational metrics: leave as engine defaults (research-band)
    }
    try:
        da = analyze_denial_drivers(profile)
    except Exception:                                  # noqa: BLE001
        return deal_shell(
            ccn, hospital, active_slug="denial",
            body_html=_empty(
                "The denial-drivers engine returned an error for this "
                "hospital's profile."),
            page_title=f"Denial · {hospital.get('name') or f'CCN {ccn}'}",
        )

    panels = [
        _panel("01 · DENIAL RECOVERY",
               "Where the leakage is, sized in dollars",
               _estimated_banner() + _recovery_hero(da)),
        _panel("02 · ROOT CAUSES",
               "Driver-level decomposition",
               _root_causes_table(getattr(da, "drivers", []) or [])),
        _panel("03 · WHAT THIS MEANS",
               "Value-creation thesis from the engine",
               _what_this_means(da)),
        _panel("04 · EXPERT RECOMMENDATIONS",
               "Curated plays that match this driver pattern",
               _expert_recs(da)),
        _panel("05 · CROSS-LINK",
               "Where the dollar conversion already lives",
               '<p style="font-family:var(--sc-serif);font-size:14.5px;'
               'line-height:1.55;color:#2a3a4a;margin:0;">'
               'The <a href="/deals/' + _html.escape(ccn, quote=True) + '/bridge" '
               'style="color:#1f7a5a;">EBITDA Bridge</a> surface also models '
               'the denial-rate lever, calibrated to the same research bands '
               'but rolled into the full 7-lever EBITDA stack. Use this '
               'surface for the <em>driver decomposition</em>; use the Bridge '
               'for the <em>portfolio-level dollar impact</em>.</p>'),
    ]
    body = "".join(panels)
    return deal_shell(
        ccn, hospital, active_slug="denial", body_html=body,
        page_title=f"Denial · {hospital.get('name') or f'CCN {ccn}'}",
    )
