"""TAM / SAM / SOM Builder — /diligence/tam-sam.

Driver-tree market sizing the way CDD teams actually build it (see
diligence/tam_sam.py): an editable driver chain, segment bands, a TAM →
SAM → SOM funnel, a growth-driver-decomposed projection, and one-click
formatted exports (CSV + real .xlsx) so the output drops straight into
the deal team's model.

Every chain value is editable via the form (qs overrides the template
defaults); the audit trail renders the running value at every step — the
chain IS the methodology, shown, not hidden.
"""
from __future__ import annotations

import html
import urllib.parse
from typing import Any, Dict, List, Optional

from ..diligence.tam_sam import (
    TEMPLATES, TamSamModel, compute, fertility_ivf_template,
)
from ._chartis_kit import (
    chartis_shell, ck_kpi_block, ck_next_section, ck_page_title, ck_panel,
    ck_source_purpose,
)

_CSS = """
<style>
.ts2-chain{width:100%;border-collapse:collapse;font-size:13px;}
.ts2-chain th{font-family:var(--sc-mono);font-size:9.5px;letter-spacing:.12em;
 text-transform:uppercase;color:var(--sc-text-dim,#465366);text-align:left;
 padding:6px 10px;border-bottom:2px solid var(--sc-rule,#c9c1ac);}
.ts2-chain td{padding:7px 10px;border-bottom:1px solid var(--sc-rule,#e4ddcd);}
.ts2-chain .r{text-align:right;font-variant-numeric:tabular-nums;
 font-family:var(--sc-mono);}
.ts2-chain input{width:120px;padding:4px 7px;border:1px solid
 var(--sc-rule,#c9c1ac);border-radius:2px;font-size:12.5px;text-align:right;
 font-variant-numeric:tabular-nums;}
.ts2-src{font-size:10.5px;color:var(--sc-text-faint,#8b94a0);}
.ts2-run{font-weight:600;color:var(--sc-navy,#0b2341);}
.ts2-form-bar{display:flex;gap:10px;align-items:center;margin:12px 0 0;
 flex-wrap:wrap;}
.ts2-btn{padding:8px 16px;background:var(--sc-navy,#0b2341);color:#fff;
 border:0;border-radius:2px;font-size:12px;font-weight:600;cursor:pointer;}
.ts2-export{display:inline-flex;align-items:center;gap:6px;padding:7px 13px;
 border:1px solid var(--sc-rule,#c9c1ac);border-radius:2px;background:#fff;
 color:var(--sc-navy,#0b2341);font-size:12px;font-weight:600;
 text-decoration:none;}
.ts2-drv{display:flex;justify-content:space-between;gap:14px;padding:7px 2px;
 border-bottom:1px solid var(--sc-rule,#e4ddcd);font-size:12.5px;}
.ts2-drv .pct{font-family:var(--sc-mono);font-variant-numeric:tabular-nums;
 font-weight:600;}
.ts2-tmpl{display:flex;gap:8px;margin:0 0 14px;flex-wrap:wrap;}
.ts2-tmpl a{padding:6px 13px;border:1px solid var(--sc-rule,#c9c1ac);
 border-radius:2px;font-size:12px;text-decoration:none;
 color:var(--sc-text,#1a2332);}
.ts2-tmpl a.on{border-color:var(--sc-teal,#155752);
 color:var(--sc-teal-ink,#0f3d39);font-weight:600;}
</style>
"""


def _fmt_money(v: float) -> str:
    if abs(v) >= 1e9:
        return f"${v/1e9:,.2f}B"
    if abs(v) >= 1e6:
        return f"${v/1e6:,.1f}M"
    return f"${v:,.0f}"


def _fmt_step_value(st: Dict[str, Any]) -> str:
    if st["op"] == "rate":
        return f"{st['value']*100:,.2f}%"
    if st["op"] == "price":
        return f"${st['value']:,.0f}"
    # Plain decimal — :,.4g goes scientific on populations (3.66e+06).
    v = st["value"]
    return f"{int(v):,}" if float(v).is_integer() else f"{v:,.2f}"


def _fmt_running(st: Dict[str, Any]) -> str:
    # Once a price step lands, the running value is dollars.
    return (_fmt_money(st["running"]) if st["op"] == "price"
            else f"{st['running']:,.0f}")


def model_from_qs(qs: Dict[str, List[str]]) -> TamSamModel:
    """Resolve template + apply qs overrides (every chain value, sam/som
    shares, growth drivers — all clamped to sane ranges)."""
    def first(k: str, d: str = "") -> str:
        return (qs.get(k) or [d])[0].strip()

    tmpl_key = first("template", "fertility_ivf")
    factory = TEMPLATES.get(tmpl_key, fertility_ivf_template)
    model = factory()

    def fnum(k: str) -> Optional[float]:
        v = first(k)
        if not v:
            return None
        try:
            x = float(v.replace(",", "").replace("$", "").replace("%", ""))
        except ValueError:
            return None
        if x != x or x in (float("inf"), float("-inf")):
            return None
        return x

    for i, st in enumerate(model.chain):
        ov = fnum(f"step{i}")
        if ov is not None and ov >= 0:
            # Rates arrive as percent points from the form (2.3 → 0.023).
            st.value = ov / 100.0 if st.op == "rate" else ov
    sam = fnum("sam_share")
    if sam is not None:
        model.sam_share = max(0.0, min(100.0, sam)) / 100.0
    som = fnum("som_share")
    if som is not None:
        model.som_share = max(0.0, min(100.0, som)) / 100.0
    # Scenario presets — Conservative halves tailwinds and amplifies
    # headwinds ×1.5; Aggressive mirrors. Applied BEFORE the explicit
    # per-driver overrides so a typed value always wins.
    scenario = first("scenario", "base").lower()
    if scenario in ("conservative", "aggressive"):
        for g in model.growth_drivers:
            if scenario == "conservative":
                g.annual_pct = (g.annual_pct * 0.5 if g.annual_pct > 0
                                else g.annual_pct * 1.5)
            else:
                g.annual_pct = (g.annual_pct * 1.5 if g.annual_pct > 0
                                else g.annual_pct * 0.5)
    for i, g in enumerate(model.growth_drivers):
        ov = fnum(f"growth{i}")
        if ov is not None and -50.0 <= ov <= 100.0:
            g.annual_pct = ov
    return model


def _state_bar_svg(states: List[Dict[str, Any]], width: int = 560) -> str:
    """Horizontal bars: facilities by state; the independent slice (the
    acquirable pool) overlaid in teal so whitespace is visible at a
    glance. Inline SVG, house pattern."""
    if not states:
        return ""
    mx = max(s["facilities"] for s in states) or 1
    row_h, pad_l, pad_r = 22, 46, 110
    bar_w = width - pad_l - pad_r
    parts = [f'<svg width="{width}" height="{len(states)*row_h + 6}" '
             'xmlns="http://www.w3.org/2000/svg" role="img" '
             'aria-label="Facilities by state">']
    for i, s in enumerate(states):
        y = i * row_h + 4
        w = s["facilities"] / mx * bar_w
        w_ind = s["independent"] / mx * bar_w
        parts.append(
            f'<text x="{pad_l-6}" y="{y+11}" text-anchor="end" '
            'font-family="monospace" font-size="10.5" '
            f'fill="#465366">{html.escape(s["state"])}</text>'
            f'<rect x="{pad_l}" y="{y}" width="{w:.1f}" height="13" '
            'fill="#0b2341" opacity="0.85"/>'
            f'<rect x="{pad_l}" y="{y}" width="{w_ind:.1f}" height="13" '
            'fill="#1F7A75"/>'
            f'<text x="{pad_l+w+6:.1f}" y="{y+11}" font-family="monospace" '
            f'font-size="10" fill="#465366">{s["facilities"]:,} '
            f'({s["independent"]} indep)</text>'
        )
    parts.append('</svg>')
    return "".join(parts)


def _projection_svg(projection: List[Dict[str, Any]],
                    width: int = 640, height: int = 220) -> str:
    """TAM/SAM/SOM lines over the horizon — the IC's one-look growth
    picture. Inline SVG, house palette, end-value labels."""
    if len(projection) < 2:
        return ""
    pad_l, pad_r, pad_t, pad_b = 56, 110, 14, 26
    pw, ph = width - pad_l - pad_r, height - pad_t - pad_b
    mx = max(p["tam"] for p in projection) or 1
    n = len(projection) - 1
    series = [("TAM", "tam", "#0b2341"), ("SAM", "sam", "#1F7A75"),
              ("SOM", "som", "#a08227")]
    parts = [f'<svg width="{width}" height="{height}" '
             'xmlns="http://www.w3.org/2000/svg" role="img" '
             'aria-label="TAM SAM SOM projection">']
    for i, p in enumerate(projection):
        x = pad_l + i / n * pw
        parts.append(
            f'<text x="{x:.0f}" y="{height-8}" text-anchor="middle" '
            'font-family="monospace" font-size="9.5" fill="#7a8699">'
            f'Y{p["year"]}</text>')
    for label, key, color in series:
        pts = " ".join(
            f"{pad_l + i / n * pw:.1f},"
            f"{pad_t + (1 - p[key] / mx) * ph:.1f}"
            for i, p in enumerate(projection))
        y_end = pad_t + (1 - projection[-1][key] / mx) * ph
        parts.append(
            f'<polyline points="{pts}" fill="none" stroke="{color}" '
            'stroke-width="2"/>'
            f'<text x="{pad_l + pw + 6}" y="{y_end + 4:.1f}" '
            'font-family="monospace" font-size="10" '
            f'fill="{color}">{label} {_fmt_money(projection[-1][key])}'
            '</text>')
        y0 = pad_t + (1 - projection[0][key] / mx) * ph
        parts.append(f'<circle cx="{pad_l}" cy="{y0:.1f}" r="2.5" '
                     f'fill="{color}"/>')
    parts.append("</svg>")
    return "".join(parts)


def _sources_panel(out: Dict[str, Any],
                   dive: Optional[Dict[str, Any]]) -> str:
    """Numbered source footnotes — every default in the build traces to a
    named public source. The defensibility layer: an IC member (or a
    trainee) can check any number against where it came from."""
    items: List[str] = []
    seen = set()
    for st in out["steps"]:
        if st["source"] and st["source"] not in seen:
            seen.add(st["source"])
            items.append(f'{html.escape(st["name"])} — '
                         f'{html.escape(st["source"])}')
    for g in out["growth_drivers"]:
        if g["note"] and g["note"] not in seen:
            seen.add(g["note"])
            items.append(f'{html.escape(g["name"])} (growth driver) — '
                         f'{html.escape(g["note"])}')
    if dive:
        for k in ("facility_source", "quality_source"):
            v = dive.get(k)
            if v and v not in seen:
                seen.add(v)
                items.append(html.escape(v))
    if out.get("basis_note"):
        items.append(html.escape(out["basis_note"]))
    lis = "".join(
        f'<li style="margin:0 0 6px;"><span style="font-family:'
        f'var(--sc-mono);color:#7a8699;">[{i+1}]</span> {t}</li>'
        for i, t in enumerate(items))
    return ck_panel(
        f'<ol style="list-style:none;margin:0;padding:0;font-size:12px;'
        f'line-height:1.5;color:#465366;">{lis}</ol>',
        title="Sources & footnotes · every default traces to a named "
              "public source",
    )


def _industry_panels(tmpl_key: str) -> str:
    """Real-data deep-dive panels under the sizing build (additive — the
    registry decides which industries have a data layer yet)."""
    from ..diligence.industry_deep_dive import deep_dive_for
    dive = deep_dive_for(tmpl_key)
    if not dive:
        return ""
    if dive.get("deals_only"):
        # No vendored facility file for this vertical — geography is
        # omitted rather than fabricated; the deal history is real.
        sd = dive["sector_deals"]
        if not sd.get("n"):
            return ""
        med = sd.get("median_moic")
        mult = sd.get("median_entry_multiple")
        yrs = (f", {sd['year_min']}–{sd['year_max']}"
               if sd.get("year_min") else "")
        med_s = f"{med:.2f}x" if med else "—"
        mult_s = f"{mult:.1f}x" if mult else "—"
        return ck_panel(
            f'<p class="ck-section-body" style="margin:0 0 8px;">'
            f'<strong>{sd["n"]} corpus deals</strong> '
            f'({sd.get("n_realized", 0)} realized{yrs}) · '
            f'median realized MOIC <strong>{med_s}</strong> · '
            f'median entry EV/EBITDA <strong>{mult_s}</strong> · '
            f'<a class="ck-link" href="{html.escape(dive["deals_href"])}">'
            'open the deals →</a></p>'
            f'<p class="ts2-src" style="margin:0;">'
            f'{html.escape(dive.get("geo_note", ""))}</p>',
            title="What this sector traded for",
        )
    pool_label = dive.get("pool_label", "Independent")
    cap_label = dive.get("capacity_label")
    q_label = dive.get("quality_label", "Quality (med)")
    # The payer dimension — present when the dive computes it (hospitals:
    # filed Medicare day share, state median from HCRIS).
    has_payer = any(s.get("medicare_mix_med") is not None
                    for s in dive["top_states"])
    # 1 · State footprint — top 10 states with the whitespace overlay.
    rows = ""
    for s in dive["top_states"]:
        q = dive["quality_by_state"].get(s["state"]) or {}
        qv = q.get("value")
        qs_s = (f"{qv:,.1f}" if qv is not None and qv < 100
                else f"{qv:,.0f}" if qv is not None else "—")
        cap_td = (f'<td class="r">{s["stations"]:,}</td>'
                  if cap_label else "")
        mm = s.get("medicare_mix_med")
        payer_td = (
            f'<td class="r">{mm*100:,.0f}%</td>' if has_payer and
            mm is not None else ('<td class="r">—</td>' if has_payer
                                 else "")
        )
        rows += (
            '<tr>'
            f'<td>{html.escape(s["state"])}</td>'
            f'<td class="r">{s["facilities"]:,}</td>'
            f'{cap_td}'
            f'<td class="r">{s["independent"]:,}</td>'
            f'<td class="r">{s["independent_share"]*100:,.0f}%</td>'
            f'{payer_td}'
            f'<td class="r">{qs_s}</td></tr>'
        )
    footprint = ck_panel(
        '<div style="display:grid;grid-template-columns:minmax(0,1fr) '
        'minmax(0,1fr);gap:24px;align-items:start;">'
        f'<div>{_state_bar_svg(dive["top_states"])}'
        '<p class="ts2-src" style="margin:8px 0 0;">Navy = all '
        f'facilities · teal = {html.escape(dive.get("pool_note", "the pool"))}. '
        f'{html.escape(dive["facility_source"])}.</p></div>'
        '<table class="ts2-chain"><thead><tr>'
        '<th>State</th><th style="text-align:right;">Facilities</th>'
        + (f'<th style="text-align:right;">{html.escape(cap_label)}</th>'
           if cap_label else "")
        + f'<th style="text-align:right;">{html.escape(pool_label)}</th>'
        f'<th style="text-align:right;">{html.escape(pool_label)} share</th>'
        + ('<th style="text-align:right;">Medicare mix (med)</th>'
           if has_payer else "")
        + f'<th style="text-align:right;">{html.escape(q_label)}</th>'
        f'</tr></thead><tbody>{rows}</tbody></table>'
        '</div>'
        f'<p class="ts2-src" style="margin:10px 0 0;">'
        f'{html.escape(dive["quality_source"])}. '
        f'<a class="ck-link" href="{html.escape(dive["screener_href"])}">'
        'Open the screener for this vertical →</a></p>',
        title=f"State footprint · top 10 of {dive['n_facilities']:,} "
              "facilities (live CMS data)",
    )
    # 2 · Consolidation + whitespace.
    chain_rows = "".join(
        '<tr>'
        f'<td>{html.escape(c["org"])}</td>'
        f'<td class="r">{c["facilities"]:,}</td>'
        f'<td class="r">{c["share"]*100:,.1f}%</td></tr>'
        for c in dive["chains"]
    )
    if dive.get("whitespace_mode") == "density":
        ws = ", ".join(
            f'{s["state"]} ({s["per_10k_seniors"]:.1f}/10K)'
            for s in dive["whitespace_states"][:5])
    else:
        ws = ", ".join(
            f'{s["state"]} ({s["independent"]})'
            for s in dive["whitespace_states"][:5])
    duo = dive.get("duopoly_share")
    duo_bit = (
        f'Top-2 chains hold <strong>{duo*100:,.0f}%</strong> of '
        'facilities; ' if duo else ""
    )
    # Chain-concentration HHI (DOJ/FTC scale) — the standard read on how
    # consolidated the operator layer is. <1500 unconcentrated · 1500–
    # 2500 moderate · >2500 highly concentrated.
    from ..diligence.industry_deep_dive import _chain_hhi
    # HHI only means something over named OPERATORS (chains_label
    # "Chain"); ownership-type / size-tier buckets aren't operators.
    hhi = (_chain_hhi(dive["chains"], dive.get("pool_label", "Independent"))
           if dive.get("chains_label") == "Chain" else None)
    hhi_bit = ""
    if hhi is not None:
        band = ("highly concentrated" if hhi > 2500
                else "moderately concentrated" if hhi >= 1500
                else "unconcentrated")
        tone = ("#b5321e" if hhi > 2500 else "#b8732a" if hhi >= 1500
                else "#0a8a5f")
        hhi_bit = (
            f' Chain-concentration <strong style="color:{tone};">HHI '
            f'{hhi:,.0f}</strong> ({band}, DOJ/FTC scale — named '
            'operators only).'
        )
    consolidation = ck_panel(
        '<table class="ts2-chain"><thead><tr>'
        f'<th>{html.escape(dive.get("chains_label", "Chain"))}</th>'
        '<th style="text-align:right;">Facilities</th>'
        '<th style="text-align:right;">Share</th>'
        f'</tr></thead><tbody>{chain_rows}</tbody></table>'
        f'<p class="ck-section-body" style="margin:12px 0 0;">'
        f'{duo_bit}<strong>{dive["n_independent"]:,} '
        f'{html.escape(pool_label.lower())}</strong> — '
        f'{html.escape(dive.get("pool_note", ""))}.{hhi_bit} Whitespace '
        f'({html.escape(dive.get("whitespace_note", ""))}): '
        f'<strong>{html.escape(ws)}</strong>.</p>',
        title="Consolidation map · who owns the market",
    )
    # 3 · What the sector traded for.
    sd = dive["sector_deals"]
    deals_band = ""
    if sd.get("n"):
        med = sd.get("median_moic")
        mult = sd.get("median_entry_multiple")
        yrs = (f", {sd['year_min']}–{sd['year_max']}"
               if sd.get("year_min") else "")
        med_s = f"{med:.2f}x" if med else "—"
        mult_s = f"{mult:.1f}x" if mult else "—"
        deals_band = ck_panel(
            f'<p class="ck-section-body" style="margin:0;">'
            f'<strong>{sd["n"]} corpus deals</strong> '
            f'({sd.get("n_realized", 0)} realized{yrs}) · '
            f'median realized MOIC <strong>{med_s}</strong> · '
            f'median entry EV/EBITDA <strong>{mult_s}</strong> · '
            f'<a class="ck-link" href="{html.escape(dive["deals_href"])}">'
            'open the deals →</a></p>',
            title="What this sector traded for",
        )
    return footprint + consolidation + deals_band


def _tornado_panel(model: TamSamModel, tam: float) -> str:
    """±20% driver sensitivity — which assumption moves the answer.
    Horizontal low–high bars around the base TAM, sorted by impact."""
    from ..diligence.tam_sam import sensitivity
    rows = sensitivity(model)
    if not rows or tam <= 0:
        return ""
    width, row_h, pad_l, pad_r = 640, 26, 230, 96
    pw = width - pad_l - pad_r
    lo_all = min(r["tam_low"] for r in rows)
    hi_all = max(r["tam_high"] for r in rows)
    span = (hi_all - lo_all) or 1
    parts = [f'<svg width="{width}" height="{len(rows)*row_h + 22}" '
             'xmlns="http://www.w3.org/2000/svg" role="img" '
             'aria-label="Driver sensitivity tornado">']
    x_base = pad_l + (tam - lo_all) / span * pw
    parts.append(
        f'<line x1="{x_base:.1f}" y1="4" x2="{x_base:.1f}" '
        f'y2="{len(rows)*row_h + 8}" stroke="#7a8699" '
        'stroke-dasharray="3,3" stroke-width="1"/>')
    for i, r in enumerate(rows):
        y = i * row_h + 12
        x_lo = pad_l + (r["tam_low"] - lo_all) / span * pw
        x_hi = pad_l + (r["tam_high"] - lo_all) / span * pw
        parts.append(
            f'<text x="{pad_l-8}" y="{y+5}" text-anchor="end" '
            'font-family="sans-serif" font-size="11" fill="#1a2332">'
            f'{html.escape(r["name"][:32])}</text>'
            f'<rect x="{x_lo:.1f}" y="{y-6}" '
            f'width="{max(2, x_hi-x_lo):.1f}" height="12" '
            'fill="#1F7A75" opacity="0.75"/>'
            f'<text x="{x_hi+6:.1f}" y="{y+5}" font-family="monospace" '
            'font-size="9.5" fill="#465366">'
            f'{_fmt_money(r["tam_low"])}\u2013{_fmt_money(r["tam_high"])}'
            '</text>')
    parts.append('</svg>')
    return ck_panel(
        "".join(parts)
        + '<p class="ts2-src" style="margin:8px 0 0;">Each bar swings '
        'ONE driver \u00b120% (rates clamped at 100%) holding the rest at '
        'base \u2014 dashed line = base TAM. Sorted by impact: the top bar '
        'is the assumption to pressure-test first.</p>',
        title="Driver sensitivity \u00b7 \u00b120% tornado",
    )


def _industry_comparison_panel(active_key: str) -> str:
    """Every sized vertical side by side — TAM × growth, sorted by size.
    The cross-industry view: where the biggest pieces are, and where
    they grow fastest. Each row links into its build."""
    from ..diligence.tam_sam import TEMPLATES, compute as _compute
    rows = []
    for key, factory in TEMPLATES.items():
        if key == "blank":
            continue
        try:
            o = _compute(factory())
        except Exception:  # noqa: BLE001
            continue
        rows.append((key, o["name"], o["tam"], o["composite_cagr_pct"]))
    rows.sort(key=lambda r: -r[2])
    max_tam = rows[0][2] if rows else 1
    trs = ""
    for key, name, tam, cagr in rows:
        short = name.split("·")[0].strip()
        on = ' style="background:var(--sc-bone,#ece5d6);"' if key == active_key else ""
        bar_w = max(2, tam / max_tam * 160)
        tone = "#0a8a5f" if cagr >= 4 else ("#b5321e" if cagr < 0 else "#1a2332")
        trs += (
            f'<tr{on}>'
            f'<td><a href="/diligence/tam-sam?template={key}" '
            f'style="color:var(--sc-navy,#0b2341);font-weight:600;'
            f'text-decoration:none;">{html.escape(short)}</a></td>'
            f'<td class="r">{_fmt_money(tam)}</td>'
            f'<td><svg width="170" height="12">'
            f'<rect x="0" y="1" width="{bar_w:.0f}" height="10" '
            f'fill="#0b2341" opacity="0.8"/></svg></td>'
            f'<td class="r" style="color:{tone};font-weight:600;">'
            f'{cagr:+.1f}%/yr</td></tr>'
        )
    return ck_panel(
        '<table class="ts2-chain"><thead><tr>'
        '<th>Vertical</th><th style="text-align:right;">TAM</th>'
        '<th>Relative size</th>'
        '<th style="text-align:right;">Composite growth</th>'
        f'</tr></thead><tbody>{trs}</tbody></table>'
        '<p class="ts2-src" style="margin:8px 0 0;">Template defaults — '
        'each row opens its full build (chain, segments, tornado, state '
        'data where a CMS file is vendored). Green ≥4%/yr · red = '
        'declining.</p>',
        title="Cross-industry view · where the biggest pieces grow "
              "fastest",
    )


def _dive_for_sources(tmpl_key: str) -> Optional[Dict[str, Any]]:
    from ..diligence.industry_deep_dive import deep_dive_for
    return deep_dive_for(tmpl_key)


def render_tam_sam_page(qs: Optional[Dict[str, List[str]]] = None) -> str:
    qs = qs or {}
    model = model_from_qs(qs)
    out = compute(model)
    tmpl_key = (qs.get("template") or ["fertility_ivf"])[0]

    title = ck_page_title(
        "TAM / SAM Builder",
        eyebrow="DILIGENCE · MARKET SIZING",
        meta=(f"{html.escape(out['name'])} · TAM {_fmt_money(out['tam'])} · "
              f"{out['composite_cagr_pct']:+.1f}%/yr composite"),
    )
    src = ck_source_purpose(
        purpose=("Build the market-sizing driver tree the IC expects — "
                 "population → utilization → price chain, segment bands, "
                 "TAM→SAM→SOM funnel, growth-driver-decomposed projection "
                 "— and export it formatted."),
        universe="template + your overrides",
        confidence="illustrative",
        source=("Template defaults from public data (per-step source "
                "labels). Replace with engagement data before IC use."),
        next_action="Drop the export into the deal model",
        next_href="#ts2-export",
    )

    scenario = (qs.get("scenario") or ["base"])[0].lower()
    if scenario not in ("conservative", "base", "aggressive"):
        scenario = "base"
    scen_bar = (
        '<div class="ts2-tmpl" style="margin:0 0 10px;">'
        '<span class="ts2-src" style="align-self:center;'
        'margin-right:4px;text-transform:uppercase;letter-spacing:.1em;">'
        'Scenario</span>'
        + "".join(
            f'<a href="/diligence/tam-sam?template={html.escape(tmpl_key)}'
            f'&scenario={s}" class="{"on" if s == scenario else ""}">'
            f'{s.title()}</a>'
            for s in ("conservative", "base", "aggressive"))
        + '<span class="ts2-src" style="align-self:center;">'
        'Conservative halves tailwinds / amplifies headwinds; '
        'Aggressive mirrors. Typed driver values always win.</span>'
        '</div>'
    )
    tmpl_bar = (
        '<div class="ts2-tmpl">'
        + "".join(
            f'<a href="/diligence/tam-sam?template={k}" '
            f'class="{"on" if k == tmpl_key else ""}">{html.escape(lbl)}</a>'
            for k, lbl in (("fertility_ivf", "Fertility · IVF"),
                           ("dialysis", "Dialysis · in-center"),
                           ("home_health", "Home health"),
                           ("hospice", "Hospice"),
                           ("snf", "SNF · nursing"),
                           ("irf", "IRF · rehab"),
                           ("ltch", "LTCH"),
                           ("behavioral_health", "Behavioral health"),
                           ("asc", "ASC · surgery"),
                           ("physician_group", "Physician groups"),
                           ("dental", "Dental · DSO"),
                           ("oncology", "Oncology"),
                           ("urgent_care", "Urgent care"),
                           ("hospitals", "Hospitals"),
                           ("infusion", "Infusion"),
                           ("imaging", "Imaging"),
                           ("physical_therapy", "Physical therapy"),
                           ("veterinary", "Veterinary"),
                           ("medspa", "Medspa"),
                           ("ems", "EMS"),
                           ("clinical_labs", "Clinical labs"),
                           ("specialty_pharmacy", "Specialty Rx"),
                           ("vision", "Vision"),
                           ("aba", "ABA · autism"),
                           ("plasma", "Plasma"),
                           ("clinical_research", "Research sites"),
                           ("wound_care", "Wound care"),
                           ("sleep", "Sleep"),
                           ("occ_health", "Occ health"),
                           ("dermatology", "Dermatology"),
                           ("pain_management", "Pain mgmt"),
                           ("hospital_at_home", "Hospital-at-home"),
                           ("ltc_pharmacy", "LTC pharmacy"),
                           ("dme", "DME"),
                           ("idd_services", "IDD services"),
                           ("eating_disorders", "Eating disorders"),
                           ("nephrology", "Nephrology"),
                           ("orthotics_prosthetics", "O&P"),
                           ("ophthalmology", "Ophthalmology"),
                           ("rcm_services", "RCM services"),
                           ("cardiology", "Cardiology"),
                           ("gastroenterology", "GI"),
                           ("orthopedics", "Orthopedics"),
                           ("womens_health", "Women's health"),
                           ("podiatry", "Podiatry"),
                           ("ent_allergy", "ENT & allergy"),
                           ("anesthesia", "Anesthesia"),
                           ("home_care", "Home care"),
                           ("pace", "PACE"),
                           ("teleradiology", "Teleradiology"),
                           ("correctional_health", "Correctional"),
                           ("locum_staffing", "Locum staffing"),
                           ("crisis_services", "Crisis services"),
                           ("school_services", "School services"),
                           ("mobile_diagnostics", "Mobile dx"),
                           ("palliative", "Palliative"),
                           ("senior_living", "Senior living"),
                           ("vascular_access", "Vascular access"),
                           ("genetic_testing", "Genetic testing"),
                           ("nemt", "NEMT"),
                           ("compounding_503b", "503B compounding"),
                           ("lop_medicine", "LOP medicine"),
                           ("dental_labs", "Dental labs"),
                           ("htm_clinical_engineering", "HTM"),
                           ("interpretation", "Interpretation"),
                           ("urology", "Urology"),
                           ("rheumatology", "Rheumatology"),
                           ("neurology", "Neurology"),
                           ("endocrinology_obesity", "Endo · obesity"),
                           ("pulmonology", "Pulmonology"),
                           ("transplant_services", "Transplant svcs"),
                           ("retail_clinics", "Retail clinics"),
                           ("surgical_assist", "Surgical assist"),
                           ("hit_consulting", "HIT consulting"),
                           ("hospitalist", "Hospitalist"),
                           ("perfusion", "Perfusion"),
                           ("sterile_processing", "Sterile processing"),
                           ("air_medical", "Air medical"),
                           ("pediatric_home_health", "Pediatric PDN"),
                           ("roi_services", "ROI services"),
                           ("virtual_primary_care", "Virtual primary"),
                           ("rpm", "RPM"),
                           ("care_navigation", "Care navigation"),
                           ("blank", "Blank scaffold")))
        + '</div>'
    )

    funnel = (
        '<div class="ck-kpi-grid" style="grid-template-columns:repeat(4,1fr);'
        'gap:8px;margin:0 0 16px;">'
        + ck_kpi_block("TAM", _fmt_money(out["tam"]), "full driver chain")
        + ck_kpi_block(
            "SAM", _fmt_money(out["sam"]),
            f"{out['sam_share']*100:.0f}% addressable")
        + ck_kpi_block(
            "SOM", _fmt_money(out["som"]),
            f"{out['som_share']*100:.0f}% of SAM obtainable")
        + ck_kpi_block(
            "Composite growth", f"{out['composite_cagr_pct']:+.1f}%/yr",
            f"{len(out['growth_drivers'])} named drivers")
        + '</div>'
    )

    # Editable chain — the audit trail IS the form.
    chain_rows = ""
    for i, st in enumerate(out["steps"]):
        # Plain decimal in the form — :g renders 3660000 as "3.66e+06",
        # which reads as a formula, not a population. The parser strips
        # commas on the way back in.
        if st["op"] == "rate":
            form_val = f"{st['value']*100:g}"
        elif float(st["value"]).is_integer():
            form_val = f"{int(st['value']):,}"
        else:
            form_val = f"{st['value']:,.4f}".rstrip("0").rstrip(".")
        chain_rows += (
            '<tr>'
            f'<td>{html.escape(st["name"])}'
            f'<div class="ts2-src">{html.escape(st["source"] or "")}</div></td>'
            f'<td class="r"><input name="step{i}" value="{form_val}" '
            f'aria-label="{html.escape(st["name"], quote=True)}"/>'
            f' <span class="ts2-src">{html.escape(st["unit"])}'
            f'{" (%)" if st["op"] == "rate" else ""}</span></td>'
            f'<td class="r">{_fmt_step_value(st)}</td>'
            f'<td class="r ts2-run">{_fmt_running(st)}</td>'
            '</tr>'
        )
    sam_row = (
        '<tr><td>Addressable share (SAM)'
        f'<div class="ts2-src">{html.escape(model.sam_note or "")}</div></td>'
        f'<td class="r"><input name="sam_share" '
        f'value="{model.sam_share*100:g}"/> <span class="ts2-src">% of TAM'
        '</span></td>'
        f'<td class="r">{model.sam_share*100:,.1f}%</td>'
        f'<td class="r ts2-run">{_fmt_money(out["sam"])}</td></tr>'
        '<tr><td>Obtainable share (SOM)'
        f'<div class="ts2-src">{html.escape(model.som_note or "")}</div></td>'
        f'<td class="r"><input name="som_share" '
        f'value="{model.som_share*100:g}"/> <span class="ts2-src">% of SAM'
        '</span></td>'
        f'<td class="r">{model.som_share*100:,.1f}%</td>'
        f'<td class="r ts2-run">{_fmt_money(out["som"])}</td></tr>'
    )
    # Directionality made visible: ▲ tailwind / ▼ headwind by sign, with
    # the root cause (the note) under each driver name.
    growth_inputs = ""
    for i, g in enumerate(out["growth_drivers"]):
        if g["annual_pct"] > 0:
            arrow = '<span style="color:#0a8a5f;">▲</span>'
        elif g["annual_pct"] < 0:
            arrow = '<span style="color:#b5321e;">▼</span>'
        else:
            arrow = '<span style="color:#7a8699;">—</span>'
        growth_inputs += (
            '<div class="ts2-drv">'
            f'<span>{arrow} {html.escape(g["name"])}'
            f'<div class="ts2-src">{html.escape(g["note"] or "")}</div></span>'
            f'<span class="pct"><input name="growth{i}" '
            f'value="{g["annual_pct"]:g}" style="width:70px;"/> %/yr</span>'
            '</div>'
        )
    chain_panel = ck_panel(
        f'<form method="GET" action="/diligence/tam-sam">'
        f'<input type="hidden" name="template" '
        f'value="{html.escape(tmpl_key, quote=True)}"/>'
        '<table class="ts2-chain"><thead><tr>'
        '<th>Driver</th><th style="text-align:right;">Your input</th>'
        '<th style="text-align:right;">Applied</th>'
        '<th style="text-align:right;">Running value</th>'
        f'</tr></thead><tbody>{chain_rows}{sam_row}</tbody></table>'
        '<div style="margin:16px 0 0;">'
        '<div class="ts2-src" style="margin-bottom:6px;text-transform:'
        'uppercase;letter-spacing:.1em;">Growth drivers (composed '
        'multiplicatively)</div>'
        f'{growth_inputs}</div>'
        '<div class="ts2-form-bar">'
        '<button type="submit" class="ts2-btn">Recompute</button>'
        '<span class="ts2-src">Every value editable — rates entered as '
        'percent points (2.3 = 2.3%).</span>'
        '</div></form>',
        title="Driver chain · the methodology, shown",
    )

    has_seg_growth = any(s.get("growth_pct") is not None
                         for s in out["segments"])
    seg_rows = ""
    for s in out["segments"]:
        sr = (f"{s['success_rate']*100:,.0f}%"
              if s["success_rate"] is not None else "—")
        fastest = s.get("is_fastest")
        row_style = (' style="background:var(--sc-bone,#ece5d6);"'
                     if fastest else "")
        g = s.get("growth_pct")
        g_s = (f'{g:+.0f}%' if g is not None else "—")
        g_tone = ("#0a8a5f" if (g or 0) >= 5
                  else "#b5321e" if (g or 0) < 0 else "#1a2332")
        y5 = s.get("tam_y_final")
        growth_tds = (
            f'<td class="r" style="color:{g_tone};font-weight:600;">'
            f'{g_s}{" ★" if fastest else ""}</td>'
            f'<td class="r">{_fmt_money(y5) if y5 else "—"}</td>'
            if has_seg_growth else ""
        )
        seg_rows += (
            f'<tr{row_style}>'
            f'<td>{html.escape(s["name"])}'
            f'<div class="ts2-src">{html.escape(s["note"] or "")}</div></td>'
            f'<td class="r">{s["share_of_volume"]*100:,.0f}%</td>'
            f'<td class="r">{_fmt_money(s["tam_value"])}</td>'
            f'{growth_tds}'
            f'<td class="r">{sr}</td>'
            '</tr>'
        )
    seg_panel = ck_panel(
        '<table class="ts2-chain"><thead><tr>'
        '<th>Segment</th><th style="text-align:right;">Volume share</th>'
        '<th style="text-align:right;">TAM slice</th>'
        + ('<th style="text-align:right;">Growth %/yr</th>'
           f'<th style="text-align:right;">Y{out["horizon_years"]} '
           'slice</th>' if has_seg_growth else "")
        + '<th style="text-align:right;">Success rate</th>'
        f'</tr></thead><tbody>{seg_rows}</tbody></table>'
        + ('<p class="ts2-src" style="margin:8px 0 0;">★ = the fastest-'
           'growing segment — where the whitespace compounds. Segment '
           'growth rates are template defaults; the composite drivers '
           'above govern the funnel projection.</p>'
           if has_seg_growth else ""),
        title="Segments · the whitespace map",
    ) if out["segments"] else ""

    proj_rows = "".join(
        '<tr>'
        f'<td>Year {p["year"]}</td>'
        f'<td class="r">{_fmt_money(p["tam"])}</td>'
        f'<td class="r">{_fmt_money(p["sam"])}</td>'
        f'<td class="r">{_fmt_money(p["som"])}</td>'
        '</tr>'
        for p in out["projection"]
    )
    proj_panel = ck_panel(
        _projection_svg(out["projection"])
        + '<table class="ts2-chain"><thead><tr>'
        '<th>Horizon</th><th style="text-align:right;">TAM</th>'
        '<th style="text-align:right;">SAM</th>'
        '<th style="text-align:right;">SOM</th>'
        f'</tr></thead><tbody>{proj_rows}</tbody></table>'
        f'<p class="ts2-src" style="margin:10px 0 0;">Composite '
        f'{out["composite_cagr_pct"]:+.1f}%/yr from the named drivers '
        'above — the decomposition survives into the export so the IC '
        'sees which lever carries the growth.</p>',
        title=f"{out['horizon_years']}-year projection",
    )

    export_qs = urllib.parse.urlencode(
        {k: v[0] for k, v in qs.items() if v}, doseq=False)
    export_panel = ck_panel(
        '<div class="ts2-form-bar" style="margin:0;" id="ts2-export">'
        f'<a class="ts2-export" '
        f'href="/api/diligence/tam-sam.xlsx?{export_qs}" download>'
        '⬇ Formatted Excel (.xlsx)</a>'
        f'<a class="ts2-export" '
        f'href="/api/diligence/tam-sam.csv?{export_qs}" download>'
        '⬇ CSV</a>'
        '<span class="ts2-src">Excel ships 3 formatted sheets — Funnel '
        '&amp; chain, Segments, Projection — headers, $ and % formats, '
        'column widths set.</span></div>',
        title="Export · drop into the deal model",
    )

    basis = (
        f'<p class="ts2-src" style="margin:4px 0 14px;">'
        f'{html.escape(out["basis_note"])}</p>'
        if out["basis_note"] else ""
    )

    body = (
        _CSS + title + src + tmpl_bar + scen_bar + basis + funnel
        + _industry_comparison_panel(tmpl_key)
        + chain_panel + seg_panel + proj_panel
        + _tornado_panel(model, out["tam"])
        + _industry_panels(tmpl_key)
        + _sources_panel(out, _dive_for_sources(tmpl_key))
        + export_panel
        + ck_next_section(
            "Carry the sizing into the IC packet",
            "/diligence/ic-packet",
            eyebrow="Up next",
            italic_word="packet",
        )
    )
    return chartis_shell(
        body, "TAM / SAM Builder",
        active_nav="/diligence/tam-sam",
    )


# ── Exports ──────────────────────────────────────────────────────────────

def tam_sam_csv(qs: Dict[str, List[str]]) -> str:
    import csv
    import io
    model = model_from_qs(qs)
    out = compute(model)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["TAM/SAM build", out["name"]])
    w.writerow(["Basis", out["basis_note"]])
    w.writerow([])
    w.writerow(["Driver", "Op", "Value", "Unit", "Source", "Running value"])
    for st in out["steps"]:
        w.writerow([st["name"], st["op"], st["value"], st["unit"],
                    st["source"], round(st["running"], 2)])
    w.writerow(["Addressable share (SAM)", "rate", out["sam_share"],
                "of TAM", out["sam_note"], round(out["sam"], 2)])
    w.writerow(["Obtainable share (SOM)", "rate", out["som_share"],
                "of SAM", out["som_note"], round(out["som"], 2)])
    w.writerow([])
    if out["segments"]:
        w.writerow(["Segment", "Volume share", "TAM slice",
                    "Growth %/yr", f"Y{out['horizon_years']} slice",
                    "Success rate", "Note"])
        for s in out["segments"]:
            w.writerow([s["name"], s["share_of_volume"],
                        round(s["tam_value"], 2),
                        s.get("growth_pct") if s.get("growth_pct")
                        is not None else "",
                        round(s["tam_y_final"], 2)
                        if s.get("tam_y_final") else "",
                        s["success_rate"] if s["success_rate"] is not None
                        else "", s["note"]])
        w.writerow([])
    w.writerow(["Growth driver", "%/yr", "Note"])
    for g in out["growth_drivers"]:
        w.writerow([g["name"], g["annual_pct"], g["note"]])
    w.writerow(["Composite CAGR", round(out["composite_cagr_pct"], 2), ""])
    w.writerow([])
    w.writerow(["Year", "TAM", "SAM", "SOM"])
    for p in out["projection"]:
        w.writerow([p["year"], round(p["tam"], 2), round(p["sam"], 2),
                    round(p["som"], 2)])
    return buf.getvalue()


def tam_sam_xlsx(qs: Dict[str, List[str]]) -> bytes:
    from ..exports.xlsx_writer import Sheet, write_xlsx
    model = model_from_qs(qs)
    out = compute(model)
    _scen = ((qs.get("scenario") or ["base"])[0] or "base").lower()
    if _scen not in ("conservative", "base", "aggressive"):
        _scen = "base"
    H = "header"
    funnel_rows: List[List[Any]] = [
        [(f"TAM/SAM build · {out['name']} · "
          f"{_scen.upper()} scenario", H), ("", H), ("", H), ("", H),
         ("", H), ("", H)],
        [out["basis_note"], "", "", "", "", ""],
        [],
        [("Driver", H), ("Op", H), ("Value", H), ("Unit", H),
         ("Source", H), ("Running", H)],
    ]
    for st in out["steps"]:
        val = ((st["value"], "pct") if st["op"] == "rate"
               else (st["value"], "money") if st["op"] == "price"
               else (st["value"], "num2"))
        run = ((st["running"], "money") if st["op"] == "price"
               else (st["running"], "num"))
        funnel_rows.append([st["name"], st["op"], val, st["unit"],
                            st["source"], run])
    funnel_rows += [
        ["Addressable share (SAM)", "rate", (out["sam_share"], "pct"),
         "of TAM", out["sam_note"], (out["sam"], "money")],
        ["Obtainable share (SOM)", "rate", (out["som_share"], "pct"),
         "of SAM", out["som_note"], (out["som"], "money")],
        [],
        [("TAM", H), (out["tam"], "money")],
        [("SAM", H), (out["sam"], "money")],
        [("SOM", H), (out["som"], "money")],
    ]
    seg_rows: List[List[Any]] = [
        [("Segment", H), ("Volume share", H), ("TAM slice", H),
         ("Growth %/yr", H), (f"Y{out['horizon_years']} slice", H),
         ("Success rate", H), ("Note", H)],
    ] + [
        [s["name"], (s["share_of_volume"], "pct"),
         (s["tam_value"], "money"),
         (s["growth_pct"] / 100.0, "pct")
         if s.get("growth_pct") is not None else "",
         (s["tam_y_final"], "money") if s.get("tam_y_final") else "",
         (s["success_rate"], "pct") if s["success_rate"] is not None else "",
         s["note"]]
        for s in out["segments"]
    ]
    proj_rows: List[List[Any]] = [
        [("Growth driver", H), ("%/yr", H), ("Note", H)],
    ] + [
        [g["name"], (g["annual_pct"] / 100.0, "pct"), g["note"]]
        for g in out["growth_drivers"]
    ] + [
        ["Composite CAGR", (out["composite_cagr_pct"] / 100.0, "pct"), ""],
        [],
        [("Year", H), ("TAM", H), ("SAM", H), ("SOM", H)],
    ] + [
        [p["year"], (p["tam"], "money"), (p["sam"], "money"),
         (p["som"], "money")]
        for p in out["projection"]
    ]
    src_rows: List[List[Any]] = [
        [("#", H), ("Item", H), ("Source", H)],
    ]
    n_src = 0
    seen_src = set()
    for st in out["steps"]:
        if st["source"] and st["source"] not in seen_src:
            seen_src.add(st["source"])
            n_src += 1
            src_rows.append([n_src, st["name"], st["source"]])
    for g in out["growth_drivers"]:
        if g["note"] and g["note"] not in seen_src:
            seen_src.add(g["note"])
            n_src += 1
            src_rows.append([n_src, f"{g['name']} (growth driver)",
                             g["note"]])
    if out.get("basis_note"):
        n_src += 1
        src_rows.append([n_src, "Basis", out["basis_note"]])
    return write_xlsx([
        Sheet("Funnel & chain", funnel_rows,
              col_widths=[34, 8, 14, 16, 44, 16]),
        Sheet("Segments", seg_rows,
              col_widths=[26, 13, 15, 12, 15, 13, 40]),
        Sheet("Projection", proj_rows, col_widths=[34, 12, 40, 16]),
        Sheet("Sources", src_rows, col_widths=[5, 38, 70]),
    ])
