"""FMV benchmark lookups over the public-aggregate library.

Every function that exposes a benchmark return carries a
"public-aggregate placeholder" caveat. The licensed MGMA /
Sullivan Cotter / AMGA data replaces these when licensing is
formalised — do NOT quote these numbers in a partner-signed FMV
opinion.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import yaml


CONTENT_DIR = Path(__file__).parent / "content"


def _load() -> Dict[str, Any]:
    return yaml.safe_load(
        (CONTENT_DIR / "fmv_benchmarks.yaml").read_text("utf-8")
    )


def get_benchmark(
    specialty: str,
    ownership_type: str = "hospital_employed",
) -> Optional[Dict[str, float]]:
    """Return the comp p25/p50/p75/p90 dict for the specialty +
    ownership combo, or None when the specialty isn't on the lattice."""
    content = _load()
    sp = content.get("specialties", {}).get(specialty.upper())
    if not sp:
        return None
    return sp.get(ownership_type) or sp.get("hospital_employed")


def percentile_placement(
    total_comp_usd: float,
    *,
    specialty: str,
    ownership_type: str = "hospital_employed",
) -> Optional[str]:
    """Return placement label:
        'below_p25' | 'p25_to_p50' | 'p50_to_p75' | 'p75_to_p90' |
        'above_p90' | None (unknown specialty)."""
    bench = get_benchmark(specialty, ownership_type)
    if not bench:
        return None
    if total_comp_usd < bench["p25"]:
        return "below_p25"
    if total_comp_usd < bench["p50"]:
        return "p25_to_p50"
    if total_comp_usd < bench["p75"]:
        return "p50_to_p75"
    if total_comp_usd < bench["p90"]:
        return "p75_to_p90"
    return "above_p90"


def comp_per_wrvu_band(
    comp_per_wrvu_val: float,
    *,
    specialty: str,
) -> Optional[str]:
    """Return the comp-per-wRVU percentile band for the specialty,
    same labels as :func:`percentile_placement`."""
    content = _load()
    anchors = content.get("comp_per_wrvu_anchors", {}).get(
        specialty.upper(),
    )
    if not anchors:
        return None
    if comp_per_wrvu_val < anchors["p25"]:
        return "below_p25"
    if comp_per_wrvu_val < anchors["p50"]:
        return "p25_to_p50"
    if comp_per_wrvu_val < anchors["p75"]:
        return "p50_to_p75"
    if comp_per_wrvu_val < anchors["p90"]:
        return "p75_to_p90"
    return "above_p90"


def data_license_status() -> str:
    """Which data class the benchmarks are currently seeded from
    (PUBLIC_AGGREGATES | MGMA_LICENSED | SULLIVAN_COTTER_LICENSED
    | AMGA_LICENSED). Memo templates must surface this alongside
    every quoted number."""
    return str(_load().get("data_license_status", "PUBLIC_AGGREGATES"))
