"""CMS Medicare Outpatient (OPPS) by Provider and Service.

Public source: ``data.cms.gov/provider-summary-by-type-of-service/
medicare-outpatient-hospitals-by-provider-and-service``. One row
per (CCN, **comprehensive APC**) tuple — the published grain is the
Ambulatory Payment Classification (``APC_Cd`` / ``APC_Desc``), NOT
HCPCS (the data dictionary's service count is ``CAPC_Srvcs`` and the
beneficiary count ``Bene_Cnt``). The parser accepts both spellings:
the original HCPCS aliases are kept for older extracts, and the APC
aliases make the CURRENT vintage parse instead of yielding nothing.

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
                row, "HCPCS_Cd", "HCPCS_Code",
                "APC_Cd", "APC_CD") or "").strip()
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
                    "HCPCS_Description", "APC_Desc") or "").strip(),
                is_offcampus=(offcampus_str == "Y"
                              or offcampus_str == "TRUE"),
                total_services=_safe_int(_pick(
                    row, "Tot_Srvcs",
                    "Total_Services",
                    "Outpatient_Services", "CAPC_Srvcs")),
                n_unique_beneficiaries=_safe_int(_pick(
                    row, "Tot_Benes",
                    "Total_Beneficiaries", "Bene_Cnt")),
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


# ---------------------------------------------------------------------------
# Live client — data.cms.gov data-api, drug-administration APCs by state.
#
# The published grain is CCN × comprehensive APC. For infusion diligence
# the relevant rows are the four OPPS drug-administration APCs (5691–5694
# — level 1 simple injections up to level 4 chemo/complex infusions):
# they are the hospital-outpatient (HOPD) infusion volume a steerage
# thesis wants to see per market. Fails CLOSED (empty) when egress is
# blocked; nothing fabricates a service count.

import functools
import json
import logging
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

_CMS_DATA_API = "https://data.cms.gov/data-api/v1/dataset"
_CMS_CATALOG = "https://data.cms.gov/data.json"

#: OPPS comprehensive drug-administration APCs (public OPPS facts).
DRUG_ADMIN_APCS = {
    "5691": "Level 1 Drug Administration (injections)",
    "5692": "Level 2 Drug Administration (simple IV push/hydration)",
    "5693": "Level 3 Drug Administration (therapeutic IV infusion)",
    "5694": "Level 4 Drug Administration (chemo / complex infusion)",
}


@functools.lru_cache(maxsize=8)
def resolve_opps_provider_dataset(year: int = 0,
                                  timeout: float = 20.0) -> str:
    """Find the 'Outpatient Hospitals - by Provider and Service' dataset
    UUID from the CMS catalog — the entry titled for ``year`` when one
    exists, else the bare-titled entry (which serves the latest vintage).
    '' on failure (caller fails closed)."""
    from ._cms_download import ssl_context
    try:
        req = urllib.request.Request(
            _CMS_CATALOG, headers={"Accept": "application/json",
                                   "User-Agent": "rcm-mc/1.0"})
        with urllib.request.urlopen(
                req, timeout=timeout, context=ssl_context()) as r:
            cat = json.loads(r.read().decode())
    except Exception as exc:
        logger.warning("CMS catalog resolve failed: %s", exc)
        return ""
    fallback = ""
    for ds in cat.get("dataset", []):
        title = str(ds.get("title", ""))
        if "outpatient hospitals - by provider and service" \
                not in title.lower():
            continue
        for dist in ds.get("distribution", []):
            url = str(dist.get("accessURL", "")
                      or dist.get("downloadURL", ""))
            if "dataset/" not in url:
                continue
            uuid = url.split("dataset/")[1].split("/")[0]
            if year and str(year) in title:
                return uuid
            fallback = fallback or uuid
    return fallback


def fetch_opps_apc_state(
    apc: str, state: str, *, dataset: str = "", timeout: float = 20.0,
) -> List[Dict[str, Any]]:
    """Per-hospital rows for one drug-admin APC in one state:
    ``[{ccn, name, city, services, benes, avg_payment}]``. [] on
    failure (fails closed)."""
    ds = dataset or resolve_opps_provider_dataset()
    if not ds:
        return []
    from ._cms_download import ssl_context
    params = {
        "filter[APC_Cd]": str(apc),
        "filter[Rndrng_Prvdr_State_Abrvtn]": str(state).upper(),
        "size": "2000",
    }
    url = (f"{_CMS_DATA_API}/{ds}/data?"
           + urllib.parse.urlencode(params))
    try:
        req = urllib.request.Request(
            url, headers={"Accept": "application/json",
                          "User-Agent": "rcm-mc/1.0"})
        with urllib.request.urlopen(
                req, timeout=timeout, context=ssl_context()) as r:
            rows = json.loads(r.read().decode())
    except Exception as exc:
        logger.warning("CMS OPPS provider API unavailable: %s", exc)
        return []
    out: List[Dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        out.append({
            "ccn": str(_pick(row, "Rndrng_Prvdr_CCN",
                             "Provider_CCN", "CCN") or "").strip(),
            "name": str(_pick(row, "Rndrng_Prvdr_Org_Name",
                              "Provider_Name") or "").strip(),
            "city": str(_pick(row, "Rndrng_Prvdr_City",
                              "Provider_City") or "").strip(),
            "apc": str(_pick(row, "APC_Cd", "APC_CD") or "").strip(),
            "services": _safe_int(_pick(
                row, "CAPC_Srvcs", "Tot_Srvcs")) or 0,
            "benes": _safe_int(_pick(row, "Bene_Cnt", "Tot_Benes")),
            "avg_payment": _safe_float(_pick(
                row, "Avg_Mdcr_Pymt_Amt",
                "Average_Medicare_Payment_Amount")),
        })
    return [r for r in out if r["ccn"]]


def fetch_state_drug_admin(
    state: str, *, apcs: Optional[List[str]] = None,
    timeout: float = 20.0,
) -> Dict[str, Dict[str, Any]]:
    """Aggregate the drug-administration APC rows per CCN for a state:
    ``{ccn: {name, city, services, benes_max, payment_mm, by_apc}}``.
    ``benes_max`` is the LARGEST single-APC beneficiary count — bene
    counts must not be summed across APCs (one patient can appear in
    several). ``{}`` when the API is unreachable."""
    ds = resolve_opps_provider_dataset(timeout=timeout)
    if not ds:
        return {}
    agg: Dict[str, Dict[str, Any]] = {}
    for apc in (apcs or list(DRUG_ADMIN_APCS)):
        for r in fetch_opps_apc_state(
                apc, state, dataset=ds, timeout=timeout):
            slot = agg.setdefault(r["ccn"], {
                "name": r["name"], "city": r["city"],
                "services": 0, "benes_max": 0,
                "payment_mm": 0.0, "by_apc": {}})
            slot["services"] += r["services"]
            slot["by_apc"][r["apc"]] = r["services"]
            if r["benes"]:
                slot["benes_max"] = max(slot["benes_max"], r["benes"])
            if r["avg_payment"]:
                slot["payment_mm"] += (
                    r["avg_payment"] * r["services"] / 1_000_000)
    for slot in agg.values():
        slot["payment_mm"] = round(slot["payment_mm"], 3)
    return agg
