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

_EXPLAINER_CSS = """<style>
.ck-co-explainer{font-family:var(--sc-serif,'Georgia',serif);
  font-size:15px;line-height:1.55;color:var(--sc-text-dim,#465366);
  margin:0 0 var(--sc-s-6,18px) 0;max-width:72ch;}
.ck-co-explainer em{color:var(--sc-teal-ink,#155752);font-style:italic;}
</style>"""


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
        # 2026-05-28 batch 43 · Tier-4 trope removal — cap radius at 2px.
        'margin:12px 0 20px;padding:14px 16px;background:#f7f3ea;'
        'border:1px solid #d6cfc0;border-radius:2px;">'
        '<div><label style="display:block;font-size:11px;color:#7a8699;'
        'text-transform:uppercase;letter-spacing:0.05em;'
        'margin-bottom:4px;">Sector</label>'
        '<select name="sector" style="padding:6px 8px;border:1px solid '
        '#d6cfc0;border-radius:4px;font-size:13px;">'
        + "".join(sector_options) +
        '</select></div>'
        '<div><label style="display:block;font-size:11px;color:#7a8699;'
        'text-transform:uppercase;letter-spacing:0.05em;'
        'margin-bottom:4px;">Entry EV ($M)</label>'
        f'<input type="number" name="ev_mm" value="{ev_mm}" '
        'placeholder="e.g. 500" min="1" max="50000" step="1" '
        'style="padding:6px 8px;border:1px solid #d6cfc0;'
        'border-radius:4px;font-size:13px;width:120px;"></div>'
        '<div><label style="display:block;font-size:11px;color:#7a8699;'
        'text-transform:uppercase;letter-spacing:0.05em;'
        'margin-bottom:4px;">Year</label>'
        f'<input type="number" name="year" value="{year}" '
        'placeholder="e.g. 2024" min="1990" max="2030" '
        'style="padding:6px 8px;border:1px solid #d6cfc0;'
        'border-radius:4px;font-size:13px;width:100px;"></div>'
        '<div><label style="display:block;font-size:11px;color:#7a8699;'
        'text-transform:uppercase;letter-spacing:0.05em;'
        'margin-bottom:4px;" title="Sponsor name boosts match score '
        'on same-sponsor deals; useful when tracking a particular '
        'PE house\'s playbook">Sponsor (optional)</label>'
        f'<input type="text" name="buyer" value="{buyer}" '
        'placeholder="e.g. New Mountain Capital" '
        'style="padding:6px 8px;border:1px solid #d6cfc0;'
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
    # Entry EV/EBITDA — the bid-pricing anchor. Multiples exist only on
    # comps that disclose both EV and entry EBITDA; the sub names that n
    # so a thin multiple sample reads as thin.
    mult = summary.get("entry_multiple") or {}
    mult_med = mult.get("median")
    mult_med_s = f"{mult_med:.1f}x" if mult_med else "—"
    mult_p25 = mult.get("p25")
    mult_p75 = mult.get("p75")
    mult_sub = (
        f"p25 {mult_p25:.1f}x · p75 {mult_p75:.1f}x · {mult.get('n', 0)} disclosed"
        if mult_med and mult_p25 is not None and mult_p75 is not None
        else "EV + entry EBITDA disclosed on too few comps"
    )

    def _stat(label: str, big: str, sub: str) -> str:
        # 2026-05-28 batch 43 · Tier-4 trope removal — cap radius at 2px.
        return (
            f'<div style="flex:1;min-width:160px;padding:14px 16px;'
            f'background:#fff;border:1px solid #d6cfc0;border-radius:2px;">'
            f'<div style="font-size:10px;color:#7a8699;font-weight:600;'
            f'text-transform:uppercase;letter-spacing:0.05em;">'
            f'{label}</div>'
            f'<div style="font-size:24px;font-weight:700;color:var(--sc-navy);'
            f'margin-top:4px;font-variant-numeric:tabular-nums;">{big}</div>'
            f'<div style="font-size:11px;color:#7a8699;margin-top:4px;'
            f'font-variant-numeric:tabular-nums;">{sub}</div>'
            f'</div>'
        )

    return (
        '<div style="display:flex;flex-wrap:wrap;gap:10px;margin:0 0 20px;">'
        + _stat("Median MOIC", moic_med, f"p25 {moic_p25} · p75 {moic_p75}")
        + _stat("Median IRR", irr_med, f"p25 {irr_p25} · p75 {irr_p75}")
        + _stat("Entry EV/EBITDA", mult_med_s, mult_sub)
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
    # Editorial categorical hues — distinct but on-palette (no
    # blue/green/purple from Tailwind). The legend below mirrors these.
    feature_palette = {
        "sector":     "var(--sc-navy)",  # navy — the heaviest weight
        "size":       "#1F7A75",  # teal
        "year":       "#b8732a",  # amber
        "payer_mix":  "#b5321e",  # red
        "buyer_type": "#a98545",  # ochre
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
                f'fill="#E8E0D0" opacity="0.6"><title>{title}</title></rect>'
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
        ("#d9ece2", "#0a6a48") if score >= 70 else
        ("#f2e7d1", "#7a4c16") if score >= 50 else
        ("#E8E0D0", "#7a8699")
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
    # Connectivity: link the comp through to its corpus-deal detail.
    # /library is keyed by source_id (TEXT, e.g. "seed_001") — NOT the
    # integer deal_id shown as the code below.
    _sid = c.get("source_id")
    _name_txt = _html.escape(c.get("deal_name") or "")
    if _sid:
        _name_inner = (
            f'<a href="/library/{_urlparse.quote(str(_sid))}" '
            f'style="font-weight:500;color:var(--ck-accent,#155752);'
            f'text-decoration:none;">{_name_txt}</a>'
        )
    else:
        _name_inner = f'<span style="font-weight:500;color:#1a2332;">{_name_txt}</span>'
    name = (
        f'<div>{_name_inner}'
        f'<div style="font-family:var(--sc-mono,monospace);font-size:10px;color:#7a8699;'
        f'text-transform:uppercase;margin-top:2px;">'
        f'{_html.escape(c.get("deal_id") or "")}</div></div>'
    )
    reasons = c.get("match_reasons") or []
    reasons_str = (
        '<div style="font-size:11px;color:#7a8699;">'
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
    from ._chartis_kit import (
        chartis_shell, ck_eyebrow, ck_next_section, ck_page_title,
        ck_source_purpose)
    from ..diligence.comparable_outcomes import benchmark_deal
    from ..data_public.deals_corpus import DealsCorpus

    header = ck_page_title(
        "Comparable-deal outcomes",
        eyebrow="DILIGENCE · MARKET COMPARABLES",
        # Keep the meta a short scannable label — the meta row is
        # CSS-uppercased, so a full sentence here renders as a dense
        # all-caps block. The "what would this trade for?" explanation
        # lives in the readable Tip card below in normal case.
        meta="Realized MOIC / IRR on the most-similar corpus deals",
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
                    '<p style="margin:0;font-size:13px;color:#465366;">'
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
                    f'<p style="margin:0;color:#8a2a1a;">'
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

    # 2026-05-28 batch 43 · Tier-4 trope removal — cap radius at 2px.
    breakdown_legend = (
        '<div style="display:flex;flex-wrap:wrap;gap:14px;'
        'font-size:11px;color:#7a8699;margin:8px 0 0;'
        'padding:8px 12px;background:#f7f3ea;border-radius:2px;">'
        '<span style="font-weight:600;color:#1a2332;'
        'text-transform:uppercase;letter-spacing:0.05em;">'
        'Match-score bar</span>'
        '<span><span style="display:inline-block;width:10px;'
        'height:8px;background:var(--sc-navy);margin-right:4px;'
        'vertical-align:middle;"></span>sector (35)</span>'
        '<span><span style="display:inline-block;width:10px;'
        'height:8px;background:#1F7A75;margin-right:4px;'
        'vertical-align:middle;"></span>size (20)</span>'
        '<span><span style="display:inline-block;width:10px;'
        'height:8px;background:#b8732a;margin-right:4px;'
        'vertical-align:middle;"></span>year (20)</span>'
        '<span><span style="display:inline-block;width:10px;'
        'height:8px;background:#b5321e;margin-right:4px;'
        'vertical-align:middle;"></span>payer mix (15)</span>'
        '<span><span style="display:inline-block;width:10px;'
        'height:8px;background:#a98545;margin-right:4px;'
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
        "padding:8px 14px;border:1px solid #d6cfc0;border-radius:6px;"
        "background:#fff;color:var(--sc-navy);font-size:13px;font-weight:600;"
        "text-decoration:none;cursor:pointer;"
    )
    export_bar = (
        '<div style="display:flex;flex-wrap:wrap;gap:10px;'
        'align-items:center;margin:12px 0;">'
        '<span style="font-size:11px;color:#7a8699;font-weight:600;'
        'text-transform:uppercase;letter-spacing:0.05em;'
        'margin-right:4px;">One-click export</span>'
        f'<a href="/api/diligence/comparable-outcomes.csv?{export_qs}" '
        f'style="{btn_style}" download>⬇ CSV (with score breakdown)</a>'
        f'<a href="/api/diligence/comparable-outcomes.memo?{export_qs}" '
        f'style="{btn_style}" target="_blank" rel="noopener">'
        '📋 Memo bullets (paste into deal memo)</a>'
        '</div>'
    )

    # 2026-06-11 de-clutter (user-reported "too much data under the
    # title"): the 3-card KPI strip duplicated the outcome strip card
    # for card — matched count (hold-card sub), P50/median MOIC, and
    # win rate all rendered twice within one screen. The outcome strip
    # is the single results readout now; the matched count also lives
    # in the title meta.
    n_comp = summary.get("n_comparables", 0) if summary else 0

    # Phase QQQ: print-preview affordance — partners print this
    # surface as their corpus-comparable benchmark for IC. ?print=1
    # hides the input form, export bar, kpi strip, and Up-next; keeps
    # just the outcome strip + comparables table.
    import urllib.parse as _urlparse
    print_preview = str(qs.get("print") or "") == "1"
    if print_preview:
        exit_qs = {k: v for k, v in qs.items() if k != "print"}
        exit_qstr = "?" + _urlparse.urlencode(exit_qs, doseq=True) if exit_qs else ""
        inner = (
            '<div class="ck-print-preview-bar">'
            '<span class="ck-print-preview-meta">Print preview · '
            'Comparable outcomes</span>'
            f'<a href="/diligence/comparable-outcomes{_html.escape(exit_qstr)}" '
            'class="ck-print-preview-exit">Exit preview</a>'
            '</div>'
            + ck_eyebrow("Comparable Outcomes")
            + header
            + _outcome_strip(summary)
            + _wc.section_card(
                f"Top {len(rows)} comparables — sorted by match score",
                table + breakdown_legend, pad=False,
            )
        )
        body = (
            '<div class="ck-print-preview">'
            + _wc.web_styles()
            + _wc.responsive_container(inner)
            + _wc.sortable_table_js()
            + '</div>'
        )
    else:
        print_qs = {**{k: v for k, v in qs.items() if k != "print"}, "print": "1"}
        print_qstr = "?" + _urlparse.urlencode(print_qs, doseq=True)
        print_cta = (
            '<div class="ck-print-preview-cta" style="padding:8px 16px;">'
            f'<a href="/diligence/comparable-outcomes{_html.escape(print_qstr)}" '
            'class="ck-link">Preview print version →</a>'
            '</div>'
        )
        sector_label = _html.escape(str(target.get("sector") or ""))
        # Reciprocal linkage with the sizing catalogue: when the chosen
        # sector maps to a TAM/SAM template, offer "size this market".
        try:
            from ..diligence.tam_sam import template_for_sector
            _ts_key = template_for_sector(target.get("sector"))
        except Exception:  # noqa: BLE001
            _ts_key = None
        size_link = (
            f'<p style="margin:6px 2px 0;font-size:11.5px;">'
            f'<a href="/diligence/tam-sam?template={_ts_key}" '
            'style="color:var(--sc-navy);font-weight:600;'
            'text-decoration:none;">Size this market in the TAM/SAM '
            'Builder →</a></p>' if _ts_key else ""
        )
        page_title_block = (
            ck_page_title(
            "Comparable Outcomes",
            eyebrow="DILIGENCE · MARKET COMPARABLES",
            meta=f"{n_comp} matched · {sector_label}" if sector_label else f"{n_comp} matched",
        )
            + ck_source_purpose(
                purpose="Sanity-check bid pricing against realized MOIC/IRR/exit-multiple distributions on comparable deals (sector × size × hold × exit channel).",
                universe="corpus",
                confidence="illustrative",
                source="Platform deal corpus — real deals with MOIC/IRR modeled where not publicly disclosed, not your fund's realized benchmark. Read the distributions as directional context.",
                next_action="Carry the comp distribution into the IC narrative",
                next_href="/diligence/ic-packet",
            )
        )
        # ONE editorial lede under the title — this page stacked three
        # near-identical explainers (source_purpose band + page_explainer
        # + this lede), each restating "realized MOIC/IRR from the
        # corpus, sanity-check bid pricing". The source_purpose band
        # keeps the structured provenance; this single serif sentence
        # keeps the editorial voice; the page_explainer (a verbatim
        # restatement of both) is gone.
        explainer_html = (
            '<p class="ck-co-explainer">'
            '<em>What deals like this actually returned.</em> '
            "Realized-MOIC distribution across corpus deals matched on "
            "profile distance — sector, size, vintage, payer mix. Use "
            "the bands as the underwriting reality check; the bear case "
            "should land near the corpus P25."
            '</p>'
        )
        # Cross-link these illustrative comparables to the real, sourced set —
        # sponsor-aware when the partner filtered by a buyer.
        from urllib.parse import quote as _q
        from ..data_public.verified_deals import (
            verified_deal_count, verified_deals_for_sponsor,
        )
        _buyer = str(qs.get("buyer") or "").strip()
        _nv = len(verified_deals_for_sponsor(_buyer)) if _buyer else 0
        if _nv:
            _vd_link = (
                f'<a href="/verified-deals?sponsor={_q(_buyer)}" '
                'style="color:var(--sc-navy);font-weight:600;text-decoration:none;">'
                f'{_nv} real, sourced {_html.escape(_buyer)} '
                f'deal{"s" if _nv != 1 else ""} →</a>'
            )
        else:
            _vd_link = (
                '<a href="/verified-deals" style="color:var(--sc-navy);'
                f'text-decoration:none;">the {verified_deal_count()} verified '
                'deals →</a>'
            )
        verified_note = (
            '<p style="margin:10px 2px 0;font-size:11.5px;color:#7a8699;">'
            'These comparables are real deals from the corpus, with modeled '
            f'financials. For the fully source-linked subset, see {_vd_link}</p>'
        )
        # Sponsor track record — when the partner names a buyer, answer
        # "what does THIS house actually return" next to "what do deals
        # like this return". Aggregated from the buyer's own corpus deals
        # (realized only; unrealized counted, never imputed).
        sponsor_band = ""
        if _buyer:
            try:
                from ..diligence.comparable_outcomes import (
                    sponsor_track_record,
                )
                rec = sponsor_track_record(corpus, _buyer)
            except Exception:  # noqa: BLE001 — intel band must never 500
                rec = None
            if rec and rec["n_realized"]:
                s_med = rec["moic"]["median"]
                c_med = (summary.get("moic") or {}).get("median")
                if s_med and c_med:
                    delta = s_med - c_med
                    tone = "#0a8a5f" if delta >= 0 else "#b8732a"
                    vs = (
                        f' · <span style="color:{tone};font-weight:600;">'
                        f'{delta:+.2f}x vs this comp set</span>'
                    )
                else:
                    vs = ""
                yrs = (
                    f' · active {rec["year_min"]}–{rec["year_max"]}'
                    if rec.get("year_min") else ""
                )
                irr_bit = (
                    f' · median IRR {rec["irr_median"]*100:.1f}%'
                    if rec.get("irr_median") else ""
                )
                sponsor_band = (
                    '<div style="margin:0 0 14px;padding:10px 14px;'
                    'background:#f7f3ea;border:1px solid #d6cfc0;'
                    'border-radius:2px;font-size:12.5px;color:#1a2332;">'
                    '<span style="font-size:10px;color:#7a8699;font-weight:600;'
                    'text-transform:uppercase;letter-spacing:0.05em;'
                    f'margin-right:8px;">Sponsor record</span>'
                    f'<strong>{_html.escape(rec["buyer"])}</strong>: '
                    f'{rec["n_deals"]} corpus deal'
                    f'{"s" if rec["n_deals"] != 1 else ""} '
                    f'({rec["n_realized"]} realized) · '
                    f'median {s_med:.2f}x{vs}{irr_bit}{yrs}'
                    f' · <a href="/verified-deals?sponsor={_q(_buyer)}" '
                    'style="color:var(--sc-navy);">sourced deals →</a>'
                    '</div>'
                )
        # Layout: identity → one lede → inputs → results together
        # (outcome strip directly above the table it summarizes) →
        # exports/print at the point of use → provenance footnote.
        # The form no longer splits the results in half.
        inner = (
            page_title_block
            + explainer_html
            + form
            + _outcome_strip(summary)
            + size_link
            + sponsor_band
            + export_bar
            + print_cta
            + _wc.section_card(
                f"Top {len(rows)} comparables — sorted by match score",
                table + breakdown_legend, pad=False,
            )
            + verified_note
        )
        next_up = ck_next_section(
            "Cross-check against named bear cases",
            "/bear-cases",
            eyebrow="Up next",
            italic_word="bear",
        )
        body = (
            _wc.web_styles()
            + _wc.responsive_container(inner)
            + _wc.sortable_table_js()
            + next_up
        )
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body, "Comparable outcomes",
        active_nav="/diligence/comparable-outcomes",
        extra_css=_EXPLAINER_CSS,
    )
