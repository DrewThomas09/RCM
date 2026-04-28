"""`/diligence/comparable-outcomes` — comparable-deal benchmarking.

Partner inputs sector + EV size (or a corpus deal_id), the page
returns the top-N most-similar realized PE deals from the corpus
with their MOIC / IRR distribution.

Public API:
    render_comparable_outcomes_page(qs: dict) -> str
"""
from __future__ import annotations

import html as _html
import urllib.parse as _urlparse
from typing import Any, Dict, List, Optional  # noqa: F401


def _input_form(qs: Dict[str, Any]) -> str:
    """Form so a partner can re-run with different inputs without
    leaving the page."""
    sector = str(qs.get("sector") or "hospital")
    ev_mm = _html.escape(str(qs.get("ev_mm") or ""))
    year = _html.escape(str(qs.get("year") or ""))
    buyer = _html.escape(str(qs.get("buyer") or ""))
    sector_options = []
    for s in ("hospital", "managed_care", "post_acute",
              "physician_practice", "specialty_group"):
        sel = " selected" if s == sector else ""
        sector_options.append(
            f'<option value="{_html.escape(s)}"{sel}>{_html.escape(s)}</option>'
        )
    return (
        '<form method="GET" action="/diligence/comparable-outcomes" '
        'style="display:flex;flex-wrap:wrap;gap:10px;align-items:end;'
        'margin:12px 0 20px;padding:14px 16px;background:#fafbfc;'
        'border:1px solid #e5e7eb;border-radius:6px;">'
        '<div><label style="display:block;font-size:11px;color:#6b7280;'
        'text-transform:uppercase;letter-spacing:0.05em;'
        'margin-bottom:4px;">Sector</label>'
        '<select name="sector" style="padding:6px 8px;border:1px solid '
        '#e5e7eb;border-radius:4px;font-size:13px;">'
        + "".join(sector_options) +
        '</select></div>'
        '<div><label style="display:block;font-size:11px;color:#6b7280;'
        'text-transform:uppercase;letter-spacing:0.05em;'
        'margin-bottom:4px;">Entry EV ($M)</label>'
        f'<input type="number" name="ev_mm" value="{ev_mm}" '
        'placeholder="e.g. 500" min="1" max="50000" step="1" '
        'style="padding:6px 8px;border:1px solid #e5e7eb;'
        'border-radius:4px;font-size:13px;width:120px;"></div>'
        '<div><label style="display:block;font-size:11px;color:#6b7280;'
        'text-transform:uppercase;letter-spacing:0.05em;'
        'margin-bottom:4px;">Year</label>'
        f'<input type="number" name="year" value="{year}" '
        'placeholder="e.g. 2024" min="1990" max="2030" '
        'style="padding:6px 8px;border:1px solid #e5e7eb;'
        'border-radius:4px;font-size:13px;width:100px;"></div>'
        '<div><label style="display:block;font-size:11px;color:#6b7280;'
        'text-transform:uppercase;letter-spacing:0.05em;'
        'margin-bottom:4px;" title="Sponsor name boosts match score '
        'on same-sponsor deals — useful when tracking a particular '
        'PE house\'s playbook">Sponsor (optional)</label>'
        f'<input type="text" name="buyer" value="{buyer}" '
        'placeholder="e.g. New Mountain Capital" '
        'style="padding:6px 8px;border:1px solid #e5e7eb;'
        'border-radius:4px;font-size:13px;width:200px;"></div>'
        '<button type="submit" '
        'style="padding:8px 16px;background:var(--sc-navy);color:#fff;'
        'border:0;border-radius:4px;font-size:13px;font-weight:500;'
        'cursor:pointer;">Find comparables</button>'
        '</form>'
    )


def _fmt_moic(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"{v:.2f}x"


def _fmt_pct(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"{v * 100:.1f}%"


def _fmt_money(v: Optional[float]) -> str:
    if v is None:
        return "—"
    if v >= 1000:
        return f"${v/1000:.1f}B"
    return f"${v:.0f}M"


def _outcome_strip(summary: Dict[str, Any]) -> str:
    """Big stat cards for MOIC + IRR + win rate — what a partner
    would say out loud about the comparable set."""
    moic_med = _fmt_moic(summary["moic"].get("median"))
    moic_p25 = _fmt_moic(summary["moic"].get("p25"))
    moic_p75 = _fmt_moic(summary["moic"].get("p75"))
    irr_med = _fmt_pct(summary["irr"].get("median"))
    irr_p25 = _fmt_pct(summary["irr"].get("p25"))
    irr_p75 = _fmt_pct(summary["irr"].get("p75"))
    win = _fmt_pct(summary.get("win_rate_2_5x"))
    hold = summary.get("hold_years_median")
    hold_s = f"{hold:.1f}y" if hold else "—"

    def _stat(label: str, big: str, sub: str) -> str:
        return (
            f'<div style="flex:1;min-width:160px;padding:14px 16px;'
            f'background:#fff;border:1px solid #e5e7eb;border-radius:8px;">'
            f'<div style="font-size:10px;color:#6b7280;font-weight:600;'
            f'text-transform:uppercase;letter-spacing:0.05em;">'
            f'{label}</div>'
            f'<div style="font-size:24px;font-weight:700;color:var(--sc-navy);'
            f'margin-top:4px;font-variant-numeric:tabular-nums;">{big}</div>'
            f'<div style="font-size:11px;color:#6b7280;margin-top:4px;'
            f'font-variant-numeric:tabular-nums;">{sub}</div>'
            f'</div>'
        )

    return (
        '<div style="display:flex;flex-wrap:wrap;gap:10px;margin:0 0 20px;">'
        + _stat("Median MOIC", moic_med, f"p25 {moic_p25} · p75 {moic_p75}")
        + _stat("Median IRR", irr_med, f"p25 {irr_p25} · p75 {irr_p75}")
        + _stat("Median hold", hold_s,
                f"{summary.get('n_comparables', 0)} comparables")
        + _stat("Win rate (≥2.5x)", win, "fraction of deals clearing the bar")
        + '</div>'
    )


def _breakdown_bar(breakdown: Dict[str, float]) -> str:
    """Stacked horizontal mini-bar showing per-feature contribution
    to the composite match score. Hovering each segment shows the
    feature name + points. Lets a partner instantly see whether a
    65 came from "sector + payer match, size off" or "size + year
    match, sector wrong".
    """
    if not breakdown:
        return ""
    feature_palette = {
        "sector":     "var(--sc-navy)",  # navy — the heaviest weight
        "size":       "#3b82f6",  # blue
        "year":       "#10b981",  # green
        "payer_mix":  "#f59e0b",  # amber
        "buyer_type": "#8b5cf6",  # purple
    }
    feature_max = {
        "sector": 35.0, "size": 20.0, "year": 20.0,
        "payer_mix": 15.0, "buyer_type": 10.0,
    }
    width = 80
    height = 8
    segments: List[str] = []
    x_cursor = 0
    for feat, max_w in feature_max.items():
        # Each feature owns a fixed slice of the bar (proportional
        # to its max weight). Within that slice, fill = actual /
        # max points. Empty fraction shows up as track gray.
        slice_w = max_w / 100.0 * width
        actual = breakdown.get(feat, 0.0)
        fill_pct = actual / max_w if max_w > 0 else 0
        fill_w = slice_w * fill_pct
        color = feature_palette[feat]
        # Title attribute = hover tooltip
        title = f"{feat}: {actual:.1f}/{max_w:.0f}"
        # Filled segment
        if fill_w > 0:
            segments.append(
                f'<rect x="{x_cursor}" y="0" '
                f'width="{fill_w}" height="{height}" fill="{color}">'
                f'<title>{title}</title></rect>'
            )
        # Empty fraction shows track color so segment widths read
        if fill_w < slice_w:
            segments.append(
                f'<rect x="{x_cursor + fill_w}" y="0" '
                f'width="{slice_w - fill_w}" height="{height}" '
                f'fill="#f3f4f6" opacity="0.6"><title>{title}</title></rect>'
            )
        x_cursor += slice_w
    return (
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'aria-label="Match score breakdown" '
        f'style="display:block;margin-top:3px;">'
        + "".join(segments) +
        '</svg>'
    )


def _comparable_row(c: Dict[str, Any]) -> List[str]:
    score = c.get("match_score") or 0
    bg, fg = (
        ("#d1fae5", "#065f46") if score >= 70 else
        ("#fef3c7", "#92400e") if score >= 50 else
        ("#f3f4f6", "#6b7280")
    )
    breakdown = c.get("score_breakdown") or {}
    bar = _breakdown_bar(breakdown)
    score_chip = (
        f'<div>'
        f'<span style="display:inline-block;padding:1px 8px;background:{bg};'
        f'color:{fg};border-radius:9999px;font-size:11px;font-weight:600;'
        f'font-variant-numeric:tabular-nums;">{score:.0f}</span>'
        f'{bar}'
        f'</div>'
    )
    name = (
        f'<div><span style="font-weight:500;color:#1f2937;">'
        f'{_html.escape(c.get("deal_name") or "")}</span>'
        f'<div style="font-family:monospace;font-size:10px;color:#6b7280;'
        f'text-transform:uppercase;margin-top:2px;">'
        f'{_html.escape(c.get("deal_id") or "")}</div></div>'
    )
    reasons = c.get("match_reasons") or []
    reasons_str = (
        '<div style="font-size:11px;color:#6b7280;">'
        + " · ".join(_html.escape(r) for r in reasons)
        + '</div>'
    ) if reasons else ""
    return [
        score_chip,
        name + reasons_str,
        _html.escape(str(c.get("year") or "—")),
        _html.escape(c.get("buyer") or "—"),
        _fmt_money(c.get("ev_mm")),
        _fmt_moic(c.get("realized_moic")),
        _fmt_pct(c.get("realized_irr")),
        f"{c.get('hold_years'):.1f}y" if c.get("hold_years") else "—",
    ]


def render_comparable_outcomes_page(
    qs: Dict[str, Any],
    *, db_path: Optional[str] = None,
) -> str:
    from . import _web_components as _wc
    from ._chartis_kit import chartis_shell
    from ..diligence.comparable_outcomes import benchmark_deal
    from ..data_public.deals_corpus import DealsCorpus

    header = _wc.page_header(
        "Comparable-deal outcomes",
        subtitle=(
            "For a target deal profile (sector + EV + year), surface "
            "the most-similar realized PE deals in the corpus and "
            "their MOIC / IRR distribution. The "
            "\"what would this trade for?\" answer in one screen."
        ),
        crumbs=[("Dashboard", "/dashboard"),
                ("Comparable outcomes", None)],
    )

    form = _input_form(qs)

    # No inputs yet → just the form. First-load pitch.
    has_inputs = bool(qs.get("sector")) or bool(qs.get("ev_mm"))
    if not has_inputs:
        body = (
            _wc.web_styles()
            + _wc.responsive_container(
                header
                + form
                + _wc.section_card(
                    "Tip",
                    '<p style="margin:0;font-size:13px;color:#4b5563;">'
                    'Enter a sector + entry EV (in $M) above. The '
                    'tool ranks every realized deal in the corpus by '
                    'similarity (sector / size / vintage / payer mix '
                    '/ buyer) and shows the top 10 with their realized '
                    'MOIC and IRR. Use this when sizing a new bid or '
                    'pressure-testing a sponsor\'s base case.</p>'
                )
            )
            + _wc.sortable_table_js()
        )
        return chartis_shell(body, "Comparable outcomes",
                             active_nav="/diligence/comparable-outcomes")

    # Build the target profile from query string
    try:
        ev_mm = float(qs.get("ev_mm")) if qs.get("ev_mm") else None
    except (TypeError, ValueError):
        ev_mm = None
    try:
        year = int(qs.get("year")) if qs.get("year") else None
    except (TypeError, ValueError):
        year = None
    target = {
        "sector": (qs.get("sector") or "hospital"),
        "ev_mm": ev_mm,
        "year": year,
        "buyer": qs.get("buyer") or "",
    }

    try:
        # Use the same SQLite DB as the rest of the platform —
        # corpus + portfolio + audit all share the file.
        if not db_path:
            import os as _os
            db_path = _os.environ.get("RCM_MC_DB",
                                      "/tmp/rcm_mc.db")
        corpus = DealsCorpus(db_path)
        try:
            corpus.seed(skip_if_populated=True)
        except Exception:  # noqa: BLE001
            pass
        result = benchmark_deal(corpus, target, top_n=10)
    except Exception as exc:  # noqa: BLE001
        body = (
            _wc.web_styles()
            + _wc.responsive_container(
                header + form
                + _wc.section_card(
                    "Couldn't run benchmark",
                    f'<p style="margin:0;color:#991b1b;">'
                    f'Error: {_html.escape(type(exc).__name__)}. '
                    f'The corpus may not be initialized — try running '
                    f'<code>rcm-mc data refresh</code> first.</p>'
                )
            )
        )
        return chartis_shell(body, "Comparable outcomes",
                             active_nav="/diligence/comparable-outcomes")

    summary = result["outcome_distribution"]
    rows = [_comparable_row(c) for c in result["comparables"]]
    table = _wc.sortable_table(
        ["Match", "Deal", "Year", "Buyer", "EV", "MOIC", "IRR", "Hold"],
        rows,
        id="comp-table", hide_columns_sm=[2, 7],
        filterable=True,
        filter_placeholder="Filter by deal name or buyer…",
    )

    breakdown_legend = (
        '<div style="display:flex;flex-wrap:wrap;gap:14px;'
        'font-size:11px;color:#6b7280;margin:8px 0 0;'
        'padding:8px 12px;background:#fafbfc;border-radius:6px;">'
        '<span style="font-weight:600;color:#374151;'
        'text-transform:uppercase;letter-spacing:0.05em;">'
        'Match-score bar</span>'
        '<span><span style="display:inline-block;width:10px;'
        'height:8px;background:var(--sc-navy);margin-right:4px;'
        'vertical-align:middle;"></span>sector (35)</span>'
        '<span><span style="display:inline-block;width:10px;'
        'height:8px;background:#3b82f6;margin-right:4px;'
        'vertical-align:middle;"></span>size (20)</span>'
        '<span><span style="display:inline-block;width:10px;'
        'height:8px;background:#10b981;margin-right:4px;'
        'vertical-align:middle;"></span>year (20)</span>'
        '<span><span style="display:inline-block;width:10px;'
        'height:8px;background:#f59e0b;margin-right:4px;'
        'vertical-align:middle;"></span>payer mix (15)</span>'
        '<span><span style="display:inline-block;width:10px;'
        'height:8px;background:#8b5cf6;margin-right:4px;'
        'vertical-align:middle;"></span>sponsor (10)</span>'
        '</div>'
    )

    # Time-saver: surface CSV + memo-bullet exports in one click. The
    # partner already filled out sector/ev/year — preserve that
    # through to the download URLs so the file matches what's on
    # screen.
    import urllib.parse as _up
    export_qs = _up.urlencode({
        k: str(v) for k, v in target.items()
        if v is not None and v != ""
    })
    btn_style = (
        "display:inline-flex;align-items:center;gap:6px;"
        "padding:8px 14px;border:1px solid #d1d5db;border-radius:6px;"
        "background:#fff;color:var(--sc-navy);font-size:13px;font-weight:600;"
        "text-decoration:none;cursor:pointer;"
    )
    export_bar = (
        '<div style="display:flex;flex-wrap:wrap;gap:10px;'
        'align-items:center;margin:12px 0;">'
        '<span style="font-size:11px;color:#6b7280;font-weight:600;'
        'text-transform:uppercase;letter-spacing:0.05em;'
        'margin-right:4px;">One-click export</span>'
        f'<a href="/api/diligence/comparable-outcomes.csv?{export_qs}" '
        f'style="{btn_style}" download>⬇ CSV (with score breakdown)</a>'
        f'<a href="/api/diligence/comparable-outcomes.memo?{export_qs}" '
        f'style="{btn_style}" target="_blank" rel="noopener">'
        '📋 Memo bullets (paste into deal memo)</a>'
        '</div>'
    )

    inner = (
        header
        + form
        + _outcome_strip(summary)
        + export_bar
        + _wc.section_card(
            f"Top {len(rows)} comparables — sorted by match score",
            table + breakdown_legend, pad=False,
        )
    )
    body = (
        _wc.web_styles()
        + _wc.responsive_container(inner)
        + _wc.sortable_table_js()
    )
    return chartis_shell(body, "Comparable outcomes",
                         active_nav="/diligence/comparable-outcomes")
