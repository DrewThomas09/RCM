"""EDI 837/835 parser for claim submission and remittance data (Prompt 75).

Healthcare claims flow as EDI X12 transactions.  837 = claim submission,
835 = remittance advice.  We parse the minimum segment set needed for
denial-rate analytics and AR aging — not a full HIPAA-compliant parser.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, date
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Dataclasses ───────────────────────────────────────────────────────

@dataclass
class ClaimSubmission:
    """Represents a single claim from an EDI 837 transaction."""
    claim_id: str
    payer: str = ""
    provider_npi: str = ""
    service_date: str = ""
    total_charge: float = 0.0
    dx_codes: list[str] = field(default_factory=list)
    drg_code: str = ""


@dataclass
class RemittanceAdvice:
    """Represents a single remittance line from an EDI 835 transaction."""
    claim_id: str
    paid_amount: float = 0.0
    adjudication_date: str = ""
    claim_status: str = ""  # "paid" / "denied" / "partial"
    carc_codes: list[str] = field(default_factory=list)
    denial_amount: float = 0.0


# ── Segment helpers ───────────────────────────────────────────────────

def _split_segments(content: str) -> list[list[str]]:
    """Split EDI content into segments, each a list of elements."""
    raw = content.strip()
    # Segments delimited by ~, elements by *
    segments: list[list[str]] = []
    for seg_str in raw.split("~"):
        seg_str = seg_str.strip()
        if not seg_str:
            continue
        elements = seg_str.split("*")
        segments.append(elements)
    return segments


def _classify_claim_status(paid: float, billed: float) -> str:
    """Derive claim status from payment vs billed amounts."""
    if paid <= 0:
        return "denied"
    if paid >= billed:
        return "paid"
    return "partial"


# ── 837 Parser ────────────────────────────────────────────────────────

def parse_837(content: str) -> list[ClaimSubmission]:
    """Parse an EDI 837 (Professional/Institutional) into ClaimSubmission objects.

    Minimal segment extraction:
    - ISA: interchange header (payer identification when SBR/N1 absent)
    - CLM: claim-level data (claim_id, total_charge)
    - HI: diagnosis codes (ABK/ABF qualifiers map to ICD-10 Dx)
    - SV1: service lines (service_date, provider NPI when REF absent)
    - NM1: entity identification (payer via NM1*PR, provider via NM1*85)
    - DTP: date segments (service date via DTP*472)
    - REF: reference (provider NPI via REF*HPI)
    - DRG: DRG information
    """
    segments = _split_segments(content)
    claims: list[ClaimSubmission] = []
    current_claim: Optional[ClaimSubmission] = None
    # Track interchange-level payer as fallback
    interchange_payer = ""
    # Pending values from NM1 segments that appear before a CLM
    pending_payer = ""
    pending_npi = ""

    for elems in segments:
        seg_id = elems[0] if elems else ""

        if seg_id == "ISA":
            # ISA*00*          *00*          *ZZ*SENDER         *ZZ*RECEIVER       *...
            if len(elems) > 8:
                interchange_payer = elems[8].strip()

        elif seg_id == "CLM":
            # CLM*claim_id*total_charge*...*
            if current_claim is not None:
                claims.append(current_claim)
            claim_id = elems[1] if len(elems) > 1 else ""
            charge = 0.0
            if len(elems) > 2:
                try:
                    charge = float(elems[2])
                except (ValueError, IndexError):
                    pass
            current_claim = ClaimSubmission(
                claim_id=claim_id,
                total_charge=charge,
                payer=pending_payer or interchange_payer,
                provider_npi=pending_npi,
            )
            # Reset pending so next claim doesn't inherit
            pending_payer = ""
            pending_npi = ""

        elif seg_id == "HI" and current_claim is not None:
            # HI*ABK:J069*ABF:E119*...
            for elem in elems[1:]:
                if ":" in elem:
                    qualifier, code = elem.split(":", 1)
                    qualifier = qualifier.strip().upper()
                    if qualifier in ("ABK", "ABF", "BK", "BF"):
                        current_claim.dx_codes.append(code.strip())

        elif seg_id == "NM1":
            # NM1*PR*2*PAYER NAME*...  (payer)
            # NM1*85*1*LAST*FIRST*...*XX*1234567890  (billing provider)
            # Element indices: 0=NM1, 1=entity, 2=type, 3=last/org,
            #   4=first, 5=mid, 6=prefix, 7=suffix, 8=id_qualifier, 9=id
            if len(elems) > 1:
                entity = elems[1]
                if entity == "PR" and len(elems) > 3:
                    payer_name = elems[3].strip()
                    if current_claim is not None:
                        current_claim.payer = payer_name
                    else:
                        pending_payer = payer_name
                elif entity == "85":
                    # NPI follows the qualifier (XX); find it by scanning
                    # for the XX qualifier and taking the next element.
                    npi_val = ""
                    for idx in range(8, len(elems)):
                        if elems[idx].strip() == "XX" and idx + 1 < len(elems):
                            npi_val = elems[idx + 1].strip()
                            break
                    if current_claim is not None:
                        current_claim.provider_npi = npi_val
                    else:
                        pending_npi = npi_val

        elif seg_id == "REF" and current_claim is not None:
            # REF*HPI*provider_npi  (rendering provider NPI)
            if len(elems) > 2 and elems[1] in ("HPI", "SY"):
                current_claim.provider_npi = elems[2].strip()

        elif seg_id == "DTP" and current_claim is not None:
            # DTP*472*D8*20250115  (service date)
            if len(elems) > 3 and elems[1] == "472":
                current_claim.service_date = elems[3].strip()

        elif seg_id == "DRG" and current_claim is not None:
            # DRG*drg_code*...
            if len(elems) > 1:
                current_claim.drg_code = elems[1].strip()

        elif seg_id == "SV1" and current_claim is not None:
            # SV1 is a service-line segment; we keep it for completeness
            # SV1*HC:99213*150*UN*1*...*
            pass

    # Don't forget the last claim
    if current_claim is not None:
        claims.append(current_claim)

    return claims


# ── 835 Parser ────────────────────────────────────────────────────────

def parse_835(content: str) -> list[RemittanceAdvice]:
    """Parse an EDI 835 (Health Care Claim Payment) into RemittanceAdvice objects.

    Minimal segment extraction:
    - CLP: claim payment data (claim_id, status_code, billed, paid)
    - CAS: claim adjustment with CARC codes
    - SVC: service-level adjustments
    - DTM: adjudication date (DTM*036)
    """
    segments = _split_segments(content)
    remittances: list[RemittanceAdvice] = []
    current_ra: Optional[RemittanceAdvice] = None
    current_billed: float = 0.0

    for elems in segments:
        seg_id = elems[0] if elems else ""

        if seg_id == "CLP":
            # CLP*claim_id*status_code*billed*paid*patient_resp*...
            if current_ra is not None:
                current_ra.claim_status = _classify_claim_status(
                    current_ra.paid_amount, current_billed,
                )
                remittances.append(current_ra)

            claim_id = elems[1] if len(elems) > 1 else ""
            # CLP02 status: 1=processed/primary, 2=processed/secondary, etc.
            billed = 0.0
            paid = 0.0
            if len(elems) > 3:
                try:
                    billed = float(elems[3])
                except (ValueError, IndexError):
                    pass
            if len(elems) > 4:
                try:
                    paid = float(elems[4])
                except (ValueError, IndexError):
                    pass
            current_billed = billed
            current_ra = RemittanceAdvice(
                claim_id=claim_id,
                paid_amount=paid,
            )

        elif seg_id == "CAS" and current_ra is not None:
            # CAS*group_code*carc_code*amount*quantity[*carc*amt*qty]*...
            # group codes: CO (contractual), PR (patient resp), OA, PI, CR
            i = 2
            while i < len(elems):
                carc = elems[i].strip()
                if carc:
                    current_ra.carc_codes.append(carc)
                # Amount follows the CARC
                if i + 1 < len(elems):
                    try:
                        adj_amt = float(elems[i + 1])
                        current_ra.denial_amount += adj_amt
                    except (ValueError, IndexError):
                        pass
                i += 3  # skip to next carc triplet

        elif seg_id == "SVC" and current_ra is not None:
            # SVC*procedure*charge*paid*...*
            # Service-level detail; aggregate adjustments already in CAS
            pass

        elif seg_id == "DTM" and current_ra is not None:
            # DTM*036*20250201  (adjudication date)
            if len(elems) > 2 and elems[1] in ("036", "573"):
                current_ra.adjudication_date = elems[2].strip()

    # Flush last
    if current_ra is not None:
        current_ra.claim_status = _classify_claim_status(
            current_ra.paid_amount, current_billed,
        )
        remittances.append(current_ra)

    return remittances


# ── Matching ──────────────────────────────────────────────────────────

def match_837_835(
    submissions: list[ClaimSubmission],
    remittances: list[RemittanceAdvice],
) -> list[dict]:
    """Join submissions and remittances on claim_id.

    Returns a list of dicts combining both sides plus computed fields
    like turnaround_days and denial_reason.
    """
    sub_map: dict[str, ClaimSubmission] = {s.claim_id: s for s in submissions}
    matched: list[dict] = []

    for ra in remittances:
        sub = sub_map.get(ra.claim_id)
        if sub is None:
            # Remittance without a matching submission — still record it
            rec = {
                "claim_id": ra.claim_id,
                "payer": "",
                "provider_npi": "",
                "service_date": "",
                "total_charge": 0.0,
                "dx_codes": [],
                "drg_code": "",
                "paid_amount": ra.paid_amount,
                "adjudication_date": ra.adjudication_date,
                "claim_status": ra.claim_status,
                "carc_codes": ra.carc_codes,
                "denial_amount": ra.denial_amount,
                "turnaround_days": None,
                "denial_reason": ra.carc_codes[0] if ra.carc_codes else "",
            }
        else:
            turnaround = _compute_turnaround(sub.service_date, ra.adjudication_date)
            rec = {
                "claim_id": sub.claim_id,
                "payer": sub.payer,
                "provider_npi": sub.provider_npi,
                "service_date": sub.service_date,
                "total_charge": sub.total_charge,
                "dx_codes": sub.dx_codes,
                "drg_code": sub.drg_code,
                "paid_amount": ra.paid_amount,
                "adjudication_date": ra.adjudication_date,
                "claim_status": ra.claim_status,
                "carc_codes": ra.carc_codes,
                "denial_amount": ra.denial_amount,
                "turnaround_days": turnaround,
                "denial_reason": ra.carc_codes[0] if ra.carc_codes else "",
            }
        matched.append(rec)

    return matched


def _compute_turnaround(service_date: str, adjudication_date: str) -> Optional[int]:
    """Compute days between service and adjudication dates (YYYYMMDD or YYYY-MM-DD)."""
    if not service_date or not adjudication_date:
        return None
    try:
        fmt = "%Y%m%d" if len(service_date) == 8 else "%Y-%m-%d"
        sd = datetime.strptime(service_date, fmt).date()
        fmt2 = "%Y%m%d" if len(adjudication_date) == 8 else "%Y-%m-%d"
        ad = datetime.strptime(adjudication_date, fmt2).date()
        return (ad - sd).days
    except (ValueError, TypeError):
        return None


# ── SQLite persistence ────────────────────────────────────────────────

def _ensure_claim_table(store: Any) -> None:
    """Create claim_records table if it doesn't exist."""
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS claim_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                claim_id TEXT NOT NULL,
                payer TEXT,
                provider_npi TEXT,
                service_date TEXT,
                total_charge REAL,
                dx_codes_json TEXT,
                drg_code TEXT,
                paid_amount REAL,
                adjudication_date TEXT,
                claim_status TEXT,
                carc_codes_json TEXT,
                denial_amount REAL,
                turnaround_days INTEGER,
                denial_reason TEXT,
                created_at TEXT NOT NULL
            )"""
        )
        con.commit()


def save_claims(store: Any, deal_id: str, records: list[dict]) -> int:
    """Persist matched claim records to SQLite. Returns count inserted."""
    _ensure_claim_table(store)
    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    with store.connect() as con:
        for rec in records:
            con.execute(
                """INSERT INTO claim_records
                   (deal_id, claim_id, payer, provider_npi, service_date,
                    total_charge, dx_codes_json, drg_code, paid_amount,
                    adjudication_date, claim_status, carc_codes_json,
                    denial_amount, turnaround_days, denial_reason, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    deal_id,
                    rec.get("claim_id", ""),
                    rec.get("payer", ""),
                    rec.get("provider_npi", ""),
                    rec.get("service_date", ""),
                    rec.get("total_charge", 0.0),
                    json.dumps(rec.get("dx_codes", [])),
                    rec.get("drg_code", ""),
                    rec.get("paid_amount", 0.0),
                    rec.get("adjudication_date", ""),
                    rec.get("claim_status", ""),
                    json.dumps(rec.get("carc_codes", [])),
                    rec.get("denial_amount", 0.0),
                    rec.get("turnaround_days"),
                    rec.get("denial_reason", ""),
                    now,
                ),
            )
            inserted += 1
        con.commit()
    return inserted


def load_claims(store: Any, deal_id: str) -> list[dict]:
    """Load claim records for a deal from SQLite."""
    _ensure_claim_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT * FROM claim_records WHERE deal_id = ? ORDER BY id",
            (deal_id,),
        ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["dx_codes"] = json.loads(d.pop("dx_codes_json", "[]"))
        d["carc_codes"] = json.loads(d.pop("carc_codes_json", "[]"))
        result.append(d)
    return result
