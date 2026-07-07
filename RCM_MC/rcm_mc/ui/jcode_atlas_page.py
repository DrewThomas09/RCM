"""J-Code Atlas — the page for ``diligence.jcode_atlas``.

Scans every infusion J-code by site of care (home / office / ambulatory
suite / HOPD), shows THE CHANGE (the 2018→now home / out-of-hospital
migration) code by code, and ties each code to its disease + the size of
the patient pool it serves. The "scan infusion codes by home vs in
office and the change", made concrete per HCPCS code.

Built on the chartis editorial kit: strict Tier-1 5-block head, kit
KPI grid with provenance tooltips, ``ck_data_table``/``ck_data_cell``
tables (mono J-codes, right-aligned 2dp dollars, tabular-nums), and a
therapeutic-area grouping on the code-level scan so an associate can
read the atlas class by class rather than as one flat 48-row list.
"""
from __future__ import annotations

import html
import math
import urllib.parse
from typing import Any, Dict, List

from ._chartis_kit import (
    chartis_shell, ck_arrow_link, ck_data_cell, ck_data_table,
    ck_editorial_head, ck_empty_state, ck_fmt_number, ck_kpi_block,
    ck_page_actions, ck_provenance_tooltip, ck_section_header,
    ck_signal_badge,
)

# ── Chart palette — SVG fills ONLY (README "Inline-SVG editorial
#    charts" conventions). Text / borders / surfaces use kit CSS vars
#    with canonical fallbacks in _PAGE_CSS below, never these hexes.
_POS = "#0a8a5f"      # semantic positive (gaining out-of-hospital)
_WARN = "#b8732a"     # semantic warning (HOPD / back to hospital)
_GRID = "#E8E0D0"     # documented gridline
_RULE = "#BFB6A2"     # documented rule
_MUTED = "#5C6878"    # documented muted (SVG text fill)
_INK = "#1a2332"      # documented ink (SVG text fill)

# Site-of-care palette — out-of-hospital sites in greens/teals, HOPD in
# the warning amber (the share being steered away). All four are
# documented README chart tones.
_SITE_COLOR = {"home": "#0a8a5f", "office": "#1F7A75",
               "aic": "#7ED3A8", "hopd": "#b8732a"}
_SITE_LABEL = {"home": "Home", "office": "Office", "aic": "Amb. suite",
               "hopd": "HOPD"}

# Coarse therapeutic-area rollup for the scan-table grouping. The raw
# drug_class taxonomy is 39 classes over 48 codes (mostly singletons),
# so the group subheads use a prefix-driven rollup that reads the way a
# diligence associate scans a code atlas: "the IVIG block", "the
# immunology biologics", "oncology + support". Exact drug_class still
# renders per row under the drug name.
_AREA_PREFIXES = (
    ("Immune globulin", "Immune globulin (IVIG / SCIG)"),
    ("Immunology", "Immunology biologics"),
    ("Oncology", "Oncology & oncology support"),
    ("Neurology", "Neurology biologics"),
    ("Enzyme replacement", "Enzyme replacement"),
    ("Hemophilia", "Hematology & hemophilia"),
    ("Hematology", "Hematology & hemophilia"),
    ("Respiratory", "Respiratory biologics"),
    ("Complement inhibitor", "Complement & HAE"),
    ("HAE", "Complement & HAE"),
    ("PAH", "Cardio-pulmonary infusion"),
    ("Cardiology", "Cardio-pulmonary infusion"),
    ("Ophthalmology", "Ophthalmology (intravitreal)"),
)


def _therapeutic_area(drug_class: str) -> str:
    for prefix, area in _AREA_PREFIXES:
        if drug_class.startswith(prefix):
            return area
    return drug_class


# Page-scoped CSS — kit vars with canonical fallbacks only; the raw
# hexes are confined to SVG fills above and the legend swatches (chart
# palette), per the README chart conventions.
_PAGE_CSS = """
.jc-atlas{max-width:1180px;}
.jc-cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));
  gap:16px;align-items:start;margin:0 0 18px;}
.jc-scatter-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));
  gap:18px;align-items:start;margin-bottom:18px;}
.jc-panel{border:1px solid var(--sc-rule,#d6cfc0);border-radius:5px;
  padding:12px 14px;background:var(--paper-card,#fefcf3);}
.jc-panel-title{font-family:var(--sc-mono,'JetBrains Mono',monospace);
  font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;
  color:var(--sc-text-dim,#465366);margin:0 0 6px;}
.jc-panel-sub{font-size:10.5px;color:var(--sc-text-dim,#465366);margin:0 0 6px;}
.jc-sub{font-size:12px;line-height:1.55;color:var(--sc-text-dim,#465366);
  margin:2px 0 8px;max-width:82ch;}
.jc-sub em{color:var(--green-deep,#154e36);}
.jc-note{font-size:11px;color:var(--sc-text-dim,#465366);margin-top:14px;
  line-height:1.6;max-width:92ch;}
.jc-legend{display:flex;flex-wrap:wrap;gap:12px;align-items:center;
  margin:4px 0 10px;}
.jc-legend span{display:inline-flex;align-items:center;gap:5px;
  font-size:10.5px;color:var(--sc-text-dim,#465366);}
.jc-sw{width:10px;height:10px;border-radius:2px;display:inline-block;}
.jc-sw-home{background:#0a8a5f;}.jc-sw-office{background:#1F7A75;}
.jc-sw-aic{background:#7ED3A8;}.jc-sw-hopd{background:#b8732a;}
.jc-sitebar{border-radius:2px;overflow:hidden;display:block;}
.jc-shift{display:inline-flex;align-items:center;gap:5px;}
.jc-shift-v{font-family:var(--sc-mono,'JetBrains Mono',monospace);
  font-variant-numeric:tabular-nums;font-weight:700;font-size:10.5px;
  min-width:40px;}
.jc-shift-v.pos{color:var(--sc-positive,#0a8a5f);}
.jc-shift-v.neg{color:var(--sc-warning,#b8732a);}
.jc-drugname{display:block;font-weight:600;color:var(--sc-text,#1a2332);}
.jc-drugclass{display:block;font-size:10.5px;color:var(--sc-text-dim,#465366);}
.jc-mix{display:block;font-size:10.5px;color:var(--sc-text-dim,#465366);
  margin-top:2px;}
.jc-dim{color:var(--sc-text-dim,#465366);}
.jc-atlas .ck-badge{font-size:9.5px;padding:1px 6px;letter-spacing:.05em;
  margin-left:6px;vertical-align:1px;}
.jc-movers{margin:0;padding-left:20px;font-size:12px;}
.jc-movers li{margin-bottom:5px;line-height:1.45;}
.jc-movers .jc-code{font-family:var(--sc-mono,'JetBrains Mono',monospace);
  font-weight:700;color:var(--sc-teal-ink,#155752);}
.jc-movers .jc-pts{font-family:var(--sc-mono,'JetBrains Mono',monospace);
  font-weight:700;color:var(--sc-positive,#0a8a5f);}
.jc-vscroll{max-height:76vh;overflow:auto;border:1px solid var(--sc-rule,#d6cfc0);
  border-radius:4px;}
.jc-vscroll .ck-data-table thead th{position:sticky;top:0;z-index:3;
  background:var(--sc-bone,#f2ede3);}
.jc-atlas .ck-data-table tbody tr:not(.jc-group):hover{
  background:rgba(31,122,117,0.07);}
.jc-group td{background:var(--sc-bone,#f2ede3);
  border-top:2px solid var(--green-deep,#154e36);
  font-family:var(--sc-mono,'JetBrains Mono',monospace);font-size:10px;
  letter-spacing:.07em;text-transform:uppercase;
  color:var(--green-deep,#154e36);font-weight:700;padding:5px 10px;}
.jc-group .jc-group-meta{color:var(--sc-text-dim,#465366);font-weight:400;
  margin-left:10px;letter-spacing:.05em;}
.jc-chart{width:100%;max-width:580px;height:auto;}
.jc-chart text{font-family:var(--sc-mono,'JetBrains Mono',monospace);}
.jc-chart-caption{font-family:var(--sc-mono,'JetBrains Mono',monospace);
  font-size:10px;letter-spacing:.06em;text-transform:uppercase;
  color:#5C6878;margin:4px 0 8px;}
.jc-live-note{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
  font-size:11.5px;color:var(--sc-text-dim,#465366);
  border:1px solid var(--sc-rule,#d6cfc0);border-radius:4px;
  background:var(--paper-card,#fefcf3);padding:7px 11px;margin:0 0 12px;}
.jc-links{display:flex;flex-wrap:wrap;gap:18px;align-items:center;
  margin:16px 0 22px;}
.jc-links code{font-size:10.5px;}
@media print{
  .jc-atlas svg{print-color-adjust:exact;-webkit-print-color-adjust:exact;}
  .jc-vscroll{max-height:none;overflow:visible;border:none;}
}
"""


def _site_bar(mix: Dict[str, float], width: int = 150) -> str:
    """A 100%-stacked horizontal site-of-care bar for one mix dict."""
    segs = ""
    x = 0.0
    for s in ("home", "office", "aic", "hopd"):
        w = max(0.0, float(mix.get(s, 0.0))) * width
        if w <= 0:
            continue
        segs += (f'<rect x="{x:.1f}" y="0" width="{w:.1f}" height="11" '
                 f'fill="{_SITE_COLOR[s]}"><title>{_SITE_LABEL[s]}: '
                 f'{mix.get(s, 0) * 100:.1f}%</title></rect>')
        x += w
    aria = ", ".join(f'{_SITE_LABEL[s]} {mix.get(s, 0) * 100:.1f}%'
                     for s in ("home", "office", "aic", "hopd"))
    return (f'<svg width="{width}" height="11" viewBox="0 0 {width} 11" '
            f'preserveAspectRatio="xMidYMid meet" class="jc-sitebar" '
            f'role="img" aria-label="Site mix: {html.escape(aria, quote=True)}">'
            f'{segs}</svg>')


def _shift_bar(pts: float, scale: float = 1.4) -> str:
    """A diverging bar centered on zero for a +/- percentage-point change.
    Green right (gaining out-of-hospital), amber left (back to hospital)."""
    half = 46.0
    w = min(half, abs(pts) * scale)
    tone = "pos" if pts >= 0 else "neg"
    color = _POS if pts >= 0 else _WARN
    sign = "+" if pts > 0 else ""
    if pts >= 0:
        rect = (f'<rect x="{half:.1f}" y="0" width="{w:.1f}" height="10" '
                f'fill="{color}" rx="1"/>')
    else:
        rect = (f'<rect x="{half - w:.1f}" y="0" width="{w:.1f}" height="10" '
                f'fill="{color}" rx="1"/>')
    return (
        f'<span class="jc-shift">'
        f'<svg width="{half * 2:.0f}" height="10" '
        f'viewBox="0 0 {half * 2:.0f} 10" role="img" '
        f'aria-label="{sign}{pts:.1f} points out of hospital">'
        f'<line x1="{half:.0f}" y1="0" x2="{half:.0f}" y2="10" '
        f'stroke="{_RULE}" stroke-width="1"/>{rect}</svg>'
        f'<span class="jc-shift-v {tone}">{sign}{pts:.1f}</span></span>')


def _legend() -> str:
    items = "".join(
        f'<span><span class="jc-sw jc-sw-{s}"></span>{_SITE_LABEL[s]}</span>'
        for s in ("home", "office", "aic", "hopd"))
    return f'<div class="jc-legend">{items}</div>'


def _book_change_panel(summary: Dict[str, Any], then_year: int,
                       now_year: int) -> str:
    """The whole-book home/office/AIC/HOPD mix now vs then + the change."""
    now, then = summary["book_mix_now"], summary["book_mix_then"]
    chg = summary["book_change_pts"]
    rows = ""
    for s in ("home", "office", "aic", "hopd"):
        c = chg[s]
        tone = "pos" if c > 0 else "neg" if c < 0 else "dim"
        delta = f"{c:+.1f}" if c else "0.0"
        rows += (
            "<tr>"
            + ck_data_cell(
                f'<span class="jc-sw jc-sw-{s}"></span> {_SITE_LABEL[s]}')
            + ck_data_cell(f"{then[s] * 100:.1f}%", align="right",
                           mono=True, tone="dim")
            + ck_data_cell(f"{now[s] * 100:.1f}%", align="right",
                           mono=True, weight=700)
            + ck_data_cell(delta, align="right", mono=True,
                           tone=tone, weight=700)
            + "</tr>")
    table = ck_data_table(
        headers=[{"label": "Site"},
                 {"label": str(then_year), "align": "right"},
                 {"label": str(now_year), "align": "right"},
                 {"label": "Δ pts", "align": "right"}],
        rows_html=rows, scrollable=False)
    return (
        '<section class="jc-panel">'
        '<h3 class="jc-panel-title">Whole-book site-of-care mix · '
        'demand-weighted</h3>'
        f'{table}</section>')


def _movers_panel(summary: Dict[str, Any]) -> str:
    items = ""
    for m in summary["top_movers"]:
        ooh = m["out_of_hospital_pts"]
        items += (
            f'<li><span class="jc-code">{html.escape(m["hcpcs"])}</span> '
            f'{html.escape(m["drug"])} '
            f'<span class="jc-pts">{ooh:+.1f} pts</span> '
            f'<span class="jc-dim">out of hospital</span></li>')
    return (
        '<section class="jc-panel">'
        '<h3 class="jc-panel-title">Biggest site-of-care movers</h3>'
        f'<ol class="jc-movers">{items}</ol></section>')


def _biosim_badge() -> str:
    return ck_signal_badge("BIOSIM", tone="warning")


def _scan_table(scan: List[Dict[str, Any]]) -> str:
    """The 48-code site-of-care scan, grouped by therapeutic area.

    Groups are ordered by their demand-weighted pooled migration (the
    fastest-moving class first); within a group rows keep the global
    migration rank. The table opts out of the kit's click-to-sort
    (``data-no-sort``) because re-sorting would scramble the group
    subhead rows, and out of hover-totals (``data-no-totals``) because
    patient pools overlap across brands and must not be summed.
    """
    if not scan:
        return ck_empty_state(
            "No J-codes in the catalog.",
            "The infusion J-code catalog returned no rows — check the "
            "data layer.", eyebrow="CODE-LEVEL SCAN")
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for r in scan:
        groups.setdefault(_therapeutic_area(r["drug_class"]), []).append(r)

    def _pooled_delta(rows: List[Dict[str, Any]]) -> float:
        wsum = sum(r["estimated_patients"] for r in rows) or 1
        return sum(r["out_of_hospital_pts"] * r["estimated_patients"]
                   for r in rows) / wsum

    ordered = sorted(
        groups.items(),
        key=lambda kv: (-_pooled_delta(kv[1]),
                        -sum(r["estimated_patients"] for r in kv[1])))

    rows_html = ""
    for area, rows in ordered:
        pooled = _pooled_delta(rows)
        rows_html += (
            f'<tr class="jc-group"><td colspan="7">'
            f'{html.escape(area)}'
            f'<span class="jc-group-meta">{len(rows)} code'
            f'{"s" if len(rows) != 1 else ""} · pooled Δ {pooled:+.1f} pts'
            f'</span></td></tr>')
        for r in rows:
            bio = _biosim_badge() if r["biosimilar"] else ""
            asp = r.get("asp_payment_limit_per_unit")
            asp_cell = (
                f"${asp:,.2f}" if asp is not None
                else '<span class="jc-dim" title="Paid at ASP+6% — '
                     'per-unit payment limit not fetched. Append ?live=1 '
                     'to pull the CMS ASP file.">—</span>')
            dz = ", ".join(r["diseases"][:2])
            if len(r["diseases"]) > 2:
                dz += f' +{len(r["diseases"]) - 2}'
            now = r["site_mix_now"]
            mix_line = (
                f'home {now["home"] * 100:.1f}% · '
                f'office {now["office"] * 100:.1f}% · '
                f'AIC {now["aic"] * 100:.1f}% · '
                f'HOPD {now["hopd"] * 100:.1f}%')
            rows_html += (
                "<tr>"
                + ck_data_cell(f'{html.escape(r["hcpcs"])}{bio}',
                               mono=True, weight=700, tone="acc")
                + ck_data_cell(
                    f'<span class="jc-drugname">{html.escape(r["drug"])}'
                    f'</span><span class="jc-drugclass">'
                    f'{html.escape(r["drug_class"])}</span>')
                + ck_data_cell(html.escape(dz), tone="dim")
                + ck_data_cell(
                    f'{_site_bar(now)}<span class="jc-mix">{mix_line}</span>')
                + ck_data_cell(_shift_bar(r["out_of_hospital_pts"]))
                + ck_data_cell(ck_fmt_number(r["estimated_patients"]),
                               align="right", mono=True)
                + ck_data_cell(asp_cell, align="right", mono=True)
                + "</tr>")

    heads = ""
    for label, align in (("J-code", ""), ("Drug / class", ""),
                         ("Disease", ""), ("Site of care (now)", ""),
                         ("Δ out-of-hospital (pts)", ""),
                         ("Est. patients", "right"),
                         ("ASP $/unit", "right")):
        cls = " ck-cell-r" if align == "right" else ""
        heads += (f'<th scope="col" class="ck-cell ck-data-table-head{cls}">'
                  f'{html.escape(label)}</th>')
    return (
        '<div class="ck-data-table-scroll jc-vscroll" role="region" '
        'aria-label="Site-of-care scan table" tabindex="0">'
        '<table class="ck-data-table" data-no-sort data-no-totals>'
        f'<thead><tr>{heads}</tr></thead>'
        f'<tbody>{rows_html}</tbody></table></div>')


def _disease_table(diseases: List[Dict[str, Any]]) -> str:
    """All diseases (no silent truncation), sortable, in a sticky-head
    scroll region. Hover-totals stay off: the per-disease pool is a MAX
    across overlapping brands, so a column sum would double-count."""
    if not diseases:
        return ck_empty_state(
            "No disease ties yet.",
            "No J-code in the catalog carries a disease indication — "
            "check the data layer.", eyebrow="DEMAND POOLS")
    rows_html = ""
    for d in diseases:
        dom = d["dominant_site"]
        dom_html = (f'<span class="jc-sw jc-sw-{html.escape(str(dom))}">'
                    f'</span> {_SITE_LABEL.get(dom, html.escape(str(dom)))}'
                    if dom in _SITE_LABEL else html.escape(str(dom)))
        ooh = d["out_of_hospital_pts"]
        tone = "pos" if ooh > 0 else "neg" if ooh < 0 else "dim"
        bio = _biosim_badge() if d["any_biosimilar"] else ""
        codes = ", ".join(d["codes"][:4]) + ("…" if len(d["codes"]) > 4
                                             else "")
        rows_html += (
            "<tr>"
            + ck_data_cell(f'{html.escape(d["disease"])}{bio}', weight=600)
            + ck_data_cell(str(d["n_codes"]), align="right", mono=True,
                           tone="dim")
            + ck_data_cell(html.escape(codes), mono=True, tone="dim")
            + ck_data_cell(ck_fmt_number(d["estimated_pool"]),
                           align="right", mono=True, weight=700)
            + ck_data_cell(dom_html)
            + ck_data_cell(f"{ooh:+.1f}" if ooh else "0.0", align="right",
                           mono=True, tone=tone, weight=700)
            + "</tr>")
    table = ck_data_table(
        headers=[{"label": "Disease"},
                 {"label": "Codes", "align": "right"},
                 {"label": "J-codes"},
                 {"label": "Est. pool", "align": "right"},
                 {"label": "Dominant site"},
                 {"label": "Δ OOH (pts)", "align": "right"}],
        rows_html=rows_html, scrollable=False)
    # data-no-totals: pools must not be summed (overlapping brands).
    table = table.replace('<table class="ck-data-table">',
                          '<table class="ck-data-table" data-no-totals>', 1)
    return ('<div class="ck-data-table-scroll jc-vscroll" role="region" '
            'aria-label="Disease demand-pool table" tabindex="0">'
            f'{table}</div>')


def _opportunity_panel(summary: Dict[str, Any]) -> str:
    """Ranked home-shift roll-up targets — which J-codes are the best
    home/AIC acquisition candidates (demand × momentum × HOPD runway)."""
    rows_html = ""
    for i, o in enumerate(summary["top_opportunities"], start=1):
        bio = _biosim_badge() if o["biosimilar"] else ""
        rows_html += (
            "<tr>"
            + ck_data_cell(str(i), mono=True, tone="dim")
            + ck_data_cell(f'{html.escape(o["hcpcs"])}{bio}', mono=True,
                           weight=700, tone="acc")
            + ck_data_cell(html.escape(o["drug"]))
            + ck_data_cell(f'{o["score"]:.0f}', align="right", mono=True,
                           weight=700, bar=o["score"])
            + ck_data_cell(ck_fmt_number(o["estimated_patients"]),
                           align="right", mono=True, tone="dim")
            + "</tr>")
    table = ck_data_table(
        headers=[{"label": "#"}, {"label": "Code"}, {"label": "Drug"},
                 {"label": "Score", "align": "right"},
                 {"label": "Est. patients", "align": "right"}],
        rows_html=rows_html, scrollable=False)
    return (
        '<section class="jc-panel">'
        '<h3 class="jc-panel-title">Home-shift roll-up targets</h3>'
        '<p class="jc-panel-sub">demand × migration momentum × HOPD '
        'runway · BIOSIM codes carry an ASP-erosion haircut</p>'
        f'{table}</section>')


def _pool_tick_label(k: int) -> str:
    """Axis label for a 10^k patient-pool tick: 1K / 10K / 100K / 1M."""
    if k >= 6:
        return f"{10 ** (k - 6)}M"
    if k >= 3:
        return f"{10 ** (k - 3)}K"
    return str(10 ** k)


def _migration_scatter(scan: List[Dict[str, Any]]) -> str:
    """A 2×2 of patient pool (x, log) vs out-of-hospital migration (y) —
    the "where is the volume, and is it moving?" quadrant. Bubbles are
    colored by the dominant current site of care."""
    if not scan:
        return ""  # README chart convention: guard empty input.
    W, H = 560, 320
    ml, mr, mt, mb = 48, 16, 30, 40
    pw, ph = W - ml - mr, H - mt - mb
    pools = [max(1, r["estimated_patients"]) for r in scan]
    xs = [math.log10(p) for p in pools]
    x0, x1 = min(xs), max(xs)
    xr = (x1 - x0) or 1.0
    ys = [r["out_of_hospital_pts"] for r in scan]
    y0, y1 = min(0.0, min(ys)), max(ys)
    yr = (y1 - y0) or 1.0

    def px(x):
        return ml + (x - x0) / xr * pw

    def py(y):
        return mt + (1 - (y - y0) / yr) * ph

    # Mono numeric scales on both axes (README chart conventions).
    ticks = ""
    for k in range(math.ceil(x0), math.floor(x1) + 1):
        tx = px(k)
        ticks += (
            f'<line x1="{tx:.0f}" y1="{mt}" x2="{tx:.0f}" y2="{mt + ph}" '
            f'stroke="{_GRID}" stroke-width="1"/>'
            f'<text x="{tx:.0f}" y="{mt + ph + 14:.0f}" text-anchor="middle" '
            f'font-size="9" fill="{_MUTED}">{_pool_tick_label(k)}</text>')
    y_step = 5.0 if yr <= 15 else 10.0
    ty = int(math.floor(y0 / y_step)) * y_step
    while ty <= y1:
        yy = py(ty)
        ticks += (
            f'<line x1="{ml}" y1="{yy:.0f}" x2="{ml + pw}" y2="{yy:.0f}" '
            f'stroke="{_GRID}" stroke-width="1"/>'
            f'<text x="{ml - 6:.0f}" y="{yy + 3:.0f}" text-anchor="end" '
            f'font-size="9" fill="{_MUTED}">'
            f'{f"{ty:+.0f}" if ty else "0"}</text>')
        ty += y_step

    # Quadrant split at the median pool and the mean migration.
    x_mid = sorted(xs)[len(xs) // 2]
    y_mid = sum(ys) / len(ys)
    grid = (
        f'<line x1="{px(x_mid):.0f}" y1="{mt}" x2="{px(x_mid):.0f}" '
        f'y2="{mt + ph}" stroke="{_RULE}" stroke-width="1" '
        f'stroke-dasharray="3,3"/>'
        f'<line x1="{ml}" y1="{py(y_mid):.0f}" x2="{ml + pw}" '
        f'y2="{py(y_mid):.0f}" stroke="{_RULE}" stroke-width="1" '
        f'stroke-dasharray="3,3"/>')
    # The high-value quadrant (big pool, fast migration) gets a tint.
    hv = (f'<rect x="{px(x_mid):.0f}" y="{mt}" '
          f'width="{ml + pw - px(x_mid):.0f}" '
          f'height="{py(y_mid) - mt:.0f}" fill="{_POS}" opacity="0.05"/>')
    dots = ""
    for r in scan:
        pool = max(1, r["estimated_patients"])
        cx = px(math.log10(pool))
        cy = py(r["out_of_hospital_pts"])
        dom = max(r["site_mix_now"], key=r["site_mix_now"].get)
        col = _SITE_COLOR.get(dom, _MUTED)
        rad = 3.0 + min(7.0, math.log10(pool))
        dots += (
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rad:.1f}" fill="{col}" '
            f'opacity="0.62" stroke="#fff" stroke-width="0.6">'
            f'<title>{html.escape(r["hcpcs"])} {html.escape(r["drug"])} — '
            f'{r["estimated_patients"]:,} patients, '
            f'{r["out_of_hospital_pts"]:+.1f} pts out of hospital</title>'
            f'</circle>')
    # Direct labels on the headline movers (skip overlapping labels).
    labels = ""
    placed: List[Any] = []
    for r in sorted(scan, key=lambda r: (-r["out_of_hospital_pts"],
                                         -r["estimated_patients"])):
        if len(placed) >= 4:
            break
        cx = px(math.log10(max(1, r["estimated_patients"])))
        cy = py(r["out_of_hospital_pts"])
        if any(abs(cx - qx) < 52 and abs(cy - qy) < 11 for qx, qy in placed):
            continue
        placed.append((cx, cy))
        labels += (f'<text x="{cx + 11:.0f}" y="{cy + 3:.0f}" '
                   f'font-size="8.5" fill="{_INK}" font-weight="700">'
                   f'{html.escape(r["hcpcs"])}</text>')
    captions = (
        f'<text x="{ml}" y="12" text-anchor="start" font-size="9" '
        f'fill="{_POS}" font-weight="700" letter-spacing="0.5">'
        f'Δ OUT-OF-HOSPITAL (PTS) ↑</text>'
        f'<text x="{ml + pw:.0f}" y="{H - 6:.0f}" text-anchor="end" '
        f'font-size="9" fill="{_MUTED}" letter-spacing="0.5">'
        f'PATIENT POOL, LOG SCALE →</text>')
    return (
        f'<svg viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet" '
        f'class="jc-chart" role="img" '
        f'aria-label="Scatter of {len(scan)} J-codes: patient pool '
        f'(log x-axis) vs points of share migrated out of hospital '
        f'(y-axis)">'
        f'{hv}{ticks}{grid}{dots}{labels}{captions}</svg>'
        '<div class="jc-chart-caption">Each bubble one J-code · size = '
        'patient pool · color = dominant site of care · shaded quadrant = '
        'big pool, fast migration</div>')


def _links_row(pop: "int | None", live: bool) -> str:
    """CSV export + cross-links to the sibling infusion surfaces."""
    params = {}
    if pop:
        params["pop"] = str(pop)
    if live:
        params["live"] = "1"
    q = ("?" + urllib.parse.urlencode(params)) if params else ""
    csv_href = html.escape(f"/api/diligence/jcode-atlas/export.csv{q}",
                           quote=True)
    return (
        '<div class="jc-links">'
        f'<a class="cad-btn cad-btn-primary" href="{csv_href}">'
        'Export site-of-care scan (CSV)</a>'
        + ck_arrow_link("Texas infusion deep-dive",
                        "/diligence/texas-infusion")
        + ck_arrow_link("National market scan",
                        "/diligence/infusion-markets")
        + '</div>')


def render_jcode_atlas_page(qs: "Dict[str, Any] | None" = None) -> str:
    from ..diligence.jcode_atlas import jcode_atlas

    qs = qs or {}
    # Optional geography scaling: ?pop=<int> scales the patient pools to a
    # real market (defaults to US). A partner can paste a state/metro pop.
    pop = None
    try:
        raw = qs.get("pop")
        if isinstance(raw, list):
            raw = raw[0] if raw else None
        if raw:
            pop = max(1, int(float(str(raw).replace(",", ""))))
    except (TypeError, ValueError):
        pop = None
    # Live ASP overlay is opt-in (?live=1) to keep the page fast offline.
    live = str((qs.get("live") or [""])[0] if isinstance(qs.get("live"), list)
               else qs.get("live") or "") in ("1", "true", "yes")

    a = jcode_atlas(population=pop, fetch_live=live)
    s = a["summary"]
    then_year, now_year = a["then_year"], a["now_year"]
    geo = a["geography"]
    geo_label = ("US (default)" if geo["is_default_us"]
                 else f'{geo["population"] / 1e6:.1f}M population')

    head = ck_editorial_head(
        eyebrow="DILIGENCE · INFUSION J-CODES",
        # Trusted pre-escaped markup per the helper's contract — the
        # raw string carries one "&amp;" so the H1 shows "&".
        title="J-Code Atlas — Site of Care &amp; Disease",
        meta=(f'{s["n_codes"]} J-codes · {s["n_diseases"]} diseases · '
              f'{then_year}→{now_year} site-of-care shift · {geo_label}'),
        lede_italic_phrase=(
            "Every infusion J-code, scanned by site of care"),
        lede_body=(
            "— home vs office vs ambulatory suite vs HOPD, the "
            f"{then_year}→{now_year} migration code by code, and the "
            "disease-level demand pool behind each code."),
        source_note=(
            "HCPCS codes + descriptors (CMS); FDA-labeled indications; "
            "published treated-prevalence anchors; site-of-care mix = "
            "labeled NHIA/MedPAC archetype anchors; ASP payment limits "
            "live from the CMS ASP file where egress permits."),
    )

    live_note = ""
    if live:
        n_priced = sum(1 for r in a["scan"] if r.get("asp_live"))
        tone = "positive" if n_priced else "warning"
        detail = (
            f'Live ASP pricing requested — {n_priced} of {s["n_codes"]} '
            'codes priced from the CMS ASP file.'
            + ("" if n_priced else
               " Fetch unavailable (offline?) — unpriced codes show an "
               "em-dash and are paid at ASP+6%."))
        live_note = (f'<div class="jc-live-note">'
                     f'{ck_signal_badge("LIVE ASP", tone=tone)}'
                     f'<span>{html.escape(detail)}</span></div>')

    kpi_codes = ck_provenance_tooltip(
        "Infusion J-codes", ck_fmt_number(s["n_codes"]),
        explainer=(
            "Count of HCPCS J-codes in the infusion catalog (CMS codes + "
            "descriptors). Every code carries at least one FDA-labeled "
            "indication and a treated-prevalence anchor."))
    kpi_migrating = ck_provenance_tooltip(
        "Migrating out of hospital", ck_fmt_number(s["n_migrating_home"]),
        explainer=(
            "Codes whose home + office + ambulatory-suite share gained "
            f"points {then_year}→{now_year}, per the labeled NHIA/MedPAC "
            "site-of-care archetype anchors."),
        inject_css=False)
    kpi_home_office = ck_provenance_tooltip(
        "Home + office now", f'{s["home_office_now"] * 100:.1f}%',
        explainer=(
            "Demand-weighted share of the whole infusion book infused at "
            "home or in the office today, weighted by each code's "
            "estimated patient pool."),
        inject_css=False)
    kpi_biosim = ck_provenance_tooltip(
        "Biosimilar / ASP-erosion", ck_fmt_number(s["n_biosimilar"]),
        explainer=(
            "Codes with a marketed biosimilar competitor. Biosimilar "
            "entry erodes the ASP payment limit and compresses the "
            "drug-margin spread."),
        inject_css=False)
    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Infusion J-codes", kpi_codes,
                       f'{s["n_diseases"]} diseases tied')
        + ck_kpi_block("Migrating out of hospital", kpi_migrating,
                       f'of {s["n_codes"]} codes',
                       f'{s["out_of_hospital_gain_pts"]:+.1f} pts')
        + ck_kpi_block(
            "Home + office now", kpi_home_office,
            f'from {s["home_office_then"] * 100:.1f}% in {then_year}',
            f'{(s["home_office_now"] - s["home_office_then"]) * 100:+.1f} '
            'pts')
        + ck_kpi_block("Biosimilar / ASP-erosion", kpi_biosim,
                       'codes flagged drug-margin risk')
        + '</div>')

    scatter_intro = (
        '<p class="jc-sub">Each J-code plotted by patient pool (x, log) '
        'vs out-of-hospital migration (y). The shaded upper-right '
        'quadrant — <em>big pool, fast migration</em> — is where a '
        'home/AIC platform competes hardest. Bubbles colored by dominant '
        'site of care.</p>')
    scan_intro = (
        f'<p class="jc-sub">Every J-code grouped by therapeutic area and '
        f'ranked by how far it has moved <em>out</em> of the hospital '
        f'({then_year}→{now_year}). Δ out-of-hospital = points of share '
        f'gained by home + office + ambulatory suite. BIOSIM marks codes '
        f'with a marketed biosimilar (ASP-erosion / drug-margin risk); '
        f'an em-dash in ASP $/unit means the code is paid at ASP+6% with '
        f'no fetched per-unit limit.</p>')
    disease_intro = (
        f'<p class="jc-sub">All {s["n_diseases"]} diseases, ranked by '
        f'pool — each with the J-codes that treat it, the '
        f'infusion-eligible patient pool ({geo_label}, real population × '
        f'published epi), the dominant site of care, and how fast its '
        f'drugs are migrating home. Full detail in the CSV export '
        f'below.</p>')

    note = (
        f'<p class="jc-note">{html.escape(a["note"])} '
        f'Pool = the largest single-code estimate per disease (brands of '
        f'one therapy overlap, so they are not summed). Append '
        f'<code>?pop=31000000</code> to scale pools to a market, or '
        f'<code>?live=1</code> for live ASP pricing.</p>')

    body = (
        '<div class="jc-atlas">'
        + head
        + live_note
        + kpis
        + '<div class="jc-cols">'
        + _book_change_panel(s, then_year, now_year)
        + _movers_panel(s)
        + '</div>'
        + ck_section_header("Where is the volume — and is it moving?",
                            eyebrow="MIGRATION MAP", count=s["n_codes"])
        + scatter_intro
        + '<div class="jc-scatter-row">'
        + f'<div>{_migration_scatter(a["scan"])}{_legend()}</div>'
        + _opportunity_panel(s)
        + '</div>'
        + ck_section_header("Site-of-care scan — by home vs office & "
                            "the change",
                            eyebrow="CODE-LEVEL SCAN", count=s["n_codes"])
        + scan_intro
        + _legend()
        + _scan_table(a["scan"])
        + _links_row(pop, live)
        + ck_section_header("J-codes tied to disease — the demand pool",
                            eyebrow="DEMAND POOLS", count=s["n_diseases"])
        + disease_intro
        + _disease_table(a["diseases"])
        + note
        + ck_page_actions()
        + '</div>')

    return chartis_shell(
        body, "J-Code Atlas", active_nav="/diligence",
        subtitle="Infusion J-codes · site of care & disease",
        extra_css=_PAGE_CSS)
