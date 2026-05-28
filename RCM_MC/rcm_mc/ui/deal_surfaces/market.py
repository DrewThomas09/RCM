"""Surface 10 · Market — local-market structure (HHI, share, payer mix).

Wired to real HCRIS state aggregates. The spec calls for market = CMS
hospital-service-area (HSA), which HCRIS does NOT publish at row level.
This surface uses the target's STATE as the market proxy and labels that
choice in every place a partner reads "market" — no pretense that this
is HSA-level. When CMS HSA crosswalks are vendored in a later phase, the
math here lifts unchanged onto a tighter market definition.

Components shipped (all 5 in the spec; HSA caveat disclosed):
1. Market position panel — moat verdict + 6-row score grid
2. Hero strip            — hospitals in market, total beds, market NPR,
                           HHI, moat score, target share
3. Top competitors       — revenue market-share bar chart (top 8)
4. Regional payer mix    — Medicare / Medicaid / Commercial (state agg)
5. What this means       — verdict prose + cross-links
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional, Tuple

from ._shell import _fmt_int, _fmt_money, _fmt_pct, deal_shell


def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def _panel(eyebrow: str, title: str, body_html: str) -> str:
    return (
        '<section style="background:#fff;border:1px solid #c9c1ac;'
        'padding:20px 22px;margin:0 0 18px;">'
        f'<span style="font-family:var(--sc-mono);font-size:10px;'
        f'letter-spacing:.18em;text-transform:uppercase;color:#1f7a5a;">'
        f'{_html.escape(eyebrow)}</span>'
        f'<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
        f'line-height:1.15;margin:6px 0 14px;color:#15202b;">'
        f'{_html.escape(title)}</h3>'
        f'{body_html}</section>'
    )


def _empty(reason: str) -> str:
    return (
        '<section style="background:#faf6ec;border:1px solid #c9c1ac;'
        'padding:24px 26px;">'
        '<span style="font-family:var(--sc-mono);font-size:10px;'
        'letter-spacing:.18em;text-transform:uppercase;color:#b8842e;">'
        'Market view cannot run</span>'
        '<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
        'margin:6px 0 12px;color:#15202b;">No state on file</h3>'
        f'<p style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;">{_html.escape(reason)} The market view needs '
        'a state to define the (loose) market proxy.</p>'
        '</section>'
    )


# ──────────────────── moat verdict — finite map ────────────────────
def _moat_verdict(hhi: float, target_share: float, n_in_market: int) -> Tuple[str, str, str]:
    """Return (verdict_label, color, prose).

    Finite map of bands — no hallucinated language. HHI thresholds per the
    spec's build note (1500-2500 competitive, 2500+ concentrated).
    """
    if n_in_market < 5:
        return ("No moat — sparse market", "#b8842e",
                "Fewer than 5 hospitals in this market — confidence on every "
                "structural read is low; treat the moat call as provisional.")
    if hhi >= 2500 and target_share >= 0.30:
        return ("Wide moat", "#1f7a5a",
                "Concentrated market AND meaningful target share — the "
                "structural case for pricing power is intact.")
    if hhi >= 1500 and target_share >= 0.15:
        return ("Narrow moat", "#2d8964",
                "Moderately concentrated market AND a top-quartile target share "
                "— some structural advantage, but not exceptional.")
    if hhi < 1500:
        return ("No moat — fragmented", "#b5321e",
                "Market is fragmented; the hospital does not enjoy structural "
                "pricing power. Thesis cannot rest on payer-negotiation upside.")
    return ("No moat — small player", "#b8842e",
            "Market is concentrated but the target is a small player — the "
            "structural moat sits with someone else.")


# ──────────────────── market math ────────────────────
def _build_market(hospital: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build the state-as-market summary from real HCRIS rows.

    Returns None when no state is on file or no peer rows can be matched.
    Every figure in the returned dict is computed from real HCRIS data.
    """
    state = str(hospital.get("state") or "").strip().upper()
    if not state:
        return None
    try:
        from ...data.hcris import _get_latest_per_ccn
    except ImportError:                                # pragma: no cover
        from rcm_mc.data.hcris import _get_latest_per_ccn
    try:
        hdf = _get_latest_per_ccn()
    except Exception:                                  # noqa: BLE001
        return None
    if hdf is None or hdf.empty:
        return None
    state_df = hdf[hdf["state"].astype(str).str.upper() == state]
    if state_df.empty:
        return None
    # Restrict to hospitals with a positive NPR so shares are meaningful
    npr_mask = state_df["net_patient_revenue"].fillna(0) > 0
    market_df = state_df[npr_mask].copy()
    if market_df.empty:
        return None
    market_df = market_df.sort_values("net_patient_revenue", ascending=False)
    total_npr = float(market_df["net_patient_revenue"].sum() or 0.0)
    total_beds = float(market_df["beds"].fillna(0).sum())
    n_in_market = int(len(market_df))
    if total_npr <= 0:
        return None
    # Shares + HHI
    shares = [float(r) / total_npr for r in market_df["net_patient_revenue"]]
    hhi = float(sum(s * s for s in shares) * 10000.0)  # 0..10,000
    # Target's row + share
    target_ccn = str(hospital.get("ccn") or "")
    target_row = market_df[market_df["ccn"].astype(str) == target_ccn]
    if target_row.empty:
        # If the target CCN isn't in the state pool (data missing) treat
        # share as the target's NPR / state total — fall back to the
        # hospital dict's NPR.
        target_npr = _safe_float(hospital.get("net_patient_revenue")) or 0.0
        target_share = target_npr / total_npr if total_npr > 0 else 0.0
    else:
        target_npr = float(target_row.iloc[0]["net_patient_revenue"] or 0.0)
        target_share = target_npr / total_npr
    # Payer mix — state aggregate over patient-day percentages, weighted by
    # patient days so big hospitals don't get over-counted by being uniform.
    medicare_share = None
    medicaid_share = None
    if "medicare_days" in market_df.columns and "total_patient_days" in market_df.columns:
        md_sum = float(market_df["medicare_days"].fillna(0).sum())
        td_sum = float(market_df["total_patient_days"].fillna(0).sum())
        if td_sum > 0:
            medicare_share = md_sum / td_sum
    if "medicaid_days" in market_df.columns and "total_patient_days" in market_df.columns:
        md2 = float(market_df["medicaid_days"].fillna(0).sum())
        td_sum = float(market_df["total_patient_days"].fillna(0).sum())
        if td_sum > 0:
            medicaid_share = md2 / td_sum
    commercial_share = None
    if medicare_share is not None and medicaid_share is not None:
        commercial_share = max(0.0, 1.0 - medicare_share - medicaid_share)
    return {
        "state": state,
        "n_in_market": n_in_market,
        "total_beds": total_beds,
        "total_npr": total_npr,
        "hhi": hhi,
        "target_npr": target_npr,
        "target_share": target_share,
        "medicare_share": medicare_share,
        "medicaid_share": medicaid_share,
        "commercial_share": commercial_share,
        "competitors": market_df.head(8).to_dict("records"),
    }


# ──────────────────── rendering ────────────────────
def _moat_panel(market: Dict[str, Any]) -> str:
    hhi = float(market["hhi"])
    target_share = float(market["target_share"])
    n = int(market["n_in_market"])
    verdict, color, prose = _moat_verdict(hhi, target_share, n)
    # 6-row score grid
    rows = [
        ("HHI",                f"{hhi:,.0f}"),
        ("Market hospitals",   f"{n}"),
        ("Target share",       _fmt_pct(target_share)),
        ("Concentration band", "Concentrated" if hhi >= 2500
                              else ("Competitive" if hhi >= 1500 else "Fragmented")),
        ("Target rank",        f"#{1 + sum(1 for c in market['competitors'] if (float(c.get('net_patient_revenue') or 0)) > market['target_npr'])}"),
        ("Total market NPR",   _fmt_money(market["total_npr"])),
    ]
    grid_cells = "".join(
        '<div style="border:1px solid #ece6d7;padding:10px 12px;background:#faf6ec;">'
        f'<dt style="font-family:var(--sc-mono);font-size:9.5px;'
        f'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;'
        f'margin:0 0 3px;">{_html.escape(label)}</dt>'
        '<dd style="font-family:var(--sc-serif);font-size:16px;margin:0;'
        f'color:#15202b;font-variant-numeric:tabular-nums;">{_html.escape(value)}</dd></div>'
        for label, value in rows
    )
    return (
        '<div style="display:grid;grid-template-columns:1fr 1.4fr;gap:24px;'
        'align-items:start;">'
        '<div>'
        f'<div style="font-family:var(--sc-mono);font-size:10.5px;'
        f'letter-spacing:.18em;text-transform:uppercase;color:#6a7480;'
        f'margin-bottom:6px;">Moat verdict</div>'
        f'<div style="font-family:var(--sc-serif);font-size:30px;font-weight:400;'
        f'line-height:1.1;letter-spacing:-.01em;color:{color};">'
        f'{_html.escape(verdict)}</div>'
        f'<p style="font-family:var(--sc-serif);font-size:13.5px;line-height:1.6;'
        f'color:#2a3a4a;margin:14px 0 0;max-width:42ch;">{_html.escape(prose)}</p>'
        '</div>'
        '<dl style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));'
        f'gap:10px;margin:0;">{grid_cells}</dl>'
        '</div>'
    )


def _hero(market: Dict[str, Any]) -> str:
    hhi = float(market["hhi"])
    band_color = "#1f7a5a" if hhi >= 2500 else (
        "#b8842e" if hhi >= 1500 else "#b5321e")
    rows = [
        ("Hospitals in market", f"{market['n_in_market']:,}"),
        ("Total beds",           _fmt_int(market["total_beds"])),
        ("Market revenue (NPR)", _fmt_money(market["total_npr"])),
        ("HHI",                  f"{hhi:,.0f}"),
        ("Target share",         _fmt_pct(market["target_share"])),
        ("Market proxy",         f"State · {_html.escape(str(market['state']))}"),
    ]
    cells = "".join(
        '<div style="border:1px solid #c9c1ac;background:#faf6ec;padding:12px 14px;">'
        f'<dt style="font-family:var(--sc-mono);font-size:9.5px;'
        f'letter-spacing:.14em;text-transform:uppercase;color:#6a7480;'
        f'margin:0 0 4px;">{_html.escape(label)}</dt>'
        '<dd style="font-family:var(--sc-serif);font-size:20px;margin:0;'
        f'color:#15202b;font-variant-numeric:tabular-nums;">{_html.escape(value)}</dd></div>'
        for label, value in rows
    )
    return (
        '<dl style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));'
        f'gap:12px;margin:0;">{cells}</dl>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        f'color:{band_color};margin:10px 0 0;">'
        'MARKET = THE TARGET\'S STATE (LOOSE PROXY). HCRIS DOES NOT PUBLISH CMS '
        'HSA BOUNDARIES; A TIGHTER MARKET DEFINITION LANDS WHEN HSA CROSSWALKS '
        'ARE VENDORED.</p>'
    )


def _competitors_chart(market: Dict[str, Any], target_ccn: str) -> str:
    total = float(market["total_npr"] or 1.0)
    rows = []
    for i, c in enumerate(market["competitors"]):
        npr = float(c.get("net_patient_revenue") or 0)
        share = npr / total
        bar_w = max(2.0, min(100.0, share * 100.0))
        # Fade by rank per the spec's build note (1.0 → 0.45 at rank 10)
        opacity = max(0.45, 1.0 - i * 0.06)
        is_target = str(c.get("ccn")) == str(target_ccn)
        bar_color = "#1f7a5a" if is_target else "#155752"
        peer_ccn = _html.escape(str(c.get("ccn") or ""), quote=True)
        peer_name = _html.escape(str(c.get("name") or f"CCN {peer_ccn}"))
        rows.append(
            '<div style="display:grid;grid-template-columns:1.8fr 3fr 0.8fr;'
            'gap:14px;align-items:center;padding:6px 0;'
            'border-bottom:1px solid #ece6d7;">'
            f'<div style="font-family:var(--sc-serif);font-size:14px;'
            f'color:{("#154e36" if is_target else "#15202b")};">'
            f'<a href="/deals/{peer_ccn}/profile" style="color:inherit;'
            f'text-decoration:none;">{peer_name}'
            f'{(" · target" if is_target else "")}</a></div>'
            '<div style="background:#f3eddb;border:1px solid #ece6d7;'
            'height:14px;overflow:hidden;">'
            f'<div style="background:{bar_color};opacity:{opacity:.2f};'
            f'height:100%;width:{bar_w:.1f}%;"></div>'
            '</div>'
            '<div style="font-family:var(--sc-mono);font-size:11.5px;'
            'color:#2a3a4a;text-align:right;font-variant-numeric:tabular-nums;">'
            f'{share*100:.1f}%</div></div>'
        )
    return (
        "".join(rows) +
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'TOP 8 BY NPR · TARGET HIGHLIGHTED IN DEEPER GREEN · BARS FADE BY RANK '
        '(SPEC\'S BUILD NOTE).</p>'
    )


def _payer_mix_bar(market: Dict[str, Any]) -> str:
    mc = market.get("medicare_share")
    md = market.get("medicaid_share")
    co = market.get("commercial_share")
    if mc is None and md is None:
        return ('<p style="font-family:var(--sc-serif);font-style:italic;'
                'color:#6a7480;font-size:13px;margin:0;">'
                'No state-aggregate payer-day data available.</p>')
    total = (mc or 0) + (md or 0) + (co or 0)
    if total <= 0:
        return ''
    def _seg(label: str, frac: Optional[float], color: str) -> str:
        if frac is None:
            return ''
        w = frac / total * 100.0
        return (
            f'<div style="flex:0 0 {w:.1f}%;background:{color};color:#fff;'
            f'padding:8px 10px;font-family:var(--sc-mono);font-size:10.5px;'
            f'letter-spacing:.1em;overflow:hidden;white-space:nowrap;">'
            f'{_html.escape(label)} {frac*100:.0f}%</div>'
        )
    return (
        '<div style="display:flex;border:1px solid #c9c1ac;overflow:hidden;">'
        + _seg("Medicare", mc, "#0b2341")
        + _seg("Medicaid", md, "#155752")
        + _seg("Commercial", co, "#5a6f7a")
        + '</div>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'STATE-AGGREGATE PATIENT-DAY MIX · COMMERCIAL = REMAINDER. SAME '
        'PROPORTIONAL-NOT-NORMALIZED RULE AS THE PROFILE SURFACE.</p>'
    )


def _what_this_means(market: Dict[str, Any], ccn: str) -> str:
    hhi = float(market["hhi"])
    target_share = float(market["target_share"])
    verdict, color, prose = _moat_verdict(hhi, target_share, int(market["n_in_market"]))
    ccn_safe = _html.escape(ccn, quote=True)
    return (
        f'<p style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.6;'
        f'color:#2a3a4a;margin:0 0 12px;max-width:60ch;">'
        f'<em style="color:#154e36;font-style:italic;">{_html.escape(verdict)}'
        f' at HHI {hhi:,.0f} and target share {target_share*100:.1f}%.</em> '
        f'{_html.escape(prose)}</p>'
        '<p style="font-family:var(--sc-serif);font-size:13.5px;line-height:1.6;'
        f'color:#2a3a4a;margin:0;">Cross-links: '
        f'<a href="/deals/{ccn_safe}/comp-intel" style="color:#1f7a5a;">'
        'Comp Intel</a> (deeper peer ranks) &middot; '
        f'<a href="/deals/{ccn_safe}/profile" style="color:#1f7a5a;">Profile</a> '
        '(this hospital alone).</p>'
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'VERDICT FROM A FINITE BAND MAP — NEVER A HALLUCINATED MARKET THESIS.</p>'
    )


def render_deal_market(ccn: str, hospital: Dict[str, Any]) -> str:
    """Render Surface 10 (Market) for ``ccn``.

    Uses the target's state as the market proxy — HCRIS doesn't carry CMS
    HSA boundaries, and the surface labels this everywhere a partner would
    read "market."
    """
    market = _build_market(hospital)
    if market is None:
        return deal_shell(
            ccn, hospital, active_slug="market",
            body_html=_empty(
                f"CCN {ccn} has no state on file or HCRIS has no peer hospitals "
                "in that state."),
            page_title=f"Market · {hospital.get('name') or f'CCN {ccn}'}",
        )
    panels = [
        _panel("01 · MARKET POSITION",
               "Moat verdict + scoreboard",
               _moat_panel(market)),
        _panel("02 · HERO",
               "Market size at a glance",
               _hero(market)),
        _panel("03 · TOP COMPETITORS",
               "Revenue market share (top 8 by NPR)",
               _competitors_chart(market, ccn)),
        _panel("04 · REGIONAL PAYER MIX",
               "State-aggregate patient-day breakdown",
               _payer_mix_bar(market)),
        _panel("05 · WHAT THIS MEANS",
               "Verdict + where to drill next",
               _what_this_means(market, ccn)),
    ]
    body = "".join(panels)
    return deal_shell(
        ccn, hospital, active_slug="market", body_html=body,
        page_title=f"Market · {hospital.get('name') or f'CCN {ccn}'}",
    )
