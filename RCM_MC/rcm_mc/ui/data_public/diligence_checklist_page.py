"""Diligence Checklist Generator page — /diligence-checklist."""
from __future__ import annotations

from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_kpi_block


_SECTORS = [
    "Physician Group", "Behavioral Health", "Dental", "Dermatology",
    "Urgent Care", "Ambulatory Surgery", "Home Health", "Hospice",
    "Radiology", "Laboratory", "Orthopedics", "Cardiology",
    "Gastroenterology", "Ophthalmology", "Physical Therapy",
    "Skilled Nursing", "Health IT", "Revenue Cycle Management",
    "Staffing", "Pediatric",
]

_CATEGORY_ORDER = [
    "Financial Quality", "Operations", "Regulatory", "Market", "Leverage", "Management"
]


def _category_bar_svg(by_category: dict) -> str:
    cats = [c for c in _CATEGORY_ORDER if c in by_category]
    W = 600
    bar_h = 18
    row_h = 28
    pad_l, pad_r, pad_t = 140, 60, 16
    total_h = pad_t + len(cats) * row_h + 20

    max_count = max(len(items) for items in by_category.values()) if by_category else 1
    chart_w = W - pad_l - pad_r

    lines = [
        f'<svg viewBox="0 0 {W} {total_h}" width="100%" xmlns="http://www.w3.org/2000/svg" '
        f'style="font-family:\'JetBrains Mono\',monospace;font-size:10px;'
        f'background:{P["panel"]};border:1px solid {P["border"]}">',
    ]

    for i, cat in enumerate(cats):
        items = by_category.get(cat, [])
        y = pad_t + i * row_h
        critical_n = sum(1 for x in items if x.priority == "Critical")
        high_n = sum(1 for x in items if x.priority == "High")
        other_n = len(items) - critical_n - high_n

        x_off = pad_l
        for n, color in [(critical_n, "#ef4444"), (high_n, "#ea580c"), (other_n, "#f59e0b")]:
            if n > 0:
                bw = (n / max_count) * chart_w * 0.6
                lines.append(f'<rect x="{x_off:.1f}" y="{y}" width="{bw:.1f}" height="{bar_h}" '
                              f'fill="{color}" opacity="0.8"/>')
                lines.append(f'<text x="{x_off + bw/2:.1f}" y="{y + bar_h - 4}" '
                              f'text-anchor="middle" fill="{P["bg"]}" font-size="9">{n}</text>')
                x_off += bw

        lines.append(f'<text x="{pad_l - 6}" y="{y + bar_h - 4}" text-anchor="end" '
                     f'fill="{P["text_dim"]}">{cat}</text>')
        lines.append(f'<text x="{x_off + 4:.1f}" y="{y + bar_h - 4}" '
                     f'fill="{P["text_dim"]}">{len(items)} items</text>')

    lines.append('</svg>')
    return "\n".join(lines)


def _checklist_section(category: str, items: list) -> str:
    bg = P["bg"]
    bg2 = P["panel"]
    border = P["border"]
    tdim = P["text_dim"]
    tprim = P["text"]

    rows = []
    for i, item in enumerate(items):
        rbg = bg2 if i % 2 else bg
        prio_c = item.priority_color
        rf_badge = (f'<span style="color:{P["negative"]};font-size:9px;'
                    f'border:1px solid {P["negative"]};padding:1px 4px;margin-left:6px">RED FLAG</span>'
                    if item.is_red_flag else "")
        fail_pct = f"{item.corpus_fail_rate * 100:.0f}%"
        rows.append(
            f'<tr style="background:{rbg}">'
            f'<td style="padding:5px 8px;width:90px">'
            f'<span style="color:{prio_c};font-family:\'JetBrains Mono\',monospace;font-size:10px">{item.priority}</span></td>'
            f'<td style="padding:5px 8px;color:{tprim}">{item.title}{rf_badge}</td>'
            f'<td style="padding:5px 8px;color:{tdim};font-size:10px;max-width:300px">{item.description}</td>'
            f'<td style="padding:5px 8px;text-align:right;font-variant-numeric:tabular-nums;color:{tdim};font-size:10px">{fail_pct}</td>'
            f'<td style="padding:5px 8px;width:80px">'
            f'<span style="color:{tdim};font-family:\'JetBrains Mono\',monospace;font-size:10px">Open</span></td>'
            f'</tr>'
        )

    hdr_r = f'style="padding:5px 8px;text-align:right;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'
    hdr_l = f'style="padding:5px 8px;text-align:left;color:{tdim};font-size:10px;border-bottom:1px solid {border};background:{bg}"'

    return (
        f'<div style="margin-top:10px;background:{bg2};border:1px solid {border}">'
        f'<div style="padding:6px 10px;background:{P["panel_alt"]};border-bottom:1px solid {border};'
        f'font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tprim};text-transform:uppercase;letter-spacing:0.08em">'
        f'{category} ({len(items)})</div>'
        f'<table style="width:100%;border-collapse:collapse;font-family:\'JetBrains Mono\',monospace;font-size:11px">'
        f'<thead><tr>'
        f'<th {hdr_l}>Priority</th>'
        f'<th {hdr_l}>Item</th>'
        f'<th {hdr_l}>Description</th>'
        f'<th {hdr_r}>Corpus Fail%</th>'
        f'<th {hdr_l}>Status</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
        f'</div>'
    )


def _input_form(params: dict) -> str:
    sector = params.get("sector", "Physician Group")
    ev = params.get("ev", "200.0")
    comm = params.get("comm", "0.55")
    ar = params.get("ar", "45.0")

    options = "".join(
        f'<option value="{s}" {"selected" if s == sector else ""}>{s}</option>'
        for s in _SECTORS
    )
    inp = (
        f'background:{P["panel_alt"]};color:{P["text"]};'
        f'border:1px solid {P["border"]};padding:6px 8px;'
        f'font-family:\'JetBrains Mono\',monospace;font-size:12px;'
        f'border-radius:2px;width:100%;box-sizing:border-box'
    )
    lbl = (
        f'display:block;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:10px;color:{P["text_dim"]};'
        f'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:4px'
    )
    btn = (
        f'background:{P["accent"]};color:{P["text"]};'
        f'border:none;padding:8px 20px;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:12px;cursor:pointer;border-radius:2px'
    )

    return f'''<form method="get" action="/diligence-checklist" style="
    background:{P["panel"]};border:1px solid {P["border"]};
    padding:14px 16px;display:grid;grid-template-columns:2fr 1fr 1fr 1fr auto;
    gap:12px;align-items:end">
  <div><label style="{lbl}">Sector</label>
    <select name="sector" style="{inp}">{options}</select></div>
  <div><label style="{lbl}">EV ($M)</label>
    <input name="ev" type="number" step="10" value="{ev}" style="{inp}"></div>
  <div><label style="{lbl}">Commercial %</label>
    <input name="comm" type="number" step="0.01" value="{comm}" style="{inp}"></div>
  <div><label style="{lbl}">AR Days (DSO)</label>
    <input name="ar" type="number" step="1" value="{ar}" style="{inp}"></div>
  <div><button type="submit" style="{btn}">Generate</button></div>
</form>'''


def render_diligence_checklist(params: dict) -> str:
    sector = params.get("sector", "Physician Group")
    try:
        ev_mm = float(params.get("ev", "200.0"))
    except (ValueError, TypeError):
        ev_mm = 200.0
    try:
        comm_pct = float(params.get("comm", "0.55"))
    except (ValueError, TypeError):
        comm_pct = 0.55
    try:
        ar_days = float(params.get("ar", "45.0"))
    except (ValueError, TypeError):
        ar_days = 45.0

    from rcm_mc.data_public.diligence_checklist import compute_diligence_checklist
    r = compute_diligence_checklist(sector, ev_mm, comm_pct=comm_pct, ar_days=ar_days)

    kpis = ck_kpi_block("Total Items", str(r.total_items))
    kpis += ck_kpi_block("Critical", str(r.critical_items),
                         unit="Require immediate attention")
    kpis += ck_kpi_block("High", str(r.high_items))
    kpis += ck_kpi_block("Red Flags",
                         f'<span style="color:{P["negative"]}">{r.red_flags_triggered}</span>',
                         unit="Triggered by deal profile")
    medium = r.total_items - r.critical_items - r.high_items
    kpis += ck_kpi_block("Medium / Low", str(medium))
    kpis += ck_kpi_block("Corpus Deals", str(r.corpus_deal_count))

    cat_chart = _category_bar_svg(r.by_category)

    sections = ""
    for cat in _CATEGORY_ORDER:
        if cat in r.by_category:
            sections += _checklist_section(cat, r.by_category[cat])

    bg_sec = P["panel"]
    border = P["border"]
    tdim = P["text_dim"]

    content = f'''
{_input_form(params)}

<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-top:12px">
{kpis}
</div>

<div style="margin-top:12px;background:{bg_sec};border:1px solid {border};padding:12px">
  <div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;color:{tdim};
    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">
    Items by Category
  </div>
  {cat_chart}
</div>

<div style="margin-top:12px">
  {sections}
</div>
'''

    return chartis_shell(
        body=content,
        title=f"Diligence Checklist — {sector}",
        active_nav="/diligence-checklist",
    )
