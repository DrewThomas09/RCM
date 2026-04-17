"""Deal entry risk score — composite quantitative risk assessment.

Answers the IC question: "On a 0-100 scale, how risky is this entry?"

Scores six risk dimensions against the corpus:
  1. Entry multiple risk   — how aggressive vs. corpus median?
  2. Leverage risk         — over-levered vs. sector norms?
  3. Payer mix risk        — Medicaid concentration, self-pay exposure?
  4. Sector loss rate      — what fraction of sector deals lost money?
  5. Sponsor risk          — sponsor track record in corpus?
  6. Deal size uncertainty — small deals have wider outcome distributions?

Each dimension is scored 0-40 (risk points; higher = more risky).
Total is summed and clamped to 0-100.
Signal: Green (< 25), Yellow (25-55), Red (> 55).

A score near 0 does not mean certain success — it means the observable
risk factors are within corpus-normal ranges. This is a diligence filter,
not a return predictor.

Public API:
    RiskDimension                dataclass (name, score, max_score, rationale)
    EntryRiskScore               dataclass (total, signal, dimensions)
    score_entry_risk(deal, corpus_deals, assumptions) -> EntryRiskScore
    risk_score_report(score)     -> str
    risk_score_table(scores)     -> str
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RiskDimension:
    """Single risk dimension with score and rationale."""
    name: str
    score: float        # 0 - max_score (higher = more risky)
    max_score: float
    pct_of_max: float   # score / max_score
    rationale: str
    signal: str         # "low" / "medium" / "high"


@dataclass
class EntryRiskScore:
    """Composite entry risk assessment."""
    total: float                    # 0-100 (higher = more risky)
    signal: str                     # "green" / "yellow" / "red"
    dimensions: List[RiskDimension] = field(default_factory=list)
    deal_name: str = ""
    corpus_n: int = 0
    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _pct_rank(value: float, sorted_corpus: List[float]) -> float:
    """Return percentile rank (0-1) of value within sorted_corpus."""
    if not sorted_corpus:
        return 0.5
    n = len(sorted_corpus)
    below = sum(1 for v in sorted_corpus if v <= value)
    return below / n


def _payer_risk_score(payer_mix: Optional[Dict[str, float]]) -> float:
    """
    Payer mix risk: 0=all commercial, 40=all Medicaid/self-pay.

    Risk weights per payer type:
        commercial: 0.0   (best for margins and reimbursement certainty)
        medicare:   0.15  (moderate; rate risk but more predictable than Medicaid)
        medicaid:   0.35  (high rate risk; state budget dependency)
        self_pay:   0.50  (highest bad debt / write-off risk)
    """
    if not payer_mix:
        return 20.0  # unknown → medium risk

    weights = {
        "commercial": 0.0,
        "medicare": 0.15,
        "medicaid": 0.35,
        "self_pay": 0.50,
    }
    raw = sum(weights.get(k, 0.25) * v for k, v in payer_mix.items())
    return min(40.0, raw * 100.0)  # scale to 0-40


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------

def score_entry_risk(
    deal: Dict[str, Any],
    corpus_deals: List[Dict[str, Any]],
    assumptions: Optional[Dict[str, Any]] = None,
) -> EntryRiskScore:
    """Compute composite entry risk score.

    Args:
        deal:           Deal dict (at minimum: ev_mm, ebitda_at_entry_mm,
                        sector, buyer, payer_mix)
        corpus_deals:   Raw seed dicts for benchmarking
        assumptions:    Optional: leverage_pct, ebitda_cagr, hold_years

    Returns:
        EntryRiskScore with total (0-100), signal, and dimension breakdown
    """
    ass = assumptions or {}
    deal_name = deal.get("deal_name", "Unknown")

    ev = float(deal.get("ev_mm") or deal.get("entry_ev_mm") or 0)
    ebitda = float(deal.get("ebitda_at_entry_mm") or deal.get("ebitda_mm") or 0)
    sector = deal.get("sector") or ""
    buyer = deal.get("buyer") or ""
    payer_mix = deal.get("payer_mix") or {}
    leverage_pct = float(ass.get("leverage_pct", deal.get("leverage_pct", 0.55)))

    entry_multiple = ev / ebitda if ebitda > 0 else None

    # Filter corpus for benchmarking
    realized = [d for d in corpus_deals if d.get("realized_moic") and d.get("ev_mm") and d.get("ebitda_at_entry_mm")]
    corpus_n = len(realized)

    dimensions = []
    notes = []

    # ------------------------------------------------------------------
    # Dimension 1: Entry Multiple Risk (max 20 pts)
    # ------------------------------------------------------------------
    mult_score = 10.0  # default medium
    mult_rationale = "No entry multiple data"
    if entry_multiple and realized:
        corpus_multiples = sorted([
            float(d["ev_mm"]) / float(d["ebitda_at_entry_mm"])
            for d in realized
            if float(d.get("ebitda_at_entry_mm", 0)) > 0
        ])
        pct = _pct_rank(entry_multiple, corpus_multiples)
        corpus_med = corpus_multiples[len(corpus_multiples) // 2]
        mult_score = min(20.0, pct * 20.0)
        mult_signal = "low" if pct < 0.40 else ("medium" if pct < 0.70 else "high")
        mult_rationale = (
            f"{entry_multiple:.1f}x entry vs. corpus median {corpus_med:.1f}x "
            f"(P{pct*100:.0f})"
        )
        if pct > 0.80:
            notes.append(f"Entry multiple {entry_multiple:.1f}x is top-quintile aggressive vs. corpus")
    else:
        mult_signal = "medium"

    dimensions.append(RiskDimension(
        name="entry_multiple",
        score=round(mult_score, 1),
        max_score=20.0,
        pct_of_max=round(mult_score / 20.0, 3),
        rationale=mult_rationale,
        signal=mult_signal if entry_multiple else "medium",
    ))

    # ------------------------------------------------------------------
    # Dimension 2: Leverage Risk (max 15 pts)
    # ------------------------------------------------------------------
    lev_score = 7.5  # default
    lev_rationale = "Leverage not specified; using 55% default"
    lev_signal = "medium"
    # Benchmark: > 60% leverage is elevated, > 70% is aggressive
    if leverage_pct > 0.70:
        lev_score = 15.0
        lev_rationale = f"Leverage {leverage_pct:.0%} exceeds 70% — aggressive for healthcare"
        lev_signal = "high"
    elif leverage_pct > 0.60:
        lev_score = 10.0
        lev_rationale = f"Leverage {leverage_pct:.0%} elevated (>60%)"
        lev_signal = "medium"
    elif leverage_pct > 0.50:
        lev_score = 5.0
        lev_rationale = f"Leverage {leverage_pct:.0%} within normal range"
        lev_signal = "low"
    else:
        lev_score = 2.0
        lev_rationale = f"Leverage {leverage_pct:.0%} conservative"
        lev_signal = "low"

    # Additional interest coverage check
    if ebitda > 0 and ev > 0:
        entry_debt = ev * leverage_pct
        annual_interest = entry_debt * 0.065  # assume 6.5% debt rate
        dscr = ebitda / annual_interest
        if dscr < 1.5:
            lev_score = min(15.0, lev_score + 5.0)
            lev_rationale += f"; DSCR {dscr:.1f}x below 1.5x — tight coverage"
            notes.append(f"Tight DSCR {dscr:.1f}x — minimal covenant headroom at entry")

    dimensions.append(RiskDimension(
        name="leverage",
        score=round(lev_score, 1),
        max_score=15.0,
        pct_of_max=round(lev_score / 15.0, 3),
        rationale=lev_rationale,
        signal=lev_signal,
    ))

    # ------------------------------------------------------------------
    # Dimension 3: Payer Mix Risk (max 20 pts)
    # ------------------------------------------------------------------
    raw_payer = _payer_risk_score(payer_mix)
    # Scale: 0-40 raw → capped at 20 pts for this dimension
    payer_score = min(20.0, raw_payer * 0.5)
    medicaid_pct = payer_mix.get("medicaid", 0)
    selfpay_pct = payer_mix.get("self_pay", 0)
    payer_sig = "low" if payer_score < 7 else ("medium" if payer_score < 14 else "high")
    payer_rationale = (
        f"Medicaid {medicaid_pct:.0%}, self-pay {selfpay_pct:.0%}; "
        f"composite payer risk {payer_score:.1f}/20"
    )
    if medicaid_pct > 0.50:
        notes.append(f"High Medicaid concentration ({medicaid_pct:.0%}) exposes to state budget cycles")
    if selfpay_pct > 0.20:
        notes.append(f"Elevated self-pay ({selfpay_pct:.0%}) — bad debt / collection risk")

    dimensions.append(RiskDimension(
        name="payer_mix",
        score=round(payer_score, 1),
        max_score=20.0,
        pct_of_max=round(payer_score / 20.0, 3),
        rationale=payer_rationale,
        signal=payer_sig,
    ))

    # ------------------------------------------------------------------
    # Dimension 4: Sector Loss Rate (max 20 pts)
    # ------------------------------------------------------------------
    loss_score = 10.0  # default
    loss_rationale = "Insufficient sector data"
    loss_signal = "medium"
    try:
        from .subsector_benchmarks import get_sector_benchmark
        bench = get_sector_benchmark(corpus_deals, sector)
        if bench and bench.deal_count >= 3:
            loss_rate = bench.loss_rate or 0.0
            # loss_rate = 0 → 0 pts; loss_rate = 0.40 → 20 pts
            loss_score = min(20.0, loss_rate * 50.0)
            loss_signal = "low" if loss_rate < 0.10 else ("medium" if loss_rate < 0.25 else "high")
            loss_rationale = (
                f"Sector '{bench.sector}' loss rate {loss_rate:.0%} "
                f"(n={bench.deal_count}); MOIC P50 {bench.moic_p50:.2f}x"
            )
            if loss_rate > 0.25:
                notes.append(f"Sector loss rate {loss_rate:.0%} — elevated for this subsector")
    except Exception:
        pass

    dimensions.append(RiskDimension(
        name="sector_loss_rate",
        score=round(loss_score, 1),
        max_score=20.0,
        pct_of_max=round(loss_score / 20.0, 3),
        rationale=loss_rationale,
        signal=loss_signal,
    ))

    # ------------------------------------------------------------------
    # Dimension 5: Sponsor Risk (max 15 pts)
    # ------------------------------------------------------------------
    spon_score = 7.5  # unknown → medium
    spon_rationale = "Sponsor not found in corpus"
    spon_signal = "medium"
    try:
        from .sponsor_track_record import build_sponsor_records, _extract_sponsors
        if buyer:
            sponsors = _extract_sponsors(deal)
            records = build_sponsor_records(corpus_deals)
            for s in sponsors:
                if s in records:
                    rec = records[s]
                    med_moic = rec.median_moic or 0.0
                    loss_r = rec.loss_rate or 0.0
                    # Strong sponsor → low risk; weak → high risk
                    if med_moic >= 3.0 and loss_r < 0.10:
                        spon_score = 2.0
                        spon_signal = "low"
                    elif med_moic >= 2.0:
                        spon_score = 5.0
                        spon_signal = "low"
                    elif med_moic >= 1.5:
                        spon_score = 10.0
                        spon_signal = "medium"
                    else:
                        spon_score = 15.0
                        spon_signal = "high"
                    spon_rationale = (
                        f"Sponsor '{s}': {rec.deal_count} deals, "
                        f"median MOIC {med_moic:.2f}x, loss rate {loss_r:.0%}"
                    )
                    break
    except Exception:
        pass

    dimensions.append(RiskDimension(
        name="sponsor_track_record",
        score=round(spon_score, 1),
        max_score=15.0,
        pct_of_max=round(spon_score / 15.0, 3),
        rationale=spon_rationale,
        signal=spon_signal,
    ))

    # ------------------------------------------------------------------
    # Dimension 6: Deal Size Uncertainty (max 10 pts)
    # ------------------------------------------------------------------
    size_score = 5.0  # default
    size_rationale = "Deal size unknown"
    size_signal = "medium"
    if ev > 0:
        if ev < 200:
            size_score = 8.0
            size_rationale = f"Small deal (${ev:,.0f}M EV) — limited comparable exits"
            size_signal = "high"
        elif ev < 500:
            size_score = 5.0
            size_rationale = f"Mid-market (${ev:,.0f}M EV) — moderate comparable depth"
            size_signal = "medium"
        elif ev < 2_000:
            size_score = 2.0
            size_rationale = f"Large deal (${ev:,.0f}M EV) — good corpus coverage"
            size_signal = "low"
        else:
            size_score = 1.0
            size_rationale = f"Mega deal (${ev:,.0f}M EV) — thin corpus but well-known dynamics"
            size_signal = "low"

    dimensions.append(RiskDimension(
        name="deal_size_uncertainty",
        score=round(size_score, 1),
        max_score=10.0,
        pct_of_max=round(size_score / 10.0, 3),
        rationale=size_rationale,
        signal=size_signal,
    ))

    # ------------------------------------------------------------------
    # Total score
    # ------------------------------------------------------------------
    total = sum(d.score for d in dimensions)
    total = round(min(100.0, total), 1)

    if total < 25:
        signal = "green"
    elif total < 55:
        signal = "yellow"
    else:
        signal = "red"

    return EntryRiskScore(
        total=total,
        signal=signal,
        dimensions=dimensions,
        deal_name=deal_name,
        corpus_n=corpus_n,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def risk_score_report(score: EntryRiskScore) -> str:
    """Formatted risk report for IC packet."""
    sig_display = {"green": "GREEN ✓", "yellow": "YELLOW ⚠", "red": "RED ✗"}.get(
        score.signal, score.signal.upper()
    )
    lines = [
        f"Entry Risk Score: {score.deal_name}",
        "=" * 55,
        f"  Total Risk Score:  {score.total:.1f} / 100  [{sig_display}]",
        f"  Corpus comparisons: {score.corpus_n} realized deals",
        "",
        "Risk Dimensions:",
        f"  {'Dimension':<28} {'Score':>7} {'Max':>5} {'Signal':<8}",
        "-" * 55,
    ]
    for d in score.dimensions:
        bar = "█" * int(d.pct_of_max * 10) + "░" * (10 - int(d.pct_of_max * 10))
        lines.append(
            f"  {d.name.replace('_',' '):<28} {d.score:>5.1f} /{d.max_score:>3.0f}  "
            f"[{d.signal:<6}] {bar}"
        )
    lines.append("-" * 55)
    lines.append("")
    lines.append("Dimension Details:")
    for d in score.dimensions:
        lines.append(f"  {d.name.replace('_',' ').title()}: {d.rationale}")

    if score.notes:
        lines += ["", "Key Flags:"]
        for n in score.notes:
            lines.append(f"  • {n}")

    return "\n".join(lines) + "\n"


def risk_score_table(scores: List[EntryRiskScore]) -> str:
    """Compact comparison table for multiple deals."""
    hdr = f"{'Deal':<35} {'Score':>7} {'Signal':<8} {'Notes'}"
    sep = "-" * 80
    lines = [hdr, sep]
    for s in sorted(scores, key=lambda x: x.total, reverse=True):
        name = s.deal_name[:33]
        top_note = s.notes[0][:30] if s.notes else ""
        lines.append(f"{name:<35} {s.total:>5.1f}  [{s.signal:<6}] {top_note}")
    return "\n".join(lines) + "\n"
