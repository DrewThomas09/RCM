"""Webhooks: HMAC-signed event dispatch (Prompt 39).

Events (``deal.created``, ``analysis.completed``, ``risk.critical``)
fire from the server via :func:`dispatch_event`. Each configured
webhook URL receives a POST with a JSON body + an ``X-RCM-Signature``
header (HMAC-SHA256 of the body keyed on the webhook's secret).
Three retries with exponential backoff on failure.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import threading
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Schema ─────────────────────────────────────────────────────────

def _ensure_tables(store: Any) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS webhooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                secret TEXT NOT NULL,
                events TEXT NOT NULL,          -- comma-separated
                active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                description TEXT
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS webhook_deliveries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                webhook_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status_code INTEGER,
                attempts INTEGER DEFAULT 0,
                delivered_at TEXT,
                error TEXT
            )"""
        )
        con.commit()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── CRUD ───────────────────────────────────────────────────────────

def register_webhook(
    store: Any, url: str, secret: str,
    events: List[str], *, description: str = "",
) -> int:
    _ensure_tables(store)
    with store.connect() as con:
        cur = con.execute(
            "INSERT INTO webhooks (url, secret, events, created_at, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (url, secret, ",".join(events), _utcnow(), description),
        )
        con.commit()
        return int(cur.lastrowid)


def list_webhooks(store: Any) -> List[Dict[str, Any]]:
    _ensure_tables(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT id, url, events, active, created_at, description "
            "FROM webhooks ORDER BY id",
        ).fetchall()
    return [dict(r) for r in rows]


def delete_webhook(store: Any, webhook_id: int) -> bool:
    _ensure_tables(store)
    with store.connect() as con:
        cur = con.execute("DELETE FROM webhooks WHERE id = ?", (webhook_id,))
        con.commit()
        return cur.rowcount > 0


# ── Dispatch ───────────────────────────────────────────────────────

def _sign(body: bytes, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"), body, hashlib.sha256,
    ).hexdigest()


def _deliver(
    url: str, body: bytes, signature: str,
    *, retries: int = 3,
) -> tuple:
    """POST with HMAC signature. Returns ``(status_code, error)``."""
    import time
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, data=body, method="POST",
                headers={
                    "Content-Type": "application/json",
                    "X-RCM-Signature": f"sha256={signature}",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, None
        except Exception as exc:  # noqa: BLE001
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                return 0, str(exc)
    return 0, "max retries exceeded"


def dispatch_event(
    store: Any, event_type: str, payload: Dict[str, Any],
    *, async_delivery: bool = True,
) -> int:
    """Fire ``event_type`` to all matching active webhooks.

    Returns the count of webhooks that matched. Delivery happens in
    background threads by default so the caller's request isn't
    blocked.
    """
    _ensure_tables(store)
    body = json.dumps(
        {"event": event_type, "payload": payload,
         "timestamp": _utcnow()},
        default=str,
    ).encode("utf-8")

    with store.connect() as con:
        rows = con.execute(
            "SELECT id, url, secret, events FROM webhooks WHERE active = 1",
        ).fetchall()

    matched = 0
    for row in rows:
        events = (row["events"] or "").split(",")
        if event_type not in events and "*" not in events:
            continue
        matched += 1
        wh_id = row["id"]
        url = row["url"]
        secret = row["secret"]
        sig = _sign(body, secret)

        def _do_deliver(wh_id=wh_id, url=url, sig=sig):
            status, error = _deliver(url, body, sig)
            try:
                with store.connect() as con:
                    con.execute(
                        "INSERT INTO webhook_deliveries "
                        "(webhook_id, event_type, payload_json, "
                        " status_code, attempts, delivered_at, error) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (wh_id, event_type, body.decode(), status,
                         1, _utcnow(), error),
                    )
                    con.commit()
            except Exception:  # noqa: BLE001
                pass

        if async_delivery:
            threading.Thread(target=_do_deliver, daemon=True).start()
        else:
            _do_deliver()
    return matched
