"""Healthcare labor-market page — /labor-market.

Role-level wage/turnover/vacancy reads plus a labor-cost stress
calculator: enter a target's labor spend, role mix, and revenue to get
the next-year wage-inflation cost and the uncompensated margin
compression in bps. Renders from ``rcm_mc.market_intel.labor_market``.
"""
from __future__ import annotations

import html as _html
from typing import Dict

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_data_cell, ck_kpi_block, ck_page_explainer,
    ck_page_title,
)

# Calculator defaults: a multi-site physician-services platform —
# clinical support heavy, physician comp the biggest single line.
_DEFAULT_MIX = {"PHYS_PC": 25.0, "PHYS_SPEC": 15.0, "NP_PA": 10.0,
                "RN": 15.0, "MA": 15.0, "RCM_ADMIN": 20.0}


def _f(params: dict, name: str, default: float) -> float:
    try:
        v = float(params.get(name, default))
    except (TypeError, ValueError):
        return default
    return v if v >= 0 else default


def _fragility_tone(score: float) -> str:
    return "neg" if score >= 60 else ("dim" if score >= 40 else "pos")


def _roles_table(roles) -> str:
    border = P["border"]; text_dim = P["text_dim"]
    cols = [("Role", "left"), ("Median wage ($/hr)", "right"),
            ("Wage YoY", "right"), ("Turnover", "right"),
            ("Vacancy", "right"), ("Time to fill (wks)", "right"),
            ("Fragility /100", "right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid '
        f'{border};font-size:10px;color:{text_dim};letter-spacing:0.05em">'
        f'{c}</th>' for c, a in cols)
    trs = []
    for r in sorted(roles, key=lambda r: -r.fragility_score()):
        frag = r.fragility_score()
        trs.append("<tr>" + "".join([
            ck_data_cell(_html.escape(r.label), mono=True, weight=600),
            ck_data_cell(f"${r.median_hourly_usd:,.2f}", align="right",
                         mono=True),
            ck_data_cell(f"+{r.wage_yoy_pct:.1f}%", align="right", mono=True,
                         tone="neg" if r.wage_yoy_pct >= 4.5 else "dim"),
            ck_data_cell(f"{r.turnover_pct:.1f}%", align="right", mono=True,
                         tone="neg" if r.turnover_pct >= 25 else "dim"),
            ck_data_cell(f"{r.vacancy_pct:.1f}%", align="right", mono=True),
            ck_data_cell(str(r.replacement_weeks), align="right", mono=True),
            ck_data_cell(f"{frag:.1f}", align="right", mono=True,
                         weight=600, tone=_fragility_tone(frag),
                         bar=frag),
        ]) + "</tr>")
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody>'
            f'</table></div>')


def _stress_table(stress) -> str:
    border = P["border"]; text_dim = P["text_dim"]
    cols = [("Role", "left"), ("Spend share", "right"),
            ("Wage YoY", "right"), ("Cost increase ($)", "right"),
            ("Fragility", "right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid '
        f'{border};font-size:10px;color:{text_dim};letter-spacing:0.05em">'
        f'{c}</th>' for c, a in cols)
    trs = []
    for row in stress.per_role:
        trs.append("<tr>" + "".join([
            ck_data_cell(_html.escape(row["label"]), mono=True, weight=600),
            ck_data_cell(f'{row["share_pct"]:.1f}%', align="right",
                         mono=True),
            ck_data_cell(f'+{row["wage_yoy_pct"]:.1f}%', align="right",
                         mono=True),
            ck_data_cell(f'${row["cost_increase_usd"]:,.2f}', align="right",
                         mono=True, weight=600, tone="neg"),
            ck_data_cell(f'{row["fragility_score"]:.1f}', align="right",
                         mono=True,
                         tone=_fragility_tone(row["fragility_score"])),
        ]) + "</tr>")
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody>'
            f'</table></div>')


def render_labor_market(params: dict = None) -> str:
    params = params or {}
    from rcm_mc.market_intel.labor_market import (
        labor_cost_stress, list_roles,
    )
    roles = list_roles()

    labor_m = _f(params, "labor", 32.0)
    revenue_m = _f(params, "revenue", 60.0)
    mix: Dict[str, float] = {
        r.role: _f(params, f"mix_{r.role.lower()}",
                   _DEFAULT_MIX.get(r.role, 0.0))
        for r in roles
    }
    stress = labor_cost_stress(labor_m * 1_000_000, mix,
                               revenue_usd=revenue_m * 1_000_000)

    panel = P["panel"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]

    most_fragile = max(roles, key=lambda r: r.fragility_score())
    fastest_wage = max(roles, key=lambda r: r.wage_yoy_pct)
    kpi_strip = (
        ck_kpi_block("Roles tracked", str(len(roles)), "", "") +
        ck_kpi_block("Blended wage growth",
                     f"+{stress.blended_wage_growth_pct:.1f}%",
                     "mix-weighted, next year", "") +
        ck_kpi_block("Cost increase",
                     f"${stress.annual_cost_increase_usd / 1e6:,.2f}M",
                     f"on ${labor_m:,.2f}M labor base", "") +
        ck_kpi_block("Margin compression",
                     f"-{stress.ebitda_margin_impact_bps:,.0f} bps",
                     "if rates stay flat", "") +
        ck_kpi_block("Most fragile role",
                     f"{most_fragile.fragility_score():.0f}/100",
                     _html.escape(most_fragile.label), "") +
        ck_kpi_block("Fastest wage growth",
                     f"+{fastest_wage.wage_yoy_pct:.1f}%",
                     _html.escape(fastest_wage.label), "")
    )

    mix_inputs = "".join(
        f'<label style="font-size:11px;color:{text_dim}" '
        f'title="{_html.escape(r.label)}">'
        f'{_html.escape(r.role)} %'
        f'<input name="mix_{r.role.lower()}" value="{mix[r.role]:g}" '
        f'type="number" step="5" min="0" '
        f'style="margin-left:4px;background:{panel};border:1px solid '
        f'{border};color:{text};padding:4px 6px;font-size:11px;'
        f'font-family:JetBrains Mono,monospace;width:58px"/></label>'
        for r in roles)
    form = f"""
<form method="GET" action="/labor-market" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Labor cost ($M)
    <input name="labor" value="{labor_m:g}" type="number" step="5" min="0"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  <label style="font-size:11px;color:{text_dim}">Revenue ($M)
    <input name="revenue" value="{revenue_m:g}" type="number" step="10" min="0"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:70px"/>
  </label>
  {mix_inputs}
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Run stress</button>
</form>"""

    cell = (f"background:{panel};border:1px solid {border};padding:16px;"
            f"margin-bottom:16px")
    h3 = (f"font-size:11px;font-weight:600;letter-spacing:0.08em;"
          f"color:{text_dim};text-transform:uppercase;margin-bottom:10px")

    page_title = ck_page_title(
        "Healthcare Labor Market",
        eyebrow="MARKET INTEL · LABOR & WAGES",
        meta=(f"{len(roles)} roles · blended wage growth "
              f"+{stress.blended_wage_growth_pct:.1f}% on the entered mix → "
              f"${stress.annual_cost_increase_usd / 1e6:,.2f}M / "
              f"-{stress.ebitda_margin_impact_bps:,.0f} bps if "
              f"uncompensated"),
    )
    explainer = ck_page_explainer(
        "Labor is the cost line that breaks healthcare margins.",
        "Role-level wage, turnover, vacancy, and time-to-fill reads, "
        "curated from BLS OES and the annual staffing surveys. Enter a "
        "target's labor spend and role mix to see next-year wage "
        "inflation in dollars — and in margin bps if rate increases "
        "don't keep pace. The fragility score blends turnover, vacancy, "
        "and wage pressure into one replace-risk number per role. "
        "National medians; verify against the current BLS release and "
        "local wage indices before IC use.",
    )

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {explainer}
  {form}
  <div class="ck-kpi-grid">{kpi_strip}</div>
  <div style="{cell}">
    <div style="{h3}">Wage-inflation stress on the entered labor base</div>
    {_stress_table(stress)}
  </div>
  <div style="{cell}">
    <div style="{h3}">Role economics (fragility-descending)</div>
    {_roles_table(roles)}
  </div>
</div>"""
    return chartis_shell(body, title="Healthcare Labor Market",
                         active_nav="/labor-market")
