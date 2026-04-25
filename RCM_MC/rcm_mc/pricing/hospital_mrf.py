"""Hospital Machine-Readable File (MRF) parser + loader.

CMS Hospital Price Transparency rule (45 CFR §180) requires every
hospital to publish a comprehensive machine-readable file listing
all standard charges for every item and service. The file must
include all five charge types:

    1. Gross charge
    2. Discounted cash price
    3. Payer-specific negotiated charge (one per payer plan)
    4. De-identified minimum negotiated charge
    5. De-identified maximum negotiated charge

Schema: CMS Hospital Price Transparency JSON v2.0::

    {
      "hospital_name": "...",
      "ccn": "...",
      "license_number": "...",
      "version": "2.0.0",
      "standard_charge_information": [
        {
          "description": "TOTAL KNEE ARTHROPLASTY",
          "code_information": [{"code": "27447", "type": "CPT"}],
          "standard_charges": [
            {"setting": "outpatient",
             "gross_charge": 75000,
             "discounted_cash": 30000,
             "minimum_negotiated_charge": 22000,
             "maximum_negotiated_charge": 56000,
             "payers_information": [
               {"payer_name": "BCBS-TX", "plan_name": "PPO",
                "standard_charge_dollar": 24500},
               ...
             ]}
          ]
        }
      ]
    }

Some hospitals still ship a CSV variant (CMS allows both). This
parser only handles the JSON v2.0 form — CSV converters can be
added later by yielding ``HospitalChargeRecord`` instances.

Public API::

    parse_hospital_mrf(path) -> Iterator[HospitalChargeRecord]
    load_hospital_mrf(store, records) -> int
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, List, Optional

from .normalize import normalize_code, normalize_payer_name


@dataclass
class HospitalChargeRecord:
    """A single charge row — one combination of (CCN, code, payer,
    plan, setting). Cash-price rows have empty payer_name + plan_name."""
    ccn: str
    npi: Optional[str] = None
    code: str = ""
    code_type: str = "CPT"
    description: str = ""
    setting: str = ""
    gross_charge: Optional[float] = None
    discounted_cash_price: Optional[float] = None
    payer_specific_charge: Optional[float] = None
    payer_name: str = ""
    plan_name: str = ""
    deidentified_min: Optional[float] = None
    deidentified_max: Optional[float] = None


def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_hospital_mrf(
    path: object,
) -> Iterator[HospitalChargeRecord]:
    """Yield one record per (charge × payer plan) row in a CMS v2.0
    Hospital MRF JSON. Cash-only and de-identified rows yield as
    additional records with empty payer_name/plan_name.
    """
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(f"Hospital MRF not found at {p}")

    with p.open("r", encoding="utf-8") as fh:
        doc = json.load(fh)

    ccn = str(doc.get("ccn") or doc.get("hospital_id") or "")
    npi = doc.get("billing_npi") or doc.get("npi")
    npi = str(npi) if npi else None

    items = doc.get("standard_charge_information") or []
    for item in items:
        description = str(item.get("description") or "")
        codes: List[dict] = item.get("code_information") or []
        # Use the first listed code (CPT preferred), fall through.
        # If multiple codes are listed (e.g. CPT + DRG), we yield
        # one set of records per code.
        for code_block in codes:
            raw_code = code_block.get("code")
            ctype = str(code_block.get("type") or "CPT").upper()
            normed = normalize_code(raw_code, ctype)
            if not normed:
                continue

            for charge in (item.get("standard_charges") or []):
                setting = str(charge.get("setting") or "").lower()
                gross = _safe_float(charge.get("gross_charge"))
                cash = _safe_float(
                    charge.get("discounted_cash") or
                    charge.get("discounted_cash_price"))
                dmin = _safe_float(
                    charge.get("minimum_negotiated_charge"))
                dmax = _safe_float(
                    charge.get("maximum_negotiated_charge"))

                payers = charge.get("payers_information") or []
                if payers:
                    for p_blk in payers:
                        rate = _safe_float(
                            p_blk.get("standard_charge_dollar")
                            or p_blk.get("negotiated_dollar")
                            or p_blk.get("standard_charge")
                        )
                        yield HospitalChargeRecord(
                            ccn=ccn, npi=npi,
                            code=normed, code_type=ctype,
                            description=description, setting=setting,
                            gross_charge=gross,
                            discounted_cash_price=cash,
                            payer_specific_charge=rate,
                            payer_name=normalize_payer_name(
                                p_blk.get("payer_name")),
                            plan_name=str(
                                p_blk.get("plan_name") or "").strip(),
                            deidentified_min=dmin,
                            deidentified_max=dmax,
                        )
                else:
                    # Cash-price-only row (no payer rates)
                    yield HospitalChargeRecord(
                        ccn=ccn, npi=npi,
                        code=normed, code_type=ctype,
                        description=description, setting=setting,
                        gross_charge=gross,
                        discounted_cash_price=cash,
                        payer_specific_charge=None,
                        payer_name="", plan_name="",
                        deidentified_min=dmin,
                        deidentified_max=dmax,
                    )


def load_hospital_mrf(
    store: Any,
    records: Iterable[HospitalChargeRecord],
    *,
    source_key: Optional[str] = None,
) -> int:
    """Insert/replace charge rows. Returns count loaded.

    ``source_key`` is the human-friendly identifier in the load log
    (e.g. the hospital CCN or filename); defaults to the CCN of
    the first record."""
    store.init_db()
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    first_ccn: Optional[str] = None
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        try:
            for r in records:
                if first_ccn is None and r.ccn:
                    first_ccn = r.ccn
                con.execute(
                    """INSERT OR REPLACE INTO pricing_hospital_charges (
                        ccn, npi, code, code_type, description,
                        setting, gross_charge, discounted_cash_price,
                        payer_specific_charge, payer_name, plan_name,
                        deidentified_min, deidentified_max, loaded_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (r.ccn, r.npi, r.code, r.code_type, r.description,
                     r.setting, r.gross_charge,
                     r.discounted_cash_price,
                     r.payer_specific_charge,
                     r.payer_name, r.plan_name,
                     r.deidentified_min, r.deidentified_max,
                     now),
                )
                n += 1
            key = source_key or first_ccn or "hospital_mrf"
            con.execute(
                "INSERT OR REPLACE INTO pricing_load_log "
                "(source, key, record_count, loaded_at, notes) "
                "VALUES (?, ?, ?, ?, ?)",
                ("hospital_mrf", key, n, now, ""),
            )
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n
