"""Market structure — HHI / CR3 / CR5 and consolidation diagnosis.

Standard industrial-organization metrics applied to healthcare deal
markets:

- **HHI** (Herfindahl–Hirschman Index) — sum of squared market shares.
  Lower = more fragmented. DOJ/FTC thresholds: <1500 unconcentrated,
  1500-2500 moderate, >2500 high. These are published agency
  guidelines.
- **CR3 / CR5** — concentration ratio: sum of the top-3 / top-5
  shares.
- **Fragmentation verdict** — "fragmented" (HHI < 1500), "consolidating"
  (1500-2500), "consolidated" (> 2500).
- **Consolidation-play score** — 0..1 signal that the market is ripe
  for roll-up. Higher when: HHI low, CR5 low, long tail of small
  players, no single dominant player.

Inputs are market shares as a dict ``{player: share}`` where shares
are fractions or percentages (auto-normalized).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# DOJ/FTC guideline thresholds (on HHI scale 0..10000).
HHI_UNCONCENTRATED = 1500
HHI_HIGHLY_CONCENTRATED = 2500


@dataclass
class MarketStructureResult:
    hhi: float                                 # 0..10000
    cr3: float                                 # 0..1
    cr5: float                                 # 0..1
    n_players: int
    top_share: float                           # largest single share
    fragmentation_verdict: str                 # fragmented / consolidating / consolidated
    consolidation_play_score: float            # 0..1
    partner_note: str = ""
    partner_thesis_hint: str = ""
    shares_used: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hhi": self.hhi,
            "cr3": self.cr3,
            "cr5": self.cr5,
            "n_players": self.n_players,
            "top_share": self.top_share,
            "fragmentation_verdict": self.fragmentation_verdict,
            "consolidation_play_score": self.consolidation_play_score,
            "partner_note": self.partner_note,
            "partner_thesis_hint": self.partner_thesis_hint,
            "shares_used": dict(self.shares_used),
        }


def _normalize_shares(shares: Dict[str, float]) -> Dict[str, float]:
    """Normalize to fractions that sum to 1.0. Accepts percents or fractions."""
    if not shares:
        return {}
    clean = {str(k): float(v) for k, v in shares.items() if v is not None}
    total = sum(clean.values())
    if total <= 0:
        return clean
    # Renormalize to sum=1 regardless of input scale.
    return {k: v / total for k, v in clean.items()}


def compute_hhi(shares: Dict[str, float]) -> float:
    """HHI on the standard 0..10000 scale.

    Shares passed in as fractions (0..1) or percentages. Normalized
    first so HHI is scale-independent of the input.
    """
    norm = _normalize_shares(shares)
    return sum((s * 100.0) ** 2 for s in norm.values())


def compute_cr(shares: Dict[str, float], n: int) -> float:
    """Top-N concentration ratio as a fraction (0..1)."""
    norm = _normalize_shares(shares)
    top = sorted(norm.values(), reverse=True)[:max(n, 1)]
    return sum(top)


def compute_cr3(shares: Dict[str, float]) -> float:
    return compute_cr(shares, 3)


def compute_cr5(shares: Dict[str, float]) -> float:
    return compute_cr(shares, 5)


def _fragmentation_verdict(hhi: float) -> str:
    if hhi < HHI_UNCONCENTRATED:
        return "fragmented"
    if hhi < HHI_HIGHLY_CONCENTRATED:
        return "consolidating"
    return "consolidated"


def _consolidation_play_score(
    hhi: float,
    cr5: float,
    n_players: int,
    top_share: float,
) -> float:
    """Score how attractive the market is for a roll-up play [0..1].

    Higher = more ripe:
    - Low HHI (fragmented)
    - Low CR5 (no dominant group)
    - Many players (long tail)
    - No single dominant player
    """
    # HHI component: full score below 1000, 0 at 2500+.
    hhi_score = max(0.0, min(1.0, (2500.0 - hhi) / 1500.0))
    # CR5 component: full score below 0.30, 0 at 0.75+.
    cr5_score = max(0.0, min(1.0, (0.75 - cr5) / 0.45))
    # Player count: saturates at 25 players.
    n_score = min(1.0, n_players / 25.0)
    # No-dominance: penalize if anyone has > 25% share.
    dom_score = 1.0 if top_share <= 0.15 else max(0.0, (0.30 - top_share) / 0.15)
    # Weighted blend.
    return round(0.35 * hhi_score + 0.25 * cr5_score +
                 0.20 * n_score + 0.20 * dom_score, 4)


def _partner_note(verdict: str, score: float) -> str:
    if verdict == "fragmented" and score >= 0.60:
        return ("Fragmented market with long tail — classic roll-up setup. "
                "Operational integration, not competitive displacement, is "
                "the alpha.")
    if verdict == "fragmented":
        return "Fragmented but not deeply scored — validate the tuck-in pipeline."
    if verdict == "consolidating":
        return ("Market is mid-consolidation — watch for multiple inflation; "
                "the window to be a consolidator is narrowing.")
    return ("Market is already consolidated — roll-up math is late. "
            "Competitive displacement or capability build is the thesis, "
            "not scale arbitrage.")


def _partner_thesis_hint(verdict: str, score: float, top_share: float) -> str:
    if verdict == "fragmented" and score >= 0.60:
        return "platform_rollup"
    if verdict == "consolidating":
        return "buy_and_build"
    if top_share >= 0.35:
        return "challenger_or_niche"
    return "scale_or_capability"


# DOJ/FTC 2023 Merger Guidelines: a merger that raises HHI by >200
# into a market already above 2500 is presumed to enhance market power.
HHI_DELTA_PRESUMPTION = 200


@dataclass
class RollupStep:
    """One bolt-on in a buy-and-build sequence."""
    n: int                      # acquisition number (1-based)
    acquired: str
    combined_share: float       # platform share AFTER this acquisition
    hhi_after: float
    delta_hhi: float            # HHI rise from this acquisition
    crosses_presumption: bool   # HHI_after>2500 AND delta>200

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class RollupRunway:
    """How far a buy-and-build can run before antitrust bites.

    Models the platform (largest player, or a named one) acquiring the
    next-largest independents one at a time. At each step the merged
    entity's share is the sum of the two; everyone else is unchanged.
    Pure arithmetic on the shares + published DOJ thresholds, so the
    runway is auditable.
    """
    platform: str
    platform_share_start: float
    target_share: float
    acquisitions_to_target: Optional[int]   # None if unreachable
    presumption_step: Optional[int]         # acquisition n that crosses
    runway_acquisitions: int                # bolt-ons before presumption
    steps: List[RollupStep]
    note: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "platform_share_start": self.platform_share_start,
            "target_share": self.target_share,
            "acquisitions_to_target": self.acquisitions_to_target,
            "presumption_step": self.presumption_step,
            "runway_acquisitions": self.runway_acquisitions,
            "steps": [s.to_dict() for s in self.steps],
            "note": self.note,
        }


def rollup_runway(
    shares: Dict[str, float],
    *,
    platform: Optional[str] = None,
    target_share: float = 0.30,
    max_steps: int = 12,
) -> Optional[RollupRunway]:
    """Simulate a buy-and-build: the platform absorbs the next-largest
    independents until it hits ``target_share`` or the DOJ presumption.

    Returns None when there is nothing to roll up (fewer than two
    players). The presumption flag fires when a post-merger HHI sits
    above 2500 AND that acquisition raised HHI by more than 200 — the
    point where the next deal invites a Second Request.
    """
    norm = _normalize_shares(shares)
    if len(norm) < 2:
        return None
    # Platform = explicit name (if present) else the largest player.
    if platform and platform in norm:
        plat = platform
    else:
        plat = max(norm, key=norm.get)
    plat_start = norm[plat]

    # Acquisition order: largest independents first.
    others = sorted(
        ((k, v) for k, v in norm.items() if k != plat),
        key=lambda kv: -kv[1],
    )
    # Mutable working shares; merge acquired into the platform.
    work = dict(norm)
    prev_hhi = compute_hhi(work)   # 0..10000 scale
    steps: List[RollupStep] = []
    acq_to_target: Optional[int] = None
    presumption_step: Optional[int] = None

    for i, (name, sh) in enumerate(others[:max_steps], start=1):
        work[plat] = work.get(plat, 0.0) + sh
        work.pop(name, None)
        new_hhi = compute_hhi(work)
        delta = new_hhi - prev_hhi
        combined = work[plat]
        crosses = (new_hhi > HHI_HIGHLY_CONCENTRATED
                   and delta > HHI_DELTA_PRESUMPTION)
        steps.append(RollupStep(
            n=i, acquired=name, combined_share=round(combined, 4),
            hhi_after=round(new_hhi, 1), delta_hhi=round(delta, 1),
            crosses_presumption=crosses,
        ))
        if acq_to_target is None and combined >= target_share:
            acq_to_target = i
        if presumption_step is None and crosses:
            presumption_step = i
        prev_hhi = new_hhi
        # Stop once both milestones are known (keeps the table tight).
        if acq_to_target is not None and presumption_step is not None:
            break

    runway = (presumption_step - 1) if presumption_step else len(steps)

    if acq_to_target is not None and (
            presumption_step is None or acq_to_target <= presumption_step):
        note = (
            f"{plat} ({plat_start*100:.0f}% today) reaches {target_share*100:.0f}% "
            f"in {acq_to_target} bolt-on(s)"
            + (f", and the DOJ presumption (HHI>2500, ΔHHI>200) bites at "
               f"acquisition {presumption_step}." if presumption_step
               else " without tripping the DOJ concentration presumption "
                    "in this window.")
        )
    elif presumption_step is not None:
        note = (
            f"{plat} ({plat_start*100:.0f}% today) hits the DOJ concentration "
            f"presumption at acquisition {presumption_step} — before reaching "
            f"{target_share*100:.0f}%. Buy-and-build runway is "
            f"~{runway} clean bolt-on(s); beyond that, expect a Second Request."
        )
    else:
        reached = steps[-1].combined_share if steps else plat_start
        note = (
            f"{plat} ({plat_start*100:.0f}% today) can absorb all "
            f"{len(steps)} sizeable independents and still only reach "
            f"{reached*100:.0f}% — a long, antitrust-safe roll-up runway."
        )

    return RollupRunway(
        platform=plat, platform_share_start=round(plat_start, 4),
        target_share=target_share,
        acquisitions_to_target=acq_to_target,
        presumption_step=presumption_step,
        runway_acquisitions=runway, steps=steps, note=note,
    )


def analyze_market_structure(
    shares: Dict[str, float],
) -> MarketStructureResult:
    """Compute HHI/CR3/CR5 + consolidation diagnosis for a share map."""
    norm = _normalize_shares(shares)
    if not norm:
        return MarketStructureResult(
            hhi=0.0, cr3=0.0, cr5=0.0, n_players=0, top_share=0.0,
            fragmentation_verdict="unknown",
            consolidation_play_score=0.0,
            partner_note="No share data provided.",
            partner_thesis_hint="",
            shares_used={},
        )
    hhi = compute_hhi(shares)
    cr3 = compute_cr3(shares)
    cr5 = compute_cr5(shares)
    n = len(norm)
    top = max(norm.values())
    verdict = _fragmentation_verdict(hhi)
    score = _consolidation_play_score(hhi, cr5, n, top)
    return MarketStructureResult(
        hhi=round(hhi, 2),
        cr3=round(cr3, 4),
        cr5=round(cr5, 4),
        n_players=n,
        top_share=round(top, 4),
        fragmentation_verdict=verdict,
        consolidation_play_score=score,
        partner_note=_partner_note(verdict, score),
        partner_thesis_hint=_partner_thesis_hint(verdict, score, top),
        shares_used=norm,
    )


def is_consolidation_play(result: MarketStructureResult, *,
                          min_score: float = 0.55) -> bool:
    """Boolean gate: is this a credible roll-up setup?"""
    return (result.fragmentation_verdict == "fragmented"
            and result.consolidation_play_score >= min_score)
