# SeekingChartis / RCM-MC

**A full-stack healthcare RCM diligence workbench. Runs locally. Calibrated to public-filing data. Turns a banker's book into an IC-ready memo in roughly thirty minutes.**

This replaces the slice of healthcare diligence that firms typically outsource to $200K–500K third-party advisors — peer benchmarking, regulatory exposure, covenant stress, synergy-bridge audit, bear case. The inputs are public: HCRIS, Care Compare, 10-K, IRS 990. The models are transparent; every output traces back to an input and a function you can read. Nothing leaves your laptop. There are no API calls, no SaaS subscriptions, no black-box scoring.

---

## I need to…

| Goal | Go to |
|------|-------|
| **Install it** | [§4 — Install](#4-install) |
| **See a full MondayAM→ICready walkthrough** | [§5 — Deal walkthrough](#5-deal-walkthrough-mondayam--ic-ready-by-1030am) or the longer [WALKTHROUGH.md](WALKTHROUGH.md) |
| **Find a file or module** | [FILE_INDEX.md](FILE_INDEX.md) (navigation map) or [FILE_MAP.md](FILE_MAP.md) (1,659-file catalogue) |
| **See the architecture visually** | [ARCHITECTURE_MAP.md](ARCHITECTURE_MAP.md) — 8 Mermaid diagrams (GitHub-rendered) |
| **Read a module's methodology** | [§6 — Module methodology](#6-module-methodology) — each links to its per-module README |
| **Audit a number's provenance** | [METRIC_PROVENANCE.md](RCM_MC/docs/METRIC_PROVENANCE.md), [BENCHMARK_SOURCES.md](RCM_MC/docs/BENCHMARK_SOURCES.md) |
| **Read the PE heuristics rulebook** | [PE_HEURISTICS.md](RCM_MC/docs/PE_HEURISTICS.md) — 275+ named partner rules |
| **See what's changed** | [CHANGELOG.md](RCM_MC/CHANGELOG.md), [COMPUTER_24HOUR_UPDATE_NUMBER_1.md](COMPUTER_24HOUR_UPDATE_NUMBER_1.md) |
| **See the 6-month roadmap** | [PRODUCT_ROADMAP_6MO.md](RCM_MC/docs/PRODUCT_ROADMAP_6MO.md) — quarter-by-quarter ship plan |
| **See the beta program** | [BETA_PROGRAM_PLAN.md](RCM_MC/docs/BETA_PROGRAM_PLAN.md) — 3-cohort validation structure |
| **Read the strategy index** | [docs/README.md](RCM_MC/docs/README.md) — 15 planning docs |
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

You give it a target — CCN or hospital name — plus the LOI economics (NPR, EBITDA, EV, debt stack, entry multiple, payer mix, landlord). It runs a 19-step pipeline in roughly 170 milliseconds and returns:

- A **peer benchmark** across 15 HCRIS metrics, compared to 25–50 hospitals matched on size, state, and region — with three-year trend slopes and peer P25 / median / P75 bands
- A **regulatory exposure map** that identifies, by date, which of your named thesis drivers are killed by upcoming CMS / OIG / FTC rules — and the annual EBITDA overlay that flows downstream
- A **covenant stress simulation**: 500 lognormal EBITDA paths × 20 quarters × 4 covenants, with equity-cure sizing per breach
- A **bridge audit** of seller synergies against a library of roughly 3,000 historical initiative outcomes, with counter-bid math and an earn-out alternative
- A **payer concentration Monte Carlo** with historical rate-shock priors and an HHI amplifier
- A **Deal MC** (1,500+ trials, 8 varied drivers) producing MOIC / IRR / proceeds cones with driver attribution
- An **autopsy match** against 12 named historical failures — Steward, Cano, Envision, Surgery Partners, and others
- An **exit-timing IRR curve** crossed with buyer-type fit across Y2 through Y7
- An **auto-generated bear case** with citation keys, ranked by severity and dollar impact, rendered as print-ready IC-memo HTML

Every number is reproducible. Same inputs, same outputs. Monte Carlo is seeded where it matters. No network calls in the hot path.

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

Every module follows the same pattern. That uniformity is what makes the outputs auditable.

**Curated priors.** Each analytic engine sits on top of a hand-calibrated prior library — payer rate-move distributions, lever-realization priors, regulatory events mapped to thesis drivers, autopsy signatures. Every prior cites its source (HFMA survey, 10-K commentary, Federal Register docket, retrospective failure analysis) and documents its refresh cadence. You can read every prior in the module README and edit it in one file.

**Target-profile normalization.** The LOI inputs plus the HCRIS lookup feed a single `target_profile` dictionary — specialty, MA mix, payer concentration, landlord, CCN. Every module reads from this dictionary. There is no hidden cross-module state.

**Monte Carlo where the distribution matters.** Covenant stress runs 500 paths across 20 quarters. Deal MC runs 1,500+ trials across 8 drivers. Payer stress runs 500 paths across the hold period. Every simulation uses a stdlib-only Beasley-Springer-Moro inverse normal for lognormal sampling — no scipy, no outside dependency beyond numpy and pandas.

**Target-conditional adjustments.** Priors are not static. A denial-workflow lever gets +12 points of median realization when the target's denial rate is already above 8% — the low-hanging-fruit adjustment. An FTE-reduction prior loses 30 points when the target is unionized. These adjustments live in the `LeverPrior` dataclass, visible and auditable, not buried in scoring code.

**Named verdict thresholds.** Every module terminates in a PASS / CAUTION / WARNING / FAIL verdict against documented numeric cutoffs — covenant breach probability above 50% is a FAIL; Top-1 payer share above 30% triggers the concentration amplifier. The thresholds are published in each module's README and editable in one place.

**Dollar-impact rollup.** Every analytic output terminates in an EBITDA-at-risk number, and that number flows downstream. The regulatory overlay flows into the Covenant Lab path reconstruction, which flows into Deal MC's `reg_headwind_usd` driver, which flows into the Bear Case `[R1]` evidence, which flows into the IC memo headline. The arithmetic is explicit at every step.

**Trust hooks.** Every dataclass output carries a `source_module` and `citation_key`. Every Monte Carlo function accepts a `seed` argument for deterministic reproduction. Every prior's calibration source is documented in its module README. Any metric can be traced back through the provenance graph to raw inputs via `rcm-mc analysis <deal_id> --explain <metric>`.

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

Each module's per-file README carries the full math. The summaries below describe what each engine does, the data behind it, and where the key assumptions live.

### HCRIS Peer X-Ray · `/diligence/hcris-xray` · [README](RCM_MC/rcm_mc/diligence/hcris_xray/README.md)

The peer-benchmark engine. It loads 17,701 Medicare cost reports from the CMS HCRIS public extract (FY 2020–2022) and benchmarks the target against bed-size-, state-, and region-matched peers across 15 derived metrics.

Peer selection uses a waterfall: same cohort (MICRO / SMALL_COMMUNITY / COMMUNITY / REGIONAL / ACADEMIC, binned on beds) plus same state with beds within ±30%, falling back to same region, then national, until at least 25 peers are found. The metric surface covers Size, Payer Mix, Revenue Cycle, Cost Structure, and Margin; each metric carries a direction flag (higher-is-better, lower-is-better, neutral) that drives the coloring. Trend is a three-year linear slope on the same CCN's history, classified as improving, flat, or deteriorating at a ±1% annualized cut.

Cold load parses the gzipped CSV in about 250 milliseconds. Subsequent lookups run in roughly 7 milliseconds on the cached dataset.

### Regulatory Calendar × Kill-Switch · `/diligence/regulatory-calendar` · [README](RCM_MC/rcm_mc/diligence/regulatory_calendar/README.md)

The thesis kill-switch. It carries 11 hand-curated US healthcare regulatory events — CMS V28, OPPS site-neutral, the TEAM mandatory bundled payment, NSA IDR recalculation, ESRD PPS CY2027, the FTC HSR expansion, the USAP consent order, and others — each with its publish and effective dates, affected specialties, named thesis drivers it puts at risk, impact distribution, and Federal Register docket URL.

A target-profile impact mapper takes the target's specialty, MA mix, payer share, HOPD revenue share, and landlord type, then returns a per-driver verdict of UNAFFECTED, DAMAGED (above a 10% impairment threshold), or KILLED (above 50%, or zero residual value). The overall verdict is PASS if no driver is impaired above 10%, CAUTION for one damaged driver, WARNING for a kill or two damaged, and FAIL for two or more kills. The per-year EBITDA headwind feeds downstream into Covenant Lab's path reconstruction and Deal MC's `reg_headwind_usd` driver.

### Covenant & Capital Stack Stress Lab · `/diligence/covenant-stress` · [README](RCM_MC/rcm_mc/diligence/covenant_lab/README.md)

The covenant breach simulator. It takes Deal MC's yearly P25 / P50 / P75 EBITDA bands and reconstructs 500 lognormal paths using a stdlib-only Beasley-Springer-Moro inverse normal. No scipy.

The capital stack supports six tranche kinds — revolver, TLA, TLB, unitranche, mezzanine, seller note — each with floating or fixed rate, custom amortization, commitment fees on undrawn revolver balance, and lien priority. Quarterly debt service is applied against each path and tested against four covenants: Net Leverage, DSCR, Interest Coverage, and Fixed Charge Coverage. Step-down schedules are supported (e.g., leverage opens at 7.5× and steps to 6.0× by Y4). For every breach, the tool solves for the minimum equity injection that restores the ratio above threshold with cushion.

Verdict thresholds match PE-bank underwriting norms: maximum breach probability under 10% is a PASS, 10–25% is a WATCH, 25–50% is a WARNING, and above 50% is a FAIL.

### EBITDA Bridge Auto-Auditor · `/diligence/bridge-audit` · [README](RCM_MC/rcm_mc/diligence/bridge_audit/README.md)

The synergy audit engine. It routes each line of a banker's bridge into one of 21 canonical lever categories using a priority-tiebreak keyword classifier — specialized categories like `MA_CODING_UPLIFT` and `SITE_NEUTRAL_MITIGATION` beat the generic `CODING_INTENSITY` when keywords overlap. Each category sits on top of a realization prior calibrated from approximately 3,000 historical RCM initiative outcomes (HFMA / MGMA / AHA surveys, 10-K commentary, retrospective analysis of PE healthcare failures).

Each prior carries median / P25 / P75 realization as a fraction of the claimed lift, a historical failure rate (share of deals realizing less than half the claim), a duration-to-run-rate in months, and target-conditional adjustments. The denial-workflow prior gets +12 points of median realization when the target's denial rate is already above 8%. The FTE-reduction prior loses 30 points when the target is unionized. The MA coding prior dropped 15 points between 2022 and 2026 as V28 took effect.

Each lever receives a verdict of REALISTIC (inside the P25–P75 band), OVERSTATED (claim above P75), UNSUPPORTED (claim above P75 and historical failure rate above 40%), or UNDERSTATED (claim below P25 — potential seller sandbag). The bridge-level rollup computes the gap between claimed and realistic P50, then translates that into counter-bid math (gap × entry multiple) with an earn-out alternative triggered at a higher LTM EBITDA threshold.

### Bear Case Auto-Generator · `/diligence/bear-case` · [README](RCM_MC/rcm_mc/diligence/bear_case/README.md)

The IC-memo bear-case synthesizer. It runs eight defensive extractors — one per source module — that each pull relevant findings and normalize them into a common `Evidence` record with severity (CRITICAL / HIGH / MEDIUM / LOW), dollar impact, citation key, narrative, and a deep link back to the source.

Evidence is ranked by severity × absolute dollar impact × source-module priority, with deduplication between the regulatory overlay and the bridge-audit gap (a common double-count). Citation keys follow a scheme that lets a reader trace any claim back to its origin: `[R]` for regulatory, `[C]` for covenant, `[B]` for bridge audit, `[M]` for Deal MC, `[A]` for autopsy, `[E]` for exit timing, `[P]` for payer, `[H]` for HCRIS. The verdict is framed in terms of EBITDA at risk as a share of run-rate: under 3% clears IC, 3–10% is a watch, 10–25% is material, and above 25% is IC-killable territory.

### Payer Mix Stress Lab · `/diligence/payer-stress` · [README](RCM_MC/rcm_mc/diligence/payer_stress/README.md)

The payer concentration Monte Carlo. The prior library covers 19 US healthcare payers — the national commercials (UnitedHealthcare, Anthem, Aetna, Cigna, Humana), regional Blues plans, Medicare FFS and Medicare Advantage, Medicaid FFS plus managed Medicaid (Centene, Molina), TRICARE, Workers Comp, and Self-pay. Each payer ships with a per-renewal rate-move distribution (P25 / median / P75), a negotiating leverage score (0–1), a 12-month renewal probability, and a churn probability. The priors were calibrated from HFMA / MGMA rate-move surveys and 10-K disclosures by HCA, Tenet, and UHS.

The simulation runs 500 paths per year per payer. Each path samples a rate move from a Normal fit to the prior, dampens the move by `(1 − renewal probability)` when the contract isn't up for renewal that year, and draws a tail churn event with payer-specific probability.

A concentration amplifier — an empirical PE credit-fund heuristic — scales aggregate NPR volatility when the mix is top-heavy. If the top payer's share exceeds 30%, aggregate volatility is multiplied by `1 + (top_1 − 0.30) × 2`. If the top two exceed 50% combined, another 10 points of amplification. If the top three exceed 70%, another 10.

### Deal Monte Carlo · `/diligence/deal-mc`

The headline value simulation. It runs 1,500 to 3,000 trials (configurable) over a five-year default hold. Each trial varies eight drivers with calibrated distributions: organic NPR growth, denial-improvement realization, regulatory headwind dollars, lease escalator percentage, physician attrition, cyber-incident probability, V28 coding compression, and exit multiple. The full priors live in the `DealScenario` dataclass.

The outputs are MOIC, IRR, and proceeds distributions at P10 / P50 / P90, along with a driver-attribution decomposition (Sobol-style first-order indices, stdlib-only) and a sensitivity tornado. The `P(MOIC < 1×)` statistic — the probability of losing money — is surfaced as a first-class metric.

### Exit Timing + Buyer Fit · `/diligence/exit-timing`

The exit-window engine. It evaluates MOIC, IRR, and proceeds for an exit in each of years 2 through 7, applying exit-multiple expansion or compression priors by buyer type. It scores four buyer archetypes — Strategic, PE Secondary, IPO, Sponsor-Hold — on scale fit, synergy fit, financing environment, and regulatory timing. The recommendation picks the year-buyer pair with the highest probability-weighted proceeds.

### Thesis Pipeline · `/diligence/thesis-pipeline` · [README](RCM_MC/rcm_mc/diligence/thesis_pipeline/README.md)

The orchestrator. It runs the 19-step diligence chain, each step wrapped in `_timed(step_name, fn, step_log)` to catch exceptions, log elapsed milliseconds, and tag each step OK / ERROR / SKIP. One broken step never breaks the whole report. A headline synthesizer pulls roughly 20 top-line numbers into a single `ThesisPipelineReport` for the Deal Profile and IC Packet. End-to-end runtime on fixture data is about 170 milliseconds. Optional steps are gated on input — HCRIS X-Ray runs when a CCN is supplied, regulatory calendar runs when specialty and payer data are present.

### Management Scorecard · `/diligence/management`

The management-quality grader. Role weights are CEO at 35%, CFO at 25%, COO at 20%, with the remainder split across named direct reports. Each executive is scored 0–100 on forecast reliability, comp competitiveness, tenure, and prior-role reputation. The team-level rollup is a weighted average across roles.

### Physician Attrition · `/diligence/physician-attrition`

Per-NPI flight risk. Inputs are physician tenure, age, productivity trend, comp delta versus market, and specialty churn rate. The output is a per-physician flight-risk percentile plus an NPR-at-risk rollup.

### Provider Economics · `/diligence/physician-eu`

Per-physician P&L. Gross receipts minus variable costs minus allocated overhead minus compensation. A "drop candidate" is a physician with negative contribution margin and replacement availability. The EBITDA uplift from pruning drop candidates is fed into Deal MC.

### Deal Autopsy · `/diligence/deal-autopsy`

The pattern-match engine. It holds 12 named historical PE healthcare failures — Steward, Cano Health, Envision, Surgery Partners, US Acute Care Solutions, Covis Pharma, and others — each with a documented signature across payer mix, lease intensity, regulatory exposure, physician concentration, and sponsor pattern. Cosine similarity on the target's signature vector surfaces the closest match, along with a severity grade, narrative rationale, and link to the case study.

### RCM Benchmarks · `/diligence/benchmarks`

Twenty-plus revenue-cycle KPIs computed from the claims corpus — days in AR, gross denial rate, clean claim rate, cost-to-collect, NPSR realization, cohort liquidation curves, and write-off patterns — each compared to HFMA peer bands (P25 / P50 / P75) bucketed by specialty and size.

### Diligence Checklist · `/diligence/checklist`

A workflow tracker for 40+ diligence tasks across five phases: Screening, CCD and benchmarks, Risk workbench, Financial, and Deliverables. Auto-checks are triggered by module-fire events in the portfolio audit log.

### IC Packet · `/diligence/ic-packet`

The one-click investment-committee deliverable. A print-ready HTML memo bundles deal metadata and recommendation (PROCEED / PROCEED_WITH_CONDITIONS / DECLINE), waterfall and KPIs, bankruptcy scan, autopsy matches, counterfactual sensitivity, public-comp context, auto-injected regulatory timeline block, auto-injected bear-case block, open questions for the banker, and walkaway conditions. `@media print` CSS makes for a clean Cmd-P to PDF.

### Seeking Alpha Market Intelligence · `/market-intel/seeking-alpha`

Public-tape context. Fourteen public healthcare operators (HCA, THC, CYH, UHS, EHC, ARDT, PRVA, DVA, FMS, SGRY, UNH, ELV, MPW, WELL) with EV / EBITDA multiples and analyst BUY / HOLD / SELL consensus, alongside 12 recent PE transactions with sponsor, target, multiple, and outcome narrative. Sector sentiment is rendered as a category heatmap and news feed. The data refreshes weekly via curated YAML in `market_intel/content/`.

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
- ML predictors reference: [rcm_mc/ml/README.md](RCM_MC/rcm_mc/ml/README.md)
- Data sources reference: [rcm_mc/data/README.md](RCM_MC/rcm_mc/data/README.md)
- UI components reference: [rcm_mc/ui/README.md](RCM_MC/rcm_mc/ui/README.md)
- Strategy index (15 docs): [docs/README.md](RCM_MC/docs/README.md)
- 6-month roadmap: [PRODUCT_ROADMAP_6MO.md](RCM_MC/docs/PRODUCT_ROADMAP_6MO.md)
- Beta program: [BETA_PROGRAM_PLAN.md](RCM_MC/docs/BETA_PROGRAM_PLAN.md)
- PE heuristics rulebook: [PE_HEURISTICS.md](RCM_MC/docs/PE_HEURISTICS.md)
- Metric provenance: [METRIC_PROVENANCE.md](RCM_MC/docs/METRIC_PROVENANCE.md)
- Architecture: [ARCHITECTURE.md](RCM_MC/docs/ARCHITECTURE.md)
- Changelog: [CHANGELOG.md](RCM_MC/CHANGELOG.md)
- GitHub: https://github.com/DrewThomas09/RCM
- Most recent cycle (Apr 2026): 80+ commits — 4 public-data sources, 13 ML predictors, 14+ UI components, 15 strategy docs
