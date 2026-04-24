# SeekingChartis / RCM-MC

**Full-stack healthcare RCM diligence workbench — local Python, public-data models, ~30 min from tape to IC-ready memo.**

Replaces the $200K–500K third-party-advisory slice of a healthcare diligence (peer benchmarking, regulatory exposure, covenant stress, bridge audit, bear case) with transparent stdlib-heavy models calibrated to public-filing corpora (HCRIS, Care Compare, 10-K, IRS 990). Everything runs on your laptop. No API calls, no SaaS subscription, no black-box scoring — every output traces back to an input and a function you can read.

---

## I need to…

| Goal | Go to |
|------|-------|
| **Install it** | [§4 — Install](#4-install) |
| **See a full MondayAM→ICready walkthrough** | [§5 — Deal walkthrough](#5-deal-walkthrough-mondayam--ic-ready-by-1030am) or the longer [WALKTHROUGH.md](WALKTHROUGH.md) |
| **Find a file or module** | [FILE_INDEX.md](FILE_INDEX.md) |
| **Read a module's methodology** | [§6 — Module methodology](#6-module-methodology) — each links to its per-module README |
| **Audit a number's provenance** | [METRIC_PROVENANCE.md](RCM_MC/docs/METRIC_PROVENANCE.md), [BENCHMARK_SOURCES.md](RCM_MC/docs/BENCHMARK_SOURCES.md) |
| **Read the PE heuristics rulebook** | [PE_HEURISTICS.md](RCM_MC/docs/PE_HEURISTICS.md) — 275+ named partner rules |
| **See what's changed** | [CHANGELOG.md](RCM_MC/CHANGELOG.md), [COMPUTER_24HOUR_UPDATE_NUMBER_1.md](COMPUTER_24HOUR_UPDATE_NUMBER_1.md) |
| **Contribute** | [CONTRIBUTING.md](CONTRIBUTING.md), [CLAUDE.md](RCM_MC/CLAUDE.md) (coding conventions) |

---

## Table of contents

1. [What it does](#1-what-it-does)
2. [Module surface — 17 analytic cuts](#2-module-surface--17-analytic-cuts)
3. [How the models work](#3-how-the-models-work)
4. [Install](#4-install)
5. [Deal walkthrough (Monday AM → IC-ready by 10:30 AM)](#5-deal-walkthrough-mondayam--ic-ready-by-1030am)
6. [Module methodology](#6-module-methodology)
7. [Stack & design choices](#7-stack--design-choices)
8. [File layout](#8-file-layout)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. What it does

Takes a target (CCN or name) and an LOI-style input (NPR, EBITDA, EV, debt, entry multiple, payer mix, landlord) and runs a **19-step pipeline** in ~170ms that produces:

- Peer benchmark across 15 HCRIS metrics vs 25–50 bed/state/region-matched peers (3-yr trend slopes, peer P25/median/P75 bands)
- Regulatory exposure mapped to **named thesis drivers** with first-kill date and annual EBITDA overlay
- 500-path × 20-quarter covenant stress with equity-cure sizing per breach
- Bridge audit of seller synergies against ~3,000-outcome lever-realization priors with counter-bid math
- Payer concentration MC with rate-shock priors and HHI amplifier
- Deal MC (1,500+ trials) with MOIC/IRR/proceeds cones
- Autopsy match against 12 named historical failures (Steward, Cano, Envision, etc.)
- Exit-timing IRR curve × buyer-fit across Y2–Y7
- Auto-generated bear case with `[R/C/B/M/A/E/P/H]` citation keys → print-ready IC memo HTML

Every number is reproducible — same inputs → same outputs, no RNG leakage (seeded where needed), no external network calls.

---

## 2. Module surface — 17 analytic cuts

### Screening
1. **HCRIS Peer X-Ray** — 17,701 Medicare cost reports (FY 2020–2022) × 15 derived metrics × cohort-matched peer group
2. **Bankruptcy-Survivor Scan** — signature match against a named-failure risk matrix
3. **Deal Autopsy** — 12 historical PE healthcare failures with payer-mix × lease × regulatory × physician-concentration signatures

### Diligence
4. **RCM Benchmarks** — 20+ revenue-cycle KPIs (gross denial rate, clean-DAR, cost-to-collect, NPSR realization) vs HFMA peer bands
5. **Denial Prediction** — ridge-regression (stdlib) over claims features with conformal prediction bands
6. **Management Scorecard** — role-weighted (CEO 35% / CFO 25% / COO 20%) forecast-reliability × comp × tenure × prior-role
7. **Physician Attrition** — per-NPI flight-risk with revenue-at-risk rollup
8. **Provider Economics** — per-MD P&L with drop-candidate identification
9. **Payer Mix Stress** — 19 curated payers × historical rate-move priors × HHI concentration amplifier × 500-path MC

### Market / regulatory context
10. **Regulatory Calendar × Kill-Switch** — 11 curated CMS/OIG/FTC/DOJ events × ThesisDriver mapping × first-kill date × EBITDA overlay
11. **Seeking Alpha Intelligence** — 14 public operators + 12 recent PE transactions + sector sentiment
12. **Market Intel** — private deal multiples by specialty × size bucket

### Financial modeling
13. **Deal Monte Carlo** — 1,500+ trials, 8 drivers varied (organic growth, denial improvement, reg headwind, lease escalator, attrition, cyber, V28 compression, exit multiple) with attribution + sensitivity tornado
14. **Covenant Stress Lab** — 500 lognormal paths × 20 quarters × 4 covenants with step-down schedules + equity-cure math + regulatory overlay
15. **Bridge Auto-Auditor** — 21-category keyword-priority classifier × ~3,000-outcome realization priors with target-conditional boosts
16. **Exit Timing + Buyer Fit** — IRR curve × buyer-type scoring (Strategic / PE Secondary / IPO / Sponsor-Hold)

### Synthesis
17. **Bear Case + IC Packet** — 8-source evidence synthesizer, severity × $-impact ranked, citation-keyed, print-ready memo HTML

### Financial modeling (can we make money?)
13. **Deal Monte Carlo** — runs 3,000 simulated futures for the deal, shows the range of possible MOIC (money multiple) and IRR (annual return) outcomes.
14. **Covenant Stress Lab** — models debt payments quarter by quarter, shows probability of breaching loan covenants.
15. **Bridge Auto-Auditor** — paste the seller's synergy claims, get a risk-adjusted rebuild with counter-offer math.
16. **Exit Timing + Buyer Fit** — when should you sell the company, and to whom?

---

## 3. How the models work

Every module follows the same pattern so outputs are auditable:

1. **Curated prior library** — hand-calibrated YAML / Python dataclass tuples (payer rate-move distributions, lever realization priors, regulatory event × driver mappings, PE autopsy signatures). Each prior cites its source (HFMA survey, 10-K commentary, Federal Register docket, retrospective failure analysis). Refresh cadence per file.
2. **Target profile normalization** — LOI inputs + HCRIS lookup feed a `target_profile` dict with specialty, MA mix, payer concentration, landlord, CCN. Modules read from this — no cross-module state.
3. **Monte Carlo where distributions matter** — covenant stress (500 paths × 20 quarters), Deal MC (1,500+ trials × 8 drivers), payer stress (500 paths × horizon years), HCRIS peer-density quantiles. All MC uses stdlib-only Beasley-Springer-Moro inverse normal (no scipy) for reproducibility and zero runtime deps beyond numpy/pandas.
4. **Target-conditional adjustments** — priors aren't static. A denial-workflow lever prior gets +12pp median realization when the target's denial rate is already >8% (low-hanging fruit). An FTE-reduction prior loses 30pp when the target is unionized. These boosts are explicit in the `LeverPrior` dataclass, not hidden in scoring code.
5. **Verdict thresholds → named** — every module emits PASS / CAUTION / WARNING / FAIL against documented numeric cutoffs (e.g., covenant breach-probability >50% = FAIL). Thresholds are in the README for each module, editable in one place.
6. **Dollar-impact rollup** — everything terminates in an EBITDA-at-risk number that feeds downstream. Regulatory overlay → Covenant Lab overlay → Deal MC `reg_headwind_usd` → Bear Case `[R1]` evidence → IC memo headline.

**Trust hooks**:
- Every `@dataclass` output has a `source_module` and `citation_key` field
- Every MC function accepts `seed: int` for deterministic reproduction
- Every prior's calibration source is documented in the module README's "Refreshing the priors" section
- `rcm-mc analysis <deal_id> --explain <metric>` traces any metric back through its provenance graph to raw inputs

---

## 4. Install

Requirements: macOS/Linux (Windows via WSL), Python 3.14, git, ~1 GB disk.

```bash
git clone https://github.com/DrewThomas09/RCM.git
cd RCM
python3.14 -m venv .venv
source .venv/bin/activate
cd RCM_MC
pip install -e ".[all]"
python demo.py
```

Demo seeds a SQLite fixture DB, starts `ThreadingHTTPServer` on `:8080`, opens the browser. No external deps beyond numpy / pandas / pyyaml / matplotlib / openpyxl.

Restart later:

```bash
cd ~/Desktop/RCM/RCM_MC && source ../.venv/bin/activate && python demo.py
```

---

## 5. Deal walkthrough (Monday AM → IC-ready by 10:30 AM)

Scenario: 300-bed Alabama community hospital, $600M ask, IC-memo deadline Friday.

### Monday 9:00 AM — Discover the target

1. Go to `http://localhost:8080/home`
2. You see a panel at the top called **"New Diligence Modules"**. Click **HCRIS Peer X-Ray**.
3. In the search box, type `REGIONAL` and filter state `AL`. You see 26 Alabama hospitals. Pick the one with ~300 beds — say, Southeast Health Medical Center (CCN `010001`).

### 9:02 AM — Get the instant benchmark

The HCRIS X-Ray page loads. You see:

- **Southeast Health is 353 beds** (close to 300)
- **Operating margin: −4.4%** (red — losing money!)
- **3-year trend: DETERIORATING** (red chip). Margin went from -1.7% → -5.9% → -4.4%
- **Occupancy rate: 80.7%** (above peer P75 — the hospital is busy)
- **Medicare day share: 24.9%** (normal)

Per-metric box-plot shows target's position in peer density. 3-yr sparkline shows slope. **Read**: occupancy-strong, margin-distressed, trajectory negative → turnaround thesis only, not a growth story.

### 9:10 AM — Public-market context

**Seeking Alpha** (follows you via the working-deal context bar):

- HCA 8.9× EV/EBITDA — the large-cap peer anchor
- Target margin −4.4% vs HCA +16.9% → 21.3pp gap, not explainable by size alone
- Recent comp: Audax / behavioral platform at 10.8× (size-bucketed)

**Read**: public-hospital tape ≈ 9×; private small-cap premium ≈ +1–2×; distressed adjustment -3–4×. Anchor bid in the 5–6× range.

### 9:15 AM — Open Deal Profile and set the "working deal"

Click **Deal Profile** in the sidebar. Type:
- Target name: `Southeast Health Medical Center`
- Specialty: `HOSPITAL`
- Revenue: `$427M` (from HCRIS)
- EBITDA: `$21M` (5% placeholder since actual is negative)

You now see **tiles for every diligence module**. A thin bar at the top says `Working deal: Southeast Health Medical Center · $427M NPR · $21M EBITDA` — that bar follows you to every page.

### 9:20 AM — Run the full Thesis Pipeline

Click the **Thesis Pipeline** tile. This runs 14 steps in one go (~170ms):

- CCD ingest → benchmarks → denial prediction → bankruptcy scan → management → cyber → counterfactual → attrition → provider economics → market intel → **payer stress** → **HCRIS X-Ray** → **regulatory calendar** → deal scenario → **Deal MC** → **covenant stress** → exit timing

On one page you see every module's headline number + a step log showing how long each took.

### 9:25 AM — Check regulatory risk

Click the **Regulatory Calendar** deep-link. It shows:

- **Verdict: WARNING**
- 2 upcoming CMS/OIG events will "damage" this hospital's thesis drivers
- First impact date: **2026-04-12** (V28 MA coding rule)
- Combined EBITDA overlay: **−$13.2M** across the 5-year hold

### 9:30 AM — Stress test the debt

Click **Covenant Stress Lab**. You plug in:
- Total debt: $250M
- EBITDA: $21M

Output:
- **Verdict: FAIL**
- The Interest Coverage covenant breaches in Y1Q1 — 100% of simulated paths
- Median equity cure: $0.8M (not a lot, but continuous)
- At 11% blended rate × $250M = $27.5M interest vs $21M EBITDA → ICR 0.76× (below 2.25× floor)

**Read**: capital stack broken — can't lever $250M against $21M EBITDA. Either under-lever (equity-rich) or re-cut at lower EV.

### 9:45 AM — Audit the banker's synergies

The banker sent a bridge claiming $15.9M of synergies. Click **Bridge Auto-Auditor**. Paste:

```
Denial workflow overhaul, 4.2M
Coding uplift, 3.1M
Vendor consolidation, 2.8M
AR aging liquidation, 1.5M
Site-neutral mitigation, 1.8M
Tuck-in M&A synergy, 2.5M
```

Output:
- **$15.9M claimed → $10.6M realistic** ($5.3M gap, 33% of claim)
- 2 UNSUPPORTED levers (vendor consolidation + site-neutral — both have >40% historical fail rates)
- 1 OVERSTATED (tuck-in M&A)
- **Recommendation**: counter at **$654M** (down $56M from $710M ask) or structure $4.6M as a 24-month earn-out

### 10:00 AM — Stress test the payer mix

Click **Payer Mix Stress Lab**. The tool automatically built a mix from the hospital's Medicare share. Output:

- **Verdict: WARNING** (Top-1 payer share >30%)
- P10 5-year EBITDA drag: **−$8.4M**
- Worst-exposed payer: **UnitedHealthcare** — cumulative 5-year median rate move −2.1%

### 10:15 AM — Generate the bear case

Click **Bear Case Auto-Generator**. In ~100ms it produces:

> "Thesis is at risk on 7 CRITICAL evidence items — combined $46.8M of EBITDA at risk. Top drivers: Interest Coverage covenant, deteriorating HCRIS margin trend, V28 regulatory kill."

Below that, every evidence item has a citation key `[H1]`, `[C1]`, `[R1]`, etc., grouped by theme (Regulatory / Credit / Operational / Market). At the bottom is a **print-ready IC memo block** you can literally copy-paste into your Word doc.

### 10:30 AM — IC Packet

Click **IC Packet**. Everything from every module is bundled into a single memo with:
- Deal metadata + recommendation (`PROCEED_WITH_CONDITIONS`)
- Waterfall + KPIs
- Bankruptcy scan + autopsy matches
- Counterfactual sensitivity
- Public market context
- **Regulatory timeline block** (auto-injected)
- **Bear case block** (auto-injected)
- Open questions for the banker

Cmd-P prints it cleanly for the partners' Tuesday 8 AM meeting.

---

## 6. Module methodology

Each module's per-file README has the full math. The summaries below cover calibration source, sample size, method, key assumptions, and named thresholds.

### HCRIS Peer X-Ray · `/diligence/hcris-xray` · [README](RCM_MC/rcm_mc/diligence/hcris_xray/README.md)

**Corpus**: 17,701 Medicare cost reports, CMS HCRIS public extract, FY 2020–2022. Cost of 1 cold-load parse ~250ms, cached; subsequent lookups ~7ms.

**Peer-match waterfall**: same cohort (`MICRO / SMALL_COMMUNITY / COMMUNITY / REGIONAL / ACADEMIC` binned on beds) + same state + beds within ±30% → same region → national. Stops at ≥25 peers (configurable via `peer_k`).

**Metric surface**: 15 derived ratios grouped into Size / Payer Mix / Revenue Cycle / Cost Structure / Margin. Each metric has a `direction` flag (HIGHER_BETTER / LOWER_BETTER / NEUTRAL) that drives the green/red coloring logic. Full spec in [`metrics.py`](RCM_MC/rcm_mc/diligence/hcris_xray/metrics.py) `METRIC_SPECS`.

**Trend slope**: 3-year linear slope on same-CCN history; classified IMPROVING / FLAT / DETERIORATING on ±1% annualized threshold.

### Regulatory Calendar × Kill-Switch · `/diligence/regulatory-calendar` · [README](RCM_MC/rcm_mc/diligence/regulatory_calendar/README.md)

**Corpus**: 11 hand-curated events covering CMS V28 HCC, OPPS site-neutral CY2026, TEAM mandatory bundled payment, NSA IDR QPA recalculation, ESRD PPS CY2027, FTC HSR expansion, USAP FTC consent order, CT HB 5316 sale-leaseback phaseout, CMS PFS E/M updates, OIG management-fee advisory, DOJ FCA retroactive coding. Each carries publish / effective dates, affected specialties, impact distribution, thesis drivers killed, Federal Register docket URL.

**Driver mapping**: target profile (specialty, MA mix, payer share, HOPD revenue %, REIT landlord) fed to per-event impact mapper. Driver-level verdict: UNAFFECTED / DAMAGED (>10% impair) / KILLED (>50% impair or zero residual).

**Verdict thresholds**: PASS = no driver impaired >10%. CAUTION = 1 damaged, 0 killed. WARNING = 1 killed OR 2+ damaged. FAIL = 2+ killed.

**Dollar overlay**: per-year EBITDA headwind $ fed downstream to Covenant Lab (subtracted from EBITDA paths pre-test) and Deal MC (`reg_headwind_usd` driver).

### Covenant & Capital Stack Stress Lab · `/diligence/covenant-stress` · [README](RCM_MC/rcm_mc/diligence/covenant_lab/README.md)

**Path reconstruction**: Deal MC yearly P25/P50/P75 bands → 500 lognormal paths via stdlib Beasley-Springer-Moro inverse normal. No scipy.

**Debt schedule**: 6 tranche kinds (REVOLVER / TLA / TLB / UNITRANCHE / MEZZANINE / SELLER_NOTE) with floating or fixed rates, custom amort, commitment fees on undrawn revolver, lien priority. Quarterly interest + scheduled principal + fees.

**Covenants tested** (default set, editable in [`covenants.py`](RCM_MC/rcm_mc/diligence/covenant_lab/covenants.py) `DEFAULT_COVENANTS`): Net Leverage, DSCR, Interest Coverage, Fixed Charge Coverage. Step-downs supported (e.g., 7.5× → 6.0× over Y1–Y4).

**Equity cure math**: for each breaching path × quarter, solve for the minimum $ injection that restores the breached ratio above threshold with cushion.

**Verdict thresholds** (PE bank underwriting norms): max breach probability <10% = PASS · 10–25% = WATCH · 25–50% = WARNING · >50% = FAIL.

### EBITDA Bridge Auto-Auditor · `/diligence/bridge-audit` · [README](RCM_MC/rcm_mc/diligence/bridge_audit/README.md)

**Prior corpus**: ~3,000 historical RCM initiative outcomes calibrated from HFMA/MGMA/AHA surveys + 10-K commentary + retrospective analysis of PE healthcare failures (Steward, Cano, Envision). Refreshed when regulatory environment shifts the failure rate (e.g., V28 dropped `MA_CODING_UPLIFT` prior 15pp from 2022 → 2026).

**21 lever categories**: routed from raw banker text via priority-tiebreak keyword classifier. Specialized (`MA_CODING_UPLIFT`, `SITE_NEUTRAL_MITIGATION`) beat generic (`CODING_INTENSITY`) on priority. Full list + keywords in [`lever_library.py`](RCM_MC/rcm_mc/diligence/bridge_audit/lever_library.py).

**Per-lever prior**: median / P25 / P75 realization fraction (1.0 = fully realized), failure rate (fraction <50% realized), duration-to-run-rate months, conditional boosts (e.g., `denial_workflow` gets +12pp median when target denial rate >8%; `FTE_REDUCTION` gets −30pp when target is unionized).

**Verdict per lever**: REALISTIC (inside P25-P75) / OVERSTATED (claim >P75) / UNSUPPORTED (claim >P75 AND historical failure rate >40%) / UNDERSTATED (claim <P25, potential sandbag).

**Rollup**: bridge-level gap % between claimed and realistic P50 → counter-bid math = gap × entry multiple. Alternative: structure gap $ as earn-out triggered at higher LTM EBITDA threshold.

### Bear Case Auto-Generator · `/diligence/bear-case` · [README](RCM_MC/rcm_mc/diligence/bear_case/README.md)

**Evidence extractors (8)**: one per source module. Each returns a list of `Evidence` with severity (CRITICAL / HIGH / MEDIUM / LOW), $ impact, citation key, narrative, source deep-link. Extractors are defensive — missing inputs return `[]`, never raise.

**Ranking**: severity × absolute $ impact × source-module priority, with deduplication between regulatory overlay and bridge-audit gap (common double-count).

**Citation keys**: `[R{n}]` regulatory, `[C{n}]` covenant, `[B{n}]` bridge audit, `[M{n}]` Deal MC, `[A{n}]` autopsy, `[E{n}]` exit, `[P{n}]` payer, `[H{n}]` HCRIS. Each resolves to a deep link back to the source module page.

**Verdict thresholds**: EBITDA-at-risk as % of run-rate — <3% = clears IC · 3–10% = watch · 10–25% = material · >25% = IC-killable.

### Payer Mix Stress Lab · `/diligence/payer-stress` · [README](RCM_MC/rcm_mc/diligence/payer_stress/README.md)

**Prior library**: 19 curated payers covering national commercial (UHC, Anthem, Aetna, Cigna, Humana), regional Blues, Medicare FFS + MA, Medicaid FFS + Centene + Molina, TRICARE, Workers Comp, Self-pay. Each: per-renewal rate-move distribution (p25/median/p75), negotiating leverage (0-1), 12-mo renewal probability, churn probability. Calibrated from HFMA/MGMA surveys + 10-K commentary (HCA/THC/UHS disclose payer-specific rate movements).

**Monte Carlo**: 500 paths × horizon years × each payer. Per path: sample rate move from Normal fit to prior, dampen by (1 − renewal probability) when not renewing that year, draw tail churn event with payer-specific probability.

**Concentration amplifier** (empirical PE credit-fund heuristic): Top-1 share >30% → multiply aggregate NPR volatility by `1 + (top_1 − 0.30) × 2`. Top-2 >50% → +0.10. Top-3 >70% → +0.10 more.

**Verdict thresholds**: max concentration severity + P10 EBITDA drag → PASS / CAUTION / WARNING / FAIL.

### Deal Monte Carlo · `/diligence/deal-mc`

**Trials**: 1,500–3,000 (configurable via `n_runs`). 5-year hold default.

**Drivers varied**: organic NPR growth, denial-improvement realization, regulatory headwind $, lease escalator %, physician attrition, cyber-incident probability, V28 coding compression, exit multiple. Each driver has a calibrated Normal or lognormal distribution — full priors in the `DealScenario` dataclass.

**Outputs**: MOIC / IRR / proceeds distributions (P10/P50/P90), attribution (variance decomposition across drivers via Sobol-style first-order indices, stdlib-only), sensitivity tornado, P(MOIC<1×).

### Exit Timing + Buyer Fit · `/diligence/exit-timing`

**IRR curve**: MOIC / IRR / proceeds evaluated for exit at each Y2–Y7. Applies exit-multiple compression/expansion priors by buyer type.

**Buyer-fit scoring**: Strategic / PE Secondary / IPO / Sponsor-Hold — each scored on scale fit × synergy fit × financing environment × regulatory timing. Recommendation picks the highest probability-weighted proceeds.

### Thesis Pipeline · `/diligence/thesis-pipeline` · [README](RCM_MC/rcm_mc/diligence/thesis_pipeline/README.md)

**Step chain**: 19 steps wrapped in `_timed(step_name, fn, step_log)` — catches exceptions per step, logs elapsed ms + OK/ERROR/SKIP status. One broken step never breaks the whole report. Headline synthesizer pulls ~20 top-line numbers into `ThesisPipelineReport` for Deal Profile + IC Packet.

**End-to-end runtime**: ~170ms on fixture data. Optional steps (HCRIS X-Ray when `hcris_ccn` supplied, regulatory calendar when specialty/payer data present) gated on input.

### Management Scorecard · `/diligence/management`

**Role weights**: CEO 35% / CFO 25% / COO 20% / remainder split across named direct reports. Per-exec score = forecast reliability × comp competitiveness × tenure × prior-role reputation (0–100 each, weighted).

### Physician Attrition · `/diligence/physician-attrition`

**Inputs**: per-NPI tenure, age, productivity trend, comp delta vs market, specialty churn rate. Outputs per-NPI flight-risk percentile + NPR-at-risk rollup.

### Provider Economics · `/diligence/physician-eu`

**Per-MD P&L**: gross receipts − variable costs − allocated overhead − comp. Drop-candidate = negative contribution margin AND replacement availability. EBITDA uplift from removing drop-candidates fed into Deal MC.

### Deal Autopsy · `/diligence/deal-autopsy`

**Corpus**: 12 named historical failures (Steward, Cano Health, Envision, Surgery Partners, US Acute Care Solutions, Covis Pharma, etc.) with documented signatures across payer mix × lease intensity × regulatory exposure × physician concentration × sponsor pattern.

**Match**: cosine similarity on signature vector. Top match returned with severity grade + narrative rationale + link to case study.

### RCM Benchmarks · `/diligence/benchmarks`

**KPIs**: 20+ revenue-cycle metrics — days in AR, gross denial rate, clean claim rate, cost-to-collect, NPSR realization, cohort liquidation curves, write-off patterns. Computed from claims corpus + HFMA peer-band compared (P25/P50/P75 peer bands by specialty + size).

### Diligence Checklist · `/diligence/checklist`

**Items**: 40+ diligence tasks across 5 phases — Screening → CCD/benchmarks → Risk workbench → Financial → Deliverables. Auto-check triggered by module fire events in the portfolio audit log.

### IC Packet · `/diligence/ic-packet`

**Output**: print-ready HTML memo bundling Deal metadata + recommendation (PROCEED / PROCEED_WITH_CONDITIONS / DECLINE), waterfall + KPIs, bankruptcy scan, autopsy matches, counterfactual sensitivity, public-comp context, auto-injected regulatory timeline block, auto-injected bear case block, open banker questions, walkaway conditions. `@media print` CSS for clean Cmd-P to PDF.

### Seeking Alpha Market Intelligence · `/market-intel/seeking-alpha`

**Public operators (14)**: HCA, THC, CYH, UHS, EHC, ARDT, PRVA, DVA, FMS, SGRY, UNH, ELV, MPW, WELL. EV/EBITDA + analyst consensus BUY/HOLD/SELL. **PE transactions (12)**: recent sponsor/target/multiple with narrative and outcome. **Sector sentiment**: category heatmap + news feed. Refresh cadence weekly via curated YAML in `market_intel/content/`.

---

## 7. Stack & design choices

- **Python 3.14**, stdlib-heavy — runtime deps = `numpy`, `pandas`, `pyyaml`, `matplotlib`, `openpyxl`. No sklearn, no torch, no scipy.
- **Persistence**: SQLite via stdlib `sqlite3` — 17 tables, `busy_timeout=5000`, idempotent `CREATE TABLE IF NOT EXISTS` migrations.
- **HTTP**: stdlib `http.server.ThreadingHTTPServer`. No Flask, FastAPI, or Docker required.
- **Auth**: stdlib `hashlib.scrypt` + session cookies + CSRF + rate-limited login + unified audit log.
- **Rendering**: server-side HTML string concatenation through one shared `shell()` in [`_ui_kit.py`](RCM_MC/rcm_mc/ui/_ui_kit.py). Scoped CSS (Chartis dark palette, `var(--accent) = #1F4E78`). One small vanilla-JS shim for CSRF-patching forms.
- **Monte Carlo**: Beasley-Springer-Moro inverse normal throughout, seeded where reproducibility matters. No `np.random.default_rng` leakage between modules.
- **Curated priors**: hand-written YAML / Python dataclass tuples with refresh cadence documented in each module README. No ML black boxes.
- **Test coverage**: 2,971 passing tests via stdlib `unittest` driven by pytest. Multi-step workflows hit a real HTTP server on a free port via `urllib.request` — no mocks of our own code.

Design philosophy: **boring stack so it runs on corporate-firewalled laptops offline**. No network calls in the hot path.

---

## 8. File layout

**For a full navigable directory of every major file and module, see [FILE_INDEX.md](FILE_INDEX.md).** The sketch below is the 30-second version.

```
Coding Projects/
├── README.md                              ← you are here
├── FILE_INDEX.md                          ← master map of every file
├── COMPUTER_24HOUR_UPDATE_NUMBER_1.md    ← latest cycle summary
├── WALKTHROUGH.md                         ← detailed case study
│
└── RCM_MC/
    ├── README.md                          ← package-level README
    ├── demo.py                            ← start here: python demo.py
    ├── readME/                            ← organized documentation
    ├── docs/                              ← deep-dive specs
    │
    └── rcm_mc/
        ├── server.py                      ← HTTP router
        ├── cli.py                         ← command-line tool
        │
        ├── diligence/                     ← all the analytic modules
        │   ├── regulatory_calendar/       ← new this cycle
        │   ├── covenant_lab/              ← new this cycle
        │   ├── bridge_audit/              ← new this cycle
        │   ├── bear_case/                 ← new this cycle
        │   ├── payer_stress/              ← new this cycle
        │   ├── hcris_xray/                ← new this cycle
        │   ├── thesis_pipeline/           ← orchestrator
        │   ├── deal_mc/                   ← Monte Carlo
        │   ├── exit_timing/
        │   ├── management_scorecard/
        │   ├── physician_attrition/
        │   ├── physician_eu/
        │   ├── deal_autopsy/
        │   ├── benchmarks/
        │   ├── denial_prediction/
        │   ├── cyber/
        │   └── ...
        │
        ├── market_intel/                  ← public comps + PE transactions
        │   ├── pe_transactions.py         ← new this cycle
        │   ├── public_comps.py
        │   └── content/                   ← YAML data libraries
        │
        ├── ui/                            ← web pages
        │   ├── hcris_xray_page.py         ← new this cycle
        │   ├── regulatory_calendar_page.py ← new this cycle
        │   ├── covenant_lab_page.py       ← new this cycle
        │   ├── bridge_audit_page.py       ← new this cycle
        │   ├── bear_case_page.py          ← new this cycle
        │   ├── payer_stress_page.py       ← new this cycle
        │   ├── seeking_alpha_page.py      ← new this cycle
        │   └── power_ui.py                ← shared UI helpers
        │
        ├── data/                          ← datasets
        │   └── hcris.csv.gz               ← 17,701 Medicare cost reports
        │
        └── tests/                         ← 8,500+ tests
```

---

## 9. Troubleshooting

| Problem | Fix |
|---------|-----|
| `no module named rcm_mc` | `source .venv/bin/activate` |
| Tests fail | Run the new-module subset: `pytest tests/test_hcris_xray.py tests/test_bear_case.py tests/test_payer_stress.py tests/test_bridge_audit.py tests/test_covenant_lab.py tests/test_regulatory_calendar.py -q` → expect `258 passed` |
| Port 8080 in use | `lsof -ti:8080 \| xargs kill -9` or `rcm-mc serve --port 8081` |
| Corrupt local DB | Delete `RCM_MC/seekingchartis.db` + re-run `python demo.py` |
| Where do I start? | [WALKTHROUGH.md](WALKTHROUGH.md) — longer hands-on tour |

---

## Links

- Master file map: [FILE_INDEX.md](FILE_INDEX.md)
- Per-module READMEs under [`RCM_MC/rcm_mc/diligence/`](RCM_MC/rcm_mc/diligence/)
- PE heuristics rulebook: [PE_HEURISTICS.md](RCM_MC/docs/PE_HEURISTICS.md)
- Metric provenance: [METRIC_PROVENANCE.md](RCM_MC/docs/METRIC_PROVENANCE.md)
- Architecture: [ARCHITECTURE.md](RCM_MC/docs/ARCHITECTURE.md)
- Changelog: [CHANGELOG.md](RCM_MC/CHANGELOG.md)
- GitHub: https://github.com/DrewThomas09/RCM
- Test status: 258/258 green on the new modules · 8,477/8,534 (99.3%) on the full suite
