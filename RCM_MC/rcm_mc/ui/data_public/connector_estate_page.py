"""Connector Estate browser — /connector-estate.

Browses the repo-root ``connectors/`` estate (13+ public healthcare API
connectors, ~150 registered datasets, plus the synced open-data catalogs
— all counts computed live, never hardcoded) through the read-only
bridge in ``rcm_mc.data_public.connector_estate``.

Views (all GET — this surface never mutates anything):
  /connector-estate                    estate overview, per-connector cards
  /connector-estate?connector=<name>   one connector, every dataset
  /connector-estate?q=<text>           search dataset id / table / endpoint
  /connector-estate?dataset=<id>       registry detail + sample rows +
                                       copy-ready API/CLI + quick aggregate

The estate is optional at runtime (wheel installs don't ship the repo
root), so the whole page degrades to an editorial empty state — never a
500 — when the bridge reports the estate unavailable.
"""
from __future__ import annotations

import html as _html
from typing import Any

from rcm_mc.data_public import connector_estate as _estate
from rcm_mc.ui._chartis_kit import (
    chartis_shell,
    ck_bar_row,
    ck_empty_state,
    ck_kpi_block,
    ck_page_title,
    ck_section_header,
)

_ROUTE = "/connector-estate"


def _e(x: Any) -> str:
    return _html.escape(str(x if x is not None else ""))


def _mono(text: str) -> str:
    return (f'<span style="font-family:var(--ck-mono,monospace);font-size:10.5px;">'
            f'{_e(text)}</span>')


def _dataset_link(dataset_id: str) -> str:
    return (f'<a href="{_ROUTE}?dataset={_e(dataset_id)}" '
            f'style="font-family:var(--ck-mono,monospace);font-size:10.5px;'
            f'color:var(--ck-accent,#155752);">{_e(dataset_id)}</a>')


def _code_block(text: str) -> str:
    """Copy-ready one-liner — mono block the partner can triple-click."""
    return (
        '<pre style="margin:4px 0 10px;padding:8px 12px;background:var(--sc-bone,#efe9dc);'
        'border:1px solid var(--ck-border,#d8d0bf);border-radius:3px;'
        'font-family:var(--ck-mono,monospace);font-size:11px;overflow-x:auto;'
        f'white-space:pre;">{_e(text)}</pre>')


def _datasets_table(rows: list[dict[str, Any]], *, show_connector: bool = False) -> str:
    """Registry rows as a striped table; every dataset_id links to detail."""
    head_cols = (["Connector"] if show_connector else []) + [
        "Dataset", "Target table", "Cadence", "Join keys"]
    ths = "".join(
        f'<th style="padding:6px 10px;text-align:left;font-size:10px;'
        f'text-transform:uppercase;letter-spacing:.06em;">{_e(c)}</th>'
        for c in head_cols)
    trs = []
    for i, r in enumerate(rows):
        stripe = ' style="background:var(--sc-bone,#efe9dc)"' if i % 2 == 0 else ""
        cells = []
        if show_connector:
            cells.append(f'<td style="padding:5px 10px;">{_mono(r.get("connector", ""))}</td>')
        cells.append(f'<td style="padding:5px 10px;">{_dataset_link(r.get("dataset_id", ""))}</td>')
        cells.append(f'<td style="padding:5px 10px;">{_mono(r.get("target_table", ""))}</td>')
        cells.append(
            f'<td style="padding:5px 10px;font-size:10.5px;color:var(--ck-text-dim,#56606f);">'
            f'{_e(r.get("refresh_cadence", ""))}</td>')
        joins = ", ".join(r.get("join_keys") or [])
        cells.append(f'<td style="padding:5px 10px;">{_mono(joins)}</td>')
        trs.append(f'<tr{stripe}>{"".join(cells)}</tr>')
    return (
        '<div class="ck-table-wrap"><table class="ck-table" '
        'style="width:100%;border-collapse:collapse;">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _connector_card(summary: dict[str, Any], rows: list[dict[str, Any]],
                    ingested: dict[str, int], *, max_rows: int | None = 8,
                    vintages: dict[str, str] | None = None) -> str:
    name = summary.get("connector", "")
    label = summary.get("label", name)
    n = summary.get("n_datasets", len(rows))
    bases = " · ".join(summary.get("base_urls") or [])
    n_ing = ingested.get(name)
    ing_html = ""
    if n_ing:
        vintage = (vintages or {}).get(name, "")
        vintage_html = (
            f' · last ingested {_e(vintage)}' if vintage else "")
        ing_html = (
            f'<span style="font-family:var(--ck-mono,monospace);font-size:10px;'
            f'color:var(--sc-positive,#0a8a5f);font-weight:700;">'
            f'{n_ing:,} rows ingested{vintage_html}</span>')
    shown = rows if max_rows is None else rows[:max_rows]
    more_html = ""
    if max_rows is not None and len(rows) > max_rows:
        more_html = (
            f'<div style="margin-top:6px;"><a href="{_ROUTE}?connector={_e(name)}" '
            f'style="font-size:11px;color:var(--ck-accent,#155752);font-weight:600;">'
            f'+ {len(rows) - max_rows} more datasets →</a></div>')
    return (
        '<div class="ck-panel" style="margin-bottom:16px;">'
        '<div class="ck-panel-title" style="display:flex;justify-content:space-between;'
        'gap:12px;flex-wrap:wrap;align-items:baseline;">'
        f'<span>{_e(label)}</span>'
        f'<span style="display:flex;gap:14px;align-items:baseline;">{ing_html}'
        f'<span style="font-family:var(--ck-mono,monospace);font-size:10px;'
        f'color:var(--ck-text-faint,#8b94a0);">{_e(name)} · {n} datasets</span>'
        '</span></div>'
        f'<div style="padding:6px 12px 0;font-family:var(--ck-mono,monospace);'
        f'font-size:10px;color:var(--ck-text-faint,#8b94a0);word-break:break-all;">'
        f'{_e(bases)}</div>'
        f'<div style="padding:8px 12px 12px;">{_datasets_table(shown)}{more_html}</div>'
        '</div>')


def _kpi_strip(summaries: list[dict[str, Any]] | None = None,
               ingested: dict[str, int] | None = None) -> str:
    # Optional precomputed inputs: render_connector_estate computes them
    # once per request and threads them through (each ingested_counts()
    # call opens every connector's SQLite file and COUNTs every table).
    # None falls back to self-service for compatibility.
    summaries = _estate.connectors_summary() if summaries is None else summaries
    n_conn = len(summaries)
    n_reg = sum(s.get("n_datasets", 0) for s in summaries)
    ingested = _estate.ingested_counts() if ingested is None else ingested
    n_rows = sum(ingested.values())
    cat_counts = _estate.catalog_dataset_counts()
    n_disc = sum(cat_counts.values())
    if n_disc:
        disc_val = f'<span class="mn">{n_disc:,}</span>'
        disc_sub = f"across {len(cat_counts)} synced open-data catalogs"
    else:
        disc_val = f'<span class="mn">{n_reg:,}</span>'
        disc_sub = "registry only — run refresh/discover to sync catalogs"
    return (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Connectors", f'<span class="mn">{n_conn}</span>',
                       "public healthcare APIs")
        + ck_kpi_block("Registered datasets", f'<span class="mn">{n_reg:,}</span>',
                       "curated, uniformly queryable")
        + ck_kpi_block("Rows ingested", f'<span class="mn">{n_rows:,}</span>',
                       "local SQLite, read-only here")
        + ck_kpi_block("Datasets discoverable", disc_val, disc_sub)
        + "</div>")


# ── detail view ─────────────────────────────────────────────────────────


def _registry_fields(row: dict[str, Any]) -> str:
    fields = [
        ("Connector", row.get("connector", "")),
        ("Base URL", row.get("base_url", "")),
        ("Endpoint", row.get("endpoint", "")),
        ("Target table", row.get("target_table", "")),
        ("Refresh cadence", row.get("refresh_cadence", "")),
        ("Join keys", ", ".join(row.get("join_keys") or [])),
        ("Source filter", row.get("source_filter", "") or "—"),
        ("Date field", row.get("date_field", "") or "—"),
        ("Default params", str(row.get("default_params") or {}) if row.get("default_params") else "—"),
    ]
    cells = "".join(
        '<div style="padding:8px 12px;background:var(--ck-panel-alt,#f2eee4);">'
        f'<div style="font-family:var(--ck-mono,monospace);font-size:9px;'
        f'letter-spacing:.1em;text-transform:uppercase;'
        f'color:var(--ck-text-faint,#8b94a0);margin-bottom:3px;">{_e(k)}</div>'
        f'<div style="font-family:var(--ck-mono,monospace);font-size:11px;'
        f'word-break:break-all;">{_e(v)}</div></div>'
        for k, v in fields)
    return (
        '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));'
        f'gap:1px;background:var(--ck-border,#d8d0bf);border:1px solid '
        f'var(--ck-border,#d8d0bf);margin:10px 0 16px;">{cells}</div>')


def _sample_table(sample: dict[str, Any]) -> str:
    rows = sample.get("rows") or []
    if not rows:
        return ""
    cols = list(rows[0].keys())[:8]
    ths = "".join(
        f'<th style="padding:6px 8px;text-align:left;font-size:9.5px;'
        f'text-transform:uppercase;letter-spacing:.05em;">{_e(c)}</th>'
        for c in cols)
    trs = []
    for i, r in enumerate(rows):
        stripe = ' style="background:var(--sc-bone,#efe9dc)"' if i % 2 == 0 else ""
        tds = "".join(
            f'<td style="padding:4px 8px;font-family:var(--ck-mono,monospace);'
            f'font-size:10px;max-width:220px;overflow:hidden;text-overflow:ellipsis;'
            f'white-space:nowrap;">{_e(str(r.get(c, ""))[:120])}</td>'
            for c in cols)
        trs.append(f'<tr{stripe}>{tds}</tr>')
    return (
        '<div class="ck-table-wrap" style="overflow-x:auto;">'
        '<table class="ck-table" style="border-collapse:collapse;min-width:100%;">'
        f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _aggregate_panel(dataset_id: str, params: dict[str, Any]) -> str:
    cols = _estate.dataset_columns(dataset_id)
    if not cols:
        return ""
    group_by = params.get("group_by", "")
    options = "".join(
        f'<option value="{_e(c)}"{" selected" if c == group_by else ""}>{_e(c)}</option>'
        for c in cols)
    form = (
        f'<form method="get" action="{_ROUTE}" style="display:flex;gap:8px;'
        'align-items:center;flex-wrap:wrap;margin:4px 0 10px;">'
        f'<input type="hidden" name="dataset" value="{_e(dataset_id)}" />'
        '<label style="font-size:11px;color:var(--ck-text-dim,#56606f);">'
        'Group by</label>'
        f'<select name="group_by" style="padding:5px 8px;border:1px solid '
        f'var(--ck-border,#d8d0bf);border-radius:3px;font-size:11.5px;'
        f'font-family:var(--ck-mono,monospace);">{options}</select>'
        '<button type="submit" style="padding:6px 14px;background:var(--ck-accent,#155752);'
        'color:#fff;border:none;border-radius:3px;font-size:11px;cursor:pointer;">'
        'Aggregate</button></form>')
    bars = ""
    if group_by and group_by in cols:
        agg = _estate.aggregate(dataset_id, group_by, limit=12)
        arows = agg.get("rows") or []
        if arows:
            top = max(int(r.get("count", 0)) for r in arows) or 1
            bars = "".join(
                ck_bar_row(str(r.get(group_by) or "—")[:60],
                           f'{int(r.get("count", 0)):,}',
                           int(r.get("count", 0)) / top * 100.0,
                           tone="teal")
                for r in arows)
            bars += (
                '<div style="font-size:10px;color:var(--ck-text-faint,#8b94a0);'
                'margin-top:6px;font-family:var(--ck-mono,monospace);">'
                f'Top {len(arows)} groups by row count · group_by={_e(group_by)}</div>')
        else:
            bars = (
                '<div style="font-size:11px;color:var(--ck-text-dim,#56606f);">'
                'No groups — the local store has no rows for this dataset yet.</div>')
    return (
        '<div class="ck-panel" style="margin-bottom:16px;">'
        '<div class="ck-panel-title">Quick aggregate</div>'
        f'<div style="padding:10px 12px;">{form}{bars}</div></div>')


def _detail_view(dataset_id: str, params: dict[str, Any]) -> str:
    row = _estate.dataset_row(dataset_id)
    if row is None:
        return ck_empty_state(
            "Unknown dataset",
            f"No registry row named {dataset_id!r} exists in the connector estate.",
            eyebrow="CONNECTOR ESTATE",
            cta_label="Back to the estate", cta_href=_ROUTE)
    owner = row.get("connector", "")
    n_local = _estate.dataset_ingested_count(dataset_id)
    back = (f'<div style="margin:0 0 10px;"><a href="{_ROUTE}" '
            'style="font-size:11px;color:var(--ck-accent,#155752);">'
            f'← All connectors</a> · <a href="{_ROUTE}?connector={_e(owner)}" '
            'style="font-size:11px;color:var(--ck-accent,#155752);">'
            f'{_e(_estate.connector_label(owner))}</a></div>')

    parts = [back, ck_section_header("REGISTRY", f"declarative row for {dataset_id}"),
             _registry_fields(row)]

    hint = _estate.ingest_hint(owner)
    if n_local is not None:
        sample = _estate.sample_rows(dataset_id, limit=10)
        parts.append(ck_section_header(
            "LOCAL STORE",
            f"{n_local:,} rows ingested · first 10 shown, first 8 columns"))
        vintage = _estate.dataset_vintage(dataset_id)
        if vintage:
            parts.append(
                '<div style="font-family:var(--ck-mono,monospace);font-size:10px;'
                'color:var(--ck-text-faint,#8b94a0);margin:-4px 0 8px;">'
                f'last ingested {_e(vintage)}</div>')
        if sample.get("rows"):
            parts.append('<div class="ck-panel" style="margin-bottom:16px;">'
                         f'<div style="padding:10px 12px;">{_sample_table(sample)}</div></div>')
        else:
            parts.append(
                '<div style="font-size:11.5px;color:var(--ck-text-dim,#56606f);'
                'margin-bottom:16px;">Table is empty — fetch this dataset first '
                '(see the CLI one-liners below).</div>')
        parts.append(_aggregate_panel(dataset_id, params))
    elif hint.get("planned") is False:
        # Honest absent-data copy: refresh deliberately skips manual-only
        # connectors, so the old "run refresh, then reload" instruction
        # could never work for their datasets.
        parts.append(
            '<div style="font-size:11.5px;color:var(--ck-text-dim,#56606f);'
            'margin-bottom:16px;">No local ingest for this connector yet — '
            'the estate-level refresh skips it (manual-only: its ingest '
            'verbs need domain arguments). Ingest with '
            f'<code>{_e(hint.get("command", ""))}</code> — see '
            f'<code>{_e(hint.get("readme", f"connectors/{owner}/README.md"))}</code>.'
            '</div>')
    else:
        refresh_cmd = hint.get(
            "command",
            f"python -m connectors.cli refresh --db var/connectors "
            f"--connector {owner}")
        parts.append(
            '<div style="font-size:11.5px;color:var(--ck-text-dim,#56606f);'
            'margin-bottom:16px;">No local ingest for this connector yet — '
            f'run <code>{_e(refresh_cmd)}</code> '
            'from the repo root, then reload.</div>')

    api_url = f"/v1/query/{dataset_id}?limit=10"
    agg_url = f"/v1/query/{dataset_id}/aggregate?group_by=<column>"
    # Storage-flagged one-liner: without the flag the per-connector CLIs
    # query an empty default store and print 0 rows even after a full
    # ingest (the bridge knows each CLI's flag style via the estate SPI).
    cli_query = (_estate.cli_query_hint(dataset_id)
                 or f"python -m connectors.{owner}.cli query {dataset_id} --limit 10")
    if hint.get("planned") is False:
        ingest_line = (f"python -m connectors.{owner}.cli  "
                       f"# manual-only ingest — see connectors/{owner}/README.md")
    else:
        ingest_line = (f"python -m connectors.cli refresh --db var/connectors "
                       f"--connector {owner}")
    parts.append(ck_section_header("QUERY IT", "unified /v1 surface + CLI"))
    parts.append(
        '<div class="ck-panel" style="margin-bottom:16px;"><div style="padding:10px 12px;">'
        '<div style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;'
        'color:var(--ck-text-faint,#8b94a0);">Unified API '
        '(python -m connectors.cli serve --db var/connectors)</div>'
        + _code_block(api_url) + _code_block(agg_url) +
        '<div style="font-size:10px;text-transform:uppercase;letter-spacing:.08em;'
        'color:var(--ck-text-faint,#8b94a0);">CLI</div>'
        + _code_block(cli_query)
        + _code_block(ingest_line)
        + "</div></div>")
    return "".join(parts)


# ── list / search views ─────────────────────────────────────────────────


def _search_view(q: str) -> str:
    ql = q.lower()
    rows = [r for r in _estate.all_datasets()
            if ql in r.get("dataset_id", "").lower()
            or ql in r.get("target_table", "").lower()
            or ql in r.get("endpoint", "").lower()
            or ql in r.get("connector", "").lower()
            or ql in _estate.connector_label(r.get("connector", "")).lower()]
    header = ck_section_header(
        "SEARCH RESULTS", f"{len(rows)} datasets matching “{q}”")
    clear = (f'<div style="margin:0 0 10px;"><a href="{_ROUTE}" '
             'style="font-size:11px;color:var(--ck-accent,#155752);">'
             '← Clear search</a></div>')
    if not rows:
        return clear + header + ck_empty_state(
            "No datasets match",
            "Try a dataset id fragment (nadac, hcahps, faers), a table name, "
            "or a connector name (medicaid_data, openfda).",
            eyebrow="CONNECTOR ESTATE")
    return (clear + header
            + '<div class="ck-panel" style="margin-bottom:16px;">'
              f'<div style="padding:8px 12px;">{_datasets_table(rows, show_connector=True)}</div></div>')


def _search_box(q: str) -> str:
    return (
        f'<form method="get" action="{_ROUTE}" style="margin:14px 0;">'
        f'<input type="text" name="q" value="{_e(q)}" '
        'placeholder="Search datasets — id, table, endpoint, connector…" '
        'style="width:420px;max-width:92%;padding:8px 12px;border:1px solid '
        'var(--ck-border,#d8d0bf);border-radius:3px;font-size:12.5px;" />'
        '<button type="submit" style="margin-left:8px;padding:8px 16px;'
        'background:var(--ck-accent,#155752);color:#fff;border:none;'
        'border-radius:3px;font-size:12px;cursor:pointer;">Search</button>'
        '</form>')


def _overview(connector_filter: str,
              summaries: list[dict[str, Any]] | None = None,
              ingested: dict[str, int] | None = None,
              vintages: dict[str, str] | None = None) -> str:
    # Same compute-once threading as _kpi_strip: None self-serves.
    summaries = _estate.connectors_summary() if summaries is None else summaries
    ingested = _estate.ingested_counts() if ingested is None else ingested
    vintages = _estate.connector_vintages() if vintages is None else vintages
    by_conn: dict[str, list[dict[str, Any]]] = {}
    for r in _estate.all_datasets():
        by_conn.setdefault(r.get("connector", ""), []).append(r)
    parts: list[str] = []
    if connector_filter:
        summaries = [s for s in summaries
                     if s.get("connector") == connector_filter]
        if not summaries:
            return ck_empty_state(
                "Unknown connector",
                f"No connector named {connector_filter!r} is registered.",
                eyebrow="CONNECTOR ESTATE",
                cta_label="Back to the estate", cta_href=_ROUTE)
        parts.append(f'<div style="margin:0 0 10px;"><a href="{_ROUTE}" '
                     'style="font-size:11px;color:var(--ck-accent,#155752);">'
                     '← All connectors</a></div>')
    for s in summaries:
        name = s.get("connector", "")
        parts.append(_connector_card(
            s, by_conn.get(name, []), ingested,
            max_rows=None if connector_filter else 8,
            vintages=vintages))
    return "".join(parts)


def render_connector_estate(params: dict[str, Any] | None = None) -> str:
    params = params or {}
    if not _estate.estate_available():
        failure = _estate.load_failure()
        if failure:
            # The estate root RESOLVED but importing it raised — telling
            # the operator to "check out the full repository" would be
            # factually wrong (it IS checked out). Surface the cached
            # import error instead. Both strings are escaped inside
            # ck_empty_state.
            root = _estate.repo_root() or "(unresolved)"
            body = ck_page_title(
                "Connector Estate", eyebrow="Public Data",
                meta="connectors/ estate found but failed to load",
            ) + ck_empty_state(
                "Connector estate failed to load",
                f"The connectors/ estate was found at {root} but importing "
                f"it raised: {failure}. The checkout is present — no need "
                "to re-clone. Fix the import error (half-updated tree, "
                "syntax error), then restart the server; the failure is "
                "cached per root until then.",
                eyebrow="PUBLIC DATA",
                icon="⛁", tone="warning")
            return chartis_shell(
                body, "Connector Estate",
                active_nav=_ROUTE,
                subtitle="Public healthcare API estate — failed to load")
        body = ck_page_title(
            "Connector Estate", eyebrow="Public Data",
            meta="repo-root connectors/ estate not found on this deployment",
        ) + ck_empty_state(
            "Connector estate not available",
            "This deployment has no repo-root connectors/ estate on disk. "
            "Check out the full repository (the estate lives beside RCM_MC), "
            "then ingest and serve it: python -m connectors.cli refresh "
            "--db var/connectors && python -m connectors.cli serve "
            "--db var/connectors. Set RCM_MC_CONNECTORS_ROOT if the estate "
            "lives somewhere non-standard.",
            eyebrow="PUBLIC DATA",
            icon="⛁")
        return chartis_shell(body, "Connector Estate",
                             active_nav=_ROUTE,
                             subtitle="Public healthcare API estate — unavailable")

    # Compute the expensive per-request inputs ONCE and thread them
    # through the sub-renderers — ingested_counts() opens every
    # connector's SQLite file and COUNTs every canonical table, and this
    # page used to recompute it up to three times per GET.
    summaries = _estate.connectors_summary()
    ingested = _estate.ingested_counts()
    n_conn = len(summaries)
    n_reg = sum(s.get("n_datasets", 0) for s in summaries)
    n_rows = sum(ingested.values())
    meta = (f"{n_conn} connectors · {n_reg} registered datasets · "
            f"{n_rows:,} rows ingested locally")

    dataset = str(params.get("dataset", "") or "").strip()
    q = str(params.get("q", "") or "").strip()
    connector = str(params.get("connector", "") or "").strip()

    parts = [
        ck_page_title("Connector Estate", eyebrow="Public Data", meta=meta),
        _kpi_strip(summaries, ingested),
    ]
    if dataset:
        parts.append(_detail_view(dataset, params))
    elif q:
        parts.append(_search_box(q))
        parts.append(_search_view(q))
    else:
        parts.append(_search_box(""))
        parts.append(_overview(connector, summaries, ingested))
    return chartis_shell(
        "".join(parts), "Connector Estate",
        active_nav=_ROUTE,
        subtitle=f"Public healthcare API estate · {meta}")
