"""Portfolio Analytics — /portfolio-analytics.

Combines ``data_public/portfolio_analytics.py`` (corpus scorecard,
vintage cohorts, deals-by-sponsor / type, return distribution,
outlier detection, payer-mix sensitivity) with
``data_public/market_concentration.py`` (concentration table, state
growth / volatility summaries, provider geo dependency).

Portfolio-scope views rather than per-deal: concentration risk
across the corpus, vintage mix, pacing, cross-holding synergy hints.
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
from ._helpers import (
    empty_note,
    fmt_multiple,
    fmt_pct,
    load_corpus_deals,
    small_panel,
    verdict_badge,
)


def _fmt_ev_mm(v: Any) -> str:
    try:
        f = float(v)
        if abs(f) >= 1000:
            return f"${f/1000:.2f}B"
        return f"${f:,.0f}M"
    except (TypeError, ValueError):
        return "—"


def _scorecard_panel(sc: Dict[str, Any]) -> str:
    rows = [
        ("Total Deals", str(sc.get("total_deals", 0))),
        ("Realized", str(sc.get("realized_deals", 0))),
        ("Total EV", _fmt_ev_mm(sc.get("total_ev_mm"))),
        ("Median EV", _fmt_ev_mm(sc.get("median_ev_mm"))),
        ("MOIC P25 / P50 / P75",
         f"{fmt_multiple(sc.get('moic_p25'))} · "
         f"{fmt_multiple(sc.get('moic_p50'))} · "
         f"{fmt_multiple(sc.get('moic_p75'))}"),
        ("MOIC Mean", fmt_multiple(sc.get("moic_mean"))),
        ("IRR P25 / P50 / P75",
         f"{fmt_pct(sc.get('irr_p25'))} · "
         f"{fmt_pct(sc.get('irr_p50'))} · "
         f"{fmt_pct(sc.get('irr_p75'))}"),
        ("Loss Rate", fmt_pct(sc.get("loss_rate"))),
        ("Home-Run Rate", fmt_pct(sc.get("home_run_rate"))),
        ("Outliers (z≥2)", str(sc.get("outlier_count", 0))),
        ("Vintage Years", str(sc.get("vintage_years", 0))),
    ]
    items = []
    for k, v in rows:
        items.append(
            f'<div style="display:flex;gap:14px;padding:5px 0;'
            f'border-bottom:1px solid {P["border_dim"]};font-size:11.5px;">'
            f'<span style="color:{P["text_faint"]};font-family:var(--ck-mono);'
            f'font-size:10px;letter-spacing:0.08em;width:200px;flex-shrink:0;">'
            f'{_html.escape(k)}</span>'
            f'<span style="color:{P["text"]};font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;">{v}</span>'
            f'</div>'
        )
    return "".join(items) or empty_note("No scorecard fields.")


def _vintage_table(cohorts: List[Dict[str, Any]]) -> str:
    if not cohorts:
        return empty_note("No vintage data.")
    rows = []
    for c in cohorts:
        year = c.get("year", "—")
        count = c.get("count", 0)
        realized = c.get("realized_count", 0)
        median = c.get("median_moic")
        ev = c.get("total_ev_mm")
        loss = c.get("loss_rate")
        hr = c.get("home_run_rate")
        median_col = (
            P["positive"] if (median or 0) >= 2.5
            else P["warning"] if (median or 0) >= 1.5
            else P["negative"]
        )
        rows.append(
            f'<tr>'
            f'<td style="font-family:var(--ck-mono);color:{P["text"]};'
            f'font-weight:600;" data-val="{year}">{year}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["text"]};" data-val="{count}">'
            f'{count}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" data-val="{realized}">'
            f'{realized}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{median_col};font-weight:600;" '
            f'data-val="{median or 0}">{fmt_multiple(median)}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" data-val="{ev or 0}">'
            f'{_fmt_ev_mm(ev)}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["negative"] if (loss or 0) > 0.3 else P["text"]};" '
            f'data-val="{loss or 0}">{fmt_pct(loss)}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["positive"] if (hr or 0) > 0.25 else P["text"]};" '
            f'data-val="{hr or 0}">{fmt_pct(hr)}</td>'
            f'</tr>'
        )
    return (
        f'<div class="ck-table-wrap"><table class="ck-table sortable">'
        f'<thead><tr>'
        f'<th>Vintage</th>'
        f'<th class="num">Count</th>'
        f'<th class="num">Realized</th>'
        f'<th class="num">Med MOIC</th>'
        f'<th class="num">Total EV</th>'
        f'<th class="num">Loss %</th>'
        f'<th class="num">HR %</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def _deal_type_table(by_type: Dict[str, Dict[str, Any]]) -> str:
    if not by_type:
        return empty_note("No deal-type breakdown.")
    items = sorted(
        by_type.items(),
        key=lambda kv: kv[1].get("count", 0),
        reverse=True,
    )
    rows = []
    total = sum(v.get("count", 0) for v in by_type.values()) or 1
    for deal_type, stats in items:
        n = stats.get("count", 0)
        pct = n / total * 100.0
        median = stats.get("median_moic")
        loss = stats.get("loss_rate")
        hr = stats.get("home_run_rate")
        median_col = (
            P["positive"] if (median or 0) >= 2.5
            else P["warning"] if (median or 0) >= 1.5
            else P["negative"]
        )
        rows.append(
            f'<tr>'
            f'<td style="color:{P["text"]};font-family:var(--ck-mono);'
            f'font-size:11px;">{_html.escape(deal_type)}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["text"]};" data-val="{n}">'
            f'{n}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" data-val="{pct}">'
            f'{pct:.1f}%</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{median_col};font-weight:600;" '
            f'data-val="{median or 0}">{fmt_multiple(median)}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["negative"] if (loss or 0) > 0.3 else P["text_dim"]};" '
            f'data-val="{loss or 0}">{fmt_pct(loss)}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["positive"] if (hr or 0) > 0.25 else P["text_dim"]};" '
            f'data-val="{hr or 0}">{fmt_pct(hr)}</td>'
            f'</tr>'
        )
    return (
        f'<div class="ck-table-wrap"><table class="ck-table sortable">'
        f'<thead><tr>'
        f'<th>Deal Type</th>'
        f'<th class="num">Count</th>'
        f'<th class="num">Share %</th>'
        f'<th class="num">Med MOIC</th>'
        f'<th class="num">Loss %</th>'
        f'<th class="num">HR %</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def _concentration_panel(deals: List[Dict[str, Any]]) -> str:
    """Renders concentration across payer, subsector, and geography.

    Uses portfolio_analytics.deals_by_type for deal-type concentration
    (already covered by the deal-type table) — here we hand-roll payer +
    subsector + state concentration via simple counts because the
    market_concentration module expects a pandas DataFrame with a
    different shape than the corpus dicts.
    """
    from collections import Counter, defaultdict
    import statistics as _stats

    sector_counts: Counter = Counter()
    state_counts: Counter = Counter()
    sponsor_ev: defaultdict = defaultdict(float)
    sponsor_count: Counter = Counter()
    for d in deals:
        sec = d.get("subsector") or d.get("sector")
        if sec:
            sector_counts[str(sec)] += 1
        st = d.get("state") or d.get("headquarters_state")
        if st:
            state_counts[str(st)] += 1
        sp = d.get("buyer") or d.get("sponsor")
        ev = d.get("ev_mm")
        if sp and ev is not None:
            try:
                sponsor_ev[str(sp)] += float(ev)
                sponsor_count[str(sp)] += 1
            except (TypeError, ValueError):
                pass

    def _top_table(counter: Dict[str, Any], *, col1: str, top_n: int = 10) -> str:
        items = sorted(counter.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
        total = sum(counter.values()) or 1
        rows = []
        for name, n in items:
            pct = n / total * 100.0
            rows.append(
                f'<tr>'
                f'<td style="color:{P["text"]};font-family:var(--ck-mono);'
                f'font-size:11px;">{_html.escape(str(name))}</td>'
                f'<td style="text-align:right;font-family:var(--ck-mono);'
                f'font-variant-numeric:tabular-nums;color:{P["text"]};" data-val="{n}">'
                f'{n}</td>'
                f'<td style="text-align:right;font-family:var(--ck-mono);'
                f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" data-val="{pct}">'
                f'{pct:.1f}%</td>'
                f'<td style="width:160px;"><span style="display:block;height:6px;'
                f'background:{P["border_dim"]};border-radius:1px;overflow:hidden;">'
                f'<span style="display:block;height:100%;width:{min(100,pct*2):.1f}%;'
                f'background:{P["accent"]};"></span></span></td>'
                f'</tr>'
            )
        return (
            f'<div class="ck-table-wrap"><table class="ck-table sortable">'
            f'<thead><tr><th>{_html.escape(col1)}</th><th class="num">Count</th>'
            f'<th class="num">Share</th><th></th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
        )

    def _sponsor_ev_table(top_n: int = 10) -> str:
        items = sorted(
            sponsor_ev.items(), key=lambda kv: kv[1], reverse=True
        )[:top_n]
        total_ev = sum(sponsor_ev.values()) or 1.0
        rows = []
        for sp, ev in items:
            pct = ev / total_ev * 100.0
            n = sponsor_count[sp]
            rows.append(
                f'<tr>'
                f'<td style="color:{P["text"]};font-family:var(--ck-mono);'
                f'font-size:11px;">{_html.escape(sp)}</td>'
                f'<td style="text-align:right;font-family:var(--ck-mono);'
                f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" data-val="{n}">'
                f'{n}</td>'
                f'<td style="text-align:right;font-family:var(--ck-mono);'
                f'font-variant-numeric:tabular-nums;color:{P["text"]};" data-val="{ev}">'
                f'{_fmt_ev_mm(ev)}</td>'
                f'<td style="text-align:right;font-family:var(--ck-mono);'
                f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" data-val="{pct}">'
                f'{pct:.1f}%</td>'
                f'</tr>'
            )
        return (
            f'<div class="ck-table-wrap"><table class="ck-table sortable">'
            f'<thead><tr><th>Sponsor</th><th class="num">Deals</th>'
            f'<th class="num">Total EV</th><th class="num">Share</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
        )

    sector_table = _top_table(dict(sector_counts), col1="Subsector")
    state_table = _top_table(dict(state_counts), col1="State / Region")
    sponsor_table = _sponsor_ev_table()

    return (
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
        + small_panel(
            f"Subsector concentration (top 10 of {len(sector_counts)})",
            sector_table, code="SEC",
        )
        + small_panel(
            f"Geographic concentration (top 10 of {len(state_counts)})",
            state_table, code="GEO",
        )
        + f'</div>'
        + small_panel(
            f"Sponsor $EV concentration (top 10 of {len(sponsor_count)})",
            sponsor_table, code="SPN",
        )
    )


def _outlier_panel(corpus: List[Dict[str, Any]]) -> str:
    try:
        from ...data_public.portfolio_analytics import outlier_deals
        outliers = outlier_deals(corpus, z=2.0)
    except Exception:
        return empty_note("outlier_deals failed.")
    if not outliers:
        return empty_note("No MOIC outliers (|z| ≥ 2) in the corpus.")
    rows = []
    for d in outliers[:30]:
        name = _html.escape(str(d.get("deal_name", "—")))
        year = d.get("year", "—")
        moic = d.get("realized_moic")
        z = d.get("z_score")
        col = P["positive"] if (moic or 0) >= 3 else (
            P["negative"] if (moic or 0) < 1 else P["warning"]
        )
        rows.append(
            f'<tr>'
            f'<td style="color:{P["text"]};font-size:11.5px;">{name}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};">{year}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{col};font-weight:600;">'
            f'{fmt_multiple(moic)}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};">'
            + (f"{float(z):+.2f}" if isinstance(z, (int, float)) else "—")
            + f'</td>'
            f'</tr>'
        )
    return (
        f'<div class="ck-table-wrap"><table class="ck-table sortable">'
        f'<thead><tr><th>Deal</th><th class="num">Year</th>'
        f'<th class="num">Realized MOIC</th><th class="num">Z-score</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    )


def render_portfolio_analytics(
    store: Any = None,
    current_user: Optional[str] = None,
) -> str:
    try:
        from ...data_public.portfolio_analytics import (
            corpus_scorecard, vintage_cohort_summary, deals_by_type,
        )
    except Exception as exc:  # noqa: BLE001
        body = small_panel(
            "Portfolio analytics unavailable",
            empty_note(f"portfolio_analytics module failed: {exc!r}"),
            code="ERR",
        )
        return chartis_shell(
            body, title="Portfolio Analytics",
            active_nav="/portfolio-analytics",
            subtitle="Module unavailable",
        )

    corpus = load_corpus_deals()
    if not corpus:
        body = small_panel(
            "Portfolio analytics — no corpus",
            empty_note("No corpus available."),
            code="NIL",
        )
        return chartis_shell(
            body, title="Portfolio Analytics",
            active_nav="/portfolio-analytics",
            subtitle="Corpus unavailable",
        )

    try:
        sc = corpus_scorecard(corpus)
        vc = vintage_cohort_summary(corpus)
        dt = deals_by_type(corpus)
    except Exception as exc:  # noqa: BLE001
        body = small_panel(
            "Portfolio analytics failed",
            empty_note(f"scorecard/vintage/type raised: {exc!r}"),
            code="ERR",
        )
        return chartis_shell(
            body, title="Portfolio Analytics",
            active_nav="/portfolio-analytics",
            subtitle="Analysis raised",
        )

    intro = (
        f'<p style="color:{P["text_dim"]};font-size:12px;line-height:1.6;'
        f'margin-bottom:10px;">'
        f'Portfolio-scope views across the 655-deal corpus. Combines '
        f'<code style="color:{P["accent"]};font-family:var(--ck-mono);">'
        f'portfolio_analytics</code> (scorecard, vintages, return distribution) '
        f'with concentration analysis across subsector, geography, and sponsor. '
        f'For per-sponsor depth see <a href="/sponsor-track-record" '
        f'style="color:{P["accent"]};">/sponsor-track-record</a>; for payer-mix '
        f'depth see <a href="/payer-intelligence" style="color:{P["accent"]};">'
        f'/payer-intelligence</a>.</p>'
    )

    kpis = (
        ck_kpi_block("Total Deals", str(sc.get("total_deals", 0)), "corpus size")
        + ck_kpi_block("Realized",
                        str(sc.get("realized_deals", 0)),
                        f"{sc.get('realized_deals',0)/max(sc.get('total_deals',1),1)*100:.0f}% of corpus")
        + ck_kpi_block("Median MOIC",
                        fmt_multiple(sc.get("moic_p50")), "realized deals")
        + ck_kpi_block("Home-Run Rate",
                        fmt_pct(sc.get("home_run_rate")), "≥ 3.0x MOIC")
        + ck_kpi_block("Loss Rate",
                        fmt_pct(sc.get("loss_rate")), "< 1.0x MOIC")
        + ck_kpi_block("Outliers",
                        str(sc.get("outlier_count", 0)), "|z| ≥ 2")
    )
    kpi_strip = f'<div class="ck-kpi-grid">{kpis}</div>'

    scorecard = small_panel(
        "Corpus scorecard (corpus_scorecard output)",
        _scorecard_panel(sc), code="SCR",
    )

    vintage_panel = small_panel(
        f"Vintage cohort summary ({len(vc)} years)",
        _vintage_table(vc), code="VNT",
    )

    type_panel = small_panel(
        f"Deals by type ({len(dt)} categories)",
        _deal_type_table(dt), code="TYP",
    )

    outlier_panel = small_panel(
        "Outlier deals (|z| ≥ 2 realized MOIC)",
        _outlier_panel(corpus), code="OUT",
    )

    body = (
        intro
        + kpi_strip
        + ck_section_header(
            "CORPUS SCORECARD",
            "realized-deal roll-up statistics",
        )
        + f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">'
        + scorecard + type_panel
        + f'</div>'
        + ck_section_header(
            "VINTAGE MIX & PACING",
            "annual cohort sizes + realized-MOIC distribution",
            count=len(vc),
        )
        + vintage_panel
        + ck_section_header(
            "CONCENTRATION RISK",
            "where the corpus is clustered — subsector, geography, sponsor",
        )
        + _concentration_panel(corpus)
        + ck_section_header(
            "OUTLIER DEALS", "tails of the realized-MOIC distribution",
        )
        + outlier_panel
    )

    return chartis_shell(
        body,
        title="Portfolio Analytics",
        active_nav="/portfolio-analytics",
        subtitle=f"{sc.get('total_deals',0)} deals · "
                 f"median {fmt_multiple(sc.get('moic_p50'))} · "
                 f"HR {fmt_pct(sc.get('home_run_rate'))} · "
                 f"loss {fmt_pct(sc.get('loss_rate'))}",
    )
