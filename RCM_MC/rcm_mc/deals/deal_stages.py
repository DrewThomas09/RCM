"""Deal stage tracking + stage-change events for automation.

Tracks the lifecycle stage of each deal: pipeline → diligence →
ic → hold → exit. Stage changes are recorded in ``deal_stage_history``
and fire events via the automation engine (Prompt 63) so rules like
"when deal moves to IC, generate package" can execute.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


VALID_STAGES = ("pipeline", "diligence", "ic", "hold", "exit", "closed")

_ALLOWED_TRANSITIONS: Dict[str, tuple] = {
    "pipeline":   ("diligence", "closed"),
    "diligence":  ("ic", "pipeline", "closed"),
    "ic":         ("hold", "diligence", "closed"),
    "hold":       ("exit", "ic", "closed"),
    "exit":       ("closed",),
    "closed":     (),
}


def validate_transition(from_stage: Optional[str], to_stage: str) -> Optional[str]:
    """Return an error message if the transition is invalid, or None if OK.

    First stage (from_stage=None) is always allowed.
    """
    if from_stage is None:
        return None
    if from_stage == to_stage:
        return None
    allowed = _ALLOWED_TRANSITIONS.get(from_stage, ())
    if to_stage not in allowed:
        return (
            f"cannot transition from {from_stage!r} to {to_stage!r}; "
            f"allowed: {allowed}"
        )
    return None


def _ensure_table(store: Any) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS deal_stage_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                changed_by TEXT,
                notes TEXT,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id) ON DELETE CASCADE
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_deal_stages "
            "ON deal_stage_history(deal_id, changed_at)"
        )
        con.commit()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def set_stage(
    store: Any, deal_id: str, stage: str,
    *, changed_by: str = "system", notes: str = "",
) -> int:
    """Record a stage transition. Returns the row ID.

    Also fires a ``stage_change`` event through the automation engine
    when it's available.
    """
    if stage not in VALID_STAGES:
        raise ValueError(f"invalid stage {stage!r}; valid: {VALID_STAGES}")
    _ensure_table(store)
    cur_stg = current_stage(store, deal_id)
    err = validate_transition(cur_stg, stage)
    if err:
        raise ValueError(err)
    with store.connect() as con:
        cur = con.execute(
            "INSERT INTO deal_stage_history "
            "(deal_id, stage, changed_at, changed_by, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (deal_id, stage, _utcnow(), changed_by, notes),
        )
        con.commit()
        row_id = int(cur.lastrowid)

    # Fire automation event (best-effort).
    try:
        from ..infra.automation_engine import evaluate_rules
        evaluate_rules(
            store, "stage_change",
            {"deal_id": deal_id, "stage": stage, "changed_by": changed_by},
        )
    except Exception:  # noqa: BLE001
        pass

    return row_id


def current_stage(store: Any, deal_id: str) -> Optional[str]:
    """Return the most recent stage for a deal, or None."""
    _ensure_table(store)
    with store.connect() as con:
        row = con.execute(
            "SELECT stage FROM deal_stage_history "
            "WHERE deal_id = ? ORDER BY changed_at DESC LIMIT 1",
            (deal_id,),
        ).fetchone()
    return row["stage"] if row else None


def stage_history(store: Any, deal_id: str) -> List[Dict[str, Any]]:
    """Return the full stage history for a deal, newest first."""
    _ensure_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT * FROM deal_stage_history "
            "WHERE deal_id = ? ORDER BY changed_at DESC",
            (deal_id,),
        ).fetchall()
    return [dict(r) for r in rows]
