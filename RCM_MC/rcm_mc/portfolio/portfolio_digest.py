"""Early-warning digest: what's changed in the portfolio since ``since`` date.

PE partners review portfolios weekly. The dashboard is a point-in-time
snapshot; the digest is the *diff* — what changed since you last looked.
Keeps a partner from re-reading everything every Monday.

Event types captured:

- ``new_deal``: a deal_id that didn't exist in the store before ``since``
- ``stage_advance``: moved forward in the DEAL_STAGES funnel (good)
- ``stage_regress``: moved backward (rare; usually means deal fell out)
- ``covenant_degrade``: SAFE → TIGHT, TIGHT → TRIPPED, or SAFE → TRIPPED
- ``covenant_recover``: the reverse
- ``variance_worse``: quarterly variance crossed into lagging or off_track
- ``variance_better``: the reverse

Only material crossings are reported — a deal that stayed TRIPPED won't
produce a ``covenant_degrade`` event every week. That's the whole point
of a digest vs a re-dump of current state.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from ..pe.hold_tracking import variance_report
from .store import PortfolioStore
from .portfolio_snapshots import DEAL_STAGES, list_snapshots


# Stage → index for directional comparison. Higher = later in funnel.
_STAGE_RANK = {s: i for i, s in enumerate(DEAL_STAGES)}


@dataclass
class DigestEvent:
    """One material change observed in the review window."""
    deal_id: str
    change_type: str
    from_state: Optional[str]
    to_state: Optional[str]
    detail: str
    timestamp: str


def _parse_since(since: Optional[str]) -> datetime:
    """Parse ``since`` as ISO date/datetime; default to 7 days back."""
    if since is None:
        return datetime.now(timezone.utc) - timedelta(days=7)
    # Accept either 2026-04-15 or 2026-04-15T12:34:56+00:00
    try:
        dt = datetime.fromisoformat(since)
    except ValueError as exc:
        raise ValueError(f"Invalid --since value {since!r}: {exc}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _latest_before(snapshots: pd.DataFrame, cutoff: datetime) -> Optional[pd.Series]:
    """Newest snapshot strictly before ``cutoff``. None if none exist."""
    if snapshots.empty:
        return None
    cutoff_iso = cutoff.isoformat()
    before = snapshots[snapshots["created_at"] < cutoff_iso]
    if before.empty:
        return None
    return before.sort_values("created_at", ascending=False).iloc[0]


def _latest_in_or_after(snapshots: pd.DataFrame, cutoff: datetime) -> Optional[pd.Series]:
    """Newest snapshot at or after ``cutoff``. None if none exist."""
    if snapshots.empty:
        return None
    cutoff_iso = cutoff.isoformat()
    after = snapshots[snapshots["created_at"] >= cutoff_iso]
    if after.empty:
        return None
    return after.sort_values("created_at", ascending=False).iloc[0]


def _covenant_severity_rank(status: Optional[str]) -> int:
    """Higher rank = worse covenant state."""
    return {"SAFE": 0, "TIGHT": 1, "TRIPPED": 2}.get(str(status or ""), -1)


def _variance_severity_rank(severity: Optional[str]) -> int:
    """Higher rank = worse variance state."""
    return {"on_track": 0, "no_plan": 0, "lagging": 1, "off_track": 2}.get(
        str(severity or ""), -1,
    )


# ── Core digest logic ──────────────────────────────────────────────────────

def build_digest(
    store: PortfolioStore,
    since: Optional[str] = None,
) -> List[DigestEvent]:
    """Compute material portfolio changes since ``since`` (ISO date).

    Returns a flat list of DigestEvents, newest first. An analyst-friendly
    dataframe form is available via :func:`digest_to_frame`.
    """
    cutoff = _parse_since(since)
    all_snapshots = list_snapshots(store)  # newest first
    events: List[DigestEvent] = []

    if all_snapshots.empty:
        return events

    deal_ids = all_snapshots["deal_id"].unique()
    for did in deal_ids:
        per_deal = all_snapshots[all_snapshots["deal_id"] == did]
        before = _latest_before(per_deal, cutoff)
        after = _latest_in_or_after(per_deal, cutoff)

        # ── New deal: no snapshot existed before cutoff ──
        if before is None and after is not None:
            events.append(DigestEvent(
                deal_id=did,
                change_type="new_deal",
                from_state=None,
                to_state=str(after["stage"]),
                detail=f"New deal entered portfolio at stage {after['stage']}",
                timestamp=str(after["created_at"]),
            ))
            # Still compute covenant / variance change for this deal below
            # (a new deal at TRIPPED is also a warning)
            if after.get("covenant_status") == "TRIPPED":
                events.append(DigestEvent(
                    deal_id=did,
                    change_type="covenant_degrade",
                    from_state=None,
                    to_state="TRIPPED",
                    detail="Initial snapshot already TRIPPED",
                    timestamp=str(after["created_at"]),
                ))
            continue

        # No snapshot after cutoff — nothing changed in the window
        if after is None:
            continue

        # ── Stage change ──
        before_stage = str(before["stage"])
        after_stage = str(after["stage"])
        if before_stage != after_stage:
            b_rank = _STAGE_RANK.get(before_stage, -1)
            a_rank = _STAGE_RANK.get(after_stage, -1)
            change_type = "stage_advance" if a_rank > b_rank else "stage_regress"
            events.append(DigestEvent(
                deal_id=did, change_type=change_type,
                from_state=before_stage, to_state=after_stage,
                detail=f"{before_stage} → {after_stage}",
                timestamp=str(after["created_at"]),
            ))

        # ── Covenant change ──
        before_cov = before.get("covenant_status")
        after_cov = after.get("covenant_status")
        b_sev = _covenant_severity_rank(before_cov)
        a_sev = _covenant_severity_rank(after_cov)
        # Only emit when both states are known AND severity crossed
        if b_sev >= 0 and a_sev >= 0 and b_sev != a_sev:
            change_type = ("covenant_degrade" if a_sev > b_sev
                           else "covenant_recover")
            events.append(DigestEvent(
                deal_id=did, change_type=change_type,
                from_state=str(before_cov),
                to_state=str(after_cov),
                detail=f"Covenant {before_cov} → {after_cov}",
                timestamp=str(after["created_at"]),
            ))

        # ── Variance severity change (EBITDA, quarterly actuals) ──
        var_df = variance_report(store, did)
        if not var_df.empty and "ebitda" in var_df["kpi"].values:
            ebitda_hist = var_df[var_df["kpi"] == "ebitda"].sort_values("quarter")
            # Find quarters straddling the cutoff
            recent = ebitda_hist[ebitda_hist["quarter"] >= _quarter_from_date(cutoff)]
            prior = ebitda_hist[ebitda_hist["quarter"] < _quarter_from_date(cutoff)]
            if not recent.empty and not prior.empty:
                before_sev = str(prior.iloc[-1]["severity"])
                after_sev = str(recent.iloc[-1]["severity"])
                b_rank = _variance_severity_rank(before_sev)
                a_rank = _variance_severity_rank(after_sev)
                if b_rank != a_rank and b_rank >= 0 and a_rank >= 0:
                    change_type = ("variance_worse" if a_rank > b_rank
                                   else "variance_better")
                    events.append(DigestEvent(
                        deal_id=did, change_type=change_type,
                        from_state=before_sev, to_state=after_sev,
                        detail=f"EBITDA variance {before_sev} → {after_sev} "
                               f"(Q {recent.iloc[-1]['quarter']})",
                        timestamp=str(recent.iloc[-1]["quarter"]),
                    ))

    # Sort newest first for the partner's natural reading order
    events.sort(key=lambda e: e.timestamp, reverse=True)
    return events


def _quarter_from_date(dt: datetime) -> str:
    """Return 'YYYYQn' that contains ``dt``."""
    q = (dt.month - 1) // 3 + 1
    return f"{dt.year}Q{q}"


def digest_to_frame(events: List[DigestEvent]) -> pd.DataFrame:
    """DataFrame form of the event list — handy for JSON output or further analysis."""
    if not events:
        return pd.DataFrame(columns=[
            "deal_id", "change_type", "from_state", "to_state",
            "detail", "timestamp",
        ])
    return pd.DataFrame([
        {
            "deal_id": e.deal_id,
            "change_type": e.change_type,
            "from_state": e.from_state,
            "to_state": e.to_state,
            "detail": e.detail,
            "timestamp": e.timestamp,
        }
        for e in events
    ])


# ── Terminal formatter ─────────────────────────────────────────────────────

_EVENT_GLYPH = {
    "new_deal":         "●",
    "stage_advance":    "↑",
    "stage_regress":    "↓",
    "covenant_degrade": "⚠",
    "covenant_recover": "✓",
    "variance_worse":   "⚠",
    "variance_better":  "✓",
}

_EVENT_SEVERITY = {
    "new_deal":         "info",
    "stage_advance":    "positive",
    "stage_regress":    "warning",
    "covenant_degrade": "alert",
    "covenant_recover": "positive",
    "variance_worse":   "alert",
    "variance_better":  "positive",
}


def format_digest(events: List[DigestEvent], since: Optional[str] = None) -> str:
    """Terminal block grouped by severity bucket — alerts first."""
    cutoff = _parse_since(since)
    header = f"Portfolio digest — since {cutoff.date().isoformat()}"
    if not events:
        return f"{header}\n" + "─" * 50 + "\n  No material changes in the window."

    # Group by severity for partner readability — alerts at the top
    buckets: Dict[str, List[DigestEvent]] = {"alert": [], "warning": [], "positive": [], "info": []}
    for e in events:
        sev = _EVENT_SEVERITY.get(e.change_type, "info")
        buckets[sev].append(e)

    lines = [header, "─" * 50]
    bucket_labels = {
        "alert":    "Alerts",
        "warning":  "Warnings",
        "positive": "Positive changes",
        "info":     "Informational",
    }
    for sev in ("alert", "warning", "positive", "info"):
        bucket = buckets[sev]
        if not bucket:
            continue
        lines.append(f"\n  {bucket_labels[sev]}:")
        for e in bucket:
            glyph = _EVENT_GLYPH.get(e.change_type, "·")
            lines.append(f"    {glyph} {e.deal_id:<20s}  {e.detail}")

    # Summary counts at the bottom — partners like headline numbers
    counts = {k: len(v) for k, v in buckets.items() if v}
    if counts:
        lines.append("")
        lines.append(
            "  Summary: "
            + " · ".join(f"{v} {bucket_labels[k].lower()}" for k, v in counts.items())
        )
    return "\n".join(lines)
