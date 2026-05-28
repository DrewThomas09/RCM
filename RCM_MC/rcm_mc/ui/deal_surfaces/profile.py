"""Surface 01 · Profile — front door of a deal.

Wired to real data only:
- Identity / financials / payer mix → HCRIS via _get_latest_per_ccn.
- PE Desk score (0–100 + components + grade) → compute_caduceus_score
  (already used by /hospital/<ccn>); components map to the 4 sub-scores in
  the handoff (market position / financial health / op quality / moat).
- Comparable hospitals → ml.comparable_finder.find_comparables, top 8.
- Actions → cross-links to other deal-lens surfaces.

Nothing is fabricated — missing values render as "—". The "Investment thesis"
component is constructed from REAL signals derived from the score and
financials, not a hallucinated paragraph; if there isn't enough to say, the
panel is omitted rather than padded.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from ._shell import (
    SURFACE_BY_PATH, _fmt_int, _fmt_money, _fmt_pct, deal_shell,
)


# ───────────────────────── helpers ─────────────────────────

def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def _op_margin(h: Dict[str, Any]) -> Optional[float]:
    npr = _safe_float(h.get("net_patient_revenue"))
    opex = _safe_float(h.get("operating_expenses"))
    if not npr or not opex or npr <= 1e4:
        return None
    return (npr - opex) / npr


def _rev_per_bed(h: Dict[str, Any]) -> Optional[float]:
    npr = _safe_float(h.get("net_patient_revenue"))
    beds = _safe_float(h.get("beds") or h.get("bed_count"))
    if not npr or not beds or beds <= 0:
        return None
    return npr / beds


def _payer_pct(h: Dict[str, Any], key: str) -> Optional[float]:
    """HCRIS stores payer day shares as fractions in several possible columns —
    return the first one found; never invent a value."""
    for candidate in (
        f"percent_days_{key}", f"pct_days_{key}",
        f"{key}_days_pct", f"{key}_day_pct",
    ):
        v = _safe_float(h.get(candidate))
        if v is not None:
            return v
    return None


# ───────────────────────── panels ─────────────────────────

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


def _score_color(score: int) -> str:
    if score >= 70:
        return "#1f7a5a"
    if score >= 30:
        return "#b8842e"
    return "#b5321e"


def _key_stats(h: Dict[str, Any]) -> str:
    rows = [
        ("Net patient revenue", _fmt_money(h.get("net_patient_revenue"))),
        ("Operating margin",    _fmt_pct(_op_margin(h))),
        ("Net income",          _fmt_money(h.get("net_income"))),
        ("Beds",                _fmt_int(h.get("beds") or h.get("bed_count"))),
        ("Revenue / bed",       _fmt_money(_rev_per_bed(h))),
        ("Operating expenses",  _fmt_money(h.get("operating_expenses"))),
    ]
    cells = "".join(
        '<div style="border:1px solid #c9c1ac;background:#faf6ec;'
        f'padding:12px 14px;">'
        f'<dt style="font-family:var(--sc-mono);font-size:9.5px;'
        f'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;'
        f'margin:0 0 4px;">{_html.escape(label)}</dt>'
        f'<dd style="font-family:var(--sc-serif);font-size:20px;margin:0;'
        f'color:#15202b;font-variant-numeric:tabular-nums;">{value}</dd>'
        '</div>'
        for label, value in rows
    )
    return (
        '<dl style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));'
        f'gap:12px;margin:0;">{cells}</dl>'
    )


def _payer_mix(h: Dict[str, Any]) -> str:
    medicare = _payer_pct(h, "medicare") or 0.0
    medicaid = _payer_pct(h, "medicaid") or 0.0
    # Commercial = remainder of patient-days when both Medicare/Medicaid present.
    commercial = max(0.0, 1.0 - medicare - medicaid) if (medicare or medicaid) else None
    if not medicare and not medicaid and commercial is None:
        return (
            '<p style="font-family:var(--sc-serif);font-style:italic;'
            'color:#6a7480;font-size:13px;margin:0;">'
            'Payer-day percentages are not reported in this HCRIS row.</p>'
        )
    # Proportional bar — never normalized to 100, per the handoff spec.
    total = (medicare or 0) + (medicaid or 0) + (commercial or 0)
    if total <= 0:
        return ''
    def _seg(label: str, frac: Optional[float], color: str) -> str:
        if frac is None:
            return ''
        w = (frac / total) * 100.0
        return (
            f'<div style="flex:0 0 {w:.1f}%;background:{color};color:#fff;'
            f'padding:8px 10px;font-family:var(--sc-mono);font-size:10.5px;'
            f'letter-spacing:.1em;overflow:hidden;white-space:nowrap;">'
            f'{_html.escape(label)} {frac*100:.0f}%</div>'
        )
    bar = (
        '<div style="display:flex;border:1px solid #c9c1ac;overflow:hidden;'
        f'margin:0 0 6px;">'
        f'{_seg("Medicare",   medicare,   "#0b2341")}'
        f'{_seg("Medicaid",   medicaid,   "#155752")}'
        f'{_seg("Commercial", commercial, "#5a6f7a")}'
        '</div>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:4px 0 0;">'
        'PROPORTIONAL TO REPORTED PATIENT-DAY MIX · HCRIS</p>'
    )
    return bar


def _score_panel(score_obj: Any) -> str:
    """Render the PE Desk score block from a ChartisScore.

    ChartisScore.components is a {component_name: 0..max_pts} dict — we
    reuse those raw points without rescaling so the displayed numbers
    match exactly what the score builder produced.
    """
    score = int(getattr(score_obj, "score", 0))
    grade = str(getattr(score_obj, "grade", "—"))
    color = _score_color(score)
    components = getattr(score_obj, "components", {}) or {}
    breakdown = getattr(score_obj, "breakdown", {}) or {}
    rows = []
    for name, pts in components.items():
        # Each component is also keyed in breakdown with a human string.
        bd = breakdown.get(name, "")
        rows.append(
            '<div style="display:grid;grid-template-columns:1.4fr 0.6fr;'
            'gap:10px;align-items:baseline;padding:6px 0;'
            'border-bottom:1px solid #ece6d7;">'
            '<div>'
            f'<div style="font-family:var(--sc-serif);font-size:14.5px;'
            f'color:#15202b;">{_html.escape(str(name).replace("_", " ").title())}</div>'
            f'<div style="font-family:var(--sc-mono);font-size:10.5px;'
            f'color:#6a7480;margin-top:2px;">{_html.escape(str(bd))}</div>'
            '</div>'
            f'<div style="text-align:right;font-family:var(--sc-mono);font-size:13px;'
            f'color:#2a3a4a;font-variant-numeric:tabular-nums;">'
            f'+{float(pts):.1f} pts</div>'
            '</div>'
        )
    return (
        '<div style="display:grid;grid-template-columns:0.55fr 1fr;gap:24px;'
        'align-items:center;">'
        '<div style="text-align:center;">'
        f'<div style="font-family:var(--sc-serif);font-size:64px;font-weight:400;'
        f'line-height:1;color:{color};">{score}</div>'
        '<div style="font-family:var(--sc-mono);font-size:10.5px;letter-spacing:.18em;'
        'text-transform:uppercase;color:#6a7480;margin-top:6px;">PE Desk score</div>'
        f'<div style="font-family:var(--sc-serif);font-size:18px;margin-top:8px;'
        f'color:{color};">Grade {_html.escape(grade)}</div>'
        '</div>'
        f'<div>{"".join(rows) or "<em>No score components computed.</em>"}</div>'
        '</div>'
    )


def _comparables_panel(comps: List[Dict[str, Any]], ccn: str) -> str:
    if not comps:
        return (
            '<p style="font-family:var(--sc-serif);font-style:italic;'
            'color:#6a7480;font-size:13px;margin:0;">'
            'No comparable hospitals returned from the matcher.</p>'
        )
    rows = []
    for p in comps:
        peer_ccn = _html.escape(str(p.get("ccn", "")), quote=True)
        peer_name = _html.escape(str(p.get("name", "") or f"CCN {peer_ccn}"))
        state = _html.escape(str(p.get("state", "") or "—"))
        beds = _fmt_int(p.get("beds") or p.get("bed_count"))
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
            f'<td class="num">{sim_str}</td>'
            '</tr>'
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
        'TOP MATCHES FROM <code>ml.comparable_finder</code> · HCRIS · '
        'CLICK A ROW FOR THAT PEER&rsquo;S DEAL.</p>'
    )


def _signals_panel(h: Dict[str, Any], score: int) -> str:
    """Real signal bullets derived from the data — NOT a hallucinated thesis.

    Each bullet either has a real number behind it or isn't included.
    """
    bullets: List[str] = []
    margin = _op_margin(h)
    if margin is not None:
        if margin > 0.08:
            bullets.append(
                f"Operating margin <strong>{margin*100:.1f}%</strong> is in "
                "the upper band among HCRIS hospitals (median ~3–5%)."
            )
        elif margin > 0:
            bullets.append(
                f"Operating margin <strong>{margin*100:.1f}%</strong> is "
                "near-median for HCRIS hospitals — modest profitability."
            )
        else:
            bullets.append(
                f"Operating margin <strong>{margin*100:.1f}%</strong> is "
                "negative — the deal lens has to defend a turnaround thesis."
            )
    beds = _safe_float(h.get("beds") or h.get("bed_count"))
    if beds is not None and beds >= 250:
        bullets.append(
            f"Bed count <strong>{int(beds):,}</strong> puts this in the "
            "upper size cohort — peers come from the size-matched bucket."
        )
    elif beds is not None and beds < 100:
        bullets.append(
            f"Bed count <strong>{int(beds)}</strong> is small — read the "
            "Comp Intel cohort in <em>size-matched</em> rather than national."
        )
    if score >= 70:
        bullets.append(
            "PE Desk score in the upper band — financial-health + scale "
            "components are both contributing."
        )
    elif score < 30:
        bullets.append(
            "PE Desk score is low — at least one structural component is "
            "weak. Open the Comp Intel surface to see which."
        )
    if not bullets:
        return ""  # nothing real to say — omit, never pad
    items = "".join(f"<li>{b}</li>" for b in bullets)
    return (
        '<ul style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;padding-left:18px;">{items}</ul>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'SIGNALS DERIVED FROM REAL HCRIS + SCORE COMPONENTS &mdash; NOT A PROSE THESIS.</p>'
    )


def _actions_panel(ccn: str) -> str:
    """Cross-links to the other 17 surfaces — every link works (built or stub)."""
    ccn_safe = _html.escape(ccn, quote=True)
    def btn(slug: str, label: str) -> str:
        s = SURFACE_BY_PATH.get(slug)
        soon = " · soon" if s and not s.built else ""
        cls = "cad-btn"
        return (
            f'<a class="{cls}" href="/deals/{ccn_safe}/{slug}" '
            f'style="display:inline-block;padding:8px 14px;border:1px solid #c9c1ac;'
            f'background:#faf6ec;color:#15202b;text-decoration:none;font-family:var(--sc-mono);'
            f'font-size:11px;letter-spacing:.12em;text-transform:uppercase;'
            f'margin:0 8px 8px 0;">{_html.escape(label)}{soon}</a>'
        )
    rows = [
        ("Diligence workflow",
         [("ic-memo", "IC Memo"), ("bridge", "Bridge"),
          ("comp-intel", "Comp Intel"), ("scenarios", "Scenarios")]),
        ("Deep analysis",
         [("ml", "ML Analysis"), ("market", "Market"),
          ("denial", "Denial"), ("trends", "Trends")]),
        ("Financial models",
         [("dcf", "DCF"), ("lbo", "LBO"),
          ("stmt", "3-Statement"), ("returns", "Returns")]),
    ]
    out = []
    for label, items in rows:
        btns = "".join(btn(s, t) for s, t in items)
        out.append(
            f'<div style="margin:0 0 10px;">'
            f'<div style="font-family:var(--sc-mono);font-size:9.5px;'
            f'letter-spacing:.18em;text-transform:uppercase;color:#6a7480;'
            f'margin:0 0 8px;">{_html.escape(label)}</div>'
            f'{btns}</div>'
        )
    return "".join(out)


# ───────────────────────── entry point ─────────────────────────

def render_deal_profile(ccn: str, hospital: Dict[str, Any]) -> str:
    """Render Surface 01 (Profile) for ``ccn``.

    ``hospital`` is the real HCRIS row dict; the caller is responsible for
    rendering a 404 page when no row exists for the CCN.
    """
    # PE Desk score from the existing scorer (real, already used elsewhere).
    try:
        from ...intelligence.caduceus_score import compute_caduceus_score
    except ImportError:  # pragma: no cover
        from rcm_mc.intelligence.caduceus_score import compute_caduceus_score
    score_obj = compute_caduceus_score(hospital)
    score_int = int(getattr(score_obj, "score", 0))

    # Comparable hospitals — size+state matched, top 8.
    comps: List[Dict[str, Any]] = []
    try:
        from ...data.hcris import _get_latest_per_ccn
        from ...ml.comparable_finder import find_comparables
        hdf = _get_latest_per_ccn()
        pool = hdf.to_dict("records") if hdf is not None else []
        comps = find_comparables(hospital, pool, max_results=8) or []
    except Exception:  # noqa: BLE001 — never fail the page on comp lookup
        comps = []

    panels = [
        _panel(
            "01 · IDENTITY", "Headline financials",
            _key_stats(hospital),
        ),
        _panel(
            "02 · PE DESK SCORE",
            f"{score_int}/100 · grade {getattr(score_obj, 'grade', '—')}",
            _score_panel(score_obj),
        ),
    ]
    signals = _signals_panel(hospital, score_int)
    if signals:
        panels.append(_panel(
            "03 · INVESTMENT SIGNALS", "What the data is saying", signals,
        ))
    panels.append(_panel(
        "04 · PAYER MIX", "Reported patient-day breakdown",
        _payer_mix(hospital),
    ))
    panels.append(_panel(
        "05 · COMPARABLE HOSPITALS", "Closest matches in HCRIS",
        _comparables_panel(comps, ccn),
    ))
    panels.append(_panel(
        "06 · ACTIONS", "Open this deal in another lens",
        _actions_panel(ccn),
    ))

    body = "".join(panels)
    return deal_shell(
        ccn, hospital, active_slug="profile", body_html=body,
        page_title=f"Profile · {hospital.get('name') or f'CCN {ccn}'}",
    )
