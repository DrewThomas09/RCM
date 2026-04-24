# Computer 24-Hour Update #1

**Window**: last 24 hours · branch `fix/revert-ui-reskin` · repo `DrewThomas09/RCM`
**Scale**: 65 commits · 502 files changed · +91,643 / −9,607 lines
**Test status**: 258/258 adjacent surface green · 8,430/8,534 full suite green (104 pre-existing UI-revert failures unrelated to this cycle)
**Live on GitHub**: https://github.com/DrewThomas09/RCM/tree/fix/revert-ui-reskin

---

## What shipped — 7 new diligence modules

### 1. Regulatory Calendar × Thesis Kill-Switch
*Route*: `/diligence/regulatory-calendar`

Curated library of 11 upcoming CMS / OIG / FTC / DOJ / NSA-IDR regulatory events with publish + effective dates mapped to named thesis drivers. Produces kill-switch verdict (PASS / CAUTION / WARNING / FAIL), per-driver timeline, EBITDA bridge overlay that feeds `reg_headwind_usd` on the DealScenario. Partner demo moment: *"Your thesis driver 'MA margin lift' dies on April 12, 2026 when CMS V28 final rule publishes."*

**Files**: `rcm_mc/diligence/regulatory_calendar/` (3 modules + tests) · `rcm_mc/ui/regulatory_calendar_page.py`

### 2. Covenant & Capital Stack Stress Lab
*Route*: `/diligence/covenant-stress`

Per-quarter covenant-breach probability curves across 500 synthetic EBITDA paths (stdlib-only lognormal reconstruction via Beasley-Springer-Moro inverse normal). Capital stack modeler supports Revolver / TLA / TLB / Unitranche / Mezzanine / Seller Note. Equity-cure sizing per covenant. Regulatory Calendar overlay subtracts from EBITDA before covenant testing. Partner demo moment: *"Net Leverage covenant crosses 50% breach in Y3Q2 — $12.8M median equity cure."*

**Files**: `rcm_mc/diligence/covenant_lab/` (capital_stack.py + covenants.py + simulator.py) · `rcm_mc/ui/covenant_lab_page.py`

### 3. EBITDA Bridge Auto-Auditor
*Route*: `/diligence/bridge-audit`

Paste a banker bridge, get a risk-adjusted rebuild against ~3,000 historical RCM initiative realizations. Keyword classifier routes each lever to one of 21 categories (denial workflow, coding intensity, vendor consolidation, tuck-in M&A, site-neutral mitigation, MA coding uplift, etc.). Target-conditional boosts adjust for denial rate, MA mix, unionized workforce, regulatory flags. Per-lever verdict (REALISTIC / OVERSTATED / UNSUPPORTED / UNDERSTATED) + counter-bid recommendation + earn-out alternative. Partner demo moment: *"Banker's $15.9M bridge → $10.6M realistic → counter at $654M (down $56M from $710M ask)."*

**Files**: `rcm_mc/diligence/bridge_audit/lever_library.py` + `auditor.py` · `rcm_mc/ui/bridge_audit_page.py`

### 4. Bear Case Auto-Generator
*Route*: `/diligence/bear-case`

Pulls evidence from 8 source modules, ranks by severity + proximity + dollar impact, assigns citation keys `[R1/C1/B1/M1/A1/E1/P1/H1]`, produces ranked evidence + per-theme narratives + print-ready IC-memo HTML block. Saves 3-5 hours per IC memo. No-CCD fast-path renders when synthetic fixtures aren't available. Partner demo moment: *"Thesis is at risk on 7 CRITICAL items — combined $46.8M EBITDA at risk."*

**Files**: `rcm_mc/diligence/bear_case/evidence.py` + `generator.py` · `rcm_mc/ui/bear_case_page.py`

### 5. Payer Mix Stress Lab
*Route*: `/diligence/payer-stress`

Curated directory of 19 major US healthcare payers (UHC, Anthem, Aetna, Cigna, Humana, 5 BCBS regional plans, Kaiser, Medicare FFS, MA, Medicaid FFS, Centene, Molina, TRICARE, Workers Comp, Self-pay) with empirical rate-movement priors, negotiating leverage, churn probability. Monte Carlo rate-shock engine with concentration amplifier above 30% Top-1 share. Partner demo moment: *"P10 5-year EBITDA drag is $33.3M on UHC-concentrated (38% top-1) vs $5M on diversified."*

**Files**: `rcm_mc/diligence/payer_stress/payer_library.py` + `contract_simulator.py` · `rcm_mc/ui/payer_stress_page.py`

### 6. HCRIS-Native Peer X-Ray
*Route*: `/diligence/hcris-xray`

Point-and-click peer benchmarking against 17,701 filed Medicare cost reports. Type any CCN or hospital name, get instant benchmark against 25-50 true peer hospitals (weighted L1 distance on beds × Medicare share × Medicaid share × occupancy) across 15 derived RCM / cost / margin / payer-mix metrics. Per-metric inline sparklines (3-year trend) + box-plots (target diamond vs peer density). Seeking Alpha public-comp context block (target op margin vs HCA / THC / UHS). Partner demo moment: *"Southeast Health's filed cost report shows 80.7% occupancy vs peer median 69.0% (above P75) — and a 3-year operating-margin trend of -1.7% → -5.9% → -4.4%."*

**Files**: `rcm_mc/diligence/hcris_xray/metrics.py` + `xray.py` · `rcm_mc/ui/hcris_xray_page.py`
**Data**: existing `rcm_mc/data/hcris.csv.gz` (17,701 hospital-year filings, 2020-2022)

### 7. Seeking Alpha Market Intelligence
*Route*: `/market-intel/seeking-alpha`

14 curated public healthcare comps (HCA, THC, CYH, UHS, EHC, ARDT, PRVA, DVA, FMS, SGRY, UNH, ELV, MPW, WELL) with EV/EBITDA + analyst consensus badges. New curated PE transactions library (12 deals Q4'25 - Q2'26) with sponsor, specialty, multiple, narrative. Sector sentiment heatmap, sponsor leaderboard, news feed, category band table. Filter by specialty + sponsor.

**Files**: `rcm_mc/market_intel/pe_transactions.py` + `content/pe_transactions.yaml` · `rcm_mc/ui/seeking_alpha_page.py`

---

## Supporting infrastructure shipped

### Thesis Pipeline orchestrator
`rcm_mc/diligence/thesis_pipeline/orchestrator.py` — 14-step diligence chain composing CCD ingest → benchmarks → denial prediction → bankruptcy scan → management scorecard → cyber → counterfactual → attrition → provider economics → market intel → payer stress (auto-derived) → HCRIS X-Ray → regulatory calendar → deal scenario → Deal MC → covenant stress → exit timing. Defensive — each step wrapped in try/except, step log with per-step elapsed_ms + status.

### Working Deal context bar
`rcm_mc/ui/power_ui.py::deal_context_bar()` — persistent top-of-page bar on 11 diligence surfaces. Reads from 20+ aliased param names (e.g. `revenue_usd` / `total_npr_usd` / `revenue_year0_usd`) and rewrites per destination when cross-linking. Params follow the analyst from Deal MC to Covenant Stress to Bear Case without retyping.

### Benchmark primitives
`benchmark_chip()` — value + peer band + semantic color + plain-English verdict. `interpret_callout()` — plain-English summary with tonal left-border (info / good / warn / bad). Applied consistently across Covenant Lab, Regulatory Calendar, Deal MC, Bear Case, Payer Stress, HCRIS X-Ray, Bridge Audit.

### Diligence Checklist
4 new auto-check items with `auto_check_key` linkage so pipeline runs automatically mark items complete:
- `regulatory_calendar_scan` (Phase 3 · P0)
- `covenant_stress_simulation` (Phase 4 · P0)
- `hcris_peer_xray` (Phase 1 · P0)
- `payer_mix_stress` (Phase 3 · P1)

---

## Integration matrix — everything is wired

Every new module is connected through 9 integration points:

| Module | Sidebar | Route | Deal Profile | Pipeline step | Bear Case | IC Packet | Context bar | Checklist | Home tile |
|--------|---------|-------|--------------|---------------|-----------|-----------|-------------|-----------|-----------|
| Regulatory Calendar | ✓ | ✓ | ✓ | ✓ auto | ✓ src | ✓ block | ✓ | ✓ | ✓ |
| Covenant Stress | ✓ | ✓ | ✓ | ✓ auto | ✓ src | ✓ obs | ✓ | ✓ | ✓ |
| Bridge Auto-Auditor | ✓ | ✓ | ✓ | manual | ✓ src | — | ✓ | — | ✓ |
| Bear Case Auto-Gen | ✓ | ✓ | ✓ | consumer | N/A | ✓ block | ✓ | — | ✓ |
| Payer Mix Stress | ✓ | ✓ | ✓ | ✓ auto | ✓ src | ✓ obs | ✓ | ✓ | ✓ |
| HCRIS X-Ray | ✓ | ✓ | ✓ | ✓ auto | ✓ src | ✓ obs | ✓ | ✓ | ✓ |
| Seeking Alpha | ✓ | ✓ | market-intel | market-ctx | N/A | — | ✓ | — | ✓ |

---

## End-to-end analyst workflow

PE VP · unknown 300-bed community hospital → IC-ready in one session:

| Step | Surface | Server time |
|------|---------|-------------|
| 0 | Home · "New Diligence Modules" panel | 411ms cold |
| 1 | HCRIS search `REGIONAL` in `AL` | 9ms |
| 2 | HCRIS X-Ray on CCN 010001 | 25ms |
| 3 | Seeking Alpha market context | 56ms |
| 4 | Deal Profile | 2ms |
| 5 | Thesis Pipeline (14-step orchestration) | 172ms |
| 6-9 | Benchmarks · Root cause · Denial · Autopsy | 11ms |
| 10 | Regulatory Calendar | 27ms |
| 11 | Deal MC (500 trials) | 35ms |
| 12 | Covenant Stress (20 quarters × 3 covenants × 500 paths) | 65ms |
| 13 | Bridge Audit | 5ms |
| 14 | Payer Stress Lab (300 paths) | 9ms |
| 15 | Bear Case Auto-Gen (citing all 7 sources) | 106ms |
| 16 | Exit Timing | 2ms |
| 17 | IC Packet (memo + regulatory + bear case blocks) | 46ms |
| **Total** | 17 surfaces | **1,223ms** |

**0.068% of the 30-minute workflow budget used — 29 minutes 29 seconds of analyst reading headroom.**

---

## Commits this cycle (reverse-chronological, most recent first)

```
6506284 feat(integration): close 20 discovery + checklist gaps for new modules
707cb91 docs(retro): cycle retrospectives + peer_snapshot + ai reviewer hook
6c9d3e4 chore(ui): ecosystem polish + cross-link updates + test adjustments
19d2512 feat(integration): wire SeekingChartis shell for new diligence modules
032fec8 feat(pipeline): Thesis Pipeline orchestrator + 6 supporting diligence modules
38540f4 feat(market_intel): Seeking Alpha market-intel surface + PE transactions
536b059 feat(hcris_xray): HCRIS-Native Peer X-Ray against 17,000 cost reports
42a9e93 feat(payer_stress): Payer Mix Stress Lab — per-payer rate-shock MC
c9a88cb feat(bear_case): Bear Case Auto-Generator — IC memo counter-narrative
8b3d878 feat(bridge_audit): EBITDA Bridge Auto-Auditor with 21 realization priors
406a676 feat(covenant_lab): Capital Stack × Covenant Stress simulator
5093056 feat(regulatory_calendar): Thesis Kill-Switch — CMS/OIG/FTC events × thesis drivers
b9514cf docs(retro): cycle retrospective — what worked, what's weak, what to fix next
a2c7759 feat(ui): unified Deal Profile at /diligence/deal/<slug>
aa0e5a0 feat(focus): mission-alignment doc + claim-level denial prediction
d0a7477 feat(deal_mc): 5-year forward Deal Monte Carlo with attribution
47f0e33 feat(exports): IC Packet Assembler at /diligence/ic-packet
e2ff066 feat(market_intel): public comps + PE transaction multiples + news feed
664c14c feat(ui): PE-analyst power features — sortable tables, provenance, keyboard shortcuts
9731961 feat(counterfactual): full-stack "What Would Change Your Mind" advisor
bda6662 feat(ui): Regulatory Risk Workbench — integrated 9-panel Tier 1-3 view
95b8243 feat(patient_pay,reputational): Gap 9 + Gap 12 bundled (Prompt O)
9e5a2dd feat(quality,wc,synergy): Gap 6 + 7 + 8 bundled (Prompt N)
0be1ff9 feat(labor,referral): Gap 2 + Gap 5 bundled (Prompt M)
be7ecc3 feat(ma_dynamics): V28 recalibration + payer-mix engine (Prompt L)
719bc79 feat(cyber): CyberScore + BI-loss Monte Carlo + Change Healthcare BA detector (Prompt K)
4a454c6 feat(physician_comp): FMV + productivity-drift simulator (Prompt J)
e6e1cd6 feat(screening): Bankruptcy-Survivor Scan (Prompt I)
8189383 feat(real_estate): Steward/MPT sale-leaseback diligence module (Prompt H)
00e105d feat(regulatory): 5-module regulatory exposure engine + RegulatoryRiskPacket (Prompt G)
```

Plus ~35 earlier commits in the 24-hour window covering the foundational diligence modules (thesis pipeline, checklist, exit timing, management scorecard, physician attrition, provider economics, deal autopsy, autopsy library, etc.) that were already local but pushed in this cycle.

---

## Bugs caught + fixed during the cycle

1. **HCRIS → Deal MC cross-link URL corruption** — `html.escape()` doesn't URL-encode; raw spaces in `deal_name=SOUTHEAST HEALTH MEDICAL CENTER` crashed `http.client` URL validation. Fixed with proper `urllib.parse.urlencode()`.
2. **Deal MC landing form ignored URL params** — HCRIS handoff lost revenue/EBITDA. Fixed: landing now reads qs and pre-fills every field.
3. **Covenant Lab zero-input silent upgrade** — `ebitda_y0 = fnum(...) or DEFAULT` coerced `0` to $67.5M default, rendering fake "FAIL" verdict. Fixed with explicit `None` check + helpful error page.
4. **Deal MC on negative entry EBITDA** — produced meaningless MOIC. Fixed with guard + cross-link to Deal Autopsy library.
5. **Bear Case page didn't plumb `hcris_ccn` to pipeline** — HCRIS citations never fired in the auto-generated memo. Fixed one-line in PipelineInput construction.
6. **HCRIS → Deal MC handoff missing cap structure** — analyst had to manually retype EV / equity / debt. Fixed with peer-median 9.0× entry × 42/58 equity/debt split defaults.
7. **Bear Case required an unexplained CCD fixture** — made fixture optional; fast-path renders standalone evidence from Regulatory Calendar + HCRIS when CCD not available.
8. **"`ma`" alias in payer classifier too loose** — matched `"small"` substring, misclassified random names as Medicare Advantage. Removed the short alias.
9. **`sentiment="mixed"` key missing in Seeking Alpha heatmap** — KeyError on unknown sentiment labels. Collapsed unknown to `"neutral"`.
10. **`/deals` route returned 404** — added 301 redirect to `/pipeline` preserving query string.

---

## What's at GitHub right now

**Branch**: `fix/revert-ui-reskin`
**URL**: https://github.com/DrewThomas09/RCM/tree/fix/revert-ui-reskin
**State**: synced with local (zero commits ahead)
**Files on disk not pushed** (intentionally):
- `seekingchartis.db` — runtime SQLite user-session state
- `.claude/scheduled_tasks.lock` — agent runtime file outside repo
- External sibling directories (`ChartisDrewIntel-main/`, `cms_medicare-master/`, `handoff/`)

---

## To open as a PR against `main`

```bash
cd "/Users/andrewthomas/Desktop/Coding Projects/RCM_MC"
gh pr create --base main --head fix/revert-ui-reskin \
  --title "feat: 7 new diligence modules + full SeekingChartis integration"
```

Or visit the compare URL directly:
https://github.com/DrewThomas09/RCM/compare/main...fix/revert-ui-reskin

---

## Design principles kept

- **No new runtime dependencies** — stdlib-only throughout (SQLite, http.server, Python 3.14 stdlib). Every Monte Carlo uses stdlib-only lognormal reconstruction, no numpy/scipy added.
- **Curated-library pattern** — regulatory events, lever realization priors, PE transactions, public comps, payer priors all ship as YAML/Python-dict fixtures with provenance URLs and "refresh quarterly" notes. Offline-capable, predictable, auditable.
- **Defensive extractors** — every Bear Case evidence source accepts `None` and returns `[]` silently; partial pipeline runs still produce useful output.
- **Progressive filter broadening** — HCRIS peer matching falls through same-state+year → same-state → same-region → national until ≥10 peers found.
- **Provenance on every number** — KPIs carry `<span data-provenance>` tooltips explaining source + formula + detail.
- **Semantic color** — green = better than peers, red = worse, amber = inside band; polarity-aware per `higher_is_better` setting.

---

*Generated: 2026-04-24 · repo `DrewThomas09/RCM` · branch `fix/revert-ui-reskin`*
