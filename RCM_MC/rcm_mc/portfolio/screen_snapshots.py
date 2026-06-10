"""P9 — vintage-diff snapshots of saved Target-Screener screens.

A saved screen is a query string (see saved_screens.py); its RESULT SET
changes when the underlying CMS data is re-vendored (facilities enter/leave
the screen, beds/quality move, ownership flips). This module lets a partner
snapshot a screen's results and, on later visits, see an honest diff line —
"+3 entered · −1 left · 2 changed" — instead of silently looking at a
different universe than last month.

Storage follows the saved_screens pattern (additive CREATE TABLE IF NOT
EXISTS, parameterised SQL, owner-scoped). Snapshots are derivative analytics
of a saved screen: when the screen is deleted, the server's delete handler
calls ``delete_snapshots_for_screen`` explicitly (saved_screens has no FK
chain to ride, so the cleanup is deliberate — see the delete-policy matrix
in CLAUDE.md).

Diff thresholds are deliberate, documented honesty guards: a 1-bed rounding
wiggle is NOT a change.
  - size (beds/units): relative change ≥ 5%
  - q (metric column): relative change ≥ 5% (numeric only)
  - ownership / name: any change (string identity)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .store import PortfolioStore

# Cap stored rows per snapshot — a statewide screen can be thousands of
# facilities; the diff story is about the screen a partner actually watches,
# and 1,000 rows ≈ 150 KB of JSON, a sane per-row ceiling for SQLite.
_MAX_ROWS = 1000

_REL_THRESHOLD = 0.05   # 5% relative move on numeric fields


def _ensure_table(store: PortfolioStore) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS screen_result_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                screen_id INTEGER NOT NULL,
                owner TEXT NOT NULL,
                taken_at TEXT NOT NULL,
                results_json TEXT NOT NULL
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_screen_snap_screen "
            "ON screen_result_snapshots (screen_id, owner, taken_at)"
        )
        con.commit()


def take_snapshot(store: PortfolioStore, owner: str, screen_id: int,
                  results: Dict[str, Dict[str, Any]]) -> int:
    """Persist the screen's current result set keyed by CCN. Returns row id.

    ``results`` = {ccn: {"name":…, "state":…, "ownership":…, "size":…, "q":…}}
    — the normalized row shape _vertical_rows produces, minus presentation
    fields. Caller is responsible for having computed it from the same code
    path the screener renders (no parallel implementations).
    """
    owner = (owner or "").strip()
    if not owner:
        raise ValueError("snapshot requires an owner")
    _ensure_table(store)
    trimmed = dict(list(results.items())[:_MAX_ROWS])
    now = datetime.now(timezone.utc).isoformat()
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            "INSERT INTO screen_result_snapshots "
            "(screen_id, owner, taken_at, results_json) VALUES (?, ?, ?, ?)",
            (int(screen_id), owner, now,
             json.dumps(trimmed, separators=(",", ":"))),
        )
        con.commit()
        return int(cur.lastrowid)


def latest_snapshot(store: PortfolioStore, owner: str,
                    screen_id: int) -> Optional[Dict[str, Any]]:
    """Newest snapshot for (owner, screen) → {"taken_at", "results"} or None."""
    owner = (owner or "").strip()
    if not owner:
        return None
    _ensure_table(store)
    with store.connect() as con:
        row = con.execute(
            "SELECT taken_at, results_json FROM screen_result_snapshots "
            "WHERE screen_id = ? AND owner = ? "
            "ORDER BY taken_at DESC, id DESC LIMIT 1",
            (int(screen_id), owner),
        ).fetchone()
    if row is None:
        return None
    try:
        results = json.loads(row[1])
    except Exception:  # noqa: BLE001 — corrupt JSON reads as empty, not 500
        results = {}
    return {"taken_at": str(row[0]), "results": results}


def delete_snapshots_for_screen(store: PortfolioStore, owner: str,
                                screen_id: int) -> int:
    """Explicit cleanup when a saved screen is deleted (no FK chain to ride).
    Returns rows removed."""
    owner = (owner or "").strip()
    if not owner:
        return 0
    _ensure_table(store)
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute(
            "DELETE FROM screen_result_snapshots "
            "WHERE screen_id = ? AND owner = ?",
            (int(screen_id), owner),
        )
        con.commit()
        return cur.rowcount


def _num(v: Any) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def _moved(old: Any, new: Any) -> bool:
    """True when a numeric field moved ≥ the relative threshold, or a value
    appeared/disappeared. Sub-threshold wiggle is NOT a change (honesty
    guard: re-vendored files round differently)."""
    o, n = _num(old), _num(new)
    if o is None and n is None:
        return False
    if o is None or n is None:
        return True               # newly reported / newly missing IS a change
    base = max(abs(o), 1e-9)
    return abs(n - o) / base >= _REL_THRESHOLD


def diff_results(old: Dict[str, Dict[str, Any]],
                 new: Dict[str, Dict[str, Any]]) -> Dict[str, List]:
    """Pure set+field diff between two snapshots' result dicts.

    Returns {"entered": [{ccn,name}], "left": [{ccn,name}],
             "changed": [{ccn,name,field,old,new}]} — changed covers
    ownership/name (string identity) and size/q (≥5% relative move).
    """
    old_keys, new_keys = set(old), set(new)
    entered = [{"ccn": c, "name": str((new[c] or {}).get("name") or "")}
               for c in sorted(new_keys - old_keys)]
    left = [{"ccn": c, "name": str((old[c] or {}).get("name") or "")}
            for c in sorted(old_keys - new_keys)]
    changed: List[Dict[str, Any]] = []
    for c in sorted(old_keys & new_keys):
        o, n = old[c] or {}, new[c] or {}
        for field in ("ownership", "name"):
            ov, nv = str(o.get(field) or ""), str(n.get(field) or "")
            if ov != nv and (ov or nv):
                changed.append({"ccn": c, "name": nv or ov, "field": field,
                                "old": ov or "—", "new": nv or "—"})
        for field in ("size", "q"):
            if _moved(o.get(field), n.get(field)):
                changed.append({
                    "ccn": c, "name": str(n.get("name") or ""),
                    "field": field,
                    "old": o.get(field) if o.get(field) is not None else "—",
                    "new": n.get(field) if n.get(field) is not None else "—",
                })
    return {"entered": entered, "left": left, "changed": changed}


def diff_summary(diff: Dict[str, List]) -> str:
    """One honest line for the saved-screens card. Empty diff → '' (silence
    over a fabricated 'no change' that implies a fresh comparison ran)."""
    bits = []
    if diff["entered"]:
        bits.append(f"+{len(diff['entered'])} entered")
    if diff["left"]:
        bits.append(f"−{len(diff['left'])} left")
    if diff["changed"]:
        bits.append(f"{len(diff['changed'])} changed")
    return " · ".join(bits)
