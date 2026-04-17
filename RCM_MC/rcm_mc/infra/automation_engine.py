"""Workflow automation engine for rule-based actions.

Partners configure rules that fire automatically when specific events
occur — stage changes, metric thresholds, analysis completions, risk
flags. This keeps the daily-ops loop tight: the system surfaces what
matters and kicks off the right follow-up without a partner clicking
through six screens.

Design:
- Rules live in SQLite (``automation_rules`` table) so they survive
  restarts and are auditable.
- Execution history is logged to ``automation_log`` so partners can
  see what ran and whether it succeeded.
- Five preset rules are auto-seeded on the first call to
  ``list_rules`` or ``evaluate_rules`` so a fresh database is
  immediately useful.
- Action execution is intentionally thin — we return
  :class:`ActionResult` descriptors rather than performing side
  effects, so the caller (server, CLI, cron) decides how to dispatch.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Dataclasses ──────────────────────────────────────────────────────

@dataclass
class AutomationRule:
    """One automation rule.

    ``trigger`` is one of the four supported event types.
    ``conditions`` is a list of dicts, each with ``field``, ``op``,
    ``value`` — all must match for the rule to fire (AND logic).
    ``actions`` is a list of dicts, each with ``action_type`` plus
    action-specific keys.
    """
    rule_id: str
    name: str
    trigger: str
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    active: bool = True
    created_by: str = "system"


@dataclass
class ActionResult:
    """Outcome of evaluating one action from a matched rule."""
    rule_id: str
    action_type: str
    success: bool
    detail: str = ""


# ── Supported types ──────────────────────────────────────────────────

TRIGGER_TYPES = frozenset({
    "stage_change",
    "metric_threshold",
    "analysis_completed",
    "risk_fired",
})

ACTION_TYPES = frozenset({
    "send_notification",
    "rebuild_analysis",
    "add_tag",
})


# ── Table setup ──────────────────────────────────────────────────────

def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_tables(store: Any) -> None:
    """Idempotent CREATE for automation tables.

    Always runs CREATE IF NOT EXISTS — no process-level caching flag
    because test suites create fresh DB files per test case and a
    stale flag would skip the CREATE on the new file.
    """
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS automation_rules (
                rule_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                trigger TEXT NOT NULL,
                conditions_json TEXT NOT NULL DEFAULT '[]',
                actions_json TEXT NOT NULL DEFAULT '[]',
                active INTEGER NOT NULL DEFAULT 1,
                created_by TEXT NOT NULL DEFAULT 'system',
                created_at TEXT NOT NULL
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS automation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_data_json TEXT,
                action_type TEXT NOT NULL,
                success INTEGER NOT NULL,
                detail TEXT,
                executed_at TEXT NOT NULL
            )"""
        )
        con.commit()
    _TABLES_CREATED = True


def reset_tables_created_flag() -> None:
    """Test helper — reset the module-level caching flag."""
    global _TABLES_CREATED
    _TABLES_CREATED = False


# ── CRUD ─────────────────────────────────────────────────────────────

def save_rule(store: Any, rule: AutomationRule) -> None:
    """Insert or replace an automation rule."""
    _ensure_tables(store)
    with store.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        try:
            con.execute(
                """INSERT OR REPLACE INTO automation_rules
                   (rule_id, name, trigger, conditions_json, actions_json,
                    active, created_by, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    rule.rule_id,
                    rule.name,
                    rule.trigger,
                    json.dumps(rule.conditions),
                    json.dumps(rule.actions),
                    1 if rule.active else 0,
                    rule.created_by,
                    _utcnow_iso(),
                ),
            )
            con.commit()
        except Exception:
            con.rollback()
            raise


def list_rules(store: Any) -> List[AutomationRule]:
    """Return all rules, seeding presets if the table is empty."""
    _ensure_tables(store)
    _seed_presets_if_empty(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT * FROM automation_rules ORDER BY rule_id"
        ).fetchall()
    return [_row_to_rule(r) for r in rows]


def toggle_rule(store: Any, rule_id: str, active: bool) -> bool:
    """Enable or disable a rule. Returns True if the rule existed."""
    _ensure_tables(store)
    with store.connect() as con:
        cur = con.execute(
            "UPDATE automation_rules SET active = ? WHERE rule_id = ?",
            (1 if active else 0, rule_id),
        )
        con.commit()
        return cur.rowcount > 0


def _row_to_rule(row: Any) -> AutomationRule:
    return AutomationRule(
        rule_id=row["rule_id"],
        name=row["name"],
        trigger=row["trigger"],
        conditions=json.loads(row["conditions_json"]),
        actions=json.loads(row["actions_json"]),
        active=bool(row["active"]),
        created_by=row["created_by"],
    )


# ── Evaluation engine ────────────────────────────────────────────────

def evaluate_rules(
    store: Any,
    event_type: str,
    event_data: Dict[str, Any],
) -> List[ActionResult]:
    """Check all active rules against an event, return matching actions.

    Each matching rule produces one :class:`ActionResult` per action in
    its ``actions`` list. Results are also logged to ``automation_log``.
    """
    _ensure_tables(store)
    _seed_presets_if_empty(store)
    rules = _load_active_rules(store, event_type)
    results: List[ActionResult] = []
    for rule in rules:
        if not _conditions_match(rule.conditions, event_data):
            continue
        for action in rule.actions:
            action_type = action.get("action_type", "unknown")
            result = ActionResult(
                rule_id=rule.rule_id,
                action_type=action_type,
                success=action_type in ACTION_TYPES,
                detail=json.dumps(action),
            )
            results.append(result)
            _log_execution(store, rule.rule_id, event_type, event_data, result)
    return results


def _load_active_rules(store: Any, event_type: str) -> List[AutomationRule]:
    with store.connect() as con:
        rows = con.execute(
            "SELECT * FROM automation_rules WHERE active = 1 AND trigger = ?",
            (event_type,),
        ).fetchall()
    return [_row_to_rule(r) for r in rows]


def _conditions_match(
    conditions: List[Dict[str, Any]],
    event_data: Dict[str, Any],
) -> bool:
    """All conditions must match (AND logic).

    Supported operators: ``eq``, ``ne``, ``gt``, ``lt``, ``gte``,
    ``lte``, ``contains``, ``in``.
    """
    if not conditions:
        return True
    for cond in conditions:
        fld = cond.get("field", "")
        op = cond.get("op", "eq")
        expected = cond.get("value")
        actual = event_data.get(fld)
        if not _op_check(op, actual, expected):
            return False
    return True


def _op_check(op: str, actual: Any, expected: Any) -> bool:
    """Evaluate one condition operator."""
    try:
        if op == "eq":
            return actual == expected
        if op == "ne":
            return actual != expected
        if op == "gt":
            return float(actual) > float(expected)
        if op == "lt":
            return float(actual) < float(expected)
        if op == "gte":
            return float(actual) >= float(expected)
        if op == "lte":
            return float(actual) <= float(expected)
        if op == "contains":
            return str(expected) in str(actual)
        if op == "in":
            return actual in (expected if isinstance(expected, (list, tuple)) else [expected])
    except (TypeError, ValueError):
        return False
    return False


def _log_execution(
    store: Any,
    rule_id: str,
    event_type: str,
    event_data: Dict[str, Any],
    result: ActionResult,
) -> None:
    """Write an execution record to automation_log."""
    try:
        with store.connect() as con:
            con.execute(
                """INSERT INTO automation_log
                   (rule_id, event_type, event_data_json, action_type,
                    success, detail, executed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    rule_id,
                    event_type,
                    json.dumps(event_data),
                    result.action_type,
                    1 if result.success else 0,
                    result.detail,
                    _utcnow_iso(),
                ),
            )
            con.commit()
    except Exception:
        logger.debug("automation_log write failed", exc_info=True)


# ── Preset rules ─────────────────────────────────────────────────────

_PRESET_RULES: List[AutomationRule] = [
    AutomationRule(
        rule_id="preset_ic_package",
        name="IC package on stage change to IC",
        trigger="stage_change",
        conditions=[{"field": "new_stage", "op": "eq", "value": "IC"}],
        actions=[{"action_type": "rebuild_analysis", "reason": "IC package prep"}],
        created_by="system",
    ),
    AutomationRule(
        rule_id="preset_hold_onboarding",
        name="Notify on hold during onboarding",
        trigger="stage_change",
        conditions=[{"field": "new_stage", "op": "eq", "value": "on_hold"}],
        actions=[{"action_type": "send_notification", "message": "Deal placed on hold during onboarding"}],
        created_by="system",
    ),
    AutomationRule(
        rule_id="preset_covenant_warning",
        name="Covenant headroom warning",
        trigger="metric_threshold",
        conditions=[{"field": "metric_key", "op": "eq", "value": "covenant_headroom"},
                    {"field": "value", "op": "lt", "value": 0.10}],
        actions=[{"action_type": "send_notification", "message": "Covenant headroom below 10%"}],
        created_by="system",
    ),
    AutomationRule(
        rule_id="preset_stale_analysis",
        name="Tag stale analysis",
        trigger="analysis_completed",
        conditions=[{"field": "packet_age_days", "op": "gt", "value": 30}],
        actions=[{"action_type": "add_tag", "tag": "stale_analysis"}],
        created_by="system",
    ),
    AutomationRule(
        rule_id="preset_consecutive_miss",
        name="Alert on consecutive miss",
        trigger="risk_fired",
        conditions=[{"field": "risk_type", "op": "eq", "value": "consecutive_miss"}],
        actions=[{"action_type": "send_notification", "message": "Consecutive miss detected"}],
        created_by="system",
    ),
]


def _seed_presets_if_empty(store: Any) -> None:
    """Insert preset rules when the table is empty."""
    with store.connect() as con:
        count = con.execute("SELECT COUNT(*) FROM automation_rules").fetchone()[0]
    if count > 0:
        return
    for rule in _PRESET_RULES:
        save_rule(store, rule)
