"""Medicare Part D Prescribers utilization.

Public source: ``data.cms.gov/provider-summary-by-type-of-service/
medicare-part-d-prescribers-by-provider-and-drug``. One row per
(NPI × drug) tuple.

Per-prescriber derived metrics:

  • total_claims_filled: Σ claims
  • total_drug_cost_mm: Σ Medicare-paid amounts / 1M
  • n_unique_drugs: count of distinct NDCs
  • opioid_prescriber_flag: ≥10% of claims are opioid analgesics
                            (an OIG audit-risk signal)
  • brand_share: brand vs generic mix (cost-driver signal)
  • top_drug_share: largest single-drug share of claims
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set


@dataclass
class PartDRecord:
    """One (NPI × drug) row from the Part D file."""
    npi: str
    drug_name: str
    drug_generic_name: str = ""
    n_claims: Optional[int] = None
    n_unique_beneficiaries: Optional[int] = None
    total_drug_cost: Optional[float] = None
    total_day_supply: Optional[int] = None
    is_brand: bool = False
    provider_specialty: str = ""


# Common Schedule II/III opioids — small list sufficient for the
# diligence-grade flag. CMS publishes the full opioid drug list
# annually; partner can override via the ``opioid_drugs`` arg.
DEFAULT_OPIOID_DRUGS: Set[str] = {
    "oxycodone", "hydrocodone", "morphine sulfate",
    "methadone", "fentanyl", "tramadol", "codeine",
    "buprenorphine", "hydromorphone", "oxymorphone",
}


@dataclass
class PartDPrescriberMetrics:
    """Per-prescriber aggregated metrics."""
    npi: str
    specialty: str = ""
    total_claims_filled: int = 0
    total_drug_cost_mm: float = 0.0
    n_unique_drugs: int = 0
    top_drug_name: str = ""
    top_drug_share: float = 0.0
    brand_share: float = 0.0
    opioid_claim_share: float = 0.0
    opioid_prescriber_flag: bool = False


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


def parse_part_d_csv(path: Any) -> Iterable[PartDRecord]:
    """Stream-parse the CMS Part D Prescriber/Drug file."""
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(f"Part D CSV not found at {p}")
    with p.open("r", encoding="utf-8", errors="replace",
                newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            npi = str(_pick(
                row, "Prscrbr_NPI", "NPI") or "").strip()
            drug = str(_pick(
                row, "Brnd_Name", "Drug_Name",
                "Brand_Name") or "").strip()
            if not (npi and drug):
                continue
            generic = str(_pick(
                row, "Gnrc_Name", "Generic_Name") or "").strip()
            is_brand = bool(generic and generic.lower()
                            != drug.lower())
            yield PartDRecord(
                npi=npi,
                drug_name=drug,
                drug_generic_name=generic,
                n_claims=_safe_int(_pick(
                    row, "Tot_Clms", "Total_Claim_Count")),
                n_unique_beneficiaries=_safe_int(_pick(
                    row, "Tot_Benes", "Total_Beneficiaries")),
                total_drug_cost=_safe_float(_pick(
                    row, "Tot_Drug_Cst",
                    "Total_Drug_Cost")),
                total_day_supply=_safe_int(_pick(
                    row, "Tot_Day_Suply",
                    "Total_Day_Supply")),
                is_brand=is_brand,
                provider_specialty=str(_pick(
                    row, "Prscrbr_Type",
                    "Provider_Type") or "").strip(),
            )


def compute_part_d_metrics(
    records: Iterable[PartDRecord],
    *,
    opioid_drugs: Optional[Set[str]] = None,
    opioid_threshold: float = 0.10,
) -> Dict[str, PartDPrescriberMetrics]:
    """Aggregate per-NPI metrics from Part D rows.

    Args:
      records: stream of PartDRecord.
      opioid_drugs: overrides DEFAULT_OPIOID_DRUGS (lowercase
        substrings; matched against drug_name + drug_generic_name).
      opioid_threshold: claim share above which a prescriber is
        flagged. Default 10% per CMS Center for Program Integrity
        guidance.
    """
    opioid_set = opioid_drugs or DEFAULT_OPIOID_DRUGS
    by_npi: Dict[str, Dict[str, Any]] = {}
    for r in records:
        if not r.n_claims:
            continue
        bucket = by_npi.setdefault(r.npi, {
            "specialty": r.provider_specialty,
            "claims": 0,
            "cost": 0.0,
            "by_drug": {},
            "brand_claims": 0,
            "opioid_claims": 0,
        })
        if r.provider_specialty:
            bucket["specialty"] = r.provider_specialty
        bucket["claims"] += r.n_claims
        bucket["cost"] += r.total_drug_cost or 0.0
        bucket["by_drug"][r.drug_name] = (
            bucket["by_drug"].get(r.drug_name, 0)
            + r.n_claims)
        # is_brand: use the parser-set value OR derive on the
        # fly when callers construct PartDRecord directly
        # (drug_name differs case-insensitively from generic).
        is_brand = r.is_brand
        if (not is_brand and r.drug_generic_name
                and r.drug_name.lower()
                != r.drug_generic_name.lower()):
            is_brand = True
        if is_brand:
            bucket["brand_claims"] += r.n_claims
        # Opioid match: any opioid substring in drug_name or
        # generic_name (case-insensitive).
        d_lower = r.drug_name.lower()
        g_lower = r.drug_generic_name.lower()
        if any(o in d_lower or o in g_lower
               for o in opioid_set):
            bucket["opioid_claims"] += r.n_claims

    out: Dict[str, PartDPrescriberMetrics] = {}
    for npi, b in by_npi.items():
        total = b["claims"]
        if not total:
            continue
        by_drug = b["by_drug"]
        top_drug = max(by_drug, key=by_drug.get) if by_drug else ""
        top_share = (by_drug[top_drug] / total
                     if top_drug else 0.0)
        brand_share = b["brand_claims"] / total
        opioid_share = b["opioid_claims"] / total
        out[npi] = PartDPrescriberMetrics(
            npi=npi,
            specialty=b["specialty"],
            total_claims_filled=total,
            total_drug_cost_mm=round(
                b["cost"] / 1_000_000, 4),
            n_unique_drugs=len(by_drug),
            top_drug_name=top_drug,
            top_drug_share=round(top_share, 4),
            brand_share=round(brand_share, 4),
            opioid_claim_share=round(opioid_share, 4),
            opioid_prescriber_flag=opioid_share >= opioid_threshold,
        )
    return out


def _ensure_table(con: Any) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS cms_part_d_metrics (
            npi TEXT PRIMARY KEY,
            specialty TEXT,
            total_claims_filled INTEGER,
            total_drug_cost_mm REAL,
            n_unique_drugs INTEGER,
            top_drug_name TEXT,
            top_drug_share REAL,
            brand_share REAL,
            opioid_claim_share REAL,
            opioid_prescriber_flag INTEGER,
            loaded_at TEXT NOT NULL
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS "
        "idx_part_d_opioid "
        "ON cms_part_d_metrics(opioid_prescriber_flag)"
    )


def load_part_d_metrics(
    store: Any,
    metrics: Dict[str, PartDPrescriberMetrics],
) -> int:
    store.init_db()
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    with store.connect() as con:
        _ensure_table(con)
        con.execute("BEGIN IMMEDIATE")
        try:
            for npi, m in metrics.items():
                con.execute(
                    "INSERT OR REPLACE INTO cms_part_d_metrics "
                    "(npi, specialty, total_claims_filled, "
                    " total_drug_cost_mm, n_unique_drugs, "
                    " top_drug_name, top_drug_share, "
                    " brand_share, opioid_claim_share, "
                    " opioid_prescriber_flag, loaded_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (m.npi, m.specialty,
                     m.total_claims_filled,
                     m.total_drug_cost_mm,
                     m.n_unique_drugs, m.top_drug_name,
                     m.top_drug_share, m.brand_share,
                     m.opioid_claim_share,
                     1 if m.opioid_prescriber_flag else 0,
                     now),
                )
                n += 1
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n


def get_part_d_metrics(store: Any, npi: str,
                       ) -> Optional[Dict[str, Any]]:
    if not npi:
        return None
    with store.connect() as con:
        _ensure_table(con)
        row = con.execute(
            "SELECT * FROM cms_part_d_metrics WHERE npi = ?",
            (str(npi).strip(),),
        ).fetchone()
    if not row:
        return None
    out = dict(row)
    out["opioid_prescriber_flag"] = bool(
        out.get("opioid_prescriber_flag", 0))
    return out
