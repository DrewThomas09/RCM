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
    "RenderingNPI", "AttendingNPI", "ReferringNPI", "OrderingNPI",
    "OperatingNPI", "PatientName", "DateOfService",
    "PlaceOfService", "TypeOfBill", "RevenueCode", "HCPCS", "Modifiers",
    "DiagnosisCode", "Units", "BilledAmt",
]


def looks_like_x12(data: bytes) -> bool:
    """An interchange starts with "ISA" + a one-byte element separator.
    The separator is never alphanumeric, which cheaply rejects CSVs whose
    first header happens to start with "ISA…" — EXCEPT when the separator
    itself is a CSV delimiter ("ISA,BillingNPI" / "ISA\\tBillingNPI").
    For those, the full ISA envelope shape is required: a real ISA carries
    16 elements (≥16 separators) before its first line break, while a CSV
    header cell named "ISA" is followed by a newline long before that."""
    head = data.lstrip()[:4]
    if len(head) < 4 or not head.startswith(b"ISA"):
        return False
    sep = head[3:4]
    if sep.isalnum() or sep in (b" ",):
        return False
    if sep in (b",", b";", b"|", b"\t"):
        probe = data.lstrip()[:200]
        nl = probe.find(b"\n")
        window = probe if nl < 0 else probe[:nl]
        if window.count(sep) < 16:
            return False
    return True


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
                # A line-level 2420A rendering provider overrides the
                # claim-level 2310B for THAT LINE ONLY — stored on the open
                # line (cleared at flush) so it can't leak onto subsequent
                # lines of the same claim that lack their own 2420A.
                if line is not None:
                    line["rendering"] = ident
                else:
                    ctx["rendering_npi"] = ident
            elif qual == "71" and id_qual == "XX":  # attending (837I)
                ctx["attending_npi"] = ident
            elif qual in ("DN", "P3") and id_qual == "XX":  # referring
                if line is not None:               # 2420F line-level
                    line["referring"] = ident
                else:                              # 2310A claim-level
                    ctx["referring_npi"] = ident
            elif qual == "DK" and id_qual == "XX":  # ordering (2420E)
                if line is not None:
                    line["ordering"] = ident
                else:
                    ctx["ordering_npi"] = ident
            elif qual == "72" and id_qual == "XX":  # operating (837I)
                ctx["operating_npi"] = ident
            elif qual == "PR":                     # payer
                ctx["payer"] = last_or_org
            elif qual in ("IL", "QC") and is_person:
                ctx["patient"] = name
        elif tag == "CLM" and len(seg) > 1:
            flush_claim()
            # Per-claim provider loops (2310) live AFTER their CLM — they
            # must not leak forward into the next claim.
            ctx.pop("rendering_npi", None)
            ctx.pop("attending_npi", None)
            ctx.pop("referring_npi", None)
            ctx.pop("ordering_npi", None)
            ctx.pop("operating_npi", None)
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


# ---------------------------------------------------------------------------
# 835 remittance (ERA) — the payer's answer to the 837. One row per service
# line (SVC) or per claim payment (CLP) when a claim has no line detail.
# CAS adjustments flatten to a CARC list (feeds the existing denial
# analytics + CARC catalog) plus a per-row audit string with group codes
# and dollar amounts (CO-45:12.50 …).
# ---------------------------------------------------------------------------
# PayeeName precedes PayerName deliberately: the engine's generic "name"
# hint takes the FIRST matching column for NPPES recovery, and the payee
# IS the provider — with payer first, recovery queried NPPES with the
# insurance company's name.
HEADERS_835: List[str] = [
    "ClaimID", "PayerClaimID", "ClaimStatus", "PayeeName", "PayeeNPI",
    "PayerName", "PatientName", "DateOfService", "PaidDate", "RevenueCode",
    "HCPCS", "Modifiers", "Units", "BilledAmt", "PaidAmt", "PatientResp",
    "DenialCodes", "AdjustmentDetail",
]


def x835_to_table(data: bytes) -> Optional[Tuple[List[str], List[List[str]]]]:
    """Flatten an 835 interchange to (HEADERS_835, rows). None when the
    file carries no CLP segments (it's some other transaction set)."""
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
    env: Dict[str, str] = {}      # payer / payee / paid-date context
    clp: Dict[str, str] = {}      # current claim payment
    clp_adjs: List[str] = []      # claim-level CAS audit strings
    clp_carcs: List[str] = []     # claim-level CARC codes
    svc: Optional[Dict[str, object]] = None   # carries its own CAS lists
    clp_lines = 0

    def _row835(line: Dict[str, object]) -> List[str]:
        codes = clp_carcs + list(line.get("carcs") or [])
        detail = clp_adjs + list(line.get("adjs") or [])
        return [
            clp.get("claim_id", ""), clp.get("payer_icn", ""),
            clp.get("status", ""), env.get("payee", ""),
            env.get("payee_npi", ""), env.get("payer", ""),
            clp.get("patient", ""),
            str(line.get("dos") or clp.get("dos", "")),
            env.get("paid_date", ""), str(line.get("rev", "")),
            str(line.get("hcpcs", "")), str(line.get("mods", "")),
            str(line.get("units", "")),
            str(line.get("billed") or clp.get("billed", "")),
            str(line.get("paid") or clp.get("paid", "")),
            clp.get("pt_resp", ""),
            ", ".join(dict.fromkeys(codes)),
            "; ".join(detail),
        ]

    def flush_svc() -> None:
        nonlocal svc, clp_lines
        if svc is None:
            return
        rows.append(_row835(svc))
        clp_lines += 1
        svc = None

    def flush_clp() -> None:
        nonlocal clp, clp_adjs, clp_carcs, clp_lines
        flush_svc()
        if clp and clp_lines == 0:
            rows.append(_row835({}))
        clp = {}
        clp_adjs = []
        clp_carcs = []
        clp_lines = 0

    for seg in segs:
        tag = seg[0].upper()
        if tag == "N1" and len(seg) > 2:
            if seg[1] == "PR":
                env["payer"] = seg[2]
            elif seg[1] == "PE":
                env["payee"] = seg[2]
                if len(seg) > 4 and seg[3] == "XX":
                    env["payee_npi"] = seg[4]
        elif tag == "DTM" and len(seg) > 2:
            when = _date_iso(seg[2])
            if seg[1] == "405":                    # production date
                env.setdefault("paid_date", when)
            elif seg[1] == "472" and svc is not None:
                svc["dos"] = when                  # per-line service date
            elif seg[1] in ("232", "472"):         # claim statement date
                if clp:
                    clp.setdefault("dos", when)
        elif tag == "CLP" and len(seg) > 4:
            flush_clp()
            clp = {"claim_id": seg[1], "status": seg[2],
                   "billed": seg[3], "paid": seg[4],
                   "pt_resp": seg[5] if len(seg) > 5 else "",
                   "payer_icn": seg[7] if len(seg) > 7 else ""}
        elif tag == "NM1" and len(seg) > 3 and clp:
            if seg[1] == "QC" and (seg[2] if len(seg) > 2 else "") == "1":
                first = seg[4] if len(seg) > 4 else ""
                clp["patient"] = (f"{seg[3]}, {first}" if first else seg[3])
        elif tag == "CAS" and len(seg) > 3 and clp:
            group = seg[1]
            _c_sink = (svc["carcs"] if svc is not None else clp_carcs)
            _a_sink = (svc["adjs"] if svc is not None else clp_adjs)
            i = 2
            while i + 1 < len(seg):
                reason, amount = seg[i], seg[i + 1]
                if reason:
                    _c_sink.append(reason)
                    _a_sink.append(f"{group}-{reason}:{amount or '0'}")
                i += 3                              # (reason, amt, qty) triplets
        elif tag == "SVC" and len(seg) > 3:
            flush_svc()
            parts = seg[1].split(comp) if seg[1] else []
            code = parts[1] if len(parts) > 1 else (parts[0] if parts else "")
            mods = [p for p in parts[2:6] if len(p) == 2 and p.isalnum()]
            rev = seg[4] if len(seg) > 4 else ""
            svc = {"hcpcs": code, "mods": ",".join(mods),
                   "billed": seg[2], "paid": seg[3],
                   "rev": rev if (rev.isdigit() and len(rev) == 4) else "",
                   "units": seg[5] if len(seg) > 5 else "",
                   "carcs": [], "adjs": []}
        elif tag in ("SE", "ST"):
            flush_clp()

    flush_clp()
    if not rows:
        return None
    return list(HEADERS_835), rows


def _row(ctx: Dict[str, str], claim: Dict[str, str],
         line: Dict[str, str]) -> List[str]:
    return [
        claim.get("claim_id", ""),
        ctx.get("payer", ""),
        ctx.get("billing_name", ""),
        ctx.get("billing_npi", ""),
        # Line-level 2420 providers win over the claim-level 2310 loop for
        # their own line only (see the NM1 handler).
        line.get("rendering") or ctx.get("rendering_npi", ""),
        ctx.get("attending_npi", ""),
        line.get("referring") or ctx.get("referring_npi", ""),
        line.get("ordering") or ctx.get("ordering_npi", ""),
        ctx.get("operating_npi", ""),
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
