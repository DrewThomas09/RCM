"""Corpus Backtest — /corpus-backtest.

Calls ``data_public/backtester.match_deals(store_db, corpus_db)`` —
the module that cross-matches platform-predicted outcomes against the
655-deal corpus's realized MOIC / IRR, then scores the platform's
forecast accuracy.

Distinct from the existing ``/backtester`` (value_backtester — an
in-model ML-predictor backtest). Both pages carry a disambiguation
banner.

The real match_deals() requires a separate corpus SQLite DB with a
``public_deals`` table. That DB isn't always populated on a fresh
install; when it's absent we fall back to a corpus self-analysis:
realized-MOIC distribution by vintage year + subsector, which
establishes the ground-truth curve platform predictions would need
to match against.
"""
from __future__ import annotations

import html as _html
import statistics as _stats
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

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
from ._sanity import render_number


def _disambig_banner() -> str:
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-left:4px solid {P["warning"]};border-radius:3px;'
        f'padding:12px 16px;margin-bottom:14px;">'
        f'<div style="font-family:var(--ck-mono);font-size:9.5px;'
        f'letter-spacing:0.15em;color:{P["warning"]};margin-bottom:4px;">'
        f'DISAMBIGUATION</div>'
        f'<div style="color:{P["text"]};font-size:12px;line-height:1.6;">'
        f'<strong>/corpus-backtest</strong> (this page) measures how well '
        f'<em>platform deal predictions</em> matched realized outcomes in the '
        f'655-deal corpus — the <code style="color:{P["accent"]};'
        f'font-family:var(--ck-mono);">backtester.py</code> module. '
        f'For the <strong>value-bridge / ML-predictor backtest</strong> '
        f'(calibration curves + conformal intervals on an individual deal '
        f'model) see <a href="/backtester" style="color:{P["accent"]};">'
        f'/backtester</a>. They answer different questions.'
        f'</div></div>'
    )


def _vintage_row(year: int, moics: List[float]) -> str:
    n = len(moics)
    median = _stats.median(moics)
    mean = _stats.mean(moics)
    stdev = _stats.stdev(moics) if n > 1 else 0.0
    mn = min(moics)
    mx = max(moics)
    median_col = P["positive"] if median >= 2.5 else (
        P["warning"] if median >= 1.5 else P["negative"]
    )
    stdev_col = P["warning"] if stdev >= 1.5 else P["text_dim"]
    return (
        f'<tr>'
        f'<td style="font-family:var(--ck-mono);color:{P["text"]};'
        f'font-weight:600;" data-val="{year}">{year}</td>'
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" data-val="{n}">'
        f'{n}</td>'
        f'<td style="text-align:right;font-weight:600;" '
        f'data-val="{median}">{render_number(median, "moic")}</td>'
        f'<td style="text-align:right;" data-val="{mean}">'
        f'{render_number(mean, "moic")}</td>'
        # stdev is a dispersion, not a MOIC value — leave unguarded.
        f'<td style="text-align:right;font-family:var(--ck-mono);'
        f'font-variant-numeric:tabular-nums;color:{stdev_col};" data-val="{stdev}">'
        f'{fmt_multiple(stdev)}</td>'
        f'<td style="text-align:right;" data-val="{mn}">'
        f'{render_number(mn, "moic")}</td>'
        f'<td style="text-align:right;" data-val="{mx}">'
        f'{render_number(mx, "moic")}</td>'
        f'</tr>'
    )


def _corpus_self_analysis(corpus: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    """Fallback: realized-MOIC distribution by vintage + sector.

    This isn't a "prediction vs realized" comparison — we don't have
    platform predictions in this install. But it IS the ground-truth
    curve any forecast would need to match, so showing it here still
    answers the "how does outcome vary by vintage / subsector" half
    of the corpus-backtest question.
    """
    by_year: Dict[int, List[float]] = defaultdict(list)
    by_sector: Dict[str, List[float]] = defaultdict(list)
    for d in corpus:
        m = d.get("realized_moic")
        if m is None:
            continue
        try:
            mf = float(m)
        except (TypeError, ValueError):
            continue
        y = d.get("year")
        try:
            if y is not None:
                by_year[int(y)].append(mf)
        except (TypeError, ValueError):
            pass
        sec = d.get("subsector") or d.get("sector") or "unknown"
        by_sector[str(sec)].append(mf)

    vintage_rows = "".join(
        _vintage_row(year, moics)
        for year, moics in sorted(by_year.items())
    )
    vintage_table = (
        f'<div class="ck-table-wrap"><table class="ck-table sortable">'
        f'<thead><tr>'
        f'<th>Vintage</th>'
        f'<th class="num">N</th>'
        f'<th class="num">Median</th>'
        f'<th class="num">Mean</th>'
        f'<th class="num">Stdev</th>'
        f'<th class="num">Min</th>'
        f'<th class="num">Max</th>'
        f'</tr></thead>'
        f'<tbody>{vintage_rows}</tbody></table></div>'
    )

    # Sector table
    sector_rows = []
    sector_items = sorted(
        by_sector.items(),
        key=lambda kv: _stats.median(kv[1]) if kv[1] else 0,
        reverse=True,
    )
    for sec, moics in sector_items:
        if len(moics) < 3:
            continue  # skip too-thin cohorts
        median = _stats.median(moics)
        mean = _stats.mean(moics)
        stdev = _stats.stdev(moics) if len(moics) > 1 else 0.0
        col = P["positive"] if median >= 2.5 else (
            P["warning"] if median >= 1.5 else P["negative"]
        )
        sector_rows.append(
            f'<tr>'
            f'<td style="color:{P["text"]};font-family:var(--ck-mono);'
            f'font-size:11px;">{_html.escape(str(sec))}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};" '
            f'data-val="{len(moics)}">{len(moics)}</td>'
            f'<td style="text-align:right;font-weight:600;" '
            f'data-val="{median}">{render_number(median, "moic")}</td>'
            f'<td style="text-align:right;" data-val="{mean}">'
            f'{render_number(mean, "moic")}</td>'
            # stdev stays unguarded — it's a dispersion, not a MOIC.
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["text_faint"]};" '
            f'data-val="{stdev}">{fmt_multiple(stdev)}</td>'
            f'</tr>'
        )
    sector_table = (
        f'<div class="ck-table-wrap"><table class="ck-table sortable">'
        f'<thead><tr>'
        f'<th>Subsector</th>'
        f'<th class="num">N</th>'
        f'<th class="num">Median MOIC</th>'
        f'<th class="num">Mean</th>'
        f'<th class="num">Stdev</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(sector_rows)}</tbody></table></div>'
    )

    n_realized = sum(len(v) for v in by_year.values())
    summary = {
        "n_realized": n_realized,
        "n_vintages": len(by_year),
        "n_sectors_scored": len(sector_items),
    }

    combined = (
        small_panel(
            f"Realized MOIC by vintage ({len(by_year)} years · {n_realized} deals)",
            vintage_table,
            code="VYR",
        )
        + small_panel(
            f"Realized MOIC by subsector ({len(sector_items)} segments)",
            sector_table,
            code="SEG",
        )
    )
    return combined, summary


def _match_results_panel(results: List[Any]) -> str:
    """Render the BacktestResult list when match_deals succeeded."""
    if not results:
        return empty_note("match_deals returned zero rows.")
    rows = []
    matched = [r for r in results if getattr(r, "platform_deal_id", None)]
    for r in matched[:100]:
        corpus_name = _html.escape(str(getattr(r, "corpus_deal_name", "—")))
        corpus_year = getattr(r, "corpus_year", "—")
        real_moic = getattr(r, "corpus_realized_moic", None)
        pred_moic = getattr(r, "predicted_moic", None)
        err = getattr(r, "moic_error", None)
        match_score = getattr(r, "match_score", None)
        err_col = P["text"]
        try:
            err_f = float(err)
            if abs(err_f) <= 0.25:
                err_col = P["positive"]
            elif abs(err_f) <= 0.75:
                err_col = P["warning"]
            else:
                err_col = P["negative"]
        except (TypeError, ValueError):
            pass
        rows.append(
            f'<tr>'
            f'<td style="color:{P["text"]};font-size:11px;">{corpus_name}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["text_dim"]};">{corpus_year}</td>'
            f'<td style="text-align:right;">{render_number(real_moic, "moic")}</td>'
            f'<td style="text-align:right;">{render_number(pred_moic, "moic")}</td>'
            # err is a MOIC-delta (predicted - realized), not an absolute
            # MOIC — can legitimately be very large.
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{err_col};">{fmt_multiple(err)}</td>'
            f'<td style="text-align:right;font-family:var(--ck-mono);'
            f'font-variant-numeric:tabular-nums;color:{P["text_faint"]};">'
            f'{fmt_pct(match_score, digits=0)}</td>'
            f'</tr>'
        )
    return (
        f'<div class="ck-table-wrap"><table class="ck-table sortable">'
        f'<thead><tr>'
        f'<th>Corpus Deal</th><th class="num">Year</th>'
        f'<th class="num">Realized MOIC</th>'
        f'<th class="num">Predicted MOIC</th>'
        f'<th class="num">Error</th>'
        f'<th class="num">Match %</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
    )


def render_corpus_backtest(
    store: Any = None,
    store_db_path: Optional[str] = None,
    current_user: Optional[str] = None,
) -> str:
    corpus = load_corpus_deals()
    if not corpus:
        body = _disambig_banner() + small_panel(
            "Corpus backtest — no corpus",
            empty_note("No corpus loaded; backtesting requires the 655-deal seed set."),
            code="NIL",
        )
        return chartis_shell(
            body, title="Corpus Backtest",
            active_nav="/corpus-backtest",
            subtitle="Corpus unavailable",
        )

    # Attempt the real prediction-vs-realized backtest first. Requires
    # a corpus DB with a public_deals table — commonly unpopulated in
    # a fresh install, so we degrade gracefully.
    match_attempt: Optional[List[Any]] = None
    match_stats: Optional[Dict[str, Any]] = None
    match_error: Optional[str] = None
    if store_db_path:
        try:
            from ...data_public.backtester import match_deals, summary_stats
            # Use the same DB for both — the module will look for
            # public_deals on corpus_db_path; if the table isn't there
            # it raises OperationalError which we catch below.
            match_attempt = match_deals(store_db_path, store_db_path)
            match_stats = summary_stats(match_attempt) if match_attempt else None
        except Exception as exc:  # noqa: BLE001
            match_attempt = None
            match_error = str(exc)

    self_analysis, self_summary = _corpus_self_analysis(corpus)

    # Build KPIs from whichever data source we have
    if match_attempt:
        matched = [r for r in match_attempt if getattr(r, "platform_deal_id", None)]
        kpis = (
            ck_kpi_block("Corpus Deals", str(len(match_attempt)), "in backtest universe")
            + ck_kpi_block("Matched", str(len(matched)),
                            f"{len(matched)/len(match_attempt)*100:.0f}% match rate" if match_attempt else "—")
            + ck_kpi_block("Realized", str(self_summary["n_realized"]),
                            "with known MOIC")
            + ck_kpi_block("Vintages", str(self_summary["n_vintages"]),
                            "years in corpus")
        )
    else:
        kpis = (
            ck_kpi_block("Corpus Deals", str(len(corpus)), "in 655-deal seed")
            + ck_kpi_block("Realized", str(self_summary["n_realized"]),
                            "with known MOIC")
            + ck_kpi_block("Vintages", str(self_summary["n_vintages"]),
                            "years in corpus")
            + ck_kpi_block("Subsectors", str(self_summary["n_sectors_scored"]),
                            "with ≥3 deals")
        )
    kpi_strip = f'<div class="ck-kpi-grid">{kpis}</div>'

    if match_attempt:
        match_panel = small_panel(
            f"Prediction-vs-Realized ({len(match_attempt)} corpus deals)",
            _match_results_panel(match_attempt),
            code="MAT",
        )
        header = ck_section_header(
            "PLATFORM PREDICTIONS · REALIZED OUTCOMES",
            "fuzzy-matched against the 655-deal corpus",
            count=len(match_attempt),
        )
        body_blocks = header + match_panel + ck_section_header(
            "GROUND-TRUTH CURVE", "realized MOIC by vintage + subsector",
        ) + self_analysis
    else:
        no_match = (
            f'<div style="color:{P["text_dim"]};font-size:11.5px;line-height:1.6;'
            f'margin-bottom:8px;">'
            f'The prediction-vs-realized join requires a corpus SQLite DB '
            f'with a <code style="color:{P["accent"]};font-family:var(--ck-mono);">'
            f'public_deals</code> table — not populated on this install. '
            f'Populate it with <code style="color:{P["accent"]};'
            f'font-family:var(--ck-mono);">rcm-mc data refresh</code> '
            f'to unlock the match table above. In the meantime, the '
            f'<strong>corpus self-analysis</strong> below shows the '
            f'ground-truth realized-MOIC curve any forecast would need '
            f'to match.'
            f'</div>'
            + (
                f'<div style="font-family:var(--ck-mono);font-size:10px;'
                f'color:{P["negative"]};">Last error: {_html.escape(match_error)}</div>'
                if match_error else ""
            )
        )
        header = ck_section_header(
            "PREDICTION-VS-REALIZED JOIN",
            "requires a populated corpus DB",
        )
        body_blocks = header + small_panel(
            "Prediction-vs-realized — not yet available",
            no_match,
            code="N/A",
        ) + ck_section_header(
            "GROUND-TRUTH CURVE", "realized MOIC by vintage + subsector",
        ) + self_analysis

    body = _disambig_banner() + kpi_strip + body_blocks

    return chartis_shell(
        body,
        title="Corpus Backtest",
        active_nav="/corpus-backtest",
        subtitle=(
            f"{len(corpus)} corpus deals · "
            f"{self_summary['n_realized']} realized · "
            f"{'prediction match ready' if match_attempt else 'ground-truth mode'}"
        ),
    )
