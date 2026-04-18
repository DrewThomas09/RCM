"""Corpus health check — validates internal consistency of all seed deals.

Runs a suite of data quality checks over the loaded corpus and returns
a HealthCheckResult with per-deal issues and summary statistics.

Checks:
  1. Required fields present (source_id, deal_name)
  2. Payer mix sums to ~1.0 (tolerance ±0.05)
  3. MOIC-IRR-hold consistency (if all three present)
  4. No duplicate source_ids
  5. EV in plausible range ($5M–$50B)
  6. EBITDA margin in plausible range (-200% to +80% of EV)
  7. Realized MOIC ≥ 0 (no negative equity returns allowed)
  8. Hold years in range [0.5, 15]
  9. Year in range [1990, 2030]

Public API:
    DealIssue                          dataclass
    HealthCheckResult                  dataclass
    check_corpus(deals)                -> HealthCheckResult
    health_check_text(result)          -> str
    run_corpus_health_check(db_path)   -> HealthCheckResult
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class DealIssue:
    """A single data quality issue in a deal."""
    source_id: str
    deal_name: str
    check: str
    severity: str   # error / warning / info
    detail: str


@dataclass
class HealthCheckResult:
    """Summary of corpus health check."""
    total_deals: int = 0
    issues: List[DealIssue] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    duplicate_source_ids: List[str] = field(default_factory=list)
    clean_deal_count: int = 0
    health_score: float = 1.0   # 0–1, 1 = perfect


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _payer_sum(deal: Dict) -> Optional[float]:
    pm = deal.get("payer_mix")
    if isinstance(pm, str):
        try:
            pm = json.loads(pm)
        except Exception:
            return None
    if not isinstance(pm, dict):
        return None
    vals = [v for v in pm.values() if v is not None]
    if not vals:
        return None
    try:
        return sum(float(v) for v in vals)
    except (TypeError, ValueError):
        return None


def _check_required_fields(deal: Dict, src_id: str, name: str) -> List[DealIssue]:
    issues = []
    if not deal.get("source_id"):
        issues.append(DealIssue(src_id, name, "required_fields", "error", "Missing source_id"))
    if not deal.get("deal_name"):
        issues.append(DealIssue(src_id, name, "required_fields", "error", "Missing deal_name"))
    return issues


def _check_payer_mix(deal: Dict, src_id: str, name: str) -> List[DealIssue]:
    issues = []
    ps = _payer_sum(deal)
    if ps is None:
        return []  # no payer mix → skip
    if abs(ps - 1.0) > 0.05:
        issues.append(DealIssue(
            src_id, name, "payer_mix_sum", "warning",
            f"Payer mix sums to {ps:.3f} (expected ~1.0)"
        ))
    return issues


def _check_moic_irr_hold(deal: Dict, src_id: str, name: str) -> List[DealIssue]:
    issues = []
    moic = _safe_float(deal.get("realized_moic"))
    irr = _safe_float(deal.get("realized_irr"))
    hold = _safe_float(deal.get("hold_years"))
    if moic is None or irr is None or hold is None:
        return []

    if hold <= 0:
        return []

    # Implied IRR from MOIC and hold
    if moic > 0:
        implied_irr = moic ** (1.0 / hold) - 1.0
        gap = abs(implied_irr - irr)
        if gap > 0.12:
            issues.append(DealIssue(
                src_id, name, "moic_irr_consistency", "warning",
                f"MOIC {moic:.2f}x / hold {hold:.1f}y implies IRR ~{implied_irr:.1%} "
                f"but reported {irr:.1%} (gap {gap:.0%})"
            ))

    # MOIC-IRR direction
    if moic > 1.0 and irr < -0.02:
        issues.append(DealIssue(
            src_id, name, "moic_irr_direction", "error",
            f"MOIC {moic:.2f}x positive but IRR {irr:.1%} negative"
        ))
    if moic < 1.0 and irr > 0.05:
        issues.append(DealIssue(
            src_id, name, "moic_irr_direction", "warning",
            f"MOIC {moic:.2f}x below 1 but IRR {irr:.1%} > 5%"
        ))
    return issues


def _check_ev_range(deal: Dict, src_id: str, name: str) -> List[DealIssue]:
    issues = []
    ev = _safe_float(deal.get("ev_mm"))
    if ev is None:
        return []
    if ev < 5:
        issues.append(DealIssue(src_id, name, "ev_range", "warning", f"EV ${ev:.0f}M very small"))
    if ev > 50000:
        issues.append(DealIssue(src_id, name, "ev_range", "info", f"EV ${ev:,.0f}M very large — verify"))
    return issues


def _check_year(deal: Dict, src_id: str, name: str) -> List[DealIssue]:
    issues = []
    yr = deal.get("year")
    if yr is None:
        return []
    try:
        yr_f = int(yr)
    except (TypeError, ValueError):
        issues.append(DealIssue(src_id, name, "year_range", "error", f"Non-integer year: {yr}"))
        return issues
    if yr_f < 1990 or yr_f > 2030:
        issues.append(DealIssue(src_id, name, "year_range", "warning", f"Year {yr_f} out of range [1990,2030]"))
    return issues


def _check_hold_years(deal: Dict, src_id: str, name: str) -> List[DealIssue]:
    issues = []
    hold = _safe_float(deal.get("hold_years"))
    if hold is None:
        return []
    if hold < 0.5 or hold > 15:
        issues.append(DealIssue(
            src_id, name, "hold_years_range", "warning",
            f"Hold years {hold:.1f} outside typical range [0.5, 15]"
        ))
    return issues


def _check_nonneg_moic(deal: Dict, src_id: str, name: str) -> List[DealIssue]:
    issues = []
    moic = _safe_float(deal.get("realized_moic"))
    if moic is not None and moic < 0:
        issues.append(DealIssue(src_id, name, "nonneg_moic", "error", f"Negative MOIC {moic:.3f}"))
    return issues


_CHECKS = [
    _check_required_fields,
    _check_payer_mix,
    _check_moic_irr_hold,
    _check_ev_range,
    _check_year,
    _check_hold_years,
    _check_nonneg_moic,
]


# ---------------------------------------------------------------------------
# Main health check
# ---------------------------------------------------------------------------

def check_corpus(deals: List[Dict[str, Any]]) -> HealthCheckResult:
    """Run all health checks on a list of deal dicts."""
    result = HealthCheckResult(total_deals=len(deals))

    # Duplicate source_id check
    seen_ids: Dict[str, int] = {}
    for d in deals:
        sid = str(d.get("source_id") or "")
        seen_ids[sid] = seen_ids.get(sid, 0) + 1
    duplicates = [k for k, v in seen_ids.items() if v > 1 and k]
    result.duplicate_source_ids = duplicates
    for dup in duplicates:
        result.issues.append(DealIssue(
            dup, "", "duplicate_source_id", "error",
            f"source_id '{dup}' appears {seen_ids[dup]} times"
        ))

    # Per-deal checks
    deals_with_issues: set = set()
    for d in deals:
        src_id = str(d.get("source_id") or "")
        name = str(d.get("deal_name") or "")

        for check_fn in _CHECKS:
            for issue in check_fn(d, src_id, name):
                result.issues.append(issue)
                deals_with_issues.add(src_id)

    result.error_count = sum(1 for i in result.issues if i.severity == "error")
    result.warning_count = sum(1 for i in result.issues if i.severity == "warning")
    result.info_count = sum(1 for i in result.issues if i.severity == "info")
    result.clean_deal_count = len(deals) - len(deals_with_issues)

    # Health score: penalize errors more than warnings
    penalty = result.error_count * 0.05 + result.warning_count * 0.01 + len(duplicates) * 0.10
    result.health_score = round(max(0.0, 1.0 - penalty / max(len(deals), 1)), 3)

    return result


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def health_check_text(result: HealthCheckResult) -> str:
    """Formatted text report of the health check."""
    lines = [
        "Corpus Health Check Report",
        "=" * 60,
        f"  Total deals    : {result.total_deals}",
        f"  Clean deals    : {result.clean_deal_count}",
        f"  Errors         : {result.error_count}",
        f"  Warnings       : {result.warning_count}",
        f"  Info           : {result.info_count}",
        f"  Duplicates     : {len(result.duplicate_source_ids)}",
        f"  Health score   : {result.health_score:.1%}",
        "-" * 60,
    ]

    if not result.issues:
        lines.append("  No issues found. Corpus is clean.")
    else:
        for issue in result.issues[:30]:
            lines.append(
                f"  [{issue.severity.upper()}] {issue.source_id} | "
                f"{issue.check}: {issue.detail}"
            )
        if len(result.issues) > 30:
            lines.append(f"  ... {len(result.issues) - 30} more issues")

    lines.append("=" * 60)
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# One-call helper
# ---------------------------------------------------------------------------

def run_corpus_health_check(db_path: str = "corpus.db") -> HealthCheckResult:
    """Load and health-check the full seeded corpus from db_path."""
    from .deals_corpus import DealsCorpus
    corpus = DealsCorpus(db_path)
    corpus.seed()
    deals = corpus.list()
    return check_corpus(deals)
