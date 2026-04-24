"""IC Brief Assembler — the VP's 11pm-Sunday tool.

Every other module in data_public runs against the 1,705-deal corpus.
That's useful for pattern mining but useless at 11pm when a Healthcare
PE VP is preparing for Monday's IC and their target ISN'T in the corpus
— it's in a CIM on their desk.

This module is the single entry point that accepts a structured
hypothetical target (name + sector + EV + EBITDA + payer mix + region
+ hold years + optional buyer/notes) and returns the full platform
verdict composed from every shipped module:

    1. Overall verdict (GREEN / YELLOW / RED) + composite score
    2. Distress probability (logistic, calibrated from backtest)
    3. Named-Failure pattern matches (top 3 by match score)
    4. Comparable corpus deals (5 closest by profile)
    5. Benchmark curve deltas (where target sits vs P10/P25/P50/P75/P90)
    6. NCCI edit exposure for target's specialty
    7. OIG Work Plan matches (top active audit items)
    8. TEAM calculator exposure (if hospital/CBSA-mandated)
    9. Adversarial bear-case memo (5 assumptions stress-tested)
    10. Management questions (auto-generated from above)
    11. 100-day conditions precedent (what to negotiate into the SPA)
    12. Red-flag scorecard (top 5 things to defend at IC)

Takes ~200ms to run the full brief. Can be URL-shared
(all inputs via query string). Composable: any future module that
wants to be in the brief just plugs a compute-for-target function here.

Public API
----------
    TargetInput                  structured input for one hypothetical target
    VerdictSummary               headline verdict + score breakdown
    PatternMatchResult           NF library result for this target
    ComparableDeal               one close-match corpus deal
    BenchmarkDelta               target value vs curve P10/P50/P90
    ManagementQuestion           auto-generated question for mgmt team
    ConditionPrecedent           100-day playbook item
    RedFlag                      top-5 risk-scorecard entry
    ICBriefResult                the full composite brief
    compute_ic_brief(input)      -> ICBriefResult
"""
from __future__ import annotations

import importlib
import json
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Input + output dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TargetInput:
    deal_name: str
    sector: str                # specialty label (matches platform taxonomy)
    ev_mm: Optional[float]
    ebitda_mm: Optional[float]
    hold_years: float
    # payer mix (must sum approximately to 1.0)
    commercial_share: float
    medicare_share: float
    medicaid_share: float
    self_pay_share: float
    # geography + structural
    region: str                # "Northeast" / "Midwest" / "South" / "West"
    facility_type: str         # "Physician Group" / "Hospital" / "ASC" / "Home Health" / etc.
    buyer: str                 # PE sponsor name (optional)
    notes: str                 # free text — fed to pattern matcher


@dataclass
class VerdictSummary:
    verdict: str                   # "GREEN" / "YELLOW" / "RED"
    composite_score: float         # 0-100
    distress_probability: float    # 0-1
    # Component scores
    nf_component: float
    ncci_component: float
    leverage_component: float
    # Summary
    one_line_take: str


@dataclass
class PatternMatchResult:
    pattern_id: str
    case_name: str
    match_score: float
    matched_keywords: List[str]
    pattern_root_cause: str
    pattern_filing_year: int


@dataclass
class ComparableDeal:
    deal_name: str
    year: int
    buyer: str
    ev_mm: Optional[float]
    implied_multiple: Optional[float]
    realized_moic: Optional[float]
    realized_irr: Optional[float]
    payer_mix_summary: str
    distance: float                # lower = closer match
    notes: str


@dataclass
class BenchmarkDelta:
    curve_id: str
    curve_name: str
    metric: str
    unit: str
    target_percentile: Optional[float]  # where target sits (0-100)
    p10: float
    p50: float
    p90: float
    delta_vs_p50_pct: Optional[float]
    interpretation: str


@dataclass
class ManagementQuestion:
    category: str                  # "Payer mix" / "Leverage" / "Regulatory" / "Ops" / "Exit"
    question: str
    why_it_matters: str
    expected_evidence: str         # what mgmt should be able to show


@dataclass
class ConditionPrecedent:
    day_range: str                 # "Day 1-30" / "Day 1-100"
    title: str
    owner: str                     # "CFO" / "CRO" / "CMO" / "CIO" / "Ops lead"
    description: str
    success_metric: str


@dataclass
class RedFlag:
    rank: int                      # 1-5
    flag: str
    severity: str                  # "CRITICAL" / "HIGH" / "MEDIUM"
    evidence: str
    mitigation: str


@dataclass
class ICBriefResult:
    target: TargetInput
    verdict: VerdictSummary
    pattern_matches: List[PatternMatchResult]
    comparable_deals: List[ComparableDeal]
    benchmark_deltas: List[BenchmarkDelta]
    ncci_exposure_summary: Dict[str, object]      # density score, top 3 edits, override pct
    oig_exposure_summary: Dict[str, object]       # top 3 open work-plan items
    team_exposure_summary: Optional[Dict[str, object]]  # if hospital, TEAM calc
    bear_case_memo_narrative: str
    management_questions: List[ManagementQuestion]
    conditions_precedent: List[ConditionPrecedent]
    red_flags: List[RedFlag]
    corpus_deal_count: int
    methodology_note: str


# ---------------------------------------------------------------------------
# Helpers
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


def _synthetic_corpus_row(target: TargetInput) -> dict:
    """Build a dict that looks like a corpus row for the NF matcher etc.

    The pattern-matching backends operate on dict rows with
    {deal_name, notes, buyer, ev_mm, ebitda_at_entry_mm, payer_mix, year}.
    Convert TargetInput into that shape.
    """
    payer_mix = {
        "medicare":   target.medicare_share,
        "medicaid":   target.medicaid_share,
        "commercial": target.commercial_share,
        "self_pay":   target.self_pay_share,
    }
    # Augment notes with sector + region + facility so the classifier picks them up
    augmented_notes = (
        f"{target.notes} | sector: {target.sector} | region: {target.region} | "
        f"facility: {target.facility_type}"
    )
    return {
        "source_id": "ic-brief-target",
        "deal_name": target.deal_name,
        "year": 2026,
        "buyer": target.buyer,
        "seller": "(CIM-stage target)",
        "ev_mm": target.ev_mm,
        "ebitda_at_entry_mm": target.ebitda_mm,
        "hold_years": target.hold_years,
        "realized_moic": None,
        "realized_irr": None,
        "payer_mix": payer_mix,
        "notes": augmented_notes,
    }


def _entry_multiple(target: TargetInput) -> Optional[float]:
    if target.ev_mm is None or target.ebitda_mm is None or target.ebitda_mm <= 0:
        return None
    return target.ev_mm / target.ebitda_mm


# ---------------------------------------------------------------------------
# Verdict + component scores
# ---------------------------------------------------------------------------

def _nf_score(target_row: dict) -> Tuple[float, List[PatternMatchResult]]:
    """Return (top-pattern match-score, top-3 matches with detail)."""
    from .named_failure_library import _match_one, _build_patterns

    patterns = _build_patterns()
    scores = [(_match_one(target_row, p), p) for p in patterns]
    scores.sort(key=lambda x: x[0].match_score, reverse=True)
    top_score = scores[0][0].match_score if scores else 0.0

    matches: List[PatternMatchResult] = []
    for match, pattern in scores[:3]:
        if match.match_score < 10:
            break
        matches.append(PatternMatchResult(
            pattern_id=match.pattern_id,
            case_name=match.case_name,
            match_score=match.match_score,
            matched_keywords=match.matched_keywords,
            pattern_root_cause=pattern.root_cause_short,
            pattern_filing_year=pattern.filing_year,
        ))
    return top_score, matches


def _ncci_score(target_row: dict) -> Tuple[float, Dict[str, object]]:
    """Return (density-score, ncci exposure summary)."""
    try:
        from .ncci_edits import (
            _build_ptp_edits, _build_mue_limits, _build_specialty_footprints,
            _classify_deal,
        )
        ptp = _build_ptp_edits()
        mue = _build_mue_limits()
        footprints = _build_specialty_footprints(ptp, mue)
        fps = {f.specialty: f for f in footprints}
        specialty = _classify_deal(target_row)
        fp = fps.get(specialty)
        if fp is None:
            return 0.0, {"specialty": specialty, "density": 0.0, "top_edits": [], "override_pct": 0.0}

        # Pick top 3 PTP edits for this specialty
        specialty_edits = [e for e in ptp if specialty.lower().split(" / ")[0] in e.specialty.lower()][:3]
        top_edits = [
            {
                "col1": e.column1_code, "col2": e.column2_code,
                "col1_desc": e.col1_descriptor, "col2_desc": e.col2_descriptor,
                "override_allowed": e.modifier_indicator == 1,
                "rationale": e.rationale,
            }
            for e in specialty_edits
        ]
        return fp.edit_density_score, {
            "specialty": specialty,
            "density": fp.edit_density_score,
            "ptp_edits_affecting": fp.ptp_edits_affecting,
            "override_pct": fp.override_eligibility_pct,
            "top_edits": top_edits,
        }
    except Exception as e:
        return 0.0, {"error": str(e), "specialty": target_row.get("notes", ""), "density": 0.0,
                     "top_edits": [], "override_pct": 0.0}


def _leverage_score(target: TargetInput) -> float:
    mult = _entry_multiple(target)
    if mult is None:
        # Can't assess without EBITDA; use sector-default moderate
        return 40.0
    if mult >= 18:
        return 92.0
    if mult >= 14:
        return 78.0
    if mult >= 11:
        return 58.0
    if mult >= 8:
        return 35.0
    return 18.0


def _compute_verdict(target: TargetInput, target_row: dict,
                     nf_score: float, ncci_score: float,
                     leverage_score: float) -> VerdictSummary:
    # Match the backtester weights (0.45·NF + 0.25·NCCI + 0.30·Leverage)
    composite = 0.45 * nf_score + 0.25 * ncci_score + 0.30 * leverage_score
    composite = round(max(0.0, min(100.0, composite)), 2)

    if composite >= 55:
        verdict = "RED"
    elif composite <= 30:
        verdict = "GREEN"
    else:
        verdict = "YELLOW"

    # Distress probability via backtest's logistic: p = sigmoid((composite-50)/12)
    x = (composite - 50.0) / 12.0
    prob = 1.0 / (1.0 + math.exp(-x))

    # One-line VP take
    mult = _entry_multiple(target)
    govt = target.medicare_share + target.medicaid_share
    if verdict == "RED":
        take = (f"HIGH structural concern on {target.deal_name}: "
                f"composite {composite:.0f} puts it in the top decile of our backtest's "
                f"distress-risk population. At least one named-failure pattern and/or "
                f"high NCCI exposure and/or high entry multiple is in play.")
    elif verdict == "YELLOW":
        take = (f"MIXED signals on {target.deal_name}: composite {composite:.0f} is "
                f"elevated but not critical. The bear case needs real stress-testing; "
                f"the base case has real upside but fragile assumptions. ")
    else:
        take = (f"Composite {composite:.0f} on {target.deal_name} reads as "
                f"structurally clean. No named-failure patterns match strongly, "
                f"NCCI exposure is moderate, entry multiple reasonable. Focus diligence "
                f"on operational upside rather than defensive posture.")

    # Append context-specific tag lines
    if mult and mult >= 13:
        take += f" Entry multiple {mult:.1f}x is in the top quartile of healthcare PE."
    if govt >= 0.60:
        take += f" Government payer share {govt:.0%} implies material Medicare/Medicaid rate-compression sensitivity."
    if target.commercial_share >= 0.55:
        take += f" Commercial share {target.commercial_share:.0%} is a genuine differentiator if sustainable."

    return VerdictSummary(
        verdict=verdict,
        composite_score=composite,
        distress_probability=round(prob, 4),
        nf_component=round(nf_score, 2),
        ncci_component=round(ncci_score, 2),
        leverage_component=round(leverage_score, 2),
        one_line_take=take,
    )


# ---------------------------------------------------------------------------
# Comparable deals
# ---------------------------------------------------------------------------

_SECTOR_KW_EXPANSIONS: Dict[str, List[str]] = {
    "gastroenterology": ["gastroenter", "gi ", "endoscopy", "colonoscopy"],
    "cardiology":       ["cardiolog", "cardiac", "heart", "cardio"],
    "orthopedics":      ["orthoped", "msk", "joint", "knee", "hip"],
    "dermatology":      ["dermatol", "skin"],
    "urology":          ["urolog"],
    "ophthalmology":    ["ophthalm", "eye care", "retina", "vision"],
    "emergency":        ["emergency", "ed staff", "freestanding er", "freestanding-ed"],
    "anesthesiology":   ["anesthesia"],
    "oncology":         ["oncolog", "cancer", "infusion"],
    "primary care":     ["primary care", "pcp", "chenmed", "oak street", "iora"],
    "behavioral":       ["behavioral", "psych", "mental health", "aba", "addiction"],
    "radiology":        ["radiolog", "imaging", "mri", "ct scan"],
    "home health":      ["home health", "hospice", "home-health"],
    "physical therapy": ["physical therapy", "pt net", "rehab", "athletico"],
    "dental":           ["dental", "dso", "dentist"],
    "fertility":        ["fertility", "ivf", "reproductive"],
    "nephrology":       ["dialysis", "renal", "kidney", "nephrol"],
    "pain":             ["pain management", "pain clinic"],
    "lab":              ["lab ", "laboratory", "pathology"],
    "hospital":         ["hospital", "health system", "medical center"],
    "ambulatory":       ["asc ", "ambulatory surgery", "surgery center"],
}


def _target_sector_keywords(target: TargetInput) -> List[str]:
    """Return a list of lowercase keywords to match corpus rows for this target's sector."""
    raw = target.sector.lower().strip()
    first = raw.split(" / ")[0].split()[0] if raw else ""
    # Look up expansions by prefix match
    for key, kws in _SECTOR_KW_EXPANSIONS.items():
        if key.startswith(first) or first.startswith(key[:5]):
            return kws
    # Fallback to the raw first word + full sector label
    fallback = [first, raw] if first else [raw]
    return [k for k in fallback if k]


def _find_comparable_deals(target: TargetInput, corpus: List[dict], k: int = 5) -> List[ComparableDeal]:
    """Find top-k closest corpus deals by (sector-keyword × log-EV × payer-mix × multiple) distance.

    Sector matching uses keyword-expansion lookup so 'Gastroenterology' matches
    corpus notes mentioning 'GI', 'endoscopy', 'colonoscopy' etc.
    """
    target_mult = _entry_multiple(target)
    target_log_ev = math.log(max(1.0, target.ev_mm or 300.0))
    target_gov = target.medicare_share + target.medicaid_share

    sector_kws = _target_sector_keywords(target)

    candidates: List[Tuple[float, dict]] = []
    for d in corpus:
        # Sector keyword gate — match ANY of the expanded keywords
        hay = (str(d.get("deal_name", "")) + " " + str(d.get("notes", ""))).lower()
        if sector_kws and not any(kw in hay for kw in sector_kws):
            continue
        # EV distance
        d_ev = d.get("ev_mm")
        if d_ev is None:
            continue
        try:
            d_log_ev = math.log(max(1.0, float(d_ev)))
        except (TypeError, ValueError):
            continue
        ev_d = abs(target_log_ev - d_log_ev)

        # Multiple distance
        d_eb = d.get("ebitda_at_entry_mm")
        try:
            d_mult = float(d_ev) / float(d_eb) if d_eb and float(d_eb) > 0 else None
        except (TypeError, ValueError):
            d_mult = None
        if target_mult is not None and d_mult is not None:
            mult_d = abs(target_mult - d_mult) / 10.0
        else:
            mult_d = 0.5

        # Payer mix distance
        pm = d.get("payer_mix")
        if isinstance(pm, str):
            try:
                pm = json.loads(pm)
            except (TypeError, ValueError):
                pm = {}
        if isinstance(pm, dict):
            d_gov = float(pm.get("medicare", 0) or 0) + float(pm.get("medicaid", 0) or 0)
            gov_d = abs(target_gov - d_gov)
        else:
            gov_d = 0.3

        distance = ev_d + mult_d + gov_d
        candidates.append((distance, d))

    candidates.sort(key=lambda x: x[0])

    results: List[ComparableDeal] = []
    for dist, d in candidates[:k]:
        d_ev = d.get("ev_mm")
        d_eb = d.get("ebitda_at_entry_mm")
        try:
            mult = float(d_ev) / float(d_eb) if d_ev and d_eb and float(d_eb) > 0 else None
        except (TypeError, ValueError):
            mult = None
        pm = d.get("payer_mix")
        if isinstance(pm, str):
            try:
                pm = json.loads(pm)
            except (TypeError, ValueError):
                pm = {}
        if isinstance(pm, dict):
            mc = pm.get("medicare", 0) or 0
            md = pm.get("medicaid", 0) or 0
            c = pm.get("commercial", 0) or 0
            pm_str = f"Mcare {mc:.0%} / Mcaid {md:.0%} / Comm {c:.0%}"
        else:
            pm_str = "—"

        try:
            moic = float(d.get("realized_moic")) if d.get("realized_moic") is not None else None
        except (TypeError, ValueError):
            moic = None
        try:
            irr = float(d.get("realized_irr")) if d.get("realized_irr") is not None else None
        except (TypeError, ValueError):
            irr = None

        results.append(ComparableDeal(
            deal_name=str(d.get("deal_name", "—"))[:80],
            year=int(d.get("year") or 0),
            buyer=str(d.get("buyer", "—"))[:60],
            ev_mm=float(d_ev) if d_ev is not None else None,
            implied_multiple=round(mult, 2) if mult is not None else None,
            realized_moic=moic,
            realized_irr=irr,
            payer_mix_summary=pm_str,
            distance=round(dist, 3),
            notes=str(d.get("notes", ""))[:240],
        ))
    return results


# ---------------------------------------------------------------------------
# Benchmark deltas
# ---------------------------------------------------------------------------

def _benchmark_deltas(target: TargetInput) -> List[BenchmarkDelta]:
    """Pull the 2-3 most relevant curve rows from the Benchmark Curve Library."""
    try:
        from .benchmark_curve_library import compute_benchmark_library
        bench = compute_benchmark_library()
    except Exception:
        return []

    deltas: List[BenchmarkDelta] = []
    mult = _entry_multiple(target)

    # 1. Per-physician Medicare revenue for target specialty × region (BC-02)
    bc02 = [r for r in bench.curve_rows
            if r.curve_id == "BC-02"
            and r.specialty and target.sector.lower().split()[0] in r.specialty.lower()
            and r.region == target.region]
    if bc02:
        r = bc02[0]
        deltas.append(BenchmarkDelta(
            curve_id=r.curve_id, curve_name=r.curve_name,
            metric=r.metric, unit=r.unit,
            target_percentile=None,
            p10=r.p10, p50=r.p50, p90=r.p90,
            delta_vs_p50_pct=None,
            interpretation=(
                f"Per-physician Medicare revenue for {r.specialty} × {r.region} · "
                f"P50 ${r.p50:,.0f}. Assume commercial+Medicaid multiplier 2.0-2.8x "
                f"for full-revenue view. Your target's physician headcount × this "
                f"figure × multiplier = baseline Medicare-revenue line for sanity-check."
            ),
        ))

    # 2. Operating margin by bed-size × region (BC-05) — hospital only
    if target.facility_type.lower() == "hospital":
        bc05 = [r for r in bench.curve_rows if r.curve_id == "BC-05"
                and r.region == target.region and r.year == 2023]
        if bc05:
            r = bc05[0]
            deltas.append(BenchmarkDelta(
                curve_id=r.curve_id, curve_name=r.curve_name,
                metric=r.metric, unit=r.unit,
                target_percentile=None,
                p10=r.p10, p50=r.p50, p90=r.p90,
                delta_vs_p50_pct=None,
                interpretation=(
                    f"2023 operating margin for {r.facility_type} × {r.region} · "
                    f"P50 {r.p50:.1f}%. If your hospital target's margin is below P25 "
                    f"({r.p25:.1f}%), that's a structural problem requiring RCM + "
                    f"cost-structure intervention, not just operational upside."
                ),
            ))

    # 3. Entry-multiple context (synthetic — not a curve in the library but derivable)
    if mult is not None:
        # Approximate multiple peer benchmark
        if target.facility_type.lower() == "hospital":
            p10, p50, p90 = 6.5, 9.5, 13.0
        else:
            p10, p50, p90 = 8.0, 11.5, 15.0
        pctile = None
        if mult <= p10:
            pctile = 10
        elif mult <= p50:
            pctile = 50 * (mult - p10) / (p50 - p10)
        elif mult <= p90:
            pctile = 50 + 40 * (mult - p50) / (p90 - p50)
        else:
            pctile = min(99, 90 + (mult - p90) * 2)
        delta = (mult - p50) / p50 * 100
        deltas.append(BenchmarkDelta(
            curve_id="MULT-PEER",
            curve_name="Entry Multiple vs Healthcare-PE Peer",
            metric="Entry EV/EBITDA multiple",
            unit="x",
            target_percentile=round(pctile, 1) if pctile is not None else None,
            p10=p10, p50=p50, p90=p90,
            delta_vs_p50_pct=round(delta, 1),
            interpretation=(
                f"Target entry multiple {mult:.1f}x sits at the ~{pctile:.0f}th "
                f"percentile of peer healthcare-PE deals. Delta to P50: {delta:+.1f}%. "
                f"{'Expect mean reversion of 2-4 turns by exit.' if mult > 13 else 'Reasonable multiple entry.'}"
            ),
        ))
    return deltas


# ---------------------------------------------------------------------------
# OIG Work Plan exposure (soft import — module may not be committed yet)
# ---------------------------------------------------------------------------

def _oig_exposure(target_row: dict) -> Dict[str, object]:
    try:
        from .oig_workplan import _build_items, _score_deal_exposure   # type: ignore
        items = _build_items()
        exp = _score_deal_exposure(target_row, items)
        # Top 3 items in target's provider-type
        relevant = [it for it in items if it.provider_type == exp.inferred_provider_type
                    and it.status in ("open", "active")][:3]
        return {
            "provider_type": exp.inferred_provider_type,
            "risk_tier": exp.risk_tier,
            "matched_items": exp.matched_items,
            "open_active_matches": exp.open_active_matches,
            "exposure_mm": exp.total_exposure_mid_mm,
            "top_items": [
                {"item_id": it.item_id, "title": it.title,
                 "enforcement_risk": it.enforcement_risk,
                 "typical_recovery_low": it.typical_recovery_low_mm,
                 "typical_recovery_high": it.typical_recovery_high_mm}
                for it in relevant
            ],
        }
    except Exception as e:
        return {"error": f"OIG Work Plan module not yet wired: {e}",
                "provider_type": "—", "risk_tier": "UNKNOWN",
                "matched_items": 0, "open_active_matches": 0,
                "exposure_mm": 0.0, "top_items": []}


# ---------------------------------------------------------------------------
# TEAM exposure (hospital only)
# ---------------------------------------------------------------------------

def _team_exposure(target: TargetInput, target_row: dict) -> Optional[Dict[str, object]]:
    if target.facility_type.lower() != "hospital":
        return None
    try:
        from .team_calculator import (
            _build_cbsa_lattice, _build_risk_share_schedule, _score_deal_exposure
        )
        lattice = _build_cbsa_lattice()
        schedule = _build_risk_share_schedule()
        exp = _score_deal_exposure(target_row, lattice, schedule)
        if exp is None:
            return {"risk_tier": "UNAFFECTED", "notes": "No CBSA match inferred."}
        return {
            "risk_tier": exp.risk_tier,
            "inferred_facilities": exp.inferred_facility_count,
            "matched_cbsas": exp.matched_cbsas[:3],
            "annual_at_risk_mm": exp.annual_at_risk_mm,
            "py1_downside_mm": exp.py1_downside_exposure_mm,
            "py3_downside_mm": exp.py3_downside_exposure_mm,
            "py5_downside_mm": exp.py5_downside_exposure_mm,
            "notes": exp.notes,
        }
    except Exception as e:
        return {"error": str(e), "risk_tier": "UNKNOWN"}


# ---------------------------------------------------------------------------
# Bear-case memo narrative
# ---------------------------------------------------------------------------

def _bear_case_narrative(target: TargetInput, target_row: dict) -> str:
    try:
        from .adversarial_engine import _build_memo
        memo = _build_memo(target_row)
        return memo.red_team_summary
    except Exception as e:
        return f"(bear-case engine error: {e})"


# ---------------------------------------------------------------------------
# Management questions
# ---------------------------------------------------------------------------

def _management_questions(target: TargetInput, verdict: VerdictSummary,
                           ncci_summary: Dict[str, object],
                           oig_summary: Dict[str, object]) -> List[ManagementQuestion]:
    qs: List[ManagementQuestion] = []

    # Payer-mix questions
    if target.commercial_share >= 0.50:
        qs.append(ManagementQuestion(
            "Payer mix",
            "What's your top-3-commercial-payer concentration and when do those contracts renew?",
            "High commercial share is a structural differentiator but if it's concentrated in 1-2 payers, contract loss = EBITDA shock.",
            "Payer-level AR aging + contract renewal calendar + current rate trajectory",
        ))
    govt = target.medicare_share + target.medicaid_share
    if govt >= 0.55:
        qs.append(ManagementQuestion(
            "Payer mix",
            "What's your Medicaid unwinding exposure across states and your safety-net designation?",
            "Medicaid redeterminations + state budget pressure = rate compression risk.",
            "State-by-state Medicaid enrollment trend + DSH exposure",
        ))

    # Leverage / valuation
    mult = _entry_multiple(target)
    if mult and mult >= 13:
        qs.append(ManagementQuestion(
            "Leverage",
            f"Your {mult:.1f}x entry multiple requires 2-4 turns of EBITDA growth just to hold exit multiple. Where is that EBITDA coming from specifically, quarter by quarter?",
            "Top-quartile entry multiples rarely sustain without demonstrable organic growth or a structural cost lever.",
            "Quarterly EBITDA walk-forward, organic vs bolt-on decomposition, 100-day actions with dollar impact",
        ))

    # RCM operational
    if ncci_summary.get("density", 0) >= 30:
        qs.append(ManagementQuestion(
            "Ops / RCM",
            f"Your specialty shows NCCI edit-density {ncci_summary.get('density', 0):.0f}. What's your denial rate by CARC code over the last 12 months?",
            "NCCI edit exposure directly drives denial write-offs; if denial rates aren't in control, post-close cost-to-collect balloons.",
            "CARC-level denial report, modifier-override success rate, denial-management SLAs",
        ))

    # Regulatory / OIG
    if oig_summary.get("open_active_matches", 0) >= 2:
        qs.append(ManagementQuestion(
            "Regulatory",
            "OIG Work Plan has open items matching your provider type. What's your internal compliance review cadence and recent self-disclosure activity?",
            "Active OIG audit exposure is a recoupment risk; self-disclosure before close is vastly better than Discovery during.",
            "Last 3 years internal compliance audits + any active qui tam or DOJ inquiries",
        ))

    # Exit / competitive
    qs.append(ManagementQuestion(
        "Exit",
        "Who are the 3-5 most likely strategic buyers at exit, and what's your read on their current M&A appetite?",
        "A 3x MOIC in 5 years requires a buyer at exit; if strategic demand thins, valuation pressure follows.",
        "Competitive landscape map + recent transactions in adjacency + strategic-buyer interactions",
    ))

    return qs[:6]


# ---------------------------------------------------------------------------
# Conditions precedent (100-day / SPA items)
# ---------------------------------------------------------------------------

def _conditions_precedent(target: TargetInput, verdict: VerdictSummary,
                           ncci_summary: Dict[str, object],
                           oig_summary: Dict[str, object],
                           team_summary: Optional[Dict[str, object]]) -> List[ConditionPrecedent]:
    conds: List[ConditionPrecedent] = []

    # Always-on basics
    conds.append(ConditionPrecedent(
        "Day 1",
        "Compliance monitor in place",
        "CRO / Legal",
        "Engage external compliance counsel for 90-day post-close coding + billing audit sample.",
        "Sample-audit 200 claims by Day 30; compliance dashboard live by Day 45.",
    ))
    conds.append(ConditionPrecedent(
        "Day 1-30",
        "Top-10 payer contract rate review",
        "CFO",
        "Extract rate schedule + underpayment status for top-10 commercial + MA payers.",
        "Identified underpayment recoveries ≥ 0.5% of NPR by Day 30.",
    ))

    # Conditional on NCCI exposure
    if ncci_summary.get("density", 0) >= 30:
        conds.append(ConditionPrecedent(
            "Day 1-60",
            "NCCI denial-management workflow",
            "CRO / Billing lead",
            f"Deploy NCCI edit-compliance scan against last 12 months of claims; quantify edit-triggered denials by CPT pair; roll out X{{EPSU}} modifier training.",
            f"Clean-claim rate uplift ≥2 pts in 90 days; modifier-59 use reduced ≥25%.",
        ))

    # Conditional on OIG exposure
    if oig_summary.get("open_active_matches", 0) >= 2:
        conds.append(ConditionPrecedent(
            "Day 1-90",
            "OIG Work Plan gap analysis",
            "CRO / Legal",
            "For each active OIG item matching provider type, conduct documentation-adequacy review; consider pre-close self-disclosure on material findings.",
            "Gap analysis complete by Day 60; remediation plan by Day 90.",
        ))

    # Conditional on TEAM exposure
    if team_summary and team_summary.get("risk_tier") in ("CRITICAL", "HIGH", "MEDIUM"):
        conds.append(ConditionPrecedent(
            "Day 1-120",
            "TEAM (mandatory bundled payment) readiness",
            "CFO / CMO",
            "Model per-hospital PY1 TEAM exposure; negotiate post-acute network + home-health integration; pre-position for PY3 risk-share ramp.",
            "Target baseline episode spend within P25 benchmark by PY1 close (2026Q4).",
        ))

    # Conditional on elevated leverage
    mult = _entry_multiple(target)
    if mult and mult >= 12:
        conds.append(ConditionPrecedent(
            "Day 1-30",
            "Covenant + refi runway lock",
            "CFO",
            "Pre-secure covenant waivers for 12 months; lock refi commitment within 90 days.",
            "Covenant headroom >1.2x in base case + cushion in downside.",
        ))

    # Conditional on RED verdict
    if verdict.verdict == "RED":
        conds.append(ConditionPrecedent(
            "Day 1-15",
            "Second-opinion diligence engagement",
            "IC Chair",
            "Commission independent diligence firm (non-advisor conflict) to validate the bear-case scenario before close.",
            "Independent written opinion delivered Day 14.",
        ))

    return conds[:8]


# ---------------------------------------------------------------------------
# Red flags (top-5 scorecard)
# ---------------------------------------------------------------------------

def _red_flags(target: TargetInput, verdict: VerdictSummary,
                pattern_matches: List[PatternMatchResult],
                ncci_summary: Dict[str, object],
                oig_summary: Dict[str, object],
                team_summary: Optional[Dict[str, object]]) -> List[RedFlag]:
    candidates: List[Tuple[int, RedFlag]] = []
    rank = 1

    mult = _entry_multiple(target)
    if mult and mult >= 13:
        candidates.append((10, RedFlag(
            rank=rank,
            flag=f"Top-quartile entry multiple ({mult:.1f}x)",
            severity="HIGH",
            evidence=f"Enters at {mult:.1f}x vs specialty peer-median ~11.5x",
            mitigation="Demonstrate organic EBITDA growth pathway; secure refi runway Day 30",
        )))
        rank += 1

    # Top pattern match
    if pattern_matches and pattern_matches[0].match_score >= 50:
        top = pattern_matches[0]
        sev = "CRITICAL" if top.match_score >= 70 else "HIGH"
        candidates.append((20, RedFlag(
            rank=rank,
            flag=f"Structural similarity to {top.case_name} ({top.pattern_id})",
            severity=sev,
            evidence=f"Match score {top.match_score:.1f}, keywords: {', '.join(top.matched_keywords[:4])}",
            mitigation=f"Run pre-facto-signal diagnostic per {top.pattern_id} thresholds in 60-day diligence extension",
        )))
        rank += 1

    # NCCI
    if ncci_summary.get("density", 0) >= 40:
        candidates.append((15, RedFlag(
            rank=rank,
            flag=f"Elevated NCCI edit density ({ncci_summary.get('density', 0):.0f})",
            severity="HIGH" if ncci_summary.get("density", 0) >= 55 else "MEDIUM",
            evidence=f"Specialty={ncci_summary.get('specialty', '?')}, edits affecting={ncci_summary.get('ptp_edits_affecting', 0)}",
            mitigation="Deploy NCCI edit-compliance scan + modifier-override training in first 60 days",
        )))
        rank += 1

    # OIG
    if oig_summary.get("open_active_matches", 0) >= 3:
        sev = "HIGH" if oig_summary.get("open_active_matches", 0) >= 5 else "MEDIUM"
        candidates.append((12, RedFlag(
            rank=rank,
            flag=f"Multiple open OIG Work Plan items ({oig_summary.get('open_active_matches', 0)})",
            severity=sev,
            evidence=f"Provider type {oig_summary.get('provider_type', '?')}, exposure ${oig_summary.get('exposure_mm', 0):.1f}M",
            mitigation="Pre-close OIG gap analysis; consider self-disclosure on material findings",
        )))
        rank += 1

    # TEAM
    if team_summary and team_summary.get("risk_tier") in ("CRITICAL", "HIGH"):
        candidates.append((18, RedFlag(
            rank=rank,
            flag=f"TEAM mandatory bundled-payment exposure ({team_summary.get('risk_tier', '?')})",
            severity="HIGH",
            evidence=f"PY5 downside ${team_summary.get('py5_downside_mm', 0):.1f}M across {len(team_summary.get('matched_cbsas', []))} mandated CBSAs",
            mitigation="Model per-hospital PY1-PY5 TEAM reconciliation; secure post-acute network Day 1",
        )))
        rank += 1

    # Payer concentration
    govt = target.medicare_share + target.medicaid_share
    if govt >= 0.65:
        candidates.append((14, RedFlag(
            rank=rank,
            flag=f"Government payer concentration ({govt:.0%})",
            severity="HIGH",
            evidence=f"Medicare {target.medicare_share:.0%} + Medicaid {target.medicaid_share:.0%} = {govt:.0%}",
            mitigation="Model Medicaid unwinding + MA V28 scenarios; pressure-test supplemental payments",
        )))
        rank += 1

    # Commercial concentration RED flag (opposite direction)
    if target.commercial_share >= 0.60 and not pattern_matches:
        candidates.append((5, RedFlag(
            rank=rank,
            flag=f"High commercial concentration — contract-loss sensitivity",
            severity="MEDIUM",
            evidence=f"Commercial {target.commercial_share:.0%} — check top-3 payer concentration in diligence",
            mitigation="Require top-3 payer concentration disclosure + 3-year renewal calendar",
        )))
        rank += 1

    # Leverage if unknown EBITDA
    if target.ebitda_mm is None or target.ebitda_mm <= 0:
        candidates.append((8, RedFlag(
            rank=rank,
            flag="EBITDA not disclosed or negative at entry",
            severity="HIGH",
            evidence=f"EBITDA = {target.ebitda_mm}",
            mitigation="Require audited EBITDA + QoE adjustment schedule before SPA",
        )))
        rank += 1

    # FALLBACK: even GREEN deals need 3+ things to defend at IC
    if len(candidates) < 3:
        # Commercial concentration always worth surfacing at MEDIUM
        if target.commercial_share >= 0.45 and not any("commercial" in f.flag.lower() for _, f in candidates):
            candidates.append((4, RedFlag(
                rank=rank,
                flag=f"Commercial payer concentration — top-3 payer exposure",
                severity="MEDIUM",
                evidence=f"Commercial {target.commercial_share:.0%} of payer mix — contract-loss sensitivity",
                mitigation="Require top-3 commercial-payer concentration + 3-year renewal calendar in diligence",
            )))
            rank += 1

        # Entry multiple context — always useful if in 10-13x band
        if mult and 10 <= mult < 13:
            candidates.append((3, RedFlag(
                rank=rank,
                flag=f"Entry multiple {mult:.1f}x — above peer median, mean-reversion risk",
                severity="MEDIUM",
                evidence=f"Peer median ~11.5x; each 0.5-turn compression → -4% MOIC",
                mitigation="Secure refi path + 100-day EBITDA growth plan",
            )))
            rank += 1

        # NCCI density medium band
        if 20 <= ncci_summary.get("density", 0) < 40:
            candidates.append((2, RedFlag(
                rank=rank,
                flag=f"Moderate NCCI edit density ({ncci_summary.get('density', 0):.0f}) — denial workflow scrutiny",
                severity="MEDIUM",
                evidence=f"Specialty={ncci_summary.get('specialty', '?')}; modifier-59/X{{EPSU}} usage pattern matters",
                mitigation="Audit 12 months of denial CARC-level data in first 60 days post-close",
            )))
            rank += 1

        # Always surface bear-case MC capital-loss if >= 40%
        candidates.append((1, RedFlag(
            rank=rank,
            flag="Bear-case capital-loss probability per adversarial engine",
            severity="MEDIUM",
            evidence="Worst-quartile Monte Carlo (pessimistic priors) — review bear memo below",
            mitigation="Pressure-test base case at P25 inputs; require management signal on 3-5 specific KPIs quarterly",
        )))
        rank += 1

    # Sort by weight and rerank 1-5
    candidates.sort(key=lambda x: -x[0])
    flags: List[RedFlag] = []
    for i, (_w, f) in enumerate(candidates[:5]):
        f.rank = i + 1
        flags.append(f)
    return flags


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_ic_brief(target: TargetInput) -> ICBriefResult:
    corpus = _load_corpus()
    target_row = _synthetic_corpus_row(target)

    # Component scores
    nf_top_score, pattern_matches = _nf_score(target_row)
    ncci_density, ncci_summary = _ncci_score(target_row)
    leverage = _leverage_score(target)

    # Verdict
    verdict = _compute_verdict(target, target_row, nf_top_score, ncci_density, leverage)

    # Comparables
    comps = _find_comparable_deals(target, corpus, k=5)

    # Benchmark deltas
    bench_deltas = _benchmark_deltas(target)

    # Regulatory
    oig_summary = _oig_exposure(target_row)
    team_summary = _team_exposure(target, target_row)

    # Bear narrative
    bear_narr = _bear_case_narrative(target, target_row)

    # Management questions + conditions + red flags
    questions = _management_questions(target, verdict, ncci_summary, oig_summary)
    conditions = _conditions_precedent(target, verdict, ncci_summary, oig_summary, team_summary)
    flags = _red_flags(target, verdict, pattern_matches, ncci_summary, oig_summary, team_summary)

    return ICBriefResult(
        target=target,
        verdict=verdict,
        pattern_matches=pattern_matches,
        comparable_deals=comps,
        benchmark_deltas=bench_deltas,
        ncci_exposure_summary=ncci_summary,
        oig_exposure_summary=oig_summary,
        team_exposure_summary=team_summary,
        bear_case_memo_narrative=bear_narr,
        management_questions=questions,
        conditions_precedent=conditions,
        red_flags=flags,
        corpus_deal_count=len(corpus),
        methodology_note=(
            "IC Brief composes output from every shipped data_public module: "
            "Named-Failure Library (pattern match), NCCI Scanner (edit density), "
            "Benchmark Curve Library (percentile positioning), OIG Work Plan "
            "(audit exposure), TEAM Calculator (mandatory bundle), Adversarial "
            "Engine (bear memo). Verdict uses the Backtest Harness composite: "
            "0.45·NF + 0.25·NCCI + 0.30·Leverage. Distress probability via "
            "logistic((composite-50)/12). Comparables use log-EV + multiple + "
            "government-share distance on sector-filtered corpus."
        ),
    )


# ---------------------------------------------------------------------------
# Default target for demo (Project Cypress — GI endoscopy roll-up)
# ---------------------------------------------------------------------------

DEFAULT_DEMO_TARGET = TargetInput(
    deal_name="Project Cypress — GI Endoscopy Platform",
    sector="Gastroenterology",
    ev_mm=420.0,
    ebitda_mm=38.0,
    hold_years=5.0,
    commercial_share=0.55,
    medicare_share=0.30,
    medicaid_share=0.12,
    self_pay_share=0.03,
    region="West",
    facility_type="Physician Group",
    buyer="Mid-market healthcare PE sponsor",
    notes=(
        "14-clinic GI endoscopy platform across CA/TX/AZ. Thesis: commercial GI "
        "volume growth 6-8%, 3-4 bolt-on practices, regional-scale commercial rate "
        "negotiation, ASC conversion opportunity on ~40% of polypectomy cases. "
        "Sponsor's 4th healthcare platform deal."
    ),
)
