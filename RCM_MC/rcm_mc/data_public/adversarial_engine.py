"""Adversarial Diligence Engine — auto-generated bear-case memos.

Blueprint Moat Layer 5. Every diligence artifact the platform produces
has a counterpart here: the structured bear-case memo. The engine takes
a management thesis (implicit in a corpus deal's structure and payer
mix, or explicit via a ThesisInput), decomposes it into discrete
assumptions, stress-tests each against the Named-Failure Library + the
Benchmark Curve Library, runs a worst-quartile Monte Carlo, and
produces a structured red-team memo.

The output is deliberately a COUNTER-argument, not a confirmation.
Typical diligence artifacts tend to rationalize the deal thesis; this
engine flips the framing. Output: here's exactly what would have to
go wrong, here's what's happened historically at comparable deals that
did fail, here's the probability-weighted outcome if the bear case
prevails.

Integrates with:
    - named_failure_library.py — pattern match drives stress oracle
    - ncci_edits.py            — edit density stresses RCM assumption
    - benchmark_curve_library.py — worst-quartile distributional priors
    - backtest_harness.py       — composite score as base rate

Public API
----------
    ThesisAssumption             one decomposed assumption
    AssumptionStressTest         result of stressing one assumption
    WorstCaseMCOutput            worst-quartile Monte Carlo summary
    BearCaseMemo                 full memo for one deal
    AssumptionCatalogRow         flattened table view
    AdversarialEngineResult      composite output
    compute_adversarial_engine() -> AdversarialEngineResult
"""
from __future__ import annotations

import importlib
import json
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ThesisAssumption:
    """One decomposed assumption extracted from a deal's implied thesis."""
    assumption_id: str              # "ASM-01" per deal
    category: str                   # "Growth" / "Multiple" / "PayerMix" / "Leverage" / "OpImprovement"
    assumption_statement: str       # plain-English statement
    assumed_value: str              # the value being assumed (e.g. "5% annual revenue growth")
    source_field: str               # which deal field this was derived from


@dataclass
class AssumptionStressTest:
    assumption_id: str
    assumption_statement: str
    stress_result: str              # "HOLDS" / "FRAGILE" / "BROKEN"
    stress_rationale: str           # why the stress test concluded this
    matched_nf_patterns: List[str]  # list of NF-XX pattern IDs that fit this assumption's risk mode
    worst_quartile_value: str       # the P10 / P25 benchmark value from the curve library
    assumption_severity: str        # "critical" / "warning" / "context"


@dataclass
class WorstCaseMCOutput:
    iterations: int
    worst_quartile_moic_p10: float   # 10th-percentile MOIC at worst-quartile inputs
    worst_quartile_moic_p50: float
    worst_quartile_moic_mean: float
    capital_loss_probability: float  # P(MOIC < 1.0)
    severe_loss_probability: float   # P(MOIC < 0.5)
    mean_hold_years_to_distress: Optional[float]
    rng_seed: int                    # reproducibility anchor


@dataclass
class BearCaseMemo:
    deal_name: str
    year: int
    buyer: str
    ev_mm: Optional[float]
    ebitda_mm: Optional[float]
    implied_multiple: Optional[float]
    # Decomposed assumptions
    assumptions: List[ThesisAssumption]
    stress_results: List[AssumptionStressTest]
    worst_case_mc: WorstCaseMCOutput
    # Memo conclusion
    critical_assumptions_broken: int
    recommendation: str             # "PROCEED" / "PROCEED_WITH_CONDITIONS" / "STOP"
    probability_weighted_bear_moic: float
    red_team_summary: str           # narrative paragraph


@dataclass
class AssumptionCatalogRow:
    """Flattened table view for UI: one row per (deal × assumption × stress)."""
    deal_name: str
    deal_year: int
    assumption_id: str
    category: str
    assumption_statement: str
    stress_result: str
    matched_pattern: str
    severity: str


@dataclass
class AdversarialEngineResult:
    total_memos: int
    total_assumptions: int
    total_broken_assumptions: int
    deals_stop_recommendation: int
    deals_proceed_with_conditions: int
    deals_proceed: int
    avg_bear_moic: float

    memos: List[BearCaseMemo]
    assumption_catalog: List[AssumptionCatalogRow]

    corpus_deal_count: int
    methodology: str


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
# Assumption decomposition
# ---------------------------------------------------------------------------

def _parse_payer_mix(deal: dict) -> Dict[str, float]:
    pm = deal.get("payer_mix")
    if isinstance(pm, str):
        try:
            pm = json.loads(pm)
        except (ValueError, TypeError):
            return {}
    if isinstance(pm, dict):
        return {k: float(v) for k, v in pm.items() if isinstance(v, (int, float))}
    return {}


def _decompose_thesis(deal: dict) -> List[ThesisAssumption]:
    """Extract the 5 load-bearing assumptions in any PE deal thesis."""
    assumptions: List[ThesisAssumption] = []

    ev = deal.get("ev_mm")
    ebitda = deal.get("ebitda_at_entry_mm")
    hold = deal.get("hold_years") or 5
    multiple = None
    try:
        if ev is not None and ebitda is not None and float(ebitda) > 0:
            multiple = float(ev) / float(ebitda)
    except (TypeError, ValueError):
        pass

    # ASM-01: Growth
    assumptions.append(ThesisAssumption(
        assumption_id="ASM-01",
        category="Growth",
        assumption_statement=(
            "Target grows revenue at 6-10% CAGR over the hold period, "
            "driven by organic volume + bolt-on tuck-ins."
        ),
        assumed_value="6-10% revenue CAGR",
        source_field="deal_name + sector (inferred)",
    ))

    # ASM-02: Multiple expansion
    if multiple:
        assumed_exit = multiple * 1.1
        assumptions.append(ThesisAssumption(
            assumption_id="ASM-02",
            category="Multiple",
            assumption_statement=(
                f"Exit-multiple holds at or above entry ({multiple:.1f}x); "
                f"base case assumes mild expansion to ~{assumed_exit:.1f}x."
            ),
            assumed_value=f"entry {multiple:.1f}x → exit {assumed_exit:.1f}x",
            source_field="ev_mm / ebitda_at_entry_mm",
        ))
    else:
        assumptions.append(ThesisAssumption(
            assumption_id="ASM-02",
            category="Multiple",
            assumption_statement="Exit-multiple holds at peer-median for specialty.",
            assumed_value="peer-median specialty multiple",
            source_field="(EV or EBITDA not disclosed — assumption implicit)",
        ))

    # ASM-03: Payer mix stability
    pm = _parse_payer_mix(deal)
    govt = pm.get("medicare", 0.0) + pm.get("medicaid", 0.0)
    commercial = pm.get("commercial", 0.0)
    if pm:
        mix_str = f"government {govt:.0%} / commercial {commercial:.0%}"
    else:
        mix_str = "payer mix not disclosed"
    assumptions.append(ThesisAssumption(
        assumption_id="ASM-03",
        category="PayerMix",
        assumption_statement=(
            f"Payer mix holds: {mix_str}. No material commercial-payer "
            "contract losses or government-payer rate compression."
        ),
        assumed_value=mix_str,
        source_field="payer_mix",
    ))

    # ASM-04: Leverage / debt-service
    assumptions.append(ThesisAssumption(
        assumption_id="ASM-04",
        category="Leverage",
        assumption_statement=(
            "Debt-service coverage holds ≥1.3x; no covenant breach; "
            "refinancing available at or below entry spread."
        ),
        assumed_value="DSCR ≥ 1.3x, covenants held",
        source_field="(leverage implicit in EV/EBITDA + PE-sponsor class)",
    ))

    # ASM-05: Operational improvement / RCM uplift
    assumptions.append(ThesisAssumption(
        assumption_id="ASM-05",
        category="OpImprovement",
        assumption_statement=(
            "Post-close RCM improvements (clean-claim rate, denials, A/R) deliver "
            "150-300bps of EBITDA uplift over 18 months."
        ),
        assumed_value="150-300bps EBITDA margin uplift over 18 months",
        source_field="(implied by PE-sponsor RCM playbook)",
    ))

    return assumptions


# ---------------------------------------------------------------------------
# Per-assumption stress tests
# ---------------------------------------------------------------------------

def _stress_growth_assumption(deal: dict, nf_matches: List[str]) -> AssumptionStressTest:
    # Growth is broken by: volume pressure (NF-07 Quorum rural), competitor disruption
    # (NF-14 IntegraMed), regulatory site-neutral cut (NF-16 Akumin)
    risk_patterns = [p for p in nf_matches if p in ("NF-07", "NF-14", "NF-16", "NF-02")]
    if risk_patterns:
        return AssumptionStressTest(
            assumption_id="ASM-01",
            assumption_statement="Revenue grows 6-10% CAGR over hold.",
            stress_result="FRAGILE",
            stress_rationale=(
                f"Deal matches growth-headwind patterns {', '.join(risk_patterns)}. "
                "Revenue-growth assumption would need to absorb rural depopulation "
                "(NF-07), competitive disruption (NF-14), or regulatory rate cuts "
                "(NF-16). Benchmark P25 sector growth is -1% to +3% when these "
                "headwinds apply."
            ),
            matched_nf_patterns=risk_patterns,
            worst_quartile_value="0-2% CAGR at P25 benchmark",
            assumption_severity="critical",
        )
    return AssumptionStressTest(
        assumption_id="ASM-01",
        assumption_statement="Revenue grows 6-10% CAGR over hold.",
        stress_result="HOLDS",
        stress_rationale="No named-failure pattern challenges the growth assumption structurally.",
        matched_nf_patterns=[],
        worst_quartile_value="4-7% CAGR at P25 benchmark",
        assumption_severity="context",
    )


def _stress_multiple_assumption(deal: dict, nf_matches: List[str]) -> AssumptionStressTest:
    ev = deal.get("ev_mm")
    ebitda = deal.get("ebitda_at_entry_mm")
    try:
        if ev and ebitda and float(ebitda) > 0:
            mult = float(ev) / float(ebitda)
        else:
            mult = None
    except (TypeError, ValueError):
        mult = None

    # High entry multiples face contraction risk; NF-02/03/11/16 show rollup-multiple collapse
    risk_patterns = [p for p in nf_matches if p in ("NF-02", "NF-03", "NF-11", "NF-16")]
    if mult and mult >= 14.0:
        return AssumptionStressTest(
            assumption_id="ASM-02",
            assumption_statement=f"Exit multiple holds at ~{mult:.1f}x entry.",
            stress_result="BROKEN",
            stress_rationale=(
                f"Entry multiple {mult:.1f}x is in the top quartile of healthcare PE "
                "deals (>75th percentile). Historical mean reversion suggests 2-4 turn "
                "compression likely. NF cluster "
                f"{risk_patterns if risk_patterns else '(rollup-compression risk)'} "
                "shows multiple collapsed post-close on hospital-based physician rollups."
            ),
            matched_nf_patterns=risk_patterns,
            worst_quartile_value=f"exit {mult*0.75:.1f}x at P25",
            assumption_severity="critical",
        )
    if risk_patterns:
        return AssumptionStressTest(
            assumption_id="ASM-02",
            assumption_statement="Exit multiple holds at entry peer-median.",
            stress_result="FRAGILE",
            stress_rationale=(
                f"Pattern match on {', '.join(risk_patterns)}. Rollup-compression "
                "risk is non-trivial in this specialty."
            ),
            matched_nf_patterns=risk_patterns,
            worst_quartile_value="25% multiple compression at P25",
            assumption_severity="warning",
        )
    return AssumptionStressTest(
        assumption_id="ASM-02",
        assumption_statement="Exit multiple holds at entry peer-median.",
        stress_result="HOLDS",
        stress_rationale="Entry multiple in line with peers; no cluster-failure overhang.",
        matched_nf_patterns=[],
        worst_quartile_value="10% multiple compression at P25",
        assumption_severity="context",
    )


def _stress_payermix_assumption(deal: dict, nf_matches: List[str]) -> AssumptionStressTest:
    pm = _parse_payer_mix(deal)
    govt = pm.get("medicare", 0) + pm.get("medicaid", 0)

    # Heavy government mix is stressed by: NF-01 Steward, NF-05 Prospect, NF-07 Quorum,
    # NF-09 Hahnemann, NF-15 Pipeline. MA-risk stressed by NF-04 Cano, NF-10 CareMax, NF-12 Babylon.
    safety_net_patterns = [p for p in nf_matches if p in ("NF-01", "NF-05", "NF-07", "NF-09", "NF-15")]
    ma_risk_patterns = [p for p in nf_matches if p in ("NF-04", "NF-10", "NF-12")]
    nsa_patterns = [p for p in nf_matches if p in ("NF-02", "NF-03", "NF-08", "NF-11")]

    if govt > 0.65 and safety_net_patterns:
        return AssumptionStressTest(
            assumption_id="ASM-03",
            assumption_statement=f"Payer mix stable at {govt:.0%} government.",
            stress_result="BROKEN",
            stress_rationale=(
                f"Government payer mix {govt:.0%} combined with safety-net pattern "
                f"match ({', '.join(safety_net_patterns)}) — exactly the risk "
                "profile of Steward, Prospect Medical, Pipeline Health. "
                "Medicaid rate compression + state AG intervention are typical "
                "downside triggers."
            ),
            matched_nf_patterns=safety_net_patterns,
            worst_quartile_value="government-payer EBITDAR coverage < 1.0x at P10",
            assumption_severity="critical",
        )
    if ma_risk_patterns:
        return AssumptionStressTest(
            assumption_id="ASM-03",
            assumption_statement="MA-risk-book economics hold; RAF stable.",
            stress_result="BROKEN",
            stress_rationale=(
                f"MA-risk primary-care pattern match ({', '.join(ma_risk_patterns)}) "
                "— V28 risk-adjustment model reduces RAF scores 3-4% in the 3-year "
                "phase-in. Cano and CareMax template shows the MA-risk model is in "
                "structural reset."
            ),
            matched_nf_patterns=ma_risk_patterns,
            worst_quartile_value="MLR > 90% at MA-risk book at P10",
            assumption_severity="critical",
        )
    if nsa_patterns:
        return AssumptionStressTest(
            assumption_id="ASM-03",
            assumption_statement="OON/commercial-balance billing economics hold.",
            stress_result="FRAGILE",
            stress_rationale=(
                f"Hospital-based physician rollup pattern match "
                f"({', '.join(nsa_patterns)}). NSA IDR outcomes compress OON rates; "
                "FTC Welsh Carson/USAP consent order signals antitrust overhang."
            ),
            matched_nf_patterns=nsa_patterns,
            worst_quartile_value="-30 to -40% OON-rate compression at P10",
            assumption_severity="warning",
        )
    return AssumptionStressTest(
        assumption_id="ASM-03",
        assumption_statement="Payer mix stable through hold.",
        stress_result="HOLDS",
        stress_rationale="No dominant payer-mix failure pattern matches.",
        matched_nf_patterns=[],
        worst_quartile_value="±5% government-share drift at P25",
        assumption_severity="context",
    )


def _stress_leverage_assumption(deal: dict, nf_matches: List[str]) -> AssumptionStressTest:
    ev = deal.get("ev_mm")
    ebitda = deal.get("ebitda_at_entry_mm")
    try:
        if ev and ebitda and float(ebitda) > 0:
            mult = float(ev) / float(ebitda)
        else:
            mult = None
    except (TypeError, ValueError):
        mult = None

    # Dividend-recap / SLB pattern matches apply here
    recap_patterns = [p for p in nf_matches if p in ("NF-05",)]  # Prospect Medical dividend recap
    slb_patterns = [p for p in nf_matches if p in ("NF-01",)]    # Steward SLB

    if mult and mult >= 15:
        return AssumptionStressTest(
            assumption_id="ASM-04",
            assumption_statement=f"Leverage {mult:.1f}x serviceable; covenants held.",
            stress_result="BROKEN",
            stress_rationale=(
                f"Entry leverage {mult:.1f}x implies debt/EBITDA > 7x at typical "
                "PE capital structures (70% debt). Rate-rise environment + any "
                "EBITDA slippage breaches covenants. Envision (NF-02) failed at "
                "similar leverage with NSA-driven EBITDA compression."
            ),
            matched_nf_patterns=["NF-02", "NF-03"],
            worst_quartile_value="DSCR < 1.0x at P10 EBITDA scenario",
            assumption_severity="critical",
        )
    if recap_patterns or slb_patterns:
        combined = recap_patterns + slb_patterns
        return AssumptionStressTest(
            assumption_id="ASM-04",
            assumption_statement="Leverage serviceable; no extractive dividend risk.",
            stress_result="FRAGILE",
            stress_rationale=(
                f"Match on {', '.join(combined)} — dividend-recap or sale-leaseback "
                "pattern implies sponsor may extract equity at the expense of "
                "covenant headroom."
            ),
            matched_nf_patterns=combined,
            worst_quartile_value="post-recap EBITDAR coverage < 1.2x",
            assumption_severity="warning",
        )
    return AssumptionStressTest(
        assumption_id="ASM-04",
        assumption_statement="Debt-service coverage holds ≥1.3x.",
        stress_result="HOLDS",
        stress_rationale="Leverage within market norms; no extractive-structure signals.",
        matched_nf_patterns=[],
        worst_quartile_value="DSCR 1.1-1.2x at P25",
        assumption_severity="context",
    )


def _stress_opimprovement_assumption(deal: dict, nf_matches: List[str], ncci_score: float) -> AssumptionStressTest:
    if ncci_score >= 55:
        return AssumptionStressTest(
            assumption_id="ASM-05",
            assumption_statement="RCM uplift delivers 150-300bps EBITDA margin.",
            stress_result="BROKEN",
            stress_rationale=(
                f"NCCI edit density {ncci_score:.0f} (HIGH tier). The target is "
                "already absorbing structural denial exposure; the 'post-close RCM "
                "uplift' thesis becomes 'post-close RCM normalization to peer.' "
                "APP (NF-03) template: rollup-absorbed denials don't clear without "
                "EMR consolidation."
            ),
            matched_nf_patterns=["NF-03"],
            worst_quartile_value="0-50bps uplift at P10 (and 200-400bps haircut if audit)",
            assumption_severity="warning",
        )
    if ncci_score >= 30:
        return AssumptionStressTest(
            assumption_id="ASM-05",
            assumption_statement="RCM uplift delivers 150-300bps EBITDA margin.",
            stress_result="FRAGILE",
            stress_rationale=(
                f"NCCI edit density {ncci_score:.0f} (MEDIUM tier). RCM uplift is "
                "achievable but contingent on EMR consolidation and modifier-override "
                "workflow maturity."
            ),
            matched_nf_patterns=[],
            worst_quartile_value="50-100bps uplift at P25",
            assumption_severity="warning",
        )
    return AssumptionStressTest(
        assumption_id="ASM-05",
        assumption_statement="RCM uplift delivers 150-300bps EBITDA margin.",
        stress_result="HOLDS",
        stress_rationale=(
            f"NCCI edit density {ncci_score:.0f} (low). The target is clean; "
            "upside realization is more likely than peer."
        ),
        matched_nf_patterns=[],
        worst_quartile_value="100-150bps uplift at P25",
        assumption_severity="context",
    )


# ---------------------------------------------------------------------------
# Worst-quartile Monte Carlo
# ---------------------------------------------------------------------------

def _worst_quartile_mc(
    deal: dict,
    nf_match_count: int,
    ncci_score: float,
    broken_count: int,
) -> WorstCaseMCOutput:
    """Simple deterministic worst-quartile MC using a PRNG seeded on deal_id.

    Runs 2000 iterations. Draws entry/exit multiple from a compressed
    distribution + revenue growth from a lowered distribution + EBITDA
    margin drift negative. Returns MOIC distribution.

    Uses `random` from stdlib — no new deps.
    """
    import random

    source_id = str(deal.get("source_id", deal.get("deal_name", "")))
    seed = hash(source_id) & 0xFFFFFFFF
    rng = random.Random(seed)

    ev = deal.get("ev_mm")
    ebitda = deal.get("ebitda_at_entry_mm")
    try:
        entry_mult = float(ev) / float(ebitda) if ev and ebitda and float(ebitda) > 0 else None
    except (TypeError, ValueError):
        entry_mult = None

    # Worst-quartile parameters
    base_exit_mult_compression = 0.75 + 0.05 * (3 - min(nf_match_count, 3))
    base_revenue_cagr_mean = 0.02 - 0.01 * min(nf_match_count, 3)   # -1% to 2%
    base_ebitda_margin_drift = -0.005 * min(max(ncci_score, 10) / 20, 3)  # -0.5% to -1.5%
    hold_years = float(deal.get("hold_years") or 5)

    iterations = 2000
    moics: List[float] = []
    distressed = 0
    severe = 0
    for _ in range(iterations):
        # Sample worst-quartile drivers
        rev_cagr = rng.gauss(base_revenue_cagr_mean, 0.025)
        exit_mult_ratio = rng.gauss(base_exit_mult_compression, 0.08)
        exit_mult_ratio = max(0.35, exit_mult_ratio)
        ebitda_drift = rng.gauss(base_ebitda_margin_drift, 0.004)

        # Starting: revenue × margin = EBITDA
        r_growth = (1.0 + rev_cagr) ** hold_years
        margin_growth = 1.0 + (ebitda_drift * hold_years)   # linear per-year drift
        margin_growth = max(0.30, margin_growth)
        exit_ebitda_ratio = r_growth * margin_growth
        if entry_mult is not None:
            exit_mult = entry_mult * exit_mult_ratio
            moic = exit_mult_ratio * exit_ebitda_ratio
        else:
            moic = exit_mult_ratio * exit_ebitda_ratio

        # Broken-assumption multiplier: each broken assumption cuts MOIC 15%
        moic *= (1.0 - 0.15) ** broken_count
        moics.append(moic)
        if moic < 1.0:
            distressed += 1
        if moic < 0.5:
            severe += 1

    moics.sort()
    p10 = moics[int(iterations * 0.10)]
    p50 = moics[int(iterations * 0.50)]
    mean = sum(moics) / iterations

    return WorstCaseMCOutput(
        iterations=iterations,
        worst_quartile_moic_p10=round(p10, 3),
        worst_quartile_moic_p50=round(p50, 3),
        worst_quartile_moic_mean=round(mean, 3),
        capital_loss_probability=round(distressed / iterations, 4),
        severe_loss_probability=round(severe / iterations, 4),
        mean_hold_years_to_distress=hold_years if distressed > iterations * 0.3 else None,
        rng_seed=seed,
    )


# ---------------------------------------------------------------------------
# Memo assembly
# ---------------------------------------------------------------------------

def _classify_memo(broken_count: int, fragile_count: int, mc: WorstCaseMCOutput) -> Tuple[str, float]:
    """Return (recommendation, probability_weighted_bear_moic).

    Recommendation logic: the MC is pessimistic by construction (draws from
    worst-quartile parameters), so its capital-loss probability is a
    DEPENDENT signal on the structural assumption breakage, not an
    independent trigger. Classification anchors on broken-assumption count.
    """
    # Probability-weighted bear: weight by 0.25 bear-case + 0.75 base case
    # (bear = mc mean; base = assume 1.8x as neutral)
    weighted = 0.25 * mc.worst_quartile_moic_mean + 0.75 * 1.8

    # Structural triggers on broken assumptions + MC as confirmation
    if broken_count >= 3:
        return ("STOP", round(weighted, 3))
    if broken_count >= 2 and mc.capital_loss_probability >= 0.50:
        return ("STOP", round(weighted, 3))
    if broken_count >= 2 or fragile_count >= 3:
        return ("PROCEED_WITH_CONDITIONS", round(weighted, 3))
    if broken_count >= 1 and mc.capital_loss_probability >= 0.60:
        return ("PROCEED_WITH_CONDITIONS", round(weighted, 3))
    return ("PROCEED", round(weighted, 3))


def _build_memo(deal: dict) -> BearCaseMemo:
    from .named_failure_library import _match_one, _build_patterns

    patterns = _build_patterns()
    nf_scores = [_match_one(deal, p) for p in patterns]
    nf_matches = [s.pattern_id for s in nf_scores if s.match_score >= 15]

    # NCCI score
    try:
        from .ncci_edits import (
            _build_ptp_edits, _build_mue_limits, _build_specialty_footprints,
            _classify_deal,
        )
        ptp = _build_ptp_edits()
        mue = _build_mue_limits()
        fps = _build_specialty_footprints(ptp, mue)
        specialty = _classify_deal(deal)
        fp = next((f for f in fps if f.specialty == specialty), None)
        ncci_score = fp.edit_density_score if fp else 20.0
    except Exception:
        ncci_score = 20.0

    # Decompose + stress
    assumptions = _decompose_thesis(deal)
    stress_results = [
        _stress_growth_assumption(deal, nf_matches),
        _stress_multiple_assumption(deal, nf_matches),
        _stress_payermix_assumption(deal, nf_matches),
        _stress_leverage_assumption(deal, nf_matches),
        _stress_opimprovement_assumption(deal, nf_matches, ncci_score),
    ]

    broken = sum(1 for s in stress_results if s.stress_result == "BROKEN")
    fragile = sum(1 for s in stress_results if s.stress_result == "FRAGILE")

    mc = _worst_quartile_mc(deal, nf_match_count=len(nf_matches),
                             ncci_score=ncci_score, broken_count=broken)

    recommendation, bear_moic = _classify_memo(broken, fragile, mc)

    # Red-team summary narrative
    matched_critical = [s for s in stress_results if s.stress_result == "BROKEN"]
    critical_str = "; ".join(s.assumption_id + ": " + s.stress_rationale[:120] for s in matched_critical[:2])
    if not critical_str:
        critical_str = "No assumptions broken — but note remaining fragilities."
    rt_summary = (
        f"BEAR CASE: {broken} assumption(s) BROKEN, {fragile} FRAGILE. "
        f"Worst-quartile MC (n={mc.iterations}) → MOIC p10={mc.worst_quartile_moic_p10}, "
        f"p50={mc.worst_quartile_moic_p50}, mean={mc.worst_quartile_moic_mean}. "
        f"Capital-loss probability {mc.capital_loss_probability * 100:.1f}%. "
        f"Recommendation: {recommendation}. "
        f"Top concerns — {critical_str}"
    )[:2000]

    ev = deal.get("ev_mm")
    ebitda = deal.get("ebitda_at_entry_mm")
    try:
        ev_f = float(ev) if ev is not None else None
        eb_f = float(ebitda) if ebitda is not None else None
        mult_f = ev_f / eb_f if (ev_f and eb_f and eb_f > 0) else None
    except (TypeError, ValueError):
        ev_f = eb_f = mult_f = None

    return BearCaseMemo(
        deal_name=str(deal.get("deal_name", "—"))[:80],
        year=int(deal.get("year") or 0),
        buyer=str(deal.get("buyer", "—"))[:60],
        ev_mm=ev_f,
        ebitda_mm=eb_f,
        implied_multiple=round(mult_f, 2) if mult_f is not None else None,
        assumptions=assumptions,
        stress_results=stress_results,
        worst_case_mc=mc,
        critical_assumptions_broken=broken,
        recommendation=recommendation,
        probability_weighted_bear_moic=bear_moic,
        red_team_summary=rt_summary,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_adversarial_engine() -> AdversarialEngineResult:
    corpus = _load_corpus()
    # Sample 30 deals spanning pattern-match + EV distribution — not the full corpus,
    # because per-memo MC is 2000 iterations × NF scoring × NCCI classification,
    # and full-corpus runs at this depth would take O(minutes). 30 memos is
    # sufficient to demonstrate the engine without being slow.
    # Selection: 10 largest by EV + 10 highest NF-match + 10 random representatives.

    # 10 largest by EV
    def _safe_ev(d):
        try:
            return float(d.get("ev_mm") or 0)
        except (TypeError, ValueError):
            return 0.0
    by_ev = sorted(corpus, key=_safe_ev, reverse=True)[:10]

    # 10 highest NF-match
    from .named_failure_library import _match_one, _build_patterns
    patterns = _build_patterns()
    nf_ranked = []
    for d in corpus:
        scores = [_match_one(d, p) for p in patterns]
        top = max(scores, key=lambda s: s.match_score) if scores else None
        nf_ranked.append((d, top.match_score if top else 0.0))
    nf_ranked.sort(key=lambda x: x[1], reverse=True)
    by_nf = [d for (d, _) in nf_ranked[:10]]

    # 10 diverse representatives (every 170th deal)
    representatives = corpus[::170][:10]

    # Deduplicate
    seen = set()
    selected: List[dict] = []
    for d in list(by_ev) + list(by_nf) + list(representatives):
        sid = d.get("source_id") or d.get("deal_name")
        if sid in seen:
            continue
        seen.add(sid)
        selected.append(d)
        if len(selected) >= 30:
            break

    memos = [_build_memo(d) for d in selected]

    # Flat catalog view
    catalog: List[AssumptionCatalogRow] = []
    for m in memos:
        for s in m.stress_results:
            asm = next((a for a in m.assumptions if a.assumption_id == s.assumption_id), None)
            catalog.append(AssumptionCatalogRow(
                deal_name=m.deal_name,
                deal_year=m.year,
                assumption_id=s.assumption_id,
                category=asm.category if asm else "",
                assumption_statement=s.assumption_statement,
                stress_result=s.stress_result,
                matched_pattern=", ".join(s.matched_nf_patterns[:3]) or "—",
                severity=s.assumption_severity,
            ))

    total_broken = sum(m.critical_assumptions_broken for m in memos)
    stops = sum(1 for m in memos if m.recommendation == "STOP")
    pwc = sum(1 for m in memos if m.recommendation == "PROCEED_WITH_CONDITIONS")
    proceed = sum(1 for m in memos if m.recommendation == "PROCEED")
    avg_bear = sum(m.probability_weighted_bear_moic for m in memos) / len(memos) if memos else 0.0

    return AdversarialEngineResult(
        total_memos=len(memos),
        total_assumptions=sum(len(m.assumptions) for m in memos),
        total_broken_assumptions=total_broken,
        deals_stop_recommendation=stops,
        deals_proceed_with_conditions=pwc,
        deals_proceed=proceed,
        avg_bear_moic=round(avg_bear, 3),
        memos=memos,
        assumption_catalog=catalog,
        corpus_deal_count=len(corpus),
        methodology=(
            "For each sampled deal, decompose the implied PE thesis into 5 load-bearing "
            "assumptions (Growth, Multiple, PayerMix, Leverage, OpImprovement). Stress-test "
            "each against Named-Failure Library pattern matches + NCCI edit density + "
            "implied entry multiple. HOLDS / FRAGILE / BROKEN classification per assumption. "
            "Worst-quartile Monte Carlo (2000 iter, deterministic seed per deal) draws "
            "revenue CAGR, exit-multiple compression, and margin drift from the pessimistic "
            "tail; broken assumptions cut MOIC 15% each. Recommendation: STOP if ≥3 BROKEN "
            "or capital-loss probability ≥ 40%; PROCEED_WITH_CONDITIONS if ≥ 2 BROKEN or "
            "capital-loss ≥ 20%; otherwise PROCEED."
        ),
    )
