"""Private-market PE transaction-multiple lookups."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


CONTENT_DIR = Path(__file__).parent / "content"

#: Bands whose trailing-12-month sample is below this are flagged
#: ``small_sample`` — p25/p75 quartiles over a single-digit deal count
#: identify a neighborhood, not a distribution, and several fixture
#: rows sit at n=4-9 (EMERGENCY_MEDICINE is 4). The flag travels with
#: the band (peer snapshot ``transaction_band``, API) so a consumer
#: can render "directional" instead of quoting the quartiles as if
#: they were market structure.
SMALL_SAMPLE_FLOOR: int = 10


@dataclass
class MultipleBand:
    specialty: str
    deal_size_band: str
    p25_ev_ebitda: float
    p50_ev_ebitda: float
    p75_ev_ebitda: float
    sample_size: int
    note: Optional[str] = None
    # How this band was selected for the caller's query:
    #   "size_band"               — the requested/computed size band matched
    #   "largest_sample_fallback" — a size band was requested but has no row
    #                               for the specialty; nearest available
    #                               (largest-sample) band returned instead
    #   "largest_sample_default"  — no size requested; documented default
    # Disclosed because a $50M EV query silently answered with the
    # OVER_500M band reads as "the" multiple to downstream consumers
    # (peer snapshot, API) unless the mismatch travels with the row.
    match_basis: str = "size_band"
    # n= disclosure: True when sample_size < SMALL_SAMPLE_FLOOR — see
    # the constant's note for why quartiles need this caveat.
    small_sample: bool = False

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
        n = int(row.get("sample_size_trailing_12_mo", 0) or 0)
        out.append(MultipleBand(
            specialty=sp,
            deal_size_band=str(row.get("deal_size_band", "")),
            p25_ev_ebitda=float(row.get("p25_ev_ebitda", 0)),
            p50_ev_ebitda=float(row.get("p50_ev_ebitda", 0)),
            p75_ev_ebitda=float(row.get("p75_ev_ebitda", 0)),
            sample_size=n,
            note=row.get("note"),
            small_sample=n < SMALL_SAMPLE_FLOOR,
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

    The returned band's ``match_basis`` says which of those happened —
    in particular ``"largest_sample_fallback"`` when a size band WAS
    requested but the specialty has no row for it, so callers can
    render "nearest available band" instead of presenting a different
    size class as the requested one.
    """
    data = _load()
    bands = list_specialty_bands(specialty)
    if not bands:
        return None
    size_bands = data.get("deal_size_bands") or {}

    size_requested = deal_size_band is not None or ev_usd is not None
    explicit = deal_size_band
    if explicit is None and ev_usd is not None:
        explicit = _size_band_for_ev(float(ev_usd), size_bands)
    if explicit:
        for b in bands:
            if b.deal_size_band == explicit:
                b.match_basis = "size_band"
                return b
    # Fallback: largest sample.
    bands.sort(key=lambda b: -b.sample_size)
    best = bands[0]
    best.match_basis = (
        "largest_sample_fallback" if size_requested
        else "largest_sample_default"
    )
    return best
