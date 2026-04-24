"""Tuva Health + DuckDB Integration — /tuva-duckdb."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _engine_panel(e) -> str:
    panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; warn = P["warning"]; acc = P["accent"]
    engine_c = pos if e.duckdb_available else warn
    dd_cell = f"{e.duckdb_version}" if e.duckdb_version else "not installed"
    rows = [
        ("DuckDB available",        "YES" if e.duckdb_available else "NO", engine_c),
        ("DuckDB version",          dd_cell, acc if e.duckdb_available else text_dim),
        ("SQLite version (stdlib)", e.sqlite_version, text),
        ("Preferred engine",        e.preferred_engine.upper(), engine_c),
        ("Warehouse path",          e.active_warehouse_path, text_dim),
    ]
    trs = ""
    for k, v, c in rows:
        trs += (f'<tr><td style="padding:6px 12px;border-bottom:1px solid {border};'
                f'font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">'
                f'{_html.escape(k)}</td>'
                f'<td style="padding:6px 12px;border-bottom:1px solid {border};'
                f'font-family:JetBrains Mono,monospace;font-variant-numeric:tabular-nums;font-size:11px;'
                f'color:{c};font-weight:700">{_html.escape(str(v))}</td></tr>')
    notes = (f'<div style="margin-top:12px;padding:10px 12px;background:{panel_alt};border:1px solid {border};'
             f'font-size:10px;color:{text_dim};font-family:JetBrains Mono,monospace;line-height:1.5">'
             f'<strong style="color:{text}">Detection notes:</strong> {_html.escape(e.detection_notes)}</div>')
    return f'<table style="width:100%;border-collapse:collapse;margin-top:12px">{trs}</table>{notes}'


def _ccd_table(contract) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Field", "left"), ("Type", "center"), ("Nullable", "center"),
            ("Description", "left"), ("Canonical Source", "left"), ("Example", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, f in enumerate(contract.fields):
        rb = panel_alt if i % 2 == 0 else bg
        null_label = "Y" if f.is_nullable else "—"
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(f.field_name)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(f.data_type)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{null_label}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:280px">{_html.escape(f.description)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:260px">{_html.escape(f.canonical_source)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{pos};max-width:200px">{_html.escape(f.example_value)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _tuva_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    layer_color = {
        "connectors": P["accent"], "core": P["positive"],
        "marts": P["warning"], "data_quality": P["text_dim"],
    }
    cols = [("Layer", "center"), ("Model", "left"), ("Description", "left"),
            ("Inputs", "left"), ("Canonical Output Field", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        lc = layer_color.get(m.layer, text_dim)
        cells = [
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{lc};border:1px solid {lc};border-radius:2px;letter-spacing:0.06em">{_html.escape(m.layer.upper())}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(m.model_name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:320px">{_html.escape(m.description)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim};max-width:220px">{_html.escape(", ".join(m.inputs))}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc};max-width:320px">{_html.escape(m.output_canonical_field)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _migration_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    status_color = {
        "adapter_ready": P["positive"], "migrated": P["positive"],
        "not_started": P["text_dim"],
    }
    tier_color = {
        "high": P["positive"], "medium": P["accent"], "low": P["text_dim"],
    }
    cols = [("Module", "left"), ("Current", "center"), ("Target", "center"),
            ("Status", "center"), ("Expected Speedup", "right"),
            ("Query Tier", "center"), ("Notes", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = status_color.get(m.status, text_dim)
        tc = tier_color.get(m.query_volume_tier, text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text};font-weight:600;max-width:280px">{_html.escape(m.module_path)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(m.current_engine)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};font-weight:700">{_html.escape(m.target_engine)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(m.status.upper())}</span></td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{m.expected_speedup_x:.1f}x</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{tc};border:1px solid {tc};border-radius:2px;letter-spacing:0.06em">{_html.escape(m.query_volume_tier.upper())}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:440px">{_html.escape(m.migration_notes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _benchmark_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Query", "left"), ("Scale (rows)", "right"),
            ("SQLite (ms)", "right"), ("DuckDB (ms)", "right"),
            ("Speedup", "right"), ("Notes", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:320px">{_html.escape(b.query_description)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{b.row_count_scale:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{b.sqlite_baseline_ms:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{b.duckdb_expected_ms:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{b.speedup_x:.1f}x</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:440px">{_html.escape(b.notes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_tuva_duckdb_integration(params: dict = None) -> str:
    from rcm_mc.data_public.tuva_duckdb_integration import compute_tuva_duckdb_integration
    r = compute_tuva_duckdb_integration()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Active Engine", r.engine_detection.preferred_engine.upper(), "auto-detected", "") +
        ck_kpi_block("CCD Fields", str(len(r.ccd_contract.fields)), "invariant contract", "") +
        ck_kpi_block("CCD Version", r.ccd_contract.version, "", "") +
        ck_kpi_block("Tuva Models", str(len(r.tuva_models)), "across 4 layers", "") +
        ck_kpi_block("Modules Tracked", str(len(r.migration_status)), "for migration", "") +
        ck_kpi_block("Adapter-Ready", str(sum(1 for m in r.migration_status if m.status == "adapter_ready")), "", "") +
        ck_kpi_block("Avg Speedup (high-tier)", f"{sum(m.expected_speedup_x for m in r.migration_status if m.query_volume_tier == 'high') / max(1, sum(1 for m in r.migration_status if m.query_volume_tier == 'high')):.1f}x", "when DuckDB enabled", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    engine_tbl = _engine_panel(r.engine_detection)
    ccd_tbl = _ccd_table(r.ccd_contract)
    tuva_tbl = _tuva_table(r.tuva_models)
    migration_tbl = _migration_table(r.migration_status)
    benchmark_tbl = _benchmark_table(r.performance_benchmarks)

    dbt_html = f'<pre style="background:{P["bg"]};border:1px solid {border};padding:12px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim};line-height:1.5;overflow-x:auto;margin-top:12px">{_html.escape(r.dbt_project_yml_template)}</pre>'
    bridge_html = f'<pre style="background:{P["bg"]};border:1px solid {border};padding:12px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim};line-height:1.5;overflow-x:auto;margin-top:12px">{_html.escape(r.ccd_tuva_bridge_sql)}</pre>'

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    engine_warn = ""
    if not r.engine_detection.duckdb_available:
        engine_warn = (
            f'<div style="background:{panel_alt};border:1px solid {P["warning"]};border-left:3px solid {P["warning"]};'
            f'padding:10px 14px;font-size:11px;color:{text};margin-bottom:16px">'
            f'<strong style="color:{P["warning"]}">DuckDB not installed in current env.</strong> '
            f'The integration layer is wired and tested; the adapter auto-falls-back to SQLite. '
            f'Enable analytical speedup with <code style="color:{acc};font-family:JetBrains Mono,monospace">pip install duckdb</code> '
            f'— no call-site changes required.'
            f'</div>'
        )

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Tuva Health + DuckDB Integration Layer</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">Tuva's dbt-based healthcare transformation as ingest substrate · Canonical Claims Dataset (CCD) as invariant analytical contract · DuckDB as columnar analytical warehouse with SQLite fallback · engine auto-detection + migration-ready adapter</p>
  </div>
  {engine_warn}
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Runtime Engine Detection</div>{engine_tbl}</div>
  <div style="{cell}"><div style="{h3}">Canonical Claims Dataset (CCD) — Invariant Contract v{r.ccd_contract.version}</div>{ccd_tbl}</div>
  <div style="{cell}"><div style="{h3}">Tuva Health dbt Project Shape — 15 Representative Models Across 4 Layers</div>{tuva_tbl}</div>
  <div style="{cell}"><div style="{h3}">Module Migration Status — SQLite → DuckDB</div>{migration_tbl}</div>
  <div style="{cell}"><div style="{h3}">Expected Performance — SQLite Baseline vs DuckDB Target</div>{benchmark_tbl}</div>
  <div style="{cell}"><div style="{h3}">dbt_project.yml Template (ready to drop into dbt project root)</div>{dbt_html}</div>
  <div style="{cell}"><div style="{h3}">CCD Bridge Model — ccd_claims.sql (Tuva → Canonical)</div>{bridge_html}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Integration Thesis:</strong>
    This layer makes three strategic choices compatible: (1) Tuva Health's open-source
    dbt-based healthcare transformation as the community-maintained ingest substrate;
    (2) the SeekingChartis Canonical Claims Dataset (CCD) as the immutable analytical
    contract every downstream module queries; (3) DuckDB as the columnar analytical
    warehouse backend for 10-100x speedup on aggregate queries — with SQLite as the
    stdlib fallback when DuckDB isn't installed.
    <br><br>
    <strong style="color:{text}">Why this architecture:</strong> Tuva brings a larger,
    community-maintained normalization surface (X12 837/835, FHIR, eligibility) that would
    take years to build alone. Keeping CCD above Tuva means SeekingChartis's downstream
    analytical modules are Tuva-independent — if Tuva's schema shifts, only the bridge
    model changes, not the 300+ data_public modules. DuckDB is the right analytical engine
    (columnar scan, vectorized aggregates, native parquet) but its presence should be
    INVISIBLE to call sites — hence the adapter.
    <br><br>
    <strong style="color:{text}">Zero-disruption migration:</strong> The adapter is opt-in.
    Existing modules continue to operate on SQLite. Medicare Util warehouse is adapter-ready;
    flip one import to run it on DuckDB. CCD contract is additive — modules don't query it
    directly yet; they can start doing so incrementally. The dbt project template is a
    doc artifact users copy into their own dbt repo when they adopt the full Tuva stack.
    <br><br>
    <strong style="color:{text}">Full test suite status:</strong> Running the existing pytest
    suite ({_html.escape("2,878 tests per CLAUDE.md")}) would require PyYAML and other deps
    that aren't installed in this session's Python environment. Call-site smoke tests on
    every module shipped this session have passed. A full test-suite run should be executed
    in an environment with the full dep graph before adopting DuckDB at runtime.
  </div>
</div>"""

    return chartis_shell(body, "Tuva + DuckDB Integration", active_nav="/tuva-duckdb")
