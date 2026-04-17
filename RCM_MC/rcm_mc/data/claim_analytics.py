"""Claim analytics: denial rates, top denial reasons, payer aging (Prompt 75).

Operates on the ``claim_records`` table populated by ``edi_parser.save_claims``.
All queries are parameterised and read-only.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _ensure_claim_table(store: Any) -> None:
    """Guarantee the claim_records table exists before querying."""
    from .edi_parser import _ensure_claim_table as _ect
    _ect(store)


# ── Denial rate by dimension ─────────────────────────────────────────

def denial_rate_by_dimension(
    store: Any,
    deal_id: str,
    *,
    dimension: str = "payer",
) -> dict:
    """Aggregate claim_records by a given dimension and compute denial rates.

    Supported dimensions:
      - ``payer``:  group by payer name
      - ``carc``:   group by CARC code (one row per code per claim)
      - ``status``: group by claim_status

    Returns ``{dimension_value: {total: int, denied: int, denial_rate: float,
    denial_dollars: float}}``.
    """
    _ensure_claim_table(store)
    valid_dimensions = {"payer", "carc", "status"}
    if dimension not in valid_dimensions:
        raise ValueError(f"dimension must be one of {valid_dimensions}")

    with store.connect() as con:
        rows = con.execute(
            "SELECT * FROM claim_records WHERE deal_id = ?",
            (deal_id,),
        ).fetchall()

    # Build per-dimension buckets
    buckets: dict[str, dict] = defaultdict(
        lambda: {"total": 0, "denied": 0, "denial_dollars": 0.0},
    )

    for row in rows:
        r = dict(row)
        status = r.get("claim_status", "")
        is_denied = status == "denied"
        denial_amt = float(r.get("denial_amount", 0))

        if dimension == "payer":
            key = r.get("payer", "") or "Unknown"
            buckets[key]["total"] += 1
            if is_denied:
                buckets[key]["denied"] += 1
                buckets[key]["denial_dollars"] += denial_amt

        elif dimension == "status":
            key = status or "unknown"
            buckets[key]["total"] += 1
            if is_denied:
                buckets[key]["denied"] += 1
                buckets[key]["denial_dollars"] += denial_amt

        elif dimension == "carc":
            carc_json = r.get("carc_codes_json", "[]")
            codes = json.loads(carc_json) if carc_json else []
            if not codes:
                codes = ["none"]
            for code in codes:
                buckets[code]["total"] += 1
                if is_denied:
                    buckets[code]["denied"] += 1
                    buckets[code]["denial_dollars"] += denial_amt

    # Compute rates
    result: dict = {}
    for key, b in buckets.items():
        total = b["total"]
        denied = b["denied"]
        result[key] = {
            "total": total,
            "denied": denied,
            "denial_rate": round(denied / total, 4) if total else 0.0,
            "denial_dollars": round(b["denial_dollars"], 2),
        }

    return result


# ── Top denial reasons ───────────────────────────────────────────────

def top_denial_reasons(
    store: Any,
    deal_id: str,
    *,
    limit: int = 10,
) -> list[dict]:
    """Rank CARC codes by frequency and dollar impact.

    Returns up to *limit* dicts:
    ``[{carc: str, count: int, total_denial_dollars: float, pct_of_denials: float}]``
    sorted by count descending.
    """
    _ensure_claim_table(store)

    with store.connect() as con:
        rows = con.execute(
            "SELECT carc_codes_json, denial_amount, claim_status "
            "FROM claim_records WHERE deal_id = ?",
            (deal_id,),
        ).fetchall()

    carc_freq: dict[str, int] = defaultdict(int)
    carc_dollars: dict[str, float] = defaultdict(float)
    total_denied_claims = 0

    for row in rows:
        r = dict(row)
        codes = json.loads(r.get("carc_codes_json", "[]") or "[]")
        denial_amt = float(r.get("denial_amount", 0))
        status = r.get("claim_status", "")
        if status in ("denied", "partial") and codes:
            total_denied_claims += 1
            for code in codes:
                carc_freq[code] += 1
                carc_dollars[code] += denial_amt / len(codes)

    ranked = sorted(carc_freq.items(), key=lambda x: x[1], reverse=True)
    result: list[dict] = []
    for carc, count in ranked[:limit]:
        result.append({
            "carc": carc,
            "count": count,
            "total_denial_dollars": round(carc_dollars[carc], 2),
            "pct_of_denials": (
                round(count / total_denied_claims, 4)
                if total_denied_claims else 0.0
            ),
        })

    return result


# ── Payer aging ──────────────────────────────────────────────────────

def payer_aging(store: Any, deal_id: str) -> dict:
    """AR aging buckets by payer from claim service dates.

    Returns ``{payer: {current: float, 30_day: float, 60_day: float,
    90_day: float, 120_plus: float, total_outstanding: float}}``.

    Outstanding = total_charge - paid_amount for unpaid/partial claims.
    Aging is computed from the service_date relative to today.
    """
    _ensure_claim_table(store)

    with store.connect() as con:
        rows = con.execute(
            "SELECT * FROM claim_records WHERE deal_id = ?",
            (deal_id,),
        ).fetchall()

    today = datetime.now(timezone.utc).date()
    payer_buckets: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "current": 0.0,
            "30_day": 0.0,
            "60_day": 0.0,
            "90_day": 0.0,
            "120_plus": 0.0,
            "total_outstanding": 0.0,
        },
    )

    for row in rows:
        r = dict(row)
        status = r.get("claim_status", "")
        # Only unpaid or partially paid claims contribute to AR aging
        if status == "paid":
            continue

        payer = r.get("payer", "") or "Unknown"
        charge = float(r.get("total_charge", 0))
        paid = float(r.get("paid_amount", 0))
        outstanding = charge - paid
        if outstanding <= 0:
            continue

        service_date_str = r.get("service_date", "")
        if not service_date_str:
            # Can't compute aging without a service date; dump into 120+
            payer_buckets[payer]["120_plus"] += outstanding
            payer_buckets[payer]["total_outstanding"] += outstanding
            continue

        try:
            fmt = "%Y%m%d" if len(service_date_str) == 8 else "%Y-%m-%d"
            sd = datetime.strptime(service_date_str, fmt).date()
        except ValueError:
            payer_buckets[payer]["120_plus"] += outstanding
            payer_buckets[payer]["total_outstanding"] += outstanding
            continue

        age_days = (today - sd).days

        if age_days <= 30:
            payer_buckets[payer]["current"] += outstanding
        elif age_days <= 60:
            payer_buckets[payer]["30_day"] += outstanding
        elif age_days <= 90:
            payer_buckets[payer]["60_day"] += outstanding
        elif age_days <= 120:
            payer_buckets[payer]["90_day"] += outstanding
        else:
            payer_buckets[payer]["120_plus"] += outstanding

        payer_buckets[payer]["total_outstanding"] += outstanding

    # Round all values
    result: dict = {}
    for payer, buckets in payer_buckets.items():
        result[payer] = {k: round(v, 2) for k, v in buckets.items()}

    return result
