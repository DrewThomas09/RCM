from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import numpy as np
import pandas as pd
import yaml

from ..core.distributions import sample_dist


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _beta_params_from_mean_sd(mean: float, sd: float) -> Tuple[float, float]:
    """Convert mean/sd to Beta(alpha,beta). Falls back to a conservative prior if invalid."""
    m = float(np.clip(mean, 1e-6, 1 - 1e-6))
    sd = float(max(sd, 1e-8))
    var = sd * sd
    max_var = m * (1 - m) * 0.99
    if var >= max_var:
        var = max_var
    k = m * (1 - m) / var - 1.0
    a = m * k
    b = (1 - m) * k
    if not np.isfinite(a) or not np.isfinite(b) or a <= 0 or b <= 0:
        # conservative fallback
        a = 10.0 * m
        b = 10.0 * (1 - m)
        a = max(a, 1.0)
        b = max(b, 1.0)
    return float(a), float(b)


def extract_primitives_from_config(cfg: Dict[str, Any], n_draws: int = 4000, seed: int = 123) -> Dict[str, Any]:
    """Summarize key modeled primitives (mean/sd) from config distributions."""
    rng = np.random.default_rng(int(seed))
    payers = {}
    for payer, pconf in cfg.get("payers", {}).items():
        row = {}
        dar = sample_dist(rng, pconf["dar_clean_days"], size=int(n_draws))
        row["dar_clean_days_mean"] = float(np.mean(dar))
        row["dar_clean_days_sd"] = float(np.std(dar, ddof=1))

        if pconf.get("include_denials", False):
            idr = sample_dist(rng, pconf["denials"]["idr"], size=int(n_draws))
            fwr = sample_dist(rng, pconf["denials"]["fwr"], size=int(n_draws))
            row["idr_mean"] = float(np.mean(idr))
            row["idr_sd"] = float(np.std(idr, ddof=1))
            row["fwr_mean"] = float(np.mean(fwr))
            row["fwr_sd"] = float(np.std(fwr, ddof=1))

        payers[payer] = row

    return {"payers": payers}


@dataclass
class RunRecord:
    run_id: int
    deal_id: str
    scenario: str
    created_at: str
    notes: str
    config_yaml: str
    summary_json: str
    primitives_json: str


class PortfolioStore:
    """SQLite-backed store of diligence runs for portfolio benchmarking."""

    def __init__(self, db_path: str):
        self.db_path = str(db_path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Context manager yielding a connection that is always closed on exit.

        sqlite3.Connection's own context manager only commits/rolls back — it
        does not close. Without this wrapper we leak connections.

        B147 fix: set ``busy_timeout`` so concurrent handler threads
        retry briefly on a locked database instead of immediately
        raising ``sqlite3.OperationalError: database is locked``.
        """
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        # 5s is generous but matches partner-tolerance for a form POST
        con.execute("PRAGMA busy_timeout = 5000")
        # Prompt 21: FK enforcement is off by default in SQLite. We opt
        # in on every connection so orphan inserts into
        # ``deal_overrides`` / ``analysis_runs`` / ``mc_simulation_runs``
        # / ``generated_exports`` raise IntegrityError immediately
        # instead of silently creating dangling rows.
        con.execute("PRAGMA foreign_keys = ON")
        try:
            yield con
        finally:
            con.close()

    def init_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.execute(
                """CREATE TABLE IF NOT EXISTS deals (
                    deal_id TEXT PRIMARY KEY,
                    name TEXT,
                    created_at TEXT,
                    profile_json TEXT
                )"""
            )
            try:
                con.execute("ALTER TABLE deals ADD COLUMN archived_at TEXT")
            except Exception:
                pass
            con.execute(
                """CREATE TABLE IF NOT EXISTS runs (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    deal_id TEXT,
                    scenario TEXT,
                    created_at TEXT,
                    notes TEXT,
                    config_yaml TEXT,
                    summary_json TEXT,
                    primitives_json TEXT,
                    FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
                )"""
            )
            con.commit()

    def upsert_deal(self, deal_id: str, name: Optional[str] = None, profile: Optional[Dict[str, Any]] = None) -> None:
        self.init_db()
        with self.connect() as con:
            # Serialize the insert-or-update path so concurrent helper
            # calls (watchlist, deadlines, notes) can't both observe
            # "missing" and race into a UNIQUE violation.
            con.execute("BEGIN IMMEDIATE")
            try:
                con.execute(
                    "INSERT OR IGNORE INTO deals (deal_id, name, created_at, profile_json) "
                    "VALUES (?, ?, ?, ?)",
                    (deal_id, name or deal_id, _utcnow(), json.dumps(profile or {})),
                )
                if name is not None or profile is not None:
                    existing = con.execute("SELECT * FROM deals WHERE deal_id=?", (deal_id,)).fetchone()
                    cur_name = existing["name"]
                    cur_profile = json.loads(existing["profile_json"] or "{}")
                    new_name = name if name is not None else cur_name
                    if profile is not None:
                        cur_profile.update(profile)
                    con.execute(
                        "UPDATE deals SET name=?, profile_json=? WHERE deal_id=?",
                        (new_name, json.dumps(cur_profile), deal_id),
                    )
                con.commit()
            except Exception:
                con.rollback()
                raise

    def delete_deal(self, deal_id: str) -> bool:
        """Delete a deal and all associated data across child tables.

        Returns True if the deal existed and was deleted.
        """
        self.init_db()
        child_tables = [
            "runs", "deal_overrides", "analysis_runs", "mc_simulation_runs",
            "generated_exports", "deal_notes", "deal_tags", "deal_owners",
            "deal_deadlines", "deal_sim_inputs", "comments",
            "approval_requests", "alert_acks", "alert_history",
            "deal_stages", "health_scores", "watchlist",
            "value_creation_plans", "hold_period_tracking",
            "initiative_tracking", "provenance_registry",
            "refresh_schedule", "portfolio_snapshots",
        ]
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            try:
                existing = con.execute(
                    "SELECT deal_id FROM deals WHERE deal_id = ?",
                    (deal_id,),
                ).fetchone()
                if not existing:
                    con.rollback()
                    return False
                for tbl in child_tables:
                    try:
                        con.execute(
                            f"DELETE FROM {tbl} WHERE deal_id = ?",
                            (deal_id,),
                        )
                    except Exception:
                        pass
                con.execute(
                    "DELETE FROM deals WHERE deal_id = ?", (deal_id,),
                )
                con.commit()
                return True
            except Exception:
                con.rollback()
                raise

    def clone_deal(self, source_id: str, new_id: str, new_name: Optional[str] = None) -> bool:
        """Deep-copy a deal with a new ID. Copies profile, tags, sim inputs.

        Returns True if the source deal existed and was cloned.
        """
        self.init_db()
        with self.connect() as con:
            src = con.execute(
                "SELECT * FROM deals WHERE deal_id = ?", (source_id,),
            ).fetchone()
            if not src:
                return False
            name = new_name or f"{src['name']} (copy)"
            con.execute("BEGIN IMMEDIATE")
            try:
                con.execute(
                    "INSERT INTO deals (deal_id, name, created_at, profile_json) "
                    "VALUES (?, ?, ?, ?)",
                    (new_id, name, _utcnow(), src["profile_json"]),
                )
                for tbl in ("deal_tags", "deal_sim_inputs"):
                    try:
                        cols_rows = con.execute(
                            f"PRAGMA table_info({tbl})"
                        ).fetchall()
                        cols = [c["name"] for c in cols_rows if c["name"] != "id"]
                        col_list = ", ".join(cols)
                        select_cols = ", ".join(
                            f"'{new_id}'" if c == "deal_id" else c
                            for c in cols
                        )
                        con.execute(
                            f"INSERT INTO {tbl} ({col_list}) "
                            f"SELECT {select_cols} FROM {tbl} WHERE deal_id = ?",
                            (source_id,),
                        )
                    except Exception:
                        pass
                con.commit()
                return True
            except Exception:
                con.rollback()
                raise

    def archive_deal(self, deal_id: str) -> bool:
        """Soft-delete: set archived_at. Returns True if the deal existed."""
        self.init_db()
        with self.connect() as con:
            cur = con.execute(
                "UPDATE deals SET archived_at = ? WHERE deal_id = ? AND archived_at IS NULL",
                (_utcnow(), deal_id),
            )
            con.commit()
            return cur.rowcount > 0

    def unarchive_deal(self, deal_id: str) -> bool:
        """Restore an archived deal. Returns True if the deal was archived."""
        self.init_db()
        with self.connect() as con:
            cur = con.execute(
                "UPDATE deals SET archived_at = NULL WHERE deal_id = ? AND archived_at IS NOT NULL",
                (deal_id,),
            )
            con.commit()
            return cur.rowcount > 0

    def list_deals(self, include_archived: bool = False) -> pd.DataFrame:
        self.init_db()
        with self.connect() as con:
            if include_archived:
                rows = con.execute(
                    "SELECT deal_id, name, created_at, profile_json, archived_at "
                    "FROM deals ORDER BY created_at DESC"
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT deal_id, name, created_at, profile_json, archived_at "
                    "FROM deals WHERE archived_at IS NULL ORDER BY created_at DESC"
                ).fetchall()
        out = []
        for r in rows:
            d = {"deal_id": r["deal_id"], "name": r["name"],
                 "created_at": r["created_at"],
                 **json.loads(r["profile_json"] or "{}")}
            if r["archived_at"]:
                d["archived_at"] = r["archived_at"]
            out.append(d)
        return pd.DataFrame(out)

    def add_run(
        self,
        *,
        deal_id: str,
        scenario: str,
        cfg: Dict[str, Any],
        summary_df: pd.DataFrame,
        notes: str = "",
    ) -> int:
        self.init_db()
        self.upsert_deal(deal_id)

        cfg_yaml = yaml.safe_dump(cfg, sort_keys=False)
        summary_json = summary_df.reset_index().to_json(orient="records")
        primitives_json = json.dumps(extract_primitives_from_config(cfg))

        with self.connect() as con:
            cur = con.execute(
                "INSERT INTO runs (deal_id, scenario, created_at, notes, config_yaml, summary_json, primitives_json) VALUES (?,?,?,?,?,?,?)",
                (deal_id, scenario, _utcnow(), notes, cfg_yaml, summary_json, primitives_json),
            )
            con.commit()
            return int(cur.lastrowid)

    def list_runs(self, deal_id: Optional[str] = None) -> pd.DataFrame:
        self.init_db()
        with self.connect() as con:
            if deal_id:
                rows = con.execute(
                    "SELECT run_id, deal_id, scenario, created_at, notes FROM runs WHERE deal_id=? ORDER BY created_at DESC",
                    (deal_id,),
                ).fetchall()
            else:
                rows = con.execute(
                    "SELECT run_id, deal_id, scenario, created_at, notes FROM runs ORDER BY created_at DESC"
                ).fetchall()
        return pd.DataFrame([dict(r) for r in rows])

    def get_run(self, run_id: int) -> RunRecord:
        with self.connect() as con:
            r = con.execute("SELECT * FROM runs WHERE run_id=?", (int(run_id),)).fetchone()
            if r is None:
                raise KeyError(f"run_id not found: {run_id}")
            return RunRecord(**dict(r))

    def export_priors(self, out_yaml_path: str) -> Dict[str, Any]:
        """Compute empirical priors for IDR/FWR/DAR by payer from stored runs (across scenarios)."""
        self.init_db()
        with self.connect() as con:
            rows = con.execute("SELECT primitives_json FROM runs").fetchall()

        if not rows:
            priors = {"payers": {}}
            Path(out_yaml_path).write_text(yaml.safe_dump(priors, sort_keys=False))
            return priors

        # Collect per-payer primitives across runs
        per_payer = {}
        for r in rows:
            prim = json.loads(r["primitives_json"] or "{}")
            for payer, vals in prim.get("payers", {}).items():
                per_payer.setdefault(payer, []).append(vals)

        priors = {"payers": {}}
        for payer, entries in per_payer.items():
            # arrays
            idr = [e.get("idr_mean") for e in entries if "idr_mean" in e]
            fwr = [e.get("fwr_mean") for e in entries if "fwr_mean" in e]
            dar = [e.get("dar_clean_days_mean") for e in entries if "dar_clean_days_mean" in e]

            def _mean_sd(xs: List[float]) -> Tuple[float, float]:
                xs = [float(x) for x in xs if x is not None and np.isfinite(float(x))]
                if len(xs) < 2:
                    m = float(xs[0]) if xs else 0.0
                    return m, max(abs(m) * 0.10, 1e-6)
                return float(np.mean(xs)), float(np.std(xs, ddof=1))

            idr_m, idr_s = _mean_sd(idr)
            fwr_m, fwr_s = _mean_sd(fwr)
            dar_m, dar_s = _mean_sd(dar)

            payer_prior = {
                "dar_clean_days": {"dist": "normal", "mean": dar_m, "sd": dar_s},
            }
            if idr:
                a, b = _beta_params_from_mean_sd(idr_m, idr_s)
                payer_prior.setdefault("denials", {})["idr"] = {"dist": "beta", "mean": idr_m, "sd": idr_s, "alpha": a, "beta": b}
            if fwr:
                a, b = _beta_params_from_mean_sd(fwr_m, fwr_s)
                payer_prior.setdefault("denials", {})["fwr"] = {"dist": "beta", "mean": fwr_m, "sd": fwr_s, "alpha": a, "beta": b}

            priors["payers"][payer] = payer_prior

        Path(out_yaml_path).write_text(yaml.safe_dump(priors, sort_keys=False))
        return priors
