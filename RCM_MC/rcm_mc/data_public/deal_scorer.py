"""Deal quality scorer for the public corpus.

Assigns a 0–100 quality score to each corpus deal based on:
    - Data completeness (how many key fields are populated)
    - Analytical credibility (EV/EBITDA multiple in range, IRR/MOIC reasonable)
    - Source reliability (seed > PE portfolio > news > sec_edgar)
    - Payer mix completeness (explicit percentages that sum to ~1.0)

Why score deal quality?
    The corpus is used for calibration and backtesting. Deals with missing
    fields or implausible values should be down-weighted when computing
    base-rate benchmarks.  The score drives sample weights in base_rates.py
    extensions and flags low-confidence records for human review.

Public API:
    DealQualityScore dataclass
    score_deal(deal_dict)               -> DealQualityScore
    score_corpus(corpus_db_path)        -> List[DealQualityScore]
    top_n(corpus_db_path, n)            -> List[DealQualityScore]
    bottom_n(corpus_db_path, n)         -> List[DealQualityScore]
    quality_report(corpus_db_path)      -> str
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..portfolio.store import PortfolioStore


@dataclass
class DealQualityScore:
    source_id: str
    deal_name: str
    total_score: float          # 0–100
    completeness_score: float   # 0–40 points
    credibility_score: float    # 0–40 points
    source_score: float         # 0–20 points
    issues: List[str] = field(default_factory=list)
    grade: str = ""             # A/B/C/D/F

    def as_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "deal_name": self.deal_name,
            "grade": self.grade,
            "total_score": round(self.total_score, 1),
            "completeness_score": round(self.completeness_score, 1),
            "credibility_score": round(self.credibility_score, 1),
            "source_score": round(self.source_score, 1),
            "issues": self.issues,
        }


# ---------------------------------------------------------------------------
# Source reliability weights
# ---------------------------------------------------------------------------
_SOURCE_SCORES = {
    "seed":          20,  # fully curated, verified against SEC/press releases
    "pe_portfolio":  15,  # curated from investor pages; generally reliable
    "news":          12,  # curated from news sources; EV sometimes estimated
    "sec_edgar":      8,  # raw EDGAR; name/date reliable; EV often absent
    "manual":        18,  # manually entered by analyst
}


def _score_completeness(deal: Dict[str, Any]) -> tuple[float, List[str]]:
    """Return (completeness_score: 0-40, issues: List[str])."""
    issues: List[str] = []
    score = 0.0

    # Core identifier fields (8 pts)
    if deal.get("deal_name"):
        score += 2
    if deal.get("year"):
        score += 2
    if deal.get("buyer"):
        score += 2
    else:
        issues.append("buyer missing")
    if deal.get("seller"):
        score += 2
    else:
        issues.append("seller missing")

    # Financial fields (20 pts)
    if deal.get("ev_mm"):
        score += 6
    else:
        issues.append("ev_mm missing")

    if deal.get("ebitda_at_entry_mm"):
        score += 6
    else:
        issues.append("ebitda_at_entry_mm missing")

    if deal.get("realized_moic") is not None:
        score += 4
    else:
        issues.append("realized_moic missing (may be unrealized)")

    if deal.get("realized_irr") is not None:
        score += 4
    else:
        issues.append("realized_irr missing (may be unrealized)")

    # Payer mix (8 pts)
    pm = deal.get("payer_mix")
    if isinstance(pm, str):
        try:
            pm = json.loads(pm)
        except Exception:
            pm = None
    if pm and isinstance(pm, dict) and len(pm) >= 2:
        score += 4
        total = sum(float(v) for v in pm.values())
        if abs(total - 1.0) < 0.05:
            score += 4
        else:
            issues.append(f"payer_mix sums to {total:.2f}, not 1.0")
    else:
        issues.append("payer_mix missing or incomplete")

    # Hold years (4 pts — needed for IRR calculation)
    if deal.get("hold_years"):
        score += 4
    elif deal.get("realized_moic") is not None:
        issues.append("hold_years missing but moic present — IRR not computable")

    return score, issues


def _score_credibility(deal: Dict[str, Any]) -> tuple[float, List[str]]:
    """Return (credibility_score: 0-40, issues: List[str])."""
    issues: List[str] = []
    score = 40.0  # start at max, deduct for issues

    ev = deal.get("ev_mm")
    ebitda = deal.get("ebitda_at_entry_mm")
    moic = deal.get("realized_moic")
    irr = deal.get("realized_irr")
    hold = deal.get("hold_years")

    # EV/EBITDA multiple sanity check (10 pt deduction if bad)
    if ev and ebitda and ebitda > 0:
        mult = ev / ebitda
        if mult < 2.0:
            score -= 15
            issues.append(f"EV/EBITDA {mult:.1f}x implausibly low (< 2x)")
        elif mult < 4.0:
            score -= 5
            issues.append(f"EV/EBITDA {mult:.1f}x low (< 4x)")
        elif mult > 30:
            score -= 10
            issues.append(f"EV/EBITDA {mult:.1f}x implausibly high (> 30x)")
        elif mult > 20:
            score -= 5
            issues.append(f"EV/EBITDA {mult:.1f}x high (> 20x)")
    elif ev and not ebitda:
        score -= 3  # minor: EV without EBITDA reduces calibration value

    # MOIC sanity (8 pt deduction if implausible)
    if moic is not None:
        if moic < -0.1:
            score -= 2  # not impossible; Envision was near 0
        if moic > 10:
            score -= 10
            issues.append(f"realized_moic {moic:.2f}x > 10x — verify")

    # IRR sanity (8 pt deduction)
    if irr is not None:
        if irr > 1.0:
            score -= 10
            issues.append(f"realized_irr {irr:.1%} > 100% — verify decimal vs. pct")
        if irr < -1.0:
            score -= 5
            issues.append(f"realized_irr {irr:.1%} < -100% — verify")

    # MOIC/IRR/hold consistency check (4 pts)
    if moic is not None and irr is not None and hold and hold > 0:
        implied_moic = (1 + irr) ** hold
        if abs(implied_moic - moic) > moic * 0.30:
            score -= 4
            issues.append(
                f"MOIC/IRR/hold inconsistent: {moic:.2f}x at {irr:.1%} for {hold:.1f}y "
                f"implies {implied_moic:.2f}x"
            )

    # Year sanity
    year = deal.get("year")
    if year and (year < 1980 or year > 2030):
        score -= 10
        issues.append(f"year {year} out of range 1980-2030")

    return max(0.0, score), issues


def _letter_grade(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def score_deal(deal: Dict[str, Any]) -> DealQualityScore:
    """Compute the quality score for a single deal dict."""
    completeness, c_issues = _score_completeness(deal)
    credibility, cr_issues = _score_credibility(deal)
    source = _SOURCE_SCORES.get(str(deal.get("source", "seed")), 10)

    total = completeness + credibility + source
    all_issues = c_issues + cr_issues

    return DealQualityScore(
        source_id=str(deal.get("source_id", "")),
        deal_name=str(deal.get("deal_name", "")),
        total_score=total,
        completeness_score=completeness,
        credibility_score=credibility,
        source_score=float(source),
        issues=all_issues,
        grade=_letter_grade(total),
    )


def _load_all(corpus_db_path: str) -> List[Dict[str, Any]]:
    # Route through PortfolioStore (campaign target 4E, data_public
    # sweep): inherits busy_timeout=5000, foreign_keys=ON, and
    # row_factory=Row — replacing the prior bare-connect plus
    # manual row_factory assignment.
    with PortfolioStore(corpus_db_path).connect() as con:
        rows = con.execute("SELECT * FROM public_deals").fetchall()
    deals = []
    for row in rows:
        d = dict(row)
        pm = d.get("payer_mix")
        if pm and isinstance(pm, str):
            try:
                d["payer_mix"] = json.loads(pm)
            except Exception:
                pass
        deals.append(d)
    return deals


def score_corpus(corpus_db_path: str) -> List[DealQualityScore]:
    """Score all deals in the corpus. Returns list sorted by score descending."""
    deals = _load_all(corpus_db_path)
    scores = [score_deal(d) for d in deals]
    return sorted(scores, key=lambda s: s.total_score, reverse=True)


def top_n(corpus_db_path: str, n: int = 10) -> List[DealQualityScore]:
    return score_corpus(corpus_db_path)[:n]


def bottom_n(corpus_db_path: str, n: int = 10) -> List[DealQualityScore]:
    return score_corpus(corpus_db_path)[-n:]


def quality_report(corpus_db_path: str) -> str:
    scores = score_corpus(corpus_db_path)
    grade_counts: Dict[str, int] = {}
    for s in scores:
        grade_counts[s.grade] = grade_counts.get(s.grade, 0) + 1

    lines = [
        f"Deal Quality Report ({len(scores)} deals)",
        "-" * 80,
        f"  Grade distribution: "
        + "  ".join(f"{g}={grade_counts.get(g, 0)}" for g in ["A", "B", "C", "D", "F"]),
        "",
        f"{'Grade':<5} {'Score':>5}  {'Deal':<55} Issues",
        "-" * 80,
    ]
    for s in scores[:25]:  # top 25
        issue_str = "; ".join(s.issues[:2]) if s.issues else "—"
        lines.append(
            f"  {s.grade:<3} {s.total_score:>5.0f}  {s.deal_name[:54]:<55} {issue_str}"
        )
    if len(scores) > 25:
        lines.append(f"  ... and {len(scores) - 25} more deals")
    return "\n".join(lines)
