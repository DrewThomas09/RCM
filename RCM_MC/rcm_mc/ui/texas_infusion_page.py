"""Texas infusion market — a full CDD diligence page.

Renders :func:`rcm_mc.diligence.texas_infusion.build_texas_infusion_analysis`
as the editorial diligence surface a deal team reads when sizing a
Texas infusion platform: TAM/SAM/SOM funnel, therapy-form + site-of-
care segmentation, chain-concentration HHI, payer mix, the Medicare
65+ tailwind, and the Texas structural factors. Every figure carries
its source; the page declares the model illustrative where it scales
public data.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_page_title, ck_section_header,
    ck_source_purpose,
)

_POS = "#0a8a5f"
_NEG = "#b5321e"
_WARN = "#b8732a"
_NAVY = "#0b2341"
_TEAL = "#1F7A75"
_DIM = "#465366"
_FAINT = "#7a8699"


def _money(v: float) -> str:
    if abs(v) >= 1e9:
        return f"${v/1e9:.2f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:.1f}M"
    return f"${v:,.0f}"


def _bar(pct: float, tone: str, width: int = 100) -> str:
    w = max(1.0, min(100.0, pct))
    return (
        f'<span style="display:inline-block;width:{width}px;height:9px;'
        f'background:#ece5d6;border-radius:2px;overflow:hidden;'
        f'vertical-align:middle;">'
        f'<span style="display:block;height:100%;width:{w:.0f}%;'
        f'background:{tone};"></span></span>')


def _kpi_strip(a: Dict[str, Any]) -> str:
    s = a["sizing"]
    demo = a["demographics"]
    return (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("TX infusion TAM", _money(s["tam"]),
                       sub="annual market, all sites")
        + ck_kpi_block("Addressable (SAM)", _money(s["sam"]),
                       sub=f'{s["sam_share"]*100:.0f}% of TAM · '
                           'platform-serviceable')
        + ck_kpi_block("Obtainable (SOM)", _money(s["som"]),
                       sub=f'{s["som_share"]*100:.0f}% of SAM · entry share')
        + ck_kpi_block("5-yr market CAGR",
                       f'{s["composite_cagr_pct"]:.1f}%',
                       sub="composite of named drivers")
        + ck_kpi_block("Chain HHI", f'{a["hhi"]:,.0f}',
                       sub=html.escape(a["hhi_band"]))
        + ck_kpi_block("Texans 65+",
                       f'{demo["seniors_65_plus"]/1e6:.2f}M',
                       sub=f'{demo["pct_age_65_plus"]*100:.1f}% of '
                           f'{demo["population"]/1e6:.1f}M — Medicare base')
        + '</div>'
    )


def _sizing_chain(a: Dict[str, Any]) -> str:
    rows = ""
    for st in a["sizing"]["steps"]:
        op = st["op"]
        val = st["value"]
        if op == "rate":
            val_s = f'×{val*100:.1f}%'
        elif op == "price":
            val_s = f'×${val:,.0f}'
        elif op == "mult":
            val_s = f'×{val:,.0f}'
        else:
            val_s = f'{val:,.0f}'
        run = st["running"]
        run_s = _money(run) if op == "price" else f'{run:,.0f}'
        rows += (
            f'<tr>'
            f'<td style="padding:6px 8px;">{html.escape(st["name"])}'
            f'<div style="font-size:10px;color:{_FAINT};">'
            f'{html.escape(st["source"])}</div></td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'font-variant-numeric:tabular-nums;color:{_DIM};">{val_s}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'font-variant-numeric:tabular-nums;font-weight:600;">'
            f'{run_s}'
            f'<span style="font-size:10px;color:{_FAINT};"> '
            f'{html.escape(st["unit"])}</span></td>'
            f'</tr>')
    return (
        '<div style="overflow-x:auto;"><table style="width:100%;'
        'border-collapse:collapse;font-size:12.5px;">'
        '<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        '<th style="text-align:left;padding:6px 8px;">Driver (source)</th>'
        '<th style="text-align:right;padding:6px 8px;">Step</th>'
        '<th style="text-align:right;padding:6px 8px;">Running</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
        f'<p style="font-size:11px;color:{_FAINT};margin:8px 0 0;">'
        'The chain is the methodology — TX patient base × infusion '
        'frequency × revenue per infusion. Every step is editable in '
        'the TAM/SAM builder.</p>')


def _segment_table(a: Dict[str, Any]) -> str:
    """Therapy-form segmentation with growth divergence (fastest ★)."""
    rows = ""
    for seg in a["sizing"]["segments"]:
        star = (' <span style="color:%s;font-weight:700;">★ fastest</span>'
                % _POS) if seg.get("is_fastest") else ""
        g = seg.get("growth_pct")
        g_s = (f'<span style="color:{_POS if g and g>=6 else _DIM};">'
               f'+{g:.0f}%</span>' if g is not None else "—")
        y5 = seg.get("tam_y_final")
        rows += (
            f'<tr>'
            f'<td style="padding:6px 8px;">{html.escape(seg["name"])}{star}'
            + (f'<div style="font-size:10px;color:{_FAINT};">'
               f'{html.escape(seg["note"])}</div>' if seg.get("note") else "")
            + f'</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">'
            f'{seg["share_of_volume"]*100:.0f}%</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'font-weight:600;">{_money(seg["tam_value"])}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">{g_s}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'color:{_DIM};">{_money(y5) if y5 else "—"}</td>'
            f'</tr>')
    return (
        '<div style="overflow-x:auto;"><table style="width:100%;'
        'border-collapse:collapse;font-size:12.5px;">'
        '<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        '<th style="text-align:left;padding:6px 8px;">Therapy form</th>'
        '<th style="text-align:right;padding:6px 8px;">Share</th>'
        '<th style="text-align:right;padding:6px 8px;">TAM today</th>'
        '<th style="text-align:right;padding:6px 8px;">Growth</th>'
        '<th style="text-align:right;padding:6px 8px;">TAM Y5</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>')


def _site_table(a: Dict[str, Any]) -> str:
    """Site-of-care segmentation — the HOPD → home/AIS migration in $."""
    rows = ""
    for s in a["site_of_care"]:
        g = s["growth_pct"]
        tone = _POS if g > 0 else _NEG
        g_s = f'<span style="color:{tone};font-weight:600;">{g:+.0f}%</span>'
        rows += (
            f'<tr>'
            f'<td style="padding:6px 8px;">{html.escape(s["site"])}'
            f'<div style="font-size:10px;color:{_FAINT};">'
            f'{html.escape(s["note"])}</div></td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">'
            f'{s["share"]*100:.0f}%</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">'
            f'{_money(s["tam_today"])}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">{g_s}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'font-weight:600;color:{tone};">{_money(s["tam_y5"])}</td>'
            f'</tr>')
    return (
        '<div style="overflow-x:auto;"><table style="width:100%;'
        'border-collapse:collapse;font-size:12.5px;">'
        '<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        '<th style="text-align:left;padding:6px 8px;">Site of care</th>'
        '<th style="text-align:right;padding:6px 8px;">Share</th>'
        '<th style="text-align:right;padding:6px 8px;">TAM today</th>'
        '<th style="text-align:right;padding:6px 8px;">Growth</th>'
        '<th style="text-align:right;padding:6px 8px;">TAM Y5</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
        f'<p style="font-size:11px;color:{_FAINT};margin:8px 0 0;">'
        'The site-of-care shift is the thesis: HOPD volume (2–3× the '
        'suite rate) is being steered to home + ambulatory suites. HOPD '
        'is the only declining site.</p>')


def _metro_table(a: Dict[str, Any]) -> str:
    """Ranked metro breakdown — real CBSA ACS data + derived demand."""
    rows = ""
    for m in a["metros"]:
        att = m["attractiveness"]
        att_tone = _POS if att >= 90 else _TEAL if att >= 80 else _WARN
        rows += (
            f'<tr>'
            f'<td class="num" style="padding:6px 8px;font-weight:700;'
            f'color:{att_tone};">#{m["rank"]}</td>'
            f'<td style="padding:6px 8px;font-weight:600;">'
            f'{html.escape(m["metro"])}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">'
            f'{m["population"]/1e6:.2f}M</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">'
            f'{m["seniors"]/1e3:,.0f}K</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">'
            f'{m["infusion_patients"]:,}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">'
            f'{m["referral_density_per_100k"]:,.0f}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">'
            f'~{m["est_ais_centers"]}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'font-weight:700;color:{att_tone};">{att:.0f}</td>'
            f'</tr>')
    return (
        '<div style="overflow-x:auto;"><table style="width:100%;'
        'border-collapse:collapse;font-size:12px;">'
        '<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        '<th style="text-align:left;padding:6px 8px;">Rank</th>'
        '<th style="text-align:left;padding:6px 8px;">Metro</th>'
        '<th style="text-align:right;padding:6px 8px;">Population</th>'
        '<th style="text-align:right;padding:6px 8px;">65+</th>'
        '<th style="text-align:right;padding:6px 8px;">Infusion pts</th>'
        '<th style="text-align:right;padding:6px 8px;">Per 100k</th>'
        '<th style="text-align:right;padding:6px 8px;">AIS (est)</th>'
        '<th style="text-align:right;padding:6px 8px;">Attract.</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
        f'<p style="font-size:11px;color:{_FAINT};margin:8px 0 0;'
        f'line-height:1.55;">Population, 65+ share and rurality are REAL '
        'CBSA aggregates of member-county ACS data. Infusion patients '
        'apportion the TX base by metro senior + total population; '
        'referral density = patients per 100k residents; AIS counts are '
        'population-scaled estimates. Attractiveness (0–100) blends '
        'senior demand (log-scaled), 65+ growth, and a rural-route '
        'penalty — the four metros hold ~70% of Texans.</p>')


def _provider_panel(a: Dict[str, Any]) -> str:
    pl = a["provider_landscape"]
    hs = a["health_system_capacity"]
    frag = a["fragmentation"]
    return (
        '<div class="ck-kpi-grid" style="margin-bottom:10px;">'
        + ck_kpi_block("Home-infusion locations (est)",
                       f'~{pl["home_infusion_locations"]}',
                       sub="NHIA national × TX share")
        + ck_kpi_block("Ambulatory infusion centers (est)",
                       f'~{pl["ambulatory_infusion_centers"]}',
                       sub=f'growing ~{pl["ais_growth_pct"]:.0f}%/yr')
        + ck_kpi_block("Health-system (HOPD) capacity",
                       f'{hs["hopd_share"]*100:.0f}%',
                       sub="captive — outside the pool")
        + '</div>'
        + f'<p style="font-size:11px;color:{_FAINT};margin:0 0 12px;'
        f'line-height:1.55;">{html.escape(pl["note"])}</p>'
        + f'<div style="padding:10px 14px;background:#f7f3ea;'
        f'border-left:3px solid {_POS};border-radius:0 3px 3px 0;'
        f'font-size:12.5px;color:#1a2332;line-height:1.6;margin-bottom:10px;">'
        f'<strong>Competitive read:</strong> {html.escape(frag["verdict"])}'
        f'</div>'
        + f'<p style="font-size:12px;color:{_DIM};line-height:1.6;">'
        f'<strong>Health-system-owned capacity:</strong> '
        f'{html.escape(hs["note"])}</p>')


def _concentration(a: Dict[str, Any]) -> str:
    """Chain table + HHI read — the fragmentation that drives roll-up."""
    rows = ""
    for c in a["chains"]:
        tone = _NAVY if c["named"] else _FAINT
        rows += (
            f'<tr>'
            f'<td style="padding:5px 8px;color:{tone};'
            f'{"font-weight:600;" if c["named"] else ""}">'
            f'{html.escape(c["org"])}'
            f'<div style="font-size:10px;color:{_FAINT};">'
            f'{html.escape(c["note"])}</div></td>'
            f'<td class="num" style="padding:5px 8px;text-align:right;">'
            f'{c["share"]*100:.0f}%</td>'
            f'<td style="padding:5px 8px;">{_bar(c["share"]*100, tone, 120)}</td>'
            f'</tr>')
    band_tone = (_NEG if a["hhi"] > 2500 else _WARN if a["hhi"] >= 1500
                 else _POS)
    return (
        '<div style="overflow-x:auto;"><table style="width:100%;'
        'border-collapse:collapse;font-size:12.5px;">'
        '<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        '<th style="text-align:left;padding:5px 8px;">Operator</th>'
        '<th style="text-align:right;padding:5px 8px;">Share</th>'
        '<th style="padding:5px 8px;"></th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
        f'<p style="font-size:12px;color:{_DIM};margin:10px 0 0;'
        f'line-height:1.6;">Named-chain <strong>HHI = '
        f'<span style="color:{band_tone};">{a["hhi"]:,.0f}</span></strong> '
        f'({html.escape(a["hhi_band"])}, DOJ/FTC 0–10,000 scale). A reading '
        'this low says the operator layer is <strong>fragmented</strong> — '
        'no single platform dominates and the regional/independent pool is '
        'the roll-up whitespace. This is the buy-and-build setup.</p>'
        f'<p style="font-size:9.5px;color:{_FAINT};margin:6px 0 0;">'
        'Shares are national operator estimates mapped to Texas '
        '(no TX-specific infusion provider census is vendored) — '
        'illustrative for the concentration read; HHI computed over the '
        'named chains only.</p>')


def _payer_section(a: Dict[str, Any]) -> str:
    rows = ""
    for p in a["payer_mix"]:
        rows += (
            f'<tr>'
            f'<td style="padding:6px 8px;font-weight:500;">'
            f'{html.escape(p["payer"])}'
            f'<div style="font-size:10px;color:{_FAINT};">'
            f'{html.escape(p["note"])}</div></td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;">'
            f'{p["share"]*100:.0f}%</td>'
            f'<td style="padding:6px 8px;">{_bar(p["share"]*100, _TEAL, 120)}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'color:{_DIM};">{_money(p["tam_value"])}</td>'
            f'</tr>')
    return (
        '<div style="overflow-x:auto;"><table style="width:100%;'
        'border-collapse:collapse;font-size:12.5px;">'
        '<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        '<th style="text-align:left;padding:6px 8px;">Payer</th>'
        '<th style="text-align:right;padding:6px 8px;">Share</th>'
        '<th style="padding:6px 8px;"></th>'
        '<th style="text-align:right;padding:6px 8px;">TAM $</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>')


def _factors(a: Dict[str, Any]) -> str:
    out = ""
    for f in a["structural_factors"]:
        tone = _POS if f["tone"] == "positive" else _NEG
        sign = "▲" if f["tone"] == "positive" else "▼"
        out += (
            f'<div style="padding:9px 0;border-bottom:1px solid #e4ddca;">'
            f'<div style="font-size:12.5px;font-weight:600;color:#1a2332;">'
            f'<span style="color:{tone};">{sign}</span> '
            f'{html.escape(f["factor"])}</div>'
            f'<div style="font-size:11.5px;color:{_DIM};margin-top:2px;'
            f'line-height:1.55;">{html.escape(f["detail"])}</div></div>')
    return out


def _growth_drivers(a: Dict[str, Any]) -> str:
    out = ""
    for g in a["sizing"]["growth_drivers"]:
        tone = _POS if g["annual_pct"] > 0 else _NEG
        out += (
            f'<div style="padding:7px 0;border-bottom:1px solid #e4ddca;'
            f'display:flex;gap:10px;align-items:baseline;">'
            f'<span style="font-family:monospace;font-weight:700;color:{tone};'
            f'min-width:52px;">{g["annual_pct"]:+.1f}%</span>'
            f'<span><strong style="font-size:12px;">'
            f'{html.escape(g["name"])}</strong>'
            f'<div style="font-size:11px;color:{_DIM};">'
            f'{html.escape(g["note"])}</div></span></div>')
    return out


_SEV_TONE = {"HIGH": _NEG, "MEDIUM": _WARN, "LOW": _FAINT}
_CHANNEL_TONE = {"AIC": _NAVY, "Home": _TEAL, "Both": "#6e5b9e"}


def _aic_waterfall_svg(sections: List[Dict[str, Any]]) -> str:
    """Per-chair P&L as a section waterfall — gross revenue drawn down
    by each cost to the contribution margin. The 'breakdown by sections'
    graphic."""
    # Build running cumulative for the waterfall.
    width, row_h, gap, pad_l, pad_top = 620, 26, 9, 220, 8
    revenue = next((s["value"] for s in sections
                    if s["kind"] == "revenue"), 1.0) or 1.0
    height = pad_top * 2 + len(sections) * (row_h + gap)
    scale = (width - pad_l - 90) / revenue
    parts = [f'<svg viewBox="0 0 {width} {height}" width="100%" '
             f'style="max-width:{width}px;display:block;" role="img">']
    running = 0.0
    for i, s in enumerate(sections):
        y = pad_top + i * (row_h + gap)
        ty = y + row_h / 2 + 4
        v = s["value"]
        kind = s["kind"]
        if kind == "revenue":
            x0, w, tone, running = pad_l, v * scale, _POS, v
        elif kind == "subtotal":
            x0, w, tone, running = pad_l, v * scale, _NAVY, v
        else:  # cost — draws from current running down by |v|
            running_new = running + v       # v is negative
            x0 = pad_l + running_new * scale
            w = (-v) * scale
            tone = _NEG
            running = running_new
        parts.append(
            f'<text x="{pad_l-8}" y="{ty:.0f}" text-anchor="end" '
            f'font-size="11" fill="#1a2332">{html.escape(s["label"])}</text>'
            f'<rect x="{x0:.1f}" y="{y}" width="{max(w,2):.1f}" '
            f'height="{row_h}" rx="2" fill="{tone}" fill-opacity="0.85"/>'
            f'<text x="{pad_l + abs(revenue)*scale + 6:.0f}" y="{ty:.0f}" '
            f'font-size="10.5" font-weight="600" fill="{tone}">'
            f'${abs(v)/1e3:,.0f}K</text>')
    parts.append("</svg>")
    return "".join(parts)


def _aic_economics_section(a: Dict[str, Any]) -> str:
    e = a["aic_economics"]
    kpi_cards = "".join(
        f'<div style="border:1px solid #d6cfc0;border-radius:4px;'
        f'padding:8px 10px;background:#fff;">'
        f'<div style="font-size:9px;letter-spacing:0.06em;color:{_FAINT};'
        f'font-weight:700;">{html.escape(k["kpi"]).upper()}</div>'
        f'<div style="font-size:16px;font-weight:700;color:{_NAVY};'
        f'font-variant-numeric:tabular-nums;">{html.escape(k["value"])}</div>'
        f'<div style="font-size:10px;color:{_DIM};line-height:1.4;">'
        f'{html.escape(k["lever"])}</div>'
        + (f'<div style="font-size:9px;color:{_POS};">good: '
           f'{html.escape(k["good"])}</div>' if k.get("good") and
           k["good"] != "—" else "")
        + '</div>'
        for k in e["kpis"])
    sect_notes = "".join(
        f'<li style="font-size:11px;color:{_DIM};margin:2px 0;">'
        f'<strong>{html.escape(s["label"])}</strong> '
        f'(${abs(s["value"])/1e3:,.0f}K) — {html.escape(s["note"])}</li>'
        for s in e["sections"])
    return (
        f'<p style="font-size:12px;color:{_DIM};line-height:1.6;'
        f'margin:0 0 10px;">A healthy AIC runs on <strong>high chair '
        f'utilization, high nurse productivity, recurring (chronic) '
        f'patients, a commercial-heavy payer mix, disciplined prior-auth, '
        f'and tight drug acquisition</strong>. Per-chair P&amp;L at the '
        f'benchmark assumptions — every input editable:</p>'
        f'<div style="display:grid;grid-template-columns:1.1fr 1fr;'
        f'gap:18px;align-items:start;">'
        f'<div><div style="font-size:10px;color:{_FAINT};letter-spacing:'
        f'0.06em;font-weight:700;margin-bottom:4px;">PER-CHAIR P&amp;L — '
        f'BREAKDOWN BY SECTION (annual)</div>'
        f'{_aic_waterfall_svg(e["sections"])}'
        f'<ul style="margin:6px 0 0;padding-left:16px;">{sect_notes}</ul>'
        f'</div>'
        f'<div><div style="font-size:10px;color:{_FAINT};letter-spacing:'
        f'0.06em;font-weight:700;margin-bottom:4px;">OPERATING KPIs — '
        f'THE LEVERS</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">'
        f'{kpi_cards}</div></div></div>'
        f'<p style="font-size:9.5px;color:{_FAINT};margin:10px 0 0;">'
        f'{html.escape(e["basis_note"])}</p>')


def _drug_supply_section(a: Dict[str, Any]) -> str:
    ds = a["drug_supply"]
    def _tone(status: str) -> str:
        if "CURRENT" in status:
            return _NEG
        if "WATCH" in status:
            return _WARN
        return _POS
    rows = ""
    for c in ds["classes"]:
        t = _tone(c["status"])
        ex = ", ".join(c["examples"][:3]) if c["examples"] else "—"
        rows += (
            f'<tr>'
            f'<td style="padding:6px 8px;font-weight:600;">'
            f'{html.escape(c["klass"])}'
            f'<div style="font-size:10px;color:{_FAINT};">'
            f'{html.escape(c["channel"])}</div></td>'
            f'<td style="padding:6px 8px;"><span style="font-size:10px;'
            f'font-weight:700;color:{t};border:1px solid {t};'
            f'border-radius:2px;padding:1px 6px;">'
            f'{html.escape(c["status"])}</span></td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'color:{_DIM};">{c["current_shortages"]} cur / '
            f'{c["total_listed"]} listed</td>'
            f'<td style="padding:6px 8px;font-size:10.5px;color:{_FAINT};">'
            f'{html.escape(ex)}</td>'
            f'</tr>')
    return (
        f'<div style="padding:10px 14px;background:#eef3ee;'
        f'border-left:3px solid {_POS};border-radius:0 3px 3px 0;'
        f'font-size:12.5px;color:#1a2332;line-height:1.6;margin-bottom:10px;">'
        f'<strong>Supply read:</strong> {html.escape(ds["headline"])}</div>'
        f'<div style="overflow-x:auto;"><table style="width:100%;'
        f'border-collapse:collapse;font-size:12px;">'
        f'<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        f'<th style="text-align:left;padding:6px 8px;">Drug class</th>'
        f'<th style="text-align:left;padding:6px 8px;">FDA status</th>'
        f'<th style="text-align:right;padding:6px 8px;">Shortages</th>'
        f'<th style="text-align:left;padding:6px 8px;">Examples</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
        f'<p style="font-size:9.5px;color:{_FAINT};margin:8px 0 0;">'
        f'Live from the {html.escape(str(ds["snapshot_date"]))} '
        f'{html.escape(ds["source"])} ({ds["total_current"]:,} current US '
        f'shortages). Full list: '
        f'<a href="/drug-shortage" style="color:{_NAVY};font-weight:600;'
        f'text-decoration:none;">Drug Shortage tracker →</a></p>')


def _aic_assumptions_form(a: Dict[str, Any]) -> str:
    """The change-your-assumptions form. GET → the same page; every
    field range-clamped server-side; blank = model default."""
    asm = a["aic_economics"]["assumptions"]
    fields = [
        ("aic_chairs", "Chairs", asm["chairs"], "1–60"),
        ("aic_util", "Utilization %", round(asm["util_pct"] * 100),
         "30–95"),
        ("aic_per_day", "Infusions / chair / day",
         asm["infusions_per_chair_day"], "2–12"),
        ("aic_drug_rev", "Drug revenue / infusion $",
         round(asm["revenue_per_infusion_drug"]), "100–5,000"),
        ("aic_commercial", "Commercial mix %",
         round(asm["commercial_mix_pct"] * 100), "0–100"),
        ("aic_nurse_ratio", "Nurse : chair ratio",
         asm["nurse_to_chair"], "0.10–1.0"),
        ("aic_nurse_cost", "Nurse cost (loaded) $",
         round(asm["nurse_fully_loaded"]), "60K–250K"),
        ("aic_overhead", "Overhead / chair $",
         round(asm["facility_overhead_per_chair"]), "5K–120K"),
        ("aic_rcm", "RCM cost %", round(asm["rcm_cost_pct"] * 100),
         "1–15"),
    ]
    inputs = "".join(
        f'<label style="font-size:10px;color:{_FAINT};display:block;">'
        f'{html.escape(label)} <span style="color:#c9c1ac;">({rng})</span>'
        f'<input name="{key}" value="{val}" inputmode="decimal" '
        f'style="width:100%;padding:4px 7px;border:1px solid #c9c1ac;'
        f'border-radius:3px;font-variant-numeric:tabular-nums;'
        f'font-size:12px;"></label>'
        for key, label, val, rng in fields)
    edited = (
        f'<span style="font-size:9px;font-weight:700;color:{_WARN};'
        f'border:1px solid {_WARN};border-radius:2px;padding:1px 6px;'
        f'margin-left:8px;">EDITED — your assumptions</span>'
        if a.get("aic_overrides_active") else
        f'<span style="font-size:9px;color:{_FAINT};margin-left:8px;">'
        f'benchmark defaults — edit and recompute</span>')
    return (
        f'<form method="get" action="/diligence/texas-infusion#aic" '
        f'style="border:1px solid #d6cfc0;border-radius:4px;'
        f'padding:10px 14px;background:#fff;margin-bottom:12px;">'
        f'<div style="font-size:10px;font-weight:700;letter-spacing:'
        f'0.06em;color:{_NAVY};margin-bottom:6px;">CHANGE THE '
        f'ASSUMPTIONS{edited}</div>'
        f'<div style="display:grid;grid-template-columns:repeat('
        f'auto-fill,minmax(150px,1fr));gap:8px;align-items:end;">'
        f'{inputs}'
        f'<button type="submit" style="padding:6px 12px;cursor:pointer;'
        f'background:{_NAVY};color:#fff;border:none;border-radius:3px;'
        f'font-size:12px;font-weight:600;">Recompute ↻</button>'
        f'<a href="/diligence/texas-infusion#aic" style="font-size:11px;'
        f'color:{_FAINT};text-decoration:none;align-self:center;">reset</a>'
        f'</div>'
        f'<p style="font-size:9.5px;color:{_FAINT};margin:7px 0 0;">'
        f'Inputs are range-clamped server-side; blank = benchmark '
        f'default. With no explicit admin-fee/drug-margin override, both '
        f'blend from the commercial mix (commercial '
        f'${"%.0f" % 260}/{14:.0f}% vs Medicare ${"%.0f" % 155}/'
        f'{4.3:.1f}% — MedPAC ASP+4.3 sequestered), so the mix slider '
        f'moves the P&amp;L.</p>'
        f'</form>')


def _aic_tornado_svg(rows: List[Dict[str, Any]]) -> str:
    """Contribution tornado — which lever moves the chair P&L."""
    if not rows:
        return ""
    base = rows[0]["base"]
    mx = max(max(abs(r["contribution_low"] - base),
                 abs(r["contribution_high"] - base)) for r in rows) or 1.0
    label_w, half_w = 190, 160
    cx = label_w + half_w
    row_h, gap, pad = 20, 7, 8
    width = label_w + 2 * half_w + 80
    height = pad * 2 + len(rows) * (row_h + gap) - gap + 16
    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;display:block;" role="img">'
        f'<line x1="{cx}" y1="{pad}" x2="{cx}" y2="{height-22}" '
        f'stroke="#c9c1ac" stroke-width="1"/>'
        f'<text x="{cx}" y="{height-8}" text-anchor="middle" '
        f'font-size="9" fill="{_FAINT}">base ${base/1e3:,.0f}K</text>']
    for i, r in enumerate(rows):
        y = pad + i * (row_h + gap)
        ty = y + row_h / 2 + 3.5
        lo_d = r["contribution_low"] - base
        hi_d = r["contribution_high"] - base
        for d, tone in ((lo_d, _NEG if lo_d < 0 else _POS),
                        (hi_d, _POS if hi_d > 0 else _NEG)):
            w = abs(d) / mx * half_w
            x = cx - w if d < 0 else cx
            parts.append(
                f'<rect x="{x:.1f}" y="{y}" width="{max(w,1):.1f}" '
                f'height="{row_h}" rx="2" fill="{tone}" '
                f'fill-opacity="0.75"/>')
        parts.append(
            f'<text x="{label_w-6}" y="{ty:.0f}" text-anchor="end" '
            f'font-size="10.5" fill="#1a2332">'
            f'{html.escape(r["lever"])}</text>'
            f'<text x="{cx+half_w+6}" y="{ty:.0f}" font-size="10" '
            f'font-weight="600" fill="{_DIM}">±${r["impact"]/2e3:,.0f}K'
            f'</text>')
    parts.append("</svg>")
    return "".join(parts)


def _util_curve_svg(curve: Dict[str, Any]) -> str:
    """Contribution vs chair utilization with the break-even marker —
    the de-novo ramp picture."""
    pts = curve["points"]
    if not pts:
        return ""
    width, h, pad_l, pad_b, pad_t = 560, 200, 64, 30, 14
    plot_w, plot_h = width - pad_l - 16, h - pad_t - pad_b
    us = [p["util_pct"] for p in pts]
    cs = [p["contribution"] for p in pts]
    lo_c, hi_c = min(min(cs), 0), max(cs)
    span = (hi_c - lo_c) or 1.0
    def _x(u): return pad_l + (u - us[0]) / (us[-1] - us[0]) * plot_w
    def _y(c): return pad_t + (1 - (c - lo_c) / span) * plot_h
    path = " ".join(
        f'{"M" if i == 0 else "L"} {_x(p["util_pct"]):.1f} '
        f'{_y(p["contribution"]):.1f}' for i, p in enumerate(pts))
    zero_y = _y(0)
    parts = [
        f'<svg viewBox="0 0 {width} {h}" width="100%" '
        f'style="max-width:{width}px;display:block;" role="img">'
        f'<line x1="{pad_l}" y1="{zero_y:.1f}" x2="{width-16}" '
        f'y2="{zero_y:.1f}" stroke="#c9c1ac" stroke-width="1" '
        f'stroke-dasharray="3,3"/>'
        f'<text x="{pad_l-4}" y="{zero_y+3:.1f}" text-anchor="end" '
        f'font-size="9" fill="{_FAINT}">$0</text>'
        f'<path d="{path}" fill="none" stroke="{_NAVY}" '
        f'stroke-width="2"/>']
    be = curve.get("breakeven_util")
    if be is not None and us[0] <= be <= us[-1]:
        parts.append(
            f'<line x1="{_x(be):.1f}" y1="{pad_t}" x2="{_x(be):.1f}" '
            f'y2="{h-pad_b}" stroke="{_WARN}" stroke-width="1.5" '
            f'stroke-dasharray="4,3"/>'
            f'<text x="{_x(be):.1f}" y="{pad_t-3}" text-anchor="middle" '
            f'font-size="9" font-weight="700" fill="{_WARN}">'
            f'break-even {be*100:.0f}%</text>')
    elif be is not None:
        parts.append(
            f'<text x="{pad_l}" y="{pad_t-3}" font-size="9" '
            f'font-weight="700" fill="{_WARN}">break-even '
            f'{be*100:.0f}% (left of chart)</text>')
    cu = curve["current_util"]
    parts.append(
        f'<circle cx="{_x(cu):.1f}" '
        f'cy="{_y(curve["current_contribution"]):.1f}" r="5" '
        f'fill="{_POS}"/>'
        f'<text x="{_x(cu)+8:.1f}" '
        f'y="{_y(curve["current_contribution"])-6:.1f}" font-size="9.5" '
        f'font-weight="700" fill="{_POS}">you: {cu*100:.0f}% · '
        f'${curve["current_contribution"]/1e3:,.0f}K</text>')
    for u in (0.40, 0.60, 0.80, 0.95):
        parts.append(
            f'<text x="{_x(u):.1f}" y="{h-10}" text-anchor="middle" '
            f'font-size="9" fill="{_FAINT}">{u*100:.0f}%</text>')
    parts.append("</svg>")
    return "".join(parts)


_SEG_TONE = ["#0b2341", "#b5321e", "#6e5b9e", "#1F7A75", "#b8732a"]


def _provider_segments_section(a: Dict[str, Any]) -> str:
    """Competitive dynamics — infusion capacity by OWNERSHIP segment:
    national/regional chains, health-system-owned, physician-owned,
    independent AIC, independent home. A 100% ownership strip + a
    table with examples and the roll-up read."""
    segs = a["provider_segments"]
    # 100% ownership strip.
    strip, x = [], 0.0
    for i, s in enumerate(segs):
        w = s["share"] * 100
        tone = _SEG_TONE[i % len(_SEG_TONE)]
        strip.append(
            f'<div style="width:{w:.0f}%;background:{tone};height:26px;'
            f'display:inline-flex;align-items:center;justify-content:center;'
            f'color:#fff;font-size:9.5px;font-weight:600;" '
            f'title="{html.escape(s["segment"])} {w:.0f}%">'
            f'{w:.0f}%</div>')
    rows = ""
    for i, s in enumerate(segs):
        tone = _SEG_TONE[i % len(_SEG_TONE)]
        tag = ('<span style="color:%s;font-weight:700;">non-hospital</span>'
               % _POS if s["non_hospital"] else
               '<span style="color:%s;font-weight:700;">health-system '
               'captive</span>' % _FAINT)
        rows += (
            f'<tr>'
            f'<td style="padding:6px 8px;"><span style="display:inline-block;'
            f'width:9px;height:9px;border-radius:2px;background:{tone};'
            f'margin-right:6px;"></span><strong>{html.escape(s["segment"])}'
            f'</strong></td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'font-weight:600;">{s["share"]*100:.0f}%</td>'
            f'<td style="padding:6px 8px;">{tag}</td>'
            f'<td style="padding:6px 8px;font-size:11px;color:{_DIM};">'
            f'{html.escape(s["examples"])}</td>'
            f'<td style="padding:6px 8px;font-size:11px;color:{_FAINT};">'
            f'{html.escape(s["note"])}</td>'
            f'</tr>')
    return (
        f'<p style="font-size:12px;color:{_DIM};line-height:1.6;'
        f'margin:0 0 8px;">National infusion capacity by owner — the '
        f'segments a roll-up competes with, buys, or steers around. '
        f'Health-system-owned is captive (the steered-away HOPD pool); '
        f'the other ~67% is the non-hospital landscape, and the '
        f'independent AIC + physician-owned + independent home segments '
        f'(~39%) are the fragmented roll-up pool.</p>'
        f'<div style="display:flex;border-radius:3px;overflow:hidden;'
        f'margin-bottom:10px;">{"".join(strip)}</div>'
        f'<div style="overflow-x:auto;"><table style="width:100%;'
        f'border-collapse:collapse;font-size:12px;">'
        f'<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        f'<th style="text-align:left;padding:6px 8px;">Ownership segment</th>'
        f'<th style="text-align:right;padding:6px 8px;">US share</th>'
        f'<th style="text-align:left;padding:6px 8px;">Pool</th>'
        f'<th style="text-align:left;padding:6px 8px;">Examples</th>'
        f'<th style="text-align:left;padding:6px 8px;">Roll-up read</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
        f'<p style="font-size:9.5px;color:{_FAINT};margin:8px 0 0;">'
        f'Ownership shares are national estimates (NHIA / industry '
        f'structure), applied to each county\'s estimated chairs in the '
        f'city deep-dives below. Illustrative — replace with a state '
        f'pharmacy-board / NPPES pull in diligence.</p>')


_CDC_TONE = {"rheum": "#6e5b9e", "onc": _NEG, "iron": _TEAL,
             "chronic": _WARN, "access": _NAVY}


def _cdc_proxies_section(a: Dict[str, Any]) -> str:
    """CDC PLACES / ACS public-health proxies — one row per infusion
    therapy family with the real proxy measure, TX rate, and source.
    A live/offline badge flags whether county rates came from the
    Socrata API or the vendored TX state fallback."""
    cp = a.get("cdc_proxies") or {}
    rows_data = cp.get("therapies", [])
    if not rows_data:
        return (f'<p style="font-size:12px;color:{_FAINT};">CDC proxy '
                f'data unavailable.</p>')
    live = cp.get("live")
    badge = (
        f'<span style="font-size:9px;font-weight:700;letter-spacing:0.06em;'
        f'padding:2px 7px;border-radius:3px;background:{("#e6f4ee" if live else "#f3efe4")};'
        f'color:{(_POS if live else _WARN)};border:1px solid '
        f'{(_POS if live else _WARN)};">'
        f'{"LIVE — CDC PLACES county API" if live else "OFFLINE — TX state rate (county API when egress available)"}'
        f'</span>')
    rows = ""
    for t in rows_data:
        tone = _CDC_TONE.get(t["key"], _FAINT)
        meas = ", ".join(t["measures"])
        rows += (
            f'<tr>'
            f'<td style="padding:6px 8px;"><span style="display:inline-block;'
            f'width:9px;height:9px;border-radius:2px;background:{tone};'
            f'margin-right:6px;"></span><strong>{html.escape(t["therapy"])}'
            f'</strong></td>'
            f'<td style="padding:6px 8px;font-size:11px;color:{_DIM};'
            f'font-family:monospace;">{html.escape(meas)}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'font-weight:700;color:{tone};">{t["rate_pct"]:.1f}%</td>'
            f'<td style="padding:6px 8px;font-size:11px;color:{_FAINT};">'
            f'{html.escape(t["denominator"])}</td>'
            f'<td style="padding:6px 8px;font-size:10.5px;color:{_FAINT};">'
            f'{html.escape(t["source"])}</td>'
            f'</tr>')
    notes = "".join(
        f'<li style="margin:2px 0;font-size:11px;color:{_DIM};">'
        f'<strong style="color:{_CDC_TONE.get(t["key"], _FAINT)};">'
        f'{html.escape(t["therapy"])}:</strong> {html.escape(t["note"])}</li>'
        for t in rows_data)
    return (
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">'
        f'<p style="font-size:12px;color:{_DIM};line-height:1.6;margin:0;'
        f'max-width:680px;">{html.escape(cp.get("note", ""))}</p>{badge}</div>'
        f'<div style="overflow-x:auto;"><table style="width:100%;'
        f'border-collapse:collapse;font-size:12px;">'
        f'<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        f'<th style="text-align:left;padding:6px 8px;">Infusion therapy '
        f'family</th>'
        f'<th style="text-align:left;padding:6px 8px;">CDC/ACS proxy</th>'
        f'<th style="text-align:right;padding:6px 8px;">TX rate</th>'
        f'<th style="text-align:left;padding:6px 8px;">Denominator</th>'
        f'<th style="text-align:left;padding:6px 8px;">Source</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
        f'<ul style="margin:10px 0 0;padding-left:18px;">{notes}</ul>'
        f'<p style="font-size:9.5px;color:{_FAINT};margin:8px 0 0;">'
        f'PLACES = CDC model-based full-population crude prevalence '
        f'(BRFSS + ACS). Arthritis / cancer / CKD shown here from CMS '
        f'Medicare chronic-conditions (TX-adjusted) until the PLACES '
        f'county API is reached, then full-population rates apply. '
        f'Female share for the IV-iron pool from ACS B01001.</p>')


def _cdc_demand_block(dd: Dict[str, Any]) -> str:
    """Per-metro CDC-proxied therapy demand — ranked bars + a payer-
    access read pulled from the top county."""
    rows = dd.get("cdc_demand", [])
    if not rows:
        return ""
    mx = max((r["estimated_patients"] for r in rows), default=1) or 1
    bars = ""
    for r in rows:
        w = r["estimated_patients"] / mx * 100
        tone = _CDC_TONE.get(r["key"], _FAINT)
        bars += (
            f'<div style="display:grid;grid-template-columns:1fr 90px;'
            f'align-items:center;gap:8px;margin:3px 0;">'
            f'<div><div style="font-size:11px;color:#1a2332;">'
            f'{html.escape(r["therapy"])}</div>'
            f'<div style="height:11px;background:#ece5d6;border-radius:2px;'
            f'overflow:hidden;margin-top:2px;"><div style="height:100%;'
            f'width:{w:.0f}%;background:{tone};"></div></div></div>'
            f'<div style="font-size:11px;font-weight:700;color:{tone};'
            f'text-align:right;">{r["estimated_patients"]:,}</div></div>')
    # Payer access read from the largest county.
    top = max(dd.get("suburbs", [{}]),
              key=lambda s: s.get("infusion_patients", 0), default={})
    pa = top.get("payer_access") or {}
    pa_tone = (_POS if pa.get("band") == "strong" else
               _WARN if pa.get("band") == "moderate" else _NEG)
    pa_html = (
        f'<div style="margin-top:8px;padding:7px 11px;background:#fff;'
        f'border-left:3px solid {pa_tone};border-radius:0 3px 3px 0;'
        f'font-size:11px;color:#1a2332;line-height:1.5;">'
        f'<strong>Payer access ({html.escape(top.get("county", ""))}):</strong> '
        f'index <strong style="color:{pa_tone};">{pa.get("score", 0):.0f}</strong> '
        f'(<span style="color:{pa_tone};">{html.escape(pa.get("band", ""))}</span>) '
        f'— {pa.get("uninsured_rate", 0)*100:.0f}% uninsured · '
        f'{pa.get("child_poverty_rate", 0)*100:.0f}% child poverty · '
        f'{pa.get("routine_checkup_pct", 0):.0f}% routine checkup</div>'
        if pa else "")
    return (
        f'<div style="margin-top:10px;"><div style="font-size:10px;'
        f'color:{_FAINT};letter-spacing:0.06em;margin-bottom:3px;">'
        f'CDC-PROXIED INFUSION DEMAND BY THERAPY (est. patients · real '
        f'population × proxy prevalence)</div>{bars}{pa_html}</div>')


_SAT_TONE = {"UNDERSUPPLIED": _NEG, "balanced": _TEAL,
             "saturated": _WARN, "no local capacity": _NEG}


def _scorecard_section(a: Dict[str, Any]) -> str:
    """The high-level Texas scorecard — counties across the 4 metros
    ranked by long-term opportunity score, with the undersupplied
    growth markets surfaced."""
    sc = a["growth_scorecard"]
    top = sc["top_opportunities"]
    # Ranked opportunity-score bars.
    bar_rows = [{"label": f'{r["county"]} · {r["metro"]}',
                 "score": r["score"], "rank": r["rank"],
                 "flag": r["demand_exceeds_capacity"]}
                for r in top]
    mx = max((r["score"] for r in bar_rows), default=1) or 1
    bars = ""
    for r in bar_rows:
        w = r["score"] / mx * 100
        tone = _NEG if r["flag"] else _NAVY
        flag = (' <span style="color:%s;font-weight:700;font-size:9px;">'
                '★ DEMAND&gt;CAPACITY</span>' % _NEG) if r["flag"] else ""
        bars += (
            f'<div style="display:grid;grid-template-columns:150px 1fr 44px;'
            f'align-items:center;gap:8px;margin:3px 0;">'
            f'<div style="font-size:11px;text-align:right;color:#1a2332;">'
            f'<strong style="color:{tone};">#{r["rank"]}</strong> '
            f'{html.escape(r["label"])}</div>'
            f'<div style="height:14px;background:#ece5d6;border-radius:2px;'
            f'overflow:hidden;"><div style="height:100%;width:{w:.0f}%;'
            f'background:{tone};"></div></div>'
            f'<div style="font-size:11px;font-weight:700;color:{tone};'
            f'text-align:right;">{r["score"]:.0f}</div>'
            f'<div style="grid-column:2/4;font-size:9px;margin-top:-2px;">'
            f'{flag}</div></div>')
    # Undersupplied growth-markets table.
    us_rows = ""
    for r in sc["undersupplied_growth_markets"]:
        dc = r["demand_capacity_ratio"]
        us_rows += (
            f'<tr>'
            f'<td style="padding:5px 8px;font-weight:600;">'
            f'{html.escape(r["county"])} '
            f'<span style="font-size:10px;color:{_FAINT};">'
            f'{html.escape(r["metro"])}</span></td>'
            f'<td class="num" style="padding:5px 8px;text-align:right;">'
            f'{r["infusion_patients"]:,}</td>'
            f'<td class="num" style="padding:5px 8px;text-align:right;">'
            f'{r["est_chairs"]}</td>'
            f'<td class="num" style="padding:5px 8px;text-align:right;'
            f'color:{_NEG};font-weight:600;">{dc if dc is not None else "—"}'
            f'</td>'
            f'<td style="padding:5px 8px;font-size:10px;color:{_FAINT};">'
            f'{html.escape(r["saturation_band"])}</td>'
            f'</tr>')
    return (
        f'<p style="font-size:12px;color:{_DIM};line-height:1.6;'
        f'margin:0 0 6px;">{html.escape(sc["note"])}</p>'
        f'<div style="font-size:10px;color:{_FAINT};letter-spacing:0.06em;'
        f'font-weight:700;margin:10px 0 4px;">TOP-10 COUNTY OPPORTUNITIES '
        f'(of {sc["n_counties"]} across the 4 metros)</div>'
        f'{bars}'
        f'<div style="font-size:10px;color:{_NEG};letter-spacing:0.06em;'
        f'font-weight:700;margin:14px 0 4px;">UNDERSUPPLIED GROWTH MARKETS '
        f'— demand likely to exceed AIS chair capacity ({sc["n_undersupplied"]})'
        f'</div>'
        f'<div style="overflow-x:auto;"><table style="width:100%;'
        f'border-collapse:collapse;font-size:12px;">'
        f'<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        f'<th style="text-align:left;padding:5px 8px;">County</th>'
        f'<th style="text-align:right;padding:5px 8px;">Infusion pts</th>'
        f'<th style="text-align:right;padding:5px 8px;">AIS chairs (est)</th>'
        f'<th style="text-align:right;padding:5px 8px;">Demand / capacity</th>'
        f'<th style="text-align:left;padding:5px 8px;">Saturation</th>'
        f'</tr></thead><tbody>{us_rows}</tbody></table></div>'
        f'<p style="font-size:9.5px;color:{_FAINT};margin:8px 0 0;">'
        f'Demand/capacity = AIS-channel slice (~22% of infusion volume) '
        f'÷ estimated AIS chair capacity; ≥1.10 or a balanced growth '
        f'corridor (where site-of-care migration 22%→30% + population '
        f'growth push it over) flags ★. Score blends demand · '
        f'under-saturation · payer quality · growth.</p>')


def _county_capacity_table(dd: Dict[str, Any]) -> str:
    """Per-county capacity & saturation for a metro's top counties."""
    rows = ""
    for s in dd["suburbs"][:8]:
        cap = s.get("capacity") or {}
        opp = s.get("opportunity") or {}
        dc = cap.get("demand_capacity_ratio")
        band = cap.get("saturation_band", "")
        bt = _SAT_TONE.get(band, _FAINT)
        flag = (' <span style="color:%s;font-weight:700;">★</span>' % _NEG
                if opp.get("demand_exceeds_capacity") else "")
        rows += (
            f'<tr>'
            f'<td style="padding:4px 8px;">{html.escape(s["county"])}'
            + (' <span style="font-size:9px;color:%s;">▲N</span>' % _NAVY
               if s.get("region") == "North suburb" else "")
            + f'{flag}</td>'
            f'<td class="num" style="padding:4px 8px;text-align:right;">'
            f'{s["infusion_patients"]:,}</td>'
            f'<td class="num" style="padding:4px 8px;text-align:right;">'
            f'{cap.get("est_chairs","—")}</td>'
            f'<td class="num" style="padding:4px 8px;text-align:right;">'
            f'{cap.get("patients_per_chair") or "—"}</td>'
            f'<td class="num" style="padding:4px 8px;text-align:right;'
            f'color:{bt};font-weight:600;">{dc if dc is not None else "—"}</td>'
            f'<td class="num" style="padding:4px 8px;text-align:right;">'
            f'{cap.get("non_hospital_penetration",0)*100:.0f}%</td>'
            f'<td style="padding:4px 8px;font-size:10px;color:{bt};">'
            f'{html.escape(band)}</td>'
            f'<td class="num" style="padding:4px 8px;text-align:right;'
            f'font-weight:700;color:{_NAVY};">{opp.get("score",0):.0f}</td>'
            f'</tr>')
    return (
        f'<div style="margin-top:10px;"><div style="font-size:10px;'
        f'color:{_FAINT};letter-spacing:0.06em;margin-bottom:3px;">'
        f'CHAIR CAPACITY · SATURATION · OPPORTUNITY BY COUNTY</div>'
        f'<table style="width:100%;border-collapse:collapse;font-size:11px;">'
        f'<thead><tr style="border-bottom:1px solid #d6cfc0;color:{_FAINT};">'
        f'<th style="text-align:left;padding:3px 8px;">County</th>'
        f'<th style="text-align:right;padding:3px 8px;">Pts</th>'
        f'<th style="text-align:right;padding:3px 8px;">Chairs</th>'
        f'<th style="text-align:right;padding:3px 8px;">Pts/chair</th>'
        f'<th style="text-align:right;padding:3px 8px;">D/C</th>'
        f'<th style="text-align:right;padding:3px 8px;">Non-hosp</th>'
        f'<th style="text-align:left;padding:3px 8px;">Saturation</th>'
        f'<th style="text-align:right;padding:3px 8px;">Score</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>'
        f'<p style="font-size:9px;color:{_FAINT};margin:3px 0 0;">'
        f'D/C = AIS-channel demand ÷ chair capacity · Non-hosp = est. '
        f'non-hospital site penetration · ▲N north suburb · ★ demand '
        f'likely to exceed capacity.</p></div>')


def _channel_cards(a: Dict[str, Any]) -> str:
    """Two side-by-side channel breakdowns — AIC vs home infusion."""
    cards = ""
    for c in a["channel_economics"]:
        is_aic = "AIC" in c["channel"]
        tone = _NAVY if is_aic else _TEAL
        def _row(label: str, val: str) -> str:
            return (
                f'<div style="margin-top:7px;"><div style="font-size:9px;'
                f'letter-spacing:0.08em;color:{_FAINT};font-weight:700;">'
                f'{label}</div><div style="font-size:11.5px;color:{_DIM};'
                f'line-height:1.5;">{html.escape(val)}</div></div>')
        cards += (
            f'<div style="border:1px solid #d6cfc0;border-top:3px solid '
            f'{tone};border-radius:4px;padding:12px 14px;background:#fff;">'
            f'<div style="font-size:14px;font-weight:700;color:{tone};">'
            f'{html.escape(c["channel"])}</div>'
            f'<p style="font-size:11.5px;color:{_DIM};line-height:1.55;'
            f'margin:4px 0 0;">{html.escape(c["what"])}</p>'
            + _row("REIMBURSEMENT BASIS", c["reimbursement"])
            + _row("MARGIN MODEL", c["margin_model"])
            + _row("WORKING CAPITAL", c["working_capital"])
            + f'<div style="margin-top:8px;padding:7px 10px;background:#fbf3ef;'
            f'border-left:3px solid {_NEG};border-radius:0 3px 3px 0;">'
            f'<div style="font-size:9px;letter-spacing:0.08em;color:{_NEG};'
            f'font-weight:700;">DEFINING RISK</div>'
            f'<div style="font-size:11.5px;color:#1a2332;line-height:1.5;">'
            f'{html.escape(c["key_risk"])}</div></div>'
            f'</div>')
    return (
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">'
        + cards + '</div>')


def _players_table(a: Dict[str, Any]) -> str:
    rows = ""
    for p in a["players"]:
        ct = _CHANNEL_TONE.get(p["channel"], _FAINT)
        tx = ('<span style="color:%s;font-weight:700;">TX ✓</span>' % _POS
              if p["tx"] else '<span style="color:%s;">—</span>' % _FAINT)
        name = (f'<a href="{html.escape(p["link"], quote=True)}" '
                f'target="_blank" rel="noopener" style="color:{_NAVY};'
                f'font-weight:600;text-decoration:none;">'
                f'{html.escape(p["name"])} ↗</a>'
                if p.get("link") else
                f'<span style="font-weight:600;">{html.escape(p["name"])}</span>')
        rows += (
            f'<tr>'
            f'<td style="padding:6px 8px;">{name}</td>'
            f'<td style="padding:6px 8px;"><span style="font-size:10px;'
            f'font-weight:700;color:{ct};">{html.escape(p["channel"])}</span>'
            f'</td>'
            f'<td style="padding:6px 8px;font-size:11px;color:{_DIM};">'
            f'{html.escape(p["ownership"])}</td>'
            f'<td style="padding:6px 8px;text-align:center;">{tx}</td>'
            f'<td style="padding:6px 8px;font-size:11px;color:{_DIM};">'
            f'{html.escape(p["scale"])}</td>'
            f'</tr>')
    return (
        '<div style="overflow-x:auto;"><table style="width:100%;'
        'border-collapse:collapse;font-size:12px;">'
        '<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        '<th style="text-align:left;padding:6px 8px;">Operator</th>'
        '<th style="text-align:left;padding:6px 8px;">Channel</th>'
        '<th style="text-align:left;padding:6px 8px;">Ownership</th>'
        '<th style="padding:6px 8px;">TX</th>'
        '<th style="text-align:left;padding:6px 8px;">Scale / note</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
        f'<p style="font-size:9.5px;color:{_FAINT};margin:8px 0 0;">'
        'Channel: AIC = ambulatory infusion center · Home = home '
        'infusion · Both. Ownership and scale from public filings / '
        'company disclosures (directional). Payer-owned operators '
        '(Optum, Paragon) can steer their own members — a competitive '
        'and white-bagging risk to independents.</p>')


def _risk_register(a: Dict[str, Any]) -> str:
    rows = ""
    for r in a["risk_register"]:
        st = _SEV_TONE.get(r["severity"], _FAINT)
        ct = _CHANNEL_TONE.get(r["hits"], _FAINT)
        rows += (
            f'<div style="padding:10px 0;border-bottom:1px solid #e4ddca;">'
            f'<div style="display:flex;gap:8px;align-items:baseline;'
            f'flex-wrap:wrap;">'
            f'<span style="font-family:monospace;font-size:9px;font-weight:'
            f'700;color:{st};border:1px solid {st};border-radius:2px;'
            f'padding:1px 5px;">{r["severity"]}</span>'
            f'<span style="font-size:9px;color:{_FAINT};text-transform:'
            f'uppercase;letter-spacing:0.06em;">{html.escape(r["category"])}'
            f'</span>'
            f'<span style="font-size:13px;font-weight:600;color:#1a2332;">'
            f'{html.escape(r["risk"])}</span>'
            f'<span style="margin-left:auto;font-size:9px;font-weight:700;'
            f'color:{ct};">hits {html.escape(r["hits"])}</span></div>'
            f'<div style="font-size:11.5px;color:{_DIM};margin-top:3px;'
            f'line-height:1.5;">{html.escape(r["detail"])}</div>'
            f'<div style="font-size:11.5px;color:#1a2332;margin-top:4px;'
            f'line-height:1.5;padding-left:10px;border-left:2px solid '
            f'{_TEAL};"><strong style="color:{_TEAL};">RCM read: </strong>'
            f'{html.escape(r["rcm_angle"])}</div>'
            f'</div>')
    return rows


def _rcm_playbook(a: Dict[str, Any]) -> str:
    pb = a["rcm_playbook"]
    kpi_rows = "".join(
        f'<tr>'
        f'<td style="padding:5px 8px;font-weight:600;">'
        f'{html.escape(k["kpi"])}</td>'
        f'<td style="padding:5px 8px;font-size:11px;color:{_DIM};">'
        f'{html.escape(k["why"])}</td>'
        f'<td style="padding:5px 8px;font-size:11px;color:{_FAINT};">'
        f'{html.escape(k["benchmark"])}</td>'
        f'</tr>' for k in pb["kpis"])
    denials = "".join(
        f'<li style="font-size:11.5px;color:{_DIM};margin:2px 0;">'
        f'{html.escape(d)}</li>' for d in pb["denial_drivers"])
    questions = "".join(
        f'<li style="font-size:11.5px;color:#1a2332;margin:3px 0;">'
        f'{html.escape(q)}</li>' for q in pb["diligence_questions"])
    return (
        f'<div style="padding:10px 14px;background:#eef3f2;'
        f'border-left:3px solid {_TEAL};border-radius:0 3px 3px 0;'
        f'font-size:12.5px;color:#1a2332;line-height:1.6;margin-bottom:12px;">'
        f'<strong>Why infusion RCM is different:</strong> '
        f'{html.escape(pb["why_different"])}</div>'
        + '<div style="font-size:10px;color:%s;letter-spacing:0.06em;'
        'font-weight:700;margin:4px 0;">THE INFUSION RCM KPI SET</div>'
        % _FAINT
        + '<div style="overflow-x:auto;"><table style="width:100%;'
        'border-collapse:collapse;font-size:12px;">'
        '<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        '<th style="text-align:left;padding:5px 8px;">KPI</th>'
        '<th style="text-align:left;padding:5px 8px;">Why it matters here</th>'
        '<th style="text-align:left;padding:5px 8px;">Read</th>'
        f'</tr></thead><tbody>{kpi_rows}</tbody></table></div>'
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px;'
        'margin-top:12px;">'
        f'<div><div style="font-size:10px;color:{_NEG};letter-spacing:'
        f'0.06em;font-weight:700;margin-bottom:3px;">TOP DENIAL DRIVERS</div>'
        f'<ul style="margin:0;padding-left:18px;">{denials}</ul></div>'
        f'<div><div style="font-size:10px;color:{_TEAL};letter-spacing:'
        f'0.06em;font-weight:700;margin-bottom:3px;">RCM DILIGENCE '
        f'QUESTIONS</div><ol style="margin:0;padding-left:18px;">'
        f'{questions}</ol></div></div>')


def _hbar_svg(rows: List[Dict[str, Any]], *, label_key: str,
             value_key: str, value_fmt, tone: str, sub_key: str = "",
             width: int = 560, rank_key: str = "") -> str:
    """Compact ranked horizontal-bar SVG — the 'easy to visualize'
    aggregation. ``rows`` already ordered for display; bar length ∝
    value / max."""
    if not rows:
        return ""
    vals = [float(r.get(value_key) or 0) for r in rows]
    mx = max(vals) or 1.0
    label_w, bar_w, right_w = 168, 250, 130
    row_h, gap, pad = 22, 6, 6
    height = pad * 2 + len(rows) * (row_h + gap) - gap
    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'style="max-width:{width}px;display:block;" role="img">']
    for i, r in enumerate(rows):
        y = pad + i * (row_h + gap)
        ty = y + row_h / 2 + 4
        v = float(r.get(value_key) or 0)
        w = max(2.0, bar_w * v / mx)
        rk = (f'<tspan font-weight="700" fill="{tone}">#'
              f'{r.get(rank_key)}</tspan> ' if rank_key else "")
        lab = html.escape(str(r.get(label_key, "")))
        parts.append(
            f'<text x="{label_w-6}" y="{ty:.0f}" text-anchor="end" '
            f'font-size="11" fill="#1a2332">{rk}{lab}</text>'
            f'<rect x="{label_w}" y="{y}" width="{w:.1f}" height="{row_h}" '
            f'rx="2" fill="{tone}" fill-opacity="0.85"/>'
            f'<text x="{label_w+w+6:.1f}" y="{ty:.0f}" font-size="10.5" '
            f'font-weight="600" fill="{_DIM}">{value_fmt(v)}'
            + (f'<tspan fill="{_FAINT}" font-weight="400"> · '
               f'{html.escape(str(r.get(sub_key,"")))}</tspan>'
               if sub_key else "")
            + '</text>')
    parts.append("</svg>")
    return "".join(parts)


def _city_section(dd: Dict[str, Any]) -> str:
    att = dd["attractiveness"]
    att_tone = _POS if att >= 90 else _TEAL if att >= 80 else _WARN
    # Operators, linked.
    ops = " ".join(
        (f'<a href="{html.escape(o["link"], quote=True)}" target="_blank" '
         f'rel="noopener" style="display:inline-block;padding:3px 9px;'
         f'margin:0 5px 5px 0;border:1px solid #c9c1ac;border-radius:3px;'
         f'font-size:11px;color:{_NAVY};text-decoration:none;'
         f'background:#fff;">{html.escape(o["org"])} ↗</a>')
        if o.get("link") else
        (f'<span style="display:inline-block;padding:3px 9px;'
         f'margin:0 5px 5px 0;border:1px solid #c9c1ac;border-radius:3px;'
         f'font-size:11px;color:{_NAVY};">{html.escape(o["org"])}</span>')
        for o in dd["operators"])

    # Age bands in age order (rank badge inline) — demand share bars.
    age_rows = [
        {"band": b["band"], "demand_share": b["demand_share"],
         "demand_rank": b["demand_rank"],
         "sub": f'{b["population"]/1e3:,.0f}K · util {b["util_index"]:.1f}'}
        for b in dd["age_bands"]]
    age_chart = _hbar_svg(
        age_rows, label_key="band", value_key="demand_share",
        value_fmt=lambda v: f'{v*100:.0f}%', tone=_TEAL, sub_key="sub",
        rank_key="demand_rank")

    # Top suburbs (member counties) by infusion patients — north
    # suburbs get a ▲N marker on the label.
    sub_rows = []
    for s in dd["suburbs"][:8]:
        lab = s["county"] + (" ▲N" if s.get("region") == "North suburb"
                             else "")
        sub_rows.append({**s, "county_label": lab})
    sub_chart = _hbar_svg(
        sub_rows, label_key="county_label", value_key="infusion_patients",
        value_fmt=lambda v: f'{v:,.0f} pts', tone=_NAVY, rank_key="demand_rank",
        sub_key="")

    # North-suburb callout.
    north = (
        f'<div style="margin-top:10px;padding:7px 11px;background:#eef2f7;'
        f'border-left:3px solid {_NAVY};border-radius:0 3px 3px 0;'
        f'font-size:11.5px;color:#1a2332;line-height:1.5;">'
        f'<strong>North suburbs:</strong> {html.escape(dd["north_suburbs"])}'
        f'</div>' if dd.get("north_suburbs") else "")

    # Illness burden → most-common therapies (metro-aggregated, real
    # population × TX prevalence).
    ib_rows = "".join(
        f'<tr>'
        f'<td style="padding:4px 8px;font-weight:500;">'
        f'{html.escape(i["condition"])}</td>'
        f'<td class="num" style="padding:4px 8px;text-align:right;'
        f'font-variant-numeric:tabular-nums;">{i["estimated_patients"]:,}</td>'
        f'<td style="padding:4px 8px;font-size:11px;color:{_DIM};">'
        f'{html.escape(i["therapy"])}</td>'
        f'<td style="padding:4px 8px;font-size:10px;color:{_FAINT};">'
        f'{html.escape(i["channel"])}</td>'
        f'</tr>'
        for i in dd.get("illness_burden", []))
    illness = (
        f'<div style="margin-top:10px;">'
        f'<div style="font-size:10px;color:{_FAINT};letter-spacing:0.06em;'
        f'margin-bottom:3px;">ILLNESS BURDEN → MOST-COMMON THERAPIES '
        f'(est. adults = pop × TX prevalence)</div>'
        f'<table style="width:100%;border-collapse:collapse;font-size:11.5px;">'
        f'<thead><tr style="border-bottom:1px solid #d6cfc0;color:{_FAINT};">'
        f'<th style="text-align:left;padding:3px 8px;">Condition</th>'
        f'<th style="text-align:right;padding:3px 8px;">Est. patients</th>'
        f'<th style="text-align:left;padding:3px 8px;">Therapy</th>'
        f'<th style="text-align:left;padding:3px 8px;">Channel</th>'
        f'</tr></thead><tbody>{ib_rows}</tbody></table></div>'
        if ib_rows else "")

    # White-space callout. patients_per_ais is None when a county has no
    # estimated local AIS — that is MAXIMAL whitespace, labeled as such.
    def _ws_cap(w: Dict[str, Any]) -> str:
        ppa = w.get("patients_per_ais")
        if ppa is None:
            return "no local AIS — fully unserved"
        return f'{w["est_ais_centers"]} AIS ({ppa:,}/center)'
    ws = "".join(
        f'<li style="margin:2px 0;font-size:11.5px;color:{_DIM};">'
        f'<strong>{html.escape(w["county"])}</strong> — '
        f'{w["infusion_patients"]:,} patients vs {_ws_cap(w)} · '
        f'{w["pct_age_65_plus"]*100:.0f}% 65+</li>'
        for w in dd["whitespace_counties"][:4])

    return (
        f'<div style="border:1px solid #d6cfc0;border-radius:5px;'
        f'padding:14px 16px;margin:0 0 16px;background:#fbf9f4;">'
        # Header
        f'<div style="display:flex;gap:10px;align-items:baseline;'
        f'flex-wrap:wrap;border-bottom:1px solid #e4ddca;padding-bottom:8px;">'
        f'<span style="font-family:monospace;font-weight:700;font-size:15px;'
        f'color:{att_tone};">#{dd["rank"]}</span>'
        f'<span style="font-size:16px;font-weight:700;color:#1a2332;">'
        f'{html.escape(dd["metro"])}</span>'
        f'<span style="margin-left:auto;font-family:monospace;font-size:11px;'
        f'color:{_DIM};">pop {dd["population"]/1e6:.2f}M · '
        f'{dd["seniors"]/1e3:,.0f}K seniors · '
        f'attractiveness <strong style="color:{att_tone};">{att:.0f}</strong></span>'
        f'</div>'
        # Specialty + operators
        f'<p style="font-size:12px;color:{_DIM};line-height:1.55;'
        f'margin:8px 0 6px;"><strong style="color:#1a2332;">Specialty tilt:'
        f'</strong> {html.escape(dd["specialty"])}</p>'
        f'<div style="font-size:10px;color:{_FAINT};letter-spacing:0.06em;'
        f'margin:4px 0 2px;">BIG OPERATORS PRESENT (linked):</div>'
        f'<div>{ops}</div>'
        # Two-up charts
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px;'
        f'margin-top:12px;">'
        f'<div><div style="font-size:10px;color:{_FAINT};'
        f'letter-spacing:0.06em;margin-bottom:4px;">'
        f'INFUSION DEMAND BY AGE BAND (ranked)</div>{age_chart}</div>'
        f'<div><div style="font-size:10px;color:{_FAINT};'
        f'letter-spacing:0.06em;margin-bottom:4px;">'
        f'SUBURBS / COUNTIES BY PATIENTS (ranked · ▲N = north suburb)'
        f'</div>{sub_chart}</div>'
        f'</div>'
        + north
        + illness
        + _cdc_demand_block(dd)
        + _county_capacity_table(dd)
        # White-space
        + f'<div style="margin-top:10px;padding:8px 12px;background:#fff;'
        f'border-left:3px solid {_WARN};border-radius:0 3px 3px 0;">'
        f'<div style="font-size:10px;color:{_WARN};font-weight:700;'
        f'letter-spacing:0.06em;margin-bottom:3px;">EARLY / WHITESPACE '
        f'SUBURBS — demand with thin local capacity</div>'
        f'<ul style="margin:0;padding-left:18px;">{ws}</ul></div>'
        f'</div>')


def render_texas_infusion_page(
    qs: "Dict[str, Any] | None" = None,
) -> str:
    """Render the full Texas infusion diligence page. ``qs`` carries
    optional AIC assumption overrides (clamped server-side)."""
    from ..diligence.texas_infusion import (
        aic_assumptions_from_qs, build_texas_infusion_analysis,
    )
    overrides = aic_assumptions_from_qs(qs or {})
    a = build_texas_infusion_analysis(aic_overrides=overrides)
    demo = a["demographics"]

    sources = "".join(
        f'<li style="margin:3px 0;font-size:11px;color:{_DIM};">'
        f'{html.escape(src)}</li>' for src in a["sources"])

    body = (
        ck_page_title(
            "Texas Infusion Market",
            eyebrow="DILIGENCE · MARKET SIZING",
            meta=f"TAM {_money(a['sizing']['tam'])} · "
                 f"{a['sizing']['composite_cagr_pct']:.1f}% CAGR · "
                 f"HHI {a['hhi']:,.0f} ({a['hhi_band']})",
        )
        + ck_source_purpose(
            purpose="Size and segment the Texas ambulatory + home "
                    "infusion market for a buy-and-build thesis.",
            universe="illustrative",
            source="NHIA + MedPAC demand magnitudes scaled to TX by "
                   "Census 2024 population share; ACS demographics; "
                   "DOJ/FTC HHI. Replace with engagement data before IC.",
        )
        + '<div class="ts-wrap" style="max-width:980px;">'
        + _kpi_strip(a)

        + ck_section_header("Market sizing — the driver chain",
                            eyebrow="TAM / SAM / SOM")
        + _sizing_chain(a)

        + ck_section_header("The two channels — AIC vs home infusion",
                            eyebrow="REIMBURSEMENT · MARGIN · WORKING CAPITAL")
        + _channel_cards(a)

        + ck_section_header("Players — the named operators",
                            eyebrow="WHO COMPETES · OWNERSHIP · TX PRESENCE")
        + _players_table(a)

        + ck_section_header("Competitive dynamics — capacity by owner",
                            eyebrow="NATIONAL/REGIONAL · HEALTH-SYSTEM · "
                                    "PHYSICIAN · INDEPENDENT AIC · HOME")
        + _provider_segments_section(a)

        + ck_section_header("CDC public-health demand proxies",
                            eyebrow="PLACES + ACS → THERAPY DEMAND · LIVE API "
                                    "WITH OFFLINE FALLBACK")
        + _cdc_proxies_section(a)

        + ck_section_header("Where the risks are",
                            eyebrow="REIMBURSEMENT · RCM · MARKET — WITH THE "
                                    "RCM READ")
        + _risk_register(a)

        + ck_section_header("How RCM talks about infusion",
                            eyebrow="THE REVENUE-CYCLE PLAYBOOK")
        + _rcm_playbook(a)

        + '<div id="aic"></div>'
        + ck_section_header("AIC unit economics",
                            eyebrow="PER-CHAIR P&L · THE LEVERS · BREAKDOWN "
                                    "BY SECTION · EDITABLE")
        + _aic_assumptions_form(a)
        + _aic_economics_section(a)
        + '<div style="display:grid;grid-template-columns:1fr 1fr;'
          'gap:18px;margin-top:14px;">'
        + (f'<div><div style="font-size:10px;color:{_FAINT};'
           f'letter-spacing:0.06em;font-weight:700;margin-bottom:4px;">'
           f'SENSITIVITY — WHAT MOVES CONTRIBUTION / CHAIR (±20% swings)'
           f'</div>{_aic_tornado_svg(a["aic_sensitivity"])}</div>')
        + (f'<div><div style="font-size:10px;color:{_FAINT};'
           f'letter-spacing:0.06em;font-weight:700;margin-bottom:4px;">'
           f'UTILIZATION → CONTRIBUTION CURVE · BREAK-EVEN</div>'
           f'{_util_curve_svg(a["aic_utilization_curve"])}'
           f'<p style="font-size:9.5px;color:{_FAINT};margin:4px 0 0;">'
           f'Fixed nursing + overhead don\'t scale with utilization — '
           f'that gap creates the break-even. Recomputed from your '
           f'assumptions above.</p></div>')
        + '</div>'

        + ck_section_header("Drug supply & inventory",
                            eyebrow="LIVE FDA SHORTAGE STATUS — NO SYNTHETIC "
                                    "DATA")
        + _drug_supply_section(a)

        + ck_section_header("Segmentation by therapy form",
                            eyebrow="WHERE THE DOLLARS — AND THE GROWTH — ARE")
        + _segment_table(a)

        + ck_section_header("Segmentation by site of care",
                            eyebrow="THE SITE-OF-CARE SHIFT")
        + _site_table(a)

        + ck_section_header("Provider landscape & competitiveness",
                            eyebrow="COUNTS · CAPACITY · FRAGMENTATION")
        + _provider_panel(a)

        + ck_section_header("Metro attractiveness ranking",
                            eyebrow="HOUSTON · DFW · AUSTIN · SAN ANTONIO")
        + _metro_table(a)

        + ck_section_header("City deep-dives",
                            eyebrow="AGE-BAND DEMAND · SUBURBS · OPERATORS · "
                                    "WHITESPACE")
        + "".join(_city_section(dd) for dd in a["metro_deepdives"])

        + ck_section_header("Texas growth scorecard",
                            eyebrow="COUNTY OPPORTUNITY RANKING · WHERE DEMAND "
                                    "OUTRUNS CAPACITY")
        + _scorecard_section(a)

        + ck_section_header("Concentration — operator landscape",
                            eyebrow="HHI · FRAGMENTATION → ROLL-UP")
        + _concentration(a)

        + ck_section_header("Payer mix",
                            eyebrow="COMMERCIAL-HEAVY · TX NON-EXPANSION")
        + _payer_section(a)

        + ck_section_header("Medicare population & demographics",
                            eyebrow="THE DEMAND TAILWIND")
        + (
            f'<div style="font-size:12.5px;color:{_DIM};line-height:1.7;">'
            f'<p>Texas has <strong>{demo["seniors_65_plus"]/1e6:.2f}M</strong> '
            f'residents aged 65+ ({demo["pct_age_65_plus"]*100:.1f}% of '
            f'{demo["population"]/1e6:.1f}M across {demo["counties"]} '
            f'counties) — the Medicare-covered base for infused therapies, '
            f'and one of the fastest-growing senior populations in the US '
            f'(Sun-Belt aging + net in-migration). The 65+ cohort drives '
            f'oncology-support, OPAT, and IVIG volume.</p>'
            f'<p style="margin-top:6px;"><strong>Growth trend:</strong> '
            f'{html.escape(a["population_growth"]["note"])}</p>'
            f'<p style="margin-top:6px;">Counterweights: a '
            f'<strong>{demo["uninsured_rate"]*100:.0f}% uninsured rate</strong> '
            f'(the highest in the US, a Medicaid-non-expansion consequence) '
            f'and <strong>{demo["pct_rural"]*100:.0f}% rural</strong> '
            f'population that complicates home-nurse route economics outside '
            f'the four big metros. Median household income '
            f'${demo["median_household_income"]:,.0f}.</p></div>')

        + ck_section_header("Five-year growth drivers",
                            eyebrow="WHICH LEVER CARRIES THE GROWTH")
        + _growth_drivers(a)

        + ck_section_header("Texas structural factors",
                            eyebrow="WHAT'S DIFFERENT ABOUT TEXAS")
        + _factors(a)

        + ck_section_header("Sources & basis", eyebrow="VERIFIABILITY")
        + f'<ul style="margin:0;padding-left:18px;">{sources}</ul>'
        + f'<p style="font-size:11px;color:{_FAINT};margin:10px 0 0;'
        f'line-height:1.6;">{html.escape(a["basis_note"])}</p>'
        + '<p style="font-size:11.5px;margin:10px 0 0;">'
        '<a href="/diligence/tam-sam?template=infusion" '
        f'style="color:{_NAVY};font-weight:600;text-decoration:none;">'
        'Open the editable infusion model in the TAM/SAM Builder →</a></p>'
        + '</div>'
    )

    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body, "Texas Infusion Market",
        active_nav="/diligence",
        subtitle=f"TAM {_money(a['sizing']['tam'])} · HHI {a['hhi']:,.0f}",
    )
