"""User-defined custom metrics.

Partners sometimes track KPIs that aren't in the standard
:data:`rcm_mc.analysis.completeness.RCM_METRIC_REGISTRY` — for
instance a proprietary "revenue integrity index" or a region-specific
quality measure. This module lets them register those as first-class
metrics with metadata (unit, directionality, valid range) so the
platform can render, validate, and trend them consistently.

Constraints:
- ``metric_key`` must be lowercase alphanumeric + underscore (no
  spaces, no dashes, no uppercase) so it plays nicely with SQLite
  column references and JSON keys.
- The key must not collide with any key already in
  ``RCM_METRIC_REGISTRY`` — custom metrics extend the registry,
  they don't shadow it.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass
class CustomMetric:
    """One user-defined metric."""
    metric_key: str
    display_name: str
    unit: str = "pct"
    directionality: str = "higher_is_better"  # or "lower_is_better"
    category: str = "custom"
    valid_range: Tuple[float, float] = (0.0, 100.0)
    description: str = ""
    created_by: str = "system"


# ── Table setup ──────────────────────────────────────────────────────

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_table(store: Any) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS custom_metrics (
                metric_key TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                unit TEXT NOT NULL DEFAULT 'pct',
                directionality TEXT NOT NULL DEFAULT 'higher_is_better',
                category TEXT NOT NULL DEFAULT 'custom',
                valid_range_lo REAL NOT NULL DEFAULT 0.0,
                valid_range_hi REAL NOT NULL DEFAULT 100.0,
                description TEXT NOT NULL DEFAULT '',
                created_by TEXT NOT NULL DEFAULT 'system',
                created_at TEXT NOT NULL
            )"""
        )
        con.commit()


# ── Validation ───────────────────────────────────────────────────────

def _get_builtin_keys() -> frozenset:
    """Lazily import the built-in metric registry to check for conflicts."""
    try:
        from ..analysis.completeness import RCM_METRIC_REGISTRY
        return frozenset(RCM_METRIC_REGISTRY.keys())
    except ImportError:
        return frozenset()


def validate_metric_key(key: str) -> List[str]:
    """Return a list of validation errors (empty = valid)."""
    errors: List[str] = []
    if not key:
        errors.append("metric_key must not be empty")
        return errors
    if not _KEY_PATTERN.match(key):
        errors.append(
            "metric_key must be lowercase alphanumeric + underscore, "
            "starting with a letter"
        )
    builtin = _get_builtin_keys()
    if key in builtin:
        errors.append(
            f"metric_key {key!r} conflicts with a built-in metric in "
            f"RCM_METRIC_REGISTRY"
        )
    return errors


# ── CRUD ─────────────────────────────────────────────────────────────

def register_custom_metric(store: Any, metric: CustomMetric) -> None:
    """Register a new custom metric. Raises ValueError on validation failure."""
    errors = validate_metric_key(metric.metric_key)
    if errors:
        raise ValueError("; ".join(errors))
    if metric.directionality not in ("higher_is_better", "lower_is_better"):
        raise ValueError(
            f"directionality must be 'higher_is_better' or "
            f"'lower_is_better', got {metric.directionality!r}"
        )
    _ensure_table(store)
    lo, hi = metric.valid_range
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        try:
            existing = con.execute(
                "SELECT metric_key FROM custom_metrics WHERE metric_key = ?",
                (metric.metric_key,),
            ).fetchone()
            if existing:
                raise ValueError(
                    f"custom metric {metric.metric_key!r} already exists"
                )
            con.execute(
                """INSERT INTO custom_metrics
                   (metric_key, display_name, unit, directionality,
                    category, valid_range_lo, valid_range_hi,
                    description, created_by, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    metric.metric_key,
                    metric.display_name,
                    metric.unit,
                    metric.directionality,
                    metric.category,
                    float(lo),
                    float(hi),
                    metric.description,
                    metric.created_by,
                    _utcnow_iso(),
                ),
            )
            con.commit()
        except ValueError:
            con.rollback()
            raise
        except Exception:
            con.rollback()
            raise


def list_custom_metrics(store: Any) -> List[CustomMetric]:
    """Return all registered custom metrics."""
    _ensure_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT * FROM custom_metrics ORDER BY metric_key"
        ).fetchall()
    return [
        CustomMetric(
            metric_key=r["metric_key"],
            display_name=r["display_name"],
            unit=r["unit"],
            directionality=r["directionality"],
            category=r["category"],
            valid_range=(float(r["valid_range_lo"]), float(r["valid_range_hi"])),
            description=r["description"],
            created_by=r["created_by"],
        )
        for r in rows
    ]


def delete_custom_metric(store: Any, metric_key: str) -> bool:
    """Remove a custom metric. Returns True if it existed."""
    _ensure_table(store)
    with store.connect() as con:
        cur = con.execute(
            "DELETE FROM custom_metrics WHERE metric_key = ?",
            (metric_key,),
        )
        con.commit()
        return cur.rowcount > 0
