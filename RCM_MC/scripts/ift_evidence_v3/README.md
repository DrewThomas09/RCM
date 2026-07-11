# IFT Sourced Evidence Master v3 — build pipeline

Deterministic pipeline that produces
`RCM_MC/deliverables/IFT_Sourced_Evidence_Master_v3_3.xlsx` (~269 tabs,
~13,000 printed pages, ~197 native charts, facts F001–F442, sources
S001–S312) from:

1. **The v2.7 master** (`rcm_mc/market_reports/reference/IFT_Sourced_Evidence_Master_v2_7.xlsx`)
   — carried forward cell-for-cell (values, formulas, styles, comments); the
   copy is proven by recalculating in LibreOffice and diffing every cell
   against v2.7's cached values (zero diffs), and the 37 v2.7 charts are
   re-created natively from a full-fidelity re-parse of their XML
   (`reparse_v27.py` → `v27_charts2.json`: series, names, categories, axis
   number formats, bar direction).
2. **The platform IFT database** (`rcm_mc/market_reports/ift_*.py` and vendored
   files under `rcm_mc/data/vendor/`) — only GOV / SOURCED / ACADEMIC /
   PUBLIC-WEB-labeled content; everything ILLUSTRATIVE is quarantined on
   Excluded_Not_Sourced.
3. **Live government-API pulls** (CMS data.cms.gov, Care Compare PDC, BLS QCEW,
   Census, CDC PLACES, OIG LEIE) — cached under
   `rcm_mc/market_reports/reference/ift_v3_cache/` (gzipped JSON) with a
   manifest (endpoint, dataset UUID, filters, rows, SHA-256, UTC timestamp)
   rendered on the workbook's Pull_Manifest tab.

## Charts (v3.3)

Every chart — v3-built and v2.7-carried — goes through one house-style layer
in `v3lib.py`:

- `add_chart()` builds single-axis Bar/Line charts only; anything that wants
  a second value axis is built as two separate charts at the call site.
- `style_chart()` enforces the style: bottom category axis (left for
  horizontal bars), explicit `delete=0` axes, palette series colours and
  line weights, no smoothing, bottom legend only when there are 2+ series,
  subtle value gridlines, 11pt navy titles, 8pt tick labels.
- `normalize_all_charts()` runs workbook-wide before save: restyles every
  chart and resolves chart-on-chart collisions using true column/row
  geometry.
- `format_sweep()` normalizes print setup on every tab and widens columns
  whose text is clipped against a non-empty right neighbour.
- `chart_audit.py` is the standalone XML auditor used to find chart defects;
  `verify.py` gate **V9** re-runs the structural checks on every build.

## Regenerate

```bash
pip install openpyxl                     # the only build dep (pandas optional)
cd RCM_MC/scripts/ift_evidence_v3

# 1. (optional) re-pull the live artifacts — otherwise the committed caches are used
python3 pull.py && python3 pull2.py && python3 pull3.py && python3 pull4.py && python3 pull5.py && python3 pull6.py && python3 pull7.py

# 2. assemble (first pass), verify, then re-assemble with the verification
#    numbers stamped into Verification_Log Panel K
export IFT_V27_XLSX=../../rcm_mc/market_reports/reference/IFT_Sourced_Evidence_Master_v2_7.xlsx
export IFT_V3_CACHE=../../rcm_mc/market_reports/reference/ift_v3_cache
export IFT_V3_OUT=../../deliverables/IFT_Sourced_Evidence_Master_v3_3.xlsx
python3 assemble.py
python3 verify.py                        # needs libreoffice-calc for the recalc gate
python3 assemble.py verify_results.json
python3 verify.py                        # must print ALL GATES PASS
```

## Verification gates (verify.py)

- **V1 fidelity** — every carried v2.7 cell recalculates to the same value
  (10,679 cells, 0 diffs), excluding the rebuilt README/Source_Index/
  Methodology and the edits enumerated on V3_Change_Log.
- **V2 zero errors** — LibreOffice full recalc of all 50k+ formulas yields no
  Excel error cells.
- **V3 recompute** — derived cells re-derived in python from the cached
  artifacts match to 1e-6.
- **V7 deliverable gates** — >= 200 tabs, >= 200 printed-page estimate,
  >= 29 MB.
- **V8 ledger integrity** — Fact IDs and Source IDs contiguous; every fact's
  home tab exists.
- **V9 chart integrity** — no combo/secondary-axis charts, house axis
  positions with explicit `delete=0`, no smoothed line series, no zero-series
  charts, no chart-on-chart overlaps (exact geometry).

Section builders live in `sections/` — one module per tab family, each
returning its facts / sources / exclusions for the governance merge in
`assemble.py`. The Methodology tab is rebuilt by `methodology_tab.py`
(harvests the carried v2.7 wording, repairs the `data-api/revision 1/` URL
artifact, adds the v3 pipeline/gate sections). Tests:
`RCM_MC/tests/test_ift_evidence_v3.py` validates the committed deliverable
without regenerating it, including the v3.3 chart house-style guards.
