"""Saved peer sets — owner-scoped, named CCN baskets (P4's open half).

A peer set is a named list of provider CCNs a partner curates once and
reuses across modules: the screener compare view, the roll-up builder,
and any future peer-scoped analysis. The OBJECT is just the CCN list —
each consuming module re-resolves the CCNs against its own live
universe at render time, so a stale CCN degrades to that module's own
"not found" handling, never a fabricated row.

Additive, new-table only (``CREATE TABLE IF NOT EXISTS``). Mirrors the
saved_screens store pattern: parameterised SQL only, ``BEGIN
IMMEDIATE`` around check-then-write, owner-scoped reads and deletes.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from .store import PortfolioStore

#: CCNs are 6 alphanumerics (hospitals all-digit; some verticals carry
#: letters). The cap keeps a pathological paste from ballooning a row.
_CCN_RE = re.compile(r"^[A-Za-z0-9]{4,10}$")
_MAX_CCNS = 24


def _ensure_table(store: PortfolioStore) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS peer_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL,
                name TEXT NOT NULL,
                ccns TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        con.commit()


def _clean_ccns(raw: Any) -> List[str]:
    """Normalize a CCN list: split, trim, validate shape, de-dup
    (order-preserving), cap. Invalid tokens are DROPPED, not stored —
    a peer set must never carry markup or junk into consumers."""
    if isinstance(raw, str):
        parts = [p.strip() for p in raw.replace(";", ",").split(",")]
    else:
        parts = [str(p).strip() for p in (raw or [])]
    seen, out = set(), []
    for p in parts:
        if not p or not _CCN_RE.match(p) or p in seen:
            continue
        seen.add(p)
        out.append(p)
        if len(out) >= _MAX_CCNS:
            break
    return out


def save_peer_set(store: PortfolioStore, owner: str, name: str,
                  ccns: Any) -> int:
    """Persist a named peer set for ``owner``; returns the new row id.
    Requires a non-empty owner, name, and at least 2 valid CCNs (a
    one-provider "peer set" is not a peer set)."""
    owner = (owner or "").strip()
    name = (name or "").strip()[:120]
    clean = _clean_ccns(ccns)
    if not owner or not name:
        raise ValueError("peer set requires a non-empty owner and name")
    if len(clean) < 2:
        raise ValueError("peer set requires at least 2 valid CCNs")
    _ensure_table(store)
    now = datetime.now(timezone.utc).isoformat()
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            "INSERT INTO peer_sets (owner, name, ccns, created_at) "
            "VALUES (?, ?, ?, ?)",
            (owner, name, ",".join(clean), now),
        )
        con.commit()
        return int(cur.lastrowid)


def list_peer_sets(store: PortfolioStore, owner: str) -> List[Dict[str, Any]]:
    """All peer sets for ``owner``, newest first."""
    owner = (owner or "").strip()
    if not owner:
        return []
    _ensure_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT id, name, ccns, created_at FROM peer_sets "
            "WHERE owner = ? ORDER BY created_at DESC, id DESC",
            (owner,),
        ).fetchall()
    return [
        {"id": int(r[0]), "name": str(r[1]),
         "ccns": str(r[2]).split(","), "created_at": str(r[3])}
        for r in rows
    ]


def delete_peer_set(store: PortfolioStore, owner: str, set_id: int) -> bool:
    """Delete one of ``owner``'s peer sets; True when a row went away.
    Owner-scoped — one partner can never delete another's set."""
    owner = (owner or "").strip()
    if not owner:
        return False
    _ensure_table(store)
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            "DELETE FROM peer_sets WHERE id = ? AND owner = ?",
            (int(set_id), owner),
        )
        con.commit()
        return cur.rowcount > 0
