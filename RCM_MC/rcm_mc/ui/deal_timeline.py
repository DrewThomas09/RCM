"""Unified deal activity timeline (Prompt 34).

Pulls events from every table that records deal-level state changes
and renders a vertical timeline the associate reads top-down. Each
event is a color-coded card: analysis=blue, alert=amber, export=green,
note=gray, override=purple, mc=teal. Filter toggles + date range.

Route: ``GET /deal/<id>/timeline`` and workbench 8th tab "Activity".
API: ``GET /api/deals/<id>/timeline?days=30``.
"""
from __future__ import annotations

import html
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Event model ────────────────────────────────────────────────────

_EVENT_COLORS = {
    "analysis": "#3b82f6",
    "alert": "#f59e0b",
    "export": "#10b981",
    "note": "#94a3b8",
    "override": "#8b5cf6",
    "mc_run": "#14b8a6",
    "other": "#64748b",
}


def _esc(s: Any) -> str:
    return html.escape("" if s is None else str(s))


def _event_dict(
    *, event_type: str, timestamp: str, title: str,
    detail: str = "", deal_id: str = "", author: str = "",
) -> Dict[str, Any]:
    return {
        "event_type": event_type,
        "timestamp": timestamp,
        "title": title,
        "detail": detail,
        "deal_id": deal_id,
        "author": author,
    }


# ── Event collectors ───────────────────────────────────────────────

def _collect_analysis_events(
    store: Any, deal_id: str, since: str,
) -> List[Dict[str, Any]]:
    """From ``analysis_runs``."""
    events: List[Dict[str, Any]] = []
    try:
        from ..analysis.analysis_store import list_packets
        for row in list_packets(store, deal_id):
            ts = row.get("created_at") or ""
            if ts < since:
                continue
            events.append(_event_dict(
                event_type="analysis",
                timestamp=ts,
                title=f"Analysis packet built (run {row.get('run_id') or '?'})",
                detail=f"model_version={row.get('model_version') or '?'}",
                deal_id=deal_id,
            ))
    except Exception:  # noqa: BLE001
        pass
    return events


def _collect_export_events(
    store: Any, deal_id: str, since: str,
) -> List[Dict[str, Any]]:
    """From ``generated_exports``."""
    events: List[Dict[str, Any]] = []
    try:
        from ..exports.export_store import list_exports
        for row in list_exports(store, deal_id):
            ts = row.get("generated_at") or ""
            if ts < since:
                continue
            events.append(_event_dict(
                event_type="export",
                timestamp=ts,
                title=f"Export: {row.get('format') or '?'}",
                detail=f"by {row.get('generated_by') or 'system'}",
                deal_id=deal_id,
                author=row.get("generated_by") or "",
            ))
    except Exception:  # noqa: BLE001
        pass
    return events


def _collect_note_events(
    store: Any, deal_id: str, since: str,
) -> List[Dict[str, Any]]:
    """From ``deal_notes``."""
    events: List[Dict[str, Any]] = []
    try:
        from ..deals.deal_notes import list_notes
        df = list_notes(store, deal_id=deal_id)
        for _, row in df.iterrows():
            ts = str(row.get("created_at") or "")
            if ts < since:
                continue
            body = str(row.get("body") or "")
            events.append(_event_dict(
                event_type="note",
                timestamp=ts,
                title="Note",
                detail=body[:200],
                deal_id=deal_id,
                author=str(row.get("author") or ""),
            ))
    except Exception:  # noqa: BLE001
        pass
    return events


def _collect_override_events(
    store: Any, deal_id: str, since: str,
) -> List[Dict[str, Any]]:
    """From ``deal_overrides``."""
    events: List[Dict[str, Any]] = []
    try:
        from ..analysis.deal_overrides import list_overrides
        for row in list_overrides(store, deal_id):
            ts = row.get("set_at") or ""
            if ts < since:
                continue
            events.append(_event_dict(
                event_type="override",
                timestamp=ts,
                title=f"Override: {row.get('override_key') or '?'}",
                detail=(
                    f"= {row.get('override_value')!r}"
                    + (f" ({row.get('reason')})" if row.get("reason") else "")
                ),
                deal_id=deal_id,
                author=row.get("set_by") or "",
            ))
    except Exception:  # noqa: BLE001
        pass
    return events


def _collect_mc_events(
    store: Any, deal_id: str, since: str,
) -> List[Dict[str, Any]]:
    """From ``mc_simulation_runs``."""
    events: List[Dict[str, Any]] = []
    try:
        from ..mc.mc_store import list_mc_runs
        for row in list_mc_runs(store, deal_id):
            ts = row.get("created_at") or ""
            if ts < since:
                continue
            events.append(_event_dict(
                event_type="mc_run",
                timestamp=ts,
                title=f"MC run: {row.get('scenario_label') or 'default'}",
                detail=f"n={row.get('n_simulations') or '?'}",
                deal_id=deal_id,
            ))
    except Exception:  # noqa: BLE001
        pass
    return events


# ── Public API ─────────────────────────────────────────────────────

def collect_timeline(
    store: Any, deal_id: str, *, days: int = 90,
) -> List[Dict[str, Any]]:
    """Aggregate events from all tables, sorted newest-first."""
    since = (
        datetime.now(timezone.utc) - timedelta(days=max(1, int(days)))
    ).isoformat()
    events: List[Dict[str, Any]] = []
    events.extend(_collect_analysis_events(store, deal_id, since))
    events.extend(_collect_export_events(store, deal_id, since))
    events.extend(_collect_note_events(store, deal_id, since))
    events.extend(_collect_override_events(store, deal_id, since))
    events.extend(_collect_mc_events(store, deal_id, since))
    events.sort(key=lambda e: e.get("timestamp") or "", reverse=True)
    return events


# ── HTML renderer ──────────────────────────────────────────────────

def render_timeline(
    deal_id: str, deal_name: str,
    events: List[Dict[str, Any]],
) -> str:
    """Full-page timeline HTML."""
    from ._chartis_kit import (
        chartis_shell, ck_eyebrow, ck_fmt_num, ck_kpi_block,
        ck_next_section, ck_provenance_tooltip,
    )

    if not events:
        return chartis_shell(
            '<div class="cad-card"><p style="color:var(--cad-text3);">No activity recorded yet. '
            f'<a href="/analysis/{_esc(deal_id)}" style="color:var(--cad-link);">View analysis &rarr;</a>'
            '</p></div>',
            f"{deal_name} — Timeline",
        )

    cards: List[str] = []
    for ev in events:
        color = _EVENT_COLORS.get(ev["event_type"], _EVENT_COLORS["other"])
        author = f' — {_esc(ev["author"])}' if ev.get("author") else ""
        cards.append(
            f'<div class="tl-card" style="border-left:3px solid {color};">'
            f'<div class="tl-meta">{_esc(ev["timestamp"][:19])}{author}</div>'
            f'<div class="tl-title">'
            f'<span class="tl-badge" style="background:{color};">'
            f'{_esc(ev["event_type"])}</span> '
            f'{_esc(ev["title"])}</div>'
            + (f'<div class="tl-detail">{_esc(ev["detail"])}</div>'
               if ev.get("detail") else "")
            + '</div>'
        )

    css = """
    .tl-card { background:#FAF7F0; border:1px solid #D6CFC0;
      border-left:3px solid #155752;
      padding:12px 14px; margin-bottom:8px; border-radius:2px;
      font-family:"Inter Tight","Inter",sans-serif; }
    .tl-meta { color:#5C6878; font-size:11px; margin-bottom:4px;
      font-family:"JetBrains Mono",monospace; letter-spacing:.04em; }
    .tl-title { font-weight:600; font-size:13px; color:#1a2332; }
    .tl-badge { color:#FAF7F0; font-size:10px; padding:2px 7px;
      border-radius:2px; text-transform:uppercase; letter-spacing:.08em;
      font-family:"JetBrains Mono",monospace; font-weight:600; }
    .tl-detail { color:#5C6878; font-size:12px; margin-top:4px; line-height:1.5; }
    """
    body = f"""
    <h2>{_esc(deal_name)} — Activity Timeline ({len(events)} events)</h2>
    <div>{''.join(cards)}</div>
    """
    # Cycle 47 — KPI strip + provenance + editorial chrome.
    type_counts: Dict[str, int] = {}
    for ev in events:
        et = ev.get("event_type", "other")
        type_counts[et] = type_counts.get(et, 0) + 1
    most_common = max(type_counts.items(), key=lambda kv: kv[1]) if type_counts else ("—", 0)
    events_value = ck_provenance_tooltip(
        "Activity events on this deal",
        ck_fmt_num(len(events)),
        explainer=(
            f"Audit-log events recorded against this deal "
            f"(notes, status changes, alerts, exports, simulation "
            f"reruns). Most-common type: {most_common[0]} "
            f"({most_common[1]}x)."
        ),
    )
    types_value = ck_provenance_tooltip(
        "Event types observed",
        ck_fmt_num(len(type_counts)),
        explainer=(
            "Distinct event categories (note / status / alert / "
            "export / sim / etc.) observed on this deal. Higher "
            "diversity = more partner engagement; sustained "
            "single-category activity may indicate a stuck deal."
        ),
        inject_css=False,
    )
    kpi_strip = (
        '<div class="ck-kpi-grid" style="grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px;">'
        + ck_kpi_block("Total Events", events_value, "in audit log")
        + ck_kpi_block("Event Types", types_value, "distinct categories")
        + ck_kpi_block("Most Common",
                       most_common[0],
                       f"{most_common[1]} occurrences")
        + '</div>'
    )

    next_up = ck_next_section(
        "Back to the deal profile",
        f"/deal/{_esc(deal_id)}",
        eyebrow="Continue —",
        italic_word="profile",
    )
    return chartis_shell(
        ck_eyebrow("Activity Timeline") + kpi_strip + f'<div>{"".join(cards)}</div>' + next_up,
        f"{deal_name} — Timeline",
        subtitle=f"{len(events)} events",
        extra_css=css,
        editorial_intro={
            "eyebrow": "DEAL TIMELINE",
            "headline": "What's happened on this deal.",
            "italic_word": "happened",
            "body": (
                "Chronological audit log of every event on the "
                "deal - notes, status changes, alerts, exports, "
                "simulation reruns. Use this to read partner "
                "engagement velocity over time."
            ),
        },
    )
