"""Peer discovery — find most-similar deals for a candidate.

Given a candidate deal and a list of peer reference deals, rank
peers by similarity across a weighted feature vector:

- Sector
- Size (EBITDA bucket)
- Payer mix regime
- Geography (state)
- Margin band
- Leverage band

Used pre-IC to find analogs the partner already knows, and post-
close to find cohorts for operating-lever benchmarking.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .reasonableness import classify_payer_mix, classify_size


@dataclass
class PeerDeal:
    deal_id: str
    name: str = ""
    sector: Optional[str] = None
    ebitda_m: Optional[float] = None
    payer_mix: Dict[str, float] = field(default_factory=dict)
    state: Optional[str] = None
    ebitda_margin: Optional[float] = None
    leverage_multiple: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "name": self.name,
            "sector": self.sector,
            "ebitda_m": self.ebitda_m,
            "payer_mix": dict(self.payer_mix),
            "state": self.state,
            "ebitda_margin": self.ebitda_margin,
            "leverage_multiple": self.leverage_multiple,
        }


@dataclass
class PeerMatch:
    peer: PeerDeal
    similarity: float
    match_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "peer": self.peer.to_dict(),
            "similarity": self.similarity,
            "match_reasons": list(self.match_reasons),
        }


def _margin_band(margin: Optional[float]) -> str:
    if margin is None:
        return "unknown"
    if margin < 0.05:
        return "low"
    if margin < 0.12:
        return "mid"
    if margin < 0.20:
        return "high"
    return "very_high"


def _leverage_band(lev: Optional[float]) -> str:
    if lev is None:
        return "unknown"
    if lev < 3.0:
        return "conservative"
    if lev < 5.0:
        return "moderate"
    if lev < 6.5:
        return "aggressive"
    return "extreme"


def _similarity(candidate: PeerDeal, peer: PeerDeal) -> tuple:
    """Return (similarity, reasons)."""
    reasons: List[str] = []
    score = 0.0
    weight_total = 0.0

    # Sector: 0.30 weight.
    if candidate.sector and peer.sector:
        weight_total += 0.30
        if candidate.sector.lower() == peer.sector.lower():
            score += 0.30
            reasons.append(f"same sector ({candidate.sector})")

    # Size bucket: 0.20 weight.
    cb = classify_size(candidate.ebitda_m)
    pb = classify_size(peer.ebitda_m)
    weight_total += 0.20
    if cb == pb:
        score += 0.20
        reasons.append(f"same size bucket ({cb})")

    # Payer regime: 0.20 weight.
    cr = classify_payer_mix(candidate.payer_mix)
    pr = classify_payer_mix(peer.payer_mix)
    weight_total += 0.20
    if cr == pr:
        score += 0.20
        reasons.append(f"same payer regime ({cr})")

    # State: 0.10 weight.
    if candidate.state and peer.state:
        weight_total += 0.10
        if candidate.state.upper() == peer.state.upper():
            score += 0.10
            reasons.append(f"same state ({candidate.state})")

    # Margin band: 0.10 weight.
    cm = _margin_band(candidate.ebitda_margin)
    pm = _margin_band(peer.ebitda_margin)
    if cm != "unknown" and pm != "unknown":
        weight_total += 0.10
        if cm == pm:
            score += 0.10
            reasons.append(f"same margin band ({cm})")

    # Leverage band: 0.10 weight.
    cl = _leverage_band(candidate.leverage_multiple)
    pl = _leverage_band(peer.leverage_multiple)
    if cl != "unknown" and pl != "unknown":
        weight_total += 0.10
        if cl == pl:
            score += 0.10
            reasons.append(f"same leverage band ({cl})")

    if weight_total == 0:
        return (0.0, [])
    return (score / weight_total, reasons)


def find_peers(
    candidate: PeerDeal,
    universe: List[PeerDeal],
    *,
    top_n: int = 5,
    min_similarity: float = 0.50,
) -> List[PeerMatch]:
    """Rank a universe of peers by similarity to the candidate."""
    matches: List[PeerMatch] = []
    for peer in universe:
        if peer.deal_id == candidate.deal_id:
            continue
        sim, reasons = _similarity(candidate, peer)
        if sim < min_similarity:
            continue
        matches.append(PeerMatch(
            peer=peer, similarity=round(sim, 4), match_reasons=reasons,
        ))
    matches.sort(key=lambda m: -m.similarity)
    return matches[:top_n]


def render_peers_markdown(candidate: PeerDeal,
                          matches: List[PeerMatch]) -> str:
    lines = [
        f"# Peer matches for {candidate.name or candidate.deal_id}",
        "",
    ]
    if not matches:
        lines.append("_No close peers in universe above similarity threshold._")
        return "\n".join(lines)
    lines.extend([
        "| Peer | Similarity | Match reasons |",
        "|---|---:|---|",
    ])
    for m in matches:
        name = m.peer.name or m.peer.deal_id
        lines.append(
            f"| {name} | {m.similarity:.2f} | {'; '.join(m.match_reasons)} |"
        )
    return "\n".join(lines)
