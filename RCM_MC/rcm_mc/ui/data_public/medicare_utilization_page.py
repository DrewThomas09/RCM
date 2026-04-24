"""Medicare Provider Utilization & Payment Data warehouse — /medicare-utilization."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


_SCHEMA_COLS = [
    ("npi",                      "TEXT",    "NPI (anonymized synthetic in seed; real 10-digit in CMS refresh)"),
    ("provider_last_name",       "TEXT",    "Surname (CMS publishes; first name is not included in physician summary)"),
    ("provider_type",            "TEXT",    "CMS taxonomy label"),
    ("specialty_normalized",     "TEXT",    "Platform-internal specialty mapping (joins to NCCI, HFMA, OIG modules)"),
    ("state",                    "TEXT",    "Practice state (2-letter)"),
    ("hcpcs_code",               "TEXT",    "CPT or HCPCS Level II code"),
    ("hcpcs_description",        "TEXT",    "Short descriptor"),
    ("place_of_service",         "TEXT",    "'office' or 'facility'"),
    ("year",                     "INTEGER", "Reporting year (CMS publishes with ~2-year lag)"),
    ("service_count",            "INTEGER", "Total services rendered in year"),
    ("beneficiary_count",        "INTEGER", "Unique beneficiaries served"),
    ("avg_submitted_charge",     "REAL",    "Average charge submitted to Medicare"),
    ("avg_medicare_allowed",     "REAL",    "Average Medicare-allowed amount"),
    ("avg_medicare_payment",     "REAL",    "Average payment (allowed × 80%)"),
    ("total_medicare_payment",   "REAL",    "service_count × avg_payment"),
]


def _schema_table() -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Column", "left"), ("Type", "left"), ("Description", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, (name, typ, desc) in enumerate(_SCHEMA_COLS):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(typ)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:680px">{_html.escape(desc)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _specialty_profile_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Specialty", "left"), ("Providers", "right"), ("Codes", "right"),
            ("Services (M)", "right"), ("Payment ($M)", "right"),
            ("Concentration HHI", "right"), ("Top-5 HCPCS", "left"),
            ("Top-5 $M", "right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, p in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        hhi_c = neg if p.concentration_hhi >= 3000 else (acc if p.concentration_hhi >= 2000 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(p.specialty)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.provider_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{p.code_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{p.total_services_m:,.3f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${p.total_payment_mm:,.2f}M</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{hhi_c};font-weight:700">{p.concentration_hhi:,.0f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(p.top_5_codes)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${p.top_5_payment_mm:.2f}M</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _top_rows_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("NPI", "left"), ("Provider", "left"), ("State", "center"),
            ("Specialty", "left"), ("HCPCS", "left"), ("Description", "left"),
            ("POS", "center"), ("Services", "right"), ("Beneficiaries", "right"),
            ("Avg Allowed", "right"), ("Total Payment", "right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(r.npi)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(r.provider_last_name)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.state)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc}">{_html.escape(r.specialty_normalized)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(r.hcpcs_code)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:220px">{_html.escape(r.hcpcs_description)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.place_of_service)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{r.service_count:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.beneficiary_count:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">${r.avg_medicare_allowed:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">${r.total_medicare_payment:,.2f}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _baseline_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Deal", "left"), ("Year", "right"), ("Buyer", "left"),
            ("Inferred Specialty", "left"), ("Top HCPCS", "left"),
            ("Top Code Description", "left"), ("Avg Payment", "right"),
            ("Baseline $/Phys (K)", "right"), ("Confidence", "center")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, b in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        conf_c = pos if b.baseline_confidence == "high" else (acc if b.baseline_confidence == "medium" else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:600">{_html.escape(b.deal_name)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{b.year or "—"}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:220px">{_html.escape(b.buyer)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{acc};font-weight:600">{_html.escape(b.inferred_specialty)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(b.top_code)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:240px">{_html.escape(b.top_code_description)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">${b.top_code_avg_payment:,.2f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">${b.baseline_cpt_revenue_per_physician_k:,.1f}K</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{conf_c};border:1px solid {conf_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(b.baseline_confidence.upper())}</span></td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _meta_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Key", "left"), ("Value", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, m in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(m.key)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:860px;word-wrap:break-word">{_html.escape(m.value)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_medicare_utilization(params: dict = None) -> str:
    from rcm_mc.data_public.medicare_utilization import compute_medicare_utilization
    r = compute_medicare_utilization()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Warehouse Rows", f"{r.warehouse_row_count:,}", "", "") +
        ck_kpi_block("Distinct NPIs", f"{r.distinct_npis:,}", "", "") +
        ck_kpi_block("Distinct HCPCS", f"{r.distinct_hcpcs:,}", "", "") +
        ck_kpi_block("Specialties", str(r.distinct_specialties), "", "") +
        ck_kpi_block("Services (M)", f"{r.total_services_m:.2f}", "", "") +
        ck_kpi_block("Medicare $B", f"${r.total_medicare_payment_b:.3f}B", "", "") +
        ck_kpi_block("Source Year", str(r.source_year), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    schema_tbl = _schema_table()
    specialty_tbl = _specialty_profile_table(r.specialty_profiles)
    top_rows_tbl = _top_rows_table(r.top_codes_sample)
    baseline_tbl = _baseline_table(r.deal_baselines)
    meta_tbl = _meta_table(r.meta_rows)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Medicare Provider Utilization &amp; Payment Data Warehouse</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.warehouse_row_count:,} per-NPI × HCPCS × year rows · {r.distinct_npis} providers × {r.distinct_hcpcs} codes × {r.distinct_specialties} specialties · ${r.total_medicare_payment_b:.3f}B total Medicare payment · schema {r.schema_version} · source year {r.source_year} · SQLite warehouse (DuckDB-compatible schema) — ingested from <a href="{_html.escape(r.source_url)}" style="color:{acc}">CMS Provider Summary</a>, queryable via rcm_mc.data_public.medicare_utilization.MedicareUtilWarehouse</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Schema — medicare_utilization table</div>{schema_tbl}</div>
  <div style="{cell}"><div style="{h3}">Specialty Profiles — Payment × Concentration × Top Codes</div>{specialty_tbl}</div>
  <div style="{cell}"><div style="{h3}">Top 30 Rows by Total Medicare Payment</div>{top_rows_tbl}</div>
  <div style="{cell}"><div style="{h3}">Per-Deal Pre-Data-Room Baseline — Inferred Revenue Profile per Specialty</div>{baseline_tbl}</div>
  <div style="{cell}"><div style="{h3}">Warehouse Metadata ( _meta table)</div>{meta_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Warehouse Thesis:</strong>
    The CMS Medicare Provider Utilization &amp; Payment Data files publish annually with ~2-year lag and
    summarize every Medicare-participating provider's CPT/HCPCS-level claim volume. The blueprint's
    thesis on this dataset is precise: <strong style="color:{text}">it lets the platform compute provider-level
    benchmarks for any target without needing the target's own billing data</strong> — enough to build a baseline
    CPT-level revenue and utilization profile for most mid-to-large physician groups before they even open a data room.
    This warehouse is stored at <code style="color:{acc};font-family:JetBrains Mono,monospace">rcm_mc/data_public/_warehouse/medicare_utilization.db</code>
    (gitignored; regenerated from seed on first call). Schema is DuckDB-compatible — when DuckDB is adopted as a
    runtime dep per the OSS-stack blueprint, the MedicareUtilWarehouse class swaps engines via one import change,
    no query-site refactor needed. Specialty-normalized column joins directly to NCCI Edit Scanner (/ncci-scanner),
    HFMA MAP Keys (/hfma-map-keys), and OIG Work Plan (forthcoming) for cross-module analytics. Source year: {r.source_year}.
    Deal-baseline table demonstrates the pre-data-room utility: inferred per-physician revenue derived from inferred
    specialty footprint — producing a first-screen valuation sanity-check for any physician-group target.
    Incremental refresh via <code style="color:{acc};font-family:JetBrains Mono,monospace">refresh_medicare_utilization(year, source_manifest)</code>
    — source_manifest schema documented in module docstring.
  </div>
</div>"""

    return chartis_shell(body, "Medicare Provider Utilization Warehouse", active_nav="/medicare-utilization")
