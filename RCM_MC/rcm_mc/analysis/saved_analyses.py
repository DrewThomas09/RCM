"""Saved analysis templates — partner-named shortcuts.

A partner running the same HCRIS Peer X-Ray against ``ccn=010001``
fifty times a month shouldn't type the CCN fifty times. This module
lets them save (name, route, params) triples and launch them in one
click from the dashboard.

Shape on disk::

    CREATE TABLE IF NOT EXISTS saved_analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        route TEXT NOT NULL,
        params_json TEXT NOT NULL DEFAULT '{}',
        description TEXT NOT NULL DEFAULT '',
        created_by TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        last_run_at TEXT,
        run_count INTEGER NOT NULL DEFAULT 0,
        pinned INTEGER NOT NULL DEFAULT 0
    )

Public API::

    save_template(store, *, name, route, params, description="", created_by="") -> int
    list_templates(store, *, limit=50) -> List[Dict]
    delete_template(store, template_id) -> bool
    bump_run(store, template_id) -> None
    resolved_href(template) -> str    # route + encoded params

The deliberately-thin shape matches the existing `saved_searches`
table so the two can grow independently without coupling. Params
are stored as JSON so a template can carry arbitrary shape
(``{"ccn": "010001"}``, ``{"dataset": "hospital_04", "years": 5}``,
etc.).
"""
from __future__ import annotations

import json
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_table(store: Any) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS saved_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                route TEXT NOT NULL,
                params_json TEXT NOT NULL DEFAULT '{}',
                description TEXT NOT NULL DEFAULT '',
                created_by TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                last_run_at TEXT,
                run_count INTEGER NOT NULL DEFAULT 0,
                pinned INTEGER NOT NULL DEFAULT 0
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_saved_analyses_pinned "
            "ON saved_analyses(pinned DESC, last_run_at DESC)"
        )
        con.commit()


# ── Write ──────────────────────────────────────────────────────────

def save_template(
    store: Any,
    *,
    name: str,
    route: str,
    params: Optional[Dict[str, Any]] = None,
    description: str = "",
    created_by: str = "",
    pinned: bool = False,
) -> int:
    """Insert a new saved template. Returns the new row id.

    Validates that ``route`` is a local path (no open-redirect gadget)
    and that ``name`` isn't empty. Raises ValueError on bad input —
    caller should surface the message to the user (the message is
    safe to render verbatim; no internal state in it).
    """
    if not name or not name.strip():
        raise ValueError("name required")
    route_s = (route or "").strip()
    if not (route_s.startswith("/") and not route_s.startswith("//")
            and "://" not in route_s):
        raise ValueError(
            f"route must be a local path, got {route_s!r}"
        )
    _ensure_table(store)
    params_s = json.dumps(params or {}, sort_keys=True)
    with store.connect() as con:
        cur = con.execute(
            "INSERT INTO saved_analyses "
            "(name, route, params_json, description, created_by, "
            " created_at, pinned) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name.strip()[:80], route_s[:500], params_s[:4000],
             (description or "")[:200], (created_by or "")[:80],
             _utcnow(), 1 if pinned else 0),
        )
        con.commit()
        return int(cur.lastrowid)


def delete_template(store: Any, template_id: int) -> bool:
    _ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            "DELETE FROM saved_analyses WHERE id = ?",
            (int(template_id),),
        )
        con.commit()
        return cur.rowcount > 0


def bump_run(store: Any, template_id: int) -> None:
    """Update last_run_at + increment run_count. Called whenever a
    partner launches a saved template. Silent no-op for unknown ids."""
    _ensure_table(store)
    with store.connect() as con:
        con.execute(
            "UPDATE saved_analyses "
            "SET last_run_at = ?, run_count = run_count + 1 "
            "WHERE id = ?",
            (_utcnow(), int(template_id)),
        )
        con.commit()


# ── Read ───────────────────────────────────────────────────────────

def list_templates(
    store: Any, *, limit: int = 50,
) -> List[Dict[str, Any]]:
    """Return templates newest-pinned-first, then by last_run_at."""
    _ensure_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT id, name, route, params_json, description, "
            "created_by, created_at, last_run_at, run_count, pinned "
            "FROM saved_analyses "
            "ORDER BY pinned DESC, "
            "COALESCE(last_run_at, created_at) DESC "
            "LIMIT ?",
            (int(limit),),
        ).fetchall()
    out: List[Dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        try:
            d["params"] = json.loads(d.get("params_json") or "{}")
        except json.JSONDecodeError:
            d["params"] = {}
        out.append(d)
    return out


def get_template(
    store: Any, template_id: int,
) -> Optional[Dict[str, Any]]:
    _ensure_table(store)
    with store.connect() as con:
        row = con.execute(
            "SELECT id, name, route, params_json, description, "
            "created_by, created_at, last_run_at, run_count, pinned "
            "FROM saved_analyses WHERE id = ?",
            (int(template_id),),
        ).fetchone()
    if row is None:
        return None
    d = dict(row)
    try:
        d["params"] = json.loads(d.get("params_json") or "{}")
    except json.JSONDecodeError:
        d["params"] = {}
    return d


# ── Helper ─────────────────────────────────────────────────────────

def resolved_href(template: Dict[str, Any]) -> str:
    """route + URL-encoded query string from params.

    Used by the UI to build the launch link. Empty params collapse
    to just the route; ``{"ccn": "010001"}`` → ``/route?ccn=010001``.
    """
    route = template.get("route") or "/"
    params = template.get("params") or {}
    if not params:
        return route
    qs = urllib.parse.urlencode(
        {k: v for k, v in params.items() if v is not None},
        doseq=True,
    )
    sep = "&" if "?" in route else "?"
    return f"{route}{sep}{qs}" if qs else route
