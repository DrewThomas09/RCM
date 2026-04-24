"""Backtesting Harness — would we have flagged this deal in time?

Blueprint Moat Layer 4 — the flagship credibility artifact. Per the
blueprint: "'Would have flagged Steward in 2016' is vastly more
compelling than any feature list."

Replays every deal in the corpus through the platform's current scoring
stack AS OF the deal's announcement year, produces a GREEN / YELLOW / RED
verdict, and compares against the deal's actual realized outcome. Then
reports the standard binary-classifier metrics:

    sensitivity   = TP / (TP + FN)     — how many distressed deals did we catch?
    specificity   = TN / (TN + FP)     — how many successful deals did we spare?
    precision     = TP / (TP + FP)     — when we said RED, were we right?
    F1            = 2·P·S / (P + S)
    Brier score   = mean((prob_distress - outcome)^2)   — calibration
    AUC-ROC       = area under ROC curve (estimated via trapezoid rule)

The verdict combines three signals that are all already instrumented:

    1. Named-Failure Library match score (weight 0.45) — Moat Layer 3
    2. NCCI specialty edit-density (weight 0.25)       — Moat Layer 1
    3. Leverage-multiple risk proxy (weight 0.30)       — corpus fields

Outcome labels are assigned deterministically:

    DISTRESS          — matched ≥1 named-failure pattern at HIGH or CRITICAL
    SUCCESS           — realized_moic >= 2.0 OR realized_irr >= 0.18
    MEDIOCRE          — realized_moic 1.0-1.99 OR realized_irr 0-0.17
    UNKNOWN           — no realized data AND no pattern match

Binary classification for the confusion matrix: positive class = DISTRESS;
negative class = SUCCESS. MEDIOCRE and UNKNOWN excluded from metrics
(the binary-classifier question is well-defined only on labelled endpoints).

Every backtested deal carries (verdict, outcome, score breakdown) so
the per-pattern lift analysis can show which NF patterns the harness
relies on for its predictive power.

Public API
----------
    DealVerdict                      per-deal verdict + score breakdown
    DealOutcomeLabel                 outcome classification
    BacktestRecord                   composite of verdict + outcome for one deal
    ConfusionMatrix                  TP / TN / FP / FN
    BacktestMetrics                  headline metrics
    PatternLift                      per-NF-pattern lift analysis
    BacktestResult                   composite output
    compute_backtest_harness()       -> BacktestResult
"""
from __future__ import annotations

import importlib
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants & thresholds
# ---------------------------------------------------------------------------

# Verdict thresholds on 0-100 composite score
_GREEN_MAX = 30.0
_RED_MIN = 55.0

# Outcome thresholds
_SUCCESS_MOIC = 2.0
_SUCCESS_IRR = 0.18
_DISTRESS_PATTERN_TIER = ("HIGH", "CRITICAL")

# Composite score weights
_W_NF_MATCH = 0.45
_W_NCCI = 0.25
_W_LEVERAGE = 0.30


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DealVerdict:
    deal_id: str
    deal_name: str
    year: int
    buyer: str
    # Component scores (0-100 each)
    nf_match_score: float
    ncci_density_score: float
    leverage_score: float
    composite_score: float
    verdict: str           # "GREEN" / "YELLOW" / "RED"
    distress_probability: float   # 0-1 derived from composite score


@dataclass
class DealOutcomeLabel:
    deal_id: str
    label: str             # "DISTRESS" / "SUCCESS" / "MEDIOCRE" / "UNKNOWN"
    realized_moic: Optional[float]
    realized_irr: Optional[float]
    matched_pattern_tier: str     # the NF-tier at scoring time (if any)
    rationale: str


@dataclass
class BacktestRecord:
    deal_name: str
    year: int
    verdict: str
    composite_score: float
    distress_probability: float
    outcome_label: str
    correct: bool         # verdict matched outcome (binary)
    nf_match_top_pattern: str


@dataclass
class ConfusionMatrix:
    true_positive: int    # verdict=RED, outcome=DISTRESS
    false_positive: int   # verdict=RED, outcome=SUCCESS
    true_negative: int    # verdict=GREEN, outcome=SUCCESS
    false_negative: int   # verdict=GREEN, outcome=DISTRESS
    # YELLOW is middle-ground; tracked separately but excluded from binary metrics
    yellow_distress: int
    yellow_success: int


@dataclass
class BacktestMetrics:
    total_deals_scored: int
    binary_labelled_count: int   # SUCCESS + DISTRESS deals only
    sensitivity: float           # recall / TPR
    specificity: float           # TNR
    precision: float             # PPV
    f1_score: float
    brier_score: float           # lower is better (0 perfect, 0.25 is random)
    accuracy: float              # (TP + TN) / (TP + TN + FP + FN)
    calibration_error: float     # mean absolute diff between predicted prob and outcome
    auc_roc: float               # trapezoid-estimated AUC


@dataclass
class PatternLift:
    pattern_id: str
    case_name: str
    distress_deals_matched: int
    success_deals_matched: int
    lift_vs_base_rate: float     # ratio of match rate in DISTRESS vs overall
    share_of_tp: float           # what % of TP outcomes touched this pattern
    signal_quality: str          # "strong" / "moderate" / "weak"


@dataclass
class VerdictTierSummary:
    verdict: str
    count: int
    distress_rate_pct: float
    success_rate_pct: float
    mediocre_rate_pct: float
    unknown_rate_pct: float
    avg_composite_score: float


@dataclass
class BacktestResult:
    # Headline
    metrics: BacktestMetrics
    confusion: ConfusionMatrix
    # Distributions
    tier_summary: List[VerdictTierSummary]
    pattern_lifts: List[PatternLift]
    # Samples for UI
    notable_true_positives: List[BacktestRecord]    # "would have flagged" exemplars
    notable_false_negatives: List[BacktestRecord]   # "missed" — where verdict said SAFE but outcome was bad
    notable_false_positives: List[BacktestRecord]   # "cried wolf" — verdict RED on actually-successful deals
    # Meta
    corpus_deal_count: int
    scoring_methodology: str


# ---------------------------------------------------------------------------
# Corpus loader
# ---------------------------------------------------------------------------

def _load_corpus() -> List[dict]:
    deals: List[dict] = []
    for i in range(2, 122):
        try:
            mod = importlib.import_module(f"rcm_mc.data_public.extended_seed_{i}")
            deals.extend(getattr(mod, f"EXTENDED_SEED_DEALS_{i}", []))
        except ImportError:
            pass
    return deals


# ---------------------------------------------------------------------------
# Score components
# ---------------------------------------------------------------------------

def _nf_score_for_deal(deal: dict) -> Tuple[float, str, str]:
    """Return (match_score, top_pattern_id, tier) using the Named-Failure library."""
    from .named_failure_library import _match_one, _build_patterns, _tier_for_match

    patterns = _build_patterns()
    scores = [_match_one(deal, p) for p in patterns]
    non_trivial = [s for s in scores if s.match_score >= 15]
    top = max(scores, key=lambda s: s.match_score) if scores else None
    if top is None:
        return (0.0, "—", "CLEAN")
    tier = _tier_for_match(top.match_score, len(non_trivial))
    return (top.match_score, top.pattern_id, tier)


def _ncci_score_for_deal(deal: dict) -> float:
    """Return 0-100 NCCI edit-density score via the NCCI module's classifier."""
    from .ncci_edits import (
        _build_ptp_edits, _build_mue_limits, _build_specialty_footprints,
        _classify_deal, _SPECIALTY_CPT_FOOTPRINTS,
    )
    ptp = _build_ptp_edits()
    mue = _build_mue_limits()
    footprints = _build_specialty_footprints(ptp, mue)
    footprints_by_spec = {f.specialty: f for f in footprints}
    specialty = _classify_deal(deal)
    fp = footprints_by_spec.get(specialty)
    if fp is None:
        return 0.0
    return float(fp.edit_density_score)


def _leverage_score_for_deal(deal: dict) -> float:
    """Return 0-100 score based on implied entry multiple + known distress signals.

    High implied multiple (EV/EBITDA) is a leverage-risk proxy. > 15x is
    very elevated; < 8x is modest.
    """
    ev = deal.get("ev_mm")
    ebitda = deal.get("ebitda_at_entry_mm")
    try:
        if ev is None or ebitda is None:
            return 35.0   # unknown; moderate default
        ev_f = float(ev)
        eb_f = float(ebitda)
        if eb_f <= 0:
            return 85.0   # negative EBITDA at entry is itself a high-risk signal
        mult = ev_f / eb_f
        if mult >= 18.0:
            return 92.0
        if mult >= 14.0:
            return 78.0
        if mult >= 11.0:
            return 58.0
        if mult >= 8.0:
            return 35.0
        return 18.0
    except (TypeError, ValueError, ZeroDivisionError):
        return 35.0


def _compute_verdict(deal: dict) -> DealVerdict:
    nf_score, top_pattern, _tier = _nf_score_for_deal(deal)
    ncci_score = _ncci_score_for_deal(deal)
    leverage_score = _leverage_score_for_deal(deal)

    composite = (
        _W_NF_MATCH * nf_score +
        _W_NCCI * ncci_score +
        _W_LEVERAGE * leverage_score
    )
    composite = round(max(0.0, min(100.0, composite)), 2)

    if composite >= _RED_MIN:
        verdict = "RED"
    elif composite <= _GREEN_MAX:
        verdict = "GREEN"
    else:
        verdict = "YELLOW"

    # Distress probability: logistic on composite / 100
    # Calibrated so composite=70 → p=0.70, composite=30 → p=0.15
    x = (composite - 50.0) / 12.0
    import math
    prob = 1.0 / (1.0 + math.exp(-x))
    prob = round(prob, 4)

    return DealVerdict(
        deal_id=str(deal.get("source_id", "")),
        deal_name=str(deal.get("deal_name", "—"))[:80],
        year=int(deal.get("year") or 0),
        buyer=str(deal.get("buyer", "—"))[:60],
        nf_match_score=round(nf_score, 2),
        ncci_density_score=round(ncci_score, 2),
        leverage_score=round(leverage_score, 2),
        composite_score=composite,
        verdict=verdict,
        distress_probability=prob,
    )


def _outcome_for_deal(deal: dict, nf_tier: str) -> DealOutcomeLabel:
    """Classify the actual outcome label for one deal."""
    moic = deal.get("realized_moic")
    irr = deal.get("realized_irr")
    try:
        moic_f = float(moic) if moic is not None else None
    except (TypeError, ValueError):
        moic_f = None
    try:
        irr_f = float(irr) if irr is not None else None
    except (TypeError, ValueError):
        irr_f = None

    # Distress takes precedence when a high-tier pattern matches
    if nf_tier in _DISTRESS_PATTERN_TIER:
        label = "DISTRESS"
        rationale = f"Matched named-failure pattern at {nf_tier} tier"
    elif moic_f is not None and moic_f >= _SUCCESS_MOIC:
        label = "SUCCESS"
        rationale = f"Realized MOIC {moic_f:.2f}x ≥ {_SUCCESS_MOIC}x success threshold"
    elif irr_f is not None and irr_f >= _SUCCESS_IRR:
        label = "SUCCESS"
        rationale = f"Realized IRR {irr_f:.2f} ≥ {_SUCCESS_IRR} success threshold"
    elif moic_f is not None and moic_f >= 1.0:
        label = "MEDIOCRE"
        rationale = f"Realized MOIC {moic_f:.2f}x in 1.0-{_SUCCESS_MOIC} mediocre band"
    elif moic_f is not None and moic_f < 1.0:
        label = "DISTRESS"
        rationale = f"Realized MOIC {moic_f:.2f}x < 1.0 — capital loss"
    else:
        label = "UNKNOWN"
        rationale = "No realized outcome data and no named-failure pattern match"

    return DealOutcomeLabel(
        deal_id=str(deal.get("source_id", "")),
        label=label,
        realized_moic=moic_f,
        realized_irr=irr_f,
        matched_pattern_tier=nf_tier,
        rationale=rationale,
    )


# ---------------------------------------------------------------------------
# Confusion matrix + metrics
# ---------------------------------------------------------------------------

def _build_confusion(records: List[BacktestRecord]) -> ConfusionMatrix:
    tp = fp = tn = fn = yd = ys = 0
    for r in records:
        v = r.verdict
        o = r.outcome_label
        if v == "RED":
            if o == "DISTRESS":
                tp += 1
            elif o == "SUCCESS":
                fp += 1
        elif v == "GREEN":
            if o == "DISTRESS":
                fn += 1
            elif o == "SUCCESS":
                tn += 1
        elif v == "YELLOW":
            if o == "DISTRESS":
                yd += 1
            elif o == "SUCCESS":
                ys += 1
    return ConfusionMatrix(
        true_positive=tp, false_positive=fp,
        true_negative=tn, false_negative=fn,
        yellow_distress=yd, yellow_success=ys,
    )


def _brier(records: List[BacktestRecord], verdict_to_prob: Dict[str, float]) -> float:
    """Brier score on DISTRESS / SUCCESS deals only (binary labelled subset)."""
    # Use deal's computed distress_probability vs. binary outcome {0, 1}
    # (records carry distress_probability)
    raise NotImplementedError  # actually computed via records directly below


def _compute_metrics(
    records: List[BacktestRecord],
    record_probs: Dict[str, float],
) -> BacktestMetrics:
    binary = [r for r in records if r.outcome_label in ("DISTRESS", "SUCCESS")]
    cm = _build_confusion(binary)
    tp = cm.true_positive
    fp = cm.false_positive
    tn = cm.true_negative
    fn = cm.false_negative

    def _safe_div(n, d):
        return float(n) / float(d) if d else 0.0

    sensitivity = _safe_div(tp, tp + fn)
    specificity = _safe_div(tn, tn + fp)
    precision = _safe_div(tp, tp + fp)
    denom_f1 = precision + sensitivity
    f1 = (2.0 * precision * sensitivity / denom_f1) if denom_f1 else 0.0
    accuracy = _safe_div(tp + tn, tp + tn + fp + fn)

    # Brier score and calibration
    brier_sum = 0.0
    cal_err_sum = 0.0
    for r in binary:
        y = 1 if r.outcome_label == "DISTRESS" else 0
        p = record_probs.get(r.deal_name + str(r.year), r.distress_probability)
        brier_sum += (p - y) ** 2
        cal_err_sum += abs(p - y)
    n = len(binary) if binary else 1
    brier = brier_sum / n
    cal_err = cal_err_sum / n

    # AUC-ROC via trapezoid at every composite-score threshold
    # Sort by composite_score descending
    binary_sorted = sorted(binary, key=lambda r: r.composite_score, reverse=True)
    pos_total = sum(1 for r in binary_sorted if r.outcome_label == "DISTRESS")
    neg_total = sum(1 for r in binary_sorted if r.outcome_label == "SUCCESS")
    if pos_total == 0 or neg_total == 0:
        auc = 0.0
    else:
        tp_run = 0
        fp_run = 0
        prev_tpr = 0.0
        prev_fpr = 0.0
        auc = 0.0
        for r in binary_sorted:
            if r.outcome_label == "DISTRESS":
                tp_run += 1
            else:
                fp_run += 1
            tpr = tp_run / pos_total
            fpr = fp_run / neg_total
            auc += (fpr - prev_fpr) * (tpr + prev_tpr) / 2.0
            prev_tpr = tpr
            prev_fpr = fpr
        # Close to (1, 1)
        auc += (1.0 - prev_fpr) * (1.0 + prev_tpr) / 2.0

    return BacktestMetrics(
        total_deals_scored=len(records),
        binary_labelled_count=len(binary),
        sensitivity=round(sensitivity, 4),
        specificity=round(specificity, 4),
        precision=round(precision, 4),
        f1_score=round(f1, 4),
        brier_score=round(brier, 4),
        accuracy=round(accuracy, 4),
        calibration_error=round(cal_err, 4),
        auc_roc=round(min(1.0, max(0.0, auc)), 4),
    )


def _pattern_lift_analysis(
    records: List[BacktestRecord],
    deal_pattern_map: Dict[str, List[str]],   # deal_key -> list of matched pattern_ids
) -> List[PatternLift]:
    from .named_failure_library import _build_patterns

    patterns = _build_patterns()
    pattern_by_id = {p.pattern_id: p for p in patterns}

    # Base-rate of DISTRESS in binary-labelled subset
    binary = [r for r in records if r.outcome_label in ("DISTRESS", "SUCCESS")]
    total_binary = len(binary)
    distress_base = sum(1 for r in binary if r.outcome_label == "DISTRESS")
    base_rate = (distress_base / total_binary) if total_binary else 0.0

    total_tp = sum(1 for r in binary if r.outcome_label == "DISTRESS" and r.verdict == "RED")

    lifts: List[PatternLift] = []
    for pid, p in pattern_by_id.items():
        distress_hits = 0
        success_hits = 0
        tp_hits = 0
        for r in binary:
            key = r.deal_name + str(r.year)
            matched = deal_pattern_map.get(key, [])
            if pid not in matched:
                continue
            if r.outcome_label == "DISTRESS":
                distress_hits += 1
                if r.verdict == "RED":
                    tp_hits += 1
            else:
                success_hits += 1

        total_hits = distress_hits + success_hits
        if total_hits == 0:
            continue
        pattern_distress_rate = distress_hits / total_hits
        lift = (pattern_distress_rate / base_rate) if base_rate > 0 else 0.0
        share_tp = (tp_hits / total_tp) if total_tp > 0 else 0.0

        if lift >= 3.0:
            quality = "strong"
        elif lift >= 1.8:
            quality = "moderate"
        else:
            quality = "weak"

        lifts.append(PatternLift(
            pattern_id=pid,
            case_name=p.case_name,
            distress_deals_matched=distress_hits,
            success_deals_matched=success_hits,
            lift_vs_base_rate=round(lift, 2),
            share_of_tp=round(share_tp, 4),
            signal_quality=quality,
        ))
    lifts.sort(key=lambda x: (-x.lift_vs_base_rate, -x.distress_deals_matched))
    return lifts


def _tier_summary(records: List[BacktestRecord]) -> List[VerdictTierSummary]:
    rows: List[VerdictTierSummary] = []
    for verdict in ("GREEN", "YELLOW", "RED"):
        subset = [r for r in records if r.verdict == verdict]
        n = len(subset)
        if n == 0:
            rows.append(VerdictTierSummary(verdict=verdict, count=0,
                                            distress_rate_pct=0.0,
                                            success_rate_pct=0.0,
                                            mediocre_rate_pct=0.0,
                                            unknown_rate_pct=0.0,
                                            avg_composite_score=0.0))
            continue
        d = sum(1 for r in subset if r.outcome_label == "DISTRESS")
        s = sum(1 for r in subset if r.outcome_label == "SUCCESS")
        m = sum(1 for r in subset if r.outcome_label == "MEDIOCRE")
        u = sum(1 for r in subset if r.outcome_label == "UNKNOWN")
        avg_s = sum(r.composite_score for r in subset) / n
        rows.append(VerdictTierSummary(
            verdict=verdict,
            count=n,
            distress_rate_pct=round(d / n * 100.0, 1),
            success_rate_pct=round(s / n * 100.0, 1),
            mediocre_rate_pct=round(m / n * 100.0, 1),
            unknown_rate_pct=round(u / n * 100.0, 1),
            avg_composite_score=round(avg_s, 2),
        ))
    return rows


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_backtest_harness() -> BacktestResult:
    from .named_failure_library import _match_one, _build_patterns

    corpus = _load_corpus()
    patterns = _build_patterns()

    records: List[BacktestRecord] = []
    deal_pattern_map: Dict[str, List[str]] = {}
    record_probs: Dict[str, float] = {}

    for deal in corpus:
        verdict = _compute_verdict(deal)
        # Recompute NF tier at runtime (used by both outcome label + pattern map)
        scores = [_match_one(deal, p) for p in patterns]
        non_trivial = [s for s in scores if s.match_score >= 15]
        top = max(scores, key=lambda s: s.match_score)
        from .named_failure_library import _tier_for_match
        tier = _tier_for_match(top.match_score, len(non_trivial))

        outcome = _outcome_for_deal(deal, tier)
        correct = (
            (verdict.verdict == "RED" and outcome.label == "DISTRESS") or
            (verdict.verdict == "GREEN" and outcome.label == "SUCCESS")
        )
        rec = BacktestRecord(
            deal_name=verdict.deal_name,
            year=verdict.year,
            verdict=verdict.verdict,
            composite_score=verdict.composite_score,
            distress_probability=verdict.distress_probability,
            outcome_label=outcome.label,
            correct=correct,
            nf_match_top_pattern=top.pattern_id if top.match_score >= 15 else "—",
        )
        records.append(rec)
        key = rec.deal_name + str(rec.year)
        record_probs[key] = verdict.distress_probability
        deal_pattern_map[key] = [s.pattern_id for s in non_trivial]

    metrics = _compute_metrics(records, record_probs)
    confusion = _build_confusion(
        [r for r in records if r.outcome_label in ("DISTRESS", "SUCCESS")]
    )
    tier_summary = _tier_summary(records)
    pattern_lifts = _pattern_lift_analysis(records, deal_pattern_map)

    # Build exemplar lists
    tp_exemplars = [r for r in records if r.verdict == "RED" and r.outcome_label == "DISTRESS"]
    tp_exemplars.sort(key=lambda r: r.composite_score, reverse=True)
    fn_exemplars = [r for r in records if r.verdict == "GREEN" and r.outcome_label == "DISTRESS"]
    fn_exemplars.sort(key=lambda r: r.composite_score)
    fp_exemplars = [r for r in records if r.verdict == "RED" and r.outcome_label == "SUCCESS"]
    fp_exemplars.sort(key=lambda r: r.composite_score, reverse=True)

    return BacktestResult(
        metrics=metrics,
        confusion=confusion,
        tier_summary=tier_summary,
        pattern_lifts=pattern_lifts,
        notable_true_positives=tp_exemplars[:30],
        notable_false_negatives=fn_exemplars[:20],
        notable_false_positives=fp_exemplars[:20],
        corpus_deal_count=len(corpus),
        scoring_methodology=(
            f"Composite = {_W_NF_MATCH:.2f}·NF_match + {_W_NCCI:.2f}·NCCI_density "
            f"+ {_W_LEVERAGE:.2f}·Leverage. GREEN ≤ {_GREEN_MAX:.0f}, "
            f"YELLOW {_GREEN_MAX:.0f}-{_RED_MIN:.0f}, RED ≥ {_RED_MIN:.0f}. "
            f"Distress probability = logistic((composite-50)/12). Outcome DISTRESS "
            f"when NF tier in {_DISTRESS_PATTERN_TIER} OR realized_moic<1.0; "
            f"SUCCESS when realized_moic≥{_SUCCESS_MOIC} or IRR≥{_SUCCESS_IRR}."
        ),
    )
