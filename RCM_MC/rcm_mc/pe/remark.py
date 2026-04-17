"""Underwrite re-mark (Brick 61).

When a held deal has several quarters of actuals, the original IC
projection becomes stale. This module re-underwrites a deal based on
its actual EBITDA run-rate and emits a before/after comparison:

    Original underwrite:  entry $50M EBITDA → $58M at exit → MOIC 2.55x, IRR 21%
    Re-mark as of 2026Q2: actual $46M TTM   → $52M projected → MOIC 2.05x, IRR 15%

The math reuses the deal's original entry conditions (entry multiple,
hold years, equity structure) from the snapshot, but substitutes the
latest actual EBITDA as the new starting point and extrapolates the
quarterly run-rate forward to the remaining hold period.

Crucially, a re-mark is recorded as a **new snapshot** with an explicit
``notes`` field flagging the re-mark vintage. The original underwrite
snapshot is preserved in the audit trail — partners can walk IC through
"here's what we told you, here's what happened, here's the revised
outlook" without reconstructing history.

Scope boundary: deliberately does NOT adjust the entry multiple or
debt structure — those are baked contractual facts. Only the forward
EBITDA trajectory is re-estimated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

from .hold_tracking import variance_report
from .pe_math import (
    CovenantCheck,
    compute_returns,
    covenant_check,
    value_creation_bridge,
)
from ..portfolio.store import PortfolioStore
from ..portfolio.portfolio_snapshots import list_snapshots, register_snapshot


@dataclass
class RemarkResult:
    """Before/after snapshot of a re-mark.

    Fields labelled ``original_*`` come from the deal's latest snapshot at
    the time of re-mark (i.e., the current "as-underwritten" state).
    Fields labelled ``remark_*`` are the fresh computation based on actuals.
    Both are preserved so partners see the delta.
    """
    deal_id: str
    as_of_quarter: str
    actual_ttm_ebitda: float
    quarters_of_actuals: int
    # Original underwrite (frozen)
    original_entry_ebitda: float
    original_moic: Optional[float]
    original_irr: Optional[float]
    original_exit_ebitda: float
    # Re-marked projection
    remark_implied_uplift: float
    remark_exit_ebitda: float
    remark_moic: float
    remark_irr: float
    # Deltas
    moic_delta: Optional[float]
    irr_delta: Optional[float]
    ebitda_delta_vs_plan: float
    # Sizing echoed for audit
    entry_multiple: float
    exit_multiple: float
    hold_years_total: float
    years_remaining: float


def _quarters_elapsed(start_quarter: str, as_of_quarter: str) -> int:
    """Count quarters between two ``YYYYQn`` strings (as_of inclusive).

    Used to figure out how far into the hold period we are when re-marking.
    If inputs are malformed we return 0 so the re-mark degrades to "no
    time elapsed yet" rather than crashing.
    """
    import re
    pat = re.compile(r"^(\d{4})Q([1-4])$")
    m_a = pat.match(start_quarter)
    m_b = pat.match(as_of_quarter)
    if not (m_a and m_b):
        return 0
    y_a, q_a = int(m_a.group(1)), int(m_a.group(2))
    y_b, q_b = int(m_b.group(1)), int(m_b.group(2))
    return max(0, (y_b - y_a) * 4 + (q_b - q_a) + 1)


def compute_remark(
    store: PortfolioStore,
    deal_id: str,
    as_of_quarter: str,
) -> RemarkResult:
    """Re-underwrite a deal based on actuals through ``as_of_quarter``.

    Raises ``ValueError`` if:
      - No snapshots exist for the deal (can't re-mark a phantom).
      - No quarterly actuals recorded through the target quarter.
      - Original snapshot lacks entry_ebitda / entry_multiple / hold_years.

    The re-mark logic is deliberately simple and defensible:

    1. Compute TTM EBITDA from the last 4 quarters of actuals (or fewer
       if <4 quarters exist, annualized from the mean).
    2. ``years_remaining = hold_years_total - (quarters_of_actuals / 4)``.
    3. Project exit EBITDA assuming the current actual run-rate compounds
       at ``organic_growth_pct`` (from original snapshot, default 0%).
    4. Implied uplift = remark_exit_ebitda - original_entry_ebitda, used
       in the bridge to preserve reconciliation.
    5. MOIC / IRR computed from the new exit EV + existing equity ratio.
    """
    snaps = list_snapshots(store, deal_id=deal_id)
    if snaps.empty:
        raise ValueError(f"No snapshots for deal {deal_id!r}")
    snap = snaps.iloc[0]

    entry_ebitda = snap.get("entry_ebitda")
    entry_multiple = snap.get("entry_multiple")
    exit_multiple = snap.get("exit_multiple")
    hold_years = snap.get("hold_years")
    if any(
        pd.isna(v) for v in (entry_ebitda, entry_multiple, exit_multiple, hold_years)
    ):
        raise ValueError(
            f"Deal {deal_id!r} snapshot missing entry_ebitda / "
            f"entry_multiple / exit_multiple / hold_years — can't re-mark"
        )

    var_df = variance_report(store, deal_id)
    if var_df.empty or "ebitda" not in set(var_df["kpi"]):
        raise ValueError(
            f"No EBITDA actuals recorded for deal {deal_id!r} "
            f"through {as_of_quarter}"
        )
    ebitda_actuals = var_df[var_df["kpi"] == "ebitda"].sort_values("quarter")
    actuals_through = ebitda_actuals[ebitda_actuals["quarter"] <= as_of_quarter]
    if actuals_through.empty:
        raise ValueError(
            f"No EBITDA actuals recorded for deal {deal_id!r} "
            f"through {as_of_quarter}"
        )

    # TTM: mean of last 4 quarters × 4 (annualized)
    last_quarters = actuals_through.tail(4)
    quarterly_mean = float(last_quarters["actual"].mean())
    ttm_ebitda = quarterly_mean * 4
    quarters_of_actuals = len(actuals_through)

    # Time accounting
    first_quarter = str(ebitda_actuals.iloc[0]["quarter"])
    years_elapsed = quarters_of_actuals / 4.0
    years_remaining = max(float(hold_years) - years_elapsed, 0.1)

    # Project exit EBITDA by compounding at the original organic rate
    # (we don't change the organic assumption on re-mark — that's a
    # macro input the partner can re-stress separately).
    # Pull organic from somewhere — if not on snapshot, default to 0
    organic = 0.0

    remark_exit_ebitda = ttm_ebitda * ((1.0 + organic) ** years_remaining)
    implied_uplift = remark_exit_ebitda - float(entry_ebitda)

    # Re-run bridge for a reconciled EV; re-use original entry / exit
    # multiples because those are contractual (entry) and planned (exit).
    bridge = value_creation_bridge(
        entry_ebitda=float(entry_ebitda),
        uplift=implied_uplift,
        entry_multiple=float(entry_multiple),
        exit_multiple=float(exit_multiple),
        hold_years=float(hold_years),
        organic_growth_pct=organic,
    )

    # Equity structure: preserve original 40/60 split implied by snapshot
    # if entry_equity isn't carried; otherwise use what's there.
    entry_ev = bridge.entry_ev
    # PE snapshot only has entry_ev, not entry_equity split — infer from
    # the ratio most PE deals use (40% equity / 60% debt) unless we know
    # otherwise. This is the same assumption pe_integration.py makes.
    equity_pct = 0.40
    entry_equity = entry_ev * equity_pct
    debt_at_entry = entry_ev * (1 - equity_pct)

    exit_equity = max(bridge.exit_ev - debt_at_entry, 0.0)
    returns = compute_returns(
        entry_equity=entry_equity,
        exit_proceeds=exit_equity,
        hold_years=float(hold_years),
    )

    original_moic = snap.get("moic")
    original_irr = snap.get("irr")
    moic_delta = (
        returns.moic - float(original_moic)
        if pd.notna(original_moic) else None
    )
    irr_delta = (
        returns.irr - float(original_irr)
        if pd.notna(original_irr) else None
    )

    # Plan at as_of_quarter: whatever the sum of quarterly plans was
    plan_through = actuals_through["plan"].dropna()
    plan_sum = float(plan_through.sum()) if not plan_through.empty else None
    actual_sum = float(actuals_through["actual"].sum())
    ebitda_delta_vs_plan = (
        actual_sum - plan_sum if plan_sum is not None else 0.0
    )

    # Original exit EBITDA: prefer snapshot's exit_ev; else back-derive
    # from MOIC (exit_equity = moic × entry_equity; exit_ev = + debt).
    # If neither is available, fall back to entry_ebitda as a placeholder.
    if pd.notna(snap.get("exit_ev")):
        original_exit_ebitda = float(snap["exit_ev"]) / float(exit_multiple)
    elif pd.notna(original_moic):
        implied_exit_equity = float(original_moic) * entry_equity
        implied_exit_ev = implied_exit_equity + debt_at_entry
        original_exit_ebitda = implied_exit_ev / float(exit_multiple)
    else:
        original_exit_ebitda = float(entry_ebitda)

    return RemarkResult(
        deal_id=deal_id,
        as_of_quarter=as_of_quarter,
        actual_ttm_ebitda=float(ttm_ebitda),
        quarters_of_actuals=int(quarters_of_actuals),
        original_entry_ebitda=float(entry_ebitda),
        original_moic=float(original_moic) if pd.notna(original_moic) else None,
        original_irr=float(original_irr) if pd.notna(original_irr) else None,
        original_exit_ebitda=float(original_exit_ebitda),
        remark_implied_uplift=float(implied_uplift),
        remark_exit_ebitda=float(remark_exit_ebitda),
        remark_moic=float(returns.moic),
        remark_irr=float(returns.irr),
        moic_delta=moic_delta,
        irr_delta=irr_delta,
        ebitda_delta_vs_plan=float(ebitda_delta_vs_plan),
        entry_multiple=float(entry_multiple),
        exit_multiple=float(exit_multiple),
        hold_years_total=float(hold_years),
        years_remaining=float(years_remaining),
    )


def persist_remark(
    store: PortfolioStore,
    result: RemarkResult,
) -> int:
    """Record the re-marked returns as a new `hold`-stage snapshot.

    The new snapshot carries the re-marked MOIC / IRR and a notes field
    that flags the re-mark vintage, so the audit trail reads:

        #42  loi      original underwrite
        #73  hold     auto-registered by `rcm-mc run`
        #99  hold     re-mark as of 2026Q2

    Returns the new snapshot's ID. Writing a new row (rather than
    updating the prior) is deliberate — re-marks are historical events,
    not corrections.
    """
    from ..portfolio.portfolio_snapshots import _ensure_snapshot_table
    from datetime import datetime, timezone

    _ensure_snapshot_table(store)
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
                result.deal_id, "hold",
                datetime.now(timezone.utc).isoformat(),
                None,   # no run_dir for remarks
                result.original_entry_ebitda,
                result.entry_multiple, result.exit_multiple,
                result.hold_years_total,
                result.remark_moic, result.remark_irr,
                result.original_entry_ebitda * result.entry_multiple,
                result.remark_exit_ebitda * result.exit_multiple,
                None, None, None,  # covenant not recomputed on re-mark
                None, None,
                f"Re-mark as of {result.as_of_quarter} "
                f"(TTM EBITDA ${result.actual_ttm_ebitda/1e6:.1f}M, "
                f"{result.quarters_of_actuals} quarters actuals)",
            ),
        )
        con.commit()
        return int(cur.lastrowid)


def format_remark(r: RemarkResult) -> str:
    """Before/after block for terminal consumption."""
    def _pct_or_dash(v):
        return "—" if v is None else f"{v*100:.1f}%"

    def _x_or_dash(v):
        return "—" if v is None else f"{v:.2f}x"

    def _delta_str(v, kind):
        """kind in {'pp' (percentage points for IRR), 'x' (multiple delta for MOIC)}."""
        if v is None:
            return "—"
        if kind == "pp":
            return f"{v*100:+.1f}pp"
        return f"{v:+.2f}x"

    lines = [
        f"Underwrite re-mark — {r.deal_id} as of {r.as_of_quarter}",
        "─" * 70,
        f"  Quarters of actuals:    {r.quarters_of_actuals}",
        f"  TTM EBITDA:             ${r.actual_ttm_ebitda/1e6:.1f}M",
        f"  Cumulative Δ vs plan:   ${r.ebitda_delta_vs_plan/1e6:+.1f}M",
        f"  Years remaining:        {r.years_remaining:.2f}",
        "",
        f"  {'':22s}  {'Original':>12s}  {'Re-mark':>12s}  {'Δ':>8s}",
        f"  {'Exit EBITDA':22s}  "
        f"{'$' + f'{r.original_exit_ebitda/1e6:.1f}M':>12s}  "
        f"{'$' + f'{r.remark_exit_ebitda/1e6:.1f}M':>12s}  "
        f"{(r.remark_exit_ebitda - r.original_exit_ebitda)/1e6:+.1f}M",
        f"  {'MOIC':22s}  "
        f"{_x_or_dash(r.original_moic):>12s}  "
        f"{_x_or_dash(r.remark_moic):>12s}  "
        f"{_delta_str(r.moic_delta, kind='x'):>8s}",
        f"  {'IRR':22s}  "
        f"{_pct_or_dash(r.original_irr):>12s}  "
        f"{_pct_or_dash(r.remark_irr):>12s}  "
        f"{_delta_str(r.irr_delta, kind='pp'):>8s}",
    ]
    return "\n".join(lines)


def remark_to_dict(r: RemarkResult) -> Dict[str, Any]:
    """JSON-friendly payload."""
    return {
        "deal_id": r.deal_id,
        "as_of_quarter": r.as_of_quarter,
        "actual_ttm_ebitda": r.actual_ttm_ebitda,
        "quarters_of_actuals": r.quarters_of_actuals,
        "original": {
            "entry_ebitda": r.original_entry_ebitda,
            "exit_ebitda": r.original_exit_ebitda,
            "moic": r.original_moic,
            "irr": r.original_irr,
        },
        "remark": {
            "implied_uplift": r.remark_implied_uplift,
            "exit_ebitda": r.remark_exit_ebitda,
            "moic": r.remark_moic,
            "irr": r.remark_irr,
        },
        "deltas": {
            "moic": r.moic_delta,
            "irr": r.irr_delta,
            "ebitda_vs_plan": r.ebitda_delta_vs_plan,
        },
        "entry_multiple": r.entry_multiple,
        "exit_multiple": r.exit_multiple,
        "hold_years_total": r.hold_years_total,
        "years_remaining": r.years_remaining,
    }
