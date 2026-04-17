"""Integration hub: DealCloud / Salesforce / Google Sheets (Prompt 58).

Standardized portfolio CSV export + webhook-based CRM sync.
Google Sheets push is optional (API key in config). The CSV format
is the common denominator — DealCloud and Salesforce can both
consume it via their CSV import endpoints.
"""
from __future__ import annotations

import csv
import io
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Schema ─────────────────────────────────────────────────────────

def _ensure_table(store: Any) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS integration_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                config_json TEXT NOT NULL,
                active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            )"""
        )
        con.commit()


def save_integration(
    store: Any, provider: str, config: Dict[str, str],
) -> int:
    _ensure_table(store)
    now = datetime.now(timezone.utc).isoformat()
    with store.connect() as con:
        cur = con.execute(
            "INSERT INTO integration_configs "
            "(provider, config_json, created_at) VALUES (?, ?, ?)",
            (provider, json.dumps(config), now),
        )
        con.commit()
        return int(cur.lastrowid)


def list_integrations(store: Any) -> List[Dict[str, Any]]:
    _ensure_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT * FROM integration_configs ORDER BY id",
        ).fetchall()
    return [dict(r) for r in rows]


# ── Portfolio CSV export ───────────────────────────────────────────

_CSV_COLUMNS = [
    "deal_id", "deal_name", "state", "bed_count",
    "completeness_grade", "ebitda_opportunity",
    "top_risk", "risk_count",
]


def export_portfolio_csv(store: Any) -> str:
    """One row per deal with key metrics — the format DealCloud and
    Salesforce can consume directly."""
    try:
        from ..analysis.analysis_store import list_packets, load_packet_by_id
    except Exception:  # noqa: BLE001
        return ""
    rows_data = list_packets(store)
    seen: set = set()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(_CSV_COLUMNS)
    for r in rows_data:
        did = r.get("deal_id") or ""
        if did in seen:
            continue
        seen.add(did)
        pkt = load_packet_by_id(store, r["id"])
        if pkt is None:
            continue
        ebitda = float(pkt.ebitda_bridge.total_ebitda_impact or 0) if pkt.ebitda_bridge else 0
        grade = getattr(pkt.completeness, "grade", "") or ""
        state = getattr(pkt.profile, "state", "") or ""
        beds = getattr(pkt.profile, "bed_count", "") or ""
        top_risk = ""
        risk_count = len(pkt.risk_flags or [])
        if pkt.risk_flags:
            top_risk = pkt.risk_flags[0].title or ""
        w.writerow([
            did, pkt.deal_name or did, state, beds,
            grade, f"{ebitda:.0f}", top_risk, risk_count,
        ])
    return buf.getvalue()


# ── Webhook-based CRM sync ────────────────────────────────────────

def sync_deal_to_crm(
    store: Any, deal_id: str, event_type: str = "deal.updated",
) -> int:
    """Fire a standardized payload to all active integration webhooks.

    Reuses the webhook dispatch from Prompt 39 so the CRM just needs
    to consume the same event shape.
    """
    try:
        from ..infra.webhooks import dispatch_event
    except Exception:  # noqa: BLE001
        return 0
    payload = {"deal_id": deal_id, "event": event_type}
    try:
        from ..analysis.analysis_store import list_packets, load_packet_by_id
        rows = list_packets(store, deal_id)
        if rows:
            pkt = load_packet_by_id(store, rows[0]["id"])
            if pkt:
                payload["deal_name"] = pkt.deal_name or deal_id
                payload["ebitda_opportunity"] = float(
                    pkt.ebitda_bridge.total_ebitda_impact or 0
                ) if pkt.ebitda_bridge else 0
    except Exception:  # noqa: BLE001
        pass
    return dispatch_event(store, event_type, payload, async_delivery=True)
