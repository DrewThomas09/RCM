"""X12 837 (EDI) claim extractor — the native claims wire format.

Claims teams live in two worlds: tabular extracts (CSV/XLSX) and the raw
X12 837 files that actually move between providers, clearinghouses, and
payers. This module lets the cleaner ingest the second world directly: a
pragmatic, segment-level 837P/837I reader that flattens claims to one row
per SERVICE LINE (the shape every downstream check expects), then hands
the table to the normal cleaning pipeline — NPI Luhn checks, code shape
screens, TOB/POS domains, timely filing, de-identification, all of it.

Deliberately NOT a full X12 validator: separators are taken from the ISA
envelope per spec (element = byte 3, component/terminator = after the
16th element), unknown segments are skipped, and anything that doesn't
contain an 837 CLM loop returns None so the caller can say "this is X12
but not claims" instead of silently emitting an empty file. Stdlib only.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

# One row per service line, in a header vocabulary the engine's role
# detection already understands (BillingNPI → billing column, TypeOfBill →
# TOB domain check, PatientName → de-id target, …).
HEADERS: List[str] = [
    "ClaimID", "PayerName", "BillingProviderName", "BillingNPI",
    "RenderingNPI", "AttendingNPI", "PatientName", "DateOfService",
    "PlaceOfService", "TypeOfBill", "RevenueCode", "HCPCS", "Modifiers",
    "DiagnosisCode", "Units", "BilledAmt",
]


def looks_like_x12(data: bytes) -> bool:
    """An interchange starts with "ISA" + a one-byte element separator.
    The separator is never alphanumeric, which cheaply rejects CSVs whose
    first header happens to start with "ISA…"."""
    head = data.lstrip()[:4]
    if len(head) < 4 or not head.startswith(b"ISA"):
        return False
    sep = head[3:4]
    return not sep.isalnum() and sep not in (b" ",)


def _separators(text: str) -> Tuple[str, str, str]:
    """(element, component, segment-terminator) from the ISA envelope.

    Spec-exact rather than fixed-width: real-world ISA segments are often
    not padded correctly, but the 16th element separator is always
    followed by the component separator and then the terminator."""
    elem = text[3]
    count = 0
    for pos in range(3, min(len(text), 512)):
        if text[pos] == elem:
            count += 1
            if count == 16:
                comp = text[pos + 1] if pos + 1 < len(text) else ":"
                term = text[pos + 2] if pos + 2 < len(text) else "~"
                if term in "\r\n" or term.isalnum():
                    term = "~"
                return elem, comp, term
    return elem, ":", "~"


def _date_iso(v: str) -> str:
    """CCYYMMDD → ISO; RD8 ranges (start-end) keep the start date."""
    v = v.split("-")[0].strip()
    if len(v) == 8 and v.isdigit():
        return f"{v[0:4]}-{v[4:6]}-{v[6:8]}"
    return v


def x12_to_table(data: bytes) -> Optional[Tuple[List[str], List[List[str]]]]:
    """Flatten an 837 interchange to (HEADERS, rows). None when the file
    is X12 but carries no CLM segments (an 835/999/270…), so the caller
    can produce a precise warning instead of an empty table."""
    text = data.decode("latin-1", errors="replace").lstrip()
    if not text.startswith("ISA"):
        return None
    elem, comp, term = _separators(text)
    segs = []
    for raw_seg in text.split(term):
        s = raw_seg.strip("\r\n ")
        if s:
            segs.append(s.split(elem))

    rows: List[List[str]] = []
    txn = ""                      # "prof" | "inst" | ""
    ctx: Dict[str, str] = {}      # provider/payer/patient context
    claim: Dict[str, str] = {}    # current CLM-level fields
    line: Optional[Dict[str, str]] = None
    claim_lines = 0

    def flush_line() -> None:
        nonlocal line, claim_lines
        if line is None:
            return
        rows.append(_row(ctx, claim, line))
        claim_lines += 1
        line = None

    def flush_claim() -> None:
        nonlocal claim, claim_lines
        flush_line()
        if claim and claim_lines == 0:
            # A claim with no service lines still deserves a row — its
            # header-level fields (NPIs, dates, charge) are checkable.
            rows.append(_row(ctx, claim, {}))
        claim = {}
        claim_lines = 0

    for seg in segs:
        tag = seg[0].upper()

        if tag == "ST":
            flush_claim()
            ref = seg[3] if len(seg) > 3 else ""
            txn = ("prof" if "X222" in ref else
                   "inst" if "X223" in ref else txn)
        elif tag == "GS":
            ref = seg[8] if len(seg) > 8 else ""
            if "X222" in ref:
                txn = "prof"
            elif "X223" in ref:
                txn = "inst"
        elif tag == "NM1" and len(seg) > 3:
            qual = seg[1]
            is_person = (seg[2] if len(seg) > 2 else "") == "1"
            last_or_org = seg[3] if len(seg) > 3 else ""
            first = seg[4] if len(seg) > 4 else ""
            id_qual = seg[8] if len(seg) > 8 else ""
            ident = seg[9] if len(seg) > 9 else ""
            name = (f"{last_or_org}, {first}" if is_person and first
                    else last_or_org)
            if qual == "85":                       # billing provider
                ctx["billing_name"] = name
                if id_qual == "XX":
                    ctx["billing_npi"] = ident
            elif qual == "82" and id_qual == "XX":  # rendering
                ctx["rendering_npi"] = ident
            elif qual == "71" and id_qual == "XX":  # attending (837I)
                ctx["attending_npi"] = ident
            elif qual == "PR":                     # payer
                ctx["payer"] = last_or_org
            elif qual in ("IL", "QC") and is_person:
                ctx["patient"] = name
        elif tag == "CLM" and len(seg) > 1:
            flush_claim()
            # Rendering/attending live in the 2310 loops AFTER their CLM —
            # they must not leak forward into the next claim.
            ctx.pop("rendering_npi", None)
            ctx.pop("attending_npi", None)
            claim = {"claim_id": seg[1],
                     "total": seg[2] if len(seg) > 2 else ""}
            # CLM05 composite: facility/POS code : qualifier : frequency.
            if len(seg) > 5 and seg[5]:
                parts = seg[5].split(comp)
                code = parts[0] if parts else ""
                freq = parts[2] if len(parts) > 2 else ""
                if txn == "inst":
                    claim["tob"] = (code + freq) if code else ""
                else:
                    claim["pos"] = code
                    claim["clm05_freq"] = freq
        elif tag == "DTP" and len(seg) > 3:
            when = _date_iso(seg[3])
            if seg[1] == "472":                    # service date
                if line is not None:
                    line["dos"] = when
                else:
                    claim.setdefault("dos", when)
            elif seg[1] == "434":                  # statement period (837I)
                claim.setdefault("dos", when)
        elif tag == "HI" and len(seg) > 1 and claim:
            parts = seg[1].split(comp)
            if len(parts) > 1 and parts[0].upper() in ("ABK", "BK"):
                claim.setdefault("dx", parts[1])
        elif tag == "LX":
            flush_line()
        elif tag == "SV1" and len(seg) > 1:        # professional line
            flush_line()
            parts = seg[1].split(comp)
            code = parts[1] if len(parts) > 1 else parts[0]
            mods = [p for p in parts[2:6] if len(p) == 2 and p.isalnum()]
            line = {"hcpcs": code, "mods": ",".join(mods),
                    "charge": seg[2] if len(seg) > 2 else "",
                    "units": seg[4] if len(seg) > 4 else "",
                    "pos": seg[5] if len(seg) > 5 else ""}
        elif tag == "SV2" and len(seg) > 1:        # institutional line
            flush_line()
            code = ""
            mods: List[str] = []
            if len(seg) > 2 and seg[2]:
                parts = seg[2].split(comp)
                code = parts[1] if len(parts) > 1 else ""
                mods = [p for p in parts[2:6] if len(p) == 2 and p.isalnum()]
            line = {"rev": seg[1], "hcpcs": code, "mods": ",".join(mods),
                    "charge": seg[3] if len(seg) > 3 else "",
                    "units": seg[5] if len(seg) > 5 else ""}
        elif tag == "SE":
            flush_claim()

    flush_claim()
    if not rows:
        return None
    return list(HEADERS), rows


def _row(ctx: Dict[str, str], claim: Dict[str, str],
         line: Dict[str, str]) -> List[str]:
    return [
        claim.get("claim_id", ""),
        ctx.get("payer", ""),
        ctx.get("billing_name", ""),
        ctx.get("billing_npi", ""),
        ctx.get("rendering_npi", ""),
        ctx.get("attending_npi", ""),
        ctx.get("patient", ""),
        line.get("dos") or claim.get("dos", ""),
        line.get("pos") or claim.get("pos", ""),
        claim.get("tob", ""),
        line.get("rev", ""),
        line.get("hcpcs", ""),
        line.get("mods", ""),
        claim.get("dx", ""),
        line.get("units", ""),
        line.get("charge") or claim.get("total", ""),
    ]
