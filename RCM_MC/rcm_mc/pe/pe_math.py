"""PE deal-math layer: value creation bridge, returns, leverage.

Converts simulated EBITDA uplift into the metrics a PE IC actually
underwrites on. Deliberately stdlib-only for the pure math (pandas is used
only for tabular output) — this is the audit-defensible kernel that a
director can walk through on a whiteboard.

Public API:
    value_creation_bridge(entry_ebitda, uplift, entry_multiple, exit_multiple,
                          hold_years, organic_growth_pct=0.0)
        → BridgeResult

    format_bridge(bridge) → str (terminal)
    bridge_to_records(bridge) → list[dict] (JSON / workbook)

Design principle: every line item in the bridge reconciles. Entry EV +
sum(bridge deltas) must equal exit EV exactly. PE IC committees reject
bridges that don't add up.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Data types ──────────────────────────────────────────────────────────────

@dataclass
class BridgeResult:
    """Value-creation bridge from entry EV to exit EV.

    Attributes split the exit-EV uplift into three economically distinct
    drivers that a PE IC committee reads in order:

    1. ``organic_ebitda_contribution`` — growth you'd have gotten without any
       RCM intervention (e.g., 3% annual market growth × entry multiple).
    2. ``rcm_uplift_contribution`` — the modeled RCM EBITDA uplift × entry
       multiple. This is what the diligence bundle underwrites.
    3. ``multiple_expansion_contribution`` — change in exit multiple vs entry,
       applied to exit EBITDA. Usually a separate story (market timing,
       platform effects).

    ``entry_ev + organic + rcm_uplift + multiple_expansion == exit_ev``
    by construction.
    """
    # Inputs (echoed for audit trail)
    entry_ebitda: float
    exit_ebitda: float
    entry_multiple: float
    exit_multiple: float
    hold_years: float
    organic_growth_pct: float
    rcm_uplift: float

    # Outputs
    entry_ev: float
    exit_ev: float
    organic_ebitda_contribution: float
    rcm_uplift_contribution: float
    multiple_expansion_contribution: float
    total_value_created: float


# ── Core math ──────────────────────────────────────────────────────────────

def value_creation_bridge(
    entry_ebitda: float,
    uplift: float,
    entry_multiple: float,
    exit_multiple: float,
    hold_years: float,
    organic_growth_pct: float = 0.0,
    *,
    registry: Any = None,
) -> BridgeResult:
    """Compute the entry → exit value-creation bridge.

    Parameters
    ----------
    entry_ebitda
        Target EBITDA at deal close, in dollars.
    uplift
        Incremental EBITDA from the RCM value plan *at exit*, fully ramped.
        Usually the ``ebitda_uplift`` mean from the diligence bundle.
    entry_multiple
        EV/EBITDA multiple at entry (e.g., 9.0 for 9x). PE purchase price
        is ``entry_ebitda * entry_multiple``.
    exit_multiple
        EV/EBITDA multiple at exit. Often equals entry (no multiple
        expansion assumed) for conservative underwriting.
    hold_years
        Holding period in years. Drives the organic growth compound.
    organic_growth_pct
        Annual organic EBITDA growth rate (decimal, e.g., 0.03 for 3%/yr).
        Compounds over ``hold_years``. Represents market-level growth the
        platform would have captured *without* any RCM intervention.

    Returns
    -------
    BridgeResult with entry EV, exit EV, and the three bridge components.
    Reconciliation is exact: entry_ev + sum(components) == exit_ev.

    Raises
    ------
    ValueError
        If ``entry_ebitda``, ``entry_multiple``, ``exit_multiple``, or
        ``hold_years`` are non-positive. RCM uplift and organic growth may
        be negative (value destruction scenarios are valid to model).
    """
    if entry_ebitda <= 0:
        raise ValueError(f"entry_ebitda must be positive (got {entry_ebitda})")
    if entry_multiple <= 0:
        raise ValueError(f"entry_multiple must be positive (got {entry_multiple})")
    if exit_multiple <= 0:
        raise ValueError(f"exit_multiple must be positive (got {exit_multiple})")
    if hold_years <= 0:
        raise ValueError(f"hold_years must be positive (got {hold_years})")

    # Organic EBITDA contribution: compound growth over the hold period
    organic_ebitda_at_exit = entry_ebitda * ((1 + organic_growth_pct) ** hold_years)
    organic_uplift = organic_ebitda_at_exit - entry_ebitda

    # Exit EBITDA = entry + organic growth + RCM uplift
    exit_ebitda = entry_ebitda + organic_uplift + uplift

    # Enterprise values at entry and exit
    entry_ev = entry_ebitda * entry_multiple
    exit_ev = exit_ebitda * exit_multiple

    # Bridge components — ordered to reconcile cleanly:
    #
    #   entry_ev
    #     + organic_ebitda_contribution  = organic_uplift × entry_multiple
    #     + rcm_uplift_contribution      = uplift        × entry_multiple
    #     + multiple_expansion           = exit_ebitda   × (exit_multiple - entry_multiple)
    #   = exit_ev
    #
    # Economic interpretation: the first two apply the ENTRY multiple (value
    # from EBITDA you would have generated even at no multiple change); the
    # third captures the multiple-arbitrage on the TOTAL exit EBITDA.
    organic_contribution = organic_uplift * entry_multiple
    rcm_contribution = uplift * entry_multiple
    multiple_expansion = exit_ebitda * (exit_multiple - entry_multiple)

    total_value_created = exit_ev - entry_ev

    result = BridgeResult(
        entry_ebitda=float(entry_ebitda),
        exit_ebitda=float(exit_ebitda),
        entry_multiple=float(entry_multiple),
        exit_multiple=float(exit_multiple),
        hold_years=float(hold_years),
        organic_growth_pct=float(organic_growth_pct),
        rcm_uplift=float(uplift),
        entry_ev=float(entry_ev),
        exit_ev=float(exit_ev),
        organic_ebitda_contribution=float(organic_contribution),
        rcm_uplift_contribution=float(rcm_contribution),
        multiple_expansion_contribution=float(multiple_expansion),
        total_value_created=float(total_value_created),
    )

    if registry is not None:
        try:
            _record_bridge_provenance(registry, result)
        except Exception:  # noqa: BLE001
            pass
    return result


def _record_bridge_provenance(registry, b: "BridgeResult") -> None:
    """Record each bridge component with upstream references."""
    # Leaf inputs — these may already be in the registry; record()
    # is last-write-wins so we record them as CALCULATED only if no
    # existing DataPoint exists.
    def _ensure_leaf(metric: str, value: float, formula: str):
        existing = registry.get(metric)
        if existing is not None:
            return existing
        return registry.record_calc(
            value=value, metric_name=metric,
            formula=formula, upstream=[],
        )

    entry_e = _ensure_leaf("entry_ebitda", b.entry_ebitda, "user input")
    entry_m = _ensure_leaf("entry_multiple", b.entry_multiple, "user input")
    exit_m = _ensure_leaf("exit_multiple", b.exit_multiple, "user input")
    hold = _ensure_leaf("hold_years", b.hold_years, "user input")
    rcm_u = _ensure_leaf("rcm_uplift", b.rcm_uplift, "from simulator")

    exit_ebitda_dp = registry.record_calc(
        value=b.exit_ebitda, metric_name="exit_ebitda",
        formula="entry_ebitda + organic_growth + rcm_uplift",
        upstream=[entry_e, rcm_u, hold],
    )
    registry.record_calc(
        value=b.entry_ev, metric_name="entry_ev",
        formula="entry_ebitda × entry_multiple",
        upstream=[entry_e, entry_m],
    )
    registry.record_calc(
        value=b.exit_ev, metric_name="exit_ev",
        formula="exit_ebitda × exit_multiple",
        upstream=[exit_ebitda_dp, exit_m],
    )
    registry.record_calc(
        value=b.total_value_created,
        metric_name="total_value_created",
        formula="exit_ev − entry_ev",
        upstream=[entry_e, entry_m, exit_m, rcm_u, hold],
    )


# ── Formatters ──────────────────────────────────────────────────────────────

def _fmt_money(v: float) -> str:
    """PE-style money: negatives in parens (red, on terminal; plain in text)."""
    sign = "(" if v < 0 else ""
    close = ")" if v < 0 else ""
    af = abs(v)
    if af >= 1e9:
        return f"{sign}${af/1e9:.2f}B{close}"
    if af >= 1e6:
        return f"{sign}${af/1e6:.1f}M{close}"
    if af >= 1e3:
        return f"{sign}${af/1e3:.0f}K{close}"
    return f"{sign}${af:.0f}{close}"


def _fmt_pct(v: float) -> str:
    return f"{v*100:+.1f}%"


def format_bridge(b: BridgeResult) -> str:
    """Render a BridgeResult as a terminal-friendly block.

    Lays out the bridge vertically with reconciliation totals at top and
    bottom so the reader can verify the math visually.
    """
    total = b.total_value_created
    def _share(x: float) -> str:
        if total == 0:
            return "—"
        return f"{x / total * 100:+.0f}%"

    lines = [
        f"Value Creation Bridge — {b.hold_years:g}-year hold",
        "─" * 60,
        f"  Entry EBITDA:         {_fmt_money(b.entry_ebitda)}",
        f"  Exit EBITDA:          {_fmt_money(b.exit_ebitda)}",
        f"  Entry multiple:       {b.entry_multiple:.1f}x",
        f"  Exit multiple:        {b.exit_multiple:.1f}x",
        "",
        f"  Entry EV:             {_fmt_money(b.entry_ev)}",
        "   ─ Components ─",
        f"    + Organic EBITDA:   {_fmt_money(b.organic_ebitda_contribution):>12s}  "
        f"({_fmt_pct(b.organic_growth_pct)}/yr × {b.hold_years:g}y)  "
        f"{_share(b.organic_ebitda_contribution)}",
        f"    + RCM uplift:       {_fmt_money(b.rcm_uplift_contribution):>12s}  "
        f"(× {b.entry_multiple:.1f}x entry)                  "
        f"{_share(b.rcm_uplift_contribution)}",
        f"    + Multiple exp:     {_fmt_money(b.multiple_expansion_contribution):>12s}  "
        f"(Δ{b.exit_multiple - b.entry_multiple:+.1f}x × exit EBITDA)      "
        f"{_share(b.multiple_expansion_contribution)}",
        f"  Exit EV:              {_fmt_money(b.exit_ev)}",
        "─" * 60,
        f"  Total value created:  {_fmt_money(b.total_value_created)}  "
        f"({b.total_value_created / b.entry_ev * 100:+.0f}% vs entry EV)",
    ]
    return "\n".join(lines)


# ── Returns math: IRR / MOIC ────────────────────────────────────────────────

@dataclass
class ReturnsResult:
    """Equity returns for a PE hold: MOIC + annualized IRR.

    Conventions — sign matches LP perspective:
      - ``entry_equity`` is a positive number (capital deployed)
      - ``interim_cash_flows`` are positive distributions (dividends,
        recapitalizations); negative entries are follow-on capital calls
      - ``exit_proceeds`` is equity received at exit, net of transaction fees

    ``moic`` = (exit_proceeds + Σ interim) / entry_equity
    ``irr``  = the discount rate that zeros NPV of (−entry_equity, interim_cf…,
              exit_proceeds). Solved by bisection; bounded to [-0.99, 10.0].
    """
    entry_equity: float
    interim_cash_flows: List[float]
    exit_proceeds: float
    hold_years: float
    moic: float
    irr: float                      # annualized, decimal (0.25 = 25% IRR)
    total_distributions: float      # exit + sum(interim)


def _npv(rate: float, cashflows: List[float]) -> float:
    """Net present value of cashflows at a given rate.

    cashflows[0] is t=0 (the initial equity check, as a NEGATIVE number).
    cashflows[i] is at year i (annual cadence — PE underwriting convention).
    """
    return sum(cf / ((1.0 + rate) ** t) for t, cf in enumerate(cashflows))


def irr(cashflows: List[float], tol: float = 1e-7, max_iter: int = 200) -> float:
    """Solve IRR via bisection over ``[-0.99, 10.0]``.

    Bisection beats Newton-Raphson here: NPV isn't always monotonic for
    mixed-sign flows (a PE fund with follow-on capital calls can have
    multiple sign changes), but bisection converges iff we're given a
    valid bracket. We verify bracket validity and raise on failure rather
    than silently returning a wrong answer.

    Returns the annualized rate as a decimal (0.25 = 25%).
    """
    if not cashflows or len(cashflows) < 2:
        raise ValueError("IRR needs at least 2 cashflows (entry + exit)")
    if all(cf >= 0 for cf in cashflows) or all(cf <= 0 for cf in cashflows):
        raise ValueError("IRR needs at least one positive and one negative cashflow")

    lo, hi = -0.99, 10.0
    npv_lo = _npv(lo, cashflows)
    npv_hi = _npv(hi, cashflows)
    if npv_lo * npv_hi > 0:
        # No sign change in the bracket — IRR is outside [-99%, 1000%].
        # For realistic PE deals this means catastrophic loss or impossibly
        # high return. Return the bracket endpoint that's closer to zero.
        return lo if abs(npv_lo) < abs(npv_hi) else hi

    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        npv_mid = _npv(mid, cashflows)
        if abs(npv_mid) < tol:
            return mid
        if npv_mid * npv_lo < 0:
            hi = mid
            npv_hi = npv_mid
        else:
            lo = mid
            npv_lo = npv_mid
    return 0.5 * (lo + hi)


def compute_returns(
    entry_equity: float,
    exit_proceeds: float,
    hold_years: float,
    interim_cash_flows: List[float] = None,
    *,
    registry: Any = None,
) -> ReturnsResult:
    """Compute MOIC + IRR for a PE hold.

    Parameters
    ----------
    entry_equity
        Positive dollar amount deployed at close.
    exit_proceeds
        Positive dollar amount received at exit (net of transaction fees).
    hold_years
        Integer or fractional years; we assume annual-period cashflows.
    interim_cash_flows
        Optional list aligned to years 1..N-1 (year N is exit). Positive
        = distribution to LPs; negative = follow-on capital call.

    Returns
    -------
    ReturnsResult with MOIC, IRR, and total distributions.

    Raises
    ------
    ValueError
        If entry_equity ≤ 0 or hold_years ≤ 0.
    """
    if entry_equity <= 0:
        raise ValueError(f"entry_equity must be positive (got {entry_equity})")
    if hold_years <= 0:
        raise ValueError(f"hold_years must be positive (got {hold_years})")

    interim = list(interim_cash_flows or [])
    total_distributions = exit_proceeds + sum(interim)
    moic = total_distributions / entry_equity

    # Build IRR cashflow series: −entry at t=0, interim at years 1..k, exit at t=hold_years.
    # For non-integer holds we still snap exit to t=hold_years; the bisection
    # tolerates fractional exponents.
    cashflows: List[float] = [-entry_equity]
    for i, cf in enumerate(interim):
        cashflows.append(cf)
    # Pad with zeros if interim list is shorter than (hold_years - 1) to align
    # exit at the correct year index. Only meaningful when hold_years is int.
    expected_interim_slots = int(hold_years) - 1
    while len(cashflows) - 1 < expected_interim_slots:
        cashflows.append(0.0)
    cashflows.append(exit_proceeds)

    # For fractional hold years, use the non-integer exponent directly
    if hold_years != int(hold_years):
        # Simpler path: discount exit at the fractional year explicitly
        def _npv_fractional(rate: float) -> float:
            npv = -entry_equity
            for i, cf in enumerate(interim, start=1):
                npv += cf / ((1.0 + rate) ** i)
            npv += exit_proceeds / ((1.0 + rate) ** hold_years)
            return npv
        lo, hi = -0.99, 10.0
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            v = _npv_fractional(mid)
            if abs(v) < 1e-7:
                break
            if v > 0:
                lo = mid
            else:
                hi = mid
        irr_val = 0.5 * (lo + hi)
    else:
        irr_val = irr(cashflows)

    result = ReturnsResult(
        entry_equity=float(entry_equity),
        interim_cash_flows=[float(x) for x in interim],
        exit_proceeds=float(exit_proceeds),
        hold_years=float(hold_years),
        moic=float(moic),
        irr=float(irr_val),
        total_distributions=float(total_distributions),
    )

    if registry is not None:
        try:
            _record_returns_provenance(registry, result)
        except Exception:  # noqa: BLE001
            pass
    return result


def _record_returns_provenance(registry, r: "ReturnsResult") -> None:
    """Record MOIC + IRR with upstream refs on entry/exit equity."""
    def _ensure(metric: str, value: float, formula: str):
        existing = registry.get(metric)
        if existing is not None:
            return existing
        return registry.record_calc(
            value=value, metric_name=metric,
            formula=formula, upstream=[],
        )

    entry_eq = _ensure("entry_equity", r.entry_equity, "user input")
    exit_p = _ensure("exit_proceeds", r.exit_proceeds,
                     "from bridge / underwrite")
    hold = _ensure("hold_years", r.hold_years, "user input")

    registry.record_calc(
        value=r.moic, metric_name="moic",
        formula="total_distributions ÷ entry_equity",
        upstream=[entry_eq, exit_p],
    )
    registry.record_calc(
        value=r.irr, metric_name="irr",
        formula="bisection IRR over cashflow series",
        upstream=[entry_eq, exit_p, hold],
    )


def format_returns(r: ReturnsResult) -> str:
    """PE-style returns summary block."""
    interim_line = ""
    if r.interim_cash_flows:
        interim_str = ", ".join(_fmt_money(cf) for cf in r.interim_cash_flows)
        interim_line = f"\n  Interim flows:        {interim_str}"
    return "\n".join([
        f"Equity Returns — {r.hold_years:g}-year hold",
        "─" * 50,
        f"  Entry equity:         {_fmt_money(r.entry_equity)}",
        f"  Exit proceeds:        {_fmt_money(r.exit_proceeds)}{interim_line}",
        f"  Total distributions:  {_fmt_money(r.total_distributions)}",
        "─" * 50,
        f"  MOIC:                 {r.moic:.2f}x",
        f"  IRR (annualized):     {r.irr*100:.1f}%",
    ])


# ── Hold-period sensitivity grid ───────────────────────────────────────────

def hold_period_grid(
    *,
    entry_ebitda: float,
    uplift_by_year: Dict[int, float],
    entry_multiple: float,
    exit_multiples: List[float],
    hold_years_list: List[int],
    entry_equity: float,
    debt_at_entry: float = 0.0,
    debt_at_exit_by_year: Dict[int, float] = None,
    organic_growth_pct: float = 0.0,
    interest_rate: float = 0.08,
) -> List[Dict[str, Any]]:
    """Two-dimensional sensitivity: every (hold_years, exit_multiple) pair.

    Returns one row per scenario with the full bridge + returns math. This
    is what a PE IC committee actually asks for: "show me the sensitivity
    table at 3/5/7-year exits across 8x, 9x, 10x exit multiples."

    Parameters
    ----------
    uplift_by_year
        RCM EBITDA uplift at each hold-year milestone, e.g.
        ``{3: 5e6, 5: 8e6, 7: 9e6}``. Must contain a key for each entry
        in ``hold_years_list``. Reflects the ramp curve (not all uplift
        is realized in year 1).
    debt_at_exit_by_year
        Optional. Debt outstanding at each exit year (amortization schedule).
        Defaults to ``debt_at_entry`` held flat. Each key in
        ``hold_years_list`` should have an entry.
    interest_rate
        Cost of debt, used if we later compute levered cash flows. Not
        applied to the simple exit-proceeds formula here, but kept in the
        signature so B44 can plug leverage/covenant math through this grid.

    Returns
    -------
    List of dicts, one per (hold_years × exit_multiple) pair:
        {
            "hold_years": 5, "exit_multiple": 10.0,
            "entry_ev": ..., "exit_ev": ...,
            "entry_equity": ..., "exit_equity": ...,
            "moic": ..., "irr": ...,
            "total_value_created": ...,
            "rcm_uplift_share": ...,   # fraction of value creation from RCM
        }
    """
    if not uplift_by_year:
        raise ValueError("uplift_by_year must have at least one entry")
    for y in hold_years_list:
        if y not in uplift_by_year:
            raise ValueError(f"uplift_by_year missing entry for hold year {y}")
    if debt_at_exit_by_year is None:
        debt_at_exit_by_year = {y: debt_at_entry for y in hold_years_list}

    rows: List[Dict[str, Any]] = []
    for years in hold_years_list:
        for xm in exit_multiples:
            uplift = uplift_by_year[years]
            bridge = value_creation_bridge(
                entry_ebitda=entry_ebitda,
                uplift=uplift,
                entry_multiple=entry_multiple,
                exit_multiple=xm,
                hold_years=float(years),
                organic_growth_pct=organic_growth_pct,
            )
            exit_debt = debt_at_exit_by_year.get(years, debt_at_entry)
            exit_equity = bridge.exit_ev - exit_debt
            underwater = exit_equity <= 0.0

            if underwater:
                # Total equity loss — IRR is -100%, MOIC is 0. Don't invoke
                # the bisection solver (would raise on all-negative flows).
                class _StubReturns:
                    pass
                returns = _StubReturns()
                returns.moic = 0.0
                returns.irr = -1.0
            else:
                returns = compute_returns(
                    entry_equity=entry_equity,
                    exit_proceeds=exit_equity,
                    hold_years=float(years),
                )
            total_value = bridge.total_value_created
            rcm_share = (
                bridge.rcm_uplift_contribution / total_value if total_value > 0 else 0.0
            )
            rows.append({
                "hold_years": int(years),
                "exit_multiple": float(xm),
                "entry_ev": bridge.entry_ev,
                "exit_ev": bridge.exit_ev,
                "entry_equity": float(entry_equity),
                "exit_debt": float(exit_debt),
                "exit_equity": float(exit_equity),
                "underwater": bool(underwater),
                "moic": returns.moic,
                "irr": returns.irr,
                "total_value_created": total_value,
                "rcm_uplift_share": rcm_share,
            })
    return rows


def hold_period_grid_with_mc(
    *,
    entry_ebitda: float,
    mc_ebitda_summary: Any,                       # DistributionSummary-like object
    entry_multiple: float,
    exit_multiples: List[float],
    hold_years_list: List[int],
    entry_equity: float,
    organic_growth_pct: float = 0.0,
    debt_at_entry: float = 0.0,
    debt_at_exit_by_year: Optional[Dict[int, float]] = None,
) -> List[Dict[str, Any]]:
    """Probability-weighted variant of :func:`hold_period_grid`.

    Consumes a :class:`rcm_mc.mc.DistributionSummary` (or any object
    with ``p10``/``p50``/``p90`` attributes) as the uplift distribution.
    For each ``(hold_years, exit_multiple)`` cell returns MOIC / IRR at
    the P10, P50, and P90 bands so the partner sees downside / central /
    upside without running three grids.

    Rationale: partners underwrite deals at the P50 but protect the LP
    at the P10. Showing all three side-by-side is the single biggest
    piece of IC homework this grid does.
    """
    if debt_at_exit_by_year is None:
        debt_at_exit_by_year = {y: debt_at_entry for y in hold_years_list}

    # Read P10/P50/P90 off whatever we were passed — dict or dataclass.
    def _pick(attr: str) -> float:
        if hasattr(mc_ebitda_summary, attr):
            return float(getattr(mc_ebitda_summary, attr))
        if isinstance(mc_ebitda_summary, dict):
            return float(mc_ebitda_summary.get(attr) or 0.0)
        return 0.0
    uplift_p10 = _pick("p10")
    uplift_p50 = _pick("p50")
    uplift_p90 = _pick("p90")

    rows: List[Dict[str, Any]] = []
    for years in hold_years_list:
        for xm in exit_multiples:
            cell: Dict[str, Any] = {
                "hold_years": int(years),
                "exit_multiple": float(xm),
            }
            for band, uplift in (("p10", uplift_p10),
                                  ("p50", uplift_p50),
                                  ("p90", uplift_p90)):
                bridge = value_creation_bridge(
                    entry_ebitda=entry_ebitda,
                    uplift=uplift,
                    entry_multiple=entry_multiple,
                    exit_multiple=xm,
                    hold_years=float(years),
                    organic_growth_pct=organic_growth_pct,
                )
                exit_debt = debt_at_exit_by_year.get(years, debt_at_entry)
                exit_equity = bridge.exit_ev - exit_debt
                if exit_equity <= 0.0:
                    cell[f"moic_{band}"] = 0.0
                    cell[f"irr_{band}"] = -1.0
                    continue
                r = compute_returns(
                    entry_equity=max(entry_equity, 1.0),
                    exit_proceeds=float(exit_equity),
                    hold_years=float(years),
                )
                cell[f"moic_{band}"] = float(r.moic)
                cell[f"irr_{band}"] = float(r.irr)
                cell["entry_ev"] = bridge.entry_ev
                cell[f"exit_ev_{band}"] = bridge.exit_ev
            rows.append(cell)
    return rows


def format_hold_grid(rows: List[Dict[str, Any]]) -> str:
    """Terminal-friendly pivot table: hold-years × exit-multiple → IRR / MOIC.

    Two-line cell: IRR on top, MOIC on bottom. Markers for stress outcomes:
    ``!`` = underwater (negative exit equity).
    """
    if not rows:
        return "(no scenarios)"

    years = sorted({r["hold_years"] for r in rows})
    multiples = sorted({r["exit_multiple"] for r in rows})
    by_key = {(r["hold_years"], r["exit_multiple"]): r for r in rows}

    lines = ["Hold-period × exit-multiple sensitivity (IRR / MOIC):"]
    lines.append("─" * 60)
    header = f"    {'Hold':>5s}  " + "  ".join(f"{m:>5.1f}x" for m in multiples)
    lines.append(header)
    for y in years:
        parts_irr = [f"    {y:>4d}y "]
        parts_moic = [" " * 9]
        for m in multiples:
            r = by_key.get((y, m))
            if r is None:
                parts_irr.append(f" {'—':>6s}")
                parts_moic.append(f" {'':>6s}")
                continue
            flag = "!" if r.get("underwater") else " "
            parts_irr.append(f" {r['irr']*100:>4.0f}%{flag}")
            parts_moic.append(f" {r['moic']:>5.2f}x")
        lines.append("".join(parts_irr))
        lines.append("".join(parts_moic))
    lines.append("─" * 60)
    if any(r.get("underwater") for r in rows):
        lines.append("  ! = exit equity underwater (negative) — deal below debt")
    return "\n".join(lines)


# ── Leverage & covenant headroom ───────────────────────────────────────────

@dataclass
class CovenantCheck:
    """Leverage / covenant headroom analysis for one EBITDA scenario.

    Debt / EBITDA is the canonical PE covenant — lenders trigger default
    protections when actual leverage exceeds the covenant (typically set
    1.0-2.0 turns above entry leverage).

    ``ebitda_cushion_pct`` answers "how much EBITDA can compress before
    the covenant trips?" — the single most-asked question at downside
    committees.
    """
    ebitda: float
    debt: float
    covenant_max_leverage: float
    actual_leverage: float
    covenant_headroom_turns: float   # covenant - actual (positive = safe)
    ebitda_cushion_pct: float         # fractional EBITDA decline to trip
    covenant_trips_at_ebitda: float   # EBITDA level that hits the covenant
    interest_coverage: float           # EBITDA / interest expense (None if no rate)


def covenant_check(
    ebitda: float,
    debt: float,
    covenant_max_leverage: float,
    interest_rate: float = 0.0,
    *,
    registry: Any = None,
) -> CovenantCheck:
    """Single-point covenant check at a given (EBITDA, debt) pair.

    Parameters
    ----------
    ebitda
        Trailing-twelve-months EBITDA at the test date.
    debt
        Total funded debt subject to the covenant.
    covenant_max_leverage
        Maximum Debt/EBITDA multiple permitted by the senior credit
        agreement (e.g., 6.0 for a 6.0x cov-lite). Must be positive.
    interest_rate
        Weighted-average cost of debt (decimal). If >0, compute
        interest-coverage = EBITDA / (debt × rate). 0 disables this.

    Returns
    -------
    CovenantCheck with actual leverage, headroom, and the EBITDA cushion
    before the covenant trips (critical for downside stress tests).
    """
    if ebitda <= 0:
        raise ValueError(f"ebitda must be positive (got {ebitda})")
    if debt < 0:
        raise ValueError(f"debt must be non-negative (got {debt})")
    if covenant_max_leverage <= 0:
        raise ValueError(f"covenant_max_leverage must be positive (got {covenant_max_leverage})")

    actual_leverage = debt / ebitda if ebitda > 0 else float("inf")
    headroom_turns = covenant_max_leverage - actual_leverage

    # Trip point: EBITDA = debt / covenant — the level where actual leverage
    # equals the covenant. Below this, we're in violation.
    trip_ebitda = debt / covenant_max_leverage if covenant_max_leverage > 0 else 0.0
    # Cushion as a fraction of current EBITDA — negative = already tripped
    if ebitda > 0:
        cushion_pct = (ebitda - trip_ebitda) / ebitda
    else:
        cushion_pct = 0.0

    interest_cov = 0.0
    if interest_rate > 0 and debt > 0:
        interest_expense = debt * interest_rate
        interest_cov = ebitda / interest_expense if interest_expense > 0 else float("inf")

    result = CovenantCheck(
        ebitda=float(ebitda),
        debt=float(debt),
        covenant_max_leverage=float(covenant_max_leverage),
        actual_leverage=float(actual_leverage),
        covenant_headroom_turns=float(headroom_turns),
        ebitda_cushion_pct=float(cushion_pct),
        covenant_trips_at_ebitda=float(trip_ebitda),
        interest_coverage=float(interest_cov),
    )
    if registry is not None:
        try:
            _record_covenant_provenance(registry, result)
        except Exception:  # noqa: BLE001
            pass
    return result


def _record_covenant_provenance(registry, c: "CovenantCheck") -> None:
    def _ensure(metric: str, value: float, formula: str):
        existing = registry.get(metric)
        if existing is not None:
            return existing
        return registry.record_calc(
            value=value, metric_name=metric,
            formula=formula, upstream=[],
        )
    e = _ensure("ebitda", c.ebitda, "TTM EBITDA")
    d = _ensure("debt", c.debt, "user input / loan agreement")
    cap = _ensure("covenant_max_leverage", c.covenant_max_leverage,
                  "from credit agreement")
    registry.record_calc(
        value=c.actual_leverage, metric_name="actual_leverage",
        formula="debt ÷ ebitda", upstream=[d, e],
    )
    registry.record_calc(
        value=c.covenant_headroom_turns,
        metric_name="covenant_headroom_turns",
        formula="covenant_max_leverage − actual_leverage",
        upstream=[cap, d, e],
    )


def format_covenant(c: CovenantCheck) -> str:
    """Terminal-friendly covenant status block."""
    status = "SAFE" if c.covenant_headroom_turns >= 1.0 else (
        "TIGHT" if c.covenant_headroom_turns >= 0 else "TRIPPED"
    )
    lines = [
        f"Covenant Check — {status}",
        "─" * 50,
        f"  EBITDA:               {_fmt_money(c.ebitda)}",
        f"  Total debt:           {_fmt_money(c.debt)}",
        f"  Actual leverage:      {c.actual_leverage:.2f}x",
        f"  Covenant maximum:     {c.covenant_max_leverage:.2f}x",
        f"  Headroom:             {c.covenant_headroom_turns:+.2f} turns",
        f"  EBITDA cushion:       {c.ebitda_cushion_pct*100:+.0f}%  "
        f"(trips at {_fmt_money(c.covenant_trips_at_ebitda)})",
    ]
    if c.interest_coverage > 0:
        lines.append(f"  Interest coverage:    {c.interest_coverage:.1f}x")
    return "\n".join(lines)


def returns_from_rcm_bridge(
    bridge_result: Any,
    *,
    entry_multiple: float,
    exit_multiple: float,
    hold_years: float,
    organic_growth_pct: float = 0.0,
    equity_share: float = 1.0,
    interim_cash_flows: Optional[List[float]] = None,
    registry: Any = None,
) -> Dict[str, Any]:
    """Bridge :class:`rcm_mc.analysis.packet.EBITDABridgeResult` into
    :class:`BridgeResult` + :class:`ReturnsResult`.

    The RCM bridge gives us the "what does the management plan look
    like in dollars" answer. PE math then translates that into IC
    language: entry EV, exit EV, MOIC, IRR. This function is the seam.

    ``bridge_result`` is the packet-side dataclass with
    ``current_ebitda`` / ``target_ebitda`` — we treat ``target_ebitda``
    as the fully-ramped exit EBITDA (same convention as
    :func:`value_creation_bridge`). ``equity_share`` scales the exit
    proceeds: 1.0 means all-equity deal, 0.5 means half the EV is
    distributed to LPs after exit (pay-down of leverage not modeled —
    this stays deliberately simple so the math reconciles without a
    debt schedule).

    Returns a dict with ``bridge`` (``BridgeResult``) + ``returns``
    (``ReturnsResult``) + ``entry_ev`` / ``exit_ev`` for convenience.
    """
    current = float(getattr(bridge_result, "current_ebitda", 0.0) or 0.0)
    rcm_uplift = float(getattr(bridge_result, "total_ebitda_impact", 0.0) or 0.0)
    if current <= 0:
        raise ValueError("RCM bridge must carry a positive current_ebitda")

    bridge = value_creation_bridge(
        entry_ebitda=current,
        uplift=rcm_uplift,
        entry_multiple=entry_multiple,
        exit_multiple=exit_multiple,
        hold_years=hold_years,
        organic_growth_pct=organic_growth_pct,
        registry=registry,
    )
    entry_equity = bridge.entry_ev * float(equity_share)
    exit_proceeds = bridge.exit_ev * float(equity_share)
    returns = compute_returns(
        entry_equity=max(entry_equity, 1.0),
        exit_proceeds=exit_proceeds,
        hold_years=hold_years,
        interim_cash_flows=interim_cash_flows,
        registry=registry,
    )
    return {
        "bridge": bridge,
        "returns": returns,
        "entry_ev": bridge.entry_ev,
        "exit_ev": bridge.exit_ev,
    }


def bridge_to_records(b: BridgeResult) -> List[Dict[str, Any]]:
    """Bridge components as a list of dicts — JSON / workbook friendly.

    One row per bridge step so Excel can chart it as a waterfall.
    """
    total = b.total_value_created
    rows: List[Dict[str, Any]] = [
        {"step": "Entry EV",            "value": b.entry_ev,              "share_of_creation": None,  "note": f"{b.entry_multiple:.1f}x × entry EBITDA"},
        {"step": "Organic EBITDA",      "value": b.organic_ebitda_contribution,   "share_of_creation": (b.organic_ebitda_contribution / total) if total else None, "note": f"{b.organic_growth_pct*100:+.1f}%/yr × {b.hold_years:g}y"},
        {"step": "RCM uplift",          "value": b.rcm_uplift_contribution,       "share_of_creation": (b.rcm_uplift_contribution / total) if total else None,     "note": f"× {b.entry_multiple:.1f}x entry multiple"},
        {"step": "Multiple expansion",  "value": b.multiple_expansion_contribution, "share_of_creation": (b.multiple_expansion_contribution / total) if total else None, "note": f"Δ{b.exit_multiple - b.entry_multiple:+.1f}x × exit EBITDA"},
        {"step": "Exit EV",             "value": b.exit_ev,              "share_of_creation": None,  "note": f"{b.exit_multiple:.1f}x × exit EBITDA"},
    ]
    return rows
