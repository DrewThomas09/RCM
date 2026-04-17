"""Abstract base class for Practice Management System connectors (Prompt 76).

Each PMS vendor (Epic, Cerner, athena, etc.) subclasses ``PMSConnector``
and implements the four pull methods.  Credential storage uses SQLite
with base64 encoding as a placeholder for real encryption — the
round-trip fidelity matters more than the cipher at this stage.
"""
from __future__ import annotations

import base64
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Abstract base ─────────────────────────────────────────────────────

class PMSConnector(ABC):
    """Interface every PMS integration must implement."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    @abstractmethod
    def test_connection(self) -> bool:
        """Return True if the remote system is reachable."""
        ...

    @abstractmethod
    def pull_encounters(self, date_range: Tuple[str, str]) -> list[dict]:
        """Pull encounter/visit records for the given (start, end) date range."""
        ...

    @abstractmethod
    def pull_charges(self, date_range: Tuple[str, str]) -> list[dict]:
        """Pull charge/billing records for the given date range."""
        ...

    @abstractmethod
    def pull_ar_aging(self) -> dict:
        """Pull current AR aging summary from the PMS."""
        ...


# ── Credential storage ───────────────────────────────────────────────

def _ensure_credentials_table(store: Any) -> None:
    """Create integration_credentials table if absent."""
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS integration_credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                system TEXT NOT NULL,
                config_b64 TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(deal_id, system)
            )"""
        )
        con.commit()


def save_credentials(
    store: Any,
    deal_id: str,
    system: str,
    config: dict[str, Any],
) -> None:
    """Persist PMS credentials (base64-encoded JSON) for a deal+system pair.

    Uses INSERT OR REPLACE so repeated saves update in place.
    """
    _ensure_credentials_table(store)
    now = datetime.now(timezone.utc).isoformat()
    encoded = base64.b64encode(json.dumps(config).encode()).decode()
    with store.connect() as con:
        con.execute(
            """INSERT INTO integration_credentials
               (deal_id, system, config_b64, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(deal_id, system)
               DO UPDATE SET config_b64 = excluded.config_b64,
                             updated_at = excluded.updated_at""",
            (deal_id, system, encoded, now, now),
        )
        con.commit()


def load_credentials(
    store: Any,
    deal_id: str,
    system: str,
) -> Optional[dict[str, Any]]:
    """Load and decode PMS credentials for a deal+system pair.

    Returns None if no credentials are stored.
    """
    _ensure_credentials_table(store)
    with store.connect() as con:
        row = con.execute(
            "SELECT config_b64 FROM integration_credentials "
            "WHERE deal_id = ? AND system = ?",
            (deal_id, system),
        ).fetchone()
    if row is None:
        return None
    try:
        decoded = base64.b64decode(row["config_b64"]).decode()
        return json.loads(decoded)
    except Exception:
        logger.warning("Failed to decode credentials for %s/%s", deal_id, system)
        return None
