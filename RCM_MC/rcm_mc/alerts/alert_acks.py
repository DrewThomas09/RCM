"""Alert acknowledgement + snooze (Brick 102).

Hardcoded evaluators (Brick 101) re-fire on every /alerts page view. Left
alone that breaks the Monday-morning partner workflow: after triage, the
same RED covenant alert keeps shouting for attention until the underlying
state changes. Analysts need a way to say "seen, hide" without mutating
the deal itself.

Design:

- **Ack is per-trigger-instance, not per-deal.** An ack records
  ``(kind, deal_id, trigger_key)`` where ``trigger_key`` is the Alert's
  ``triggered_at`` (snapshot timestamp, quarter, etc.). When the
  underlying state changes, the trigger_key changes, and the ack no
  longer matches → alert reappears. That's the desired behavior:
  silencing a stale alert is fine; silencing the category forever is not.
- **Snooze = optional expiry.** ``snooze_days=0`` acks permanently for
  this instance; ``snooze_days=N`` silences for N days then unmutes.
- **Append-only audit trail.** We never delete acks — unacking inserts a
  new "revoked" row. Partners asking "who silenced this on Tuesday" get
  a straight answer.

Public API::

    ack_alert(store, kind, deal_id, trigger_key, snooze_days=0, note="", acked_by="")
    is_acked(store, kind, deal_id, trigger_key, now=None) -> bool
    list_acks(store) -> pd.DataFrame
    trigger_key_for(alert) -> str
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd

from ..portfolio.store import PortfolioStore


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _ensure_table(store: PortfolioStore) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS alert_acks (
                ack_id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                deal_id TEXT NOT NULL,
                trigger_key TEXT NOT NULL,
                acked_at TEXT NOT NULL,
                acked_by TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                snooze_until TEXT
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_alert_acks_lookup "
            "ON alert_acks(kind, deal_id, trigger_key)"
        )
        con.commit()


def trigger_key_for(alert) -> str:
    """Stable string key for an Alert instance. Used to dedupe acks.

    B160 fix: strip whitespace from each component so a hand-crafted
    ack with trailing space in ``trigger_key`` still matches the
    canonical evaluator-generated key. Previously two acks with
    visually-identical keys but whitespace differences would both be
    stored and only one would silence the alert.
    """
    kind = (alert.kind or "").strip()
    deal_id = (alert.deal_id or "").strip()
    trig = (alert.triggered_at or "").strip()
    return f"{kind}|{deal_id}|{trig}"


def ack_alert(
    store: PortfolioStore,
    *,
    kind: str,
    deal_id: str,
    trigger_key: str,
    snooze_days: int = 0,
    note: str = "",
    acked_by: str = "",
) -> int:
    """Record an ack. Returns the new ack_id."""
    _ensure_table(store)
    now = _utcnow()
    snooze_until: Optional[str] = None
    if snooze_days and int(snooze_days) > 0:
        snooze_until = _iso(now + timedelta(days=int(snooze_days)))
    with store.connect() as con:
        cur = con.execute(
            "INSERT INTO alert_acks "
            "(kind, deal_id, trigger_key, acked_at, acked_by, note, snooze_until) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (kind, deal_id, trigger_key, _iso(now),
             acked_by or "", note or "", snooze_until),
        )
        con.commit()
        return int(cur.lastrowid)


def is_acked(
    store: PortfolioStore,
    *,
    kind: str,
    deal_id: str,
    trigger_key: str,
    now: Optional[datetime] = None,
) -> bool:
    """True if an unexpired ack covers this trigger instance."""
    _ensure_table(store)
    now = now or _utcnow()
    with store.connect() as con:
        cur = con.execute(
            "SELECT snooze_until FROM alert_acks "
            "WHERE kind = ? AND deal_id = ? AND trigger_key = ? "
            "ORDER BY ack_id DESC LIMIT 1",
            (kind, deal_id, trigger_key),
        )
        row = cur.fetchone()
    if row is None:
        return False
    snooze_until = row["snooze_until"]
    if not snooze_until:
        return True  # permanent ack
    try:
        expires = datetime.fromisoformat(snooze_until)
    except (TypeError, ValueError):
        return True
    return now < expires


def was_snoozed(
    store: PortfolioStore,
    *,
    kind: str,
    deal_id: str,
    trigger_key: str,
    now: Optional[datetime] = None,
) -> bool:
    """Did this alert instance get snoozed, and has that snooze expired?

    Used to flag "returning after snooze" alerts (B145). Distinct from
    :func:`is_acked` — we want ``True`` only when there *was* a snooze
    and it has *elapsed*. A permanent ack (snooze_until NULL) returns
    False regardless of time; a never-acked instance returns False.
    """
    _ensure_table(store)
    now = now or _utcnow()
    with store.connect() as con:
        cur = con.execute(
            "SELECT snooze_until FROM alert_acks "
            "WHERE kind = ? AND deal_id = ? AND trigger_key = ? "
            "ORDER BY ack_id DESC LIMIT 1",
            (kind, deal_id, trigger_key),
        )
        row = cur.fetchone()
    if row is None:
        return False
    snooze_until = row["snooze_until"]
    if not snooze_until:
        return False  # permanent ack — not a snooze
    try:
        expires = datetime.fromisoformat(snooze_until)
    except (TypeError, ValueError):
        return False
    return now >= expires


def list_acks(store: PortfolioStore) -> pd.DataFrame:
    """All acks newest-first (audit view)."""
    _ensure_table(store)
    with store.connect() as con:
        return pd.read_sql_query(
            "SELECT ack_id, kind, deal_id, trigger_key, acked_at, "
            "acked_by, note, snooze_until FROM alert_acks "
            "ORDER BY ack_id DESC",
            con,
        )
