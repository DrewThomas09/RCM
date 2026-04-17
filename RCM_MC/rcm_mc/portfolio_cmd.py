"""`rcm-mc portfolio` — portfolio-level deal tracking CLI (Brick 49).

Four subcommands answer the four PE portfolio questions:

    rcm-mc portfolio register --deal-id X --stage loi [--run-dir DIR] [--notes ...]
        Add a snapshot at the current stage.

    rcm-mc portfolio list [--deal-id X]
        Tabular view: latest-per-deal by default, all snapshots for one deal
        with --deal-id.

    rcm-mc portfolio show --deal-id X
        Audit trail: every snapshot for one deal, oldest → newest.

    rcm-mc portfolio rollup
        Portfolio aggregates: weighted MOIC/IRR, stage funnel, covenant
        trips, deals with concerning signals.

Defaults the DB path to ``~/.rcm_mc/portfolio.db`` so a PE analyst gets
a persistent portfolio across sessions without flag fiddling. Override
with ``--db PATH``.

Not a useless feature: every PE firm actually runs this workflow today
with ad-hoc Excel — this is the first consolidated tool that captures
the full snapshot from a diligence run.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from .portfolio.store import PortfolioStore
from .portfolio.portfolio_snapshots import (
    DEAL_STAGES,
    format_rollup,
    latest_per_deal,
    list_snapshots,
    portfolio_rollup,
    register_snapshot,
)


# Default portfolio DB path: per-user, persistent across sessions.
# Matches how `rcm-mc hcris info` points at a per-user cache.
_DEFAULT_DB = os.path.expanduser("~/.rcm_mc/portfolio.db")


def _format_latest_table(df) -> str:
    """Compact tabular view of latest-per-deal snapshots."""
    if df is None or df.empty:
        return "(no deals in portfolio)"

    lines = [
        f"Portfolio — {len(df)} deals",
        "─" * 80,
        f"  {'Deal ID':<20s}  {'Stage':<8s}  {'MOIC':>6s}  {'IRR':>6s}  "
        f"{'Covenant':<9s}  {'Signals':<10s}  {'Snapshot':<20s}",
    ]
    def _clean(v):
        """Coerce pandas NaN → None so string formatting doesn't trip."""
        if v is None:
            return None
        if isinstance(v, float) and v != v:
            return None
        return v

    for _, r in df.iterrows():
        moic_v = _clean(r.get("moic"))
        irr_v = _clean(r.get("irr"))
        moic = "—" if moic_v is None else f"{float(moic_v):.2f}x"
        irr = "—" if irr_v is None else f"{float(irr_v)*100:.0f}%"
        cov = _clean(r.get("covenant_status")) or "—"
        nc_v = _clean(r.get("concerning_signals"))
        nf_v = _clean(r.get("favorable_signals"))
        if nc_v is None and nf_v is None:
            sig = "—"
        else:
            sig = f"{int(nc_v or 0)}c/{int(nf_v or 0)}f"
        created = str(_clean(r.get("created_at")) or "")[:19]
        lines.append(
            f"  {str(r['deal_id']):<20s}  {str(r['stage']):<8s}  "
            f"{moic:>6s}  {irr:>6s}  {cov:<9s}  {sig:<10s}  {created:<20s}"
        )
    return "\n".join(lines)


def _format_snapshot_audit(df) -> str:
    """Audit trail: every snapshot for one deal, oldest → newest."""
    if df is None or df.empty:
        return "(no snapshots for this deal)"
    df = df.sort_values("created_at")
    lines = [f"Audit trail — {df.iloc[0]['deal_id']}", "─" * 60]
    for _, r in df.iterrows():
        created = str(r.get("created_at") or "")[:19]
        line = f"  {created}  {r['stage']:<8s}"
        if r.get("moic") is not None and r.get("moic") == r.get("moic"):
            line += f"  MOIC {float(r['moic']):.2f}x"
        if r.get("irr") is not None and r.get("irr") == r.get("irr"):
            line += f"  IRR {float(r['irr'])*100:.1f}%"
        if r.get("covenant_status"):
            line += f"  Cov {r['covenant_status']}"
        notes = r.get("notes") or ""
        if notes:
            line += f"  — {notes}"
        lines.append(line)
    return "\n".join(lines)


# ── Subcommand handlers ────────────────────────────────────────────────────

def _cmd_register(args: argparse.Namespace) -> int:
    store = PortfolioStore(args.db)
    try:
        sid = register_snapshot(
            store,
            deal_id=args.deal_id,
            stage=args.stage,
            run_dir=args.run_dir,
            notes=args.notes or "",
        )
    except ValueError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 2
    sys.stdout.write(
        f"Registered snapshot #{sid}: deal={args.deal_id} stage={args.stage}\n"
    )
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    store = PortfolioStore(args.db)
    if args.deal_id:
        df = list_snapshots(store, deal_id=args.deal_id)
    else:
        df = latest_per_deal(store)
    if args.json:
        sys.stdout.write(df.to_json(orient="records", indent=2) + "\n")
    else:
        sys.stdout.write(_format_latest_table(df) + "\n")
    return 0 if not df.empty else 1


def _cmd_show(args: argparse.Namespace) -> int:
    store = PortfolioStore(args.db)
    df = list_snapshots(store, deal_id=args.deal_id)
    if df.empty:
        sys.stderr.write(f"No snapshots for deal {args.deal_id!r}\n")
        return 1
    if args.json:
        sys.stdout.write(df.sort_values("created_at").to_json(
            orient="records", indent=2,
        ) + "\n")
    else:
        sys.stdout.write(_format_snapshot_audit(df) + "\n")
    return 0


def _cmd_rollup(args: argparse.Namespace) -> int:
    store = PortfolioStore(args.db)
    rollup = portfolio_rollup(store)
    if args.json:
        sys.stdout.write(json.dumps(rollup, indent=2, default=str) + "\n")
    else:
        sys.stdout.write(format_rollup(rollup) + "\n")
    return 0


def _cmd_dashboard(args: argparse.Namespace) -> int:
    from .portfolio.portfolio_dashboard import build_portfolio_dashboard
    store = PortfolioStore(args.db)
    out_path = args.out or "portfolio_dashboard.html"
    path = build_portfolio_dashboard(store, out_path, title=args.title)
    sys.stdout.write(f"Wrote: {path}\n")
    return 0


def _cmd_actuals(args: argparse.Namespace) -> int:
    """Record a quarter of actuals for a deal (B52)."""
    from .pe.hold_tracking import TRACKED_KPIS, record_quarterly_actuals

    store = PortfolioStore(args.db)
    actuals: dict = {}
    for kpi in TRACKED_KPIS:
        v = getattr(args, kpi, None)
        if v is not None:
            actuals[kpi] = float(v)
    if not actuals:
        sys.stderr.write(
            "Error: provide at least one KPI flag "
            f"({' '.join('--' + k.replace('_','-') for k in TRACKED_KPIS)})\n"
        )
        return 2

    plan: dict = {}
    for kpi in TRACKED_KPIS:
        v = getattr(args, f"plan_{kpi}", None)
        if v is not None:
            plan[kpi] = float(v)

    try:
        aid = record_quarterly_actuals(
            store, deal_id=args.deal_id, quarter=args.quarter,
            actuals=actuals, plan=plan or None, notes=args.notes or "",
        )
    except ValueError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 2
    sys.stdout.write(
        f"Recorded actuals #{aid}: deal={args.deal_id} quarter={args.quarter}\n"
    )
    return 0


def _cmd_initiative_actual(args: argparse.Namespace) -> int:
    """Record initiative-level EBITDA impact for a quarter (B57)."""
    from .rcm.initiative_tracking import record_initiative_actual

    store = PortfolioStore(args.db)
    try:
        aid = record_initiative_actual(
            store, deal_id=args.deal_id, initiative_id=args.initiative_id,
            quarter=args.quarter, ebitda_impact=args.impact,
            notes=args.notes or "",
        )
    except ValueError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 2
    sys.stdout.write(
        f"Recorded initiative actual #{aid}: "
        f"deal={args.deal_id} initiative={args.initiative_id} "
        f"quarter={args.quarter} impact=${args.impact:,.0f}\n"
    )
    return 0


def _cmd_initiative_variance(args: argparse.Namespace) -> int:
    from .rcm.initiative_tracking import (
        format_initiative_variance, initiative_variance_report,
    )

    store = PortfolioStore(args.db)
    df = initiative_variance_report(store, args.deal_id)
    if df.empty:
        sys.stderr.write(
            f"No initiative actuals recorded for deal {args.deal_id!r}\n"
        )
        return 1
    if args.json:
        sys.stdout.write(df.to_json(orient="records", indent=2) + "\n")
    else:
        sys.stdout.write(format_initiative_variance(df) + "\n")
    return 0


def _cmd_initiative_import(args: argparse.Namespace) -> int:
    from .rcm.initiative_tracking import import_initiative_actuals_csv

    store = PortfolioStore(args.db)
    try:
        summary = import_initiative_actuals_csv(store, args.csv)
    except (FileNotFoundError, ValueError) as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 2
    sys.stdout.write(f"Ingested {summary['rows_ingested']} initiative-actual row(s)\n")
    for e in summary["errors"]:
        sys.stderr.write(f"  ✗ {e}\n")
    return 0 if summary["rows_ingested"] > 0 else 1


def _cmd_remark(args: argparse.Namespace) -> int:
    """Re-underwrite a deal based on actuals through a given quarter (B61)."""
    import json as _json
    from .pe.remark import compute_remark, format_remark, persist_remark, remark_to_dict

    store = PortfolioStore(args.db)
    try:
        result = compute_remark(store, deal_id=args.deal_id,
                                as_of_quarter=args.as_of)
    except ValueError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1

    if args.persist:
        sid = persist_remark(store, result)
        sys.stdout.write(f"Persisted re-mark snapshot #{sid}\n")
    if args.json:
        sys.stdout.write(_json.dumps(remark_to_dict(result), indent=2, default=str) + "\n")
    else:
        sys.stdout.write(format_remark(result) + "\n")
    return 0


def _cmd_synergy(args: argparse.Namespace) -> int:
    """Cross-platform RCM synergy across held platforms (B60)."""
    import json as _json
    from .portfolio.portfolio_synergy import compute_synergy, format_synergy, synergy_to_dict

    store = PortfolioStore(args.db)
    try:
        result = compute_synergy(
            store,
            shared_service_pct=args.shared_service_pct,
            savings_pct=args.savings_pct,
        )
    except ValueError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 2
    if args.json:
        sys.stdout.write(_json.dumps(synergy_to_dict(result), indent=2, default=str) + "\n")
    else:
        sys.stdout.write(format_synergy(result) + "\n")
    return 0


def _cmd_exit_memo(args: argparse.Namespace) -> int:
    """Generate an exit-readiness HTML memo for one held deal (B55)."""
    from .reports.exit_memo import build_exit_memo

    store = PortfolioStore(args.db)
    out_path = args.out or f"exit_memo_{args.deal_id}.html"
    try:
        path = build_exit_memo(
            store, deal_id=args.deal_id, out_path=out_path,
            title=args.title,
        )
    except ValueError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 1
    sys.stdout.write(f"Wrote: {path}\n")
    return 0


def _cmd_actuals_import(args: argparse.Namespace) -> int:
    """Bulk ingest actuals from a management-reporting CSV (B56)."""
    from .pe.hold_tracking import import_actuals_csv

    store = PortfolioStore(args.db)
    try:
        summary = import_actuals_csv(
            store, args.csv, strict=not args.lenient,
        )
    except (FileNotFoundError, ValueError) as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 2

    sys.stdout.write(
        f"Ingested {summary['rows_ingested']} row(s) "
        f"across {len(summary['deals'])} deal(s), "
        f"{len(summary['quarters'])} quarter(s).\n"
    )
    for w in summary["warnings"]:
        sys.stdout.write(f"  ⚠ {w}\n")
    for e in summary["errors"]:
        sys.stderr.write(f"  ✗ {e}\n")
    return 0 if summary["rows_ingested"] > 0 else 1


def _cmd_digest(args: argparse.Namespace) -> int:
    """Early-warning digest: diff since last review (B54)."""
    from .portfolio.portfolio_digest import build_digest, digest_to_frame, format_digest

    store = PortfolioStore(args.db)
    try:
        events = build_digest(store, since=args.since)
    except ValueError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        return 2
    if args.json:
        sys.stdout.write(digest_to_frame(events).to_json(
            orient="records", indent=2,
        ) + "\n")
    else:
        sys.stdout.write(format_digest(events, since=args.since) + "\n")
    return 0


def _cmd_variance(args: argparse.Namespace) -> int:
    """Emit the variance report for one deal (B52)."""
    from .pe.hold_tracking import format_variance_report, variance_report

    store = PortfolioStore(args.db)
    df = variance_report(store, args.deal_id)
    if df.empty:
        sys.stderr.write(f"No quarterly actuals for deal {args.deal_id!r}\n")
        return 1
    if args.json:
        sys.stdout.write(df.to_json(orient="records", indent=2) + "\n")
    else:
        sys.stdout.write(format_variance_report(df) + "\n")
    return 0


# ── Dispatcher ─────────────────────────────────────────────────────────────

def _build_parser(prog: str) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog=prog,
        description="Portfolio-level deal tracking: snapshot, list, roll up.",
    )
    ap.add_argument(
        "--db", default=_DEFAULT_DB, metavar="PATH",
        help=f"Portfolio DB path (default: {_DEFAULT_DB})",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    # register
    reg = sub.add_parser("register", help="Snapshot a deal at its current stage")
    reg.add_argument("--deal-id", required=True,
                     help="Stable identifier (e.g., 'ccf_2026', 'project_phoenix')")
    reg.add_argument("--stage", required=True, choices=DEAL_STAGES,
                     help="Current deal stage")
    reg.add_argument("--run-dir", default=None, metavar="DIR",
                     help="Path to `rcm-mc run` output folder — PE math auto-pulled")
    reg.add_argument("--notes", default=None,
                     help="Freeform note captured with the snapshot")

    # list
    lst = sub.add_parser("list", help="List deals (latest-per-deal by default)")
    lst.add_argument("--deal-id", default=None,
                     help="Show all snapshots for this deal instead of latest-per-deal")
    lst.add_argument("--json", action="store_true")

    # show
    show = sub.add_parser("show", help="Audit trail for one deal")
    show.add_argument("--deal-id", required=True)
    show.add_argument("--json", action="store_true")

    # rollup
    rol = sub.add_parser("rollup", help="Portfolio aggregates (weighted IRR/MOIC, funnel)")
    rol.add_argument("--json", action="store_true")

    # dashboard
    dash = sub.add_parser("dashboard", help="Generate self-contained HTML portfolio dashboard")
    dash.add_argument("--out", default=None, metavar="PATH",
                      help="Output HTML path (default: portfolio_dashboard.html)")
    dash.add_argument("--title", default="RCM Portfolio Dashboard",
                      help="Dashboard title (e.g., 'Chartis RCM Portfolio — Q2 2026')")

    # actuals — record one quarter
    act = sub.add_parser("actuals", help="Record one quarter of actuals for a held deal")
    act.add_argument("--deal-id", required=True)
    act.add_argument("--quarter", required=True, metavar="YYYYQn",
                     help="Reporting quarter, e.g., 2026Q2")
    act.add_argument("--ebitda", type=float, default=None, help="TTM EBITDA ($)")
    act.add_argument("--net-patient-revenue", dest="net_patient_revenue",
                     type=float, default=None, help="TTM NPSR ($)")
    act.add_argument("--idr-blended", dest="idr_blended", type=float, default=None,
                     help="Initial denial rate (decimal)")
    act.add_argument("--fwr-blended", dest="fwr_blended", type=float, default=None,
                     help="Final write-off rate (decimal)")
    act.add_argument("--dar-clean-days", dest="dar_clean_days",
                     type=float, default=None, help="Days-A/R clean claims")
    # Optional plan overrides for the same KPIs
    act.add_argument("--plan-ebitda", dest="plan_ebitda", type=float, default=None)
    act.add_argument("--plan-net-patient-revenue",
                     dest="plan_net_patient_revenue", type=float, default=None)
    act.add_argument("--plan-idr-blended", dest="plan_idr_blended",
                     type=float, default=None)
    act.add_argument("--plan-fwr-blended", dest="plan_fwr_blended",
                     type=float, default=None)
    act.add_argument("--plan-dar-clean-days", dest="plan_dar_clean_days",
                     type=float, default=None)
    act.add_argument("--notes", default=None)

    # actuals-import — bulk-ingest a management-reporting CSV
    imp = sub.add_parser("actuals-import", help="Bulk ingest quarterly actuals from CSV")
    imp.add_argument("--csv", required=True, metavar="PATH",
                     help="CSV with columns deal_id, quarter, <kpi>, plan_<kpi>")
    imp.add_argument("--lenient", action="store_true",
                     help="Warn (not raise) on unknown columns — use for vendor decks with extras")

    # variance — report actual vs plan
    var = sub.add_parser("variance", help="Actual vs underwritten variance report")
    var.add_argument("--deal-id", required=True)
    var.add_argument("--json", action="store_true")

    # digest — "what's changed since last review"
    dig = sub.add_parser("digest", help="Early-warning digest of portfolio changes")
    dig.add_argument("--since", default=None, metavar="YYYY-MM-DD",
                     help="Lower bound for the diff window (default: 7 days ago)")
    dig.add_argument("--json", action="store_true")

    # initiative-actual — record per-initiative EBITDA impact
    ini = sub.add_parser("initiative-actual",
                         help="Record initiative-level EBITDA impact for a quarter")
    ini.add_argument("--deal-id", required=True)
    ini.add_argument("--initiative-id", required=True,
                     help="Initiative identifier (must match initiatives_library.yaml)")
    ini.add_argument("--quarter", required=True, metavar="YYYYQn")
    ini.add_argument("--impact", type=float, required=True,
                     help="Dollar EBITDA impact attributed in this quarter")
    ini.add_argument("--notes", default=None)

    # initiative-variance — per-initiative variance report
    iniv = sub.add_parser("initiative-variance",
                          help="Per-initiative cumulative actual vs plan")
    iniv.add_argument("--deal-id", required=True)
    iniv.add_argument("--json", action="store_true")

    # initiative-import — bulk CSV
    inii = sub.add_parser("initiative-import",
                          help="Bulk-ingest initiative actuals from CSV")
    inii.add_argument("--csv", required=True, metavar="PATH")

    # remark — re-underwrite based on actuals
    rmk = sub.add_parser("remark",
                         help="Re-underwrite a deal based on actuals through a quarter")
    rmk.add_argument("--deal-id", required=True)
    rmk.add_argument("--as-of", required=True, metavar="YYYYQn",
                     help="Target quarter for the re-mark, e.g., 2026Q2")
    rmk.add_argument("--persist", action="store_true",
                     help="Record the re-mark as a new snapshot in the audit trail")
    rmk.add_argument("--json", action="store_true")

    # synergy — cross-platform RCM savings math
    syn = sub.add_parser("synergy",
                         help="Cross-platform RCM synergy (shared services) across held deals")
    syn.add_argument("--shared-service-pct", type=float, default=0.40,
                     help="Fraction of RCM cost routed through shared services (default 0.40)")
    syn.add_argument("--savings-pct", type=float, default=0.15,
                     help="Savings rate on shared portion (default 0.15; PE ops benchmark range 0.10-0.20)")
    syn.add_argument("--json", action="store_true")

    # exit-memo — HTML memo for buyer diligence
    # B118: Alerts CLI
    al = sub.add_parser("alerts", help="Portfolio alerts (active / ack / history)")
    al_sub = al.add_subparsers(dest="alerts_cmd", required=True)
    al_sub.add_parser("active", help="List active (non-acked) alerts")
    al_sub.add_parser("all", help="List all alerts including acked")
    al_ack = al_sub.add_parser("ack", help="Acknowledge an alert instance")
    al_ack.add_argument("--kind", required=True,
                        help="Alert kind (e.g. covenant_tripped)")
    al_ack.add_argument("--deal-id", required=True)
    al_ack.add_argument("--trigger-key", required=True,
                        help="Trigger-key as returned by `alerts active` JSON")
    al_ack.add_argument("--snooze-days", type=int, default=0)
    al_ack.add_argument("--note", default="")
    al_ack.add_argument("--by", default="", metavar="OWNER")

    # B118: Deadlines CLI
    dl = sub.add_parser("deadlines", help="Deadline inbox (overdue / upcoming / add / complete)")
    dl_sub = dl.add_subparsers(dest="deadlines_cmd", required=True)
    dl_up = dl_sub.add_parser("upcoming", help="Open deadlines due in the next N days")
    dl_up.add_argument("--days", type=int, default=14)
    dl_up.add_argument("--owner", default=None)
    dl_od = dl_sub.add_parser("overdue", help="Deadlines past their due date")
    dl_od.add_argument("--owner", default=None)
    dl_add = dl_sub.add_parser("add", help="Add a deadline to a deal")
    dl_add.add_argument("--deal-id", required=True)
    dl_add.add_argument("--label", required=True)
    dl_add.add_argument("--due-date", required=True, metavar="YYYY-MM-DD")
    dl_add.add_argument("--owner", default="")
    dl_add.add_argument("--notes", default="")
    dl_done = dl_sub.add_parser("complete", help="Mark a deadline done")
    dl_done.add_argument("--id", required=True, type=int, metavar="DEADLINE_ID")

    # B118: Owners CLI
    ow = sub.add_parser("owners", help="Deal ownership (list / assign / show deals)")
    ow_sub = ow.add_subparsers(dest="owners_cmd", required=True)
    ow_sub.add_parser("list", help="Counts by owner")
    ow_deals = ow_sub.add_parser("deals", help="Deals currently owned by a given analyst")
    ow_deals.add_argument("--owner", required=True)
    ow_assign = ow_sub.add_parser("assign", help="Assign a deal to an owner")
    ow_assign.add_argument("--deal-id", required=True)
    ow_assign.add_argument("--owner", required=True)
    ow_assign.add_argument("--note", default="")

    # B125: Users CLI (for multi-user auth setup)
    us = sub.add_parser("users", help="Manage login users (B125)")
    us_sub = us.add_subparsers(dest="users_cmd", required=True)
    us_list = us_sub.add_parser("list", help="List users")
    us_create = us_sub.add_parser("create", help="Create a user")
    us_create.add_argument("--username", required=True)
    us_create.add_argument("--password", required=True)
    us_create.add_argument("--display-name", default="")
    us_create.add_argument("--role", default="analyst",
                           choices=("admin", "analyst"))
    us_del = us_sub.add_parser("delete", help="Delete a user + sessions")
    us_del.add_argument("--username", required=True)
    us_pw = us_sub.add_parser("password", help="Rotate a user's password")
    us_pw.add_argument("--username", required=True)
    us_pw.add_argument("--new-password", required=True)

    # B122: Rerun simulation by deal (uses stored sim-input paths)
    rr = sub.add_parser("rerun",
                        help="Rerun a simulation for a deal with stored paths")
    rr.add_argument("--deal-id", required=True)
    rr.add_argument("--n-sims", type=int, default=5000)
    rr.add_argument("--seed", type=int, default=42)

    # B122: Set or view sim-input paths for a deal
    si = sub.add_parser("sim-inputs",
                        help="Configure actual/benchmark paths for rerun")
    si_sub = si.add_subparsers(dest="si_cmd", required=True)
    si_show = si_sub.add_parser("show", help="Print current sim-input paths")
    si_show.add_argument("--deal-id", required=True)
    si_set = si_sub.add_parser("set", help="Set/update sim-input paths")
    si_set.add_argument("--deal-id", required=True)
    si_set.add_argument("--actual", required=True, metavar="PATH")
    si_set.add_argument("--benchmark", required=True, metavar="PATH")
    si_set.add_argument("--outdir-base", default="", metavar="PATH")

    # B120: LP-update CLI (for external cron / launchd)
    lp = sub.add_parser("lp-update", help="Write the LP-update HTML to a file")
    lp.add_argument("--out", default="lp_update.html", metavar="PATH",
                    help="Output HTML path (default: lp_update.html)")
    lp.add_argument("--days", type=int, default=30,
                    help="Window for recent activity section (default: 30)")
    lp.add_argument("--title", default="LP Update",
                    help="Page title (e.g. 'Fund III — Q2 2026 LP Update')")

    exm = sub.add_parser("exit-memo", help="Generate exit-readiness HTML memo for one deal")
    exm.add_argument("--deal-id", required=True)
    exm.add_argument("--out", default=None, metavar="PATH",
                     help="Output HTML path (default: exit_memo_<deal_id>.html)")
    exm.add_argument("--title", default=None,
                     help="Memo title override (default: 'Exit-Readiness Memo — <deal>')")

    return ap


def main(argv: Optional[List[str]] = None, prog: str = "rcm-mc portfolio") -> int:
    ap = _build_parser(prog)
    args = ap.parse_args(argv)
    if args.cmd == "register":
        return _cmd_register(args)
    if args.cmd == "list":
        return _cmd_list(args)
    if args.cmd == "show":
        return _cmd_show(args)
    if args.cmd == "rollup":
        return _cmd_rollup(args)
    if args.cmd == "dashboard":
        return _cmd_dashboard(args)
    if args.cmd == "actuals":
        return _cmd_actuals(args)
    if args.cmd == "variance":
        return _cmd_variance(args)
    if args.cmd == "digest":
        return _cmd_digest(args)
    if args.cmd == "actuals-import":
        return _cmd_actuals_import(args)
    if args.cmd == "initiative-actual":
        return _cmd_initiative_actual(args)
    if args.cmd == "initiative-variance":
        return _cmd_initiative_variance(args)
    if args.cmd == "initiative-import":
        return _cmd_initiative_import(args)
    if args.cmd == "remark":
        return _cmd_remark(args)
    if args.cmd == "synergy":
        return _cmd_synergy(args)
    if args.cmd == "exit-memo":
        return _cmd_exit_memo(args)
    if args.cmd == "alerts":
        return _cmd_alerts(args)
    if args.cmd == "deadlines":
        return _cmd_deadlines(args)
    if args.cmd == "owners":
        return _cmd_owners(args)
    if args.cmd == "lp-update":
        return _cmd_lp_update(args)
    if args.cmd == "rerun":
        return _cmd_rerun(args)
    if args.cmd == "sim-inputs":
        return _cmd_sim_inputs(args)
    if args.cmd == "users":
        return _cmd_users(args)
    ap.print_help()
    return 2


def _cmd_users(args) -> int:
    from .auth.auth import create_user, delete_user, list_users
    store = PortfolioStore(args.db)
    if args.users_cmd == "list":
        print(list_users(store).to_csv(index=False))
        return 0
    if args.users_cmd == "create":
        try:
            create_user(
                store, args.username, args.password,
                display_name=args.display_name, role=args.role,
            )
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(json.dumps({"ok": True, "username": args.username}))
        return 0
    if args.users_cmd == "delete":
        ok = delete_user(store, args.username)
        print(json.dumps({"deleted": ok}))
        return 0 if ok else 1
    if args.users_cmd == "password":
        from .auth.auth import change_password
        try:
            ok = change_password(store, args.username, args.new_password)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        if not ok:
            print(f"ERROR: user {args.username!r} not found", file=sys.stderr)
            return 1
        print(json.dumps({"ok": True, "username": args.username}))
        return 0
    return 2


def _cmd_rerun(args) -> int:
    """B122: queue a simulation using a deal's stored paths.

    Blocking-ish: submits and waits briefly; returns 0 on queued (not
    on sim completion — the CLI is cron-friendly and a long-running
    sim shouldn't block the caller).
    """
    import os as _os
    from .deals.deal_sim_inputs import get_inputs, next_outdir
    from .infra.job_queue import get_default_registry
    store = PortfolioStore(args.db)
    inputs = get_inputs(store, args.deal_id)
    if inputs is None:
        print(
            f"ERROR: no stored sim inputs for {args.deal_id!r}. "
            f"Set them first with `sim-inputs set`.", file=sys.stderr,
        )
        return 1
    for label, key in (("actual", "actual_path"),
                       ("benchmark", "benchmark_path")):
        p = inputs[key]
        if not _os.path.isfile(p):
            print(f"ERROR: {label} path does not exist: {p}",
                  file=sys.stderr)
            return 1
    outdir = next_outdir(args.deal_id, inputs.get("outdir_base") or "")
    reg = get_default_registry()
    job_id = reg.submit_run(
        actual=inputs["actual_path"],
        benchmark=inputs["benchmark_path"],
        outdir=outdir,
        n_sims=args.n_sims, seed=args.seed,
    )
    print(json.dumps({
        "job_id": job_id, "deal_id": args.deal_id, "outdir": outdir,
    }))
    return 0


def _cmd_sim_inputs(args) -> int:
    from .deals.deal_sim_inputs import get_inputs, set_inputs
    store = PortfolioStore(args.db)
    if args.si_cmd == "show":
        data = get_inputs(store, args.deal_id)
        if data is None:
            print(f"(no sim inputs stored for {args.deal_id!r})")
            return 1
        print(json.dumps(data, indent=2))
        return 0
    if args.si_cmd == "set":
        set_inputs(
            store, deal_id=args.deal_id,
            actual_path=args.actual,
            benchmark_path=args.benchmark,
            outdir_base=args.outdir_base,
        )
        print(json.dumps({"ok": True, "deal_id": args.deal_id}))
        return 0
    return 2


def _cmd_lp_update(args) -> int:
    from .reports.lp_update import build_lp_update_html
    store = PortfolioStore(args.db)
    html_doc = build_lp_update_html(
        store, days=args.days, title=args.title,
    )
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(html_doc)
    print(f"Wrote {args.out} ({len(html_doc):,} chars)")
    return 0


def _cmd_alerts(args) -> int:
    from .alerts.alert_acks import ack_alert
    from .alerts.alerts import evaluate_active, evaluate_all
    store = PortfolioStore(args.db)
    if args.alerts_cmd == "active":
        alerts = evaluate_active(store)
        print(json.dumps([a.to_dict() for a in alerts], indent=2, default=str))
        return 0
    if args.alerts_cmd == "all":
        alerts = evaluate_all(store)
        print(json.dumps([a.to_dict() for a in alerts], indent=2, default=str))
        return 0
    if args.alerts_cmd == "ack":
        ack_id = ack_alert(
            store,
            kind=args.kind, deal_id=args.deal_id,
            trigger_key=args.trigger_key,
            snooze_days=args.snooze_days,
            note=args.note, acked_by=args.by,
        )
        print(json.dumps({"ack_id": ack_id}))
        return 0
    return 2


def _cmd_deadlines(args) -> int:
    from .deals.deal_deadlines import (
        add_deadline, complete_deadline, overdue, upcoming,
    )
    store = PortfolioStore(args.db)
    if args.deadlines_cmd == "upcoming":
        df = upcoming(store, days_ahead=args.days, owner=args.owner)
        print(df.to_csv(index=False))
        return 0
    if args.deadlines_cmd == "overdue":
        df = overdue(store, owner=args.owner)
        print(df.to_csv(index=False))
        return 0
    if args.deadlines_cmd == "add":
        did = add_deadline(
            store, deal_id=args.deal_id, label=args.label,
            due_date=args.due_date, owner=args.owner, notes=args.notes,
        )
        print(json.dumps({"deadline_id": did}))
        return 0
    if args.deadlines_cmd == "complete":
        ok = complete_deadline(store, args.id)
        print(json.dumps({"completed": ok}))
        return 0
    return 2


def _cmd_owners(args) -> int:
    from .deals.deal_owners import all_owners, assign_owner, deals_by_owner
    store = PortfolioStore(args.db)
    if args.owners_cmd == "list":
        for o, n in all_owners(store):
            print(f"{o}\t{n}")
        return 0
    if args.owners_cmd == "deals":
        for d in deals_by_owner(store, args.owner):
            print(d)
        return 0
    if args.owners_cmd == "assign":
        rid = assign_owner(
            store, deal_id=args.deal_id, owner=args.owner, note=args.note,
        )
        print(json.dumps({"history_id": rid}))
        return 0
    return 2
