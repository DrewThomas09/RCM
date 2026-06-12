"""Medicare rate environment page — /rate-environment.

Setting-level CMS payment updates (3 rule cycles), with a blended
calculator that turns a target's Medicare revenue × setting mix into a
next-cycle dollar impact. Renders from
``rcm_mc.market_intel.rate_environment``.
"""
from __future__ import annotations

import html as _html
from typing import Dict

from rcm_mc.ui._chartis_kit import (
    P, chartis_shell, ck_data_cell, ck_kpi_block, ck_page_explainer,
    ck_page_title,
)

# Calculator defaults: a physician-services platform with surgical
# exposure — the most common mix the desk diligences.
_DEFAULT_MIX = {"PFS": 40.0, "OPPS": 25.0, "ASC": 20.0, "IPPS": 15.0}


def _f(params: dict, name: str, default: float) -> float:
    try:
        v = float(params.get(name, default))
    except (TypeError, ValueError):
        return default
    # Negative shares/revenue make no sense and only distort the blend.
    return v if v >= 0 else default


def _updates_table(settings) -> str:
    border = P["border"]; text_dim = P["text_dim"]
    periods = [u.period[-4:] for u in settings[0].updates] if settings else []
    cols = [("Setting", "left")] + [(p, "right") for p in periods] + [
        ("3-cycle compound", "right"), ("Policy note", "left")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid '
        f'{border};font-size:10px;color:{text_dim};letter-spacing:0.05em">'
        f'{_html.escape(c)}</th>' for c, a in cols)
    trs = []
    for s in settings:
        cells = [ck_data_cell(
            f"{_html.escape(s.label)} <span style='color:{text_dim}'>"
            f"[{_html.escape(s.cycle)}]</span>", mono=True, weight=600)]
        for u in s.updates:
            tone = ("pos" if u.net_update_pct >= 2.5 else
                    ("neg" if u.net_update_pct < 1.0 else "dim"))
            flag = "" if u.status == "FINAL" else " (prop.)"
            cells.append(ck_data_cell(
                f"{u.net_update_pct:+.1f}%{flag}", align="right",
                mono=True, tone=tone))
        comp = s.three_year_compound_pct()
        cells.append(ck_data_cell(
            f"{comp:+.1f}%", align="right", mono=True, weight=600,
            tone="pos" if comp >= 7 else
            ("neg" if comp < 2 else "dim")))
        cells.append(
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;'
            f'color:{text_dim};max-width:340px">'
            f'{_html.escape(s.note or "")}</td>')
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody>'
            f'</table></div>')


def _impact_table(impact) -> str:
    border = P["border"]; text_dim = P["text_dim"]
    cols = [("Setting", "left"), ("Mix share", "right"),
            ("Next-cycle update", "right"), ("Revenue impact ($)", "right")]
    ths = "".join(
        f'<th style="text-align:{a};padding:6px 10px;border-bottom:1px solid '
        f'{border};font-size:10px;color:{text_dim};letter-spacing:0.05em">'
        f'{c}</th>' for c, a in cols)
    trs = []
    for row in impact.per_setting:
        dollars = row["revenue_impact_usd"]
        trs.append("<tr>" + "".join([
            ck_data_cell(
                f'{_html.escape(row["label"])} '
                f'<span style="color:{text_dim}">'
                f'({_html.escape(row["period"])})</span>',
                mono=True, weight=600),
            ck_data_cell(f'{row["share_pct"]:.1f}%', align="right", mono=True),
            ck_data_cell(f'{row["net_update_pct"]:+.1f}%', align="right",
                         mono=True,
                         tone="pos" if row["net_update_pct"] >= 0
                         else "neg"),
            ck_data_cell(f"${dollars:,.2f}", align="right", mono=True,
                         weight=600,
                         tone="pos" if dollars >= 0 else "neg"),
        ]) + "</tr>")
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody>'
            f'</table></div>')


def render_rate_environment(params: dict = None) -> str:
    params = params or {}
    from rcm_mc.market_intel.rate_environment import (
        blended_rate_impact, list_settings,
    )
    settings = list_settings()

    revenue_m = _f(params, "revenue", 60.0)
    mix: Dict[str, float] = {
        s.setting: _f(params, f"mix_{s.setting.lower()}",
                      _DEFAULT_MIX.get(s.setting, 0.0))
        for s in settings
    }
    impact = blended_rate_impact(revenue_m * 1_000_000, mix)

    panel = P["panel"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]

    latest = [(s, s.latest()) for s in settings]
    best = max(latest, key=lambda t: t[1].net_update_pct if t[1] else -99)
    worst = min(latest, key=lambda t: t[1].net_update_pct if t[1] else 99)

    kpi_strip = (
        ck_kpi_block("Settings tracked", str(len(settings)), "", "") +
        ck_kpi_block("Blended update",
                     f"{impact.blended_update_pct:+.1f}%",
                     "mix-weighted, next cycle", "") +
        ck_kpi_block("Revenue impact",
                     f"${impact.revenue_impact_usd / 1e6:,.2f}M",
                     f"on ${revenue_m:,.2f}M Medicare base", "") +
        ck_kpi_block("Best setting",
                     f"{best[1].net_update_pct:+.1f}%" if best[1] else "—",
                     _html.escape(best[0].setting), "") +
        ck_kpi_block("Worst setting",
                     f"{worst[1].net_update_pct:+.1f}%" if worst[1] else "—",
                     _html.escape(worst[0].setting), "")
    )

    mix_inputs = "".join(
        f'<label style="font-size:11px;color:{text_dim}">'
        f'{_html.escape(s.setting)} %'
        f'<input name="mix_{s.setting.lower()}" value="{mix[s.setting]:g}" '
        f'type="number" step="5" min="0" '
        f'style="margin-left:4px;background:{panel};border:1px solid '
        f'{border};color:{text};padding:4px 6px;font-size:11px;'
        f'font-family:JetBrains Mono,monospace;width:58px"/></label>'
        for s in settings)
    from urllib.parse import urlencode
    dl_qs = urlencode({"revenue": f"{revenue_m:g}", **{
        f"mix_{k.lower()}": f"{v:g}" for k, v in mix.items()}})
    form = f"""
<form method="GET" action="/rate-environment" style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:16px">
  <label style="font-size:11px;color:{text_dim}">Medicare revenue ($M)
    <input name="revenue" value="{revenue_m:g}" type="number" step="10" min="0"
      style="margin-left:6px;background:{panel};border:1px solid {border};color:{text};
      padding:4px 8px;font-size:11px;font-family:JetBrains Mono,monospace;width:80px"/>
  </label>
  {mix_inputs}
  <button type="submit"
    style="background:{border};color:{text};border:1px solid {border};
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace;cursor:pointer">Compute impact</button>
  <a href="/rate-environment.xlsx?{dl_qs}" download
    style="background:#155752;color:#fffdf9;border:1px solid #155752;text-decoration:none;
    padding:4px 12px;font-size:11px;font-family:JetBrains Mono,monospace">Download model (.xlsx)</a>
</form>"""

    cell = (f"background:{panel};border:1px solid {border};padding:16px;"
            f"margin-bottom:16px")
    h3 = (f"font-size:11px;font-weight:600;letter-spacing:0.08em;"
          f"color:{text_dim};text-transform:uppercase;margin-bottom:10px")

    page_title = ck_page_title(
        "Medicare Rate Environment",
        eyebrow="MARKET INTEL · REIMBURSEMENT",
        meta=(f"{len(settings)} care settings · 3 rule cycles · blended "
              f"{impact.blended_update_pct:+.1f}% on the entered mix → "
              f"${impact.revenue_impact_usd / 1e6:,.2f}M next-cycle impact"),
    )
    explainer = ck_page_explainer(
        "Rate is the revenue line you don't control.",
        "Headline net Medicare payment updates by care setting, curated "
        "from CMS final rules. Enter a target's Medicare revenue and "
        "setting mix to get the blended next-cycle dollar impact — then "
        "read the policy notes, because the headline update routinely "
        "hides the real exposure (site-neutral, behavioral adjustments, "
        "conversion-factor politics). Verify against the final rule "
        "before IC use.",
    )

    body = f"""
<div class="ck-page-wrap">
  {page_title}
  {explainer}
  {form}
  <div class="ck-kpi-grid">{kpi_strip}</div>
  <div style="{cell}">
    <div style="{h3}">Net payment updates by setting (CMS final rules)</div>
    {_updates_table(settings)}
  </div>
  <div style="{cell}">
    <div style="{h3}">Blended impact on the entered Medicare book</div>
    {_impact_table(impact)}
  </div>
</div>"""
    return chartis_shell(body, title="Medicare Rate Environment",
                         active_nav="/rate-environment")


def rate_environment_xlsx(params: dict = None) -> bytes:
    """Workbook version of this page — and unlike the HTML, a *model*:
    the Impact sheet's revenue and mix cells are blue inputs feeding
    live SUM/SUMPRODUCT formulas, so the partner can rerun the blend in
    Excel without coming back to the page."""
    from rcm_mc.exports.xlsx_writer import F, Sheet, write_xlsx
    from rcm_mc.market_intel.rate_environment import list_settings

    params = params or {}
    settings = list_settings()
    revenue_m = _f(params, "revenue", 60.0)
    mix = {
        s.setting: _f(params, f"mix_{s.setting.lower()}",
                      _DEFAULT_MIX.get(s.setting, 0.0))
        for s in settings
    }

    # -- Sheet 1: the curated update calendar, compound as a formula.
    upd: list = []
    upd.append([("MEDICARE NET PAYMENT UPDATES BY SETTING", "header")]
               + [("", "header")] * 5)
    upd.append(["Curated from CMS final rules — verify against the "
                "final rule before IC use."])
    upd.append([""])
    periods = [u.period for u in settings[0].updates]
    upd.append([("Setting", "header")]
               + [(p, "header") for p in periods]
               + [("3-cycle compound", "header"), ("Policy note", "header")])
    for i, s in enumerate(settings):
        n = 5 + i
        row: list = [f"{s.label} [{s.cycle}]"]
        for u in s.updates:
            row.append((u.net_update_pct / 100.0, "pct"))
        row.append((F(f"(1+B{n})*(1+C{n})*(1+D{n})-1"), "pct"))
        row.append(s.note or "")
        upd.append(row)

    # -- Sheet 2: the blended-impact model (blue inputs, live blend).
    imp: list = []
    imp.append([("BLENDED RATE-IMPACT MODEL", "header")]
               + [("", "header")] * 4)
    imp.append(["Blue cells = inputs (edit these). "
                "Black cells = live formulas."])
    imp.append([""])
    imp.append(["Medicare revenue ($)",
                (revenue_m * 1_000_000, "input_money")])          # B4
    imp.append([""])
    imp.append([("Setting", "header"), ("Mix share", "header"),
                ("Normalized share", "header"),
                ("Latest update %", "header"),
                ("Revenue impact ($)", "header")])                # row 6
    first, last = 7, 6 + len(settings)
    for i, s in enumerate(settings):
        n = first + i
        latest = s.latest()
        imp.append([
            s.label,
            (mix[s.setting] / 100.0, "input_pct"),
            (F(f"B{n}/SUM(B${first}:B${last})"), "pct"),
            ((latest.net_update_pct / 100.0) if latest else 0.0, "pct"),
            (F(f"$B$4*C{n}*D{n}"), "money2"),
        ])
    t = last + 1
    imp.append([("Total / blended", "label"),
                (F(f"SUM(B{first}:B{last})"), "pct"),
                (F(f"SUM(C{first}:C{last})"), "pct"),
                (F(f"SUMPRODUCT(C{first}:C{last},D{first}:D{last})"), "pct"),
                (F(f"SUM(E{first}:E{last})"), "money2")])
    imp.append([""])
    imp.append(["Blended impact on revenue ($)",
                (F(f"$B$4*D{t}"), "money2")])

    return write_xlsx([
        Sheet("Rate Updates", upd, col_widths=[34, 11, 11, 11, 16, 60]),
        Sheet("Impact Model", imp, col_widths=[34, 13, 17, 15, 18]),
    ])
