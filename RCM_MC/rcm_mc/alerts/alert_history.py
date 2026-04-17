"""Alert history + first-seen tracking (Brick 104).

Evaluators (Brick 101) are stateless — they compute the current alert
set from snapshots on every page load. That means partners can't
answer: "how long has this covenant been red?" or "which alerts have
been live > 30 days, signalling escalation?"

This module adds a lightweight upsert log: every time an evaluator
emits an Alert, we record (or update) a row in ``alert_history`` keyed
on ``(kind, deal_id, trigger_key)``. First sighting sets
``first_seen_at``; subsequent sightings bump ``last_seen_at`` and
``sightings_count``. Acked alerts still get logged — history is
audit-grade, not UI-filtered.

Public API::

    record_sightings(store, alerts) -> None
    get_first_seen(store, kind, deal_id, trigger_key) -> str | None
    list_history(store) -> pd.DataFrame
    days_red(store, min_days=30) -> pd.DataFrame   # escalation view
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, Optional

import pandas as pd

from ..portfolio.store import PortfolioStore


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_table(store: PortfolioStore) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS alert_history (
                kind TEXT NOT NULL,
                deal_id TEXT NOT NULL,
                trigger_key TEXT NOT NULL,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                detail TEXT NOT NULL,
                sightings_count INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (kind, deal_id, trigger_key)
            )"""
        )
        con.commit()


def record_sightings(store: PortfolioStore, alerts: Iterable) -> None:
    """Upsert one row per alert. First sighting sets first_seen_at.

    B152 fix: upsert the deal row for each alert's ``deal_id`` before
    writing, so every history row references a real deal.
    """
    _ensure_table(store)
    from .alert_acks import trigger_key_for
    now = _utcnow_iso()
    alerts_list = list(alerts)
    # Ensure every referenced deal exists
    for a in alerts_list:
        try:
            store.upsert_deal(a.deal_id)
        except Exception:  # noqa: BLE001 — never block history
            pass
    with store.connect() as con:
        for a in alerts_list:
            tk = trigger_key_for(a)
            con.execute(
                """INSERT INTO alert_history
                   (kind, deal_id, trigger_key, first_seen_at, last_seen_at,
                    severity, title, detail, sightings_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                   ON CONFLICT(kind, deal_id, trigger_key) DO UPDATE SET
                     last_seen_at = excluded.last_seen_at,
                     severity = excluded.severity,
                     title = excluded.title,
                     detail = excluded.detail,
                     sightings_count = alert_history.sightings_count + 1""",
                (a.kind, a.deal_id, tk, now, now,
                 a.severity, a.title, a.detail),
            )
        con.commit()


def get_first_seen(
    store: PortfolioStore, *, kind: str, deal_id: str, trigger_key: str,
) -> Optional[str]:
    _ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            "SELECT first_seen_at FROM alert_history "
            "WHERE kind = ? AND deal_id = ? AND trigger_key = ?",
            (kind, deal_id, trigger_key),
        )
        row = cur.fetchone()
    return row["first_seen_at"] if row else None


def list_history(store: PortfolioStore) -> pd.DataFrame:
    _ensure_table(store)
    with store.connect() as con:
        return pd.read_sql_query(
            "SELECT kind, deal_id, trigger_key, first_seen_at, last_seen_at, "
            "severity, title, detail, sightings_count "
            "FROM alert_history ORDER BY first_seen_at DESC",
            con,
        )


def days_red(store: PortfolioStore, min_days: int = 30) -> pd.DataFrame:
    """Escalation view: red alerts with ``first_seen_at`` older than N days.

    Returns columns: kind, deal_id, trigger_key, first_seen_at,
    last_seen_at, title, days_open.
    """
    df = list_history(store)
    if df.empty:
        return df
    red = df[df["severity"] == "red"].copy()
    if red.empty:
        return red.assign(days_open=0)
    now = datetime.now(timezone.utc)
    def _age(ts):
        try:
            return (now - datetime.fromisoformat(ts)).days
        except (TypeError, ValueError):
            return 0
    red["days_open"] = red["first_seen_at"].apply(_age)
    red = red[red["days_open"] >= int(min_days)]
    return red.sort_values("days_open", ascending=False).reset_index(drop=True)


def age_hint(first_seen_at: Optional[str], *, now: Optional[datetime] = None) -> str:
    """'3d ago' / '2h ago' / '12m ago' / '' for non-parseable inputs."""
    if not first_seen_at:
        return ""
    try:
        ts = datetime.fromisoformat(first_seen_at)
    except (TypeError, ValueError):
        return ""
    now = now or datetime.now(timezone.utc)
    delta = now - ts
    secs = delta.total_seconds()
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)}m ago"
    if secs < 86400:
        return f"{int(secs // 3600)}h ago"
    return f"{delta.days}d ago"
