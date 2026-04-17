"""Email + Slack notification dispatch (Prompt 44).

Partners want a weekly email digest and Slack alerts on critical
events. This module provides the channel abstraction, message
formatting, and scheduling — all optional-dep-free (stdlib
``smtplib`` for email, ``urllib`` for Slack incoming webhooks).
"""
from __future__ import annotations

import json
import logging
import os
import smtplib
import threading
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Schema ─────────────────────────────────────────────────────────

def _ensure_tables(store: Any) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS notification_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                config_json TEXT NOT NULL,
                events TEXT NOT NULL,
                active INTEGER DEFAULT 1
            )"""
        )
        con.commit()


# ── Config CRUD ────────────────────────────────────────────────────

def save_config(
    store: Any, user_id: str, channel: str,
    config: Dict[str, str], events: List[str],
) -> int:
    _ensure_tables(store)
    with store.connect() as con:
        cur = con.execute(
            "INSERT INTO notification_configs "
            "(user_id, channel, config_json, events) "
            "VALUES (?, ?, ?, ?)",
            (user_id, channel,
             json.dumps(config), ",".join(events)),
        )
        con.commit()
        return int(cur.lastrowid)


def get_configs(store: Any, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    _ensure_tables(store)
    with store.connect() as con:
        if user_id:
            rows = con.execute(
                "SELECT * FROM notification_configs WHERE user_id = ?",
                (user_id,),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM notification_configs",
            ).fetchall()
    return [dict(r) for r in rows]


# ── Senders ────────────────────────────────────────────────────────

def _send_email(
    to: str, subject: str, body_html: str,
) -> bool:
    """Send via SMTP. Env vars: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS.
    Returns False (no-op) when not configured — never raises."""
    host = os.environ.get("SMTP_HOST")
    if not host:
        logger.debug("SMTP not configured; email skipped")
        return False
    port = int(os.environ.get("SMTP_PORT") or 587)
    user = os.environ.get("SMTP_USER") or ""
    password = os.environ.get("SMTP_PASS") or ""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = user or "rcm-mc@noreply.local"
    msg["To"] = to
    msg.attach(MIMEText(body_html, "html"))
    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.ehlo()
            if port == 587:
                server.starttls()
            if user and password:
                server.login(user, password)
            server.sendmail(msg["From"], [to], msg.as_string())
        return True
    except Exception as exc:  # noqa: BLE001
        logger.debug("email send failed: %s", exc)
        return False


def _send_slack(webhook_url: str, text: str) -> bool:
    """POST to a Slack incoming webhook. Returns True on 2xx."""
    if not webhook_url:
        return False
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        webhook_url, data=payload, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return 200 <= resp.status < 300
    except Exception as exc:  # noqa: BLE001
        logger.debug("slack send failed: %s", exc)
        return False


# ── Dispatch ───────────────────────────────────────────────────────

def send_notification(
    channel: str, config: Dict[str, str],
    event_type: str, payload: Dict[str, Any],
) -> bool:
    """Route to the right sender."""
    text = f"[RCM-MC] {event_type}: {json.dumps(payload, default=str)[:500]}"
    if channel == "EMAIL":
        return _send_email(
            config.get("email") or "",
            f"RCM-MC: {event_type}",
            f"<h3>{event_type}</h3><pre>{json.dumps(payload, indent=2, default=str)}</pre>",
        )
    if channel == "SLACK":
        return _send_slack(config.get("slack_webhook") or "", text)
    return False


def dispatch_to_configs(
    store: Any, event_type: str, payload: Dict[str, Any],
) -> int:
    """Check all active notification_configs and dispatch matches."""
    configs = get_configs(store)
    sent = 0
    for cfg in configs:
        if not cfg.get("active"):
            continue
        events = (cfg.get("events") or "").split(",")
        if event_type not in events and "*" not in events:
            continue
        try:
            config_data = json.loads(cfg.get("config_json") or "{}")
        except json.JSONDecodeError:
            continue
        channel = cfg.get("channel") or ""

        def _do(ch=channel, cd=config_data):
            send_notification(ch, cd, event_type, payload)

        threading.Thread(target=_do, daemon=True).start()
        sent += 1
    return sent


# ── Weekly digest ──────────────────────────────────────────────────

@dataclass
class DigestReport:
    deals_needing_attention: List[str] = field(default_factory=list)
    total_deals: int = 0
    critical_risks: int = 0
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deals_needing_attention": list(self.deals_needing_attention),
            "total_deals": int(self.total_deals),
            "critical_risks": int(self.critical_risks),
            "summary": self.summary,
        }


def build_weekly_digest(store: Any) -> DigestReport:
    """Portfolio-level summary for the weekly email."""
    report = DigestReport()
    try:
        from ..analysis.analysis_store import list_packets, load_packet_by_id
        rows = list_packets(store)
        seen: set = set()
        for r in rows:
            did = r.get("deal_id") or ""
            if did in seen:
                continue
            seen.add(did)
            report.total_deals += 1
            pkt = load_packet_by_id(store, r["id"])
            if pkt is None:
                continue
            for rf in (pkt.risk_flags or []):
                sev = rf.severity.value if hasattr(rf.severity, "value") else str(rf.severity)
                if sev == "CRITICAL":
                    report.critical_risks += 1
                    if did not in report.deals_needing_attention:
                        report.deals_needing_attention.append(did)
    except Exception as exc:  # noqa: BLE001
        logger.debug("digest build failed: %s", exc)
    report.summary = (
        f"{report.total_deals} deal(s), "
        f"{report.critical_risks} critical risk(s), "
        f"{len(report.deals_needing_attention)} deal(s) need attention."
    )
    return report
