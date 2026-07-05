"""Mapping templates — named, persisted column-mapping overrides.

Every source system exports claims with its own header vocabulary
("Billing_Prov_NPI", "SVC_DT", …). The mapping editor lets a user fix the
auto-detector per upload; a TEMPLATE lets a team fix it once per source
system ("Epic extract", "Athena 837 dump") and reuse it on every upload —
the same idea as profiles.py, but for column roles instead of rules.

Storage follows the profiles/history pattern: a dedicated SQLite file in
the cleaner's WORKDIR holding role→header strings only — configuration,
never claim data. Role keys are deliberately NOT restricted to the roles
the stdlib engine acts on: unknown roles flow through clean_bytes'
overrides to the v49 engine via vendor_adapter, exactly like a live
X-Overrides header does.
"""
from __future__ import annotations

import json
import re
import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

from .engine import WORKDIR

_DB_PATH = Path(WORKDIR) / "npi_cleaner_mappings.sqlite3"
_LOCK = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS mappings (
    name    TEXT PRIMARY KEY,
    mapping TEXT NOT NULL,     -- JSON {role: header}
    updated REAL NOT NULL
);
"""

# Role keys look like detector role tokens (billing_npi, service_date …).
_ROLE_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_MAX_ROLES = 100
_MAX_HEADER_LEN = 160


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(_DB_PATH)
    con.execute("PRAGMA busy_timeout = 5000")
    con.executescript(_SCHEMA)
    return con


def _sanitize(mapping: Dict[str, object]) -> Dict[str, str]:
    """Keep only sane role→header pairs: lowercase role tokens, non-empty
    bounded header strings, capped entry count. Garbage in a template must
    degrade to auto-detection, never to an exception at upload time."""
    if not isinstance(mapping, dict):
        return {}
    out: Dict[str, str] = {}
    for k, v in mapping.items():
        role = str(k).strip().lower()
        header = str(v).strip() if v is not None else ""
        if not header or len(header) > _MAX_HEADER_LEN:
            continue
        if not _ROLE_RE.match(role):
            continue
        out[role] = header
        if len(out) >= _MAX_ROLES:
            break
    return out


def save_mapping(name: str, mapping: Dict[str, object]) -> Dict[str, str]:
    """Upsert a named template; returns the sanitized mapping as stored."""
    name = (name or "").strip()[:64]
    if not name:
        raise ValueError("template name required")
    clean = _sanitize(mapping or {})
    if not clean:
        raise ValueError("template needs at least one role -> column entry")
    with _LOCK, _conn() as con:
        con.execute(
            "INSERT INTO mappings (name, mapping, updated) VALUES (?,?,?) "
            "ON CONFLICT(name) DO UPDATE SET mapping=excluded.mapping,"
            " updated=excluded.updated",
            (name, json.dumps(clean), time.time()))
    return clean


def get_mapping(name: str) -> Optional[Dict[str, str]]:
    name = (name or "").strip()
    if not name:
        return None
    try:
        with _LOCK, _conn() as con:
            row = con.execute("SELECT mapping FROM mappings WHERE name = ?",
                              (name,)).fetchone()
    except Exception:  # noqa: BLE001 — a broken store degrades to auto-detect
        return None
    if row is None:
        return None
    try:
        raw = json.loads(row[0])
    except ValueError:
        return None
    return _sanitize(raw) or None


def list_mappings() -> List[Dict[str, object]]:
    try:
        with _LOCK, _conn() as con:
            rows = con.execute(
                "SELECT name, mapping, updated FROM mappings "
                "ORDER BY name").fetchall()
    except Exception:  # noqa: BLE001
        return []
    out = []
    for name, map_json, updated in rows:
        try:
            m = _sanitize(json.loads(map_json))
        except ValueError:
            m = {}
        out.append({"name": name, "updated": updated, "mapping": m,
                    "roles": len(m)})
    return out


def delete_mapping(name: str) -> bool:
    with _LOCK, _conn() as con:
        cur = con.execute("DELETE FROM mappings WHERE name = ?",
                          ((name or "").strip(),))
        return cur.rowcount > 0
