"""Medicare Inpatient Hospital utilization data loader.

Source: ``data.cms.gov/provider-summary-by-type-of-service/medicare-
inpatient-hospitals``. One row per (provider, DRG). Columns include
``Total Discharges``, ``Average Covered Charges``, ``Average Total
Payments``, ``Average Medicare Payments``.

Per-hospital derived metrics we compute and push into the benchmark
database:

- ``avg_charge_to_payment_ratio`` — weighted by discharges. Large gap
  indicates negotiated-rate discipline; a proxy for payer mix.
- ``top_drg_volume`` — total discharges of the hospital's single largest DRG.
- ``service_line_concentration`` — Herfindahl index across DRGs. High
  (>0.25) means the hospital specializes; low (<0.05) means generalist.
- ``total_medicare_discharges`` — sum across all DRGs for this provider.
"""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from . import _cms_download

logger = logging.getLogger(__name__)


UTILIZATION_URL = (
    "https://data.cms.gov/provider-summary-by-type-of-service/"
    "medicare-inpatient-hospitals/medicare-inpatient-hospitals-by-provider-and-service"
    "/api/1/datastore/query/csv"
)


# ── Record ───────────────────────────────────────────────────────────

@dataclass
class UtilizationRecord:
    """One (provider, DRG) row. Keeping the per-DRG shape in case the
    partner wants a specific service-line drilldown — the derived
    per-hospital metrics in :func:`compute_provider_metrics` are the
    aggregate view.
    """
    provider_id: str
    drg_code: str
    drg_description: str = ""
    total_discharges: Optional[int] = None
    average_covered_charges: Optional[float] = None
    average_total_payments: Optional[float] = None
    average_medicare_payments: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Download ─────────────────────────────────────────────────────────

def download_medicare_utilization(
    *,
    dest: Optional[Path] = None,
    overwrite: bool = False,
) -> Path:
    dest = Path(dest) if dest else _cms_download.cache_dir("utilization") / "medicare_inpatient.csv"
    return _cms_download.fetch_url(UTILIZATION_URL, dest, overwrite=overwrite)


# ── Parse ────────────────────────────────────────────────────────────

def _pick(row: Dict[str, Any], *names: str) -> Any:
    for n in names:
        if n in row and row[n] not in (None, ""):
            return row[n]
    lower = {k.lower(): k for k in row.keys()}
    for n in names:
        k = lower.get(n.lower())
        if k is not None and row[k] not in (None, ""):
            return row[k]
    return None


def _f(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(str(x).replace(",", "").replace("$", "").strip())
    except (TypeError, ValueError):
        return None


def _i(x: Any) -> Optional[int]:
    v = _f(x)
    return int(v) if v is not None else None


def parse_utilization(filepath: Path) -> List[UtilizationRecord]:
    """Parse the CMS IPPS utilization CSV into per-(provider, DRG) rows."""
    out: List[UtilizationRecord] = []
    with open(filepath, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            pid = _pick(row, "Rndrng_Prvdr_CCN", "provider_id", "Provider Id",
                        "Rndrng_Prvdr_Id")
            drg = _pick(row, "DRG_Cd", "drg_code", "DRG Code", "DRG Definition")
            if not pid or not drg:
                continue
            out.append(UtilizationRecord(
                provider_id=str(pid).strip(),
                drg_code=str(drg).strip(),
                drg_description=str(_pick(row, "DRG_Desc", "drg_description",
                                          "DRG Definition") or ""),
                total_discharges=_i(_pick(row, "Tot_Dschrgs", "total_discharges")),
                average_covered_charges=_f(_pick(row, "Avg_Submtd_Cvrd_Chrg",
                                                  "average_covered_charges")),
                average_total_payments=_f(_pick(row, "Avg_Tot_Pymt_Amt",
                                                 "average_total_payments")),
                average_medicare_payments=_f(_pick(row, "Avg_Mdcr_Pymt_Amt",
                                                    "average_medicare_payments")),
            ))
    return out


# ── Derived per-hospital metrics ─────────────────────────────────────

def compute_provider_metrics(records: Iterable[UtilizationRecord]) -> Dict[str, Dict[str, float]]:
    """Aggregate ``UtilizationRecord`` rows into per-provider metrics.

    Returns ``{provider_id: {metric_key: value}}``.
    """
    per: Dict[str, List[UtilizationRecord]] = {}
    for r in records:
        per.setdefault(r.provider_id, []).append(r)

    result: Dict[str, Dict[str, float]] = {}
    for pid, rows in per.items():
        total_discharges = 0
        weighted_ratio_num = 0.0
        weighted_ratio_den = 0
        drg_volumes: Dict[str, int] = {}
        for r in rows:
            d = int(r.total_discharges or 0)
            if d <= 0:
                continue
            total_discharges += d
            drg_volumes[r.drg_code] = drg_volumes.get(r.drg_code, 0) + d
            if r.average_covered_charges and r.average_total_payments:
                if r.average_total_payments > 0:
                    weighted_ratio_num += (r.average_covered_charges / r.average_total_payments) * d
                    weighted_ratio_den += d
        metrics: Dict[str, float] = {}
        if total_discharges > 0:
            metrics["total_medicare_discharges"] = float(total_discharges)
        if weighted_ratio_den > 0:
            metrics["avg_charge_to_payment_ratio"] = weighted_ratio_num / weighted_ratio_den
        if drg_volumes:
            top_drg_volume = max(drg_volumes.values())
            metrics["top_drg_volume"] = float(top_drg_volume)
            if total_discharges > 0:
                # Herfindahl-Hirschman concentration index — 1/n … 1.
                shares = [v / total_discharges for v in drg_volumes.values()]
                hhi = sum(s * s for s in shares)
                metrics["service_line_concentration"] = float(hhi)
        if metrics:
            result[pid] = metrics
    return result


def load_utilization_to_store(
    store: Any,
    records: Iterable[UtilizationRecord],
    *,
    period: Optional[str] = None,
) -> int:
    from .data_refresh import save_benchmarks
    per_provider = compute_provider_metrics(records)
    rows: List[Dict[str, Any]] = []
    for pid, metrics in per_provider.items():
        for metric_key, value in metrics.items():
            rows.append({
                "provider_id": pid,
                "metric_key": metric_key,
                "value": value,
                "period": period or "",
            })
    return save_benchmarks(store, rows, source="UTILIZATION", period=period)


# ── Refresh entry point ──────────────────────────────────────────────

def refresh_utilization_source(store: Any) -> int:
    path = download_medicare_utilization()
    records = parse_utilization(path)
    return load_utilization_to_store(store, records)
