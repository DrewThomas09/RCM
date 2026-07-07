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
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from .engine import WORKDIR

_DB_NAME = "npi_cleaner_history.sqlite3"
_DB_PATH = Path(WORKDIR) / _DB_NAME
_LOCK = threading.Lock()


def _db_path() -> Path:
    """The store lives under /tmp by default, which any reboot or tmp
    cleaner wipes — silently erasing the longitudinal memory this module
    promises. RCM_MC_NPI_WORKDIR points the store at a persistent
    directory; read per-call so deployments can set it without an import
    cycle and tests can still monkeypatch ``_DB_PATH``."""
    root = (os.environ.get("RCM_MC_NPI_WORKDIR") or "").strip()
    if root:
        return Path(root) / _DB_NAME
    return _DB_PATH

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
    p = _db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p)
    con.execute("PRAGMA busy_timeout = 5000")
    con.executescript(_SCHEMA)
    # Migration: population metrics (PMPM / readmit / encounters / top
    # setting) so those trend across runs like the quality dimensions.
    # Idempotent — ADD COLUMN raises on an existing column, swallowed.
    try:
        con.execute("ALTER TABLE runs ADD COLUMN population TEXT")
    except sqlite3.OperationalError:
        pass
    return con


def _population_metrics(scorecard: Dict[str, object]) -> Dict[str, object]:
    """Flatten the trendable population numbers from a scorecard —
    aggregate only, no claim rows, no PHI (same discipline as the rest of
    history)."""
    pop = scorecard.get("population") or {}
    out: Dict[str, object] = {}
    enc = pop.get("encounters") or {}
    if enc:
        out["n_encounters"] = enc.get("n_encounters")
        rd = enc.get("readmissions") or {}
        if rd:
            out["readmit_rate_pct"] = rd.get("rate_pct")
    vol = pop.get("volume") or {}
    if vol.get("median_observed_pmpm") is not None:
        out["median_observed_pmpm"] = vol.get("median_observed_pmpm")
    mix = pop.get("service_mix") or {}
    cats = mix.get("categories") or []
    if cats:
        out["top_setting"] = cats[0].get("category")
        out["top_setting_pct"] = cats[0].get("pct")
    ci = pop.get("coding_intensity") or {}
    if ci.get("file_avg_level") is not None:
        out["em_avg_level"] = ci.get("file_avg_level")
    return out


def record_run(scorecard: Dict[str, object], file_name: str) -> str:
    """Persist one run's aggregate summary. Guarded: history is a
    nice-to-have, so a storage failure must never fail the cleaning job."""
    run_id = uuid.uuid4().hex[:12]
    q = scorecard.get("quality") or {}
    try:
        with _LOCK, _conn() as con:
            con.execute(
                "INSERT INTO runs (run_id, ts, file_name, rows_in, rows_out,"
                " dupes, score, letter, dimensions, repairs, sanity, changes,"
                " population)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (run_id, time.time(), file_name,
                 int(scorecard.get("rows_in") or 0),
                 int(scorecard.get("rows_out") or 0),
                 int(scorecard.get("duplicates_removed") or 0),
                 int(q.get("score") or 0), str(q.get("letter") or "—"),
                 json.dumps(q.get("dimensions") or {}),
                 json.dumps(scorecard.get("repairs") or {}),
                 json.dumps(scorecard.get("sanity") or {}),
                 int(scorecard.get("changes_logged") or 0),
                 json.dumps(_population_metrics(scorecard))))
    except Exception:  # noqa: BLE001 — observability never blocks cleaning
        return ""
    return run_id


def list_runs(limit: int = 50) -> List[Dict[str, object]]:
    try:
        with _LOCK, _conn() as con:
            rows = con.execute(
                "SELECT run_id, ts, file_name, rows_in, rows_out, dupes,"
                " score, letter, dimensions, sanity, changes, population"
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
            "population": json.loads(r[11] or "{}") if len(r) > 11 else {},
        })
    return out


def latest_run_for(file_name: str) -> Optional[Dict[str, object]]:
    """Most recent recorded run of the SAME file name — the baseline for
    trend alerts. Exact-name matching is deliberate: a team re-uploading
    nightly extracts keeps the name stable, and a fuzzy match would
    compare unrelated files."""
    try:
        with _LOCK, _conn() as con:
            r = con.execute(
                "SELECT score, sanity, ts FROM runs WHERE file_name = ?"
                " ORDER BY ts DESC LIMIT 1", (file_name,)).fetchone()
    except Exception:  # noqa: BLE001
        return None
    if r is None:
        return None
    return {"score": r[0], "sanity": json.loads(r[1] or "{}"), "ts": r[2]}


def trend_alerts(scorecard: Dict[str, object], file_name: str) -> List[str]:
    """Regression warnings vs the previous run of this file: a score drop,
    a rule count doubling, or a sizeable brand-new finding. Called BEFORE
    the current run is recorded so it never compares a run to itself."""
    prev = latest_run_for(file_name)
    if not prev:
        return []
    alerts: List[str] = []
    q = scorecard.get("quality") or {}
    score = int(q.get("score") or 0)
    prev_score = int(prev.get("score") or 0)
    if prev_score - score >= 5:
        alerts.append(f"Quality score dropped {prev_score} → {score} vs "
                      "the previous run of this file.")
    elif score - prev_score >= 5:
        # The narrative was one-sided: regressions alerted, recoveries were
        # silent — so a team that fixed its feed never saw the payoff.
        alerts.append(f"Quality score recovered {prev_score} → {score} vs "
                      "the previous run of this file.")
    prev_san = prev.get("sanity") or {}
    cur_san = scorecard.get("sanity") or {}
    for rule in sorted(cur_san):
        n = int(cur_san.get(rule) or 0)
        p = int(prev_san.get(rule, 0))
        if p > 0 and n >= 10 and n >= 2 * p:
            alerts.append(f"'{rule}' jumped {p} → {n} rows vs the "
                          "previous run.")
        elif p == 0 and n >= 25:
            alerts.append(f"'{rule}' is new since the previous run "
                          f"({n} rows).")
    return alerts[:8]


def get_run(run_id: str) -> Optional[Dict[str, object]]:
    try:
        with _LOCK, _conn() as con:
            r = con.execute(
                "SELECT run_id, ts, file_name, rows_in, rows_out, dupes,"
                " score, letter, dimensions, repairs, sanity, changes,"
                " population"
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
            "changes": r[11],
            "population": json.loads(r[12] or "{}") if len(r) > 12 else {}}


def compare_runs(a_id: str, b_id: str) -> Optional[Dict[str, object]]:
    """Run-over-run delta: score movement plus per-rule flag changes —
    "did this feed get better after the source fix?" in one payload.
    ``dimension_delta`` and ``population_delta`` are additive keys so the
    per-dimension and PMPM/readmit/E&M movement (recorded on every run but
    previously compared nowhere) reach the compare surface."""
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

    dim_delta: Dict[str, float] = {}
    for k in sorted(set(a["dimensions"]) | set(b["dimensions"])):
        try:
            dim_delta[k] = round(float(b["dimensions"].get(k, 0.0))
                                 - float(a["dimensions"].get(k, 0.0)), 1)
        except (TypeError, ValueError):
            continue

    pop_delta: Dict[str, float] = {}
    pa = a.get("population") or {}
    pb = b.get("population") or {}
    for k in sorted(set(pa) | set(pb)):
        va, vb = pa.get(k), pb.get(k)
        if not isinstance(va, (int, float)) or not isinstance(vb, (int, float)):
            continue        # top_setting etc. — strings don't delta
        nd = 2 if k == "median_observed_pmpm" else (
            1 if k.endswith("_pct") else 2)
        pop_delta[k] = round(float(vb) - float(va), nd)

    return {"a": a, "b": b,
            "score_delta": int(b["score"]) - int(a["score"]),
            "rule_delta": rule_delta,
            "dimension_delta": dim_delta,
            "population_delta": pop_delta}


def streaks(file_name: str) -> Optional[Dict[str, object]]:
    """Run-over-run streaks for one file: how many consecutive runs the
    quality score has been improving (or declining), the best/worst score
    on record, and the latest movement — the "is this feed trending the
    right way" answer the per-run deltas can't give. Never raises."""
    try:
        with _LOCK, _conn() as con:
            rows = con.execute(
                "SELECT score FROM runs WHERE file_name = ?"
                " ORDER BY ts ASC", (file_name,)).fetchall()
    except Exception:  # noqa: BLE001
        return None
    scores = [int(r[0]) for r in rows]
    if not scores:
        return None
    improving = declining = 0
    for i in range(len(scores) - 1, 0, -1):
        d = scores[i] - scores[i - 1]
        if d > 0 and declining == 0:
            improving += 1
        elif d < 0 and improving == 0:
            declining += 1
        else:
            break
    return {"runs": len(scores),
            "improving_streak": improving,
            "declining_streak": declining,
            "best_score": max(scores),
            "worst_score": min(scores),
            "latest_score": scores[-1],
            "latest_delta": (scores[-1] - scores[-2]
                             if len(scores) >= 2 else None)}
