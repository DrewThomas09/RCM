"""Deal watchlist / starring (Brick 111).

An analyst actively tracking 5 deals out of 50 doesn't want to scroll
through the full portfolio every morning. A first-class "starred"
flag on each deal enables a quick /watchlist filter and a pinned
badge on /deal/<id>.

Design:

- Separate table ``deal_stars`` rather than a column on ``deals`` —
  keeps schema evolution cheap and lets us expand later to per-user
  stars without another migration.
- **Idempotent**: re-starring an already-starred deal is a no-op.
- **Stateless toggle API** (``toggle_star``) for single-click UX.

Public API::

    star_deal(store, deal_id) -> bool   # True if state changed
    unstar_deal(store, deal_id) -> bool
    toggle_star(store, deal_id) -> bool # new state
    is_starred(store, deal_id) -> bool
    list_starred(store) -> list[str]
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from ..portfolio.store import PortfolioStore


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_stars_table(store: PortfolioStore) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            # Report 0256 MR1057: add deal_id FK so the star is cleared
            # when the parent deal is deleted. New DBs only (CREATE
            # TABLE IF NOT EXISTS no-op on existing schemas).
            """CREATE TABLE IF NOT EXISTS deal_stars (
                deal_id TEXT PRIMARY KEY,
                starred_at TEXT NOT NULL,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
                    ON DELETE CASCADE
            )"""
        )
        con.commit()


def is_starred(store: PortfolioStore, deal_id: str) -> bool:
    _ensure_stars_table(store)
    with store.connect() as con:
        row = con.execute(
            "SELECT 1 FROM deal_stars WHERE deal_id = ?",
            (deal_id,),
        ).fetchone()
    return row is not None


def star_deal(store: PortfolioStore, deal_id: str) -> bool:
    """Mark ``deal_id`` starred. Returns True if state changed.

    B152 fix: upsert the deal row before inserting the star so we never
    leave a star pointing at a deal that has no row in ``deals``.
    """
    _ensure_stars_table(store)
    store.upsert_deal(deal_id)
    with store.connect() as con:
        cur = con.execute(
            "INSERT OR IGNORE INTO deal_stars (deal_id, starred_at) "
            "VALUES (?, ?)",
            (deal_id, _utcnow()),
        )
        con.commit()
        return cur.rowcount > 0


def unstar_deal(store: PortfolioStore, deal_id: str) -> bool:
    """Unstar ``deal_id``. Returns True if state changed."""
    _ensure_stars_table(store)
    with store.connect() as con:
        cur = con.execute(
            "DELETE FROM deal_stars WHERE deal_id = ?",
            (deal_id,),
        )
        con.commit()
        return cur.rowcount > 0


def toggle_star(store: PortfolioStore, deal_id: str) -> bool:
    """Flip the starred state atomically. Returns the new state.

    B146 fix: earlier read-modify-write racing two concurrent toggles
    could end up with both requests thinking they "turned off" a row
    that was actually reinserted. We now run the read + write inside a
    single IMMEDIATE transaction so SQLite serializes them.
    """
    _ensure_stars_table(store)
    store.upsert_deal(deal_id)  # B152: keep deal ref valid
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        try:
            row = con.execute(
                "SELECT 1 FROM deal_stars WHERE deal_id = ?",
                (deal_id,),
            ).fetchone()
            if row is None:
                con.execute(
                    "INSERT INTO deal_stars (deal_id, starred_at) "
                    "VALUES (?, ?)",
                    (deal_id, _utcnow()),
                )
                new_state = True
            else:
                con.execute(
                    "DELETE FROM deal_stars WHERE deal_id = ?",
                    (deal_id,),
                )
                new_state = False
            con.commit()
        except Exception:
            con.rollback()
            raise
    return new_state


def list_starred(store: PortfolioStore) -> List[str]:
    """All starred deal_ids, newest-first.

    B147 fix: secondary sort by deal_id so ties (two deals starred in
    the same second) are deterministic across runs.
    """
    _ensure_stars_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT deal_id FROM deal_stars "
            "ORDER BY starred_at DESC, deal_id ASC",
        ).fetchall()
    return [r["deal_id"] for r in rows]
