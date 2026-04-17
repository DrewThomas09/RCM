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
