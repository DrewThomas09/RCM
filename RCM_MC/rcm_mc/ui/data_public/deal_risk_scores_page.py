"""Deal Risk Scores Dashboard — /deal-risk-scores.

Scores every corpus deal across 5 risk dimensions and shows the
distribution by tier (Low/Medium/High/Critical) with MOIC validation.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional

import urllib.parse as _urlparse

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_section_header, ck_kpi_block, ck_fmt_moic,
    ck_provenance_tooltip, ck_scatter, ck_illustrative_note,
)

_TIER_TONE = {
    "Low": "positive", "Medium": "teal", "High": "warning", "Critical": "negative",
}

TIER_COLORS = {
    "Low":      "#0a8a5f",
    "Medium":   "#1F7A75",
    "High":     "#b8732a",
    "Critical": "#b5321e",
}


def _tint(hex_color: str, alpha: float) -> str:
    """Faint background wash derived from an editorial tier color."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# Row washes derive from the same editorial palette as the tier badges
# above — previously hardcoded Tailwind rgba (incl. an off-palette blue
# Medium wash under a teal Medium badge), which drifted from the badges.
TIER_BG = {
    tier: _tint(color, 0.09 if tier == "Critical" else 0.07)
    for tier, color in TIER_COLORS.items()
}


def _tier_badge(tier: str) -> str:
    color = TIER_COLORS.get(tier, P["text_faint"])
    return (
        f'<span style="display:inline-block;background:{color};color:#000;'
        f'font-size:9px;padding:1px 6px;border-radius:2px;font-weight:700;'
        f'letter-spacing:.06em">{_html.escape(tier)}</span>'
    )


def _distribution_svg(dist: List[Any], width: int = 500, height: int = 100) -> str:
    """Stacked horizontal bar showing tier distribution."""
    if not dist:
        return ""
    total = sum(d.n for d in dist)
    if not total:
        return ""
    ml, mr, mt, mb = 10, 10, 14, 24
    W = width - ml - mr
    bar_h = 28

    lines = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" style="display:block">'
    ]
    x = ml
    for d in dist:
        seg_w = max(1, int(d.n / total * W))
        color = TIER_COLORS.get(d.tier, P["text_faint"])
        lines.append(
            f'<rect x="{x}" y="{mt}" width="{seg_w}" height="{bar_h}" fill="{color}"/>'
        )
        if seg_w > 30:
            lines.append(
                f'<text x="{x + seg_w//2}" y="{mt + bar_h//2 + 5}" '
                f'text-anchor="middle" font-size="10" fill="#000" font-weight="700" '
                f'font-family="JetBrains Mono,monospace">{d.pct:.0f}%</text>'
            )
        lines.append(
            f'<text x="{x + seg_w//2}" y="{mt + bar_h + 14}" '
            f'text-anchor="middle" font-size="9" fill="{color}" '
            f'font-family="Inter,sans-serif">{_html.escape(d.tier)}</text>'
        )
        x += seg_w

    lines.append("</svg>")
    return "\n".join(lines)


def _dist_table(dist: List[Any]) -> str:
    rows = []
    for d in dist:
        badge = _tier_badge(d.tier)
        moic_color = TIER_COLORS.get(d.tier, P["text_faint"])
        row_bg = TIER_BG.get(d.tier, "")
        rows.append(
            f"<tr style='background:{row_bg}'>"
            f"<td>{badge}</td>"
            f"<td class='r mn'>{d.n}</td>"
            f"<td class='r mn'>{d.pct:.1f}%</td>"
            f"<td class='r mn' style='color:{moic_color}'>"
            f"{f'{d.avg_moic:.2f}×' if d.avg_moic else '—'}</td>"
            f"<td class='r mn' style='color:{moic_color}'>"
            f"{f'{d.moic_p50:.2f}×' if d.moic_p50 else '—'}</td>"
            f"</tr>"
        )
    return (
        '<table class="ck-table">'
        "<thead><tr>"
        "<th>Risk Tier</th><th class='r'>N</th><th class='r'>% of Corpus</th>"
        "<th class='r'>Avg MOIC</th><th class='r'>P50 MOIC</th>"
        "</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )


def _sector_risk_table(rows_data: List[Dict[str, Any]], corpus_avg: float) -> str:
    rows = []
    for r in rows_data:
        score_color = (
            P["negative"] if r["avg_score"] >= 60
            else P["warning"] if r["avg_score"] >= 40
            else P["positive"]
        )
        high_color = (
            P["negative"] if r["pct_high"] >= 50
            else P["warning"] if r["pct_high"] >= 25
            else P["text_faint"]
        )
        vs_corpus = r["avg_score"] - corpus_avg
        vs_html = (
            f'<span class="mn" style="color:{P["negative"] if vs_corpus > 5 else P["positive"] if vs_corpus < -5 else P["text_dim"]}">'
            f'{vs_corpus:+.1f}</span>'
        )
        rows.append(
            f"<tr>"
            f"<td>{_html.escape(r['sector'])}</td>"
            f"<td class='r mn'>{r['n']}</td>"
            f"<td class='r mn' style='color:{score_color}'>{r['avg_score']:.1f}</td>"
            f"<td class='r'>{vs_html}</td>"
            f"<td class='r mn' style='color:{high_color}'>{r['pct_high']:.0f}%</td>"
            f"<td class='r'>{ck_fmt_moic(r.get('moic_p50'))}</td>"
            f"</tr>"
        )
    return (
        '<table class="ck-table">'
        "<thead><tr>"
        "<th>Sector</th><th class='r'>N</th>"
        "<th class='r'>Avg Risk Score</th><th class='r'>vs. Corpus</th>"
        "<th class='r'>% High/Critical</th><th class='r'>P50 MOIC</th>"
        "</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )


def _deal_table(deals: List[Any], tier_filter: str) -> str:
    if tier_filter:
        deals = [d for d in deals if d.tier == tier_filter]
    if not deals:
        return '<p class="ck-empty">No deals match the selected tier.</p>'

    deals_sorted = sorted(deals, key=lambda d: -d.composite_score)[:60]
    rows = []
    for d in deals_sorted:
        badge = _tier_badge(d.tier)
        tier_color = TIER_COLORS.get(d.tier, P["text"])
        moic_html = (
            f'<span class="mn" style="color:{tier_color}">{d.moic:.2f}×</span>'
            if d.moic else "—"
        )
        rows.append(
            f"<tr>"
            f"<td>{_html.escape(d.company_name[:30] or d.source_id)}</td>"
            f"<td>{_html.escape(d.sector[:22])}</td>"
            f"<td class='r mn'>{d.year}</td>"
            f"<td class='r mn'>{f'{d.ev_ebitda:.1f}×' if d.ev_ebitda else '—'}</td>"
            f"<td class='r mn'>{d.composite_score:.0f}</td>"
            f"<td>{badge}</td>"
            f"<td class='r'>{moic_html}</td>"
            f"</tr>"
        )
    return (
        '<table class="ck-table" style="font-size:11px">'
        "<thead><tr>"
        "<th>Company</th><th>Sector</th><th class='r'>Yr</th>"
        "<th class='r'>EV/EBITDA</th><th class='r'>Risk Score</th>"
        "<th>Tier</th><th class='r'>MOIC</th>"
        "</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody>"
        "</table>"
    )


def _risk_return_scatter(deals: List[Any], corpus_avg: float) -> str:
    """Risk vs realized-return scatter — the page's headline claim made
    visual. Composite risk score (x) vs realized MOIC (y), one dot per
    realized deal, colored by tier. The dashed vertical marks the corpus
    average risk; y=1.0x is break-even. Lower-right (high risk, sub-1x)
    is where the score should have called the loss; upper-left is low-
    risk high-return. Dots click through to the deal's /library detail.
    """
    pts = []
    for d in deals:
        moic = getattr(d, "moic", None)
        score = getattr(d, "composite_score", None)
        if moic is None or score is None:
            continue
        tone = _TIER_TONE.get(getattr(d, "tier", ""), "teal")
        sid = getattr(d, "source_id", None)
        href = f"/library/{_urlparse.quote(str(sid))}" if sid else None
        label = (getattr(d, "company_name", "") or str(sid or ""))[:40]
        pts.append((float(score), float(moic), label, tone, href))

    chart = ck_scatter(
        pts,
        x_label="Composite risk score (0–100)",
        y_label="Realized MOIC (×)",
        x_ref=corpus_avg,
        y_ref=1.0,
        height=260,
        caption=(
            "Each dot a realized deal (click through to its detail) · "
            f"dashed vertical = corpus average risk ({corpus_avg:.0f}) · "
            "y = 1.0× is break-even · lower-right = high-risk losses the "
            "score flagged · green Low / teal Medium / amber High / red "
            "Critical tier"
        ),
    )
    if not chart:
        return ""
    return (
        ck_section_header(
            "Risk vs Realized Return",
            "Does the score actually separate winners from losers?")
        + '<div style="overflow-x:auto;margin-bottom:24px">' + chart + '</div>'
    )


def render_deal_risk_scores(params: Dict[str, str]) -> str:
    from rcm_mc.data_public.deal_risk_scorer import compute_deal_risk_scores

    tier_filter = params.get("tier", "")
    result = compute_deal_risk_scores()

    # Filter controls
    tier_opts = '<option value="">All Tiers</option>' + "".join(
        f'<option value="{t}" {"selected" if t == tier_filter else ""}>{t}</option>'
        for t in ["Low", "Medium", "High", "Critical"]
    )
    # Explicit Apply button so the filter works on click even when the
    # onchange auto-submit doesn't fire (the "button not working" report);
    # a Clear link resets to All Tiers. onchange kept for one-click convenience.
    _clear = ('<a href="/deal-risk-scores" class="ck-filter-clear" '
              'style="font-size:11px;color:var(--sc-teal,#155752);margin-left:8px;'
              'text-decoration:none">Clear</a>') if tier_filter else ""
    filter_bar = f"""
<form method="get" action="/deal-risk-scores" class="ck-filters"
  style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
  <span class="ck-filter-label">Filter by Tier</span>
  <select name="tier" class="ck-sel" onchange="this.form.submit()">{tier_opts}</select>
  <button type="submit" class="ck-sel"
    style="cursor:pointer;background:var(--sc-teal,#155752);color:#fff;
    border:1px solid var(--sc-teal,#155752);padding:5px 14px;font-size:11px;
    font-family:JetBrains Mono,monospace">Apply</button>
  {_clear}
</form>"""

    # Cycle 36 — provenance wraps on the two scoring KPIs that
    # carry the most partner judgment weight.
    avg_score_value = ck_provenance_tooltip(
        "Corpus average risk score",
        f"{result.corpus_avg_score:.1f}",
        explainer=(
            "Weighted composite: entry multiple 30%, payer "
            "concentration 20%, hold duration 20%, vintage cycle "
            "15%, deal size 15%. Scaled 0 (lowest risk) to 100 "
            "(highest)."
        ),
    )
    pct_critical_value = ck_provenance_tooltip(
        "% high or critical risk",
        f"{result.pct_high_critical:.1f}%",
        explainer=(
            "Share of corpus with composite score >= 50. "
            "Tier cutoffs: Low <25, Medium 25-49, High 50-69, "
            "Critical >=70."
        ),
        inject_css=False,
    )
    kpi_grid = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block(
            "Deals Scored",
            f'<span class="mn">{result.total_deals}</span>',
            "full corpus",
        )
        + ck_kpi_block(
            "Corpus Avg Score",
            avg_score_value,
            "0 = lowest risk, 100 = highest",
        )
        + ck_kpi_block(
            "% High / Critical",
            pct_critical_value,
            "score ≥ 50",
        )
        + ck_kpi_block(
            "Low Risk P50 MOIC",
            ck_fmt_moic(result.tier_moic.get("Low")),
            "realized MOIC validation",
        )
        + ck_kpi_block(
            "High Risk P50 MOIC",
            ck_fmt_moic(result.tier_moic.get("High")),
            "vs. Low risk benchmark",
        )
        + "</div>"
    )

    dist_svg = _distribution_svg(result.distribution)
    dist_table = _dist_table(result.distribution)
    sec_table = _sector_risk_table(result.sector_avg_risk, result.corpus_avg_score)
    deal_table = _deal_table(result.scored_deals, tier_filter)
    risk_return = _risk_return_scatter(
        result.scored_deals, result.corpus_avg_score)

    title_suffix = f" — {tier_filter} Only" if tier_filter else ""

    body = f"""
{ck_illustrative_note("risk scores (illustrative seed corpus)")}
{filter_bar}
{kpi_grid}
{risk_return}
{ck_section_header("Risk Tier Distribution")}
<div style="overflow-x:auto;margin-bottom:16px">{dist_svg}</div>
<div style="overflow-x:auto;margin-bottom:24px">{dist_table}</div>
{ck_section_header("Highest-Risk Sectors", "By average composite score, min 3 deals")}
<div style="overflow-x:auto;margin-bottom:24px">{sec_table}</div>
{ck_section_header(f"Deal Risk Scores{title_suffix}", "Top 60 by composite score (descending)")}
<div style="overflow-x:auto">{deal_table}</div>
<p style="font-size:11px;color:var(--ck-text-faint);margin-top:12px">
  Risk score = weighted composite: entry multiple 30%, payer concentration 20%,
  hold duration 20%, vintage cycle 15%, deal size 15%.
  Tiers: Low &lt;25, Medium 25–49, High 50–69, Critical ≥70.
</p>
"""

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body,
        title="Deal Risk Score Dashboard",
        active_nav="/deal-risk-scores",
        subtitle="Corpus-wide 5-factor risk scoring — validated against realized MOIC",
        editorial_intro={
            "eyebrow": "RISK SCORES",
            "headline": "Where the corpus called the loss before exit.",
            "italic_word": "called",
        },
    )
