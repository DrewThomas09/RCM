"""Run-history observability — quality tracked across runs, not just within
one file.

Data-observability platforms (Monte Carlo, Bigeye) earn their keep by
answering "is this feed getting better or worse?" — a single-run report
can't. Every cleaner run records its scorecard summary here; the history
page trends the quality score, compares runs, and shows which rules are
recurring vs newly introduced.

Storage is a dedicated SQLite file in the cleaner's WORKDIR — deliberately
NOT the portfolio store. The cleaner promises "nothing is written to the
app database", and this keeps that promise while still giving teams
longitudinal memory. The file holds aggregate counts only: no claim rows,
no PHI, just metadata about each run.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from .engine import WORKDIR

_DB_PATH = Path(WORKDIR) / "npi_cleaner_history.sqlite3"
_LOCK = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id      TEXT PRIMARY KEY,
    ts          REAL NOT NULL,
    file_name   TEXT NOT NULL,
    rows_in     INTEGER NOT NULL,
    rows_out    INTEGER NOT NULL,
    dupes       INTEGER NOT NULL,
    score       INTEGER NOT NULL,
    letter      TEXT NOT NULL,
    dimensions  TEXT NOT NULL,   -- JSON {completeness: 98.3, ...}
    repairs     TEXT NOT NULL,   -- JSON {rule: count}
    sanity      TEXT NOT NULL,   -- JSON {rule: count}
    changes     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_runs_ts ON runs (ts DESC);
"""


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(_DB_PATH)
    con.execute("PRAGMA busy_timeout = 5000")
    con.executescript(_SCHEMA)
    return con


def record_run(scorecard: Dict[str, object], file_name: str) -> str:
    """Persist one run's aggregate summary. Guarded: history is a
    nice-to-have, so a storage failure must never fail the cleaning job."""
    run_id = uuid.uuid4().hex[:12]
    q = scorecard.get("quality") or {}
    try:
        with _LOCK, _conn() as con:
            con.execute(
                "INSERT INTO runs (run_id, ts, file_name, rows_in, rows_out,"
                " dupes, score, letter, dimensions, repairs, sanity, changes)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (run_id, time.time(), file_name,
                 int(scorecard.get("rows_in") or 0),
                 int(scorecard.get("rows_out") or 0),
                 int(scorecard.get("duplicates_removed") or 0),
                 int(q.get("score") or 0), str(q.get("letter") or "—"),
                 json.dumps(q.get("dimensions") or {}),
                 json.dumps(scorecard.get("repairs") or {}),
                 json.dumps(scorecard.get("sanity") or {}),
                 int(scorecard.get("changes_logged") or 0)))
    except Exception:  # noqa: BLE001 — observability never blocks cleaning
        return ""
    return run_id


def list_runs(limit: int = 50) -> List[Dict[str, object]]:
    try:
        with _LOCK, _conn() as con:
            rows = con.execute(
                "SELECT run_id, ts, file_name, rows_in, rows_out, dupes,"
                " score, letter, dimensions, sanity, changes"
                " FROM runs ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
    except Exception:  # noqa: BLE001
        return []
    out = []
    for r in rows:
        out.append({
            "run_id": r[0], "ts": r[1], "file_name": r[2],
            "rows_in": r[3], "rows_out": r[4], "dupes": r[5],
            "score": r[6], "letter": r[7],
            "dimensions": json.loads(r[8] or "{}"),
            "sanity": json.loads(r[9] or "{}"),
            "changes": r[10],
        })
    return out


def get_run(run_id: str) -> Optional[Dict[str, object]]:
    try:
        with _LOCK, _conn() as con:
            r = con.execute(
                "SELECT run_id, ts, file_name, rows_in, rows_out, dupes,"
                " score, letter, dimensions, repairs, sanity, changes"
                " FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    except Exception:  # noqa: BLE001
        return None
    if r is None:
        return None
    return {"run_id": r[0], "ts": r[1], "file_name": r[2],
            "rows_in": r[3], "rows_out": r[4], "dupes": r[5],
            "score": r[6], "letter": r[7],
            "dimensions": json.loads(r[8] or "{}"),
            "repairs": json.loads(r[9] or "{}"),
            "sanity": json.loads(r[10] or "{}"),
            "changes": r[11]}


def compare_runs(a_id: str, b_id: str) -> Optional[Dict[str, object]]:
    """Run-over-run delta: score movement plus per-rule flag changes —
    "did this feed get better after the source fix?" in one payload."""
    a, b = get_run(a_id), get_run(b_id)
    if not a or not b:
        return None
    keys = sorted(set(a["sanity"]) | set(b["sanity"]))
    rule_delta = []
    for k in keys:
        av = int(a["sanity"].get(k, 0))
        bv = int(b["sanity"].get(k, 0))
        if av != bv:
            rule_delta.append({"rule": k, "a": av, "b": bv, "delta": bv - av})
    rule_delta.sort(key=lambda d: abs(int(d["delta"])), reverse=True)
    return {"a": a, "b": b,
            "score_delta": int(b["score"]) - int(a["score"]),
            "rule_delta": rule_delta}
