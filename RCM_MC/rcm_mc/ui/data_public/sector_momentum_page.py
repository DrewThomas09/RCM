"""Sector Momentum — which sectors are growing vs declining in deal activity.

Computes recent 5-year deal count vs prior 5-year count, showing
acceleration/deceleration trends. Also shows MOIC trend by sector.
"""
from __future__ import annotations

import html
import importlib
import math
from collections import defaultdict
from typing import Any, Dict, List, Optional


def _load_corpus() -> List[Dict[str, Any]]:
    from rcm_mc.data_public.deals_corpus import _SEED_DEALS
    deals: List[Dict[str, Any]] = list(_SEED_DEALS)
    for i in range(2, 40):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            key = f"EXTENDED_SEED_DEALS_{i}"
            deals += getattr(mod, key, [])
        except Exception:
            pass
    return deals


from rcm_mc.ui._chartis_kit import P, _MONO, _SANS, chartis_shell, ck_section_header
from rcm_mc.data_public.sector_smoothing import (
    bayesian_smooth,
    fmt_ttv,
    laplace_change_pct,
    safe_change_pct,
    shrinkage_weight,
    total_transaction_value,
)


def _percentile(vals: List[float], p: float) -> Optional[float]:
    if not vals:
        return None
    s = sorted(vals)
    idx = (len(s) - 1) * p / 100
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def _momentum_arrow(change_pct: float) -> str:
    if change_pct >= 50:
        col, sym = P["positive"], "▲▲"
    elif change_pct >= 10:
        col, sym = P["positive"], "▲"
    elif change_pct >= -10:
        col, sym = P["text_dim"], "—"
    elif change_pct >= -50:
        col, sym = P["warning"], "▼"
    else:
        col, sym = P["negative"], "▼▼"
    return f'<span style="font-size:12px;color:{col};font-family:{_MONO}">{sym}</span>'


def _momentum_bar_svg(sectors_data: list, w: int = 280, item_h: int = 20) -> str:
    """Horizontal bar showing recent vs prior count per sector."""
    if not sectors_data:
        return ""
    max_count = max(max(d["recent"], d["prior"]) for d in sectors_data) or 1
    pad_l = 160
    pad_r = 50
    cw = w - pad_l - pad_r
    total_h = len(sectors_data) * item_h + 12

    parts: List[str] = []
    for i, d in enumerate(sectors_data):
        y = i * item_h + 4
        trunc = d["sector"][:24]
        parts.append(f'<text x="{pad_l-4}" y="{y+item_h//2+4}" text-anchor="end" fill="{P["text_dim"]}" font-size="9" font-family="{_SANS}">{html.escape(trunc)}</text>')

        # prior (background, dimmer)
        pw = int(d["prior"] / max_count * cw)
        parts.append(f'<rect x="{pad_l}" y="{y+4}" width="{pw}" height="{item_h-8}" fill="{P["border"]}" opacity="0.6"/>')

        # recent (foreground)
        rw = int(d["recent"] / max_count * cw)
        col = P["positive"] if d["recent"] > d["prior"] else (P["negative"] if d["recent"] < d["prior"] else P["text_dim"])
        parts.append(f'<rect x="{pad_l}" y="{y+6}" width="{rw}" height="{item_h-12}" fill="{col}"/>')

        # labels
        parts.append(f'<text x="{pad_l+max(rw,pw)+4}" y="{y+item_h//2+4}" fill="{col}" font-size="8" font-family="{_MONO}" font-variant-numeric="tabular-nums">{d["recent"]}/{d["prior"]}</text>')

    return f'<svg width="{w}" height="{total_h}">{"".join(parts)}</svg>'


def render_sector_momentum(recent_years: int = 5) -> str:
    corpus = _load_corpus()

    from datetime import date
    current_year = 2024  # use fixed reference year
    recent_cutoff = current_year - recent_years
    prior_cutoff  = recent_cutoff - recent_years

    sector_recent: Dict[str, int] = defaultdict(int)
    sector_prior:  Dict[str, int] = defaultdict(int)
    sector_recent_deals: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    sector_prior_deals:  Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    sector_moic_recent: Dict[str, List[float]] = defaultdict(list)
    sector_moic_prior:  Dict[str, List[float]] = defaultdict(list)

    for d in corpus:
        sec = d.get("sector")
        yr  = d.get("year")
        if not sec or not yr:
            continue
        moic = d.get("realized_moic")
        if yr >= recent_cutoff:
            sector_recent[sec] += 1
            sector_recent_deals[sec].append(d)
            if moic: sector_moic_recent[sec].append(moic)
        elif yr >= prior_cutoff:
            sector_prior[sec] += 1
            sector_prior_deals[sec].append(d)
            if moic: sector_moic_prior[sec].append(moic)

    # Corpus prior for Bayesian smoothing of per-sector MOIC.
    all_recent_moics = [m for moics in sector_moic_recent.values() for m in moics]
    corpus_moic_prior = _percentile(all_recent_moics, 50)

    # build momentum data
    all_sectors = set(sector_recent.keys()) | set(sector_prior.keys())
    momentum_data = []
    for sec in all_sectors:
        recent = sector_recent[sec]
        prior  = sector_prior[sec]
        if recent == 0 and prior == 0:
            continue
        # Phase 3D fixes:
        # - safe_change_pct returns None when prior < 3, so the UI
        #   stops printing "+400%" / "+∞" on a 0→N or 1→N base. The
        #   absolute deal-count delta is shown instead.
        # - laplace_change_pct gives a smooth fallback that works on
        #   zero-base transitions for sorting / momentum-arrow logic.
        change = safe_change_pct(recent, prior)
        change_smooth = laplace_change_pct(recent, prior)
        # Total Transaction Value alongside count: surfaces the
        # capital-deployed signal that pure deal count obscures.
        ttv_recent = total_transaction_value(sector_recent_deals[sec])
        ttv_prior  = total_transaction_value(sector_prior_deals[sec])
        ttv_change_pct = safe_change_pct(ttv_recent, ttv_prior, min_reliable=50)
        # Per-sector MOIC P50, smoothed toward corpus prior with
        # weight inversely proportional to sector sample size.
        raw_moic_recent = _percentile(sector_moic_recent[sec], 50)
        raw_moic_prior  = _percentile(sector_moic_prior[sec], 50)
        n_recent = len(sector_moic_recent[sec])
        n_prior  = len(sector_moic_prior[sec])
        moic_recent_p50 = bayesian_smooth(raw_moic_recent, n_recent, corpus_moic_prior)
        moic_prior_p50  = bayesian_smooth(raw_moic_prior,  n_prior,  corpus_moic_prior)
        momentum_data.append({
            "sector": sec,
            "recent": recent,
            "prior": prior,
            "change_pct": change,
            "change_smooth": change_smooth,
            "ttv_recent": ttv_recent,
            "ttv_prior": ttv_prior,
            "ttv_change_pct": ttv_change_pct,
            "moic_recent": moic_recent_p50,
            "moic_prior": moic_prior_p50,
            "moic_n_recent": n_recent,
            "shrinkage": shrinkage_weight(n_recent),
        })

    # accelerating and decelerating sectors — sort by Laplace-smoothed
    # change so 0→N transitions don't dominate the top of the list.
    momentum_data.sort(key=lambda x: -x["change_smooth"])
    top_growing = momentum_data[:10]
    top_declining = sorted(momentum_data, key=lambda x: x["change_smooth"])[:10]

    def _table(items: list, title: str) -> str:
        rows = ""
        for i, d in enumerate(items):
            bg = P.get("row_stripe", P.get("panel_alt", "#ece6db")) if i % 2 else P["panel"]
            change = d.get("change_pct")
            smooth = d.get("change_smooth", 0)
            col = (
                P["positive"] if smooth > 0
                else P["negative"] if smooth < 0
                else P["text_dim"]
            )
            # When prior base is too thin to support a percent change,
            # show the absolute count delta + a "from N" qualifier so
            # the partner sees the magnitude in honest units.
            if change is None:
                delta = d["recent"] - d["prior"]
                sign = "+" if delta > 0 else ""
                pct_cell = (
                    f'<span style="color:{P.get("warning", "#b8732a")};font-weight:600;">'
                    f'{sign}{delta} deals</span>'
                    f'<div style="font-size:8px;color:{P["text_faint"]};letter-spacing:0;'
                    f'font-family:{_SANS};">from base of {d["prior"]} (low-N)</div>'
                )
            else:
                sign = "+" if change > 0 else ""
                pct_cell = f'{sign}{change:.1f}%'
            # MOIC cells reflect the Bayesian-smoothed estimate; a
            # small "shrunk N%" badge shows how much weight the prior
            # got, so the partner can tell when a P50 is mostly the
            # corpus mean rather than the sector signal.
            shrink_pct = d.get("shrinkage", 0) * 100
            shrink_badge = (
                f' <span style="font-size:8px;color:{P["text_faint"]};font-family:{_MONO};">'
                f'(shrunk {shrink_pct:.1f}%)</span>'
                if shrink_pct >= 30 else ""
            )
            moic_r = (
                f"{d['moic_recent']:.2f}×{shrink_badge}"
                if d.get("moic_recent") is not None else "—"
            )
            moic_p = (
                f"{d['moic_prior']:.2f}×"
                if d.get("moic_prior") is not None else "—"
            )
            ttv_r = fmt_ttv(d["ttv_recent"]) if d.get("ttv_recent") else "—"
            ttv_p = fmt_ttv(d["ttv_prior"])  if d.get("ttv_prior")  else "—"
            rows += (
                f'<tr style="background:{bg}">'
                f'<td style="padding:4px 8px;font-size:11px">{html.escape(d["sector"][:30])}</td>'
                f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{d["recent"]}</td>'
                f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;color:{P["text_dim"]};font-variant-numeric:tabular-nums">{d["prior"]}</td>'
                f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;color:{col};font-variant-numeric:tabular-nums;font-weight:600">{ttv_r}</td>'
                f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;color:{P["text_dim"]};font-variant-numeric:tabular-nums">{ttv_p}</td>'
                f'<td style="padding:4px 8px;font-size:11px;font-family:{_MONO};text-align:right;font-weight:700;color:{col};font-variant-numeric:tabular-nums">{pct_cell}</td>'
                f'<td style="padding:4px 8px;text-align:center">{_momentum_arrow(smooth)}</td>'
                f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;font-variant-numeric:tabular-nums">{moic_r}</td>'
                f'<td style="padding:4px 8px;font-size:10px;font-family:{_MONO};text-align:right;color:{P["text_dim"]};font-variant-numeric:tabular-nums">{moic_p}</td>'
                f'</tr>'
            )

        th = f"padding:4px 8px;font-size:9px;letter-spacing:.08em;color:{P['text_dim']};font-family:{_SANS};border-bottom:1px solid {P.get('border', P.get('rule', '#d6cfc3'))}"
        return f"""<div style="margin-bottom:16px">
<div style="font-size:9px;color:{P['text_dim']};font-family:{_SANS};letter-spacing:.1em;margin-bottom:6px;border-bottom:1px solid {P.get('border', P.get('rule', '#d6cfc3'))};padding-bottom:4px">{html.escape(title)}</div>
<div style="border:1px solid {P.get('border', P.get('rule', '#d6cfc3'))};overflow-x:auto">
<table style="width:100%;border-collapse:collapse">
<thead><tr style="background:{P['panel_alt']}">
  <th style="{th}">SECTOR</th>
  <th style="{th};text-align:right">N (R)</th>
  <th style="{th};text-align:right">N (P)</th>
  <th style="{th};text-align:right">TTV (R)</th>
  <th style="{th};text-align:right">TTV (P)</th>
  <th style="{th};text-align:right">CHANGE</th>
  <th style="{th};text-align:center">MOM</th>
  <th style="{th};text-align:right">MOIC P50 (R)</th>
  <th style="{th};text-align:right">MOIC P50 (P)</th>
</tr></thead>
<tbody>{rows}</tbody>
</table></div></div>"""

    # Use the Laplace-smoothed change for bar-chart inclusion so 0→N
    # transitions still show up but are not the only thing visible.
    bar_data_growing = [
        {"sector": d["sector"], "recent": d["recent"], "prior": d["prior"]}
        for d in top_growing
        if d.get("change_smooth", 0) > 5
    ]

    window_label = f"{recent_cutoff}–{current_year-1} vs {prior_cutoff}–{recent_cutoff-1}"

    # filter links
    filter_links = " ".join(
        f'<a href="/sector-momentum?years={n}" style="font-size:11px;font-family:{_MONO};color:{P["accent"] if recent_years==n else P["text_dim"]};text-decoration:none;padding:3px 8px;border:1px solid {P["border"] if recent_years!=n else P["accent"]}">{n}y window</a>'
        for n in [3, 5, 7, 10]
    )

    body = f"""
<div style="padding:16px 20px;max-width:1200px">
  {ck_section_header("SECTOR MOMENTUM", f"Deal activity acceleration by sector — {len(corpus)} corpus transactions", None)}

  <div style="display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap">
    <span style="font-size:10px;color:{P['text_dim']};font-family:{_SANS}">COMPARISON WINDOW:</span>
    {filter_links}
    <span style="font-size:10px;color:{P['text_faint']};font-family:{_SANS};margin-left:8px">{window_label}</span>
  </div>

  <div style="margin-bottom:8px;font-size:10px;color:{P['text_faint']};font-family:{_SANS};line-height:1.5">
    "Recent" = {recent_cutoff}–{current_year-1}. "Prior" = {prior_cutoff}–{recent_cutoff-1}.
    Change column shows percent change ONLY when prior base ≥ 3 deals — sectors with thinner prior counts surface
    the absolute deal-count delta (e.g. "+4 deals from base of 1") instead of inflated zero-base percentages.
    Sort + momentum arrow use a Laplace-smoothed change that adds 2 pseudo-deals to each end, so 0→N transitions
    don't dominate the leaderboard. TTV = total transaction value (sum of EV) — surfaces capital deployed alongside
    pure deal count. MOIC P50 cells are Bayesian-smoothed toward the corpus prior with a "shrunk X%" badge when the
    prior contributes ≥30% of the displayed value (i.e. when sector N is small).
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
    {_table(top_growing, f"ACCELERATING SECTORS — TOP 10 BY DEAL GROWTH ({window_label})")}
    {_table(top_declining, f"DECELERATING SECTORS — TOP 10 BY DEAL DECLINE ({window_label})")}
  </div>

  {"<div style='background:" + P['panel_alt'] + ";border:1px solid " + P['border'] + ";padding:12px;margin-top:8px'><div style='font-size:9px;color:" + P['text_dim'] + ";font-family:" + _SANS + ";letter-spacing:.08em;margin-bottom:8px'>RECENT vs PRIOR DEAL COUNT — GROWING SECTORS (bar: recent=solid, prior=gray)</div>" + _momentum_bar_svg(bar_data_growing) + "</div>" if bar_data_growing else ""}
</div>"""

    return chartis_shell(body, "Sector Momentum", active_nav="/sector-momentum",
                         subtitle=f"{recent_years}y window — {len(momentum_data)} sectors")
