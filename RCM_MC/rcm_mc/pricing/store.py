"""SQLite store for the pricing-transparency foundation.

Shared by every parser/loader in this package. Schema is shaped
around the *consumer* needs of the PayerNegotiationSimulator and
the other downstream packets — denormalized enough that a single
SELECT + WHERE serves the common query patterns:

  • "What's the negotiated rate for CPT 27447 with BCBS-TX in NPI 1234?"
  • "What hospitals report a gross charge for DRG 470 in CBSA 19100?"
  • "Which payers negotiate with NPI 1234?"

We deliberately do NOT normalize into a 5-table star schema — the
read patterns are point-lookups + filtered scans, not analytic
joins. Indexes carry the weight.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class PricingStore:
    """Connection helper around a SQLite file holding the pricing
    foundation tables. Idempotent migrations on every ``init_db()``
    so loaders can call it freely."""

    def __init__(self, db_path: str) -> None:
        self.db_path = str(db_path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA busy_timeout = 5000")
        con.execute("PRAGMA foreign_keys = ON")
        try:
            yield con
        finally:
            con.close()

    def init_db(self) -> None:
        """Create / migrate the four foundation tables."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            # ── NPPES Type-2 organizational NPIs ────────────────
            con.execute("""
                CREATE TABLE IF NOT EXISTS pricing_nppes (
                    npi TEXT PRIMARY KEY,
                    entity_type INTEGER NOT NULL,
                    organization_name TEXT,
                    last_name TEXT,
                    first_name TEXT,
                    taxonomy_code TEXT,
                    taxonomy_label TEXT,
                    address_line TEXT,
                    city TEXT,
                    state TEXT,
                    zip5 TEXT,
                    cbsa TEXT,
                    nppes_last_updated TEXT,
                    loaded_at TEXT NOT NULL
                )
            """)
            con.execute(
                "CREATE INDEX IF NOT EXISTS "
                "idx_pricing_nppes_state ON pricing_nppes(state)"
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS "
                "idx_pricing_nppes_cbsa ON pricing_nppes(cbsa)"
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS "
                "idx_pricing_nppes_taxonomy "
                "ON pricing_nppes(taxonomy_code)"
            )

            # ── Hospital MRF charges ────────────────────────────
            # PK: (ccn, code, payer_name, plan_name) — a hospital may
            # publish a different rate per payer plan. Cash-price
            # rows store NULL for payer/plan.
            con.execute("""
                CREATE TABLE IF NOT EXISTS pricing_hospital_charges (
                    ccn TEXT NOT NULL,
                    npi TEXT,
                    code TEXT NOT NULL,
                    code_type TEXT NOT NULL,
                    description TEXT,
                    setting TEXT,
                    gross_charge REAL,
                    discounted_cash_price REAL,
                    payer_specific_charge REAL,
                    payer_name TEXT NOT NULL DEFAULT '',
                    plan_name TEXT NOT NULL DEFAULT '',
                    deidentified_min REAL,
                    deidentified_max REAL,
                    loaded_at TEXT NOT NULL,
                    PRIMARY KEY (ccn, code, payer_name, plan_name, setting)
                )
            """)
            con.execute(
                "CREATE INDEX IF NOT EXISTS "
                "idx_pricing_hospital_code "
                "ON pricing_hospital_charges(code)"
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS "
                "idx_pricing_hospital_npi "
                "ON pricing_hospital_charges(npi)"
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS "
                "idx_pricing_hospital_payer "
                "ON pricing_hospital_charges(payer_name)"
            )

            # ── Payer TiC negotiated rates ──────────────────────
            con.execute("""
                CREATE TABLE IF NOT EXISTS pricing_payer_rates (
                    payer_name TEXT NOT NULL,
                    plan_name TEXT NOT NULL DEFAULT '',
                    npi TEXT NOT NULL,
                    code TEXT NOT NULL,
                    code_type TEXT NOT NULL,
                    negotiation_arrangement TEXT NOT NULL DEFAULT 'ffs',
                    negotiated_rate REAL,
                    negotiation_basis TEXT,
                    expiration_date TEXT,
                    service_line TEXT,
                    loaded_at TEXT NOT NULL,
                    PRIMARY KEY (
                        payer_name, plan_name, npi, code,
                        negotiation_arrangement
                    )
                )
            """)
            con.execute(
                "CREATE INDEX IF NOT EXISTS "
                "idx_pricing_payer_rates_npi "
                "ON pricing_payer_rates(npi)"
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS "
                "idx_pricing_payer_rates_code "
                "ON pricing_payer_rates(code)"
            )
            con.execute(
                "CREATE INDEX IF NOT EXISTS "
                "idx_pricing_payer_rates_service_line "
                "ON pricing_payer_rates(service_line)"
            )

            # ── Loader status (one row per (source, key)) ───────
            # Source = 'nppes' | 'hospital_mrf' | 'payer_tic'
            con.execute("""
                CREATE TABLE IF NOT EXISTS pricing_load_log (
                    source TEXT NOT NULL,
                    key TEXT NOT NULL,
                    record_count INTEGER NOT NULL,
                    loaded_at TEXT NOT NULL,
                    notes TEXT,
                    PRIMARY KEY (source, key)
                )
            """)
            con.commit()
