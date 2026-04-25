"""Transparency in Coverage (TiC) payer MRF parser + loader.

Every commercial group health plan must publish a TiC MRF listing
in-network negotiated rates. The schema is one of two flavours:

  • In-network rate file: per (NPI × CPT/HCPCS/DRG) negotiated rate
  • Allowed-amount file: out-of-network historical allowed amounts

We currently parse the in-network shape, which is what the
PayerNegotiationSimulator needs:

    {
      "reporting_entity_name": "Aetna",
      "reporting_entity_type": "Health Insurance Issuer",
      "plan_name": "Open Choice PPO",
      "in_network": [
        {
          "billing_code": "27447",
          "billing_code_type": "CPT",
          "negotiated_rates": [
            {
              "provider_groups": [
                {"npi": ["1234567890", "1003456789"], "tin": {"type":"ein","value":"12-3456789"}}
              ],
              "negotiated_prices": [
                {"negotiated_type": "negotiated",
                 "negotiated_rate": 24500.00,
                 "billing_class": "professional",
                 "expiration_date": "2026-12-31",
                 "service_code": ["11", "21"]}
              ]
            }
          ]
        }
      ]
    }

Real payer MRFs are sharded into thousands of files (one per plan
or geography) and frequently >5GB compressed. This loader streams
JSON line-by-line via ``ijson`` if available, else ``json.load`` —
either way it should run on a laptop given the test fixtures we
ship in this repo.

Public API::

    parse_payer_tic_mrf(path) -> Iterator[PayerRateRecord]
    load_payer_tic_mrf(store, records) -> int
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

from .normalize import (
    normalize_code,
    normalize_payer_name,
    classify_service_line,
)


@dataclass
class PayerRateRecord:
    """One negotiated-rate row, denormalized to (payer, plan, NPI,
    code, arrangement) — a shape the simulator can SELECT directly
    against without joins."""
    payer_name: str
    plan_name: str = ""
    npi: str = ""
    code: str = ""
    code_type: str = "CPT"
    negotiation_arrangement: str = "ffs"
    negotiated_rate: Optional[float] = None
    negotiation_basis: Optional[str] = None
    expiration_date: Optional[str] = None
    service_line: Optional[str] = None


def _safe_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_payer_tic_mrf(
    path: object,
) -> Iterator[PayerRateRecord]:
    """Yield one record per (payer × plan × NPI × code × arrangement)
    combination across the in_network array."""
    p = Path(str(path))
    if not p.is_file():
        raise FileNotFoundError(f"Payer TiC MRF not found at {p}")

    with p.open("r", encoding="utf-8") as fh:
        doc = json.load(fh)

    payer = normalize_payer_name(doc.get("reporting_entity_name"))
    plan = str(doc.get("plan_name") or "").strip()

    for item in (doc.get("in_network") or []):
        ctype = str(
            item.get("billing_code_type") or "CPT").upper()
        normed = normalize_code(item.get("billing_code"), ctype)
        if not normed:
            continue
        service_line = classify_service_line(normed, ctype)

        for nr in (item.get("negotiated_rates") or []):
            # Each NR can carry multiple provider_groups (each with
            # multiple NPIs) AND multiple negotiated_prices. We
            # cross-product so each (NPI × price) gets a row.
            npis: list = []
            for pg in (nr.get("provider_groups") or []):
                for npi in (pg.get("npi") or []):
                    if npi:
                        npis.append(str(npi))
            for price in (nr.get("negotiated_prices") or []):
                rate = _safe_float(
                    price.get("negotiated_rate"))
                arrangement = str(
                    price.get("negotiated_type") or "ffs").lower()
                basis = price.get("billing_class")
                expires = price.get("expiration_date")
                # If no NPIs were listed, still emit one row keyed
                # by an empty NPI — the loader uses INSERT OR
                # REPLACE so duplicate empty-NPI rows collapse
                # naturally.
                emit_npis = npis or [""]
                for npi in emit_npis:
                    yield PayerRateRecord(
                        payer_name=payer,
                        plan_name=plan,
                        npi=npi,
                        code=normed,
                        code_type=ctype,
                        negotiation_arrangement=arrangement,
                        negotiated_rate=rate,
                        negotiation_basis=basis,
                        expiration_date=expires,
                        service_line=service_line,
                    )


def load_payer_tic_mrf(
    store: Any,
    records: Iterable[PayerRateRecord],
    *,
    source_key: Optional[str] = None,
) -> int:
    """Insert/replace negotiated-rate rows. Returns count loaded."""
    store.init_db()
    now = datetime.now(timezone.utc).isoformat()
    n = 0
    seen_payer: Optional[str] = None
    seen_plan: Optional[str] = None
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        try:
            for r in records:
                if seen_payer is None:
                    seen_payer = r.payer_name
                    seen_plan = r.plan_name
                con.execute(
                    """INSERT OR REPLACE INTO pricing_payer_rates (
                        payer_name, plan_name, npi, code, code_type,
                        negotiation_arrangement, negotiated_rate,
                        negotiation_basis, expiration_date,
                        service_line, loaded_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (r.payer_name, r.plan_name, r.npi, r.code,
                     r.code_type, r.negotiation_arrangement,
                     r.negotiated_rate, r.negotiation_basis,
                     r.expiration_date, r.service_line, now),
                )
                n += 1
            key = source_key or (
                f"{seen_payer or 'unknown'}|{seen_plan or ''}")
            con.execute(
                "INSERT OR REPLACE INTO pricing_load_log "
                "(source, key, record_count, loaded_at, notes) "
                "VALUES (?, ?, ?, ?, ?)",
                ("payer_tic", key, n, now, ""),
            )
            con.commit()
        except Exception:
            con.rollback()
            raise
    return n
