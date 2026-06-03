"""ACO Economics page — /aco-economics."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_illustrative_note, ck_value_anchor


def _tracks_chart(items) -> str:
    """Lead chart for the ACO risk-track table — tracks ranked by covered
    beneficiaries so the lives distribution across risk arrangements
    reads at a glance. Bar width = share of total beneficiaries; value =
    beneficiary count; tone teal. Full track grid stays directly below.
    """
    total = sum(t.beneficiaries for t in items) or 1
    ranked = sorted(items, key=lambda t: t.beneficiaries, reverse=True)
    rows = []
    for t in ranked:
        rows.append(ck_bar_row(
            t.track,
            f"{t.beneficiaries:,}",
            t.beneficiaries / total * 100.0,
            tone="teal",
        ))
    return (
        '<div style="margin-bottom:14px">'
        f'{"".join(rows)}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;font-family:JetBrains Mono,monospace">'
        'Bar = share of total beneficiaries · value = covered lives</div>'
        '</div>'
    )

_EXPLAINER_CSS = """<style>
.ck-ao-explainer{font-family:var(--sc-serif,'Georgia',serif);
  font-size:15px;line-height:1.55;color:var(--sc-text-dim,#465366);
  margin:0 0 var(--sc-s-6,18px) 0;max-width:72ch;}
.ck-ao-explainer em{color:var(--sc-teal-ink,#155752);font-style:italic;}
</style>"""


def _savings_waterfall_svg(savings) -> str:
    if not savings: return ""
    w, h = 560, 220
    pad_l, pad_r, pad_t, pad_b = 60, 30, 30, 50
    inner_w = w - pad_l - pad_r
    inner_h = h - pad_t - pad_b
    max_v = max(s.payout_to_aco_mm for s in savings) or 1
    bg = P["panel"]; pos = P["positive"]; neg = P["negative"]
    text_dim = P["text_dim"]; text_faint = P["text_faint"]
    n = len(savings)
    bar_w = (inner_w - (n - 1) * 10) / n
    bars = []
    for i, s in enumerate(savings):
        x = pad_l + i * (bar_w + 10)
        bh = max(0, s.payout_to_aco_mm) / max_v * inner_h
        y = (h - pad_b) - bh
        color = pos if s.payout_to_aco_mm > 1 else (P["accent"] if s.payout_to_aco_mm > 0 else neg)
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" fill="{color}" opacity="0.85"/>'
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 4:.1f}" fill="{P["text_dim"]}" font-size="11" text-anchor="middle" font-family="JetBrains Mono,monospace;font-weight:600">${s.payout_to_aco_mm:,.2f}M</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 14}" fill="{text_faint}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{_html.escape(s.scenario if len(s.scenario) <= 20 else s.scenario[:19] + "…")}</text>'
            f'<text x="{x + bar_w / 2:.1f}" y="{h - pad_b + 26}" fill="{text_faint}" font-size="9" text-anchor="middle" font-family="JetBrains Mono,monospace">{s.savings_pct * 100:+.1f}% vs bench</text>'
        )
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" xmlns="http://www.w3.org/2000/svg">'
            f'<rect width="{w}" height="{h}" fill="{bg}"/>{"".join(bars)}'
            f'<text x="10" y="15" fill="{text_dim}" font-size="10" font-family="Inter,sans-serif">Shared Savings Payout by Performance Scenario</text></svg>')


def _tracks_table(tracks) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    risk_colors = {"upside-only": P["positive"], "two-sided": P["warning"], "global / full-risk": P["negative"], "full-risk": P["negative"]}
    cols = [("Track","left"),("Beneficiaries","right"),("Benchmark PMPM","right"),("Risk Level","left"),("Upside Cap","right"),("Downside Cap","right"),("Quality Weight","right"),("Min Savings Rate","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, t in enumerate(tracks):
        rb = panel_alt if i % 2 == 0 else bg
        rc = risk_colors.get(t.risk_level, text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.track)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{t.beneficiaries:,}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""${t.benchmark_pmpm:,.0f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{rc};border:1px solid {rc};border-radius:2px;letter-spacing:0.06em">{_html.escape(t.risk_level)}</span>""")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">{t.upside_cap_pct * 100:.0f}%</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["negative"] if t.downside_cap_pct else text_dim}">{t.downside_cap_pct * 100:.0f}%</td>',
            f'{ck_data_cell(f"""{t.quality_weight * 100:.0f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{t.min_savings_rate * 100:.1f}%""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _benchmark_table(benchmark) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    cols = [("Component","left"),("Value PMPM","right"),("Basis","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, b in enumerate(benchmark):
        rb = panel_alt if i % 2 == 0 else bg
        is_total = "Complete" in b.component
        cells = [
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:11px;color:{text};font-weight:{"700" if is_total else "400"}">{_html.escape(b.component)}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["accent"] if is_total else text};font-weight:{"700" if is_total else "400"}">${b.value_pmpm:,.0f}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(b.basis)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _savings_table(savings) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Scenario","left"),("Actual PMPM","right"),("Savings %","right"),("Gross Savings ($M)","right"),("Quality Mult","right"),("Net Shared Savings","right"),("ACO Share","right"),("Payout ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(savings):
        rb = panel_alt if i % 2 == 0 else bg
        sav_c = pos if s.savings_pct > 0 else P["negative"]
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.scenario)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${s.actual_pmpm:,.0f}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{sav_c};font-weight:600">{s.savings_pct * 100:+.2f}%</td>',
            f'{ck_data_cell(f"""${s.gross_savings_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{s.quality_multiplier:.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${s.net_shared_savings_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{s.aco_share_pct * 100:.0f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${s.payout_to_aco_mm:,.2f}""", align="right", mono=True, tone="pos", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _quality_table(q) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    cols = [("Component","left"),("Weight","right"),("Current Score","right"),("Target","right"),("Contribution","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(q):
        rb = panel_alt if i % 2 == 0 else bg
        contrib_c = P["positive"] if c.contribution_to_quality >= 0.95 else P["warning"]
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.component)}""", mono=True, weight=600)}',
            f'{ck_data_cell(f"""{c.weight * 100:.0f}%""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{c.current_score:.1f}""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["positive"]}">{c.target:.1f}</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{contrib_c};font-weight:600">{c.contribution_to_quality:.2f}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _infra_table(infra) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Investment","left"),("Y1 Cost ($M)","right"),("Ongoing ($M)","right"),("Enables Savings ($M)","right"),("Payback (mo)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, inv in enumerate(infra):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(inv.investment)}""", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${inv.year_1_cost_mm:,.2f}</td>',
            f'{ck_data_cell(f"""${inv.ongoing_cost_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${inv.enables_savings_mm:,.2f}""", align="right", mono=True, tone="pos", weight=600)}',
            f'{ck_data_cell(f"""{inv.payback_months}""", align="right", mono=True, tone="dim")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _full_risk_table(fr) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]; text = P["text"]; text_dim = P["text_dim"]; pos = P["positive"]
    cols = [("Stage","left"),("Risk Exposure","right"),("Required Infra ($M)","right"),("Reinsurance ($M)","right"),("Shared Savings ($M)","right"),("Capitation Margin ($M)","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, s in enumerate(fr):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(s.stage)}""", mono=True, weight=600)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">{s.risk_exposure_pct * 100:.0f}%</td>',
            f'{ck_data_cell(f"""${s.required_infra_mm:,.2f}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{P["warning"]}">${s.reinsurance_cost_mm:,.2f}</td>',
            f'{ck_data_cell(f"""${s.expected_shared_savings_mm:,.2f}""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""${s.expected_capitation_margin_mm:,.2f}""", align="right", mono=True, tone="pos", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_aco_economics(params: dict = None) -> str:
    params = params or {}

    def _f(name, default):
        try: return float(params.get(name, default))
        except (ValueError, TypeError): return default

    def _i(name, default):
        try: return int(params.get(name, default))
        except (ValueError, TypeError): return default

    benefs = _i("beneficiaries", 25000)
    pmpm = _f("pmpm", 950.0)

    from rcm_mc.data_public.aco_economics import compute_aco_economics
    r = compute_aco_economics(total_beneficiaries=benefs, regional_benchmark_pmpm=pmpm)

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]

    kpi_strip = (
        ck_kpi_block("Beneficiaries", f"{r.total_beneficiaries:,}", "", "") +
        ck_kpi_block("Benchmark PMPM", f"${r.blended_benchmark_pmpm:,.0f}", "", "") +
        ck_kpi_block("Quality Score", f"{r.quality_score:.3f}", "", "") +
        ck_kpi_block("Expected Savings", f"${r.expected_shared_savings_mm:,.1f}M", "", "") +
        ck_kpi_block("Total Annual Value", f"${r.total_annual_value_mm:,.1f}M", "", "") +
        ck_kpi_block("Tracks", str(len(r.tracks)), "", "") +
        ck_kpi_block("Infra Items", str(len(r.infrastructure)), "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    savings_svg = _savings_waterfall_svg(r.savings_scenarios)
    tracks_chart = _tracks_chart(r.tracks)
    tracks_tbl = _tracks_table(r.tracks)
    value_anchor = ck_value_anchor(
        "ACO Economics",
        f"${r.total_annual_value_mm:,.1f}M annual value",
        delta=f"{r.total_beneficiaries:,} beneficiaries · ${r.blended_benchmark_pmpm:,.0f} PMPM benchmark · quality {r.quality_score * 100:.0f}%",
        opportunity=f"${r.expected_shared_savings_mm:,.1f}M expected shared savings",
        tone="positive",
    )
    bench_tbl = _benchmark_table(r.benchmark)
    savings_tbl = _savings_table(r.savings_scenarios)
    quality_tbl = _quality_table(r.quality_components)
    infra_tbl = _infra_table(r.infrastructure)
    risk_tbl = _full_risk_table(r.full_risk)

    form = f"""
<form method="GET" action="/aco-economics" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Beneficiaries<input name="beneficiaries" value="{benefs}" type="number" step="1000" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:90px"/></label>
  <label style="font-size:11px;color:{text_dim}">Benchmark PMPM<input name="pmpm" value="{pmpm}" type="number" step="25" style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/></label>
  <button type="submit" style="background:{border};color:{text};border:1px solid {border};padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run analysis</button>
</form>"""

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    page_title = ck_page_title(
        "ACO Economics",
        eyebrow="ACO ECONOMICS",
        meta=f"{r.corpus_deal_count:,} corpus deals · {r.total_beneficiaries:,} beneficiaries · ${r.blended_benchmark_pmpm:,.0f}/PMPM bench",
    )
    ao_explainer = (
        '<p class="ck-ao-explainer">'
        "<em>MSSP, ACO REACH, MA capitation.</em> "
        "Shared savings, quality scoring, and full-risk transition — "
        "what the ACO economics reveal on this deal."
        "</p>"
    )
    body = page_title + ck_illustrative_note("figures") + ao_explainer + f"""
<div class="ck-page-wrap">
  {form}
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Shared Savings Performance Scenarios</div>{savings_svg}</div>
  <div style="{cell}"><div style="{h3}">ACO Risk Tracks</div>{tracks_chart}{tracks_tbl}</div>
  <div style="{cell}"><div style="{h3}">Benchmark Establishment</div>{bench_tbl}</div>
  <div style="{cell}"><div style="{h3}">Savings Scenario Detail</div>{savings_tbl}</div>
  <div style="{cell}"><div style="{h3}">Quality Score Components</div>{quality_tbl}</div>
  <div style="{cell}"><div style="{h3}">Infrastructure Investment Portfolio</div>{infra_tbl}</div>
  <div style="{cell}"><div style="{h3}">Full-Risk Transition Path</div>{risk_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">ACO Thesis:</strong> {r.total_beneficiaries:,} attributed lives at ${r.blended_benchmark_pmpm:,.0f} PMPM benchmark.
    Quality score {r.quality_score:.3f} unlocks full savings share. Expected ${r.expected_shared_savings_mm:,.1f}M shared savings
    + ${r.total_annual_value_mm - r.expected_shared_savings_mm:,.1f}M capitation/MA margin = ${r.total_annual_value_mm:,.1f}M total value.
    Transition to full-risk over 4 years unlocks material margin expansion.
  </div>
</div>"""

    # 2026-05-28 wave-B: ck_page_actions adds Copy share link
    # + Back-to-top affordances. Idempotent JS guards.
    from .._chartis_kit import ck_page_actions
    body = body + ck_page_actions()
    return chartis_shell(body, "ACO Economics", active_nav="/aco-economics",
        extra_css=_EXPLAINER_CSS)
