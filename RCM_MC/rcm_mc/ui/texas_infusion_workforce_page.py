"""Texas infusion · workforce & demand heatmaps —
``/diligence/texas-infusion/workforce``.

Two heatmaps a deal team reads when underwriting a Texas AIC +
home-infusion platform:

* **Employment by specialty** — a matrix heatmap of the clinical roster
  that staffs an infusion platform and the prescriber specialties that
  feed it, scored on AIC fit, home-infusion fit, demand pull and hiring
  scarcity, with the Texas headcount alongside.
* **County demand geography** — a true-geography heatmap on the real
  Census Texas boundary: every county with a geocoded facility plotted
  at its real centroid, coloured by infusion-patients-per-100k.

Renders straight from
:mod:`rcm_mc.diligence.texas_infusion_workforce` — nothing is typed
into this page. CSV at ``/diligence/texas-infusion/workforce.csv``.
"""
from __future__ import annotations

import html
import math
from typing import Any, Callable, List, Tuple

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

# Intensity heatmap (0-100 fit/scarcity scores) — parchment → deep teal.
_FIT_LO, _FIT_MID, _FIT_HI = "#f1ece0", "#6aa39b", "#11423d"
# Geographic demand heatmap — pale gold → orange → deep red (a true
# "heat" ramp, desaturated for print per the editorial palette).
_HEAT_LO, _HEAT_MID, _HEAT_HI = "#f6edd0", "#dd8b3a", "#8a1c10"

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


def _fmt_int(v: float) -> str:
    return f"{round(v):,}"


# ── Matrix heatmap (employment by specialty) ────────────────────────

def _matrix_heatmap_svg(matrix: List[dict], columns: List[dict]) -> str:
    """Specialty × channel-fit heatmap. Each cell is a 0-100 intensity
    coloured on the teal ramp; a trailing column renders the Texas
    headcount as a magnitude bar so the absolute size reads alongside
    the qualitative fit. Rows are grouped (clinical, then prescriber)
    with a band header drawn inline when the group changes."""
    if not matrix:
        return ""
    label_w, cell_w, bar_w = 210, 116, 150
    row_h, head_h, pad = 30, 46, 8
    n_cols = len(columns)
    width = label_w + n_cols * cell_w + bar_w + 16
    # +1 band header per group transition.
    groups = [r["group"] for r in matrix]
    n_bands = len(set(groups))
    height = (head_h + pad * 2 + len(matrix) * row_h
              + n_bands * 22)
    hc_max = max(r["headcount"] for r in matrix) or 1

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;display:block;font-family:'
        f'var(--sc-mono,monospace);" role="img" '
        f'aria-label="Employment by specialty heatmap">']

    # Column headers.
    for j, col in enumerate(columns):
        cx = label_w + j * cell_w + cell_w / 2
        parts.append(
            f'<text x="{cx:.0f}" y="{head_h-18}" text-anchor="middle" '
            f'font-size="11" font-weight="700" fill="{_NAVY}">'
            f'{html.escape(col["label"])}</text>')
    parts.append(
        f'<text x="{label_w + n_cols*cell_w + bar_w/2:.0f}" '
        f'y="{head_h-18}" text-anchor="middle" font-size="11" '
        f'font-weight="700" fill="{_NAVY}">TX headcount</text>')

    y = head_h
    last_group = None
    for r in matrix:
        if r["group"] != last_group:
            parts.append(
                f'<rect x="0" y="{y}" width="{width}" height="20" '
                f'fill="#efe9dc"/>'
                f'<text x="6" y="{y+14}" font-size="10" font-weight="700" '
                f'letter-spacing="0.06em" fill="{_DIM}">'
                f'{html.escape(r["group"].upper())}</text>')
            y += 22
            last_group = r["group"]
        # Row label.
        parts.append(
            f'<text x="{label_w-8}" y="{y+row_h/2+4:.0f}" text-anchor="end" '
            f'font-size="11.5" fill="#1a2332">'
            f'{html.escape(r["label"])}</text>')
        # Intensity cells.
        for j, col in enumerate(columns):
            v = float(r[col["key"]])
            fill = gradient_color(v, 0, 50, 100, _FIT_LO, _FIT_MID, _FIT_HI)
            tx_fill = "#ffffff" if v >= 55 else "#1a2332"
            cx = label_w + j * cell_w
            parts.append(
                f'<rect x="{cx+2}" y="{y+2}" width="{cell_w-4}" '
                f'height="{row_h-4}" rx="2" fill="{fill}">'
                f'<title>{html.escape(r["label"])} · '
                f'{html.escape(col["label"])}: {v:.0f}/100</title></rect>'
                f'<text x="{cx+cell_w/2:.0f}" y="{y+row_h/2+4:.0f}" '
                f'text-anchor="middle" font-size="11" font-weight="700" '
                f'fill="{tx_fill}">{v:.0f}</text>')
        # Headcount magnitude bar — cap the bar so the value label that
        # trails it always has room (the largest row is six digits).
        bx = label_w + n_cols * cell_w + 6
        bw = max(2.0, (bar_w - 64) * r["headcount"] / hc_max)
        parts.append(
            f'<rect x="{bx}" y="{y+row_h/2-6:.0f}" width="{bw:.1f}" '
            f'height="12" rx="2" fill="{_TEAL}" fill-opacity="0.8">'
            f'<title>{r["headcount_note"]}</title></rect>'
            f'<text x="{bx+bw+5:.1f}" y="{y+row_h/2+4:.0f}" '
            f'font-size="10" fill="{_DIM}">{_fmt_int(r["headcount"])}</text>')
        y += row_h
    parts.append("</svg>")
    return "".join(parts)


def _fit_legend() -> str:
    stops = ((0, _FIT_LO), (50, _FIT_MID), (100, _FIT_HI))
    swatches = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:5px;'
        f'margin-right:14px;"><span style="width:14px;height:14px;'
        f'border-radius:3px;background:{c};display:inline-block;'
        f'border:1px solid #d6cfc0;"></span>'
        f'<span style="font-size:11px;color:{_DIM};">{v}</span></span>'
        for v, c in stops)
    return (f'<div style="margin:8px 0 2px;font-size:11px;color:{_FAINT};">'
            f'Cell intensity (0–100): low fit&nbsp;&nbsp;{swatches}'
            f'&nbsp;high fit · bar = Texas infusion-relevant headcount</div>')


# ── Therapy demand + risk heatmap ───────────────────────────────────

# Risk ramp: low risk (1) pale green → amber → red (5). Risk is "warm
# = bad", the inverse of the channel-fit ramp.
_RISK_LO, _RISK_MID, _RISK_HI = "#e7f0e6", "#e2b15f", "#b5321e"


def _therapy_risk_heatmap_svg(mix: dict) -> str:
    """Therapy × five-axis diligence-risk heatmap. Cells are the 1–5 axis
    scores on the risk ramp; a trailing column carries the weighted
    overall percentile and risk band. Demand (estimated TX patients)
    rides as a magnitude bar on the left so the biggest pools and the
    riskiest therapies read together."""
    therapies = mix.get("therapies") or []
    axes = list(mix.get("axis_labels", {}).items())
    if not therapies or not axes:
        return ""
    label_w, bar_w, cell_w, overall_w = 196, 104, 104, 92
    row_h, head_h, pad = 32, 58, 8
    n = len(axes)
    width = label_w + bar_w + n * cell_w + overall_w + 12
    height = head_h + pad * 2 + len(therapies) * row_h
    pmax = max((t["estimated_patients"] or 0) for t in therapies) or 1

    def _trunc(s: str, m: int = 22) -> str:
        return s if len(s) <= m else s[:m - 1] + "…"

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;display:block;font-family:'
        f'var(--sc-mono,monospace);" role="img" '
        f'aria-label="Therapy diligence-risk heatmap">']

    # Column headers (wrapped to two lines on the long axis labels).
    parts.append(
        f'<text x="{label_w+bar_w/2:.0f}" y="{head_h-20}" '
        f'text-anchor="middle" font-size="10" font-weight="700" '
        f'fill="{_NAVY}">Est. TX patients</text>')
    for j, (_key, lab) in enumerate(axes):
        cx = label_w + bar_w + j * cell_w + cell_w / 2
        short = lab.split(" (")[0].split(" / ")[0]
        words = short.split()
        mid = (len(words) + 1) // 2
        l1, l2 = " ".join(words[:mid]), " ".join(words[mid:])
        parts.append(
            f'<text x="{cx:.0f}" y="{head_h-26}" text-anchor="middle" '
            f'font-size="9.5" font-weight="700" fill="{_NAVY}">'
            f'{html.escape(l1)}</text>'
            f'<text x="{cx:.0f}" y="{head_h-15}" text-anchor="middle" '
            f'font-size="9.5" font-weight="700" fill="{_NAVY}">'
            f'{html.escape(l2)}</text>')
    parts.append(
        f'<text x="{label_w+bar_w+n*cell_w+overall_w/2:.0f}" '
        f'y="{head_h-20}" text-anchor="middle" font-size="10" '
        f'font-weight="700" fill="{_NAVY}">Overall</text>')

    y = head_h
    for t in therapies:
        # Rank badge + therapy label, left-aligned in a fixed zone that
        # never reaches the demand-bar column.
        lab = _trunc(t["therapy"].split(" (")[0], 20)
        parts.append(
            f'<text x="4" y="{y+row_h/2+4:.0f}" font-size="11" '
            f'font-weight="700" fill="{_TEAL}">#{t["rank"]}</text>'
            f'<text x="22" y="{y+row_h/2+4:.0f}" font-size="11" '
            f'fill="#1a2332">{html.escape(lab)}</text>')
        # Demand bar + count, in its own column.
        pts = t["estimated_patients"] or 0
        bw = max(2.0, (bar_w - 8) * pts / pmax)
        parts.append(
            f'<rect x="{label_w+4}" y="{y+row_h/2-3:.0f}" width="{bw:.1f}" '
            f'height="9" rx="2" fill="{_TEAL}" fill-opacity="0.55">'
            f'<title>{pts:,} est. TX patients</title></rect>'
            f'<text x="{label_w+4:.0f}" y="{y+row_h/2-6:.0f}" '
            f'font-size="8.5" fill="{_DIM}">{pts:,}</text>')
        # Risk cells.
        for j, (key, lab2) in enumerate(axes):
            v = float(t["axes"][key])
            fill = gradient_color(v, 1, 3, 5, _RISK_LO, _RISK_MID, _RISK_HI)
            tx_fill = "#ffffff" if v >= 4 else "#1a2332"
            cx = label_w + bar_w + j * cell_w
            parts.append(
                f'<rect x="{cx+2}" y="{y+2}" width="{cell_w-4}" '
                f'height="{row_h-4}" rx="2" fill="{fill}">'
                f'<title>{html.escape(lab)} · {html.escape(lab2)}: '
                f'{v:.0f}/5</title></rect>'
                f'<text x="{cx+cell_w/2:.0f}" y="{y+row_h/2+4:.0f}" '
                f'text-anchor="middle" font-size="11" font-weight="700" '
                f'fill="{tx_fill}">{v:.0f}</text>')
        # Overall band.
        band_color = {"HIGH": _RISK_HI, "ELEVATED": "#b8732a"}.get(
            t["band"], _TEAL)
        ox = label_w + bar_w + n * cell_w
        parts.append(
            f'<text x="{ox+overall_w/2:.0f}" y="{y+row_h/2:.0f}" '
            f'text-anchor="middle" font-size="13" font-weight="700" '
            f'fill="{band_color}">{t["overall_pct"]}%</text>'
            f'<text x="{ox+overall_w/2:.0f}" y="{y+row_h/2+11:.0f}" '
            f'text-anchor="middle" font-size="8" letter-spacing="0.05em" '
            f'fill="{_DIM}">{html.escape(t["band"])}</text>')
        y += row_h
    parts.append("</svg>")
    return "".join(parts)


def _risk_legend() -> str:
    stops = ((1, _RISK_LO, "low"), (3, _RISK_MID, "med"),
             (5, _RISK_HI, "high"))
    sw = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:5px;'
        f'margin-right:14px;"><span style="width:14px;height:14px;'
        f'border-radius:3px;background:{c};display:inline-block;'
        f'border:1px solid #d6cfc0;"></span>'
        f'<span style="font-size:11px;color:{_DIM};">{v} {t}</span></span>'
        for v, c, t in stops)
    return (f'<div style="margin:8px 0 2px;font-size:11px;color:{_FAINT};">'
            f'Axis score (1–5, higher = more risk): {sw}'
            f'· bar = estimated Texas patients · overall = weighted '
            f'percentile</div>')


def _therapy_table(mix: dict) -> str:
    rows = "".join(
        f'<tr><td {_TD}><strong>{html.escape(t["therapy"])}</strong>'
        f'<div style="font-size:11px;color:{_DIM};">'
        f'{html.escape(t["conditions"])}</div></td>'
        f'<td {_TDN}>{t["epi_per_100k"]:.0f}</td>'
        f'<td {_TDN}>{(t["estimated_patients"] or 0):,}</td>'
        f'<td {_TD} style="font-size:11.5px;">{html.escape(t["regimen"])}</td>'
        f'<td {_TD} style="font-size:11px;">{html.escape(t["lead_risk"])}</td>'
        f'</tr>' for t in mix["therapies"])
    return (
        '<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr><th {_TH}>Infusion therapy</th>'
        f'<th {_THN}>Per 100k</th><th {_THN}>Est. TX patients</th>'
        f'<th {_TH}>Regimen</th><th {_TH}>Lead risk</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>')


# ── Geographic county-demand heatmap ────────────────────────────────

def _projector(boundary: List[Tuple[float, float]], width: float,
               pad: float) -> Tuple[Callable[[float, float],
                                              Tuple[float, float]], float]:
    """Equirectangular projection with a cos(lat) aspect correction so
    the Texas outline is not stretched horizontally. Returns the
    projector and the computed height for the given width."""
    lons = [p[0] for p in boundary]
    lats = [p[1] for p in boundary]
    lon0, lon1 = min(lons), max(lons)
    lat0, lat1 = min(lats), max(lats)
    coslat = math.cos(math.radians((lat0 + lat1) / 2)) or 1.0
    geo_w = (lon1 - lon0) * coslat or 1.0
    geo_h = (lat1 - lat0) or 1.0
    plot_w = width - 2 * pad
    scale = plot_w / geo_w
    height = geo_h * scale + 2 * pad

    def proj(lon: float, lat: float) -> Tuple[float, float]:
        x = pad + (lon - lon0) * coslat * scale
        y = pad + (lat1 - lat) * scale
        return x, y

    return proj, height


def _geo_heatmap_svg(geo: dict) -> str:
    """County infusion-demand heatmap on the real Texas boundary. Dots
    sit at real facility-derived centroids, coloured by patients-per-100k
    and sized by absolute demand."""
    boundary = geo.get("boundary") or []
    placed = geo.get("placed") or []
    if not boundary or not placed:
        return ""
    width, pad = 460.0, 12.0
    proj, height = _projector(boundary, width, pad)

    path = "M" + " L".join(f"{x:.1f},{y:.1f}"
                           for x, y in (proj(lon, lat)
                                        for lon, lat in boundary)) + " Z"
    dom = geo["intensity_domain"]
    lo, mid, hi = dom["lo"], dom["mid"], dom["hi"]
    pmax = max(r["infusion_patients"] for r in placed) or 1

    dots = []
    # Largest demand first so small dots paint on top (visible).
    for r in placed:
        x, y = proj(r["lon"], r["lat"])
        rad = 2.2 + 7.0 * (r["infusion_patients"] / pmax) ** 0.5
        fill = gradient_color(r["patients_per_100k"], lo, mid, hi,
                              _HEAT_LO, _HEAT_MID, _HEAT_HI)
        dots.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" fill="{fill}" '
            f'fill-opacity="0.82" stroke="#5a3210" stroke-width="0.4">'
            f'<title>{html.escape(r["county"])} County — '
            f'{r["patients_per_100k"]:,.0f}/100k · '
            f'{r["infusion_patients"]:,} patients</title></circle>')

    svg = (
        f'<svg viewBox="0 0 {width:.0f} {height:.0f}" width="100%" '
        f'style="max-width:{width:.0f}px;display:block;background:#fdfcf9;'
        f'border:1px solid #d6cfc0;border-radius:6px;" role="img" '
        f'aria-label="Texas county infusion-demand heatmap">'
        f'<path d="{path}" fill="#f3eee3" stroke="#c9c1ac" '
        f'stroke-width="1"/>{"".join(dots)}</svg>')
    return svg


def _geo_legend(geo: dict) -> str:
    dom = geo["intensity_domain"]
    grad = (f"linear-gradient(90deg,{_HEAT_LO},{_HEAT_MID},{_HEAT_HI})")
    return (
        '<div style="display:flex;flex-wrap:wrap;gap:24px;align-items:center;'
        'margin:8px 0 2px;">'
        '<div style="font-size:11px;color:#465366;">'
        '<div style="margin-bottom:3px;">Infusion patients per 100k '
        '(colour)</div>'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="font-family:var(--sc-mono);">{dom["lo"]:,.0f}</span>'
        f'<span style="width:140px;height:12px;border-radius:3px;'
        f'background:{grad};border:1px solid #d6cfc0;display:inline-block;">'
        f'</span>'
        f'<span style="font-family:var(--sc-mono);">{dom["hi"]:,.0f}</span>'
        '</div></div>'
        '<div style="font-size:11px;color:#465366;">'
        '<div style="margin-bottom:3px;">Dot size = absolute infusion '
        'demand</div>'
        '<svg width="150" height="26" role="img" aria-hidden="true">'
        '<circle cx="14" cy="13" r="3" fill="#dd8b3a" fill-opacity="0.82"/>'
        '<circle cx="48" cy="13" r="6" fill="#dd8b3a" fill-opacity="0.82"/>'
        '<circle cx="92" cy="13" r="9" fill="#dd8b3a" fill-opacity="0.82"/>'
        '<text x="118" y="17" font-size="10" fill="#465366">more</text>'
        '</svg></div></div>')


# ── Tables ──────────────────────────────────────────────────────────

def _clinical_table(emp: dict) -> str:
    rows = "".join(
        f'<tr><td {_TD}><strong>{html.escape(c["role"])}</strong>'
        f'<div style="font-size:11px;color:{_DIM};">'
        f'{html.escape(c["note"])}</div></td>'
        f'<td {_TD} style="font-family:var(--sc-mono);font-size:11px;">'
        f'{html.escape(c["soc"])}</td>'
        f'<td {_TDN}>{c["tx_employment"]:,}</td>'
        f'<td {_TDN}>{c["infusion_relevant"]*100:.1f}%</td>'
        f'<td {_TDN}>{c["infusion_relevant_headcount"]:,}</td></tr>'
        for c in emp["clinical"])
    return (
        '<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr><th {_TH}>Clinical role</th><th {_TH}>SOC</th>'
        f'<th {_THN}>TX employment</th><th {_THN}>Infusion %</th>'
        f'<th {_THN}>Infusion headcount</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>')


def _prescriber_table(emp: dict) -> str:
    rows = "".join(
        f'<tr><td {_TD}><strong>{html.escape(p["specialty"])}</strong></td>'
        f'<td {_TDN}>{p["tx_physicians"]:,}</td>'
        f'<td {_TD}>{html.escape(p["therapies"])}</td>'
        f'<td {_TD} style="font-size:11.5px;">{html.escape(p["channel"])}</td>'
        f'</tr>' for p in emp["prescribers"])
    return (
        '<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr><th {_TH}>Prescriber specialty</th>'
        f'<th {_THN}>TX physicians (est.)</th><th {_TH}>Infusion therapies</th>'
        f'<th {_TH}>Channel</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>')


def _metro_employment_table() -> str:
    from ..diligence.texas_infusion_workforce import (
        specialty_employment_by_metro, texas_specialty_employment)
    metros = [m["metro"] for m in texas_specialty_employment()["metros"]]
    rows = specialty_employment_by_metro()
    head = "".join(f'<th {_THN}>{html.escape(m)}</th>' for m in metros)
    body = "".join(
        '<tr><td ' + _TD + f'><strong>{html.escape(r["role"])}</strong></td>'
        + "".join(f'<td {_TDN}>{r[m]:,}</td>' for m in metros)
        + f'<td {_TDN}><strong>{r["tx"]:,}</strong></td></tr>'
        for r in rows)
    return (
        '<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr><th {_TH}>Infusion-relevant role</th>{head}'
        f'<th {_THN}>TX total</th></tr></thead>'
        f'<tbody>{body}</tbody></table>')


def _whitespace_table(geo: dict) -> str:
    rows = "".join(
        f'<tr><td {_TDN}>{i}</td>'
        f'<td {_TD}><strong>{html.escape(r["county"])}</strong></td>'
        f'<td {_TD}>{html.escape(r["metro_class"])}</td>'
        f'<td {_TDN}>{r["population"]:,}</td>'
        f'<td {_TDN}>{r["infusion_patients"]:,}</td>'
        f'<td {_TDN}>{r["patients_per_100k"]:,.0f}</td>'
        f'<td {_TDN}>{r["expected_distance_mi"]:.1f}</td></tr>'
        for i, r in enumerate(geo["unplaced"][:15], start=1))
    return (
        '<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr><th {_THN}>#</th><th {_TH}>County (no in-county site)</th>'
        f'<th {_TH}>Class</th><th {_THN}>Population</th>'
        f'<th {_THN}>Patients</th><th {_THN}>Per 100k</th>'
        f'<th {_THN}>Distance (mi)</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>')


# ── Page ────────────────────────────────────────────────────────────

def render_texas_infusion_workforce_page(
        qs: dict[str, Any] | None = None) -> str:
    from ..diligence.texas_infusion_workforce import (
        county_demand_centroids, texas_specialty_employment,
        texas_therapy_mix)
    emp = texas_specialty_employment()
    geo = county_demand_centroids()
    mix = texas_therapy_mix()
    t = emp["totals"]
    cov = geo["coverage"]

    head = ck_page_title(
        "Texas infusion · workforce & demand heatmaps",
        eyebrow="DILIGENCE · WORKFORCE + GEOGRAPHY",
        meta=(f"{t['infusion_relevant_clinical']:,} INFUSION CLINICAL · "
              f"{t['prescriber_physicians']:,} PRESCRIBERS · "
              f"{cov['counties_placed']} COUNTIES MAPPED"),
    )
    src = ck_source_purpose(
        purpose=("Who staffs and who feeds a Texas AIC + home-infusion "
                 "platform, and where the county-level demand actually "
                 "sits — the labour-supply and referral-funnel read for "
                 "site selection and hiring."),
        universe="cms",
        source=emp["sources"],
        confidence="modeled",
        next_action="Open the county proximity workbench",
        next_href="/diligence/texas-infusion/counties",
    )

    kpis = (
        '<div class="ck-kpi-row" style="display:grid;grid-template-'
        'columns:repeat(4,1fr);gap:12px;margin:16px 0;">'
        + ck_kpi_block(
            "Infusion clinical workforce",
            f"{t['infusion_relevant_clinical']:,}",
            "addressable TX headcount across 7 roles")
        + ck_kpi_block(
            "Prescriber physicians",
            f"{t['prescriber_physicians']:,}",
            "across 6 infusion-driving specialties")
        + ck_kpi_block(
            "Counties on the heatmap",
            f"{cov['counties_placed']} / {cov['counties_total']}",
            f"{cov['demand_share_placed']*100:.1f}% of demand, real "
            "centroids")
        + ck_kpi_block(
            "Unmapped rural counties",
            f"{cov['counties_unplaced']}",
            "no in-county geocoded site — whitespace below")
        + '</div>')

    matrix_panel = ck_panel(
        '<div style="display:flex;justify-content:space-between;'
        'align-items:flex-start;gap:12px;">'
        '<p class="ck-section-body" style="font-size:13px;line-height:1.5;'
        'margin:0;">'
        'Each cell scores a specialty 0–100 on its fit to the AIC and '
        'home-infusion channels, the infusion demand it pulls, and how '
        'hard the role is to hire in Texas. The bar is the Texas '
        'infusion-relevant headcount (clinical: BLS OES × infusion share; '
        'prescribers: national density × Texas population).</p>'
        '<a class="ck-link" href="/diligence/texas-infusion/workforce.csv" '
        'style="font-size:12px;white-space:nowrap;">Download CSV</a></div>'
        + _matrix_heatmap_svg(emp["matrix"], emp["matrix_columns"])
        + _fit_legend(),
        title="Employment by specialty — channel-fit heatmap")

    clinical_panel = ck_panel(
        _clinical_table(emp), title="Clinical staffing roster (BLS OES TX)")
    prescriber_panel = ck_panel(
        _prescriber_table(emp),
        title="Prescriber specialties — the referral funnel")
    metro_panel = ck_panel(
        '<p class="ck-section-body" style="font-size:12.5px;color:#465366;">'
        'Infusion-relevant clinical headcount apportioned to the four '
        'major metros by population share — the honest public sub-state '
        'split (there is no provider-level geocode of the infusion '
        'workforce).</p>' + _metro_employment_table(),
        title="Workforce by metro (population apportionment)")

    therapy_panel = ck_panel(
        '<p class="ck-section-body" style="font-size:13px;line-height:1.5;">'
        'What the prescriber funnel actually infuses, and how risky each '
        'therapy class is to underwrite. Estimated Texas patients = real '
        'population × published treated-prevalence; the five-axis risk '
        f'score (1–5) is the documented diligence framework. Most at risk: '
        f'<strong>{html.escape(mix["most_at_risk"])}</strong>.</p>'
        + _therapy_risk_heatmap_svg(mix) + _risk_legend(),
        title="Therapy demand & diligence-risk heatmap")
    therapy_table_panel = ck_panel(
        _therapy_table(mix),
        title="Therapy reference — demand, regimen & lead risk")

    geo_panel = ck_panel(
        '<p class="ck-section-body" style="font-size:13px;line-height:1.5;">'
        'Every Texas county with a geocoded CMS facility is plotted at '
        'its real facility-derived centroid on the Census state boundary, '
        f'coloured by infusion patients per 100k. {cov["counties_placed"]} '
        f'of {cov["counties_total"]} counties carry '
        f'{cov["demand_share_placed"]*100:.1f}% of statewide demand; the '
        f'{cov["counties_unplaced"]} facility-less rural counties cannot '
        'be positioned without invented coordinates and are listed as '
        'whitespace below.</p>'
        '<div style="display:grid;grid-template-columns:minmax(0,1fr);'
        'gap:10px;">' + _geo_heatmap_svg(geo) + _geo_legend(geo) + '</div>',
        title="County infusion-demand heatmap (true geography)")

    whitespace_panel = ck_panel(
        '<p class="ck-section-body" style="font-size:12.5px;color:#465366;">'
        'Counties with real demand but no in-county geocoded site — the '
        'referral catchments an adjacent-county AIC serves. Ranked by '
        'infusion patients.</p>' + _whitespace_table(geo),
        title="Unmapped demand — rural whitespace (top 15)")

    methodology = ck_panel(
        '<div class="ck-section-body" style="font-size:13px;line-height:'
        '1.55;">'
        '<p><strong>Clinical headcount (REAL anchor).</strong> Texas '
        'statewide employment by SOC code from BLS OES May 2023. The '
        'infusion-relevant share is a MODELED overlay — the fraction of '
        'each occupation realistically addressable to AIC / home-infusion '
        'staffing — and is labelled illustrative.</p>'
        '<p><strong>Prescriber counts (MODELED).</strong> National '
        'active-physician density per 100k (AAMC/ACGME) scaled to the '
        'Texas population. Channel and therapy mappings describe the '
        'infusion demand each specialty drives.</p>'
        '<p><strong>Channel-fit scores (MODELED).</strong> The 0–100 AIC '
        'fit, home-infusion fit, demand pull and hiring scarcity are '
        'analyst intensities for prioritisation, not measured rates.</p>'
        '<p><strong>Geographic heatmap (REAL coordinates).</strong> '
        'County centroids are the mean latitude/longitude of that '
        "county's geocoded CMS facilities (real points). Demand intensity "
        '(patients per 100k) and absolute demand recompute from the '
        'county universe on the proximity workbench. Counties without an '
        'in-county facility are not placed — no coordinates are invented.'
        '</p></div>',
        title="Methodology & evidence classes")

    body = (head + src + kpis
            + ck_section_header("Employment by specialty",
                                eyebrow="WHO STAFFS · WHO FEEDS THE PLATFORM")
            + matrix_panel + clinical_panel + prescriber_panel + metro_panel
            + ck_section_header("What they infuse — therapy mix & risk",
                                eyebrow="DEMAND × DILIGENCE RISK")
            + therapy_panel + therapy_table_panel
            + ck_section_header("Where the demand sits",
                                eyebrow="COUNTY HEATMAP · TRUE GEOGRAPHY")
            + geo_panel + whitespace_panel
            + ck_section_header("How it is built")
            + methodology)
    return chartis_shell(
        body, "Texas infusion · workforce & demand heatmaps",
        active_nav="/diligence/texas-infusion")


def texas_workforce_csv() -> str:
    """CSV of the specialty matrix + the placed county centroids."""
    from ..diligence.texas_infusion_workforce import (
        county_demand_centroids, texas_specialty_employment,
        texas_therapy_mix)
    emp = texas_specialty_employment()
    geo = county_demand_centroids()
    mix = texas_therapy_mix()
    out = ["section,label,a,b,c,d,e"]
    out.append("specialty_columns,label,aic_fit,home_fit,demand_pull,"
               "scarcity,headcount")
    for r in emp["matrix"]:
        out.append(",".join(str(x) for x in [
            "specialty", _csv(r["label"]), r["aic_fit"], r["home_fit"],
            r["demand_pull"], r["scarcity"], r["headcount"]]))
    out.append("therapy_columns,therapy,reimbursement,steerage,"
               "referral_concentration,clinical,supply,overall_pct,"
               "est_tx_patients")
    for r in mix["therapies"]:
        ax = r["axes"]
        out.append(",".join(str(x) for x in [
            "therapy", _csv(r["therapy"]), ax["reimbursement"],
            ax["steerage"], ax["referral_concentration"], ax["clinical"],
            ax["supply"], r["overall_pct"], r["estimated_patients"]]))
    out.append("county_columns,county,lat,lon,infusion_patients,"
               "patients_per_100k,population")
    for r in geo["placed"]:
        out.append(",".join(str(x) for x in [
            "county", _csv(r["county"]), r["lat"], r["lon"],
            r["infusion_patients"], r["patients_per_100k"],
            r["population"]]))
    return "\n".join(out) + "\n"


def _csv(v: str) -> str:
    s = str(v)
    if "," in s or '"' in s:
        return '"' + s.replace('"', '""') + '"'
    return s
