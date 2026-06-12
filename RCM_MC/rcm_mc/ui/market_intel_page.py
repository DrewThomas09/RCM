"""Market Intelligence UI at /market-intel.

Three stacked sections:

    1. Public operator comps (HCA / THC / CYH / UHS / EHC / ARDT)
       with EV/EBITDA + EV/Revenue + payer mix, filtered by the
       caller's target category if one is supplied.

    2. Private-market transaction multiples for the target's
       specialty × deal-size.

    3. Healthcare PE news feed filtered to the target's context
       (tickers, specialty, tags).

Optional query params:
    ?category=MULTI_SITE_ACUTE_HOSPITAL
    &specialty=ANESTHESIOLOGY
    &ev_usd=350000000
    &revenue_usd=200000000
    &tickers=HCA,THC
    &tags=nsa,site_neutral
"""
from __future__ import annotations

import html
import statistics as _stats
from typing import Any, Dict, List, Optional, Tuple

from ..market_intel import (
    MultipleBand, NewsItem, PublicComp, category_bands,
    find_comparables, list_companies, news_for_target,
    sector_sentiment, transaction_multiple,
)
from ._chartis_kit import (
    P, chartis_shell, ck_kpi_block, ck_next_section, ck_panel,
    ck_section_intro, ck_source_purpose,
)
from .power_ui import provenance, sortable_table


_SENTIMENT_COLOR = {
    "positive": P["positive"],
    "negative": P["negative"],
    "neutral":  P["text_dim"],
    "mixed":    P["warning"],
}


# Sub-vertical taxonomy — roll the granular `category` codes up into the
# public-market sub-verticals a healthcare-PE desk actually screens by. The
# second tuple element is display rank (acute first → REITs last); any code
# not listed falls through to "Other operators".
_SUBVERTICAL: Dict[str, Tuple[str, int]] = {
    "MULTI_SITE_ACUTE_HOSPITAL":       ("Acute Hospitals", 0),
    "RURAL_ACUTE_HOSPITAL":            ("Acute Hospitals", 0),
    "MULTI_SITE_ACUTE_AND_BEHAVIORAL": ("Acute Hospitals", 0),
    "POST_ACUTE_REHAB":                ("Post-Acute & Rehab", 1),
    "MANAGED_CARE_PAYER":              ("Payors / Managed Care", 2),
    "DIALYSIS":                        ("Outpatient & Services", 3),
    "AMBULATORY_SURGERY":              ("Outpatient & Services", 3),
    "PHYSICIAN_GROUP_ROLL_UP":         ("Outpatient & Services", 3),
    "HEALTHCARE_REIT":                 ("Healthcare REITs", 4),
}


def _subvertical_of(category: Optional[str]) -> Tuple[str, int]:
    return _SUBVERTICAL.get(category or "", ("Other operators", 9))


def _hhi(values: List[float]) -> float:
    """Herfindahl–Hirschman Index over a set of revenue figures, on the
    0–10,000 merger-review scale. >2,500 reads as highly concentrated;
    1,500–2,500 moderately; <1,500 competitive. Used here to flag how
    top-heavy the tracked public-operator universe is (one mega-cap payer
    dominates revenue, so the figure runs high by design)."""
    pos = [v for v in values if v and v > 0]
    total = sum(pos)
    if total <= 0:
        return 0.0
    return sum(((v / total) * 100.0) ** 2 for v in pos)


def _hhi_label(hhi: float) -> str:
    if hhi >= 2500:
        return "highly concentrated"
    if hhi >= 1500:
        return "moderately concentrated"
    return "competitive"


def _target_scatter_chart(
    comps_dicts: List[Dict[str, Any]],
    target_revenue_usd: Optional[float] = None,
    target_ev_usd: Optional[float] = None,
    width: int = 1100, height: int = 420,
) -> str:
    """SVG scatter: EV/EBITDA (y) vs Revenue TTM (x) for the peer
    set, with the target highlighted if revenue + EV supplied.

    Clean layout — no axes noise, tight tick labels, peer labels
    only on hover (via <title>). Default size enlarged 2026-04-26
    per UX feedback (was 640x240, scatter was unreadably small).
    """
    if not comps_dicts:
        return ""
    pad_l, pad_r, pad_t, pad_b = 80, 32, 36, 52
    inner_w = max(1, width - pad_l - pad_r)
    inner_h = max(1, height - pad_t - pad_b)

    xs = [c.get("revenue_ttm_usd_bn") or 0 for c in comps_dicts]
    ys = [c.get("ev_ebitda_multiple") or 0 for c in comps_dicts]
    # Include target in ranges so axis covers both.
    target_rev_bn = (
        target_revenue_usd / 1e9 if target_revenue_usd else None
    )
    target_mult = None
    if target_ev_usd and target_revenue_usd:
        # Approximate implied multiple assuming 12% EBITDA margin
        # (acute hospital system median).  Used for positioning in
        # the scatter; the partner sees the assumption inline.
        implied_ebitda = target_revenue_usd * 0.12
        if implied_ebitda > 0:
            target_mult = target_ev_usd / implied_ebitda
    if target_rev_bn is not None:
        xs = xs + [target_rev_bn]
    if target_mult is not None:
        ys = ys + [target_mult]
    if not any(x > 0 for x in xs) or not any(y > 0 for y in ys):
        return ""

    import math as _math
    # LOG x-axis (revenue). A few mega-cap insurers (UNH ~$434B) otherwise
    # compress every hospital operator + services firm into an unreadable smear
    # at the origin on a linear scale. Log space spreads the ~$1B–$450B range
    # evenly so HCA/THC/UHS and the services names are legible.
    x_pos = [x for x in xs if x > 0]
    x_lo = max(min(x_pos) * 0.85, 0.5)   # floor keeps log finite/clean
    x_hi = max(x_pos) * 1.25
    lx_lo, lx_hi = _math.log10(x_lo), _math.log10(x_hi)
    y_max = max(ys) * 1.15 or 1.0
    y_min = min(y for y in ys if y > 0) * 0.85

    def px_x(v):
        return pad_l + (_math.log10(max(v, x_lo)) - lx_lo) / (lx_hi - lx_lo) * inner_w
    def px_y(v): return pad_t + inner_h - (v - y_min) / (y_max - y_min) * inner_h

    # Grid lines
    grid = []
    for y_t in (y_min, (y_min + y_max) / 2, y_max):
        grid.append(
            f'<line x1="{pad_l}" y1="{px_y(y_t):.1f}" '
            f'x2="{pad_l + inner_w}" y2="{px_y(y_t):.1f}" '
            f'stroke="{P["border_dim"]}" stroke-width="1" />'
            f'<text x="{pad_l - 6:.0f}" y="{px_y(y_t) + 3:.0f}" '
            f'fill="{P["text_faint"]}" text-anchor="end" '
            f'font-size="9" font-family="JetBrains Mono, monospace">'
            f'{y_t:.1f}x</text>'
        )

    # Outliers to call out distinctly (amber, larger, always labeled): the
    # highest-revenue peer (UNH on scale) and the highest-multiple peer (WELL,
    # a REIT whose EV/EBITDA reads high because REITs trade on FFO).
    _out_x = max(comps_dicts, key=lambda c: c.get("revenue_ttm_usd_bn") or 0)
    _out_y = max(comps_dicts, key=lambda c: c.get("ev_ebitda_multiple") or 0)
    outlier_tk = {_out_x.get("ticker"), _out_y.get("ticker")}

    # Peer dots — labels de-collide greedily (the cluster of services firms
    # used to pile their tickers on top of each other). Revenue-major sort so
    # the bigger names win label placement.
    dots = []
    placed: List[Tuple[float, float]] = []
    for c in sorted(comps_dicts, key=lambda c: -(c.get("revenue_ttm_usd_bn") or 0)):
        x = c.get("revenue_ttm_usd_bn") or 0
        y = c.get("ev_ebitda_multiple") or 0
        if x <= 0 or y <= 0:
            continue
        cx, cy = px_x(x), px_y(y)
        tk = c.get("ticker", "")
        is_out = tk in outlier_tk
        fill = P["warning"] if is_out else P["accent"]
        r = 6.5 if is_out else 4.8
        _m = c.get("op_margin_pct")
        if _m is None:
            _m = c.get("operating_margin_pct")
        if _m is None:
            # PublicComp.to_dict() carries the margin as a fraction.
            _frac = c.get("operating_margin")
            if isinstance(_frac, (int, float)):
                _m = _frac * 100.0
        mtxt = f" · {_m:.0f}% op margin" if isinstance(_m, (int, float)) else ""
        title = (
            f"{tk} · {c.get('name', '')} · ${x:,.1f}B revenue · "
            f"{y:.1f}x EV/EBITDA{mtxt}"
        )
        dots.append(
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" '
            f'fill="{fill}" opacity="{0.92 if is_out else 0.72}" '
            f'stroke="{P["panel"] if is_out else "none"}" stroke-width="1">'
            f'<title>{html.escape(title)}</title></circle>'
        )
        # Label outliers always; others only if their label clears the ones
        # already placed (greedy vertical de-collision).
        lx, ly = cx + 8, cy - 5
        clear = all(abs(ly - py) > 11 or abs(lx - px) > 64 for px, py in placed)
        if is_out or clear:
            for _ in range(6):
                if all(abs(ly - py) > 11 or abs(lx - px) > 64 for px, py in placed):
                    break
                ly += 11
            placed.append((lx, ly))
            lab_fill = P["warning"] if is_out else P["text_faint"]
            weight = ' font-weight="700"' if is_out else ""
            dots.append(
                f'<text x="{lx:.1f}" y="{ly:.1f}" fill="{lab_fill}"{weight} '
                f'font-size="9" font-family="JetBrains Mono, monospace">'
                f'{html.escape(tk)}</text>'
            )

    # Target marker
    target_marker = ""
    if target_rev_bn is not None and target_mult is not None:
        tx = px_x(target_rev_bn)
        ty = px_y(target_mult)
        target_marker = (
            f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="9" '
            f'fill="none" stroke="{P["warning"]}" stroke-width="2">'
            f'<title>Target · ${target_rev_bn:,.1f}B revenue · '
            f'{target_mult:.1f}x implied EV/EBITDA (12% margin '
            f'assumption)</title></circle>'
            f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="3" '
            f'fill="{P["warning"]}"><title>Target</title></circle>'
            f'<text x="{tx + 12:.1f}" y="{ty + 4:.1f}" '
            f'fill="{P["warning"]}" font-size="10" '
            f'font-family="Helvetica Neue, Arial, sans-serif" '
            f'font-weight="700">TARGET</text>'
        )

    # X axis labels — log-spaced ticks (1× / 3× each decade) inside the range,
    # so the eye reads $1B → $3B → $10B → … → $300B at even pixel spacing. The
    # highest-revenue peer is always anchored near the right edge so the mega-cap
    # (UNH) keeps a labelled tick instead of floating unmarked.
    x_axis = []
    _ticks: List[float] = []
    _decade = int(_math.floor(lx_lo))
    while _decade <= int(_math.ceil(lx_hi)):
        for _mant in (1.0, 3.0):
            _v = _mant * (10 ** _decade)
            if x_lo <= _v <= x_hi:
                _ticks.append(_v)
        _decade += 1
    _hi_peer = max(x_pos)
    if all(abs(_v - _hi_peer) > _hi_peer * 0.10 for _v in _ticks):
        _ticks.append(_hi_peer)
    for x_t in _ticks:
        _lbl = f"${x_t:,.0f}B" if x_t >= 100 else f"${x_t:,.1f}B"
        x_axis.append(
            f'<text x="{px_x(x_t):.1f}" y="{pad_t + inner_h + 16:.1f}" '
            f'fill="{P["text_faint"]}" text-anchor="middle" '
            f'font-size="9" font-family="JetBrains Mono, monospace">'
            f'{_lbl}</text>'
        )
    # Axis title — flag the log scale so the spacing isn't misread as linear.
    x_axis.append(
        f'<text x="{pad_l + inner_w / 2:.0f}" y="{pad_t + inner_h + 34:.0f}" '
        f'fill="{P["text_faint"]}" text-anchor="middle" font-size="9" '
        f'font-family="Helvetica Neue, Arial, sans-serif" '
        f'letter-spacing="1" font-style="italic">'
        f'TTM REVENUE — LOG SCALE ($B)</text>'
    )

    note = ""
    if target_marker:
        note = (
            f'<text x="{pad_l}" y="{height - 6:.0f}" '
            f'fill="{P["text_faint"]}" font-size="9.5" '
            f'font-family="Helvetica Neue, Arial, sans-serif" '
            f'font-style="italic">'
            f'Target position uses a 12% EBITDA margin assumption '
            f'(acute hospital median).</text>'
        )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'preserveAspectRatio="xMidYMid meet" '
        f'style="max-width:{width}px;height:auto;display:block;margin-top:8px;">'
        f'<text x="{pad_l}" y="14" fill="{P["text_dim"]}" '
        f'font-size="10" font-family="Helvetica Neue, Arial, sans-serif" '
        f'font-weight="700" letter-spacing="1.5">'
        f'EV/EBITDA vs REVENUE · PEER SCATTER</text>'
        f'{"".join(grid)}'
        f'{"".join(dots)}'
        f'{target_marker}'
        f'{"".join(x_axis)}'
        f'{note}'
        f'</svg>'
    )


def _hero(category: Optional[str], specialty: Optional[str]) -> str:
    sub_parts = []
    if category:
        sub_parts.append(f"Category: {html.escape(category)}")
    if specialty:
        sent = sector_sentiment(specialty)
        if sent:
            sub_parts.append(f"Sector sentiment: {html.escape(sent)}")
    sub = " · ".join(sub_parts) if sub_parts else (
        "Public-market overlay. Refresh the curated content YAMLs "
        "quarterly from primary filings."
    )
    # 2026-05-28 batch 20 · universal strict 5-block head.
    from ._chartis_kit import ck_editorial_head
    return ck_editorial_head(
        eyebrow="MARKET INTELLIGENCE",
        title="Public comps & market context.",
        meta="PUBLIC-MARKET OVERLAY · QUARTERLY REFRESH",
        lede_body=sub,
    )


def _public_comps_section(
    category: Optional[str],
    target_revenue_usd: Optional[float],
    target_ev_usd: Optional[float] = None,
) -> str:
    if category:
        payload = find_comparables(
            target_category=category,
            target_revenue_usd=target_revenue_usd,
        )
        comps_dicts = payload["comps"]
        band = payload["band"]
        if not comps_dicts:
            fallback = (
                f'<div style="color:{P["text_faint"]};font-size:12px;'
                f'font-style:italic;">{html.escape(payload.get("note", ""))}'
                f'</div>'
            )
        else:
            fallback = ""
        # Hydrate back to PublicComp objects for formatting convenience
        # but keep comparing against the dict for display.
    else:
        comps_dicts = [c.to_dict() for c in list_companies()]
        band = None
        fallback = ""

    if not comps_dicts:
        return ck_panel(
            fallback or '<p class="ck-section-body">No comparable '
            'public operators for this target.</p>',
            title="Public Healthcare Operators",
        )

    def _consensus_pill(consensus: str) -> str:
        color = {
            "BUY": P["positive"], "HOLD": P["warning"],
            "SELL": P["negative"], "NONE": P["text_faint"],
        }.get(consensus.upper(), P["text_faint"])
        return (
            f'<span style="display:inline-block;padding:1px 7px;'
            f'border:1px solid {color};color:{color};font-size:9px;'
            f'letter-spacing:1.2px;text-transform:uppercase;'
            f'font-weight:700;border-radius:3px;">'
            f'{html.escape(consensus)}</span>'
        )

    # ---- universe snapshot (always on) -----------------------------------
    revs = [c.get("revenue_ttm_usd_bn") or 0.0 for c in comps_dicts]
    mults = [c["ev_ebitda_multiple"] for c in comps_dicts
             if c.get("ev_ebitda_multiple")]
    agg_rev = sum(revs)
    med_mult = _stats.median(mults) if mults else 0.0
    hhi = _hhi(revs)
    snapshot = (
        '<div class="ck-kpi-strip">'
        + ck_kpi_block("Tracked operators", f"{len(comps_dicts)}",
                       sub="public healthcare equities")
        + ck_kpi_block("Median EV/EBITDA", f"{med_mult:.1f}x",
                       sub="across the tracked set")
        + ck_kpi_block("Aggregate revenue", f"${agg_rev:,.0f}B",
                       sub="trailing-twelve-month")
        + ck_kpi_block("Revenue HHI", f"{hhi:,.0f}",
                       sub=f"{_hhi_label(hhi)} · 0–10,000 scale")
        + '</div>'
    )

    # ---- sub-vertical grid ------------------------------------------------
    groups: Dict[str, List[Dict[str, Any]]] = {}
    rank_of: Dict[str, int] = {}
    for c in comps_dicts:
        label, rank = _subvertical_of(c.get("category"))
        groups.setdefault(label, []).append(c)
        rank_of[label] = rank
    cards = []
    for label in sorted(groups, key=lambda l: (rank_of[l], l)):
        g = groups[label]
        g_mults = [x["ev_ebitda_multiple"] for x in g
                   if x.get("ev_ebitda_multiple")]
        g_rev = sum(x.get("revenue_ttm_usd_bn") or 0.0 for x in g)
        g_marg = [x["operating_margin"] for x in g
                  if x.get("operating_margin") is not None]
        g_med = _stats.median(g_mults) if g_mults else 0.0
        g_margin = (_stats.median(g_marg) * 100.0) if g_marg else 0.0
        ticks = ", ".join(sorted(x.get("ticker", "") for x in g))
        mc = (P["positive"] if g_med >= 12
              else P["negative"] if g_med < 8 else P["text"])
        cards.append(
            f'<div class="mi-vert-card">'
            f'<div class="mi-vert-name">{html.escape(label)}</div>'
            f'<div class="mi-vert-stat">'
            f'<span class="mi-vert-num" style="color:{mc}">{g_med:.1f}x</span>'
            f'<span class="mi-vert-lbl">median<br>EV/EBITDA</span></div>'
            f'<div class="mi-vert-row"><span>{len(g)} cos</span>'
            f'<span>${g_rev:,.0f}B rev</span>'
            f'<span>{g_margin:.0f}% op mgn</span></div>'
            f'<div class="mi-vert-tk">{html.escape(ticks)}</div>'
            f'</div>'
        )
    grid = (
        f'<div class="mi-section-label">Sub-verticals · '
        f'{len(groups)} groups</div>'
        f'<div class="mi-vert-grid">{"".join(cards)}</div>'
    )

    # ---- dense, color-coded comp table -----------------------------------
    def _mult_cell(m: Optional[float]) -> str:
        if not m:
            return "—"
        col = (P["positive"] if m >= 12
               else P["negative"] if m < 8 else P["text"])
        return (f'<span style="color:{col};font-family:\'JetBrains Mono\','
                f'monospace;font-weight:600">{m:.1f}x</span>')

    def _margin_cell(frac: Optional[float]) -> str:
        if frac is None:
            return "—"
        p = frac * 100.0
        col = (P["positive"] if p >= 15
               else P["negative"] if p < 8 else P["text"])
        return (f'<span style="color:{col};font-family:\'JetBrains Mono\','
                f'monospace;font-weight:600">{p:.1f}%</span>')

    headers = [
        "Ticker", "Name", "Sub-vertical", "EV ($bn)", "Revenue ($bn)",
        "EV/EBITDA", "EV/Rev", "Op margin", "Debt/EBITDA", "Analyst",
    ]
    rows = []
    sort_keys = []
    for c in sorted(
        comps_dicts,
        key=lambda c: (_subvertical_of(c.get("category"))[1],
                       -(c.get("revenue_ttm_usd_bn") or 0.0)),
    ):
        ac = c.get("analyst_coverage") or {}
        consensus = str(ac.get("consensus") or "NONE").upper()
        price_target = ac.get("price_target_usd")
        analyst_html = _consensus_pill(consensus)
        if price_target:
            analyst_html += (
                f' <span style="color:{P["text_faint"]};'
                f'font-size:10px;">PT ${price_target:,.0f}</span>'
            )
        sv_label = _subvertical_of(c.get("category"))[0]
        mult = c.get("ev_ebitda_multiple")
        rows.append([
            c["ticker"],
            c["name"],
            sv_label,
            provenance(
                f"${c['enterprise_value_usd_bn']:,.1f}",
                source=f"{c['ticker']} 10-K filing, TTM balance sheet",
                formula="market_cap + total_debt - cash",
            ),
            f"${c['revenue_ttm_usd_bn']:,.1f}",
            _mult_cell(mult),
            f"{c['ev_revenue_multiple']:.2f}x",
            _margin_cell(c.get("operating_margin")),
            (f"{c['debt_to_ebitda']:.2f}x"
             if c.get("debt_to_ebitda") is not None else "—"),
            analyst_html,
        ])
        sort_keys.append([
            c["ticker"],
            c["name"],
            sv_label,
            c["enterprise_value_usd_bn"],
            c["revenue_ttm_usd_bn"],
            mult or 0.0,
            c["ev_revenue_multiple"],
            c.get("operating_margin") or 0.0,
            c.get("debt_to_ebitda") or 0.0,
            consensus,
        ])
    table = sortable_table(
        headers, rows,
        name="public_comps",
        sort_keys=sort_keys,
        table_class="ck-table sortable",
        caption=(
            "EV/EBITDA shaded green ≥12x (premium multiple) · red <8x "
            "(discount). Op margin shaded green ≥15% · red <8%. Default "
            "order groups by sub-vertical then revenue — click any header "
            "to re-sort. EV = market_cap + total_debt − cash; "
            "EV/EBITDA = EV ÷ TTM EBITDA."
        ),
    )

    band_html = ""
    if band:
        kpi_strip = (
            '<div class="ck-kpi-strip">'
            + ck_kpi_block(
                "Median EV/EBITDA",
                f'{band["median_ev_ebitda"]:.1f}x',
                sub=f'p25–p75: {band["p25_ev_ebitda"]:.1f}x – {band["p75_ev_ebitda"]:.1f}x',
            )
            + ck_kpi_block(
                "Constituents",
                f"{len(band['constituents'])}",
                sub=", ".join(band["constituents"]),
            )
            + '</div>'
        )
        band_html = ck_panel(
            kpi_strip
            + (f'<p class="ck-eyebrow">{html.escape(band["note"])}</p>'
               if band.get("note") else ""),
            title="Category band",
        )
    scatter = _target_scatter_chart(
        comps_dicts,
        target_revenue_usd=target_revenue_usd,
        target_ev_usd=target_ev_usd,
    )
    scatter_html = ""
    if scatter:
        scatter_html = ck_panel(
            scatter, title="EV/EBITDA × revenue scatter")
    return ck_panel(
        f'{snapshot}{grid}{band_html}{scatter_html}{fallback}{table}',
        title="Public Healthcare Operators",
    )


def _multiples_directory() -> str:
    """The full specialty × size-band library, rendered when no
    specialty is selected. Before this, the 29-band library was
    invisible unless the caller already knew a specialty code — the
    directory makes the depth browsable and each row links the
    focused view."""
    from rcm_mc.market_intel.transaction_multiples import _load
    from ._chartis_kit import ck_data_cell
    rows_data = _load().get("bands") or []
    by_spec: dict = {}
    for r in rows_data:
        by_spec.setdefault(str(r.get("specialty", "")), []).append(r)
    trs = []
    for spec in sorted(by_spec):
        for r in sorted(by_spec[spec],
                        key=lambda x: str(x.get("deal_size_band", ""))):
            label = spec.replace("_", " ").title()
            note = (r.get("note") or "").strip().replace("\n", " ")
            trs.append("<tr>" + "".join([
                ck_data_cell(
                    f'<a href="/market-intel?specialty={html.escape(spec)}" '
                    f'style="color:inherit">{html.escape(label)}</a>',
                    mono=True, weight=600),
                ck_data_cell(html.escape(
                    str(r.get("deal_size_band", "")).replace("_", " ")),
                    mono=True),
                ck_data_cell(f'{float(r["p25_ev_ebitda"]):.2f}x',
                             align="right", mono=True),
                ck_data_cell(f'{float(r["p50_ev_ebitda"]):.2f}x',
                             align="right", mono=True, weight=600),
                ck_data_cell(f'{float(r["p75_ev_ebitda"]):.2f}x',
                             align="right", mono=True),
                ck_data_cell(str(r.get("sample_size_trailing_12_mo", "")),
                             align="right", mono=True, tone="dim"),
                f'<td class="ck-cell" style="max-width:300px;font-size:10px;'
                f'color:#6b7280">{html.escape(note)}</td>',
            ]) + "</tr>")
    ths = "".join(
        ck_data_cell(c, align=a, is_header=True)
        for c, a in (("Specialty", "left"), ("Size band", "left"),
                     ("P25", "right"), ("P50", "right"), ("P75", "right"),
                     ("n (TTM)", "right"), ("Note", "left")))
    table = (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
             f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody>'
             f'</table></div>')
    n_specs = len(by_spec)
    return ck_panel(
        f'<p class="ck-section-body">EV/EBITDA bands across {n_specs} '
        f'healthcare specialties ({len(rows_data)} specialty × size-band '
        f'combinations). Click a specialty to focus it against a target '
        f'EV. <a href="/transaction-multiples.xlsx" download '
        f'style="color:#155752;font-weight:600">Download the library '
        f'(.xlsx)</a>.</p>{table}',
        title="Private-market transaction multiples — full library",
    )


def _transaction_multiples_section(
    specialty: Optional[str],
    ev_usd: Optional[float],
) -> str:
    if not specialty:
        return _multiples_directory()
    band = transaction_multiple(specialty=specialty, ev_usd=ev_usd)
    if not band:
        return ck_panel(
            '<p class="ck-section-body">'
            f'No transaction-multiple data for {html.escape(specialty)}.</p>',
            title="Private-market transaction multiples",
        )
    ev_range_str = (
        (f" · target EV ${ev_usd/1e9:,.2f}B" if ev_usd >= 1e9 else f" · target EV ${ev_usd/1e6:,.0f}M") if ev_usd else ""
    )
    inner = (
        '<p class="ck-eyebrow">'
        f'{html.escape(specialty)} · {html.escape(band.deal_size_band)}{ev_range_str}'
        '</p>'
        '<div class="ck-kpi-strip">'
        + ck_kpi_block(
            "Median EV/EBITDA",
            f"{band.p50_ev_ebitda:.1f}x",
            sub=f"p25 {band.p25_ev_ebitda:.1f}x · p75 {band.p75_ev_ebitda:.1f}x",
        )
        + ck_kpi_block(
            "Sample size",
            f"{band.sample_size}",
            sub="deals trailing 12 months",
        )
        + '</div>'
        + (f'<p class="ck-section-body">{html.escape(band.note)}</p>'
           if band.note else "")
    )
    return ck_panel(
        inner, title="Private-market transaction multiple",
    )


def _news_section(
    specialty: Optional[str],
    tickers: Optional[List[str]],
    tags: Optional[List[str]],
) -> str:
    items = news_for_target(
        specialty=specialty, tickers=tickers, tags=tags, limit=12,
    )
    if not items:
        return ""
    rows = []
    for it in items:
        tag_html = "".join(
            f'<span class="mi-tag">{html.escape(t)}</span>'
            for t in it.tags
        )
        sent_cls = {
            "BULLISH": "cad-pos", "BEARISH": "cad-neg",
            "NEUTRAL": "",
        }.get(it.sentiment.upper(), "")
        rows.append(
            '<div class="mi-news-row">'
            '<div class="mi-news-body">'
            f'<div class="ck-eyebrow">{html.escape(it.date)} · '
            f'{html.escape(it.source)}'
            f'{(" · " + html.escape(it.specialty)) if it.specialty else ""}</div>'
            f'<a href="{html.escape(it.url)}" target="_blank" rel="noopener" '
            f'class="mi-news-title">{html.escape(it.title)}</a>'
            f'<div class="mi-news-tags">{tag_html}</div>'
            f'<p class="ck-section-body">{html.escape(it.summary)}</p>'
            '</div>'
            f'<span class="cad-badge {sent_cls}">{html.escape(it.sentiment)}</span>'
            '</div>'
        )
    return ck_panel(
        ''.join(rows),
        title="Healthcare PE News Feed",
    )


def _earnings_calendar_section() -> str:
    """Upcoming earnings snapshot derived from the most recent
    earnings_latest disclosures. Each ticker's next expected
    reporting date is heuristically estimated as last_reported +
    90 days (standard quarterly cadence)."""
    from datetime import date, datetime, timedelta
    comps = list_companies()
    rows: List[Dict[str, Any]] = []
    today = date.today()
    for c in comps:
        el = c.earnings_latest
        if el is None or not el.reported_on:
            continue
        try:
            reported = datetime.strptime(
                str(el.reported_on), "%Y-%m-%d",
            ).date()
        except (ValueError, TypeError):
            continue
        # Next-quarterly estimate: 90d after last report. Real feed
        # would replace this with consensus reporting calendar.
        next_expected = reported + timedelta(days=90)
        days_to = (next_expected - today).days
        rows.append({
            "ticker": c.ticker, "name": c.name,
            "last_period": el.period,
            "last_eps_reported": el.eps_reported,
            "last_surprise_pct": el.surprise_pct,
            "last_reported_on": el.reported_on,
            "next_expected": next_expected.isoformat(),
            "days_to_next": days_to,
            "analyst_consensus": (
                c.analyst_coverage.consensus
                if c.analyst_coverage else "—"
            ),
        })
    # Sort by soonest upcoming (negative days = past-due / recent)
    rows.sort(key=lambda r: r["days_to_next"])

    if not rows:
        return ""

    headers = [
        "Ticker", "Name", "Last period", "Last EPS",
        "Last surprise", "Next expected", "Days to next", "Analyst",
    ]
    table_rows: List[List[str]] = []
    sort_keys: List[List[Any]] = []
    for r in rows:
        surprise_pct = r["last_surprise_pct"]
        surprise_html = "—"
        if surprise_pct is not None:
            color = (
                P["positive"] if surprise_pct > 0.01
                else P["negative"] if surprise_pct < -0.01
                else P["text_dim"]
            )
            arrow = "▲" if surprise_pct > 0.01 else (
                "▼" if surprise_pct < -0.01 else "●"
            )
            surprise_html = (
                f'<span style="color:{color};font-family:\'JetBrains Mono\',monospace;">'
                f'{arrow} {surprise_pct*100:+.1f}%</span>'
            )
        # Color the "days to next" by proximity — red for imminent,
        # amber for < 14d, grey for further out, muted for past-due.
        days = r["days_to_next"]
        if days < 0:
            days_color = P["text_faint"]
            days_label = f"{abs(days)}d ago (reported)"
        elif days <= 7:
            days_color = P["negative"]
            days_label = f"{days}d"
        elif days <= 30:
            days_color = P["warning"]
            days_label = f"{days}d"
        else:
            days_color = P["text_dim"]
            days_label = f"{days}d"
        days_html = (
            f'<span style="color:{days_color};font-family:'
            f'\'JetBrains Mono\',monospace;font-weight:600;">'
            f'{html.escape(days_label)}</span>'
        )
        table_rows.append([
            r["ticker"], r["name"], r["last_period"],
            f"${r['last_eps_reported']:.2f}" if r["last_eps_reported"] else "—",
            surprise_html,
            r["next_expected"],
            days_html,
            r["analyst_consensus"],
        ])
        sort_keys.append([
            r["ticker"], r["name"], r["last_period"],
            r["last_eps_reported"] or 0,
            surprise_pct if surprise_pct is not None else -9.9,
            r["next_expected"],
            days,
            r["analyst_consensus"],
        ])
    table = sortable_table(
        headers, table_rows, name="earnings_calendar",
        sort_keys=sort_keys,
    )
    # Call-out if any are imminent
    imminent = [r for r in rows if 0 <= r["days_to_next"] <= 14]
    imminent_html = ""
    if imminent:
        names = ", ".join(r["ticker"] for r in imminent[:5])
        imminent_html = (
            '<p class="ck-section-body cad-warn">'
            f'<strong>⚠ {len(imminent)} upcoming in next 14 days '
            f'({html.escape(names)})</strong> — hold diligence pricing '
            'decisions until after prints.</p>'
        )
    return ck_panel(
        '<p class="ck-section-body">'
        "Derived from each ticker's most recent earnings report + "
        'standard 90-day quarterly cadence. Real data-vendor / '
        'Yahoo Finance feed would replace the estimate with '
        'consensus-published dates.</p>'
        f'{imminent_html}{table}',
        title="Earnings calendar · next expected reporting dates",
    )


_MI_STYLES = f"""
<style>
.mi-tag{{font-size:9px;padding:1px 6px;background:{P["panel_alt"]};
color:{P["text_faint"]};border-radius:2px;margin-left:4px;}}
.mi-news-row{{padding:12px 0;border-bottom:1px solid {P["border"]};
display:flex;justify-content:space-between;align-items:baseline;gap:10px;}}
.mi-news-body{{flex:1;min-width:0;}}
.mi-news-title{{font-size:14px;color:{P["text"]};font-weight:500;
text-decoration:none;line-height:1.4;display:block;margin-top:2px;}}
.mi-news-tags{{margin-top:4px;}}
.mi-section-label{{font-size:10px;color:{P["text_faint"]};
letter-spacing:1.5px;text-transform:uppercase;font-weight:700;
margin:14px 0 10px;}}
.mi-vert-grid{{display:grid;
grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
gap:10px;margin:0 0 16px;}}
.mi-vert-card{{border:1px solid {P["border"]};border-radius:3px;
padding:11px 13px;background:{P["panel"]};}}
.mi-vert-name{{font-size:11px;font-weight:700;color:{P["text"]};
letter-spacing:0.04em;text-transform:uppercase;margin-bottom:8px;
min-height:26px;}}
.mi-vert-stat{{display:flex;align-items:baseline;gap:7px;
margin-bottom:8px;}}
.mi-vert-num{{font-family:'JetBrains Mono',monospace;font-size:23px;
font-weight:700;line-height:1;}}
.mi-vert-lbl{{font-size:8.5px;color:{P["text_faint"]};
text-transform:uppercase;letter-spacing:0.06em;line-height:1.15;}}
.mi-vert-row{{display:flex;gap:9px;font-size:10px;color:{P["text_dim"]};
font-family:'JetBrains Mono',monospace;margin-bottom:7px;flex-wrap:wrap;}}
.mi-vert-tk{{font-size:10px;color:{P["text_faint"]};
font-family:'JetBrains Mono',monospace;border-top:1px solid
{P["border_dim"]};padding-top:6px;line-height:1.5;}}
</style>
"""


def _geo_intel_section() -> str:
    """Surface the real-data Geographic Intelligence suite on the market-intel
    page — public-market comps + PE deal flow are one lens; real state/metro
    public data is the other. Pure navigation; renders no figures."""
    border = P["border"]; tp = P["text"]; td = P["text_dim"]
    fa = P.get("text_faint", td); ac = P["accent"]
    links = [
        ("Map", "/geo-map", "shade states by any metric"),
        ("Compare", "/state-compare", "states side by side"),
        ("Rank", "/state-rankings", "all states on one metric"),
        ("Profile", "/state-profile", "one state + national rank"),
        ("Metros", "/metro-markets", "real CBSA demographics"),
        ("Counties", "/county-explorer", "drill into a state"),
    ]
    chips = "".join(
        f'<a href="{href}" style="display:inline-block;background:{P["panel_alt"]};'
        f'border:1px solid {border};border-radius:2px;padding:5px 10px;margin:0 6px 6px 0;'
        f'text-decoration:none;color:{ac};font-family:Inter Tight,sans-serif;font-size:12px">'
        f'{lbl} <span style="color:{fa};font-size:10px">· {hint}</span></a>'
        for lbl, href, hint in links
    )
    # 2026-05-28 batch 34 · Tier-4 trope removal — strip 3px accent.
    return (
        f'<div style="background:{P["panel"]};border:1px solid {border};'
        f'border-radius:2px;padding:14px 16px;margin:0 0 18px">'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:10px;color:{td};'
        f'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">'
        f'Geographic Intelligence · real public data</div>'
        f'<div style="font-size:12px;color:{td};margin-bottom:10px;max-width:72ch">'
        f'The public-market and PE-deal overlay below is one lens; the '
        f'<a href="/geo-intel" style="color:{ac};text-decoration:none;font-weight:600">'
        f'Geographic Intelligence</a> suite is the other — 50 states + DC and 918 metros '
        f'on real Census/ACS · CMS · HRSA · CDC · OIG data (no synthetic values).</div>'
        f'<div>{chips}</div></div>'
    )


def render_market_intel_page(
    *,
    category: Optional[str] = None,
    specialty: Optional[str] = None,
    ev_usd: Optional[float] = None,
    revenue_usd: Optional[float] = None,
    tickers: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
) -> str:
    next_up = ck_next_section(
        "Dig into public-comp + PE deal flow",
        "/market-intel/public-market",
        eyebrow="Up next",
        italic_word="deal",
    )
    # Top-section cleanup: the public-comps hub is the focal point, so it
    # renders immediately under the hero (the old "research reference / mixed
    # data" purpose box was removed — its provenance now lives inside the comps
    # section's own source line). The Geographic Intelligence suite is a
    # secondary nav strip, so it drops below the comps + transactions.
    body = (
        _MI_STYLES
        + _hero(category, specialty)
        + _public_comps_section(
            category, revenue_usd, target_ev_usd=ev_usd,
        )
        + _transaction_multiples_section(specialty, ev_usd)
        + _geo_intel_section()
        + _earnings_calendar_section()
        + _news_section(specialty, tickers, tags)
        + next_up
    )
    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from ._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(
        body, "RCM Diligence — Market Intelligence",
        active_nav="/market-intel",
        subtitle="Public-market + PE transaction overlay",
    )


def transaction_multiples_xlsx() -> bytes:
    """The multiples library as a comps-tab-ready sheet — partners
    paste these bands into deal models; shipping the directory as a
    workbook saves the retyping (and the typos)."""
    from rcm_mc.exports.xlsx_writer import Sheet, write_xlsx
    from rcm_mc.market_intel.transaction_multiples import _load
    data = _load()
    rows: list = [
        [("HEALTHCARE TRANSACTION MULTIPLES — EV/EBITDA", "header")]
        + [("", "header")] * 5,
        [f"Curated from public aggregates · last reviewed "
         f"{data.get('last_reviewed', '')} · verify before IC use."],
        [""],
        [("Specialty", "header"), ("Size band", "header"),
         ("P25", "header"), ("P50", "header"), ("P75", "header"),
         ("n (TTM)", "header")],
    ]
    bands = sorted(data.get("bands") or (),
                   key=lambda r: (str(r.get("specialty", "")),
                                  str(r.get("deal_size_band", ""))))
    for r in bands:
        rows.append([
            str(r.get("specialty", "")).replace("_", " ").title(),
            str(r.get("deal_size_band", "")).replace("_", " "),
            (float(r["p25_ev_ebitda"]), "mult"),
            (float(r["p50_ev_ebitda"]), "mult"),
            (float(r["p75_ev_ebitda"]), "mult"),
            (int(r.get("sample_size_trailing_12_mo", 0) or 0), "num"),
        ])
    return write_xlsx([Sheet("Multiples", rows,
                             col_widths=[30, 16, 9, 9, 9, 9])])
