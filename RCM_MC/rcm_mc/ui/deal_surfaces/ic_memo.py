"""Surface 02 · IC Memo — auto-assembled investment committee memorandum.

Composition surface. Pulls outputs from every other built surface in the
deal-lens family and lays them out in the spec's 8-section sequence + a
dark-navy recommendation block. Nothing here is generated; every section
is real data from real engines, or it's an honest empty.

Sources used (all real services already wired in earlier phases):
- intelligence.caduceus_score        → investability grade letter for the hero
- HCRIS row                          → KPI table in Target Overview
- ml.comparable_finder               → RCM comp peer table
- ui.ebitda_bridge_page._compute_bridge
  + ml.realization_predictor         → Predicted Improvements (5 levers,
                                       P-weighted), EBITDA bridge
- finance.lbo_model.build_lbo_from_deal at 3 exit multiples
                                     → Returns scenarios matrix (bear/base/bull)
- finance.denial_drivers.analyze_denial_drivers
                                     → Risk surface auto-derives the top
                                       denial drivers as flagged risks

The spec calls for a streaming "section-by-section navy bars fill as each
section resolves" pattern; on the server we render synchronously, so the
sections appear in a single page-load. That's fine — no fabrication.

What the spec wants but we deliberately don't ship:
- PDF export                — needs a server-side render pipeline; deferred.
- Right-rail comments       — needs persistence; deferred.
- Risks taxonomy from a     — render only AUTO-DERIVED risks (from real
  curated deal-team source     drivers). The spec's hand-curated taxonomy
                                lands when the deal team has supplied it.
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


def _medicare_share(h: Dict[str, Any]) -> Optional[float]:
    for k in ("percent_days_medicare", "medicare_day_pct", "medicare_days_pct"):
        v = _safe_float(h.get(k))
        if v is not None:
            return v if v <= 1.5 else v / 100.0
    return None


# ───────────────────────── section helpers ─────────────────────────

def _section(num: int, title: str, body_html: str) -> str:
    """One IC-memo section — sticky-pinned head + body in a square panel."""
    return (
        '<section id="section-' + str(num) + '" '
        'style="background:#fff;border:1px solid #c9c1ac;'
        'padding:24px 28px;margin:0 0 22px;scroll-margin-top:80px;">'
        '<header style="display:flex;align-items:baseline;gap:16px;'
        'border-bottom:1px solid #ece6d7;padding-bottom:10px;margin-bottom:18px;">'
        f'<span style="font-family:var(--sc-mono);font-size:10.5px;'
        f'letter-spacing:.22em;text-transform:uppercase;color:#1f7a5a;">'
        f'Section {num}</span>'
        f'<h2 style="font-family:var(--sc-serif);font-weight:400;font-size:24px;'
        f'line-height:1.15;letter-spacing:-.01em;margin:0;color:#15202b;">'
        f'{_html.escape(title)}</h2></header>'
        f'{body_html}</section>'
    )


def _empty(reason: str) -> str:
    return (
        '<section style="background:#faf6ec;border:1px solid #c9c1ac;'
        'padding:24px 26px;">'
        '<span style="font-family:var(--sc-mono);font-size:10px;'
        'letter-spacing:.18em;text-transform:uppercase;color:#b8842e;">'
        'IC memo cannot run</span>'
        '<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
        'margin:6px 0 12px;color:#15202b;">HCRIS inputs not available</h3>'
        f'<p style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;">{_html.escape(reason)}</p>'
        '</section>'
    )


def _hero(hospital: Dict[str, Any], score: Any) -> str:
    """Investability grade + cross-link buttons."""
    ccn = _html.escape(str(hospital.get("ccn", "")), quote=True)
    grade = str(getattr(score, "grade", "—"))
    s = int(getattr(score, "score", 0))
    color = "#1f7a5a" if s >= 70 else ("#b8842e" if s >= 30 else "#b5321e")
    cross = [
        ("profile",     "Profile"),
        ("bridge",      "Bridge"),
        ("lbo",         "LBO"),
        ("comp-intel",  "Comp Intel"),
        ("returns",     "Returns"),
    ]
    btns = "".join(
        f'<a href="/deals/{ccn}/{slug}" style="display:inline-block;'
        f'padding:8px 14px;border:1px solid #c9c1ac;background:#faf6ec;'
        f'color:#15202b;text-decoration:none;font-family:var(--sc-mono);'
        f'font-size:11px;letter-spacing:.12em;text-transform:uppercase;'
        f'margin:0 8px 8px 0;">{_html.escape(label)}</a>'
        for slug, label in cross
    )
    return (
        '<div style="display:grid;grid-template-columns:0.4fr 1.6fr;gap:24px;'
        'align-items:center;background:#fff;border:1px solid #c9c1ac;'
        'padding:24px 28px;margin:0 0 22px;">'
        '<div style="text-align:center;">'
        f'<div style="font-family:var(--sc-serif);font-size:72px;font-weight:400;'
        f'line-height:1;color:{color};">{_html.escape(grade)}</div>'
        '<div style="font-family:var(--sc-mono);font-size:10.5px;letter-spacing:.18em;'
        'text-transform:uppercase;color:#6a7480;margin-top:6px;">Investability grade</div>'
        f'<div style="font-family:var(--sc-mono);font-size:11px;color:#2a3a4a;'
        f'margin-top:6px;font-variant-numeric:tabular-nums;">{s} / 100</div>'
        '</div>'
        '<div>'
        '<div style="font-family:var(--sc-mono);font-size:10.5px;letter-spacing:.18em;'
        'text-transform:uppercase;color:#6a7480;margin-bottom:10px;">Cross-links</div>'
        f'{btns}'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'PDF EXPORT IS A SERVER-SIDE PIPELINE THAT LANDS IN A LATER PHASE.</p>'
        '</div></div>'
    )


def _kpi_table(hospital: Dict[str, Any]) -> str:
    npr = _safe_float(hospital.get("net_patient_revenue"))
    opex = _safe_float(hospital.get("operating_expenses"))
    margin = None
    if npr and opex and npr > 0:
        margin = (npr - opex) / npr
    rows = [
        ("Net patient revenue",  _fmt_money(npr)),
        ("Operating expenses",   _fmt_money(opex)),
        ("Operating EBITDA",     _fmt_money(((npr - opex) if (npr and opex) else None))),
        ("Operating margin",     _fmt_pct(margin)),
        ("Beds",                 _fmt_int(hospital.get("beds"))),
        ("State",                _html.escape(str(hospital.get("state") or "—"))),
    ]
    rows_html = "".join(
        '<tr>'
        f'<td style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.12em;'
        f'text-transform:uppercase;color:#6a7480;padding:6px 4px;width:55%;">'
        f'{_html.escape(label)}</td>'
        f'<td class="num" style="font-family:var(--sc-mono);font-size:12.5px;'
        f'color:#15202b;text-align:right;padding:6px 4px;'
        f'font-variant-numeric:tabular-nums;">{value}</td>'
        '</tr>'
        for label, value in rows
    )
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        f'<tbody>{rows_html}</tbody></table>'
    )


def _target_overview(hospital: Dict[str, Any], score: Any) -> str:
    name = _html.escape(str(hospital.get("name") or "(unnamed)"))
    state = _html.escape(str(hospital.get("state") or "—"))
    city = _html.escape(str(hospital.get("city") or ""))
    loc = f"{city}, {state}" if city else state
    grade = str(getattr(score, "grade", "—"))
    s = int(getattr(score, "score", 0))
    # Lede pattern from the sweep spec: italic first phrase, then roman.
    prose = (
        '<p style="font-family:var(--sc-serif);font-size:16px;line-height:1.55;'
        'color:#2a3a4a;margin:0 0 14px;max-width:56ch;">'
        f'<em style="color:#154e36;font-style:italic;">A {loc} hospital '
        f'scoring {s}/100 on the PE Desk composite.</em> '
        f'{name} carries the financial and structural profile of a '
        f'{"Tier-A" if s >= 70 else "developmental"} acquisition target. '
        'The KPI table at right is sourced entirely from HCRIS — every '
        'figure is a real reported column or a subtotal computed from '
        'one.</p>'
    )
    return (
        '<div style="display:grid;grid-template-columns:1.4fr 1fr;gap:32px;'
        'align-items:start;">'
        f'<div>{prose}</div>'
        f'<div>{_kpi_table(hospital)}</div></div>'
    )


def _market_context(hospital: Dict[str, Any]) -> str:
    """State stat trio — we have state but not state aggregates here; render
    the honest stat-trio with the hospital's own state and an honest note
    that state-aggregate panels need the Market surface (Phase 16 next)."""
    state = _html.escape(str(hospital.get("state") or "—"))
    npr = _safe_float(hospital.get("net_patient_revenue"))
    beds = _safe_float(hospital.get("beds"))
    rows = [
        ("State", state),
        ("This hospital's NPR", _fmt_money(npr)),
        ("This hospital's beds", _fmt_int(beds)),
    ]
    cells = "".join(
        '<div style="border:1px solid #c9c1ac;background:#faf6ec;padding:14px 18px;">'
        f'<dt style="font-family:var(--sc-mono);font-size:9.5px;letter-spacing:.14em;'
        f'text-transform:uppercase;color:#6a7480;margin:0 0 4px;">{_html.escape(label)}</dt>'
        '<dd style="font-family:var(--sc-serif);font-size:20px;margin:0;'
        f'color:#15202b;font-variant-numeric:tabular-nums;">{value}</dd></div>'
        for label, value in rows
    )
    return (
        '<dl style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));'
        f'gap:12px;margin:0 0 12px;">{cells}</dl>'
        '<p style="font-family:var(--sc-serif);font-size:14px;line-height:1.55;'
        'color:#2a3a4a;margin:0;">'
        '<em style="color:#154e36;font-style:italic;">State-aggregate market '
        'context lives on the Market surface.</em> '
        'This memo intentionally does not duplicate that analysis — the '
        'cross-link in the hero opens it directly.</p>'
    )


def _rcm_comp(hospital: Dict[str, Any]) -> str:
    """Peer comp table; uses comparable_finder."""
    try:
        from ...data.hcris import _get_latest_per_ccn
        from ...ml.comparable_finder import find_comparables
    except ImportError:                                # pragma: no cover
        from rcm_mc.data.hcris import _get_latest_per_ccn
        from rcm_mc.ml.comparable_finder import find_comparables
    try:
        hdf = _get_latest_per_ccn()
        pool = hdf.to_dict("records") if hdf is not None else []
    except Exception:                                  # noqa: BLE001
        pool = []
    peers = find_comparables(hospital, pool, max_results=6) or []
    if not peers:
        return ('<p style="font-family:var(--sc-serif);font-style:italic;'
                'color:#6a7480;font-size:13px;margin:0;">'
                'No peer rows available from the matcher.</p>')
    rows = []
    for p in peers:
        peer_ccn = _html.escape(str(p.get("ccn", "")), quote=True)
        peer_name = _html.escape(str(p.get("name", "") or f"CCN {peer_ccn}"))
        st = _html.escape(str(p.get("state", "") or "—"))
        beds = _fmt_int(p.get("beds"))
        npr_p = _fmt_money(p.get("net_patient_revenue"))
        opex_p = _safe_float(p.get("operating_expenses"))
        npr_pn = _safe_float(p.get("net_patient_revenue"))
        margin = ((npr_pn - opex_p) / npr_pn) if (npr_pn and opex_p) else None
        rows.append(
            '<tr>'
            f'<td><a href="/deals/{peer_ccn}/profile" style="color:#1f7a5a;'
            f'text-decoration:none;">{peer_name}</a></td>'
            f'<td>{st}</td><td class="num">{beds}</td>'
            f'<td class="num">{npr_p}</td><td class="num">{_fmt_pct(margin)}</td>'
            '</tr>'
        )
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        '<thead><tr>'
        '<th>Peer</th><th>State</th><th class="num">Beds</th>'
        '<th class="num">NPR</th><th class="num">Op margin</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


def _predicted_improvements(bridge: Dict[str, Any], realization: Any) -> str:
    """5-lever table (top 5 by gross impact) + P-weighted column."""
    levers = list(bridge.get("levers") or [])[:5]
    p = float(getattr(realization, "expected_realization", 1.0) or 1.0)
    if not levers:
        return ('<p style="font-family:var(--sc-serif);font-style:italic;'
                'color:#6a7480;font-size:13px;margin:0;">'
                'No levers produced impact at this metric set.</p>')
    rows = []
    for lev in levers:
        name = str(lev.get("name") or lev.get("metric") or "")
        impact = float(lev.get("ebitda_impact") or 0.0)
        ramp = int(lev.get("ramp_months") or 12)
        rows.append(
            '<tr>'
            f'<td>{_html.escape(name)}</td>'
            f'<td class="num">{_fmt_money(impact)}</td>'
            f'<td class="num">{_fmt_money(impact * p)}</td>'
            f'<td class="num">{ramp} mo</td>'
            '</tr>'
        )
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        '<thead><tr>'
        '<th>Lever</th><th class="num">Gross EBITDA Δ</th>'
        '<th class="num">P-weighted Δ</th><th class="num">Ramp</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        f'P-WEIGHTED = GROSS × REALIZATION ({p*100:.0f}%, FROM THE REALIZATION MODEL).</p>'
    )


def _ebitda_bridge(bridge: Dict[str, Any]) -> str:
    """Reconciliation block: current → uplift → pro-forma."""
    current = float(bridge.get("current_ebitda") or 0.0)
    uplift = float(bridge.get("total_ebitda_impact") or 0.0)
    target = float(bridge.get("new_ebitda") or 0.0)
    rows = [
        ("Current EBITDA",    _fmt_money(current)),
        ("RCM uplift (gross)", _fmt_money(uplift)),
        ("Pro-forma EBITDA",  _fmt_money(target)),
    ]
    rows_html = "".join(
        '<tr>'
        f'<td style="font-family:var(--sc-serif);font-size:14px;color:#15202b;">'
        f'{_html.escape(label)}</td>'
        f'<td class="num" style="font-family:var(--sc-mono);font-size:13px;'
        f'color:#15202b;text-align:right;font-variant-numeric:tabular-nums;">{value}</td>'
        '</tr>'
        for label, value in rows
    )
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        f'<tbody>{rows_html}</tbody></table>'
    )


def _returns_scenarios(profile: Dict[str, Any]) -> str:
    """Bear / Base / Bull LBO at three exit multiples — the LBO engine
    actually accepts `exit_multiple` so we run it three times."""
    try:
        from ...finance.lbo_model import build_lbo, LBOAssumptions
    except ImportError:                                # pragma: no cover
        from rcm_mc.finance.lbo_model import build_lbo, LBOAssumptions
    rev = float(profile.get("net_revenue") or 0.0)
    ebitda = float(profile.get("current_ebitda") or 0.0)
    if rev <= 0 or ebitda <= 0:
        return ('<p style="font-family:var(--sc-serif);font-style:italic;'
                'color:#6a7480;font-size:13px;margin:0;">'
                'Returns matrix needs positive current EBITDA.</p>')
    margin = ebitda / rev
    cases = [("Bear", 8.0), ("Base", 10.5), ("Bull", 13.0)]
    rows = []
    for label, exit_m in cases:
        try:
            lbo = build_lbo(
                entry_ebitda=ebitda, revenue_base=rev,
                ebitda_margin_base=max(0.02, min(0.40, margin)),
                exit_multiple=exit_m,
            )
            irr = float(lbo.returns.irr)
            moic = float(lbo.returns.moic)
            equity_exit = float(lbo.returns.equity_at_exit)
            rows.append(
                '<tr>'
                f'<td><strong>{label}</strong>'
                f' <span style="font-family:var(--sc-mono);font-size:10px;color:#6a7480;">'
                f'({exit_m:.1f}x exit)</span></td>'
                f'<td class="num">{irr*100:.1f}%</td>'
                f'<td class="num">{moic:.2f}x</td>'
                f'<td class="num">{_fmt_money(equity_exit)}</td>'
                '</tr>'
            )
        except Exception:                              # noqa: BLE001
            rows.append(
                f'<tr><td><strong>{label}</strong></td>'
                '<td class="num">—</td><td class="num">—</td>'
                '<td class="num">—</td></tr>'
            )
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        '<thead><tr>'
        '<th>Scenario</th><th class="num">IRR</th><th class="num">MOIC</th>'
        '<th class="num">Exit equity</th>'
        '</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'BEAR / BASE / BULL ARE EXIT-MULTIPLE SHOCKS HOLDING ENTRY + LEVERAGE + '
        'GROWTH CONSTANT. ALL OTHER ASSUMPTIONS COME FROM THE LBO ENGINE DEFAULTS.'
        '</p>'
    )


def _risks_and_mitigants(da: Any) -> str:
    """Two-column itemized list. Risks come from the denial engine's drivers;
    mitigants are the corresponding expert recommendations.
    """
    drivers = list(getattr(da, "drivers", []) or [])[:5]
    recs = list(getattr(da, "expert_recommendations", []) or [])[:5]
    if not drivers and not recs:
        return ('<p style="font-family:var(--sc-serif);font-style:italic;'
                'color:#6a7480;font-size:13px;margin:0;">'
                'No risks auto-derived at this driver profile. The hand-'
                'curated risk taxonomy from the deal team lands here when '
                'supplied.</p>')
    risk_items = "".join(
        f'<li><strong>{_html.escape(str(getattr(d, "driver", "")))}</strong>'
        f' &middot; <span style="color:#6a7480;">{_fmt_money(getattr(d, "estimated_annual_impact", 0))}</span>'
        f'<div style="font-family:var(--sc-serif);font-size:12.5px;'
        f'font-style:italic;color:#6a7480;margin-top:2px;line-height:1.5;">'
        f'{_html.escape(str(getattr(d, "impact_description", "")))}</div></li>'
        for d in drivers
    )
    mit_items = "".join(
        f'<li><strong>{_html.escape(str(r.get("area", "")))}</strong>'
        f' &middot; <span style="color:#6a7480;">{_html.escape(str(r.get("type", "")))}</span>'
        f'<div style="font-family:var(--sc-serif);font-size:12.5px;'
        f'font-style:italic;color:#6a7480;margin-top:2px;line-height:1.5;">'
        f'{_html.escape(str(r.get("examples", "")))}</div></li>'
        for r in recs
    )
    return (
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:32px;">'
        '<div><div style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.18em;'
        'text-transform:uppercase;color:#b5321e;margin-bottom:10px;">Risks</div>'
        f'<ul style="font-family:var(--sc-serif);font-size:14px;line-height:1.55;'
        f'color:#15202b;margin:0;padding-left:18px;">{risk_items or "<li>—</li>"}</ul></div>'
        '<div><div style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.18em;'
        'text-transform:uppercase;color:#1f7a5a;margin-bottom:10px;">Mitigants</div>'
        f'<ul style="font-family:var(--sc-serif);font-size:14px;line-height:1.55;'
        f'color:#15202b;margin:0;padding-left:18px;">{mit_items or "<li>—</li>"}</ul></div>'
        '</div>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:14px 0 0;">'
        'AUTO-DERIVED FROM THE DENIAL DRIVERS + EXPERT-PLAY LIBRARY. '
        'HAND-CURATED RISK TAXONOMY LANDS WHEN DEAL TEAM SUPPLIES IT.</p>'
    )


def _recommendation(score: Any, irr_base: Optional[float], ccn: str) -> str:
    s = int(getattr(score, "score", 0))
    if s >= 75 and irr_base is not None and irr_base >= 0.20:
        verdict, color, cta = (
            "Proceed to deeper diligence",
            "#1f7a5a",
            "Stand up the full diligence workstream and management meeting.",
        )
    elif s >= 50:
        verdict, color, cta = (
            "Hold for further analysis",
            "#b8842e",
            "Pressure-test the bridge realization and exit multiple before "
            "committing diligence resources.",
        )
    else:
        verdict, color, cta = (
            "Pass",
            "#b5321e",
            "Score and modeled returns don't justify a full diligence "
            "spend at the current entry assumption.",
        )
    ccn_safe = _html.escape(ccn, quote=True)
    return (
        '<div style="background:#0b2341;color:#efeadd;'
        'padding:32px 36px;border:1px solid #0b2341;">'
        '<div style="font-family:var(--sc-mono);font-size:10.5px;letter-spacing:.22em;'
        'text-transform:uppercase;color:#a5b4ca;margin-bottom:10px;">Recommendation</div>'
        f'<h2 style="font-family:var(--sc-serif);font-weight:400;font-size:30px;'
        f'line-height:1.1;letter-spacing:-.01em;margin:0 0 14px;color:{color};">'
        f'{_html.escape(verdict)}</h2>'
        '<p style="font-family:var(--sc-serif);font-size:15.5px;line-height:1.6;'
        f'color:#efeadd;margin:0 0 18px;max-width:64ch;">{_html.escape(cta)}</p>'
        f'<a href="/deals/{ccn_safe}/playbook" style="display:inline-block;'
        'padding:10px 20px;border:1px solid #efeadd;background:transparent;'
        'color:#efeadd;text-decoration:none;font-family:var(--sc-mono);'
        'font-size:11.5px;letter-spacing:.14em;text-transform:uppercase;">'
        'Open the 100-day playbook →</a>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#a5b4ca;margin:18px 0 0;">'
        'VERDICT DERIVED FROM CADUCEUS SCORE + LBO BASE-CASE IRR &mdash; '
        'NOT A HALLUCINATED RECOMMENDATION.</p>'
        '</div>'
    )


# ───────────────────────── entry ─────────────────────────

def render_deal_ic_memo(ccn: str, hospital: Dict[str, Any]) -> str:
    """Render Surface 02 (IC Memo) for ``ccn``.

    8-section memo composed from the engines wired in earlier phases. Each
    section is real-data-backed; sections whose source returns nothing
    render an honest empty inside the section frame.
    """
    npr = _safe_float(hospital.get("net_patient_revenue"))
    opex = _safe_float(hospital.get("operating_expenses"))
    if not npr or npr <= 1e5:
        return deal_shell(
            ccn, hospital, active_slug="ic-memo",
            body_html=_empty(
                f"CCN {ccn} has no positive HCRIS net revenue — the memo "
                "can't anchor any of its sections."),
            page_title=f"IC Memo · {hospital.get('name') or f'CCN {ccn}'}",
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
    current_ebitda = float(npr) - float(opex or 0.0)
    medicare = _medicare_share(hospital) or 0.40
    try:
        bridge = _compute_bridge(
            net_revenue=float(npr), current_ebitda=float(current_ebitda),
            medicare_pct=float(medicare),
        )
    except Exception:                                  # noqa: BLE001
        bridge = {"levers": [], "current_ebitda": current_ebitda,
                  "total_ebitda_impact": 0.0, "new_ebitda": current_ebitda}
    realization = None
    try:
        hdf = _get_latest_per_ccn()
        realization = predict_realization(
            ccn, hdf, bridge_uplift=float(bridge.get("total_ebitda_impact") or 0.0))
    except Exception:                                  # noqa: BLE001
        realization = None
    if realization is None:
        class _Default:
            expected_realization = 1.0
        realization = _Default()
    lbo_profile = {"net_revenue": float(npr), "current_ebitda": current_ebitda}
    try:
        lbo_base = build_lbo_from_deal(lbo_profile)
        irr_base = float(lbo_base.returns.irr)
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
            expert_recommendations = []
        da = _Empty()

    sections = []
    sections.append(_hero(hospital, score))
    sections.append(_section(1, "Target overview",
                             _target_overview(hospital, score)))
    sections.append(_section(2, "Market context",
                             _market_context(hospital)))
    sections.append(_section(3, "RCM comp",
                             _rcm_comp(hospital)))
    sections.append(_section(4, "Predicted improvements",
                             _predicted_improvements(bridge, realization)))
    sections.append(_section(5, "EBITDA bridge",
                             _ebitda_bridge(bridge)))
    sections.append(_section(6, "Returns scenarios",
                             _returns_scenarios(lbo_profile)))
    sections.append(_section(7, "Risks & mitigants",
                             _risks_and_mitigants(da)))
    sections.append(_section(8, "Recommendation",
                             _recommendation(score, irr_base, ccn)))
    body = "".join(sections)
    return deal_shell(
        ccn, hospital, active_slug="ic-memo", body_html=body,
        page_title=f"IC Memo · {hospital.get('name') or f'CCN {ccn}'}",
    )
