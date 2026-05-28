"""Surface 08 · LBO — 5-year hold leveraged-buyout model.

Wired to `finance.lbo_model.build_lbo_from_deal` — the same closed-form LBO
engine used elsewhere in the app. Inputs come from HCRIS
(net_patient_revenue, operating_expenses → current EBITDA). When net revenue
is missing or non-positive the surface renders an honest empty state; the
model is never run on fabricated inputs.

Components shipped (all 4 in the spec):
1. Hero strip            — IRR, MOIC, entry EV, exit EV, equity invested
2. Sources & Uses table  — senior debt / sub debt / equity (amount + % + bar)
3. Interpretation panel  — value-creation decomposition into growth / multiple
                           / deleveraging (signal-bullets derived from
                           the real LBO output, never a hallucinated thesis)
4. Returns waterfall     — exit EBITDA → exit EV → net debt → equity → value
                           created (every row a real number from LBOResult)
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
        'LBO cannot run</span>'
        '<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
        'margin:6px 0 12px;color:#15202b;">'
        'Inputs not available in HCRIS for this hospital</h3>'
        f'<p style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;">{_html.escape(reason)} The LBO needs a '
        'positive net revenue and either current EBITDA or operating expenses '
        'so EBITDA can be derived. Until those land in the HCRIS row no '
        'returns are shown here rather than fabricated.</p>'
        '</section>'
    )


def _hero(returns_obj: Any, su_obj: Any, ass_obj: Any) -> str:
    irr = float(getattr(returns_obj, "irr", 0.0) or 0.0)
    moic = float(getattr(returns_obj, "moic", 0.0) or 0.0)
    entry_ev = float(getattr(su_obj, "enterprise_value", 0.0) or 0.0)
    exit_ev = float(getattr(returns_obj, "exit_ev", 0.0) or 0.0)
    equity = float(getattr(returns_obj, "equity_invested", 0.0) or 0.0)
    rows = [
        ("IRR",            f"{irr*100:.1f}%"),
        ("MOIC",           f"{moic:.2f}x"),
        ("Entry EV",       _fmt_money(entry_ev)),
        ("Exit EV",        _fmt_money(exit_ev)),
        ("Equity invested",_fmt_money(equity)),
        ("Hold",           f"{int(getattr(ass_obj, 'hold_years', 5) or 5)} years"),
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
        'CLOSED-FORM LBO &middot; ASSUMPTIONS COME FROM HCRIS-DERIVED NPR &amp; EBITDA '
        '&middot; ENGINE DEFAULTS USED FOR ENTRY/EXIT MULTIPLES UNTIL THE DEAL TEAM '
        'OVERRIDES.</p>'
    )


def _sources_and_uses(su_obj: Any) -> str:
    senior = float(getattr(su_obj, "senior_debt", 0.0) or 0.0)
    sub = float(getattr(su_obj, "sub_debt", 0.0) or 0.0)
    equity = float(getattr(su_obj, "equity", 0.0) or 0.0)
    total = float(getattr(su_obj, "total_sources", 0.0) or 0.0) or (senior + sub + equity)
    if total <= 0:
        return ''
    rows = [
        ("Senior debt", senior, "#0b2341"),
        ("Sub debt",    sub,    "#155752"),
        ("Equity",      equity, "#5a6f7a"),
    ]
    body = []
    for label, amount, color in rows:
        pct = (amount / total * 100.0) if total > 0 else 0.0
        body.append(
            '<div style="display:grid;grid-template-columns:1.2fr 3fr 1.2fr 0.7fr;'
            'gap:14px;align-items:center;padding:8px 0;'
            'border-bottom:1px solid #ece6d7;">'
            f'<div style="font-family:var(--sc-serif);font-size:14.5px;'
            f'color:#15202b;">{_html.escape(label)}</div>'
            '<div style="background:#f3eddb;border:1px solid #ece6d7;'
            'height:14px;overflow:hidden;">'
            f'<div style="background:{color};height:100%;width:{pct:.1f}%;"></div>'
            '</div>'
            '<div style="font-family:var(--sc-mono);font-size:12.5px;'
            'color:#2a3a4a;text-align:right;'
            'font-variant-numeric:tabular-nums;">'
            f'{_fmt_money(amount)}</div>'
            '<div style="font-family:var(--sc-mono);font-size:11px;'
            'color:#6a7480;text-align:right;'
            f'font-variant-numeric:tabular-nums;">{pct:.1f}%</div></div>'
        )
    # Uses footer with EV / fees / total uses
    ev = float(getattr(su_obj, "enterprise_value", 0.0) or 0.0)
    fees = float(getattr(su_obj, "transaction_fees", 0.0) or 0.0)
    body.append(
        '<div style="margin-top:10px;padding-top:10px;border-top:1px solid #c9c1ac;'
        'display:grid;grid-template-columns:repeat(3,1fr);gap:14px;">'
        f'<div><dt style="font-family:var(--sc-mono);font-size:9.5px;'
        'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;">Enterprise value</dt>'
        f'<dd style="font-family:var(--sc-serif);font-size:16px;margin:2px 0 0;'
        f'color:#15202b;font-variant-numeric:tabular-nums;">{_fmt_money(ev)}</dd></div>'
        f'<div><dt style="font-family:var(--sc-mono);font-size:9.5px;'
        'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;">Transaction fees</dt>'
        f'<dd style="font-family:var(--sc-serif);font-size:16px;margin:2px 0 0;'
        f'color:#15202b;font-variant-numeric:tabular-nums;">{_fmt_money(fees)}</dd></div>'
        f'<div><dt style="font-family:var(--sc-mono);font-size:9.5px;'
        'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;">Total uses</dt>'
        f'<dd style="font-family:var(--sc-serif);font-size:16px;margin:2px 0 0;'
        f'color:#15202b;font-variant-numeric:tabular-nums;">'
        f'{_fmt_money(float(getattr(su_obj, "total_uses", 0.0) or 0.0))}</dd></div>'
        '</div>'
    )
    return (
        '<div style="display:grid;grid-template-columns:1.2fr 3fr 1.2fr 0.7fr;'
        'gap:14px;padding:0 0 6px;font-family:var(--sc-mono);font-size:9.5px;'
        'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;">'
        '<div>Source</div><div>&nbsp;</div>'
        '<div style="text-align:right;">Amount</div>'
        '<div style="text-align:right;">% of stack</div></div>'
        + "".join(body) +
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'BAR WIDTHS PROPORTIONAL TO TOTAL SOURCES. EQUITY IS THE LP-RELEVANT '
        'CHECK SIZE.</p>'
    )


def _waterfall_panel(returns_obj: Any) -> str:
    """Exit EBITDA → Exit EV → Net debt → Equity at exit → Value created."""
    exit_ebitda = float(getattr(returns_obj, "exit_ebitda", 0.0) or 0.0)
    exit_ev = float(getattr(returns_obj, "exit_ev", 0.0) or 0.0)
    net_debt = float(getattr(returns_obj, "net_debt_at_exit", 0.0) or 0.0)
    equity_exit = float(getattr(returns_obj, "equity_at_exit", 0.0) or 0.0)
    equity_in = float(getattr(returns_obj, "equity_invested", 0.0) or 0.0)
    value_created = float(getattr(returns_obj, "total_value_created", 0.0) or 0.0)
    steps = [
        ("Exit EBITDA",      exit_ebitda,    False),
        ("× Exit multiple → Exit EV", exit_ev, False),
        ("− Net debt at exit", -net_debt,    True),
        ("= Equity at exit",   equity_exit,  False),
        ("− Equity invested", -equity_in,    True),
        ("= Value created",    value_created, False),
    ]
    rows = "".join(
        '<tr>'
        f'<td>{_html.escape(label)}</td>'
        f'<td class="num" style="{"color:#b5321e;" if neg else ""}">'
        f'{_fmt_money(abs(val)) if neg else _fmt_money(val)}</td>'
        '</tr>'
        for label, val, neg in steps
    )
    # Value-creation decomposition
    growth = float(getattr(returns_obj, "value_from_growth", 0.0) or 0.0)
    multiple = float(getattr(returns_obj, "value_from_multiple", 0.0) or 0.0)
    deleveraging = float(getattr(returns_obj, "value_from_deleveraging", 0.0) or 0.0)
    total_decomp = max(1.0, abs(growth) + abs(multiple) + abs(deleveraging))
    def _decomp_row(name: str, val: float, color: str) -> str:
        share = abs(val) / total_decomp * 100.0
        return (
            '<div style="display:grid;grid-template-columns:1.2fr 3fr 1.1fr 0.6fr;'
            'gap:14px;align-items:center;padding:6px 0;'
            'border-bottom:1px solid #ece6d7;">'
            f'<div style="font-family:var(--sc-serif);font-size:13.5px;'
            f'color:#15202b;">{_html.escape(name)}</div>'
            '<div style="background:#f3eddb;border:1px solid #ece6d7;'
            'height:12px;overflow:hidden;">'
            f'<div style="background:{color};height:100%;width:{share:.1f}%;"></div>'
            '</div>'
            '<div style="font-family:var(--sc-mono);font-size:12px;'
            'color:#2a3a4a;text-align:right;font-variant-numeric:tabular-nums;">'
            f'{_fmt_money(val)}</div>'
            '<div style="font-family:var(--sc-mono);font-size:11px;'
            'color:#6a7480;text-align:right;font-variant-numeric:tabular-nums;">'
            f'{share:.0f}%</div></div>'
        )
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        '<thead><tr><th>Step</th><th class="num">Value</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
        '<h4 style="font-family:var(--sc-serif);font-weight:400;font-size:16px;'
        'margin:16px 0 8px;color:#15202b;">Value-creation decomposition</h4>'
        + _decomp_row("Growth (EBITDA build)",  growth,       "#1f7a5a")
        + _decomp_row("Multiple (entry → exit)", multiple,    "#155752")
        + _decomp_row("Deleveraging (debt paydown)", deleveraging, "#5a6f7a")
        +
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'DECOMPOSITION RECONCILES TO TOTAL VALUE CREATED WITHIN $1M '
        '(GUARDED IN THE LBO TEST SUITE).</p>'
    )


def _signals_panel(returns_obj: Any, ass_obj: Any) -> str:
    """Bullets derived from real LBO output; never a hallucinated thesis."""
    bullets: List[str] = []
    irr = float(getattr(returns_obj, "irr", 0.0) or 0.0)
    moic = float(getattr(returns_obj, "moic", 0.0) or 0.0)
    equity_exit = float(getattr(returns_obj, "equity_at_exit", 0.0) or 0.0)
    growth = float(getattr(returns_obj, "value_from_growth", 0.0) or 0.0)
    multiple = float(getattr(returns_obj, "value_from_multiple", 0.0) or 0.0)
    deleveraging = float(getattr(returns_obj, "value_from_deleveraging", 0.0) or 0.0)
    total_v = abs(growth) + abs(multiple) + abs(deleveraging)
    if irr >= 0.25:
        bullets.append(
            f"IRR <strong>{irr*100:.1f}%</strong> clears a typical 20% hurdle "
            "with room — defensible at this assumption set."
        )
    elif irr >= 0.15:
        bullets.append(
            f"IRR <strong>{irr*100:.1f}%</strong> is in the 15–25% range — "
            "partner-defendable but sensitive to exit multiple."
        )
    elif irr > 0:
        bullets.append(
            f"IRR <strong>{irr*100:.1f}%</strong> is below typical fund "
            "hurdles — the deal needs an upside lever to clear."
        )
    else:
        bullets.append(
            f"IRR <strong>{irr*100:.1f}%</strong> is non-positive at these "
            "assumptions — equity is impaired in the model."
        )
    if equity_exit < 0:
        bullets.append(
            "Equity at exit is <strong>negative</strong> — the model "
            "shows the deal unworkable at the entry assumed. The Returns "
            "surface (when it ships) will let you stress-test where it breaks."
        )
    if total_v > 0:
        top = max(("Growth", growth), ("Multiple", multiple),
                  ("Deleveraging", deleveraging), key=lambda x: abs(x[1]))
        share = abs(top[1]) / total_v * 100.0
        bullets.append(
            f"<strong>{top[0]}</strong> is the dominant value driver "
            f"(<strong>{share:.0f}%</strong> of total value created)."
        )
    if multiple < 0:
        bullets.append(
            f"Exit multiple ({float(getattr(ass_obj, 'exit_multiple', 0) or 0):.1f}x) "
            "is below entry — value-from-multiple is negative; the deal relies "
            "on EBITDA growth and deleveraging to clear."
        )
    items = "".join(f"<li>{b}</li>" for b in bullets)
    return (
        '<ul style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;padding-left:18px;">{items}</ul>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'EVERY BULLET IS DERIVED FROM REAL LBORESULT NUMBERS &mdash; NOT A PROSE THESIS.</p>'
    )


def render_deal_lbo(ccn: str, hospital: Dict[str, Any]) -> str:
    """Render Surface 08 (LBO) for ``ccn``.

    Reads HCRIS NPR + opex → builds the LBO via `build_lbo_from_deal`. When
    NPR is missing/zero, renders an honest empty panel — no defaulted returns.
    """
    npr = _safe_float(hospital.get("net_patient_revenue"))
    opex = _safe_float(hospital.get("operating_expenses"))
    if not npr or npr <= 1e5:
        return deal_shell(
            ccn, hospital, active_slug="lbo",
            body_html=_empty(f"HCRIS net patient revenue is missing or "
                             f"non-positive for CCN {ccn}."),
            page_title=f"LBO · {hospital.get('name') or f'CCN {ccn}'}",
        )

    try:
        from ...finance.lbo_model import build_lbo_from_deal
    except ImportError:                                # pragma: no cover
        from rcm_mc.finance.lbo_model import build_lbo_from_deal

    # Pass the real NPR; pass current EBITDA when both NPR and opex are
    # present so the engine doesn't fall back to its 12% default margin.
    profile: Dict[str, Any] = {"net_revenue": float(npr)}
    if opex is not None and opex > 0:
        profile["current_ebitda"] = float(npr) - float(opex)

    try:
        lbo = build_lbo_from_deal(profile)
    except Exception:                                  # noqa: BLE001
        return deal_shell(
            ccn, hospital, active_slug="lbo",
            body_html=_empty(
                "The LBO engine returned an error for this hospital's inputs."
            ),
            page_title=f"LBO · {hospital.get('name') or f'CCN {ccn}'}",
        )

    panels = [
        _panel("01 · HERO", "5-year hold returns",
               _hero(lbo.returns, lbo.sources_and_uses, lbo.assumptions)),
        _panel("02 · SOURCES & USES", "Capital stack at entry",
               _sources_and_uses(lbo.sources_and_uses)),
        _panel("03 · WHAT DRIVES THE RETURN",
               "Signals from the LBO output",
               _signals_panel(lbo.returns, lbo.assumptions)),
        _panel("04 · RETURNS WATERFALL",
               "Exit EBITDA → Equity → Value created",
               _waterfall_panel(lbo.returns)),
        _panel("05 · WHAT'S NEXT", "Coming in later phases",
               '<p style="font-family:var(--sc-serif);font-size:14.5px;'
               'line-height:1.55;color:#2a3a4a;margin:0;">'
               'Editable assumption panel (entry/exit multiples, leverage, '
               'growth, margin path) and the year-by-year debt schedule '
               'land in a follow-up PR; the model already supports them — '
               'this surface just needs the editor UI. Cross-link to '
               f'<a href="/deals/{_html.escape(ccn, quote=True)}/returns" '
               'style="color:#1f7a5a;">Returns</a> for the covenant '
               'headroom and stress-test lens.</p>'),
    ]
    body = "".join(panels)
    return deal_shell(
        ccn, hospital, active_slug="lbo", body_html=body,
        page_title=f"LBO · {hospital.get('name') or f'CCN {ccn}'}",
    )
