"""Per-deal Partner Review — /deal/<id>/partner-review.

This is the single biggest integration point with the PE Intelligence
Brain. Loads the cached DealAnalysisPacket for the deal, runs
``rcm_mc.pe_intelligence.partner_review.partner_review(packet)``, and
renders every field of the returned PartnerReview:

  - IC recommendation banner (PASS / PROCEED_WITH_CAVEATS /
    PROCEED / STRONG_PROCEED) with rationale
  - Partner-voice headline, bull case, bear case, IC-memo paragraph
  - Three-things-that-would-change-my-mind (key_questions)
  - Reasonableness band grid (IN_BAND / STRETCH / OUT_OF_BAND /
    IMPLAUSIBLE counts + per-check detail)
  - Heuristic hits (critical / high / medium / low severity)
  - Investability score, regime classification, market structure
    (HHI / CR3), stress grid, white-space adjacencies

If the packet is missing fields the brain needs, partner_review()
returns an UNKNOWN-verdict review rather than raising — we still
render the page but show a "partial data" banner.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

from .._chartis_kit import (
    P,
    chartis_shell,
    ck_kpi_block,
    ck_section_header,
)
from ._helpers import related_views_panel
from ._sanity import REGISTRY as _METRIC_REGISTRY, render_number


_REC_COLORS = {
    "PASS": P["negative"],
    "PROCEED_WITH_CAVEATS": P["warning"],
    "PROCEED": P["text"],
    "STRONG_PROCEED": P["positive"],
}

_VERDICT_COLORS = {
    "IN_BAND": P["positive"],
    "STRETCH": P["warning"],
    "OUT_OF_BAND": P["negative"],
    "IMPLAUSIBLE": P["critical"],
    "UNKNOWN": P["text_faint"],
}

_SEV_COLORS = {
    "CRITICAL": P["critical"],
    "HIGH": P["negative"],
    "MEDIUM": P["warning"],
    "LOW": P["text_dim"],
}


def _panel(title: str, body: str, *, code: str = "") -> str:
    code_html = (
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'letter-spacing:0.12em;color:{P["text_faint"]};'
        f'margin-left:8px;">{_html.escape(code)}</span>'
        if code else ""
    )
    return (
        f'<div class="ck-panel">'
        f'<div class="ck-panel-title">{_html.escape(title)}{code_html}</div>'
        f'<div style="padding:12px 14px;">{body}</div>'
        f'</div>'
    )


def _empty_paragraph(msg: str) -> str:
    return (
        f'<p style="color:{P["text_faint"]};font-size:11px;font-style:italic;">'
        f'{_html.escape(msg)}</p>'
    )


def _banner_insufficient(missing: List[str], deal_id: str) -> str:
    missing_list = ", ".join(_html.escape(m) for m in missing) if missing else "—"
    return (
        f'<div style="background:rgba(239,68,68,0.10);border:1px solid {P["negative"]};'
        f'border-radius:3px;padding:12px 14px;margin-bottom:14px;">'
        f'<div style="font-family:var(--ck-mono);font-size:9.5px;'
        f'color:{P["negative"]};letter-spacing:0.12em;margin-bottom:4px;">'
        f'INSUFFICIENT DATA FOR PARTNER REVIEW</div>'
        f'<div style="color:{P["text"]};font-size:12px;margin-bottom:6px;">'
        f'The PE intelligence brain could not run on this deal. '
        f'Missing: <span style="font-family:var(--ck-mono);color:{P["warning"]};">'
        f'{missing_list}</span></div>'
        f'<div style="color:{P["text_dim"]};font-size:11px;">'
        f'Open the <a href="/analysis/{_html.escape(deal_id)}" '
        f'style="color:{P["accent"]};">analysis workbench</a> to finish building '
        f'the packet, or <a href="/new-deal" style="color:{P["accent"]};">import '
        f'more data</a>.</div>'
        f'</div>'
    )


def _recommendation_banner(review: Any) -> str:
    rec = str(getattr(review.narrative, "recommendation", "") or "—")
    headline = str(getattr(review.narrative, "headline", "") or "")
    rationale = str(getattr(review.narrative, "recommendation_rationale", "") or "")
    col = _REC_COLORS.get(rec, P["text_dim"])
    return (
        f'<div style="background:{P["panel"]};border-left:4px solid {col};'
        f'border:1px solid {P["border"]};border-left-width:4px;'
        f'border-radius:3px;padding:14px 18px;margin-bottom:14px;">'
        f'<div style="display:flex;gap:12px;align-items:baseline;">'
        f'<span style="font-family:var(--ck-mono);font-size:9px;'
        f'color:{P["text_faint"]};letter-spacing:0.15em;">IC VERDICT</span>'
        f'<span style="font-family:var(--ck-mono);font-size:16px;font-weight:700;'
        f'letter-spacing:0.08em;color:{col};">{_html.escape(rec)}</span>'
        f'</div>'
        f'<div style="color:{P["text"]};font-size:13px;margin-top:8px;'
        f'line-height:1.55;">{_html.escape(headline)}</div>'
        + (
            f'<div style="color:{P["text_dim"]};font-size:11.5px;margin-top:6px;'
            f'line-height:1.55;">{_html.escape(rationale)}</div>' if rationale else ""
        )
        + f'</div>'
    )


def _kpi_strip(review: Any) -> str:
    sev = review.severity_counts()
    bands = review.band_counts()
    rec = review.narrative.recommendation or "—"
    fundable = "YES" if review.is_fundable() else "NO"

    inv = review.investability or {}
    inv_score = None
    for key in ("composite_score", "score", "investability_score"):
        if isinstance(inv, dict) and key in inv and inv[key] is not None:
            try:
                inv_score = float(inv[key])
                break
            except (TypeError, ValueError):
                continue

    critical = sev.get("CRITICAL", 0)
    high = sev.get("HIGH", 0)
    stretch = bands.get("STRETCH", 0)
    oob = bands.get("OUT_OF_BAND", 0) + bands.get("IMPLAUSIBLE", 0)

    inv_val = render_number(inv_score, "investability_score")

    tiles = (
        ck_kpi_block("Verdict", _html.escape(rec), "")
        + ck_kpi_block("Fundable", fundable, "narrative")
        + ck_kpi_block("Critical Flags", str(critical), f"{high} high")
        + ck_kpi_block("Bands Out", str(oob), f"{stretch} stretch")
        + ck_kpi_block("Investability", inv_val, "composite 0-100")
    )
    return f'<div class="ck-kpi-grid">{tiles}</div>'


def _narrative_panel(review: Any) -> str:
    n = review.narrative
    bull = str(getattr(n, "bull_case", "") or "").strip()
    bear = str(getattr(n, "bear_case", "") or "").strip()
    memo = str(getattr(n, "ic_memo_paragraph", "") or "").strip()

    col_bull = (
        f'<div style="flex:1;min-width:0;">'
        f'<div style="font-family:var(--ck-mono);font-size:9px;letter-spacing:0.12em;'
        f'color:{P["positive"]};margin-bottom:4px;">BULL CASE</div>'
        f'<p style="color:{P["text"]};font-size:11.5px;line-height:1.55;">'
        f'{_html.escape(bull) if bull else "—"}</p></div>'
    )
    col_bear = (
        f'<div style="flex:1;min-width:0;">'
        f'<div style="font-family:var(--ck-mono);font-size:9px;letter-spacing:0.12em;'
        f'color:{P["negative"]};margin-bottom:4px;">BEAR CASE</div>'
        f'<p style="color:{P["text"]};font-size:11.5px;line-height:1.55;">'
        f'{_html.escape(bear) if bear else "—"}</p></div>'
    )
    memo_block = ""
    if memo:
        memo_block = (
            f'<div style="margin-top:12px;padding-top:10px;'
            f'border-top:1px solid {P["border_dim"]};">'
            f'<div style="font-family:var(--ck-mono);font-size:9px;'
            f'letter-spacing:0.12em;color:{P["text_faint"]};margin-bottom:4px;">'
            f'IC MEMO PARAGRAPH</div>'
            f'<p style="color:{P["text_dim"]};font-size:11.5px;line-height:1.6;'
            f'font-style:italic;">{_html.escape(memo)}</p></div>'
        )
    return (
        f'<div style="display:flex;gap:18px;">'
        f'{col_bull}{col_bear}</div>{memo_block}'
    )


def _change_my_mind(review: Any) -> str:
    questions = getattr(review.narrative, "key_questions", None) or []
    if not questions:
        return _empty_paragraph(
            "No flip signals — the brain could not derive change-my-mind questions "
            "from this packet."
        )
    items = []
    for i, q in enumerate(questions[:5], start=1):
        items.append(
            f'<li style="padding:5px 0;color:{P["text"]};font-size:11.5px;'
            f'line-height:1.55;"><span style="font-family:var(--ck-mono);'
            f'color:{P["accent"]};font-weight:700;margin-right:6px;">'
            f'{i}.</span>{_html.escape(str(q))}</li>'
        )
    return f'<ol style="list-style:none;padding:0;margin:0;">{"".join(items)}</ol>'


def _bands_table(review: Any) -> str:
    checks = list(review.reasonableness_checks or [])
    if not checks:
        return _empty_paragraph("No reasonableness bands ran.")
    rows = []
    for b in checks:
        verdict = str(getattr(b, "verdict", "UNKNOWN") or "UNKNOWN")
        col = _VERDICT_COLORS.get(verdict, P["text_faint"])
        metric_raw = str(getattr(b, "metric", "—"))
        metric = _html.escape(metric_raw)
        observed = getattr(b, "observed", None)
        # Route the observed value through the sanity guard if the
        # BandCheck metric matches a known REGISTRY entry. If not
        # (e.g. "lever_realizability"), fall back to the old :.2f.
        if metric_raw in _METRIC_REGISTRY:
            obs_str = render_number(observed, metric_raw)
        else:
            obs_str = (
                f'{observed:.2f}' if isinstance(observed, (int, float))
                else _html.escape(str(observed) if observed is not None else "—")
            )
        band = getattr(b, "band", None)
        band_str = ""
        if isinstance(band, (list, tuple)) and len(band) == 2:
            lo, hi = band
            try:
                band_str = f'[{float(lo):.2f}, {float(hi):.2f}]'
            except (TypeError, ValueError):
                band_str = "—"
        elif band is not None:
            band_str = _html.escape(str(band))
        else:
            band_str = "—"
        note = _html.escape(str(getattr(b, "partner_note", "") or ""))
        rationale = _html.escape(str(getattr(b, "rationale", "") or ""))
        rows.append(
            f'<tr>'
            f'<td style="font-family:var(--ck-mono);color:{P["text"]};'
            f'font-size:11px;">{metric}</td>'
            f'<td style="font-family:var(--ck-mono);color:{P["text"]};'
            f'font-size:11px;font-variant-numeric:tabular-nums;text-align:right;">'
            f'{obs_str}</td>'
            f'<td style="font-family:var(--ck-mono);color:{P["text_dim"]};'
            f'font-size:10.5px;text-align:right;">{band_str}</td>'
            f'<td><span class="ck-sig" style="color:{col};'
            f'border:1px solid {col};background:rgba(255,255,255,0.02);">'
            f'{_html.escape(verdict)}</span></td>'
            f'<td style="color:{P["text_dim"]};font-size:11px;'
            f'white-space:normal;line-height:1.45;">{note or rationale or "—"}</td>'
            f'</tr>'
        )
    return (
        f'<div class="ck-table-wrap"><table class="ck-table">'
        f'<thead><tr>'
        f'<th>Metric</th><th class="num">Observed</th><th class="num">Band</th>'
        f'<th>Verdict</th><th>Partner Note</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    )


def _hits_table(review: Any, *, severities: Optional[List[str]] = None) -> str:
    hits = list(review.heuristic_hits or [])
    if severities:
        hits = [h for h in hits if str(getattr(h, "severity", "")) in severities]
    if not hits:
        return _empty_paragraph("No heuristic hits at the requested severities.")
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    hits_sorted = sorted(hits, key=lambda h: order.get(str(h.severity), 9))
    rows = []
    for h in hits_sorted:
        sev = str(getattr(h, "severity", "LOW"))
        col = _SEV_COLORS.get(sev, P["text_dim"])
        title = _html.escape(str(getattr(h, "title", "—")))
        finding = _html.escape(str(getattr(h, "finding", "") or ""))
        voice = _html.escape(str(getattr(h, "partner_voice", "") or ""))
        category = _html.escape(str(getattr(h, "category", "") or ""))
        remediation = _html.escape(str(getattr(h, "remediation", "") or ""))
        trigger = getattr(h, "trigger_metrics", None) or []
        trig_str = _html.escape(", ".join(str(t) for t in trigger))
        rows.append(
            f'<tr>'
            f'<td><span class="ck-sig" style="color:{col};border:1px solid {col};'
            f'background:rgba(255,255,255,0.02);">{_html.escape(sev)}</span></td>'
            f'<td style="color:{P["text_faint"]};font-family:var(--ck-mono);'
            f'font-size:10px;">{category}</td>'
            f'<td style="color:{P["text"]};font-size:11px;font-weight:600;">{title}</td>'
            f'<td style="color:{P["text_dim"]};font-size:11px;line-height:1.5;'
            f'white-space:normal;">{finding}'
            + (
                f'<div style="color:{P["text_faint"]};font-style:italic;margin-top:3px;'
                f'font-size:10.5px;">&ldquo;{voice}&rdquo;</div>' if voice else ""
            )
            + (
                f'<div style="color:{P["warning"]};margin-top:3px;font-size:10.5px;">'
                f'Remediation: {remediation}</div>' if remediation else ""
            )
            + f'</td>'
            f'<td style="font-family:var(--ck-mono);color:{P["text_faint"]};'
            f'font-size:10px;">{trig_str}</td>'
            f'</tr>'
        )
    return (
        f'<div class="ck-table-wrap"><table class="ck-table">'
        f'<thead><tr>'
        f'<th style="width:90px;">Severity</th><th style="width:120px;">Category</th>'
        f'<th>Title</th><th>Finding</th><th>Triggered By</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    )


def _secondary_analytics(review: Any) -> str:
    """Render the six enrichment sections — each is a {label: value} dict."""
    sections: List[str] = []

    def _as_dict(x: Any) -> Dict[str, Any]:
        if isinstance(x, dict):
            return x
        return {}

    # Map secondary-analytics dict keys to REGISTRY metric names so
    # render_number can guard the right range. Keys not in this map
    # fall back to generic float formatting.
    _KEY_METRIC = {
        "hhi": "hhi",
        "cr3": "cr3",
        "cr5": "cr5",
        "top_player_share": "market_share",
        "base_moic": "moic",
        "bear_moic": "moic",
        "bull_moic": "moic",
        "base_irr": "irr",
        "bear_irr": "irr",
        "bull_irr": "irr",
        "current_margin": "ebitda_margin",
        "peer_median_margin": "ebitda_margin",
        "composite_score": "investability_score",
        "score": "investability_score",
        "investability_score": "investability_score",
        "confidence": "cr3",  # reuse 0-1 range check
    }

    def _mini_block(title: str, data: Dict[str, Any], fields: List[str]) -> str:
        if not data or data.get("error"):
            err = data.get("error") if isinstance(data, dict) else None
            if err:
                body = _empty_paragraph(str(err))
            else:
                body = _empty_paragraph("No output (missing packet inputs).")
        else:
            items = []
            shown_any = False
            for key in fields:
                val = data.get(key)
                if val is None:
                    continue
                shown_any = True
                metric = _KEY_METRIC.get(key)
                if metric:
                    val_html = render_number(val, metric)
                elif isinstance(val, float):
                    val_str = f"{val:.3f}" if abs(val) < 10 else f"{val:,.2f}"
                    val_html = (
                        f'<span style="color:{P["text"]};font-family:var(--ck-mono);'
                        f'font-variant-numeric:tabular-nums;">{val_str}</span>'
                    )
                else:
                    val_html = (
                        f'<span style="color:{P["text"]};font-family:var(--ck-mono);">'
                        f'{_html.escape(str(val))}</span>'
                    )
                items.append(
                    f'<div style="display:flex;gap:10px;padding:3px 0;'
                    f'border-bottom:1px solid {P["border_dim"]};font-size:11px;">'
                    f'<span style="color:{P["text_faint"]};font-family:var(--ck-mono);'
                    f'font-size:10px;width:150px;">{_html.escape(key)}</span>'
                    f'{val_html}'
                    f'</div>'
                )
            if not shown_any:
                note = data.get("note") or data.get("partner_note")
                if note:
                    items.append(
                        f'<p style="color:{P["text_dim"]};font-size:11px;'
                        f'font-style:italic;">{_html.escape(str(note))}</p>'
                    )
                else:
                    items.append(_empty_paragraph("No scored fields in this section."))
            body = "".join(items)
        return _panel(title, body, code="ANX")

    regime = _as_dict(review.regime)
    market = _as_dict(review.market_structure)
    posture = _as_dict(review.operating_posture)
    stress = _as_dict(review.stress_scenarios)
    ws = _as_dict(review.white_space)
    inv = _as_dict(review.investability)

    sections.append(_mini_block(
        "Regime Classifier", regime,
        ["regime", "confidence", "revenue_cagr_3yr", "ebitda_cagr_3yr",
         "current_margin", "peer_median_margin", "partner_note"],
    ))
    sections.append(_mini_block(
        "Market Structure", market,
        ["hhi", "cr3", "cr5", "concentration_band", "top_player_share",
         "partner_note", "note"],
    ))
    sections.append(_mini_block(
        "Operating Posture", posture,
        ["posture", "posture_score", "dominant_theme", "partner_note"],
    ))
    sections.append(_mini_block(
        "Stress Scenarios", stress,
        ["base_moic", "bear_moic", "bull_moic", "base_irr", "bear_irr",
         "bull_irr", "covenant_breach_risk", "partner_note"],
    ))
    sections.append(_mini_block(
        "White Space", ws,
        ["top_state_opportunity", "top_segment_opportunity",
         "top_channel_opportunity", "adjacency_count", "partner_note"],
    ))
    sections.append(_mini_block(
        "Investability Score", inv,
        ["composite_score", "score", "investability_score", "band",
         "sub_scores", "partner_note"],
    ))
    return (
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">'
        + "".join(sections)
        + f'</div>'
    )


def render_partner_review(
    packet: Any,
    deal_id: str,
    *,
    deal_name: str = "",
    error: Optional[str] = None,
    missing_fields: Optional[List[str]] = None,
    current_user: Optional[str] = None,
) -> str:
    """Render a partner-review page for a deal.

    Called from server.py after ``partner_review(packet)`` has been run
    (or after failing to run). If ``error`` is set, render the degraded
    page. Otherwise pass the PartnerReview in via ``packet`` as the
    computed review object.
    """
    deal_label = deal_name or deal_id
    header_links = (
        f'<div style="margin-bottom:14px;">'
        f'<a href="/deal/{_html.escape(deal_id)}" '
        f'style="color:{P["accent"]};font-family:var(--ck-mono);font-size:10px;'
        f'letter-spacing:0.10em;">&larr; DEAL DASHBOARD</a>'
        f'<span style="color:{P["text_faint"]};padding:0 8px;">·</span>'
        f'<a href="/deal/{_html.escape(deal_id)}/red-flags" '
        f'style="color:{P["accent"]};font-family:var(--ck-mono);font-size:10px;'
        f'letter-spacing:0.10em;">RED FLAGS →</a>'
        f'<span style="color:{P["text_faint"]};padding:0 8px;">·</span>'
        f'<a href="/analysis/{_html.escape(deal_id)}" '
        f'style="color:{P["accent"]};font-family:var(--ck-mono);font-size:10px;'
        f'letter-spacing:0.10em;">ANALYSIS WORKBENCH →</a>'
        f'</div>'
    )

    if error:
        body = header_links + _banner_insufficient(missing_fields or [], deal_id)
        body += _panel(
            "Error detail",
            f'<pre style="color:{P["text_dim"]};font-family:var(--ck-mono);'
            f'font-size:11px;white-space:pre-wrap;">{_html.escape(error)}</pre>',
            code="ERR",
        )
        return chartis_shell(
            body,
            title=f"Partner Review · {deal_label}",
            active_nav="/pe-intelligence",
            subtitle=f"Partner review unavailable for {deal_label}",
        )

    review = packet  # already the PartnerReview object at this point
    banner = _recommendation_banner(review)
    kpi_strip = _kpi_strip(review)

    narrative_section = _panel(
        "Partner Voice — Headline, Bull, Bear",
        _narrative_panel(review),
        code="VOC",
    )
    change_section = _panel(
        "Three Things That Would Change My Mind",
        _change_my_mind(review),
        code="FLP",
    )
    bands_section = _panel(
        f"Reasonableness Bands ({len(review.reasonableness_checks or [])})",
        _bands_table(review),
        code="BND",
    )
    crit_high = [h for h in (review.heuristic_hits or [])
                 if str(getattr(h, "severity", "")) in ("CRITICAL", "HIGH")]
    crit_section = _panel(
        f"Critical + High Severity Findings ({len(crit_high)})",
        _hits_table(review, severities=["CRITICAL", "HIGH"]),
        code="FLG",
    )
    other_hits = [h for h in (review.heuristic_hits or [])
                  if str(getattr(h, "severity", "")) in ("MEDIUM", "LOW")]
    other_section = _panel(
        f"Medium + Low Findings ({len(other_hits)})",
        _hits_table(review, severities=["MEDIUM", "LOW"]),
        code="HIT",
    )

    secondary_header = ck_section_header(
        "SECONDARY ANALYTICS",
        "regime, market, posture, stress, white-space, investability",
        count=6,
    )

    related_header = ck_section_header(
        "RELATED VIEWS",
        "drill into any secondary-analytic section as its own page",
    )
    related = related_views_panel(deal_id, exclude="partner-review")

    body = (
        header_links
        + banner
        + kpi_strip
        + narrative_section
        + change_section
        + bands_section
        + crit_section
        + other_section
        + secondary_header
        + _secondary_analytics(review)
        + related_header
        + related
    )

    subtitle = f"{deal_label} · 278-module brain run · {review.generated_at:%Y-%m-%d %H:%M UTC}"
    return chartis_shell(
        body,
        title=f"Partner Review · {deal_label}",
        active_nav="/pe-intelligence",
        subtitle=subtitle,
    )
