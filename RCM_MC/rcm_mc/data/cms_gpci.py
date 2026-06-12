"""CMS Physician Fee Schedule GPCIs — geography is a price term.

Vendors the official CY2025 GPCI file (Addendum E, "FINAL CY 2025
GEOGRAPHIC PRACTICE COST INDICES (GPCIs) BY STATE AND MEDICARE
LOCALITY", distributed in the CMS RVU25 package) and exposes:

  • the per-locality work / PE / MP GPCIs (public CMS facts);
  • a computed composite GAF per locality — the standard one-number
    read of how a locality pays vs the national PFS amount; and
  • a state-level roll-up (unweighted mean across the state's
    localities, with the locality count carried so multi-locality
    states are read correctly).

The composite uses the published national cost-share weights (work
50.866% / PE 44.839% / MP 4.295%). CMS publishes its own GAF table in
Addendum D; this recompute matches it to ~±0.001 — labeled as computed
so nothing is misrepresented as the Addendum D file itself. The work
GPCI column carries the statutory 1.0 floor (and the 1.5 Alaska
floor), as published.
"""
from __future__ import annotations

import csv
import functools
from pathlib import Path
from typing import Any, Dict, List

#: Published national PFS cost-share weights used for the composite GAF.
GPCI_COST_WEIGHTS = {"work": 0.50866, "pe": 0.44839, "mp": 0.04295}

_VENDOR = Path(__file__).resolve().parent / "vendor" / "cms_gpci"
_FILE = _VENDOR / "GPCI2025.csv"


def composite_gaf(work: float, pe: float, mp: float) -> float:
    """Composite GAF from the three GPCIs at the published weights."""
    w = GPCI_COST_WEIGHTS
    return round(work * w["work"] + pe * w["pe"] + mp * w["mp"], 4)


@functools.lru_cache(maxsize=1)
def gpci_localities() -> List[Dict[str, Any]]:
    """All CY2025 PFS payment localities with GPCIs + computed GAF.
    Parsed straight from the vendored CMS Addendum E file."""
    out: List[Dict[str, Any]] = []
    with _FILE.open(newline="") as f:
        rows = list(csv.reader(f))
    start = next(i for i, r in enumerate(rows)
                 if r and r[0].startswith("Medicare"))
    for r in rows[start + 1:]:
        if len(r) < 7 or not r[1].strip():
            continue
        try:
            work, pe, mp = float(r[4]), float(r[5]), float(r[6])
        except (TypeError, ValueError):
            continue
        out.append({
            "mac": r[0].strip(),
            "state": r[1].strip(),
            "locality": r[2].strip().zfill(2),
            "name": r[3].strip(),
            "work": work, "pe": pe, "mp": mp,
            "gaf": composite_gaf(work, pe, mp),
        })
    return out


@functools.lru_cache(maxsize=1)
def state_gaf() -> Dict[str, Dict[str, Any]]:
    """State → {gaf, localities} — the unweighted mean composite GAF
    across the state's PFS localities (single-locality states are
    exact; CA/NY/TX means are labeled with their locality counts).
    Excludes the territories so the 50-state + DC map reads cleanly."""
    agg: Dict[str, List[float]] = {}
    for loc in gpci_localities():
        if loc["state"] in ("PR", "VI"):
            continue
        agg.setdefault(loc["state"], []).append(loc["gaf"])
    return {
        s: {"gaf": round(sum(v) / len(v), 4), "localities": len(v)}
        for s, v in sorted(agg.items())
    }


def texas_localities() -> List[Dict[str, Any]]:
    """The eight Texas PFS payment localities, GAF-ranked. San Antonio,
    El Paso and the RGV have no locality of their own — they pay
    Rest of Texas, the lowest rate in the state."""
    tx = [dict(loc) for loc in gpci_localities() if loc["state"] == "TX"]
    tx.sort(key=lambda r: -r["gaf"])
    return tx


GPCI_SOURCE_NOTE = (
    "CMS CY2025 PFS GPCI file (Addendum E, RVU25A package; the October "
    "RVU25D release is byte-identical, so these values held all year). "
    "Work GPCI carries the statutory 1.0 floor (1.5 in Alaska). The "
    "composite GAF is COMPUTED at the published cost-share weights "
    "(work 50.9% / PE 44.8% / MP 4.3%), not read from Addendum D.")
