"""Deal Quality Scorer page — /deal-quality.

Scores each corpus deal on data completeness + analytical credibility.
Shows tier distribution, flag summary, and per-deal detail table.
"""
from __future__ import annotations

import html as _html
import importlib
import math
from typing import Any, Dict, List


def _load_corpus() -> List[Dict[str, Any]]:
    from rcm_mc.data_public.deals_corpus import _SEED_DEALS
    from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
    result = list(_SEED_DEALS) + list(EXTENDED_SEED_DEALS)
    for i in range(2, 32):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            result += list(getattr(mod, f"EXTENDED_SEED_DEALS_{i}"))
        except (ImportError, AttributeError):
            pass
    return result


# ---------------------------------------------------------------------------
# Inline SVG helpers
# ---------------------------------------------------------------------------

def _mini_bar(pct: float, color: str, width: int = 80) -> str:
    filled = max(0, min(width, int(pct * width)))
    return (
        f'<svg width="{width}" height="8" xmlns="http://www.w3.org/2000/svg">'
        f'<rect x="0" y="0" width="{width}" height="8" rx="1" fill="#ECE5D6"/>'
        f'<rect x="0" y="0" width="{filled}" height="8" rx="1" fill="{color}"/>'
        f'</svg>'
    )


def _tier_badge(tier: str) -> str:
    colors = {"A": "#0a8a5f", "B": "#1F7A75", "C": "#b8732a", "D": "#b5321e"}
    c = colors.get(tier, "#7a8699")
    return (
        f'<span style="display:inline-block;padding:1px 6px;border:1px solid {c};'
        f'color:{c};font-family:var(--ck-mono);font-size:9.5px;border-radius:2px;">'
        f'{tier}</span>'
    )


def _severity_badge(severity: str) -> str:
    if severity == "error":
        return '<span style="color:#b5321e;font-size:8.5px;font-family:var(--ck-mono);">ERR</span>'
    return '<span style="color:#b8732a;font-size:8.5px;font-family:var(--ck-mono);">WRN</span>'


def _tier_distribution_svg(tier_counts: Dict[str, int], total: int) -> str:
    """Horizontal stacked bar of tier distribution."""
    tiers = [("A", "#0a8a5f"), ("B", "#1F7A75"), ("C", "#b8732a"), ("D", "#b5321e")]
    W, H = 400, 24
    segments = []
    x = 0
    for tier, color in tiers:
        count = tier_counts.get(tier, 0)
        w = int(count / total * W) if total else 0
        if w > 0:
            segments.append(f'<rect x="{x}" y="0" width="{w}" height="{H}" fill="{color}"/>')
            if w > 20:
                lx = x + w // 2
                segments.append(
                    f'<text x="{lx}" y="15" text-anchor="middle" '
                    f'font-family="JetBrains Mono,monospace" font-size="9" fill="#1a2332">'
                    f'{tier}:{count}</text>'
                )
        x += w
    return (
        f'<svg width="{W}" height="{H}" xmlns="http://www.w3.org/2000/svg">'
        f'{"".join(segments)}'
        f'</svg>'
    )


def _quality_histogram_svg(scores: List[float], width: int = 400, height: int = 80) -> str:
    """Histogram of quality scores in 10-point buckets."""
    buckets = [0] * 10
    for s in scores:
        idx = min(9, int(s / 10))
        buckets[idx] += 1
    max_b = max(buckets) if buckets else 1
    bar_w = (width - 20) // 10
    bars = []
    for i, cnt in enumerate(buckets):
        bh = max(1, int(cnt / max_b * (height - 20)))
        bx = 10 + i * bar_w
        by = height - 10 - bh
        color = "#0a8a5f" if i >= 7 else ("#1F7A75" if i >= 5 else ("#b8732a" if i >= 3 else "#b5321e"))
        bars.append(f'<rect x="{bx}" y="{by}" width="{bar_w-2}" height="{bh}" fill="{color}"/>')
        label = f'{i*10}'
        bars.append(
            f'<text x="{bx + bar_w//2 - 2}" y="{height-1}" '
            f'font-family="JetBrains Mono,monospace" font-size="7" fill="#7a8699">{label}</text>'
        )
    # median line
    if scores:
        med = sorted(scores)[len(scores) // 2]
        mx = int(10 + med / 100 * (width - 20))
        bars.append(f'<line x1="{mx}" y1="0" x2="{mx}" y2="{height-10}" stroke="#7a8699" stroke-width="1" stroke-dasharray="3,3"/>')
        bars.append(
            f'<text x="{mx+2}" y="10" font-family="JetBrains Mono,monospace" font-size="7" fill="#7a8699">med={med:.0f}</text>'
        )
    return (
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'{"".join(bars)}'
        f'</svg>'
    )


def render_deal_quality(tier_filter: str = "", sort_by: str = "quality_score", page: int = 1) -> str:
    from rcm_mc.ui._chartis_kit import (
        chartis_shell, ck_fmt_num, ck_kpi_block, ck_page_title,
        ck_provenance_tooltip, ck_section_header, ck_illustrative_note,
    )
    from rcm_mc.data_public.deal_quality_score import score_corpus_quality, DealQualityScore

    corpus = _load_corpus()
    all_scores = score_corpus_quality(corpus)

    # Stats
    total = len(all_scores)
    from collections import Counter
    tier_counts = Counter(s.tier for s in all_scores)
    avg_q = sum(s.quality_score for s in all_scores) / total if total else 0
    n_flagged = sum(1 for s in all_scores if s.flags)
    n_errors = sum(sum(1 for f in s.flags if f.severity == "error") for s in all_scores)

    # Filter
    if tier_filter and tier_filter.upper() in ("A", "B", "C", "D"):
        scores = [s for s in all_scores if s.tier == tier_filter.upper()]
    else:
        scores = list(all_scores)

    # Sort
    reverse = True
    if sort_by == "deal_name":
        scores.sort(key=lambda s: s.deal_name, reverse=False)
        reverse = False
    elif sort_by == "completeness":
        scores.sort(key=lambda s: s.completeness_pct, reverse=True)
    elif sort_by == "credibility":
        scores.sort(key=lambda s: s.credibility_pct, reverse=True)
    elif sort_by == "tier":
        scores.sort(key=lambda s: s.tier)
        reverse = False
    else:
        scores.sort(key=lambda s: s.quality_score, reverse=True)

    # Paginate
    PAGE_SIZE = 50
    total_pages = max(1, math.ceil(len(scores) / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    page_scores = scores[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]

    # KPIs — cycle 41 adds provenance + ck_fmt_num.
    avg_q_value = ck_provenance_tooltip(
        "Average corpus quality score",
        f"{avg_q:.1f}",
        explainer=(
            "Mean quality score across all corpus deals. Score "
            "blends completeness (% of fields populated) and "
            "credibility (% of fields passing range / type "
            "checks). Tier cutoffs: A>=80, B 60-79, C 40-59, D<40."
        ),
    )
    flagged_value = ck_provenance_tooltip(
        "Deals with data-quality flags",
        ck_fmt_num(n_flagged),
        explainer=(
            f"Number of deals carrying at least one flagged field, "
            f"of which {n_errors} are hard errors (range / type "
            f"violations) vs. softer warnings. Hard errors block "
            f"a deal from contributing to corpus benchmarks."
        ),
        inject_css=False,
    )
    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Total Deals", ck_fmt_num(total), "in corpus")
        + ck_kpi_block("Avg Quality", avg_q_value, "out of 100")
        + ck_kpi_block("Tier A", f'<span class="mn" style="color:#0a8a5f">{tier_counts.get("A",0)}</span>', f'{100*tier_counts.get("A",0)/total:.0f}% of corpus')
        + ck_kpi_block("Tier B", f'<span class="mn" style="color:#1F7A75">{tier_counts.get("B",0)}</span>', f'{100*tier_counts.get("B",0)/total:.0f}% of corpus')
        + ck_kpi_block("Flagged", flagged_value, f"{n_errors} errors total")
        + '</div>'
    )

    # Distribution panel
    dist_svg = _tier_distribution_svg(tier_counts, total)
    hist_svg = _quality_histogram_svg([s.quality_score for s in all_scores])

    dist_panel = f"""
<div class="ck-panel">
  <div class="ck-panel-title">Quality Distribution</div>
  <div style="padding:12px 16px;display:grid;grid-template-columns:1fr 1fr;gap:24px;">
    <div>
      <div class="ck-section-label" style="margin-bottom:6px;">Tier Breakdown</div>
      {dist_svg}
      <div style="margin-top:8px;font-size:9px;color:#7a8699;">
        A≥75 · B≥55 · C≥35 · D&lt;35 &nbsp;|&nbsp; composite = 55% completeness + 45% credibility
      </div>
    </div>
    <div>
      <div class="ck-section-label" style="margin-bottom:6px;">Score Histogram (0–100)</div>
      {hist_svg}
    </div>
  </div>
</div>"""

    # Filter bar
    tiers_nav = "".join(
        f'<a href="/deal-quality?tier={t}&sort_by={sort_by}" style="display:inline-block;margin:2px 4px;'
        f'padding:2px 8px;border:1px solid {"#0a8a5f" if t=="A" else "#1F7A75" if t=="B" else "#b8732a" if t=="C" else "#b5321e"};'
        f'color:{"#0a8a5f" if t=="A" else "#1F7A75" if t=="B" else "#b8732a" if t=="C" else "#b5321e"};'
        f'font-family:var(--ck-mono);font-size:10px;border-radius:2px;text-decoration:none;">'
        f'Tier {t} ({tier_counts.get(t,0)})</a>'
        for t in ("A", "B", "C", "D")
    )
    filter_panel = f"""
<div class="ck-panel">
  <div class="ck-panel-title">Filter &amp; Sort</div>
  <div style="padding:8px 16px;display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
    <div>
      <span style="font-size:9px;color:#7a8699;margin-right:6px;text-transform:uppercase;letter-spacing:0.08em;">Tier</span>
      <a href="/deal-quality?sort_by={sort_by}" style="margin-right:4px;font-size:10px;color:#7a8699;text-decoration:none;">All</a>
      {tiers_nav}
    </div>
    <div>
      <span style="font-size:9px;color:#7a8699;margin-right:6px;text-transform:uppercase;letter-spacing:0.08em;">Sort</span>
      {"".join(
        f'<a href="/deal-quality?tier={tier_filter}&sort_by={s}" style="margin-right:6px;font-size:10px;'
        f'color:{"#1F7A75" if s==sort_by else "#7a8699"};text-decoration:none;">{s.replace("_"," ")}</a>'
        for s in ("quality_score", "completeness", "credibility", "tier", "deal_name")
      )}
    </div>
    <div style="font-size:9.5px;color:#7a8699;">
      Showing {len(page_scores)} of {len(scores)} deals
      {"· p."+str(page)+"/"+str(total_pages) if total_pages > 1 else ""}
    </div>
  </div>
</div>"""

    # Table
    def _col_header(label: str, key: str) -> str:
        active = sort_by == key
        color = "#d6cfc0" if active else "#7a8699"
        return (
            f'<th style="padding:5px 8px;text-align:left;cursor:pointer;color:{color};">'
            f'<a href="/deal-quality?tier={tier_filter}&sort_by={key}" '
            f'style="color:{color};text-decoration:none;">{label}</a></th>'
        )

    rows = []
    for i, s in enumerate(page_scores):
        stripe = ' style="background:var(--sc-bone)"' if i % 2 == 1 else ""
        flag_html = ""
        if s.flags:
            flag_parts = []
            for fl in s.flags[:3]:
                flag_parts.append(
                    f'{_severity_badge(fl.severity)} '
                    f'<span style="font-size:9px;color:#7a8699;">{_html.escape(fl.message[:60])}</span>'
                )
            flag_html = "<br>".join(flag_parts)
            if len(s.flags) > 3:
                flag_html += f'<br><span style="font-size:9px;color:#7a8699;">+{len(s.flags)-3} more</span>'

        missing_html = ""
        if s.missing_fields:
            mf = s.missing_fields[:5]
            missing_html = (
                '<span style="font-size:8.5px;color:#7a8699;font-family:var(--ck-mono);">'
                + ", ".join(mf)
                + ("…" if len(s.missing_fields) > 5 else "")
                + "</span>"
            )

        rows.append(f"""<tr{stripe}>
  <td style="padding:5px 8px;font-size:9.5px;color:#7a8699;font-family:var(--ck-mono);">{_html.escape(s.source_id)}</td>
  <td style="padding:5px 8px;font-size:10px;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
    <span title="{_html.escape(s.deal_name)}">{_html.escape(s.deal_name[:38])}</span>
  </td>
  <td style="padding:5px 8px;text-align:center;">{_tier_badge(s.tier)}</td>
  <td style="padding:5px 8px;font-family:var(--ck-mono);font-variant-numeric:tabular-nums;text-align:right;
      color:{'#0a8a5f' if s.quality_score>=75 else '#1F7A75' if s.quality_score>=55 else '#b8732a' if s.quality_score>=35 else '#b5321e'};">
    {s.quality_score:.1f}
  </td>
  <td style="padding:5px 8px;">
    {_mini_bar(s.completeness_pct, '#1F7A75')}
    <span style="font-family:var(--ck-mono);font-size:9px;color:#7a8699;margin-left:4px;">{s.completeness_pct*100:.0f}%</span>
  </td>
  <td style="padding:5px 8px;">
    {_mini_bar(s.credibility_pct, '#0a8a5f' if s.credibility_pct>=0.9 else '#b8732a' if s.credibility_pct>=0.7 else '#b5321e')}
    <span style="font-family:var(--ck-mono);font-size:9px;color:#7a8699;margin-left:4px;">{s.credibility_pct*100:.0f}%</span>
  </td>
  <td style="padding:5px 8px;font-size:9px;">{flag_html or '<span style="color:#465366;">—</span>'}</td>
  <td style="padding:5px 8px;">{missing_html or '<span style="font-size:9px;color:#465366;">—</span>'}</td>
</tr>""")

    table_html = f"""
<div class="ck-panel">
  <div class="ck-panel-title">Per-Deal Quality Scores — {len(page_scores)} of {len(scores)}</div>
  <div class="ck-table-wrap" style="max-height:600px;overflow-y:auto;">
    <table class="ck-table" style="width:100%;table-layout:fixed;">
      <thead style="position:sticky;top:0;background:#ECE5D6;z-index:2;">
        <tr>
          {_col_header("ID", "source_id")}
          <th style="padding:5px 8px;text-align:left;color:#7a8699;width:220px;">Deal</th>
          {_col_header("Tier", "tier")}
          {_col_header("Score", "quality_score")}
          {_col_header("Completeness", "completeness")}
          {_col_header("Credibility", "credibility")}
          <th style="padding:5px 8px;text-align:left;color:#7a8699;width:200px;">Flags</th>
          <th style="padding:5px 8px;text-align:left;color:#7a8699;">Missing Fields</th>
        </tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>
</div>"""

    # Pagination
    page_links = ""
    if total_pages > 1:
        parts = []
        for p in range(1, total_pages + 1):
            color = "#1F7A75" if p == page else "#7a8699"
            parts.append(
                f'<a href="/deal-quality?tier={tier_filter}&sort_by={sort_by}&page={p}" '
                f'style="margin:0 3px;font-family:var(--ck-mono);font-size:10px;color:{color};text-decoration:none;">{p}</a>'
            )
        page_links = f'<div style="padding:8px 16px;text-align:center;">{"".join(parts)}</div>'

    # Methodology panel
    method_panel = """
<div class="ck-panel">
  <div class="ck-panel-title">Scoring Methodology</div>
  <div style="padding:12px 16px;display:grid;grid-template-columns:1fr 1fr;gap:24px;">
    <div>
      <div class="ck-section-label" style="margin-bottom:6px;">Completeness (55% weight)</div>
      <table style="font-size:9.5px;line-height:1.8;width:100%;">
        <tr><td class="dim">sector</td><td class="mono" style="text-align:right;">20 pts</td></tr>
        <tr><td class="dim">ebitda_at_entry_mm</td><td class="mono" style="text-align:right;">18 pts</td></tr>
        <tr><td class="dim">year</td><td class="mono" style="text-align:right;">10 pts</td></tr>
        <tr><td class="dim">source</td><td class="mono" style="text-align:right;">8 pts</td></tr>
        <tr><td class="dim">ebitda_mm / ev_ebitda</td><td class="mono" style="text-align:right;">8 / 7 pts</td></tr>
        <tr><td class="dim">deal_type / region / revenue</td><td class="mono" style="text-align:right;">6 / 6 / 5 pts</td></tr>
        <tr><td class="dim">geography / state / leverage / notes</td><td class="mono" style="text-align:right;">4/3/3/2 pts</td></tr>
      </table>
    </div>
    <div>
      <div class="ck-section-label" style="margin-bottom:6px;">Credibility (45% weight)</div>
      <table style="font-size:9.5px;line-height:1.8;width:100%;">
        <tr><td class="dim">Start score</td><td class="mono" style="text-align:right;">100</td></tr>
        <tr><td class="dim">MOIC ≤ 0 (error)</td><td class="mono" style="text-align:right;">−30</td></tr>
        <tr><td class="dim">IRR &lt; −100% (error)</td><td class="mono" style="text-align:right;">−20</td></tr>
        <tr><td class="dim">EV ≤ 0 (error)</td><td class="mono" style="text-align:right;">−25</td></tr>
        <tr><td class="dim">Hold ≤ 0 (error)</td><td class="mono" style="text-align:right;">−15</td></tr>
        <tr><td class="dim">MOIC/IRR mismatch &gt;25pp</td><td class="mono" style="text-align:right;">−10</td></tr>
        <tr><td class="dim">EV/EBITDA outside 2–40×</td><td class="mono" style="text-align:right;">−8</td></tr>
      </table>
    </div>
  </div>
</div>"""

    # B11 — pre-fix, this page had no h1 at all (neither inline
    # .ck-page-h1 nor ck_page_title — just KPI tiles + tier
    # distribution + filter panel + per-deal table + method panel).
    # Partners landing on /deal-quality saw stats without an
    # editorial anchor identifying what the page is. Adding
    # ck_page_title gives the partner-facing identity. Title pulled
    # from module docstring ("Deal Quality Scorer"). Meta packs
    # the tier-distribution stats since that's the visual headline
    # of the page (every deal's letter grade is the load-bearing
    # output of the scoring system).
    page_title = ck_page_title(
        "Deal Quality Scorer",
        eyebrow="DEAL QUALITY",
        meta=(
            f"{total} deals scored · avg {avg_q:.1f}/100 · "
            f"A:{tier_counts.get('A', 0)} "
            f"B:{tier_counts.get('B', 0)} "
            f"C:{tier_counts.get('C', 0)} "
            f"D:{tier_counts.get('D', 0)} · "
            f"{n_flagged} flagged"
        ),
    )
    body = (page_title + ck_illustrative_note("deal-quality grades (illustrative seed corpus)")
            + kpis + dist_panel + filter_panel + table_html + page_links + method_panel)

    return chartis_shell(
        body,
        title="Deal Quality",
        active_nav="/deal-quality",
        subtitle=(
            f"{total} deals scored · "
            f"avg quality {avg_q:.1f}/100 · "
            f"A:{tier_counts.get('A',0)} B:{tier_counts.get('B',0)} "
            f"C:{tier_counts.get('C',0)} D:{tier_counts.get('D',0)} · "
            f"{n_flagged} flagged"
        ),
        editorial_intro={
            "eyebrow": "DEAL QUALITY",
            "headline": "Which deals carry their grade.",
            "italic_word": "carry",
            "body": (
                f"A 0-100 quality grade across {total} corpus "
                f"deals, decomposed by entry discipline, hold "
                f"economics, and exit certainty. Use this to "
                f"benchmark the current deal against the "
                f"realized A-tier, not the average."
            ),
        },
    )
