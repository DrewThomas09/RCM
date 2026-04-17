"""Multi-fund support.

PE firms manage multiple funds (Fund I, II, III) with different
vintages and sizes. Deals are assigned to funds via a many-to-many
``deal_fund_assignments`` join table rather than altering the
``deals`` table — this preserves backward compat and lets a deal
appear in multiple funds (co-invest, continuation vehicles).

Design:
- ``Fund`` is a lightweight dataclass with an ID, name, vintage
  year, and AUM/size.
- The ``funds`` table stores fund metadata.
- ``deal_fund_assignments`` is the join table; each row is
  ``(deal_id, fund_id)``.
- No FK to ``deals`` because the deals table is owned by
  ``portfolio/store.py`` and we don't want a circular dependency.
  We just store the deal_id string and let the caller validate.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Fund:
    """One PE fund."""
    fund_id: str
    fund_name: str
    vintage_year: int
    fund_size: float = 0.0


# ── Table setup ──────────────────────────────────────────────────────

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_tables(store: Any) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS funds (
                fund_id TEXT PRIMARY KEY,
                fund_name TEXT NOT NULL,
                vintage_year INTEGER NOT NULL,
                fund_size REAL NOT NULL DEFAULT 0.0,
                created_at TEXT NOT NULL
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS deal_fund_assignments (
                deal_id TEXT NOT NULL,
                fund_id TEXT NOT NULL,
                assigned_at TEXT NOT NULL,
                PRIMARY KEY (deal_id, fund_id),
                FOREIGN KEY (fund_id) REFERENCES funds(fund_id)
                    ON DELETE CASCADE
            )"""
        )
        con.commit()


# ── CRUD ─────────────────────────────────────────────────────────────

def create_fund(store: Any, fund: Fund) -> None:
    """Create a new fund. Raises ValueError if fund_id already exists."""
    _ensure_tables(store)
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        try:
            existing = con.execute(
                "SELECT fund_id FROM funds WHERE fund_id = ?",
                (fund.fund_id,),
            ).fetchone()
            if existing:
                raise ValueError(f"fund {fund.fund_id!r} already exists")
            con.execute(
                """INSERT INTO funds (fund_id, fund_name, vintage_year,
                   fund_size, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    fund.fund_id,
                    fund.fund_name,
                    int(fund.vintage_year),
                    float(fund.fund_size),
                    _utcnow_iso(),
                ),
            )
            con.commit()
        except ValueError:
            con.rollback()
            raise
        except Exception:
            con.rollback()
            raise


def list_funds(store: Any) -> List[Fund]:
    """Return all funds ordered by vintage year descending."""
    _ensure_tables(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT * FROM funds ORDER BY vintage_year DESC, fund_id"
        ).fetchall()
    return [
        Fund(
            fund_id=r["fund_id"],
            fund_name=r["fund_name"],
            vintage_year=int(r["vintage_year"]),
            fund_size=float(r["fund_size"]),
        )
        for r in rows
    ]


def assign_deal_to_fund(store: Any, deal_id: str, fund_id: str) -> None:
    """Assign a deal to a fund. Idempotent — re-assigning is a no-op."""
    _ensure_tables(store)
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        try:
            # Verify fund exists
            fund_row = con.execute(
                "SELECT fund_id FROM funds WHERE fund_id = ?",
                (fund_id,),
            ).fetchone()
            if not fund_row:
                raise ValueError(f"fund {fund_id!r} does not exist")
            con.execute(
                """INSERT OR IGNORE INTO deal_fund_assignments
                   (deal_id, fund_id, assigned_at)
                   VALUES (?, ?, ?)""",
                (deal_id, fund_id, _utcnow_iso()),
            )
            con.commit()
        except ValueError:
            con.rollback()
            raise
        except Exception:
            con.rollback()
            raise


def deals_for_fund(store: Any, fund_id: str) -> List[str]:
    """Return all deal_ids assigned to a fund."""
    _ensure_tables(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT deal_id FROM deal_fund_assignments WHERE fund_id = ? ORDER BY deal_id",
            (fund_id,),
        ).fetchall()
    return [r["deal_id"] for r in rows]


def funds_for_deal(store: Any, deal_id: str) -> List[Fund]:
    """Return all funds a deal is assigned to."""
    _ensure_tables(store)
    with store.connect() as con:
        rows = con.execute(
            """SELECT f.* FROM funds f
               JOIN deal_fund_assignments a ON f.fund_id = a.fund_id
               WHERE a.deal_id = ?
               ORDER BY f.vintage_year DESC""",
            (deal_id,),
        ).fetchall()
    return [
        Fund(
            fund_id=r["fund_id"],
            fund_name=r["fund_name"],
            vintage_year=int(r["vintage_year"]),
            fund_size=float(r["fund_size"]),
        )
        for r in rows
    ]
