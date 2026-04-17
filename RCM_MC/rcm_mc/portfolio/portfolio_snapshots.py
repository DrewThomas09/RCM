"""Portfolio-level deal snapshots (Brick 49).

A PE firm holds 5-30 platforms simultaneously. Each platform needs a
frozen snapshot at key milestones (IOI, LOI, SPA, close, quarterly
re-mark) so the firm can answer:

- What's the portfolio IRR / MOIC today?
- Which deals have tripped covenants or are close to tripping?
- Which deals are the outliers (best / worst case)?
- Where are we in the funnel — how many sourced vs closed?

This module extends :class:`rcm_mc.portfolio.store.PortfolioStore` with a
``deal_snapshots`` table. Each snapshot captures the PE math artifacts
(bridge + returns + covenant) plus the trend-signal watchlist count at
a given moment for a given deal, with an explicit ``stage``.

Snapshots are append-only — the audit trail from IOI through exit is the
point. ``latest_per_deal()`` aggregates to the current state.
"""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .store import PortfolioStore


# ── Stages (ordered sourced → hold → exit) ──
# These are the canonical PE deal-flow milestones. Keeping them in a
# tuple (vs a free-form string) enforces a funnel we can roll up on.
DEAL_STAGES: tuple = (
    "sourced",   # in the pipeline, no formal IOI yet
    "ioi",       # indication of interest submitted
    "loi",       # letter of intent signed, exclusivity
    "spa",       # sale-purchase agreement in negotiation
    "closed",    # deal closed, hold period begins
    "hold",      # active hold, quarterly re-marks go here
    "exit",      # exited / realized
)


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Data types ──────────────────────────────────────────────────────────────

@dataclass
class DealSnapshot:
    """One point-in-time snapshot for a deal."""
    snapshot_id: int
    deal_id: str
    stage: str
    created_at: str
    run_dir: Optional[str]
    # PE math (from pe_bridge + pe_returns)
    entry_ebitda: Optional[float]
    entry_multiple: Optional[float]
    exit_multiple: Optional[float]
    hold_years: Optional[float]
    moic: Optional[float]
    irr: Optional[float]
    entry_ev: Optional[float]
    exit_ev: Optional[float]
    # Covenant status
    covenant_leverage: Optional[float]
    covenant_headroom_turns: Optional[float]
    covenant_status: Optional[str]   # SAFE / TIGHT / TRIPPED / None
    # Trend watchlist
    concerning_signals: Optional[int]
    favorable_signals: Optional[int]
    # Freeform
    notes: str


def _ensure_snapshot_table(store: PortfolioStore) -> None:
    """Create the deal_snapshots table if absent. Idempotent.

    Runs inside the existing store's connection wrapper so we inherit the
    safe-close semantics and the same DB file. Only CREATE TABLE here —
    schema migrations are a later brick (when we have users with data to
    migrate).
    """
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS deal_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                stage TEXT NOT NULL,
                created_at TEXT NOT NULL,
                run_dir TEXT,
                entry_ebitda REAL,
                entry_multiple REAL,
                exit_multiple REAL,
                hold_years REAL,
                moic REAL,
                irr REAL,
                entry_ev REAL,
                exit_ev REAL,
                covenant_leverage REAL,
                covenant_headroom_turns REAL,
                covenant_status TEXT,
                concerning_signals INTEGER,
                favorable_signals INTEGER,
                notes TEXT,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_snapshots_deal ON deal_snapshots(deal_id, created_at DESC)"
        )
        con.commit()


# ── Read PE artifacts from a run directory ─────────────────────────────────

def _read_pe_artifacts(run_dir: str) -> Dict[str, Any]:
    """Pull PE math + trend-signal snapshot fields from a run directory.

    All files are optional — a deal in ``sourced`` stage usually has no
    PE run yet. Missing values return None so the snapshot captures
    "what we knew at this point" faithfully.
    """
    fields: Dict[str, Any] = {
        "entry_ebitda": None, "entry_multiple": None, "exit_multiple": None,
        "hold_years": None, "moic": None, "irr": None,
        "entry_ev": None, "exit_ev": None,
        "covenant_leverage": None, "covenant_headroom_turns": None,
        "covenant_status": None,
        "concerning_signals": None, "favorable_signals": None,
    }
    if not run_dir or not os.path.isdir(run_dir):
        return fields

    bridge_path = os.path.join(run_dir, "pe_bridge.json")
    if os.path.isfile(bridge_path):
        try:
            with open(bridge_path, encoding="utf-8") as f:
                b = json.load(f)
            fields["entry_ebitda"] = b.get("entry_ebitda")
            fields["entry_multiple"] = b.get("entry_multiple")
            fields["exit_multiple"] = b.get("exit_multiple")
            fields["hold_years"] = b.get("hold_years")
            fields["entry_ev"] = b.get("entry_ev")
            fields["exit_ev"] = b.get("exit_ev")
        except (OSError, json.JSONDecodeError):
            pass

    returns_path = os.path.join(run_dir, "pe_returns.json")
    if os.path.isfile(returns_path):
        try:
            with open(returns_path, encoding="utf-8") as f:
                r = json.load(f)
            fields["moic"] = r.get("moic")
            fields["irr"] = r.get("irr")
        except (OSError, json.JSONDecodeError):
            pass

    covenant_path = os.path.join(run_dir, "pe_covenant.json")
    if os.path.isfile(covenant_path):
        try:
            with open(covenant_path, encoding="utf-8") as f:
                c = json.load(f)
            fields["covenant_leverage"] = c.get("actual_leverage")
            fields["covenant_headroom_turns"] = c.get("covenant_headroom_turns")
            h = c.get("covenant_headroom_turns")
            if h is not None:
                fields["covenant_status"] = (
                    "SAFE" if h >= 1.0 else ("TIGHT" if h >= 0 else "TRIPPED")
                )
        except (OSError, json.JSONDecodeError):
            pass

    signals_path = os.path.join(run_dir, "trend_signals.csv")
    if os.path.isfile(signals_path):
        try:
            df = pd.read_csv(signals_path)
            if "severity" in df.columns:
                fields["concerning_signals"] = int(
                    (df["severity"] == "concerning").sum()
                )
                fields["favorable_signals"] = int(
                    (df["severity"] == "favorable").sum()
                )
        except (OSError, pd.errors.ParserError, ValueError):
            pass

    return fields


# ── Public API ─────────────────────────────────────────────────────────────

def register_snapshot(
    store: PortfolioStore,
    deal_id: str,
    stage: str,
    run_dir: Optional[str] = None,
    notes: str = "",
) -> int:
    """Persist a snapshot for a deal at a given stage.

    Reads PE math + trend-signal artifacts from ``run_dir`` if provided.
    For early-stage entries (sourced, IOI), ``run_dir`` can be None —
    the snapshot still records stage + notes for funnel tracking.

    Returns the new ``snapshot_id``.
    """
    if stage not in DEAL_STAGES:
        raise ValueError(
            f"stage must be one of {DEAL_STAGES} (got {stage!r})"
        )
    _ensure_snapshot_table(store)
    store.upsert_deal(deal_id)
    fields = _read_pe_artifacts(run_dir) if run_dir else _read_pe_artifacts("")

    with store.connect() as con:
        cur = con.execute(
            """INSERT INTO deal_snapshots
            (deal_id, stage, created_at, run_dir,
             entry_ebitda, entry_multiple, exit_multiple, hold_years,
             moic, irr, entry_ev, exit_ev,
             covenant_leverage, covenant_headroom_turns, covenant_status,
             concerning_signals, favorable_signals, notes)
            VALUES (?,?,?,?, ?,?,?,?, ?,?,?,?, ?,?,?, ?,?, ?)""",
            (
                deal_id, stage, _utcnow(),
                run_dir if run_dir else None,
                fields["entry_ebitda"], fields["entry_multiple"],
                fields["exit_multiple"], fields["hold_years"],
                fields["moic"], fields["irr"],
                fields["entry_ev"], fields["exit_ev"],
                fields["covenant_leverage"], fields["covenant_headroom_turns"],
                fields["covenant_status"],
                fields["concerning_signals"], fields["favorable_signals"],
                notes,
            ),
        )
        con.commit()
        return int(cur.lastrowid)


def list_snapshots(
    store: PortfolioStore,
    deal_id: Optional[str] = None,
) -> pd.DataFrame:
    """Return all snapshots (optionally filtered to one deal), newest first."""
    _ensure_snapshot_table(store)
    with store.connect() as con:
        if deal_id:
            rows = con.execute(
                "SELECT * FROM deal_snapshots WHERE deal_id=? "
                "ORDER BY created_at DESC",
                (deal_id,),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM deal_snapshots ORDER BY created_at DESC"
            ).fetchall()
    return pd.DataFrame([dict(r) for r in rows])


def latest_per_deal(store: PortfolioStore) -> pd.DataFrame:
    """One row per deal — the most-recent snapshot. This is the
    portfolio-current-state view a partner reads for quarterly reviews.

    B156 fix: add ``snapshot_id`` as a secondary sort key. When two
    snapshots share an identical ``created_at`` (rare but possible on
    same-second inserts), ``drop_duplicates`` was order-dependent on
    upstream DataFrame iteration. Using the auto-incrementing PK as
    tiebreaker guarantees deterministic output across runs.
    """
    df = list_snapshots(store)
    if df.empty:
        return df
    sort_cols = ["created_at"]
    ascending = [False]
    if "snapshot_id" in df.columns:
        sort_cols.append("snapshot_id")
        ascending.append(False)
    return (
        df.sort_values(sort_cols, ascending=ascending)
          .drop_duplicates(subset=["deal_id"], keep="first")
          .reset_index(drop=True)
    )


def portfolio_rollup(store: PortfolioStore) -> Dict[str, Any]:
    """Aggregate the latest-per-deal view into a single summary dict.

    Used by the cross-portfolio dashboard (Brick 50). Returns:
        {
            "deal_count": int,
            "stage_funnel": {stage: count, ...},
            "weighted_moic": float or None,   # equity-weighted
            "weighted_irr": float or None,
            "covenant_trips": int,            # deals with TRIPPED covenant
            "covenant_tight": int,            # deals with TIGHT covenant
            "concerning_deals": int,          # deals with ≥1 concerning signal
        }
    """
    df = latest_per_deal(store)
    rollup: Dict[str, Any] = {
        "deal_count": int(len(df)),
        "stage_funnel": {},
        "weighted_moic": None,
        "weighted_irr": None,
        "covenant_trips": 0,
        "covenant_tight": 0,
        "concerning_deals": 0,
    }
    if df.empty:
        return rollup

    # Stage funnel — preserve canonical order, fill missing with 0
    stage_counts = df["stage"].value_counts().to_dict()
    rollup["stage_funnel"] = {s: int(stage_counts.get(s, 0)) for s in DEAL_STAGES}

    # Weighted MOIC / IRR — weight by entry_ev (proxy for deal size).
    # Equity-weighted would be more correct but requires entry_equity,
    # which isn't always stored. Use entry_ev as the best available
    # size proxy; skip deals with no EV recorded.
    #
    # B150 fix: aggregate in Decimal to avoid float-summation drift
    # that compounds with portfolio size. 50 deals × 5 years of
    # quarterly recomputes would visibly shift the last basis points.
    from decimal import Decimal as _D
    sized = df.dropna(subset=["moic", "irr", "entry_ev"])
    if not sized.empty:
        weights_f = sized["entry_ev"].astype(float).tolist()
        moic_f = sized["moic"].astype(float).tolist()
        irr_f = sized["irr"].astype(float).tolist()
        total_w = sum(_D(str(w)) for w in weights_f)
        if total_w > 0:
            wm = sum(_D(str(m)) * _D(str(w))
                     for m, w in zip(moic_f, weights_f)) / total_w
            wi = sum(_D(str(r)) * _D(str(w))
                     for r, w in zip(irr_f, weights_f)) / total_w
            rollup["weighted_moic"] = float(wm)
            rollup["weighted_irr"] = float(wi)

    # Covenant status counts
    rollup["covenant_trips"] = int((df["covenant_status"] == "TRIPPED").sum())
    rollup["covenant_tight"] = int((df["covenant_status"] == "TIGHT").sum())

    # Concerning-signal count
    concerning = df["concerning_signals"].fillna(0).astype(int)
    rollup["concerning_deals"] = int((concerning >= 1).sum())

    return rollup


def format_rollup(rollup: Dict[str, Any]) -> str:
    """Terminal-friendly portfolio summary block."""
    def _pct_or_dash(v):
        return "—" if v is None else f"{v*100:.1f}%"

    def _x_or_dash(v):
        return "—" if v is None else f"{v:.2f}x"

    funnel = rollup.get("stage_funnel") or {}
    funnel_line = " · ".join(
        f"{stage}: {funnel.get(stage, 0)}" for stage in DEAL_STAGES
        if funnel.get(stage, 0) > 0
    )
    if not funnel_line:
        funnel_line = "(no deals)"

    lines = [
        f"Portfolio roll-up — {rollup['deal_count']} deals",
        "─" * 60,
        f"  Stage funnel:    {funnel_line}",
        f"  Weighted MOIC:   {_x_or_dash(rollup['weighted_moic'])}",
        f"  Weighted IRR:    {_pct_or_dash(rollup['weighted_irr'])}",
        f"  Covenant trips:  {rollup['covenant_trips']}",
        f"  Covenant tight:  {rollup['covenant_tight']}",
        f"  With concerning: {rollup['concerning_deals']}",
    ]
    return "\n".join(lines)
