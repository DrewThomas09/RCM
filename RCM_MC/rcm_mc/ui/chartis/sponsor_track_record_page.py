"""PE Sponsor Track Record — /sponsor-track-record.

Top-level portfolio-scope page that surfaces
``data_public/sponsor_track_record.py`` — sortable league table of
every PE sponsor in the deal corpus with:

  - deal count + realized count
  - MOIC (p25/p50/mean/p75)
  - IRR median
  - median hold years
  - loss rate + home-run rate
  - consistency score (0-1)
  - observable sector specialization

Orthogonal to the existing ``/sponsor-heatmap`` (sector × sponsor MOIC
grid) and ``/sponsor-league`` (top-25 by MOIC only).
"""
from __future__ import annotations

import html as _html
from typing import Any, List, Optional

from .._chartis_kit import (
    P,
    chartis_shell,
    ck_data_universe,
    ck_kpi_block,
    ck_page_title,
    ck_section_header,
)
from ._helpers import (
    empty_note,
    fmt_multiple,
    fmt_pct,
    load_corpus_deals,
    small_panel,
    verdict_badge,
)
from ._sanity import render_number


_EXPLAINER_CSS = """
.ck-str-explainer{font-family:var(--sc-serif);font-size:15px;line-height:1.6;
color:var(--sc-text-dim);max-width:68ch;
margin:var(--sc-s-4) 0 var(--sc-s-6);}
.ck-str-explainer em{color:var(--sc-teal-ink);font-style:italic;}
"""

_CONSISTENCY_BANDS = [
    (0.70, P["positive"], "HIGH"),
    (0.45, P["warning"], "MEDIUM"),
    (0.0, P["text_faint"], "LOW"),
]


def _consistency_band(score: float) -> tuple[str, str]:
    for thresh, col, label in _CONSISTENCY_BANDS:
        if score >= thresh:
            return col, label
    return P["text_faint"], "—"


def _fmt_years(v: Any) -> str:
    try:
        return f"{float(v):.1f}y"
    except (TypeError, ValueError):
        return "—"


def _fmt_ev(v: Any) -> str:
    try:
        f = float(v)
        if abs(f) >= 1000:
            return f"${f/1000:.2f}B"
        return f"${f:,.0f}M"
    except (TypeError, ValueError):
        return "—"


def _consistency_moic_scatter(records: List[Any]) -> str:
    """SVG scatter: Consistency (x) vs. Median MOIC (y), bubble
    size = deal count.

    Helps the partner read the four-quadrant structure of the
    sponsor universe at a glance:
      - top-right: high MOIC + high consistency → compounders
      - top-left:  high MOIC + low consistency  → lottery sponsors
      - bottom-right: low MOIC + high consistency → underperformers
      - bottom-left:  low MOIC + low consistency  → mixed/avoid

    The scatter is a glanceable version of the table below; partners
    looking for "find me the compounders" point at the top-right
    region instead of sorting columns.
    """
    points = [
        r for r in records
        if r.consistency_score is not None
        and r.median_moic is not None
    ]
    if not points:
        return ""

    width = 720
    height = 380
    pad_l, pad_r, pad_t, pad_b = 60, 24, 32, 48
    inner_w = width - pad_l - pad_r
    inner_h = height - pad_t - pad_b

    # Consistency_score is on a 0-100 composite scale (see
    # data_public/sponsor_track_record.py:146). MOIC: 0 → max+0.5.
    moics = [float(r.median_moic) for r in points]
    max_moic = max(max(moics), 3.0) + 0.5
    deal_counts = [r.deal_count for r in points]
    max_deals = max(deal_counts)

    def sx(v: float) -> float:
        # v is 0..100; clamp defensively in case of out-of-range
        v_clamped = max(0.0, min(100.0, v))
        return pad_l + (v_clamped / 100.0) * inner_w

    def sy(v: float) -> float:
        return pad_t + inner_h - (v / max_moic) * inner_h

    def sr(deals: int) -> float:
        # Bubble radius 3..16 by sqrt scaling (area ~ deals)
        if max_deals <= 1:
            return 6.0
        return 3.0 + 13.0 * (deals / max_deals) ** 0.5

    # Quadrant background tint at consistency=55, MOIC=2.0 (median-ish
    # split). Subtle wash so the four zones are visible without
    # overpowering the dots.
    qx = sx(55.0)
    qy = sy(2.0)
    quadrants = (
        # top-right: compounders (light green wash)
        f'<rect x="{qx:.1f}" y="{pad_t}" '
        f'width="{pad_l + inner_w - qx:.1f}" height="{qy - pad_t:.1f}" '
        f'fill="#0a8a5f" fill-opacity="0.05" />'
        # bottom-left: avoid (light red wash)
        f'<rect x="{pad_l}" y="{qy:.1f}" '
        f'width="{qx - pad_l:.1f}" '
        f'height="{pad_t + inner_h - qy:.1f}" '
        f'fill="#b5321e" fill-opacity="0.03" />'
    )

    # Gridlines at MOIC 1, 2, 3 and Consistency 25, 50, 75
    grid = []
    for v in (1.0, 2.0, 3.0):
        if v > max_moic:
            continue
        y = sy(v)
        grid.append(
            f'<line x1="{pad_l}" x2="{pad_l + inner_w}" '
            f'y1="{y:.1f}" y2="{y:.1f}" stroke="#d6cfc0" '
            f'stroke-dasharray="2,4" />'
            f'<text x="{pad_l - 6}" y="{y + 3:.1f}" '
            f'fill="#7a8699" text-anchor="end" font-size="10" '
            f'font-family="JetBrains Mono, monospace">{v:.1f}x</text>'
        )
    for v in (25.0, 50.0, 75.0):
        x = sx(v)
        grid.append(
            f'<line y1="{pad_t}" y2="{pad_t + inner_h}" '
            f'x1="{x:.1f}" x2="{x:.1f}" stroke="#d6cfc0" '
            f'stroke-dasharray="2,4" />'
            f'<text x="{x:.1f}" y="{height - pad_b + 14}" '
            f'fill="#7a8699" text-anchor="middle" font-size="10" '
            f'font-family="JetBrains Mono, monospace">{v:.0f}</text>'
        )

    # Plot each sponsor as a bubble
    bubbles = []
    for r in points:
        cx = sx(float(r.consistency_score))
        cy = sy(float(r.median_moic))
        rad = sr(r.deal_count)
        # Color by MOIC band (same as vintage chart)
        moic = float(r.median_moic)
        color = (
            "#0a8a5f" if moic >= 2.5
            else "#b8732a" if moic >= 1.5
            else "#b5321e"
        )
        sponsor = _html.escape(str(r.sponsor))
        bubbles.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rad:.1f}" '
            f'fill="{color}" fill-opacity="0.55" '
            f'stroke="{color}" stroke-width="1">'
            f'<title>{sponsor}: {moic:.2f}x median MOIC · '
            f'{float(r.consistency_score):.0f} consistency · '
            f'{r.deal_count} deals</title>'
            f'</circle>'
        )

    # Axis labels
    axis_labels = (
        f'<text x="{pad_l + inner_w/2:.1f}" y="{height - 8}" '
        f'fill="#1a2332" text-anchor="middle" font-size="12" '
        f'font-family="Inter, sans-serif" font-weight="600">'
        f'Consistency score (0 = scattered, 100 = tight)</text>'
        f'<text x="16" y="{pad_t + inner_h/2:.1f}" '
        f'fill="#1a2332" text-anchor="middle" font-size="12" '
        f'font-family="Inter, sans-serif" font-weight="600" '
        f'transform="rotate(-90 16 {pad_t + inner_h/2:.1f})">'
        f'Median MOIC</text>'
    )

    # Quadrant legend chips in the corners
    quad_legend = (
        f'<text x="{pad_l + inner_w - 12}" y="{pad_t + 14}" '
        f'fill="#0a8a5f" text-anchor="end" font-size="10" '
        f'font-family="Inter, sans-serif" font-weight="600" '
        f'fill-opacity="0.75">COMPOUNDERS →</text>'
        f'<text x="{pad_l + 12}" y="{pad_t + 14}" '
        f'fill="#b8732a" text-anchor="start" font-size="10" '
        f'font-family="Inter, sans-serif" font-weight="600" '
        f'fill-opacity="0.75">← LOTTERY</text>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;background:transparent;'
        f'margin:8px 0 16px;">'
        f'{quadrants}'
        f'{"".join(grid)}'
        f'{"".join(bubbles)}'
        f'{axis_labels}'
        f'{quad_legend}'
        f'</svg>'
    )


def _sponsor_row(rec: Any) -> str:
    sponsor = _html.escape(str(rec.sponsor))
    sector_tags = ""
    if rec.sectors:
        # SponsorRecord.sectors is a list of sector labels; show top 3.
        items = list(rec.sectors)[:3]
        sector_tags = " ".join(
            f'<span style="font-family:var(--ck-mono);font-size:9px;'
            f'color:{P["text_faint"]};background:{P["panel_alt"]};'
            f'border:1px solid {P["border_dim"]};padding:1px 5px;'
            f'border-radius:2px;margin-right:3px;">'
            f'{_html.escape(str(s))}</span>'
            for s in items
        )
    consistency = rec.consistency_score or 0.0
    cons_col, cons_label = _consistency_band(consistency)

    loss_col = P["negative"] if rec.loss_rate > 0.30 else P["text"]
    hr_col = P["positive"] if rec.home_run_rate > 0.25 else P["text"]

    median_col = P["positive"] if (rec.median_moic or 0) >= 2.5 else (
        P["warning"] if (rec.median_moic or 0) >= 1.5 else P["negative"]
    )

    return (
        f'<tr>'
        f'<td style="color:{P["text"]};font-weight:600;font-size:11.5px;">{sponsor}'
        + (f'<div style="margin-top:4px;">{sector_tags}</div>' if sector_tags else "")
        + f'</td>'
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{P["text"]};" data-val="{rec.deal_count}">'
        f'{rec.deal_count}</td>'
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" data-val="{rec.realized_count}">'
        f'{rec.realized_count}</td>'
        f'<td style="text-align:right;" '
        f'data-val="{rec.median_moic or 0}">{render_number(rec.median_moic, "moic")}</td>'
        f'<td style="text-align:right;" '
        f'data-val="{rec.moic_p25 or 0}">{render_number(rec.moic_p25, "moic")}</td>'
        f'<td style="text-align:right;" '
        f'data-val="{rec.moic_p75 or 0}">{render_number(rec.moic_p75, "moic")}</td>'
        f'<td style="text-align:right;" '
        f'data-val="{rec.median_irr or 0}">{render_number(rec.median_irr, "irr")}</td>'
        f'<td style="text-align:right;" '
        f'data-val="{rec.median_hold_years or 0}">{render_number(rec.median_hold_years, "hold_years")}</td>'
        f'<td style="text-align:right;" '
        f'data-val="{rec.loss_rate}">{render_number(rec.loss_rate, "loss_rate")}</td>'
        f'<td style="text-align:right;" '
        f'data-val="{rec.home_run_rate}">{render_number(rec.home_run_rate, "home_run_rate")}</td>'
        f'<td style="text-align:right;" data-val="{consistency}">'
        f'{render_number(consistency, "consistency_score")}</td>'
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" '
        f'data-val="{rec.avg_ev_mm or 0}">{_fmt_ev(rec.avg_ev_mm)}</td>'
        f'</tr>'
    )


def render_sponsor_track_record(
    store: Any = None,
    current_user: Optional[str] = None,
) -> str:
    def _title(meta: str) -> str:
        return ck_page_title(
            "Sponsor Track Record",
            eyebrow="SPONSOR TRACK RECORD",
            meta=meta,
        ) + '<div style="margin:8px 0 0;">' + ck_data_universe("corpus") + '</div>'
    explainer_html = (
        '<p class="ck-str-explainer">'
        '<em>What the sponsor track record reveals.</em> '
        "Sortable league table of every PE sponsor in the deal "
        "corpus: MOIC quartiles, IRR, hold years, loss rate, home-run "
        "rate, and a 0–1 consistency score blending MOIC + IRR "
        "dispersion. A high median MOIC with low consistency is a "
        "lottery sponsor; tight quartiles signal a compounder."
        '</p>'
    )

    try:
        from ...data_public.sponsor_track_record import (
            sponsor_league_table, sector_specialization,
        )
    except Exception as exc:  # noqa: BLE001
        body = small_panel(
            "Sponsor track record unavailable",
            empty_note(f"sponsor_track_record module failed: {exc!r}"),
            code="ERR",
        )
        return chartis_shell(
            _title("module unavailable") + explainer_html + body,
            title="Sponsor Track Record",
            active_nav="/sponsor-track-record",
            extra_css=_EXPLAINER_CSS,
        )

    corpus = load_corpus_deals()
    if not corpus:
        body = small_panel(
            "Sponsor track record — no corpus",
            empty_note(
                "No corpus loaded. The deals corpus seeds live at "
                "rcm_mc/data_public/_SEED_DEALS + extended_seed_*.py "
                "and should total the full deal corpus."
            ),
            code="NIL",
        )
        return chartis_shell(
            _title("no corpus available") + explainer_html + body,
            title="Sponsor Track Record",
            active_nav="/sponsor-track-record",
            extra_css=_EXPLAINER_CSS,
        )

    records = sponsor_league_table(corpus, min_deals=2)
    # Sort by median_moic descending as default league ordering
    records_sorted = sorted(
        records,
        key=lambda r: (r.median_moic or 0, r.deal_count),
        reverse=True,
    )

    total_sponsors = len(records_sorted)
    total_deals = sum(r.deal_count for r in records_sorted)
    realized = sum(r.realized_count for r in records_sorted)
    overall_median = (
        sorted((r.median_moic for r in records_sorted if r.median_moic))[
            len([r for r in records_sorted if r.median_moic]) // 2
        ]
        if any(r.median_moic for r in records_sorted) else None
    )
    consistent = [r for r in records_sorted if (r.consistency_score or 0) >= 0.70]

    kpis = (
        ck_kpi_block("Sponsors Tracked", str(total_sponsors), f"min {2} deals")
        + ck_kpi_block("Deals Counted", str(total_deals), "across the deal corpus")
        + ck_kpi_block("Realized", str(realized),
                        f"{realized/total_deals*100:.0f}% of tracked" if total_deals else "—")
        + ck_kpi_block("Overall Median MOIC",
                        render_number(overall_median, "moic"), "sponsor-weighted")
        + ck_kpi_block("High Consistency",
                        str(len(consistent)), "sponsors ≥ 0.70 score")
    )
    kpi_strip = f'<div class="ck-kpi-grid">{kpis}</div>'

    # Visual sponsor universe: scatter of consistency × MOIC sized
    # by deal count, so the partner can read the four-quadrant
    # structure (compounders / lottery / underperformers / avoid)
    # without sorting the table below.
    scatter = _consistency_moic_scatter(records_sorted)

    table_rows = "".join(_sponsor_row(r) for r in records_sorted)
    table = (
        f'<div class="ck-table-wrap">'
        f'<table class="ck-table sortable" id="sponsor-league">'
        f'<thead><tr>'
        f'<th style="width:200px;">Sponsor · Top Sectors</th>'
        f'<th class="num">Deals</th>'
        f'<th class="num">Realized</th>'
        f'<th class="num">Med MOIC</th>'
        f'<th class="num">P25</th>'
        f'<th class="num">P75</th>'
        f'<th class="num">Med IRR</th>'
        f'<th class="num">Hold</th>'
        f'<th class="num">Loss %</th>'
        f'<th class="num">HR %</th>'
        f'<th class="num">Consistency</th>'
        f'<th class="num">Avg EV</th>'
        f'</tr></thead>'
        f'<tbody>{table_rows}</tbody></table></div>'
    )

    # Top-5 by MOIC strip as a glanceable highlight
    top5 = records_sorted[:5]
    top5_cards = []
    for rec in top5:
        col, cons_label = _consistency_band(rec.consistency_score or 0.0)
        top5_cards.append(
            f'<div style="flex:1;min-width:180px;background:{P["panel"]};'
            f'border:1px solid {col};border-left-width:4px;border-radius:3px;'
            f'padding:10px 14px;">'
            f'<div style="font-family:var(--ck-mono);font-size:13px;font-weight:600;'
            f'color:{P["text"]};">{_html.escape(str(rec.sponsor))}</div>'
            f'<div style="font-family:var(--ck-mono);font-size:20px;'
            f'font-weight:700;margin-top:4px;">'
            f'{render_number(rec.median_moic, "moic")}</div>'
            f'<div style="color:{P["text_faint"]};font-family:var(--ck-mono);'
            f'font-size:9.5px;letter-spacing:0.10em;margin-top:2px;">'
            f'median MOIC · {rec.deal_count} deals · {cons_label.lower()} consistency</div>'
            f'</div>'
        )
    top5_strip = (
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;">'
        f'{"".join(top5_cards)}</div>'
    )

    meta = (
        f"{total_sponsors} sponsors · {total_deals} deals · "
        f"{realized} realized"
    )
    body = (
        _title(meta)
        + explainer_html
        + kpi_strip
        + ck_section_header("TOP 5 BY MEDIAN MOIC", "highest realized returns")
        + top5_strip
        + ck_section_header(
            "SPONSOR UNIVERSE — CONSISTENCY × MOIC",
            "compounders top-right · lottery sponsors top-left · "
            "bubble size = deal count",
        )
        + scatter
        + ck_section_header(
            "FULL LEAGUE TABLE",
            f"sorted by median MOIC · click a column header to re-sort",
            count=total_sponsors,
        )
        + table
    )

    return chartis_shell(
        body,
        title="Sponsor Track Record",
        active_nav="/sponsor-track-record",
        extra_css=_EXPLAINER_CSS,
    )
