"""PEdesk Industry Intelligence — loaders over licensed-report-derived data.

Reads the committed derived artifacts under ``data/industry_intel/`` (produced
offline by ``scripts/extract_industry_report_intel.py`` from licensed IBISWorld
reports — raw PDFs are NOT in the repo). All facts carry provenance and a
license note. This is **industry-level context**, not provider-specific data,
and forecasts are report-derived (not PEdesk predictions). See
``docs/industry/INDUSTRY_REPORT_LICENSE_POLICY.md``.

No runtime network; loaders read committed JSON/CSV only.
"""
from __future__ import annotations

import csv
import functools
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# data/ lives at the repo root (sibling of rcm_mc/), not inside the package.
_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "industry_intel"

SOURCE_KIND = "LICENSED_REPORT_DERIVED"
ATTRIBUTION = "Derived from licensed IBISWorld industry report"


@functools.lru_cache(maxsize=None)
def load_industry_reports() -> List[Dict[str, Any]]:
    p = _DIR / "industry_reports.json"
    return json.loads(p.read_text()) if p.exists() else []


@functools.lru_cache(maxsize=None)
def _load_csv(name: str) -> List[Dict[str, Any]]:
    p = _DIR / name
    if not p.exists() or not p.read_text().strip():
        return []
    with p.open(newline="") as fh:
        return list(csv.DictReader(fh))


def _rows_for(name: str, industry_id: str) -> List[Dict[str, Any]]:
    rows = _load_csv(name)
    if industry_id:
        return [r for r in rows if r.get("industry_id") == industry_id]
    return rows


def load_industry_metrics(industry_id: str = "") -> List[Dict[str, Any]]:
    return _rows_for("industry_metrics.csv", industry_id)


def load_industry_segments(industry_id: str = "") -> List[Dict[str, Any]]:
    return _rows_for("industry_segments.csv", industry_id)


def load_industry_drivers(industry_id: str = "") -> List[Dict[str, Any]]:
    return _rows_for("industry_drivers.csv", industry_id)


def load_industry_benchmarks(industry_id: str = "") -> List[Dict[str, Any]]:
    return _rows_for("industry_benchmarks.csv", industry_id)


def load_industry_questions(industry_id: str = "") -> List[Dict[str, Any]]:
    return _rows_for("industry_questions.csv", industry_id)


def load_industry_risks(industry_id: str = "") -> List[Dict[str, Any]]:
    return _rows_for("industry_risks.csv", industry_id)


def report_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    return next((r for r in load_industry_reports() if r.get("slug") == slug), None)


def report_by_id(industry_id: str) -> Optional[Dict[str, Any]]:
    return next((r for r in load_industry_reports() if r.get("industry_id") == industry_id), None)


def industry_for_naics(code: str) -> Optional[Dict[str, Any]]:
    code = str(code).strip()
    for r in load_industry_reports():
        if str(r.get("naics_code")) == code:
            return r
    # prefix match (e.g. 6221 → 622110)
    for r in load_industry_reports():
        if code and str(r.get("naics_code", "")).startswith(code):
            return r
    return None


def industry_for_vertical(vertical_slug: str) -> Optional[Dict[str, Any]]:
    v = (vertical_slug or "").lower()
    for r in load_industry_reports():
        if v in [x.lower() for x in r.get("pedesk_verticals", [])]:
            return r
    return None


def industry_for_keyword(keyword: str) -> List[Dict[str, Any]]:
    k = (keyword or "").lower()
    if not k:
        return []
    out = []
    for r in load_industry_reports():
        hay = " ".join([r.get("title", ""), r.get("slug", ""),
                        " ".join(r.get("included_services", [])),
                        " ".join(r.get("pedesk_verticals", []))]).lower()
        if k in hay:
            out.append(r)
    return out


def industry_intel_sources() -> List[Dict[str, str]]:
    # The provenance registry lives inside the package, under data/vendor/.
    reg = Path(__file__).resolve().parent / "vendor" / "source_registry.csv"
    if not reg.exists():
        return []
    with reg.open(newline="") as fh:
        return [r for r in csv.DictReader(fh)
                if r.get("source_id") == "industry_intel"]
