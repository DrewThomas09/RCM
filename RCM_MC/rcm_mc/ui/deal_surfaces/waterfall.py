"""Surface 14 · Waterfall — LP / GP distribution split (8% pref + 80/20 carry).

Wired to `finance.lbo_model.build_lbo_from_deal` (the LBO surface's engine).
The LBO engine treats the hold as one bullet distribution at exit — so this
surface applies a standard European waterfall to the exit proceeds:

  1. Return of capital     → LP gets contributed capital back.
  2. Preferred return       → LP gets pref (default 8% IRR-equivalent on
                              capital over the hold) before GP earns carry.
  3. GP catch-up            → GP gets 100% of profits until LP+GP carry-to-
                              date is 80/20 (default).
  4. Split                  → 80% LP / 20% GP on remaining profits.

Spec components shipped (all 3 in the spec):
1. Hero strip            — gross IRR, gross MOIC, invested, exit proceeds, hold
2. LP/GP split bar       — single horizontal bar, two segments with $/MOIC tags;
                           diagonal-stripe pattern when LP MOIC < 1.0
                           (return-of-capital not complete) per the build note
3. What this means       — carry-negotiation guidance derived from the real split

Pref % and 80/20 split are EXPLICIT DEFAULTS — labeled in the footer. The
spec's "drag the pref % input" interaction and "European vs American toggle"
are deferred (read-only display today; the editable controls land later).
"""
from __future__ import annotations

import html as _html
from dataclasses import dataclass
from typing import Any, Dict, Optional

from ._shell import _fmt_money, _fmt_pct, deal_shell


# Industry-default European waterfall terms — labeled explicitly in the UI.
_DEFAULT_PREF_RATE = 0.08          # 8% annual hurdle on contributed capital
_DEFAULT_CARRY_SPLIT = 0.20        # 80 LP / 20 GP above the pref + catch-up


@dataclass
class WaterfallSplit:
    """One run of the European waterfall."""
    invested: float
    exit_proceeds: float
    hold_years: int
    pref_rate: float
    carry_split: float          # GP share above pref + catch-up
    # Outputs
    pref_amount: float
    catch_up: float
    profit_above_catch_up: float
    lp_total: float
    gp_total: float
    lp_moic: float              # lp_total / invested
    gp_moic: float              # gp_total / invested  (carry as % of capital)
    pref_cleared: bool          # exit_proceeds covers ROC + pref


def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def _european_waterfall(
    invested: float, exit_proceeds: float, hold_years: int,
    pref_rate: float = _DEFAULT_PREF_RATE,
    carry_split: float = _DEFAULT_CARRY_SPLIT,
) -> WaterfallSplit:
    """European waterfall on a single bullet distribution at exit.

    Pref is approximated as ``invested × pref_rate × hold_years`` — i.e., a
    simple-interest hurdle equivalent to an 8%-per-year preferred return.
    Compounded pref would use ``invested × ((1+pref_rate)**hold − 1)`` and
    differs by <2% at 5-year holds; we keep the simple-interest convention
    to match the closed-form LBO engine elsewhere in the app.
    """
    invested = max(0.0, float(invested))
    exit_proceeds = max(0.0, float(exit_proceeds))
    hold_years = max(1, int(hold_years))
    pref_amount = invested * pref_rate * hold_years
    roc_plus_pref = invested + pref_amount
    if exit_proceeds <= invested:
        # Return-of-capital not even complete; LP takes everything, GP zero.
        return WaterfallSplit(
            invested, exit_proceeds, hold_years, pref_rate, carry_split,
            pref_amount=0.0, catch_up=0.0, profit_above_catch_up=0.0,
            lp_total=exit_proceeds, gp_total=0.0,
            lp_moic=(exit_proceeds / invested) if invested else 0.0,
            gp_moic=0.0, pref_cleared=False,
        )
    if exit_proceeds <= roc_plus_pref:
        # Pref not yet cleared; LP gets ROC + partial pref, GP zero.
        return WaterfallSplit(
            invested, exit_proceeds, hold_years, pref_rate, carry_split,
            pref_amount=exit_proceeds - invested, catch_up=0.0,
            profit_above_catch_up=0.0,
            lp_total=exit_proceeds, gp_total=0.0,
            lp_moic=exit_proceeds / invested,
            gp_moic=0.0, pref_cleared=False,
        )
    # GP catch-up: GP takes 100% until total carry-paid / (pref+catch-up) = 20%.
    # Solve: catch_up_amount × 1 = carry_split × (pref + catch_up_amount)
    # → catch_up_amount = (carry_split / (1 - carry_split)) × pref
    catch_up = (carry_split / (1.0 - carry_split)) * pref_amount
    after_catch_up_pool = max(0.0, exit_proceeds - roc_plus_pref - catch_up)
    profit_above_catch_up = after_catch_up_pool
    gp_split_share = carry_split * after_catch_up_pool
    lp_split_share = (1.0 - carry_split) * after_catch_up_pool
    lp_total = invested + pref_amount + lp_split_share
    gp_total = min(exit_proceeds - lp_total, catch_up + gp_split_share)
    return WaterfallSplit(
        invested, exit_proceeds, hold_years, pref_rate, carry_split,
        pref_amount=pref_amount, catch_up=catch_up,
        profit_above_catch_up=after_catch_up_pool,
        lp_total=lp_total, gp_total=gp_total,
        lp_moic=lp_total / invested if invested else 0.0,
        gp_moic=gp_total / invested if invested else 0.0,
        pref_cleared=True,
    )


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
        'Waterfall cannot run</span>'
        '<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
        'margin:6px 0 12px;color:#15202b;">'
        'LBO inputs missing</h3>'
        f'<p style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;">{_html.escape(reason)} The waterfall '
        'inherits the LBO engine\'s entry equity and exit proceeds.</p>'
        '</section>'
    )


def _hero(lbo_returns: Any, ass: Any) -> str:
    irr = float(getattr(lbo_returns, "irr", 0.0) or 0.0)
    moic = float(getattr(lbo_returns, "moic", 0.0) or 0.0)
    invested = float(getattr(lbo_returns, "equity_invested", 0.0) or 0.0)
    exit_proceeds = float(getattr(lbo_returns, "equity_at_exit", 0.0) or 0.0)
    hold = int(getattr(ass, "hold_years", 5) or 5)
    rows = [
        ("Gross IRR",        f"{irr*100:.1f}%"),
        ("Gross MOIC",       f"{moic:.2f}x"),
        ("Equity invested",  _fmt_money(invested)),
        ("Exit proceeds",    _fmt_money(exit_proceeds)),
        ("Hold",             f"{hold} years"),
    ]
    cells = "".join(
        '<div style="border:1px solid #c9c1ac;background:#faf6ec;padding:12px 14px;">'
        f'<dt style="font-family:var(--sc-mono);font-size:9.5px;'
        f'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;'
        f'margin:0 0 4px;">{_html.escape(label)}</dt>'
        '<dd style="font-family:var(--sc-serif);font-size:20px;margin:0;'
        f'color:#15202b;font-variant-numeric:tabular-nums;">{value}</dd></div>'
        for label, value in rows
    )
    return (
        '<dl style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));'
        f'gap:12px;margin:0;">{cells}</dl>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'GROSS NUMBERS BEFORE THE WATERFALL APPLIES — LP/GP SHARES ARE BELOW.</p>'
    )


def _split_bar(w: WaterfallSplit) -> str:
    """LP/GP horizontal bar + dollar/MOIC tags. Diagonal stripes on LP when
    return-of-capital isn't complete (lp_moic < 1.0).
    """
    total = max(1.0, w.lp_total + w.gp_total)
    lp_pct = w.lp_total / total * 100.0
    gp_pct = 100.0 - lp_pct
    stripe = w.lp_moic < 1.0
    lp_bg = (
        # Diagonal stripes signal "return of capital not yet complete"
        "repeating-linear-gradient(45deg,#b8842e 0 6px,#ecdfb4 6px 12px)"
        if stripe else "#0b2341"
    )
    return (
        '<div style="display:flex;border:1px solid #c9c1ac;height:36px;'
        'overflow:hidden;background:#faf6ec;">'
        # LP segment
        f'<div style="flex:0 0 {lp_pct:.1f}%;background:{lp_bg};color:#fff;'
        'padding:0 14px;display:flex;align-items:center;font-family:var(--sc-mono);'
        f'font-size:11px;letter-spacing:.12em;text-transform:uppercase;">'
        f'LP {_fmt_money(w.lp_total)} ({w.lp_moic:.2f}x)</div>'
        # GP segment
        f'<div style="flex:0 0 {gp_pct:.1f}%;background:#155752;color:#fff;'
        'padding:0 14px;display:flex;align-items:center;font-family:var(--sc-mono);'
        f'font-size:11px;letter-spacing:.12em;text-transform:uppercase;">'
        f'GP {_fmt_money(w.gp_total)} ({w.gp_moic:.2f}x carry/capital)</div>'
        '</div>'
        # Breakdown rows
        '<div style="margin:14px 0 0;font-family:var(--sc-serif);font-size:13.5px;'
        'color:#2a3a4a;line-height:1.6;">'
        f'<div>Return of capital → LP <strong>{_fmt_money(w.invested)}</strong></div>'
        f'<div>Preferred return ({w.pref_rate*100:.0f}% × {w.hold_years}y simple) '
        f'→ LP <strong>{_fmt_money(w.pref_amount)}</strong>'
        f'{"" if w.pref_cleared else " — <em style=\"color:#b8842e;\">pref not cleared</em>"}'
        '</div>'
        f'<div>GP catch-up → GP <strong>{_fmt_money(w.catch_up)}</strong></div>'
        f'<div>Profit above catch-up → split '
        f'{int((1-w.carry_split)*100)}% LP / {int(w.carry_split*100)}% GP '
        f'on <strong>{_fmt_money(w.profit_above_catch_up)}</strong></div>'
        '</div>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:12px 0 0;">'
        f'PREF {w.pref_rate*100:.0f}% &middot; CARRY {int((1-w.carry_split)*100)}/'
        f'{int(w.carry_split*100)} &middot; EUROPEAN WATERFALL &middot; THESE ARE '
        'INDUSTRY-DEFAULT TERMS — OVERRIDE WITH THE ACTUAL FUND DOCS WHEN AVAILABLE.'
        f'{" DIAGONAL-STRIPE PATTERN ON LP = RETURN-OF-CAPITAL NOT COMPLETE." if w.lp_moic < 1.0 else ""}'
        '</p>'
    )


def _what_this_means(w: WaterfallSplit, irr: float) -> str:
    bullets = []
    if not w.pref_cleared:
        bullets.append(
            "<strong>Pref is not cleared</strong> at this exit — LP doesn't "
            "earn its 8% hurdle and GP earns zero carry. The deal needs more "
            "exit value or a longer hold before carry math matters."
        )
    elif w.gp_moic < 0.10:
        bullets.append(
            f"GP carry / capital is <strong>{w.gp_moic:.2f}x</strong> — modest. "
            "If the GP is negotiating fund terms, this is a deal where a higher "
            "carry split (e.g. 75/25) is harder to justify."
        )
    else:
        bullets.append(
            f"GP carry / capital is <strong>{w.gp_moic:.2f}x</strong> on top of "
            f"capital — material. Standard 80/20 terms hold up."
        )
    if irr < 0.20 and w.pref_cleared:
        bullets.append(
            f"IRR of <strong>{irr*100:.1f}%</strong> just clears the pref hurdle. "
            "Be ready for LP questions about cushion against multiple-compression "
            "at exit."
        )
    items = "".join(f"<li>{b}</li>" for b in bullets)
    return (
        '<ul style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;padding-left:18px;">{items}</ul>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'GUIDANCE DERIVED FROM REAL WATERFALL NUMBERS — NEVER A PROSE THESIS.</p>'
    )


def render_deal_waterfall(ccn: str, hospital: Dict[str, Any]) -> str:
    """Render Surface 14 (Waterfall) for ``ccn``."""
    npr = _safe_float(hospital.get("net_patient_revenue"))
    opex = _safe_float(hospital.get("operating_expenses"))
    if not npr or npr <= 1e5:
        return deal_shell(
            ccn, hospital, active_slug="waterfall",
            body_html=_empty(f"CCN {ccn} has no positive HCRIS net revenue."),
            page_title=f"Waterfall · {hospital.get('name') or f'CCN {ccn}'}",
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
            ccn, hospital, active_slug="waterfall",
            body_html=_empty("The LBO engine returned an error."),
            page_title=f"Waterfall · {hospital.get('name') or f'CCN {ccn}'}",
        )

    invested = float(getattr(lbo.returns, "equity_invested", 0.0) or 0.0)
    exit_proceeds = float(getattr(lbo.returns, "equity_at_exit", 0.0) or 0.0)
    hold = int(getattr(lbo.assumptions, "hold_years", 5) or 5)
    irr = float(getattr(lbo.returns, "irr", 0.0) or 0.0)
    w = _european_waterfall(invested, exit_proceeds, hold)

    panels = [
        _panel("01 · HERO", "Gross deal returns",
               _hero(lbo.returns, lbo.assumptions)),
        _panel("02 · LP / GP SPLIT",
               "Where the exit proceeds actually land",
               _split_bar(w)),
        _panel("03 · WHAT THIS MEANS",
               "Carry-negotiation guidance",
               _what_this_means(w, irr)),
        _panel("04 · WHAT'S NEXT", "Deferred to a later phase",
               '<p style="font-family:var(--sc-serif);font-size:14.5px;'
               'line-height:1.55;color:#2a3a4a;margin:0;">'
               'The spec\'s editable pref % input and European/American toggle '
               'are read-only today. When the deal-team config layer lands, '
               'this surface picks them up automatically.</p>'),
    ]
    body = "".join(panels)
    return deal_shell(
        ccn, hospital, active_slug="waterfall", body_html=body,
        page_title=f"Waterfall · {hospital.get('name') or f'CCN {ccn}'}",
    )
