"""Hold-period initiative attribution (Brick 57).

EBITDA variance (B52) answers "is this deal on plan?" — but not "which
RCM workstream is behind plan?". When a platform is $2M under plan on
EBITDA, partners need to know whether denials automation stalled, A/R
aging worsened, or coding/CDI fell short.

This module adds a per-initiative quarterly attribution layer:

- ``initiative_actuals`` table keyed on (deal_id, initiative_id, quarter)
- Each row records the dollar EBITDA impact attributable to that
  initiative in that quarter, per management's own P&L attribution.
- ``initiative_variance_report`` compares cumulative actuals vs the
  underwritten expected impact (from `configs/initiatives_library.yaml`
  annual_run_rate, pro-rated to quarters elapsed).

Why this matters for PE: when a variance appears at the EBITDA level,
the board conversation is "which lever do we push?". Without
initiative-level attribution, everyone argues. With it, the bucket is
obvious and the 100-day-plan refresh writes itself.

Strictly RCM scope: captures RCM-initiative attribution, not OpEx line
items, wage inflation, or non-RCM value-creation levers.
"""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from .initiatives import get_all_initiatives
from ..portfolio.store import PortfolioStore


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_initiative_table(store: PortfolioStore) -> None:
    """Create initiative_actuals table if missing. Idempotent."""
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS initiative_actuals (
                init_actual_id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                initiative_id TEXT NOT NULL,
                quarter TEXT NOT NULL,
                created_at TEXT NOT NULL,
                ebitda_impact REAL NOT NULL,
                notes TEXT,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
            )"""
        )
        # Upsert-on-reimport: (deal, initiative, quarter) is unique
        con.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_init_actuals "
            "ON initiative_actuals(deal_id, initiative_id, quarter)"
        )
        con.commit()


# ── Public API ─────────────────────────────────────────────────────────────

def record_initiative_actual(
    store: PortfolioStore,
    *,
    deal_id: str,
    initiative_id: str,
    quarter: str,
    ebitda_impact: float,
    notes: str = "",
) -> int:
    """Record the EBITDA impact attributable to one initiative in one quarter.

    Validates ``initiative_id`` against the shipped initiatives library —
    a typo like ``prior_auth_improvment`` (missing 'e') is caught
    immediately rather than silently storing orphan rows.
    """
    import re
    qtr = quarter.replace(" ", "").upper()
    if not re.fullmatch(r"\d{4}Q[1-4]", qtr):
        raise ValueError(f"quarter must be 'YYYYQn' format (got {quarter!r})")

    known = {i["id"] for i in get_all_initiatives() if i.get("id")}
    if known and initiative_id not in known:
        raise ValueError(
            f"Unknown initiative {initiative_id!r}. "
            f"Known IDs: {sorted(known)}"
        )

    _ensure_initiative_table(store)
    store.upsert_deal(deal_id)
    with store.connect() as con:
        con.execute(
            "DELETE FROM initiative_actuals "
            "WHERE deal_id=? AND initiative_id=? AND quarter=?",
            (deal_id, initiative_id, qtr),
        )
        cur = con.execute(
            "INSERT INTO initiative_actuals "
            "(deal_id, initiative_id, quarter, created_at, ebitda_impact, notes) "
            "VALUES (?,?,?,?,?,?)",
            (deal_id, initiative_id, qtr, _utcnow(),
             float(ebitda_impact), notes),
        )
        con.commit()
        return int(cur.lastrowid)


def import_initiative_actuals_csv(
    store: PortfolioStore,
    csv_path: str,
) -> Dict[str, Any]:
    """Bulk ingest. CSV header: deal_id, initiative_id, quarter, ebitda_impact, [notes]."""
    import csv

    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    # B151 fix: fall back from UTF-8 to latin-1 for Excel-exported CSVs
    # B154 fix: close the probe on fallback to avoid fd leak
    _probe = open(csv_path, encoding="utf-8-sig", newline="")
    try:
        _probe.read(1); _probe.seek(0)
        f = _probe
    except UnicodeDecodeError:
        _probe.close()
        f = open(csv_path, encoding="latin-1", newline="")
    with f:
        reader = csv.DictReader(f)
        required = {"deal_id", "initiative_id", "quarter", "ebitda_impact"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV missing required columns: {sorted(missing)}")
        rows = list(reader)

    ingested = 0
    errors: List[str] = []
    for idx, row in enumerate(rows, start=2):
        try:
            record_initiative_actual(
                store,
                deal_id=row["deal_id"].strip(),
                initiative_id=row["initiative_id"].strip(),
                quarter=row["quarter"].strip(),
                ebitda_impact=float(row["ebitda_impact"]),
                notes=(row.get("notes") or "").strip(),
            )
            ingested += 1
        except (ValueError, KeyError) as exc:
            errors.append(f"Line {idx}: {exc}")
    return {"rows_ingested": ingested, "errors": errors}


def initiative_variance_report(
    store: PortfolioStore,
    deal_id: str,
) -> pd.DataFrame:
    """Per-initiative cumulative actual vs underwritten-plan EBITDA impact.

    Plan is derived from the shipped initiatives library's
    ``annual_run_rate``, pro-rated to the number of quarters with actuals
    recorded for that initiative. This is the simplest defensible plan:
    "if we said $4M/year and we're 3 quarters in, plan is $3M cumulative".

    Returns one row per (deal, initiative) pair with ``quarters_active``,
    ``cumulative_actual``, ``cumulative_plan``, ``variance_pct``,
    ``severity`` fields. Empty DataFrame when no actuals recorded.
    """
    _ensure_initiative_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT initiative_id, quarter, ebitda_impact "
            "FROM initiative_actuals WHERE deal_id=? "
            "ORDER BY initiative_id, quarter",
            (deal_id,),
        ).fetchall()

    if not rows:
        return pd.DataFrame(columns=[
            "deal_id", "initiative_id", "quarters_active",
            "cumulative_actual", "cumulative_plan",
            "variance_pct", "severity",
        ])

    library = {i["id"]: i for i in get_all_initiatives() if i.get("id")}

    per_init: Dict[str, List] = {}
    for r in rows:
        per_init.setdefault(r["initiative_id"], []).append(
            (r["quarter"], float(r["ebitda_impact"]))
        )

    out: List[Dict[str, Any]] = []
    for init_id, records in per_init.items():
        quarters_active = len(records)
        cumulative_actual = sum(r[1] for r in records)

        annual_rr = None
        lib_entry = library.get(init_id) or {}
        if lib_entry:
            annual_rr = float(lib_entry.get("annual_run_rate", 0) or 0)
            # Some library entries use delta_mean shocks rather than a dollar
            # run rate — those don't have a direct EBITDA plan, mark no_plan.
            if annual_rr == 0:
                annual_rr = None

        cumulative_plan: Optional[float]
        variance_pct: Optional[float]
        severity: str
        if annual_rr is None or annual_rr == 0:
            cumulative_plan = None
            variance_pct = None
            severity = "no_plan"
        else:
            cumulative_plan = annual_rr * (quarters_active / 4.0)
            if cumulative_plan != 0:
                variance_pct = (cumulative_actual - cumulative_plan) / cumulative_plan
                # Reuse the same severity bands as EBITDA variance
                absv = abs(variance_pct)
                if absv < 0.05:
                    severity = "on_track"
                elif absv < 0.15:
                    severity = "lagging"
                else:
                    severity = "off_track"
            else:
                variance_pct = None
                severity = "no_plan"

        out.append({
            "deal_id": deal_id,
            "initiative_id": init_id,
            "quarters_active": quarters_active,
            "cumulative_actual": cumulative_actual,
            "cumulative_plan": cumulative_plan,
            "variance_pct": variance_pct,
            "severity": severity,
        })
    # Sort so worst-performing initiatives surface first — partner-readable
    return pd.DataFrame(out).sort_values(
        "variance_pct", ascending=True, na_position="last",
    ).reset_index(drop=True)


def format_initiative_variance(df: pd.DataFrame) -> str:
    """Terminal block — one line per initiative, severity-ordered."""
    if df is None or df.empty:
        return "(no initiative actuals recorded)"

    lines = [
        f"Initiative variance — {df.iloc[0]['deal_id']}",
        "─" * 70,
    ]
    glyph = {"on_track": "✓", "lagging": "⚠", "off_track": "✗", "no_plan": "·"}
    for _, r in df.iterrows():
        g = glyph.get(r["severity"], "·")
        actual = f"${r['cumulative_actual']/1e6:.2f}M"
        plan_v = r["cumulative_plan"]
        if plan_v is None or (isinstance(plan_v, float) and plan_v != plan_v):
            plan = "—"
            var = "—"
        else:
            plan = f"${plan_v/1e6:.2f}M"
            var = (
                "—" if r["variance_pct"] is None
                or (isinstance(r["variance_pct"], float) and r["variance_pct"] != r["variance_pct"])
                else f"{r['variance_pct']*100:+.1f}%"
            )
        qtrs = int(r["quarters_active"])
        lines.append(
            f"  {g} {r['initiative_id']:<30s} "
            f"actual {actual:>9s}  plan {plan:>9s}  Δ {var:>7s}  "
            f"({qtrs} qtr)"
        )
    return "\n".join(lines)
