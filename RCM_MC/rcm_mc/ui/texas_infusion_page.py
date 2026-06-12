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
import re
from typing import Any, Dict, List, Tuple

from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_page_title, ck_section_header,
    ck_source_purpose,
)
from .cdd_chart_kit import (
    compose_exhibit, parse_table, chart_export_toolbar,
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


def texas_exhibit_svg(a: Dict[str, Any]) -> str:
    """The auto-composed 'Investment Highlights' exhibit SVG — built from
    the live analysis (funnel, site-of-care evolution, top de-novo
    counties, current mix). Shared by the page section and the download
    route so they can never disagree."""
    s = a["sizing"]
    funnel = parse_table(
        f"Stage\tValue\nTAM\t{s['tam']/1e6:.0f}\nSAM\t{s['sam']/1e6:.0f}\n"
        f"SOM\t{s['som']/1e6:.0f}")
    evo = a["site_of_care_evolution"]["series"]
    soc_rows = "\n".join(
        f"{r['year']}\t{r['hopd']*100:.0f}\t{r['ais']*100:.0f}\t"
        f"{r['home']*100:.0f}\t{r['office']*100:.0f}" for r in evo)
    soc = parse_table("Year\tHOPD\tAIS\tHome\tOffice\n" + soc_rows)
    top = a["growth_scorecard"]["top_opportunities"][:6]
    score = parse_table(
        "County\tScore\n" + "\n".join(
            f"{t['county']}\t{t['score']:.0f}" for t in top))
    site = {x["site"]: x["share"] for x in a["site_of_care"]}
    mix = parse_table(
        "Site\tShare\n" + "\n".join(
            f"{k.split(' (')[0]}\t{v*100:.0f}" for k, v in site.items()))
    panels = [
        {"type": "funnel", "title": "Market sizing — TAM → SAM → SOM ($M)",
         "table": funnel, "palette": "Navy–Teal"},
        {"type": "column_100", "title": "Site-of-care mix, 2015–2024 (%)",
         "table": soc, "palette": "Navy–Teal"},
        {"type": "bar", "title": "Top de-novo county opportunities",
         "table": score, "palette": "Chartis"},
        {"type": "donut", "title": "Current site-of-care mix",
         "table": mix, "palette": "Chartis"},
    ]
    return compose_exhibit(
        panels, title="Texas Infusion — Investment Highlights",
        eyebrow="Commercial Due Diligence",
        source="Source: NHIA / MedPAC scaled to TX (Census/ACS) · CMS · "
               "CDC PLACES — illustrative")


def _exhibit_section(a: Dict[str, Any]) -> str:
    """Auto-compose a one-page investment-highlights exhibit slide from
    the LIVE analysis — the deliverable a partner drops into a deck.
    Recomputes from the same numbers as the sections, so it can never
    disagree with them."""
    svg = texas_exhibit_svg(a)
    return (
        f'<p style="font-size:12px;color:{_DIM};line-height:1.6;'
        f'margin:0 0 8px;">A one-page exhibit auto-composed from the live '
        f'analysis on this page — download the SVG/PNG straight into a '
        f'deck. It recomputes from the same figures, so it never disagrees '
        f'with the sections below.</p>'
        f'<div style="border:1px solid #d6cfc0;border-radius:8px;'
        f'padding:12px;background:#fff;text-align:center;">'
        f'<div id="txExhibit">{svg}</div>'
        + chart_export_toolbar("txExhibit", "texas-infusion-exhibit")
        + f'<div style="margin-top:6px;"><a href="/api/diligence/'
        f'texas-infusion/exhibit.svg" style="font-size:11px;color:{_TEAL};'
        f'font-weight:600;text-decoration:none;">⬇ download the exhibit '
        f'SVG (server-rendered)</a></div>'
        + '</div>')


def _thesis_section(a: Dict[str, Any]) -> str:
    """The IC-ready investment-thesis synthesis — the top-line a partner
    reads first, recomputed from the sections below."""
    it = a.get("investment_thesis") or {}
    if not it:
        return ""
    pillars = ""
    for i, p in enumerate(it.get("pillars", []), 1):
        pillars += (
            f'<div style="border:1px solid #d6cfc0;border-radius:6px;'
            f'padding:11px 13px;background:#fff;">'
            f'<div style="font-size:9px;letter-spacing:0.06em;color:{_FAINT};'
            f'font-weight:700;">PILLAR {i}</div>'
            f'<div style="font-size:13px;font-weight:700;color:#1a2332;'
            f'margin-top:2px;">{html.escape(p["title"])}</div>'
            f'<div style="font-size:11.5px;font-weight:700;color:{_TEAL};'
            f'font-family:monospace;margin:3px 0;">{html.escape(p["stat"])}'
            f'</div>'
            f'<div style="font-size:11px;color:{_DIM};line-height:1.5;">'
            f'{html.escape(p["point"])}</div></div>')
    risks = "".join(
        f'<li style="margin:3px 0;font-size:11.5px;color:{_DIM};">'
        f'<strong style="color:{_NEG};">{html.escape(r["risk"])}:</strong> '
        f'{html.escape(r["detail"])}</li>' for r in it.get("risks", []))
    ddn = "".join(
        f'<li style="margin:3px 0;font-size:11.5px;color:{_DIM};">'
        f'{html.escape(x)}</li>' for x in it.get("diligence_next", []))
    return (
        f'<div style="border:1px solid #c9c1ac;border-top:4px solid {_NAVY};'
        f'border-radius:6px;padding:16px 18px;background:#fbf9f4;'
        f'margin-bottom:18px;">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;flex-wrap:wrap;gap:8px;">'
        f'<div style="font-size:10px;letter-spacing:0.08em;color:{_FAINT};'
        f'font-weight:700;">INVESTMENT THESIS · IC SUMMARY</div>'
        f'<a href="/api/diligence/texas-infusion/memo" '
        f'style="font-size:11px;font-weight:600;color:{_NAVY};'
        f'border:1px solid {_NAVY};border-radius:4px;padding:4px 11px;'
        f'text-decoration:none;">⬇ IC memo (Markdown)</a></div>'
        f'<p style="font-size:14px;color:#1a2332;line-height:1.6;'
        f'font-family:\'Source Serif 4\',Georgia,serif;margin:6px 0 4px;">'
        f'{html.escape(it["headline"])}</p>'
        f'<div style="display:inline-block;font-size:11px;font-weight:700;'
        f'color:{_POS};border:1px solid {_POS};border-radius:3px;'
        f'padding:2px 8px;margin-bottom:12px;">'
        f'{html.escape(it["verdict"].split(" — ")[0])}</div>'
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,'
        f'minmax(230px,1fr));gap:12px;margin-bottom:14px;">{pillars}</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:22px;">'
        f'<div><div style="font-size:10px;letter-spacing:0.06em;'
        f'color:{_NEG};font-weight:700;margin-bottom:3px;">KEY RISKS</div>'
        f'<ul style="margin:0;padding-left:16px;">{risks}</ul></div>'
        f'<div><div style="font-size:10px;letter-spacing:0.06em;'
        f'color:{_TEAL};font-weight:700;margin-bottom:3px;">DILIGENCE NEXT'
        f'</div><ul style="margin:0;padding-left:16px;">{ddn}</ul></div>'
        f'</div></div>')


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


_EVO_BANDS = [("hopd", "Hospital outpatient (HOPD)", _NAVY),
              ("office", "Physician office", "#b8a98c"),
              ("ais", "Ambulatory infusion (AIS)", _TEAL),
              ("home", "Home infusion", _POS)]


def _hopd_pool_section(a: Dict[str, Any]) -> str:
    """The HOPD 'steered-away' infusion pool by metro — the white-space an
    AIC/home platform captures."""
    hp = a.get("hopd_pool") or {}
    metros = hp.get("metros", [])
    if not metros:
        return ""
    live = hp.get("opps_live")
    badge = (
        f'<span style="font-size:9px;font-weight:700;letter-spacing:0.06em;'
        f'padding:2px 7px;border-radius:3px;background:'
        f'{("#e6f4ee" if live else "#f3efe4")};color:'
        f'{(_POS if live else _WARN)};border:1px solid '
        f'{(_POS if live else _WARN)};">'
        f'{"LIVE — CMS OPPS file" if live else "MODELED — HOPD share × real metro patients (live CMS OPPS via ?nppes=live)"}'
        f'</span>')
    mx = max((m["hopd_patients"] for m in metros), default=1) or 1
    bars = ""
    for m in metros:
        w = m["hopd_patients"] / mx * 100
        short = m["metro"].split("-")[0]
        bars += (
            f'<div style="display:grid;grid-template-columns:130px 1fr 150px;'
            f'align-items:center;gap:8px;margin:3px 0;">'
            f'<div style="font-size:11.5px;color:#1a2332;">'
            f'{html.escape(short)}</div>'
            f'<div style="height:14px;background:#ece5d6;border-radius:2px;'
            f'overflow:hidden;"><div style="height:100%;width:{w:.0f}%;'
            f'background:{_NAVY};"></div></div>'
            f'<div style="font-size:11px;color:{_DIM};text-align:right;">'
            f'<strong style="color:{_NAVY};">{m["hopd_patients"]:,}</strong>'
            f' pts · {_money(m["hopd_revenue"])}</div></div>')
    opps = ""
    if live and hp.get("opps_services"):
        opps = (f'<div style="font-size:11px;color:{_POS};margin-top:6px;">'
                f'Live CMS OPPS: {hp["opps_services"]:,} HOPD infusion '
                f'services · {_money(hp.get("opps_payment",0))} Medicare '
                f'payment (TX).</div>')
    return (
        f'<div style="border:1px solid #d6cfc0;border-top:3px solid {_NAVY};'
        f'border-radius:4px;padding:12px 14px;background:#fff;margin-top:14px;">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:6px;">'
        f'<div style="font-size:13px;font-weight:700;color:{_NAVY};">'
        f'HOPD infusion — the steered-away pool '
        f'({hp["hopd_share"]*100:.0f}% of volume)</div>{badge}</div>'
        f'<div style="display:flex;gap:18px;flex-wrap:wrap;margin-bottom:8px;">'
        f'<div><div style="font-size:9px;color:{_FAINT};letter-spacing:'
        f'0.06em;font-weight:700;">CAPTURABLE HOPD PATIENTS (4 METROS)</div>'
        f'<div style="font-size:18px;font-weight:700;color:{_NAVY};">'
        f'{hp["total_hopd_patients"]:,}</div></div>'
        f'<div><div style="font-size:9px;color:{_FAINT};letter-spacing:'
        f'0.06em;font-weight:700;">HOPD INFUSION REVENUE POOL</div>'
        f'<div style="font-size:18px;font-weight:700;color:{_NAVY};">'
        f'{_money(hp["total_hopd_revenue"])}</div></div></div>'
        f'{bars}{opps}'
        f'<p style="font-size:9.5px;color:{_FAINT};margin:8px 0 0;">'
        f'{html.escape(hp["note"])}</p></div>')


def _evolution_section(a: Dict[str, Any]) -> str:
    """How discharges → home infusion / site-of-care have evolved over
    time: a stacked-area chart of the mix shift, the market-size + OPAT
    growth, and the regulatory/structural event timeline."""
    ev = a.get("site_of_care_evolution") or {}
    series = ev.get("series", [])
    if not series:
        return ""
    yrs = [s["year"] for s in series]
    y0, y1 = yrs[0], yrs[-1]
    W, H = 100.0, 56.0

    def _x(yr):
        return (yr - y0) / (y1 - y0) * W
    # Stacked-area polygons (bottom→top: HOPD, office, AIS, home).
    bands_svg = ""
    cum = {s["year"]: 0.0 for s in series}
    for key, _label, color in _EVO_BANDS:
        top_pts, bot_pts = [], []
        for s in series:
            x = _x(s["year"])
            bot = cum[s["year"]]
            top = bot + s[key]
            bot_pts.append((x, H - bot * H))
            top_pts.append((x, H - top * H))
            cum[s["year"]] = top
        pts = top_pts + bot_pts[::-1]
        path = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
        bands_svg += (f'<polygon points="{path}" fill="{color}" '
                      f'fill-opacity="0.85"/>')
    # Year gridlines + labels.
    grid = ""
    for s in series:
        if s["year"] % 3 == 0 or s["year"] == y1:
            x = _x(s["year"])
            grid += (f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{H}" '
                     f'stroke="#fff" stroke-opacity="0.25" stroke-width="0.3"/>'
                     f'<text x="{x:.1f}" y="{H+4.5:.1f}" text-anchor="middle" '
                     f'font-size="3" fill="{_FAINT}">{s["year"]}</text>')
    chart = (
        f'<svg viewBox="0 -2 100 64" width="100%" height="240" '
        f'role="img" aria-label="Site-of-care evolution" '
        f'style="max-width:620px;">{bands_svg}{grid}</svg>')
    legend = " ".join(
        f'<span style="font-size:10.5px;color:{_DIM};margin-right:12px;">'
        f'<span style="display:inline-block;width:9px;height:9px;'
        f'border-radius:2px;background:{c};margin-right:4px;"></span>'
        f'{html.escape(lab)}</span>' for _k, lab, c in _EVO_BANDS)
    # KPI strip.
    def _kpi(label, val, sub=""):
        return (
            f'<div style="flex:1;min-width:110px;"><div style="font-size:9px;'
            f'letter-spacing:0.06em;color:{_FAINT};font-weight:700;">{label}'
            f'</div><div style="font-size:17px;font-weight:700;color:{_NAVY};">'
            f'{val}</div><div style="font-size:9.5px;color:{_FAINT};">{sub}'
            f'</div></div>')
    s0, s1 = series[0], series[-1]
    kpis = (
        f'<div style="display:flex;gap:14px;flex-wrap:wrap;margin:6px 0 10px;">'
        + _kpi("HOPD SHARE", f'{s0["hopd"]*100:.0f}% → {s1["hopd"]*100:.0f}%',
               f'−{ev["hopd_shift_pts"]} pts to non-hospital')
        + _kpi("HOME + AIS", f'{(s0["home"]+s0["ais"])*100:.0f}% → '
               f'{(s1["home"]+s1["ais"])*100:.0f}%',
               f'+{ev["home_ais_gain_pts"]} pts')
        + _kpi("MARKET SIZE", f'${s0["market_size_b"]:.0f}B → '
               f'${s1["market_size_b"]:.0f}B',
               f'{ev["market_cagr_pct"]:.1f}% CAGR')
        + _kpi("OPAT VOLUME", f'{s0["opat_index"]} → {s1["opat_index"]}',
               f'index, {y0}=100')
        + '</div>')
    # Event timeline.
    ev_rows = ""
    for e in ev.get("events", []):
        tone = (_POS if e["tone"] == "positive" else
                _WARN if e["tone"] == "warning" else _DIM)
        ev_rows += (
            f'<div style="display:grid;grid-template-columns:46px 1fr;'
            f'gap:10px;padding:7px 0;border-bottom:1px solid #e4ddca;">'
            f'<div style="font-family:monospace;font-weight:700;font-size:13px;'
            f'color:{tone};">{e["year"]}</div>'
            f'<div><div style="font-size:12.5px;font-weight:600;color:#1a2332;">'
            f'{html.escape(e["label"])}</div>'
            f'<div style="font-size:11.5px;color:{_DIM};line-height:1.5;'
            f'margin-top:1px;">{html.escape(e["detail"])}</div></div></div>')
    drivers = "".join(
        f'<li style="margin:3px 0;font-size:11.5px;color:{_DIM};">'
        f'<strong style="color:#1a2332;">{html.escape(d["driver"])}:</strong> '
        f'{html.escape(d["detail"])}</li>' for d in ev.get("drivers", []))
    return (
        f'<p style="font-size:12px;color:{_DIM};line-height:1.6;'
        f'margin:0 0 8px;max-width:720px;">{html.escape(ev.get("note", ""))}'
        f'</p>{kpis}'
        f'<div style="font-size:10px;color:{_FAINT};letter-spacing:0.06em;'
        f'font-weight:700;margin-bottom:3px;">INFUSION SITE-OF-CARE MIX, '
        f'{y0}–{y1} (HOPD → AIS + HOME)</div>{chart}'
        f'<div style="margin:6px 0 14px;">{legend}</div>'
        f'<div style="display:grid;grid-template-columns:1.15fr 1fr;gap:22px;'
        f'align-items:start;">'
        f'<div><div style="font-size:10px;color:{_FAINT};letter-spacing:'
        f'0.06em;font-weight:700;margin-bottom:3px;">WHAT DROVE THE '
        f'DISCHARGE SHIFT — EVENT TIMELINE</div>{ev_rows}</div>'
        f'<div><div style="font-size:10px;color:{_FAINT};letter-spacing:'
        f'0.06em;font-weight:700;margin-bottom:3px;">STRUCTURAL DRIVERS</div>'
        f'<ul style="margin:0;padding-left:16px;">{drivers}</ul></div></div>')


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


# Stylized Texas outline (viewBox 0 0 100 100) for the provider map.
_TX_OUTLINE = ("29,8 43,8 43,24 50,24 60,22 63,17 69,26 72,38 78,50 "
               "74,58 66,64 57,72 50,80 45,83 42,75 37,66 31,58 25,50 "
               "18,40 10,35 17,30 24,25 29,20")


def _provider_map_section(a: Dict[str, Any]) -> str:
    """An SVG bubble map of the four metros on a stylized Texas outline,
    sized by infusion-provider supply (estimated AIS centers, or the live
    NPPES count where reachable), plus the NPPES taxonomy reference."""
    pm = a.get("provider_map") or {}
    pts = pm.get("points", [])
    if not pts:
        return ""
    live = pm.get("live")

    def _val(p):
        return (p["nppes_count"] if p.get("nppes_count") is not None
                else p["estimated_centers"])
    mx = max((_val(p) for p in pts), default=1) or 1
    bubbles = ""
    for i, p in enumerate(pts):
        v = _val(p)
        r = 2.5 + 6.5 * (v / mx) ** 0.5
        tone = _NAVY if i == 0 else _TEAL
        bubbles += (
            f'<circle cx="{p["x"]}" cy="{p["y"]}" r="{r:.1f}" '
            f'fill="{tone}" fill-opacity="0.78" stroke="#fff" '
            f'stroke-width="0.6"><title>{html.escape(p["short"])}: {v} '
            f'infusion centers</title></circle>'
            f'<text x="{p["x"]}" y="{p["y"]-r-1.2:.1f}" text-anchor="middle" '
            f'font-size="3.4" font-weight="700" fill="#1a2332">'
            f'{html.escape(p["short"])}</text>'
            f'<text x="{p["x"]}" y="{p["y"]+1.1:.1f}" text-anchor="middle" '
            f'font-size="3.2" font-weight="700" fill="#fff">{v}</text>')
    svg = (
        f'<svg viewBox="0 0 100 100" width="320" height="320" '
        f'role="img" aria-label="Texas infusion-provider map" '
        f'style="max-width:340px;">'
        f'<polygon points="{_TX_OUTLINE}" fill="#efe9dc" '
        f'stroke="#c9c1ac" stroke-width="0.8"/>{bubbles}</svg>')
    taxo = "".join(
        f'<li style="margin:2px 0;font-size:11px;color:{_DIM};">'
        f'<code style="font-size:10px;color:{_NAVY};">{html.escape(t["code"])}'
        f'</code> — {html.escape(t["label"])} '
        f'<span style="color:{_FAINT};">({html.escape(t["kind"])})</span></li>'
        for t in pm.get("taxonomies", []))
    crows = "".join(
        f'<tr><td style="padding:3px 8px;font-weight:600;">'
        f'{html.escape(p["short"])}</td>'
        f'<td class="num" style="padding:3px 8px;text-align:right;">'
        f'{p["estimated_centers"]}</td>'
        f'<td class="num" style="padding:3px 8px;text-align:right;'
        f'color:{(_POS if p["nppes_count"] is not None else _FAINT)};">'
        f'{p["nppes_count"] if p["nppes_count"] is not None else "—"}</td>'
        f'</tr>' for p in pts)
    badge = (
        f'<span style="font-size:9px;font-weight:700;letter-spacing:0.06em;'
        f'padding:2px 7px;border-radius:3px;background:'
        f'{("#e6f4ee" if live else "#f3efe4")};color:'
        f'{(_POS if live else _WARN)};border:1px solid '
        f'{(_POS if live else _WARN)};">'
        f'{"LIVE — NPPES NPI Registry" if live else "MODELED — est. centers (live NPPES via ?nppes=live)"}'
        f'</span>')
    return (
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:6px;">'
        f'<p style="font-size:12px;color:{_DIM};line-height:1.6;margin:0;'
        f'max-width:640px;">{html.escape(pm.get("note", ""))}</p>{badge}</div>'
        f'<div style="display:grid;grid-template-columns:auto 1fr;gap:20px;'
        f'align-items:start;">{svg}'
        f'<div><table style="width:100%;border-collapse:collapse;'
        f'font-size:12px;margin-bottom:8px;">'
        f'<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        f'<th style="text-align:left;padding:3px 8px;">Metro</th>'
        f'<th style="text-align:right;padding:3px 8px;">Est. centers</th>'
        f'<th style="text-align:right;padding:3px 8px;">NPPES</th>'
        f'</tr></thead><tbody>{crows}</tbody></table>'
        f'<div style="font-size:10px;color:{_FAINT};letter-spacing:0.06em;'
        f'font-weight:700;margin:6px 0 3px;">NPPES INFUSION TAXONOMIES '
        f'(PUBLIC NUCC CODES)</div>'
        f'<ul style="margin:0;padding-left:16px;">{taxo}</ul></div></div>')


# Schematic US tile-grid (row, col) — a labeled state grid, not a
# geographic projection. Each tile carries its abbreviation so position
# need not be exact to read.
_STATE_TILE = {
    "AK": (0, 0), "ME": (0, 10),
    "VT": (1, 9), "NH": (1, 10),
    "WA": (2, 0), "ID": (2, 1), "MT": (2, 2), "ND": (2, 3), "MN": (2, 4),
    "IL": (2, 5), "WI": (2, 6), "MI": (2, 7), "NY": (2, 8), "MA": (2, 9),
    "RI": (2, 10),
    "OR": (3, 0), "NV": (3, 1), "WY": (3, 2), "SD": (3, 3), "IA": (3, 4),
    "IN": (3, 5), "OH": (3, 6), "PA": (3, 7), "NJ": (3, 8), "CT": (3, 9),
    "CA": (4, 0), "UT": (4, 1), "CO": (4, 2), "NE": (4, 3), "MO": (4, 4),
    "KY": (4, 5), "WV": (4, 6), "VA": (4, 7), "MD": (4, 8), "DE": (4, 9),
    "AZ": (5, 1), "NM": (5, 2), "KS": (5, 3), "AR": (5, 4), "TN": (5, 5),
    "NC": (5, 6), "SC": (5, 7), "DC": (5, 8),
    "OK": (6, 3), "LA": (6, 4), "MS": (6, 5), "AL": (6, 6), "GA": (6, 7),
    "HI": (7, 0), "TX": (7, 3), "FL": (7, 8),
}


def _heat(frac: float) -> str:
    """Light→teal sequential color for a 0–1 fraction."""
    frac = max(0.0, min(1.0, frac))
    c0 = (0xE4, 0xEC, 0xEA)
    c1 = (0x12, 0x5E, 0x59)
    rgb = tuple(round(c0[i] + (c1[i] - c0[i]) * frac) for i in range(3))
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _jcode_pos_section(a: Dict[str, Any]) -> str:
    """Infusion J-code place-of-service by state — a tile-grid choropleth
    of the non-facility (office/AIC) share, percentage tables, the
    national facility→non-facility trend, and the Texas read."""
    jp = a.get("jcode_pos") or {}
    states = jp.get("states", [])
    if not states:
        return ""
    by_code = {s["code"]: s for s in states}
    vals = [s["nonfac_pct"] for s in states]
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    live = jp.get("live")
    cell, gap = 9.0, 0.7
    ncol, nrow = 11, 8
    tiles = ""
    for code, (r, c) in _STATE_TILE.items():
        s = by_code.get(code)
        if not s:
            continue
        x, y = c * cell, r * cell
        fill = _heat((s["nonfac_pct"] - lo) / rng)
        is_tx = code == "TX"
        stroke = _NEG if is_tx else "#fff"
        sw = 0.9 if is_tx else 0.4
        txt = "#fff" if (s["nonfac_pct"] - lo) / rng > 0.55 else "#1a2332"
        tiles += (
            f'<g><rect x="{x:.1f}" y="{y:.1f}" width="{cell-gap:.1f}" '
            f'height="{cell-gap:.1f}" rx="1.2" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}">'
            f'<title>{html.escape(s["name"])}: '
            f'{s["nonfac_pct"]*100:.0f}% non-facility'
            f'{" (live)" if s["is_live"] else " (modeled)"}</title></rect>'
            f'<text x="{x+(cell-gap)/2:.1f}" y="{y+3.4:.1f}" '
            f'text-anchor="middle" font-size="2.7" font-weight="700" '
            f'fill="{txt}">{code}</text>'
            f'<text x="{x+(cell-gap)/2:.1f}" y="{y+6.4:.1f}" '
            f'text-anchor="middle" font-size="2.6" fill="{txt}">'
            f'{s["nonfac_pct"]*100:.0f}</text></g>')
    legend = (
        f'<div style="display:flex;align-items:center;gap:6px;'
        f'font-size:10px;color:{_FAINT};margin-top:4px;">'
        f'<span>{lo*100:.0f}%</span>'
        f'<span style="flex:0 0 120px;height:9px;border-radius:2px;'
        f'background:linear-gradient(90deg,{_heat(0)},{_heat(1)});"></span>'
        f'<span>{hi*100:.0f}% non-facility</span>'
        f'<span style="margin-left:8px;color:{_NEG};font-weight:700;">'
        f'▭ TX</span></div>')
    svg = (
        f'<svg viewBox="-1 -1 {ncol*cell+1:.0f} {nrow*cell+1:.0f}" '
        f'width="100%" height="300" role="img" '
        f'aria-label="J-code place-of-service by state" '
        f'style="max-width:560px;">{tiles}</svg>')

    def _row(s, hl=False):
        bg = "background:#fbf3ef;" if hl else ""
        tag = (' <span style="color:%s;font-weight:700;font-size:9px;">'
               'TX</span>' % _NEG) if s["code"] == "TX" else ""
        live_tag = ('<span style="color:%s;font-size:9px;">●live</span>' % _POS
                    if s["is_live"] else
                    '<span style="color:%s;font-size:9px;">modeled</span>'
                    % _FAINT)
        return (
            f'<tr style="{bg}border-bottom:1px solid #e8e1d0;">'
            f'<td class="num" style="padding:3px 8px;color:{_FAINT};">'
            f'#{s["rank"]}</td>'
            f'<td style="padding:3px 8px;font-weight:600;">'
            f'{html.escape(s["name"])}{tag}</td>'
            f'<td class="num" style="padding:3px 8px;text-align:right;'
            f'font-weight:700;color:{_TEAL};">{s["nonfac_pct"]*100:.0f}%</td>'
            f'<td class="num" style="padding:3px 8px;text-align:right;'
            f'color:{_DIM};">{s["rural"]*100:.0f}%</td>'
            f'<td class="num" style="padding:3px 8px;text-align:right;'
            f'color:{_DIM};">{s["ma_penetration"]*100:.0f}%</td>'
            f'<td style="padding:3px 8px;">{live_tag}</td></tr>')
    tx = jp["texas"]
    top = states[:6]
    bottom = states[-6:]
    body_rows = "".join(_row(s) for s in top)
    if 6 < tx["rank"] <= len(states) - 6:
        body_rows += ('<tr><td colspan="6" style="text-align:center;'
                      f'color:{_FAINT};font-size:10px;padding:2px;">⋯</td></tr>')
        body_rows += _row(tx, hl=True)
    body_rows += ('<tr><td colspan="6" style="text-align:center;'
                  f'color:{_FAINT};font-size:10px;padding:2px;">⋯</td></tr>')
    body_rows += "".join(_row(s) for s in bottom)
    state_table = (
        f'<table style="width:100%;border-collapse:collapse;font-size:11.5px;">'
        f'<thead><tr style="border-bottom:2px solid #c9c1ac;color:{_FAINT};">'
        f'<th style="text-align:left;padding:3px 8px;">#</th>'
        f'<th style="text-align:left;padding:3px 8px;">State</th>'
        f'<th style="text-align:right;padding:3px 8px;">Non-facility</th>'
        f'<th style="text-align:right;padding:3px 8px;">Rural</th>'
        f'<th style="text-align:right;padding:3px 8px;">MA pen</th>'
        f'<th style="text-align:left;padding:3px 8px;">Src</th>'
        f'</tr></thead><tbody>{body_rows}</tbody></table>')

    tr_rows = ""
    for t in jp["national_trend"]:
        tr_rows += (
            f'<tr style="border-bottom:1px solid #e8e1d0;">'
            f'<td style="padding:3px 8px;font-weight:600;">{t["year"]}</td>'
            f'<td class="num" style="padding:3px 8px;text-align:right;'
            f'color:{_NAVY};">{t["facility_pct"]*100:.0f}%</td>'
            f'<td style="padding:3px 8px;">'
            f'{_bar(t["nonfacility_pct"]*100, _TEAL, 90)}</td>'
            f'<td class="num" style="padding:3px 8px;text-align:right;'
            f'font-weight:700;color:{_TEAL};">'
            f'{t["nonfacility_pct"]*100:.0f}%</td></tr>')
    trend_table = (
        f'<table style="width:100%;border-collapse:collapse;font-size:11.5px;">'
        f'<thead><tr style="border-bottom:2px solid #c9c1ac;color:{_FAINT};">'
        f'<th style="text-align:left;padding:3px 8px;">Year</th>'
        f'<th style="text-align:right;padding:3px 8px;">Facility (HOPD)</th>'
        f'<th style="padding:3px 8px;"></th>'
        f'<th style="text-align:right;padding:3px 8px;">Non-facility</th>'
        f'</tr></thead><tbody>{tr_rows}</tbody></table>')

    jcodes = ", ".join(c["hcpcs"] for c in jp.get("jcodes", []))
    badge = (
        f'<span style="font-size:9px;font-weight:700;letter-spacing:0.06em;'
        f'padding:2px 7px;border-radius:3px;background:'
        f'{("#e6f4ee" if live else "#f3efe4")};color:'
        f'{(_POS if live else _WARN)};border:1px solid '
        f'{(_POS if live else _WARN)};">'
        f'{"LIVE — CMS Part B by-Geography-and-Service" if live else "MODELED — real state factors (live CMS via ?nppes=live)"}'
        f'</span>')
    tx_read = (
        f'<div style="margin-top:8px;padding:8px 11px;background:#fbf3ef;'
        f'border-left:3px solid {_NEG};border-radius:0 3px 3px 0;'
        f'font-size:11.5px;color:#1a2332;line-height:1.55;">'
        f'<strong style="color:{_NEG};">Texas:</strong> '
        f'~{tx["nonfac_pct"]*100:.0f}% of infusion J-code volume is '
        f'non-facility (office/AIC), ranking #{tx["rank"]} of '
        f'{len(states)} — pushed up by low rurality '
        f'({tx["rural"]*100:.0f}%) and high MA penetration '
        f'({tx["ma_penetration"]*100:.0f}%). That favorable site mix is '
        f'why the AIC roll-up thesis works here.</div>')
    return (
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:6px;">'
        f'<p style="font-size:12px;color:{_DIM};line-height:1.6;margin:0;'
        f'max-width:620px;">{html.escape(jp.get("note", ""))}</p>{badge}</div>'
        f'<div style="display:grid;grid-template-columns:1.05fr 1fr;gap:20px;'
        f'align-items:start;"><div>{svg}{legend}</div>'
        f'<div><div style="font-size:10px;color:{_FAINT};letter-spacing:'
        f'0.06em;font-weight:700;margin-bottom:3px;">NON-FACILITY SHARE — '
        f'TOP · TEXAS · BOTTOM</div>{state_table}</div></div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;'
        f'margin-top:14px;align-items:start;">'
        f'<div><div style="font-size:10px;color:{_FAINT};letter-spacing:'
        f'0.06em;font-weight:700;margin-bottom:3px;">NATIONAL FACILITY → '
        f'NON-FACILITY TREND</div>{trend_table}</div>'
        f'<div>{tx_read}</div></div>'
        f'<p style="font-size:9.5px;color:{_FAINT};margin:8px 0 0;">'
        f'J-code basket: {html.escape(jcodes)}. Facility = HOPD/inpatient; '
        f'non-facility = office / freestanding AIC (the binary CMS POS). '
        f'FFS only — excludes Medicare Advantage (~half of Medicare), so '
        f'the non-facility shift is understated. Small cells (&lt;11) '
        f'suppressed. Granular POS (home vs HOPD vs office) needs the paid '
        f'PSPS Master File.</p>')


_IMPACT_META = {
    "tailwind": ("▲", _POS, "TAILWIND"),
    "headwind": ("▼", _NEG, "HEADWIND"),
    "neutral": ("●", _FAINT, "NEUTRAL"),
}


def _regulatory_section(a: Dict[str, Any]) -> str:
    """The regulatory + reimbursement environment — federal Part B/D, the
    HIT benefit, IRA/biosimilars/340B, site-of-care/UM, Texas rules, and
    compliance — each item tagged tailwind/headwind/neutral with the
    diligence implication."""
    re_ = a.get("regulatory_environment") or {}
    cats = re_.get("categories", [])
    if not cats:
        return ""

    def _pill(label, n, tone):
        return (
            f'<div style="flex:1;min-width:90px;text-align:center;'
            f'padding:7px 6px;border:1px solid {tone};border-radius:4px;'
            f'background:#fff;"><div style="font-size:20px;font-weight:700;'
            f'color:{tone};">{n}</div><div style="font-size:9px;'
            f'letter-spacing:0.08em;color:{_FAINT};font-weight:700;">{label}'
            f'</div></div>')
    summary = (
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:10px;">'
        + _pill("TAILWINDS", re_["tailwinds"], _POS)
        + _pill("HEADWINDS", re_["headwinds"], _NEG)
        + _pill("NEUTRAL", re_["neutral"], _FAINT)
        + '</div>')
    net = (
        f'<div style="padding:9px 13px;background:#eef5f4;border-left:4px '
        f'solid {_TEAL};border-radius:0 4px 4px 0;margin-bottom:14px;">'
        f'<span style="font-size:9px;font-weight:800;letter-spacing:0.11em;'
        f'color:{_TEAL};">NET READ</span> '
        f'<span style="font-size:12px;color:#1a2332;line-height:1.55;">'
        f'{html.escape(re_["net_read"])}</span></div>')
    blocks = ""
    for c in cats:
        rows = ""
        for it in c["items"]:
            sym, tone, lab = _IMPACT_META.get(it["impact"],
                                              ("●", _FAINT, ""))
            rows += (
                f'<div style="padding:8px 0;border-bottom:1px solid #e8e1d0;">'
                f'<div style="display:flex;gap:8px;align-items:baseline;'
                f'flex-wrap:wrap;">'
                f'<span style="font-weight:700;color:{tone};font-size:11px;">'
                f'{sym} {lab}</span>'
                f'<span style="font-size:12.5px;font-weight:600;color:#1a2332;">'
                f'{html.escape(it["topic"])}</span>'
                f'<span style="margin-left:auto;font-size:9.5px;color:{_FAINT};'
                f'font-style:italic;">{html.escape(it["status"])}</span></div>'
                f'<div style="font-size:11.5px;color:{_DIM};line-height:1.5;'
                f'margin-top:2px;">{html.escape(it["detail"])}</div>'
                f'<div style="font-size:11.5px;color:#1a2332;line-height:1.5;'
                f'margin-top:3px;padding-left:10px;border-left:2px solid '
                f'{tone};"><strong style="color:{tone};">Implication: </strong>'
                f'{html.escape(it["implication"])}</div></div>')
        blocks += (
            f'<div style="margin-bottom:14px;"><div style="font-size:11px;'
            f'font-weight:700;letter-spacing:0.04em;color:{_NAVY};'
            f'border-bottom:2px solid #c9c1ac;padding-bottom:3px;'
            f'margin-bottom:4px;">{html.escape(c["category"])}</div>{rows}'
            f'</div>')
    return (
        summary + net + blocks
        + f'<p style="font-size:9.5px;color:{_FAINT};margin:4px 0 0;">'
        f'{html.escape(re_.get("note", ""))}</p>')


def _ma_enrollment_panel(a: Dict[str, Any]) -> str:
    """Medicare Advantage enrollment + the site-of-care-steerage read —
    the key payer-mix force on infusion."""
    ma = a.get("ma_enrollment") or {}
    if not ma:
        return ""
    def _kpi(label: str, val: str) -> str:
        return (
            f'<div style="flex:1;min-width:120px;"><div style="font-size:9px;'
            f'letter-spacing:0.06em;color:{_FAINT};font-weight:700;">{label}'
            f'</div><div style="font-size:18px;font-weight:700;color:{_NAVY};">'
            f'{val}</div></div>')
    return (
        f'<div style="border:1px solid #d6cfc0;border-top:3px solid {_NAVY};'
        f'border-radius:4px;padding:12px 14px;background:#fff;margin-top:14px;">'
        f'<div style="font-size:13px;font-weight:700;color:{_NAVY};'
        f'margin-bottom:8px;">Medicare Advantage — the site-of-care '
        f'steerage engine</div>'
        f'<div style="display:flex;gap:16px;flex-wrap:wrap;">'
        + _kpi("TX MA ENROLLEES", f'{ma["enrollment"]/1e6:.2f}M')
        + _kpi("TOTAL MEDICARE", f'{ma.get("total_medicare",0)/1e6:.2f}M')
        + _kpi("MA PENETRATION", f'{ma.get("penetration",0)*100:.0f}%')
        + _kpi("DUAL-ELIGIBLE", f'{ma["dual_eligible_pct"]*100:.0f}%')
        + '</div>'
        + f'<p style="font-size:11.5px;color:{_DIM};line-height:1.55;'
        f'margin:8px 0 0;">{html.escape(ma["note"])}</p>'
        + f'<p style="font-size:9px;color:{_FAINT};margin:6px 0 0;">'
        f'MA enrollment: CMS MA geographic-variation file (state, '
        f'{ma.get("year","—")}). Penetration denominator: '
        f'{html.escape(ma.get("denominator_source","—"))} — the true total-'
        f'Medicare base (not the 65+ proxy, which omits the &lt;65 '
        f'disabled). Live county penetration via the CMS enrollment API '
        f'where egress permits.</p></div>')


def _asp_pricing_section(a: Dict[str, Any]) -> str:
    """Part B ASP buy-and-bill drug-pricing reference — the marquee
    infusion J-codes, the ASP+6 / sequestered mechanics, and the live
    per-unit payment limit where the CMS ASP file is reachable."""
    asp = a.get("asp_pricing") or {}
    ref = asp.get("reference", [])
    if not ref:
        return ""
    live = asp.get("live")
    badge = (
        f'<span style="font-size:9px;font-weight:700;letter-spacing:0.06em;'
        f'padding:2px 7px;border-radius:3px;background:'
        f'{("#e6f4ee" if live else "#f3efe4")};color:'
        f'{(_POS if live else _WARN)};border:1px solid '
        f'{(_POS if live else _WARN)};">'
        f'{"LIVE — CMS ASP file" if live else "OFFLINE — J-code reference + formula (live $/unit when egress available)"}'
        f'</span>')
    rows = ""
    for r in ref:
        pay = r.get("payment_limit_per_unit")
        pay_s = (f'${pay:,.2f}' if pay is not None else
                 f'<span style="color:{_FAINT};">ASP×{1+asp["addon_sequestered"]:.3f}</span>')
        rows += (
            f'<tr style="border-bottom:1px solid #e4ddca;">'
            f'<td style="padding:5px 8px;font-family:monospace;'
            f'font-weight:700;color:{_NAVY};">{html.escape(r["hcpcs"])}</td>'
            f'<td style="padding:5px 8px;"><strong>{html.escape(r["drug"])}'
            f'</strong> <span style="font-size:10px;color:{_FAINT};">'
            f'{html.escape(r["unit"])}</span></td>'
            f'<td style="padding:5px 8px;font-size:11px;color:{_DIM};">'
            f'{html.escape(r["category"])}</td>'
            f'<td style="padding:5px 8px;font-size:11px;color:{_DIM};">'
            f'{html.escape(r["channel"])}</td>'
            f'<td class="num" style="padding:5px 8px;text-align:right;'
            f'font-weight:600;">{pay_s}</td>'
            f'</tr>')
    return (
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px;">'
        f'<p style="font-size:12px;color:{_DIM};line-height:1.6;margin:0;'
        f'max-width:680px;">{html.escape(asp["note"])}</p>{badge}</div>'
        f'<div style="display:flex;gap:10px;margin-bottom:8px;flex-wrap:wrap;">'
        f'<div style="padding:5px 10px;background:#eef2f7;border-radius:3px;'
        f'font-size:11px;color:#1a2332;"><strong>Statutory:</strong> '
        f'ASP + {asp["addon_statutory"]*100:.0f}%</div>'
        f'<div style="padding:5px 10px;background:#fbf3ef;border-radius:3px;'
        f'font-size:11px;color:#1a2332;"><strong>Post-sequester:</strong> '
        f'≈ASP + {asp["addon_sequestered"]*100:.1f}%</div></div>'
        f'<div style="overflow-x:auto;"><table style="width:100%;'
        f'border-collapse:collapse;font-size:12px;">'
        f'<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        f'<th style="text-align:left;padding:5px 8px;">HCPCS</th>'
        f'<th style="text-align:left;padding:5px 8px;">Drug</th>'
        f'<th style="text-align:left;padding:5px 8px;">Category</th>'
        f'<th style="text-align:left;padding:5px 8px;">Channel</th>'
        f'<th style="text-align:right;padding:5px 8px;">ASP pay limit/unit</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>'
        f'<p style="font-size:9.5px;color:{_FAINT};margin:6px 0 0;">'
        f'HCPCS J-codes + descriptors are public CMS facts; the per-unit '
        f'ASP payment limit fills in live from the CMS ASP Pricing file '
        f'(quarterly). The payment limit minus the operator\'s GPO / '
        f'channel acquisition cost is the buy-and-bill drug spread — the '
        f'engine of AIC + home economics.</p>')


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


def _denovo_jcurve_svg(ramp: Dict[str, Any]) -> str:
    """The de-novo build J-curve — cumulative cash over months, dipping
    on capex + ramp burn then crossing zero at break-even."""
    s = ramp.get("series", [])
    if not s:
        return ""
    W, H, pl, pb, pt = 560, 210, 64, 26, 14
    pw, ph = W - pl - 14, H - pt - pb
    cums = [r["cumulative"] for r in s]
    n = len(s)
    lo, hi = min(cums + [0]), max(cums + [0])
    span = (hi - lo) or 1.0

    def _x(i):
        return pl + pw * (i / max(n - 1, 1))

    def _y(v):
        return pt + ph * (1 - (v - lo) / span)
    zero_y = _y(0)
    parts = [f'<svg viewBox="0 0 {W} {H}" width="100%" height="210" '
             f'role="img" aria-label="De-novo J-curve" '
             f'style="max-width:{W}px;">']
    # Zero line.
    parts.append(f'<line x1="{pl}" y1="{zero_y:.1f}" x2="{pl+pw}" '
                 f'y2="{zero_y:.1f}" stroke="{_FAINT}" stroke-width="1" '
                 f'stroke-dasharray="3 3"/>')
    # Area under/over the curve to the zero line.
    top = " ".join(f"{_x(i):.1f},{_y(r['cumulative']):.1f}"
                   for i, r in enumerate(s))
    parts.append(f'<polyline points="{top}" fill="none" stroke="{_NAVY}" '
                 f'stroke-width="2.4"/>')
    # Break-even marker.
    be = ramp.get("breakeven_month")
    if be and be <= n:
        bx = _x(be - 1)
        parts.append(
            f'<line x1="{bx:.1f}" y1="{pt}" x2="{bx:.1f}" y2="{pt+ph}" '
            f'stroke="{_POS}" stroke-width="1" stroke-dasharray="2 2"/>'
            f'<text x="{bx:.1f}" y="{pt+8}" text-anchor="middle" '
            f'font-size="9" font-weight="700" fill="{_POS}">break-even '
            f'm{be}</text>')
    # Year x labels.
    for yr in range(1, n // 12 + 1):
        xi = _x(yr * 12 - 1)
        parts.append(f'<text x="{xi:.1f}" y="{H-8}" text-anchor="middle" '
                     f'font-size="9" fill="{_FAINT}">Y{yr}</text>')
    # Y labels (cum at trough + end).
    parts.append(f'<text x="{pl-6}" y="{_y(hi):.1f}" text-anchor="end" '
                 f'font-size="9" fill="{_FAINT}">{_money(hi)}</text>'
                 f'<text x="{pl-6}" y="{_y(lo)+3:.1f}" text-anchor="end" '
                 f'font-size="9" fill="{_FAINT}">{_money(lo)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _denovo_section(a: Dict[str, Any]) -> str:
    """De-novo AIC build economics — the J-curve + the KPIs a deal team
    underwrites on a build-vs-buy decision."""
    r = a.get("aic_denovo_ramp") or {}
    if not r.get("series"):
        return ""
    yc = r.get("year_contribution", [])

    def _kpi(label, val, sub=""):
        return (
            f'<div style="flex:1;min-width:120px;"><div style="font-size:9px;'
            f'letter-spacing:0.06em;color:{_FAINT};font-weight:700;">{label}'
            f'</div><div style="font-size:18px;font-weight:700;color:{_NAVY};">'
            f'{val}</div><div style="font-size:9.5px;color:{_FAINT};">{sub}'
            f'</div></div>')
    be = r.get("breakeven_month")
    kpis = (
        '<div style="display:flex;gap:14px;flex-wrap:wrap;margin:6px 0 10px;">'
        + _kpi("BUILD CAPEX", _money(r["capex_total"]),
               f'{r["chairs"]:.0f} chairs × {_money(r["capex_per_chair"])} '
               f'+ {_money(r["preopen"])} pre-open')
        + _kpi("CASH BREAK-EVEN",
               f'month {be}' if be else '>3 yrs',
               f'{r["ramp_months"]}-mo ramp to {r["mature_util"]*100:.0f}% util')
        + _kpi("MATURE CONTRIBUTION",
               _money(r["mature_annual_contribution"]) + "/yr",
               'at full utilization')
        + _kpi("YEAR-3 CASH-ON-CASH", f'{r["y3_cash_on_cash"]:.1f}x',
               'Y3 contribution ÷ build capex')
        + '</div>')
    yrs = "".join(
        f'<span style="margin-right:14px;">Y{i+1}: '
        f'<strong style="color:{_NAVY};">{_money(v)}</strong></span>'
        for i, v in enumerate(yc))
    return (
        kpis
        + '<div style="font-size:10px;color:%s;letter-spacing:0.06em;'
          'font-weight:700;margin-bottom:4px;">CUMULATIVE CASH — THE BUILD '
          'J-CURVE (capex out, ramp burn, then recovery)</div>' % _FAINT
        + _denovo_jcurve_svg(r)
        + f'<div style="font-size:11.5px;color:{_DIM};margin-top:6px;">'
        f'Contribution by year: {yrs}</div>'
        + f'<p style="font-size:9.5px;color:{_FAINT};margin:6px 0 0;">'
        f'{html.escape(r["note"])}</p>')


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


_HI_TONE = {"opat": _NAVY, "ig": _TEAL, "tpn": _WARN,
            "inotrope": "#6e5b9e", "biologic": _NEG, "rare": "#0a8a5f"}
_HI_TIER_TONE = {
    "National platform": _NAVY, "Payer-owned": _NEG,
    "IG specialist": _TEAL, "IG / factor": _TEAL,
    "Specialty / complex": "#6e5b9e", "Rare / factor": "#6e5b9e",
    "Franchise / roll-up pool": _WARN,
}


def _home_infusion_section(a: Dict[str, Any]) -> str:
    """The deep home-infusion read: episode economics, therapy/condition
    reference with TX eligible-population estimates, the network roster,
    and the Medicare HIT reimbursement gap."""
    hi = a.get("home_infusion") or {}
    if not hi:
        return ""
    ec = hi.get("episode_economics", {})
    conds = {c["key"]: c for c in hi.get("tx_conditions", [])}

    # Episode-economics card (the concrete number).
    drivers = "".join(
        f'<div style="display:flex;justify-content:space-between;gap:10px;'
        f'font-size:11px;padding:2px 0;border-bottom:1px dotted #e4ddca;">'
        f'<span style="color:{_DIM};">{html.escape(d[0])}</span>'
        f'<span style="color:#1a2332;font-weight:600;font-family:monospace;">'
        f'{html.escape(d[1])}</span></div>'
        for d in ec.get("drivers", []))
    econ_card = (
        f'<div style="border:1px solid #d6cfc0;border-top:3px solid {_TEAL};'
        f'border-radius:4px;padding:12px 14px;background:#fff;">'
        f'<div style="font-size:13px;font-weight:700;color:{_TEAL};">'
        f'Home-infusion episode P&amp;L — {html.escape(ec.get("therapy",""))}'
        f'</div>'
        f'<div style="display:flex;gap:16px;margin:8px 0;flex-wrap:wrap;">'
        f'<div><div style="font-size:9px;color:{_FAINT};letter-spacing:0.06em;'
        f'font-weight:700;">REVENUE</div><div style="font-size:17px;'
        f'font-weight:700;color:#1a2332;">{_money(ec.get("revenue",0))}</div>'
        f'</div>'
        f'<div><div style="font-size:9px;color:{_FAINT};letter-spacing:0.06em;'
        f'font-weight:700;">CONTRIBUTION</div><div style="font-size:17px;'
        f'font-weight:700;color:{_POS};">{_money(ec.get("contribution",0))}'
        f' <span style="font-size:11px;color:{_DIM};">'
        f'({ec.get("contribution_margin",0)*100:.0f}%)</span></div></div>'
        f'</div>{drivers}'
        f'<div style="margin-top:8px;padding:7px 10px;background:#eef5f4;'
        f'border-left:3px solid {_TEAL};border-radius:0 3px 3px 0;'
        f'font-size:11px;color:#1a2332;line-height:1.5;">'
        f'<strong>Margin lever:</strong> {html.escape(ec.get("lever",""))}'
        f'</div>'
        f'<p style="font-size:9px;color:{_FAINT};margin:6px 0 0;">'
        f'{html.escape(ec.get("note",""))}</p></div>')

    # Therapy / condition reference table with TX eligible estimates.
    trows = ""
    for t in hi.get("therapies", []):
        tone = _HI_TONE.get(t["key"], _FAINT)
        est = conds.get(t["key"], {}).get("estimated_patients")
        est_s = f'{est:,}' if est is not None else "—"
        trows += (
            f'<tr style="border-bottom:1px solid #e4ddca;">'
            f'<td style="padding:6px 8px;vertical-align:top;">'
            f'<span style="display:inline-block;width:9px;height:9px;'
            f'border-radius:2px;background:{tone};margin-right:5px;"></span>'
            f'<strong>{html.escape(t["therapy"])}</strong></td>'
            f'<td style="padding:6px 8px;font-size:11px;color:{_DIM};'
            f'vertical-align:top;">{html.escape(t["conditions"])}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'vertical-align:top;font-weight:700;color:{tone};">{est_s}'
            f'<div style="font-size:9px;color:{_FAINT};font-weight:400;">'
            f'{t["epi_per_100k"]:.0f}/100k</div></td>'
            f'<td style="padding:6px 8px;font-size:11px;color:{_DIM};'
            f'vertical-align:top;">{html.escape(t["regimen"])}</td>'
            f'<td style="padding:6px 8px;font-size:11px;color:{_DIM};'
            f'vertical-align:top;">{html.escape(t["why_home"])}</td>'
            f'</tr>')
    therapy_table = (
        f'<div style="overflow-x:auto;"><table style="width:100%;'
        f'border-collapse:collapse;font-size:12px;">'
        f'<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        f'<th style="text-align:left;padding:6px 8px;">Therapy</th>'
        f'<th style="text-align:left;padding:6px 8px;">Conditions served</th>'
        f'<th style="text-align:right;padding:6px 8px;">TX eligible/yr</th>'
        f'<th style="text-align:left;padding:6px 8px;">Regimen</th>'
        f'<th style="text-align:left;padding:6px 8px;">Why home</th>'
        f'</tr></thead><tbody>{trows}</tbody></table></div>'
        f'<p style="font-size:9.5px;color:{_FAINT};margin:6px 0 0;">'
        f'TX eligible/yr = published treated-prevalence / incidence rate '
        f'(per 100k) × real TX population — labeled epidemiology anchors '
        f'(IDSA OPAT; Immune Deficiency Foundation; ASPEN; NHF; rare-'
        f'disease registries). Counts vary by real population, not '
        f'invented rates.</p>')

    # Network roster.
    nrows = ""
    for n in hi.get("networks", []):
        tt = _HI_TIER_TONE.get(n["tier"], _FAINT)
        tx = ('<span style="color:%s;font-weight:700;">TX ✓</span>' % _POS
              if n["tx"] else '<span style="color:%s;">—</span>' % _FAINT)
        name = (f'<a href="{html.escape(n["link"], quote=True)}" '
                f'target="_blank" rel="noopener" style="color:{_NAVY};'
                f'font-weight:600;text-decoration:none;">'
                f'{html.escape(n["name"])} ↗</a>' if n.get("link") else
                f'<strong>{html.escape(n["name"])}</strong>')
        nrows += (
            f'<tr>'
            f'<td style="padding:6px 8px;">{name}</td>'
            f'<td style="padding:6px 8px;"><span style="font-size:10px;'
            f'font-weight:700;color:{tt};">{html.escape(n["tier"])}</span></td>'
            f'<td style="padding:6px 8px;font-size:11px;color:{_DIM};">'
            f'{html.escape(n["ownership"])}</td>'
            f'<td style="padding:6px 8px;text-align:center;">{tx}</td>'
            f'<td style="padding:6px 8px;font-size:11px;color:{_DIM};">'
            f'{html.escape(n["focus"])}</td>'
            f'<td style="padding:6px 8px;font-size:10px;color:{_FAINT};">'
            f'{html.escape(n["accred"])}</td>'
            f'</tr>')
    network_table = (
        f'<div style="overflow-x:auto;"><table style="width:100%;'
        f'border-collapse:collapse;font-size:12px;">'
        f'<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        f'<th style="text-align:left;padding:6px 8px;">Network</th>'
        f'<th style="text-align:left;padding:6px 8px;">Tier</th>'
        f'<th style="text-align:left;padding:6px 8px;">Ownership</th>'
        f'<th style="padding:6px 8px;">TX</th>'
        f'<th style="text-align:left;padding:6px 8px;">Focus</th>'
        f'<th style="text-align:left;padding:6px 8px;">Accreditation</th>'
        f'</tr></thead><tbody>{nrows}</tbody></table></div>'
        f'<p style="font-size:9.5px;color:{_FAINT};margin:6px 0 0;">'
        f'Payer-owned networks (Optum, Paragon/Elevance) can steer their '
        f'own members — a competitive threat to independents. The '
        f'franchise / independent pool is the fragmented roll-up target. '
        f'Accreditation (ACHC / URAC) is table-stakes for payer contracts.'
        f'</p>')

    # Reimbursement HIT-gap explainer.
    reim = hi.get("reimbursement", {})
    rpts = "".join(
        f'<div style="padding:7px 0;border-bottom:1px solid #e4ddca;">'
        f'<div style="font-size:12px;font-weight:600;color:#1a2332;">'
        f'{html.escape(p["label"])}</div>'
        f'<div style="font-size:11.5px;color:{_DIM};line-height:1.5;'
        f'margin-top:2px;">{html.escape(p["detail"])}</div></div>'
        for p in reim.get("points", []))
    reim_block = (
        f'<p style="font-size:12px;color:{_DIM};line-height:1.6;margin:0 0 6px;">'
        f'{html.escape(reim.get("summary",""))}</p>{rpts}'
        f'<div style="margin-top:8px;padding:8px 11px;background:#eef5f4;'
        f'border-left:3px solid {_TEAL};border-radius:0 3px 3px 0;'
        f'font-size:11.5px;color:#1a2332;line-height:1.55;">'
        f'<strong style="color:{_TEAL};">RCM read: </strong>'
        f'{html.escape(reim.get("rcm_read",""))}</div>')

    return (
        f'<div style="display:grid;grid-template-columns:1.1fr 1fr;gap:18px;'
        f'align-items:start;">'
        f'<div>{therapy_table}</div><div>{econ_card}</div></div>'
        f'<div style="font-size:10px;color:{_FAINT};letter-spacing:0.06em;'
        f'font-weight:700;margin:16px 0 5px;">THE NETWORKS — NATIONAL, '
        f'PAYER-OWNED, SPECIALIST &amp; THE TX ROLL-UP POOL</div>'
        f'{network_table}'
        f'<div style="font-size:10px;color:{_FAINT};letter-spacing:0.06em;'
        f'font-weight:700;margin:16px 0 5px;">REIMBURSEMENT — THE MEDICARE '
        f'HIT BENEFIT &amp; ITS GAP</div>{reim_block}')


def _home_infusion_block(dd: Dict[str, Any]) -> str:
    """Per-metro home-infusion-eligible demand by therapy (ranked bars)."""
    rows = dd.get("home_infusion", [])
    if not rows:
        return ""
    mx = max((r["estimated_patients"] for r in rows), default=1) or 1
    bars = ""
    for r in rows:
        w = r["estimated_patients"] / mx * 100
        tone = _HI_TONE.get(r["key"], _FAINT)
        bars += (
            f'<div style="display:grid;grid-template-columns:1fr 70px;'
            f'align-items:center;gap:8px;margin:3px 0;">'
            f'<div><div style="font-size:11px;color:#1a2332;">'
            f'{html.escape(r["therapy"])}</div>'
            f'<div style="height:10px;background:#ece5d6;border-radius:2px;'
            f'overflow:hidden;margin-top:2px;"><div style="height:100%;'
            f'width:{w:.0f}%;background:{tone};"></div></div></div>'
            f'<div style="font-size:11px;font-weight:700;color:{tone};'
            f'text-align:right;">{r["estimated_patients"]:,}</div></div>')
    return (
        f'<div style="margin-top:10px;"><div style="font-size:10px;'
        f'color:{_FAINT};letter-spacing:0.06em;margin-bottom:3px;">'
        f'HOME-INFUSION-ELIGIBLE PATIENTS/YR BY THERAPY (real pop × '
        f'published epidemiology)</div>{bars}</div>')


# Risk-heat scale 1 (low) → 5 (high).
_RISK_SCALE = {1: "#0a8a5f", 2: "#5a9e6f", 3: "#b8732a",
               4: "#cf5a2e", 5: "#b5321e"}
_RISK_BAND_TONE = {"HIGH": _NEG, "ELEVATED": _WARN, "MODERATE": _TEAL}


def _readmit_tone(pct: float) -> str:
    return _NEG if pct >= 20 else _WARN if pct >= 12 else _POS


def _home_discharge_section(a: Dict[str, Any]) -> str:
    """The home-infusion discharge pipeline + therapy-volume risk: annual
    referral flow by therapy, the five-axis risk heatmap (most-at-risk
    ranked), and the referral-source concentration read."""
    hi = a.get("home_infusion") or {}
    disch = hi.get("tx_discharges", [])
    risk = hi.get("therapy_risk", {})
    refs = hi.get("referral_sources", {})
    if not disch or not risk:
        return ""

    # Discharge / referral-flow table.
    drows = ""
    for d in disch:
        tone = _HI_TONE.get(d["key"], _FAINT)
        rt = _readmit_tone(d["readmission_pct"])
        drows += (
            f'<tr style="border-bottom:1px solid #e4ddca;">'
            f'<td style="padding:6px 8px;"><span style="display:inline-block;'
            f'width:9px;height:9px;border-radius:2px;background:{tone};'
            f'margin-right:5px;"></span><strong>{html.escape(d["therapy"])}'
            f'</strong></td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'font-weight:700;color:{tone};">{d["annual_referrals"]:,}'
            f'<div style="font-size:9px;color:{_FAINT};font-weight:400;">'
            f'{d["flow_per_100k"]:.0f}/100k</div></td>'
            f'<td style="padding:6px 8px;font-size:11px;color:{_DIM};">'
            f'{html.escape(d["source"])}</td>'
            f'<td class="num" style="padding:6px 8px;text-align:right;'
            f'font-weight:700;color:{rt};">{d["readmission_pct"]:.0f}%</td>'
            f'</tr>')
    flow_table = (
        f'<div style="overflow-x:auto;"><table style="width:100%;'
        f'border-collapse:collapse;font-size:12px;">'
        f'<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        f'<th style="text-align:left;padding:6px 8px;">Therapy</th>'
        f'<th style="text-align:right;padding:6px 8px;">TX referrals/yr</th>'
        f'<th style="text-align:left;padding:6px 8px;">Discharge / referral '
        f'source</th>'
        f'<th style="text-align:right;padding:6px 8px;">30-day readmit</th>'
        f'</tr></thead><tbody>{drows}</tbody></table></div>'
        f'<p style="font-size:9.5px;color:{_FAINT};margin:6px 0 0;">'
        f'Referrals/yr = published new-start / discharge incidence (per '
        f'100k) × real TX population — the demand FLOW the channel '
        f'captures, distinct from the standing eligible pool. Readmission '
        f'anchors from OPAT / HPN / HF cohort studies (re-hospitalized '
        f'patients stop billing — the leakage to underwrite).</p>')

    # Risk heatmap, ranked most-at-risk first.
    axes = ["reimbursement", "steerage", "referral_concentration",
            "clinical", "supply"]
    axhead = "".join(
        f'<th style="padding:4px 5px;font-size:9px;font-weight:700;'
        f'color:{_FAINT};writing-mode:horizontal-tb;text-align:center;">'
        f'{html.escape(risk["axis_labels"][ax].split(" ")[0])}</th>'
        for ax in axes)
    rrows = ""
    for r in risk["therapies"]:
        bt = _RISK_BAND_TONE.get(r["band"], _FAINT)
        cells = "".join(
            f'<td style="padding:4px 5px;text-align:center;">'
            f'<span style="display:inline-block;width:22px;height:18px;'
            f'line-height:18px;border-radius:3px;background:{_RISK_SCALE[v]};'
            f'color:#fff;font-size:10px;font-weight:700;">{v}</span></td>'
            for v in (r["axes"][ax] for ax in axes))
        rrows += (
            f'<tr style="border-bottom:1px solid #e4ddca;">'
            f'<td style="padding:5px 8px;"><strong style="color:{bt};">'
            f'#{r["rank"]}</strong> {html.escape(r["therapy"])}'
            f'<div style="font-size:9.5px;color:{_FAINT};">lead: '
            f'{html.escape(r["lead_risk"])}</div></td>'
            f'{cells}'
            f'<td class="num" style="padding:5px 8px;text-align:right;'
            f'font-weight:700;color:{bt};">{r["overall_pct"]}'
            f'<div style="font-size:9px;font-weight:700;color:{bt};">'
            f'{html.escape(r["band"])}</div></td>'
            f'</tr>')
    heatmap = (
        f'<div style="overflow-x:auto;"><table style="width:100%;'
        f'border-collapse:collapse;font-size:12px;">'
        f'<thead><tr style="border-bottom:2px solid #c9c1ac;">'
        f'<th style="text-align:left;padding:4px 8px;">Therapy (most at '
        f'risk first)</th>{axhead}'
        f'<th style="padding:4px 8px;text-align:right;">At-risk</th>'
        f'</tr></thead><tbody>{rrows}</tbody></table></div>'
        f'<p style="font-size:9.5px;color:{_FAINT};margin:6px 0 0;">'
        f'Five-axis diligence framework (1 low → 5 high): Reimbursement · '
        f'Steerage · Referral-concentration · Clinical · Supply. At-risk = '
        f'weighted blend (×20). {html.escape(risk.get("note", ""))}</p>')

    # Referral-source concentration.
    src_bars = ""
    for s in refs.get("sources", []):
        w = s["share"] * 100
        src_bars += (
            f'<div style="display:grid;grid-template-columns:230px 1fr 44px;'
            f'align-items:center;gap:8px;margin:3px 0;">'
            f'<div style="font-size:11px;color:#1a2332;">'
            f'{html.escape(s["source"])}</div>'
            f'<div style="height:13px;background:#ece5d6;border-radius:2px;'
            f'overflow:hidden;"><div style="height:100%;width:{w:.0f}%;'
            f'background:{_NAVY};"></div></div>'
            f'<div style="font-size:11px;font-weight:700;color:{_NAVY};'
            f'text-align:right;">{w:.0f}%</div></div>')
    ref_block = (
        f'{src_bars}'
        f'<div style="margin-top:8px;padding:8px 11px;background:#fbf3ef;'
        f'border-left:3px solid {_NEG};border-radius:0 3px 3px 0;'
        f'font-size:11.5px;color:#1a2332;line-height:1.55;">'
        f'<strong style="color:{_NEG};">Concentration risk: </strong>'
        f'{html.escape(refs.get("concentration_risk", ""))}</div>'
        f'<div style="margin-top:6px;padding:8px 11px;background:#eef5f4;'
        f'border-left:3px solid {_TEAL};border-radius:0 3px 3px 0;'
        f'font-size:11.5px;color:#1a2332;line-height:1.55;">'
        f'<strong style="color:{_TEAL};">RCM read: </strong>'
        f'{html.escape(refs.get("rcm_read", ""))}</div>')

    return (
        f'<div style="font-size:10px;color:{_FAINT};letter-spacing:0.06em;'
        f'font-weight:700;margin:0 0 5px;">ANNUAL REFERRAL FLOW BY THERAPY '
        f'+ READMISSION LEAKAGE</div>{flow_table}'
        f'<div style="font-size:10px;color:{_FAINT};letter-spacing:0.06em;'
        f'font-weight:700;margin:16px 0 5px;">WHAT&#39;S MOST AT RISK — '
        f'THERAPY-VOLUME RISK HEATMAP</div>{heatmap}'
        f'<div style="font-size:10px;color:{_FAINT};letter-spacing:0.06em;'
        f'font-weight:700;margin:16px 0 5px;">REFERRAL-SOURCE '
        f'CONCENTRATION — THE COMMERCIAL FRAGILITY</div>{ref_block}')


def _home_discharge_block(dd: Dict[str, Any]) -> str:
    """Per-metro annual home-infusion referral flow by therapy."""
    rows = dd.get("home_infusion_discharges", [])
    if not rows:
        return ""
    mx = max((r["annual_referrals"] for r in rows), default=1) or 1
    bars = ""
    for r in rows:
        w = r["annual_referrals"] / mx * 100
        tone = _HI_TONE.get(r["key"], _FAINT)
        rt = _readmit_tone(r["readmission_pct"])
        bars += (
            f'<div style="display:grid;grid-template-columns:1fr 100px;'
            f'align-items:center;gap:8px;margin:3px 0;">'
            f'<div><div style="font-size:11px;color:#1a2332;">'
            f'{html.escape(r["therapy"])}</div>'
            f'<div style="height:10px;background:#ece5d6;border-radius:2px;'
            f'overflow:hidden;margin-top:2px;"><div style="height:100%;'
            f'width:{w:.0f}%;background:{tone};"></div></div></div>'
            f'<div style="text-align:right;"><span style="font-size:11px;'
            f'font-weight:700;color:{tone};">{r["annual_referrals"]:,}</span>'
            f'<span style="font-size:9px;color:{rt};"> · {r["readmission_pct"]:.0f}%↩</span>'
            f'</div></div>')
    return (
        f'<div style="margin-top:10px;"><div style="font-size:10px;'
        f'color:{_FAINT};letter-spacing:0.06em;margin-bottom:3px;">'
        f'ANNUAL HOME-INFUSION REFERRALS/YR BY THERAPY (new starts · '
        f'↩ 30-day readmit)</div>{bars}</div>')


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
        + _home_infusion_block(dd)
        + _home_discharge_block(dd)
        + _county_capacity_table(dd)
        # White-space
        + f'<div style="margin-top:10px;padding:8px 12px;background:#fff;'
        f'border-left:3px solid {_WARN};border-radius:0 3px 3px 0;">'
        f'<div style="font-size:10px;color:{_WARN};font-weight:700;'
        f'letter-spacing:0.06em;margin-bottom:3px;">EARLY / WHITESPACE '
        f'SUBURBS — demand with thin local capacity</div>'
        f'<ul style="margin:0;padding-left:18px;">{ws}</ul></div>'
        f'</div>')


def _so_what(text: str, tone: str = _TEAL) -> str:
    """A scannable 'SO WHAT' takeaway callout — the diligence implication
    of the section it follows. Distinct from source / RCM-read notes."""
    return (
        f'<div style="margin:11px 0 2px;padding:9px 13px;background:#eef5f4;'
        f'border-left:4px solid {tone};border-radius:0 4px 4px 0;">'
        f'<span style="font-size:9px;font-weight:800;letter-spacing:0.11em;'
        f'color:{tone};vertical-align:1px;">SO WHAT</span> '
        f'<span style="font-size:12px;color:#1a2332;line-height:1.55;">'
        f'{html.escape(text)}</span></div>')


def _so_whats(a: Dict[str, Any]) -> Dict[str, str]:
    """Build the per-section takeaways from REAL analysis values so each
    'so what' recomputes from the data it summarizes."""
    s = a["sizing"]
    frag = a["fragmentation"]
    hi = a["home_infusion"]
    ec = hi["episode_economics"]
    risk = hi["therapy_risk"]
    refs = hi["referral_sources"]
    disch = {d["key"]: d for d in hi["tx_discharges"]}
    opat = disch.get("opat", {}).get("annual_referrals", 0)
    aic = a["aic_economics"]
    curve = a["aic_utilization_curve"]
    ma = a["ma_enrollment"]
    sc = a["growth_scorecard"]
    pm = a["provider_map"]
    site = {x["site"]: x["share"] for x in a["site_of_care"]}
    home = site.get("Home infusion", 0)
    ais = site.get("Ambulatory infusion suite (AIS)", 0)
    hopd = next((v for k, v in site.items() if "HOPD" in k
                 or "Hospital" in k), 0)
    commercial = next((p["share"] for p in a["payer_mix"]
                       if "Commercial" in p["payer"]), 0)
    top_metro = a["metros"][0]
    centers = sum(p["estimated_centers"] for p in pm["points"])
    us = ", ".join(r["county"] for r in
                   sc["undersupplied_growth_markets"][:3])
    seg_seg = a["provider_segments"]
    rollup_pool = sum(x["share"] for x in seg_seg
                      if x["non_hospital"] and "Independent" in x["segment"]
                      or x["segment"].startswith("Physician"))
    return {
        "sizing": (
            f"A {_money(s['tam'])} TAM growing {s['composite_cagr_pct']:.1f}%/yr "
            f"with {_money(s['sam'])} addressable (home + AIC) is platform-"
            f"scale — but the CAGR depends on the site-of-care shift, so "
            f"underwrite the demand chain and steerage, not the headline."),
        "channels": (
            f"Home ({home*100:.0f}%) + AIS ({ais*100:.0f}%) = "
            f"{(home+ais)*100:.0f}% of volume already sits outside the "
            f"hospital; the {hopd*100:.0f}% HOPD pool is white-space to "
            f"capture by steerage, not a competitor to displace."),
        "home": (
            f"IG + rare-disease are the margin engine; the Medicare HIT "
            f"calendar-day gap under-pays the rest, so the home channel "
            f"only makes money on a strong COMMERCIAL mix — that's the "
            f"first number to diligence."),
        "discharge": (
            f"~{opat:,} OPAT referrals/yr are the volume engine, but "
            f"{refs['hospital_dependence']*100:.0f}% of referrals flow "
            f"through hospital discharge desks — referral concentration is "
            f"the #1 commercial risk, while {risk['most_at_risk'].split('/')[0].strip()} "
            f"and IG/biologics carry the reimbursement + steerage risk."),
        "players": (
            f"No operator holds more than {frag['top_operator_share']*100:.0f}% "
            f"nationally — the real competitive threat is payer-owned "
            f"steerage (Optum, Paragon/Elevance), not a scale incumbent."),
        "segments": (
            f"~{rollup_pool*100:.0f}% of capacity is the fragmented "
            f"independent + physician-owned roll-up pool; the health-"
            f"system-owned third is captive (not for sale) — that split "
            f"defines the acquirable universe."),
        "cdc": (
            "Real county prevalence (not just headcount) localizes demand "
            "— CKD / diabetes / arthritis concentrations flag exactly "
            "where IV-iron, chronic and immunology volume clusters."),
        "aic": (
            f"At ~{_money(aic['contribution_per_chair'])} contribution/"
            f"chair and break-even near {curve['breakeven_util']*100:.0f}% "
            f"utilization, chair throughput + commercial mix make or break "
            f"the unit — de-novo ramps below break-even bleed cash."),
        "denovo": (
            f"A new center costs ~{_money(a['aic_denovo_ramp']['capex_total'])} "
            f"to build and reaches cash break-even around month "
            f"{a['aic_denovo_ramp']['breakeven_month']}, returning "
            f"~{a['aic_denovo_ramp']['y3_cash_on_cash']:.1f}x cash-on-cash by "
            f"year 3 — a fast-payback de-novo engine that, with the no-CON "
            f"runway, can out-pace bolt-on multiples."),
        "asp": (
            f"The drug spread is thin and policy-set (ASP + "
            f"{a['asp_pricing']['addon_sequestered']*100:.1f}%); the real "
            f"margin is GPO acquisition cost vs the payment limit — and "
            f"white-bagging can erase it entirely."),
        "site": (
            f"The {hopd*100:.0f}% HOPD pool migrating to AIS/home is the "
            f"growth engine — back operators positioned to RECEIVE the "
            f"steered volume, not defend a chair."),
        "regulatory": (
            f"{a['regulatory_environment']['tailwinds']} tailwinds vs "
            f"{a['regulatory_environment']['headwinds']} headwinds: policy "
            f"pushes VOLUME to the platform's site (site-neutral + HIT "
            f"benefit) but squeezes the DRUG SPREAD (IRA, biosimilars, "
            f"340B, white-bagging). Texas's no-CON rule is a structural "
            f"tailwind — underwrite on service margin + commercial mix, "
            f"not the drug."),
        "evolution": (
            f"Infusion has moved {a['site_of_care_evolution']['hopd_shift_pts']} "
            f"points out of the hospital since 2015 (HOPD "
            f"{a['site_of_care_evolution']['soc_start']['hopd']*100:.0f}%→"
            f"{a['site_of_care_evolution']['soc_end']['hopd']*100:.0f}%) while "
            f"the market compounded "
            f"{a['site_of_care_evolution']['market_cagr_pct']:.1f}%/yr — COVID "
            f"+ the HIT benefit + payer steerage made the discharge shift "
            f"structural, not cyclical. Underwrite it continuing."),
        "providers": (
            f"~{centers} estimated infusion centers across the four metros, "
            f"fragmented and un-consolidated — the supply side has not "
            f"rolled up, leaving the runway open."),
        "map": (
            f"Supply concentrates in DFW + Houston; relative to growth, "
            f"Austin and San Antonio are thinner — the white-space metros "
            f"for de-novo or tuck-in entry."),
        "jcode_pos": (
            f"Texas runs ~{a['jcode_pos']['texas']['nonfac_pct']*100:.0f}% "
            f"of infusion J-code volume non-facility (office/AIC), #"
            f"{a['jcode_pos']['texas']['rank']} of "
            f"{len(a['jcode_pos']['states'])} — a structurally favorable "
            f"site mix (low rural, high MA) that hands the AIC roll-up its "
            f"runway. The national facility→non-facility drift keeps "
            f"widening it."),
        "metro": (
            f"{top_metro['metro'].split('-')[0]} ranks #1 on attractiveness "
            f"({top_metro['attractiveness']:.0f}), but DFW carries the most "
            f"supply — match entry strategy to each metro's demand-vs-"
            f"supply balance, not a single ranking."),
        "scorecard": (
            f"{sc['n_undersupplied']} north / Austin-corridor counties "
            f"({us}…) show demand outrunning AIS chair capacity — the "
            f"priority de-novo and tuck-in targets."),
        "concentration": (
            f"HHI {frag['hhi']:,.0f} with the largest operator at "
            f"{frag['top_operator_share']*100:.0f}% and a "
            f"{frag['independent_pool_share']*100:.0f}% independent pool is "
            f"a textbook roll-up runway — no incumbent can block a build-up."),
        "payer": (
            f"Commercial-heavy ({commercial*100:.0f}%) funds the economics, "
            f"but {ma['enrollment']/1e6:.1f}M MA lives "
            f"({ma.get('penetration',0)*100:.0f}% of total Medicare) are "
            f"steering site-of-care and gating biologics — payer mix is "
            f"the swing factor on margin."),
        "demographics": (
            "The 65+ tailwind is real, but TX's highest-in-US uninsured "
            "rate and rural spread complicate home economics outside the "
            "four metros — stay metro-clustered."),
        "growth": (
            "Site-of-care migration — not population growth alone — carries "
            "the forecast; the thesis lives or dies on steerage to AIS/home "
            "continuing."),
    }


_SEC_RE = re.compile(
    r'(<header class="ck-section-header">)(.*?<h2 class="sc-h2">)([^<]+)',
    re.S)


def _inject_section_nav(body: str) -> Tuple[str, str]:
    """Post-process the assembled body: give each section header an id
    and build a floating 'jump to section' navigator. The page has ~25
    sections — a partner needs to move around it."""
    items: List[Tuple[str, str]] = []
    seen: Dict[str, int] = {}

    def _repl(m: "re.Match") -> str:
        title = html.unescape(m.group(3)).strip()
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or "sec"
        if slug in seen:
            seen[slug] += 1
            slug = f"{slug}-{seen[slug]}"
        else:
            seen[slug] = 0
        items.append((title, slug))
        return (f'{m.group(1)[:-1]} id="{slug}" '
                f'style="scroll-margin-top:70px;">{m.group(2)}{m.group(3)}')

    body = _SEC_RE.sub(_repl, body)
    if not items:
        return body, ""
    links = "".join(
        f'<a href="#{s}" style="display:block;padding:4px 12px;'
        f'font-size:12px;color:#1a2332;text-decoration:none;'
        f'border-bottom:1px solid #efe9dc;">{html.escape(t)}</a>'
        for t, s in items)
    nav = (
        '<details style="position:fixed;right:18px;bottom:18px;z-index:50;'
        'font-family:\'Inter Tight\',system-ui,sans-serif;">'
        '<summary style="list-style:none;cursor:pointer;background:#0b2341;'
        'color:#fff;padding:8px 14px;border-radius:20px;font-size:12px;'
        'font-weight:600;box-shadow:0 2px 8px rgba(0,0,0,0.18);">'
        '☰ Sections</summary>'
        '<div style="position:absolute;right:0;bottom:40px;width:248px;'
        'max-height:60vh;overflow-y:auto;background:#fff;border:1px solid '
        '#c9c1ac;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,0.18);'
        f'">{links}</div></details>')
    return body, nav


def render_texas_infusion_page(
    qs: "Dict[str, Any] | None" = None,
) -> str:
    """Render the full Texas infusion diligence page. ``qs`` carries
    optional AIC assumption overrides (clamped server-side)."""
    from ..diligence.texas_infusion import (
        aic_assumptions_from_qs, build_texas_infusion_analysis,
    )
    overrides = aic_assumptions_from_qs(qs or {})
    # Live NPPES provider count is opt-in (?nppes=live) so a normal
    # render never blocks on the NPI Registry.
    _nppes = (qs or {}).get("nppes")
    nppes_live = (_nppes == "live"
                  or (isinstance(_nppes, list) and "live" in _nppes))
    a = build_texas_infusion_analysis(
        aic_overrides=overrides, nppes_live=nppes_live)
    demo = a["demographics"]
    sw = _so_whats(a)

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
        + _thesis_section(a)

        + ck_section_header("Market sizing — the driver chain",
                            eyebrow="TAM / SAM / SOM")
        + _sizing_chain(a)
        + _so_what(sw["sizing"])

        + ck_section_header("The two channels — AIC vs home infusion",
                            eyebrow="REIMBURSEMENT · MARGIN · WORKING CAPITAL")
        + _channel_cards(a)
        + _so_what(sw["channels"])

        + ck_section_header("Home infusion — therapies, networks & "
                            "reimbursement",
                            eyebrow="OPAT · IG · TPN · INOTROPES · RARE · "
                                    "THE HIT BENEFIT GAP")
        + _home_infusion_section(a)
        + _so_what(sw["home"])

        + ck_section_header("Home-infusion discharge pipeline & therapy "
                            "risk",
                            eyebrow="REFERRAL FLOW · READMISSION LEAKAGE · "
                                    "WHAT'S MOST AT RISK")
        + _home_discharge_section(a)
        + _so_what(sw["discharge"], _NEG)

        + ck_section_header("Players — the named operators",
                            eyebrow="WHO COMPETES · OWNERSHIP · TX PRESENCE")
        + _players_table(a)
        + _so_what(sw["players"])

        + ck_section_header("Competitive dynamics — capacity by owner",
                            eyebrow="NATIONAL/REGIONAL · HEALTH-SYSTEM · "
                                    "PHYSICIAN · INDEPENDENT AIC · HOME")
        + _provider_segments_section(a)
        + _so_what(sw["segments"])

        + ck_section_header("CDC public-health demand proxies",
                            eyebrow="PLACES + ACS → THERAPY DEMAND · LIVE API "
                                    "WITH OFFLINE FALLBACK")
        + _cdc_proxies_section(a)
        + _so_what(sw["cdc"])

        + ck_section_header("Regulatory & reimbursement environment",
                            eyebrow="PART B/D · HIT BENEFIT · IRA · "
                                    "BIOSIMILARS · 340B · SITE-NEUTRAL · TEXAS")
        + _regulatory_section(a)
        + _so_what(sw["regulatory"])

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
        + _so_what(sw["aic"])

        + ck_section_header("De-novo AIC build — the J-curve",
                            eyebrow="CAPEX · RAMP · CASH BREAK-EVEN · "
                                    "YEAR-3 CASH-ON-CASH · EDITABLE")
        + _denovo_section(a)
        + _so_what(sw["denovo"])

        + ck_section_header("Part B drug pricing — ASP buy-and-bill",
                            eyebrow="CMS ASP+6 (SEQ. +4.3%) · INFUSION J-CODES "
                                    "· LIVE ASP FILE")
        + _asp_pricing_section(a)
        + _so_what(sw["asp"])

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
        + _hopd_pool_section(a)
        + _so_what(sw["site"])

        + ck_section_header("How discharges → home infusion have evolved",
                            eyebrow="SITE-OF-CARE MIGRATION OVER TIME · "
                                    "2015–2024 · EVENT TIMELINE")
        + _evolution_section(a)
        + _so_what(sw["evolution"])

        + ck_section_header("Provider landscape & competitiveness",
                            eyebrow="COUNTS · CAPACITY · FRAGMENTATION")
        + _provider_panel(a)
        + _so_what(sw["providers"])

        + ck_section_header("Infusion-provider map",
                            eyebrow="NPPES NPI REGISTRY · SUPPLY BY METRO")
        + _provider_map_section(a)
        + _so_what(sw["map"])

        + ck_section_header("J-code place of service by state",
                            eyebrow="CMS PART B · FACILITY vs NON-FACILITY · "
                                    "MAP + 3-YR TREND")
        + _jcode_pos_section(a)
        + _so_what(sw["jcode_pos"])

        + ck_section_header("Metro attractiveness ranking",
                            eyebrow="HOUSTON · DFW · AUSTIN · SAN ANTONIO")
        + _metro_table(a)
        + _so_what(sw["metro"])

        + ck_section_header("City deep-dives",
                            eyebrow="AGE-BAND DEMAND · SUBURBS · OPERATORS · "
                                    "WHITESPACE")
        + "".join(_city_section(dd) for dd in a["metro_deepdives"])

        + ck_section_header("Texas growth scorecard",
                            eyebrow="COUNTY OPPORTUNITY RANKING · WHERE DEMAND "
                                    "OUTRUNS CAPACITY")
        + _scorecard_section(a)
        + _so_what(sw["scorecard"], _NEG)

        + ck_section_header("Concentration — operator landscape",
                            eyebrow="HHI · FRAGMENTATION → ROLL-UP")
        + _concentration(a)
        + _so_what(sw["concentration"])

        + ck_section_header("Payer mix",
                            eyebrow="COMMERCIAL-HEAVY · TX NON-EXPANSION · MA "
                                    "STEERAGE")
        + _payer_section(a)
        + _ma_enrollment_panel(a)
        + _so_what(sw["payer"])

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
        + _so_what(sw["demographics"])

        + ck_section_header("Five-year growth drivers",
                            eyebrow="WHICH LEVER CARRIES THE GROWTH")
        + _growth_drivers(a)
        + _so_what(sw["growth"])

        + ck_section_header("Texas structural factors",
                            eyebrow="WHAT'S DIFFERENT ABOUT TEXAS")
        + _factors(a)

        + ck_section_header("One-page exhibit",
                            eyebrow="AUTO-COMPOSED FROM THE LIVE ANALYSIS · "
                                    "DECK-READY · SVG/PNG")
        + _exhibit_section(a)

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
    body, section_nav = _inject_section_nav(body)
    body = body + section_nav + ck_page_actions()
    return chartis_shell(
        body, "Texas Infusion Market",
        active_nav="/diligence",
        subtitle=f"TAM {_money(a['sizing']['tam'])} · HHI {a['hhi']:,.0f}",
    )
