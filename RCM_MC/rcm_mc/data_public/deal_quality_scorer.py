"""Deal quality scorer — data completeness and analytical credibility.

Answers the IC question: "How much can we trust the analysis for this deal?"

Two separate assessments:
  1. Data completeness score (0-100): Are all required fields populated?
  2. Analytical credibility score (0-100): Are the values internally consistent
     and within empirically plausible ranges?

Combined quality grade: A (>=85), B (70-84), C (55-69), D (<55)

Data completeness dimensions:
  - Core identity fields (deal_name, sector, entry_year)
  - Financials (ev_mm, ebitda_at_entry_mm)
  - Payer mix (payer_mix dict with major payer types)
  - Transaction specifics (buyer, leverage_pct)
  - Outcome data (realized_moic, hold_years, realized_irr)
  - Geography + size context (region, hospital_size)

Analytical credibility checks:
  - EV/EBITDA multiple within plausible range (1x-40x)
  - Payer mix sums to ~1.0 (±0.05 tolerance)
  - Leverage ratio within 0-100%
  - MOIC vs IRR consistency (if both present)
  - Hold years consistent with entry/exit year
  - MOIC vs entry multiple plausibility

Public API:
    DataCompleteness       dataclass (score, grade, missing_fields, populated_fields)
    CredibilityCheck       dataclass (name, passed, value, note)
    DealQualityScore       dataclass (deal_name, completeness, credibility, combined_score, grade)
    score_deal_quality(deal) -> DealQualityScore
    batch_quality_scores(deals) -> List[DealQualityScore]
    quality_report(score) -> str
    quality_table(scores) -> str
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Field registry with weights
# ---------------------------------------------------------------------------

_FIELD_WEIGHTS: Dict[str, float] = {
    # Core identity (35 pts)
    "deal_name": 5.0,
    "sector": 8.0,
    "entry_year": 7.0,
    "buyer": 5.0,
    "seller": 3.0,
    "region": 4.0,
    "hospital_size": 3.0,
    # Financial inputs (30 pts)
    "ev_mm": 12.0,
    "ebitda_at_entry_mm": 12.0,
    "leverage_pct": 6.0,
    # Payer mix (15 pts)
    "payer_mix": 15.0,
    # Outcome data (20 pts)
    "realized_moic": 10.0,
    "hold_years": 5.0,
    "realized_irr": 5.0,
}

_TOTAL_WEIGHT = sum(_FIELD_WEIGHTS.values())  # = 100


def _field_present(deal: Dict[str, Any], key: str) -> bool:
    """Return True if field is populated (not None, empty string, or zero-only)."""
    val = deal.get(key)
    if val is None:
        return False
    if isinstance(val, str) and not val.strip():
        return False
    if isinstance(val, dict) and not val:
        return False
    return True


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DataCompleteness:
    """Data completeness assessment."""
    score: float               # 0-100 (weighted fraction of fields populated)
    populated_fields: List[str]
    missing_fields: List[str]
    has_outcome_data: bool     # realized_moic is populated


@dataclass
class CredibilityCheck:
    """Single credibility check result."""
    name: str
    passed: bool
    value: Optional[float]    # the computed value being checked
    note: str


@dataclass
class DealQualityScore:
    """Combined data quality assessment."""
    deal_name: str
    source_id: str
    completeness: DataCompleteness
    credibility_checks: List[CredibilityCheck] = field(default_factory=list)
    completeness_score: float = 0.0    # 0-100
    credibility_score: float = 0.0     # 0-100
    combined_score: float = 0.0        # 0-100 (65% completeness + 35% credibility)
    grade: str = "D"                   # A/B/C/D
    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Completeness scoring
# ---------------------------------------------------------------------------

def _score_completeness(deal: Dict[str, Any]) -> DataCompleteness:
    populated = []
    missing = []
    earned = 0.0

    for field_name, weight in _FIELD_WEIGHTS.items():
        if _field_present(deal, field_name):
            populated.append(field_name)
            earned += weight
        else:
            # Also check aliases
            alias_map = {
                "ev_mm": "entry_ev_mm",
                "ebitda_at_entry_mm": "ebitda_mm",
            }
            alias = alias_map.get(field_name)
            if alias and _field_present(deal, alias):
                populated.append(field_name)
                earned += weight
            else:
                missing.append(field_name)

    score = round(earned / _TOTAL_WEIGHT * 100.0, 1)
    return DataCompleteness(
        score=score,
        populated_fields=populated,
        missing_fields=missing,
        has_outcome_data=_field_present(deal, "realized_moic"),
    )


# ---------------------------------------------------------------------------
# Credibility checks
# ---------------------------------------------------------------------------

def _run_credibility_checks(deal: Dict[str, Any]) -> Tuple[List[CredibilityCheck], float]:
    """Run all credibility checks. Returns (checks, score 0-100)."""
    checks: List[CredibilityCheck] = []

    ev = float(deal.get("ev_mm") or deal.get("entry_ev_mm") or 0)
    ebitda = float(deal.get("ebitda_at_entry_mm") or deal.get("ebitda_mm") or 0)
    moic = deal.get("realized_moic")
    irr = deal.get("realized_irr")
    hold = deal.get("hold_years")
    entry_year = deal.get("entry_year") or deal.get("year")
    exit_year = deal.get("exit_year")
    leverage = deal.get("leverage_pct")
    payer_mix = deal.get("payer_mix") or {}

    # ---- Check 1: Entry multiple plausibility (1x-40x is credible)
    if ev > 0 and ebitda > 0:
        multiple = ev / ebitda
        passed = 1.0 <= multiple <= 40.0
        checks.append(CredibilityCheck(
            name="entry_multiple_range",
            passed=passed,
            value=round(multiple, 1),
            note=f"EV/EBITDA = {multiple:.1f}x {'✓' if passed else '✗ outside 1-40x'}",
        ))
    else:
        checks.append(CredibilityCheck(
            name="entry_multiple_range",
            passed=False,
            value=None,
            note="Cannot compute multiple — ev or ebitda missing/zero",
        ))

    # ---- Check 2: Payer mix sums to ~1.0 (tolerance ±0.05)
    if payer_mix and isinstance(payer_mix, dict):
        total = sum(float(v) for v in payer_mix.values())
        passed = abs(total - 1.0) <= 0.05
        checks.append(CredibilityCheck(
            name="payer_mix_sum",
            passed=passed,
            value=round(total, 3),
            note=f"Payer mix total = {total:.3f} {'✓' if passed else '✗ should sum to 1.0'}",
        ))

    # ---- Check 3: Leverage ratio plausible (0%-90%)
    if leverage is not None:
        lev = float(leverage)
        passed = 0.0 <= lev <= 0.90
        checks.append(CredibilityCheck(
            name="leverage_range",
            passed=passed,
            value=round(lev, 3),
            note=f"Leverage = {lev:.0%} {'✓' if passed else '✗ outside 0-90%'}",
        ))

    # ---- Check 4: MOIC vs IRR consistency (if both present)
    if moic is not None and irr is not None and hold is not None:
        try:
            moic_f = float(moic)
            irr_f = float(irr)
            hold_f = float(hold)
            if hold_f > 0 and moic_f > 0:
                # IRR implied by MOIC and hold: (moic)^(1/hold) - 1
                implied_irr = moic_f ** (1.0 / hold_f) - 1.0
                discrepancy = abs(implied_irr - irr_f)
                passed = discrepancy <= 0.10  # within 10 percentage points
                checks.append(CredibilityCheck(
                    name="moic_irr_consistency",
                    passed=passed,
                    value=round(discrepancy, 3),
                    note=(
                        f"Implied IRR {implied_irr:.1%} vs stated {irr_f:.1%} "
                        f"(Δ {discrepancy:.1%}) {'✓' if passed else '✗'}"
                    ),
                ))
        except (TypeError, ValueError, ZeroDivisionError):
            pass

    # ---- Check 5: Hold years vs entry/exit year consistency
    if entry_year and exit_year and hold is not None:
        try:
            computed_hold = int(exit_year) - int(entry_year)
            stated_hold = float(hold)
            passed = abs(computed_hold - stated_hold) <= 1.0
            checks.append(CredibilityCheck(
                name="hold_years_consistency",
                passed=passed,
                value=round(abs(computed_hold - stated_hold), 1),
                note=(
                    f"Exit({exit_year})-Entry({entry_year})={computed_hold}yr "
                    f"vs stated {stated_hold:.1f}yr {'✓' if passed else '✗'}"
                ),
            ))
        except (TypeError, ValueError):
            pass

    # ---- Check 6: MOIC plausibility (0-20x is plausible; >20x is suspicious)
    if moic is not None:
        try:
            moic_f = float(moic)
            passed = 0.0 <= moic_f <= 20.0
            checks.append(CredibilityCheck(
                name="moic_plausibility",
                passed=passed,
                value=round(moic_f, 2),
                note=f"MOIC = {moic_f:.2f}x {'✓' if passed else '✗ outside 0-20x'}",
            ))
        except (TypeError, ValueError):
            pass

    # ---- Check 7: EBITDA margin sanity (EBITDA/EV should be between 2%-25% for typical deal)
    if ev > 0 and ebitda > 0:
        margin_pct = ebitda / ev * 100.0
        passed = 1.0 <= margin_pct <= 30.0
        checks.append(CredibilityCheck(
            name="ebitda_ev_ratio",
            passed=passed,
            value=round(margin_pct, 1),
            note=f"EBITDA/EV = {margin_pct:.1f}% {'✓' if passed else '✗ unusual — verify'}",
        ))

    # Compute score: each check worth equal weight
    if not checks:
        return checks, 50.0  # no checks possible → medium confidence
    passed_count = sum(1 for c in checks if c.passed)
    score = round(passed_count / len(checks) * 100.0, 1)
    return checks, score


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------

def score_deal_quality(deal: Dict[str, Any]) -> DealQualityScore:
    """Compute combined data quality score for a single deal.

    Args:
        deal: Raw deal dict (same schema as corpus seed dicts)

    Returns:
        DealQualityScore with completeness, credibility, and combined grade
    """
    deal_name = deal.get("deal_name", "Unknown")
    source_id = deal.get("source_id", "")

    completeness = _score_completeness(deal)
    checks, credibility_score = _run_credibility_checks(deal)

    # Combined: 65% completeness + 35% credibility
    combined = round(0.65 * completeness.score + 0.35 * credibility_score, 1)

    # Grade
    if combined >= 85:
        grade = "A"
    elif combined >= 70:
        grade = "B"
    elif combined >= 55:
        grade = "C"
    else:
        grade = "D"

    notes = []
    if completeness.missing_fields:
        top_missing = completeness.missing_fields[:3]
        notes.append(f"Missing: {', '.join(top_missing)}")
    failed_checks = [c for c in checks if not c.passed]
    if failed_checks:
        notes.append(f"Credibility issues: {', '.join(c.name for c in failed_checks[:2])}")

    return DealQualityScore(
        deal_name=deal_name,
        source_id=source_id,
        completeness=completeness,
        credibility_checks=checks,
        completeness_score=completeness.score,
        credibility_score=credibility_score,
        combined_score=combined,
        grade=grade,
        notes=notes,
    )


def batch_quality_scores(deals: List[Dict[str, Any]]) -> List[DealQualityScore]:
    """Score quality of all deals and return sorted by combined_score descending."""
    scores = [score_deal_quality(d) for d in deals]
    return sorted(scores, key=lambda s: s.combined_score, reverse=True)


def corpus_quality_summary(deals: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate quality statistics across the full corpus."""
    scores = batch_quality_scores(deals)
    if not scores:
        return {}
    grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for s in scores:
        grade_counts[s.grade] = grade_counts.get(s.grade, 0) + 1

    combined_values = [s.combined_score for s in scores]
    combined_s = sorted(combined_values)
    n = len(combined_s)

    return {
        "total_deals": n,
        "grade_counts": grade_counts,
        "median_combined_score": combined_s[n // 2],
        "pct_with_outcome_data": round(sum(1 for s in scores if s.completeness.has_outcome_data) / n * 100, 1),
        "pct_grade_a_or_b": round((grade_counts["A"] + grade_counts["B"]) / n * 100, 1),
        "most_common_missing": _most_common_missing(scores),
    }


def _most_common_missing(scores: List[DealQualityScore]) -> List[str]:
    counts: Dict[str, int] = {}
    for s in scores:
        for f in s.completeness.missing_fields:
            counts[f] = counts.get(f, 0) + 1
    return [f for f, _ in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]]


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def quality_report(score: DealQualityScore) -> str:
    """Formatted quality report for a single deal."""
    lines = [
        f"Deal Quality Score: {score.deal_name}",
        "=" * 55,
        f"  Combined Score: {score.combined_score:.1f} / 100  [Grade {score.grade}]",
        f"  Completeness:   {score.completeness_score:.1f} / 100",
        f"  Credibility:    {score.credibility_score:.1f} / 100",
        "",
        "Data Completeness:",
        f"  Populated ({len(score.completeness.populated_fields)}): {', '.join(score.completeness.populated_fields[:6])}{'...' if len(score.completeness.populated_fields) > 6 else ''}",
    ]
    if score.completeness.missing_fields:
        lines.append(f"  Missing  ({len(score.completeness.missing_fields)}): {', '.join(score.completeness.missing_fields)}")

    if score.credibility_checks:
        lines += ["", "Credibility Checks:"]
        for c in score.credibility_checks:
            icon = "✓" if c.passed else "✗"
            lines.append(f"  [{icon}] {c.name:<30} {c.note}")

    if score.notes:
        lines += ["", "Issues:"]
        for n in score.notes:
            lines.append(f"  • {n}")

    return "\n".join(lines) + "\n"


def quality_table(scores: List[DealQualityScore]) -> str:
    """Compact comparison table across multiple deals."""
    hdr = f"{'Deal':<35} {'Grade':<6} {'Combined':>9} {'Complete':>9} {'Credible':>9}"
    sep = "-" * 75
    lines = [hdr, sep]
    for s in sorted(scores, key=lambda x: x.combined_score, reverse=True):
        name = s.deal_name[:33]
        lines.append(
            f"{name:<35} [{s.grade}]  {s.combined_score:>7.1f} "
            f"{s.completeness_score:>9.1f} {s.credibility_score:>9.1f}"
        )
    return "\n".join(lines) + "\n"
