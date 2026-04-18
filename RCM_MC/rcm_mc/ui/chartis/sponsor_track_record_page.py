"""PE Sponsor Track Record — /sponsor-track-record.

Top-level portfolio-scope page that surfaces
``data_public/sponsor_track_record.py`` — sortable league table of
every PE sponsor in the 655-deal corpus with:

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
    ck_kpi_block,
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
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{median_col};font-weight:600;" '
        f'data-val="{rec.median_moic or 0}">{fmt_multiple(rec.median_moic)}</td>'
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" '
        f'data-val="{rec.moic_p25 or 0}">{fmt_multiple(rec.moic_p25)}</td>'
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" '
        f'data-val="{rec.moic_p75 or 0}">{fmt_multiple(rec.moic_p75)}</td>'
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{P["text"]};" '
        f'data-val="{rec.median_irr or 0}">{fmt_pct(rec.median_irr)}</td>'
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" '
        f'data-val="{rec.median_hold_years or 0}">{_fmt_years(rec.median_hold_years)}</td>'
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{loss_col};" data-val="{rec.loss_rate}">'
        f'{fmt_pct(rec.loss_rate)}</td>'
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{hr_col};" data-val="{rec.home_run_rate}">'
        f'{fmt_pct(rec.home_run_rate)}</td>'
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{cons_col};" data-val="{consistency}">'
        f'{consistency:.2f}</td>'
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" '
        f'data-val="{rec.avg_ev_mm or 0}">{_fmt_ev(rec.avg_ev_mm)}</td>'
        f'</tr>'
    )


def render_sponsor_track_record(
    store: Any = None,
    current_user: Optional[str] = None,
) -> str:
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
            body, title="Sponsor Track Record",
            active_nav="/sponsor-track-record",
            subtitle="Module unavailable",
        )

    corpus = load_corpus_deals()
    if not corpus:
        body = small_panel(
            "Sponsor track record — no corpus",
            empty_note(
                "No corpus loaded. The deals corpus seeds live at "
                "rcm_mc/data_public/_SEED_DEALS + extended_seed_*.py "
                "and should total 655 deals."
            ),
            code="NIL",
        )
        return chartis_shell(
            body, title="Sponsor Track Record",
            active_nav="/sponsor-track-record",
            subtitle="Corpus unavailable",
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
        + ck_kpi_block("Deals Counted", str(total_deals), "across 655-deal corpus")
        + ck_kpi_block("Realized", str(realized),
                        f"{realized/total_deals*100:.0f}% of tracked" if total_deals else "—")
        + ck_kpi_block("Overall Median MOIC",
                        fmt_multiple(overall_median), "sponsor-weighted")
        + ck_kpi_block("High Consistency",
                        str(len(consistent)), "sponsors ≥ 0.70 score")
    )
    kpi_strip = f'<div class="ck-kpi-grid">{kpis}</div>'

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
            f'font-weight:700;color:{col};margin-top:4px;'
            f'font-variant-numeric:tabular-nums;">'
            f'{fmt_multiple(rec.median_moic)}</div>'
            f'<div style="color:{P["text_faint"]};font-family:var(--ck-mono);'
            f'font-size:9.5px;letter-spacing:0.10em;margin-top:2px;">'
            f'median MOIC · {rec.deal_count} deals · {cons_label.lower()} consistency</div>'
            f'</div>'
        )
    top5_strip = (
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px;">'
        f'{"".join(top5_cards)}</div>'
    )

    intro = (
        f'<p style="color:{P["text_dim"]};font-size:12px;line-height:1.6;'
        f'margin-bottom:10px;">'
        f'Complement to <a href="/sponsor-heatmap" style="color:{P["accent"]};">'
        f'/sponsor-heatmap</a> (sector × sponsor MOIC grid) and '
        f'<a href="/sponsor-league" style="color:{P["accent"]};">/sponsor-league</a> '
        f'(top-25 by MOIC). This page surfaces the full '
        f'<code style="color:{P["accent"]};font-family:var(--ck-mono);">'
        f'sponsor_track_record</code> module — consistency scoring, '
        f'loss + home-run rates, and per-sponsor sector specialization from '
        f'the corpus.'
        f'</p>'
    )

    body = (
        intro
        + kpi_strip
        + ck_section_header("TOP 5 BY MEDIAN MOIC", "highest realized returns")
        + top5_strip
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
        subtitle=f"{total_sponsors} sponsors · {total_deals} deals · "
                 f"{realized} realized",
    )
