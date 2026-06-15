"""J-code commercial benchmark, 2022–2026 —
``/diligence/texas-infusion/jcode-benchmark``.

The commercial buy-and-bill benchmark by HCPCS J-code across the hold
window: the published commercial-as-%-of-Medicare multiples, and a
J-code × year heatmap of the biosimilar-driven blended-ASP trajectory.
Built from public anchors only — Merative MarketScan (the licensed
commercial-claims source) is not vendored, and no commercial-claims
dollar is fabricated. Renders from
:mod:`rcm_mc.diligence.jcode_commercial_benchmark`. CSV at
``/diligence/texas-infusion/jcode-benchmark.csv``.
"""
from __future__ import annotations

import html
from typing import Any

from ._chartis_kit import (
    chartis_shell,
    ck_kpi_block,
    ck_page_title,
    ck_panel,
    ck_section_header,
    ck_source_purpose,
)
from .excel_mapping_page import gradient_color

_NAVY = "#0b2341"
_TEAL = "#155752"
_DIM = "#465366"
_FAINT = "#7a8699"
_POS = "#0a8a5f"
_WARN = "#b8732a"
_NEG = "#b5321e"

# Price-level ramp: eroded/commoditized (pale) → premium/rising (navy).
_LO, _MID, _HI = "#eaf1ea", "#7fb1aa", "#0b2341"

_TD = ('style="padding:5px 10px;border-bottom:1px solid '
       'var(--sc-rule,#e4ddcd);font-size:12.5px;"')
_TDN = ('style="padding:5px 10px;border-bottom:1px solid '
        'var(--sc-rule,#e4ddcd);font-size:12.5px;text-align:right;'
        'font-variant-numeric:tabular-nums;font-family:var(--sc-mono);"')
_TH = ('style="padding:6px 10px;border-bottom:2px solid '
       'var(--sc-rule,#c9c1ac);font-size:10.5px;letter-spacing:.06em;'
       'text-transform:uppercase;color:var(--sc-text-dim,#465366);'
       'text-align:left;"')
_THN = _TH.replace('text-align:left', 'text-align:right')

_TREND = {"eroding": _NEG, "rising": _POS, "stable": _DIM}


def _year_heatmap_svg(bench: dict) -> str:
    """J-code × year heatmap of the blended-ASP index (pre-competition
    molecule = 100). Cell colour = price level; the trailing column marks
    the 2022→2026 change so the biosimilar-erosion story reads at a
    glance."""
    rows = bench["jcodes"]
    years = bench["years"]
    if not rows:
        return ""
    label_w, cell_w, chg_w = 232, 78, 92
    row_h, head_h = 28, 40
    n = len(years)
    width = label_w + n * cell_w + chg_w + 12
    height = head_h + len(rows) * row_h + 8

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;display:block;font-family:'
        f'var(--sc-mono,monospace);" role="img" '
        f'aria-label="J-code commercial benchmark heatmap 2022-2026">']
    # Headers.
    for j, y in enumerate(years):
        cx = label_w + j * cell_w + cell_w / 2
        parts.append(
            f'<text x="{cx:.0f}" y="{head_h-14}" text-anchor="middle" '
            f'font-size="11" font-weight="700" fill="{_NAVY}">{y}</text>')
    parts.append(
        f'<text x="{label_w+n*cell_w+chg_w/2:.0f}" y="{head_h-14}" '
        f'text-anchor="middle" font-size="11" font-weight="700" '
        f'fill="{_NAVY}">Δ 22→26</text>')

    y = head_h
    for r in rows:
        lab = r["drug"].split(" (")[0]
        tone = _TREND.get(r["trend"], _DIM)
        entry = (f' · biosim {r["biosimilar_entry"]}'
                 if r["biosimilar_entry"] else "")
        parts.append(
            f'<text x="6" y="{y+row_h/2+1:.0f}" font-size="11" '
            f'fill="#1a2332">{html.escape(lab)}</text>'
            f'<text x="6" y="{y+row_h/2+11:.0f}" font-size="8" '
            f'fill="{tone}">{html.escape(r["hcpcs"])} · '
            f'{html.escape(r["trend"])}{html.escape(entry)}</text>')
        for j, yr in enumerate(years):
            v = float(r["index_by_year"][yr])
            fill = gradient_color(v, 48, 100, 113, _LO, _MID, _HI)
            txt = "#ffffff" if v >= 92 else "#1a2332"
            cx = label_w + j * cell_w
            parts.append(
                f'<rect x="{cx+2}" y="{y+2}" width="{cell_w-4}" '
                f'height="{row_h-4}" rx="2" fill="{fill}">'
                f'<title>{html.escape(lab)} {yr}: index {v:.0f}'
                f'</title></rect>'
                f'<text x="{cx+cell_w/2:.0f}" y="{y+row_h/2+4:.0f}" '
                f'text-anchor="middle" font-size="10.5" font-weight="700" '
                f'fill="{txt}">{v:.0f}</text>')
        chg = r["change_22_26"]
        cc = _NEG if chg < 0 else _POS if chg > 0 else _DIM
        ox = label_w + n * cell_w
        parts.append(
            f'<text x="{ox+chg_w/2:.0f}" y="{y+row_h/2+4:.0f}" '
            f'text-anchor="middle" font-size="11" font-weight="700" '
            f'fill="{cc}">{chg:+.0f}</text>')
        y += row_h
    parts.append("</svg>")
    return "".join(parts)


def _heat_legend() -> str:
    grad = f"linear-gradient(90deg,{_LO},{_MID},{_HI})"
    return (
        f'<div style="margin:8px 0 2px;font-size:11px;color:{_FAINT};">'
        'Blended-ASP index (pre-competition molecule = 100): '
        '<span style="display:inline-flex;align-items:center;gap:8px;'
        'vertical-align:middle;"><span>eroded</span>'
        f'<span style="width:120px;height:12px;border-radius:3px;'
        f'background:{grad};border:1px solid #d6cfc0;display:inline-block;">'
        '</span><span>premium</span></span> · '
        f'<span style="color:{_NEG};">red Δ</span> = biosimilar erosion, '
        f'<span style="color:{_POS};">green Δ</span> = supply-driven rise.')


def _multiple_table(bench: dict) -> str:
    rows = "".join(
        f'<tr><td {_TD}><strong>{html.escape(m["source"])}</strong></td>'
        f'<td {_TDN}>{m["multiple"]*100:.0f}%</td>'
        f'<td {_TD} style="font-size:11.5px;">{html.escape(m["basis"])}</td>'
        f'</tr>' for m in bench["multiples"])
    band = bench["multiple_band"]
    return (
        '<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr><th {_TH}>Benchmark</th>'
        f'<th {_THN}>Commercial % of Medicare</th><th {_TH}>Basis</th>'
        f'</tr></thead><tbody>{rows}'
        f'<tr><td {_TD}><strong>Blended band</strong></td>'
        f'<td {_TDN}><strong>{band["lo"]*100:.0f}–{band["hi"]*100:.0f}%'
        f'</strong></td><td {_TD} style="font-size:11.5px;color:'
        f'{_DIM};">commercial buy-and-bill range vs the Medicare ASP+6 '
        f'payment limit</td></tr></tbody></table>')


def _reference_table(bench: dict) -> str:
    rows = "".join(
        f'<tr><td {_TD}><strong style="font-family:var(--sc-mono);">'
        f'{html.escape(r["hcpcs"])}</strong></td>'
        f'<td {_TD}>{html.escape(r["drug"])}'
        f'<div style="font-size:11px;color:{_DIM};">'
        f'{html.escape(r["category"])} · {html.escape(r["channel"])}</div>'
        f'</td>'
        f'<td {_TD}><span style="color:{_TREND.get(r["trend"], _DIM)};'
        f'font-weight:600;">{html.escape(r["trend"])}</span></td>'
        f'<td {_TDN}>{r["biosimilar_entry"] or "—"}</td>'
        f'<td {_TD} style="font-size:11px;">{html.escape(r["competition"])}'
        f'</td></tr>' for r in bench["jcodes"])
    return (
        '<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr><th {_TH}>J-code</th><th {_TH}>Drug</th>'
        f'<th {_TH}>Trend</th><th {_THN}>Biosimilar entry</th>'
        f'<th {_TH}>Competition</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>')


def render_texas_infusion_jcode_benchmark_page(
        qs: dict[str, Any] | None = None) -> str:
    from ..diligence.jcode_commercial_benchmark import (
        jcode_commercial_benchmark)
    bench = jcode_commercial_benchmark()
    band = bench["multiple_band"]

    head = ck_page_title(
        "J-code commercial benchmark · 2022–2026",
        eyebrow="DILIGENCE · BUY-AND-BILL REIMBURSEMENT",
        meta=(f"{len(bench['jcodes'])} J-CODES · "
              f"{band['lo']*100:.0f}–{band['hi']*100:.0f}% OF MEDICARE · "
              f"{bench['eroding_count']} BIOSIMILAR-EXPOSED"),
    )
    src = ck_source_purpose(
        purpose=("Benchmark commercial buy-and-bill reimbursement by "
                 "HCPCS J-code across the hold window — the published "
                 "commercial multiples plus the biosimilar-driven ASP "
                 "trajectory that moves each molecule 2022→2026."),
        universe="cms",
        source=("CMS Part B ASP+6 payment mechanics · published "
                "commercial-rate multiples (HCCI / CBO / MedPAC / KFF / "
                "Milliman) · public FDA biosimilar approval/launch years"),
        confidence="modeled",
        next_action="Open the Texas revenue build",
        next_href="/diligence/texas-infusion/revenue",
    )

    marketscan = ck_panel(
        f'<div class="ck-section-body" style="font-size:13px;line-height:'
        f'1.55;"><p style="margin:0;"><strong>Merative MarketScan note.'
        f'</strong> {html.escape(bench["marketscan_note"])} This page is '
        f'the public-anchor proxy: the commercial multiples and the '
        f'biosimilar-entry ASP trajectory, not commercial-claims data. '
        f'When a licensed extract is loaded, the modeled index columns '
        f'are replaced with actual commercial allowed amounts.</p></div>',
        title="Data source — licensed vs public")

    kpis = (
        '<div class="ck-kpi-row" style="display:grid;grid-template-'
        'columns:repeat(4,1fr);gap:12px;margin:16px 0;">'
        + ck_kpi_block("J-codes benchmarked", f"{len(bench['jcodes'])}",
                       "marquee infusion drugs (vendored HCPCS facts)")
        + ck_kpi_block("Commercial vs Medicare",
                       f"{band['lo']*100:.0f}–{band['hi']*100:.0f}%",
                       f"published multiple band · mid {band['mid']*100:.0f}%")
        + ck_kpi_block("Biosimilar-exposed", f"{bench['eroding_count']}",
                       "molecules eroding across 2022–2026")
        + ck_kpi_block("Window", "2022–2026",
                       "five-year buy-and-bill trajectory")
        + '</div>')

    multiple_panel = ck_panel(
        '<p class="ck-section-body" style="font-size:13px;line-height:1.5;">'
        'Commercial buy-and-bill benchmarks off the Medicare ASP+6 '
        'payment limit. The published multiples bound the commercial '
        'allowed amount per code:</p>' + _multiple_table(bench),
        title="Commercial-as-%-of-Medicare multiples (published)")

    heatmap_panel = ck_panel(
        '<div style="display:flex;justify-content:space-between;'
        'align-items:flex-start;gap:12px;">'
        '<p class="ck-section-body" style="font-size:13px;line-height:1.5;'
        'margin:0;">Blended-ASP index by J-code and year (pre-competition '
        'molecule = 100). Biosimilar-exposed molecules erode after entry; '
        'sole-source biologics hold; plasma-derived IVIG drifts up on '
        'supply tightness.</p>'
        '<a class="ck-link" '
        'href="/diligence/texas-infusion/jcode-benchmark.csv" '
        'style="font-size:12px;white-space:nowrap;">Download CSV</a></div>'
        + _year_heatmap_svg(bench) + _heat_legend(),
        title="J-code × year benchmark heatmap, 2022–2026")

    reference_panel = ck_panel(
        _reference_table(bench),
        title="J-code reference — competition & biosimilar status")

    method_panel = ck_panel(
        '<div class="ck-section-body" style="font-size:13px;line-height:'
        f'1.55;"><p>{html.escape(bench["method_note"])}</p></div>',
        title="Methodology & evidence")

    body = (head + src + kpis + marketscan
            + ck_section_header("The commercial multiple",
                                eyebrow="VS MEDICARE ASP+6")
            + multiple_panel
            + ck_section_header("By J-code, by year",
                                eyebrow="BIOSIMILAR-DRIVEN ASP TRAJECTORY")
            + heatmap_panel + reference_panel
            + ck_section_header("How it is built")
            + method_panel)
    return chartis_shell(
        body, "J-code commercial benchmark · 2022–2026",
        active_nav="/diligence/texas-infusion")


def texas_jcode_benchmark_csv() -> str:
    """CSV of the J-code × year index + competition status."""
    from ..diligence.jcode_commercial_benchmark import (
        jcode_commercial_benchmark)
    bench = jcode_commercial_benchmark()
    years = bench["years"]
    out = ["hcpcs,drug,category,trend,biosimilar_entry,"
           + ",".join(f"index_{y}" for y in years) + ",change_22_26"]
    for r in bench["jcodes"]:
        vals = [r["hcpcs"], _csv(r["drug"]), _csv(r["category"]),
                r["trend"], r["biosimilar_entry"] or ""]
        vals += [r["index_by_year"][y] for y in years]
        vals.append(r["change_22_26"])
        out.append(",".join(str(x) for x in vals))
    return "\n".join(out) + "\n"


def _csv(v: str) -> str:
    s = str(v)
    if "," in s or '"' in s:
        return '"' + s.replace('"', '""') + '"'
    return s
