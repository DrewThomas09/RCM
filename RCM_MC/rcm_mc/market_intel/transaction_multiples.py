"""Private-market PE transaction-multiple lookups."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


CONTENT_DIR = Path(__file__).parent / "content"


@dataclass
class MultipleBand:
    specialty: str
    deal_size_band: str
    p25_ev_ebitda: float
    p50_ev_ebitda: float
    p75_ev_ebitda: float
    sample_size: int
    note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()


def _load() -> Dict[str, Any]:
    return yaml.safe_load(
        (CONTENT_DIR / "transaction_multiples.yaml").read_text("utf-8")
    )


def _size_band_for_ev(ev_usd: float, bands: Dict[str, Any]) -> Optional[str]:
    for name, rng in bands.items():
        lo = float(rng.get("min_ev_usd", 0) or 0)
        hi = rng.get("max_ev_usd")
        hi_val = float(hi) if hi is not None else float("inf")
        if lo <= ev_usd < hi_val:
            return name
    return None


def list_specialty_bands(specialty: str) -> List[MultipleBand]:
    """Return all deal-size bands for a specialty."""
    data = _load()
    sp = (specialty or "").upper()
    out: List[MultipleBand] = []
    for row in data.get("bands") or ():
        if str(row.get("specialty", "")).upper() != sp:
            continue
        out.append(MultipleBand(
            specialty=sp,
            deal_size_band=str(row.get("deal_size_band", "")),
            p25_ev_ebitda=float(row.get("p25_ev_ebitda", 0)),
            p50_ev_ebitda=float(row.get("p50_ev_ebitda", 0)),
            p75_ev_ebitda=float(row.get("p75_ev_ebitda", 0)),
            sample_size=int(row.get("sample_size_trailing_12_mo", 0) or 0),
            note=row.get("note"),
        ))
    return out


def transaction_multiple(
    *,
    specialty: str,
    ev_usd: Optional[float] = None,
    deal_size_band: Optional[str] = None,
) -> Optional[MultipleBand]:
    """Return the most relevant multiple band for the specialty ×
    deal-size combo.

    - When ``deal_size_band`` is given explicitly, match exactly.
    - When ``ev_usd`` is given, compute the size band from the YAML
      ranges and match.
    - Otherwise fall back to the specialty's largest-sample band.
    """
    data = _load()
    bands = list_specialty_bands(specialty)
    if not bands:
        return None
    size_bands = data.get("deal_size_bands") or {}

    explicit = deal_size_band
    if explicit is None and ev_usd is not None:
        explicit = _size_band_for_ev(float(ev_usd), size_bands)
    if explicit:
        for b in bands:
            if b.deal_size_band == explicit:
                return b
    # Fallback: largest sample.
    bands.sort(key=lambda b: -b.sample_size)
    return bands[0]
