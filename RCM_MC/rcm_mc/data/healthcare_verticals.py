"""Healthcare Verticals 2025-2026 — loader over the chart-ready reference bundle.

Reads the committed public-source-synthesis artifacts under
``data/industry_intel/healthcare_verticals_2025_2026/`` (CSVs + the narrative
markdown + chart_specs.json). This is a DIFFERENT provenance class from the
NAICS-keyed licensed-IBISWorld data in ``industry_intel.py``: here the source
kind is ``PUBLIC_SOURCE_SYNTHESIS`` (CMS rules, MedPAC, NIC MAP, USRDS, SAMHSA,
HRSA, CDC ART, PHI, named market-research estimates). It lives in its own
subdirectory so it never mixes into the industry_intel loader (which reads files
directly in its own directory, not recursively).

No runtime network; loaders read committed CSV/JSON/MD only.
"""
from __future__ import annotations

import csv
import functools
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# data/ lives at the repo root (sibling of rcm_mc/), not inside the package.
_DIR = (Path(__file__).resolve().parent.parent.parent
        / "data" / "industry_intel" / "healthcare_verticals_2025_2026")

SOURCE_KIND = "PUBLIC_SOURCE_SYNTHESIS"
ATTRIBUTION = ("Public-source synthesis (CMS payment rules, MedPAC, NIC MAP, "
               "USRDS, SAMHSA, HRSA, CDC/NCHS ART, PHI, company filings)")

# Human-readable group labels keyed by the single-letter group in verticals.csv.
GROUPS = {
    "A": "Long-Term Care & Aging Services",
    "B": "Behavioral Health & Substance Use",
    "C": "Home-Based & Post-Acute Care",
    "D": "Research, Manufacturing & Emerging Therapeutics",
    "E": "Other Specialized Verticals",
}


@functools.lru_cache(maxsize=None)
def _load_csv(name: str) -> List[Dict[str, Any]]:
    p = _DIR / name
    if not p.exists() or not p.read_text().strip():
        return []
    with p.open(newline="") as fh:
        return list(csv.DictReader(fh))


def load_verticals() -> List[Dict[str, Any]]:
    """The 17-vertical index, in file order (Group A→E, then by number)."""
    return _load_csv("verticals.csv")


def vertical_by_id(vertical_id: str) -> Optional[Dict[str, Any]]:
    return next((v for v in load_verticals()
                 if v.get("vertical_id") == vertical_id), None)


def _rows_for(name: str, vertical_id: str) -> List[Dict[str, Any]]:
    rows = _load_csv(name)
    if vertical_id:
        return [r for r in rows if r.get("vertical_id") == vertical_id]
    return rows


def load_payment_updates(vertical_id: str = "") -> List[Dict[str, Any]]:
    return _rows_for("payment_updates_2026.csv", vertical_id)


def load_payment_buildup(vertical_id: str = "") -> List[Dict[str, Any]]:
    return _rows_for("payment_buildup_2026.csv", vertical_id)


def load_unit_economics(vertical_id: str = "") -> List[Dict[str, Any]]:
    return _rows_for("unit_economics.csv", vertical_id)


def load_market_structure(vertical_id: str = "") -> List[Dict[str, Any]]:
    return _rows_for("market_structure.csv", vertical_id)


def load_workforce(vertical_id: str = "") -> List[Dict[str, Any]]:
    return _rows_for("workforce.csv", vertical_id)


def load_sources(vertical_id: str = "") -> List[Dict[str, Any]]:
    return _rows_for("sources.csv", vertical_id)


def load_gene_therapy_prices() -> List[Dict[str, Any]]:
    return _load_csv("gene_therapy_prices.csv")


@functools.lru_cache(maxsize=None)
def load_chart_specs() -> Dict[str, Any]:
    p = _DIR / "chart_specs.json"
    return json.loads(p.read_text()) if p.exists() else {}


@functools.lru_cache(maxsize=None)
def report_markdown() -> str:
    p = _DIR / "healthcare_verticals_2025_2026.md"
    return p.read_text() if p.exists() else ""
