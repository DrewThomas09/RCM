"""EBITDA Bridge Auto-Auditor page.

Route: ``/diligence/bridge-audit``

The demo moment: a banker delivers a $12M synergy bridge; partner
pastes it in the textarea; 200ms later sees "$6.8M realistic,
$5.2M gap, counter at $X — press banker on vendor consolidation,
the largest single overstated lever."

Visualizations partners can't get elsewhere:
    * Claimed vs Realistic bridge comparison (grouped bars)
    * Per-lever audit table with color-coded verdict chips
    * Realization distribution (P25 / median / P75) per lever
    * Counter-bid math block with earn-out alternative
"""
from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from ..diligence.bridge_audit import (
    BridgeAuditReport, BridgeLever, LEVER_PRIORS, LeverAudit,
    LeverVerdict, audit_bridge, parse_bridge_text,
)
from ._chartis_kit import P, chartis_shell
from .power_ui import (
    benchmark_chip, bookmark_hint, deal_context_bar,
    export_json_panel, interpret_callout, provenance, sortable_table,
)


# ────────────────────────────────────────────────────────────────────
# Scoped CSS (ba- prefix)
# ────────────────────────────────────────────────────────────────────

def _scoped_styles() -> str:
    css = """
.ba-wrap{{font-family:"Helvetica Neue",Arial,sans-serif;}}
.ba-eyebrow{{font-size:11px;letter-spacing:1.6px;text-transform:uppercase;
color:{tf};font-weight:600;}}
.ba-h1{{font-size:26px;color:{tx};font-weight:600;line-height:1.15;
margin:4px 0 0 0;letter-spacing:-.2px;}}
.ba-section-label{{font-size:10px;letter-spacing:1.6px;text-transform:uppercase;
font-weight:700;color:{tf};margin:22px 0 10px 0;}}
.ba-panel{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:14px 20px;margin-bottom:16px;}}
.ba-callout{{background:{pa};padding:12px 16px;border-left:3px solid {ac};
border-radius:0 3px 3px 0;font-size:12px;color:{td};line-height:1.65;
max-width:900px;margin-top:12px;}}
.ba-verdict-card{{background:{pn};border:1px solid {bd};border-radius:4px;
padding:18px 22px;margin-top:14px;position:relative;overflow:hidden;}}
.ba-verdict-card::before{{content:"";position:absolute;top:0;left:0;right:0;
height:3px;background:linear-gradient(90deg,var(--tone),{ac});}}
.ba-verdict-OK{{--tone:{po};}}
.ba-verdict-GAP{{--tone:{wn};}}
.ba-verdict-MATERIAL{{--tone:{ne};}}
.ba-verdict-badge{{display:inline-block;padding:4px 12px;border-radius:3px;
font-size:11px;font-weight:700;letter-spacing:1.3px;text-transform:uppercase;
background:var(--tone);color:#fff;}}
.ba-verdict-headline{{font-size:17px;color:{tx};font-weight:600;
line-height:1.45;margin-top:12px;}}
.ba-verdict-rationale{{font-size:12px;color:{td};line-height:1.55;
margin-top:8px;max-width:900px;}}
.ba-verdict-chip{{display:inline-block;padding:3px 9px;border-radius:3px;
font-size:10.5px;font-weight:700;letter-spacing:1.1px;
font-family:"JetBrains Mono",monospace;}}
.ba-chip-REALISTIC{{background:{pa};color:{po};border:1px solid {po};}}
.ba-chip-OVERSTATED{{background:{wn};color:#1a1a1a;}}
.ba-chip-UNSUPPORTED{{background:{ne};color:#fff;}}
.ba-chip-UNDERSTATED{{background:{pa};color:{ac};border:1px solid {ac};}}
.ba-kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
gap:14px;margin-top:14px;}}
.ba-kpi__label{{font-size:9px;letter-spacing:1.3px;text-transform:uppercase;
color:{tf};font-weight:600;margin-bottom:3px;}}
.ba-kpi__val{{font-size:24px;line-height:1;font-family:"JetBrains Mono",monospace;
font-variant-numeric:tabular-nums;font-weight:700;color:{tx};}}
.ba-kpi__val.neg{{color:{ne};}}
.ba-kpi__val.pos{{color:{po};}}
.ba-counter-card{{background:linear-gradient(135deg,{pa} 0%,{pn} 100%);
border:1px solid {po};border-radius:4px;padding:18px 22px;margin-top:14px;}}
.ba-counter-num{{font-size:36px;font-family:"JetBrains Mono",monospace;
font-weight:700;color:{po};line-height:1;}}
.ba-counter-sub{{font-size:12px;color:{td};line-height:1.55;margin-top:8px;
max-width:700px;}}
.ba-form-field label{{display:block;font-size:10px;color:{tf};
letter-spacing:1.2px;text-transform:uppercase;font-weight:600;margin-bottom:4px;}}
.ba-form-field input,.ba-form-field textarea{{width:100%;
background:{pa};color:{tx};border:1px solid {bd};padding:8px 10px;
border-radius:3px;font-family:"JetBrains Mono",monospace;font-size:13px;}}
.ba-form-field textarea{{min-height:140px;resize:vertical;line-height:1.6;}}
.ba-form-submit{{margin-top:18px;padding:10px 20px;background:{ac};
color:#fff;border:0;border-radius:3px;font-size:12px;letter-spacing:1.3px;
text-transform:uppercase;font-weight:700;cursor:pointer;}}
.ba-form-submit:hover{{filter:brightness(1.15);}}
.ba-form-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
gap:14px;}}
""".format(
        tx=P["text"], td=P["text_dim"], tf=P["text_faint"],
        pn=P["panel"], pa=P["panel_alt"],
        bd=P["border"], ac=P["accent"],
        po=P["positive"], wn=P["warning"], ne=P["negative"],
    )
    return f"<style>{css}</style>"


# ────────────────────────────────────────────────────────────────────
# Claimed-vs-realistic bridge chart (horizontal grouped bars)
# ────────────────────────────────────────────────────────────────────

def _bridge_comparison_chart(
    report: BridgeAuditReport,
    width: int = 920, height: int = 360,
) -> str:
    if not report.per_lever:
        return ""
    levers = sorted(
        report.per_lever,
        key=lambda a: -a.claimed_usd,
    )
    max_val = max(
        max(a.claimed_usd for a in levers),
        max(a.realistic_p75_usd for a in levers),
        1.0,
    )

    pad_l, pad_r, pad_t, pad_b = 240, 140, 30, 30
    inner_w = max(1, width - pad_l - pad_r)
    inner_h = max(1, height - pad_t - pad_b)
    row_h = inner_h / max(len(levers), 1)
    bar_h = row_h * 0.38

    def x(v: float) -> float:
        return pad_l + (v / max_val) * inner_w

    rows: List[str] = []
    for i, a in enumerate(levers):
        y0 = pad_t + i * row_h + row_h / 2 - bar_h - 2
        y1 = pad_t + i * row_h + row_h / 2 + 2

        # Label
        label = a.lever.name[:32]
        if len(a.lever.name) > 32:
            label += "…"
        tone_lbl = {
            LeverVerdict.REALISTIC: P["text"],
            LeverVerdict.OVERSTATED: P["warning"],
            LeverVerdict.UNSUPPORTED: P["negative"],
            LeverVerdict.UNDERSTATED: P["accent"],
        }[a.verdict]
        rows.append(
            f'<text x="{pad_l - 10}" y="{pad_t + i * row_h + row_h / 2 + 4:.1f}" '
            f'text-anchor="end" font-size="11" '
            f'fill="{tone_lbl}" font-weight="600">'
            f'{html.escape(label)}</text>'
        )

        # Claimed (banker) bar
        claimed_w = x(a.claimed_usd) - pad_l
        rows.append(
            f'<rect x="{pad_l}" y="{y0:.1f}" '
            f'width="{claimed_w:.1f}" height="{bar_h:.1f}" '
            f'fill="{P["text_faint"]}" opacity="0.85">'
            f'<title>Claimed: ${a.claimed_usd/1e6:.2f}M</title>'
            f'</rect>'
        )
        rows.append(
            f'<text x="{pad_l + claimed_w + 6:.1f}" y="{y0 + bar_h * 0.75:.1f}" '
            f'font-size="10" fill="{P["text_faint"]}" '
            f'font-family="JetBrains Mono,monospace">'
            f'${a.claimed_usd/1e6:.1f}M</text>'
        )

        # Realistic range (P25–P75 band) + median marker
        p25_x = x(a.realistic_p25_usd)
        p75_x = x(a.realistic_p75_usd)
        med_x = x(a.realistic_median_usd)
        tone_bar = {
            LeverVerdict.REALISTIC: P["positive"],
            LeverVerdict.OVERSTATED: P["warning"],
            LeverVerdict.UNSUPPORTED: P["negative"],
            LeverVerdict.UNDERSTATED: P["accent"],
        }[a.verdict]
        rows.append(
            f'<rect x="{p25_x:.1f}" y="{y1:.1f}" '
            f'width="{max(1, p75_x - p25_x):.1f}" '
            f'height="{bar_h:.1f}" '
            f'fill="{tone_bar}" opacity="0.35"/>'
        )
        rows.append(
            f'<line x1="{med_x:.1f}" y1="{y1:.1f}" '
            f'x2="{med_x:.1f}" y2="{y1 + bar_h:.1f}" '
            f'stroke="{tone_bar}" stroke-width="2.5">'
            f'<title>Realistic median: ${a.realistic_median_usd/1e6:.2f}M</title>'
            f'</line>'
        )
        rows.append(
            f'<text x="{pad_l + inner_w + 6}" y="{y1 + bar_h * 0.75:.1f}" '
            f'font-size="10" fill="{tone_bar}" '
            f'font-family="JetBrains Mono,monospace" font-weight="600">'
            f'${a.realistic_median_usd/1e6:.1f}M</text>'
        )

    # Legend
    legend = (
        f'<g transform="translate({pad_l}, 10)">'
        f'<rect width="12" height="8" fill="{P["text_faint"]}" opacity="0.85"/>'
        f'<text x="18" y="8" font-size="11" '
        f'fill="{P["text"]}">Banker claim</text>'
        f'<rect x="120" width="12" height="8" fill="{P["positive"]}" opacity="0.35"/>'
        f'<text x="138" y="8" font-size="11" '
        f'fill="{P["text"]}">Realistic P25-P75</text>'
        f'<line x1="270" y1="0" x2="270" y2="8" stroke="{P["positive"]}" stroke-width="2.5"/>'
        f'<text x="278" y="8" font-size="11" '
        f'fill="{P["text"]}">Realistic median</text>'
        f'</g>'
    )

    return (
        f'<svg viewBox="0 0 {width} {height}" '
        f'width="100%" style="max-width:{width}px;height:auto;" '
        f'role="img" aria-label="Claimed vs realistic bridge">'
        f'<rect x="0" y="0" width="{width}" height="{height}" '
        f'fill="{P["panel"]}"/>'
        + legend + "".join(rows)
        + '</svg>'
    )


# ────────────────────────────────────────────────────────────────────
# Composed blocks
# ────────────────────────────────────────────────────────────────────

def _verdict_card(report: BridgeAuditReport) -> str:
    gap_pct = report.gap_pct
    if gap_pct > 0.25 or report.unsupported_count >= 2:
        verdict = "MATERIAL"
        plain = (
            "Material gap between banker claim and realistic "
            "realization. Partners should not accept the bridge "
            "at face value — counter on price or insist on an "
            "earn-out structured on the overstated levers."
        )
        plain_tone = "bad"
    elif gap_pct > 0.10:
        verdict = "GAP"
        plain = (
            "Moderate gap. The bridge overshoots realistic "
            "outcomes by a meaningful margin — worth a negotiation "
            "round but not a walk."
        )
        plain_tone = "warn"
    else:
        verdict = "OK"
        plain = (
            "Bridge clears audit. The banker's synergy claims "
            "fall inside the realistic P25-P75 band across levers."
        )
        plain_tone = "good"

    # Benchmark chip for realization %
    if report.claimed_bridge_usd > 0:
        realization_pct = (
            report.realistic_bridge_usd / report.claimed_bridge_usd * 100
        )
    else:
        realization_pct = 100.0
    realization_chip = benchmark_chip(
        value=realization_pct,
        peer_low=60.0,
        peer_high=90.0,
        higher_is_better=True,
        format_spec=".0f",
        suffix="%",
        label="Bridge Realization",
        peer_label="PE healthcare band",
    )

    gap_val = provenance(
        f"${report.gap_usd/1e6:+,.1f}M",
        source="Audit engine",
        formula="Σ (claimed - realistic_median) across levers",
        detail=(
            "Gap > 0 = banker overclaims; gap < 0 = sandbagging. "
            "Bridge gap × entry multiple = price-reduction ask."
        ),
    )

    return (
        f'<div class="ba-verdict-card ba-verdict-{verdict}">'
        f'<div class="ba-verdict-badge">{verdict}</div>'
        f'<div class="ba-verdict-headline">'
        f'{html.escape(report.headline)}</div>'
        f'<div class="ba-verdict-rationale">'
        f'{html.escape(report.rationale)}</div>'
        + interpret_callout("Plain-English read:", plain, tone=plain_tone)
        + f'<div style="margin-top:16px;">{realization_chip}</div>'
        + f'<div class="ba-kpi-grid">'
        f'  <div><div class="ba-kpi__label">Banker Claim</div>'
        f'       <div class="ba-kpi__val">'
        f'${report.claimed_bridge_usd/1e6:.1f}M</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">total sell-side bridge</div></div>'
        f'  <div><div class="ba-kpi__label">Realistic (P50)</div>'
        f'       <div class="ba-kpi__val pos">'
        f'${report.realistic_bridge_usd/1e6:.1f}M</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">P25 ${report.realistic_bridge_p25_usd/1e6:.1f}M – '
        f'P75 ${report.realistic_bridge_p75_usd/1e6:.1f}M</div></div>'
        f'  <div><div class="ba-kpi__label">Gap</div>'
        f'       <div class="ba-kpi__val '
        f'{"neg" if report.gap_usd > 0 else "pos"}">{gap_val}</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">{report.gap_pct*100:+.0f}% of claim</div></div>'
        f'  <div><div class="ba-kpi__label">Levers Audited</div>'
        f'       <div class="ba-kpi__val">{len(report.per_lever)}</div>'
        f'       <div style="font-size:10px;color:{P["text_faint"]};'
        f'margin-top:3px;">'
        f'{report.overstated_count} overstated · '
        f'{report.unsupported_count} unsupported · '
        f'{report.realistic_count} realistic</div></div>'
        f'</div>'
        f'</div>'
    )


def _counter_bid_card(report: BridgeAuditReport) -> str:
    if (
        not report.entry_multiple
        or not report.asking_price_usd
        or report.price_reduction_usd is None
        or report.price_reduction_usd < 1_000_000
    ):
        return ""
    return (
        f'<div class="ba-counter-card">'
        f'<div style="font-size:11px;letter-spacing:1.5px;'
        f'text-transform:uppercase;color:{P["text_faint"]};'
        f'font-weight:700;">Counter-bid recommendation</div>'
        f'<div class="ba-counter-num">'
        f'${report.counter_offer_usd/1e6:,.0f}M</div>'
        f'<div class="ba-counter-sub">'
        f'Banker asking '
        f'<strong style="color:{P["text"]};">'
        f'${report.asking_price_usd/1e6:,.0f}M</strong> at '
        f'{report.entry_multiple:.1f}× — our audit shows '
        f'${report.gap_usd/1e6:,.1f}M of realistic bridge gap. '
        f'At the entry multiple, that prices out to '
        f'<strong style="color:{P["negative"]};">'
        f'${report.price_reduction_usd/1e6:,.1f}M of overpayment</strong>. '
        f'Counter at '
        f'<strong style="color:{P["positive"]};">'
        f'${report.counter_offer_usd/1e6:,.0f}M</strong>, or structure '
        f'<strong>${(report.earn_out_target_usd or 0)/1e6:,.1f}M as a 24-month '
        f'earn-out</strong> triggered at '
        f'<strong>${(report.earn_out_trigger_usd or 0)/1e6:,.1f}M</strong> '
        f'LTM EBITDA to preserve bid competitiveness while shifting '
        f'the realization risk back to the seller.'
        f'</div></div>'
    )


def _per_lever_table(report: BridgeAuditReport) -> str:
    headers = [
        "Lever", "Category", "Verdict",
        "Claimed", "Realistic (P50)", "Gap",
        "Realization %", "Fail Rate", "Months",
    ]
    rows = []
    sort_keys = []

    def _chip(v: str) -> str:
        return (
            f'<span class="ba-verdict-chip ba-chip-{v}">'
            f'{v}</span>'
        )

    def _colored(text: str, color: str) -> str:
        return (
            f'<span style="color:{color};font-weight:700;">'
            f'{html.escape(text)}</span>'
        )

    for a in sorted(report.per_lever, key=lambda x: -x.claimed_usd):
        # Gap color: red if banker overclaims materially, green if sandbag
        if a.gap_usd > a.claimed_usd * 0.25:
            gap_color = P["negative"]
        elif a.gap_usd > a.claimed_usd * 0.05:
            gap_color = P["warning"]
        elif a.gap_usd < -a.claimed_usd * 0.05:
            gap_color = P["positive"]
        else:
            gap_color = P["text_dim"]

        realization_pct = a.adjusted_realization_median * 100
        realization_color = (
            P["positive"] if realization_pct >= 80
            else P["warning"] if realization_pct >= 50
            else P["negative"]
        )
        fail_pct = a.failure_rate * 100
        fail_color = (
            P["negative"] if fail_pct >= 40
            else P["warning"] if fail_pct >= 25
            else P["positive"]
        )

        rows.append([
            html.escape(a.lever.name),
            html.escape(a.category_label),
            _chip(a.verdict.value),
            f"${a.claimed_usd/1e6:,.2f}M",
            f"${a.realistic_median_usd/1e6:,.2f}M",
            _colored(f"${a.gap_usd/1e6:+,.2f}M", gap_color),
            _colored(f"{realization_pct:.0f}%", realization_color),
            _colored(f"{fail_pct:.0f}%", fail_color),
            str(a.duration_months_median),
        ])
        sort_keys.append([
            a.lever.name, a.category.value, a.verdict.value,
            a.claimed_usd, a.realistic_median_usd, a.gap_usd,
            realization_pct, fail_pct, a.duration_months_median,
        ])

    return sortable_table(
        headers, rows, sort_keys=sort_keys,
        name="bridge_audit_per_lever",
        caption=(
            "Each row one lever · color-coded by audit verdict · "
            "click any column to sort · CSV export auto-wired"
        ),
    )


def _per_lever_narrative_block(report: BridgeAuditReport) -> str:
    """Expanded per-lever narrative block — each lever gets a small
    card with the audit's plain-English reasoning + a 'claim vs
    peer median' bar chip so first-time readers see the relative
    overshoot at a glance."""
    cards: List[str] = []
    for a in sorted(report.per_lever, key=lambda x: -x.gap_usd):
        tone_border = {
            LeverVerdict.REALISTIC: P["positive"],
            LeverVerdict.OVERSTATED: P["warning"],
            LeverVerdict.UNSUPPORTED: P["negative"],
            LeverVerdict.UNDERSTATED: P["accent"],
        }[a.verdict]

        # Claim vs peer-median bar. Shows how many % of the
        # realistic median the banker's claim represents.
        # 100% = perfect match. >100% = banker overclaims.
        if a.realistic_median_usd > 0:
            pct_vs_median = (
                a.claimed_usd / a.realistic_median_usd * 100
            )
        else:
            pct_vs_median = 0.0
        bar_pct = min(200.0, max(0.0, pct_vs_median))
        bar_color = (
            P["negative"] if pct_vs_median >= 150
            else P["warning"] if pct_vs_median >= 115
            else P["positive"] if pct_vs_median >= 85
            else P["accent"]
        )
        pct_verdict_text = (
            "overclaims peer median" if pct_vs_median >= 115
            else "below peer median (sandbag?)"
            if pct_vs_median < 85 else
            "at peer median"
        )
        vs_bar = (
            f'<div style="margin-top:10px;">'
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:10px;color:{P["text_faint"]};'
            f'letter-spacing:1.1px;text-transform:uppercase;'
            f'font-weight:700;margin-bottom:3px;">'
            f'<span>Claim vs peer median</span>'
            f'<span style="color:{bar_color};">'
            f'{pct_vs_median:.0f}% · {pct_verdict_text}</span>'
            f'</div>'
            f'<div style="background:{P["panel_alt"]};'
            f'border-radius:3px;height:8px;position:relative;'
            f'overflow:hidden;">'
            f'<div style="position:absolute;left:0;top:0;'
            f'height:100%;width:{bar_pct/2:.1f}%;'
            f'background:{bar_color};opacity:0.85;"></div>'
            f'<div style="position:absolute;left:50%;top:-2px;'
            f'bottom:-2px;width:2px;background:{P["text_faint"]};'
            f'opacity:0.8;" title="100% peer median"></div>'
            f'</div>'
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:9px;color:{P["text_faint"]};'
            f'font-family:\'JetBrains Mono\',monospace;margin-top:2px;">'
            f'<span>0%</span><span>peer median</span><span>200%</span>'
            f'</div>'
            f'</div>'
        )

        cards.append(
            f'<div style="background:{P["panel"]};'
            f'border:1px solid {P["border"]};'
            f'border-left:3px solid {tone_border};'
            f'border-radius:0 3px 3px 0;padding:12px 16px;'
            f'margin-bottom:10px;">'
            f'<div style="display:flex;gap:12px;'
            f'justify-content:space-between;align-items:baseline;'
            f'flex-wrap:wrap;">'
            f'<div style="font-size:14px;color:{P["text"]};'
            f'font-weight:600;">{html.escape(a.lever.name)}</div>'
            f'<span class="ba-verdict-chip ba-chip-{a.verdict.value}">'
            f'{a.verdict.value}</span>'
            f'</div>'
            f'<div style="font-size:10.5px;color:{P["text_faint"]};'
            f'text-transform:uppercase;letter-spacing:1.1px;'
            f'margin-top:4px;">'
            f'{html.escape(a.category_label)} · '
            f'median realization {a.adjusted_realization_median*100:.0f}% · '
            f'{a.failure_rate*100:.0f}% fail rate · '
            f'{a.duration_months_median}-month ramp</div>'
            + vs_bar
            + f'<div style="font-size:12.5px;color:{P["text_dim"]};'
            f'line-height:1.65;margin-top:8px;">'
            f'{html.escape(a.narrative)}</div>'
            f'</div>'
        )
    return "".join(cards)


def _lever_library_panel() -> str:
    """Reference panel showing the full library of realization
    priors — partners use this to sanity-check the audit's math
    and for the 'how did you get that number?' question."""
    headers = [
        "Category", "Label", "Median Realized",
        "P25 – P75", "Fail Rate", "N", "Ramp (mo)",
    ]
    rows = []
    sort_keys = []
    for p in sorted(LEVER_PRIORS, key=lambda x: -x.realization_median):
        realization_color = (
            P["positive"] if p.realization_median >= 0.70
            else P["warning"] if p.realization_median >= 0.50
            else P["negative"]
        )
        fail_color = (
            P["negative"] if p.failure_rate >= 0.40
            else P["warning"] if p.failure_rate >= 0.25
            else P["positive"]
        )
        rows.append([
            p.category.value,
            html.escape(p.label),
            f'<span style="color:{realization_color};font-weight:700;">'
            f'{p.realization_median*100:.0f}%</span>',
            f"{p.realization_p25*100:.0f}% – {p.realization_p75*100:.0f}%",
            f'<span style="color:{fail_color};font-weight:700;">'
            f'{p.failure_rate*100:.0f}%</span>',
            f"{p.realization_n_samples:,}",
            str(p.duration_months_median),
        ])
        sort_keys.append([
            p.category.value, p.label,
            p.realization_median, p.realization_p25,
            p.failure_rate, p.realization_n_samples,
            p.duration_months_median,
        ])
    return sortable_table(
        headers, rows, sort_keys=sort_keys,
        name="lever_library_reference",
        caption=(
            "Realization priors from ~3,000 RCM initiative outcomes · "
            "sortable · color-coded by realization and fail-rate bands"
        ),
    )


# ────────────────────────────────────────────────────────────────────
# Landing form
# ────────────────────────────────────────────────────────────────────

_DEFAULT_BRIDGE = (
    "Denial workflow overhaul, 4.2M\n"
    "Coding / CDI uplift, 3.1M\n"
    "Vendor clearinghouse consolidation, 2.8M\n"
    "AR aging liquidation, 1.5M\n"
    "Site-neutral mitigation, 1.8M\n"
    "Tuck-in M&A synergy, 2.5M"
)


def _landing(qs: Optional[Dict[str, List[str]]] = None) -> str:
    form = f"""
<form method="get" action="/diligence/bridge-audit" class="ba-wrap">
  <div class="ba-panel">
    <div class="ba-section-label" style="margin-top:0;">
      Paste banker's EBITDA bridge</div>
    <div style="font-size:12px;color:{P["text_dim"]};line-height:1.6;
                margin-bottom:12px;max-width:820px;">
      One lever per line. Format: <code>name, $amount</code> or
      <code>name: $amount</code>. Amounts accept <code>$4.2M</code>,
      <code>4,200,000</code>, or plain numbers. Lines starting with
      <code>#</code> are comments.
    </div>
    <div class="ba-form-field" style="margin-bottom:16px;">
      <label>Bridge line items</label>
      <textarea name="bridge">{html.escape(_DEFAULT_BRIDGE)}</textarea>
    </div>
    <div class="ba-form-grid">
      <div class="ba-form-field"><label>Target name</label>
        <input name="target_name" value="Meadowbrook Regional"/></div>
      <div class="ba-form-field"><label>Asking price (USD)</label>
        <input name="asking_price_usd" value="710000000"/></div>
      <div class="ba-form-field"><label>Entry multiple (x)</label>
        <input name="entry_multiple" value="10.5"/></div>
      <div class="ba-form-field"><label>Denial rate % (0-1)</label>
        <input name="denial_rate_pct" value="0.095"/></div>
      <div class="ba-form-field"><label>Days in AR</label>
        <input name="days_in_ar" value="52"/></div>
      <div class="ba-form-field"><label>MA mix % (0-1)</label>
        <input name="ma_mix_pct" value="0.45"/></div>
      <div class="ba-form-field"><label>Commercial share (0-1)</label>
        <input name="commercial_payer_share" value="0.32"/></div>
      <div class="ba-form-field"><label>Top-1 payer share (0-1)</label>
        <input name="top_1_payer_share" value="0.34"/></div>
      <div class="ba-form-field"><label>Beds</label>
        <input name="beds" value="300"/></div>
      <div class="ba-form-field"><label>EHR vendor</label>
        <input name="ehr_vendor" value="EPIC"/></div>
      <div class="ba-form-field"><label>Unionized workforce</label>
        <select name="unionized_workforce">
          <option value="">No</option><option value="1">Yes</option>
        </select></div>
      <div class="ba-form-field"><label>Prior denial initiative failed</label>
        <select name="prior_denial_initiative_failed">
          <option value="">No</option><option value="1">Yes</option>
        </select></div>
    </div>
    <button class="ba-form-submit" type="submit">
      Audit bridge</button>
  </div>
</form>
"""
    body = (
        _scoped_styles()
        + '<div class="ba-wrap">'
        + deal_context_bar(qs or {}, active_surface="bridge")
        + '<div style="padding:22px 0 16px 0;">'
        + '<div class="ba-eyebrow">EBITDA Bridge Auto-Auditor</div>'
        + '<div class="ba-h1">Is the banker\'s bridge credible?</div>'
        + f'<div class="ba-callout">Paste the banker\'s sell-side '
        + 'EBITDA bridge; our engine classifies each lever, pulls '
        + 'realization priors from ~3,000 historical RCM initiatives, '
        + 'adjusts for target characteristics (denial rate, payer '
        + 'mix, regulatory exposure), and returns a risk-adjusted '
        + 'bridge with counter-bid math. Median realization across '
        + 'categories ranges 35-92%; the auditor surfaces exactly '
        + 'which claims are stretching and by how much.</div>'
        + '</div>'
        + form
        + '</div>'
    )
    return chartis_shell(
        body, "RCM Diligence — Bridge Auto-Auditor",
        subtitle="Banker bridge × realization priors × target profile",
    )


# ────────────────────────────────────────────────────────────────────
# Public entry
# ────────────────────────────────────────────────────────────────────

def _parse_target(qs: Dict[str, List[str]]) -> Dict[str, Any]:
    def first(k: str, d: str = "") -> str:
        return (qs.get(k) or [d])[0].strip()

    def fnum(k: str) -> Optional[float]:
        v = first(k)
        if not v:
            return None
        try:
            return float(v)
        except ValueError:
            return None

    def fint(k: str) -> Optional[int]:
        v = first(k)
        if not v:
            return None
        try:
            return int(float(v))
        except ValueError:
            return None

    def fbool(k: str) -> bool:
        return first(k).lower() in ("1", "true", "yes", "on")

    target = {
        "denial_rate_pct": fnum("denial_rate_pct"),
        "days_in_ar": fnum("days_in_ar"),
        "ma_mix_pct": fnum("ma_mix_pct"),
        "commercial_payer_share": fnum("commercial_payer_share"),
        "top_1_payer_share": fnum("top_1_payer_share"),
        "self_pay_share": fnum("self_pay_share"),
        "beds": fint("beds"),
        "num_sites": fint("num_sites"),
        "ehr_vendor": first("ehr_vendor"),
        "unionized_workforce": fbool("unionized_workforce"),
        "prior_denial_initiative_failed":
            fbool("prior_denial_initiative_failed"),
        "prior_coding_audit_found_gaps":
            fbool("prior_coding_audit_found_gaps"),
        "cfo_tenure_under_18_months":
            fbool("cfo_tenure_under_18_months"),
        "platform_over_10_tuck_ins_history":
            fbool("platform_over_10_tuck_ins_history"),
        "doj_fca_investigation_active":
            fbool("doj_fca_investigation_active"),
        "v28_rule_finalized": True,
        "site_neutral_rule_active": True,
        "hsr_expanded_reporting_active": True,
    }
    return {k: v for k, v in target.items() if v is not None and v != ""}


def render_bridge_audit_page(
    qs: Optional[Dict[str, List[str]]] = None,
) -> str:
    qs = qs or {}
    bridge_text = (qs.get("bridge") or [""])[0].strip()
    if not bridge_text:
        return _landing(qs)

    def first(k: str, d: str = "") -> str:
        return (qs.get(k) or [d])[0].strip()

    levers = parse_bridge_text(bridge_text)
    if not levers:
        return chartis_shell(
            _scoped_styles()
            + f'<div class="ba-wrap" style="padding:28px;">'
            + f'<div class="ba-eyebrow">Bridge Audit</div>'
            + f'<div class="ba-h1" style="color:{P["negative"]};">'
            + 'Could not parse any lever rows.</div>'
            + f'<div class="ba-callout">Expected format: '
            + '<code>Denial workflow, $4.2M</code> — one line per '
            + 'lever. Check punctuation or paste again.</div>'
            + f'<div style="margin-top:18px;">'
            + f'<a href="/diligence/bridge-audit" '
            + f'style="color:{P["accent"]};">← Back to audit form</a>'
            + '</div></div>',
            "RCM Diligence — Bridge Auto-Auditor",
        )

    target_name = first("target_name", "Target")
    entry_multiple_raw = first("entry_multiple")
    asking_price_raw = first("asking_price_usd")
    entry_multiple: Optional[float] = None
    asking_price: Optional[float] = None
    try:
        if entry_multiple_raw:
            entry_multiple = float(entry_multiple_raw)
    except ValueError:
        entry_multiple = None
    try:
        if asking_price_raw:
            asking_price = float(asking_price_raw)
    except ValueError:
        asking_price = None

    target = _parse_target(qs)

    report = audit_bridge(
        levers=levers,
        target_name=target_name,
        target_profile=target,
        entry_multiple=entry_multiple,
        asking_price_usd=asking_price,
    )

    # Chart-side plain-English
    chart_plain_parts: List[str] = []
    overstated = [
        a for a in report.per_lever
        if a.verdict in (LeverVerdict.OVERSTATED, LeverVerdict.UNSUPPORTED)
    ]
    if overstated:
        worst = max(overstated, key=lambda a: a.gap_usd)
        chart_plain_parts.append(
            f"Largest single gap is "
            f"<strong style=\"color:{P['negative']};\">"
            f"{html.escape(worst.lever.name)}</strong> — banker "
            f"claims <strong>${worst.claimed_usd/1e6:,.1f}M</strong>, "
            f"realistic capture is "
            f"<strong>${worst.realistic_median_usd/1e6:,.2f}M</strong> "
            f"(<strong>{worst.adjusted_realization_median*100:.0f}%</strong> "
            f"of claim). {len(overstated)} of "
            f"{len(report.per_lever)} levers overshoot."
        )
    else:
        chart_plain_parts.append(
            f"Every lever's banker claim sits inside the P25-P75 "
            f"realistic band for its category. No counter-bid "
            f"action needed on realization risk alone."
        )
    chart_plain = " ".join(chart_plain_parts)

    hero = (
        f'<div style="padding:22px 0 16px 0;border-bottom:1px solid '
        f'{P["border"]};margin-bottom:22px;">'
        f'<div class="ba-eyebrow">EBITDA Bridge Auto-Auditor</div>'
        f'<div class="ba-h1">{html.escape(target_name)}</div>'
        f'<div style="font-size:11px;color:{P["text_faint"]};'
        f'margin-top:4px;">'
        f'{len(report.per_lever)} levers audited · '
        f'${report.claimed_bridge_usd/1e6:.1f}M claimed · '
        f'${report.realistic_bridge_usd/1e6:.1f}M realistic'
        f'</div>'
        f'{_verdict_card(report)}'
        f'{_counter_bid_card(report)}'
        f'</div>'
    )

    chart_panel = (
        f'<div class="ba-panel">'
        f'<div class="ba-section-label" style="margin-top:0;">'
        f'Claimed vs realistic — lever by lever</div>'
        f'{_bridge_comparison_chart(report)}'
        + interpret_callout("Plain-English read:", chart_plain)
        + f'<div class="ba-callout">'
        f'<strong style="color:{P["text"]};">How to read: </strong>'
        f'Each row is one lever.  The grey bar on top is what the '
        f'banker claimed; the colored band below is the P25-P75 '
        f'realistic range drawn from our library of '
        f'~3,000 similar initiatives.  The vertical tick is the '
        f'median realized outcome.  Bars where the grey sticks out '
        f'past the colored band are overstated.'
        f'</div>'
        f'</div>'
    )

    detail_panel = (
        f'<div class="ba-panel">'
        f'<div class="ba-section-label" style="margin-top:0;">'
        f'Per-lever audit · sortable detail grid</div>'
        f'{_per_lever_table(report)}'
        f'</div>'
    )

    narrative_panel = (
        f'<div class="ba-section-label">'
        f'Per-lever narrative — ordered by gap</div>'
        f'{_per_lever_narrative_block(report)}'
    )

    library_panel = (
        f'<div class="ba-panel">'
        f'<div class="ba-section-label" style="margin-top:0;">'
        f'Lever library — realization priors powering this audit</div>'
        f'<div style="font-size:12px;color:{P["text_dim"]};'
        f'line-height:1.6;margin-bottom:10px;max-width:860px;">'
        f'Every lever in the audit above is scored against one of '
        f'these category priors. Realization % is the median '
        f'claimed→realized ratio; fail rate is the fraction of '
        f'deals that captured &lt;50% of claim; N is the sample '
        f'size behind each prior.'
        f'</div>'
        f'{_lever_library_panel()}'
        f'</div>'
    )

    cross_link = (
        f'<div class="ba-panel">'
        f'<div class="ba-section-label" style="margin-top:0;">'
        f'Cross-reference</div>'
        f'<div style="font-size:13px;color:{P["text_dim"]};'
        f'line-height:1.65;">'
        f'The realistic bridge feeds directly into '
        f'<a href="/diligence/deal-mc" '
        f'style="color:{P["accent"]};">→ Deal MC</a> as the '
        f'base-case EBITDA uplift, into '
        f'<a href="/diligence/covenant-stress" '
        f'style="color:{P["accent"]};">→ Covenant Stress</a> as '
        f'the stressed DSCR numerator, and into '
        f'<a href="/diligence/ic-packet" '
        f'style="color:{P["accent"]};">→ IC Packet</a> as the '
        f'partner-signed synergy commitment.'
        f'</div></div>'
    )

    body = (
        _scoped_styles()
        + '<div class="ba-wrap">'
        + deal_context_bar(qs, active_surface="bridge")
        + hero
        + chart_panel
        + detail_panel
        + narrative_panel
        + library_panel
        + cross_link
        + export_json_panel(
            '<div class="ba-section-label" style="margin-top:22px;">'
            'JSON export — full audit report</div>',
            payload=report.to_dict(),
            name=f"bridge_audit_{target_name.replace(' ', '_')}",
        )
        + bookmark_hint()
        + '</div>'
    )
    return chartis_shell(
        body, "RCM Diligence — Bridge Auto-Auditor",
        subtitle=(
            f"{target_name} · "
            f"${report.gap_usd/1e6:+.1f}M gap vs banker"
        ),
    )
