"""One-page deal brief for IC partner review.

Renders a consolidated, formatted text report for a single corpus deal,
pulling data from all analytical modules:
    - Deal summary and corpus comparables
    - Exit scenarios (strategic / SBO / IPO / div recap)
    - Leverage structure and covenant headroom
    - Payer mix sensitivity
    - PE intelligence (deal type, risk score, red flags)
    - Data quality score
    - Vintage / entry timing context
    - Full diligence checklist

Designed to be printed or pasted into an IC memo.  No HTML, no dependencies.

Public API:
    deal_brief(deal, corpus_db_path, *, entry_debt_mm, exit_assumptions) -> str
    corpus_summary_report(corpus_db_path)                                  -> str
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def _hr(char: str = "─", width: int = 80) -> str:
    return char * width


def _section(title: str) -> str:
    return f"\n{'═' * 80}\n  {title}\n{'═' * 80}"


def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Deal brief
# ---------------------------------------------------------------------------

def deal_brief(
    deal: Dict[str, Any],
    corpus_db_path: str,
    *,
    entry_debt_mm: Optional[float] = None,
    exit_assumptions: Optional[Any] = None,
) -> str:
    """Generate a full one-page deal brief for partner review.

    Args:
        deal:             deal dict (from corpus or raw)
        corpus_db_path:   path to corpus SQLite file
        entry_debt_mm:    override entry debt ($M)
        exit_assumptions: ExitAssumptions instance (or None for defaults)

    Returns:
        Multi-section text report as a single string.
    """
    lines: List[str] = []
    name = deal.get("deal_name", "Deal")
    ev = deal.get("ev_mm")
    ebitda = deal.get("ebitda_at_entry_mm")
    year = deal.get("year")
    buyer = deal.get("buyer", "—")

    lines.append(_hr("═"))
    lines.append(f"  DEAL BRIEF: {name}")
    lines.append(f"  Generated from Public Deals Corpus")
    lines.append(_hr("═"))
    lines.append(f"  EV: {'${:,.0f}M'.format(ev) if ev else '—'}  |  "
                 f"EBITDA: {'${:,.0f}M'.format(ebitda) if ebitda else '—'}  |  "
                 f"Year: {year or '—'}  |  Buyer: {buyer}")
    if ev and ebitda and ebitda > 0:
        lines.append(f"  Entry EV/EBITDA: {ev/ebitda:.1f}x")

    pm = deal.get("payer_mix")
    if isinstance(pm, str):
        try:
            pm = json.loads(pm)
        except Exception:
            pm = None
    if pm and isinstance(pm, dict):
        pm_str = "  ".join(f"{k}: {v:.0%}" for k, v in pm.items())
        lines.append(f"  Payer Mix: {pm_str}")

    # -----------------------------------------------------------------------
    # Comparables
    # -----------------------------------------------------------------------
    lines.append(_section("1. COMPARABLE CLOSED DEALS"))
    from .comparables import find_comparables, comparables_table
    comps = _safe(find_comparables, deal, corpus_db_path, 5) or []
    if comps:
        lines.append(comparables_table(deal, corpus_db_path, n=5))
    else:
        lines.append("  No comparable deals found.")

    # -----------------------------------------------------------------------
    # Exit scenarios
    # -----------------------------------------------------------------------
    lines.append(_section("2. EXIT SCENARIOS"))
    from .exit_modeling import model_all_exits, exit_table
    results = _safe(model_all_exits, deal, entry_debt_mm, exit_assumptions) or {}
    if results:
        lines.append(exit_table(results))
        # IRR sensitivity
        from .exit_modeling import irr_sensitivity
        lines.append("")
        lines.append(irr_sensitivity(deal, entry_debt_mm))
    else:
        lines.append("  Cannot model exits — EV or EBITDA missing.")

    # -----------------------------------------------------------------------
    # Capital structure
    # -----------------------------------------------------------------------
    lines.append(_section("3. CAPITAL STRUCTURE"))
    from .leverage_analysis import model_leverage, leverage_table, covenant_headroom
    lev_assumptions = {"entry_debt_mm": entry_debt_mm} if entry_debt_mm else None
    profile = _safe(model_leverage, deal, lev_assumptions)
    if profile:
        lines.append(leverage_table(profile))
        ch = covenant_headroom(profile)
        lines.append(f"\n  Min covenant headroom: {ch['min_headroom_turns']:.2f}x "
                     f"(Year {ch['min_headroom_year']})")
    else:
        lines.append("  Cannot model leverage — EV or EBITDA missing.")

    # -----------------------------------------------------------------------
    # Payer sensitivity
    # -----------------------------------------------------------------------
    lines.append(_section("4. PAYER MIX SENSITIVITY"))
    from .payer_sensitivity import sensitivity_table
    sens = _safe(sensitivity_table, deal)
    if sens:
        lines.append(sens)
    else:
        lines.append("  Cannot run sensitivity — payer mix missing.")

    # -----------------------------------------------------------------------
    # PE intelligence
    # -----------------------------------------------------------------------
    lines.append(_section("5. PE INTELLIGENCE"))
    from .pe_intelligence import full_intelligence_report
    report = _safe(full_intelligence_report, deal, {}, corpus_db_path)
    if report:
        lines.append(f"  Deal type  : {report.deal_type.value}")
        lines.append(f"  Risk score : {report.risk_score}/10")
        r = report.reasonableness
        lines.append(f"  IRR band   : {r.irr_band[0]:.1%} – {r.irr_band[1]:.1%}")
        lines.append(f"  MOIC band  : {r.moic_band[0]:.2f}x – {r.moic_band[1]:.2f}x")
        if r.corpus_moic_p50:
            lines.append(f"  Corpus P50 : {r.corpus_moic_p50:.2f}x MOIC")
        for w in r.warnings:
            lines.append(f"  ⚠  {w}")
        if report.red_flags:
            lines.append(f"\n  Red Flags ({len(report.red_flags)}):")
            for f in report.red_flags:
                lines.append(f"    ✗ {f}")
        if report.heuristic_notes:
            lines.append(f"\n  Heuristics:")
            for n in report.heuristic_notes[:3]:
                lines.append(f"    • {n}")
    else:
        lines.append("  Could not run PE intelligence report.")

    # -----------------------------------------------------------------------
    # Data quality
    # -----------------------------------------------------------------------
    lines.append(_section("6. DATA QUALITY"))
    from .deal_scorer import score_deal
    score = _safe(score_deal, deal)
    if score:
        lines.append(f"  Grade: {score.grade}   Score: {score.total_score:.0f}/100")
        lines.append(f"    Completeness : {score.completeness_score:.0f}/40")
        lines.append(f"    Credibility  : {score.credibility_score:.0f}/40")
        lines.append(f"    Source       : {score.source_score:.0f}/20")
        if score.issues:
            lines.append("  Issues:")
            for issue in score.issues:
                lines.append(f"    • {issue}")
    else:
        lines.append("  Could not score deal.")

    # -----------------------------------------------------------------------
    # Vintage context
    # -----------------------------------------------------------------------
    if year:
        lines.append(_section("7. VINTAGE CONTEXT"))
        from .vintage_analysis import entry_timing_assessment
        assessment = _safe(entry_timing_assessment, year, corpus_db_path)
        if assessment:
            lines.append(f"  Cycle     : {assessment['cycle_label']} ({assessment['cycle']})")
            lines.append(f"  Cycle MOIC P50   : {assessment['cycle_moic_p50']:.2f}x"
                         if assessment.get("cycle_moic_p50") else "  Cycle MOIC P50   : —")
            lines.append(f"  Overall MOIC P50 : {assessment['overall_moic_p50']:.2f}x"
                         if assessment.get("overall_moic_p50") else "  Overall MOIC P50 : —")
            lines.append(f"  Timing    : {assessment['relative_performance']}")
            for note in assessment.get("timing_notes", []):
                lines.append(f"    • {note}")

    # -----------------------------------------------------------------------
    # Diligence checklist
    # -----------------------------------------------------------------------
    lines.append(_section("8. IC DILIGENCE CHECKLIST"))
    from .diligence_checklist import build_checklist, checklist_text
    checklist = _safe(build_checklist, deal, corpus_db_path, entry_debt_mm)
    if checklist:
        lines.append(checklist_text(checklist))
    else:
        lines.append("  Could not build diligence checklist.")

    lines.append("\n" + _hr("═"))
    lines.append(f"  End of Deal Brief: {name}")
    lines.append(_hr("═"))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Corpus summary report
# ---------------------------------------------------------------------------

def corpus_summary_report(corpus_db_path: str) -> str:
    """Generate a corpus-level summary report: deal counts, base rates, quality."""
    from .base_rates import full_summary
    from .deal_scorer import quality_report
    from .vintage_analysis import vintage_table
    from .ingest_pipeline import run_full_ingest

    lines: List[str] = []
    lines.append(_hr("═"))
    lines.append("  PUBLIC DEALS CORPUS — SUMMARY REPORT")
    lines.append(_hr("═"))

    # Corpus stats
    try:
        # Late local import keeps the bypass cleanup contained
        # (campaign target 4E, data_public sweep) — the module
        # top doesn't need PortfolioStore otherwise. Routes
        # through the canonical seam so this read inherits
        # busy_timeout=5000, foreign_keys=ON, and Row factory.
        from ..portfolio.store import PortfolioStore
        with PortfolioStore(corpus_db_path).connect() as con:
            total = con.execute(
                "SELECT COUNT(*) FROM public_deals"
            ).fetchone()[0]
            with_moic = con.execute(
                "SELECT COUNT(*) FROM public_deals "
                "WHERE realized_moic IS NOT NULL"
            ).fetchone()[0]
            with_irr = con.execute(
                "SELECT COUNT(*) FROM public_deals "
                "WHERE realized_irr IS NOT NULL"
            ).fetchone()[0]
        lines.append(f"\n  Total deals   : {total}")
        lines.append(f"  With MOIC     : {with_moic}")
        lines.append(f"  With IRR      : {with_irr}")
    except Exception:
        lines.append("  [Could not query corpus stats]")

    # Base rates
    lines.append(_section("BASE RATES"))
    summary = _safe(full_summary, corpus_db_path)
    if summary:
        ov = summary.get("overall", {})
        m = ov.get("moic", {})
        i = ov.get("irr", {})
        if m.get("p50"):
            lines.append(f"  MOIC  P25={m['p25']:.2f}x  P50={m['p50']:.2f}x  P75={m['p75']:.2f}x")
        if i.get("p50"):
            lines.append(f"  IRR   P25={i['p25']:.1%}  P50={i['p50']:.1%}  P75={i['p75']:.1%}")

        lines.append("\n  By size:")
        for bucket, bm in summary.get("by_size", {}).items():
            mm = bm.get("moic", {})
            if mm.get("p50"):
                lines.append(f"    {bucket:8s}: MOIC P50={mm['p50']:.2f}x  (n={bm['n_deals']})")

    # Vintage
    lines.append(_section("VINTAGE ANALYSIS"))
    vt = _safe(vintage_table, corpus_db_path)
    if vt:
        lines.append(vt)

    # Data quality
    lines.append(_section("DATA QUALITY REPORT"))
    qr = _safe(quality_report, corpus_db_path)
    if qr:
        lines.append(qr)

    lines.append("\n" + _hr("═"))
    return "\n".join(lines)
