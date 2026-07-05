"""837↔835 reconciliation — did the payer answer, and for how much?

The claims file (837 / billing extract) says what went out the door; the
remittance (835 / payment posting) says what came back. Matching the two
on claim id answers the questions a revenue-cycle team actually works:

  * which claims have NO remittance at all (silent — chase them),
  * how paid compares to billed per matched claim (variance),
  * which denial reasons dominate the paid side (with the playbook).

Pure table-in/report-out: both sides are CLEANED outputs of the engine,
so claim ids, amounts, and CARCs are already normalized. Column roles
re-use the engine's own hint vocabulary — anything the cleaner detected
as a claim id / billed / paid column reconciles the same way here.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from .engine import _CARC_HINTS, _detect_one, _to_number

_CLAIM_HINTS = ("claimid", "claimnumber", "claimno",
                "patientcontrolnumber", "icn", "dcn")
_BILLED_HINTS = ("billedamt", "billed", "chargeamt", "charge",
                 "submittedamt")
_PAID_HINTS = ("paidamt", "paymentamt", "planpaid", "paid")

_TOP_CAP = 25          # rows listed per section — the report is a summary


def _aggregate(headers: List[str],
               rows: List[List[str]]) -> Optional[Dict[str, Dict]]:
    """Per-claim rollup of one side: lines, billed, paid, CARCs."""
    ci = _detect_one(headers, _CLAIM_HINTS)
    if ci is None:
        return None
    bi = _detect_one(headers, _BILLED_HINTS)
    pi = _detect_one(headers, _PAID_HINTS)
    di = _detect_one(headers, _CARC_HINTS)
    per: Dict[str, Dict] = {}
    for row in rows:
        if ci >= len(row) or not row[ci]:
            continue
        e = per.setdefault(row[ci], {"lines": 0, "billed": 0.0,
                                     "paid": 0.0, "carcs": set()})
        e["lines"] += 1
        if bi is not None and bi < len(row):
            v = _to_number(row[bi])
            if v is not None:
                e["billed"] += v
        if pi is not None and pi < len(row):
            v = _to_number(row[pi])
            if v is not None:
                e["paid"] += v
        if di is not None and di < len(row) and row[di]:
            for c in re.split(r"[,;|\s]+", row[di].strip().upper()):
                if c:
                    e["carcs"].add(c)
    return per


def reconcile(headers_a: List[str], rows_a: List[List[str]],
              headers_b: List[str],
              rows_b: List[List[str]]) -> Dict[str, object]:
    """Match side A (claims / 837) against side B (remittance / 835)."""
    per_a = _aggregate(headers_a, rows_a)
    per_b = _aggregate(headers_b, rows_b)
    if per_a is None or per_b is None:
        side = "first" if per_a is None else "second"
        return {"error": f"No claim-id column detected in the {side} run — "
                         "reconciliation matches on claim id."}
    ids_a, ids_b = set(per_a), set(per_b)
    matched = sorted(ids_a & ids_b)
    unpaid = sorted(ids_a - ids_b,
                    key=lambda c: -per_a[c]["billed"])
    orphans = sorted(ids_b - ids_a,
                     key=lambda c: -per_b[c]["paid"])

    billed_m = sum(per_a[c]["billed"] for c in matched)
    paid_m = sum(per_b[c]["paid"] for c in matched)
    variance = sorted(
        ({"claim": c,
          "billed": round(per_a[c]["billed"], 2),
          "paid": round(per_b[c]["paid"], 2),
          "delta": round(per_a[c]["billed"] - per_b[c]["paid"], 2),
          "carcs": sorted(per_b[c]["carcs"])}
         for c in matched),
        key=lambda e: -e["delta"])

    # Denial mix on the remit side, playbook-enriched where known.
    carc_counts: Dict[str, int] = {}
    for c in ids_b:
        for code in per_b[c]["carcs"]:
            carc_counts[code] = carc_counts.get(code, 0) + 1
    try:
        from . import refdata as _rd
    except Exception:  # noqa: BLE001
        _rd = None
    denials = []
    for code, n in sorted(carc_counts.items(), key=lambda kv: -kv[1])[:10]:
        e: Dict[str, object] = {"code": code, "claims": n}
        pb = _rd.carc_playbook(code) if _rd is not None else None
        if pb:
            e["category"] = pb["category"]
            e["action"] = pb["action"]
        denials.append(e)

    n_a, n_b = len(ids_a), len(ids_b)
    return {
        "claims_a": n_a,
        "claims_b": n_b,
        "matched": len(matched),
        "match_rate_pct": round(100 * len(matched) / n_a, 1) if n_a else 0.0,
        "unpaid_count": len(unpaid),
        "unpaid": [{"claim": c, "billed": round(per_a[c]["billed"], 2),
                    "lines": per_a[c]["lines"]}
                   for c in unpaid[:_TOP_CAP]],
        "orphan_remits_count": len(orphans),
        "orphan_remits": [{"claim": c,
                           "paid": round(per_b[c]["paid"], 2)}
                          for c in orphans[:_TOP_CAP]],
        "billed_matched": round(billed_m, 2),
        "paid_matched": round(paid_m, 2),
        "variance_total": round(billed_m - paid_m, 2),
        "top_variance": variance[:_TOP_CAP],
        "denials": denials,
    }
