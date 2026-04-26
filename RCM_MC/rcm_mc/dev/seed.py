"""Demo database seeder — populate a SQLite DB so the v3 dashboard renders.

Per ``docs/design-handoff/SEEDER_PROPOSAL.md`` (commit ``e27c5de``) and
``docs/DEMO_CHECKLIST.md``: the editorial dashboard at ``/app?ui=v3``
renders empty-state across every block when the DB has no data. That's
correct behaviour, but unusable for a partner walkthrough. This module
populates a clean DB with 7 curated fictional hospital systems so every
block on the dashboard demonstrates real analytical work.

Public API:
    seed_demo_db(db_path, *, deal_count=7, snapshot_quarters=8,
                 seed_random=20260425, overwrite=False,
                 write_export_files=True, base_dir=None) -> SeedResult

CLI:
    python -m rcm_mc.dev.seed --db /tmp/demo.db
    python -m rcm_mc.dev.seed --db /tmp/demo.db --overwrite --deal-count 10
    python -m rcm_mc.dev.seed --db /tmp/demo.db --no-export-files
    python -m rcm_mc.dev.seed --db /tmp/demo.db --verify

The seeder refuses to run against a path that looks like production
(`/data/...` or filenames matching `seekingchartis.db`) unless
``force=True`` is passed. This is the "I meant /tmp/demo.db but typed
seekingchartis.db" guard.

Determinism: same ``seed_random`` produces byte-for-byte identical
data — same deal names, same EBITDA values, same covenant trajectories.
The default ``20260425`` is the date this seeder was authored.

Honesty: the seeder runs the real ``get_or_build_packet()`` pipeline for
focused-candidate deals so the EBITDA-drag block renders against actual
bridge math, not a hand-crafted fake. ~10-30 sec one-time cost; this is
the operator's tax for not inventing numbers.

Q1-Q6 decisions resolved per SEEDER_PROPOSAL.md (Andrew, 2026-04-26):
  C1 — base dir defaults to tempfile.gettempdir() / rcm_mc_demo_exports
  C2 — run real packet builder synchronously
  C3 — deal_count keeps first N curated deals; >7 extends with extra_NNN
  C4 — --verify flag included from first commit
  C5 — both unit and integration tests in separate commits
  C6 — function name seed_demo_db()
"""
from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


# ── Curated demo deals ──────────────────────────────────────────────
#
# Per SEEDER_PROPOSAL.md §4.1 — fictional hospital systems with
# plausible PE-portfolio shapes. Names verified non-trademarked at
# authoring time; if conflicts surface, swap.
#
# Each entry: (deal_id, display name, terminal stage, vintage_year)
# The snapshot trajectory per deal is in _COVENANT_TRAJECTORY below.

_CURATED_DEALS: List[Tuple[str, str, str, int]] = [
    ("ccf_2026", "Cypress Crossing Health",          "hold", 2026),
    ("arr_2025", "Arrowhead Regional",                "hold", 2025),
    ("pma_2024", "Peninsula Medical Associates",      "hold", 2024),
    ("tlc_2023", "Tidewater Long-term Care",          "exit", 2023),
    ("nbh_2026", "Northbay Heart",                    "spa",  2026),
    ("mvm_2026", "Mountainview Medical",              "loi",  2026),
    ("evh_2026", "Evergreen Health",                  "ioi",  2026),
]


# Covenant leverage trajectories per held deal (latest quarter last).
# Numbers chosen to demonstrate distinct visual outcomes on the
# editorial covenant heatmap: ccf drifts safe→watch, arr trips,
# pma deleverages cleanly, tlc held flat then exited.

_COVENANT_TRAJECTORY: Dict[str, List[float]] = {
    # 8 quarters: drifts from safe (≤6.0) into watch (≤6.5) — common
    # demo line: "the thesis is intact but warrants attention"
    "ccf_2026": [5.2, 5.4, 5.6, 5.8, 5.9, 6.0, 6.1, 6.2],
    # 8 quarters: trips covenant in latest (>6.5) — fires alerts
    "arr_2025": [5.8, 5.9, 6.0, 6.2, 6.4, 6.6, 6.8, 7.0],
    # 8 quarters: deleveraging — strong story
    "pma_2024": [5.0, 4.9, 4.8, 4.7, 4.6, 4.5, 4.4, 4.3],
    # 4 quarters at 4.5 then exited
    "tlc_2023": [4.5, 4.5, 4.5, 4.5],
}

# Per-deal entry economics (also drive the KPI strip + deals table)
_DEAL_ECONOMICS: Dict[str, Dict[str, float]] = {
    "ccf_2026": {
        "entry_ebitda": 18.5, "entry_multiple": 11.0, "exit_multiple": 12.5,
        "hold_years": 5.0, "moic": 2.4, "irr": 0.19,
        "entry_ev": 203.5, "exit_ev": 425.0,
    },
    "arr_2025": {
        "entry_ebitda": 24.0, "entry_multiple": 10.0, "exit_multiple": 9.5,
        "hold_years": 5.0, "moic": 1.6, "irr": 0.10,
        "entry_ev": 240.0, "exit_ev": 312.0,
    },
    "pma_2024": {
        "entry_ebitda": 14.0, "entry_multiple": 9.5, "exit_multiple": 13.0,
        "hold_years": 5.0, "moic": 3.1, "irr": 0.25,
        "entry_ev": 133.0, "exit_ev": 364.0,
    },
    "tlc_2023": {
        "entry_ebitda": 9.0, "entry_multiple": 8.5, "exit_multiple": 10.0,
        "hold_years": 4.0, "moic": 2.0, "irr": 0.18,
        "entry_ev": 76.5, "exit_ev": 167.0,
    },
}


# ── Production-target guard ─────────────────────────────────────────

class SeederRefuseError(RuntimeError):
    """Raised when the seeder declines to run against a target.

    Reasons:
      - db_path looks like a production location (`/data/...` or
        `seekingchartis.db`) and force=False
      - db_path exists with non-empty deals table and overwrite=False
    """


_PROD_HINTS = ("/data/", "seekingchartis.db")


def _guard_against_production(db_path: Path, *, force: bool) -> None:
    """Refuse to seed if the target path looks like a production DB.

    Soft heuristic — operator can override with ``force=True`` (or the
    ``--force-prod-path`` CLI flag). The default refusal eliminates the
    "I meant /tmp/demo.db but typed seekingchartis.db" failure mode.
    """
    if force:
        return
    resolved = str(db_path.resolve())
    if any(hint in resolved for hint in _PROD_HINTS):
        raise SeederRefuseError(
            f"db_path {resolved!r} looks like a production target. "
            f"Pass force=True (or --force-prod-path on the CLI) to override. "
            f"Recognized production hints: {_PROD_HINTS}"
        )


# ── Result + counters ───────────────────────────────────────────────

@dataclass
class SeedResult:
    """Counts of what landed in the seeded DB.

    Returned from seed_demo_db() so callers (and the verify path) can
    sanity-check the result. All counts default to 0; sections that
    aren't seeded leave their counter at 0.
    """
    deals_inserted: int = 0
    snapshots_inserted: int = 0
    stage_transitions_inserted: int = 0
    actuals_inserted: int = 0
    packets_built: int = 0
    exports_inserted: int = 0
    export_files_written: int = 0
    deals_skipped: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def summary(self) -> str:
        """One-line summary for CLI output."""
        return (
            f"deals={self.deals_inserted} snapshots={self.snapshots_inserted} "
            f"stages={self.stage_transitions_inserted} "
            f"actuals={self.actuals_inserted} packets={self.packets_built} "
            f"exports={self.exports_inserted} files={self.export_files_written} "
            f"in {self.duration_seconds:.1f}s"
        )


# ── Deals + snapshots seeders ───────────────────────────────────────

# Reference time anchors for deterministic timestamps. All snapshots
# count BACKWARDS from the reference quarter so the latest snapshot
# is the most recent — matches what `latest_per_deal()` expects.
_REF_DATETIME = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)


def _quarter_offset_dt(quarters_back: int) -> datetime:
    """Return a deterministic datetime ``quarters_back`` quarters before
    the reference. 0 = same quarter as reference, 1 = previous, etc."""
    days = int(quarters_back * 91.25)
    return _REF_DATETIME - timedelta(days=days)


def _seed_deals_and_snapshots(
    store: Any,
    *,
    deal_count: int,
    snapshot_quarters: int,
    overwrite: bool,
    result: SeedResult,
) -> None:
    """Insert curated deals + lifecycle stage history + per-quarter
    snapshots. Updates ``result`` in place.

    Held deals (``ccf_2026``, ``arr_2025``, ``pma_2024``) get
    ``snapshot_quarters`` snapshots each at stage='hold' with
    covenant_leverage following ``_COVENANT_TRAJECTORY``.

    Exit deal (``tlc_2023``) gets 4 hold snapshots then 1 exit
    snapshot (so the deals table shows it as exited).

    Pre-hold deals (spa/loi/ioi) get a single snapshot at their
    respective stage with no covenant data — they don't have one
    yet pre-close.
    """
    from rcm_mc.portfolio.portfolio_snapshots import _ensure_snapshot_table
    from rcm_mc.deals.deal_stages import _ensure_table as _ensure_stage_table

    _ensure_snapshot_table(store)
    _ensure_stage_table(store)

    # Optional clean slate when overwrite=True. Only clears the seeded
    # tables; user data in other tables (auth, audit_log, etc.) survives.
    if overwrite:
        with store.connect() as con:
            for table in (
                "deal_snapshots", "deal_stage_history",
                "initiative_actuals", "generated_exports",
                "analysis_runs", "deals",
            ):
                try:
                    con.execute(f"DELETE FROM {table}")
                except Exception:  # noqa: BLE001 — table may not exist yet
                    pass
            con.commit()

    deals_to_seed = _CURATED_DEALS[:deal_count]
    # Extension beyond the 7 curated entries: auto-named tail at sourced.
    if deal_count > len(_CURATED_DEALS):
        for i in range(deal_count - len(_CURATED_DEALS)):
            extra_id = f"extra_{i+1:03d}"
            deals_to_seed.append(
                (extra_id, f"Extra Deal {i+1:03d}", "sourced", 2026)
            )

    for deal_id, name, terminal_stage, _vintage_year in deals_to_seed:
        # 1. deals row (via store.upsert_deal)
        store.upsert_deal(deal_id, name=name)
        result.deals_inserted += 1

        # 2. deal_stage_history rows — each transition that led to the
        #    terminal stage. Uses raw INSERT to control timestamps;
        #    set_stage()'s validate_transition forces sequencing that
        #    we can encode directly.
        _seed_stage_history(store, deal_id, terminal_stage, result)

        # 3. deal_snapshots rows — varies by terminal stage.
        if terminal_stage == "hold" and deal_id in _COVENANT_TRAJECTORY:
            traj = _COVENANT_TRAJECTORY[deal_id]
            n_quarters = min(snapshot_quarters, len(traj))
            for q in range(n_quarters):
                quarters_back = (n_quarters - 1) - q
                created = _quarter_offset_dt(quarters_back)
                cov_lev = traj[q]
                _insert_snapshot(
                    store, deal_id, "hold", created, cov_lev,
                    economics=_DEAL_ECONOMICS.get(deal_id),
                    result=result,
                )
        elif terminal_stage == "exit" and deal_id in _COVENANT_TRAJECTORY:
            traj = _COVENANT_TRAJECTORY[deal_id]
            for q, cov_lev in enumerate(traj):
                quarters_back = len(traj) - q
                created = _quarter_offset_dt(quarters_back)
                _insert_snapshot(
                    store, deal_id, "hold", created, cov_lev,
                    economics=_DEAL_ECONOMICS.get(deal_id),
                    result=result,
                )
            # Final exit snapshot at reference - 1 day
            _insert_snapshot(
                store, deal_id, "exit", _REF_DATETIME - timedelta(days=1),
                None, economics=_DEAL_ECONOMICS.get(deal_id),
                result=result,
            )
        else:
            # Pre-hold deals (spa/loi/ioi/sourced): single snapshot
            _insert_snapshot(
                store, deal_id, terminal_stage,
                _REF_DATETIME - timedelta(days=14),
                None, economics=None, result=result,
            )


def _seed_stage_history(
    store: Any, deal_id: str, terminal_stage: str, result: SeedResult,
) -> None:
    """Insert a plausible stage-transition history landing at terminal_stage.

    Uses raw INSERT (not set_stage()) because we want deterministic
    timestamps and don't need automation-engine event firing.
    """
    # Stage path per terminal — chronologically ordered, oldest first.
    # The dashboard funnel reads `latest_per_deal.stage` (from
    # deal_snapshots, not deal_stage_history) — this table is for
    # the audit trail / per-deal lifecycle ribbon.
    stage_paths: Dict[str, List[str]] = {
        "ioi":     ["pipeline"],
        "loi":     ["pipeline", "diligence"],
        "spa":     ["pipeline", "diligence", "ic"],
        "hold":    ["pipeline", "diligence", "ic", "hold"],
        "exit":    ["pipeline", "diligence", "ic", "hold", "exit"],
        "sourced": [],
        "closed":  ["pipeline", "diligence", "ic", "hold", "closed"],
    }
    path = stage_paths.get(terminal_stage, [])
    if not path:
        return
    n = len(path)
    with store.connect() as con:
        for i, stg in enumerate(path):
            # Spread transitions evenly: oldest at year-2, newest at
            # year-0 (relative to reference)
            quarters_back = (n - i) * 4
            ts = _quarter_offset_dt(quarters_back)
            con.execute(
                "INSERT INTO deal_stage_history "
                "(deal_id, stage, changed_at, changed_by, notes) "
                "VALUES (?,?,?,?,?)",
                (deal_id, stg, ts.isoformat(), "seed", "seed:demo"),
            )
            result.stage_transitions_inserted += 1
        con.commit()


def _insert_snapshot(
    store: Any, deal_id: str, stage: str, created: datetime,
    covenant_leverage: Optional[float],
    *, economics: Optional[Dict[str, float]],
    result: SeedResult,
) -> None:
    """Direct INSERT into deal_snapshots — bypasses register_snapshot()
    so we control the created_at timestamp deterministically and don't
    need to spin up fake run_dirs."""
    econ = economics or {}
    cov_status: Optional[str] = None
    cov_headroom: Optional[float] = None
    if covenant_leverage is not None:
        # Translate leverage → headroom + status using the same bands
        # as the editorial covenant heatmap (Phase 3 commit 7):
        # ≤6.0x safe / ≤6.5x watch / >6.5x trip
        threshold = 6.5
        cov_headroom = round(threshold - covenant_leverage, 2)
        if covenant_leverage <= 6.0:
            cov_status = "SAFE"
        elif covenant_leverage <= 6.5:
            cov_status = "TIGHT"
        else:
            cov_status = "TRIPPED"
    with store.connect() as con:
        con.execute(
            """INSERT INTO deal_snapshots
            (deal_id, stage, created_at, run_dir,
             entry_ebitda, entry_multiple, exit_multiple, hold_years,
             moic, irr, entry_ev, exit_ev,
             covenant_leverage, covenant_headroom_turns, covenant_status,
             concerning_signals, favorable_signals, notes)
            VALUES (?,?,?,?, ?,?,?,?, ?,?,?,?, ?,?,?, ?,?, ?)""",
            (
                deal_id, stage, created.isoformat(), None,
                econ.get("entry_ebitda"), econ.get("entry_multiple"),
                econ.get("exit_multiple"), econ.get("hold_years"),
                econ.get("moic"), econ.get("irr"),
                econ.get("entry_ev"), econ.get("exit_ev"),
                covenant_leverage, cov_headroom, cov_status,
                None, None, "seed:demo",
            ),
        )
        con.commit()
        result.snapshots_inserted += 1


# ── Covenant metrics seeder (Q4.5) ──────────────────────────────────

# Per-deal covenant trajectories for the 6 spec covenants. Each held
# deal gets 8 quarters of data so the heatmap reads left-to-right
# in time order. Curated to demonstrate distinct visual outcomes:
#   ccf_2026: drifts safe → watch on multiple covenants
#   arr_2025: trips Net Leverage, hot on most others
#   pma_2024: deleveraging, healthy across the board
#
# Trajectories are 8-quarter lists. None entries are gaps (rendered
# empty). Direction-aware: "max" covenants degrade upward (Net
# Leverage rising is bad); "min" degrade downward (Interest Coverage
# falling is bad).

_COVENANT_TRAJECTORIES = {
    "ccf_2026": {
        "Net Leverage":      [5.2, 5.4, 5.6, 5.8, 5.9, 6.0, 6.1, 6.2],
        "Interest Coverage": [3.2, 3.1, 3.0, 2.9, 2.8, 2.8, 2.7, 2.6],
        "Days Cash on Hand": [110, 105, 98, 92, 88, 85, 82, 80],
        "EBITDA / Plan":     [1.05, 1.02, 0.99, 0.97, 0.95, 0.94, 0.93, 0.92],
        "Denial Rate":       [0.058, 0.060, 0.062, 0.065, 0.067, 0.070, 0.072, 0.075],
        "Days in A/R":       [38, 40, 41, 42, 43, 44, 44, 45],
    },
    "arr_2025": {
        "Net Leverage":      [5.8, 5.9, 6.0, 6.2, 6.4, 6.6, 6.8, 7.0],
        "Interest Coverage": [2.8, 2.6, 2.4, 2.2, 2.1, 2.0, 1.9, 1.8],
        "Days Cash on Hand": [85, 80, 76, 72, 68, 65, 62, 58],
        "EBITDA / Plan":     [0.98, 0.95, 0.93, 0.91, 0.89, 0.87, 0.86, 0.85],
        "Denial Rate":       [0.072, 0.075, 0.078, 0.082, 0.085, 0.088, 0.092, 0.095],
        "Days in A/R":       [44, 45, 47, 48, 50, 51, 53, 54],
    },
    "pma_2024": {
        "Net Leverage":      [5.0, 4.9, 4.8, 4.7, 4.6, 4.5, 4.4, 4.3],
        "Interest Coverage": [3.5, 3.6, 3.7, 3.8, 3.9, 4.0, 4.1, 4.2],
        "Days Cash on Hand": [120, 122, 125, 127, 130, 132, 135, 138],
        "EBITDA / Plan":     [1.02, 1.04, 1.05, 1.07, 1.08, 1.10, 1.11, 1.12],
        "Denial Rate":       [0.048, 0.046, 0.045, 0.044, 0.043, 0.042, 0.041, 0.040],
        "Days in A/R":       [35, 34, 34, 33, 33, 32, 32, 31],
    },
    "tlc_2023": {
        # 4-quarter pre-exit trajectory (deal exited mid-cycle)
        "Net Leverage":      [4.5, 4.5, 4.5, 4.5],
        "Interest Coverage": [3.0, 3.0, 3.0, 3.0],
        "Days Cash on Hand": [100, 100, 100, 100],
        "EBITDA / Plan":     [1.00, 1.00, 1.00, 1.00],
        "Denial Rate":       [0.060, 0.060, 0.060, 0.060],
        "Days in A/R":       [42, 42, 42, 42],
    },
}


def _seed_covenant_metrics(store: Any, *, result: SeedResult) -> None:
    """Insert curated covenant_metrics rows for held + exit deals.

    Q4.5 schema expansion: populates all 6 spec covenants per deal
    using SPEC_COVENANT_DEFAULTS thresholds. Each deal gets 8 trailing
    quarters' worth (4 for the exit deal). Timestamps are deterministic
    via _quarter_offset_dt, matching the snapshot-trajectory anchoring.
    """
    from rcm_mc.portfolio.covenant_metrics import (
        SPEC_COVENANT_DEFAULTS, record_covenant_metric,
    )

    inserted = 0
    for deal_id, by_covenant in _COVENANT_TRAJECTORIES.items():
        for covenant_name, values in by_covenant.items():
            spec = SPEC_COVENANT_DEFAULTS[covenant_name]
            n = len(values)
            for i, v in enumerate(values):
                # Oldest first → newest last; same direction as
                # the snapshot trajectory anchoring.
                quarters_back = (n - 1) - i
                ts = _quarter_offset_dt(quarters_back).isoformat()
                record_covenant_metric(
                    store,
                    deal_id=deal_id,
                    covenant_name=covenant_name,
                    value=v,
                    threshold=spec["threshold"],
                    direction=spec["direction"],
                    watch_threshold=spec["watch"],
                    created_at=ts,
                    notes="seed:demo",
                )
                inserted += 1
    # Track in result via the existing snapshots_inserted-adjacent
    # surface; future SeedResult versions can add a covenant_metrics
    # field. For now, log via stage_transitions_inserted to keep
    # the SeedResult shape stable.
    # (No counter mutation — covenants are derived from snapshots
    # conceptually, and test assertions check the data shape, not
    # the counter.)


# ── Initiative actuals seeder (block 7) ─────────────────────────────

# Per SEEDER_PROPOSAL §4.5 — 3 initiatives across the 3 held deals,
# curated to demonstrate distinct outcomes on the editorial initiative-
# tracker block:
#
#   prior_auth_improvement → ALL 3 held deals, all behind ≥-15%
#       → fires the PLAYBOOK GAP pill (mean ≤ -10% AND n_deals ≥ 2)
#   coding_cdi_improvement → ccf_2026 only, behind -20%
#       → demonstrates "single-deal behind" vs playbook gap distinction
#   denial_workflow_automation → pma_2024 only, ahead +12%
#       → demonstrates the ahead/healthy state in the variance dot-plot
#
# Each initiative is recorded for 4 trailing quarters so the cross-
# portfolio aggregator (cross_portfolio_initiative_variance, default
# trailing_quarters=4) picks them up. Variance is computed against the
# initiatives library's annual_run_rate via initiative_variance_report.

# (initiative_id, deal_id, variance_pct_of_plan)
# Variance is what the actual achieves vs plan. -0.5 = 50% behind.
_INITIATIVE_SEEDS: List[Tuple[str, str, float]] = [
    # prior_auth_improvement: behind on all 3 held deals (PLAYBOOK GAP)
    ("prior_auth_improvement", "ccf_2026", -0.50),
    ("prior_auth_improvement", "arr_2025", -0.40),
    ("prior_auth_improvement", "pma_2024", -0.30),
    # coding_cdi_improvement: behind on 1 deal (single-deal-behind)
    ("coding_cdi_improvement", "ccf_2026", -0.20),
    # denial_workflow_automation: ahead on 1 deal (healthy)
    ("denial_workflow_automation", "pma_2024", 0.12),
]


def _seed_initiative_actuals(
    store: Any, *, result: SeedResult,
) -> None:
    """Insert curated initiative_actuals rows that produce a clear
    cross-portfolio playbook-gap signal in the editorial dashboard.

    Records 4 trailing quarters per (initiative, deal) pair so the
    aggregator's default trailing_quarters=4 window picks them up. The
    per-quarter ebitda_impact is plan/4 * (1 + variance_pct), so a
    -0.50 variance produces 50% of plan per quarter.
    """
    from rcm_mc.rcm.initiative_tracking import record_initiative_actual
    from rcm_mc.rcm.initiatives import get_all_initiatives

    plans_by_id = {
        init["id"]: float(init.get("annual_run_rate", 0) or 0)
        for init in get_all_initiatives()
    }

    # Compute the 4 trailing quarter labels relative to reference time.
    # Q labels are the format that record_initiative_actual validates
    # against ('YYYYQn').
    quarters: List[str] = []
    for q_back in range(4):
        dt = _quarter_offset_dt(q_back)
        q_num = (dt.month - 1) // 3 + 1
        quarters.append(f"{dt.year}Q{q_num}")
    # Order chronologically (oldest first)
    quarters.reverse()

    for init_id, deal_id, variance_pct in _INITIATIVE_SEEDS:
        plan_annual = plans_by_id.get(init_id, 0)
        if plan_annual <= 0:
            # Initiative library entry doesn't have a dollar run-rate;
            # variance computation needs it. Skip silently.
            continue
        per_quarter_plan = plan_annual / 4
        per_quarter_actual = per_quarter_plan * (1 + variance_pct)
        for quarter in quarters:
            record_initiative_actual(
                store,
                deal_id=deal_id,
                initiative_id=init_id,
                quarter=quarter,
                ebitda_impact=per_quarter_actual,
                notes="seed:demo",
            )
            result.actuals_inserted += 1


# ── Packet builder seeder (block 6 — EBITDA drag) ───────────────────

# Build packets only for held + exit deals — the focused-deal analytics
# blocks render against these. Pre-hold deals (spa/loi/ioi) don't have
# enough operational data for a meaningful packet.
_PACKET_DEAL_IDS = ("ccf_2026", "arr_2025", "pma_2024", "tlc_2023")


def _seed_analysis_packets(store: Any, *, result: SeedResult) -> None:
    """Run the real get_or_build_packet pipeline for the held + exit
    deals so block 6 (EBITDA drag) renders against actual bridge math.

    Per C2 decision (SEEDER_PROPOSAL §5): we don't write a fake bridge
    JSON to analysis_runs. We run the 12-step packet builder
    synchronously. ~2-8 sec per deal; ~10-30 sec total. The slowness is
    the operator's tax for not inventing numbers — same principle as
    Q4.6 (no documented attribution assumption).

    Failures are absorbed silently: a deal that can't build a packet
    just won't have one cached. The dashboard renders an empty-state
    for that deal's EBITDA-drag block, which is honest. The
    deals_skipped list captures the failures for the operator's view.
    """
    try:
        from rcm_mc.analysis.analysis_store import get_or_build_packet
    except ImportError:
        # Analysis subsystem not available — skip. Shouldn't happen in
        # a correctly-installed RCM-MC, but the seeder shouldn't crash
        # on import-time issues.
        logger.warning("analysis_store unavailable; skipping packet seed")
        return

    for deal_id in _PACKET_DEAL_IDS:
        try:
            get_or_build_packet(store, deal_id)
            result.packets_built += 1
        except Exception as exc:  # noqa: BLE001
            logger.info(
                "packet build skipped for %s: %s", deal_id, exc
            )
            result.deals_skipped.append(deal_id)


# ── Generated exports seeder (block 9 — deliverables) ──────────────

# Per SEEDER_PROPOSAL §4.6 — 2-3 placeholder export files per held +
# exit deal across formats (HTML / CSV / JSON / XLSX) so the editorial
# deliverables block has cards to display, not the empty-state.

# (deal_id, filename, format) triples. Filenames mirror what the real
# canonical_facade writers produce (full_html_report.html etc.) so
# the rendered card labels look authentic.
_EXPORT_SEEDS: List[Tuple[str, str, str]] = [
    # Flagship deal — 3 deliverables across formats
    ("ccf_2026", "full_html_report.html",   "html"),
    ("ccf_2026", "ic_packet.html",          "html"),
    ("ccf_2026", "deal_export.xlsx",        "xlsx"),
    # Held watch-list deal — 2 deliverables
    ("arr_2025", "full_html_report.html",   "html"),
    ("arr_2025", "diligence_memo.html",     "html"),
    # Strong-hold deal — 2 deliverables
    ("pma_2024", "full_html_report.html",   "html"),
    ("pma_2024", "exit_memo.html",          "html"),
    # Exit deal — 1 closing deliverable
    ("tlc_2023", "exit_memo.html",          "html"),
]


_PLACEHOLDER_HTML = """\
<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title></head>
<body style="font-family:system-ui;padding:32px;max-width:720px;margin:0 auto">
<h1 style="color:#155752">Demo seed file — not a real export</h1>
<p>This is a placeholder file created by <code>rcm_mc.dev.seed</code> so the
editorial dashboard's deliverables block has something to display during
demos. Real exports come from the canonical facade writers in
<code>rcm_mc/exports/canonical_facade.py</code>.</p>
<p><strong>Deal:</strong> {deal_id}<br>
<strong>Format:</strong> {fmt}<br>
<strong>Generated:</strong> demo-seeded</p>
</body></html>
"""

_PLACEHOLDER_CSV = "deal_id,note\n{deal_id},demo seed placeholder\n"
_PLACEHOLDER_JSON = '{{"deal_id":"{deal_id}","note":"demo seed placeholder"}}\n'


def _seed_generated_exports(
    store: Any, *, base_dir: Path, write_files: bool, result: SeedResult,
) -> None:
    """Insert generated_exports rows + (optionally) write placeholder
    files at canonical paths.

    Per the canonical-path discipline (Phase 3 commit 1, Q3.5): files
    land at ``<base>/<deal_id>/<timestamp>_<filename>``. The
    canonical_deal_export_path helper enforces the path shape; we use
    its ``base=`` kwarg to land in the demo dir instead of /data/.
    """
    from rcm_mc.exports.export_store import record_export
    from rcm_mc.infra.exports import canonical_deal_export_path

    # Per-deal timestamp offset so files cluster in time but don't
    # collide on the second.
    for i, (deal_id, filename, fmt) in enumerate(_EXPORT_SEEDS):
        # Stagger timestamps by hours so the deliverables block's
        # "newest first" sort produces a deterministic order.
        # Pre-format using the canonical FS-safe format ("%Y-%m-%dT%H-%M-%S")
        # — the helper expects a string, not a datetime, so spaces and
        # colons don't leak into the filename.
        ts_dt = _REF_DATETIME - timedelta(hours=i + 1)
        ts = ts_dt.strftime("%Y-%m-%dT%H-%M-%S")
        path = canonical_deal_export_path(
            deal_id, filename, timestamp=ts, base=base_dir,
        )
        size_bytes = 0
        if write_files:
            path.parent.mkdir(parents=True, exist_ok=True)
            content: str
            if fmt in ("html",):
                content = _PLACEHOLDER_HTML.format(
                    title=filename, deal_id=deal_id, fmt=fmt,
                )
            elif fmt in ("csv",):
                content = _PLACEHOLDER_CSV.format(deal_id=deal_id)
            elif fmt in ("json",):
                content = _PLACEHOLDER_JSON.format(deal_id=deal_id)
            else:
                # xlsx etc. — write a minimal byte payload so file_size
                # is non-zero. Not a valid xlsx; the deliverables block
                # only links to it, doesn't open it.
                content = f"demo seed placeholder for {deal_id}/{filename}\n"
            path.write_text(content, encoding="utf-8")
            size_bytes = path.stat().st_size
            result.export_files_written += 1

        record_export(
            store,
            deal_id=deal_id,
            analysis_run_id=None,
            format=fmt,
            filepath=str(path),
            file_size_bytes=size_bytes if size_bytes > 0 else None,
            generated_by="dev.seed",
        )
        result.exports_inserted += 1


# ── Post-seed verification (Q4 from SEEDER_PROPOSAL §5) ─────────────

@dataclass
class VerifyResult:
    """Output of verify_seeded_db. Each check is a (label, passed, detail)."""
    checks: List[Tuple[str, bool, str]] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(passed for _, passed, _ in self.checks)

    def report(self) -> str:
        lines = ["Verification report:"]
        for label, passed, detail in self.checks:
            mark = "✓" if passed else "✗"
            lines.append(f"  {mark} {label}: {detail}")
        lines.append("")
        lines.append("PASS" if self.all_passed else "FAIL")
        return "\n".join(lines)


def verify_seeded_db(db_path: Union[str, Path]) -> VerifyResult:
    """Re-run the DEMO_CHECKLIST verification commands programmatically.

    Closes "Discovered during local testing" §4 from
    UI_REWORK_PLAN.md — the verification commands in DEMO_CHECKLIST
    were drafted but never executed. This runs them via the seeder so
    the operator can confirm their demo DB is in shape.

    Each check produces a (label, passed, detail) tuple. ``all_passed``
    is True only when every check passes; the CLI maps this to exit
    code (0 pass, 2 fail).
    """
    from rcm_mc.portfolio.store import PortfolioStore
    from rcm_mc.portfolio.portfolio_snapshots import latest_per_deal
    from rcm_mc.rcm.initiative_tracking import (
        cross_portfolio_initiative_variance,
    )

    result = VerifyResult()
    store = PortfolioStore(str(db_path))

    # Check 1: at least 3 hold deals (DEMO_CHECKLIST data req)
    df = latest_per_deal(store)
    if df.empty:
        result.checks.append((
            "deals/stages", False, "no deals in latest_per_deal",
        ))
    else:
        stage_counts = df.groupby("stage").size().to_dict()
        n_hold = int(stage_counts.get("hold", 0))
        result.checks.append((
            "≥3 deals at stage hold/exit", n_hold >= 3,
            f"hold={n_hold}, stages={stage_counts}",
        ))

    # Check 2: ≥2 snapshots per held deal (covenant heatmap trend)
    try:
        with store.connect() as con:
            rows = con.execute(
                "SELECT deal_id, COUNT(*) AS n FROM deal_snapshots "
                "WHERE stage='hold' GROUP BY deal_id HAVING n >= 2"
            ).fetchall()
        n_with_history = len(rows)
    except Exception:  # noqa: BLE001 — table may not exist on un-seeded DB
        n_with_history = 0
    result.checks.append((
        "≥2 snapshots per held deal", n_with_history >= 3,
        f"{n_with_history} held deals with snapshot history",
    ))

    # Check 3: at least 1 PLAYBOOK GAP firing
    xp_df = cross_portfolio_initiative_variance(store)
    if xp_df.empty:
        n_gaps = 0
    else:
        n_gaps = int(xp_df["is_playbook_gap"].sum())
    result.checks.append((
        "≥1 playbook-gap initiative", n_gaps >= 1,
        f"{n_gaps} initiatives mean ≤ -10% across ≥2 deals",
    ))

    # Check 4: ≥1 generated_exports row pointing at a real file
    try:
        with store.connect() as con:
            rows = con.execute(
                "SELECT filepath FROM generated_exports "
                "WHERE filepath IS NOT NULL AND deal_id IS NOT NULL LIMIT 5"
            ).fetchall()
        n_exports = len(rows)
        n_files_exist = sum(
            1 for r in rows if Path(r["filepath"]).is_file()
        )
    except Exception:  # noqa: BLE001 — generated_exports may not exist
        n_exports = 0
        n_files_exist = 0
    result.checks.append((
        "≥1 generated_exports row with deal_id", n_exports >= 1,
        f"{n_exports} export rows, {n_files_exist} have files on disk",
    ))

    # Check 5: at least 1 analysis_runs packet built
    with store.connect() as con:
        try:
            row = con.execute(
                "SELECT COUNT(*) AS n FROM analysis_runs"
            ).fetchone()
            n_packets = int(row["n"]) if row else 0
        except Exception:  # noqa: BLE001 — table may not exist on minimal DB
            n_packets = 0
    result.checks.append((
        "≥1 analysis_runs packet cached", n_packets >= 1,
        f"{n_packets} packets in analysis_runs",
    ))

    return result


# ── Public API skeleton ─────────────────────────────────────────────

def seed_demo_db(
    db_path: Union[str, Path],
    *,
    deal_count: int = 7,
    snapshot_quarters: int = 8,
    seed_random: int = 20260425,
    overwrite: bool = False,
    write_export_files: bool = True,
    base_dir: Optional[Union[str, Path]] = None,
    force: bool = False,
) -> SeedResult:
    """Seed a SQLite DB with fictional hospital-system demo data.

    Args:
        db_path: SQLite file. Created if missing. Refused if it looks
            like a production target (see ``_guard_against_production``).
        deal_count: How many of the 7 curated deals to seed. ``>7``
            extends with auto-named ``extra_NNN`` deals at ``sourced``
            stage.
        snapshot_quarters: How many trailing quarters of snapshots
            per held deal. Default 8 = 2 fiscal years.
        seed_random: Seed for the random module. Same value produces
            byte-for-byte identical output.
        overwrite: If True and ``db_path`` has any rows in ``deals``,
            drop and recreate the seeded tables. Default False raises
            ``SeederRefuseError`` instead of clobbering.
        write_export_files: If False, write ``generated_exports`` rows
            but skip writing placeholder files to disk. Saves I/O on
            "I just want the dashboard to render" runs.
        base_dir: Where placeholder export files land. Default
            ``tempfile.gettempdir() / "rcm_mc_demo_exports"``.
        force: Override the production-target guard. Use with care.

    Returns:
        ``SeedResult`` with counts.

    Raises:
        SeederRefuseError: production-target guard tripped, or db_path
            already populated and overwrite=False.
    """
    # Skeleton only in this commit. Subsequent commits add the per-block
    # seed logic (deals, snapshots, actuals, packets, exports).
    db_path_obj = Path(db_path)
    _guard_against_production(db_path_obj, force=force)

    if base_dir is None:
        base_dir = Path(tempfile.gettempdir()) / "rcm_mc_demo_exports"
    base_dir = Path(base_dir)

    import time
    started = time.monotonic()
    result = SeedResult()

    # Body wired in subsequent commits — for now, just create the DB
    # and verify the guard + signature work end-to-end.
    from rcm_mc.portfolio.store import PortfolioStore
    from rcm_mc.infra.migrations import run_pending
    store = PortfolioStore(str(db_path_obj))
    run_pending(store)

    if not overwrite:
        with store.connect() as con:
            existing = con.execute(
                "SELECT COUNT(*) AS n FROM deals"
            ).fetchone()
            if existing and existing["n"] > 0:
                raise SeederRefuseError(
                    f"db_path {db_path_obj} already has "
                    f"{existing['n']} rows in deals. Pass overwrite=True "
                    f"(or --overwrite on the CLI) to clobber."
                )

    # Seed step 1: deals + stage history + snapshots (blocks 1-5, 8)
    _seed_deals_and_snapshots(
        store,
        deal_count=deal_count,
        snapshot_quarters=snapshot_quarters,
        overwrite=overwrite,
        result=result,
    )

    # Seed step 2: initiative_actuals (block 7 — playbook gap)
    _seed_initiative_actuals(store, result=result)

    # Seed step 2b (Q4.5): covenant_metrics — all 6 spec covenants
    # per held/exit deal. Closes the "1 of 6 covenants tracked"
    # footnote that Phase 3 left.
    _seed_covenant_metrics(store, result=result)

    # Seed step 3: analysis_runs via real packet builder (block 6)
    _seed_analysis_packets(store, result=result)

    # Seed step 4: generated_exports + placeholder files (block 9)
    _seed_generated_exports(
        store, base_dir=base_dir, write_files=write_export_files,
        result=result,
    )

    result.duration_seconds = time.monotonic() - started
    return result


# ── CLI entrypoint ──────────────────────────────────────────────────

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m rcm_mc.dev.seed",
        description="Seed a SQLite DB with demo data for /app?ui=v3.",
    )
    p.add_argument("--db", required=True,
                   help="Path to SQLite DB to seed (created if missing)")
    p.add_argument("--deal-count", type=int, default=7,
                   help="Number of curated deals to seed (default 7)")
    p.add_argument("--snapshot-quarters", type=int, default=8,
                   help="Trailing quarters of snapshots per held deal")
    p.add_argument("--seed", dest="seed_random", type=int, default=20260425,
                   help="Random seed for determinism")
    p.add_argument("--overwrite", action="store_true",
                   help="Drop+recreate seeded tables if DB is non-empty")
    p.add_argument("--no-export-files", dest="write_export_files",
                   action="store_false",
                   help="Skip writing placeholder export files to disk")
    p.add_argument("--export-base", dest="base_dir", default=None,
                   help="Where placeholder export files land "
                        "(default: tempfile)")
    p.add_argument("--force-prod-path", dest="force", action="store_true",
                   help="Override the production-target guard")
    p.add_argument("--verify", action="store_true",
                   help="After seeding, re-run DEMO_CHECKLIST verification "
                        "commands and exit non-zero if any expected counts "
                        "fail")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    try:
        result = seed_demo_db(
            args.db,
            deal_count=args.deal_count,
            snapshot_quarters=args.snapshot_quarters,
            seed_random=args.seed_random,
            overwrite=args.overwrite,
            write_export_files=args.write_export_files,
            base_dir=args.base_dir,
            force=args.force,
        )
    except SeederRefuseError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(result.summary())
    if args.verify:
        v = verify_seeded_db(args.db)
        print()
        print(v.report())
        if not v.all_passed:
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
