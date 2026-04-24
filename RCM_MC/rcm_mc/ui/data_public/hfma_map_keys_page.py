"""HFMA MAP Keys — codified RCM KPI library at /hfma-map-keys."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


_CATEGORY_ORDER = {
    "Patient Access": 1,
    "Clinical Charge Capture": 2,
    "Pre-Billing / Claims Production": 3,
    "Claims Adjudication": 4,
    "Customer Service": 5,
}


def _direction_color(d: str) -> str:
    if d == "higher-better":
        return P["positive"]
    return P["warning"]


def _link_type_color(t: str) -> str:
    return P["positive"] if t == "direct" else P["accent"]


def _fmt_bench(v: float, unit: str) -> str:
    if unit == "%":
        return f"{v:.1f}%"
    if unit == "$":
        return f"${v:,.0f}"
    if unit == "seconds":
        return f"{v:.0f}s"
    if unit == "score":
        return f"{v:.1f}"
    if unit == "ratio":
        return f"{v:.2f}"
    return f"{v:.1f} {unit}"


def _kpi_catalog_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("ID", "left"), ("Category", "left"), ("MAP Key", "left"),
            ("Unit", "center"), ("P25", "right"), ("P50", "right"),
            ("P75", "right"), ("Top Decile", "right"),
            ("Direction", "center"), ("Freq", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    ranked = sorted(items, key=lambda k: (_CATEGORY_ORDER.get(k.category, 99), k.map_key_id))
    for i, k in enumerate(ranked):
        rb = panel_alt if i % 2 == 0 else bg
        d_c = _direction_color(k.direction)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(k.map_key_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{acc}">{_html.escape(k.category)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:280px">{_html.escape(k.name)}</td>',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(k.unit)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text_dim}">{_fmt_bench(k.benchmark_p25, k.unit)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{_fmt_bench(k.benchmark_p50, k.unit)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{_fmt_bench(k.benchmark_p75, k.unit)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos};font-weight:700">{_fmt_bench(k.benchmark_top_decile, k.unit)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:9px;font-family:JetBrains Mono,monospace;color:{d_c};border:1px solid {d_c};border-radius:2px;letter-spacing:0.06em">{("HIGHER" if k.direction == "higher-better" else "LOWER")}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(k.frequency)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _category_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Category", "left"), ("KPIs", "right"), ("Higher-Better", "right"),
            ("Lower-Better", "right"), ("Instrumented", "right"),
            ("Avg P50→Top-Decile Spread", "right"), ("Description", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        inst_pct = (c.instrumented_count / c.kpi_count * 100.0) if c.kpi_count else 0.0
        inst_c = pos if inst_pct >= 70 else (acc if inst_pct >= 40 else text_dim)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(c.category)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{text}">{c.kpi_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{pos}">{c.higher_better_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">{c.lower_better_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{inst_c};font-weight:700">{c.instrumented_count}/{c.kpi_count}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{acc};font-weight:600">{c.avg_p50_spread_to_top_decile_pct:.1f}%</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:540px">{_html.escape(c.description)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _rationale_table(items) -> str:
    """Detail view — KPI + numerator/denominator + rationale."""
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("ID", "left"), ("MAP Key", "left"), ("Numerator / Denominator", "left"),
            ("Exclusions", "left"), ("Rationale", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    ranked = sorted(items, key=lambda k: (_CATEGORY_ORDER.get(k.category, 99), k.map_key_id))
    for i, k in enumerate(ranked):
        rb = panel_alt if i % 2 == 0 else bg
        nd = f"<strong style='color:{text}'>NUM:</strong> {_html.escape(k.numerator)}<br><strong style='color:{text}'>DEN:</strong> {_html.escape(k.denominator)}"
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700;vertical-align:top">{_html.escape(k.map_key_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{acc};font-weight:600;vertical-align:top;max-width:220px">{_html.escape(k.name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:380px;vertical-align:top">{nd}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:240px;vertical-align:top">{_html.escape(k.exclusions)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:440px;vertical-align:top">{_html.escape(k.rationale)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _instrumentation_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]
    cols = [("KPI", "left"), ("Name", "left"), ("Linked Module", "left"),
            ("Link Type", "center"), ("Notes", "left")]
    ths = "".join(f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid {border};font-size:10px;color:{text_dim};letter-spacing:0.05em">{c}</th>' for c, a in cols)
    trs = []
    for i, link in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        t_c = _link_type_color(link.link_type)
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:700">{_html.escape(link.map_key_id)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text};font-weight:600;max-width:240px">{_html.escape(link.map_key_name)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc};max-width:220px">{_html.escape(link.linked_module)}</td>',
            f'<td style="text-align:center;padding:5px 10px"><span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{t_c};border:1px solid {t_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(link.link_type.upper())}</span></td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim};max-width:540px">{_html.escape(link.notes)}</td>',
        ]
        trs.append(f'<tr style="background:{rb}">{"".join(cells)}</tr>')
    return (f'<div style="overflow-x:auto;margin-top:12px"><table style="width:100%;border-collapse:collapse;font-size:11px">'
            f'<thead><tr style="background:{bg}">{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_hfma_map_keys(params: dict = None) -> str:
    from rcm_mc.data_public.hfma_map_keys import compute_hfma_map_keys
    r = compute_hfma_map_keys()

    panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("HFMA MAP Keys", str(r.total_keys), "", "") +
        ck_kpi_block("Categories", str(len(r.category_stats)), "", "") +
        ck_kpi_block("Instrumented", str(r.total_instrumented), "", "") +
        ck_kpi_block("Coverage", f"{r.coverage_pct:.1f}%", "", "") +
        ck_kpi_block("Direct Links", str(sum(1 for l in r.instrumentation if l.link_type == "direct")), "", "") +
        ck_kpi_block("Adjacent Links", str(sum(1 for l in r.instrumentation if l.link_type == "adjacent")), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    cat_tbl = _category_table(r.category_stats)
    kpi_tbl = _kpi_catalog_table(r.kpis)
    rationale_tbl = _rationale_table(r.kpis)
    inst_tbl = _instrumentation_table(r.instrumentation)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    body = f"""
<div style="padding:20px;max-width:1400px;margin:0 auto">
  <div style="margin-bottom:20px">
    <h1 style="font-size:18px;font-weight:700;color:{text};letter-spacing:0.02em">HFMA MAP Keys — Codified RCM KPI Library</h1>
    <p style="font-size:12px;color:{text_dim};margin-top:4px">{r.total_keys} HFMA MAP Keys across 5 revenue-cycle categories · {r.total_instrumented} already instrumented in platform ({r.coverage_pct:.1f}% coverage) · benchmarks from HFMA MAP App public summaries + Advisory Board / Kaufman Hall / Crowe Horwath surveys — {r.corpus_deal_count:,} corpus deals anchored to this taxonomy</p>
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px">{kpi_strip}</div>
  <div style="{cell}"><div style="{h3}">Category Roll-Up — KPI Distribution + Platform Instrumentation Coverage</div>{cat_tbl}</div>
  <div style="{cell}"><div style="{h3}">KPI Catalog — Benchmarks (P25 / P50 / P75 / Top Decile)</div>{kpi_tbl}</div>
  <div style="{cell}"><div style="{h3}">KPI Definitions — Numerator / Denominator / Exclusions / Rationale</div>{rationale_tbl}</div>
  <div style="{cell}"><div style="{h3}">Instrumentation Cross-Links — KPI → Existing data_public Modules</div>{inst_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">HFMA MAP Keys Thesis:</strong>
    The HFMA MAP Keys are the industry-standard taxonomy for revenue-cycle performance —
    every HFMA-certified RCM leader on the target side is measured against this set.
    Codifying the {r.total_keys} KPIs with machine-readable numerator / denominator / exclusion logic gives every
    downstream diligence module a shared canonical definition, and cross-linking to the {r.total_instrumented} already-instrumented
    modules ({r.coverage_pct:.1f}% coverage) surfaces exactly where the platform's RCM analytics are speaking
    the same language as the target's ops team — and where it's not.
    Largest platform-maturity gap: <strong style="color:{text}">Patient Access</strong> (only 2/6 instrumented), the front-end
    category where 60-70% of denial root causes originate — this is the top knowledge-graph build priority after the
    NCCI scanner.
    <strong style="color:{text}">Claims Adjudication</strong> has the strongest coverage (7/8 instrumented), consistent with
    the platform's existing leakage and cost-structure modules. Average P50 → Top-Decile spread is widest in
    <strong style="color:{text}">Customer Service</strong> (60.7%) and <strong style="color:{text}">Pre-Billing / Claims Production</strong>
    (54.2%) — these are the categories where a mid-performer target can most realistically be pushed to top-decile post-close.
    Every benchmark on this page is a deal-sizing anchor: a target's gap-to-top-decile at acquisition × annual revenue base =
    the realistic value-creation-plan envelope.
  </div>
</div>"""

    return chartis_shell(body, "HFMA MAP Keys", active_nav="/hfma-map-keys")
