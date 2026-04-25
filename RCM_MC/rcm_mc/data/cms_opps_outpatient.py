"""CMS Medicare Outpatient (OPPS) by Provider and Service.

Public source: ``data.cms.gov/provider-summary-by-type-of-service/
medicare-outpatient-hospitals-by-provider-and-service``. One row
per (CCN, HCPCS code) tuple. Columns include total services,
outpatient services, average submitted charges, average Medicare
payments, beneficiary counts.

Distinct from:
  • Inpatient (Part A) — DRG-level, in cms_utilization.py.
  • Part B — physician services per-NPI, in cms_part_b.py.
  • TiC payer MRF — negotiated rates, in pricing.payer_mrf.

Per-hospital derived metrics:
  • total_outpatient_services
  • total_medicare_outpatient_payment_mm
  • n_unique_hcpcs
  • top_hcpcs_share + top_hcpcs_code
  • outpatient_to_inpatient_payment_ratio (when joined to
    inpatient utilization)
  • offcampus_share (proxy for site-neutral exposure)
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional


@dataclass
class OPPSRecord:
    """One (CCN × HCPCS × off-campus flag) row."""
    ccn: str
    hcpcs_code: str
    hcpcs_description: str = ""
    is_offcampus: bool = False
    total_services: Optional[int] = None
    n_unique_beneficiaries: Optional[int] = None
    avg_submitted_charge: Optional[float] = None
    avg_medicare_payment: Optional[float] = None


@dataclass
class OPPSHospitalMetrics:
    """Per-hospital derived OPPS metrics."""
    ccn: str
    total_outpatient_services: int = 0
    total_medicare_outpatient_payment_mm: float = 0.0
    n_unique_hcpcs: int = 0
    top_hcpcs_code: str = ""
    top_hcpcs_share: float = 0.0
    offcampus_share: float = 0.0    # 0-1, fraction of services
                                    # that are off-campus PBD


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


def parse_opps_csv(path: Any) -> Iterator[OPPSRecord]:
    """Stream-parse the CMS Outpatient Provider/Service file."""
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(
            f"OPPS CSV not found at {p}")
    with p.open("r", encoding="utf-8", errors="replace",
                newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            ccn = str(_pick(
                row, "Rndrng_Prvdr_CCN",
                "Provider_CCN", "CCN") or "").strip()
            hcpcs = str(_pick(
                row, "HCPCS_Cd", "HCPCS_Code") or "").strip()
            if not (ccn and hcpcs):
                continue
            offcampus_str = str(_pick(
                row, "Offcampus_Provider_Based_Dept",
                "Off_Campus_Flag") or "").strip().upper()
            yield OPPSRecord(
                ccn=ccn,
                hcpcs_code=hcpcs,
                hcpcs_description=str(_pick(
                    row, "HCPCS_Desc",
                    "HCPCS_Description") or "").strip(),
                is_offcampus=(offcampus_str == "Y"
                              or offcampus_str == "TRUE"),
                total_services=_safe_int(_pick(
                    row, "Tot_Srvcs",
                    "Total_Services",
                    "Outpatient_Services")),
                n_unique_beneficiaries=_safe_int(_pick(
                    row, "Tot_Benes",
                    "Total_Beneficiaries")),
                avg_submitted_charge=_safe_float(_pick(
                    row, "Avg_Tot_Sbmtd_Chrgs",
                    "Average_Submitted_Charges")),
                avg_medicare_payment=_safe_float(_pick(
                    row, "Avg_Mdcr_Pymt_Amt",
                    "Average_Medicare_Payment_Amount")),
            )


def compute_opps_metrics(
    records: Iterable[OPPSRecord],
) -> Dict[str, OPPSHospitalMetrics]:
    """Aggregate per-CCN OPPS metrics."""
    by_ccn: Dict[str, Dict[str, Any]] = {}
    for r in records:
        if not r.total_services or r.total_services <= 0:
            continue
        bucket = by_ccn.setdefault(r.ccn, {
            "services": 0,
            "payment": 0.0,
            "by_hcpcs": {},
            "offcampus_services": 0,
        })
        bucket["services"] += r.total_services
        bucket["payment"] += (
            (r.avg_medicare_payment or 0.0) * r.total_services)
        bucket["by_hcpcs"][r.hcpcs_code] = (
            bucket["by_hcpcs"].get(r.hcpcs_code, 0)
            + r.total_services)
        if r.is_offcampus:
            bucket["offcampus_services"] += r.total_services

    out: Dict[str, OPPSHospitalMetrics] = {}
    for ccn, b in by_ccn.items():
        total = b["services"]
        by_h = b["by_hcpcs"]
        if by_h:
            top = max(by_h, key=by_h.get)
            top_share = by_h[top] / total
        else:
            top = ""
            top_share = 0.0
        offcampus_share = (b["offcampus_services"] / total
                           if total else 0.0)
        out[ccn] = OPPSHospitalMetrics(
            ccn=ccn,
            total_outpatient_services=int(total),
            total_medicare_outpatient_payment_mm=round(
                b["payment"] / 1_000_000, 4),
            n_unique_hcpcs=len(by_h),
            top_hcpcs_code=top,
            top_hcpcs_share=round(top_share, 4),
            offcampus_share=round(offcampus_share, 4),
        )
    return out


def _ensure_table(con: Any) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS cms_opps_outpatient (
            ccn TEXT PRIMARY KEY,
            total_outpatient_services INTEGER,
            total_medicare_outpatient_payment_mm REAL,
            n_unique_hcpcs INTEGER,
            top_hcpcs_code TEXT,
            top_hcpcs_share REAL,
            offcampus_share REAL,
            loaded_at TEXT NOT NULL
        )
        """
    )


def load_opps_metrics(
    store: Any,
    metrics: Dict[str, OPPSHospitalMetrics],
) -> int:
    store.init_db()
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    with store.connect() as con:
        _ensure_table(con)
        con.execute("BEGIN IMMEDIATE")
        try:
            for ccn, m in metrics.items():
                con.execute(
                    "INSERT OR REPLACE INTO cms_opps_outpatient "
                    "(ccn, total_outpatient_services, "
                    " total_medicare_outpatient_payment_mm, "
                    " n_unique_hcpcs, top_hcpcs_code, "
                    " top_hcpcs_share, offcampus_share, "
                    " loaded_at) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (m.ccn, m.total_outpatient_services,
                     m.total_medicare_outpatient_payment_mm,
                     m.n_unique_hcpcs, m.top_hcpcs_code,
                     m.top_hcpcs_share, m.offcampus_share,
                     now),
                )
                n += 1
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n


def get_opps_metrics(store: Any, ccn: str,
                     ) -> Optional[Dict[str, Any]]:
    if not ccn:
        return None
    with store.connect() as con:
        _ensure_table(con)
        row = con.execute(
            "SELECT * FROM cms_opps_outpatient WHERE ccn = ?",
            (str(ccn).strip(),),
        ).fetchone()
    return dict(row) if row else None
