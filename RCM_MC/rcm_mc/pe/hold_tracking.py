"""Hold-period KPI tracking: actual vs underwritten variance (Brick 52).

After a deal closes, the PE firm receives quarterly management reporting
and compares it against the IC-underwritten plan. This module captures:

- Per-KPI variance (actual vs underwritten, pct_gap + direction)
- Severity classification (on-track / lagging / off-track)
- Cumulative drift over multiple quarters (early warning signal)

Schema: a new ``quarterly_actuals`` table keyed on (deal_id, quarter).
The underwritten plan is pulled from the deal's most-recent pe_bridge
snapshot (entry EBITDA trajectory); actual KPI values come from the
management report the analyst enters.

Kept narrow to RCM-critical KPIs — EBITDA, NPSR, key denial / DAR
metrics. Full-portfolio ops reporting is out of scope.
"""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from ..portfolio.store import PortfolioStore


# Canonical KPIs we track each quarter. Keeping this tight avoids the
# "track everything" trap that makes variance reports unreadable.
TRACKED_KPIS: tuple = (
    "ebitda",                  # trailing-12-month EBITDA
    "net_patient_revenue",     # TTM NPSR
    "idr_blended",             # Initial denial rate, blended
    "fwr_blended",             # Final write-off rate
    "dar_clean_days",          # Days-A/R clean claims
)


# Severity thresholds — fractional variance below which we call it
# "on_track" vs "lagging" vs "off_track". Conservative: a 5% miss on
# EBITDA is meaningful in PE; 15%+ is a board-escalation event.
_SEVERITY_BANDS = [
    ("on_track",  0.05),   # |variance| < 5%
    ("lagging",   0.15),   # 5% ≤ |variance| < 15%
    ("off_track", float("inf")),  # ≥ 15%
]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_actuals_table(store: PortfolioStore) -> None:
    """Create the quarterly_actuals table. Idempotent."""
    store.init_db()
    with store.connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS quarterly_actuals (
                actual_id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id TEXT NOT NULL,
                quarter TEXT NOT NULL,          -- "2026Q2" format
                created_at TEXT NOT NULL,
                kpis_json TEXT NOT NULL,         -- {"ebitda": 52.5e6, ...}
                plan_kpis_json TEXT,             -- {"ebitda": 50e6, ...} at IC
                notes TEXT,
                FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
            )"""
        )
        con.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_actuals_deal_qtr "
            "ON quarterly_actuals(deal_id, quarter)"
        )
        con.commit()


# ── Public API ─────────────────────────────────────────────────────────────

def import_actuals_csv(
    store: PortfolioStore,
    csv_path: str,
    *,
    strict: bool = True,
) -> Dict[str, Any]:
    """Bulk-ingest one or more quarters of actuals from a management-reporting CSV.

    Expected CSV schema (wide):
        deal_id, quarter, ebitda, net_patient_revenue, idr_blended,
        fwr_blended, dar_clean_days, plan_ebitda, plan_net_patient_revenue, ...

    Rules:

    - ``deal_id`` + ``quarter`` columns are required.
    - Any other column must match a key in :data:`TRACKED_KPIS`
      (optionally prefixed ``plan_``). Unknown columns raise in strict
      mode; otherwise they're ignored with a warning.
    - Rows upsert on ``(deal_id, quarter)`` — re-running the import
      overwrites, which matches how PE firms re-issue corrected decks.
    - Blank / NaN cells are skipped (no value recorded for that KPI).

    Returns a summary dict:
        ``{"rows_ingested": N, "deals": [...], "quarters": [...],
            "warnings": [...], "errors": [...]}``

    Raises ``ValueError`` in strict mode if required columns are missing
    or unknown columns are present.
    """
    import csv

    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    # B151 fix: fall back from UTF-8 to latin-1 for Excel-exported CSVs
    # B154 fix: close the probe handle in the fallback path to prevent
    # leaking file descriptors when many CP1252 files are imported.
    _probe = open(csv_path, encoding="utf-8-sig", newline="")
    try:
        _probe.read(1); _probe.seek(0)
        f = _probe
    except UnicodeDecodeError:
        _probe.close()
        f = open(csv_path, encoding="latin-1", newline="")
    with f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)

    missing_required = [k for k in ("deal_id", "quarter") if k not in headers]
    if missing_required:
        raise ValueError(
            f"CSV missing required column(s): {missing_required}. "
            "Expected header row with 'deal_id,quarter,<kpi>,...'."
        )

    allowed_kpi_headers = set(TRACKED_KPIS)
    allowed_plan_headers = {f"plan_{k}" for k in TRACKED_KPIS}
    allowed_headers = {"deal_id", "quarter", "notes"} | allowed_kpi_headers | allowed_plan_headers
    unknown = [h for h in headers if h not in allowed_headers]
    warnings: List[str] = []
    if unknown:
        msg = (
            f"Unknown column(s): {unknown}. "
            f"Allowed: deal_id, quarter, notes, "
            f"{sorted(allowed_kpi_headers)}, "
            f"plan_* variants of the same."
        )
        if strict:
            raise ValueError(msg)
        warnings.append(msg)

    errors: List[str] = []
    ingested = 0
    seen_deals: set = set()
    seen_quarters: set = set()

    for idx, row in enumerate(rows, start=2):  # +2: header row is line 1
        deal_id = (row.get("deal_id") or "").strip()
        quarter = (row.get("quarter") or "").strip()
        if not (deal_id and quarter):
            errors.append(f"Line {idx}: missing deal_id or quarter, skipping")
            continue

        actuals = {}
        plan = {}
        for kpi in TRACKED_KPIS:
            v = row.get(kpi, "")
            if v is not None and str(v).strip():
                try:
                    actuals[kpi] = float(v)
                except ValueError:
                    errors.append(f"Line {idx}: {kpi}={v!r} not numeric")
            pv = row.get(f"plan_{kpi}", "")
            if pv is not None and str(pv).strip():
                try:
                    plan[kpi] = float(pv)
                except ValueError:
                    errors.append(f"Line {idx}: plan_{kpi}={pv!r} not numeric")

        if not actuals:
            errors.append(f"Line {idx}: no KPI values on row for {deal_id}/{quarter}")
            continue

        try:
            record_quarterly_actuals(
                store, deal_id=deal_id, quarter=quarter,
                actuals=actuals, plan=plan or None,
                notes=(row.get("notes") or "").strip(),
            )
            ingested += 1
            seen_deals.add(deal_id)
            seen_quarters.add(quarter)
        except ValueError as exc:
            errors.append(f"Line {idx}: {exc}")

    return {
        "rows_ingested": ingested,
        "deals": sorted(seen_deals),
        "quarters": sorted(seen_quarters),
        "warnings": warnings,
        "errors": errors,
    }


def record_quarterly_actuals(
    store: PortfolioStore,
    deal_id: str,
    quarter: str,
    actuals: Dict[str, float],
    plan: Optional[Dict[str, float]] = None,
    notes: str = "",
) -> int:
    """Persist one quarter's actuals for a deal. Upserts on (deal_id, quarter).

    Parameters
    ----------
    quarter
        ``"YYYY Q{n}"`` or ``"YYYYQn"`` string; stored normalized to ``YYYYQn``.
    actuals
        Dict of KPI → value for the reporting quarter (only keys in
        :data:`TRACKED_KPIS` are accepted; unknown keys rejected to
        prevent silent typos in management-reporting ingest).
    plan
        Underwritten plan values for this quarter. If None, later variance
        calls try to pull from the most-recent pe_bridge snapshot.
    """
    import re
    qtr = quarter.replace(" ", "").upper()
    if not re.fullmatch(r"\d{4}Q[1-4]", qtr):
        raise ValueError(f"quarter must be 'YYYYQn' format (got {quarter!r})")

    # Reject unknown KPIs — a typo like 'ebidta' would silently drop the value
    unknown = set(actuals.keys()) - set(TRACKED_KPIS)
    if unknown:
        raise ValueError(
            f"Unknown KPI(s) {sorted(unknown)}. "
            f"TRACKED_KPIS = {TRACKED_KPIS}"
        )

    _ensure_actuals_table(store)
    store.upsert_deal(deal_id)

    kpis_json = json.dumps({k: float(v) for k, v in actuals.items() if v is not None})
    plan_json = json.dumps({k: float(v) for k, v in (plan or {}).items() if v is not None})

    with store.connect() as con:
        # Upsert via delete-then-insert on the unique index
        con.execute(
            "DELETE FROM quarterly_actuals WHERE deal_id=? AND quarter=?",
            (deal_id, qtr),
        )
        cur = con.execute(
            "INSERT INTO quarterly_actuals "
            "(deal_id, quarter, created_at, kpis_json, plan_kpis_json, notes) "
            "VALUES (?,?,?,?,?,?)",
            (deal_id, qtr, _utcnow(), kpis_json, plan_json, notes),
        )
        con.commit()
        return int(cur.lastrowid)


def _classify_severity(variance_pct: float) -> str:
    """Return 'on_track' | 'lagging' | 'off_track' for a fractional variance."""
    absv = abs(variance_pct)
    for label, threshold in _SEVERITY_BANDS:
        if absv < threshold:
            return label
    return "off_track"


def _plan_for_deal(store: PortfolioStore, deal_id: str) -> Dict[str, float]:
    """Best-effort pull of the underwritten plan for a deal.

    Order:
    1. If the most-recent actuals row carries an embedded ``plan_kpis_json``
       with EBITDA, use that as the frozen IC underwrite.
    2. Otherwise fall back to the most-recent snapshot's entry_ebitda (as
       a one-field plan) — enough to flag EBITDA variance even without a
       full plan.
    """
    _ensure_actuals_table(store)
    with store.connect() as con:
        row = con.execute(
            "SELECT plan_kpis_json FROM quarterly_actuals "
            "WHERE deal_id=? AND plan_kpis_json != '{}' "
            "ORDER BY quarter DESC LIMIT 1",
            (deal_id,),
        ).fetchone()
    if row and row["plan_kpis_json"]:
        try:
            plan = json.loads(row["plan_kpis_json"])
            if plan:
                return plan
        except json.JSONDecodeError:
            pass

    # Fallback: entry_ebitda from the latest deal snapshot
    from ..portfolio.portfolio_snapshots import list_snapshots
    snaps = list_snapshots(store, deal_id=deal_id)
    if not snaps.empty:
        ebitda = snaps.iloc[0].get("entry_ebitda")
        if ebitda is not None and pd.notna(ebitda):
            return {"ebitda": float(ebitda)}
    return {}


def variance_report(
    store: PortfolioStore,
    deal_id: str,
) -> pd.DataFrame:
    """Return a DataFrame of all quarters × KPIs with actual, plan, variance,
    and severity for one deal. Oldest → newest.

    One row per (quarter, kpi) pair so the output plays well with
    Excel pivot tables and time-series charts.
    """
    _ensure_actuals_table(store)
    with store.connect() as con:
        rows = con.execute(
            "SELECT quarter, kpis_json, plan_kpis_json FROM quarterly_actuals "
            "WHERE deal_id=? ORDER BY quarter ASC",
            (deal_id,),
        ).fetchall()
    if not rows:
        return pd.DataFrame(columns=[
            "deal_id", "quarter", "kpi", "actual", "plan",
            "variance_pct", "severity",
        ])

    # Resolve a plan: per-row plan if present, else deal-wide fallback
    fallback_plan = _plan_for_deal(store, deal_id)

    out_rows: List[Dict[str, Any]] = []
    for r in rows:
        qtr = r["quarter"]
        actuals = json.loads(r["kpis_json"] or "{}")
        row_plan = json.loads(r["plan_kpis_json"] or "{}")
        combined_plan = {**fallback_plan, **row_plan}  # row-specific wins

        for kpi, actual in actuals.items():
            plan_v = combined_plan.get(kpi)
            if plan_v is None or plan_v == 0:
                variance_pct = None
                severity = "no_plan"
            else:
                variance_pct = (actual - plan_v) / plan_v
                severity = _classify_severity(variance_pct)
            out_rows.append({
                "deal_id": deal_id,
                "quarter": qtr,
                "kpi": kpi,
                "actual": float(actual),
                "plan": float(plan_v) if plan_v is not None else None,
                "variance_pct": variance_pct,
                "severity": severity,
            })
    return pd.DataFrame(out_rows)


def portfolio_variance_matrix(
    store: PortfolioStore,
    *,
    kpi: str = "ebitda",
    quarter: Optional[str] = None,
) -> pd.DataFrame:
    """Latest-quarter variance per deal for one KPI (Brick 108).

    Returns one row per deal with columns: deal_id, quarter, kpi,
    actual, plan, variance_pct, severity. Sorted worst-variance first
    so the partner's eye lands on misses immediately.

    ``quarter=None`` (default) uses each deal's own most-recent quarter,
    which is what partners usually want ("how's everyone doing *now*").
    Pass a specific quarter ("2026Q1") to pin the view when writing LP
    commentary.
    """
    from ..portfolio.portfolio_snapshots import latest_per_deal
    deals = latest_per_deal(store)
    if deals.empty:
        return pd.DataFrame(columns=[
            "deal_id", "quarter", "kpi", "actual", "plan",
            "variance_pct", "severity",
        ])

    out_rows = []
    for _, r in deals.iterrows():
        did = str(r["deal_id"])
        vdf = variance_report(store, did)
        if vdf.empty:
            continue
        sub = vdf[vdf["kpi"] == kpi]
        if sub.empty:
            continue
        if quarter is not None:
            row = sub[sub["quarter"] == quarter]
            if row.empty:
                continue
            row = row.iloc[-1]
        else:
            row = sub.sort_values("quarter").iloc[-1]
        out_rows.append(row.to_dict())

    df = pd.DataFrame(out_rows)
    if df.empty:
        return df
    # Sort: explicit NaN-safe worst-first, using variance_pct
    df = df.copy()
    # NaN (no_plan) goes to the bottom; large negative (miss) goes on top
    df["_sortkey"] = df["variance_pct"].fillna(1.0)
    df = df.sort_values("_sortkey").drop(columns=["_sortkey"]).reset_index(drop=True)
    return df


def cumulative_drift(
    store: PortfolioStore,
    deal_id: str,
    kpi: str = "ebitda",
) -> pd.DataFrame:
    """Quarter-over-quarter cumulative drift on one KPI.

    For ``ebitda`` specifically, multi-quarter drift is the strongest
    early-warning signal that a deal is slipping — three consecutive
    sub-plan quarters almost always becomes a covenant-reset conversation.

    Returns a DataFrame with ``quarter``, ``variance_pct``,
    ``cumulative_drift`` (sum of variances) columns.
    """
    df = variance_report(store, deal_id)
    if df.empty:
        return df
    kpi_df = df[df["kpi"] == kpi].copy()
    if kpi_df.empty:
        return kpi_df
    kpi_df["cumulative_drift"] = kpi_df["variance_pct"].cumsum()
    return kpi_df[["quarter", "actual", "plan", "variance_pct",
                   "cumulative_drift", "severity"]].reset_index(drop=True)


# ── Terminal formatter ─────────────────────────────────────────────────────

def format_variance_report(df: pd.DataFrame) -> str:
    """One block per quarter with per-KPI severity indicators."""
    if df is None or df.empty:
        return "(no quarterly actuals recorded)"

    lines = [
        f"Quarterly variance — {df.iloc[0]['deal_id']}",
        "─" * 64,
    ]
    sev_glyph = {
        "on_track":  "✓",
        "lagging":   "⚠",
        "off_track": "✗",
        "no_plan":   "·",
    }
    for quarter, grp in df.groupby("quarter"):
        lines.append(f"\n  {quarter}")
        for _, r in grp.iterrows():
            g = sev_glyph.get(r["severity"], "·")
            actual = r["actual"]
            plan = r["plan"]
            var_pct = r["variance_pct"]
            # Pandas coerces None → NaN in numeric columns. Normalize so the
            # formatters below only have to check `is None`.
            if plan is not None and isinstance(plan, float) and plan != plan:
                plan = None
            if var_pct is not None and isinstance(var_pct, float) and var_pct != var_pct:
                var_pct = None
            # Numeric formatting: ratios for denial/fwr, money for EBITDA/NPSR,
            # days for DAR. Kept inline to avoid another format module.
            if r["kpi"] in ("idr_blended", "fwr_blended"):
                a_str = f"{actual*100:.1f}%"
                p_str = "—" if plan is None else f"{plan*100:.1f}%"
            elif r["kpi"] == "dar_clean_days":
                a_str = f"{actual:.1f}d"
                p_str = "—" if plan is None else f"{plan:.1f}d"
            else:  # money
                a_str = f"${actual/1e6:.1f}M" if abs(actual) < 1e9 else f"${actual/1e9:.2f}B"
                p_str = ("—" if plan is None
                         else (f"${plan/1e6:.1f}M" if abs(plan) < 1e9 else f"${plan/1e9:.2f}B"))
            v_str = "—" if var_pct is None else f"{var_pct*100:+.1f}%"
            lines.append(
                f"    {g} {r['kpi']:<22s} actual {a_str:>10s}  "
                f"plan {p_str:>10s}  Δ {v_str:>7s}"
            )
    return "\n".join(lines)
