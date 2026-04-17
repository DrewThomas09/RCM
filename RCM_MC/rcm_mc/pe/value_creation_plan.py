"""Value Creation Plan builder + persistence (Prompt 41).

After closing, the deal team builds a 100-day value creation plan.
This module auto-generates :class:`Initiative` entries from the v2
bridge's lever impacts, assigns the appropriate ramp curve, and
persists the plan in SQLite so the hold dashboard (Prompt 42) can
track progress.
"""
from __future__ import annotations

import json
import logging
import zlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Dataclasses ────────────────────────────────────────────────────

@dataclass
class Milestone:
    description: str
    due_date: str = ""
    completed: bool = False
    completed_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Milestone":
        return cls(
            description=str(d.get("description") or ""),
            due_date=str(d.get("due_date") or ""),
            completed=bool(d.get("completed")),
            completed_date=d.get("completed_date"),
        )


@dataclass
class Initiative:
    initiative_id: str
    name: str
    description: str = ""
    lever_key: str = ""
    current_value: float = 0.0
    target_value: float = 0.0
    target_ebitda_impact: float = 0.0
    owner: str = ""
    start_month: int = 1
    end_month: int = 12
    milestones: List[Milestone] = field(default_factory=list)
    status: str = "not_started"
    ramp_curve: str = "default"

    def to_dict(self) -> Dict[str, Any]:
        return {
            **{k: v for k, v in asdict(self).items() if k != "milestones"},
            "milestones": [m.to_dict() for m in self.milestones],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Initiative":
        return cls(
            initiative_id=str(d.get("initiative_id") or ""),
            name=str(d.get("name") or ""),
            description=str(d.get("description") or ""),
            lever_key=str(d.get("lever_key") or ""),
            current_value=float(d.get("current_value") or 0),
            target_value=float(d.get("target_value") or 0),
            target_ebitda_impact=float(d.get("target_ebitda_impact") or 0),
            owner=str(d.get("owner") or ""),
            start_month=int(d.get("start_month") or 1),
            end_month=int(d.get("end_month") or 12),
            milestones=[
                Milestone.from_dict(m) for m in (d.get("milestones") or [])
            ],
            status=str(d.get("status") or "not_started"),
            ramp_curve=str(d.get("ramp_curve") or "default"),
        )


@dataclass
class ValueCreationPlan:
    deal_id: str
    plan_name: str = ""
    created_at: str = ""
    created_by: str = ""
    initiatives: List[Initiative] = field(default_factory=list)
    total_target_ebitda: float = 0.0
    plan_horizon_months: int = 36

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deal_id": self.deal_id,
            "plan_name": self.plan_name,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "initiatives": [i.to_dict() for i in self.initiatives],
            "total_target_ebitda": float(self.total_target_ebitda),
            "plan_horizon_months": int(self.plan_horizon_months),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ValueCreationPlan":
        return cls(
            deal_id=str(d.get("deal_id") or ""),
            plan_name=str(d.get("plan_name") or ""),
            created_at=str(d.get("created_at") or ""),
            created_by=str(d.get("created_by") or ""),
            initiatives=[
                Initiative.from_dict(i) for i in (d.get("initiatives") or [])
            ],
            total_target_ebitda=float(d.get("total_target_ebitda") or 0),
            plan_horizon_months=int(d.get("plan_horizon_months") or 36),
        )


# ── SQLite ─────────────────────────────────────────────────────────

def _ensure_table(store: Any) -> None:
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS value_creation_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                plan_json BLOB NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT,
                version INTEGER DEFAULT 1,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id) ON DELETE CASCADE
            )"""
        )
        con.commit()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_plan(store: Any, plan: ValueCreationPlan) -> int:
    _ensure_table(store)
    blob = zlib.compress(
        json.dumps(plan.to_dict(), default=str).encode("utf-8"),
    )
    with store.connect() as con:
        cur = con.execute(
            "INSERT INTO value_creation_plans "
            "(deal_id, plan_json, created_at, created_by) VALUES (?, ?, ?, ?)",
            (plan.deal_id, blob, plan.created_at or _utcnow(),
             plan.created_by or "system"),
        )
        con.commit()
        return int(cur.lastrowid)


def load_latest_plan(store: Any, deal_id: str) -> Optional[ValueCreationPlan]:
    _ensure_table(store)
    with store.connect() as con:
        row = con.execute(
            "SELECT plan_json FROM value_creation_plans "
            "WHERE deal_id = ? ORDER BY id DESC LIMIT 1",
            (deal_id,),
        ).fetchone()
    if row is None:
        return None
    try:
        data = json.loads(zlib.decompress(row["plan_json"]).decode())
        return ValueCreationPlan.from_dict(data)
    except Exception:  # noqa: BLE001
        return None


def update_initiative_status(
    store: Any, deal_id: str, initiative_id: str,
    status: str, *, notes: Optional[str] = None,
) -> bool:
    """Update one initiative's status on the latest plan.

    Loads the plan, patches the initiative, re-saves as a new
    version. Returns True if the initiative was found + updated.
    """
    plan = load_latest_plan(store, deal_id)
    if plan is None:
        return False
    for init in plan.initiatives:
        if init.initiative_id == initiative_id:
            init.status = status
            plan.created_at = _utcnow()
            save_plan(store, plan)
            return True
    return False


# ── Auto-generate from packet ─────────────────────────────────────

def create_plan_from_packet(
    packet: Any,
    *,
    owner_map: Optional[Dict[str, str]] = None,
) -> ValueCreationPlan:
    """Auto-generate one initiative per v2 bridge lever.

    ``owner_map`` maps metric_key → owner name so the deal team
    can pre-assign owners at plan creation. Unassigned levers get
    ``owner=""``.
    """
    owner_map = owner_map or {}
    initiatives: List[Initiative] = []

    # Prefer the v2 bridge (value_bridge_result); fall back to v1.
    vbr = packet.value_bridge_result or {}
    lever_impacts = vbr.get("lever_impacts") or []
    if not lever_impacts and packet.ebitda_bridge:
        lever_impacts = [
            {
                "metric_key": imp.metric_key,
                "current_value": float(imp.current_value),
                "target_value": float(imp.target_value),
                "recurring_ebitda_delta": float(imp.ebitda_impact or 0),
            }
            for imp in (packet.ebitda_bridge.per_metric_impacts or [])
        ]

    # Ramp-curve family lookup.
    try:
        from .ramp_curves import family_for_metric
    except Exception:  # noqa: BLE001
        def family_for_metric(k):
            return "default"

    for i, li in enumerate(lever_impacts):
        metric = li.get("metric_key") or f"lever_{i}"
        ebitda = float(
            li.get("recurring_ebitda_delta")
            or li.get("ebitda_impact") or 0,
        )
        family = family_for_metric(metric)
        initiatives.append(Initiative(
            initiative_id=f"init-{metric}",
            name=f"Improve {metric.replace('_', ' ')}",
            lever_key=metric,
            current_value=float(li.get("current_value") or 0),
            target_value=float(li.get("target_value") or 0),
            target_ebitda_impact=ebitda,
            owner=owner_map.get(metric, ""),
            ramp_curve=family,
        ))

    total = sum(i.target_ebitda_impact for i in initiatives)
    return ValueCreationPlan(
        deal_id=packet.deal_id,
        plan_name=f"{packet.deal_name or packet.deal_id} — Value Creation Plan",
        created_at=_utcnow(),
        initiatives=initiatives,
        total_target_ebitda=total,
    )
