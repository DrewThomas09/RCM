#!/bin/bash
# ============================================================
#  SeekingChartis — run_everything.sh
#  Testing, case study, all features walkthrough
# ============================================================
#
#  Usage:
#    ./run_everything.sh            # full walkthrough
#    ./run_everything.sh test       # just run the tests
#    ./run_everything.sh serve      # just launch the server
#    ./run_everything.sh stop       # kill any running instance
#    ./run_everything.sh check      # health + data-mode counts
#    ./run_everything.sh tour       # print the feature-tour URLs
#
# ============================================================

set -e

REPO="/Users/andrewthomas/Desktop/Coding Projects/RCM_MC"
PORT=8090                             # 8080 is often stale
PY="$REPO/.venv/bin/python"
PYTEST="$REPO/.venv/bin/pytest"

cd "$REPO"

# -------------- helpers --------------
banner() { echo; echo "============================================================"; echo " $1"; echo "============================================================"; }

kill_stale() {
  local pids
  pids=$(lsof -ti :8080 -ti :8090 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo "  killing stale seekingchartis on 8080/8090: $pids"
    echo "$pids" | xargs kill 2>/dev/null || true
    sleep 1
  fi
}

# -------------- subcommands --------------
cmd_stop() {
  banner "STOP — killing any running SeekingChartis server"
  kill_stale
  echo "  done."
}

cmd_test() {
  banner "TEST — full targeted test suite (Phase A + Phase B + integration)"
  "$PYTEST" \
      tests/test_finance_models.py \
      tests/test_corpus_provenance.py \
      tests/test_corpus_synthetic_integrity.py \
      tests/test_chartis_integration.py \
      -q
  echo "  Expected: 89 passed, 1 xfailed."
}

cmd_check() {
  banner "CHECK — provenance counts, DCF, LBO sanity"
  "$PY" - <<'PY'
from rcm_mc.data_public.corpus_loader import corpus_counts
from rcm_mc.finance.dcf_model import build_dcf_from_deal
from rcm_mc.finance.lbo_model import build_lbo_from_deal

c = corpus_counts()
print(f"  Corpus     all={c['all']:,}   real={c['real']:,}   synthetic={c['synthetic']:,}")

profile = {"net_revenue": 400e6, "current_ebitda": 50e6}
d = build_dcf_from_deal(profile).to_dict()
print(f"  DCF sample EV=${d['enterprise_value']/1e6:,.0f}M  Y1 FCF=${d['projections'][0]['free_cash_flow']/1e6:,.1f}M  Y1 PV(FCF)=${d['projections'][0]['pv_fcf']/1e6:,.1f}M")

r = build_lbo_from_deal(profile)
print(f"  LBO sample MOIC={r.returns.moic:.2f}x  IRR={r.returns.irr*100:.1f}%  EntryEV=${r.sources_and_uses.enterprise_value/1e6:,.0f}M")
PY
}

cmd_tour() {
  banner "TOUR — feature-by-feature walkthrough URLs (uses http://127.0.0.1:${PORT})"
  cat <<EOF

  Section 1 — PLATFORM (operator surface)
    http://127.0.0.1:${PORT}/home          landing dashboard
    http://127.0.0.1:${PORT}/               portfolio dashboard (legacy shell)
    http://127.0.0.1:${PORT}/alerts        alerts lifecycle (empty on fresh db)
    http://127.0.0.1:${PORT}/audit         audit log
    http://127.0.0.1:${PORT}/import        new-deal wizard

  Section 2 — ANALYTICS (brain pages)
    http://127.0.0.1:${PORT}/pe-intelligence       brain hub (278 modules)
    http://127.0.0.1:${PORT}/deal-screening        corpus-wide PASS/WATCH/FAIL
    http://127.0.0.1:${PORT}/portfolio-analytics   corpus scorecard
    http://127.0.0.1:${PORT}/sponsor-track-record  sponsor league table
    http://127.0.0.1:${PORT}/payer-intelligence    payer-mix regimes
    http://127.0.0.1:${PORT}/rcm-benchmarks        HFMA / MGMA / ASCA bands
    http://127.0.0.1:${PORT}/corpus-backtest       prediction vs realized

  Section 3 — REFERENCE
    http://127.0.0.1:${PORT}/library       655-deal corpus library
    http://127.0.0.1:${PORT}/methodology   docs hub
    http://127.0.0.1:${PORT}/api/docs      OpenAPI / Swagger UI
    http://127.0.0.1:${PORT}/module-index  analytical-module catalog

  Section 4 — PROVENANCE TAGS (look at bottom-of-page)
    http://127.0.0.1:${PORT}/cms-data-browser    green PUBLIC tag  (real feeds)
    http://127.0.0.1:${PORT}/cms-sources         green PUBLIC tag
    http://127.0.0.1:${PORT}/home                amber MIXED tag   (default)
    http://127.0.0.1:${PORT}/fundraising         red SYNTHETIC tag
    http://127.0.0.1:${PORT}/coinvest-pipeline   red SYNTHETIC tag
    http://127.0.0.1:${PORT}/board-governance    red SYNTHETIC tag

  Section 5 — CASE STUDY:  analysis on a real deal
    Step 1 — pick a deal:
      http://127.0.0.1:${PORT}/analysis
    Step 2 — click through the models (IDs vary per db):
      http://127.0.0.1:${PORT}/models/dcf/<deal_id>   DCF with FCF + PV(FCF) fixed in Phase A
      http://127.0.0.1:${PORT}/models/lbo/<deal_id>   LBO with MOIC/IRR fixed in Phase A
      http://127.0.0.1:${PORT}/models/bridge/<deal_id>
      http://127.0.0.1:${PORT}/models/financials/<deal_id>

  Section 6 — KEYBOARD SHORTCUTS
    Cmd+K / Ctrl+K    open command palette (30 shortcuts)
    ? (question mark) show all shortcuts
    g h               home
    g p               portfolio
    g b               PE Intelligence Brain
    g o               Portfolio Analytics
    g l               Library

  Section 7 — API (JSON)
    curl http://127.0.0.1:${PORT}/api/deals
    curl http://127.0.0.1:${PORT}/api/deals/<deal_id>/dcf
    curl http://127.0.0.1:${PORT}/api/deals/<deal_id>/lbo
    curl http://127.0.0.1:${PORT}/api/openapi.json | jq .

EOF
}

cmd_serve() {
  banner "SERVE — launching SeekingChartis on port ${PORT}"
  kill_stale
  echo "  URL: http://127.0.0.1:${PORT}"
  echo "  Ctrl-C to stop."
  echo
  "$PY" seekingchartis.py --port "$PORT" --no-browser
}

cmd_all() {
  banner "FULL WALKTHROUGH"

  # 1. sanity
  banner "(1/4) CHECK"
  cmd_check

  # 2. tests
  banner "(2/4) TEST"
  cmd_test

  # 3. URL tour (printed, not opened)
  banner "(3/4) TOUR — URLs to click through once the server is up"
  cmd_tour

  # 4. server (blocks)
  banner "(4/4) SERVE — server will stay running until Ctrl-C"
  cmd_serve
}

# -------------- dispatch --------------
case "${1:-all}" in
  test)    cmd_test  ;;
  serve)   cmd_serve ;;
  stop)    cmd_stop  ;;
  check)   cmd_check ;;
  tour)    cmd_tour  ;;
  all|"")  cmd_all   ;;
  *) echo "usage: $0 [test|serve|stop|check|tour|all]"; exit 1 ;;
esac
