"""Curated healthcare PE transaction library.

Loads the YAML fixture at ``content/pe_transactions.yaml`` and
exposes filtering / rollup helpers.

Used by:
    * The Seeking Alpha market-intel page — "Recent PE transactions"
      feed so partners see peer-group deal flow alongside public
      comp multiples
    * The Bridge Audit and Exit Timing pages — cross-reference
      "recent sponsor X deal closed at 12.8×" as a negotiation anchor
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


CONTENT_DIR = Path(__file__).parent / "content"


@dataclass
class PETransaction:
    """One PE deal record."""
    date: str
    target: str
    sponsor: str
    specialty: str
    deal_size_usd_mm: Optional[float] = None
    ev_ebitda_multiple: Optional[float] = None
    multiple_source: str = ""
    target_characteristics: Dict[str, Any] = field(default_factory=dict)
    narrative: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "target": self.target,
            "sponsor": self.sponsor,
            "specialty": self.specialty,
            "deal_size_usd_mm": self.deal_size_usd_mm,
            "ev_ebitda_multiple": self.ev_ebitda_multiple,
            "multiple_source": self.multiple_source,
            "target_characteristics": dict(self.target_characteristics),
            "narrative": self.narrative,
        }


def _load() -> Dict[str, Any]:
    path = CONTENT_DIR / "pe_transactions.yaml"
    if not path.exists():
        return {"transactions": []}
    with path.open("r") as f:
        return yaml.safe_load(f) or {"transactions": []}


def list_transactions() -> List[PETransaction]:
    """Return every transaction, sorted most-recent first."""
    raw = _load().get("transactions") or []
    out: List[PETransaction] = []
    for r in raw:
        out.append(PETransaction(
            date=str(r.get("date", "")),
            target=str(r.get("target", "")),
            sponsor=str(r.get("sponsor", "")),
            specialty=str(r.get("specialty", "")),
            deal_size_usd_mm=r.get("deal_size_usd_mm"),
            ev_ebitda_multiple=r.get("ev_ebitda_multiple"),
            multiple_source=str(r.get("multiple_source") or ""),
            target_characteristics=dict(
                r.get("target_characteristics") or {}
            ),
            narrative=str(r.get("narrative") or "").strip(),
        ))
    out.sort(key=lambda t: t.date, reverse=True)
    return out


def transactions_for_specialty(
    specialty: str, limit: int = 10,
) -> List[PETransaction]:
    """Filter to transactions in a given specialty (case-insensitive)."""
    sp = (specialty or "").upper()
    if not sp:
        return []
    out = [
        t for t in list_transactions()
        if t.specialty.upper() == sp
    ]
    return out[:limit]


def sponsor_activity(lookback_months: int = 12) -> Dict[str, int]:
    """Count deals per sponsor in the lookback window.

    Used by the Seeking Alpha page to show "Who's deploying capital
    in healthcare right now?" — the leaderboard of active sponsors.
    """
    from datetime import date
    as_of = date.today()
    counts: Dict[str, int] = {}
    for t in list_transactions():
        try:
            y, m, d = (int(p) for p in t.date.split("-"))
            delta_months = (
                (as_of.year - y) * 12 + (as_of.month - m)
            )
            if 0 <= delta_months <= lookback_months:
                counts[t.sponsor] = counts.get(t.sponsor, 0) + 1
        except (ValueError, TypeError):
            continue
    return dict(
        sorted(counts.items(), key=lambda kv: -kv[1])
    )


def multiple_band_by_specialty() -> Dict[str, Dict[str, float]]:
    """Roll-up: per specialty, median / min / max of observed
    EV/EBITDA multiples in the library."""
    by_sp: Dict[str, List[float]] = {}
    for t in list_transactions():
        if t.ev_ebitda_multiple and t.specialty:
            by_sp.setdefault(t.specialty, []).append(
                float(t.ev_ebitda_multiple),
            )
    out: Dict[str, Dict[str, float]] = {}
    for sp, mults in by_sp.items():
        mults.sort()
        out[sp] = {
            "count": len(mults),
            "median": mults[len(mults) // 2],
            "min": mults[0],
            "max": mults[-1],
        }
    return out
