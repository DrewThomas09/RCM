"""Partner Review — /partner-brain/review.

Renders ``rcm_mc.pe_intelligence.partner_review(packet)`` as an
HTML page. This is the single entry point that surfaces the core
31 wired pe_intelligence modules (reasonableness bands, heuristics,
red flags, narrative composition, regime/posture/stress/white-space/
investability enrichment).

Phase 0 behavior:
- If ``?deal_id=X`` resolves to a cached packet in ``analysis_runs``,
  render the real partner review.
- Otherwise render a **demo review** built from a seeded
  ``HeuristicContext`` so the page always shows something useful.
  A banner explains which mode was used.

Later phases will wire a real deal picker once the PE Brain is
integrated into the analysis workbench.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional, Tuple

from rcm_mc.ui._chartis_kit import (
    P,
    chartis_shell,
    ck_kpi_block,
    ck_section_header,
)


# ── Seeded demo context ────────────────────────────────────────────

_DEMO_DEAL_ID = "demo_acme_regional"
_DEMO_DEAL_NAME = "Acme Regional Health (demo)"


def _build_demo_context():
    """Plausible mid-market acute-care deal for the demo review."""
    from rcm_mc.pe_intelligence.heuristics import HeuristicContext

    return HeuristicContext(
        payer_mix={"medicare": 0.40, "medicaid": 0.18,
                   "commercial": 0.35, "self_pay": 0.07},
        ebitda_m=42.0,
        revenue_m=410.0,
        bed_count=420,
        hospital_type="acute_care",
        state="IL",
        urban_rural="urban",
        teaching_status="non_teaching",
        denial_rate=0.11,
        final_writeoff_rate=0.055,
        days_in_ar=55.0,
        clean_claim_rate=0.88,
        case_mix_index=1.62,
        ebitda_margin=0.102,
        exit_multiple=12.0,
        entry_multiple=10.0,
        hold_years=5.0,
        projected_irr=0.22,
        projected_moic=2.6,
        denial_improvement_bps_per_yr=140.0,
        ar_reduction_days_per_yr=3.5,
        revenue_growth_pct_per_yr=0.055,
        margin_expansion_bps_per_yr=120.0,
        deal_structure="FFS",
        leverage_multiple=5.5,
        covenant_headroom_pct=0.18,
        data_coverage_pct=0.72,
        has_case_mix_data=True,
    )


# ── Rendering helpers ─────────────────────────────────────────────

_REC_COLORS = {
    "STRONG_PROCEED": P["positive"],
    "PROCEED": P["positive"],
    "PROCEED_WITH_CAVEATS": P["warning"],
    "PASS": P["critical"],
}

_SEVERITY_COLORS = {
    "CRITICAL": P["critical"],
    "HIGH": P["negative"],
    "MEDIUM": P["warning"],
    "LOW": P["text_dim"],
}

_VERDICT_COLORS = {
    "IN_BAND": P["positive"],
    "STRETCH": P["warning"],
    "OUT_OF_BAND": P["negative"],
    "IMPLAUSIBLE": P["critical"],
    "UNKNOWN": P["text_dim"],
}


def _rec_badge(recommendation: str) -> str:
    color = _REC_COLORS.get(recommendation, P["text_dim"])
    label = recommendation.replace("_", " ").title()
    return (
        f'<span style="display:inline-block;padding:6px 14px;font-size:12px;'
        f'font-weight:700;letter-spacing:0.08em;color:{color};'
        f'border:1px solid {color};border-radius:2px;'
        f'font-family:JetBrains Mono,monospace">'
        f'{_html.escape(label)}</span>'
    )


def _severity_badge(severity: str) -> str:
    color = _SEVERITY_COLORS.get(severity, P["text_dim"])
    return (
        f'<span style="font-size:9px;font-family:JetBrains Mono,monospace;'
        f"color:{color};border:1px solid {color};padding:2px 6px;"
        f'letter-spacing:0.08em;border-radius:2px">{_html.escape(severity)}</span>'
    )


def _verdict_badge(verdict: str) -> str:
    color = _VERDICT_COLORS.get(verdict, P["text_dim"])
    return (
        f'<span style="font-size:9px;font-family:JetBrains Mono,monospace;'
        f"color:{color};border:1px solid {color};padding:2px 6px;"
        f'letter-spacing:0.08em;border-radius:2px">{_html.escape(verdict)}</span>'
    )


def _narrative_block(n: Any) -> str:
    """Render a NarrativeBlock object."""
    text = P["text"]
    text_dim = P["text_dim"]
    panel = P["panel"]
    border = P["border"]

    headline = getattr(n, "headline", "") or ""
    bull = getattr(n, "bull_case", "") or ""
    bear = getattr(n, "bear_case", "") or ""
    questions = getattr(n, "key_questions", []) or []
    ic_para = getattr(n, "ic_memo_paragraph", "") or ""
    rationale = getattr(n, "recommendation_rationale", "") or ""

    q_items = "".join(
        f'<li style="font-size:11px;color:{text_dim};line-height:1.6;margin:4px 0">'
        f"{_html.escape(str(q))}</li>"
        for q in questions
    )

    panel_style = (
        f"background:{panel};border:1px solid {border};padding:16px;"
        f"margin-bottom:12px"
    )
    label_style = (
        f"font-size:10px;color:{text_dim};letter-spacing:0.08em;"
        f"text-transform:uppercase;margin-bottom:6px;font-weight:600"
    )
    body_style = f"font-size:12px;color:{text};line-height:1.6"

    parts = []
    if headline:
        parts.append(
            f'<div style="{panel_style}">'
            f'<div style="{label_style}">Headline</div>'
            f'<div style="{body_style};font-weight:600">{_html.escape(headline)}</div>'
            f'</div>'
        )
    if rationale:
        parts.append(
            f'<div style="{panel_style}">'
            f'<div style="{label_style}">Why this recommendation</div>'
            f'<div style="{body_style}">{_html.escape(rationale)}</div>'
            f'</div>'
        )
    if bull or bear:
        parts.append(
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px">'
            f'<div style="{panel_style};margin-bottom:0">'
            f'<div style="{label_style};color:{P["positive"]}">Bull case</div>'
            f'<div style="{body_style}">{_html.escape(bull or "—")}</div>'
            f'</div>'
            f'<div style="{panel_style};margin-bottom:0">'
            f'<div style="{label_style};color:{P["negative"]}">Bear case</div>'
            f'<div style="{body_style}">{_html.escape(bear or "—")}</div>'
            f'</div>'
            f'</div>'
        )
    if q_items:
        parts.append(
            f'<div style="{panel_style}">'
            f'<div style="{label_style}">Key diligence questions</div>'
            f'<ul style="margin:4px 0;padding-left:20px">{q_items}</ul>'
            f'</div>'
        )
    if ic_para:
        parts.append(
            f'<div style="{panel_style}">'
            f'<div style="{label_style}">IC memo paragraph</div>'
            f'<div style="{body_style};font-style:italic">{_html.escape(ic_para)}</div>'
            f'</div>'
        )
    return "".join(parts)


def _heuristics_table(hits: List[Any]) -> str:
    if not hits:
        return (
            f'<div style="font-size:11px;color:{P["text_dim"]};padding:16px;'
            f'background:{P["panel"]};border:1px solid {P["border"]}">'
            f"No heuristic hits. All rules passed on this context.</div>"
        )

    bg = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]
    acc = P["accent"]

    cols = [
        ("Severity", "center", 80),
        ("Category", "center", 100),
        ("Finding", "left", 0),
        ("Partner voice", "left", 0),
    ]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em'
        f'{";width:" + str(w) + "px" if w else ""}">{c}</th>'
        for c, a, w in cols
    )

    rows = []
    for i, h in enumerate(hits):
        rb = panel_alt if i % 2 == 0 else bg
        sev = getattr(h, "severity", "") or ""
        cat = getattr(h, "category", "") or ""
        finding = getattr(h, "finding", "") or ""
        voice = getattr(h, "partner_voice", "") or ""
        title = getattr(h, "title", "") or ""

        finding_html = (
            f'<div style="font-size:11px;color:{text};font-weight:600">{_html.escape(title)}</div>'
            f'<div style="font-size:10px;color:{text_dim};margin-top:3px;line-height:1.5">'
            f"{_html.escape(finding)}</div>"
        )
        voice_html = (
            f'<div style="font-size:11px;color:{acc};font-style:italic;line-height:1.5">'
            f'"{_html.escape(voice)}"</div>'
        )

        rows.append(
            f'<tr style="background:{rb};vertical-align:top">'
            f'<td style="text-align:center;padding:8px 10px">{_severity_badge(sev)}</td>'
            f'<td style="text-align:center;padding:8px 10px;font-family:JetBrains Mono,monospace;'
            f'font-size:10px;color:{text_dim}">{_html.escape(cat)}</td>'
            f'<td style="padding:8px 10px">{finding_html}</td>'
            f'<td style="padding:8px 10px">{voice_html}</td>'
            f'</tr>'
        )

    return (
        f'<div style="overflow-x:auto;margin-top:8px">'
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def _bands_table(bands: List[Any]) -> str:
    if not bands:
        return (
            f'<div style="font-size:11px;color:{P["text_dim"]};padding:16px;'
            f'background:{P["panel"]};border:1px solid {P["border"]}">'
            f"No reasonableness checks executed.</div>"
        )

    bg = P["panel"]
    panel_alt = P["panel_alt"]
    border = P["border"]
    text = P["text"]
    text_dim = P["text_dim"]

    cols = [
        ("Verdict", "center", 120),
        ("Metric", "left", 180),
        ("Observed", "right", 100),
        ("Rationale", "left", 0),
    ]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};'
        f'font-size:10px;color:{text_dim};letter-spacing:0.05em'
        f'{";width:" + str(w) + "px" if w else ""}">{c}</th>'
        for c, a, w in cols
    )

    rows = []
    for i, b in enumerate(bands):
        rb = panel_alt if i % 2 == 0 else bg
        verdict = getattr(b, "verdict", "") or ""
        metric = getattr(b, "metric", "") or ""
        observed = getattr(b, "observed", None)
        rationale = getattr(b, "rationale", "") or ""
        partner_note = getattr(b, "partner_note", "") or ""

        obs_str = (
            f"{observed:.3f}" if isinstance(observed, float)
            else (str(observed) if observed is not None else "—")
        )

        rationale_html = (
            f'<div style="font-size:11px;color:{text};line-height:1.5">{_html.escape(rationale)}</div>'
        )
        if partner_note:
            rationale_html += (
                f'<div style="font-size:10px;color:{text_dim};font-style:italic;'
                f'margin-top:4px;line-height:1.5">{_html.escape(partner_note)}</div>'
            )

        rows.append(
            f'<tr style="background:{rb};vertical-align:top">'
            f'<td style="text-align:center;padding:8px 10px">{_verdict_badge(verdict)}</td>'
            f'<td style="padding:8px 10px;font-family:JetBrains Mono,monospace;'
            f'font-size:11px;color:{text}">{_html.escape(metric)}</td>'
            f'<td style="text-align:right;padding:8px 10px;font-variant-numeric:tabular-nums;'
            f'font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">'
            f"{_html.escape(obs_str)}</td>"
            f'<td style="padding:8px 10px">{rationale_html}</td>'
            f'</tr>'
        )

    return (
        f'<div style="overflow-x:auto;margin-top:8px">'
        f'<table style="width:100%;border-collapse:collapse;font-size:11px">'
        f'<thead><tr style="background:{bg}">{ths}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def _context_summary_block(ctx: Dict[str, Any]) -> str:
    if not ctx:
        return ""
    text = P["text"]
    text_dim = P["text_dim"]
    panel = P["panel"]
    border = P["border"]

    items = []
    for k, v in sorted(ctx.items()):
        if v is None or v == "":
            continue
        if isinstance(v, float):
            v_str = f"{v:.3f}"
        elif isinstance(v, dict):
            v_str = ", ".join(
                f"{kk} {vv*100:.0f}%" if isinstance(vv, (int, float)) else f"{kk}: {vv}"
                for kk, vv in v.items()
            )
        else:
            v_str = str(v)
        items.append(
            f'<div style="display:flex;justify-content:space-between;'
            f'padding:4px 0;border-bottom:1px dashed {border};gap:12px">'
            f'<span style="font-size:10px;color:{text_dim};'
            f'font-family:JetBrains Mono,monospace">{_html.escape(k)}</span>'
            f'<span style="font-size:11px;color:{text};'
            f"font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;"
            f'text-align:right">{_html.escape(v_str)}</span>'
            f'</div>'
        )

    return (
        f'<div style="background:{panel};border:1px solid {border};padding:14px">'
        f'{"".join(items)}</div>'
    )


# ── Main entry ───────────────────────────────────────────────────

def _try_load_packet(deal_id: str) -> Optional[Any]:
    """Best-effort load of a cached packet by deal_id. Returns None on
    any error so the page can fall back to the demo."""
    if not deal_id:
        return None
    try:
        from rcm_mc.portfolio.store import PortfolioStore
        from rcm_mc.analysis.analysis_store import get_or_build_packet
        from rcm_mc.config import Config  # type: ignore

        # Resolve the default DB path like the server does.
        try:
            cfg = Config.load()
            db_path = getattr(cfg, "db_path", None)
        except Exception:
            db_path = None
        if not db_path:
            return None
        store = PortfolioStore(db_path)
        return get_or_build_packet(store, deal_id, force_rebuild=False)
    except Exception:  # noqa: BLE001 — UI must never 500 on demo path
        return None


def render_partner_review(qp: Dict[str, str] | None = None) -> str:
    qp = qp or {}
    deal_id = qp.get("deal_id", "").strip()

    # Try real packet first, fall back to demo context.
    review = None
    used_demo = False
    packet = _try_load_packet(deal_id) if deal_id else None

    try:
        from rcm_mc.pe_intelligence import partner_review as _pr
        from rcm_mc.pe_intelligence.partner_review import (
            partner_review_from_context,
        )
        if packet is not None:
            review = _pr(packet)
        else:
            used_demo = True
            ctx = _build_demo_context()
            review = partner_review_from_context(
                ctx, deal_id=_DEMO_DEAL_ID, deal_name=_DEMO_DEAL_NAME,
            )
    except Exception as exc:  # noqa: BLE001
        # Absolute last resort — show the error surface instead of 500.
        text = P["text"]
        critical = P["critical"]
        err = _html.escape(str(exc))
        body = (
            f'<div style="padding:40px;max-width:900px;margin:0 auto">'
            f'<h1 style="color:{text};font-size:18px">Partner Review error</h1>'
            f'<pre style="color:{critical};font-size:11px;margin-top:12px">{err}</pre>'
            f'</div>'
        )
        return chartis_shell(body=body, title="Partner Review")

    # Compose the page.
    text = P["text"]
    text_dim = P["text_dim"]
    panel = P["panel"]
    border = P["border"]
    pos = P["positive"]
    warn = P["warning"]

    rec = review.narrative.recommendation if review.narrative else "UNKNOWN"
    sev_counts = review.severity_counts()
    band_counts = review.band_counts()
    gen_at = (
        review.generated_at.isoformat() if review.generated_at else "—"
    )

    kpi_strip = (
        ck_kpi_block("Recommendation", _rec_badge(rec).replace("<", "&lt;").replace(">", "&gt;"), "", "")
        + ck_kpi_block("Heuristic hits", str(len(review.heuristic_hits)), "", "")
        + ck_kpi_block("Critical", str(sev_counts.get("CRITICAL", 0)), "", "")
        + ck_kpi_block("High", str(sev_counts.get("HIGH", 0)), "", "")
        + ck_kpi_block("Reasonableness checks", str(len(review.reasonableness_checks)), "", "")
        + ck_kpi_block("Out of band", str(band_counts.get("OUT_OF_BAND", 0) + band_counts.get("IMPLAUSIBLE", 0)), "", "")
    )

    # The ck_kpi_block HTML-escaped our badge; render the badge separately above the strip.
    rec_banner = (
        f'<div style="padding:14px 20px;margin-bottom:16px;background:{panel};'
        f'border:1px solid {border};display:flex;align-items:center;gap:14px">'
        f'<span style="font-size:10px;color:{text_dim};letter-spacing:0.08em;'
        f'text-transform:uppercase">Recommendation</span>{_rec_badge(rec)}'
        f'<span style="font-size:11px;color:{text_dim};margin-left:auto">'
        f"deal: <span style=\"color:{text};font-family:JetBrains Mono,monospace\">"
        f"{_html.escape(review.deal_name or review.deal_id or '—')}</span>"
        f' · generated {_html.escape(gen_at)}</span>'
        f'</div>'
    )

    demo_banner = ""
    if used_demo:
        demo_banner = (
            f'<div style="padding:10px 14px;margin-bottom:16px;background:{panel};'
            f"border:1px solid {warn};border-left:3px solid {warn};"
            f'font-size:11px;color:{text_dim};line-height:1.5">'
            f'<span style="color:{warn};font-weight:700;letter-spacing:0.05em">'
            f"DEMO DATA:</span> "
            f"no packet cached for "
            f'<code style="color:{text}">{_html.escape(deal_id or "(no deal_id supplied)")}</code>. '
            f"Review rendered from seeded mid-market acute-care context. "
            f"Pass <code>?deal_id=X</code> where X has a cached "
            f"<code>analysis_runs</code> row to render a real review."
            f'</div>'
        )

    narrative_html = _narrative_block(review.narrative)
    bands_html = _bands_table(review.reasonableness_checks)
    hits_html = _heuristics_table(
        sorted(
            review.heuristic_hits,
            key=lambda h: getattr(h, "severity_rank", lambda: 0)(),
            reverse=True,
        )
    )
    ctx_html = _context_summary_block(review.context_summary or {})

    body = (
        f'<div style="padding:20px;max-width:1400px;margin:0 auto">'
        f'<div style="margin-bottom:16px">'
        f'<a href="/partner-brain" style="color:{P["accent"]};font-size:11px;text-decoration:none">'
        f'← Partner Brain hub</a>'
        f'</div>'
        f'<h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">'
        f'Partner Review</h1>'
        f'<p style="font-size:12px;color:{text_dim};margin-top:4px;line-height:1.5">'
        f"Reasonableness bands + heuristic rules + partner-voice narrative, "
        f"composed from <code>rcm_mc.pe_intelligence.partner_review()</code>.</p>"
        f'{demo_banner}'
        f'{rec_banner}'
        f'<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px">'
        f'{kpi_strip}</div>'
        f'{ck_section_header("Narrative", "partner-voice composition", None)}'
        f'<div style="margin-top:10px">{narrative_html}</div>'
        f'{ck_section_header("Heuristic hits", "named PE rules fired on this context", len(review.heuristic_hits))}'
        f'{hits_html}'
        f'<div style="margin-top:30px"></div>'
        f'{ck_section_header("Reasonableness bands", "IRR / margin / lever realizability vs peer bands", len(review.reasonableness_checks))}'
        f'{bands_html}'
        f'<div style="margin-top:30px"></div>'
        f'{ck_section_header("Context summary", "inputs the review saw", None)}'
        f'<div style="margin-top:10px">{ctx_html}</div>'
        f'</div>'
    )

    title = f"Partner Review · {review.deal_name or review.deal_id or 'demo'}"
    return chartis_shell(body=body, title=title, active_nav="/partner-brain")
