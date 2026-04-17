"""Integrated PE diligence checklist for a hospital M&A deal.

Aggregates outputs from all corpus analytical modules into a single,
structured checklist that a senior PE healthcare partner would review
before an IC presentation.

Checklist sections:
    1. Deal Overview          — basic facts and corpus comparables
    2. Returns Analysis       — exit scenarios, IRR, MOIC vs corpus P50
    3. Capital Structure      — leverage, coverage, covenant headroom
    4. Payer Mix Risk         — sensitivity scenarios (Medicaid cut, MA creep, etc.)
    5. PE Intelligence        — deal type, red flags, lever timeframes
    6. Data Quality           — completeness and credibility score
    7. Vintage Context        — entry timing vs macro cycle norms
    8. Open Questions         — auto-generated based on gaps and red flags

Public API:
    ChecklistItem    dataclass
    DiligenceChecklist dataclass
    build_checklist(deal, corpus_db_path, assumptions)  -> DiligenceChecklist
    checklist_text(checklist)                            -> str (formatted report)
    checklist_json(checklist)                            -> dict
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ChecklistItem:
    section: str
    item: str
    status: str        # "OK" | "WARNING" | "CRITICAL" | "MISSING" | "INFO"
    detail: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {"section": self.section, "item": self.item,
                "status": self.status, "detail": self.detail}


@dataclass
class DiligenceChecklist:
    deal_name: str
    items: List[ChecklistItem] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    summary_flags: List[str] = field(default_factory=list)  # critical/warning items

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.items if i.status == "CRITICAL")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.items if i.status == "WARNING")

    def as_dict(self) -> Dict[str, Any]:
        by_section: Dict[str, List[Dict]] = {}
        for item in self.items:
            by_section.setdefault(item.section, []).append(item.as_dict())
        return {
            "deal_name": self.deal_name,
            "critical_count": self.critical_count,
            "warning_count": self.warning_count,
            "sections": by_section,
            "open_questions": self.open_questions,
            "summary_flags": self.summary_flags,
        }


# ---------------------------------------------------------------------------
# Helper: safe import + call
# ---------------------------------------------------------------------------

def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _section_overview(
    deal: Dict[str, Any],
    corpus_db_path: str,
    items: List[ChecklistItem],
    questions: List[str],
) -> None:
    S = "1. Deal Overview"
    name = deal.get("deal_name", "—")
    ev = deal.get("ev_mm")
    ebitda = deal.get("ebitda_at_entry_mm")
    buyer = deal.get("buyer", "—")
    year = deal.get("year")

    items.append(ChecklistItem(S, "Deal name", "INFO", str(name)))
    items.append(ChecklistItem(S, "Entry year", "INFO" if year else "MISSING",
                               str(year) if year else "year not recorded"))
    items.append(ChecklistItem(S, "Buyer", "INFO" if buyer and buyer != "—" else "MISSING",
                               str(buyer)))
    items.append(ChecklistItem(S, "Enterprise Value",
                               "OK" if ev else "MISSING",
                               f"${ev:,.0f}M" if ev else "EV not recorded"))
    items.append(ChecklistItem(S, "EBITDA at entry",
                               "OK" if ebitda else "MISSING",
                               f"${ebitda:,.0f}M" if ebitda else "EBITDA not recorded"))

    if ev and ebitda and ebitda > 0:
        mult = ev / ebitda
        status = "OK" if 4 <= mult <= 20 else "WARNING"
        items.append(ChecklistItem(S, "Entry EV/EBITDA multiple",
                                   status, f"{mult:.1f}x"))
        if mult > 20:
            questions.append("Entry multiple > 20x — confirm EBITDA add-backs and synergy thesis.")

    # Comparable deals
    from .comparables import find_comparables
    comps = _safe(find_comparables, deal, corpus_db_path, 3) or []
    if comps:
        comp_str = "; ".join(f"{c.deal_name} ({c.similarity_score:.0f}%)" for c in comps[:3])
        items.append(ChecklistItem(S, "Closest corpus comparables", "INFO", comp_str))
    else:
        items.append(ChecklistItem(S, "Closest corpus comparables", "WARNING",
                                   "No comparable deals found — corpus may be sparse for this deal type"))


def _section_returns(
    deal: Dict[str, Any],
    corpus_db_path: str,
    entry_debt_mm: Optional[float],
    exit_assumptions: Optional[Any],
    items: List[ChecklistItem],
    questions: List[str],
    flags: List[str],
) -> None:
    S = "2. Returns Analysis"
    from .exit_modeling import model_all_exits, ExitAssumptions
    from .base_rates import get_benchmarks

    a = exit_assumptions or ExitAssumptions()
    results = _safe(model_all_exits, deal, entry_debt_mm, a) or {}

    if results:
        strategic = results.get("strategic_sale")
        if strategic:
            moic = strategic.moic
            irr = strategic.irr
            status = "OK" if moic >= 2.0 else ("WARNING" if moic >= 1.5 else "CRITICAL")
            items.append(ChecklistItem(S, "Strategic exit MOIC",
                                       status, f"{moic:.2f}x  IRR={irr:.1%}"))
            if status != "OK":
                flags.append(f"Returns: Strategic MOIC {moic:.2f}x below 2.0x threshold")

        for route, result in results.items():
            if route == "strategic_sale":
                continue
            items.append(ChecklistItem(
                S, f"{route.replace('_', ' ').title()} MOIC",
                "INFO", f"{result.moic:.2f}x  IRR={result.irr:.1%}"
            ))

    # Compare to corpus P50
    benchmarks = _safe(get_benchmarks, corpus_db_path)
    if benchmarks and benchmarks.moic_p50 and results.get("strategic_sale"):
        corp_p50 = benchmarks.moic_p50
        deal_moic = results["strategic_sale"].moic
        delta = deal_moic - corp_p50
        status = "OK" if delta >= -0.3 else "WARNING"
        items.append(ChecklistItem(
            S, "vs corpus MOIC P50",
            status, f"{deal_moic:.2f}x vs corpus P50={corp_p50:.2f}x  (Δ{delta:+.2f}x)"
        ))


def _section_capital_structure(
    deal: Dict[str, Any],
    entry_debt_mm: Optional[float],
    items: List[ChecklistItem],
    questions: List[str],
    flags: List[str],
) -> None:
    S = "3. Capital Structure"
    from .leverage_analysis import model_leverage, covenant_headroom

    profile = _safe(model_leverage, deal,
                    {"entry_debt_mm": entry_debt_mm} if entry_debt_mm else None)
    if not profile:
        items.append(ChecklistItem(S, "Leverage model", "MISSING",
                                   "Cannot model — ev_mm or ebitda_at_entry_mm missing"))
        return

    status = "OK" if profile.entry_leverage <= 6.0 else \
             ("WARNING" if profile.entry_leverage <= 8.0 else "CRITICAL")
    items.append(ChecklistItem(S, "Entry leverage",
                               status, f"{profile.entry_leverage:.1f}x Net Debt / EBITDA"))
    if status == "CRITICAL":
        flags.append(f"Capital Structure: Entry leverage {profile.entry_leverage:.1f}x > 8x")

    ic_status = "OK" if profile.entry_interest_coverage >= 2.0 else \
                ("WARNING" if profile.entry_interest_coverage >= 1.5 else "CRITICAL")
    items.append(ChecklistItem(S, "Entry interest coverage",
                               ic_status, f"{profile.entry_interest_coverage:.2f}x"))

    ch = covenant_headroom(profile)
    headroom = ch.get("min_headroom_turns", 0.0) or 0.0
    h_status = "OK" if headroom >= 1.0 else ("WARNING" if headroom >= 0.5 else "CRITICAL")
    items.append(ChecklistItem(S, "Min covenant headroom (hold period)",
                               h_status, f"{headroom:.2f}x turns"))
    if headroom < 0.5:
        flags.append(f"Capital Structure: Covenant headroom {headroom:.2f}x dangerously thin")

    if profile.covenant_at_risk:
        items.append(ChecklistItem(S, "Covenant breach risk",
                                   "CRITICAL",
                                   f"Projected breach in Year {profile.covenant_breach_year}"))
        flags.append(f"Capital Structure: Covenant breach projected in Year {profile.covenant_breach_year}")
        questions.append("Model covenant waiver scenario — what EBITDA cushion is needed?")


def _section_payer_mix(
    deal: Dict[str, Any],
    items: List[ChecklistItem],
    questions: List[str],
    flags: List[str],
) -> None:
    S = "4. Payer Mix Risk"
    from .payer_sensitivity import run_all_scenarios

    pm = deal.get("payer_mix")
    if not pm:
        items.append(ChecklistItem(S, "Payer mix", "MISSING",
                                   "No payer mix data — cannot run sensitivity"))
        questions.append("Obtain payer mix breakdown before IC presentation.")
        return

    if isinstance(pm, str):
        try:
            pm = json.loads(pm)
        except Exception:
            pm = None

    if pm:
        medicaid = pm.get("medicaid", 0)
        commercial = pm.get("commercial", 0)
        ma = pm.get("medicare_advantage", pm.get("medicare", 0))
        status = "OK" if medicaid <= 0.30 else ("WARNING" if medicaid <= 0.45 else "CRITICAL")
        items.append(ChecklistItem(S, "Medicaid exposure",
                                   status, f"{medicaid:.0%}"))
        if medicaid > 0.45:
            flags.append(f"Payer Mix: Medicaid {medicaid:.0%} — high political rate risk")

        items.append(ChecklistItem(S, "Commercial mix", "INFO", f"{commercial:.0%}"))

    scenarios = _safe(run_all_scenarios, deal) or []
    if scenarios:
        worst = min(scenarios, key=lambda s: s.ebitda_delta_pct or 0)
        if worst.ebitda_delta_pct is not None:
            ws = "OK" if worst.ebitda_delta_pct >= -0.10 else \
                 ("WARNING" if worst.ebitda_delta_pct >= -0.20 else "CRITICAL")
            sname = worst.scenario_name
            items.append(ChecklistItem(
                S, f"Worst scenario ({sname})",
                ws, f"EBITDA impact: {worst.ebitda_delta_pct:.1%}"
            ))
            if worst.ebitda_delta_pct < -0.20:
                flags.append(f"Payer Sensitivity: {sname} → {worst.ebitda_delta_pct:.1%} EBITDA")
                questions.append(f"Stress scenario: {sname} — does capital structure survive?")


def _section_pe_intelligence(
    deal: Dict[str, Any],
    corpus_db_path: str,
    items: List[ChecklistItem],
    questions: List[str],
    flags: List[str],
) -> None:
    S = "5. PE Intelligence"
    from .pe_intelligence import full_intelligence_report

    report = _safe(full_intelligence_report, deal, {}, corpus_db_path)
    if not report:
        items.append(ChecklistItem(S, "PE intelligence", "MISSING",
                                   "Could not run intelligence report"))
        return

    items.append(ChecklistItem(S, "Deal type", "INFO", report.deal_type.value))

    rs = report.risk_score
    rs_status = "OK" if rs <= 4 else ("WARNING" if rs <= 6 else "CRITICAL")
    items.append(ChecklistItem(S, "Risk score", rs_status, f"{rs}/10"))
    if rs > 6:
        flags.append(f"PE Intelligence: High risk score {rs}/10")

    for flag in report.red_flags[:3]:
        items.append(ChecklistItem(S, "Red flag", "CRITICAL", flag))
        flags.append(f"Red Flag: {flag[:80]}")
        questions.append(f"Address red flag: {flag}")

    for w in report.lever_warnings[:2]:
        items.append(ChecklistItem(S, "Lever warning", "WARNING", w))

    for note in report.heuristic_notes[:2]:
        items.append(ChecklistItem(S, "Heuristic", "INFO", note))


def _section_data_quality(
    deal: Dict[str, Any],
    items: List[ChecklistItem],
    questions: List[str],
    flags: List[str],
) -> None:
    S = "6. Data Quality"
    from .deal_scorer import score_deal

    score = _safe(score_deal, deal)
    if not score:
        items.append(ChecklistItem(S, "Data quality score", "MISSING", "Could not score deal"))
        return

    s_status = "OK" if score.grade in ("A", "B") else \
               ("WARNING" if score.grade == "C" else "CRITICAL")
    items.append(ChecklistItem(S, "Data quality grade",
                               s_status, f"{score.grade}  ({score.total_score:.0f}/100)"))
    if score.grade in ("D", "F"):
        flags.append(f"Data Quality: Grade {score.grade} — low-confidence deal record")
        questions.append("Improve data quality: obtain missing EV, EBITDA, payer mix data.")

    for issue in score.issues[:3]:
        items.append(ChecklistItem(S, "Data issue", "WARNING" if "missing" in issue.lower()
                                   else "INFO", issue))


def _section_vintage(
    deal: Dict[str, Any],
    corpus_db_path: str,
    items: List[ChecklistItem],
    questions: List[str],
) -> None:
    S = "7. Vintage Context"
    year = deal.get("year")
    if not year:
        items.append(ChecklistItem(S, "Vintage year", "MISSING",
                                   "Year not recorded — cannot assess entry timing"))
        return

    from .vintage_analysis import entry_timing_assessment
    assessment = _safe(entry_timing_assessment, year, corpus_db_path)
    if not assessment:
        return

    items.append(ChecklistItem(S, "Macro cycle", "INFO",
                               f"{assessment['cycle_label']} ({assessment['cycle']})"))
    items.append(ChecklistItem(S, "Entry timing vs corpus",
                               "OK" if assessment["relative_performance"] != "below par" else "WARNING",
                               assessment["relative_performance"]))

    for note in assessment.get("timing_notes", [])[:2]:
        items.append(ChecklistItem(S, "Timing context", "INFO", note))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_checklist(
    deal: Dict[str, Any],
    corpus_db_path: str,
    entry_debt_mm: Optional[float] = None,
    exit_assumptions: Optional[Any] = None,
) -> DiligenceChecklist:
    """Build a complete diligence checklist for a deal.

    Args:
        deal:             deal dict (from corpus or raw)
        corpus_db_path:   path to corpus SQLite file
        entry_debt_mm:    override entry debt ($M); defaults to 60% of EV
        exit_assumptions: ExitAssumptions instance (or None for defaults)

    Returns:
        DiligenceChecklist with ChecklistItems across all sections.
    """
    name = str(deal.get("deal_name", "Unknown"))
    items: List[ChecklistItem] = []
    questions: List[str] = []
    flags: List[str] = []

    _section_overview(deal, corpus_db_path, items, questions)
    _section_returns(deal, corpus_db_path, entry_debt_mm, exit_assumptions,
                     items, questions, flags)
    _section_capital_structure(deal, entry_debt_mm, items, questions, flags)
    _section_payer_mix(deal, items, questions, flags)
    _section_pe_intelligence(deal, corpus_db_path, items, questions, flags)
    _section_data_quality(deal, items, questions, flags)
    _section_vintage(deal, corpus_db_path, items, questions)

    return DiligenceChecklist(
        deal_name=name,
        items=items,
        open_questions=list(dict.fromkeys(questions)),   # deduplicate, preserve order
        summary_flags=list(dict.fromkeys(flags)),
    )


def checklist_text(checklist: DiligenceChecklist) -> str:
    """Format the checklist as a human-readable text report."""
    STATUS_ICON = {
        "OK":       "✓",
        "WARNING":  "⚠",
        "CRITICAL": "✗",
        "MISSING":  "?",
        "INFO":     "·",
    }

    lines = [
        f"PE Diligence Checklist: {checklist.deal_name}",
        f"  {checklist.critical_count} critical  |  {checklist.warning_count} warnings",
        "=" * 80,
    ]

    current_section = None
    for item in checklist.items:
        if item.section != current_section:
            lines.append(f"\n  {item.section}")
            lines.append("  " + "-" * 60)
            current_section = item.section
        icon = STATUS_ICON.get(item.status, "·")
        detail = f"  — {item.detail}" if item.detail else ""
        lines.append(f"    [{icon}] {item.item}{detail}")

    if checklist.summary_flags:
        lines.append("\n\n  SUMMARY FLAGS")
        lines.append("  " + "-" * 60)
        for flag in checklist.summary_flags:
            lines.append(f"    ✗ {flag}")

    if checklist.open_questions:
        lines.append("\n\n  OPEN QUESTIONS FOR IC PREP")
        lines.append("  " + "-" * 60)
        for i, q in enumerate(checklist.open_questions, 1):
            lines.append(f"    {i}. {q}")

    return "\n".join(lines)


def checklist_json(checklist: DiligenceChecklist) -> Dict[str, Any]:
    """Return the checklist as a JSON-serialisable dict."""
    return checklist.as_dict()
