"""Surface 12 · Returns — PE returns assessment + covenant headroom.

Wired to `finance.lbo_model.build_lbo_from_deal` — the same engine the LBO
surface uses. The Returns lens focuses on TWO things the LBO surface
doesn't: a partner-friendly prose verdict on the equity returns, and the
year-by-year debt-covenant headroom under the model's assumed leverage.

Components shipped (all 4 in the spec):
1. Hero strip            — IRR, MOIC, entry equity, exit proceeds, total
                           distributed, hold period
2. Returns assessment    — verdict ("Below hurdle / Marginal / Clears hurdle
                           with room") derived from IRR; bullets are real,
                           never hallucinated
3. Covenant headroom     — 6-stat grid (entry leverage, peak leverage,
                           exit leverage, min interest coverage,
                           covenant cushion, breach year if any) + a
                           year-by-year leverage bar with covenant marker
4. Actions row           — cross-links to LBO / Bridge / DCF / Waterfall
                           (Waterfall is still a stub today)
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional, Tuple

from ._shell import _fmt_int, _fmt_money, _fmt_pct, deal_shell


# Industry-default covenant assumptions. Both are loose enough not to fire
# false alarms on standard middle-market healthcare LBOs but tight enough
# to flag real over-levered deals. They're labeled defaults in the UI so
# nobody reads them as actuals from the deal docs.
_DEFAULT_MAX_LEVERAGE = 6.5         # turns of net debt / EBITDA
_DEFAULT_MIN_INT_COVERAGE = 1.75    # EBITDA / interest expense


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
        'Returns lens cannot run</span>'
        '<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
        'margin:6px 0 12px;color:#15202b;">'
        'Inputs not available in HCRIS</h3>'
        f'<p style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;">{_html.escape(reason)} The returns lens '
        'inherits the LBO engine; both need a positive net revenue and '
        'EBITDA (NPR &minus; opex) for this hospital.</p>'
        '</section>'
    )


def _hero(returns_obj: Any, ass_obj: Any, projections: List[Any]) -> str:
    irr = float(getattr(returns_obj, "irr", 0.0) or 0.0)
    moic = float(getattr(returns_obj, "moic", 0.0) or 0.0)
    equity = float(getattr(returns_obj, "equity_invested", 0.0) or 0.0)
    equity_exit = float(getattr(returns_obj, "equity_at_exit", 0.0) or 0.0)
    total_dist = float(getattr(returns_obj, "equity_at_exit", 0.0) or 0.0)
    # Total distributed = equity at exit; LBO model treats hold as no
    # interim distributions (mandatory + sweep go to debt paydown).
    hold = int(getattr(ass_obj, "hold_years", len(projections)) or len(projections))
    rows = [
        ("IRR",                f"{irr*100:.1f}%"),
        ("MOIC",               f"{moic:.2f}x"),
        ("Entry equity",       _fmt_money(equity)),
        ("Exit equity",        _fmt_money(equity_exit)),
        ("Total distributed",  _fmt_money(total_dist)),
        ("Hold",               f"{hold} years"),
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
        'TOTAL DISTRIBUTED EQUALS EQUITY AT EXIT &mdash; THE LBO ENGINE '
        'TREATS THE HOLD AS NO INTERIM DISTRIBUTIONS (FCF GOES TO DEBT '
        'PAYDOWN).</p>'
    )


def _returns_assessment(returns_obj: Any, ass_obj: Any) -> str:
    irr = float(getattr(returns_obj, "irr", 0.0) or 0.0)
    moic = float(getattr(returns_obj, "moic", 0.0) or 0.0)
    growth = float(getattr(returns_obj, "value_from_growth", 0.0) or 0.0)
    multiple = float(getattr(returns_obj, "value_from_multiple", 0.0) or 0.0)
    deleveraging = float(getattr(returns_obj, "value_from_deleveraging", 0.0) or 0.0)
    # Verdict band derived from IRR — the prose is the band's, never invented.
    if irr >= 0.25:
        verdict, color = "Clears hurdle with room", "#1f7a5a"
        verdict_detail = (f"IRR of {irr*100:.1f}% clears a typical 20% fund "
                          "hurdle comfortably.")
    elif irr >= 0.20:
        verdict, color = "Clears hurdle", "#1f7a5a"
        verdict_detail = (f"IRR of {irr*100:.1f}% clears a typical 20% fund "
                          "hurdle but with little cushion; sensitive to exit "
                          "multiple compression.")
    elif irr >= 0.15:
        verdict, color = "Marginal — in the 15–20% range", "#b8842e"
        verdict_detail = (f"IRR of {irr*100:.1f}% sits below the typical 20% "
                          "fund hurdle; the deal needs an upside lever to "
                          "clear at a partner-acceptable IRR.")
    elif irr > 0:
        verdict, color = "Below hurdle", "#b8842e"
        verdict_detail = (f"IRR of {irr*100:.1f}% is well below typical fund "
                          "hurdles; the model says this deal does not work "
                          "at the entry/leverage assumed.")
    else:
        verdict, color = "Impaired", "#b5321e"
        verdict_detail = (f"IRR of {irr*100:.1f}% is non-positive — equity is "
                          "impaired in the model at this assumption set.")
    bullets: List[str] = [verdict_detail]
    total_v = abs(growth) + abs(multiple) + abs(deleveraging)
    if total_v > 0:
        named, val = max(
            (("Growth (EBITDA build)", growth),
             ("Multiple expansion", multiple),
             ("Deleveraging", deleveraging)),
            key=lambda x: abs(x[1]),
        )
        bullets.append(
            f"<strong>{named}</strong> contributes "
            f"<strong>{abs(val)/total_v*100:.0f}%</strong> of the value "
            "created — the dominant driver of this return."
        )
    if multiple < 0:
        bullets.append(
            f"Exit multiple ({float(getattr(ass_obj, 'exit_multiple', 0) or 0):.1f}x) "
            "is below entry — value from multiple is negative; growth and "
            "deleveraging carry the deal."
        )
    items = "".join(f"<li>{b}</li>" for b in bullets)
    return (
        '<div style="display:grid;grid-template-columns:0.4fr 1fr;gap:24px;'
        'align-items:center;margin:0 0 14px;">'
        '<div style="text-align:center;">'
        f'<div style="font-family:var(--sc-serif);font-size:32px;font-weight:400;'
        f'line-height:1;color:{color};">{moic:.2f}x</div>'
        '<div style="font-family:var(--sc-mono);font-size:10.5px;letter-spacing:.18em;'
        'text-transform:uppercase;color:#6a7480;margin-top:6px;">MOIC</div>'
        f'<div style="font-family:var(--sc-serif);font-size:14px;margin-top:8px;'
        f'color:{color};font-style:italic;">{_html.escape(verdict)}</div>'
        '</div>'
        f'<ul style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;padding-left:18px;">{items}</ul></div>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:0;">'
        'EVERY BULLET DERIVED FROM REAL LBORESULT NUMBERS &mdash; NOT A PROSE THESIS.</p>'
    )


def _leverage_bar_row(year: int, leverage: float, max_cov: float) -> str:
    """One leverage-bar row: bar full-width = 1.5× the covenant; the bar
    shows actual leverage, with a coral marker pinned at the covenant.
    """
    track_max = max_cov * 1.5
    bar_w = max(2.0, min(100.0, leverage / track_max * 100.0))
    cov_x = max_cov / track_max * 100.0
    over = leverage > max_cov
    bar_color = "#b5321e" if over else "#155752"
    return (
        '<div style="display:grid;grid-template-columns:56px 1fr 110px;'
        'gap:12px;align-items:center;padding:6px 0;border-bottom:1px solid #ece6d7;">'
        f'<div style="font-family:var(--sc-mono);font-size:11px;color:#2a3a4a;">'
        f'Y{year}</div>'
        '<div style="position:relative;background:#f3eddb;border:1px solid #ece6d7;'
        'height:12px;overflow:visible;">'
        f'<div style="background:{bar_color};height:100%;width:{bar_w:.1f}%;"></div>'
        f'<div style="position:absolute;left:{cov_x:.1f}%;top:-4px;bottom:-4px;'
        'width:0;border-left:2px dashed #b5321e;"></div>'
        '</div>'
        '<div style="font-family:var(--sc-mono);font-size:11px;color:#2a3a4a;'
        f'text-align:right;font-variant-numeric:tabular-nums;">{leverage:.2f}x'
        f'{" (breach)" if over else ""}</div></div>'
    )


def _covenant_panel(projections: List[Any]) -> str:
    if not projections:
        return ('<p style="font-family:var(--sc-serif);font-style:italic;'
                'color:#6a7480;font-size:13px;margin:0;">'
                'No LBO projections to evaluate.</p>')
    max_cov = _DEFAULT_MAX_LEVERAGE
    min_int = _DEFAULT_MIN_INT_COVERAGE
    leverages = [(int(getattr(p, "year", i + 1)),
                  float(getattr(p, "leverage_turns", 0.0) or 0.0))
                 for i, p in enumerate(projections)]
    int_coverages = []
    for p in projections:
        ebitda = float(getattr(p, "ebitda", 0.0) or 0.0)
        interest = float(getattr(p, "interest_senior", 0.0) or 0.0) + \
                   float(getattr(p, "interest_sub", 0.0) or 0.0)
        cov = ebitda / interest if interest > 1.0 else float("inf")
        int_coverages.append(cov)
    entry_lev = leverages[0][1]
    peak_lev = max(l for _, l in leverages)
    peak_yr = max(leverages, key=lambda x: x[1])[0]
    exit_lev = leverages[-1][1]
    min_ic = min(c for c in int_coverages if c != float("inf"))
    breach_year: Optional[int] = None
    for yr, lev in leverages:
        if lev > max_cov:
            breach_year = yr
            break
    cushion = (max_cov - peak_lev) / max_cov * 100.0
    rows = [
        ("Entry leverage", f"{entry_lev:.2f}x"),
        ("Peak leverage", f"{peak_lev:.2f}x · Y{peak_yr}"),
        ("Exit leverage", f"{exit_lev:.2f}x"),
        ("Min interest coverage", f"{min_ic:.2f}x"),
        ("Cushion at peak", f"{cushion:+.1f}%"),
        ("Breach year", f"Y{breach_year}" if breach_year else "None"),
    ]
    cells = "".join(
        '<div style="border:1px solid #c9c1ac;background:#faf6ec;padding:10px 12px;">'
        f'<dt style="font-family:var(--sc-mono);font-size:9.5px;'
        f'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;'
        f'margin:0 0 4px;">{_html.escape(label)}</dt>'
        '<dd style="font-family:var(--sc-serif);font-size:18px;margin:0;'
        'color:#15202b;font-variant-numeric:tabular-nums;">'
        f'{_html.escape(value)}</dd></div>'
        for label, value in rows
    )
    bars = "".join(_leverage_bar_row(yr, lev, max_cov) for yr, lev in leverages)
    legend = (
        '<div style="display:flex;gap:18px;margin:10px 0 0;'
        'font-family:var(--sc-mono);font-size:10.5px;letter-spacing:.1em;'
        'text-transform:uppercase;color:#6a7480;">'
        '<span><span style="display:inline-block;width:10px;height:6px;'
        'background:#155752;vertical-align:middle;margin-right:6px;"></span>'
        f'Actual leverage</span>'
        '<span><span style="display:inline-block;width:10px;height:2px;'
        'border-top:2px dashed #b5321e;vertical-align:middle;margin-right:6px;"></span>'
        f'Max-leverage covenant ({max_cov:.1f}x · default)</span>'
        '<span><span style="display:inline-block;width:10px;height:6px;'
        'background:#b5321e;vertical-align:middle;margin-right:6px;"></span>'
        f'Breach</span></div>'
    )
    return (
        '<dl style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));'
        f'gap:10px;margin:0 0 12px;">{cells}</dl>'
        + bars + legend +
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        f'COVENANTS ARE INDUSTRY-DEFAULT: MAX LEVERAGE {max_cov:.1f}x, MIN INTEREST '
        f'COVERAGE {min_int:.2f}x. THE DEAL TEAM SHOULD OVERRIDE THESE WITH '
        'THE ACTUAL CREDIT-AGREEMENT TERMS WHEN AVAILABLE.</p>'
    )


def _actions_row(ccn: str) -> str:
    ccn_safe = _html.escape(ccn, quote=True)
    targets = [
        ("lbo",      "Full LBO model"),
        ("bridge",   "EBITDA bridge"),
        ("dcf",      "DCF cross-check"),
        ("waterfall","Distribution waterfall (soon)"),
    ]
    buttons = "".join(
        f'<a href="/deals/{ccn_safe}/{slug}" style="display:inline-block;'
        f'padding:8px 14px;border:1px solid #c9c1ac;background:#faf6ec;'
        f'color:#15202b;text-decoration:none;font-family:var(--sc-mono);'
        f'font-size:11px;letter-spacing:.12em;text-transform:uppercase;'
        f'margin:0 8px 8px 0;">{_html.escape(label)}</a>'
        for slug, label in targets
    )
    return buttons


def render_deal_returns(ccn: str, hospital: Dict[str, Any]) -> str:
    """Render Surface 12 (Returns) for ``ccn``.

    Inherits the LBO engine output; focuses on returns assessment and
    covenant headroom — the two reads the LBO surface deliberately defers.
    """
    npr = _safe_float(hospital.get("net_patient_revenue"))
    opex = _safe_float(hospital.get("operating_expenses"))
    if not npr or npr <= 1e5:
        return deal_shell(
            ccn, hospital, active_slug="returns",
            body_html=_empty(f"CCN {ccn} has no positive HCRIS net revenue."),
            page_title=f"Returns · {hospital.get('name') or f'CCN {ccn}'}",
        )
    try:
        from ...finance.lbo_model import build_lbo_from_deal
    except ImportError:                                # pragma: no cover
        from rcm_mc.finance.lbo_model import build_lbo_from_deal
    profile: Dict[str, Any] = {"net_revenue": float(npr)}
    if opex is not None and opex > 0:
        profile["current_ebitda"] = float(npr) - float(opex)
    try:
        lbo = build_lbo_from_deal(profile)
    except Exception:                                  # noqa: BLE001
        return deal_shell(
            ccn, hospital, active_slug="returns",
            body_html=_empty("The LBO engine returned an error."),
            page_title=f"Returns · {hospital.get('name') or f'CCN {ccn}'}",
        )

    panels = [
        _panel("01 · HERO", "Equity returns at a glance",
               _hero(lbo.returns, lbo.assumptions, lbo.projections)),
        _panel("02 · RETURNS ASSESSMENT",
               "Verdict + the drivers behind it",
               _returns_assessment(lbo.returns, lbo.assumptions)),
        _panel("03 · COVENANT HEADROOM",
               "Year-by-year leverage vs default covenants",
               _covenant_panel(lbo.projections)),
        _panel("04 · ACTIONS",
               "Open this deal in another lens",
               _actions_row(ccn)),
    ]
    body = "".join(panels)
    return deal_shell(
        ccn, hospital, active_slug="returns", body_html=body,
        page_title=f"Returns · {hospital.get('name') or f'CCN {ccn}'}",
    )
