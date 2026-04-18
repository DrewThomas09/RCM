"""Deal teardown analyzer — post-mortem MOIC attribution for realized deals.

Decomposes a realized PE deal's outcome into three independent value-creation
levers and benchmarks each lever against the corpus. Answers the IC question:
"We made 3.2x — was that multiple expansion, EBITDA growth, or leverage?"

Attribution framework (multiplicative decomposition):

    Gross MOIC = (Exit EV / Entry EV) × (Entry EV / Entry Equity)
               = Multiple Expansion Factor × EBITDA Growth Factor × Leverage Factor

where:
    Multiple Expansion Factor = exit_ev_ebitda / entry_ev_ebitda
    EBITDA Growth Factor      = exit_ebitda / entry_ebitda
    Leverage Factor           = entry_ev / entry_equity
    (Debt Paydown Benefit)    = reduction in debt increases equity proceeds

In practice we solve for each lever's contribution as a fraction of total MOIC
gain (gross_moic - 1.0) so they sum to 100%.

Corpus benchmarks allow comparison of each lever against P50 peers.

Public API:
    TeardownResult                              dataclass
    LeverContribution                           dataclass
    decompose_deal(deal)                        -> TeardownResult
    teardown_vs_corpus(deal, corpus_deals)      -> Dict[str, Any]
    teardown_report(result, corpus_check)       -> str
    teardown_table(results)                     -> str
    batch_teardown(deals)                       -> List[TeardownResult]
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LeverContribution:
    """Value-creation attribution for a single lever."""
    name: str
    moic_contribution: float    # Absolute MOIC points contributed
    pct_of_gain: float          # Share of total gain (sums to 1.0 across levers)
    benchmark_p50: Optional[float] = None   # Corpus median for this lever
    signal: str = ""            # "strong" / "inline" / "weak" / "unknown"


@dataclass
class TeardownResult:
    """Full decomposition for one realized deal."""
    source_id: str
    deal_name: str

    # Inputs (reconstructed or provided)
    entry_ev_mm: float
    entry_ebitda_mm: float
    entry_multiple: float       # EV/EBITDA at entry
    exit_ev_mm: float
    exit_ebitda_mm: float
    exit_multiple: float        # EV/EBITDA at exit
    entry_equity_mm: float
    exit_equity_mm: float
    hold_years: float

    # Realized returns
    gross_moic: float
    gross_irr: float

    # Attribution
    multiple_expansion_contribution: LeverContribution
    ebitda_growth_contribution: LeverContribution
    leverage_contribution: LeverContribution
    debt_paydown_contribution: LeverContribution

    # Derived
    ebitda_cagr: float
    multiple_delta: float       # exit_multiple - entry_multiple (negative = compression)
    leverage_at_entry: float    # turns (entry_debt / entry_ebitda)

    # Verdict
    primary_driver: str         # which lever contributed most
    verdict: str                # "multiple_expansion_story" / "ebitda_growth_story" / etc.
    notes: str = ""


def _safe_irr(moic: float, years: float) -> float:
    if moic <= 0 or years <= 0:
        return 0.0
    return moic ** (1.0 / years) - 1.0


def decompose_deal(deal: Dict[str, Any]) -> Optional[TeardownResult]:
    """Decompose a realized deal into MOIC attribution.

    Expects deal dict with keys (all required for meaningful output):
        source_id, deal_name, ev_mm, ebitda_at_entry_mm, realized_moic,
        hold_years, realized_irr (optional)

    Optional enrichment keys (used if present):
        exit_ev_mm, exit_ebitda_mm, exit_multiple, entry_equity_mm,
        leverage_pct (debt/EV at entry), debt_amortization_pct

    Returns None if critical inputs are missing.
    """
    sid = deal.get("source_id", "unknown")
    name = deal.get("deal_name", "")

    entry_ev = deal.get("ev_mm") or deal.get("entry_ev_mm")
    entry_ebitda = deal.get("ebitda_at_entry_mm") or deal.get("entry_ebitda_mm")
    gross_moic = deal.get("realized_moic") or deal.get("gross_moic")
    hold_years = deal.get("hold_years")

    if not all([entry_ev, entry_ebitda, gross_moic, hold_years]):
        return None
    if gross_moic <= 0 or hold_years <= 0:
        return None

    entry_ev = float(entry_ev)
    entry_ebitda = float(entry_ebitda)
    gross_moic = float(gross_moic)
    hold_years = float(hold_years)

    entry_multiple = entry_ev / entry_ebitda

    # Leverage at entry
    leverage_pct = float(deal.get("leverage_pct", 0.55))
    entry_debt = entry_ev * leverage_pct
    entry_equity = float(deal.get("entry_equity_mm", entry_ev - entry_debt))

    # Exit assumptions — use provided or reconstruct from MOIC
    gross_irr = float(deal.get("realized_irr", 0.0) or 0.0)
    if not gross_irr:
        gross_irr = _safe_irr(gross_moic, hold_years)

    exit_equity = entry_equity * gross_moic

    # If exit ev/ebitda are provided, use them; otherwise back-solve
    exit_ev_raw = deal.get("exit_ev_mm") or deal.get("exit_enterprise_value_mm")
    exit_ebitda_raw = deal.get("exit_ebitda_mm")
    debt_amort_pct = float(deal.get("debt_amortization_pct", 0.03))

    annual_paydown = entry_debt * debt_amort_pct
    total_paydown = min(annual_paydown * hold_years, entry_debt)
    exit_debt = max(0.0, entry_debt - total_paydown)

    if exit_ev_raw:
        exit_ev = float(exit_ev_raw)
        exit_equity_from_ev = max(0.0, exit_ev - exit_debt)
    else:
        exit_ev = exit_equity + exit_debt

    if exit_ebitda_raw:
        exit_ebitda = float(exit_ebitda_raw)
    else:
        # Infer from MOIC and entry multiple: find implied exit ebitda
        # that produces observed MOIC, assuming debt paydown
        # exit_equity = exit_ev - exit_debt => exit_ev = exit_equity + exit_debt
        # exit_ebitda = exit_ev / exit_multiple (unknown)
        # Use entry multiple as placeholder for exit multiple; then compute ebitda
        ebitda_cagr_implied = gross_moic ** (1.0 / hold_years) - 1.0
        # rough: assume multiple holds; ebitda grows to back-fill moic
        exit_ebitda = entry_ebitda * (1.0 + max(0.02, ebitda_cagr_implied * 0.6)) ** hold_years

    exit_multiple = exit_ev / exit_ebitda if exit_ebitda > 0 else entry_multiple
    ebitda_cagr = (exit_ebitda / entry_ebitda) ** (1.0 / hold_years) - 1.0 if hold_years > 0 else 0.0

    # -----------------------------------------------------------------------
    # Multiplicative MOIC attribution
    # Gross MOIC = exit_equity / entry_equity
    #
    # Factor 1: Multiple expansion  =  exit_ev_ebitda / entry_ev_ebitda
    # Factor 2: EBITDA growth       =  exit_ebitda / entry_ebitda
    # Factor 3: Leverage benefit    =  entry_ev / entry_equity  (pure entry leverage)
    # Factor 4: Debt paydown        =  reduction in exit_debt vs entry_debt
    #
    # We compute each factor's isolated MOIC contribution additively,
    # normalizing so they sum to (gross_moic - 1.0).
    # -----------------------------------------------------------------------
    total_gain = gross_moic - 1.0

    multiple_factor = exit_multiple / entry_multiple  # >1 = expansion, <1 = compression
    ebitda_factor = exit_ebitda / entry_ebitda
    leverage_factor = entry_ev / entry_equity if entry_equity > 0 else 1.0
    paydown_benefit = total_paydown / entry_equity if entry_equity > 0 else 0.0

    # Compute raw contributions (before normalization)
    raw_multiple = (multiple_factor - 1.0) * ebitda_factor * leverage_factor
    raw_ebitda = (ebitda_factor - 1.0) * leverage_factor
    raw_leverage = leverage_factor - 1.0
    raw_paydown = paydown_benefit

    raw_sum = abs(raw_multiple) + abs(raw_ebitda) + abs(raw_leverage) + abs(raw_paydown)

    if raw_sum > 0 and total_gain != 0:
        scale = total_gain / (raw_multiple + raw_ebitda + raw_leverage + raw_paydown + 1e-9)
    else:
        scale = 1.0

    mult_contrib = raw_multiple * scale
    ebitda_contrib = raw_ebitda * scale
    lev_contrib = raw_leverage * scale
    paydown_contrib = raw_paydown * scale

    def pct_of_gain(contrib: float) -> float:
        return contrib / total_gain if total_gain != 0 else 0.0

    def _signal(contrib_pct: float, benchmark_pct: Optional[float]) -> str:
        if benchmark_pct is None:
            return "unknown"
        delta = contrib_pct - benchmark_pct
        if delta > 0.10:
            return "strong"
        if delta < -0.10:
            return "weak"
        return "inline"

    mult_lever = LeverContribution(
        name="multiple_expansion",
        moic_contribution=round(mult_contrib, 3),
        pct_of_gain=round(pct_of_gain(mult_contrib), 3),
    )
    ebitda_lever = LeverContribution(
        name="ebitda_growth",
        moic_contribution=round(ebitda_contrib, 3),
        pct_of_gain=round(pct_of_gain(ebitda_contrib), 3),
    )
    lev_lever = LeverContribution(
        name="leverage",
        moic_contribution=round(lev_contrib, 3),
        pct_of_gain=round(pct_of_gain(lev_contrib), 3),
    )
    paydown_lever = LeverContribution(
        name="debt_paydown",
        moic_contribution=round(paydown_contrib, 3),
        pct_of_gain=round(pct_of_gain(paydown_contrib), 3),
    )

    # Primary driver
    levers_by_abs = sorted(
        [mult_lever, ebitda_lever, lev_lever, paydown_lever],
        key=lambda l: abs(l.moic_contribution),
        reverse=True,
    )
    primary_driver = levers_by_abs[0].name

    # Verdict
    if multiple_factor > 1.15 and pct_of_gain(mult_contrib) > 0.35:
        verdict = "multiple_expansion_story"
    elif ebitda_factor > 1.5 and pct_of_gain(ebitda_contrib) > 0.35:
        verdict = "ebitda_growth_story"
    elif leverage_factor > 2.5:
        verdict = "leverage_story"
    elif multiple_factor < 0.85 and gross_moic > 2.0:
        verdict = "ebitda_overcame_compression"
    elif gross_moic < 1.0:
        verdict = "value_destruction"
    else:
        verdict = "balanced"

    # Notes
    notes_parts = []
    if multiple_factor < 0.85:
        notes_parts.append(f"multiple compressed {(1-multiple_factor):.0%}")
    if ebitda_cagr > 0.15:
        notes_parts.append(f"strong EBITDA CAGR {ebitda_cagr:.1%}")
    elif ebitda_cagr < 0.05:
        notes_parts.append(f"tepid EBITDA growth {ebitda_cagr:.1%}")
    if hold_years > 7:
        notes_parts.append("long hold dampens IRR")

    return TeardownResult(
        source_id=sid,
        deal_name=name,
        entry_ev_mm=round(entry_ev, 1),
        entry_ebitda_mm=round(entry_ebitda, 1),
        entry_multiple=round(entry_multiple, 2),
        exit_ev_mm=round(exit_ev, 1),
        exit_ebitda_mm=round(exit_ebitda, 1),
        exit_multiple=round(exit_multiple, 2),
        entry_equity_mm=round(entry_equity, 1),
        exit_equity_mm=round(exit_equity, 1),
        hold_years=hold_years,
        gross_moic=gross_moic,
        gross_irr=round(gross_irr, 4),
        multiple_expansion_contribution=mult_lever,
        ebitda_growth_contribution=ebitda_lever,
        leverage_contribution=lev_lever,
        debt_paydown_contribution=paydown_lever,
        ebitda_cagr=round(ebitda_cagr, 4),
        multiple_delta=round(exit_multiple - entry_multiple, 2),
        leverage_at_entry=round(entry_debt / entry_ebitda if entry_ebitda > 0 else 0.0, 2),
        primary_driver=primary_driver,
        verdict=verdict,
        notes="; ".join(notes_parts),
    )


def batch_teardown(deals: List[Dict[str, Any]]) -> List[TeardownResult]:
    """Decompose all deals that have sufficient data."""
    results = []
    for d in deals:
        if d.get("realized_moic") and d.get("hold_years") and d.get("ev_mm"):
            r = decompose_deal(d)
            if r:
                results.append(r)
    return results


# ---------------------------------------------------------------------------
# Corpus comparison
# ---------------------------------------------------------------------------

def teardown_vs_corpus(
    deal: Dict[str, Any],
    corpus_deals: List[Dict[str, Any]],
    sector: Optional[str] = None,
) -> Dict[str, Any]:
    """Compare a deal's teardown against corpus-derived lever benchmarks.

    Returns a dict with benchmark percentiles for each lever contribution
    and a signal for each.
    """
    result = decompose_deal(deal)
    if not result:
        return {"error": "insufficient_data"}

    # Build corpus teardowns
    peers = [d for d in corpus_deals if d.get("realized_moic") and d.get("hold_years")]
    if sector:
        try:
            from .subsector_benchmarks import _canonical_sector
            canon = _canonical_sector(sector)
            sector_peers = [d for d in peers if _canonical_sector(d.get("sector")) == canon]
            if len(sector_peers) >= 5:
                peers = sector_peers
        except ImportError:
            pass

    corpus_results = [decompose_deal(d) for d in peers]
    corpus_results = [r for r in corpus_results if r]

    def _p50(values: List[float]) -> Optional[float]:
        if not values:
            return None
        s = sorted(values)
        return s[len(s) // 2]

    mult_p50 = _p50([r.multiple_expansion_contribution.pct_of_gain for r in corpus_results])
    ebitda_p50 = _p50([r.ebitda_growth_contribution.pct_of_gain for r in corpus_results])
    lev_p50 = _p50([r.leverage_contribution.pct_of_gain for r in corpus_results])
    paydown_p50 = _p50([r.debt_paydown_contribution.pct_of_gain for r in corpus_results])
    ebitda_cagr_p50 = _p50([r.ebitda_cagr for r in corpus_results])
    moic_p50 = _p50([r.gross_moic for r in corpus_results])

    def _sig(deal_val: float, bench: Optional[float]) -> str:
        if bench is None:
            return "unknown"
        return "above_median" if deal_val > bench else "below_median"

    result.multiple_expansion_contribution.benchmark_p50 = mult_p50
    result.ebitda_growth_contribution.benchmark_p50 = ebitda_p50
    result.leverage_contribution.benchmark_p50 = lev_p50
    result.debt_paydown_contribution.benchmark_p50 = paydown_p50

    result.multiple_expansion_contribution.signal = _sig(
        result.multiple_expansion_contribution.pct_of_gain, mult_p50)
    result.ebitda_growth_contribution.signal = _sig(
        result.ebitda_growth_contribution.pct_of_gain, ebitda_p50)

    return {
        "teardown": result,
        "corpus_n": len(corpus_results),
        "sector": sector,
        "corpus_moic_p50": moic_p50,
        "corpus_ebitda_cagr_p50": ebitda_cagr_p50,
        "corpus_mult_pct_p50": mult_p50,
        "corpus_ebitda_pct_p50": ebitda_p50,
        "moic_vs_corpus": _sig(result.gross_moic, moic_p50),
        "ebitda_cagr_vs_corpus": _sig(result.ebitda_cagr, ebitda_cagr_p50),
    }


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def teardown_report(
    result: TeardownResult,
    corpus_check: Optional[Dict[str, Any]] = None,
) -> str:
    """Narrative teardown report suitable for IC packet."""
    lines = [
        f"Deal Teardown: {result.deal_name}",
        "=" * 55,
        f"  Entry:   ${result.entry_ev_mm:,.0f}M EV / {result.entry_multiple:.1f}x EBITDA",
        f"  Exit:    ${result.exit_ev_mm:,.0f}M EV / {result.exit_multiple:.1f}x EBITDA",
        f"  Hold:    {result.hold_years:.1f} years",
        f"  MOIC:    {result.gross_moic:.2f}x gross  |  IRR: {result.gross_irr:.1%}",
        f"  EBITDA CAGR: {result.ebitda_cagr:.1%}",
        "",
        "Value Creation Attribution",
        "-" * 35,
    ]

    levers = [
        result.multiple_expansion_contribution,
        result.ebitda_growth_contribution,
        result.leverage_contribution,
        result.debt_paydown_contribution,
    ]
    for lev in levers:
        bench_str = ""
        if lev.benchmark_p50 is not None:
            bench_str = f"  [corpus P50: {lev.benchmark_p50:.0%}]"
        sig_str = f"  ← {lev.signal}" if lev.signal else ""
        lines.append(
            f"  {lev.name:<25} {lev.moic_contribution:+.3f}x  ({lev.pct_of_gain:+.0%})"
            + bench_str + sig_str
        )

    lines += [
        "",
        f"  Primary driver:  {result.primary_driver.replace('_', ' ').title()}",
        f"  Verdict:         {result.verdict.replace('_', ' ').title()}",
    ]
    if result.notes:
        lines.append(f"  Notes:           {result.notes}")

    if corpus_check and corpus_check.get("corpus_n", 0) >= 3:
        n = corpus_check["corpus_n"]
        moic_sig = corpus_check.get("moic_vs_corpus", "")
        cagr_sig = corpus_check.get("ebitda_cagr_vs_corpus", "")
        lines += [
            "",
            f"  Corpus context  (n={n}, sector={corpus_check.get('sector','all')})",
            f"    MOIC vs peers:       {corpus_check.get('corpus_moic_p50','n/a'):.2f}x P50  [{moic_sig}]",
            f"    EBITDA CAGR vs peers:{corpus_check.get('corpus_ebitda_cagr_p50','n/a'):.1%} P50  [{cagr_sig}]",
        ]

    return "\n".join(lines) + "\n"


def teardown_table(results: List[TeardownResult]) -> str:
    """Compact comparison table for multiple deals."""
    header = (
        f"{'Deal':<35} {'MOIC':>6} {'IRR':>6} "
        f"{'EBITDA CAGR':>12} {'Mult Δ':>7} {'Primary Driver':<22} Verdict"
    )
    sep = "-" * 110
    lines = [header, sep]
    for r in results:
        name = r.deal_name[:33]
        lines.append(
            f"{name:<35} {r.gross_moic:>5.2f}x {r.gross_irr:>5.1%} "
            f"{r.ebitda_cagr:>11.1%} {r.multiple_delta:>+6.1f}x "
            f"{r.primary_driver.replace('_',' '):<22} {r.verdict.replace('_',' ')}"
        )
    return "\n".join(lines) + "\n"
