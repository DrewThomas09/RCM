"""SQLite storage for Monte Carlo runs.

One row per ``(deal_id, scenario_label, analysis_run_id)``. Append-only
so partners can diff runs over time; the ``latest`` endpoint just
picks the most recent row.
"""
from __future__ import annotations

import json
import zlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .ebitda_mc import MonteCarloResult


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_table(store: Any) -> None:
    """``mc_simulation_runs`` — compressed JSON blobs keyed by deal."""
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS mc_simulation_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                analysis_run_id TEXT,
                scenario_label TEXT NOT NULL DEFAULT '',
                n_simulations INTEGER NOT NULL DEFAULT 0,
                result_json BLOB NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
                    ON DELETE CASCADE
            )"""
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS ix_mc_deal "
            "ON mc_simulation_runs(deal_id, created_at)"
        )
        con.commit()


def save_v2_mc_run(
    store: Any,
    deal_id: str,
    result: Any,
    *,
    analysis_run_id: Optional[str] = None,
) -> int:
    """Persist a :class:`V2MonteCarloResult` in the same table as v1 runs.

    The scenario_label is prefixed with ``v2:`` (when the caller didn't
    already) so downstream ``load_latest_mc_run`` queries can pick
    between the two simulator's outputs by looking at the prefix. We
    don't currently ship a typed ``load_latest_v2_mc_run`` — the JSON
    blob roundtrips through ``V2MonteCarloResult.to_dict()`` on write
    and is read back as a plain dict by the API caller.
    """
    _ensure_table(store)
    label = str(getattr(result, "scenario_label", "") or "")
    if not label.startswith("v2:"):
        label = f"v2:{label}" if label else "v2:default"
    payload = json.dumps(result.to_dict(), default=str).encode("utf-8")
    blob = zlib.compress(payload, level=6)
    with store.connect() as con:
        cur = con.execute(
            """INSERT INTO mc_simulation_runs
               (deal_id, analysis_run_id, scenario_label, n_simulations,
                result_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (str(deal_id), analysis_run_id or None,
             label, int(getattr(result, "n_simulations", 0)),
             blob, _utcnow_iso()),
        )
        con.commit()
        return int(cur.lastrowid)


def save_mc_run(
    store: Any,
    deal_id: str,
    result: MonteCarloResult,
    *,
    analysis_run_id: Optional[str] = None,
) -> int:
    _ensure_table(store)
    payload = json.dumps(result.to_dict(), default=str).encode("utf-8")
    blob = zlib.compress(payload, level=6)
    with store.connect() as con:
        cur = con.execute(
            """INSERT INTO mc_simulation_runs
               (deal_id, analysis_run_id, scenario_label, n_simulations,
                result_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (str(deal_id), analysis_run_id or None,
             result.scenario_label or "", int(result.n_simulations),
             blob, _utcnow_iso()),
        )
        con.commit()
        return int(cur.lastrowid)


def load_latest_mc_run(
    store: Any,
    deal_id: str,
    *,
    scenario_label: Optional[str] = None,
) -> Optional[MonteCarloResult]:
    _ensure_table(store)
    with store.connect() as con:
        if scenario_label is not None:
            row = con.execute(
                """SELECT result_json FROM mc_simulation_runs
                   WHERE deal_id = ? AND scenario_label = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (str(deal_id), str(scenario_label)),
            ).fetchone()
        else:
            row = con.execute(
                """SELECT result_json FROM mc_simulation_runs
                   WHERE deal_id = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (str(deal_id),),
            ).fetchone()
    if row is None:
        return None
    try:
        payload = zlib.decompress(row["result_json"]).decode("utf-8")
        data = json.loads(payload)
    except (zlib.error, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return _mc_from_dict(data)


def list_mc_runs(store: Any, deal_id: Optional[str] = None) -> List[Dict[str, Any]]:
    _ensure_table(store)
    with store.connect() as con:
        if deal_id:
            rows = con.execute(
                """SELECT run_id, deal_id, analysis_run_id, scenario_label,
                          n_simulations, created_at
                   FROM mc_simulation_runs WHERE deal_id = ?
                   ORDER BY created_at DESC""",
                (str(deal_id),),
            ).fetchall()
        else:
            rows = con.execute(
                """SELECT run_id, deal_id, analysis_run_id, scenario_label,
                          n_simulations, created_at
                   FROM mc_simulation_runs ORDER BY created_at DESC"""
            ).fetchall()
    return [dict(r) for r in rows]


def _mc_from_dict(d: Dict[str, Any]) -> MonteCarloResult:
    """Reverse of MonteCarloResult.to_dict(). Nested dataclasses are
    rehydrated by hand; simpler than a generic dispatcher.
    """
    from .convergence import ConvergenceReport
    from .ebitda_mc import (
        DistributionSummary,
        HistogramBin,
        TornadoBar,
    )
    def _ds(key: str) -> DistributionSummary:
        payload = d.get(key) or {}
        return DistributionSummary(**{
            k: float(v) for k, v in payload.items() if k in {
                "p5", "p10", "p25", "p50", "p75", "p90", "p95", "mean", "std",
            }
        })
    conv_raw = d.get("convergence_check") or {}
    convergence = ConvergenceReport(
        converged=bool(conv_raw.get("converged") or False),
        n_simulations=int(conv_raw.get("n_simulations") or 0),
        window=int(conv_raw.get("window") or 0),
        tolerance=float(conv_raw.get("tolerance") or 0.0),
        last_window_range=float(conv_raw.get("last_window_range") or 0.0),
        recommended_n=int(conv_raw.get("recommended_n") or 0),
        p50_final=float(conv_raw.get("p50_final") or 0.0),
    )
    return MonteCarloResult(
        n_simulations=int(d.get("n_simulations") or 0),
        ebitda_impact=_ds("ebitda_impact"),
        moic=_ds("moic"),
        irr=_ds("irr"),
        working_capital_released=_ds("working_capital_released"),
        probability_of_negative_impact=float(d.get("probability_of_negative_impact") or 0.0),
        probability_of_covenant_breach=float(d.get("probability_of_covenant_breach") or 0.0),
        probability_of_target_moic={
            k: float(v) for k, v in (d.get("probability_of_target_moic") or {}).items()
        },
        variance_contribution={
            k: float(v) for k, v in (d.get("variance_contribution") or {}).items()
        },
        tornado_data=[TornadoBar(**t) for t in (d.get("tornado_data") or [])],
        histogram_data=[HistogramBin(**h) for h in (d.get("histogram_data") or [])],
        convergence_check=convergence,
        scenario_label=str(d.get("scenario_label") or ""),
    )
