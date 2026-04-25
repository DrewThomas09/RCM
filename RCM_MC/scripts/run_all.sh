#!/usr/bin/env bash
# run_all.sh — exercise every rcm-mc surface into a single output folder.
#
# Drops everything into ./output v1/ :
#   - HCRIS screening (one-liner, peers, trend CSVs)
#   - Full diligence run (report.html, workbook, partner brief, PE math)
#   - PE math standalone (bridge, returns, grid, covenant JSON)
#   - Portfolio SQLite + dashboard HTML + exit memo
#
# Use ./run_all.sh or bash run_all.sh.

set -euo pipefail

# Resolve repo root so the script works from any cwd
ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$ROOT"

# Activate venv if not already active
if [ -z "${VIRTUAL_ENV:-}" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

OUT="output v1"
mkdir -p "$OUT"

echo ""
echo "════════════════════════════════════════════════════════════════════"
echo "  RCM-MC end-to-end demo — output → $OUT/"
echo "════════════════════════════════════════════════════════════════════"

# ── 1. HCRIS screening ──────────────────────────────────────────────────
echo ""
echo "▶ 1/6  HCRIS screening (lookup)"
python -m rcm_mc.lookup --ccn 360180 --one-liner > "$OUT/01_one_liner.txt"
python -m rcm_mc.lookup --ccn 360180 --markdown   > "$OUT/02_markdown_memo.md"
python -m rcm_mc.lookup --ccn 360180 --peers --trend --out "$OUT/03_lookup_data"

# Batch screen a shortlist
cat > "$OUT/_shortlist.csv" <<'EOF'
ccn
360180
220071
330101
EOF
python -m rcm_mc.lookup --ccns-file "$OUT/_shortlist.csv" --one-liner --sort-by npsr \
  > "$OUT/04_shortlist_brief.txt"

# Dataset diagnostics
python -m rcm_mc hcris info --json > "$OUT/05_hcris_info.json"

# ── 2. Full diligence run (simulation + bundle + brief) ─────────────────
echo "▶ 2/6  Full diligence run (5000 sims, bundle, brief)"
RUN_DIR="$OUT/10_diligence_run"

# Derive a demo actual config that carries a `deal:` section — this makes
# `rcm-mc run` auto-compute the PE bridge/returns/covenant alongside the
# simulation so the downstream portfolio snapshot has full math.
DEMO_CFG="$OUT/_demo_actual.yaml"
cat configs/actual.yaml > "$DEMO_CFG"
cat >> "$DEMO_CFG" <<'EOF'

# ── Demo PE deal structure (added for run_all.sh) ──
deal:
  entry_ebitda: 50000000        # $50M TTM EBITDA at close
  entry_multiple: 9.0            # 9x EV/EBITDA purchase
  exit_multiple: 10.0            # 10x exit (1-turn expansion)
  hold_years: 5
  organic_growth_pct: 0.03       # 3% annual organic growth
  equity_pct: 0.40               # 40% equity / 60% debt
  covenant_max_leverage: 6.5     # senior credit covenant
  interest_rate: 0.08
  portfolio_deal_id: ccf_2026    # auto-register to portfolio
  portfolio_stage: hold
EOF

python -m rcm_mc --actual "$DEMO_CFG" \
       --benchmark configs/benchmark.yaml \
       --outdir "$RUN_DIR" \
       --n-sims 5000 --seed 42 \
       --partner-brief \
       --no-portfolio \
       >/dev/null 2>&1
echo "    wrote: $RUN_DIR/"

# ── 3. PE math standalone ───────────────────────────────────────────────
echo "▶ 3/6  PE deal math (bridge / returns / grid / covenant)"
PE_DIR="$OUT/20_pe_math"
mkdir -p "$PE_DIR"
python -m rcm_mc pe bridge --entry-ebitda 50e6 --uplift 8e6 \
  --entry-multiple 9 --exit-multiple 10 --hold-years 5 --organic-growth 0.03 \
  --json > "$PE_DIR/pe_bridge.json"

python -m rcm_mc pe returns --entry-equity 180e6 --exit-proceeds 459e6 --hold-years 5 \
  --json > "$PE_DIR/pe_returns.json"

python -m rcm_mc pe grid --entry-ebitda 50e6 \
  --uplift-ramp '3:5e6,5:8e6,7:9e6' --entry-multiple 9 \
  --exit-multiples '8,9,10,11' --hold-years '3,5,7' \
  --entry-equity 180e6 --debt-at-entry 270e6 \
  --debt-at-exit '3:240e6,5:220e6,7:200e6' --organic-growth 0.03 \
  --json > "$PE_DIR/pe_hold_grid_wide.json"

# Also a canonical-CSV copy for the UI-6 renderer (pivot grid view)
python -c "
import json, pandas as pd, sys
rows = json.load(open(sys.argv[1]))
pd.DataFrame(rows).to_csv(sys.argv[2], index=False)
" "$PE_DIR/pe_hold_grid_wide.json" "$PE_DIR/pe_hold_grid.csv"

python -m rcm_mc pe covenant --ebitda 50e6 --debt 270e6 \
  --covenant-leverage 6.5 --interest-rate 0.08 \
  --json > "$PE_DIR/pe_covenant.json"

# ── 4. Portfolio lifecycle (in-folder SQLite) ───────────────────────────
echo "▶ 4/6  Portfolio lifecycle (register → actuals → variance)"
DB="$OUT/portfolio.db"

# Register three deals at different stages
python -m rcm_mc portfolio --db "$DB" register --deal-id ccf_2026 --stage loi \
  --run-dir "$RUN_DIR" --notes "Post-QoE greenlight" >/dev/null
python -m rcm_mc portfolio --db "$DB" register --deal-id mgh_2026 --stage sourced >/dev/null
python -m rcm_mc portfolio --db "$DB" register --deal-id nyp_2026 --stage ioi \
  --notes "Management met, strong fit" >/dev/null

# Advance ccf through stages to hold (audit trail)
python -m rcm_mc portfolio --db "$DB" register --deal-id ccf_2026 --stage spa >/dev/null
python -m rcm_mc portfolio --db "$DB" register --deal-id ccf_2026 --stage closed >/dev/null
python -m rcm_mc portfolio --db "$DB" register --deal-id ccf_2026 --stage hold \
  --run-dir "$RUN_DIR" >/dev/null

# Record 4 quarters of actuals as quarterly EBITDA (annual $50M plan → $12.5M/qtr).
# Realistic underperformance — platform drifting from plan each quarter.
for qtr_actual in "2025Q3:11500000:12000000" \
                  "2025Q4:11750000:12250000" \
                  "2026Q1:11600000:12500000" \
                  "2026Q2:11250000:13000000"; do
  qtr=$(echo "$qtr_actual" | cut -d: -f1)
  act=$(echo "$qtr_actual" | cut -d: -f2)
  plan=$(echo "$qtr_actual" | cut -d: -f3)
  python -m rcm_mc portfolio --db "$DB" actuals \
    --deal-id ccf_2026 --quarter "$qtr" \
    --ebitda "$act" --plan-ebitda "$plan" >/dev/null
done

# Initiative attribution (which RCM lever is behind?)
python -m rcm_mc portfolio --db "$DB" initiative-actual \
  --deal-id ccf_2026 --initiative-id prior_auth_improvement \
  --quarter 2026Q2 --impact 8000 >/dev/null
python -m rcm_mc portfolio --db "$DB" initiative-actual \
  --deal-id ccf_2026 --initiative-id coding_cdi_improvement \
  --quarter 2026Q2 --impact 18000 >/dev/null

# ── 5. Portfolio reports ────────────────────────────────────────────────
echo "▶ 5/6  Portfolio reports (rollup, dashboard, variance, digest, remark, synergy, exit memo)"
python -m rcm_mc portfolio --db "$DB" rollup    > "$OUT/30_portfolio_rollup.txt"
python -m rcm_mc portfolio --db "$DB" list      > "$OUT/31_portfolio_list.txt"
python -m rcm_mc portfolio --db "$DB" show --deal-id ccf_2026 \
                                      > "$OUT/32_portfolio_audit_trail.txt"
python -m rcm_mc portfolio --db "$DB" dashboard --out "$OUT/33_portfolio_dashboard.html" \
  --title "RCM Portfolio — Demo Run" >/dev/null

python -m rcm_mc portfolio --db "$DB" variance --deal-id ccf_2026 \
                                      > "$OUT/34_variance_ccf.txt"
python -m rcm_mc portfolio --db "$DB" initiative-variance --deal-id ccf_2026 \
                                      > "$OUT/35_initiative_variance_ccf.txt"
python -m rcm_mc portfolio --db "$DB" digest --since 2025-01-01 \
                                      > "$OUT/36_digest.txt"

# Re-mark based on 4 quarters of actuals
python -m rcm_mc portfolio --db "$DB" remark --deal-id ccf_2026 --as-of 2026Q2 \
                                      > "$OUT/37_remark_ccf.txt"

# Cross-platform synergy (needs held deals)
python -m rcm_mc portfolio --db "$DB" synergy   > "$OUT/38_synergy.txt"

# Exit memo
python -m rcm_mc portfolio --db "$DB" exit-memo --deal-id ccf_2026 \
  --out "$OUT/39_exit_memo_ccf.html" \
  --title "Project CCF — Exit Readiness" >/dev/null

# ── 6. Summary + index ──────────────────────────────────────────────────
echo "▶ 6/6  Index + manifest"
{
  echo "RCM-MC end-to-end demo — $(date '+%Y-%m-%d %H:%M:%S')"
  echo "────────────────────────────────────────────────────────────"
  (cd "$OUT" && find . -type f -not -name '.*' | sort)
} > "$OUT/MANIFEST.txt"

# UI-3: wrap every text/markdown output in a styled HTML sibling so the
# index yields a readable page rather than raw monospace on click.
python -c "
from rcm_mc.text_to_html import wrap_text_files_in_folder
import sys
wrap_text_files_in_folder(sys.argv[1])
" "$OUT" >/dev/null

# UI-6: render known PE JSON payloads (bridge, returns, covenant, hold
# grid) as styled HTML views so clicking doesn't dump raw JSON.
python -c "
from rcm_mc.json_to_html import wrap_pe_artifacts_in_folder
import os, sys
root = sys.argv[1]
wrap_pe_artifacts_in_folder(root)
for entry in os.listdir(root):
    full = os.path.join(root, entry)
    if os.path.isdir(full):
        wrap_pe_artifacts_in_folder(full)
" "$OUT" >/dev/null

# UI-7: wrap short CSVs (≤500 rows) in styled sortable HTML tables.
# Huge CSVs (5k+ row simulations.csv) intentionally left as raw files.
python -c "
from rcm_mc.csv_to_html import wrap_csvs_in_folder
import os, sys
root = sys.argv[1]
wrap_csvs_in_folder(root)
for entry in os.listdir(root):
    full = os.path.join(root, entry)
    if os.path.isdir(full) and not entry.startswith('_'):
        wrap_csvs_in_folder(full)
" "$OUT" >/dev/null

# UI-4: one landing page that navigates everything (built AFTER the HTML
# companions land so the index picks them up as Deliverables).
python -c "from rcm_mc.output_index import build_indices_recursive as b; import sys; [print(p) for p in b(sys.argv[1])]" "$OUT" >/dev/null

echo ""
echo "✓ Done. All outputs in: $OUT/"
echo "  ▶ Open this first:  open \"$OUT/index.html\""
