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

# 835 exports routinely prefix the CARC with its group code ("CO-45",
# "PR1") — strip a leading CO/OA/PI/PR/CR so playbook and description
# lookups (which key on the bare code) still hit. The lookahead keeps
# genuine letter codes (P1, W1, B7) intact: only a group code FOLLOWED
# by another code is a prefix.
_CARC_PREFIX_RE = re.compile(r"^(?:CO|OA|PI|PR|CR)[-\s]?(?=[A-Z]?\d)")


def _bare_carc(tok: str) -> str:
    return _CARC_PREFIX_RE.sub("", tok)


def _norm_claim(v: str) -> str:
    """Join-key normalization: 835s often render the patient control number
    with different casing or leading-zero padding than the 837 extract
    ('0001234' vs '1234'); an exact-string join then reports ~0% match with
    every claim listed both unpaid and orphan. Case-fold + strip, and strip
    leading zeros on purely-numeric ids."""
    s = v.strip().upper()
    if s.isdigit():
        s = s.lstrip("0") or "0"
    return s


def _id_shape(s: str) -> str:
    """Coarse shape of a claim id ('digits(7)', 'alnum(9)') — the low-match
    diagnostic shows the top shapes per side so a user can SEE why two
    exports didn't join."""
    if s.isdigit():
        return f"digits({len(s)})"
    if s.isalpha():
        return f"alpha({len(s)})"
    return f"alnum({len(s)})"


def _aggregate(headers: List[str],
               rows: List[List[str]]) -> Optional[Dict[str, Dict]]:
    """Per-claim rollup of one side: lines, billed, paid, CARCs. Keyed on
    the NORMALIZED claim id; ``display`` keeps the first raw spelling and
    ``raw_ids`` the exact-string keys (for the normalization audit note)."""
    ci = _detect_one(headers, _CLAIM_HINTS)
    if ci is None:
        return None
    bi = _detect_one(headers, _BILLED_HINTS)
    pi = _detect_one(headers, _PAID_HINTS)
    di = _detect_one(headers, _CARC_HINTS)
    per: Dict[str, Dict] = {}
    raw_ids: set = set()
    for row in rows:
        if ci >= len(row) or not row[ci]:
            continue
        raw = row[ci].strip()
        if not raw:
            continue
        raw_ids.add(raw)
        e = per.setdefault(_norm_claim(raw),
                           {"lines": 0, "billed": 0.0,
                            "paid": 0.0, "carcs": set(), "display": raw})
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
                    e["carcs"].add(_bare_carc(c))
    return {"per": per, "raw_ids": raw_ids}


def reconcile(headers_a: List[str], rows_a: List[List[str]],
              headers_b: List[str],
              rows_b: List[List[str]]) -> Dict[str, object]:
    """Match side A (claims / 837) against side B (remittance / 835)."""
    agg_a = _aggregate(headers_a, rows_a)
    agg_b = _aggregate(headers_b, rows_b)
    if agg_a is None or agg_b is None:
        side = "first" if agg_a is None else "second"
        return {"error": f"No claim-id column detected in the {side} run — "
                         "reconciliation matches on claim id."}
    per_a, per_b = agg_a["per"], agg_b["per"]
    ids_a, ids_b = set(per_a), set(per_b)
    matched = sorted(ids_a & ids_b)
    unpaid = sorted(ids_a - ids_b,
                    key=lambda c: -per_a[c]["billed"])
    orphans = sorted(ids_b - ids_a,
                     key=lambda c: -per_b[c]["paid"])

    billed_m = sum(per_a[c]["billed"] for c in matched)
    paid_m = sum(per_b[c]["paid"] for c in matched)
    variance = sorted(
        ({"claim": per_a[c]["display"],
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

    # Headline dollars — the numbers this pass exists to answer. The
    # top-25 lists truncate, so total unmatched exposure must be summed
    # across ALL unmatched claims, not just the listed ones.
    unpaid_billed_total = sum(per_a[c]["billed"] for c in unpaid)
    unpaid_lines_total = sum(per_a[c]["lines"] for c in unpaid)
    orphan_paid_total = sum(per_b[c]["paid"] for c in orphans)
    billed_all_a = billed_m + unpaid_billed_total
    matched_pct_of_billed = (round(100 * billed_m / billed_all_a, 1)
                             if billed_all_a > 0 else None)

    out: Dict[str, object] = {
        "claims_a": n_a,
        "claims_b": n_b,
        "matched": len(matched),
        "match_rate_pct": round(100 * len(matched) / n_a, 1) if n_a else 0.0,
        "matched_pct_of_billed": matched_pct_of_billed,
        "unpaid_count": len(unpaid),
        "unpaid_billed_total": round(unpaid_billed_total, 2),
        "unpaid_lines_total": unpaid_lines_total,
        "unpaid": [{"claim": per_a[c]["display"],
                    "billed": round(per_a[c]["billed"], 2),
                    "lines": per_a[c]["lines"]}
                   for c in unpaid[:_TOP_CAP]],
        "orphan_remits_count": len(orphans),
        "orphan_paid_total": round(orphan_paid_total, 2),
        "orphan_remits": [{"claim": per_b[c]["display"],
                           "paid": round(per_b[c]["paid"], 2)}
                          for c in orphans[:_TOP_CAP]],
        "billed_matched": round(billed_m, 2),
        "paid_matched": round(paid_m, 2),
        "variance_total": round(billed_m - paid_m, 2),
        "top_variance": variance[:_TOP_CAP],
        "denials": denials,
    }

    # Audit note when the id normalization actually created matches — the
    # user should know the join was fuzzy-on-padding/case, and how much.
    raw_matched = len(agg_a["raw_ids"] & agg_b["raw_ids"])
    if len(matched) > raw_matched:
        out["note"] = (f"{len(matched) - raw_matched} of {len(matched)} "
                       "matched claim ids joined only after normalization "
                       "(case / whitespace / leading zeros).")

    # Near-zero match with real volume on both sides → show WHY: the top
    # id shapes per side, so 'account numbers vs ICNs' is visible at a
    # glance instead of a silent 0%.
    if n_a >= 5 and n_b >= 5 and out["match_rate_pct"] < 5.0:
        def _top_shapes(per: Dict[str, Dict]) -> List[Dict[str, object]]:
            shapes: Dict[str, int] = {}
            for k in per:
                s = _id_shape(k)
                shapes[s] = shapes.get(s, 0) + 1
            return [{"shape": s, "claims": n}
                    for s, n in sorted(shapes.items(),
                                       key=lambda kv: -kv[1])[:3]]
        out["id_shapes"] = {"a": _top_shapes(per_a),
                            "b": _top_shapes(per_b)}
    return out
