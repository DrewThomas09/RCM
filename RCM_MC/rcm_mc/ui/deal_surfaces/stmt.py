"""Surface 09 · 3-Statement — Income statement, Balance sheet, Cash flow.

Honesty bar: HCRIS reliably publishes the income-statement spine
(gross patient revenue → contractual allowances → net patient revenue →
operating expenses → net income) but does NOT carry balance-sheet line items
or a cash-flow statement at the detail the spec calls for. So this surface
ships:

  ✓ INCOME STATEMENT  — fully wired to HCRIS, every line tagged with its
                        source ("HCRIS" / "Computed") per the spec's
                        source-tag system.
  ⏸ BALANCE SHEET     — honest empty panel naming exactly what HCRIS is
                        missing and pointing to the diligence request list.
  ⏸ CASH FLOW         — same.

The "What this means" panel explains the source-tag system + what the
deal team should request next. Per the sweep spec, source tags render via
the .chip-mini editorial badge pattern.

When HCRIS gives nothing at all for the CCN, the entire surface renders
an honest "Statement reconstruction needs HCRIS line items" empty panel.
"""
from __future__ import annotations

import html as _html
from typing import Any, Dict, List, Optional, Tuple

from ._shell import _fmt_money, _fmt_pct, deal_shell


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


def _honest_empty_panel(title: str, lines: List[str], note: str = "") -> str:
    items = "".join(f"<li>{_html.escape(l)}</li>" for l in lines)
    return (
        '<section style="background:#faf6ec;border:1px solid #c9c1ac;'
        'padding:20px 22px;margin:0 0 18px;">'
        '<span style="font-family:var(--sc-mono);font-size:10px;'
        'letter-spacing:.18em;text-transform:uppercase;color:#b8842e;">'
        'HCRIS does not carry this</span>'
        f'<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
        f'line-height:1.15;margin:6px 0 8px;color:#15202b;">'
        f'{_html.escape(title)}</h3>'
        '<p style="font-family:var(--sc-serif);font-size:14px;line-height:1.55;'
        'color:#2a3a4a;margin:0 0 10px;">'
        'Lines this surface would render here are not in HCRIS at the line-item '
        'level the spec calls for. They are diligence-request territory:</p>'
        f'<ul style="font-family:var(--sc-serif);font-size:13.5px;line-height:1.55;'
        f'color:#2a3a4a;margin:0;padding-left:20px;">{items}</ul>'
        + (f'<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
           f'color:#6a7480;margin:10px 0 0;">{_html.escape(note)}</p>' if note else "")
        + '</section>'
    )


# Editorial source-tag chip (the sweep spec's .chip-mini pattern, scoped here)
def _tag(label: str, kind: str = "hcris") -> str:
    palette = {
        "hcris":     ("#1f7a5a", "#d6e8df"),   # green   = real HCRIS
        "computed":  ("#0b2341", "#dde3ec"),   # ink     = derived
        "needs":     ("#b5321e", "#fbe7e2"),   # coral   = request
        "benchmark": ("#a08227", "#ecdfb4"),   # gold    = research band
    }
    fg, bg = palette.get(kind, palette["hcris"])
    return (
        f'<span style="font-family:var(--sc-mono);font-size:9.5px;'
        f'letter-spacing:.12em;text-transform:uppercase;color:{fg};'
        f'background:{bg};border:1px solid {fg};padding:1px 6px;'
        f'margin-left:8px;">{_html.escape(label)}</span>'
    )


# ───────────────────────── income statement ─────────────────────────

def _income_statement(h: Dict[str, Any]) -> str:
    """Render the income statement from real HCRIS lines + computed subtotals.

    Lines are tagged HCRIS (raw column) or Computed (derived subtotal); every
    cell is real or "—". No benchmarks anywhere in this surface today.
    """
    gross = _safe_float(h.get("gross_patient_revenue"))
    contractual = _safe_float(h.get("contractual_allowances"))
    npr = _safe_float(h.get("net_patient_revenue"))
    opex = _safe_float(h.get("operating_expenses"))
    net_income = _safe_float(h.get("net_income"))

    # Derived/computed lines
    npr_check = (gross - contractual) if (gross is not None and contractual is not None) else None
    op_ebitda = (npr - opex) if (npr is not None and opex is not None) else None
    op_margin = (op_ebitda / npr) if (op_ebitda is not None and npr and npr > 0) else None

    rows: List[Tuple[str, Optional[float], str, bool]] = [
        ("Gross patient revenue",     gross,        "hcris",    False),
        ("Less: contractual allowances", -contractual if contractual is not None else None, "hcris", False),
        ("Net patient revenue",       npr,          "hcris",    True),
        ("Less: operating expenses",  -opex if opex is not None else None, "hcris", False),
        ("Operating EBITDA",          op_ebitda,    "computed", True),
        ("Operating margin",          None,         "computed", False),    # value rendered separately as pct
        ("Net income",                net_income,   "hcris",    True),
    ]
    body_rows = []
    for label, value, kind, bold in rows:
        value_html = _fmt_money(value) if value is not None else "—"
        # Op margin is a pct, not money
        if label == "Operating margin":
            value_html = _fmt_pct(op_margin) if op_margin is not None else "—"
        # Negative-as-coral rendering for subtractions
        color = "#15202b"
        if value is not None and value < 0:
            color = "#b5321e"
        weight = "500" if bold else "400"
        bg = "#faf6ec" if bold else "transparent"
        body_rows.append(
            f'<tr style="background:{bg};">'
            f'<td style="font-family:var(--sc-serif);font-size:14px;font-weight:{weight};'
            f'color:#15202b;padding:8px 0 8px 4px;">{_html.escape(label)}{_tag(kind)}</td>'
            f'<td class="num" style="font-family:var(--sc-mono);font-size:12px;'
            f'font-weight:{weight};color:{color};text-align:right;padding:8px 4px;'
            f'font-variant-numeric:tabular-nums;">{value_html}</td>'
            '</tr>'
        )
    # Reconciliation note if gross - contractual ≠ npr (HCRIS occasionally has rounding gaps)
    recon = ""
    if npr is not None and npr_check is not None:
        diff = npr - npr_check
        if abs(diff) > max(1000.0, abs(npr) * 0.001):
            recon = (
                '<p style="font-family:var(--sc-mono);font-size:10px;'
                'letter-spacing:.1em;color:#b8842e;margin:8px 0 0;">'
                f'NOTE: gross − contractual ({_fmt_money(npr_check)}) differs from '
                f'reported NPR ({_fmt_money(npr)}) by {_fmt_money(diff)}. '
                'This is a HCRIS rounding / classification gap; the reported NPR '
                'is what flows downstream.</p>'
            )
    return (
        '<table class="cad-table" style="width:100%;font-family:var(--sc-serif);">'
        '<tbody>' + "".join(body_rows) + '</tbody></table>'
        + recon +
        '<p style="font-family:var(--sc-mono);font-size:10px;letter-spacing:.1em;'
        'color:#6a7480;margin:10px 0 0;">'
        'EVERY LINE IS A REAL HCRIS COLUMN OR A SUBTOTAL COMPUTED FROM ONE. NO '
        'BENCHMARKS, NO IMPUTATIONS &mdash; "—" WHEN HCRIS HAS NO VALUE.</p>'
    )


def _balance_sheet_empty() -> str:
    return _honest_empty_panel(
        "Balance sheet",
        [
            "Current assets · cash + securities + AR + inventory",
            "Fixed assets · PP&E (net), intangibles, capitalized leases",
            "Current liabilities · AP, accrued payroll, current-portion debt",
            "Long-term liabilities · senior + sub debt, pension, deferred",
            "Equity · contributed capital + retained earnings",
        ],
        note="ASK MANAGEMENT FOR THE AUDITED BALANCE SHEET TO FILL THESE LINES."
    )


def _cash_flow_empty() -> str:
    return _honest_empty_panel(
        "Cash flow statement",
        [
            "Cash from operations · net income + non-cash add-backs ± Δ working capital",
            "Cash from investing · capex, acquisitions, asset sales",
            "Cash from financing · debt issued / repaid, equity in / out, distributions",
            "Net change in cash · sum of the three above",
            "Free cash flow · CFO − maintenance capex",
        ],
        note="CASH FLOW NEEDS A BALANCE SHEET PLUS CAPEX SCHEDULE — REQUEST BOTH."
    )


def _what_this_means(h: Dict[str, Any]) -> str:
    has_real_lines = _safe_float(h.get("net_patient_revenue")) is not None
    return (
        '<p style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.6;'
        'color:#2a3a4a;margin:0 0 12px;">'
        '<em style="color:#154e36;font-style:italic;">Each line is tagged '
        'with its source.</em> The four-bucket system the team uses '
        'everywhere applies here too:</p>'
        '<ul style="font-family:var(--sc-serif);font-size:13.5px;line-height:1.65;'
        'color:#2a3a4a;margin:0 0 12px;padding-left:20px;">'
        f'<li>{_tag("hcris", "hcris")} a reported HCRIS column on this filing year.</li>'
        f'<li>{_tag("computed", "computed")} a subtotal derived from one or more HCRIS lines (e.g. EBITDA = NPR − opex).</li>'
        f'<li>{_tag("needs", "needs")} a line that needs diligence-team input — defaults are not used.</li>'
        f'<li>{_tag("benchmark", "benchmark")} a research-band default applied when HCRIS does not carry a column (this surface does <strong>not</strong> use benchmarks today).</li>'
        '</ul>'
        + (
            '<p style="font-family:var(--sc-serif);font-size:13.5px;line-height:1.55;'
            'color:#2a3a4a;margin:0;">'
            'The Income Statement above is reconstructed entirely from HCRIS — '
            'no estimation, no defaults. The Balance Sheet and Cash Flow are '
            'left as honest empties because HCRIS does not publish those line '
            'items at the depth a deal team needs. Treat every "Needs data" '
            'badge that appears here as a diligence-request item.</p>'
            if has_real_lines else
            '<p style="font-family:var(--sc-serif);font-size:13.5px;line-height:1.55;'
            'color:#2a3a4a;margin:0;">'
            'HCRIS has no financial lines on file for this CCN, so the '
            'statement cannot be reconstructed.</p>'
        )
    )


def render_deal_stmt(ccn: str, hospital: Dict[str, Any]) -> str:
    """Render Surface 09 (3-Statement) for ``ccn``.

    Income Statement is real from HCRIS; Balance Sheet and Cash Flow are
    honest empty panels naming exactly what's missing.
    """
    npr = _safe_float(hospital.get("net_patient_revenue"))
    if npr is None:
        empty = (
            '<section style="background:#faf6ec;border:1px solid #c9c1ac;'
            'padding:24px 26px;">'
            '<span style="font-family:var(--sc-mono);font-size:10px;'
            'letter-spacing:.18em;text-transform:uppercase;color:#b8842e;">'
            'Statement reconstruction cannot run</span>'
            '<h3 style="font-family:var(--sc-serif);font-weight:400;font-size:22px;'
            f'margin:6px 0 12px;color:#15202b;">HCRIS has no income data for CCN {ccn}</h3>'
            '<p style="font-family:var(--sc-serif);font-size:14.5px;line-height:1.55;'
            'color:#2a3a4a;margin:0;">Without at least a net-patient-revenue '
            'line in HCRIS, no statement is shown here rather than fabricated.</p>'
            '</section>'
        )
        return deal_shell(
            ccn, hospital, active_slug="stmt", body_html=empty,
            page_title=f"3-Statement · {hospital.get('name') or f'CCN {ccn}'}",
        )

    panels = [
        _panel("01 · INCOME STATEMENT",
               "Reconstructed from real HCRIS lines",
               _income_statement(hospital)),
        _balance_sheet_empty(),
        _cash_flow_empty(),
        _panel("04 · WHAT THIS MEANS",
               "The source-tag system, applied here",
               _what_this_means(hospital)),
    ]
    body = "".join(panels)
    return deal_shell(
        ccn, hospital, active_slug="stmt", body_html=body,
        page_title=f"3-Statement · {hospital.get('name') or f'CCN {ccn}'}",
    )
