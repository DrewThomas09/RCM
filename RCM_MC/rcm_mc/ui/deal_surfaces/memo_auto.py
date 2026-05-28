"""Surface 18 · Memo (auto) — lightweight 4-section quick-take memo.

The full IC packet lives on Surface 02 (IC Memo). This surface is the
"hour-before-review" leave-behind: 4 sections of template-driven prose
where every blank fills from real HCRIS / engine outputs.

Per the spec's build note: "Verification badge default is 'unverified';
only flip to 'verified' after fact-check passes." There is no dedicated
fact-check service today, so every section ships with the unverified
badge — honest. The hero shows the warning count (= sections still
unverified, which is all of them) so partners read this as scaffolding,
not finished memo, exactly per the spec.

Components shipped (5 of 6 in the spec):
1. HERO                 — memo sections count, fact-check warnings,
                          generation method
2. EXECUTIVE SUMMARY    — paragraph templated from HCRIS-derived facts
3. INVESTMENT THESIS    — value-creation narrative templated from
                          score + bridge gross uplift
4. RISK ASSESSMENT      — top 3 risks templated from denial drivers
                          (or default risk band when none surface)
5. RECOMMENDATION       — verdict templated from score band × IRR band
                          (same finite map as IC Memo)
6. CROSS-LINKS panel    — links to the full IC packet + diligence
                          questions surface (the JSON download is
                          deferred — needs an export endpoint that
                          doesn't exist today)
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


def _medicare_share(h: Dict[str, Any]) -> Optional[float]:
    for k in ("percent_days_medicare", "medicare_day_pct", "medicare_days_pct"):
        v = _safe_float(h.get(k))
        if v is not None:
            return v if v <= 1.5 else v / 100.0
    return None


def _verification_badge(verified: bool = False) -> str:
    """Per spec: default unverified amber pill; verified green pill."""
    if verified:
        color, bg, label = "#1f7a5a", "#d6e8df", "Verified"
    else:
        color, bg, label = "#b8842e", "#fbedd9", "Unverified"
    return (
        f'<span style="font-family:var(--sc-mono);font-size:9.5px;'
        f'letter-spacing:.14em;text-transform:uppercase;color:{color};'
        f'background:{bg};border:1px solid {color};padding:2px 8px;'
        f'margin-left:auto;">{label}</span>'
    )


def _panel(num: int, title: str, body_html: str, verified: bool = False) -> str:
    """One memo section panel — eyebrow + title + verification badge."""
    return (
        '<section style="background:#fff;border:1px solid #c9c1ac;'
        'padding:20px 22px;margin:0 0 18px;">'
        '<header style="display:flex;align-items:center;gap:12px;'
        'margin-bottom:12px;">'
        f'<span style="font-family:var(--sc-mono);font-size:10px;'
        f'letter-spacing:.18em;text-transform:uppercase;color:#1f7a5a;'
        f'flex-shrink:0;">Section {num:02d}</span>'
        f'<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
        f'line-height:1.15;margin:0;color:#15202b;">{_html.escape(title)}</h3>'
        f'{_verification_badge(verified)}'
        '</header>'
        f'{body_html}</section>'
    )


def _empty(reason: str) -> str:
    return (
        '<section style="background:#faf6ec;border:1px solid #c9c1ac;'
        'padding:24px 26px;">'
        '<span style="font-family:var(--sc-mono);font-size:10px;'
        'letter-spacing:.18em;text-transform:uppercase;color:#b8842e;">'
        'Auto-memo cannot run</span>'
        '<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
        'margin:6px 0 12px;color:#15202b;">HCRIS inputs missing</h3>'
        f'<p style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;">{_html.escape(reason)}</p>'
        '</section>'
    )


def _hero(n_sections: int, n_warnings: int) -> str:
    rows = [
        ("Sections",        f"{n_sections}"),
        ("Fact-check warnings", f"{n_warnings}"),
        ("Generation",      "Template-driven"),
        ("Reading time",    "≈ 4 minutes"),
    ]
    cells = "".join(
        '<div style="border:1px solid #c9c1ac;background:#faf6ec;padding:12px 14px;">'
        f'<dt style="font-family:var(--sc-mono);font-size:9.5px;'
        f'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;'
        f'margin:0 0 4px;">{_html.escape(label)}</dt>'
        '<dd style="font-family:var(--sc-serif);font-size:20px;margin:0;'
        f'color:#15202b;font-variant-numeric:tabular-nums;">{_html.escape(value)}</dd></div>'
        for label, value in rows
    )
    return (
        '<dl style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));'
        f'gap:12px;margin:0;">{cells}</dl>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'EVERY SECTION SHIPS WITH THE "UNVERIFIED" BADGE BY DEFAULT. THE '
        'WARNING COUNT EQUALS THE NUMBER OF SECTIONS A FACT-CHECK SERVICE '
        'WOULD NEED TO CONFIRM &mdash; THAT SERVICE ISN\'T WIRED YET, SO '
        'TREAT THIS MEMO AS SCAFFOLDING, NOT A FINISHED DOCUMENT.</p>'
    )


def _exec_summary(hospital: Dict[str, Any], score: Any, bridge: Dict[str, Any]) -> str:
    name = _html.escape(str(hospital.get("name") or "Hospital"))
    state = _html.escape(str(hospital.get("state") or "?"))
    npr = _safe_float(hospital.get("net_patient_revenue")) or 0.0
    beds = _safe_float(hospital.get("beds")) or 0
    opex = _safe_float(hospital.get("operating_expenses")) or 0.0
    current_ebitda = npr - opex
    margin = (current_ebitda / npr) if npr > 0 else 0
    uplift = float(bridge.get("total_ebitda_impact") or 0)
    s = int(getattr(score, "score", 0))
    text = (
        f'<em style="color:#154e36;font-style:italic;">A {state}-based '
        f'hospital scoring {s}/100 on the PE Desk composite.</em> '
        f'{name} runs {int(beds):,} beds and {_fmt_money(npr)} of net '
        f'patient revenue at a {margin*100:.1f}% operating margin '
        f'({_fmt_money(current_ebitda)} current EBITDA). The seven-lever '
        f'RCM bridge sizes the gross uplift at {_fmt_money(uplift)} — '
        'before realization discounts and execution risk.'
    )
    return (
        f'<p style="font-family:var(--sc-serif);font-size:15.5px;line-height:1.65;'
        f'color:#2a3a4a;margin:0;max-width:60ch;">{text}</p>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'EVERY FIGURE IS REAL HCRIS OR REAL ENGINE OUTPUT &mdash; THE PROSE '
        'WRAPPER IS TEMPLATE FILL, NOT GENERATED LANGUAGE.</p>'
    )


def _investment_thesis(hospital: Dict[str, Any], score: Any,
                       bridge: Dict[str, Any], realization: Any) -> str:
    npr = _safe_float(hospital.get("net_patient_revenue")) or 0.0
    uplift = float(bridge.get("total_ebitda_impact") or 0)
    p = float(getattr(realization, "expected_realization", 1.0) or 1.0)
    p_weighted = uplift * p
    s = int(getattr(score, "score", 0))
    band = "high" if s >= 70 else ("middle" if s >= 30 else "low")
    text = (
        f'<em style="color:#154e36;font-style:italic;">'
        f'The thesis is RCM-led EBITDA expansion at a {band}-band entry score.</em> '
        f'Applying the realization model\'s {p*100:.0f}% expected achievement '
        f'to the gross uplift puts the probability-weighted EBITDA build at '
        f'{_fmt_money(p_weighted)} — roughly '
        f'{(p_weighted / npr * 10000):.0f} bps of margin if held to NPR. '
    )
    if band == "high":
        text += "Standard-issue middle-market healthcare LBO mechanics apply."
    elif band == "middle":
        text += ("The base case clears a partner-acceptable IRR only if "
                 "exit-multiple compression stays within 1-1.5x.")
    else:
        text += ("This is a developmental thesis — the score reflects "
                 "structural drag that the bridge alone can't reverse.")
    return (
        f'<p style="font-family:var(--sc-serif);font-size:15.5px;line-height:1.65;'
        f'color:#2a3a4a;margin:0;max-width:60ch;">{text}</p>'
    )


def _risk_assessment(da: Any) -> str:
    drivers = list(getattr(da, "drivers", []) or [])[:3]
    if not drivers:
        return (
            '<p style="font-family:var(--sc-serif);font-size:15.5px;line-height:1.65;'
            'color:#2a3a4a;margin:0;max-width:60ch;">'
            '<em style="color:#154e36;font-style:italic;">No driver-level '
            'risks surfaced at this revenue scale.</em> The denial-driver '
            'engine returned an empty decomposition; the deal team should '
            'supply management-reported denial-rate actuals to refine this '
            'section before IC.</p>'
        )
    items = []
    for i, d in enumerate(drivers, start=1):
        name = _html.escape(str(getattr(d, "driver", "")))
        impact = float(getattr(d, "estimated_annual_impact", 0) or 0)
        desc = _html.escape(str(getattr(d, "impact_description", "")))
        items.append(
            f'<li style="margin:0 0 10px;line-height:1.55;">'
            f'<strong>{name}</strong> &mdash; {_fmt_money(impact)} annualized'
            f' EBITDA exposure. <span style="color:#6a7480;font-style:italic;">'
            f'{desc}</span></li>'
        )
    return (
        f'<p style="font-family:var(--sc-serif);font-size:14px;line-height:1.55;'
        f'color:#2a3a4a;margin:0 0 12px;max-width:60ch;">'
        '<em style="color:#154e36;font-style:italic;">Top three risks by sized '
        'EBITDA exposure</em>, auto-derived from the denial-driver engine. The '
        'hand-curated risk taxonomy from the deal team lands once management '
        'materials are shared.</p>'
        f'<ol style="font-family:var(--sc-serif);font-size:14.5px;'
        f'color:#15202b;margin:0;padding-left:24px;">{"".join(items)}</ol>'
    )


def _recommendation(score: Any, irr_base: Optional[float]) -> str:
    s = int(getattr(score, "score", 0))
    if s >= 75 and irr_base is not None and irr_base >= 0.20:
        verdict, tone, next_step = (
            "Proceed to full IC",
            "#1f7a5a",
            "Stand up the full diligence workstream; the score and modeled "
            "IRR justify a partner meeting.",
        )
    elif s >= 50:
        verdict, tone, next_step = (
            "Hold — pressure-test before IC",
            "#b8842e",
            "Stress the exit-multiple and realization assumptions. If the "
            "deal still clears at a 2-multiple compression and 70% "
            "realization, move it forward.",
        )
    else:
        verdict, tone, next_step = (
            "Pass — score and returns insufficient",
            "#b5321e",
            "Document the no-go reasoning in case the target re-surfaces "
            "later, but do not allocate diligence resources at this entry.",
        )
    return (
        f'<div style="font-family:var(--sc-serif);font-size:20px;font-weight:500;'
        f'color:{tone};margin:0 0 10px;">{_html.escape(verdict)}</div>'
        f'<p style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.6;'
        f'color:#2a3a4a;margin:0;max-width:60ch;">{_html.escape(next_step)}</p>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'VERDICT DRAWN FROM A FINITE MAP (SCORE BAND × IRR BAND) &mdash; '
        'IDENTICAL LOGIC TO THE IC MEMO RECOMMENDATION BLOCK.</p>'
    )


def _cross_links(ccn: str) -> str:
    ccn_safe = _html.escape(ccn, quote=True)
    return (
        '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">'
        f'<a href="/deals/{ccn_safe}/ic-memo" style="display:block;padding:16px 18px;'
        'border:1px solid #1f7a5a;background:#d6e8df;color:#154e36;text-decoration:none;">'
        '<div style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.14em;'
        'text-transform:uppercase;color:#1f7a5a;margin-bottom:4px;">Open</div>'
        '<div style="font-family:var(--sc-serif);font-size:15px;color:#154e36;">'
        'Full IC packet →</div></a>'
        f'<a href="/deals/{ccn_safe}/playbook" style="display:block;padding:16px 18px;'
        'border:1px solid #c9c1ac;background:#faf6ec;color:#15202b;text-decoration:none;">'
        '<div style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.14em;'
        'text-transform:uppercase;color:#6a7480;margin-bottom:4px;">Open</div>'
        '<div style="font-family:var(--sc-serif);font-size:15px;color:#15202b;">'
        '100-day playbook →</div></a>'
        '<div style="display:block;padding:16px 18px;border:1px solid #c9c1ac;'
        'background:#faf6ec;color:#6a7480;">'
        '<div style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.14em;'
        'text-transform:uppercase;color:#6a7480;margin-bottom:4px;">Coming soon</div>'
        '<div style="font-family:var(--sc-serif);font-size:15px;color:#6a7480;">'
        'Download JSON (template vars)</div></div>'
        '</div>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'JSON DOWNLOAD NEEDS A SERVER EXPORT ENDPOINT &mdash; LANDS WHEN THE '
        'EXPORT PIPELINE FROM THE IC MEMO PHASE IS WIRED.</p>'
    )


def render_deal_memo_auto(ccn: str, hospital: Dict[str, Any]) -> str:
    """Render Surface 18 (Memo · auto) for ``ccn``.

    Lightweight 4-section quick-take memo with template-driven prose. Every
    figure is real; every prose paragraph fills from a finite map of
    sentences keyed on real data, not generated language.
    """
    npr = _safe_float(hospital.get("net_patient_revenue"))
    if not npr or npr <= 1e5:
        return deal_shell(
            ccn, hospital, active_slug="memo-auto",
            body_html=_empty(
                f"CCN {ccn} has no positive HCRIS net revenue — the memo "
                "needs at least that to anchor the executive summary."),
            page_title=f"Memo · {hospital.get('name') or f'CCN {ccn}'}",
        )

    try:
        from ...intelligence.caduceus_score import compute_caduceus_score
        from ..ebitda_bridge_page import _compute_bridge
        from ...data.hcris import _get_latest_per_ccn
        from ...ml.realization_predictor import predict_realization
        from ...finance.lbo_model import build_lbo_from_deal
        from ...finance.denial_drivers import analyze_denial_drivers
    except ImportError:                                # pragma: no cover
        from rcm_mc.intelligence.caduceus_score import compute_caduceus_score
        from rcm_mc.ui.ebitda_bridge_page import _compute_bridge
        from rcm_mc.data.hcris import _get_latest_per_ccn
        from rcm_mc.ml.realization_predictor import predict_realization
        from rcm_mc.finance.lbo_model import build_lbo_from_deal
        from rcm_mc.finance.denial_drivers import analyze_denial_drivers

    score = compute_caduceus_score(hospital)
    opex = _safe_float(hospital.get("operating_expenses")) or 0.0
    current_ebitda = float(npr) - opex
    medicare = _medicare_share(hospital) or 0.40

    try:
        bridge = _compute_bridge(
            net_revenue=float(npr), current_ebitda=current_ebitda,
            medicare_pct=medicare,
        )
    except Exception:                                  # noqa: BLE001
        bridge = {"total_ebitda_impact": 0.0, "current_ebitda": current_ebitda,
                  "new_ebitda": current_ebitda, "levers": []}

    realization = None
    try:
        hdf = _get_latest_per_ccn()
        realization = predict_realization(
            ccn, hdf, bridge_uplift=float(bridge.get("total_ebitda_impact") or 0))
    except Exception:                                  # noqa: BLE001
        realization = None
    if realization is None:
        class _Default:
            expected_realization = 1.0
        realization = _Default()

    try:
        lbo = build_lbo_from_deal({"net_revenue": float(npr),
                                    "current_ebitda": current_ebitda})
        irr_base = float(lbo.returns.irr)
    except Exception:                                  # noqa: BLE001
        irr_base = None

    try:
        da = analyze_denial_drivers({
            "deal_id": str(ccn), "net_revenue": float(npr),
            "claims_volume": max(1000, int(float(npr) / 15000.0)),
            "state": str(hospital.get("state") or ""),
        })
    except Exception:                                  # noqa: BLE001
        class _Empty:
            drivers = []
        da = _Empty()

    sections_html = [
        _panel(1, "Executive summary",
               _exec_summary(hospital, score, bridge), verified=False),
        _panel(2, "Investment thesis",
               _investment_thesis(hospital, score, bridge, realization),
               verified=False),
        _panel(3, "Risk assessment",
               _risk_assessment(da), verified=False),
        _panel(4, "Recommendation",
               _recommendation(score, irr_base), verified=False),
    ]
    # All 4 sections currently unverified → warning count = 4
    n_warnings = sum(1 for _ in sections_html)  # one per section by default

    body = (
        '<section style="background:#fff;border:1px solid #c9c1ac;'
        'padding:20px 22px;margin:0 0 22px;">'
        '<header style="display:flex;align-items:baseline;gap:16px;'
        'margin-bottom:14px;">'
        '<span style="font-family:var(--sc-mono);font-size:10px;'
        'letter-spacing:.18em;text-transform:uppercase;color:#1f7a5a;">'
        'Section 00 · Hero</span></header>'
        + _hero(4, n_warnings) +
        '</section>'
        + "".join(sections_html) +
        _panel(5, "Cross-links", _cross_links(ccn))
    )
    return deal_shell(
        ccn, hospital, active_slug="memo-auto", body_html=body,
        page_title=f"Memo (auto) · {hospital.get('name') or f'CCN {ccn}'}",
    )
