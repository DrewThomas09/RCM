"""HCRIS data source loader.

Wraps the existing :mod:`rcm_mc.data.hcris` parsing layer (which already
knows how to pull worksheet coordinates out of the CMS bundles) and
normalizes the output into :class:`HCRISRecord` rows and
``hospital_benchmarks`` inserts.

The older module is great for one-off CCN lookups and the shipped
pre-parsed CSV; this module is the benchmark-database loader used by
:mod:`rcm_mc.data.data_refresh`. Two separate modules so neither path
has to accommodate the other's constraints.

Download URL is CMS's 2024 Cost Report data portal:
    https://data.cms.gov/provider-compliance/cost-report/hospital-provider-cost-report
The actual downloadable artifact is the yearly ``HOSP10FY{year}.zip``
at ``downloads.cms.gov`` — same file :func:`rcm_mc.data.hcris.refresh_hcris`
already consumes.
"""
from __future__ import annotations

import csv
import gzip
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from . import _cms_download
from .hcris import HCRIS_URL_TEMPLATE, DEFAULT_DATA_PATH

logger = logging.getLogger(__name__)


# ── Record shape ──────────────────────────────────────────────────────

@dataclass
class HCRISRecord:
    """Normalized HCRIS facility row. See module docstring for source
    worksheets / line numbers.

    Many fields are ``Optional`` — HCRIS bundles drop individual
    worksheets for small rural providers, and partners expect the
    downstream UI to tolerate that (dash = missing, not zero).
    """
    provider_id: str                                 # CMS CCN
    fiscal_year_end: Optional[str] = None            # ISO date
    fiscal_year: Optional[int] = None

    bed_count: Optional[int] = None
    total_discharges: Optional[int] = None
    case_mix_index: Optional[float] = None

    gross_patient_revenue: Optional[float] = None
    net_patient_revenue: Optional[float] = None
    total_operating_expenses: Optional[float] = None
    operating_margin: Optional[float] = None

    payer_mix: Dict[str, float] = field(default_factory=dict)
    bad_debt: Optional[float] = None
    charity_care: Optional[float] = None
    uncompensated_care: Optional[float] = None
    dsh_payments: Optional[float] = None
    ime_payments: Optional[float] = None
    teaching_status: Optional[bool] = None
    urban_rural: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    system_affiliation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    # Metrics we flatten into hospital_benchmarks rows. Strings land in
    # text_value (see data_refresh.save_benchmarks); numerics in value.
    _BENCHMARK_FIELDS: Tuple[str, ...] = (
        "bed_count", "total_discharges", "case_mix_index",
        "gross_patient_revenue", "net_patient_revenue",
        "total_operating_expenses", "operating_margin",
        "bad_debt", "charity_care", "uncompensated_care",
        "dsh_payments", "ime_payments",
        "state", "city", "urban_rural", "system_affiliation",
    )

    def benchmark_rows(self, *, period: Optional[str] = None) -> List[Dict[str, Any]]:
        """Flatten into hospital_benchmarks-shaped dicts.

        Emits one row per non-null field in ``_BENCHMARK_FIELDS`` plus
        the four payer-mix percentages, plus a ``teaching_status``
        boolean encoded as 1.0 / 0.0.
        """
        per = period or (self.fiscal_year_end or (str(self.fiscal_year) if self.fiscal_year else ""))
        out: List[Dict[str, Any]] = []
        for f in self._BENCHMARK_FIELDS:
            v = getattr(self, f, None)
            if v is None or v == "":
                continue
            out.append({
                "provider_id": self.provider_id,
                "metric_key": f,
                "value": v,
                "period": per,
            })
        if self.teaching_status is not None:
            out.append({
                "provider_id": self.provider_id,
                "metric_key": "teaching_status",
                "value": 1.0 if self.teaching_status else 0.0,
                "period": per,
            })
        for payer, frac in (self.payer_mix or {}).items():
            if frac is None:
                continue
            out.append({
                "provider_id": self.provider_id,
                "metric_key": f"payer_mix_{payer}_pct",
                "value": float(frac),
                "period": per,
            })
        return out


# ── Download ──────────────────────────────────────────────────────────

def download_hcris(
    year: Optional[int] = None,
    *,
    dest: Optional[Path] = None,
    overwrite: bool = False,
) -> Path:
    """Fetch the CMS HCRIS fiscal-year bundle to the local cache.

    ``year=None`` resolves to the most recent year we expect to be
    published. CMS publishes 2-3 years behind (2024 data is usually
    posted mid-2025); we default to two calendar years before today so
    we don't chase a 404 on a year CMS hasn't cut yet.
    """
    from datetime import datetime, timezone
    if year is None:
        year = datetime.now(timezone.utc).year - 2
    dest = Path(dest) if dest else _cms_download.cache_dir("hcris") / f"HOSP10FY{year}.zip"
    url = HCRIS_URL_TEMPLATE.format(year=year)
    return _cms_download.fetch_url(url, dest, overwrite=overwrite)


# ── Parse ─────────────────────────────────────────────────────────────

# Column aliases for the shipped ``hcris.csv.gz`` + generic CMS data-portal
# CSVs. Key = HCRISRecord field; value = acceptable CSV header names.
_ALIASES: Dict[str, Tuple[str, ...]] = {
    "provider_id":              ("ccn", "provider_id", "provider_ccn", "prvdr_num"),
    "fiscal_year_end":          ("fy_end_dt", "fiscal_year_end", "fy_end"),
    "fiscal_year":              ("fiscal_year", "fy", "year"),
    "bed_count":                ("beds", "bed_count", "num_beds"),
    "total_discharges":         ("total_discharges", "discharges"),
    "case_mix_index":           ("case_mix_index", "cmi"),
    "gross_patient_revenue":    ("gross_patient_revenue", "gross_revenue"),
    "net_patient_revenue":      ("net_patient_revenue", "npr", "net_revenue"),
    "total_operating_expenses": ("operating_expenses", "total_operating_expenses"),
    "bad_debt":                 ("bad_debt",),
    "charity_care":             ("charity_care",),
    "uncompensated_care":       ("uncompensated_care",),
    "dsh_payments":             ("dsh_payments", "dsh"),
    "ime_payments":             ("ime_payments", "ime"),
    "state":                    ("state",),
    "city":                     ("city",),
    "system_affiliation":       ("system_affiliation", "chain_name", "system"),
    "urban_rural":              ("urban_rural", "cbsa_type"),
}


def _pick(row: Dict[str, Any], aliases: Tuple[str, ...]) -> Any:
    for a in aliases:
        if a in row and row[a] not in (None, ""):
            return row[a]
    return None


def _to_float(x: Any) -> Optional[float]:
    if x is None or x == "":
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _to_int(x: Any) -> Optional[int]:
    f = _to_float(x)
    return int(f) if f is not None else None


def _open_text(path: Path):
    """Open .csv or .csv.gz as a text iterator. Assumes UTF-8."""
    path = Path(path)
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return open(path, "r", encoding="utf-8", newline="")


def parse_hcris(filepath: Path) -> List[HCRISRecord]:
    """Parse a pre-normalized HCRIS CSV (the shipped ``hcris.csv.gz``
    or a data.cms.gov-portal export) into :class:`HCRISRecord` rows.

    This is the cheap path — it doesn't re-parse the raw worksheet
    coordinates. For the raw ``HOSP10FY{year}.zip`` flow, the existing
    :func:`rcm_mc.data.hcris.refresh_hcris` builds a CSV we can then
    ingest here. That two-step is on purpose: the zip→CSV transform is
    expensive, and you only want it once per CMS release.
    """
    records: List[HCRISRecord] = []
    with _open_text(filepath) as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            pid = _pick(row, _ALIASES["provider_id"])
            if not pid:
                continue
            medicare_day_pct = _to_float(row.get("medicare_day_pct"))
            medicaid_day_pct = _to_float(row.get("medicaid_day_pct"))
            # Residual goes to the "other" bucket — not a great proxy
            # for commercial vs self-pay, but HCRIS doesn't split those.
            # Downstream callers should prefer IRS 990 for non-profit
            # payer splits.
            payer_mix: Dict[str, float] = {}
            if medicare_day_pct is not None:
                payer_mix["medicare"] = float(medicare_day_pct)
            if medicaid_day_pct is not None:
                payer_mix["medicaid"] = float(medicaid_day_pct)
            other = None
            if medicare_day_pct is not None and medicaid_day_pct is not None:
                other = max(0.0, 1.0 - medicare_day_pct - medicaid_day_pct)
                payer_mix["other"] = float(other)

            ime = _to_float(_pick(row, _ALIASES["ime_payments"]))
            teaching = (ime is not None and ime > 0.0) if ime is not None else None

            npr = _to_float(_pick(row, _ALIASES["net_patient_revenue"]))
            opex = _to_float(_pick(row, _ALIASES["total_operating_expenses"]))
            op_margin = None
            if npr and npr > 0 and opex is not None:
                op_margin = (npr - opex) / npr

            records.append(HCRISRecord(
                provider_id=str(pid).strip(),
                fiscal_year_end=(_pick(row, _ALIASES["fiscal_year_end"]) or None),
                fiscal_year=_to_int(_pick(row, _ALIASES["fiscal_year"])),
                bed_count=_to_int(_pick(row, _ALIASES["bed_count"])),
                total_discharges=_to_int(_pick(row, _ALIASES["total_discharges"])),
                case_mix_index=_to_float(_pick(row, _ALIASES["case_mix_index"])),
                gross_patient_revenue=_to_float(_pick(row, _ALIASES["gross_patient_revenue"])),
                net_patient_revenue=npr,
                total_operating_expenses=opex,
                operating_margin=op_margin,
                payer_mix=payer_mix,
                bad_debt=_to_float(_pick(row, _ALIASES["bad_debt"])),
                charity_care=_to_float(_pick(row, _ALIASES["charity_care"])),
                uncompensated_care=_to_float(_pick(row, _ALIASES["uncompensated_care"])),
                dsh_payments=_to_float(_pick(row, _ALIASES["dsh_payments"])),
                ime_payments=ime,
                teaching_status=teaching,
                urban_rural=(_pick(row, _ALIASES["urban_rural"]) or None),
                state=(_pick(row, _ALIASES["state"]) or None),
                city=(_pick(row, _ALIASES["city"]) or None),
                system_affiliation=(_pick(row, _ALIASES["system_affiliation"]) or None),
            ))
    return records


# ── Load ──────────────────────────────────────────────────────────────

def load_hcris_to_store(
    store: Any,
    records: Iterable[HCRISRecord],
    *,
    period: Optional[str] = None,
) -> int:
    """Insert each record's flattened benchmark rows. Returns the number
    of (provider_id, metric_key) pairs written.
    """
    from .data_refresh import save_benchmarks
    all_rows: List[Dict[str, Any]] = []
    for rec in records:
        all_rows.extend(rec.benchmark_rows(period=period))
    return save_benchmarks(store, all_rows, source="HCRIS", period=period)


# ── Refresh orchestration entry point ────────────────────────────────

def refresh_hcris_source(store: Any) -> int:
    """Called by :func:`rcm_mc.data.data_refresh.refresh_all_sources`.

    Uses the shipped ``hcris.csv.gz`` as the authoritative source (it's
    the product of the existing ``rcm-mc hcris refresh`` pipeline) so
    that a hot refresh doesn't require re-downloading from CMS. Callers
    who actually want fresh data from CMS should run ``rcm-mc hcris
    refresh --year <y>`` first.
    """
    path = Path(DEFAULT_DATA_PATH)
    if not path.is_file():
        raise FileNotFoundError(
            f"Shipped HCRIS dataset missing at {path}. "
            "Run `rcm-mc hcris refresh` to build it."
        )
    records = parse_hcris(path)
    return load_hcris_to_store(store, records)
