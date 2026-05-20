"""Capital Call / LP Communication Tracker — /capital-call."""
from __future__ import annotations

import html as _html
from rcm_mc.ui._chartis_kit import P, chartis_shell, ck_bar_row, ck_kpi_block, ck_data_cell, ck_page_title, ck_value_anchor


def _calls_chart(items) -> str:
    """Lead chart for the capital-call table — LTM calls ranked by size
    so the largest draws surface first. Bar width = share of total LTM
    call volume; value = call amount ($M); tone flags any LP default
    (red), otherwise teal. Full call grid stays directly below.
    """
    total = sum(c.amount_m for c in items) or 1.0
    ranked = sorted(items, key=lambda c: c.amount_m, reverse=True)
    rows = []
    for c in ranked:
        tone = "negative" if c.defaulted_lp else "teal"
        rows.append(ck_bar_row(
            f"{c.fund} #{c.call_number}",
            f"${c.amount_m:,.0f}M",
            c.amount_m / total * 100.0,
            tone=tone,
        ))
    return (
        '<div style="margin-bottom:14px">'
        f'{"".join(rows)}'
        '<div style="font-size:10px;color:var(--sc-text-faint);'
        'margin-top:6px;font-family:JetBrains Mono,monospace">'
        'Bar = share of total LTM call volume · value = call amount ($M) · '
        'tone = red if any LP default on the call</div>'
        '</div>'
    )

_EXPLAINER_CSS = """<style>
.ck-cc-explainer{font-family:var(--sc-serif,'Georgia',serif);
  font-size:15px;line-height:1.55;color:var(--sc-text-dim,#465366);
  margin:0 0 var(--sc-s-6,18px) 0;max-width:72ch;}
.ck-cc-explainer em{color:var(--sc-teal-ink,#155752);font-style:italic;}
</style>"""


def _status_color(s: str) -> str:
    return {
        "paid": P["positive"],
        "received": P["positive"],
        "sent": P["positive"],
        "wired": P["positive"],
        "distributed": P["positive"],
        "in progress": P["accent"],
        "drafting": P["accent"],
        "draft complete": P["accent"],
        "accepted ($18M)": P["positive"],
        "accepted ($65M)": P["positive"],
        "responded": P["positive"],
        "approved": P["positive"],
        "discussing": P["warning"],
        "in review": P["warning"],
        "declined (conflict)": P["text_dim"],
    }.get(s, P["text_dim"])


def _calls_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]; neg = P["negative"]
    cols = [("Fund","left"),("Date","right"),("Call #","right"),("Amount ($M)","right"),
            ("Purpose","left"),("Unfunded Before","right"),("Unfunded After","right"),("LTM Called","right"),("Default","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        d_c = neg if c.defaulted_lp else pos
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.fund)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{_html.escape(c.call_date)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{c.call_number}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${c.amount_m:.1f}M""", align="right", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text_dim};max-width:340px">{_html.escape(c.purpose)}</td>',
            f'{ck_data_cell(f"""${c.unfunded_before_m:,.1f}M""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${c.unfunded_after_m:,.1f}M""", align="right", mono=True, tone="acc", weight=700)}',
            f'{ck_data_cell(f"""${c.ltm_called_m:,.1f}M""", align="right", mono=True, tone="pos")}',
            f'<td style="text-align:center;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{d_c};font-weight:700">{"YES" if c.defaulted_lp else "NO"}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _dist_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Fund","left"),("Date","right"),("Dist #","right"),("Amount ($M)","right"),
            ("Type","left"),("Source","left"),("LTM Distributed","right"),("Net to LPs","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, d in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        cells = [
            f'{ck_data_cell(f"""{_html.escape(d.fund)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{_html.escape(d.dist_date)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{d.dist_number}""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${d.amount_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(d.type)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(d.source)}</td>',
            f'{ck_data_cell(f"""${d.ltm_distributed_m:,.1f}M""", align="right", mono=True, tone="pos")}',
            f'{ck_data_cell(f"""${d.net_to_lps_m:.1f}M""", align="right", mono=True, tone="pos", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _cashflow_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Fund","left"),("Vintage","right"),("Committed ($M)","right"),("Called ($M)","right"),
            ("Distributed ($M)","right"),("NAV ($M)","right"),("DPI","right"),("TVPI","right"),("Unfunded ($M)","right"),("Next Call","right")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        dpi_c = pos if c.dpi >= 1.0 else (acc if c.dpi >= 0.5 else text_dim)
        tvpi_c = pos if c.tvpi >= 2.0 else (acc if c.tvpi >= 1.5 else text_dim)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.fund)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""{c.vintage}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${c.committed_m:,.1f}M""", align="right", mono=True, weight=600)}',
            f'{ck_data_cell(f"""${c.called_m:,.1f}M""", align="right", mono=True, tone="acc")}',
            f'{ck_data_cell(f"""${c.distributed_m:,.1f}M""", align="right", mono=True, tone="pos", weight=600)}',
            f'{ck_data_cell(f"""${c.nav_m:,.1f}M""", align="right", mono=True)}',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{dpi_c};font-weight:700">{c.dpi:.2f}x</td>',
            f'<td style="text-align:right;padding:5px 10px;font-variant-numeric:tabular-nums;font-family:JetBrains Mono,monospace;font-size:11px;color:{tvpi_c};font-weight:700">{c.tvpi:.2f}x</td>',
            f'{ck_data_cell(f"""${c.unfunded_m:,.1f}M""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""{_html.escape(c.next_call_estimate)}""", align="right", mono=True, tone="acc", weight=600)}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _lp_comms_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("LP","left"),("Commitment ($M)","right"),("Type","left"),("Date","right"),
            ("Subject","left"),("Response Due","right"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, c in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(c.status)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(c.lp_name)}""", mono=True, weight=700)}',
            f'{ck_data_cell(f"""${c.commitment_m:,.1f}M""", align="right", mono=True, tone="pos", weight=600)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(c.communication_type)}</td>',
            f'{ck_data_cell(f"""{_html.escape(c.date)}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:11px;color:{text_dim};max-width:320px">{_html.escape(c.subject)}</td>',
            f'{ck_data_cell(f"""{_html.escape(c.response_due)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(c.status)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _reporting_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Fund","left"),("Quarter","left"),("Report Type","left"),("Due","right"),
            ("Status","center"),("Pages","right"),("Owner","left")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, r in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(r.completion_status)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(r.fund)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(r.quarter)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(r.report_type)}</td>',
            f'{ck_data_cell(f"""{_html.escape(r.due_date)}""", align="right", mono=True)}',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(r.completion_status)}</span>""", align="center")}',
            f'{ck_data_cell(f"""{r.pages}""", align="right", mono=True, tone="dim")}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(r.owner)}</td>',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def _treasury_table(items) -> str:
    bg = P["panel"]; panel_alt = P["panel_alt"]; border = P["border"]
    text = P["text"]; text_dim = P["text_dim"]; acc = P["accent"]; pos = P["positive"]
    cols = [("Fund","left"),("Type","left"),("Date","right"),("Amount ($M)","right"),
            ("From","left"),("To","left"),("Bank","left"),("Status","center")]
    ths = "".join(ck_data_cell(f"""{c}""", align=a, is_header=True) for c, a in cols)
    trs = []
    for i, t in enumerate(items):
        rb = panel_alt if i % 2 == 0 else bg
        s_c = _status_color(t.status)
        cells = [
            f'{ck_data_cell(f"""{_html.escape(t.fund)}""", mono=True, weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{acc}">{_html.escape(t.movement_type)}</td>',
            f'{ck_data_cell(f"""{_html.escape(t.date)}""", align="right", mono=True, tone="dim")}',
            f'{ck_data_cell(f"""${t.amount_m:.1f}M""", align="right", mono=True, tone="pos", weight=700)}',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(t.from_entity)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-size:10px;color:{text_dim}">{_html.escape(t.to_entity)}</td>',
            f'<td style="text-align:left;padding:5px 10px;font-family:JetBrains Mono,monospace;font-size:10px;color:{text_dim}">{_html.escape(t.bank)}</td>',
            f'{ck_data_cell(f"""<span style="display:inline-block;padding:2px 8px;font-size:10px;font-family:JetBrains Mono,monospace;color:{s_c};border:1px solid {s_c};border-radius:2px;letter-spacing:0.06em">{_html.escape(t.status)}</span>""", align="center")}',
        ]
        trs.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div class="ck-data-table-scroll"><table class="ck-data-table">'
            f'<thead><tr>{ths}</tr></thead><tbody>{"".join(trs)}</tbody></table></div>')


def render_capital_call_tracker(params: dict = None) -> str:
    from rcm_mc.data_public.capital_call_tracker import compute_capital_call_tracker
    r = compute_capital_call_tracker()

    bg = P["bg"]; panel = P["panel"]; panel_alt = P["panel_alt"]
    border = P["border"]; text = P["text"]; text_dim = P["text_dim"]
    pos = P["positive"]; acc = P["accent"]; neg = P["negative"]

    net_color = pos if r.net_ltm_m >= 0 else neg
    kpi_strip = (
        ck_kpi_block("Active Funds", str(r.total_funds), "", "") +
        ck_kpi_block("Committed", f"${r.total_committed_b:.2f}B", "", "") +
        ck_kpi_block("Called", f"${r.total_called_b:.2f}B", "", "") +
        ck_kpi_block("Distributed", f"${r.total_distributed_b:.2f}B", "", "") +
        ck_kpi_block("LTM Calls", f"${r.ltm_calls_m:,.1f}M", "", "") +
        ck_kpi_block("LTM Distributions", f"${r.ltm_distributions_m:,.1f}M", "", "") +
        ck_kpi_block("LTM Net", f"${r.net_ltm_m:+,.1f}M", "", "") +
        ck_kpi_block("Corpus Deals", f"{r.corpus_deal_count:,}", "", "")
    )

    cf_tbl = _cashflow_table(r.cashflows)
    cal_chart = _calls_chart(r.calls)
    cal_tbl = _calls_table(r.calls)
    value_anchor = ck_value_anchor(
        "Capital Account",
        f"${r.total_called_b:,.1f}B called",
        delta=f"of ${r.total_committed_b:,.1f}B committed · ${r.total_distributed_b:,.1f}B distributed · {r.total_funds} funds",
        opportunity=f"${r.net_ltm_m:+,.0f}M net LTM cashflow",
        tone="teal",
    )
    d_tbl = _dist_table(r.distributions)
    lp_tbl = _lp_comms_table(r.lp_comms)
    rep_tbl = _reporting_table(r.reporting)
    tr_tbl = _treasury_table(r.treasury)

    cell = f"background:{panel};border:1px solid {border};padding:16px;margin-bottom:16px"
    h3 = f"font-size:11px;font-weight:600;letter-spacing:0.08em;color:{text_dim};text-transform:uppercase;margin-bottom:10px"

    pending_reports = sum(1 for r2 in r.reporting if r2.completion_status not in ("distributed",))
    active_requests = sum(1 for c in r.lp_comms if c.status in ("in progress", "discussing", "in review"))
    page_title = ck_page_title(
        "Capital Call / LP Communication Tracker",
        eyebrow="CAPITAL CALL TRACKER",
        meta=(
            f"{r.total_funds} funds · ${r.total_committed_b:.2f}B committed · "
            f"${r.total_called_b:.2f}B called · {r.corpus_deal_count:,} corpus deals"
        ),
    )
    cc_explainer = (
        '<p class="ck-cc-explainer">'
        "<em>What the capital call tracker reveals on this deal.</em> "
        "Fund cashflow roll-up, recent capital calls and distributions, LP communications, "
        "reporting schedule, and treasury movements across the fund portfolio."
        "</p>"
    )
    body = page_title + cc_explainer + f"""
<div class="ck-page-wrap">
  <div class="ck-kpi-grid" style="margin-bottom:20px">{kpi_strip}</div>
  {value_anchor}
  <div style="{cell}"><div style="{h3}">Fund Cashflow Roll-up</div>{cf_tbl}</div>
  <div style="{cell}"><div style="{h3}">Recent Capital Calls (LTM)</div>{cal_chart}{cal_tbl}</div>
  <div style="{cell}"><div style="{h3}">Recent Distributions (LTM)</div>{d_tbl}</div>
  <div style="{cell}"><div style="{h3}">LP Communications — Active & Recent</div>{lp_tbl}</div>
  <div style="{cell}"><div style="{h3}">Reporting Schedule</div>{rep_tbl}</div>
  <div style="{cell}"><div style="{h3}">Treasury Movements</div>{tr_tbl}</div>
  <div style="background:{panel_alt};border:1px solid {border};border-left:3px solid {acc};padding:12px 16px;font-size:11px;color:{text_dim};margin-bottom:16px">
    <strong style="color:{text}">Capital Flow Summary:</strong> ${r.total_committed_b:.2f}B committed across {r.total_funds} funds — {r.total_called_b / r.total_committed_b * 100 if r.total_committed_b else 0:.1f}% called to date.
    LTM activity: ${r.ltm_calls_m:,.1f}M in capital calls vs ${r.ltm_distributions_m:,.1f}M in distributions — net ${r.net_ltm_m:+,.1f}M (active deployment phase outpacing returns).
    Call pace: 12 new calls LTM averaging $329M per call — WCAS XV ($485M) and KKR III ($525M) are the two largest drawdowns for Project Azalea and Project Ridge.
    Distribution mix: 6 SBO exits ($1,630M), 1 IPO secondary ($545M), 1 dividend recap ($185M), 1 CV proceeds ($125M) — exit path diversification delivering LP liquidity despite strategic-sale drought.
    {active_requests} active LP requests including side-letter disclosure (Temasek), co-invest offers (CPPIB +$65M, Yale +$18M), and secondary inquiry (Adams Street, HarbourVest) — strong LP engagement.
    No LP defaults or late capital calls in the past 12 months — credit quality across {sum(1 for c in r.cashflows if c.unfunded_m > 0):,} funds with unfunded commitments remains pristine.
  </div>
</div>"""

    return chartis_shell(body, "Capital Call Tracker", active_nav="/capital-call",
        extra_css=_EXPLAINER_CSS)
