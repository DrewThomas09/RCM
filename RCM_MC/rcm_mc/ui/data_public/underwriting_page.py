"""Deal Underwriting Calculator page — /underwriting.

Interactive LBO model: user inputs entry EV, EBITDA, equity%, EBITDA CAGR,
hold years, and exit multiple. Output: MOIC, IRR, debt paydown waterfall,
corpus-benchmarked percentile ranks, and a sensitivity table.

No DB required — all corpus benchmarking is in-memory.
"""
from __future__ import annotations

import html as _html
import importlib
from typing import Any, Dict, List, Optional


def _load_corpus() -> List[Dict[str, Any]]:
    from rcm_mc.data_public.deals_corpus import _SEED_DEALS
    from rcm_mc.data_public.extended_seed import EXTENDED_SEED_DEALS
    result = list(_SEED_DEALS) + list(EXTENDED_SEED_DEALS)
    for i in range(2, 32):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            result += list(getattr(mod, f"EXTENDED_SEED_DEALS_{i}"))
        except (ImportError, AttributeError):
            pass
    return result


def _percentile(vals: List[float], p: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = p / 100 * (len(s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)


def _percentile_rank(vals: List[float], target: float) -> float:
    if not vals:
        return 50.0
    return sum(1 for v in vals if v <= target) / len(vals) * 100


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

def _num(v: Optional[float], decimals: int = 2, suffix: str = "", prefix: str = "") -> str:
    if v is None:
        return '<span style="color:var(--ck-text-faint)">—</span>'
    return (
        f'<span style="font-family:var(--ck-mono);font-variant-numeric:tabular-nums">'
        f'{prefix}{v:.{decimals}f}{suffix}</span>'
    )


def _moic_html(v: Optional[float]) -> str:
    if v is None:
        return "—"
    color = "#b5321e" if v < 1.0 else ("#22c55e" if v >= 2.5 else "#b8732a")
    return (
        f'<span style="font-family:var(--ck-mono);font-variant-numeric:tabular-nums;'
        f'font-size:22px;font-weight:700;color:{color}">{v:.2f}×</span>'
    )


def _irr_html(v: Optional[float]) -> str:
    if v is None:
        return "—"
    color = "#b5321e" if v < 0.10 else ("#22c55e" if v >= 0.20 else "#b8732a")
    return (
        f'<span style="font-family:var(--ck-mono);font-variant-numeric:tabular-nums;'
        f'font-size:22px;font-weight:700;color:{color}">{v*100:.1f}%</span>'
    )


def _pct_rank_bar(rank: float, width: int = 120) -> str:
    """Horizontal percentile bar."""
    filled = int(rank / 100 * width)
    color = "#22c55e" if rank >= 60 else ("#b8732a" if rank >= 35 else "#b5321e")
    return (
        f'<div style="display:inline-flex;align-items:center;gap:6px;">'
        f'<svg width="{width}" height="8" xmlns="http://www.w3.org/2000/svg" style="display:inline-block;vertical-align:middle;">'
        f'<rect x="0" y="1" width="{width}" height="6" rx="1" fill="#d6cfc3"/>'
        f'<rect x="0" y="1" width="{filled}" height="6" rx="1" fill="{color}"/>'
        f'</svg>'
        f'<span style="font-family:var(--ck-mono);font-size:9.5px;color:{color};font-variant-numeric:tabular-nums">'
        f'{rank:.0f}th pctile</span>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Forms
# ---------------------------------------------------------------------------

def _input_form(params: Dict[str, str]) -> str:
    def _v(k: str, d: str = "") -> str:
        return _html.escape(params.get(k, d))

    return f"""
<div class="ck-panel">
  <div class="ck-panel-title">LBO Parameters</div>
  <form method="get" action="/underwriting" style="padding:14px 16px;">
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px 24px;">
      <div>
        <div class="ck-section-label" style="margin-bottom:5px;">Entry EV ($M)</div>
        <input type="number" name="entry_ev" value="{_v('entry_ev','200')}" step="5" class="ck-input" style="width:120px;">
      </div>
      <div>
        <div class="ck-section-label" style="margin-bottom:5px;">Entry EBITDA ($M)</div>
        <input type="number" name="entry_ebitda" value="{_v('entry_ebitda','20')}" step="1" class="ck-input" style="width:120px;">
      </div>
      <div>
        <div class="ck-section-label" style="margin-bottom:5px;">Equity Contribution %</div>
        <input type="number" name="equity_pct" value="{_v('equity_pct','40')}" step="5" min="10" max="100" class="ck-input" style="width:120px;">
      </div>
      <div>
        <div class="ck-section-label" style="margin-bottom:5px;">EBITDA CAGR %</div>
        <input type="number" name="ebitda_cagr" value="{_v('ebitda_cagr','10')}" step="1" class="ck-input" style="width:120px;">
      </div>
      <div>
        <div class="ck-section-label" style="margin-bottom:5px;">Hold Years</div>
        <input type="number" name="hold_years" value="{_v('hold_years','5')}" step="0.5" min="1" max="15" class="ck-input" style="width:120px;">
      </div>
      <div>
        <div class="ck-section-label" style="margin-bottom:5px;">Exit Multiple (×)</div>
        <input type="number" name="exit_multiple" value="{_v('exit_multiple','10')}" step="0.5" class="ck-input" style="width:120px;">
      </div>
    </div>
    <div style="margin-top:14px;">
      <button type="submit" class="ck-btn">Run Underwriting</button>
      <span style="margin-left:12px;font-size:10px;color:var(--ck-text-faint);">
        Assumes 7.5% interest rate · 3% annual debt amortization · 2% transaction fees
      </span>
    </div>
  </form>
</div>"""


# ---------------------------------------------------------------------------
# Results rendering
# ---------------------------------------------------------------------------

def _results_panel(result: Any, corpus: List[Dict[str, Any]]) -> str:
    """IC-grade results panel with corpus benchmarking."""
    from rcm_mc.data_public.deal_underwriting_model import sensitivity_table

    # Corpus distributions
    realized = [d for d in corpus if d.get("realized_moic") is not None]
    corpus_moics = [float(d["realized_moic"]) for d in realized]
    corpus_irrs = [float(d["realized_irr"]) for d in realized if d.get("realized_irr") is not None]

    moic_rank = _percentile_rank(corpus_moics, result.gross_moic) if result.gross_moic else 50.0
    irr_rank = _percentile_rank(corpus_irrs, result.gross_irr) if result.gross_irr else 50.0

    # Summary cards row
    cards_html = f"""
<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:1px;background:var(--ck-border);margin-bottom:1px;">
  <div style="background:var(--ck-panel-alt);padding:14px 16px;">
    <div style="font-size:8.5px;color:var(--ck-text-faint);letter-spacing:0.12em;text-transform:uppercase;margin-bottom:6px;">Gross MOIC</div>
    {_moic_html(result.gross_moic)}
    <div style="margin-top:6px;">{_pct_rank_bar(moic_rank)}</div>
    <div style="font-size:9px;color:var(--ck-text-faint);margin-top:3px;">vs. corpus realized</div>
  </div>
  <div style="background:var(--ck-panel-alt);padding:14px 16px;">
    <div style="font-size:8.5px;color:var(--ck-text-faint);letter-spacing:0.12em;text-transform:uppercase;margin-bottom:6px;">Gross IRR</div>
    {_irr_html(result.gross_irr)}
    <div style="margin-top:6px;">{_pct_rank_bar(irr_rank)}</div>
    <div style="font-size:9px;color:var(--ck-text-faint);margin-top:3px;">vs. corpus realized</div>
  </div>
  <div style="background:var(--ck-panel-alt);padding:14px 16px;">
    <div style="font-size:8.5px;color:var(--ck-text-faint);letter-spacing:0.12em;text-transform:uppercase;margin-bottom:6px;">Net MOIC (after fees)</div>
    {_moic_html(result.net_moic)}
    <div style="margin-top:6px;font-size:10px;color:var(--ck-text-faint);">
      Net IRR: {_irr_html(result.net_irr).replace('22px', '13px').replace('font-weight:700', 'font-weight:500')}
    </div>
  </div>
  <div style="background:var(--ck-panel-alt);padding:14px 16px;">
    <div style="font-size:8.5px;color:var(--ck-text-faint);letter-spacing:0.12em;text-transform:uppercase;margin-bottom:6px;">Entry / Exit Summary</div>
    <div style="font-family:var(--ck-mono);font-size:10.5px;line-height:1.8;font-variant-numeric:tabular-nums;">
      <div>Entry EV/EBITDA: <strong>{result.entry_ev_ebitda:.1f}×</strong></div>
      <div>Entry Equity: ${result.entry_equity_mm:.0f}M</div>
      <div>Entry Debt: ${result.entry_debt_mm:.0f}M</div>
      <div>Exit EV: ${result.exit_ev_mm:.0f}M</div>
      <div>Exit Equity: ${result.exit_equity_mm:.0f}M</div>
    </div>
  </div>
</div>"""

    # Sensitivity table
    try:
        sens = sensitivity_table(result.assumptions)
        sens_rows = []
        for row in sens:
            hold = row.get("hold_years")
            cells = [f'<td class="mono dim" style="padding:6px 8px;">{hold:.1f}yr</td>']
            for mult_key in sorted([k for k in row if k != "hold_years"]):
                r = row[mult_key]
                if isinstance(r, dict):
                    moic = r.get("gross_moic")
                    color = "#b5321e" if (moic or 0) < 1.0 else ("#22c55e" if (moic or 0) >= 2.5 else "#1a2332")
                    cells.append(
                        f'<td style="text-align:right;padding:6px 8px;">'
                        f'<span style="font-family:var(--ck-mono);font-variant-numeric:tabular-nums;color:{color}">'
                        f'{moic:.2f}×</span></td>'
                    )
            sens_rows.append(f'<tr>{"".join(cells)}</tr>')

        # Get unique exit multiples for header
        mult_keys = sorted([k for k in (sens[0] if sens else {}) if k != "hold_years"])
        mult_headers = "".join(
            f'<th style="text-align:right;padding:6px 8px;">Exit {k}×</th>'
            for k in mult_keys
        )
        sens_html = f"""
<div class="ck-panel" style="margin-top:0;">
  <div class="ck-panel-title">MOIC Sensitivity — Hold Years × Exit Multiple</div>
  <div class="ck-table-wrap">
    <table class="ck-table" style="width:auto;">
      <thead><tr><th>Hold</th>{mult_headers}</tr></thead>
      <tbody>{''.join(sens_rows)}</tbody>
    </table>
  </div>
</div>"""
    except Exception:
        sens_html = ""

    return f"""
<div class="ck-panel">
  <div class="ck-panel-title">Underwriting Results</div>
  {cards_html}
</div>
{sens_html}"""


def _corpus_benchmark_panel(result: Any, corpus: List[Dict[str, Any]]) -> str:
    """How does this deal compare to corpus deals at similar entry multiples?"""
    entry_mult = result.entry_ev_ebitda if result else None
    if entry_mult is None:
        return ""

    # Find comparable-multiple corpus deals
    comparable = []
    for d in corpus:
        ev = d.get("ev_mm") or d.get("entry_ev_mm")
        eb = d.get("ebitda_at_entry_mm") or d.get("ebitda_mm")
        moic = d.get("realized_moic")
        if ev and eb and moic and float(eb) > 0:
            m = float(ev) / float(eb)
            if abs(m - entry_mult) <= 3.0:  # within 3× of entry multiple
                comparable.append({"multiple": m, "moic": float(moic), "name": d.get("deal_name", "")})

    if not comparable:
        return ""

    comp_moics = sorted([c["moic"] for c in comparable])
    p25 = _percentile(comp_moics, 25)
    p50 = _percentile(comp_moics, 50)
    p75 = _percentile(comp_moics, 75)
    loss = sum(1 for m in comp_moics if m < 1.0) / len(comp_moics)

    model_moic = result.gross_moic or 0
    moic_vs_p50 = model_moic - p50

    comp_rank = _percentile_rank(comp_moics, model_moic)

    delta_color = "#22c55e" if moic_vs_p50 > 0 else "#b5321e"
    sign = "+" if moic_vs_p50 > 0 else ""

    return f"""
<div class="ck-panel">
  <div class="ck-panel-title">Corpus Benchmark — {len(comparable)} deals at {entry_mult:.1f}± 3× entry multiple</div>
  <div style="padding:12px 16px;display:grid;grid-template-columns:1fr 1fr 1fr 1fr 1fr;gap:1px;background:var(--ck-border);">
    <div style="background:var(--ck-panel-alt);padding:10px 12px;">
      <div class="ck-section-label" style="margin-bottom:4px;">Peer P25 MOIC</div>
      <div style="font-family:var(--ck-mono);font-size:14px;font-variant-numeric:tabular-nums;">{p25:.2f}×</div>
    </div>
    <div style="background:var(--ck-panel-alt);padding:10px 12px;">
      <div class="ck-section-label" style="margin-bottom:4px;">Peer P50 MOIC</div>
      <div style="font-family:var(--ck-mono);font-size:14px;font-variant-numeric:tabular-nums;">{p50:.2f}×</div>
    </div>
    <div style="background:var(--ck-panel-alt);padding:10px 12px;">
      <div class="ck-section-label" style="margin-bottom:4px;">Peer P75 MOIC</div>
      <div style="font-family:var(--ck-mono);font-size:14px;font-variant-numeric:tabular-nums;">{p75:.2f}×</div>
    </div>
    <div style="background:var(--ck-panel-alt);padding:10px 12px;">
      <div class="ck-section-label" style="margin-bottom:4px;">Peer Loss Rate</div>
      <div style="font-family:var(--ck-mono);font-size:14px;color:#b5321e;font-variant-numeric:tabular-nums;">{loss*100:.1f}%</div>
    </div>
    <div style="background:var(--ck-panel-alt);padding:10px 12px;">
      <div class="ck-section-label" style="margin-bottom:4px;">Model vs Peer P50</div>
      <div style="font-family:var(--ck-mono);font-size:14px;color:{delta_color};font-variant-numeric:tabular-nums;">{sign}{moic_vs_p50:.2f}×</div>
      <div style="font-size:9px;color:var(--ck-text-faint);margin-top:2px;">{comp_rank:.0f}th percentile</div>
    </div>
  </div>
</div>"""


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------

def render_underwriting(
    entry_ev: Optional[float] = None,
    entry_ebitda: Optional[float] = None,
    equity_pct: Optional[float] = None,
    ebitda_cagr: Optional[float] = None,
    hold_years: Optional[float] = None,
    exit_multiple: Optional[float] = None,
) -> str:
    from rcm_mc.ui._chartis_kit import chartis_shell, ck_section_header, ck_kpi_block

    # Default values
    ev = entry_ev or 200.0
    eb = entry_ebitda or 20.0
    eq = (equity_pct or 40.0) / 100.0
    cagr = (ebitda_cagr or 10.0) / 100.0
    hold = hold_years or 5.0
    exit_mult = exit_multiple or 10.0

    has_input = any(v is not None for v in [entry_ev, entry_ebitda, equity_pct, ebitda_cagr, hold_years, exit_multiple])

    params = {
        "entry_ev": str(int(ev)),
        "entry_ebitda": str(int(eb)),
        "equity_pct": str(int((eq) * 100)),
        "ebitda_cagr": str(int(cagr * 100)),
        "hold_years": str(hold),
        "exit_multiple": str(exit_mult),
    }

    corpus = _load_corpus()
    result = None
    results_html = ""
    benchmark_html = ""

    try:
        from rcm_mc.data_public.deal_underwriting_model import underwrite_deal, UnderwritingAssumptions
        assumptions = UnderwritingAssumptions(
            entry_ev_mm=ev,
            entry_ebitda_mm=eb,
            equity_contribution_pct=eq,
            ebitda_cagr=cagr,
            hold_years=hold,
            exit_multiple=exit_mult,
        )
        result = underwrite_deal(assumptions)
        results_html = _results_panel(result, corpus)
        benchmark_html = _corpus_benchmark_panel(result, corpus)
    except Exception as exc:
        results_html = f'<div class="ck-panel"><div style="padding:12px;color:#b5321e;">Error: {_html.escape(str(exc))}</div></div>'

    # KPI bar (corpus context)
    realized = [d for d in corpus if d.get("realized_moic") is not None]
    moics = sorted([float(d["realized_moic"]) for d in realized])
    irrs = sorted([float(d["realized_irr"]) for d in realized if d.get("realized_irr") is not None])

    kpis = (
        '<div class="ck-kpi-grid">'
        + ck_kpi_block("Corpus P50 MOIC",
                       f'<span class="mn">{_percentile(moics, 50):.2f}×</span>', "realized")
        + ck_kpi_block("Corpus P50 IRR",
                       f'<span class="mn">{_percentile(irrs, 50)*100:.1f}%</span>', "realized")
        + ck_kpi_block("Model MOIC",
                       f'<span class="mn" style="color:{"#22c55e" if (result.gross_moic or 0) >= 2.5 else "#b8732a"}">'
                       f'{result.gross_moic:.2f}×</span>' if result else '<span class="faint">—</span>', "projected")
        + ck_kpi_block("Model IRR",
                       f'<span class="mn">{result.gross_irr*100:.1f}%</span>' if result else '<span class="faint">—</span>', "projected")
        + ck_kpi_block("Entry Multiple",
                       f'<span class="mn">{ev/eb:.1f}×</span>', "EV/EBITDA")
        + '</div>'
    )

    body = (
        kpis
        + _input_form(params)
        + (ck_section_header("UNDERWRITING RESULTS", f"EV ${ev:.0f}M · EBITDA ${eb:.0f}M · {eq*100:.0f}% equity · {cagr*100:.0f}% CAGR · {hold:.1f}yr hold · {exit_mult:.1f}× exit") + results_html + benchmark_html)
    )

    return chartis_shell(
        body,
        title="Deal Underwriting",
        active_nav="/underwriting",
        subtitle=(
            f"EV ${ev:.0f}M · EV/EBITDA {ev/eb:.1f}× · "
            + (f"MOIC {result.gross_moic:.2f}× · IRR {result.gross_irr*100:.1f}%" if result else "enter parameters above")
        ),
    )
