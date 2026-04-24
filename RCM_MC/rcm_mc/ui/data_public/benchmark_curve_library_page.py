"""Benchmark Curve Library — /benchmark-curves."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


def _source_color(s: str) -> str:
    return {
        "medicare_utilization": P["accent"],
        "irs_990_j":            P["positive"],
        "irs_990_h":            P["positive"],
        "hcris":                P["warning"],
    }.get(s, P["text_dim"])


def _fmt_by_unit(v: float, unit: str) -> str:
    if unit == "$":
        if abs(v) >= 1_000_000:
            return f"${v/1_000_000:,.2f}M"
        if abs(v) >= 1_000:
            return f"${v/1_000:,.1f}K"
        return f"${v:,.2f}"
    if unit == "%":
        return f"{v:,.2f}%"
    if unit == "HHI":
        return f"{v:,.0f}"
    if unit == "ratio":
        return f"{v:.2f}"
    return f"{v:.2f} {unit}"


def _families_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("ID", "left"), ("Curve Family", "left"), ("Source", "center"),
            ("Slice Dimensions", "left"), ("Rows", "right"),
            ("Sample Size", "right"), ("Effective Yr", "right"),
            ("Vendor Substitution", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, f in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        sc = _source_color(f.source)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(f.curve_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:360px">{_html.escape(f.curve_name)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{sc};border:1px solid {sc};border-radius:2px;letter-spacing:0.06em">{_html.escape(f.source.upper())}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:260px">{_html.escape(f.slice_dimensions)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{f.row_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{f.total_sample_size:,}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc}">{f.effective_year}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{pos};max-width:400px">{_html.escape(f.vendor_substitution)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _rows_table(items, limit=80) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Curve", "left"), ("Specialty", "left"), ("Payer", "left"),
            ("Region", "center"), ("Facility Type", "left"), ("Year", "right"),
            ("P10", "right"), ("P25", "right"), ("P50", "right"),
            ("P75", "right"), ("P90", "right"), ("Sample", "right")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, r in enumerate(items[:limit]):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(r.curve_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc};max-width:180px">{_html.escape(r.specialty or "—")}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:220px">{_html.escape(r.payer or "—")}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.region or "—")}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:220px">{_html.escape(r.facility_type or "—")}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.year}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_fmt_by_unit(r.p10, r.unit)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_fmt_by_unit(r.p25, r.unit)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:700">{_fmt_by_unit(r.p50, r.unit)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_fmt_by_unit(r.p75, r.unit)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{_fmt_by_unit(r.p90, r.unit)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{r.sample_size:,}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _methodology_table(families) -> str:
    """One row per curve family with methodology notes from a representative row."""
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("Curve", "left"), ("Metric", "left"), ("Unit", "center"),
            ("Methodology Notes", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    # Need to look up methodology_notes from the first row of each family.
    # Caller passes pre-built list of (family, sample_row) pairs.
    for i, (f, sample_row) in enumerate(families):
        rb = panel_alt if i % 2 == 0 else bg
        notes = sample_row.methodology_notes if sample_row else ""
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700;vertical-align:top">{_html.escape(f.curve_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{acc};font-weight:600;vertical-align:top;max-width:260px">{_html.escape(f.metric)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim};vertical-align:top">{_html.escape(f.unit)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:680px;vertical-align:top">{_html.escape(notes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_benchmark_curves(params: dict = None) -> str:
    from rcm_mc.data_public.benchmark_curve_library import compute_benchmark_library
    r = compute_benchmark_library()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Curve Families", str(r.total_curve_families), "", "") +
        ck_kpi_block("Curve Rows", f"{r.total_curve_rows:,}", "", "") +
        ck_kpi_block("Specialties", str(r.total_unique_specialties), "", "") +
        ck_kpi_block("Regions", str(r.total_unique_regions), "", "") +
        ck_kpi_block("Facility Types", str(r.total_unique_facility_types), "", "") +
        ck_kpi_block("Medicare-Derived", str(sum(1 for f in r.curve_families if f.source == "medicare_utilization")), "", "") +
        ck_kpi_block("990-Derived", str(sum(1 for f in r.curve_families if f.source.startswith("irs_990"))), "", "") +
        ck_kpi_block("HCRIS-Derived", str(sum(1 for f in r.curve_families if f.source == "hcris")), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    families_tbl = _families_table(r.curve_families)
    rows_tbl = _rows_table(r.curve_rows, limit=80)

    # Sample one row per family for the methodology table
    first_row_by_family = {}
    for row in r.curve_rows:
        if row.curve_id not in first_row_by_family:
            first_row_by_family[row.curve_id] = row
    pairs = [(f, first_row_by_family.get(f.curve_id)) for f in r.curve_families]
    methodology_tbl = _methodology_table(pairs)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">Benchmark Curve Library — Public-Data Substitutes for MGMA / Sullivan Cotter / Definitive</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_curve_families} curve families · {r.total_curve_rows:,} sliced distributions · {r.total_unique_specialties} specialties × {r.total_unique_regions} regions × {r.total_unique_facility_types} facility types · sourced from Medicare Provider Utilization, IRS 990 Schedule J / H, CMS HCRIS — Blueprint Moat Layer 2</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Curve Family Catalog — 8 Curves × Paid-Vendor Substitution Targets</div>{families_tbl}</div>
  <div style="{cell}"><div style="{h3}">Methodology per Curve Family</div>{methodology_tbl}</div>
  <div style="{cell}"><div style="{h3}">Top 80 Sliced Curve Rows — P10 / P25 / P50 / P75 / P90</div>{rows_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Benchmark Library Thesis:</strong>
    Paid vendors (MGMA, Sullivan Cotter, Definitive Healthcare, Kaufman Hall, Advisory Board, KFF)
    sell healthcare-benchmark libraries at 5-6 figures annually. This library substitutes them with
    curves computed from three fully-public sources:
    <strong style="color:{text}">CMS Medicare Provider Utilization</strong> (warehoused at /medicare-utilization) drives BC-01–BC-03 —
    per-CPT payment, per-physician Medicare revenue, and CPT concentration. Replaces MGMA CPT Compensation
    and Physician Production panels at ~75% fidelity.
    <strong style="color:{text}">IRS 990 Schedule J / H</strong> drives BC-04 (executive compensation) and BC-08
    (community benefit). Replaces Sullivan Cotter / ECG exec-comp benchmarks for the nonprofit / academic
    segment at ~85% fidelity.
    <strong style="color:{text}">CMS HCRIS worksheets</strong> drive BC-05 (operating margin), BC-06 (uncompensated care),
    BC-07 (nurse FTE). Replaces Definitive + Kaufman Hall hospital-panel benchmarks at ~80% fidelity.
    Every row carries P10 / P25 / P50 / P75 / P90 distribution, sample size, and methodology notes —
    regional slices scale by CMS GPCI (physician) or BLS OEWS (facility labor) factors.
    Total coverage: {r.total_curve_rows:,} distinct slice rows, each a queryable benchmark point.
    Target growth: 2,500+ curves spanning specialty × payer × region × facility × year per the Moat Layer 2 plan.
    This library is the substrate that makes backtesting (Moat Layer 4) and adversarial diligence
    (Moat Layer 5) possible — both need distributional priors that this module now provides.
  </div>
</div>"""

    return chartis_shell(body, "Benchmark Curve Library", active_nav="/benchmark-curves")
