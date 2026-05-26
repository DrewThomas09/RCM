"""Reusable real-CMS benchmark panels for the physician/quality diligence pages.

Each returns a self-contained HTML string (or "" if the data is absent), with an
honest caveat that it is a national/sector benchmark, not the deal's own figures.
The palette ``P`` is passed in so the panel matches the page's editorial theme.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict


def _hist_cells(items, label_key: str, pct_key: str, P: Dict[str, Any]) -> str:
    cells = ""
    for it in items:
        pct = it.get(pct_key) or 0
        cells += (
            f'<div style="text-align:center;flex:1">'
            f'<div style="font-size:9px;color:{P["text_dim"]};font-family:JetBrains Mono,monospace">{pct:.0f}%</div>'
            f'<div style="height:{max(2, pct):.0f}px;background:{P["accent"]};opacity:0.8;margin:2px 3px 0"></div>'
            f'<div style="font-size:9px;color:{P["text_dim"]};margin-top:2px">{_html.escape(str(it[label_key]))}</div></div>')
    return f'<div style="display:flex;align-items:flex-end;height:60px;max-width:340px">{cells}</div>'


def mips_quality_panel(P: Dict[str, Any]) -> str:
    """Real CMS MIPS physician-quality benchmark (final-score distribution)."""
    try:
        from rcm_mc.data import mips_data as _mips
        s = _mips.mips_score_summary()
        bands = _mips.mips_score_bands()
        if not s.get("n"):
            return ""
        hist = _hist_cells(bands, "band", "pct", P)
        return (
            f'<div style="background:#fff;border:1px solid {P["border"]};'
            f'border-left:3px solid {P["accent"]};padding:14px 16px;margin-bottom:16px">'
            f'<div style="font-size:11px;font-weight:600;letter-spacing:0.08em;'
            f'text-transform:uppercase;color:{P["text_dim"]};margin-bottom:6px">'
            f'Physician quality benchmark · LIVE (CMS MIPS, PY{s.get("performance_year","2023")})</div>'
            f'<p style="font-size:12px;color:{P["text_dim"]};margin:0 0 8px">'
            f'Across <b style="color:{P["text"]}">{s["n"]:,}</b> scored clinicians, '
            f'the median MIPS final score is <b style="color:{P["text"]}">{s["median"]:.1f}</b>/100 '
            f'(mean {s["mean"]:.1f}; IQR {s["p25"]:.1f}–{s["p75"]:.1f}). The real national '
            f'physician quality-performance distribution.</p>{hist}'
            f'<p style="font-size:11px;color:{P["text_dim"]};margin:8px 0 0">'
            f'Real CMS MIPS final-score distribution — a national physician-quality '
            f'benchmark, <b>not</b> this deal’s clinicians and <b>not</b> a payment figure.</p></div>')
    except Exception:
        return ""


def _is_snf_sector(sector: str) -> bool:
    s = (sector or "").lower()
    return any(k in s for k in ("snf", "nursing", "skilled", "long-term care",
                                "ltc", "post-acute"))


def sector_quality_panel(sector: str, P: Dict[str, Any], snf_panel: str = "") -> str:
    """Pick the benchmark that matches the selected sector: the SNF Care Compare
    panel for nursing/post-acute sectors, otherwise the MIPS physician-quality
    benchmark. ``snf_panel`` is the caller's already-built SNF panel HTML."""
    if _is_snf_sector(sector):
        return snf_panel
    return mips_quality_panel(P) or snf_panel


def community_health_panel(P: Dict[str, Any]) -> str:
    """Real CDC PLACES community-health panel — the population-health / social
    ('S' in ESG) backdrop a healthcare deal operates within. Full-population
    model estimates; not this deal's patients. Returns '' if data is absent."""
    try:
        from rcm_mc.data import cdc_places_agg as _places
        s = _places.places_equity_summary()
        nat = s.get("national_prevalence_pct") or {}
        if not nat:
            return ""
        labels = _places.measure_labels()
        border = P["border"]; tprim = P["text"]; tdim = P["text_dim"]
        faint = P.get("text_faint", tdim); acc = P["accent"]
        show = ["obesity", "diabetes", "depression", "uninsured_18_64", "food_insecurity"]
        cards = "".join(
            f'<div style="text-align:center;padding:0 8px">'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:17px;color:{tprim};'
            f'font-variant-numeric:tabular-nums">{nat.get(k,0):.1f}%</div>'
            f'<div style="font-size:9px;color:{tdim}">{_html.escape(labels.get(k,k))}</div></div>'
            for k in show if nat.get(k) is not None
        )
        rel = s.get("release", ""); n_cty = int(s.get("counties", 0))
        return (
            f'<div style="background:#fff;border:1px solid {border};'
            f'border-left:3px solid {acc};padding:14px 16px;margin-bottom:16px">'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:10px;color:{tdim};'
            f'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px">'
            f'Real CDC PLACES community health &mdash; the social / population-health context'
            f'<span style="color:{acc};font-weight:600"> · LIVE</span></div>'
            f'<div style="display:flex;gap:6px;justify-content:space-between">{cards}</div>'
            f'<div style="margin-top:8px;font-size:10px;color:{faint}">'
            f'CDC PLACES {rel} ({n_cty:,} counties, model-based full-population prevalence). '
            f'Real community-health burden &mdash; the ESG "S" / population context, '
            f'NOT this deal\'s patients; the ESG scores below are illustrative.</div></div>')
    except Exception:
        return ""


def data_required_panel(
    P: Dict[str, Any],
    *,
    title: str,
    needed: list,
    template: str = "",
    request_from: str = "",
    activates: str = "",
    guide_hint: str = "",
) -> str:
    """Honest 'Data needed to activate this analysis' panel for USER/DATA
    REQUIRED pages. Renders the required user/deal data, an import-template
    reference, who to request it from, and what the page computes once
    activated — instead of presenting fabricated values as real.

    ``needed`` is a list of (field, description) tuples.
    """
    border = P["border"]; tp = P["text"]; td = P["text_dim"]
    fa = P.get("text_faint", td); ac = P["accent"]
    rows = "".join(
        f'<tr><td style="padding:3px 10px;font-family:JetBrains Mono,monospace;'
        f'font-size:11px;color:{tp};white-space:nowrap">{_html.escape(str(f))}</td>'
        f'<td style="padding:3px 10px;font-size:11px;color:{td}">{_html.escape(str(d))}</td></tr>'
        for f, d in needed
    )
    tmpl = (f'<div style="margin-top:8px;font-size:10px;color:{fa}">Import template: '
            f'<span style="font-family:JetBrains Mono,monospace;color:{td}">{_html.escape(template)}</span>'
            f' &middot; <a href="/import" style="color:{ac};text-decoration:none">Go to import &rarr;</a>'
            f'</div>'
            if template else "")
    req = (f'<div style="font-size:10px;color:{fa};margin-top:2px">Request from: '
           f'{_html.escape(request_from)}</div>' if request_from else "")
    act = (f'<div style="margin-top:8px;font-size:11px;color:{td}"><b style="color:{tp}">Once activated:</b> '
           f'{_html.escape(activates)}</div>' if activates else "")
    gh = (f'<div style="margin-top:6px;font-size:10px;color:{fa}">Ask the Guide: '
          f'<i>{_html.escape(guide_hint)}</i></div>' if guide_hint else "")
    return (
        f'<div style="background:#fff;border:1px solid {border};'
        f'border-left:3px solid {ac};padding:14px 16px;margin-bottom:16px">'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:10px;color:{td};'
        f'text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px">'
        f'Data needed to activate this analysis'
        f'<span style="color:{ac};font-weight:600"> · DATA REQUIRED</span></div>'
        f'<div style="font-size:11px;color:{td};margin-bottom:8px">{_html.escape(title)} has no public-data anchor '
        f'&mdash; it activates on your own deal/fund data. Upload the following (no values are fabricated here):</div>'
        f'<table style="width:100%;border-collapse:collapse">{rows}</table>'
        f'{tmpl}{req}{act}{gh}</div>'
    )
