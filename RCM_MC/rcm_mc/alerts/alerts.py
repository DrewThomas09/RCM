"""Portfolio alert evaluators (Brick 101).

A PE analyst's Monday-morning question: "what broke over the weekend?".
Answering it means scanning the whole portfolio for covenant trips,
variance breaches, and concerning-signal clusters. This module wraps
that scan as a set of **alert evaluators** returning a flat list of
``Alert`` records so the /alerts page and /api/alerts/active endpoint
can share the same logic.

Design:

- **No user-configurable rules yet.** Start with a fixed set of
  evaluators. Customisation is easy to add later via a rules table; the
  evaluation interface is stable so the UI layer won't move.
- **Severity levels.** ``red`` = immediate attention (covenant trip,
  ≥15% variance miss); ``amber`` = watch (TIGHT covenant, stage
  regress, concerning cluster); ``info`` = notable but not action.
- **Idempotent.** Evaluators never mutate the store. Safe to call on
  every page view.

Public API::

    evaluate_all(store) -> list[Alert]
    active_count(store) -> int         # just the red+amber ones
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..pe.hold_tracking import variance_report
from ..portfolio.store import PortfolioStore
from ..portfolio.portfolio_snapshots import DEAL_STAGES, list_snapshots


# Stage → index for detecting "regress" (went backward in funnel)
_STAGE_RANK = {s: i for i, s in enumerate(DEAL_STAGES)}


@dataclass
class Alert:
    """One portfolio-level event worth a partner's attention."""
    kind: str          # short machine id (e.g. "covenant_tripped")
    severity: str      # "red" | "amber" | "info"
    deal_id: str
    title: str         # headline shown in the list
    detail: str        # supporting sentence / numbers
    triggered_at: Optional[str] = None   # ISO timestamp of the source event
    first_seen_at: Optional[str] = None  # when history first saw this instance
    returning: bool = False              # B145: re-fired after snooze expired

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "severity": self.severity,
            "deal_id": self.deal_id,
            "title": self.title,
            "detail": self.detail,
            "triggered_at": self.triggered_at,
            "first_seen_at": self.first_seen_at,
            "returning": self.returning,
        }


# ── Evaluators ───────────────────────────────────────────────────────────

def _evaluate_covenant(store: PortfolioStore) -> List[Alert]:
    """Flag any deal whose latest snapshot has TRIPPED/TIGHT covenant."""
    from ..portfolio.portfolio_snapshots import latest_per_deal
    df = latest_per_deal(store)
    out: List[Alert] = []
    if df.empty:
        return out
    for _, r in df.iterrows():
        status = r.get("covenant_status")
        if status == "TRIPPED":
            lev = r.get("covenant_leverage")
            lev_str = f"{float(lev):.2f}x" if lev and lev == lev else "—"
            out.append(Alert(
                kind="covenant_tripped", severity="red",
                deal_id=str(r["deal_id"]),
                title="Covenant TRIPPED",
                detail=f"Actual leverage {lev_str} exceeds maximum allowed",
                triggered_at=str(r.get("created_at") or ""),
            ))
        elif status == "TIGHT":
            lev = r.get("covenant_leverage")
            lev_str = f"{float(lev):.2f}x" if lev and lev == lev else "—"
            out.append(Alert(
                kind="covenant_tight", severity="amber",
                deal_id=str(r["deal_id"]),
                title="Covenant TIGHT",
                detail=f"Actual leverage {lev_str} within 1 turn of maximum",
                triggered_at=str(r.get("created_at") or ""),
            ))
    return out


def _evaluate_variance(
    store: PortfolioStore,
    *,
    miss_threshold: float = 0.10,
) -> List[Alert]:
    """Flag deals whose most recent EBITDA variance is worse than ``-miss_threshold``.

    Default threshold 10%. A deal missing EBITDA by ≥10% vs plan in the
    latest recorded quarter is red; ≥5% is amber.
    """
    from ..portfolio.portfolio_snapshots import latest_per_deal
    deal_df = latest_per_deal(store)
    out: List[Alert] = []
    if deal_df.empty:
        return out
    for _, r in deal_df.iterrows():
        did = str(r["deal_id"])
        vdf = variance_report(store, did)
        if vdf.empty or "ebitda" not in set(vdf["kpi"]):
            continue
        ebitda = vdf[vdf["kpi"] == "ebitda"].sort_values("quarter")
        latest = ebitda.iloc[-1]
        vp = latest.get("variance_pct")
        if vp is None or (isinstance(vp, float) and vp != vp):
            continue
        vp_f = float(vp)
        if vp_f <= -miss_threshold:
            out.append(Alert(
                kind="variance_miss_red", severity="red",
                deal_id=did,
                title=f"EBITDA variance {vp_f*100:+.1f}%",
                detail=f"Quarter {latest.get('quarter')}: "
                       f"actual {latest.get('actual')} vs plan {latest.get('plan')}",
                triggered_at=str(latest.get("quarter")),
            ))
        elif vp_f <= -0.05:
            out.append(Alert(
                kind="variance_miss_amber", severity="amber",
                deal_id=did,
                title=f"EBITDA variance {vp_f*100:+.1f}%",
                detail=f"Quarter {latest.get('quarter')}: lagging plan",
                triggered_at=str(latest.get("quarter")),
            ))
    return out


def _evaluate_concerning_cluster(
    store: PortfolioStore, threshold: int = 3,
) -> List[Alert]:
    """Flag deals with ≥N concerning signals (from B30 trend severity)."""
    from ..portfolio.portfolio_snapshots import latest_per_deal
    df = latest_per_deal(store)
    out: List[Alert] = []
    if df.empty:
        return out
    for _, r in df.iterrows():
        nc = r.get("concerning_signals")
        nc_int = int(nc) if nc is not None and nc == nc else 0
        if nc_int >= threshold:
            out.append(Alert(
                kind="concerning_cluster", severity="amber",
                deal_id=str(r["deal_id"]),
                title=f"{nc_int} concerning trend signals",
                detail="Multiple HCRIS metrics trending in concerning direction",
                triggered_at=str(r.get("created_at") or ""),
            ))
    return out


def _evaluate_stage_regress(store: PortfolioStore) -> List[Alert]:
    """Flag deals whose last two snapshots moved backward in the funnel.

    ``loi`` → ``ioi`` is a regress; ``closed`` → ``hold`` is not
    (canonical forward motion). Rare but important to surface.
    """
    out: List[Alert] = []
    # Get unique deal IDs from the store
    import pandas as pd
    all_snaps = list_snapshots(store)
    if all_snaps.empty:
        return out
    for did, group in all_snaps.groupby("deal_id"):
        if len(group) < 2:
            continue
        ordered = group.sort_values("created_at")
        stages = ordered["stage"].tolist()
        for i in range(1, len(stages)):
            prev_rank = _STAGE_RANK.get(stages[i - 1], -1)
            cur_rank = _STAGE_RANK.get(stages[i], -1)
            if cur_rank < prev_rank and cur_rank >= 0:
                out.append(Alert(
                    kind="stage_regress", severity="amber",
                    deal_id=str(did),
                    title=f"Stage regress: {stages[i - 1]} → {stages[i]}",
                    detail="Deal moved backward in the funnel — confirm fall-out vs data correction.",
                    triggered_at=str(ordered.iloc[i]["created_at"]),
                ))
                break  # one alert per deal is enough
    return out


def _evaluate_overdue_deadlines(store: PortfolioStore) -> List[Alert]:
    """B115: surface overdue open deadlines as amber alerts.

    trigger_key includes the deadline_id so completing or deleting
    clears the alert naturally; if the deadline is still open but the
    date passes, a new alert instance fires at the next evaluation.
    """
    from ..deals.deal_deadlines import overdue
    out: List[Alert] = []
    try:
        df = overdue(store)
    except Exception:  # noqa: BLE001
        return out
    if df.empty:
        return out
    for _, r in df.iterrows():
        days = int(r["days_overdue"])
        did = str(r["deal_id"])
        label = str(r["label"])
        dl_id = int(r["deadline_id"])
        out.append(Alert(
            kind="deadline_overdue", severity="amber",
            deal_id=did,
            title=f"Overdue: {label}",
            detail=f"Due {r['due_date']} ({days}d ago)",
            # Include deadline_id in trigger_key so the alert is
            # instance-specific — completing deadline N clears only its
            # alert, not other overdue deadlines on the same deal.
            triggered_at=f"deadline_{dl_id}",
        ))
    return out


_EVALUATORS = [
    _evaluate_covenant,
    _evaluate_variance,
    _evaluate_concerning_cluster,
    _evaluate_stage_regress,
    _evaluate_overdue_deadlines,
]


# ── Public API ───────────────────────────────────────────────────────────

EVALUATOR_FAILURES: Dict[str, int] = {}
_LAST_EVALUATOR_FAILURE: Dict[str, str] = {}


def evaluate_all(store: PortfolioStore) -> List[Alert]:
    """Run every evaluator + return the combined list, severity-sorted.

    B162 fix: when an evaluator raises, we still continue past it (so
    one broken evaluator can't hide the others), but we now surface
    the failure via a module-level counter + stderr so operators can
    tell that "no covenant alerts today" might mean "covenant evaluator
    is broken" rather than "nothing tripped".
    """
    import sys as _sys
    import traceback as _tb
    alerts: List[Alert] = []
    for ev in _EVALUATORS:
        try:
            alerts.extend(ev(store))
        except Exception as exc:  # noqa: BLE001
            name = getattr(ev, "__name__", repr(ev))
            EVALUATOR_FAILURES[name] = EVALUATOR_FAILURES.get(name, 0) + 1
            _LAST_EVALUATOR_FAILURE[name] = (
                f"{type(exc).__name__}: {exc}"
            )
            _sys.stderr.write(
                f"[rcm-mc alerts] evaluator {name} FAILED: "
                f"{type(exc).__name__}: {exc}\n"
                f"{_tb.format_exc(limit=4)}"
            )
            _sys.stderr.flush()
            continue
    # Sort: red > amber > info; within severity, newest-first by triggered_at
    sev_order = {"red": 0, "amber": 1, "info": 2}
    alerts.sort(key=lambda a: (sev_order.get(a.severity, 9),
                               -(hash(a.triggered_at or "") & 0xFFFF)))
    return alerts


def evaluate_active(store: PortfolioStore) -> List[Alert]:
    """``evaluate_all`` minus alerts that have been acked + not expired.

    This is what the UI should display by default — acked alerts stay in
    the audit trail but aren't in the partner's face. Also records a
    sighting in ``alert_history`` (B104) and enriches each Alert with
    its ``first_seen_at`` so callers can show age hints.
    """
    from .alert_acks import is_acked, trigger_key_for, was_snoozed
    from .alert_history import get_first_seen, record_sightings
    all_alerts = evaluate_all(store)
    # Record the full set — acked alerts stay in history for audit.
    try:
        record_sightings(store, all_alerts)
    except Exception:  # noqa: BLE001 — history must not break the page
        pass
    out: List[Alert] = []
    for a in all_alerts:
        tk = trigger_key_for(a)
        if is_acked(store, kind=a.kind, deal_id=a.deal_id, trigger_key=tk):
            continue
        a.first_seen_at = get_first_seen(
            store, kind=a.kind, deal_id=a.deal_id, trigger_key=tk,
        )
        # B145: mark as "returning" when an earlier snooze has elapsed
        a.returning = was_snoozed(
            store, kind=a.kind, deal_id=a.deal_id, trigger_key=tk,
        )
        out.append(a)
    return out


def active_count(store: PortfolioStore) -> int:
    """How many red + amber alerts would the UI show right now?

    Excludes acked/snoozed alerts (since those are explicitly silenced).
    """
    return sum(1 for a in evaluate_active(store)
               if a.severity in ("red", "amber"))
