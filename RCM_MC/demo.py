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


# Hosted PaaS platforms inject ``PORT`` (legacy App Service also set ``WEBSITES_PORT``)
# at container start; honour both before falling back to the dev
# default. ``RCM_MC_HOST`` is our explicit override for binding —
# A platform front-end expects 0.0.0.0 (the container's loopback isn't reachable
# by the platform's HTTP front-end). Detect a PaaS via the legacy
# ``WEBSITE_HOSTNAME`` env var that App Service always sets, and
# default HOST to 0.0.0.0 in that case so a partner shipping an
# PaaS deploy doesn't have to remember the binding step. Local dev
# (no PaaS env markers) still binds 127.0.0.1 so a casual demo.py run
# isn't surprise-exposed on the LAN.
PORT = int(
    os.environ.get("PORT")
    or os.environ.get("WEBSITES_PORT")
    or 8765
)
_RUNNING_ON_PAAS = bool(
    os.environ.get("WEBSITE_HOSTNAME")
    or os.environ.get("WEBSITES_PORT")
)
HOST = (
    os.environ.get("RCM_MC_HOST")
    or ("0.0.0.0" if _RUNNING_ON_PAAS else "127.0.0.1")
)
USERNAME = "demo"
PASSWORD = "DemoPass!1"

# Workstream H (BACKLOG #10) — ONE of the five demo deals is rebuilt on a
# real, named CCN: ``sth`` IS White Plains Hospital (CCN 330304, NY), the
# facility the healthy-beat archetype was anchored to. Its HCRIS-filed
# metrics (NPR, beds, operating margin, Medicare share) seed as
# observed_metrics with source="HCRIS" — looked up from the live vendored
# frame at seed time so the numbers can never drift from the filing — and
# the UI relabels exactly those metrics ENTERED→ACTUAL. The RCM workflow
# metrics (denial / collection) stay illustrative: HCRIS files no such
# fields, and pretending otherwise is the kind of fake-data move the demo
# exists to avoid.
_REAL_CCN_DEAL = "sth"
_REAL_CCN = "330304"
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
        # sth is the real-CCN deal (see _REAL_CCN_DEAL): at seed time its
        # name is replaced by the facility's filed HCRIS name ("White
        # Plains Hospital"); this entry is only the frame-unavailable
        # fallback.
        "sth": "Sterling Heights Medical",
    }
    # Per-deal RCM observed metrics so the analysis-workbench
    # RCM Profile tab populates with real values instead of an
    # empty header row. Worse-performing deals (ccf, mgh) get
    # higher denial / AR / AR-over-90 to match their tripped /
    # tight covenant headroom; healthy deals (buh, sth) get
    # cleaner numbers. Keys must match RCM_METRIC_REGISTRY.
    # Percent metrics are stored 0-100 (not 0-1) to match the
    # registry's benchmark_pXX scale.
    rcm_metrics_per_deal = {
        "ccf": {  # tripped — broken RCM
            "denial_rate":          14.2,
            "final_denial_rate":     6.1,
            "days_in_ar":           58.4,
            "ar_over_90_pct":       22.4,
            "clean_claim_rate":     84.2,
            "net_collection_rate":  91.8,
            "dnfb_days":             7.8,
            "charge_lag_days":       4.2,
            "cost_to_collect":       4.1,
        },
        "mgh": {  # tight — soft RCM
            "denial_rate":          11.8,
            "final_denial_rate":     4.4,
            "days_in_ar":           52.1,
            "ar_over_90_pct":       18.3,
            "clean_claim_rate":     88.1,
            "net_collection_rate":  93.7,
            "dnfb_days":             6.4,
            "charge_lag_days":       3.6,
            "cost_to_collect":       3.4,
        },
        "nyp": {  # concerning cluster
            "denial_rate":           9.7,
            "final_denial_rate":     2.9,
            "days_in_ar":           49.3,
            "ar_over_90_pct":       15.1,
            "clean_claim_rate":     90.6,
            "net_collection_rate":  95.1,
            "dnfb_days":             5.1,
            "charge_lag_days":       2.9,
            "cost_to_collect":       2.9,
        },
        "buh": {  # healthy
            "denial_rate":           7.8,
            "final_denial_rate":     2.2,
            "days_in_ar":           42.6,
            "ar_over_90_pct":       11.8,
            "clean_claim_rate":     92.8,
            "net_collection_rate":  96.4,
            "dnfb_days":             4.2,
            "charge_lag_days":       2.4,
            "cost_to_collect":       2.6,
        },
        "sth": {  # healthy beat
            "denial_rate":           6.2,
            "final_denial_rate":     1.7,
            "days_in_ar":           38.9,
            "ar_over_90_pct":        9.4,
            "clean_claim_rate":     94.3,
            "net_collection_rate":  97.2,
            "dnfb_days":             3.4,
            "charge_lag_days":       2.1,
            "cost_to_collect":       2.2,
        },
    }
    for deal_id, headroom, concerning in [
        ("ccf",  -0.5,  0),   # covenant TRIPPED → red alert
        ("mgh",   0.3,  2),   # covenant TIGHT → amber alert
        ("nyp",   2.0,  4),   # concerning cluster → amber alert
        ("buh",   2.0,  0),   # healthy
        ("sth",   2.0,  1),   # healthy
    ]:
        # Wrap each metric in the ObservedMetric shape the packet
        # builder expects (value + quality flags).
        observed = {
            k: {"value": v, "quality_flags": []}
            for k, v in rcm_metrics_per_deal.get(deal_id, {}).items()
        }
        # Workstream H — composite demo deals: each fictional deal is
        # ANCHORED to a real, named HCRIS facility chosen to match its
        # archetype (covenant-tripped → a real deep-negative-margin system;
        # healthy-beat → a real ~+9% one). The anchor's filed financials are
        # ACTUAL public data; the RCM metrics above remain illustrative demo
        # values (HCRIS has no denial/NCR fields) and are labeled as such.
        # Anchors picked 2026-06-10 from the live frame (margin band +
        # 120-400 beds + $100M-$1.5B NPR):
        #   ccf → 240004 Hennepin County Medical Center (MN, −11.2%)
        #   mgh → 050039 Enloe Medical Center (CA, −0.5%)
        #   nyp → 330182 St. Francis Hospital (NY, +2.0%)
        #   buh → 500129 Tacoma General Allenmore (WA, +5.1%)
        # sth graduated from composite-anchor to a FULL real-CCN rebuild
        # (330304 White Plains Hospital, NY, +8.7%) — see _REAL_CCN_DEAL.
        _anchor_ccn = {"ccf": "240004", "mgh": "050039", "nyp": "330182",
                       "buh": "500129"}.get(deal_id)
        profile = {"observed_metrics": observed,
                   "rcm_metrics_basis": "illustrative-demo"}
        deal_name = deal_names[deal_id]
        if deal_id == _REAL_CCN_DEAL:
            # The real-CCN deal: name + observed financial metrics come
            # straight from the facility's filed cost report. Resilient —
            # a missing/failed frame falls back to the fictional seed so
            # the demo always boots.
            try:
                from rcm_mc.data.hcris import _get_latest_per_ccn
                _rows = _get_latest_per_ccn()
                _rows = _rows[_rows["ccn"].astype(str) == _REAL_CCN]
                if len(_rows):
                    r = _rows.iloc[0]
                    npr = float(r["net_patient_revenue"])
                    opex = float(r["operating_expenses"])
                    fy = int(r["fiscal_year"])
                    deal_name = str(r["name"]).title()
                    detail = f"CMS HCRIS CCN {_REAL_CCN} FY{fy}"
                    sourced = {
                        "net_revenue": npr,
                        "bed_count": float(r["beds"]),
                        # Patient-basis operating margin — the same
                        # (NPR - opex)/NPR the screener trusts.
                        "ebitda_margin": round((npr - opex) / npr, 4),
                        "medicare_day_pct": round(
                            float(r["medicare_day_pct"]), 4),
                    }
                    for k, v in sourced.items():
                        # Nested ObservedMetric shape carries the per-metric
                        # provenance (drives the ENTERED→ACTUAL relabel);
                        # flat copies keep every flat-key reader working.
                        observed[k] = {"value": v, "source": "HCRIS",
                                       "source_detail": detail,
                                       "quality_flags": []}
                        profile[k] = v
                    profile.update({
                        "state": str(r["state"]), "ccn": _REAL_CCN,
                        "hcris_ccn": _REAL_CCN, "hcris_fy": fy,
                        "metrics_basis": (
                            f"ACTUAL — filed HCRIS values, CCN {_REAL_CCN} "
                            f"FY{fy}"),
                    })
            except Exception:  # noqa: BLE001 — demo must seed regardless
                pass
        if _anchor_ccn:
            try:
                from rcm_mc.data.hcris import _get_latest_per_ccn
                from rcm_mc.ui.regression_page import _add_computed_features
                _row = _add_computed_features(_get_latest_per_ccn())
                _row = _row[_row["ccn"].astype(str) == _anchor_ccn]
                if len(_row):
                    r = _row.iloc[0]
                    profile["ccn"] = _anchor_ccn
                    profile["state"] = str(r.get("state") or "")
                    profile["facility_anchor"] = {
                        "ccn": _anchor_ccn,
                        "name": str(r.get("name") or ""),
                        "state": str(r.get("state") or ""),
                        "fiscal_year": int(r.get("fiscal_year") or 0),
                        "beds": float(r.get("beds")) if r.get("beds") == r.get("beds") else None,
                        "net_patient_revenue": float(r.get("net_patient_revenue"))
                            if r.get("net_patient_revenue") == r.get("net_patient_revenue") else None,
                        "operating_margin": float(r.get("operating_margin"))
                            if r.get("operating_margin") == r.get("operating_margin") else None,
                        "source": "CMS HCRIS (latest authoritative filing)",
                    }
            except Exception:  # noqa: BLE001 — anchor is additive; demo must seed
                pass
        store.upsert_deal(
            deal_id, name=deal_name,
            profile=profile,
        )
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
    # ``RCM_MC_DB_PATH`` lets Azure App Service point at a path on
    # the persistent /home volume so the SQLite file survives
    # container restarts. Local dev (env unset) keeps the
    # tempfile.mkdtemp fallback so a casual `python demo.py` run
    # still gets a fresh DB on every invocation. The parent dir
    # is created if missing — saves the partner one mkdir step.
    db_env = (os.environ.get("RCM_MC_DB_PATH") or "").strip()
    if db_env:
        db_path = db_env
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        run_dir = os.path.join(
            os.path.dirname(db_path) or ".", "runs",
        )
    else:
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
    # dashboard with the same permissions. On a persistent DB the
    # users may already exist; idempotent on second run.
    for _u, _p, _dn in (
        (USERNAME, PASSWORD, "Demo Partner"),
        (PARTNER_USERNAME, PARTNER_PASSWORD, "Andrew Thomas"),
    ):
        try:
            create_user(store, _u, _p, display_name=_dn, role="admin")
        except ValueError:
            pass  # already exists on a persistent DB — fine

    # Pick a port
    port = PORT
    while not port_free(port) and port < PORT + 20:
        port += 1

    server, _ = build_server(
        port=port, host=HOST, db_path=db_path, outdir=run_dir,
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
