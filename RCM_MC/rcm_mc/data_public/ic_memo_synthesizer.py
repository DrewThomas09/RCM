"""IC memo synthesizer — integrates all corpus analytics into a single IC packet.

One-call entry point that pulls every quantitative signal from:
  1.  LBO entry optimizer  (max affordable entry multiple)
  2.  Hold period optimizer (MOIC-maximizing exit window)
  3.  Reimbursement risk   (rate shock scenarios)
  4.  Subsector benchmarks (P25/P50/P75 for the sector)
  5.  Sponsor track record (buyer consistency / league table signal)
  6.  Deal teardown        (attribution for comparable realized deals)
  7.  Base rates           (overall corpus P25/P50/P75)
  8.  PE intelligence      (red-flag check)

Returns an IcPacket dataclass and a partner-ready text report.
Gracefully degrades — missing analytics do not fail the whole packet.

Public API:
    IcPacket                              dataclass
    build_ic_packet(deal, corpus_deals,
                    entry_assumptions)    -> IcPacket
    ic_packet_report(packet)             -> str
    quick_ic_report(deal, corpus_deals)  -> str  (one-call shortcut)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class IcPacket:
    """Full quantitative IC packet for a prospective deal."""

    deal: Dict[str, Any]

    # LBO entry
    max_entry_multiple: Optional[float] = None
    lbo_feasible: Optional[bool] = None
    lbo_warnings: List[str] = field(default_factory=list)
    entry_corpus_signal: str = "unknown"    # conservative/below_median/above_median/aggressive

    # Hold optimization
    moic_maximizing_year: Optional[float] = None
    irr_maximizing_year: Optional[float] = None
    sweet_spot_start: Optional[float] = None
    sweet_spot_end: Optional[float] = None
    peak_gross_moic: Optional[float] = None
    cliff_year: Optional[float] = None

    # Reimbursement risk
    base_ebitda_impact: Optional[float] = None        # % EBITDA impact under base_case
    moderate_cut_impact: Optional[float] = None       # % EBITDA impact under moderate_cut
    severe_cut_severity: Optional[str] = None         # "low"/"moderate"/"high"/"severe"

    # Subsector benchmarks
    sector_moic_p25: Optional[float] = None
    sector_moic_p50: Optional[float] = None
    sector_moic_p75: Optional[float] = None
    sector_hold_p50: Optional[float] = None
    sector_loss_rate: Optional[float] = None
    sector_home_run_rate: Optional[float] = None

    # Sponsor track record
    sponsor_consistency_score: Optional[float] = None
    sponsor_median_moic: Optional[float] = None
    sponsor_deal_count: Optional[int] = None
    sponsor_signal: str = "unknown"

    # Corpus base rates
    corpus_moic_p50: Optional[float] = None
    corpus_irr_p50: Optional[float] = None

    # Red flags
    red_flags: List[str] = field(default_factory=list)
    red_flag_count: int = 0

    # Teardown comparables (top 3 from corpus)
    teardown_comps: List[Dict[str, Any]] = field(default_factory=list)

    # Overall signal
    overall_signal: str = "yellow"   # "green" / "yellow" / "red"
    signal_rationale: str = ""


def build_ic_packet(
    deal: Dict[str, Any],
    corpus_deals: List[Dict[str, Any]],
    entry_assumptions: Optional[Dict[str, Any]] = None,
) -> IcPacket:
    """Build a full IC packet for a deal.

    Args:
        deal:               Deal dict with at minimum ev_mm, ebitda_at_entry_mm,
                            sector, realized_moic (if realized), buyer.
        corpus_deals:       Raw seed dicts for benchmarking.
        entry_assumptions:  Optional overrides for LBO entry optimizer
                            (ebitda_cagr, hold_years, exit_multiple, leverage_pct).
    """
    packet = IcPacket(deal=deal)

    ev = float(deal.get("ev_mm") or deal.get("entry_ev_mm") or 0)
    ebitda = float(deal.get("ebitda_at_entry_mm") or deal.get("ebitda_mm") or 0)
    sector = deal.get("sector")
    buyer = deal.get("buyer") or ""

    ea = entry_assumptions or {}

    # ------------------------------------------------------------------
    # 1. LBO entry optimizer
    # ------------------------------------------------------------------
    try:
        from .lbo_entry_optimizer import LBOAssumptions, solve_entry_multiple, entry_vs_corpus
        if ebitda > 0:
            assumptions = LBOAssumptions(
                entry_ebitda_mm=ebitda,
                ebitda_cagr=float(ea.get("ebitda_cagr", 0.10)),
                hold_years=float(ea.get("hold_years", 5.0)),
                exit_multiple=float(ea.get("exit_multiple", (ev / ebitda) if ebitda else 10.0)),
                leverage_pct=float(ea.get("leverage_pct", 0.55)),
            )
            lbo_result = solve_entry_multiple(assumptions, target_moic=ea.get("target_moic", 2.5))
            packet.max_entry_multiple = lbo_result.entry_multiple
            packet.lbo_feasible = lbo_result.feasible
            packet.lbo_warnings = lbo_result.warnings or []

            corpus_check = entry_vs_corpus(deal, assumptions, corpus_deals, sector)
            packet.entry_corpus_signal = corpus_check.get("signal", "unknown")
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 2. Hold period optimizer
    # ------------------------------------------------------------------
    try:
        from .hold_period_optimizer import compute_hold_curve, find_optimal_exit
        if ebitda > 0 and ev > 0:
            curve = compute_hold_curve(
                entry_ebitda_mm=ebitda,
                entry_multiple=ev / ebitda,
                ebitda_cagr=float(ea.get("ebitda_cagr", 0.10)),
                sector=sector,
                max_years=10,
            )
            optimal = find_optimal_exit(curve)
            packet.moic_maximizing_year = optimal.moic_maximizing_year
            packet.irr_maximizing_year = optimal.irr_maximizing_year
            packet.sweet_spot_start = optimal.sweet_spot_start
            packet.sweet_spot_end = optimal.sweet_spot_end
            packet.peak_gross_moic = optimal.peak_gross_moic
            packet.cliff_year = optimal.cliff_year
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 3. Reimbursement risk
    # ------------------------------------------------------------------
    try:
        from .reimbursement_risk_model import model_reimbursement_risk
        risk_deal = dict(deal)
        if "ebitda_mm" not in risk_deal and ebitda:
            risk_deal["ebitda_mm"] = ebitda
        if "ev_ebitda" not in risk_deal and ev and ebitda:
            risk_deal["ev_ebitda"] = ev / ebitda
        scenarios = model_reimbursement_risk(risk_deal)
        if "base_case" in scenarios:
            packet.base_ebitda_impact = scenarios["base_case"].ebitda_impact
        if "moderate_cut" in scenarios:
            packet.moderate_cut_impact = scenarios["moderate_cut"].ebitda_impact
        if "severe_cut" in scenarios:
            packet.severe_cut_severity = scenarios["severe_cut"].severity
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 4. Subsector benchmarks
    # ------------------------------------------------------------------
    try:
        from .subsector_benchmarks import get_sector_benchmark
        bench = get_sector_benchmark(corpus_deals, sector or "")
        if bench:
            packet.sector_moic_p25 = bench.moic_p25
            packet.sector_moic_p50 = bench.moic_p50
            packet.sector_moic_p75 = bench.moic_p75
            packet.sector_hold_p50 = bench.hold_p50
            packet.sector_loss_rate = bench.loss_rate
            packet.sector_home_run_rate = bench.home_run_rate
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 5. Sponsor track record
    # ------------------------------------------------------------------
    try:
        from .sponsor_track_record import build_sponsor_records, _extract_sponsors
        if buyer:
            sponsors = _extract_sponsors(deal)
            records = build_sponsor_records(corpus_deals)
            for s in sponsors:
                if s in records:
                    rec = records[s]
                    packet.sponsor_consistency_score = rec.consistency_score
                    packet.sponsor_median_moic = rec.median_moic
                    packet.sponsor_deal_count = rec.deal_count
                    if rec.median_moic and rec.median_moic >= 3.0:
                        packet.sponsor_signal = "top_quartile"
                    elif rec.median_moic and rec.median_moic >= 2.0:
                        packet.sponsor_signal = "above_median"
                    elif rec.median_moic and rec.median_moic < 1.5:
                        packet.sponsor_signal = "below_median"
                    else:
                        packet.sponsor_signal = "inline"
                    break
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 6. Corpus base rates (computed directly from raw dicts)
    # ------------------------------------------------------------------
    try:
        moics = sorted([float(d["realized_moic"]) for d in corpus_deals if d.get("realized_moic")])
        irrs = sorted([float(d["realized_irr"]) for d in corpus_deals if d.get("realized_irr")])
        if moics:
            packet.corpus_moic_p50 = moics[len(moics) // 2]
        if irrs:
            packet.corpus_irr_p50 = irrs[len(irrs) // 2]
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 7. Red flag check
    # ------------------------------------------------------------------
    try:
        from .pe_intelligence import detect_red_flags
        flags = detect_red_flags(deal)
        packet.red_flags = [f.get("flag", str(f)) if isinstance(f, dict) else str(f) for f in flags]
        packet.red_flag_count = len(flags)
    except Exception:
        pass

    # ------------------------------------------------------------------
    # 8. Teardown comps (3 closest realized deals)
    # ------------------------------------------------------------------
    try:
        from .deal_teardown_analyzer import batch_teardown
        realized = [d for d in corpus_deals
                    if d.get("realized_moic") and d.get("hold_years") and d.get("ev_mm")]
        if len(realized) >= 3:
            td_results = batch_teardown(realized[:30])
            packet.teardown_comps = [
                {
                    "deal_name": r.deal_name,
                    "gross_moic": r.gross_moic,
                    "ebitda_cagr": r.ebitda_cagr,
                    "primary_driver": r.primary_driver,
                    "verdict": r.verdict,
                }
                for r in td_results[:3]
            ]
    except Exception:
        pass

    # ------------------------------------------------------------------
    # Overall signal
    # ------------------------------------------------------------------
    red_signals = 0
    if packet.red_flag_count >= 3:
        red_signals += 2
    elif packet.red_flag_count >= 1:
        red_signals += 1
    if packet.entry_corpus_signal == "aggressive":
        red_signals += 2
    if packet.severe_cut_severity in ("high", "severe"):
        red_signals += 1
    if packet.sector_loss_rate and packet.sector_loss_rate > 0.25:
        red_signals += 1
    if packet.sponsor_signal == "below_median":
        red_signals += 1

    green_signals = 0
    if packet.entry_corpus_signal == "conservative":
        green_signals += 1
    if packet.sponsor_signal == "top_quartile":
        green_signals += 1
    if packet.sector_moic_p50 and packet.sector_moic_p50 >= 2.5:
        green_signals += 1
    if packet.peak_gross_moic and packet.peak_gross_moic >= 3.0:
        green_signals += 1

    if red_signals >= 3:
        packet.overall_signal = "red"
        packet.signal_rationale = f"{red_signals} red signals: entry aggressive, sector risk elevated"
    elif green_signals >= 3 and red_signals == 0:
        packet.overall_signal = "green"
        packet.signal_rationale = f"{green_signals} green signals: favorable entry, strong sector, top sponsor"
    else:
        packet.overall_signal = "yellow"
        packet.signal_rationale = f"{green_signals} green / {red_signals} red signals: proceed with diligence"

    return packet


def ic_packet_report(packet: IcPacket) -> str:
    """Format IC packet as a partner-ready text memo."""
    d = packet.deal
    name = d.get("deal_name", "Unknown Deal")
    ev = d.get("ev_mm", "n/a")
    ebitda = d.get("ebitda_at_entry_mm") or d.get("ebitda_mm", "n/a")
    mult = f"{float(ev)/float(ebitda):.1f}x" if ev and ebitda else "n/a"
    sector = d.get("sector", "n/a")
    buyer = d.get("buyer", "n/a")

    lines = [
        f"IC Quantitative Packet: {name}",
        "=" * 60,
        f"  Sector:  {sector}     Buyer: {buyer}",
        f"  Entry EV: ${float(ev):,.0f}M    Entry EBITDA: ${float(ebitda):,.0f}M    EV/EBITDA: {mult}",
        f"  Overall Signal:  [{packet.overall_signal.upper()}]  {packet.signal_rationale}",
        "",
        "1. LBO Entry Analysis",
        "-" * 35,
    ]

    if packet.max_entry_multiple:
        lines += [
            f"   Max affordable entry (2.5x MOIC target):  {packet.max_entry_multiple:.1f}x",
            f"   LBO feasible:   {'Yes' if packet.lbo_feasible else 'No'}",
            f"   Entry vs corpus: {packet.entry_corpus_signal}",
        ]
        if packet.lbo_warnings:
            for w in packet.lbo_warnings:
                lines.append(f"   ⚠  {w}")
    else:
        lines.append("   (insufficient data for LBO analysis)")

    lines += ["", "2. Hold Period Optimization", "-" * 35]
    if packet.moic_maximizing_year:
        lines += [
            f"   MOIC-maximizing exit:   Year {packet.moic_maximizing_year:.0f}  "
            f"({packet.peak_gross_moic:.2f}x peak)" if packet.peak_gross_moic else
            f"   MOIC-maximizing exit:   Year {packet.moic_maximizing_year:.0f}",
            f"   IRR-maximizing exit:    Year {packet.irr_maximizing_year:.0f}",
            f"   Sweet spot:             Years {packet.sweet_spot_start:.0f}"
            f"–{packet.sweet_spot_end:.0f}",
        ]
        if packet.cliff_year:
            lines.append(f"   Multiple compression cliff: Year {packet.cliff_year:.0f}")
    else:
        lines.append("   (insufficient data)")

    lines += ["", "3. Reimbursement Risk", "-" * 35]
    if packet.base_ebitda_impact is not None:
        lines += [
            f"   Base case EBITDA impact:      {packet.base_ebitda_impact:+.1%}",
            f"   Moderate rate cut impact:     {packet.moderate_cut_impact:+.1%}" if packet.moderate_cut_impact is not None else "",
            f"   Severe cut severity:          {packet.severe_cut_severity or 'n/a'}",
        ]
    else:
        lines.append("   (payer mix not provided)")

    lines += ["", "4. Sector Benchmarks", "-" * 35]
    if packet.sector_moic_p50:
        p25 = f"{packet.sector_moic_p25:.2f}x" if packet.sector_moic_p25 is not None else "n/a"
        p50 = f"{packet.sector_moic_p50:.2f}x"
        p75 = f"{packet.sector_moic_p75:.2f}x" if packet.sector_moic_p75 is not None else "n/a"
        hold = f"{packet.sector_hold_p50:.1f} yrs" if packet.sector_hold_p50 is not None else "n/a"
        loss = f"{packet.sector_loss_rate:.0%}" if packet.sector_loss_rate is not None else "n/a"
        hr = f"{packet.sector_home_run_rate:.0%}" if packet.sector_home_run_rate is not None else "n/a"
        lines += [
            f"   MOIC P25/P50/P75:  {p25} / {p50} / {p75}",
            f"   Hold P50:          {hold}",
            f"   Loss rate:         {loss}",
            f"   Home run rate:     {hr}",
        ]
    else:
        lines.append("   (sector data insufficient)")

    lines += ["", "5. Sponsor Track Record", "-" * 35]
    if packet.sponsor_deal_count:
        med_moic = f"{packet.sponsor_median_moic:.2f}x" if packet.sponsor_median_moic else "n/a"
        cons = f"{packet.sponsor_consistency_score:.2f}" if packet.sponsor_consistency_score else "n/a"
        lines += [
            f"   Deals in corpus:   {packet.sponsor_deal_count}",
            f"   Median MOIC:       {med_moic}",
            f"   Consistency score: {cons}",
            f"   Signal:            {packet.sponsor_signal}",
        ]
    else:
        lines.append("   (sponsor not found in corpus)")

    lines += ["", "6. Corpus Base Rates", "-" * 35]
    if packet.corpus_moic_p50:
        irr_str = f"{packet.corpus_irr_p50:.1%}" if packet.corpus_irr_p50 else "n/a"
        lines += [
            f"   All-sector MOIC P50:  {packet.corpus_moic_p50:.2f}x",
            f"   All-sector IRR  P50:  {irr_str}",
        ]

    if packet.red_flags:
        lines += ["", "7. Red Flags", "-" * 35]
        for rf in packet.red_flags[:5]:
            lines.append(f"   ⚠  {rf}")

    return "\n".join(l for l in lines if l is not None) + "\n"


def quick_ic_report(deal: Dict[str, Any], corpus_deals: List[Dict[str, Any]]) -> str:
    """One-call IC report using default assumptions."""
    packet = build_ic_packet(deal, corpus_deals)
    return ic_packet_report(packet)
