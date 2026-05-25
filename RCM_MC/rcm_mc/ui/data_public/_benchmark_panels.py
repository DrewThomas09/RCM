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
            f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
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
