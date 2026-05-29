"""Sector Momentum — which sectors are growing vs declining in deal activity.

Computes recent 5-year deal count vs prior 5-year count, showing
acceleration/deceleration trends. Also shows MOIC trend by sector.
"""
from __future__ import annotations

import html
import importlib
import math
from collections import defaultdict
from typing import Any, Dict, List, Optional


def _load_corpus() -> List[Dict[str, Any]]:
    from rcm_mc.data_public.deals_corpus import _SEED_DEALS
    deals: List[Dict[str, Any]] = list(_SEED_DEALS)
    for i in range(2, 40):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            key = f"EXTENDED_SEED_DEALS_{i}"
            deals += getattr(mod, key, [])
        except Exception:
            pass
    return deals


from rcm_mc.ui._chartis_kit import (
    ck_illustrative_note,
    P, _MONO, _SANS, chartis_shell, ck_fmt_num, ck_kpi_block,
    ck_paired_block, ck_provenance_tooltip, ck_section_header,
)


def _paired_sector_rows(items: list) -> tuple:
    """Accelerating-sector data for the paired block's dataset half.

    Returns ``(headers, rows, hot_rows)`` for ``ck_paired_block``.
    ``items`` arrives sorted by change_pct desc, so ``hot_rows`` just
    marks row 0 — the top grower. Six columns: sector, recent count,
    prior count, % change, MOIC P50 recent, MOIC P50 prior.
    """
    headers = [
        "Sector", "Recent", "Prior", "Change",
        "MOIC P50 R", "MOIC P50 P",
    ]
    rows: list = []
    for d in items:
        chg = d.get("change_pct", 0.0)
        sign = "+" if chg >= 0 else ""
        rows.append([
            (d.get("sector") or "")[:30],
            str(d.get("recent", 0)),
            str(d.get("prior", 0)),
            f"{sign}{chg:.0f}%",
            f"{d['moic_recent']:.2f}x" if d.get("moic_recent") else "—",
            f"{d['moic_prior']:.2f}x" if d.get("moic_prior") else "—",
        ])
    return headers, rows, ([0] if rows else [])


def _percentile(vals: List[float], p: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    idx = (len(s) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def _momentum_arrow(change_pct: float) -> str:
    if change_pct >= 50:
        col, sym = P["positive"], "▲▲"
    elif change_pct >= 10:
        col, sym = P["positive"], "▲"
    elif change_pct >= -10:
        col, sym = P["text_dim"], "—"
    elif change_pct >= -50:
        col, sym = P["warning"], "▼"
    else:
        col, sym = P["negative"], "▼▼"
    return f'<span style="font-size:12px;color:{col};font-family:{_MONO}">{sym}</span>'


def _momentum_bar_svg(sectors_data: list, w: int = 280, item_h: int = 20) -> str:
    """Horizontal bar showing recent vs prior count per sector."""
    if not sectors_data:
        return ""
    max_count = max(max(d["recent"], d["prior"]) for d in sectors_data) or 1
    pad_l = 160
    pad_r = 50
    cw = w - pad_l - pad_r
    total_h = len(sectors_data) * item_h + 12

    parts: List[str] = []
    for i, d in enumerate(sectors_data):
        y = i * item_h + 4
        trunc = d["sector"][:24]
        parts.append(f'<text x="{pad_l-4}" y="{y+item_h//2+4}" text-anchor="end" fill="{P["text_dim"]}" font-size="9" font-family="{_SANS}">{html.escape(trunc)}</text>')

        # prior (background, dimmer)
        pw = int(d["prior"] / max_count * cw)
        parts.append(f'<rect x="{pad_l}" y="{y+4}" width="{pw}" height="{item_h-8}" fill="{P["border"]}" opacity="0.6"/>')

        # recent (foreground)
        rw = int(d["recent"] / max_count * cw)
        col = P["positive"] if d["recent"] > d["prior"] else (P["negative"] if d["recent"] < d["prior"] else P["text_dim"])
        parts.append(f'<rect x="{pad_l}" y="{y+6}" width="{rw}" height="{item_h-12}" fill="{col}"/>')

        # labels
        parts.append(f'<text x="{pad_l+max(rw,pw)+4}" y="{y+item_h//2+4}" fill="{col}" font-size="8" font-family="{_MONO}" font-variant-numeric="tabular-nums">{d["recent"]}/{d["prior"]}</text>')

    return f'<svg width="{w}" height="{total_h}">{"".join(parts)}</svg>'


def render_sector_momentum(recent_years: int = 5) -> str:
    corpus = _load_corpus()

    from datetime import date
    current_year = 2024  # use fixed reference year
    recent_cutoff = current_year - recent_years
    prior_cutoff  = recent_cutoff - recent_years

    sector_recent: Dict[str, int] = defaultdict(int)
    sector_prior:  Dict[str, int] = defaultdict(int)
    sector_moic_recent: Dict[str, List[float]] = defaultdict(list)
    sector_moic_prior:  Dict[str, List[float]] = defaultdict(list)

    for d in corpus:
        sec = d.get("sector")
        yr  = d.get("year")
        if not sec or not yr:
            continue
        moic = d.get("realized_moic")
        if yr >= recent_cutoff:
            sector_recent[sec] += 1
            if moic: sector_moic_recent[sec].append(moic)
        elif yr >= prior_cutoff:
            sector_prior[sec] += 1
            if moic: sector_moic_prior[sec].append(moic)

    # build momentum data
    all_sectors = set(sector_recent.keys()) | set(sector_prior.keys())
    momentum_data = []
    for sec in all_sectors:
        recent = sector_recent[sec]
        prior  = sector_prior[sec]
        if recent == 0 and prior == 0:
            continue
        change = (recent - prior) / max(prior, 1) * 100
        moic_recent_p50 = _percentile(sector_moic_recent[sec], 50)
        moic_prior_p50  = _percentile(sector_moic_prior[sec], 50)
        momentum_data.append({
            "sector": sec,
            "recent": recent,
            "prior": prior,
            "change_pct": change,
            "moic_recent": moic_recent_p50,
            "moic_prior": moic_prior_p50,
        })

    # accelerating and decelerating sectors
    momentum_data.sort(key=lambda x: -x["change_pct"])
    top_growing = momentum_data[:10]
    top_declining = sorted(momentum_data, key=lambda x: x["change_pct"])[:10]

    def _table(items: list, title: str) -> str:
        rows = ""
        for i, d in enumerate(items):
            bg = P["row_stripe"] if i % 2 else P["panel"]
            col = P["positive"] if d["change_pct"] > 0 else (P["negative"] if d["change_pct"] < 0 else P["text_dim"])
            sign = "+" if d["change_pct"] > 0 else ""
            moic_r = f"{d['moic_recent']:.2f}×" if d.get("moic_recent") else "—"
            moic_p = f"{d['moic_prior']:.2f}×"  if d.get("moic_prior")  else "—"
            rows += (
                f'<tr>'
                f'<td style="padding:4px 8px;font-size:11px">{html.escape(d["sector"][:30])}</td>'
                f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{d["recent"]}</td>'
                f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;color:{P["text_dim"]};font-variant-numeric:tabular-nums">{d["prior"]}</td>'
                f'<td style="padding:4px 8px;font-size:11px;font-family:{_MONO};text-align:right;font-weight:700;color:{col};font-variant-numeric:tabular-nums">{sign}{d["change_pct"]:.0f}%</td>'
                f'<td style="padding:4px 8px;text-align:center">{_momentum_arrow(d["change_pct"])}</td>'
                f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{moic_r}</td>'
                f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;color:{P["text_dim"]};font-variant-numeric:tabular-nums">{moic_p}</td>'
                f'</tr>'
            )

        th = f"padding:4px 8px;font-size:9px;letter-spacing:.08em;color:{P['text_dim']};font-family:{_SANS};border-bottom:1px solid {P['border']}"
        return f"""<div style="margin-bottom:16px">
<div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.1em;margin-bottom:6px;border-bottom:1px solid {P['border']};padding-bottom:4px">{html.escape(title)}</div>
<div style="border:1px solid {P['border']};overflow-x:auto">
<table style="width:100%;border-collapse:collapse">
<thead><tr style="background:{P['panel_alt']}">
  <th style="{th}">SECTOR</th>
  <th style="{th};text-align:right">RECENT</th>
  <th style="{th};text-align:right">PRIOR</th>
  <th style="{th};text-align:right">CHANGE</th>
  <th style="{th};text-align:center">MOM</th>
  <th style="{th};text-align:right">MOIC P50 (R)</th>
  <th style="{th};text-align:right">MOIC P50 (P)</th>
</tr></thead>
<tbody>{rows}</tbody>
</table></div></div>"""

    bar_data_growing = [
        {"sector": d["sector"], "recent": d["recent"], "prior": d["prior"]}
        for d in top_growing if d["change_pct"] > 5
    ]

    window_label = f"{recent_cutoff}–{current_year-1} vs {prior_cutoff}–{recent_cutoff-1}"

    # filter links
    filter_links = " ".join(
        f'<a href="/sector-momentum?years={n}" style="font-size:11px;font-family:{_MONO};color:{P["accent"] if recent_years==n else P["text_dim"]};text-decoration:none;padding:3px 8px;border:1px solid {P["border"] if recent_years!=n else P["accent"]}">{n}y window</a>'
        for n in [3, 5, 7, 10]
    )

    # Data-source disclosure. User asked "where are these numbers
    # coming from?" — the deal counts and MOICs are NOT live; they
    # come from a curated corpus of public PE-healthcare transactions
    # stored in rcm_mc/data_public/deals_corpus.py + 38 extended_seed
    # files. Reference year is hard-coded to 2024 (no live updates).
    # Render an info-toned callout so partners see this before reading
    # the acceleration verdicts.
    corpus_min_year = min((d.get("year") for d in corpus if d.get("year")), default=current_year)
    corpus_max_year = max((d.get("year") for d in corpus if d.get("year")), default=current_year)
    data_source_callout = (
        f'<div style="background:{P["panel_alt"]};border-left:3px solid '
        f'{P["accent"]};padding:12px 16px;border-radius:0 3px 3px 0;'
        f'margin-bottom:14px;font-size:12px;color:{P["text_dim"]};'
        f'line-height:1.6;max-width:880px;">'
        f'<div style="font-family:{_MONO};font-size:10px;'
        f'letter-spacing:1.6px;text-transform:uppercase;font-weight:700;'
        f'color:{P["text_faint"]};margin-bottom:4px;">Data source</div>'
        f'<strong style="color:{P["text"]};">Curated corpus of '
        f'{len(corpus)} public PE-healthcare transactions, '
        f'{corpus_min_year}–{corpus_max_year}.</strong> Records '
        f'are hand-coded from publicly-documented sponsor disclosures, '
        f'press, and S-1 filings (see <code style="font-family:{_MONO};'
        f'font-size:11px;color:{P["accent"]};">data_public/deals_corpus.py</code>). '
        f'Reference year is pinned at {current_year} — not a live feed; '
        f'recomputation requires a code update. Recent and prior windows '
        f'are computed from each deal\'s entry year. Coverage is '
        f'best-effort, not exhaustive — selection-bias toward larger and '
        f'better-disclosed transactions.'
        f'</div>'
    )

    # Cycle 42 — KPI strip with provenance to lift fidelity over 70.
    n_growing = sum(1 for d in momentum_data if d["change_pct"] > 5)
    n_declining = sum(1 for d in momentum_data if d["change_pct"] < -5)
    biggest_grower = top_growing[0] if top_growing else {"sector": "—", "change_pct": 0}
    sector_count_value = ck_provenance_tooltip(
        "Sectors tracked",
        ck_fmt_num(len(momentum_data)),
        explainer=(
            f"Healthcare PE sector taxonomy applied to "
            f"{len(corpus)} corpus deals. Comparison: recent "
            f"window {recent_cutoff}-{current_year-1} vs. prior "
            f"window {prior_cutoff}-{recent_cutoff-1}."
        ),
    )
    accelerating_value = ck_provenance_tooltip(
        "Accelerating sectors",
        ck_fmt_num(n_growing),
        explainer=(
            "Sectors with deal-count growth above 5% recent-vs-"
            "prior. Above 5% threshold filters out noise from "
            "small-N base rates. Pair with realized MOIC trend "
            "to find sectors that are growing AND winning."
        ),
        inject_css=False,
    )
    kpi_strip = (
        f'<div class="ck-kpi-grid" style="grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:14px;">'
        + ck_kpi_block("Sectors", sector_count_value, "in taxonomy")
        + ck_kpi_block("Accelerating", accelerating_value, ">5% deal growth")
        + ck_kpi_block("Decelerating", ck_fmt_num(n_declining), ">5% deal decline")
        + ck_kpi_block("Top Grower", biggest_grower["sector"][:18],
                        f"+{biggest_grower['change_pct']:.0f}%" if biggest_grower["change_pct"] else "—")
        + '</div>'
    )

    # Signature paired viz+dataset block from the Claude Design
    # handoff: the recent-vs-prior momentum bars on the left, the
    # accelerating-sectors table on the right, one outer rule. The
    # bar SVG sits inside a caption frame on the viz side; the table
    # is built from top_growing via _paired_sector_rows. hot_rows
    # marks the strongest grower (sorted desc, so row 0).
    bar_viz = (
        f'<div style="font-size:9px;color:{P["text_dim"]};'
        f'font-family:{_SANS};letter-spacing:.08em;'
        f'text-transform:uppercase;margin-bottom:8px;">'
        'Recent vs prior deal count &mdash; growing sectors '
        '(solid = recent, gray = prior)</div>'
        f'{_momentum_bar_svg(bar_data_growing)}'
        if bar_data_growing else
        '<div style="font-size:11px;color:var(--sc-text-faint);">'
        'No accelerating sectors in this window.</div>'
    )
    grow_headers, grow_rows, grow_hot = _paired_sector_rows(top_growing)
    paired_growing = ck_paired_block(
        bar_viz,
        data_label=f"Accelerating sectors &middot; top 10 ({window_label})",
        data_source="deals corpus",
        headers=grow_headers,
        rows=grow_rows,
        hot_rows=grow_hot,
    )

    body = f"""
<div style="padding:16px 20px;max-width:1200px">
  {data_source_callout}
  {kpi_strip}

  <div style="display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap">
    <span style="font-size:10px;color:{P['text_dim']};font-family:{_SANS}">COMPARISON WINDOW:</span>
    {filter_links}
    <span style="font-size:10px;color:{P['text_faint']};font-family:{_SANS};margin-left:8px">{window_label}</span>
  </div>

  <div style="margin-bottom:8px;font-size:10px;color:{P['text_faint']};font-family:{_SANS}">
    "Recent" = {recent_cutoff}–{current_year-1}. "Prior" = {prior_cutoff}–{recent_cutoff-1}. Change = (recent − prior) / prior. ▲▲ = &gt;50% growth, ▲ = 10–50%, — = flat, ▼ = 10–50% decline, ▼▼ = &gt;50% decline.
  </div>

  {paired_growing}

  <div style="margin-top:24px;">
    {_table(top_declining, f"DECELERATING SECTORS — TOP 10 BY DEAL DECLINE ({window_label})")}
  </div>
</div>"""

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(ck_illustrative_note("deals-corpus aggregates — built from the bundled illustrative seed deals (data_public seed + extended_seed), not your ingested portfolio") + body, "Sector Momentum", active_nav="/sector-momentum",
                         subtitle=f"{recent_years}y window — {len(momentum_data)} sectors",
        editorial_intro={
            "eyebrow": "SECTOR MOMENTUM",
            "headline": "Where the deal flow is bending.",
            "italic_word": "bending",
            "body": (
                f"Recent-vs-prior deal counts and realized MOIC across "
                f"{len(momentum_data)} healthcare sectors over the last "
                f"{recent_years} years. Use the sectors that are growing "
                f"AND winning — not just one or the other."
            ),
        })
