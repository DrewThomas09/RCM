"""Hash-chain audit-log integrity.

Extends ``rcm_mc.auth.audit_log`` with a cryptographic chain so any
after-the-fact deletion, re-ordering, or mutation of audit events is
detectable. The chain links each event to its predecessor by
SHA-256, matching the pattern every HIPAA / SOC 2 auditor expects
from an immutable audit trail.

Why this is a separate module, not an edit to ``audit_log.py``:

    - The audit_log API is load-bearing across 50+ call sites; we
      don't want to risk breaking existing log_event calls.
    - Compliance capabilities (chain, scanner, readiness docs) form
      a coherent subpackage with its own test scope.
    - New rows can be hashed forward without requiring a backfill,
      so pre-chain rows get ``prev_hash = NULL`` and chain
      verification starts at the first rowid with a hash.

Trust model: the hash chain catches mutation detectable *from within
the database* — an attacker with write access to the SQLite file
can still rewrite history if they also recompute every downstream
hash. The proper mitigation (off-site hash anchor, WORM storage,
periodic export to write-once media) is documented in
``HIPAA_READINESS.md``; this module is the detective control.

Public API:

    append_chained_event(store, *, actor, action, target, detail=None,
                         request_id=None) -> (event_id, row_hash)
    verify_audit_chain(store, *, since_id=None) -> AuditChainReport
    chain_status(store) -> dict
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..portfolio.store import PortfolioStore


# ── Column migration ───────────────────────────────────────────────

def _ensure_chain_columns(store: PortfolioStore) -> None:
    """Add ``prev_hash`` + ``row_hash`` to ``audit_events`` if they
    do not yet exist. Idempotent."""
    store.init_db()
    with store.connect() as con:
        # Ensure base audit_events table exists (delegates to the
        # existing auth.audit_log module's definition).
        from ..auth.audit_log import _ensure_table  # noqa: PLC0415
        _ensure_table(store)
        cols = {
            r["name"] for r in con.execute(
                "PRAGMA table_info(audit_events)"
            ).fetchall()
        }
        if "prev_hash" not in cols:
            con.execute(
                "ALTER TABLE audit_events ADD COLUMN prev_hash TEXT"
            )
        if "row_hash" not in cols:
            con.execute(
                "ALTER TABLE audit_events ADD COLUMN row_hash TEXT"
            )
        con.commit()


# ── Canonical row payload → hash ───────────────────────────────────

def _canonical_payload(
    *,
    event_id: int,
    at: str,
    actor: str,
    action: str,
    target: str,
    detail_json: str,
    request_id: Optional[str],
    prev_hash: Optional[str],
) -> bytes:
    """Canonical serialisation of a row. The ``event_id`` is included
    so re-ordering by row-count is still detected (two rows with the
    same content but swapped ids produce different hashes)."""
    return json.dumps(
        {
            "id": int(event_id),
            "at": str(at),
            "actor": str(actor),
            "action": str(action),
            "target": str(target),
            "detail_json": str(detail_json),
            "request_id": request_id if request_id is None else str(request_id),
            "prev_hash": prev_hash,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


# ── Public API ─────────────────────────────────────────────────────

def append_chained_event(
    store: PortfolioStore,
    *,
    actor: str,
    action: str,
    target: str = "",
    detail: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> Tuple[int, str]:
    """Append an audit event AND link it into the hash chain.

    Atomic: the insert + hash-back-fill happens inside one BEGIN
    IMMEDIATE transaction so concurrent writers cannot interleave and
    break the chain.

    Returns ``(event_id, row_hash)``.
    """
    _ensure_chain_columns(store)
    at = datetime.now(timezone.utc).isoformat()
    detail_json = json.dumps(detail or {}, default=str)

    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        # 1. Insert the event WITHOUT the hash columns (we do not yet
        #    know the event_id; the canonical payload includes id).
        cur = con.execute(
            "INSERT INTO audit_events "
            "(at, actor, action, target, detail_json, request_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (at, str(actor or "system"), str(action),
             str(target or ""), detail_json, request_id),
        )
        event_id = int(cur.lastrowid)

        # 2. Look up the most recent prior row's hash (by id).
        row = con.execute(
            "SELECT row_hash FROM audit_events "
            "WHERE id < ? AND row_hash IS NOT NULL "
            "ORDER BY id DESC LIMIT 1",
            (event_id,),
        ).fetchone()
        prev_hash = row["row_hash"] if row else None

        # 3. Compute this row's hash and write it back.
        payload = _canonical_payload(
            event_id=event_id, at=at, actor=str(actor or "system"),
            action=str(action), target=str(target or ""),
            detail_json=detail_json, request_id=request_id,
            prev_hash=prev_hash,
        )
        row_hash = _hash(payload)
        con.execute(
            "UPDATE audit_events SET prev_hash = ?, row_hash = ? "
            "WHERE id = ?",
            (prev_hash, row_hash, event_id),
        )
        con.commit()
        return event_id, row_hash


@dataclass
class AuditChainReport:
    """Result of one chain verification. ``ok`` is True iff every
    hashed row re-hashes cleanly and no gap / reorder is detected."""
    ok: bool
    total_rows: int
    hashed_rows: int
    first_hashed_id: Optional[int] = None
    last_hashed_id: Optional[int] = None
    mismatches: List[Dict[str, Any]] = field(default_factory=list)
    missing_prev: List[int] = field(default_factory=list)
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "total_rows": self.total_rows,
            "hashed_rows": self.hashed_rows,
            "first_hashed_id": self.first_hashed_id,
            "last_hashed_id": self.last_hashed_id,
            "mismatches": list(self.mismatches),
            "missing_prev": list(self.missing_prev),
            "reason": self.reason,
        }


def verify_audit_chain(
    store: PortfolioStore,
    *,
    since_id: Optional[int] = None,
) -> AuditChainReport:
    """Walk the hashed-row range and verify each row's hash.

    Two failure modes are caught:
      (a) A row's recomputed hash does not match its stored
          ``row_hash`` — the row was mutated (or its predecessor
          was, then hashes were partially regenerated).
      (b) A row's stored ``prev_hash`` does not match the prior row's
          ``row_hash`` — a row was deleted or re-ordered.

    Pre-chain rows (no row_hash) are counted but not verified. A
    production deployment runs one chained event on boot to set the
    chain start, then every subsequent write uses
    :func:`append_chained_event`.
    """
    _ensure_chain_columns(store)
    with store.connect() as con:
        total = con.execute(
            "SELECT COUNT(*) AS n FROM audit_events"
        ).fetchone()["n"]

        where = "WHERE row_hash IS NOT NULL"
        params: List[Any] = []
        if since_id is not None:
            where += " AND id >= ?"
            params.append(int(since_id))
        rows = con.execute(
            f"SELECT id, at, actor, action, target, detail_json, "
            f"       request_id, prev_hash, row_hash "
            f"FROM audit_events {where} ORDER BY id ASC",
            params,
        ).fetchall()

    if not rows:
        return AuditChainReport(
            ok=True, total_rows=total, hashed_rows=0,
            reason="no hashed rows yet",
        )

    mismatches: List[Dict[str, Any]] = []
    missing_prev: List[int] = []
    prev_row_hash: Optional[str] = None
    first_id: Optional[int] = None
    last_id: Optional[int] = None

    for i, r in enumerate(rows):
        rid = int(r["id"])
        if first_id is None:
            first_id = rid
        last_id = rid

        # Link check: this row's stored prev_hash must match the
        # previous hashed row's row_hash. On the first iteration:
        #   - If since_id was supplied, the caller is checking a
        #     slice and we cannot verify the pre-slice predecessor
        #     (trust the stored prev_hash as the boundary).
        #   - Otherwise, the first iteration is the genesis row and
        #     its prev_hash MUST be None. A non-null prev_hash here
        #     means a predecessor was deleted or its row_hash was
        #     nulled (tamper signal).
        if i == 0:
            if since_id is None and r["prev_hash"] is not None:
                missing_prev.append(rid)
        else:
            if r["prev_hash"] != prev_row_hash:
                missing_prev.append(rid)

        # Recompute hash and compare.
        payload = _canonical_payload(
            event_id=rid, at=r["at"], actor=r["actor"],
            action=r["action"], target=r["target"],
            detail_json=r["detail_json"],
            request_id=r["request_id"], prev_hash=r["prev_hash"],
        )
        recomputed = _hash(payload)
        if recomputed != r["row_hash"]:
            mismatches.append({
                "id": rid,
                "stored": r["row_hash"],
                "recomputed": recomputed,
            })
        prev_row_hash = r["row_hash"]

    ok = not mismatches and not missing_prev
    return AuditChainReport(
        ok=ok, total_rows=total, hashed_rows=len(rows),
        first_hashed_id=first_id, last_hashed_id=last_id,
        mismatches=mismatches, missing_prev=missing_prev,
    )


def chain_status(store: PortfolioStore) -> Dict[str, Any]:
    """Lightweight status summary — hashed vs pre-chain row counts
    and last row hash. Cheap; safe to render in a /admin UI."""
    _ensure_chain_columns(store)
    with store.connect() as con:
        total = con.execute(
            "SELECT COUNT(*) AS n FROM audit_events"
        ).fetchone()["n"]
        hashed = con.execute(
            "SELECT COUNT(*) AS n FROM audit_events WHERE row_hash IS NOT NULL"
        ).fetchone()["n"]
        last = con.execute(
            "SELECT id, row_hash FROM audit_events "
            "WHERE row_hash IS NOT NULL ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return {
        "total_rows": int(total),
        "hashed_rows": int(hashed),
        "pre_chain_rows": int(total - hashed),
        "last_hashed_id": int(last["id"]) if last else None,
        "last_row_hash": last["row_hash"] if last else None,
    }
