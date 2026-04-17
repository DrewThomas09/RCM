"""CMS Care Compare / Hospital Compare public-data loader.

Three datasets at data.cms.gov, each a CSV download:

- General Hospital Info  — xubh-q36u: star rating, address, type
- HCAHPS (patient experience) — 632h-zaca
- Complications & Readmissions — ynj2-r877

We merge them into one :class:`CareCompareRecord` per provider_id.
Every provider may be missing some fields — Care Compare only reports
certain measures for facilities that meet CMS's case-volume floor.
"""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from . import _cms_download

logger = logging.getLogger(__name__)


# ── URLs ─────────────────────────────────────────────────────────────

CARE_COMPARE_URLS = {
    "general": "https://data.cms.gov/provider-data/api/1/datastore/query/xubh-q36u/0/download?format=csv",
    "hcahps":  "https://data.cms.gov/provider-data/api/1/datastore/query/632h-zaca/0/download?format=csv",
    "complications": "https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0/download?format=csv",
}


# ── Record ───────────────────────────────────────────────────────────

@dataclass
class CareCompareRecord:
    provider_id: str
    star_rating: Optional[float] = None             # 1-5 overall stars
    readmission_rate: Optional[float] = None        # hospital-wide 30-day
    mortality_rate: Optional[float] = None          # 30-day, composite
    patient_experience_rating: Optional[float] = None   # HCAHPS summary stars (1-5)
    vbp_total_score: Optional[float] = None         # CMS VBP score
    hac_score: Optional[float] = None               # Hospital-Acquired Condition score
    medicare_spending_per_beneficiary: Optional[float] = None   # MSPB ratio

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def benchmark_rows(self, *, period: Optional[str] = None) -> List[Dict[str, Any]]:
        fields = (
            "star_rating", "readmission_rate", "mortality_rate",
            "patient_experience_rating", "vbp_total_score", "hac_score",
            "medicare_spending_per_beneficiary",
        )
        out: List[Dict[str, Any]] = []
        for f in fields:
            v = getattr(self, f)
            if v is None:
                continue
            out.append({
                "provider_id": self.provider_id,
                "metric_key": f,
                "value": v,
                "period": period or "",
            })
        return out


# ── Download ─────────────────────────────────────────────────────────

def download_care_compare(
    *,
    dest_dir: Optional[Path] = None,
    overwrite: bool = False,
) -> Dict[str, Path]:
    """Fetch all three Care Compare datasets into the cache.

    Returns a ``{kind: path}`` map. One failing URL does NOT kill the
    others — we log and carry on so a partial refresh is still useful.
    """
    dest_dir = Path(dest_dir) if dest_dir else _cms_download.cache_dir("care_compare")
    out: Dict[str, Path] = {}
    for kind, url in CARE_COMPARE_URLS.items():
        dest = dest_dir / f"{kind}.csv"
        try:
            _cms_download.fetch_url(url, dest, overwrite=overwrite)
            out[kind] = dest
        except Exception as exc:  # noqa: BLE001
            logger.warning("care_compare/%s fetch failed: %s", kind, exc)
    return out


# ── Parse ────────────────────────────────────────────────────────────

# The CMS Care Compare CSVs quote every cell and use "Not Available"
# for nulls. Tolerate both.
_NULL_SENTINELS = {"", "N/A", "NA", "Not Available", "Not Applicable", "-"}


def _f(x: Any) -> Optional[float]:
    if x is None:
        return None
    s = str(x).strip()
    if s in _NULL_SENTINELS:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _pick(row: Dict[str, Any], *names: str) -> Any:
    for n in names:
        if n in row and row[n] not in (None, ""):
            return row[n]
    # Also try case-insensitive match — CMS has been known to rename
    # CCN to CCN alternately with each dataset release.
    lower = {k.lower(): k for k in row.keys()}
    for n in names:
        k = lower.get(n.lower())
        if k is not None and row[k] not in (None, ""):
            return row[k]
    return None


def parse_care_compare(files: Dict[str, Path] | Path) -> List[CareCompareRecord]:
    """Merge the three Care Compare CSVs into one record per provider.

    Accepts either a dict ``{kind: path}`` (the output of
    :func:`download_care_compare`) or a single path pointing at an
    already-merged "General Hospital Info" CSV (common in tests).
    """
    if isinstance(files, Path) or isinstance(files, str):
        files = {"general": Path(files)}

    by_pid: Dict[str, CareCompareRecord] = {}

    def _ensure(pid: str) -> CareCompareRecord:
        return by_pid.setdefault(pid, CareCompareRecord(provider_id=pid))

    general = files.get("general")
    if general and Path(general).is_file():
        with open(general, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                pid = _pick(row, "Facility ID", "CMS Certification Number (CCN)",
                            "Provider ID", "provider_id")
                if not pid:
                    continue
                rec = _ensure(str(pid).strip())
                rec.star_rating = _f(_pick(row, "Hospital overall rating",
                                           "Overall Rating", "star_rating"))

    hcahps = files.get("hcahps")
    if hcahps and Path(hcahps).is_file():
        with open(hcahps, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                pid = _pick(row, "Facility ID", "Provider ID", "provider_id")
                if not pid:
                    continue
                val = _pick(row, "HCAHPS Answer Percent",
                            "Patient Survey Star Rating", "patient_experience_rating")
                v = _f(val)
                if v is None:
                    continue
                rec = _ensure(str(pid).strip())
                # Keep the first rating we see — CMS files have many
                # measures per provider and the summary star is usually
                # the first row for that provider.
                if rec.patient_experience_rating is None:
                    rec.patient_experience_rating = v

    complications = files.get("complications")
    if complications and Path(complications).is_file():
        with open(complications, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                pid = _pick(row, "Facility ID", "Provider ID", "provider_id")
                if not pid:
                    continue
                rec = _ensure(str(pid).strip())
                readm = _f(_pick(row, "Score", "readmission_rate"))
                # The file has one row per measure; stamp fields when
                # the measure name matches. Heuristic match on a
                # "MORT_30" / "READM_30" style column.
                measure = str(_pick(row, "Measure ID", "Measure Name") or "")
                if "READM" in measure.upper() and rec.readmission_rate is None:
                    rec.readmission_rate = readm
                elif "MORT" in measure.upper() and rec.mortality_rate is None:
                    rec.mortality_rate = readm
                elif "HAC" in measure.upper() and rec.hac_score is None:
                    rec.hac_score = readm
                elif "MSPB" in measure.upper() and rec.medicare_spending_per_beneficiary is None:
                    rec.medicare_spending_per_beneficiary = readm
                elif "VBP" in measure.upper() and rec.vbp_total_score is None:
                    rec.vbp_total_score = readm

    return list(by_pid.values())


# ── Load ─────────────────────────────────────────────────────────────

def load_care_compare_to_store(
    store: Any,
    records: Iterable[CareCompareRecord],
    *,
    period: Optional[str] = None,
) -> int:
    from .data_refresh import save_benchmarks
    all_rows: List[Dict[str, Any]] = []
    for rec in records:
        all_rows.extend(rec.benchmark_rows(period=period))
    return save_benchmarks(store, all_rows, source="CARE_COMPARE", period=period)


# ── Refresh entry point ──────────────────────────────────────────────

def refresh_care_compare_source(store: Any) -> int:
    files = download_care_compare()
    if not files:
        raise RuntimeError("no Care Compare files downloaded")
    records = parse_care_compare(files)
    return load_care_compare_to_store(store, records)
