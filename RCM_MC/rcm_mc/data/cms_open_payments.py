"""CMS Open Payments (Sunshine Act) ingestion.

The Affordable Care Act's Sunshine Act mandates that drug + medical-
device manufacturers report payments + transfers of value to
physicians + teaching hospitals. CMS publishes the data annually
in three files:

  • General Payments — consulting fees, speaker fees, meals,
    travel, gifts.
  • Research Payments — clinical trial payments, research grants.
  • Ownership/Investment — physician ownership stakes in industry
    firms.

For PE diligence on physician-group / MSO targets, this is the
canonical conflict-of-interest source. Per-physician aggregates
matter: total industry exposure, top manufacturer concentration,
payment-category mix (consulting + speaker fees flag harder than
meals), time trend.

This module:
  • Parses the published CSV format (per-record payment rows).
  • Aggregates per-NPI metrics + flags conflicts above
    configurable thresholds.
  • Persists in cms_open_payments_npi for the screening +
    diligence packet consumers.

Public API::

    from rcm_mc.data.cms_open_payments import (
        OpenPaymentRecord,
        parse_open_payments_csv,
        compute_npi_aggregates,
        load_npi_aggregates,
        get_payments_for_npi,
        list_top_recipients,
    )
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional


# ── Schema ────────────────────────────────────────────────────

def _ensure_table(con: Any) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS cms_open_payments_npi (
            npi TEXT PRIMARY KEY,
            physician_name TEXT,
            specialty TEXT,
            program_year INTEGER,
            total_payment_usd REAL,
            n_payments INTEGER,
            n_unique_manufacturers INTEGER,
            top_manufacturer TEXT,
            top_manufacturer_share REAL,
            consulting_payment_usd REAL,
            speaker_payment_usd REAL,
            meals_travel_usd REAL,
            ownership_value_usd REAL,
            research_payment_usd REAL,
            conflict_flag INTEGER NOT NULL DEFAULT 0,
            conflict_reasons TEXT,
            loaded_at TEXT NOT NULL
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS "
        "idx_op_specialty "
        "ON cms_open_payments_npi(specialty)"
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS "
        "idx_op_total "
        "ON cms_open_payments_npi(total_payment_usd DESC)"
    )


# ── Record + per-NPI aggregate dataclasses ────────────────────

@dataclass
class OpenPaymentRecord:
    """One published payment row (covers all three file types)."""
    npi: str
    physician_name: str = ""
    specialty: str = ""
    payment_type: str = "general"   # general / research / ownership
    nature_of_payment: str = ""     # consulting / speaker / meal /
                                     # travel / royalty / etc.
    manufacturer_name: str = ""
    amount_usd: float = 0.0
    program_year: int = 0
    payment_date: str = ""


@dataclass
class NpiAggregate:
    """Per-NPI rolled-up metrics."""
    npi: str
    physician_name: str = ""
    specialty: str = ""
    program_year: int = 0
    total_payment_usd: float = 0.0
    n_payments: int = 0
    n_unique_manufacturers: int = 0
    top_manufacturer: str = ""
    top_manufacturer_share: float = 0.0
    consulting_payment_usd: float = 0.0
    speaker_payment_usd: float = 0.0
    meals_travel_usd: float = 0.0
    ownership_value_usd: float = 0.0
    research_payment_usd: float = 0.0
    conflict_flag: bool = False
    conflict_reasons: List[str] = field(default_factory=list)


def _safe_float(v: Any) -> float:
    if v is None or v == "":
        return 0.0
    try:
        return float(str(v).strip().replace(",", "")
                     .replace("$", ""))
    except (TypeError, ValueError):
        return 0.0


def _safe_int(v: Any, default: int = 0) -> int:
    if v is None or v == "":
        return default
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return default


def _pick(row: Dict[str, Any], *names: str) -> Any:
    for n in names:
        if n in row and row[n] not in (None, ""):
            return row[n]
    return None


# Heuristic: classify the nature_of_payment string into one of
# the four conflict-relevant buckets.
def _bucket(nature: str) -> str:
    n = (nature or "").lower()
    if "consulting" in n or "advisor" in n:
        return "consulting"
    if "speaker" in n or "speaking" in n or "honoraria" in n:
        return "speaker"
    if "food" in n or "meal" in n or "travel" in n \
            or "lodging" in n or "entertainment" in n:
        return "meals_travel"
    if "royalty" in n or "license" in n:
        return "royalty"
    if "ownership" in n or "investment" in n or "equity" in n:
        return "ownership"
    if "research" in n or "grant" in n:
        return "research"
    return "other"


def parse_open_payments_csv(
    path: Any,
    *,
    payment_type: str = "general",
    program_year: int = 0,
) -> Iterator[OpenPaymentRecord]:
    """Stream-parse a CMS Open Payments CSV.

    payment_type identifies which of the three file types is
    being parsed (general / research / ownership). The NPI column
    name varies across years + types — we accept several aliases.
    """
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(
            f"Open Payments CSV not found at {p}")
    with p.open("r", encoding="utf-8", errors="replace",
                newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            npi = str(_pick(
                row, "Physician_NPI", "Covered_Recipient_NPI",
                "NPI") or "").strip()
            if not npi:
                continue
            first = str(_pick(
                row, "Physician_First_Name",
                "Covered_Recipient_First_Name") or "").strip()
            last = str(_pick(
                row, "Physician_Last_Name",
                "Covered_Recipient_Last_Name") or "").strip()
            name = f"{first} {last}".strip()
            specialty = str(_pick(
                row, "Physician_Primary_Type",
                "Physician_Specialty",
                "Covered_Recipient_Primary_Type") or "").strip()
            mfr = str(_pick(
                row,
                "Applicable_Manufacturer_or_Applicable_GPO_Making_Payment_Name",
                "Submitting_Applicable_Manufacturer_or_Applicable_GPO_Name",
                "Manufacturer_Name") or "").strip()
            amount = _safe_float(_pick(
                row, "Total_Amount_of_Payment_USDollars",
                "Total_Investment_Amount_USDollars",
                "Amount_USDollars"))
            nature = str(_pick(
                row, "Nature_of_Payment_or_Transfer_of_Value",
                "Nature_of_Payment") or "").strip()
            pdate = str(_pick(
                row, "Date_of_Payment",
                "Payment_Publication_Date") or "").strip()
            yield OpenPaymentRecord(
                npi=npi,
                physician_name=name,
                specialty=specialty,
                payment_type=payment_type,
                nature_of_payment=nature,
                manufacturer_name=mfr,
                amount_usd=amount,
                program_year=program_year
                              or _safe_int(
                                  row.get("Program_Year")),
                payment_date=pdate,
            )


# ── Aggregate computation ────────────────────────────────────

def compute_npi_aggregates(
    records: Iterable[OpenPaymentRecord],
    *,
    consulting_threshold: float = 50_000.0,
    speaker_threshold: float = 50_000.0,
    total_threshold: float = 250_000.0,
    ownership_threshold: float = 100_000.0,
) -> Dict[str, NpiAggregate]:
    """Aggregate the stream of per-payment records into per-NPI
    rollups + flag conflicts above configurable thresholds.

    Default thresholds reflect partner-defensible "this is
    diligence-worthy industry exposure" levels:
      • Consulting >$50K — paid relationship rather than
        incidental
      • Speaker fees >$50K — same
      • Total industry payments >$250K — outsized exposure
      • Ownership stake >$100K — direct financial alignment
    """
    by_npi: Dict[str, Dict[str, Any]] = {}
    for r in records:
        bucket = by_npi.setdefault(r.npi, {
            "physician_name": r.physician_name,
            "specialty": r.specialty,
            "program_year": r.program_year,
            "total": 0.0,
            "n_payments": 0,
            "by_mfr": {},
            "consulting": 0.0,
            "speaker": 0.0,
            "meals_travel": 0.0,
            "ownership": 0.0,
            "research": 0.0,
        })
        # Refresh name / specialty / year if not already set
        if r.physician_name:
            bucket["physician_name"] = r.physician_name
        if r.specialty:
            bucket["specialty"] = r.specialty
        if r.program_year:
            bucket["program_year"] = max(
                bucket["program_year"], r.program_year)

        # Total + per-manufacturer
        bucket["total"] += r.amount_usd
        bucket["n_payments"] += 1
        if r.manufacturer_name:
            bucket["by_mfr"][r.manufacturer_name] = (
                bucket["by_mfr"].get(r.manufacturer_name, 0.0)
                + r.amount_usd)
        # Bucket by nature
        category = _bucket(r.nature_of_payment)
        if r.payment_type == "ownership":
            bucket["ownership"] += r.amount_usd
        elif r.payment_type == "research":
            bucket["research"] += r.amount_usd
        elif category in ("consulting", "speaker",
                          "meals_travel"):
            bucket[category] += r.amount_usd

    out: Dict[str, NpiAggregate] = {}
    for npi, b in by_npi.items():
        total = b["total"]
        by_mfr = b["by_mfr"]
        if by_mfr:
            top_mfr = max(by_mfr, key=by_mfr.get)
            top_share = (by_mfr[top_mfr] / total
                         if total > 0 else 0.0)
        else:
            top_mfr = ""
            top_share = 0.0

        flags: List[str] = []
        if b["consulting"] >= consulting_threshold:
            flags.append(
                f"Consulting payments "
                f"${b['consulting']:,.0f} ≥ "
                f"${consulting_threshold:,.0f} threshold")
        if b["speaker"] >= speaker_threshold:
            flags.append(
                f"Speaker fees ${b['speaker']:,.0f} ≥ "
                f"${speaker_threshold:,.0f} threshold")
        if total >= total_threshold:
            flags.append(
                f"Total industry payments ${total:,.0f} ≥ "
                f"${total_threshold:,.0f} threshold")
        if b["ownership"] >= ownership_threshold:
            flags.append(
                f"Ownership stake "
                f"${b['ownership']:,.0f} ≥ "
                f"${ownership_threshold:,.0f} threshold")
        if top_share >= 0.80 and total > 50_000.0:
            flags.append(
                f"Single-manufacturer concentration "
                f"{top_share*100:.0f}% — alignment risk")

        out[npi] = NpiAggregate(
            npi=npi,
            physician_name=b["physician_name"],
            specialty=b["specialty"],
            program_year=b["program_year"],
            total_payment_usd=round(total, 2),
            n_payments=b["n_payments"],
            n_unique_manufacturers=len(by_mfr),
            top_manufacturer=top_mfr,
            top_manufacturer_share=round(top_share, 4),
            consulting_payment_usd=round(b["consulting"], 2),
            speaker_payment_usd=round(b["speaker"], 2),
            meals_travel_usd=round(b["meals_travel"], 2),
            ownership_value_usd=round(b["ownership"], 2),
            research_payment_usd=round(b["research"], 2),
            conflict_flag=bool(flags),
            conflict_reasons=flags,
        )
    return out


# ── Storage ───────────────────────────────────────────────────

def load_npi_aggregates(
    store: Any,
    aggregates: Dict[str, NpiAggregate],
) -> int:
    store.init_db()
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    with store.connect() as con:
        _ensure_table(con)
        con.execute("BEGIN IMMEDIATE")
        try:
            for npi, agg in aggregates.items():
                reasons_str = " | ".join(agg.conflict_reasons)
                con.execute(
                    "INSERT OR REPLACE INTO cms_open_payments_npi "
                    "(npi, physician_name, specialty, "
                    " program_year, total_payment_usd, "
                    " n_payments, n_unique_manufacturers, "
                    " top_manufacturer, top_manufacturer_share, "
                    " consulting_payment_usd, "
                    " speaker_payment_usd, meals_travel_usd, "
                    " ownership_value_usd, "
                    " research_payment_usd, conflict_flag, "
                    " conflict_reasons, loaded_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (agg.npi, agg.physician_name,
                     agg.specialty, agg.program_year,
                     agg.total_payment_usd, agg.n_payments,
                     agg.n_unique_manufacturers,
                     agg.top_manufacturer,
                     agg.top_manufacturer_share,
                     agg.consulting_payment_usd,
                     agg.speaker_payment_usd,
                     agg.meals_travel_usd,
                     agg.ownership_value_usd,
                     agg.research_payment_usd,
                     1 if agg.conflict_flag else 0,
                     reasons_str, now),
                )
                n += 1
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n


# ── Read helpers ─────────────────────────────────────────────

def get_payments_for_npi(
    store: Any, npi: str,
) -> Optional[Dict[str, Any]]:
    if not npi:
        return None
    with store.connect() as con:
        _ensure_table(con)
        row = con.execute(
            "SELECT * FROM cms_open_payments_npi "
            "WHERE npi = ?", (str(npi).strip(),),
        ).fetchone()
    if not row:
        return None
    out = dict(row)
    out["conflict_flag"] = bool(out.get("conflict_flag", 0))
    return out


def list_top_recipients(
    store: Any,
    *,
    specialty: Optional[str] = None,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Top NPIs by total industry payment, optionally filtered
    by specialty."""
    sql = ("SELECT * FROM cms_open_payments_npi "
           "WHERE total_payment_usd > 0")
    params: List[Any] = []
    if specialty:
        sql += " AND specialty = ?"
        params.append(specialty)
    sql += " ORDER BY total_payment_usd DESC LIMIT ?"
    params.append(int(limit))
    with store.connect() as con:
        _ensure_table(con)
        rows = con.execute(sql, params).fetchall()
    return [{**dict(r),
             "conflict_flag": bool(r["conflict_flag"])}
            for r in rows]
