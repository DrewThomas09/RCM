#!/usr/bin/env bash
# Package the v3 pipeline + caches + deliverable into the repo working tree.
set -euo pipefail

SCRATCH=/tmp/claude-0/-home-user-RCM/3de345a1-c58f-5ce6-b747-7cbb0636d5d9/scratchpad
REPO=/home/user/RCM
PIPE=$REPO/RCM_MC/scripts/ift_evidence_v3
REF=$REPO/RCM_MC/rcm_mc/market_reports/reference
DELIV=$REPO/RCM_MC/deliverables

mkdir -p "$PIPE/sections" "$REF/ift_v3_cache" "$DELIV"

# pipeline code
cp "$SCRATCH"/v3lib.py "$SCRATCH"/copy_engine.py "$SCRATCH"/corrections.py \
   "$SCRATCH"/assemble.py "$SCRATCH"/pull.py "$SCRATCH"/verify.py \
   "$SCRATCH"/harness.py "$SCRATCH"/methodology_tab.py \
   "$SCRATCH"/reparse_v27.py "$SCRATCH"/chart_audit.py \
   "$SCRATCH"/scan_fact_tags.py "$SCRATCH"/reconcile_manifest.py \
   "$SCRATCH"/leak_check.py "$SCRATCH"/DELTA_NOTE_v3_5.md "$PIPE/"
for p in "$SCRATCH"/pull1*.py "$SCRATCH"/pull[2-9].py; do
  [ -f "$p" ] && cp "$p" "$PIPE/"
done
cp "$SCRATCH"/sections/sec_*.py "$PIPE/sections/"
cp "$SCRATCH"/v27_charts2.json "$PIPE/"
cp "$SCRATCH"/V3_DESIGN.md "$SCRATCH"/CONTRACT.md "$PIPE/"
cp "$SCRATCH"/CONTRACT_V34.md "$PIPE/" 2>/dev/null || true
for j in v34_seed.json nppes_crosswalk.json throughput_shelf.json \
         b1_verified.json run_log.json medicaid_rates.json \
         contract_corpus.json cohort_990.json state_ems_rosters.json \
         press_registry.json wayback_footprint.json estate_addresses.json \
         footprint_990_sweep.json; do
  [ -f "$SCRATCH/$j" ] && cp "$SCRATCH/$j" "$PIPE/"
done
rm -f "$PIPE"/v27_charts.json "$PIPE"/v27_chart_anchors.json

# input master (the verified v2.7 evidence base)
cp "/root/.claude/uploads/3de345a1-c58f-5ce6-b747-7cbb0636d5d9/bec059da-IFT_Sourced_Evidence_Master_v2_7.xlsx" \
   "$REF/IFT_Sourced_Evidence_Master_v2_7.xlsx"

# caches, gzipped (loader in the repo build reads .json.gz transparently)
rm -f "$REF/ift_v3_cache"/*.json.gz
cp "$SCRATCH/ift_v3_cache/manifest.json" "$REF/ift_v3_cache/manifest.json"
for f in "$SCRATCH"/ift_v3_cache/*.json; do
  b=$(basename "$f")
  [ "$b" = "manifest.json" ] && continue
  gzip -9 -c "$f" > "$REF/ift_v3_cache/$b.gz"
done

# deliverable
cp "$SCRATCH/IFT_Sourced_Evidence_Master_v3_5.xlsx" "$DELIV/"
rm -f "$DELIV/IFT_Sourced_Evidence_Master_v3_4.xlsx"
cp "$SCRATCH/verify_results.json" "$PIPE/"

du -sh "$REF/ift_v3_cache" "$DELIV"/IFT_Sourced_Evidence_Master_v3_5.xlsx "$PIPE"
