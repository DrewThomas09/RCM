"""CMS Provider X-Ray — benchmarked diligence report (PR B).

Composes a single diligence report for a resolved provider by REUSING the
existing layers — it adds no new benchmarking math:

- `investable_evidence.evidence_profile` (#620) → per-metric peer percentile,
  guarded z-score, weights, the transparent evidence index, and SNF
  enforcement/staffing risk flags;
- `cross_sector.sector_state_benchmark` (#619) → state market context
  (provider/locality counts, ownership mix + HHI, state percentile,
  missingness);
- `provider_xray.ProviderMatch` → identity + native profile link.

From those it derives a small set of transparent **diligence signals**
(green / amber / red / gray) — each one traceable to a component it already
shows, never a black-box score and never an investment recommendation.

Hospital/HCRIS has no cross_sector/evidence entry (its metrics are
cost-report financials), so its report is identity + an honest pointer to the
native hospital profile / HCRIS X-Ray rather than fabricated peer benchmarks.

Honest by construction: CMS public data only; concentration is composition
not market share; percentile is peer deviation; small samples (n<5) suppress
percentile/z-score; nothing is fabricated.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from .cross_sector import SECTOR_BY_ID, SectorStateBenchmark, sector_state_benchmark
from .investable_evidence import EvidenceProfile, evidence_profile
from .provider_xray import ProviderMatch

# Signal severities (paired with text everywhere — never color-only).
GREEN, AMBER, RED, GRAY = "green", "amber", "red", "gray"


@dataclass(frozen=True)
class DiligenceSignal:
    name: str
    severity: str        # green | amber | red | gray
    detail: str


@dataclass
class ProviderXrayReport:
    match: ProviderMatch
    has_benchmarks: bool
    evidence: Optional[EvidenceProfile]
    market: Optional[SectorStateBenchmark]
    signals: List[DiligenceSignal] = field(default_factory=list)
    caveats: List[str] = field(default_factory=list)
    suggested_questions: List[str] = field(default_factory=list)
    note: str = ""           # for verticals without a benchmark layer (hospital)


_BASE_QUESTIONS = [
    "What explains this provider's percentile position versus its peers?",
    "Which metrics are directly observed versus a proxy?",
    "Is this provider an outlier relative to same-state peers, or within noise?",
    "What local competitors should we diligence next?",
    "What management questions follow from the weakest metrics?",
    "What source data is missing, and would it change the read?",
    "Which single signal would most change our view if validated?",
    "How does this provider compare with the vertical's national median?",
]


def _quality_signal(ev: Optional[EvidenceProfile]) -> DiligenceSignal:
    if ev is None or ev.evidence_index is None:
        return DiligenceSignal(
            "Quality position", GRAY,
            "No rated quality metrics for this provider/peer set.")
    idx = ev.evidence_index
    if idx >= 66:
        sev, word = GREEN, "top-tier"
    elif idx >= 34:
        sev, word = AMBER, "mid-pack"
    else:
        sev, word = RED, "bottom-tier"
    return DiligenceSignal(
        "Quality position", sev,
        f"Peer-relative quality index {idx:g}/100 ({word}) across "
        f"{ev.sample_size} same-state rated peers.")


def _sample_signal(ev: Optional[EvidenceProfile]) -> DiligenceSignal:
    n = ev.sample_size if ev else 0
    if n >= 30:
        return DiligenceSignal("Peer sample", GREEN,
                               f"{n} rated same-state peers — robust comparison.")
    if n >= 5:
        return DiligenceSignal("Peer sample", AMBER,
                               f"{n} rated same-state peers — usable, read with care.")
    return DiligenceSignal("Peer sample", GRAY,
                           f"Only {n} rated same-state peers — percentile/z-score "
                           "suppressed (insufficient sample).")


def _enforcement_signal(ev: Optional[EvidenceProfile]) -> Optional[DiligenceSignal]:
    if ev is None or not ev.risk_flags:
        return None
    triggered = [f for f in ev.risk_flags if f.triggered]
    if not triggered:
        return DiligenceSignal("Enforcement / staffing", GREEN,
                               "No SFF, abuse, ownership-change, low-staffing, or "
                               "penalty flags on record.")
    sev = RED if any(f.name in ("Special Focus Facility", "Abuse icon")
                     for f in triggered) else AMBER
    return DiligenceSignal("Enforcement / staffing", sev,
                           "; ".join(f.detail for f in triggered))


def _competition_signal(mk: Optional[SectorStateBenchmark]) -> Optional[DiligenceSignal]:
    if mk is None or mk.locality_hhi is None:
        return None
    hhi = mk.locality_hhi
    if hhi >= 2500:
        sev, word = AMBER, "concentrated"
    else:
        sev, word = GREEN, "fragmented"
    return DiligenceSignal(
        "Local competition", sev,
        f"Provider-count locality HHI {hhi} ({word}; composition proxy, not "
        f"market share) across {mk.locality_count} localities in {mk.state}.")


def _ownership_signal(mk: Optional[SectorStateBenchmark]) -> Optional[DiligenceSignal]:
    if mk is None or not mk.ownership_mix:
        return None
    top_label, top_n = mk.ownership_mix[0]
    total = sum(c for _, c in mk.ownership_mix) or 1
    share = round(100 * top_n / total)
    return DiligenceSignal(
        "Ownership context", GRAY if mk.ownership_hhi is None else GREEN,
        f"Largest ownership type in {mk.state}: {top_label} ({share}% of "
        f"providers). Ownership-count HHI {mk.ownership_hhi}.")


def _missing_signal(ev: Optional[EvidenceProfile],
                    mk: Optional[SectorStateBenchmark]) -> DiligenceSignal:
    miss = list(ev.missingness) if ev else []
    state_miss = mk.missingness_pct if mk else None
    if miss or (state_miss and state_miss >= 25):
        bits = []
        if miss:
            bits.append("provider missing: " + ", ".join(miss))
        if state_miss and state_miss >= 25:
            bits.append(f"{state_miss:g}% of state peers unrated")
        return DiligenceSignal("Missing-data risk", AMBER, "; ".join(bits) + ".")
    return DiligenceSignal("Missing-data risk", GREEN,
                           "Headline metrics reported for this provider and most peers.")


def build_provider_xray_report(match: ProviderMatch) -> ProviderXrayReport:
    """Build the benchmarked diligence report for a resolved provider."""
    vid = match.vertical

    # Hospital/HCRIS: no peer-benchmark layer here — point to the native
    # surfaces rather than fabricate post-acute-style benchmarks.
    if vid == "hospital" or vid not in SECTOR_BY_ID:
        return ProviderXrayReport(
            match=match, has_benchmarks=False, evidence=None, market=None,
            signals=[DiligenceSignal(
                "Hospital cost-report metrics", GRAY,
                "Hospital benchmarking (beds, revenue, margin) lives in the "
                "HCRIS-powered hospital profile / HCRIS X-Ray — opened via the "
                "native profile link.")],
            caveats=[
                "HCRIS cost-report data is the only PEdesk source with real "
                "hospital revenue/margin; it is not benchmarked in this "
                "post-acute X-Ray view.",
                "Not an investment recommendation.",
            ],
            suggested_questions=_BASE_QUESTIONS,
            note="Open the hospital profile for HCRIS cost-report metrics.")

    ev = evidence_profile(vid, match.ccn or match.provider_id)
    mk = sector_state_benchmark(vid, match.state)

    signals: List[DiligenceSignal] = [_quality_signal(ev), _sample_signal(ev)]
    for maybe in (_enforcement_signal(ev), _competition_signal(mk),
                  _ownership_signal(mk), _missing_signal(ev, mk)):
        if maybe is not None:
            signals.append(maybe)

    caveats: List[str] = []
    if ev is not None:
        caveats.extend(ev.caveats)
    if mk is not None:
        # market caveats overlap; add only the standing market-share one.
        caveats.append("Local/ownership concentration is a provider-count "
                       "composition proxy, not market share.")

    return ProviderXrayReport(
        match=match, has_benchmarks=ev is not None, evidence=ev, market=mk,
        signals=signals, caveats=caveats, suggested_questions=_BASE_QUESTIONS)
