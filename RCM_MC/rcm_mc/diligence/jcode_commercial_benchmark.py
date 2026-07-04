"""J-code commercial reimbursement benchmark, 2022–2026.

The commercial buy-and-bill benchmark a deal team wants by HCPCS J-code
across the hold window — built from PUBLIC anchors only, because the
commercial-claims product a team would otherwise reach for (Merative
MarketScan, formerly IBM Watson Health / Truven) is licensed and not
vendored here. No commercial-claims dollar is fabricated.

Two public anchors carry the benchmark:

* **Commercial-as-%-of-Medicare multiples** — the published payer-rate
  benchmarks (HCCI, CBO, KFF, MedPAC, Milliman). Commercial buy-and-bill
  for clinician-administered drugs benchmarks off the Medicare ASP+6
  payment limit; these are the documented multiples.

* **Biosimilar-driven ASP erosion** — the molecule-level price
  trajectory 2022→2026. Each J-code carries its real biosimilar-entry
  year (public FDA approval/launch facts); the per-year index models the
  blended-ASP erosion that follows entry (sole-source molecules hold;
  plasma-derived IVIG drifts up on supply tightness). The trajectory is
  an illustrative public model, labelled as such.

When a licensed MarketScan extract is available, drop it in and the
commercial allowed-amount columns replace the modeled index — the schema
slot is documented in :func:`marketscan_ingest_schema`.
"""
from __future__ import annotations

import functools
from typing import Any

from ..data.cms_asp_pricing import INFUSION_HCPCS

YEARS = [2022, 2023, 2024, 2025, 2026]

#: Published commercial-rate benchmarks as a multiple of Medicare. These
#: are the professional/drug-rate ratios cited in the PFS source note —
#: real, sourced, and the basis for the commercial column.
COMMERCIAL_MULTIPLES = [
    {"source": "HCCI", "multiple": 1.22,
     "basis": "Health Care Cost Institute commercial vs Medicare"},
    {"source": "CBO", "multiple": 1.29,
     "basis": "Congressional Budget Office hospital/physician analysis"},
    {"source": "MedPAC", "multiple": 1.37,
     "basis": "MedPAC commercial PPO vs Medicare (134–140% band)"},
    {"source": "KFF", "multiple": 1.43,
     "basis": "Kaiser Family Foundation relative-price studies"},
    {"source": "Milliman", "multiple": 1.48,
     "basis": "Milliman commercial reimbursement benchmark"},
]

#: Biosimilar / competition status per molecule. ``entry`` is the year
#: the first biosimilar (or competing reference) reached the US market —
#: public FDA approval/launch facts. ``trend``: ``eroding`` (biosimilar
#: competition), ``stable`` (sole-source), ``rising`` (supply-constrained
#: plasma-derived IVIG). ``agents`` names the competition.
_BIOSIMILAR: dict[str, dict[str, Any]] = {
    "J1745": {"entry": 2016, "trend": "eroding",
              "agents": "Inflectra (Q5103) 2016, Renflexis (Q5104) 2017"},
    "J3380": {"entry": None, "trend": "stable", "agents": "no biosimilar"},
    "J9312": {"entry": 2019, "trend": "eroding",
              "agents": "Truxima, Ruxience (2019)"},
    "J2350": {"entry": None, "trend": "stable", "agents": "no biosimilar"},
    "J2323": {"entry": 2024, "trend": "eroding",
              "agents": "Tyruko (natalizumab biosimilar, 2024)"},
    "J0490": {"entry": None, "trend": "stable", "agents": "no biosimilar"},
    "J1300": {"entry": 2025, "trend": "eroding",
              "agents": "Bkemv, Epysqli (eculizumab biosimilars, 2025)"},
    "J1569": {"entry": None, "trend": "rising",
              "agents": "plasma-derived — no biosimilar; supply-tight"},
    "J1599": {"entry": None, "trend": "rising",
              "agents": "plasma-derived — no biosimilar; supply-tight"},
    "J9035": {"entry": 2019, "trend": "eroding",
              "agents": "Mvasi, Zirabev (bevacizumab biosimilars, 2019)"},
    "J0897": {"entry": 2025, "trend": "eroding",
              "agents": "Wyost / Jubbonti (denosumab biosimilars, 2025)"},
    "J2505": {"entry": 2018, "trend": "eroding",
              "agents": "Fulphila, Udenyca (pegfilgrastim biosimilars, 2018)"},
}


def _asp_index(spec: dict[str, Any], year: int) -> float:
    """Modeled blended-ASP index (pre-competition molecule = 100) for a
    molecule in a given year. Eroding molecules fall after biosimilar
    entry (~12% the first year, ~7%/yr thereafter, floored at 48);
    sole-source holds; IVIG drifts up ~3%/yr on supply tightness."""
    trend = spec.get("trend")
    if trend == "rising":
        return round(100.0 * (1.03 ** (year - 2022)), 1)
    entry = spec.get("entry")
    if trend != "eroding" or entry is None or year < entry:
        return 100.0
    idx = 100.0
    for k in range(1, year - entry + 1):
        idx *= 0.88 if k == 1 else 0.93
    return round(max(48.0, idx), 1)


@functools.lru_cache(maxsize=1)
def jcode_commercial_benchmark() -> dict[str, Any]:
    """The J-code × year commercial benchmark. Cached — every input is a
    documented constant."""
    lo = min(m["multiple"] for m in COMMERCIAL_MULTIPLES)
    hi = max(m["multiple"] for m in COMMERCIAL_MULTIPLES)
    mid = round(sum(m["multiple"] for m in COMMERCIAL_MULTIPLES)
                / len(COMMERCIAL_MULTIPLES), 3)

    rows = []
    for c in INFUSION_HCPCS:
        spec = _BIOSIMILAR.get(c["hcpcs"], {"entry": None, "trend": "stable",
                                            "agents": "—"})
        index_by_year = {y: _asp_index(spec, y) for y in YEARS}
        change = round(index_by_year[YEARS[-1]] - index_by_year[YEARS[0]], 1)
        rows.append({
            "hcpcs": c["hcpcs"], "drug": c["drug"], "unit": c["unit"],
            "category": c["category"], "channel": c["channel"],
            "biosimilar_entry": spec.get("entry"),
            "trend": spec.get("trend"),
            "competition": spec.get("agents"),
            "index_by_year": index_by_year,
            "change_22_26": change,
        })
    # Eroding molecules first (the price story), then by 2022 index.
    rows.sort(key=lambda r: (r["change_22_26"], -r["index_by_year"][2022]))

    return {
        "years": YEARS,
        "jcodes": rows,
        "multiples": COMMERCIAL_MULTIPLES,
        "multiple_band": {"lo": lo, "mid": mid, "hi": hi},
        "eroding_count": sum(1 for r in rows if r["trend"] == "eroding"),
        "method_note": (
            "Commercial buy-and-bill benchmarks off the Medicare ASP+6 "
            "payment limit (sequestered to ~ASP+4.3%); the published "
            "commercial multiples (HCCI 122% … Milliman 148%) bound the "
            "commercial allowed amount. The 2022–2026 index is a MODELED "
            "blended-ASP trajectory keyed to each molecule's real "
            "biosimilar-entry year — illustrative, not commercial-claims "
            "data. Drop a licensed Merative MarketScan extract in to "
            "replace the index with actual commercial allowed amounts."),
        "marketscan_note": (
            "Merative MarketScan (commercial + Medicare-supplemental "
            "claims; formerly IBM Watson Health / Truven) is the licensed "
            "source for actual commercial allowed amounts and utilization "
            "by J-code. It is not vendored here and cannot be fetched — "
            "see marketscan_ingest_schema() for the load slot."),
    }


def marketscan_ingest_schema() -> dict[str, Any]:
    """The documented schema a licensed Merative MarketScan extract must
    provide to replace the modeled index with real commercial allowed
    amounts. Mirrors the gazetteer / live-ASP ingestion pattern."""
    return {
        "filename": "vendor/marketscan/jcode_commercial_<year>.csv",
        "columns": [
            "hcpcs", "year", "n_claims", "total_units",
            "mean_allowed_per_unit", "median_allowed_per_unit",
            "mean_allowed_per_claim",
        ],
        "grain": "one row per (hcpcs, year)",
        "note": "Allowed amounts are the plan-allowed (contracted) "
                "commercial rate, not billed charges. License required; "
                "not redistributable.",
    }
