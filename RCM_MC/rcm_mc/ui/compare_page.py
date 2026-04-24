"""Side-by-side comparison view.

/diligence/compare?left=<fixture>&right=<fixture>

Each side runs the QoR waterfall + KPI bundle + counterfactual
advisor against its fixture, then the page renders them in two
columns with delta badges at the headline-metric level so a
partner can see at a glance which target is stronger on each
dimension.
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ..diligence import ingest_dataset
from ..diligence.benchmarks import (
    CashWaterfallReport, compute_cash_waterfall, compute_kpis,
)
from ..diligence.counterfactual import (
    counterfactual_bridge_lever, run_counterfactuals_from_ccd,
    summarize_ccd_inputs,
)
from ..diligence._pages import AVAILABLE_FIXTURES, _resolve_dataset
from ._chartis_kit import P, chartis_shell
from .power_ui import diff_badge


def _landing_compare() -> str:
    options = "".join(
        f'<option value="{html.escape(n)}">{html.escape(l)}</option>'
        for n, l in AVAILABLE_FIXTURES
    )
    body = (
        f'<div style="padding:24px 0 12px 0;">'
        f'<div style="font-size:11px;color:{P["text_faint"]};letter-spacing:1.5px;'
        f'text-transform:uppercase;margin-bottom:6px;font-weight:600;">'
        f'Side-by-side Compare</div>'
        f'<div style="font-size:22px;color:{P["text"]};font-weight:600;'
        f'margin-bottom:4px;">Pick two fixtures</div>'
        f'<div style="font-size:12px;color:{P["text_dim"]};max-width:680px;'
        f'line-height:1.6;">Compare CCD-derived KPIs, QoR reconciliation, '
        f'counterfactuals, and bridge-lever impact between any two '
        f'targets. Delta badges show which side wins on each '
        f'dimension.</div>'
        f'</div>'
        f'<form method="GET" action="/diligence/compare" '
        f'style="display:grid;grid-template-columns:1fr 1fr auto;gap:12px;'
        f'align-items:end;max-width:760px;margin-top:20px;">'
        f'<div><label style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:600;'
        f'display:block;margin-bottom:4px;">Left</label>'
        f'<select name="left" required style="width:100%;padding:6px 8px;'
        f'background:{P["panel_alt"]};color:{P["text"]};'
        f'border:1px solid {P["border"]};font-family:inherit;">'
        f'<option value="">—</option>{options}</select></div>'
        f'<div><label style="font-size:9px;color:{P["text_faint"]};'
        f'letter-spacing:1.5px;text-transform:uppercase;font-weight:600;'
        f'display:block;margin-bottom:4px;">Right</label>'
        f'<select name="right" required style="width:100%;padding:6px 8px;'
        f'background:{P["panel_alt"]};color:{P["text"]};'
        f'border:1px solid {P["border"]};font-family:inherit;">'
        f'<option value="">—</option>{options}</select></div>'
        f'<button type="submit" style="padding:8px 20px;background:{P["accent"]};'
        f'color:{P["panel"]};border:0;font-size:10px;letter-spacing:1.5px;'
        f'text-transform:uppercase;font-weight:700;cursor:pointer;">Compare</button>'
        f'</form>'
    )
    return chartis_shell(body, "RCM Diligence — Compare",
                        subtitle="Side-by-side comparison")


def _analyse_fixture(name: str) -> Optional[Dict[str, Any]]:
    """Run the full analytic pipeline on one fixture and return the
    shape the renderer consumes."""
    from datetime import date
    p = _resolve_dataset(name)
    if p is None:
        return None
    try:
        ccd = ingest_dataset(p)
    except Exception:  # noqa: BLE001
        return None
    as_of = date(2025, 1, 1)
    try:
        bundle = compute_kpis(ccd, as_of_date=as_of, provider_id=name)
    except Exception:  # noqa: BLE001
        bundle = None
    waterfall: Optional[CashWaterfallReport]
    try:
        waterfall = compute_cash_waterfall(ccd.claims, as_of_date=as_of)
    except Exception:  # noqa: BLE001
        waterfall = None
    ccd_summary = summarize_ccd_inputs(ccd)
    cf_set = run_counterfactuals_from_ccd(ccd, metadata={})
    lever = counterfactual_bridge_lever(cf_set)
    return {
        "name": name,
        "ccd_summary": ccd_summary,
        "bundle": bundle,
        "waterfall": waterfall,
        "counterfactual_set": cf_set,
        "bridge_lever": lever,
    }


def _metric_row(
    label: str,
    left_val: str, right_val: str,
    *,
    badge: str = "",
) -> str:
    return (
        f'<tr><td style="padding:7px 10px;color:{P["text_dim"]};'
        f'font-size:11px;">{html.escape(label)}</td>'
        f'<td class="num" style="padding:7px 10px;text-align:right;'
        f'color:{P["text"]};font-family:\'JetBrains Mono\',monospace;">'
        f'{left_val}</td>'
        f'<td style="padding:7px 10px;text-align:center;">{badge}</td>'
        f'<td class="num" style="padding:7px 10px;text-align:right;'
        f'color:{P["text"]};font-family:\'JetBrains Mono\',monospace;">'
        f'{right_val}</td></tr>'
    )


def _render_comparison(
    left: Dict[str, Any], right: Dict[str, Any],
) -> str:
    ls = left["ccd_summary"]
    rs = right["ccd_summary"]
    lw = left.get("waterfall")
    rw = right.get("waterfall")
    ll = left.get("bridge_lever")
    rl = right.get("bridge_lever")
    lcf = left.get("counterfactual_set")
    rcf = right.get("counterfactual_set")

    # Core metrics.
    rows: List[str] = []

    def claim_row(label: str, lv, rv, fmt="${:,.0f}", higher_better=True):
        lnum = float(lv) if lv is not None else 0.0
        rnum = float(rv) if rv is not None else 0.0
        return _metric_row(
            label,
            fmt.format(lnum), fmt.format(rnum),
            badge=diff_badge(
                lnum, rnum, format_spec=",.0f",
                unit="$" if fmt.startswith("${") else "",
                higher_is_better=higher_better,
            ),
        )

    rows.append(_metric_row(
        "Claims in CCD",
        f"{ls.get('claim_count', 0):,}",
        f"{rs.get('claim_count', 0):,}",
        badge=diff_badge(
            ls.get("claim_count", 0), rs.get("claim_count", 0),
            format_spec=",.0f", unit="", higher_is_better=True,
        ),
    ))
    rows.append(claim_row(
        "Total paid",
        ls.get("total_paid_usd", 0), rs.get("total_paid_usd", 0),
        fmt="${:,.0f}", higher_better=True,
    ))
    # Lower OON share is better (less NSA exposure).
    loons = float(ls.get("oon_share") or 0) * 100
    roons = float(rs.get("oon_share") or 0) * 100
    rows.append(_metric_row(
        "OON share",
        f"{loons:.1f}%", f"{roons:.1f}%",
        badge=diff_badge(loons, roons, format_spec=".1f",
                         unit="pp", higher_is_better=False),
    ))
    rows.append(claim_row(
        "HOPD revenue",
        ls.get("hopd_revenue_usd", 0), rs.get("hopd_revenue_usd", 0),
        fmt="${:,.0f}", higher_better=True,
    ))

    # Waterfall roll-up if available.
    if lw and rw:
        rows.append(claim_row(
            "Gross charges",
            lw.total_gross_charges_usd, rw.total_gross_charges_usd,
            higher_better=True,
        ))
        rows.append(claim_row(
            "Realized cash",
            lw.total_realized_cash_usd, rw.total_realized_cash_usd,
            higher_better=True,
        ))
        lrr = (lw.total_realization_rate or 0) * 100
        rrr = (rw.total_realization_rate or 0) * 100
        rows.append(_metric_row(
            "Realization rate",
            f"{lrr:.1f}%", f"{rrr:.1f}%",
            badge=diff_badge(lrr, rrr, format_spec=".1f",
                             unit="pp", higher_is_better=True),
        ))
        lacc = lw.total_accrual_revenue_usd or 0
        racc = rw.total_accrual_revenue_usd or 0
        rows.append(claim_row(
            "Accrual revenue",
            lacc, racc, higher_better=True,
        ))

    # Counterfactual bridge impact.
    if ll and rl:
        rows.append(claim_row(
            "Bridge lever (counterfactual)",
            ll.ebitda_impact_usd, rl.ebitda_impact_usd,
            higher_better=True,
        ))
    if lcf and rcf:
        rows.append(_metric_row(
            "Counterfactuals identified",
            str(len(lcf.items)), str(len(rcf.items)),
            badge=diff_badge(
                len(lcf.items), len(rcf.items),
                format_spec=",.0f", unit="", higher_is_better=False,
            ),
        ))

    table_html = (
        f'<table style="width:100%;border-collapse:collapse;'
        f'font-size:12px;margin-top:12px;">'
        f'<thead><tr style="color:{P["text_faint"]};'
        f'font-size:9px;letter-spacing:1.5px;text-transform:uppercase;">'
        f'<th style="text-align:left;padding:6px 10px;'
        f'border-bottom:1px solid {P["border"]};">Metric</th>'
        f'<th style="text-align:right;padding:6px 10px;'
        f'border-bottom:1px solid {P["border"]};">{html.escape(left["name"])}</th>'
        f'<th style="text-align:center;padding:6px 10px;'
        f'border-bottom:1px solid {P["border"]};">Δ</th>'
        f'<th style="text-align:right;padding:6px 10px;'
        f'border-bottom:1px solid {P["border"]};">{html.escape(right["name"])}</th>'
        f'</tr></thead><tbody>{"".join(rows)}</tbody></table>'
    )

    # Two per-side detail columns for the counterfactual summary.
    def col(side_data: Dict[str, Any], label: str) -> str:
        name = side_data["name"]
        cf_set = side_data["counterfactual_set"]
        lever = side_data["bridge_lever"]
        items_html = ""
        if cf_set and cf_set.items:
            items_html = "<ul style='margin:0;padding-left:18px;"\
                "font-size:11px;color:" + P["text_dim"] + ";'>" + "".join(
                f'<li style="margin:4px 0;">'
                f'<strong style="color:{P["text"]};">{html.escape(c.module)}</strong> · '
                f'{html.escape(c.target_band)} · '
                f'{html.escape(c.lever)}</li>'
                for c in cf_set.items
            ) + "</ul>"
        else:
            items_html = (
                f'<div style="font-size:11px;color:{P["text_faint"]};'
                f'font-style:italic;padding:6px 0;">No counterfactuals '
                f'(no RED/CRITICAL findings found).</div>'
            )
        return (
            f'<div class="rcm-compare-col">'
            f'<div class="rcm-compare-col-head">'
            f'<div><div class="rcm-compare-col-label">{html.escape(label)}</div>'
            f'<div class="rcm-compare-col-title">{html.escape(name)}</div></div>'
            f'<span style="font-size:10px;color:{P["text_faint"]};'
            f'letter-spacing:1px;text-transform:uppercase;">'
            f'{lever.confidence if lever else "—"}</span>'
            f'</div>'
            f'<div style="font-size:9px;color:{P["text_faint"]};'
            f'letter-spacing:1.5px;text-transform:uppercase;font-weight:600;'
            f'margin-bottom:6px;">Counterfactuals</div>'
            f'{items_html}'
            f'</div>'
        )

    grid = (
        f'<div class="rcm-compare-grid">{col(left, "Left")}{col(right, "Right")}</div>'
    )

    # Plain-English delta narrative — compare the two headline metrics
    # and tell the partner which fixture looks stronger.
    l_paid = float(left["ccd_summary"].get("total_paid_usd", 0) or 0)
    r_paid = float(right["ccd_summary"].get("total_paid_usd", 0) or 0)
    l_oon = float(left["ccd_summary"].get("oon_share", 0) or 0)
    r_oon = float(right["ccd_summary"].get("oon_share", 0) or 0)
    if l_paid == 0 and r_paid == 0:
        delta_narrative = "Both fixtures have zero paid amounts — check source data."
    else:
        paid_delta_pct = (
            (l_paid - r_paid) / max(r_paid, 1) * 100
        ) if r_paid > 0 else 0
        oon_delta_pp = (l_oon - r_oon) * 100
        bits: List[str] = []
        if abs(paid_delta_pct) >= 5:
            bigger = left["name"] if l_paid > r_paid else right["name"]
            bits.append(
                f"{html.escape(bigger)} collects "
                f"{abs(paid_delta_pct):.0f}% more revenue"
            )
        if abs(oon_delta_pp) >= 2:
            more_oon = left["name"] if l_oon > r_oon else right["name"]
            bits.append(
                f"{html.escape(more_oon)} has {abs(oon_delta_pp):.1f} "
                f"pp more OON exposure (NSA risk)"
            )
        if not bits:
            delta_narrative = (
                "Both fixtures are materially similar — no single "
                "driver shifts the relative attractiveness."
            )
        else:
            delta_narrative = "; ".join(bits) + "."

    hero = (
        f'<div data-rcm-title style="padding:24px 0 12px 0;">'
        f'<div style="font-size:11px;color:{P["text_faint"]};letter-spacing:1.5px;'
        f'text-transform:uppercase;margin-bottom:6px;font-weight:600;">'
        f'Compare</div>'
        f'<div style="font-size:22px;color:{P["text"]};font-weight:600;">'
        f'{html.escape(left["name"])} <span style="color:{P["text_dim"]};'
        f'margin:0 10px;">vs</span> {html.escape(right["name"])}</div>'
        f'<div style="background:{P["panel_alt"]};border-left:3px solid '
        f'{P["accent"]};padding:10px 14px;margin-top:12px;font-size:12px;'
        f'color:{P["text_dim"]};line-height:1.6;max-width:880px;'
        f'border-radius:0 3px 3px 0;">'
        f'<strong style="color:{P["text"]};">What this shows: </strong>'
        f'{delta_narrative}</div>'
        f'<div style="background:{P["panel_alt"]};border-left:3px solid '
        f'{P["accent"]};padding:10px 14px;margin-top:8px;font-size:12px;'
        f'color:{P["text_dim"]};line-height:1.6;max-width:880px;'
        f'border-radius:0 3px 3px 0;">'
        f'<strong style="color:{P["text"]};">How to read: </strong>'
        f'Green/red badges next to each metric show the delta — green '
        f'means the left fixture is favorable on that metric, red '
        f'means unfavorable. "Higher is better" differs by metric '
        f'(e.g., total paid = higher better; OON share = lower better).'
        f'</div>'
        f'<div style="font-size:11px;color:{P["text_faint"]};margin-top:8px;">'
        f'Press <kbd style="padding:1px 6px;background:{P["panel_alt"]};'
        f'border:1px solid {P["border"]};border-radius:2px;font-family:inherit;">b</kbd> '
        f'to bookmark this comparison · '
        f'<kbd style="padding:1px 6px;background:{P["panel_alt"]};'
        f'border:1px solid {P["border"]};border-radius:2px;font-family:inherit;">⌘K</kbd> '
        f'to jump elsewhere</div>'
        f'</div>'
    )
    return chartis_shell(
        hero + table_html + grid,
        f"Compare — {left['name']} vs {right['name']}",
        subtitle="Side-by-side",
    )


def render_compare_page(
    left: str = "", right: str = "",
) -> str:
    if not (left and right):
        return _landing_compare()
    left_data = _analyse_fixture(left)
    right_data = _analyse_fixture(right)
    if not (left_data and right_data):
        return chartis_shell(
            f'<div style="padding:24px;color:{P["negative"]};">'
            f'Unable to resolve one of the fixtures. '
            f'<a href="/diligence/compare" style="color:{P["accent"]};">'
            f'Back to picker</a>.</div>',
            "Compare",
        )
    return _render_comparison(left_data, right_data)
