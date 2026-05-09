"""Deal screening engine — rapid pass/watch/fail triage for healthcare PE deals.

Combines risk matrix, senior-partner heuristics, and base-rate benchmarks
into a single screening decision with supporting rationale.

Screening criteria (configurable):
  FAIL  – any critical risk dimension, trap scan critical, or MOIC below threshold
  WATCH – multiple warnings, above-ceiling entry multiple, or missing key data
  PASS  – all checks pass within configurable thresholds

Public API:
    ScreeningConfig                     dataclass
    ScreeningResult                     dataclass
    screen_deal(deal, config, corpus)   -> ScreeningResult
    screen_corpus(deals, config)        -> list[ScreeningResult]
    screening_report(results)           -> str
    screening_summary(results)          -> dict
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ScreeningConfig:
    """Configurable thresholds for the screening engine.

    Phase 3G — defaults tightened to match real PE-firm screening
    behaviour (~90% rejection at the top of the funnel). The previous
    defaults produced a 61.8% pass rate on the corpus, which doesn't
    match how partners actually triage:

      - composite risk threshold dropped from 60/40 to 45/25 so a
        merely "warm" signal already moves to WATCH;
      - entry-multiple watch lowered from 14× to 11× (the median
        sponsor has paid 10–12× recently — anything above is a
        deliberate stretch that needs a story);
      - Medicaid concentration is now a hard FAIL above 40% with a
        WATCH zone 25–40%, instead of the prior single 65% WATCH
        cutoff (most real PE platforms reject Medicaid-heavy
        targets outright);
      - MERC (Medical Expenditure Ratio to Capital) is now a
        first-class triage signal: ≥ 1.00 → FAIL ("operating loss"),
        ≥ 0.95 → WATCH ("approaching break-even");
      - EBITDA-margin floor + data-completeness threshold + min EV
        size all tightened to match the platform-deal cutoff.

    The Medicaid caps and MERC checks the partner asked us to keep
    are preserved — only the thresholds move.
    """
    max_composite_risk_score: float = 40.0    # above → FAIL  (was 60)
    watch_composite_risk_score: float = 20.0  # above → WATCH (was 40)
    max_ev_ebitda: float = 15.0               # above → FAIL  (was 20)
    watch_ev_ebitda: float = 10.0             # above → WATCH (was 14)
    min_moic_threshold: float = 1.5
    # Medicaid-exposure caps — preserved from the original triage
    # spec, tightened to PE-realistic levels.
    max_medicaid_pct: float = 0.40            # above → FAIL  (was 0.65, WATCH-only)
    watch_medicaid_pct: float = 0.20          # above → WATCH (new)
    # MERC total-loss-risk triage — preserved from the spec, now
    # threshold-driven. MERC ≥ 1.00 means opex exceeds NPR, the
    # structural shape of every recent PE-healthcare bankruptcy.
    merc_fail_threshold: float = 1.00         # above → FAIL  (new)
    merc_watch_threshold: float = 0.95        # above → WATCH (new)
    # EBITDA-margin floor — sub-12% margin signals weak unit economics
    # for healthcare PE platforms (mature platforms run 12–18%).
    min_ebitda_margin_watch: float = 0.12     # below → WATCH (new)
    require_ebitda_positive: bool = True
    require_hold_in_range: bool = True
    min_ev_mm: float = 100.0                  # below → WATCH (was 20; platform-deal floor)
    # Data-completeness threshold — partners reject deals where the
    # CIM hasn't disclosed the basics.
    min_data_completeness_watch: float = 0.75  # below → WATCH (was 0.50)
    # Commercial-mix floor — most middle-market healthcare PE
    # platforms target 40%+ commercial reimbursement.
    min_commercial_pct_watch: float = 0.40    # below → WATCH (new)


@dataclass
class ScreeningResult:
    """Outcome of screening a single deal."""
    source_id: str
    deal_name: str
    decision: str          # PASS / WATCH / FAIL
    score: float           # composite screening score 0-100 (higher = worse)
    fail_reasons: List[str] = field(default_factory=list)
    watch_reasons: List[str] = field(default_factory=list)
    pass_signals: List[str] = field(default_factory=list)
    risk_composite: Optional[float] = None
    heuristic_signal: Optional[str] = None
    data_completeness: Optional[float] = None

    def as_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "deal_name": self.deal_name,
            "decision": self.decision,
            "score": self.score,
            "fail_reasons": self.fail_reasons,
            "watch_reasons": self.watch_reasons,
            "pass_signals": self.pass_signals,
            "risk_composite": self.risk_composite,
            "heuristic_signal": self.heuristic_signal,
            "data_completeness": self.data_completeness,
        }


def _safe_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _payer_share(deal: Dict, key: str) -> float:
    import json
    pm = deal.get("payer_mix")
    if isinstance(pm, str):
        try:
            pm = json.loads(pm)
        except Exception:
            return 0.0
    if not isinstance(pm, dict):
        return 0.0
    return float(pm.get(key, 0) or 0)


def _data_completeness(deal: Dict[str, Any]) -> float:
    """Simple data completeness fraction for key fields."""
    key_fields = ["ev_mm", "ebitda_mm", "ev_ebitda", "hold_years",
                  "payer_mix", "year", "buyer", "deal_type"]
    present = sum(1 for f in key_fields if deal.get(f) is not None)
    return round(present / len(key_fields), 2)


def screen_deal(
    deal: Dict[str, Any],
    config: Optional[ScreeningConfig] = None,
    corpus_deals: Optional[List[Dict[str, Any]]] = None,
) -> ScreeningResult:
    """Screen a single deal and return a pass/watch/fail decision.

    Args:
        deal:         Deal dict (corpus format)
        config:       ScreeningConfig with thresholds (defaults used if None)
        corpus_deals: Optional corpus for base-rate comparison
    """
    if config is None:
        config = ScreeningConfig()

    src = str(deal.get("source_id") or "")
    name = str(deal.get("deal_name") or "")

    fail_reasons: List[str] = []
    watch_reasons: List[str] = []
    pass_signals: List[str] = []

    # --- Risk matrix ---
    from .deal_risk_matrix import build_risk_matrix
    matrix = build_risk_matrix(deal)
    risk_comp = matrix.composite_score

    if risk_comp >= config.max_composite_risk_score:
        fail_reasons.append(f"Risk score {risk_comp:.0f}/100 exceeds fail threshold {config.max_composite_risk_score:.0f}")
    elif risk_comp >= config.watch_composite_risk_score:
        watch_reasons.append(f"Risk score {risk_comp:.0f}/100 in watch zone")
    else:
        pass_signals.append(f"Risk score {risk_comp:.0f}/100 within acceptable range")

    # Critical dimension triggers immediate FAIL
    for dim in matrix.dimensions:
        if dim.level == "critical":
            fail_reasons.append(f"{dim.name.capitalize()} risk is CRITICAL")

    # --- Entry multiple ---
    ev_ebitda = _safe_float(deal.get("ev_ebitda"))
    if ev_ebitda is not None:
        if ev_ebitda > config.max_ev_ebitda:
            fail_reasons.append(f"Entry multiple {ev_ebitda:.1f}x exceeds max {config.max_ev_ebitda:.0f}x")
        elif ev_ebitda > config.watch_ev_ebitda:
            watch_reasons.append(f"Entry multiple {ev_ebitda:.1f}x above watch threshold {config.watch_ev_ebitda:.0f}x")
        else:
            pass_signals.append(f"Entry multiple {ev_ebitda:.1f}x within target range")

    # --- EBITDA positivity ---
    ebitda = _safe_float(deal.get("ebitda_mm") or deal.get("ebitda_at_entry_mm"))
    if config.require_ebitda_positive and ebitda is not None and ebitda < 0:
        fail_reasons.append(f"Negative EBITDA ${ebitda:.2f}M — pre-profitability")
    elif ebitda and ebitda > 0:
        pass_signals.append(f"Positive EBITDA ${ebitda:.2f}M")

    # --- Medicaid concentration (Phase 3G: now a hard FAIL above 40%) ---
    medicaid = _payer_share(deal, "medicaid")
    if medicaid > config.max_medicaid_pct:
        fail_reasons.append(
            f"Medicaid {medicaid:.0%} exceeds hard cap "
            f"{config.max_medicaid_pct:.0%} (reimbursement risk)"
        )
    elif medicaid > config.watch_medicaid_pct:
        watch_reasons.append(
            f"Medicaid {medicaid:.0%} above watch threshold "
            f"{config.watch_medicaid_pct:.0%}"
        )
    elif 0 < medicaid <= config.watch_medicaid_pct:
        pass_signals.append(f"Medicaid {medicaid:.0%} within acceptable range")

    # --- Commercial-mix floor (Phase 3G) ---
    commercial = _payer_share(deal, "commercial")
    if commercial > 0 and commercial < config.min_commercial_pct_watch:
        watch_reasons.append(
            f"Commercial mix {commercial:.0%} below "
            f"{config.min_commercial_pct_watch:.0%} platform floor"
        )

    # --- MERC total-loss-risk triage (Phase 3G) ---
    # MERC = opex / NPR. ≥ 1.00 means the target is operating at a
    # loss before any debt service — this is the shape of every
    # recent PE-healthcare bankruptcy at filing. Hard FAIL.
    npr_for_merc = _safe_float(deal.get("net_patient_revenue") or deal.get("npsr_at_entry_mm"))
    opex_for_merc = _safe_float(deal.get("operating_expenses") or deal.get("opex_at_entry_mm"))
    if npr_for_merc and npr_for_merc > 0 and opex_for_merc is not None:
        merc = opex_for_merc / npr_for_merc
        if merc >= config.merc_fail_threshold:
            fail_reasons.append(
                f"MERC {merc:.2f} ≥ {config.merc_fail_threshold:.2f} "
                f"(operating loss — Steward/Envision shape)"
            )
        elif merc >= config.merc_watch_threshold:
            watch_reasons.append(
                f"MERC {merc:.2f} approaches break-even "
                f"(threshold {config.merc_watch_threshold:.2f})"
            )

    # --- EBITDA-margin floor (Phase 3G) ---
    # Sub-5% EBITDA margin signals weak unit economics — possible
    # WATCH even when other metrics look clean.
    revenue_at_entry = _safe_float(
        deal.get("revenue_at_entry_mm") or deal.get("npsr_at_entry_mm")
    )
    if revenue_at_entry and revenue_at_entry > 0 and ebitda is not None and ebitda > 0:
        ebitda_margin = ebitda / revenue_at_entry
        if ebitda_margin < config.min_ebitda_margin_watch:
            watch_reasons.append(
                f"EBITDA margin {ebitda_margin:.1%} below "
                f"{config.min_ebitda_margin_watch:.0%} unit-economics floor"
            )

    # --- Deal size ---
    ev = _safe_float(deal.get("ev_mm"))
    if ev is not None and ev < config.min_ev_mm:
        watch_reasons.append(f"EV ${ev:.2f}M below min diligence size ${config.min_ev_mm:.2f}M")

    # --- Senior partner heuristics ---
    try:
        from .senior_partner_heuristics import (
            healthcare_trap_scan, full_heuristic_assessment
        )
        traps = healthcare_trap_scan(deal)
        critical_traps = [t for t in traps if t.get("severity") == "critical"]
        if critical_traps:
            for t in critical_traps:
                fail_reasons.append(f"Healthcare trap: {t['trap']} — {t['detail']}")

        assessment = full_heuristic_assessment(deal)
        heuristic_signal = assessment.get("overall_signal", "green")
        if heuristic_signal == "red":
            fail_reasons.append("Senior partner heuristics: RED signal")
        elif heuristic_signal in ("amber", "yellow"):
            watch_reasons.append(f"Senior partner heuristics: {heuristic_signal.upper()} signal")
        else:
            pass_signals.append("Senior partner heuristics: GREEN signal")
    except Exception:
        heuristic_signal = None
        watch_reasons.append("Heuristic assessment unavailable")

    # --- Hold years ---
    hold = _safe_float(deal.get("hold_years"))
    if config.require_hold_in_range and hold is not None:
        if hold < 0.5 or hold > 15:
            watch_reasons.append(f"Hold period {hold:.1f}y outside typical range [0.5, 15]")

    # --- Data completeness (Phase 3G: tighter floor) ---
    completeness = _data_completeness(deal)
    if completeness < config.min_data_completeness_watch:
        watch_reasons.append(
            f"Data completeness {completeness:.0%} below "
            f"{config.min_data_completeness_watch:.0%} CIM-quality floor"
        )
    else:
        pass_signals.append(f"Data completeness {completeness:.0%}")

    # --- Final decision ---
    if fail_reasons:
        decision = "FAIL"
    elif watch_reasons:
        decision = "WATCH"
    else:
        decision = "PASS"

    # Composite screening score (0-100; higher = worse)
    score = min(100.0, round(
        risk_comp * 0.5
        + len(fail_reasons) * 15
        + len(watch_reasons) * 5
        - len(pass_signals) * 2,
        1
    ))
    score = max(0.0, score)

    return ScreeningResult(
        source_id=src,
        deal_name=name,
        decision=decision,
        score=score,
        fail_reasons=fail_reasons,
        watch_reasons=watch_reasons,
        pass_signals=pass_signals,
        risk_composite=risk_comp,
        heuristic_signal=heuristic_signal,
        data_completeness=completeness,
    )


def screen_corpus(
    deals: List[Dict[str, Any]],
    config: Optional[ScreeningConfig] = None,
) -> List[ScreeningResult]:
    """Screen all deals in the corpus."""
    return [screen_deal(d, config) for d in deals]


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def screening_report(results: List[ScreeningResult], max_rows: int = 50) -> str:
    """Formatted screening report."""
    pass_ct = sum(1 for r in results if r.decision == "PASS")
    watch_ct = sum(1 for r in results if r.decision == "WATCH")
    fail_ct = sum(1 for r in results if r.decision == "FAIL")

    lines = [
        "Deal Screening Report",
        "=" * 70,
        f"  Total Screened: {len(results)}",
        f"  PASS  : {pass_ct} ({pass_ct/max(len(results),1):.0%})",
        f"  WATCH : {watch_ct} ({watch_ct/max(len(results),1):.0%})",
        f"  FAIL  : {fail_ct} ({fail_ct/max(len(results),1):.0%})",
        "-" * 70,
    ]
    sorted_results = sorted(results, key=lambda r: (
        {"FAIL": 0, "WATCH": 1, "PASS": 2}.get(r.decision, 3), -r.score
    ))
    for r in sorted_results[:max_rows]:
        badge = {"PASS": "[PASS]", "WATCH": "[WATCH]", "FAIL": "[FAIL]"}.get(r.decision, "[ ? ]")
        lines.append(f"  {badge} {r.deal_name[:50]:<50} score={r.score:.0f}")
        for reason in r.fail_reasons[:2]:
            lines.append(f"         ✗ {reason}")
        for reason in r.watch_reasons[:2]:
            lines.append(f"         ⚠ {reason}")
    if len(results) > max_rows:
        lines.append(f"  ... {len(results) - max_rows} more deals")
    lines.append("=" * 70)
    return "\n".join(lines) + "\n"


def screening_summary(results: List[ScreeningResult]) -> Dict[str, Any]:
    """Return a JSON-serializable summary dict."""
    by_decision = {"PASS": 0, "WATCH": 0, "FAIL": 0}
    for r in results:
        by_decision[r.decision] = by_decision.get(r.decision, 0) + 1
    scores = [r.score for r in results]
    return {
        "total": len(results),
        "by_decision": by_decision,
        "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
        "top_fails": [
            {"source_id": r.source_id, "deal_name": r.deal_name, "score": r.score,
             "fail_reasons": r.fail_reasons}
            for r in sorted(results, key=lambda x: -x.score)
            if r.decision == "FAIL"
        ][:5],
    }
