"""Shared Colorado market-context panels (real CIVHC data) for diligence pages.

These render CONTEXTUAL panels — real Colorado all-payer market data that frames
a deal, explicitly NOT provider-specific facility figures. Used by Cost
Structure and Payer Stress. Honest throughout: source + geography + year shown,
missing rendered as "—", and a caveat that Colorado data is market context, not
a national or facility-specific benchmark.
"""
from __future__ import annotations

import html as _html

from rcm_mc.ui._chartis_kit import P, ck_source_purpose


def _panel(title: str, hdr: str, inner: str, caveat: str) -> str:
    # 2026-05-28 batch 33 · Tier-4 trope removal — strip 3px accent.
    return (
        f'<div style="background:{P["panel"]};border:1px solid {P["border"]};'
        f'border-radius:2px;padding:14px 16px;margin-bottom:16px">'
        f'<div style="font-size:11px;font-weight:600;letter-spacing:0.08em;'
        f'text-transform:uppercase;color:{P["text_dim"]};margin-bottom:8px">'
        f'{_html.escape(title)} · CONTEXTUAL (Colorado, CIVHC)</div>'
        f'{hdr}{inner}'
        f'<p style="font-size:11px;color:{P["text_dim"]};margin:8px 0 0">{caveat}</p></div>')


def colorado_cost_context_panel(year: str = "2021", payer_type: str = "All",
                                claim_type: str = "Inpatient") -> str:
    """Real CO per-person-per-year spend by DOI region (cost-of-care). Market
    context only — NOT facility opex."""
    try:
        from rcm_mc.data import payer_data as _pd
        df = _pd.payer_cost_by_geography(year=year, payer_type=payer_type,
                                         claim_type=claim_type)
    except Exception:
        return ""
    if df is None or not len(df):
        return ""
    def _pppy(v):
        return f"${v:,.0f}" if v == v else "—"      # v==v guards NaN

    def _spend(v):
        return f"${v/1e6:,.0f}M" if v == v else "—"
    rows = "".join(
        f'<tr><td style="padding:4px 10px">{_html.escape(str(r.doi_region))}</td>'
        f'<td style="padding:4px 10px;text-align:right;font-variant-numeric:tabular-nums">'
        f'{_pppy(r.pppy)}</td>'
        f'<td style="padding:4px 10px;text-align:right;font-variant-numeric:tabular-nums">'
        f'{_spend(r.total_spend)}</td></tr>'
        for r in df.head(12).itertuples())
    hdr = ck_source_purpose(
        purpose=("Frame a Colorado target's cost base against real all-payer "
                 "per-person-per-year spending by region."),
        universe="cms", confidence="derived",
        source=f"CIVHC / CO APCD Cost of Care ({_html.escape(str(claim_type))}, {_html.escape(str(year))})",
        next_action="Attach a hospital CCN above for real HCRIS facility opex")
    inner = (
        f'<table style="width:100%;border-collapse:collapse;'
        f'font-family:\'JetBrains Mono\',monospace;font-size:11px"><thead>'
        f'<tr style="border-bottom:1px solid {P["border"]};color:{P["text_dim"]}">'
        f'<th style="padding:4px 10px;text-align:left">DOI Region</th>'
        f'<th style="padding:4px 10px;text-align:right">Per-Person-Per-Year</th>'
        f'<th style="padding:4px 10px;text-align:right">Total Spend</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>')
    return _panel(
        "Colorado cost context", hdr, inner,
        "PPPY is all-payer market cost context by region (claim type shown) — "
        "<b>not</b> this facility's operating expense, and Colorado-specific "
        "(do not generalize nationally). Attach a CCN for real HCRIS opex.")


def colorado_payer_pressure_panel() -> str:
    """Real CO payer-pressure context: APM penetration + provider RBP (% of
    Medicare) statewide median. Market context, not provider-specific."""
    try:
        from rcm_mc.data import payer_data as _pd
        apm = _pd.apm_adoption_by_payer("Total Medical Spending")
        rbp = _pd.reference_pricing_summary()
    except Exception:
        return ""
    if (apm is None or not len(apm)) and (rbp is None or not len(rbp)):
        return ""
    bits = []
    if apm is not None and len(apm):
        latest = apm[apm["year"] == apm["year"].max()]
        total = latest[latest["payer"] == "Total"]
        if len(total) and total["pct_apm"].notna().any():
            bits.append(f'Colorado total medical spend in APMs: '
                        f'<b style="color:{P["text"]}">{total["pct_apm"].iloc[0]*100:.0f}%</b> '
                        f'({int(apm["year"].max())})')
    if rbp is not None and len(rbp):
        med = rbp["hospital_pct_medicare"].dropna()
        if len(med):
            bits.append(f'CO provider reimbursement median '
                        f'<b style="color:{P["text"]}">{med.median():.2f}x Medicare</b> '
                        f'(n={int(rbp["organization_name"].nunique())} providers)')
    if not bits:
        return ""
    hdr = ck_source_purpose(
        purpose=("Frame payer pressure with real Colorado market signals — "
                 "value-based-care penetration and commercial-to-Medicare "
                 "reimbursement levels."),
        universe="cms", confidence="derived",
        source="CIVHC / CO APCD — APM + Reference-Based Pricing (public)",
        next_action="Attach a hospital CCN for the target's real HCRIS payer mix")
    inner = ('<ul style="margin:6px 0 0;padding-left:18px;font-size:12px;'
             f'color:{P["text_dim"]};line-height:1.7">'
             + "".join(f"<li>{b}</li>" for b in bits) + "</ul>")
    return _panel(
        "Colorado payer-pressure context", hdr, inner,
        "Market-level Colorado context, <b>not</b> this provider's payer mix or "
        "rates. Attach a hospital CCN above for real HCRIS payer-day mix; do not "
        "generalize Colorado figures nationally.")
