"""`rcm-mc pe` — command-line access to the PE deal-math layer.

Four subcommands, one per analytic:

    rcm-mc pe bridge    # value creation bridge (entry EV → exit EV)
    rcm-mc pe returns   # MOIC + IRR from entry equity + exit proceeds
    rcm-mc pe grid      # hold-years × exit-multiple sensitivity
    rcm-mc pe covenant  # leverage + covenant headroom check

Each subcommand accepts ``--json`` for structured output (script-friendly)
and ``--from-run DIR`` to pull EBITDA + uplift from an existing run's
summary.csv (so the analyst doesn't have to re-enter numbers by hand).

Design: stays narrow — no templates, no interactive prompts. The
positional arguments are the knobs a director twists in an IC session.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


def _parse_float_list(s: str) -> List[float]:
    """Parse "8,9,10,11" or "3,5,7" into a list of floats."""
    return [float(x.strip()) for x in s.split(",") if x.strip()]


def _parse_int_list(s: str) -> List[int]:
    return [int(x.strip()) for x in s.split(",") if x.strip()]


def _load_run_summary(run_dir: str) -> Dict[str, float]:
    """Pull (entry_ebitda, mean_uplift) from a prior run's summary.csv.

    Returns ``{"entry_ebitda": float, "uplift": float}`` when both fields
    are discoverable, else raises FileNotFoundError / KeyError.

    Looks for metrics named ``ebitda_drag`` / ``ebitda_uplift`` indexed on
    ``mean``. Picks the opposite-sign convention: drag is the amount
    LOST; uplift is what we'd capture closing the gap. Either is accepted.
    """
    import pandas as pd

    path = os.path.join(run_dir, "summary.csv")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"summary.csv not found in {run_dir}")
    df = pd.read_csv(path, index_col=0)

    # Uplift: we closed the gap → ebitda_uplift or (if missing) ebitda_drag
    uplift = 0.0
    for name in ("ebitda_uplift", "ebitda_drag"):
        if name in df.index and "mean" in df.columns:
            uplift = float(df.loc[name, "mean"])
            break
    return {"uplift": uplift}


# ── Subcommand handlers ────────────────────────────────────────────────────

def _cmd_bridge(args: argparse.Namespace) -> int:
    from .pe.pe_math import bridge_to_records, format_bridge, value_creation_bridge

    uplift = args.uplift
    if args.from_run:
        run_info = _load_run_summary(args.from_run)
        if uplift is None:
            uplift = run_info.get("uplift", 0.0)
    if uplift is None:
        sys.stderr.write("Error: --uplift is required (or --from-run DIR)\n")
        return 2

    bridge = value_creation_bridge(
        entry_ebitda=args.entry_ebitda,
        uplift=uplift,
        entry_multiple=args.entry_multiple,
        exit_multiple=args.exit_multiple,
        hold_years=args.hold_years,
        organic_growth_pct=args.organic_growth,
    )
    if args.json:
        payload = {
            "inputs": {
                "entry_ebitda": bridge.entry_ebitda,
                "uplift": bridge.rcm_uplift,
                "entry_multiple": bridge.entry_multiple,
                "exit_multiple": bridge.exit_multiple,
                "hold_years": bridge.hold_years,
                "organic_growth_pct": bridge.organic_growth_pct,
            },
            "entry_ev": bridge.entry_ev,
            "exit_ev": bridge.exit_ev,
            "exit_ebitda": bridge.exit_ebitda,
            "components": bridge_to_records(bridge),
            "total_value_created": bridge.total_value_created,
        }
        sys.stdout.write(json.dumps(payload, indent=2, default=str) + "\n")
    else:
        sys.stdout.write(format_bridge(bridge) + "\n")
    return 0


def _cmd_returns(args: argparse.Namespace) -> int:
    from .pe.pe_math import compute_returns, format_returns

    interim: List[float] = []
    if args.interim:
        interim = _parse_float_list(args.interim)

    r = compute_returns(
        entry_equity=args.entry_equity,
        exit_proceeds=args.exit_proceeds,
        hold_years=args.hold_years,
        interim_cash_flows=interim,
    )
    if args.json:
        sys.stdout.write(json.dumps({
            "entry_equity": r.entry_equity,
            "exit_proceeds": r.exit_proceeds,
            "interim_cash_flows": r.interim_cash_flows,
            "hold_years": r.hold_years,
            "moic": r.moic,
            "irr": r.irr,
            "total_distributions": r.total_distributions,
        }, indent=2) + "\n")
    else:
        sys.stdout.write(format_returns(r) + "\n")
    return 0


def _cmd_grid(args: argparse.Namespace) -> int:
    from .pe.pe_math import format_hold_grid, hold_period_grid

    hold_years_list = _parse_int_list(args.hold_years)
    exit_multiples = _parse_float_list(args.exit_multiples)

    # uplift_by_year: either a single --uplift applied to all years, or
    # a --uplift-ramp "3:5e6,5:8e6,7:9e6" mapping per year
    if args.uplift_ramp:
        uplift_by_year: Dict[int, float] = {}
        for pair in args.uplift_ramp.split(","):
            y, v = pair.split(":")
            uplift_by_year[int(y.strip())] = float(v.strip())
    else:
        # Flat: same uplift at every hold year — useful for conservative
        # underwriting when the ramp assumption is itself contested
        if args.uplift is None:
            sys.stderr.write("Error: provide --uplift or --uplift-ramp\n")
            return 2
        uplift_by_year = {y: args.uplift for y in hold_years_list}

    debt_at_exit_by_year: Optional[Dict[int, float]] = None
    if args.debt_at_exit:
        debt_at_exit_by_year = {}
        for pair in args.debt_at_exit.split(","):
            y, v = pair.split(":")
            debt_at_exit_by_year[int(y.strip())] = float(v.strip())

    rows = hold_period_grid(
        entry_ebitda=args.entry_ebitda,
        uplift_by_year=uplift_by_year,
        entry_multiple=args.entry_multiple,
        exit_multiples=exit_multiples,
        hold_years_list=hold_years_list,
        entry_equity=args.entry_equity,
        debt_at_entry=args.debt_at_entry,
        debt_at_exit_by_year=debt_at_exit_by_year,
        organic_growth_pct=args.organic_growth,
    )
    if args.json:
        sys.stdout.write(json.dumps(rows, indent=2, default=str) + "\n")
    else:
        sys.stdout.write(format_hold_grid(rows) + "\n")
    return 0


def _cmd_covenant(args: argparse.Namespace) -> int:
    from .pe.pe_math import covenant_check, format_covenant

    c = covenant_check(
        ebitda=args.ebitda,
        debt=args.debt,
        covenant_max_leverage=args.covenant_leverage,
        interest_rate=args.interest_rate,
    )
    if args.json:
        sys.stdout.write(json.dumps({
            "ebitda": c.ebitda,
            "debt": c.debt,
            "covenant_max_leverage": c.covenant_max_leverage,
            "actual_leverage": c.actual_leverage,
            "covenant_headroom_turns": c.covenant_headroom_turns,
            "ebitda_cushion_pct": c.ebitda_cushion_pct,
            "covenant_trips_at_ebitda": c.covenant_trips_at_ebitda,
            "interest_coverage": c.interest_coverage,
        }, indent=2) + "\n")
    else:
        sys.stdout.write(format_covenant(c) + "\n")
    return 0


# ── Dispatcher ─────────────────────────────────────────────────────────────

def _build_parser(prog: str) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog=prog,
        description="PE deal-math: value bridge, IRR/MOIC, sensitivity, covenants.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    # ── bridge ──
    b = sub.add_parser("bridge", help="Value creation bridge (entry EV → exit EV)")
    b.add_argument("--entry-ebitda", type=float, required=True,
                   help="Target EBITDA at deal close (dollars)")
    b.add_argument("--uplift", type=float, default=None,
                   help="RCM EBITDA uplift at exit (dollars; omit with --from-run)")
    b.add_argument("--entry-multiple", type=float, required=True,
                   help="EV/EBITDA multiple at entry (e.g., 9.0)")
    b.add_argument("--exit-multiple", type=float, required=True,
                   help="EV/EBITDA multiple at exit")
    b.add_argument("--hold-years", type=float, required=True,
                   help="Holding period in years (fractional OK)")
    b.add_argument("--organic-growth", type=float, default=0.0,
                   help="Annual organic growth rate (decimal, default 0.0)")
    b.add_argument("--from-run", default=None, metavar="DIR",
                   help="Pull --uplift from a prior run's summary.csv")
    b.add_argument("--json", action="store_true", help="Emit structured JSON")

    # ── returns ──
    r = sub.add_parser("returns", help="Compute MOIC + IRR for an equity hold")
    r.add_argument("--entry-equity", type=float, required=True)
    r.add_argument("--exit-proceeds", type=float, required=True)
    r.add_argument("--hold-years", type=float, required=True)
    r.add_argument("--interim", default=None, metavar="CSV",
                   help="Comma-separated interim cashflows (e.g., '0,10e6,0,0')")
    r.add_argument("--json", action="store_true")

    # ── grid ──
    g = sub.add_parser("grid", help="Hold-years × exit-multiple sensitivity")
    g.add_argument("--entry-ebitda", type=float, required=True)
    g.add_argument("--uplift", type=float, default=None,
                   help="Flat uplift applied at every hold year (vs --uplift-ramp)")
    g.add_argument("--uplift-ramp", default=None, metavar="YEAR:VALUE,...",
                   help="Ramp profile: '3:5e6,5:8e6,7:9e6'")
    g.add_argument("--entry-multiple", type=float, required=True)
    g.add_argument("--exit-multiples", required=True, metavar="CSV",
                   help="Comma-separated exit multiples (e.g., '8,9,10,11')")
    g.add_argument("--hold-years", required=True, metavar="CSV",
                   help="Comma-separated hold years (e.g., '3,5,7')")
    g.add_argument("--entry-equity", type=float, required=True)
    g.add_argument("--debt-at-entry", type=float, default=0.0)
    g.add_argument("--debt-at-exit", default=None, metavar="YEAR:VALUE,...",
                   help="Debt amortization: '3:240e6,5:220e6,7:200e6'")
    g.add_argument("--organic-growth", type=float, default=0.0)
    g.add_argument("--json", action="store_true")

    # ── covenant ──
    c = sub.add_parser("covenant", help="Leverage / covenant headroom check")
    c.add_argument("--ebitda", type=float, required=True)
    c.add_argument("--debt", type=float, required=True)
    c.add_argument("--covenant-leverage", type=float, required=True,
                   help="Max Debt/EBITDA multiple per credit agreement (e.g., 6.5)")
    c.add_argument("--interest-rate", type=float, default=0.0,
                   help="Weighted cost of debt (decimal) for interest coverage")
    c.add_argument("--json", action="store_true")

    # ── override (Prompt 18) ────────────────────────────────────
    # ``rcm-mc pe override set <deal> <key> <value> --reason "..."``
    # ``rcm-mc pe override list <deal>``
    # ``rcm-mc pe override clear <deal> <key>``
    ov = sub.add_parser(
        "override",
        help="Per-deal analyst overrides (set/list/clear)",
    )
    ov.add_argument("--db", default=os.environ.get("RCM_MC_DB") or "portfolio.db",
                    help="Portfolio SQLite path (default: ./portfolio.db "
                         "or $RCM_MC_DB)")
    ov_sub = ov.add_subparsers(dest="ov_cmd", required=True)
    ov_set = ov_sub.add_parser("set", help="Set one override")
    ov_set.add_argument("deal_id")
    ov_set.add_argument("key", help="e.g. bridge.exit_multiple")
    ov_set.add_argument("value", help="JSON literal (number / string / bool)")
    ov_set.add_argument("--reason", default=None,
                         help="Why this override was applied")
    ov_set.add_argument("--set-by", default=os.environ.get("USER") or "cli",
                         help="Analyst identifier for the audit row "
                              "(default: $USER)")
    ov_list = ov_sub.add_parser("list", help="List overrides for a deal")
    ov_list.add_argument("deal_id", nargs="?", default=None,
                          help="Omit to list every deal's overrides")
    ov_list.add_argument("--json", action="store_true")
    ov_clear = ov_sub.add_parser("clear", help="Remove one override")
    ov_clear.add_argument("deal_id")
    ov_clear.add_argument("key")

    return ap


def _cmd_override(args: argparse.Namespace) -> int:
    """Handle ``rcm-mc pe override {set|list|clear}``."""
    from .analysis.deal_overrides import (
        clear_override, list_overrides, set_override,
    )
    from .portfolio.store import PortfolioStore

    store = PortfolioStore(args.db)
    if args.ov_cmd == "set":
        # Parse value as JSON so ``11.0`` is a float and ``true`` is a bool.
        try:
            value = json.loads(args.value)
        except json.JSONDecodeError:
            # Fall back to string — analysts sometimes forget quotes.
            value = args.value
        try:
            row_id = set_override(
                store, args.deal_id, args.key, value,
                set_by=args.set_by, reason=args.reason,
            )
        except ValueError as exc:
            sys.stderr.write(f"error: {exc}\n")
            return 2
        sys.stdout.write(
            f"ok: {args.deal_id} {args.key} = {value!r} (id={row_id})\n"
        )
        return 0
    if args.ov_cmd == "list":
        rows = list_overrides(store, args.deal_id)
        if args.json:
            sys.stdout.write(json.dumps(rows, indent=2, default=str) + "\n")
            return 0
        if not rows:
            sys.stdout.write(
                f"(no overrides for {args.deal_id or 'any deal'})\n"
            )
            return 0
        for r in rows:
            reason = f" ({r['reason']})" if r.get("reason") else ""
            sys.stdout.write(
                f"{r['deal_id']:<16} {r['override_key']:<40} "
                f"= {r['override_value']!r}  "
                f"by {r['set_by']} at {r['set_at']}{reason}\n"
            )
        return 0
    if args.ov_cmd == "clear":
        removed = clear_override(store, args.deal_id, args.key)
        if removed:
            sys.stdout.write(
                f"cleared: {args.deal_id} {args.key}\n"
            )
            return 0
        sys.stderr.write(
            f"warning: no such override {args.key} for {args.deal_id}\n"
        )
        return 1
    return 2


def main(argv: Optional[List[str]] = None, prog: str = "rcm-mc pe") -> int:
    ap = _build_parser(prog)
    args = ap.parse_args(argv)
    if args.cmd == "bridge":
        return _cmd_bridge(args)
    if args.cmd == "returns":
        return _cmd_returns(args)
    if args.cmd == "grid":
        return _cmd_grid(args)
    if args.cmd == "covenant":
        return _cmd_covenant(args)
    if args.cmd == "override":
        return _cmd_override(args)
    ap.print_help()
    return 2
