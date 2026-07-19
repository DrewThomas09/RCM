"""CMS Public Data Browser — /cms-data-browser.

Renders the real CMS dataset catalog computed by
``data_public.cms_data_browser`` off the live connector estate. Every
count and vintage is read from the ingested SQLite files; a cold
deployment shows an honest "nothing cached yet" state with a path to the
Data Hub rather than fabricated numbers.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_bar_row, ck_data_cell, ck_empty_state,
    ck_kpi_block, ck_page_actions, ck_value_anchor,
)


def _compact(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return f"{n:,}"


def _date(iso: str) -> str:
    return (iso or "")[:10] or "—"


def _status_pill(status: str) -> str:
    cached = status == "cached"
    color = P["positive"] if cached else P["warning"]
    return (
        f'<td style="text-align:center;padding:5px 10px;font-family:'
        f'JetBrains Mono,monospace;font-size:10px;color:{color};'
        f'font-weight:700">{_html.escape(status.upper())}</td>'
    )


def _connectors_table(rows) -> str:
    text_dim = P["text_dim"]
    cols = [("Connector", "left"), ("API base", "left"), ("Datasets", "right"),
            ("Rows cached", "right"), ("Vintage", "center"), ("Status", "center")]
    ths = "".join(ck_data_cell(c, align=a, is_header=True) for c, a in cols)
    trs = []
    for c in rows:
        trs.append(
            "<tr>"
            + ck_data_cell(_html.escape(c.label), mono=True, weight=600)
            + f'<td style="text-align:left;padding:5px 10px;font-size:10px;'
              f'font-family:JetBrains Mono,monospace;color:{P["accent"]}">'
              f'{_html.escape(c.base_url)}</td>'
            + ck_data_cell(f"{c.n_datasets}", align="right", mono=True, tone="dim")
            + ck_data_cell(f"{c.rows_cached:,}" if c.warmed else "—",
                           align="right", mono=True, weight=700)
            + ck_data_cell(_date(c.vintage), align="center", mono=True, tone="acc")
            + _status_pill("cached" if c.warmed else "available")
            + "</tr>"
        )
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody>'
            f'</table></div>')


def _catalog_chart(datasets) -> str:
    cached = [d for d in datasets if d.record_count > 0][:12]
    if not cached:
        return ""
    total = sum(d.record_count for d in cached) or 1
    rows = "".join(
        ck_bar_row(d.dataset_id, _compact(d.record_count),
                   d.record_count / total * 100.0, tone="teal")
        for d in cached
    )
    return (
        '<div style="margin-bottom:14px">' + rows +
        '<div style="font-size:10px;color:var(--sc-text-faint);margin-top:6px;'
        'font-family:JetBrains Mono,monospace">Bar = share of cached rows '
        '· value = rows on disk (top 12 cached datasets)</div></div>'
    )


def _catalog_table(datasets) -> str:
    text_dim = P["text_dim"]
    cols = [("Dataset", "left"), ("Connector", "center"), ("Endpoint", "left"),
            ("Update Freq", "center"), ("Vintage", "center"),
            ("Records", "right"), ("Status", "center")]
    ths = "".join(ck_data_cell(c, align=a, is_header=True) for c, a in cols)
    trs = []
    for d in datasets:
        trs.append(
            "<tr>"
            + ck_data_cell(_html.escape(d.dataset_id), mono=True, weight=600)
            + f'<td style="text-align:center;padding:5px 10px;font-family:'
              f'JetBrains Mono,monospace;font-size:10px;color:{text_dim}">'
              f'{_html.escape(d.category)}</td>'
            + f'<td style="text-align:left;padding:5px 10px;font-family:'
              f'JetBrains Mono,monospace;font-size:10px;color:{text_dim}">'
              f'{_html.escape(d.endpoint)}</td>'
            + f'<td style="text-align:center;padding:5px 10px;font-family:'
              f'JetBrains Mono,monospace;font-size:10px;color:{text_dim}">'
              f'{_html.escape(d.update_frequency)}</td>'
            + ck_data_cell(_date(d.last_refresh), align="center", mono=True, tone="acc")
            + ck_data_cell(f"{d.record_count:,}" if d.record_count else "—",
                           align="right", mono=True)
            + _status_pill(d.ingestion_status)
            + "</tr>"
        )
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody>'
            f'</table></div>')


def render_cms_data_browser(params: dict = None) -> str:
    from rcm_mc.data_public.cms_data_browser import compute_cms_data_browser
    r = compute_cms_data_browser()

    panel = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]

    intro = {
        "eyebrow": "CMS DATA BROWSER",
        "headline": "The CMS datasets the desk can actually pull.",
        "italic_word": "actually",
        "body": (
            "Every dataset in the CMS public-data connectors, with its "
            "live cache status: how many rows are on disk and when they "
            "were last ingested. Cached datasets are queryable now; "
            "available ones warm from the Data Hub. Source: the "
            "connectors/ estate (read live — never illustrative)."
        ),
    }

    if not r.available:
        body = ck_empty_state(
            "CMS estate not available on this deployment",
            "The repo-root connectors/ estate isn't present here, so there "
            "is no CMS data to browse. Check out the full repository and "
            "warm sources from the Data Hub.",
            eyebrow="CMS DATA", icon="⛁", tone="warning",
            cta_label="Open Data Hub", cta_href="/data-hub",
        )
        return chartis_shell(body, "CMS Public Data Browser",
                             active_nav="/cms-data-browser",
                             subtitle="CMS public-data catalog — unavailable",
                             editorial_intro=intro)

    meta_line = (
        f"{r.total_datasets} CMS datasets · {r.cached_datasets} cached · "
        f"{r.total_rows:,} rows on disk · latest ingest {_date(r.latest_vintage)}"
    )

    kpi_strip = (
        ck_kpi_block("CMS datasets", f'<span class="mn">{r.total_datasets}</span>',
                     "registered in the estate", "") +
        ck_kpi_block("Cached now", f'<span class="mn">{r.cached_datasets}</span>',
                     "rows on disk", "") +
        ck_kpi_block("Rows cached", f'<span class="mn">{_compact(r.total_rows)}</span>',
                     "across CMS connectors", "") +
        ck_kpi_block("Connectors", f'<span class="mn">{len(r.connectors)}</span>',
                     "CMS public-data APIs", "") +
        ck_kpi_block("Latest ingest", f'<span class="mn">{_date(r.latest_vintage)}</span>',
                     "most recent pull", "")
    )

    value_anchor = ck_value_anchor(
        "CMS data cached locally",
        f"{_compact(r.total_rows)} rows",
        delta=f"{r.cached_datasets}/{r.total_datasets} datasets cached · "
              f"{len(r.connectors)} connectors",
        tone="teal",
    )

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = (f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};"
          f"text-transform:uppercase;margin-bottom:10px")

    warm_hint = (
        f'<div style="background:{panel_alt};border:1px solid {border};'
        f'border-left:3px solid {acc};padding:12px 16px;font-size:11px;'
        f'color:{text_dim};margin-bottom:16px">'
        f'<strong style="color:{text}">Filling data:</strong> warm any '
        f'connector from the <a href="/data-hub" style="color:{acc}">Data Hub</a> '
        f'(admin), then drill into individual datasets — sample rows, '
        f'copy-ready queries, and aggregates — on the '
        f'<a href="/connector-estate" style="color:{acc}">Connector Estate</a> '
        f'browser. Counts and vintages here refresh from disk on every load.'
        f'</div>'
    )

    body = f"""
<div class="ck-page-wrap">
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  {warm_hint}
  <div style="{cell}"><div style="{h3}">CMS Connectors — Cache Status</div>{_connectors_table(r.connectors)}</div>
  <div style="{cell}"><div style="{h3}">Dataset Catalog ({r.total_datasets} datasets · cached first)</div>{_catalog_chart(r.datasets)}{_catalog_table(r.datasets)}</div>
</div>"""

    body = body + ck_page_actions()
    return chartis_shell(
        body, "CMS Public Data Browser",
        active_nav="/cms-data-browser",
        subtitle=meta_line,
        editorial_intro=intro,
    )
