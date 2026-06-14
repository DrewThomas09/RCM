"""J-Code Atlas — the page for ``diligence.jcode_atlas``.

Scans every infusion J-code by site of care (home / office / ambulatory
suite / HOPD), shows THE CHANGE (the 2018→now home / out-of-hospital
migration) code by code, and ties each code to its disease + the size of
the patient pool it serves. The "scan infusion codes by home vs in
office and the change", made concrete per HCPCS code.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List

from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_page_title, ck_source_purpose,
)

_NAVY = "#0b2341"
_TEAL = "#1F7A75"
_NEG = "#b5321e"
_POS = "#0a8a5f"
_WARN = "#b8732a"
_DIM = "#465366"
_FAINT = "#7a8699"
_SERIF = ("'Source Serif 4', 'Iowan Old Style', Georgia, "
          "'Times New Roman', serif")

# Site-of-care palette — out-of-hospital sites in greens/teals, HOPD in
# the warning amber (the share being steered away).
_SITE_COLOR = {"home": "#0a8a5f", "office": "#1F7A75",
               "aic": "#7bbcb5", "hopd": "#b8732a"}
_SITE_LABEL = {"home": "Home", "office": "Office", "aic": "Amb. suite",
               "hopd": "HOPD"}


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
                 f'{mix.get(s,0)*100:.0f}%</title></rect>')
        x += w
    return (f'<svg width="{width}" height="11" viewBox="0 0 {width} 11" '
            f'role="img" style="border-radius:2px;overflow:hidden;">'
            f'{segs}</svg>')


def _shift_bar(pts: float, scale: float = 1.4) -> str:
    """A diverging bar centered on zero for a +/- percentage-point change.
    Green right (gaining out-of-hospital), amber left (back to hospital)."""
    half = 46.0
    w = min(half, abs(pts) * scale)
    color = _POS if pts >= 0 else _WARN
    sign = "+" if pts > 0 else ""
    if pts >= 0:
        rect = (f'<rect x="{half:.1f}" y="0" width="{w:.1f}" height="10" '
                f'fill="{color}" rx="1"/>')
    else:
        rect = (f'<rect x="{half-w:.1f}" y="0" width="{w:.1f}" height="10" '
                f'fill="{color}" rx="1"/>')
    return (
        f'<span style="display:inline-flex;align-items:center;gap:5px;">'
        f'<svg width="{half*2:.0f}" height="10" viewBox="0 0 {half*2:.0f} 10">'
        f'<line x1="{half:.0f}" y1="0" x2="{half:.0f}" y2="10" '
        f'stroke="#d8d0bf" stroke-width="1"/>{rect}</svg>'
        f'<span class="num" style="color:{color};font-weight:700;'
        f'font-size:10.5px;min-width:34px;">{sign}{pts:.1f}</span></span>')


def _legend() -> str:
    items = "".join(
        f'<span style="display:inline-flex;align-items:center;gap:4px;'
        f'margin-right:12px;"><span style="width:10px;height:10px;'
        f'background:{_SITE_COLOR[s]};border-radius:2px;display:inline-block;">'
        f'</span><span style="font-size:10.5px;color:{_DIM};">'
        f'{_SITE_LABEL[s]}</span></span>'
        for s in ("home", "office", "aic", "hopd"))
    return f'<div style="margin:4px 0 10px;">{items}</div>'


def _book_change_panel(summary: Dict[str, Any], then_year: int,
                       now_year: int) -> str:
    """The whole-book home/office/AIC/HOPD mix now vs then + the change."""
    now, then = summary["book_mix_now"], summary["book_mix_then"]
    chg = summary["book_change_pts"]
    rows = ""
    for s in ("home", "office", "aic", "hopd"):
        c = chg[s]
        ccolor = _POS if c > 0 else _WARN if c < 0 else _FAINT
        sign = "+" if c > 0 else ""
        rows += (
            f'<tr style="border-bottom:1px solid #ece5d6;">'
            f'<td style="padding:3px 8px;"><span style="width:9px;height:9px;'
            f'background:{_SITE_COLOR[s]};border-radius:2px;display:inline-'
            f'block;margin-right:6px;"></span>{_SITE_LABEL[s]}</td>'
            f'<td class="num" style="padding:3px 8px;text-align:right;'
            f'color:{_FAINT};">{then[s]*100:.0f}%</td>'
            f'<td class="num" style="padding:3px 8px;text-align:right;'
            f'font-weight:700;color:{_NAVY};">{now[s]*100:.0f}%</td>'
            f'<td class="num" style="padding:3px 8px;text-align:right;'
            f'font-weight:700;color:{ccolor};">{sign}{c:.1f}</td></tr>')
    return (
        f'<div style="border:1px solid #e2dac8;border-radius:5px;'
        f'padding:11px 13px;background:#fcfaf5;">'
        f'<div style="font-size:11px;color:{_FAINT};text-transform:uppercase;'
        f'letter-spacing:.06em;margin-bottom:6px;">Whole-book site-of-care '
        f'mix · demand-weighted</div>'
        f'<table style="width:100%;border-collapse:collapse;font-size:12px;">'
        f'<thead><tr style="color:{_FAINT};border-bottom:2px solid #d8cfb9;">'
        f'<th style="text-align:left;padding:3px 8px;">Site</th>'
        f'<th style="text-align:right;padding:3px 8px;">{then_year}</th>'
        f'<th style="text-align:right;padding:3px 8px;">{now_year}</th>'
        f'<th style="text-align:right;padding:3px 8px;">Δ pts</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>')


def _movers_panel(summary: Dict[str, Any]) -> str:
    movers = summary["top_movers"]
    items = ""
    for m in movers:
        ooh = m["out_of_hospital_pts"]
        items += (
            f'<li style="margin-bottom:5px;line-height:1.4;">'
            f'<span class="num" style="font-weight:700;color:{_TEAL};">'
            f'{html.escape(m["hcpcs"])}</span> '
            f'<span style="color:#1a2332;">{html.escape(m["drug"])}</span> '
            f'<span class="num" style="color:{_POS};font-weight:700;">'
            f'+{ooh:.0f} pts</span> '
            f'<span style="color:{_FAINT};font-size:10.5px;">out of '
            f'hospital</span></li>')
    return (
        f'<div style="border:1px solid #e2dac8;border-radius:5px;'
        f'padding:11px 13px;background:#fcfaf5;">'
        f'<div style="font-size:11px;color:{_FAINT};text-transform:uppercase;'
        f'letter-spacing:.06em;margin-bottom:6px;">Biggest site-of-care '
        f'movers</div><ol style="margin:0;padding-left:18px;font-size:12px;">'
        f'{items}</ol></div>')


def _scan_table(scan: List[Dict[str, Any]]) -> str:
    rows = ""
    for r in scan:
        bio = (f' <span style="color:{_WARN};font-weight:700;font-size:8.5px;'
               f'border:1px solid {_WARN};border-radius:2px;padding:0 3px;" '
               f'title="Biosimilar — ASP-erosion / drug-margin risk">BIOSIM'
               f'</span>') if r["biosimilar"] else ""
        asp = r.get("asp_payment_limit_per_unit")
        asp_cell = (f'${asp:,.2f}' if asp is not None
                    else f'<span style="color:{_FAINT};">ASP+6%</span>')
        dz = ", ".join(r["diseases"][:2])
        if len(r["diseases"]) > 2:
            dz += f' +{len(r["diseases"])-2}'
        now = r["site_mix_now"]
        rows += (
            f'<tr style="border-bottom:1px solid #ece5d6;">'
            f'<td class="num" style="padding:4px 8px;font-weight:700;'
            f'color:{_TEAL};white-space:nowrap;">{html.escape(r["hcpcs"])}'
            f'{bio}</td>'
            f'<td style="padding:4px 8px;">'
            f'<div style="font-weight:600;color:#1a2332;">'
            f'{html.escape(r["drug"])}</div>'
            f'<div style="font-size:10px;color:{_FAINT};">'
            f'{html.escape(r["drug_class"])}</div></td>'
            f'<td style="padding:4px 8px;font-size:11px;color:{_DIM};">'
            f'{html.escape(dz)}</td>'
            f'<td style="padding:4px 8px;">{_site_bar(now)}'
            f'<div style="font-size:9.5px;color:{_FAINT};">'
            f'home {now["home"]*100:.0f}% · office {now["office"]*100:.0f}% '
            f'· AIC {now["aic"]*100:.0f}% · HOPD {now["hopd"]*100:.0f}%</div>'
            f'</td>'
            f'<td style="padding:4px 8px;">'
            f'{_shift_bar(r["out_of_hospital_pts"])}</td>'
            f'<td class="num" style="padding:4px 8px;text-align:right;'
            f'color:#1a2332;">{r["estimated_patients"]:,}</td>'
            f'<td class="num" style="padding:4px 8px;text-align:right;'
            f'font-size:11px;">{asp_cell}</td></tr>')
    return (
        f'<table style="width:100%;border-collapse:collapse;font-size:12px;">'
        f'<thead><tr style="border-bottom:2px solid #c9c1ac;color:{_FAINT};'
        f'font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;">'
        f'<th style="text-align:left;padding:4px 8px;">J-code</th>'
        f'<th style="text-align:left;padding:4px 8px;">Drug / class</th>'
        f'<th style="text-align:left;padding:4px 8px;">Disease</th>'
        f'<th style="text-align:left;padding:4px 8px;">Site of care (now)</th>'
        f'<th style="text-align:left;padding:4px 8px;">Δ out-of-hospital</th>'
        f'<th style="text-align:right;padding:4px 8px;">Est. pts</th>'
        f'<th style="text-align:right;padding:4px 8px;">ASP/unit</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>')


def _disease_table(diseases: List[Dict[str, Any]]) -> str:
    rows = ""
    for d in diseases[:24]:
        dom = d["dominant_site"]
        dom_html = (f'<span style="width:9px;height:9px;background:'
                    f'{_SITE_COLOR.get(dom, _FAINT)};border-radius:2px;'
                    f'display:inline-block;margin-right:5px;"></span>'
                    f'{_SITE_LABEL.get(dom, dom)}')
        ooh = d["out_of_hospital_pts"]
        ooh_color = _POS if ooh > 0 else _WARN if ooh < 0 else _FAINT
        bio = (f' <span style="color:{_WARN};font-size:8.5px;font-weight:700;">'
               f'◆</span>') if d["any_biosimilar"] else ""
        rows += (
            f'<tr style="border-bottom:1px solid #ece5d6;">'
            f'<td style="padding:3px 8px;font-weight:600;color:#1a2332;">'
            f'{html.escape(d["disease"])}{bio}</td>'
            f'<td class="num" style="padding:3px 8px;text-align:right;'
            f'color:{_FAINT};">{d["n_codes"]}</td>'
            f'<td style="padding:3px 8px;font-size:10.5px;color:{_DIM};'
            f'font-family:monospace;">{html.escape(", ".join(d["codes"][:4]))}'
            f'{"…" if len(d["codes"]) > 4 else ""}</td>'
            f'<td class="num" style="padding:3px 8px;text-align:right;'
            f'font-weight:700;color:{_NAVY};">{d["estimated_pool"]:,}</td>'
            f'<td style="padding:3px 8px;font-size:11px;">{dom_html}</td>'
            f'<td class="num" style="padding:3px 8px;text-align:right;'
            f'font-weight:700;color:{ooh_color};">'
            f'{"+" if ooh > 0 else ""}{ooh:.1f}</td></tr>')
    return (
        f'<table style="width:100%;border-collapse:collapse;font-size:12px;">'
        f'<thead><tr style="border-bottom:2px solid #c9c1ac;color:{_FAINT};'
        f'font-size:10.5px;text-transform:uppercase;letter-spacing:.04em;">'
        f'<th style="text-align:left;padding:3px 8px;">Disease</th>'
        f'<th style="text-align:right;padding:3px 8px;">Codes</th>'
        f'<th style="text-align:left;padding:3px 8px;">J-codes</th>'
        f'<th style="text-align:right;padding:3px 8px;">Est. pool</th>'
        f'<th style="text-align:left;padding:3px 8px;">Dominant site</th>'
        f'<th style="text-align:right;padding:3px 8px;">Δ OOH pts</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>')


def _opportunity_panel(summary: Dict[str, Any]) -> str:
    """Ranked home-shift roll-up targets — which J-codes are the best
    home/AIC acquisition candidates (demand × momentum × HOPD runway)."""
    rows = ""
    for i, o in enumerate(summary["top_opportunities"], start=1):
        bio = (f' <span style="color:{_WARN};font-size:8.5px;font-weight:700;'
               f'" title="Biosimilar — drug-margin penalty applied">◆</span>'
               ) if o["biosimilar"] else ""
        bar_w = max(2.0, min(100.0, o["score"]))
        rows += (
            f'<tr style="border-bottom:1px solid #ece5d6;">'
            f'<td class="num" style="padding:3px 6px;color:{_FAINT};">{i}</td>'
            f'<td class="num" style="padding:3px 6px;font-weight:700;'
            f'color:{_TEAL};white-space:nowrap;">{html.escape(o["hcpcs"])}'
            f'{bio}</td>'
            f'<td style="padding:3px 6px;font-size:11px;color:#1a2332;">'
            f'{html.escape(o["drug"])}</td>'
            f'<td style="padding:3px 6px;width:90px;">'
            f'<div style="background:#ece5d6;border-radius:2px;height:8px;'
            f'width:80px;"><div style="background:{_POS};height:8px;'
            f'border-radius:2px;width:{bar_w*0.8:.0f}px;"></div></div></td>'
            f'<td class="num" style="padding:3px 6px;text-align:right;'
            f'font-weight:700;color:{_NAVY};">{o["score"]:.0f}</td>'
            f'<td class="num" style="padding:3px 6px;text-align:right;'
            f'color:{_DIM};">{o["estimated_patients"]:,}</td></tr>')
    return (
        f'<div style="border:1px solid #e2dac8;border-radius:5px;'
        f'padding:11px 13px;background:#fcfaf5;">'
        f'<div style="font-size:11px;color:{_FAINT};text-transform:uppercase;'
        f'letter-spacing:.06em;margin-bottom:2px;">Home-shift roll-up '
        f'targets</div>'
        f'<div style="font-size:10px;color:{_FAINT};margin-bottom:6px;">'
        f'demand × migration momentum × HOPD runway · ◆ biosimilar haircut'
        f'</div>'
        f'<table style="width:100%;border-collapse:collapse;font-size:12px;">'
        f'<thead><tr style="color:{_FAINT};border-bottom:2px solid #d8cfb9;'
        f'font-size:10px;"><th style="text-align:left;padding:3px 6px;">#</th>'
        f'<th style="text-align:left;padding:3px 6px;">Code</th>'
        f'<th style="text-align:left;padding:3px 6px;">Drug</th>'
        f'<th style="text-align:left;padding:3px 6px;">Score</th>'
        f'<th style="text-align:right;padding:3px 6px;"></th>'
        f'<th style="text-align:right;padding:3px 6px;">Pool</th>'
        f'</tr></thead><tbody>{rows}</tbody></table></div>')


def _migration_scatter(scan: List[Dict[str, Any]]) -> str:
    """A 2×2 of patient pool (x, log) vs out-of-hospital migration (y) —
    the "where is the volume, and is it moving?" quadrant. Bubbles are
    colored by the dominant current site of care."""
    import math
    W, H = 540, 300
    ml, mr, mt, mb = 46, 14, 14, 34
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

    # Quadrant split at the median pool and the mean migration.
    x_mid = sorted(xs)[len(xs) // 2]
    y_mid = sum(ys) / len(ys)
    grid = (
        f'<line x1="{px(x_mid):.0f}" y1="{mt}" x2="{px(x_mid):.0f}" '
        f'y2="{mt+ph}" stroke="#d8cfb9" stroke-width="1" '
        f'stroke-dasharray="3,3"/>'
        f'<line x1="{ml}" y1="{py(y_mid):.0f}" x2="{ml+pw}" '
        f'y2="{py(y_mid):.0f}" stroke="#d8cfb9" stroke-width="1" '
        f'stroke-dasharray="3,3"/>')
    # The high-value quadrant (big pool, fast migration) gets a tint.
    hv = (f'<rect x="{px(x_mid):.0f}" y="{mt}" width="{ml+pw-px(x_mid):.0f}" '
          f'height="{py(y_mid)-mt:.0f}" fill="#0a8a5f" opacity="0.05"/>')
    dots = ""
    for r in scan:
        pool = max(1, r["estimated_patients"])
        cx = px(math.log10(pool))
        cy = py(r["out_of_hospital_pts"])
        dom = max(r["site_mix_now"], key=r["site_mix_now"].get)
        col = _SITE_COLOR.get(dom, _FAINT)
        rad = 3.0 + min(7.0, math.log10(pool))
        dots += (
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rad:.1f}" fill="{col}" '
            f'opacity="0.62" stroke="#fff" stroke-width="0.6">'
            f'<title>{html.escape(r["hcpcs"])} {html.escape(r["drug"])} — '
            f'{r["estimated_patients"]:,} pts, +{r["out_of_hospital_pts"]:.0f} '
            f'pts out of hospital</title></circle>')
    labels = (
        f'<text x="{ml+pw:.0f}" y="{mt+10:.0f}" text-anchor="end" '
        f'font-size="9.5" fill="{_POS}" font-weight="700">↑ migrating out '
        f'of hospital · ← bigger pool →</text>'
        f'<text x="{ml-4:.0f}" y="{mt+ph+22:.0f}" text-anchor="start" '
        f'font-size="9.5" fill="{_FAINT}">small pool</text>'
        f'<text x="{ml+pw:.0f}" y="{mt+ph+22:.0f}" text-anchor="end" '
        f'font-size="9.5" fill="{_FAINT}">large pool (log)</text>')
    return (
        f'<svg viewBox="0 0 {W} {H}" width="100%" style="max-width:560px;" '
        f'role="img" aria-label="J-code migration vs pool scatter">'
        f'{hv}{grid}{dots}{labels}</svg>')


def _footer_links(pop: "int | None", live: bool) -> str:
    """Export + cross-links to the sibling infusion surfaces."""
    import urllib.parse
    params = {}
    if pop:
        params["pop"] = str(pop)
    if live:
        params["live"] = "1"
    q = ("?" + urllib.parse.urlencode(params)) if params else ""
    csv_href = html.escape(f"/api/diligence/jcode-atlas/export.csv{q}",
                           quote=True)
    return (
        f'<div style="margin-top:16px;padding:10px 13px;background:#f3efe5;'
        f'border-radius:5px;display:flex;flex-wrap:wrap;gap:18px;'
        f'font-size:11.5px;align-items:center;">'
        f'<a href="{csv_href}" style="color:{_TEAL};font-weight:700;'
        f'text-decoration:none;">⬇ Export site-of-care scan (CSV)</a>'
        f'<span style="color:#cabfa6;">·</span>'
        f'<a href="/diligence/texas-infusion" style="color:{_NAVY};'
        f'font-weight:600;text-decoration:none;">Texas infusion deep-dive →'
        f'</a>'
        f'<a href="/diligence/infusion-markets" style="color:{_NAVY};'
        f'font-weight:600;text-decoration:none;">National market scan →</a>'
        f'</div>')


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
                 else f'{geo["population"]/1e6:.1f}M population')

    kpis = (
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);'
        'gap:12px;margin:14px 0;">'
        + ck_kpi_block("Infusion J-codes", f'{s["n_codes"]}',
                       f'{s["n_diseases"]} diseases tied')
        + ck_kpi_block(
            "Migrating out of hospital", f'{s["n_migrating_home"]}',
            f'of {s["n_codes"]} codes',
            f'+{s["out_of_hospital_gain_pts"]:.0f}')
        + ck_kpi_block(
            "Home + office now",
            f'{s["home_office_now"]*100:.0f}%',
            f'from {s["home_office_then"]*100:.0f}% in {then_year}',
            f'+{(s["home_office_now"]-s["home_office_then"])*100:.0f}')
        + ck_kpi_block(
            "Biosimilar / ASP-erosion", f'{s["n_biosimilar"]}',
            'codes flagged drug-margin risk')
        + '</div>')

    body = (
        ck_page_title(
            "J-Code Atlas — Site of Care &amp; Disease",
            eyebrow="DILIGENCE · INFUSION J-CODES",
            meta=(f'{s["n_codes"]} J-codes · {s["n_diseases"]} diseases · '
                  f'{then_year}→{now_year} site-of-care shift · {geo_label}'),
        )
        + ck_source_purpose(
            purpose="Scan every infusion J-code by site of care (home vs "
                    "office vs ambulatory suite vs HOPD), measure the "
                    "home-migration change, and tie each code to its disease.",
            universe="illustrative",
            source="HCPCS codes + descriptors (CMS); FDA-labeled "
                   "indications; published treated-prevalence anchors; "
                   "site-of-care mix = labeled NHIA/MedPAC archetype "
                   "anchors; ASP payment limits live from the CMS ASP file "
                   "where egress permits.",
        )
        + '<div class="ts-wrap" style="max-width:1180px;">'
        + kpis
        + '<div style="display:grid;grid-template-columns:1fr 1.2fr;gap:16px;'
          'align-items:start;margin-bottom:18px;">'
        + _book_change_panel(s, then_year, now_year)
        + _movers_panel(s)
        + '</div>'
        + f'<h2 style="font-family:{_SERIF};color:{_NAVY};font-size:17px;'
          f'margin:6px 0 2px;">Where is the volume — and is it moving?</h2>'
        + f'<p style="font-size:11.5px;color:{_DIM};margin:0 0 6px;">Each '
          f'J-code plotted by patient pool (x, log) vs out-of-hospital '
          f'migration (y). The shaded upper-right quadrant — big pool, fast '
          f'migration — is where a home/AIC platform competes hardest. '
          f'Bubbles colored by dominant site of care.</p>'
        + '<div style="display:grid;grid-template-columns:auto 1fr;gap:18px;'
          'align-items:start;margin-bottom:18px;">'
        + f'<div>{_migration_scatter(a["scan"])}{_legend()}</div>'
        + _opportunity_panel(s)
        + '</div>'
        + f'<h2 style="font-family:{_SERIF};color:{_NAVY};font-size:17px;'
          f'margin:6px 0 2px;">Site-of-care scan — by home vs office &amp; '
          f'the change</h2>'
        + f'<p style="font-size:11.5px;color:{_DIM};margin:0 0 4px;">Every '
          f'J-code ranked by how far it has moved OUT of the hospital '
          f'({then_year}→{now_year}). Δ out-of-hospital = points of share '
          f'gained by home + office + ambulatory suite.</p>'
        + _legend()
        + _scan_table(a["scan"])
        + f'<h2 style="font-family:{_SERIF};color:{_NAVY};font-size:17px;'
          f'margin:22px 0 2px;">J-codes tied to disease — the demand pool</h2>'
        + f'<p style="font-size:11.5px;color:{_DIM};margin:0 0 8px;">Each '
          f'disease, the J-codes that treat it, the infusion-eligible '
          f'patient pool ({geo_label}, real population × published epi), the '
          f'dominant site of care, and how fast its drugs are migrating home. '
          f'◆ = a biosimilar competes in the class.</p>'
        + _disease_table(a["diseases"])
        + _footer_links(pop, live)
        + f'<p style="font-size:10px;color:{_FAINT};margin-top:14px;'
          f'line-height:1.6;">{html.escape(a["note"])} '
          f'Pool = the largest single-code estimate per disease (brands of '
          f'one therapy overlap, so they are not summed). Append '
          f'<code>?pop=31000000</code> to scale pools to a market, or '
          f'<code>?live=1</code> for live ASP pricing.</p>'
        + '</div>')

    return chartis_shell(
        body, "J-Code Atlas", active_nav="/diligence",
        subtitle="Infusion J-codes · site of care &amp; disease")
