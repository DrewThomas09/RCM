"""Deal comparables — M&A comp sourcing + implied-multiple stats.

Partners defend an exit multiple by pointing to closed comps. This
module is a lightweight comp-set builder:

- A curated registry of representative closed healthcare-PE comps
  (illustrative; refresh quarterly from transaction databases).
- Filtering by sector, size, payer-mix regime.
- Implied-multiple statistics (min/median/max) for the filtered set.

This is NOT a live feed or transaction database — it's a starting
scaffold the deal team extends with real live comps. The dataset is
intentionally small and illustrative.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Model ────────────────────────────────────────────────────────────

@dataclass
class Comparable:
    id: str
    target_name: str
    close_year: int
    sector: str                      # matches sector_benchmarks subsectors
    region: Optional[str] = None
    ev_m: Optional[float] = None     # EV in $M
    ebitda_m: Optional[float] = None
    ev_ebitda_multiple: Optional[float] = None
    payer_regime: Optional[str] = None  # commercial_heavy / balanced / medicare_heavy / medicaid_heavy / govt_heavy
    source: str = "illustrative"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "target_name": self.target_name,
            "close_year": self.close_year,
            "sector": self.sector,
            "region": self.region,
            "ev_m": self.ev_m,
            "ebitda_m": self.ebitda_m,
            "ev_ebitda_multiple": self.ev_ebitda_multiple,
            "payer_regime": self.payer_regime,
            "source": self.source,
        }


# ── Illustrative registry ────────────────────────────────────────────

COMPS: List[Comparable] = [
    # Acute care
    Comparable("c1", "Regional acute-care network (Southeast)", 2022,
               "acute_care", "SE", ev_m=950, ebitda_m=95,
               ev_ebitda_multiple=10.0, payer_regime="balanced"),
    Comparable("c2", "Mid-size acute (Medicare-heavy)", 2023,
               "acute_care", "Midwest", ev_m=420, ebitda_m=50,
               ev_ebitda_multiple=8.4, payer_regime="medicare_heavy"),
    Comparable("c3", "Large-cap acute (commercial-heavy)", 2021,
               "acute_care", "Texas", ev_m=1800, ebitda_m=165,
               ev_ebitda_multiple=10.9, payer_regime="commercial_heavy"),
    Comparable("c4", "Small-cap acute (govt-heavy)", 2024,
               "acute_care", "Louisiana", ev_m=145, ebitda_m=22,
               ev_ebitda_multiple=6.6, payer_regime="govt_heavy"),
    # ASC
    Comparable("c5", "Multi-site ASC platform", 2023,
               "asc", "National", ev_m=560, ebitda_m=45,
               ev_ebitda_multiple=12.4, payer_regime="commercial_heavy"),
    Comparable("c6", "Specialty ASC (ortho)", 2022,
               "asc", "Northeast", ev_m=320, ebitda_m=26,
               ev_ebitda_multiple=12.3, payer_regime="commercial_heavy"),
    # Behavioral
    Comparable("c7", "Behavioral-health operator", 2023,
               "behavioral", "Midwest", ev_m=780, ebitda_m=82,
               ev_ebitda_multiple=9.5, payer_regime="balanced"),
    Comparable("c8", "SUD / detox chain", 2022,
               "behavioral", "Southeast", ev_m=410, ebitda_m=42,
               ev_ebitda_multiple=9.8, payer_regime="commercial_heavy"),
    # Post-acute
    Comparable("c9", "Regional SNF operator", 2024,
               "post_acute", "West", ev_m=520, ebitda_m=65,
               ev_ebitda_multiple=8.0, payer_regime="govt_heavy"),
    Comparable("c10", "Rehab-hospital operator", 2023,
               "post_acute", "Texas", ev_m=480, ebitda_m=58,
               ev_ebitda_multiple=8.3, payer_regime="medicare_heavy"),
    # Specialty
    Comparable("c11", "Cardiovascular specialty hospital", 2022,
               "specialty", "Florida", ev_m=380, ebitda_m=32,
               ev_ebitda_multiple=11.9, payer_regime="commercial_heavy"),
    Comparable("c12", "Orthopedic specialty", 2023,
               "specialty", "Northeast", ev_m=290, ebitda_m=27,
               ev_ebitda_multiple=10.7, payer_regime="commercial_heavy"),
    # Outpatient / physician practice
    Comparable("c13", "Dermatology MSO", 2023,
               "outpatient", "National", ev_m=850, ebitda_m=62,
               ev_ebitda_multiple=13.7, payer_regime="commercial_heavy"),
    Comparable("c14", "Dental MSO", 2022,
               "outpatient", "Midwest", ev_m=340, ebitda_m=28,
               ev_ebitda_multiple=12.1, payer_regime="commercial_heavy"),
    Comparable("c15", "Primary-care MSO (VBC)", 2023,
               "outpatient", "Arizona", ev_m=620, ebitda_m=48,
               ev_ebitda_multiple=12.9, payer_regime="medicare_heavy"),
    # Critical access
    Comparable("c16", "Rural CAH consolidation", 2022,
               "critical_access", "Appalachia", ev_m=95, ebitda_m=12,
               ev_ebitda_multiple=7.9, payer_regime="govt_heavy"),
]


def _size_bucket(ebitda_m: Optional[float]) -> Optional[str]:
    if ebitda_m is None:
        return None
    if ebitda_m < 10:
        return "small"
    if ebitda_m < 25:
        return "lower_mid"
    if ebitda_m < 75:
        return "mid"
    if ebitda_m < 200:
        return "upper_mid"
    return "large"


# ── Filtering ───────────────────────────────────────────────────────

def filter_comps(
    *,
    sector: Optional[str] = None,
    payer_regime: Optional[str] = None,
    size_bucket: Optional[str] = None,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
) -> List[Comparable]:
    """Filter the comp registry by any combination of attributes."""
    out = COMPS
    if sector:
        out = [c for c in out if c.sector == sector.lower().strip()]
    if payer_regime:
        out = [c for c in out if c.payer_regime == payer_regime]
    if size_bucket:
        out = [c for c in out if _size_bucket(c.ebitda_m) == size_bucket]
    if min_year is not None:
        out = [c for c in out if c.close_year >= min_year]
    if max_year is not None:
        out = [c for c in out if c.close_year <= max_year]
    return list(out)


# ── Stats ───────────────────────────────────────────────────────────

def _median(values: List[float]) -> Optional[float]:
    clean = sorted(v for v in values if v is not None)
    if not clean:
        return None
    n = len(clean)
    if n % 2 == 1:
        return clean[n // 2]
    return 0.5 * (clean[n // 2 - 1] + clean[n // 2])


def multiple_stats(comps: List[Comparable]) -> Dict[str, Any]:
    """Return min / median / mean / max of the EV/EBITDA multiple
    for a comp set."""
    vals = [c.ev_ebitda_multiple for c in comps if c.ev_ebitda_multiple is not None]
    if not vals:
        return {"n": 0}
    vals_sorted = sorted(vals)
    return {
        "n": len(vals),
        "min": vals_sorted[0],
        "median": _median(vals),
        "mean": sum(vals) / len(vals),
        "max": vals_sorted[-1],
    }


def position_in_comps(
    modeled_multiple: float,
    comps: List[Comparable],
) -> Dict[str, Any]:
    """Return percentile placement of ``modeled_multiple`` in a comp set."""
    vals = sorted(c.ev_ebitda_multiple for c in comps
                  if c.ev_ebitda_multiple is not None)
    if not vals:
        return {"percentile": None, "n": 0}
    # Count values below.
    below = sum(1 for v in vals if v < modeled_multiple)
    percentile = int(round(100 * below / len(vals)))
    commentary: str
    if percentile >= 85:
        commentary = (f"Modeled multiple is above the ~85th percentile of comps — "
                      "above ceiling territory.")
    elif percentile >= 60:
        commentary = (f"Modeled multiple is above median — defensible with a named alpha.")
    elif percentile >= 40:
        commentary = "Modeled multiple is at the peer median."
    else:
        commentary = "Modeled multiple is below the peer median — worth a sanity check on entry."
    return {
        "percentile": percentile,
        "n": len(vals),
        "commentary": commentary,
    }
