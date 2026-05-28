"""Surface 07 · DCF — 5-year explicit projection + Gordon-growth terminal.

Wired to `finance.dcf_model.build_dcf_from_deal`. Inputs come from HCRIS
(net_patient_revenue + operating_expenses → current EBITDA). When net
revenue is missing or non-positive the surface renders an honest empty
state — the DCF is never run on fabricated inputs. Per the spec, this is a
SANITY CHECK alongside the LBO, not the source of truth.

Components shipped (4 of 5 in the spec — read-only assumption panel; the
spec's editable inputs land later):
1. Hero strip          — EV, PV cash flows, PV terminal, terminal value,
                         WACC, terminal growth
2. Cash-flow chart     — Y1-Y5 inline SVG polyline (revenue / EBITDA / FCF)
3. Cash-flow table     — same data, tabular, with PV(FCF) discounting
4. Interpretation      — verdict bullets derived from the real DCFResult +
                         cross-links to LBO / 3-Statement / Bridge
5. Assumptions panel   — read-only display of the DCFResult assumptions
                         (the editable form is a future PR)
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ._shell import _fmt_money, _fmt_pct, deal_shell


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
        'DCF cannot run</span>'
        '<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
        'margin:6px 0 12px;color:#15202b;">'
        'Inputs not available in HCRIS for this hospital</h3>'
        f'<p style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;">{_html.escape(reason)} The DCF needs a '
        'positive net revenue to project. Until HCRIS has it for this CCN, '
        'no enterprise value is shown here rather than fabricated.</p>'
        '</section>'
    )


def _hero(dcf: Any) -> str:
    a = dcf.assumptions
    rows = [
        ("Enterprise value",  _fmt_money(getattr(dcf, "enterprise_value", 0.0))),
        ("PV cash flows",     _fmt_money(getattr(dcf, "pv_cash_flows", 0.0))),
        ("PV terminal",       _fmt_money(getattr(dcf, "pv_terminal", 0.0))),
        ("Terminal value",    _fmt_money(getattr(dcf, "terminal_value", 0.0))),
        ("WACC",              _fmt_pct(getattr(a, "wacc", 0.0))),
        ("Terminal growth",   _fmt_pct(getattr(a, "terminal_growth", 0.0))),
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
        'ENTERPRISE VALUE = PV(EXPLICIT FCF) + PV(GORDON-GROWTH TERMINAL). '
        'A SANITY CHECK ALONGSIDE THE LBO, NOT THE SOURCE OF TRUTH.</p>'
    )


def _cashflow_chart(projections: List[Any]) -> str:
    """Plain SVG polyline — points pinned by year position, not index.

    Three series (revenue / EBITDA / FCF) on a single y-axis, each scaled to
    its own peak so all three are legible despite very different magnitudes.
    Per the spec build-note: "do NOT use a charting lib".
    """
    if not projections:
        return (
            '<p style="font-family:var(--sc-serif);font-style:italic;'
            'color:#6a7480;font-size:13px;margin:0;">No projection years.</p>'
        )
    years = [int(getattr(p, "year", i + 1)) for i, p in enumerate(projections)]
    rev = [float(getattr(p, "revenue", 0.0) or 0.0) for p in projections]
    ebitda = [float(getattr(p, "ebitda", 0.0) or 0.0) for p in projections]
    fcf = [float(getattr(p, "fcf", 0.0) or 0.0) for p in projections]
    # SVG viewport
    W, H, pad_l, pad_r, pad_t, pad_b = 720, 220, 56, 24, 18, 30
    inner_w = W - pad_l - pad_r
    inner_h = H - pad_t - pad_b
    def _series_points(values: List[float]) -> str:
        if not values:
            return ""
        mx = max(values) if max(values) > 0 else 1.0
        mn = min(min(values), 0.0)
        rng = mx - mn or 1.0
        pts: List[str] = []
        n_pts = len(values)
        for i, v in enumerate(values):
            x = pad_l + (i / (n_pts - 1 if n_pts > 1 else 1)) * inner_w
            y = pad_t + inner_h - ((v - mn) / rng) * inner_h
            pts.append(f"{x:.1f},{y:.1f}")
        return " ".join(pts)
    rev_pts = _series_points(rev)
    eb_pts = _series_points(ebitda)
    fcf_pts = _series_points(fcf)
    # X labels per year
    year_marks: List[str] = []
    for i, yr in enumerate(years):
        x = pad_l + (i / (len(years) - 1 if len(years) > 1 else 1)) * inner_w
        year_marks.append(
            f'<text x="{x:.0f}" y="{H - 8}" font-family="monospace" '
            f'font-size="10" fill="#6a7480" text-anchor="middle">Y{yr}</text>'
        )
    svg = (
        f'<svg viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="Y1-Y5 revenue, EBITDA, and FCF" '
        f'style="width:100%;max-width:{W}px;height:auto;display:block;'
        f'background:#faf6ec;border:1px solid #ece6d7;">'
        # axes
        f'<line x1="{pad_l}" y1="{H - pad_b}" x2="{W - pad_r}" y2="{H - pad_b}" '
        f'stroke="#c9c1ac" stroke-width="1"/>'
        f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{H - pad_b}" '
        f'stroke="#c9c1ac" stroke-width="1"/>'
        # series
        f'<polyline points="{rev_pts}" fill="none" stroke="#0b2341" stroke-width="2"/>'
        f'<polyline points="{eb_pts}" fill="none" stroke="#1f7a5a" stroke-width="2"/>'
        f'<polyline points="{fcf_pts}" fill="none" stroke="#b8842e" stroke-width="2"/>'
        # year labels
        + "".join(year_marks)
        + '</svg>'
    )
    legend = (
        '<div style="display:flex;gap:18px;margin:10px 0 0;'
        'font-family:var(--sc-mono);font-size:10.5px;letter-spacing:.1em;'
        'text-transform:uppercase;color:#6a7480;">'
        '<span><span style="display:inline-block;width:10px;height:2px;'
        'background:#0b2341;vertical-align:middle;margin-right:6px;"></span>'
        'Revenue</span>'
        '<span><span style="display:inline-block;width:10px;height:2px;'
        'background:#1f7a5a;vertical-align:middle;margin-right:6px;"></span>'
        'EBITDA</span>'
        '<span><span style="display:inline-block;width:10px;height:2px;'
        'background:#b8842e;vertical-align:middle;margin-right:6px;"></span>'
        'FCF</span></div>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:6px 0 0;">'
        'EACH SERIES SCALED TO ITS OWN PEAK FOR LEGIBILITY — POSITIONS ARE '
        'RELATIVE, NOT COMPARABLE ACROSS SERIES.</p>'
    )
    return svg + legend


def _cashflow_table(projections: List[Any]) -> str:
    if not projections:
        return ""
    rows = "".join(
        '<tr>'
        f'<td>Y{int(getattr(p, "year", 0))}</td>'
        f'<td class="num">{_fmt_money(getattr(p, "revenue", 0.0))}</td>'
        f'<td class="num">{_fmt_money(getattr(p, "ebitda", 0.0))}</td>'
        f'<td class="num">{_fmt_pct(getattr(p, "ebitda_margin", 0.0))}</td>'
        f'<td class="num">{_fmt_money(getattr(p, "fcf", 0.0))}</td>'
        f'<td class="num">{_fmt_money(getattr(p, "pv_fcf", 0.0))}</td>'
        '</tr>'
        for p in projections
    )
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        '<thead><tr>'
        '<th>Year</th>'
        '<th class="num">Revenue</th><th class="num">EBITDA</th>'
        '<th class="num">Margin</th><th class="num">FCF</th>'
        '<th class="num">PV(FCF)</th>'
        '</tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'PV(FCF) = FCF / (1 + WACC)^YEAR · USED FOR THE PV-CASH-FLOWS HERO STAT.</p>'
    )


def _interpretation(dcf: Any, ccn: str) -> str:
    """Bullets from the real DCF output — never a hallucinated thesis."""
    a = dcf.assumptions
    ev = float(getattr(dcf, "enterprise_value", 0.0) or 0.0)
    pv_cf = float(getattr(dcf, "pv_cash_flows", 0.0) or 0.0)
    pv_tv = float(getattr(dcf, "pv_terminal", 0.0) or 0.0)
    bullets: List[str] = []
    if ev > 0:
        share_terminal = (pv_tv / ev * 100.0) if ev > 0 else 0.0
        bullets.append(
            f"Terminal accounts for <strong>{share_terminal:.0f}%</strong> "
            "of EV — a high share means most of the value sits beyond the "
            "explicit horizon and is highly sensitive to terminal growth."
        )
        if share_terminal > 80:
            bullets.append(
                "Terminal share is above 80% — flag for partner review; "
                "the deal hinges on what happens after Year 5."
            )
    if ev < 0:
        bullets.append(
            "Enterprise value is <strong>negative</strong> at these "
            "assumptions. The model shows it without apology — but the "
            "deal can't be supported by this DCF alone."
        )
    wacc = float(getattr(a, "wacc", 0.0) or 0.0)
    tg = float(getattr(a, "terminal_growth", 0.0) or 0.0)
    if wacc - tg < 0.04:
        bullets.append(
            f"WACC ({wacc*100:.1f}%) minus terminal growth ({tg*100:.1f}%) "
            "is below 4 pp — Gordon-growth is acutely sensitive in this "
            "regime; sanity-check the LBO before trusting EV."
        )
    items = "".join(f"<li>{b}</li>" for b in bullets) or \
        '<li>No signals fire at this assumption set.</li>'
    ccn_safe = _html.escape(ccn, quote=True)
    return (
        f'<ul style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;padding-left:18px;">{items}</ul>'
        f'<p style="font-family:var(--sc-serif);font-size:13.5px;line-height:1.6;'
        f'color:#2a3a4a;margin:14px 0 0;">Cross-link: '
        f'<a href="/deals/{ccn_safe}/lbo" style="color:#1f7a5a;">LBO</a> '
        f'(deal economics) · '
        f'<a href="/deals/{ccn_safe}/bridge" style="color:#1f7a5a;">EBITDA Bridge</a> '
        f'(value-creation levers) · '
        f'<a href="/deals/{ccn_safe}/stmt" style="color:#1f7a5a;">3-Statement</a> '
        f'(reconstructed financials, soon).</p>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'EVERY BULLET IS DERIVED FROM REAL DCFRESULT NUMBERS — NOT A PROSE THESIS.</p>'
    )


def _assumptions_panel(a: Any) -> str:
    rows = [
        ("Revenue base",      _fmt_money(getattr(a, "revenue_base", 0.0))),
        ("EBITDA margin base",_fmt_pct(getattr(a, "ebitda_margin_base", 0.0))),
        ("WACC",              _fmt_pct(getattr(a, "wacc", 0.0))),
        ("Terminal growth",   _fmt_pct(getattr(a, "terminal_growth", 0.0))),
        ("Tax rate",          _fmt_pct(getattr(a, "tax_rate", 0.0))),
        ("Capex (% rev)",     _fmt_pct(getattr(a, "capex_pct_revenue", 0.0))),
        ("NWC (% rev)",       _fmt_pct(getattr(a, "nwc_pct_revenue", 0.0))),
        ("Projection years",  str(int(getattr(a, "projection_years", 0) or 0))),
    ]
    cells = "".join(
        '<div style="border:1px solid #ece6d7;padding:10px 12px;'
        'background:#faf6ec;">'
        f'<dt style="font-family:var(--sc-mono);font-size:9.5px;'
        f'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;'
        f'margin:0 0 3px;">{_html.escape(label)}</dt>'
        '<dd style="font-family:var(--sc-serif);font-size:16px;margin:0;'
        'color:#15202b;font-variant-numeric:tabular-nums;">'
        f'{value}</dd></div>'
        for label, value in rows
    )
    return (
        '<dl style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));'
        f'gap:10px;margin:0;">{cells}</dl>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'READ-ONLY VIEW OF THE DCF ENGINE\'S ASSUMPTIONS &mdash; THE EDITABLE FORM '
        'LANDS IN A LATER PR.</p>'
    )


def render_deal_dcf(ccn: str, hospital: Dict[str, Any]) -> str:
    """Render Surface 07 (DCF) for ``ccn``."""
    npr = _safe_float(hospital.get("net_patient_revenue"))
    opex = _safe_float(hospital.get("operating_expenses"))
    if not npr or npr <= 1e5:
        return deal_shell(
            ccn, hospital, active_slug="dcf",
            body_html=_empty(f"HCRIS net patient revenue is missing or "
                             f"non-positive for CCN {ccn}."),
            page_title=f"DCF · {hospital.get('name') or f'CCN {ccn}'}",
        )
    try:
        from ...finance.dcf_model import build_dcf_from_deal
    except ImportError:                                # pragma: no cover
        from rcm_mc.finance.dcf_model import build_dcf_from_deal
    profile: Dict[str, Any] = {"net_revenue": float(npr)}
    if opex is not None and opex > 0:
        profile["current_ebitda"] = float(npr) - float(opex)
    try:
        dcf = build_dcf_from_deal(profile)
    except Exception:                                  # noqa: BLE001
        return deal_shell(
            ccn, hospital, active_slug="dcf",
            body_html=_empty("The DCF engine returned an error for this "
                             "hospital's inputs."),
            page_title=f"DCF · {hospital.get('name') or f'CCN {ccn}'}",
        )
    panels = [
        _panel("01 · HERO", "Enterprise value at base assumptions", _hero(dcf)),
        _panel("02 · CASH-FLOW CHART",
               "Y1-Y5 revenue, EBITDA, and FCF",
               _cashflow_chart(dcf.projections)),
        _panel("03 · CASH-FLOW TABLE",
               "Same data, tabular, with PV(FCF)",
               _cashflow_table(dcf.projections)),
        _panel("04 · INTERPRETATION",
               "What the DCF is telling you",
               _interpretation(dcf, ccn)),
        _panel("05 · ASSUMPTIONS",
               "Read-only view of the engine inputs",
               _assumptions_panel(dcf.assumptions)),
    ]
    body = "".join(panels)
    return deal_shell(
        ccn, hospital, active_slug="dcf", body_html=body,
        page_title=f"DCF · {hospital.get('name') or f'CCN {ccn}'}",
    )
