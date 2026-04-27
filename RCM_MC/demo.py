#!/usr/bin/env python3
"""One-shot demo of the RCM-MC partner-ops stack.

Seeds a realistic portfolio, starts the HTTP server, and prints the
URLs to click through. Uses a temp DB so it doesn't touch your real
data.

Usage:
    .venv/bin/python demo.py
    # then open http://localhost:8765/login and sign in as either:
    #   username: andrewthomas@chartis.com  password: ChartisDemo1
    #   username: demo                      password: DemoPass!1   (legacy)
"""
from __future__ import annotations

import os
import socket
import sys
import tempfile
import threading
import time
import webbrowser
from datetime import date, datetime, timedelta, timezone

# Make sure we import from this checkout
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rcm_mc.alerts.alert_acks import ack_alert, trigger_key_for
from rcm_mc.alerts.alerts import evaluate_all
from rcm_mc.auth.auth import create_user
from rcm_mc.deals.deal_deadlines import add_deadline
from rcm_mc.deals.deal_notes import record_note
from rcm_mc.deals.deal_owners import assign_owner
from rcm_mc.deals.deal_sim_inputs import set_inputs
from rcm_mc.deals.deal_tags import add_tag
from rcm_mc.deals.health_score import compute_health
from rcm_mc.pe.hold_tracking import record_quarterly_actuals
from rcm_mc.deals.note_tags import add_note_tag
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.portfolio.portfolio_snapshots import register_snapshot
from rcm_mc.server import build_server
from rcm_mc.deals.watchlist import star_deal


PORT = 8765
USERNAME = "demo"
PASSWORD = "DemoPass!1"
# Andrew's primary partner account — added so the rendered login
# page can show a clean, real-shaped credential pair partners can
# read off the screen. Both accounts share role=admin so either
# lands in the same dashboard with the same nav.
PARTNER_USERNAME = "andrewthomas@chartis.com"
PARTNER_PASSWORD = "ChartisDemo1"


def seed(store: PortfolioStore, run_dir: str) -> None:
    """Seed 5 deals spanning green / amber / red + all workflow pieces."""
    # Stage PE artifacts for each deal so evaluators have something real
    import json
    # Friendly display names — the analysis-landing + deals-table show
    # these instead of the raw 3-letter deal_id slug.
    deal_names = {
        "ccf": "Cypress Crossing Health",
        "mgh": "Magnolia Grove Hospital",
        "nyp": "Northvale Physician Partners",
        "buh": "Beacon Urban Health",
        "sth": "Sterling Heights Medical",
    }
    for deal_id, headroom, concerning in [
        ("ccf",  -0.5,  0),   # covenant TRIPPED → red alert
        ("mgh",   0.3,  2),   # covenant TIGHT → amber alert
        ("nyp",   2.0,  4),   # concerning cluster → amber alert
        ("buh",   2.0,  0),   # healthy
        ("sth",   2.0,  1),   # healthy
    ]:
        store.upsert_deal(deal_id, name=deal_names[deal_id])
        ddir = os.path.join(run_dir, deal_id + "_run")
        os.makedirs(ddir, exist_ok=True)
        with open(os.path.join(ddir, "pe_bridge.json"), "w") as f:
            json.dump({"entry_ebitda": 50e6, "entry_ev": 450e6,
                       "entry_multiple": 9.0, "exit_multiple": 10.0,
                       "hold_years": 5.0}, f)
        with open(os.path.join(ddir, "pe_returns.json"), "w") as f:
            json.dump({"moic": 2.5, "irr": 0.20}, f)
        with open(os.path.join(ddir, "pe_covenant.json"), "w") as f:
            json.dump({"actual_leverage": 5.4,
                       "covenant_headroom_turns": headroom}, f)
        if concerning:
            import pandas as pd
            pd.DataFrame({
                "severity": ["concerning"] * concerning + ["neutral"],
            }).to_csv(os.path.join(ddir, "trend_signals.csv"), index=False)
        register_snapshot(store, deal_id, "hold", run_dir=ddir,
                          notes=f"Q1 2026 snapshot for {deal_id}")

    # Quarterly actuals — mix of misses and on-plan
    for deal_id, actual in [
        ("ccf", 7e6),    # ~-42% miss
        ("mgh", 10.5e6), # ~-12% miss
        ("nyp", 11.8e6), # just under plan
        ("buh", 12e6),   # on plan
        ("sth", 13e6),   # beat
    ]:
        record_quarterly_actuals(
            store, deal_id, "2026Q1",
            actuals={"ebitda": actual}, plan={"ebitda": 12e6},
        )

    # Cohort tags
    for deal_id, tags in [
        ("ccf", ["growth", "watch", "fund_3"]),
        ("mgh", ["roll-up", "fund_3"]),
        ("nyp", ["growth", "fund_2"]),
        ("buh", ["roll-up", "fund_2"]),
        ("sth", ["growth", "watch"]),
    ]:
        for t in tags:
            add_tag(store, deal_id=deal_id, tag=t)

    # Owners
    assign_owner(store, deal_id="ccf", owner="AT", note="lead on covenant negotiation")
    assign_owner(store, deal_id="mgh", owner="AT")
    assign_owner(store, deal_id="nyp", owner="SB")
    assign_owner(store, deal_id="buh", owner="SB")
    assign_owner(store, deal_id="sth", owner="JD")

    # Star a few
    for d in ("ccf", "nyp"):
        star_deal(store, d)

    # Deadlines — overdue + upcoming
    today = date.today()
    add_deadline(store, deal_id="ccf", label="Covenant reset call",
                 due_date=(today - timedelta(days=3)).isoformat(),
                 owner="AT")
    add_deadline(store, deal_id="ccf", label="Refi term-sheet review",
                 due_date=(today + timedelta(days=5)).isoformat(),
                 owner="AT")
    add_deadline(store, deal_id="mgh", label="Board prep deck",
                 due_date=(today + timedelta(days=2)).isoformat(),
                 owner="AT")
    add_deadline(store, deal_id="nyp", label="Q2 audit walk-through",
                 due_date=(today + timedelta(days=10)).isoformat(),
                 owner="SB")

    # Notes with searchable content
    n1 = record_note(store, deal_id="ccf",
                     body="Covenant reset discussed with lender. "
                          "Lender open to 0.5x cushion in exchange for "
                          "amendment fee.",
                     author="AT")
    add_note_tag(store, n1, "board_meeting")
    add_note_tag(store, n1, "blocker")
    n2 = record_note(store, deal_id="mgh",
                     body="Q1 close timeline slipped by 2 weeks. "
                          "CFO requested additional working capital.",
                     author="AT")
    add_note_tag(store, n2, "board_meeting")
    record_note(store, deal_id="nyp",
                body="Integration on track. New hire starts next month.",
                author="SB")
    record_note(store, deal_id="sth",
                body="Outperforming plan by 8%. Considering exit "
                     "window Q3 2027.",
                author="JD")

    # Store sim-input paths so /deal/ccf gets a live Rerun button
    actual_yaml = os.path.join(run_dir, "actual.yaml")
    bench_yaml = os.path.join(run_dir, "benchmark.yaml")
    for p in (actual_yaml, bench_yaml):
        open(p, "w").close()
    set_inputs(store, deal_id="ccf",
               actual_path=actual_yaml, benchmark_path=bench_yaml,
               outdir_base=os.path.join(run_dir, "ccf_reruns"))

    # Pre-populate alert history + one acked alert so the demo has
    # returning/escalation signals
    for a in evaluate_all(store):
        pass  # side effect: populates alert_history
    alerts = evaluate_all(store)
    for a in alerts:
        if a.kind == "covenant_tight":
            ack_alert(store, kind=a.kind, deal_id=a.deal_id,
                      trigger_key=trigger_key_for(a),
                      snooze_days=7, note="acknowledged, lender aware",
                      acked_by=USERNAME)
            break

    # Health snapshot history (for trend arrows)
    from rcm_mc.deals.health_score import _record_history
    for deal_id in ("ccf", "mgh", "nyp", "buh", "sth"):
        h = compute_health(store, deal_id)
        if h["score"] is not None:
            _record_history(store, deal_id,
                            min(100, h["score"] + 10),
                            h["band"],
                            today=today - timedelta(days=1))


def port_free(p):
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", p))
            return True
        except OSError:
            return False


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="rcm_demo_")
    db_path = os.path.join(tmp, "portfolio.db")
    run_dir = os.path.join(tmp, "runs")
    os.makedirs(run_dir, exist_ok=True)

    store = PortfolioStore(db_path)

    # Seed demo data first (while still in single-user mode)
    seed(store, run_dir)

    # Create the demo admin last — this switches the server into
    # multi-user mode, so all subsequent access goes through /login.
    # Both accounts get role=admin so they land in the same
    # dashboard with the same permissions.
    create_user(store, USERNAME, PASSWORD,
                display_name="Demo Partner", role="admin")
    create_user(store, PARTNER_USERNAME, PARTNER_PASSWORD,
                display_name="Andrew Thomas", role="admin")

    # Pick a port
    port = PORT
    while not port_free(port) and port < PORT + 20:
        port += 1

    server, _ = build_server(
        port=port, db_path=db_path, outdir=run_dir,
        title="RCM-MC Demo Portfolio",
    )
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    url = f"http://127.0.0.1:{port}"
    line = "━" * 68
    print()
    print(line)
    print("   RCM-MC demo is running")
    print(line)
    print()
    print(f"   Open in your browser:   {url}/login")
    print()
    print(f"   Username:  {USERNAME}")
    print(f"   Password:  {PASSWORD}")
    print()
    print("   After you sign in the dashboard will show a guided-tour")
    print("   card at the top that walks you through the six main")
    print("   partner workflows (alerts → my work → deal detail →")
    print("   cohorts → LP update → audit). Follow it in order.")
    print()
    print(f"   Temp DB (deleted on exit):  {db_path}")
    print(f"   Press Ctrl-C to stop.")
    print(line)
    print()

    try:
        webbrowser.open(f"{url}/login")
    except Exception:
        pass

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n  Shutting down.")
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
