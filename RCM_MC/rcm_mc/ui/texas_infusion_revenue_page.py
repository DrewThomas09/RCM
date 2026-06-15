"""Texas infusion · revenue build & competitor benchmark —
``/diligence/texas-infusion/revenue``.

The data-room reconciliation: revenue rebuilt bottom-up from CPT
administration units × the Medicare rate, the therapy-by-therapy unit
derivation, the buy-and-bill bridge to platform gross, and the Texas
competitor benchmark (operator shares + HHI + channel map). Renders
straight from :mod:`rcm_mc.diligence.texas_infusion_revenue` — nothing
is typed in. CSV at ``/diligence/texas-infusion/revenue.csv``.
"""
from __future__ import annotations

import html
from typing import Any, Callable, List

from ._chartis_kit import (
    chartis_shell,
    ck_kpi_block,
    ck_page_title,
    ck_panel,
    ck_section_header,
    ck_source_purpose,
)

_NAVY = "#0b2341"
_TEAL = "#155752"
_DIM = "#465366"
_FAINT = "#7a8699"
_POS = "#0a8a5f"
_WARN = "#b8732a"

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


def _money(v: float) -> str:
    if abs(v) >= 1e9:
        return f"${v/1e9:.2f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:.1f}M"
    if abs(v) >= 1e3:
        return f"${v/1e3:.0f}K"
    return f"${v:,.0f}"


def _hbar_svg(rows: List[dict], label_key: str, value_key: str,
              value_fmt: Callable[[float], str], tone: str,
              sub_key: str = "") -> str:
    """Ranked horizontal-bar SVG with a zero-baseline and a max gridline —
    the shared chart idiom on the Texas pages."""
    rows = [r for r in rows if (r.get(value_key) or 0) > 0]
    if not rows:
        return ""
    mx = max(float(r[value_key]) for r in rows) or 1.0
    label_w, bar_w, width = 200, 300, 660
    row_h, gap, pad = 24, 7, 8
    height = pad * 2 + len(rows) * (row_h + gap) - gap
    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;display:block;" role="img">'
        f'<line x1="{label_w}" y1="{pad-2}" x2="{label_w}" '
        f'y2="{height-pad+2}" stroke="#d6cfc0" stroke-width="1"/>'
        f'<line x1="{label_w+bar_w}" y1="{pad-2}" x2="{label_w+bar_w}" '
        f'y2="{height-pad+2}" stroke="#e4ddca" stroke-width="0.8" '
        f'stroke-dasharray="2 2"/>']
    for i, r in enumerate(rows):
        y = pad + i * (row_h + gap)
        ty = y + row_h / 2 + 4
        v = float(r[value_key])
        w = max(2.0, bar_w * v / mx)
        lab = html.escape(str(r.get(label_key, "")))
        sub = (f'<tspan fill="{_FAINT}" font-weight="400"> · '
               f'{html.escape(str(r.get(sub_key, "")))}</tspan>'
               if sub_key and r.get(sub_key) else "")
        parts.append(
            f'<text x="{label_w-6}" y="{ty:.0f}" text-anchor="end" '
            f'font-size="11" fill="#1a2332">{lab}</text>'
            f'<rect x="{label_w}" y="{y}" width="{w:.1f}" height="{row_h}" '
            f'rx="2" fill="{tone}" fill-opacity="0.85"/>'
            f'<text x="{label_w+w+6:.1f}" y="{ty:.0f}" font-size="10.5" '
            f'font-weight="600" fill="{_DIM}">{value_fmt(v)}{sub}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _bridge_svg(admin: float, drug: float) -> str:
    """A single stacked bar: administration revenue + implied drug
    buy-and-bill = platform gross."""
    total = admin + drug or 1.0
    width, h = 620, 56
    aw = width * admin / total
    return (
        f'<svg viewBox="0 0 {width} {h}" width="100%" '
        f'style="max-width:{width}px;display:block;" role="img" '
        f'aria-label="Revenue bridge">'
        f'<rect x="0" y="10" width="{aw:.1f}" height="26" rx="2" '
        f'fill="{_TEAL}"><title>Administration (CPT): {_money(admin)}'
        f'</title></rect>'
        f'<rect x="{aw:.1f}" y="10" width="{width-aw:.1f}" height="26" '
        f'rx="2" fill="{_NAVY}"><title>Drug buy-and-bill (implied): '
        f'{_money(drug)}</title></rect>'
        f'<text x="6" y="27" font-size="11" font-weight="700" '
        f'fill="#fff">Admin {_money(admin)}</text>'
        f'<text x="{aw+8:.1f}" y="27" font-size="11" font-weight="700" '
        f'fill="#fff">Drug buy-and-bill (implied) {_money(drug)}</text>'
        f'<text x="0" y="52" font-size="10" fill="{_FAINT}">CPT '
        f'administration is ~15% of gross; the drug is the balance '
        f'(Part B ASP+6, sequestered to ~ASP+4.3%).</text></svg>')


def _code_table(rev: dict) -> str:
    rows = "".join(
        f'<tr><td {_TD}><strong style="font-family:var(--sc-mono);">'
        f'{html.escape(c["code"])}</strong></td>'
        f'<td {_TD}>{html.escape(c["family"])}'
        f'<div style="font-size:11px;color:{_DIM};">'
        f'{html.escape(c["descriptor"])}</div></td>'
        f'<td {_TDN}>${c["rate_nonfac"]:.2f}</td>'
        f'<td {_TDN}>{c["units"]:,}</td>'
        f'<td {_TDN}>{_money(c["revenue"])}</td></tr>'
        for c in rev["codes"])
    return (
        '<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr><th {_TH}>CPT</th><th {_TH}>Family / descriptor</th>'
        f'<th {_THN}>Rate (non-fac)</th><th {_THN}>Modeled TX units</th>'
        f'<th {_THN}>Admin revenue</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>')


def _therapy_build_table(rev: dict) -> str:
    rows = "".join(
        f'<tr><td {_TD}><strong>{html.escape(t["therapy"])}</strong>'
        f'<div style="font-size:11px;color:{_DIM};">'
        f'{html.escape(t["basis"])}</div></td>'
        f'<td {_TDN}>{t["patients"]:,}</td>'
        f'<td {_TDN}>{t["annual_infusions"] or "—"}</td>'
        f'<td {_TDN}>{t["annual_visits"]:,}</td>'
        f'<td {_TD} style="font-family:var(--sc-mono);font-size:11px;">'
        f'{html.escape(t["stack"])}</td></tr>'
        for t in rev["therapies"])
    return (
        '<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr><th {_TH}>Therapy → CPT stack</th>'
        f'<th {_THN}>Est. TX patients</th><th {_THN}>Infusions/yr</th>'
        f'<th {_THN}>Annual visits</th><th {_TH}>CPT codes billed</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>')


def _competitor_table(bench: dict) -> str:
    rows = "".join(
        f'<tr><td {_TD}><strong>{html.escape(p["name"])}</strong></td>'
        f'<td {_TD}>{html.escape(p["channel"])}</td>'
        f'<td {_TD}>{html.escape(p["ownership"])}</td>'
        f'<td {_TD} style="font-size:11.5px;">{html.escape(p["scale"])}</td>'
        f'</tr>' for p in bench["players"])
    return (
        '<table style="width:100%;border-collapse:collapse;">'
        f'<thead><tr><th {_TH}>Operator</th><th {_TH}>Channel</th>'
        f'<th {_TH}>Ownership</th><th {_TH}>Scale / Texas footprint</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>')


def render_texas_infusion_revenue_page(qs: dict[str, Any] | None = None) -> str:
    from ..diligence.texas_infusion_revenue import (
        cpt_units_and_revenue, texas_competitor_benchmark)
    rev = cpt_units_and_revenue()
    bench = texas_competitor_benchmark()
    tot = rev["totals"]

    head = ck_page_title(
        "Texas infusion · revenue build & competitor benchmark",
        eyebrow="DILIGENCE · CODE-LEVEL REVENUE",
        meta=(f"{tot['admin_units']:,} CPT UNITS · "
              f"{_money(tot['admin_revenue'])} ADMIN · "
              f"{_money(tot['gross_revenue_implied'])} IMPLIED GROSS · "
              f"HHI {bench['hhi']:.0f}"),
    )
    src = ck_source_purpose(
        purpose=("Reconstruct the Texas infusion revenue line bottom-up "
                 "from CPT administration units × the Medicare rate, then "
                 "benchmark the platform against the Texas competitive "
                 "set — the data-room reconciliation a deal team runs."),
        universe="cms",
        source=rev["rate_source"],
        confidence="modeled",
        next_action="Open the CPT rates-by-site page",
        next_href="/diligence/texas-infusion-continued",
    )

    kpis = (
        '<div class="ck-kpi-row" style="display:grid;grid-template-'
        'columns:repeat(4,1fr);gap:12px;margin:16px 0;">'
        + ck_kpi_block("Modeled CPT units", f"{tot['admin_units']:,}",
                       "annual TX infusion-administration units")
        + ck_kpi_block("Administration revenue",
                       _money(tot['admin_revenue']),
                       "CPT units × CY2025 non-facility rate")
        + ck_kpi_block("Implied platform gross",
                       _money(tot['gross_revenue_implied']),
                       "admin grossed up at 15% of gross (drug is balance)")
        + ck_kpi_block("Operator HHI", f"{bench['hhi']:.0f}",
                       f"{html.escape(bench['hhi_band'])} · top "
                       f"{(bench['top_operator_share'] or 0)*100:.0f}%")
        + '</div>')

    code_panel = ck_panel(
        '<div style="display:flex;justify-content:space-between;'
        'align-items:flex-start;gap:12px;">'
        '<p class="ck-section-body" style="font-size:13px;line-height:1.5;'
        'margin:0;">Annual Texas administration revenue by CPT code — '
        'modeled units priced at the real CY2025 national non-facility '
        'PFS amount. Therapeutic infusion (96365) and complex-biologic '
        '(96413) carry the line.</p>'
        '<a class="ck-link" href="/diligence/texas-infusion/revenue.csv" '
        'style="font-size:12px;white-space:nowrap;">Download CSV</a></div>'
        + _hbar_svg(rev["codes"], "code", "revenue", _money, _TEAL,
                    sub_key="family")
        + _code_table(rev),
        title="CPT units & revenue by code")

    build_panel = ck_panel(
        '<p class="ck-section-body" style="font-size:13px;line-height:1.5;">'
        + html.escape(rev["method_note"]) + '</p>'
        + _therapy_build_table(rev),
        title="How the units are built — therapy → CPT")

    bridge_panel = ck_panel(
        '<p class="ck-section-body" style="font-size:13px;line-height:1.5;">'
        'Administration is the minority of an infusion platform\'s gross; '
        'the buy-and-bill drug is the rest. The implied split, off the '
        'modeled CPT revenue:</p>'
        + _bridge_svg(tot["admin_revenue"], tot["drug_revenue_implied"]),
        title="Buy-and-bill revenue bridge")

    share_rows = [{"org": c["org"], "share_pct": c["share"] * 100,
                   "note": c["note"]} for c in bench["chains"]]
    bench_panel = ck_panel(
        '<p class="ck-section-body" style="font-size:13px;line-height:1.5;">'
        + html.escape(bench["note"]) + '</p>'
        + _hbar_svg(share_rows, "org", "share_pct",
                    lambda v: f"{v:.0f}%", _NAVY)
        + '<div style="margin-top:10px;">' + _competitor_table(bench)
        + '</div>',
        title="Texas competitor benchmark — operator shares & landscape")

    body = (head + src + kpis
            + ck_section_header("Revenue by code",
                                eyebrow="CPT UNITS × MEDICARE RATE")
            + code_panel + build_panel + bridge_panel
            + ck_section_header("Who you are up against",
                                eyebrow="TEXAS COMPETITIVE SET")
            + bench_panel)
    return chartis_shell(
        body, "Texas infusion · revenue build & competitor benchmark",
        active_nav="/diligence/texas-infusion")


def texas_revenue_csv() -> str:
    """CSV of the code-level revenue build + the competitor shares."""
    from ..diligence.texas_infusion_revenue import (
        cpt_units_and_revenue, texas_competitor_benchmark)
    rev = cpt_units_and_revenue()
    bench = texas_competitor_benchmark()
    out = ["section,a,b,c,d,e"]
    out.append("code,cpt,family,rate_nonfac,units,revenue")
    for c in rev["codes"]:
        out.append(",".join(str(x) for x in [
            "code", c["code"], _csv(c["family"]), c["rate_nonfac"],
            c["units"], c["revenue"]]))
    out.append("operator,name,share_pct,named,note,")
    for c in bench["chains"]:
        out.append(",".join(str(x) for x in [
            "operator", _csv(c["org"]), round(c["share"] * 100, 1),
            c.get("named"), _csv(c["note"]), ""]))
    return "\n".join(out) + "\n"


def _csv(v: str) -> str:
    s = str(v)
    if "," in s or '"' in s:
        return '"' + s.replace('"', '""') + '"'
    return s
