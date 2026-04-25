"""`/diligence/sponsor-detail?sponsor=X` — single-sponsor drill-down.

When a sponsor pitches "we're targeting a 3.5x base case" on a new
deal, the partner needs to know what THIS sponsor has actually
realized historically — not a 30-row league table, just one
focused detail view of the sponsor's track record.

What this page surfaces (for the queried sponsor name):

  - Top stat strip: deal count, median MOIC, win rate (≥2.5x),
    consistency score, vs corpus median delta
  - Vintage timeline: which years they've been active + count per year
  - Sector breakdown: where they invest
  - Per-deal table: every deal sortable by year/MOIC/IRR/EV
  - "vs corpus" comparison so the partner sees if median MOIC
    beats or trails the broader corpus median

Reuses ``data_public.sponsor_track_record.build_sponsor_records``
so the aggregation never drifts from the league-table page.

Public API::

    render_sponsor_detail_page(qs, db_path) -> str
"""
from __future__ import annotations

import html as _html
import urllib.parse as _urlparse
from typing import Any, Dict, List, Optional


def _input_form(qs: Dict[str, Any]) -> str:
    sponsor = _html.escape(str(qs.get("sponsor") or ""))
    return (
        '<form method="GET" action="/diligence/sponsor-detail" '
        'style="display:flex;gap:10px;align-items:end;'
        'margin:12px 0 20px;padding:14px 16px;background:#fafbfc;'
        'border:1px solid #e5e7eb;border-radius:6px;">'
        '<div style="flex:1;"><label style="display:block;'
        'font-size:11px;color:#6b7280;text-transform:uppercase;'
        'letter-spacing:0.05em;margin-bottom:4px;">'
        'Sponsor name</label>'
        f'<input type="text" name="sponsor" value="{sponsor}" '
        'placeholder="e.g. New Mountain Capital, KKR, HCA" '
        'list="sponsor-suggestions" '
        'style="padding:6px 8px;border:1px solid #e5e7eb;'
        'border-radius:4px;font-size:13px;width:100%;"></div>'
        '<button type="submit" '
        'style="padding:8px 16px;background:#1F4E78;color:#fff;'
        'border:0;border-radius:4px;font-size:13px;font-weight:500;'
        'cursor:pointer;">Run track record</button>'
        '</form>'
    )


def _suggestions_datalist(records: Dict[str, Any]) -> str:
    """Type-ahead options so the partner doesn't have to guess
    the canonical spelling."""
    if not records:
        return ""
    options = []
    for name in sorted(records.keys()):
        if name and name != "Unknown":
            options.append(f'<option value="{_html.escape(name)}">')
    return f'<datalist id="sponsor-suggestions">{"".join(options)}</datalist>'


def _stat(label: str, big: str, sub: str = "",
          tone: str = "neutral") -> str:
    palette = {
        "alert":    ("#fef2f2", "#991b1b"),
        "positive": ("#f0fdf4", "#065f46"),
        "warn":     ("#fffbeb", "#92400e"),
        "neutral":  ("#fff",    "#1F4E78"),
    }
    bg, fg = palette.get(tone, palette["neutral"])
    return (
        f'<div style="flex:1;min-width:160px;padding:14px 16px;'
        f'background:{bg};border:1px solid #e5e7eb;border-radius:8px;">'
        f'<div style="font-size:10px;color:#6b7280;font-weight:600;'
        f'text-transform:uppercase;letter-spacing:0.05em;">'
        f'{_html.escape(label)}</div>'
        f'<div style="font-size:24px;font-weight:700;color:{fg};'
        f'margin-top:4px;font-variant-numeric:tabular-nums;">'
        f'{_html.escape(big)}</div>'
        f'<div style="font-size:11px;color:#6b7280;margin-top:4px;">'
        f'{_html.escape(sub)}</div>'
        f'</div>'
    )


def _fmt_moic(v: Optional[float]) -> str:
    return f"{v:.2f}x" if v is not None else "—"


def _fmt_pct(v: Optional[float]) -> str:
    return f"{v * 100:.0f}%" if v is not None else "—"


def _fmt_money(v: Optional[float]) -> str:
    if v is None:
        return "—"
    if v >= 1000:
        return f"${v / 1000:.1f}B"
    return f"${v:.0f}M"


def _vintage_bars(years_active: List[int],
                  deal_count_per_year: Dict[int, int]) -> str:
    """Mini timeline of activity by year — tells partner "this
    sponsor was busy 2016-2018, dormant since." Inline SVG bars."""
    if not deal_count_per_year:
        return ""
    sorted_years = sorted(deal_count_per_year.keys())
    if len(sorted_years) < 2:
        return ""
    min_y = sorted_years[0]
    max_y = sorted_years[-1]
    span = max(1, max_y - min_y)
    max_count = max(deal_count_per_year.values())

    width = 320
    height = 50
    bar_h_max = 36
    gap = 2
    n_bars = max_y - min_y + 1
    bar_w = max(2.0, (width - n_bars * gap) / n_bars)

    bars: List[str] = []
    labels: List[str] = []
    for i, y in enumerate(range(min_y, max_y + 1)):
        c = deal_count_per_year.get(y, 0)
        h = (c / max_count) * bar_h_max if max_count else 0
        x = i * (bar_w + gap)
        color = "#1F4E78" if c > 0 else "#f3f4f6"
        bars.append(
            f'<rect x="{x:.1f}" y="{height - h - 12:.1f}" '
            f'width="{bar_w:.1f}" height="{h:.1f}" '
            f'fill="{color}" rx="1"><title>{y}: {c} deal'
            f'{"s" if c != 1 else ""}</title></rect>'
        )
    # First and last year labels under the bars
    labels.append(
        f'<text x="0" y="{height - 1}" font-size="10" '
        f'fill="#6b7280" font-family="monospace">{min_y}</text>'
    )
    labels.append(
        f'<text x="{width - 24}" y="{height - 1}" font-size="10" '
        f'fill="#6b7280" font-family="monospace">{max_y}</text>'
    )
    return (
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'aria-label="Vintage activity timeline">'
        + "".join(bars) + "".join(labels) +
        '</svg>'
    )


def _sector_pie(sectors_with_counts: Dict[str, int]) -> str:
    """Compact sector breakdown — bar form, not pie (pies are
    notoriously hard to read at small sizes)."""
    if not sectors_with_counts:
        return ""
    total = sum(sectors_with_counts.values())
    if total == 0:
        return ""
    parts: List[str] = []
    for sector, count in sorted(sectors_with_counts.items(),
                                key=lambda t: t[1], reverse=True)[:6]:
        pct = (count / total) * 100
        bar_w = int(round(pct))
        parts.append(
            f'<div style="display:grid;grid-template-columns:'
            f'140px 1fr 60px;align-items:center;gap:10px;'
            f'padding:3px 0;font-size:12px;">'
            f'<span style="color:#374151;white-space:nowrap;'
            f'overflow:hidden;text-overflow:ellipsis;">'
            f'{_html.escape(sector)}</span>'
            f'<div style="background:#f3f4f6;border-radius:3px;'
            f'height:12px;overflow:hidden;">'
            f'<div style="background:#1F4E78;height:100%;'
            f'width:{bar_w}%;"></div></div>'
            f'<span style="color:#6b7280;font-variant-numeric:'
            f'tabular-nums;text-align:right;">{count} · '
            f'{pct:.0f}%</span></div>'
        )
    return "".join(parts)


def render_sponsor_detail_page(qs: Dict[str, Any],
                               *, db_path: Optional[str] = None) -> str:
    from . import _web_components as _wc
    from ._chartis_kit import chartis_shell
    from ..data_public.deals_corpus import DealsCorpus
    from ..data_public.sponsor_track_record import (
        build_sponsor_records,
    )

    header = _wc.page_header(
        "Sponsor track record",
        subtitle=(
            "Type a sponsor name. The tool computes their full "
            "track record from the corpus — every realized deal, "
            "median MOIC, win rate, sector breakdown, vintage "
            "timeline. Use when evaluating a sponsor's pitched "
            "base case."
        ),
        crumbs=[("Dashboard", "/dashboard"),
                ("Sponsor track record", None)],
    )

    # Pull corpus + build records once
    if not db_path:
        import os as _os
        db_path = _os.environ.get("RCM_MC_DB", "/tmp/rcm_mc.db")
    try:
        corpus = DealsCorpus(db_path)
        try:
            corpus.seed(skip_if_populated=True)
        except Exception:  # noqa: BLE001
            pass
        all_deals = corpus.list(limit=2000)
        records = build_sponsor_records(all_deals)
    except Exception as exc:  # noqa: BLE001
        body = (
            _wc.web_styles()
            + _wc.responsive_container(
                header
                + _input_form(qs)
                + _wc.section_card(
                    "Couldn't load the sponsor index",
                    f'<p style="margin:0;color:#991b1b;">'
                    f'{_html.escape(type(exc).__name__)}: '
                    f'{_html.escape(str(exc))}</p>'
                )
            )
        )
        return chartis_shell(body, "Sponsor track record",
                             active_nav="/diligence/sponsor-detail")

    sponsor_input = (qs.get("sponsor") or "").strip()
    sponsor_lookup = {k.lower(): k for k in records.keys()}

    if not sponsor_input:
        # Pitch + form, no results yet
        body = (
            _wc.web_styles()
            + _wc.responsive_container(
                header
                + _input_form(qs)
                + _suggestions_datalist(records)
                + _wc.section_card(
                    "How to use this",
                    f'<p style="margin:0 0 8px;font-size:13px;color:#4b5563;">'
                    f'Type a sponsor name above (autocomplete from '
                    f'{len(records)} sponsors in the corpus). The '
                    f'detail view shows their realized MOIC '
                    f'distribution, vintage activity, sector '
                    f'specialization, and per-deal outcomes — '
                    f'enough to gut-check whether their pitched '
                    f'base case is realistic.</p>'
                    f'<p style="margin:0;font-size:12px;color:#6b7280;">'
                    f'For the full league table across every '
                    f'sponsor, see <a href="/sponsor-track-record" '
                    f'style="color:#1F4E78;">/sponsor-track-record</a>.'
                    f'</p>'
                )
            )
        )
        return chartis_shell(body, "Sponsor track record",
                             active_nav="/diligence/sponsor-detail")

    # Match sponsor (case-insensitive)
    matched_name = sponsor_lookup.get(sponsor_input.lower())
    if matched_name is None:
        # Suggest closest matches
        partial = [k for k in records.keys()
                   if sponsor_input.lower() in k.lower()][:8]
        suggestions = "".join(
            f'<a href="/diligence/sponsor-detail?'
            f'sponsor={_urlparse.quote(s)}" '
            f'style="display:inline-block;margin:2px 4px 2px 0;'
            f'padding:4px 10px;background:#f0f6fc;color:#1F4E78;'
            f'border:1px solid #d0e3f0;border-radius:4px;'
            f'font-size:12px;text-decoration:none;">'
            f'{_html.escape(s)}</a>'
            for s in partial
        )
        body = (
            _wc.web_styles()
            + _wc.responsive_container(
                header
                + _input_form(qs)
                + _suggestions_datalist(records)
                + _wc.section_card(
                    f'No exact match for "{_html.escape(sponsor_input)}"',
                    (
                        f'<p style="margin:0 0 12px;color:#6b7280;'
                        f'font-size:13px;">{len(partial)} '
                        f'partial-match sponsor{"s" if len(partial) != 1 else ""} '
                        f'in the corpus:</p>'
                        + (suggestions or
                           '<p style="font-style:italic;color:#9ca3af;">'
                           '(none — try a different spelling)</p>')
                    )
                )
            )
        )
        return chartis_shell(body, "Sponsor track record",
                             active_nav="/diligence/sponsor-detail")

    rec = records[matched_name]

    # Corpus-median benchmark for the "vs corpus" comparison
    realized_corpus_moics = [
        d.get("realized_moic") for d in all_deals
        if d.get("realized_moic") is not None
    ]
    realized_corpus_moics.sort()
    corpus_median = (
        realized_corpus_moics[len(realized_corpus_moics) // 2]
        if realized_corpus_moics else None
    )

    # vs-corpus delta tone
    vs_tone = "neutral"
    delta_str = "—"
    if rec.median_moic is not None and corpus_median is not None:
        delta = rec.median_moic - corpus_median
        if delta >= 0.3:
            vs_tone = "positive"
        elif delta <= -0.3:
            vs_tone = "alert"
        sign = "+" if delta >= 0 else ""
        delta_str = f"{sign}{delta:.2f}x vs corpus {corpus_median:.2f}x"

    # Top stat strip
    stats = (
        '<div style="display:flex;flex-wrap:wrap;gap:10px;'
        'margin:0 0 20px;">'
        + _stat("Deals tracked",
                f"{rec.deal_count}",
                f"{rec.realized_count} realized")
        + _stat("Median MOIC",
                _fmt_moic(rec.median_moic),
                delta_str, tone=vs_tone)
        + _stat("Home-run rate (>3.0x)",
                _fmt_pct(rec.home_run_rate),
                f"loss rate {_fmt_pct(rec.loss_rate)}")
        + _stat("Median IRR",
                _fmt_pct(rec.median_irr),
                f"hold {rec.median_hold_years:.1f}y"
                if rec.median_hold_years else "")
        + _stat("Consistency score",
                f"{rec.consistency_score:.0f}",
                "0-100 — higher = predictable")
        + '</div>'
    )

    # Vintage timeline
    deal_count_per_year: Dict[int, int] = {}
    sponsor_deals = [d for d in all_deals
                     if matched_name in (d.get("buyer") or "")]
    for d in sponsor_deals:
        y = d.get("year")
        if y:
            deal_count_per_year[int(y)] = (
                deal_count_per_year.get(int(y), 0) + 1)

    vintage_card = _wc.section_card(
        "Vintage activity",
        '<p style="margin:0 0 8px;font-size:12px;color:#6b7280;">'
        f'{rec.deal_count} deals across '
        f'{len(deal_count_per_year)} active year'
        f'{"s" if len(deal_count_per_year) != 1 else ""}'
        '. Bar height = deal count.</p>'
        + _vintage_bars(rec.years_active, deal_count_per_year),
    )

    # Sector breakdown
    sector_counts: Dict[str, int] = {}
    for d in sponsor_deals:
        s = d.get("sector") or "—"
        sector_counts[s] = sector_counts.get(s, 0) + 1
    sector_card = _wc.section_card(
        "Sector specialization",
        '<p style="margin:0 0 10px;font-size:12px;color:#6b7280;">'
        f'Where {_html.escape(matched_name)} has invested '
        f'historically.</p>'
        + (_sector_pie(sector_counts) or
           '<p style="font-style:italic;color:#9ca3af;">'
           'No sector data on these deals.</p>'),
    )

    # Per-deal table
    rows: List[List[str]] = []
    for d in sorted(sponsor_deals,
                    key=lambda x: (x.get("year") or 0),
                    reverse=True):
        moic = d.get("realized_moic")
        moic_chip = _fmt_moic(moic)
        if moic is not None:
            if moic >= 2.5:
                moic_chip = (
                    f'<span style="color:#065f46;font-weight:600;">'
                    f'{moic_chip}</span>'
                )
            elif moic < 1.0:
                moic_chip = (
                    f'<span style="color:#991b1b;font-weight:600;">'
                    f'{moic_chip}</span>'
                )
        rows.append([
            _html.escape(d.get("deal_name") or
                         d.get("source_id") or ""),
            _html.escape(str(d.get("year") or "—")),
            _html.escape(d.get("sector") or "—"),
            _fmt_money(d.get("ev_mm")),
            moic_chip,
            _fmt_pct(d.get("realized_irr")),
            (f"{d.get('hold_years'):.1f}y"
             if d.get("hold_years") else "—"),
        ])
    deals_table = _wc.sortable_table(
        ["Deal", "Year", "Sector", "EV", "MOIC", "IRR", "Hold"],
        rows,
        id="sponsor-deals", hide_columns_sm=[2, 6],
        filterable=True,
        filter_placeholder="Filter by deal name or sector…",
    )

    inner = (
        header
        + _input_form(qs)
        + _suggestions_datalist(records)
        + f'<h2 style="font-size:18px;margin:8px 0 12px;'
        f'color:#0f172a;">{_html.escape(matched_name)}</h2>'
        + stats
        + vintage_card
        + sector_card
        + _wc.section_card(
            f"All {len(rows)} deals",
            deals_table, pad=False,
        )
    )

    body = (
        _wc.web_styles()
        + _wc.responsive_container(inner)
        + _wc.sortable_table_js()
    )
    return chartis_shell(body, "Sponsor track record",
                         active_nav="/diligence/sponsor-detail")
