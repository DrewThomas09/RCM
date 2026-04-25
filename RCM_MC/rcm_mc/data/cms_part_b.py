"""Medicare Part B Physician & Other Practitioners utilization.

Public source: ``data.cms.gov/provider-summary-by-type-of-service/
medicare-physician-other-practitioners-by-provider-and-service``.
One row per (NPI, HCPCS code, service-place) tuple.

Per-provider derived metrics:

  • total_services_billed: Σ services rendered
  • total_medicare_payment_mm: Σ Medicare-allowed * services / 1M
  • top_hcpcs_share: largest single-procedure share of services
  • procedure_concentration: Herfindahl across HCPCS codes
  • avg_payment_per_service: weighted-mean Medicare allowed amount

These slot into the screening dashboard's risk-factor list +
the comparable-deal feature vector for any physician-group or
MSO target.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class PartBRecord:
    """One (NPI × HCPCS × place_of_service) row."""
    npi: str
    hcpcs_code: str
    hcpcs_description: str = ""
    place_of_service: str = ""    # F (facility) | O (office)
    n_services: Optional[int] = None
    n_unique_beneficiaries: Optional[int] = None
    avg_medicare_allowed: Optional[float] = None
    avg_medicare_payment: Optional[float] = None
    provider_specialty: str = ""


@dataclass
class PartBProviderMetrics:
    """Per-provider derived metrics from Part B utilization."""
    npi: str
    specialty: str = ""
    total_services_billed: int = 0
    total_medicare_payment_mm: float = 0.0
    n_unique_hcpcs: int = 0
    top_hcpcs_code: str = ""
    top_hcpcs_share: float = 0.0
    procedure_concentration: float = 0.0   # Herfindahl
    avg_payment_per_service: float = 0.0


def _safe_int(v: Any) -> Optional[int]:
    if v is None or v == "":
        return None
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None


def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    s = str(v).strip()
    if s.lower() in ("not available", "n/a", "na"):
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _pick(row: Dict[str, Any], *names: str) -> Any:
    for n in names:
        if n in row and row[n] not in (None, ""):
            return row[n]
    return None


def parse_part_b_csv(path: Any) -> Iterable[PartBRecord]:
    """Stream-parse the CMS Part B Provider/Service file.

    Column-name candidates per axis (CMS headers vary across
    publication years): we accept several aliases.
    """
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(f"Part B CSV not found at {p}")
    with p.open("r", encoding="utf-8", errors="replace",
                newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            npi = str(_pick(row, "Rndrng_NPI", "NPI") or "").strip()
            hcpcs = str(_pick(
                row, "HCPCS_Cd", "HCPCS_Code") or "").strip()
            if not (npi and hcpcs):
                continue
            yield PartBRecord(
                npi=npi,
                hcpcs_code=hcpcs,
                hcpcs_description=str(_pick(
                    row, "HCPCS_Desc",
                    "HCPCS_Description") or "").strip(),
                place_of_service=str(_pick(
                    row, "Place_Of_Srvc") or "").strip().upper(),
                n_services=_safe_int(_pick(
                    row, "Tot_Srvcs", "Total_Services")),
                n_unique_beneficiaries=_safe_int(_pick(
                    row, "Tot_Benes", "Total_Beneficiaries")),
                avg_medicare_allowed=_safe_float(_pick(
                    row, "Avg_Mdcr_Alowd_Amt",
                    "Average_Medicare_Allowed_Amount")),
                avg_medicare_payment=_safe_float(_pick(
                    row, "Avg_Mdcr_Pymt_Amt",
                    "Average_Medicare_Payment_Amount")),
                provider_specialty=str(_pick(
                    row, "Rndrng_Prvdr_Type",
                    "Provider_Type") or "").strip(),
            )


def compute_part_b_provider_metrics(
    records: Iterable[PartBRecord],
) -> Dict[str, PartBProviderMetrics]:
    """Aggregate per-NPI metrics from a stream of Part B rows.

    Returns {npi → PartBProviderMetrics}.
    """
    by_npi: Dict[str, Dict[str, Any]] = {}
    for r in records:
        if r.n_services is None or r.n_services <= 0:
            continue
        bucket = by_npi.setdefault(r.npi, {
            "specialty": r.provider_specialty,
            "total_services": 0,
            "total_payment": 0.0,
            "by_hcpcs": {},
            "service_payment_sum": 0.0,
        })
        # Specialty: take the most-recently-seen non-empty value
        if r.provider_specialty:
            bucket["specialty"] = r.provider_specialty
        bucket["total_services"] += r.n_services
        per_payment = (r.avg_medicare_payment
                       if r.avg_medicare_payment is not None
                       else 0.0)
        bucket["total_payment"] += per_payment * r.n_services
        bucket["service_payment_sum"] += (
            (r.avg_medicare_allowed or 0.0) * r.n_services)
        bucket["by_hcpcs"][r.hcpcs_code] = (
            bucket["by_hcpcs"].get(r.hcpcs_code, 0)
            + r.n_services)

    out: Dict[str, PartBProviderMetrics] = {}
    for npi, bucket in by_npi.items():
        total = bucket["total_services"]
        by_hcpcs = bucket["by_hcpcs"]
        # Top HCPCS
        if by_hcpcs:
            top_code = max(by_hcpcs, key=by_hcpcs.get)
            top_share = by_hcpcs[top_code] / total
            # Herfindahl (sum of squared shares)
            hh = sum((c / total) ** 2 for c in by_hcpcs.values())
        else:
            top_code = ""
            top_share = 0.0
            hh = 0.0
        avg_per = (bucket["total_payment"] / total
                   if total else 0.0)
        out[npi] = PartBProviderMetrics(
            npi=npi,
            specialty=bucket["specialty"],
            total_services_billed=int(total),
            total_medicare_payment_mm=round(
                bucket["total_payment"] / 1_000_000, 4),
            n_unique_hcpcs=len(by_hcpcs),
            top_hcpcs_code=top_code,
            top_hcpcs_share=round(top_share, 4),
            procedure_concentration=round(hh, 4),
            avg_payment_per_service=round(avg_per, 2),
        )
    return out


def _ensure_table(con: Any) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS cms_part_b_metrics (
            npi TEXT PRIMARY KEY,
            specialty TEXT,
            total_services_billed INTEGER,
            total_medicare_payment_mm REAL,
            n_unique_hcpcs INTEGER,
            top_hcpcs_code TEXT,
            top_hcpcs_share REAL,
            procedure_concentration REAL,
            avg_payment_per_service REAL,
            loaded_at TEXT NOT NULL
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS "
        "idx_part_b_specialty "
        "ON cms_part_b_metrics(specialty)"
    )


def load_part_b_metrics(
    store: Any,
    metrics: Dict[str, PartBProviderMetrics],
) -> int:
    """Persist per-NPI metrics."""
    store.init_db()
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    with store.connect() as con:
        _ensure_table(con)
        con.execute("BEGIN IMMEDIATE")
        try:
            for npi, m in metrics.items():
                con.execute(
                    "INSERT OR REPLACE INTO cms_part_b_metrics "
                    "(npi, specialty, total_services_billed, "
                    " total_medicare_payment_mm, "
                    " n_unique_hcpcs, top_hcpcs_code, "
                    " top_hcpcs_share, procedure_concentration, "
                    " avg_payment_per_service, loaded_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (m.npi, m.specialty, m.total_services_billed,
                     m.total_medicare_payment_mm,
                     m.n_unique_hcpcs, m.top_hcpcs_code,
                     m.top_hcpcs_share,
                     m.procedure_concentration,
                     m.avg_payment_per_service, now),
                )
                n += 1
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n


def get_part_b_metrics(store: Any, npi: str,
                       ) -> Optional[Dict[str, Any]]:
    if not npi:
        return None
    with store.connect() as con:
        _ensure_table(con)
        row = con.execute(
            "SELECT * FROM cms_part_b_metrics WHERE npi = ?",
            (str(npi).strip(),),
        ).fetchone()
    return dict(row) if row else None
