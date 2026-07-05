"""Cleaning profiles — named, persisted rule-suite configurations.

Great Expectations calls these "expectation suites"; Informatica calls them
rule sets. A profile lets a team encode how THEIR feeds should be judged:

  * ``disabled_rules``  — flags that don't run at all (e.g. a self-pay
                          extract with no payer column noise).
  * ``accepted_rules``  — known-issue flags that still REPORT but no longer
                          count against the quality grade (data-stewardship
                          annotation: "we know, it's upstream, stop paging").
  * ``thresholds``      — tunable knobs where payers genuinely differ:
                          ``timely_filing_days`` (default 365),
                          ``stale_years`` (default 10),
                          ``outlier_iqr_mult`` (default 3.0).

Only report-only FLAGS can be disabled or accepted — the deterministic
repairs always run (they are safe by construction and fully audited in the
change log).

Storage is the same dedicated SQLite family as run history: a file in the
cleaner's WORKDIR, aggregate config only, never claim data.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from .engine import WORKDIR

_DB_PATH = Path(WORKDIR) / "npi_cleaner_profiles.sqlite3"
_LOCK = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    name    TEXT PRIMARY KEY,
    config  TEXT NOT NULL,     -- JSON
    updated REAL NOT NULL
);
"""

_DEFAULT_THRESHOLDS = {
    "timely_filing_days": 365,
    "stale_years": 10,
    "outlier_iqr_mult": 3.0,
}


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(_DB_PATH)
    con.execute("PRAGMA busy_timeout = 5000")
    con.executescript(_SCHEMA)
    return con


def _sanitize(config: Dict[str, object]) -> Dict[str, object]:
    """Clamp a raw config to the known shape — unknown keys dropped, rule
    ids validated against the registry so a typo'd rule can't silently
    disable nothing, thresholds coerced to sane numeric ranges."""
    try:
        from . import rules as _rules
        known = {r.id for r in _rules.all_rules()}
    except Exception:  # noqa: BLE001
        known = set()

    def _rule_list(key: str) -> List[str]:
        vals = config.get(key) or []
        if not isinstance(vals, list):
            return []
        out = [str(v) for v in vals if not known or str(v) in known]
        return sorted(set(out))

    thr_in = config.get("thresholds") or {}
    thr: Dict[str, object] = dict(_DEFAULT_THRESHOLDS)
    if isinstance(thr_in, dict):
        try:
            d = int(thr_in.get("timely_filing_days",
                               thr["timely_filing_days"]))
            thr["timely_filing_days"] = max(30, min(1095, d))
        except (TypeError, ValueError):
            pass
        try:
            y = int(thr_in.get("stale_years", thr["stale_years"]))
            thr["stale_years"] = max(1, min(50, y))
        except (TypeError, ValueError):
            pass
        try:
            m = float(thr_in.get("outlier_iqr_mult",
                                 thr["outlier_iqr_mult"]))
            thr["outlier_iqr_mult"] = max(1.5, min(10.0, m))
        except (TypeError, ValueError):
            pass

    return {"disabled_rules": _rule_list("disabled_rules"),
            "accepted_rules": _rule_list("accepted_rules"),
            "thresholds": thr}


def save_profile(name: str, config: Dict[str, object]) -> Dict[str, object]:
    """Upsert a named profile; returns the sanitized config as stored."""
    name = (name or "").strip()[:64]
    if not name:
        raise ValueError("profile name required")
    clean = _sanitize(config or {})
    with _LOCK, _conn() as con:
        con.execute(
            "INSERT INTO profiles (name, config, updated) VALUES (?,?,?) "
            "ON CONFLICT(name) DO UPDATE SET config=excluded.config,"
            " updated=excluded.updated",
            (name, json.dumps(clean), time.time()))
    return clean


def get_profile(name: str) -> Optional[Dict[str, object]]:
    """Load a profile's config (with its name injected) or None."""
    name = (name or "").strip()
    if not name:
        return None
    try:
        with _LOCK, _conn() as con:
            row = con.execute("SELECT config FROM profiles WHERE name = ?",
                              (name,)).fetchone()
    except Exception:  # noqa: BLE001
        return None
    if row is None:
        return None
    try:
        cfg = json.loads(row[0])
    except ValueError:
        return None
    cfg["name"] = name
    return cfg


def list_profiles() -> List[Dict[str, object]]:
    try:
        with _LOCK, _conn() as con:
            rows = con.execute(
                "SELECT name, config, updated FROM profiles "
                "ORDER BY name").fetchall()
    except Exception:  # noqa: BLE001
        return []
    out = []
    for name, cfg_json, updated in rows:
        try:
            cfg = json.loads(cfg_json)
        except ValueError:
            cfg = {}
        out.append({"name": name, "updated": updated,
                    "disabled_rules": cfg.get("disabled_rules") or [],
                    "accepted_rules": cfg.get("accepted_rules") or [],
                    "thresholds": cfg.get("thresholds")
                    or dict(_DEFAULT_THRESHOLDS)})
    return out


def delete_profile(name: str) -> bool:
    with _LOCK, _conn() as con:
        cur = con.execute("DELETE FROM profiles WHERE name = ?",
                          ((name or "").strip(),))
        return cur.rowcount > 0
