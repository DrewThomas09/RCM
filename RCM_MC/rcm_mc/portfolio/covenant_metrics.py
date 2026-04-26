"""Per-deal covenant metrics — Q4.5 schema expansion.

Phase 3 wired Net Leverage from ``deal_snapshots.covenant_leverage`` (one
column on the snapshots table). The other 5 spec covenants (Interest
Coverage, Days Cash on Hand, EBITDA/Plan, Denial Rate, Days in A/R) had
no place to land — the editorial covenant heatmap rendered "—" for them
honestly with a footnote.

This module adds the second dimension: a 1-many ``covenant_metrics``
table keyed on (deal_id, covenant_name, created_at) so any number of
covenants can be tracked per deal without forcing a column migration
each time the spec covenant set changes. Per-deal threshold + direction
config lives on each row, so a deal's covenant_doc terms can override
the spec defaults.

Schema:
    deal_id          TEXT      — FK to deals.deal_id
    snapshot_id      INTEGER   — optional FK to deal_snapshots.snapshot_id
    covenant_name    TEXT      — "Net Leverage", "Interest Coverage", etc.
    value            REAL      — the observed metric value
    threshold        REAL      — the trip floor/ceiling for this deal-covenant
    direction        TEXT      — "max" (≤ threshold safe) or "min" (≥ safe)
    watch_threshold  REAL      — the watch-zone boundary
    created_at       TEXT      — ISO timestamp
    notes            TEXT      — operator-supplied annotation

Direction semantics:
    "max"  → value ≤ watch_threshold       → safe
             watch_threshold < value ≤ threshold → watch
             value > threshold              → trip
    "min"  → value ≥ watch_threshold       → safe
             threshold ≤ value < watch_threshold → watch
             value < threshold              → trip

The covenant_grid() helper in ui/chartis/_app_covenant_heatmap.py
consumes this table and produces the 6-row × 8-quarter heatmap.

Q4.5 closes the spec gap: 1 of 6 covenants tracked → 6 of 6 covenants
tracked. The "1 of 6 covenants tracked" footnote auto-removes when
covenant_grid sees ≥ 2 wired rows.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, List, Optional

from .store import PortfolioStore


# Spec defaults per EDITORIAL_STYLE_PORT.md §6.7 — used by the seeder
# and as fallback when a deal hasn't recorded its own covenant terms.
# Direction: "max" = lower-is-better (Net Leverage / Denial Rate / DAR);
# "min" = higher-is-better (everything else).
SPEC_COVENANT_DEFAULTS = {
    "Net Leverage":       {"threshold": 6.5,   "watch": 6.0,   "direction": "max"},
    "Interest Coverage":  {"threshold": 2.0,   "watch": 2.5,   "direction": "min"},
    "Days Cash on Hand":  {"threshold": 60.0,  "watch": 75.0,  "direction": "min"},
    "EBITDA / Plan":      {"threshold": 0.90,  "watch": 0.95,  "direction": "min"},
    "Denial Rate":        {"threshold": 0.085, "watch": 0.075, "direction": "max"},
    "Days in A/R":        {"threshold": 50.0,  "watch": 45.0,  "direction": "max"},
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_table(store: PortfolioStore) -> None:
    """Create covenant_metrics table if missing. Idempotent."""
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS covenant_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                snapshot_id INTEGER,
                covenant_name TEXT NOT NULL,
                value REAL,
                threshold REAL,
                direction TEXT NOT NULL,
                watch_threshold REAL,
                created_at TEXT NOT NULL,
                notes TEXT,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
                    ON DELETE CASCADE,
                FOREIGN KEY(snapshot_id) REFERENCES deal_snapshots(snapshot_id)
                    ON DELETE SET NULL
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_cov_metrics_deal_cov "
            "ON covenant_metrics(deal_id, covenant_name, created_at)"
        )
        con.commit()


@dataclass
class CovenantMetric:
    """One observation of a covenant for a deal at a point in time."""
    deal_id: str
    covenant_name: str
    value: Optional[float]
    threshold: Optional[float]
    direction: str
    watch_threshold: Optional[float]
    created_at: str
    snapshot_id: Optional[int] = None
    notes: str = ""


def record_covenant_metric(
    store: PortfolioStore,
    *,
    deal_id: str,
    covenant_name: str,
    value: Optional[float],
    threshold: Optional[float],
    direction: str,
    watch_threshold: Optional[float],
    snapshot_id: Optional[int] = None,
    created_at: Optional[str] = None,
    notes: str = "",
) -> int:
    """Insert one (deal, covenant, time) observation. Returns row id.

    ``direction`` must be "max" or "min". ``created_at`` defaults to
    UTC now when not provided. ``threshold`` and ``watch_threshold``
    default to the spec values when None and ``covenant_name`` is in
    SPEC_COVENANT_DEFAULTS.
    """
    if direction not in ("max", "min"):
        raise ValueError(
            f"direction must be 'max' or 'min', got {direction!r}"
        )
    if threshold is None and covenant_name in SPEC_COVENANT_DEFAULTS:
        threshold = SPEC_COVENANT_DEFAULTS[covenant_name]["threshold"]
    if watch_threshold is None and covenant_name in SPEC_COVENANT_DEFAULTS:
        watch_threshold = SPEC_COVENANT_DEFAULTS[covenant_name]["watch"]
    _ensure_table(store)
    ts = created_at or _utcnow_iso()
    with store.connect() as con:
        cur = con.execute(
            """INSERT INTO covenant_metrics
               (deal_id, snapshot_id, covenant_name, value,
                threshold, direction, watch_threshold,
                created_at, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (deal_id, snapshot_id, covenant_name, value,
             threshold, direction, watch_threshold, ts, notes),
        )
        con.commit()
        return int(cur.lastrowid)


def list_covenant_history(
    store: PortfolioStore,
    deal_id: str,
    covenant_name: str,
    *,
    limit: int = 8,
) -> List[CovenantMetric]:
    """Return the last N observations of a covenant for a deal,
    chronologically ordered (oldest → newest, suitable for left-to-right
    heatmap rendering).

    Empty list when no rows or table doesn't exist yet.
    """
    try:
        _ensure_table(store)
        with store.connect() as con:
            rows = con.execute(
                """SELECT * FROM covenant_metrics
                   WHERE deal_id = ? AND covenant_name = ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (deal_id, covenant_name, int(limit)),
            ).fetchall()
    except Exception:  # noqa: BLE001
        return []
    out: List[CovenantMetric] = []
    for r in reversed(list(rows)):  # chronological: oldest first
        d = dict(r) if hasattr(r, "keys") else {}
        out.append(CovenantMetric(
            deal_id=d.get("deal_id", deal_id),
            covenant_name=d.get("covenant_name", covenant_name),
            value=d.get("value"),
            threshold=d.get("threshold"),
            direction=d.get("direction", "max"),
            watch_threshold=d.get("watch_threshold"),
            created_at=d.get("created_at", ""),
            snapshot_id=d.get("snapshot_id"),
            notes=d.get("notes", "") or "",
        ))
    return out


def band_for_metric(
    value: Optional[float],
    threshold: Optional[float],
    watch_threshold: Optional[float],
    direction: str,
) -> str:
    """Classify one (value, threshold, direction) tuple into a heatmap band.

    Returns one of "safe" / "watch" / "trip" / "empty".

    "max" direction (lower-is-better, e.g. Net Leverage):
        value ≤ watch_threshold       → safe
        watch_threshold < value ≤ threshold → watch
        value > threshold             → trip
    "min" direction (higher-is-better, e.g. Interest Coverage):
        value ≥ watch_threshold       → safe
        threshold ≤ value < watch_threshold → watch
        value < threshold             → trip

    Missing inputs (any of value/threshold/watch_threshold None) → "empty".
    """
    if value is None or threshold is None or watch_threshold is None:
        return "empty"
    try:
        v = float(value)
        t = float(threshold)
        w = float(watch_threshold)
    except (TypeError, ValueError):
        return "empty"
    if direction == "max":
        if v <= w:
            return "safe"
        if v <= t:
            return "watch"
        return "trip"
    if direction == "min":
        if v >= w:
            return "safe"
        if v >= t:
            return "watch"
        return "trip"
    return "empty"


def format_value(
    value: Optional[float],
    covenant_name: str,
) -> str:
    """Format a covenant value for display in a heatmap cell.

    Handles the unit conventions per covenant:
      - Net Leverage / Interest Coverage → "X.Xx"
      - Days Cash on Hand / Days in A/R   → "Nd"
      - EBITDA / Plan                     → "XX%" (input as fraction)
      - Denial Rate                       → "X.X%" (input as fraction)
    """
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "—"
    if covenant_name in ("Net Leverage", "Interest Coverage"):
        return f"{v:.1f}x"
    if covenant_name in ("Days Cash on Hand", "Days in A/R"):
        return f"{v:.0f}d"
    if covenant_name == "EBITDA / Plan":
        return f"{v * 100:.0f}%"
    if covenant_name == "Denial Rate":
        return f"{v * 100:.1f}%"
    return f"{v:.2f}"
