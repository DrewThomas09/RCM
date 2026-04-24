# SeekingChartis / RCM-MC

**A tool that helps private equity firms decide whether to buy hospitals and doctor groups, and then helps them manage those companies after they buy them.**

If you've never heard those words before, don't worry — this README will explain everything from scratch. By the end, you should be able to download it from GitHub, run it on your laptop, and walk through a real example deal.

---

## Table of contents

1. [What is this, in plain English?](#1-what-is-this-in-plain-english)
2. [Who uses it?](#2-who-uses-it)
3. [The big idea behind the tool](#3-the-big-idea-behind-the-tool)
4. [What can it do? All 17 features](#4-what-can-it-do-all-17-features)
5. [How to install and run it (from zero)](#5-how-to-install-and-run-it-from-zero)
6. [Full walkthrough: one imaginary deal, start to finish](#6-full-walkthrough-one-imaginary-deal-start-to-finish)
7. [The tools, explained one by one](#7-the-tools-explained-one-by-one)
8. [How it's built under the hood](#8-how-its-built-under-the-hood)
9. [Project file layout](#9-project-file-layout)
10. [If something breaks](#10-if-something-breaks)

---

## 1. What is this, in plain English?

Imagine you're a big investor who wants to buy a hospital. A hospital costs hundreds of millions of dollars. If you buy the wrong one, you lose all that money and probably your job. If you buy the right one, you make your investors rich.

Before you buy it, you have to answer hard questions like:

- Is this hospital financially healthy?
- Is it better or worse than other hospitals of the same size?
- What happens if the government changes the rules next year?
- Can the hospital's debt payments still be covered if things get worse?
- Does the hospital's marketing material ("the pitch book") tell the truth?

Answering these questions usually takes months, involves many consultants, and costs millions of dollars.

**This tool does most of that work in about 30 minutes, sitting on your laptop, using data that is publicly available.**

It's like a calculator — but instead of doing math on numbers, it does "diligence" (financial checking) on hospitals and doctor groups. "Diligence" is Wall Street slang for "checking carefully before you buy something."

**Analogy**: think of this tool as Carfax for hospitals. Carfax looks up a car's history before you buy it so you don't get scammed. This tool does the same thing — but for multi-hundred-million-dollar healthcare deals.

---

## 2. Who uses it?

- **Private equity (PE) firms** — companies like Blackstone or KKR that buy businesses, improve them for a few years, and sell them at a profit. When the business they're buying is a hospital, they need this tool.
- **Managing Directors, Principals, VPs, Associates** at those firms — the people who spend their days evaluating deals.
- **Investment committee members** — senior partners who approve or reject deal proposals. This tool makes the memos those people read.
- **Lenders and banks** that lend money to PE deals. They care about the same "can the hospital pay its bills?" questions.

If you are not one of those people, you can still use this tool to learn how PE healthcare deals work. It's a good way to see public data that nobody else productizes.

---

## 3. The big idea behind the tool

Every module in this tool answers a question a PE partner would ask out loud in a meeting. Here are the 7 main questions:

| Partner question | Tool module |
|------------------|-------------|
| "How does this hospital compare to similar hospitals?" | **HCRIS Peer X-Ray** |
| "Which government rule changes could ruin our thesis, and when?" | **Regulatory Calendar × Kill-Switch** |
| "If we borrow $350M, can the company still make its debt payments if things go bad?" | **Covenant Stress Lab** |
| "The seller is claiming $12M of synergies — is that real or fake?" | **Bridge Auto-Auditor** |
| "What if one of the big health insurers cuts our rates?" | **Payer Mix Stress Lab** |
| "What's the worst-case version of this investment I should put in the memo?" | **Bear Case Auto-Generator** |
| "What do the public hospital stocks tell me about this market right now?" | **Seeking Alpha Market Intel** |

Partners used to answer these by hiring consultants (McKinsey, Bain) for $500K+ each. Now they get instant answers on their laptop.

---

## 4. What can it do? All 17 features

Think of this as the "features list on the box":

### Screening (before you even make an offer)
1. **HCRIS Peer X-Ray** — look up any US hospital by name or Medicare ID, get instant benchmark against 25–50 similar hospitals across 15 key metrics.
2. **Bankruptcy-Survivor Scan** — red-flag risk score so you don't buy the next Steward Health.
3. **Deal Autopsy** — compares your target to 12 historical failed deals so you can spot "you're about to do Cano Health again" patterns.

### Checking the numbers (diligence)
4. **RCM Benchmarks** — 20+ revenue-cycle KPIs (denial rate, days in AR, cost-to-collect, etc.) compared to peer averages.
5. **Denial Prediction** — machine-learning model predicts how many insurance claims will get denied.
6. **Management Scorecard** — rates executives on forecast accuracy, compensation, tenure, prior-role reputation.
7. **Physician Attrition** — predicts which doctors will leave after the acquisition.
8. **Provider Economics** — per-doctor profit and loss, finds "drop candidates" who are losing money.
9. **Payer Mix Stress Lab** — stress-tests the hospital's mix of insurance companies. If UnitedHealth cuts rates 5%, here's what happens.

### Market context (what's the world doing?)
10. **Regulatory Calendar × Thesis Kill-Switch** — upcoming CMS / OIG / FTC events mapped against your deal thesis. Tells you "your MA margin thesis dies April 12, 2026 when V28 final rule publishes."
11. **Seeking Alpha Market Intelligence** — 14 public hospital stocks, 12 recent PE deals, sector sentiment, news feed.
12. **Market Intel / Peer Snapshot** — private deal multiples by specialty and deal size.

### Financial modeling (can we make money?)
13. **Deal Monte Carlo** — runs 3,000 simulated futures for the deal, shows the range of possible MOIC (money multiple) and IRR (annual return) outcomes.
14. **Covenant Stress Lab** — models debt payments quarter by quarter, shows probability of breaching loan covenants.
15. **Bridge Auto-Auditor** — paste the seller's synergy claims, get a risk-adjusted rebuild with counter-offer math.
16. **Exit Timing + Buyer Fit** — when should you sell the company, and to whom?

### Writing the memo (IC prep)
17. **Bear Case Auto-Generator + IC Packet** — collects evidence from every module, writes the "what could break this thesis" memo section, and bundles everything into a print-ready investment committee packet.

---

## 5. How to install and run it (from zero)

Your laptop needs:
- **macOS or Linux** (Windows works with WSL)
- **Python 3.14** (check by running `python3 --version` in a Terminal)
- **git** (check with `git --version`)
- About **1 GB** of free disk space

### Step 1 — Open a Terminal

- **Mac**: press `Cmd + Space`, type "Terminal", press Enter
- **Linux**: usually `Ctrl + Alt + T`

### Step 2 — Download the code from GitHub

```bash
# Pick a folder where you want the code to live
cd ~/Desktop

# Clone the repo (downloads the whole project)
git clone https://github.com/DrewThomas09/RCM.git

# Go into it
cd RCM
```

If you don't have git, you can go to https://github.com/DrewThomas09/RCM, click the green **"Code"** button, click **"Download ZIP"**, then unzip the file and `cd` into the folder.

### Step 3 — Create a Python "virtual environment"

A virtual environment is a clean Python sandbox. It keeps this project's code separate from the rest of your computer.

```bash
python3.14 -m venv .venv
source .venv/bin/activate
```

After this runs, your Terminal prompt should start with `(.venv)`. That means you're inside the sandbox.

### Step 4 — Install the tool

```bash
cd RCM_MC
pip install -e ".[all]"
```

This downloads everything the tool needs (about 30 seconds with decent internet).

### Step 5 — Run it

```bash
python demo.py
```

This:
1. Creates a demo database with fake data
2. Starts a web server at `http://localhost:8080`
3. Opens your browser automatically

You should now see the **SeekingChartis** home page. Click around!

### Later — shut it down

Press `Ctrl + C` in the Terminal where it's running.

### Later — start it up again

```bash
cd ~/Desktop/RCM/RCM_MC
source ../.venv/bin/activate   # re-activate the sandbox
python demo.py
```

---

## 6. Full walkthrough: one imaginary deal, start to finish

Let's pretend you're a PE VP. It's Monday morning. Your managing director says:

> "There's a 300-bed community hospital in Alabama. Asking price $600M. Take the week to figure out if we should bid on it."

Here's how you'd use the tool:

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

The box-plot visualizations show you exactly where this hospital sits in the peer distribution. The 3-year sparkline per metric shows whether things are improving or getting worse.

**What this tells you**: This is a distressed hospital. Still busy but losing money. Could be a turnaround play, but risky.

### 9:10 AM — Check the public market

Click **Seeking Alpha** from the context bar that follows you around. You see:

- HCA public stock trading at 8.9× EV/EBITDA — that's the peer multiple for big hospital chains
- The "Public Market Context" block on HCRIS X-Ray showed Southeast Health's −4.4% margin vs HCA's +16.9% — a 21.3pp gap
- Recent PE deals in the sector: Audax bought a behavioral platform at 10.8×

**What this tells you**: Public hospitals trade around 9×. Private deals go a bit higher. A distressed hospital like Southeast should trade at a discount — maybe 6× or less.

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

**What this tells you**: You can't borrow $250M against $21M EBITDA. Either put in more equity or walk.

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

### Total time elapsed: 90 minutes

Without this tool, this analysis would have taken 2–3 weeks and cost $200K+ in consulting fees. **You just did the same work before lunch on a Monday.**

---

## 7. The tools, explained one by one

This is the long-form walkthrough of every module. Each one has its own web page (URL) and tells a specific part of the story.

### HCRIS Peer X-Ray · `/diligence/hcris-xray`

**What it does**: Every Medicare-accepting hospital in the US files a "Medicare cost report" every year with the government. That report has 2,500+ data fields — bed count, payer mix, patient days, gross revenue, net revenue, operating expenses, everything. We loaded 17,701 of these reports. You type any hospital's name or Medicare ID (CCN), and the tool instantly benchmarks that hospital against 25–50 similar hospitals (same size, state, payer mix, year) across 15 derived metrics.

**Why it's powerful**: This is public data nobody else productizes. A CapIQ subscription costs $80K/year and doesn't give you this. You're looking at the same data the hospital filed with the government — ground truth, not banker spin.

**What you see**: target card + metric benchmark grid + per-metric sparkline (3-year trend) + per-metric box-plot (where target sits in peer distribution) + peer roster table + public-comp context block (target vs HCA/Tenet/UHS).

### Regulatory Calendar × Thesis Kill-Switch · `/diligence/regulatory-calendar`

**What it does**: We curated 11 upcoming US healthcare regulatory events (CMS V28, OPPS site-neutral, TEAM bundled payment, NSA IDR, ESRD PPS, FTC HSR expansion, OIG management-fee, DOJ False Claims, etc.). Each event has a publish date, effective date, and a mapping of which thesis drivers it kills. You input your target's profile (specialty, payer mix, geography), and the tool tells you which of your claimed value-creation drivers die, and on which specific date.

**Why it's powerful**: Traditional tools talk about "regulatory risk" in fuzzy terms. This tool tells you "your MA margin lift thesis driver dies on 2027-01-01 when V28 final rule takes effect — residual value 0.0 pp out of claimed 5.5 pp." That specificity is unique.

**What you see**: verdict card (PASS/CAUTION/WARNING/FAIL), risk score, Gantt timeline of events, per-driver timeline, EBITDA overlay table.

### Covenant & Capital Stack Stress Lab · `/diligence/covenant-stress`

**What it does**: Takes the Deal MC EBITDA projections (the distribution of how much money the company might make over 5 years), overlays your debt structure (revolvers, term loans, mezzanine), and tells you per-quarter how likely you are to breach your loan covenants. A covenant is a rule in the loan agreement like "debt-to-EBITDA must stay below 6×" — break one and the bank can call the loan.

**Why it's powerful**: Partners ask "when does this deal hit a cliff?" This tool answers with a specific quarter and a dollar amount for the equity cure needed.

**What you see**: breach probability curves per covenant × quarter, debt service cliff chart, equity cure sizing table, capital stack detail.

### EBITDA Bridge Auto-Auditor · `/diligence/bridge-audit`

**What it does**: When sellers pitch their business, they give buyers a "synergy bridge" — a list of ways the buyer will improve EBITDA after closing. For example: "we'll consolidate vendors (saves $2.8M), overhaul denials (adds $4.2M), uplift coding (adds $3.1M)." Total: $10M+ of claimed improvements. Banker says the deal deserves a higher multiple because of these synergies.

The problem: **most of those claimed synergies never show up**. Vendor consolidation only realizes its claim 38% of the time. This tool paste-audits each lever against a library of ~3,000 historical RCM initiative outcomes and rebuilds the bridge with realistic numbers.

**Why it's powerful**: Partners pay consulting firms $500K+ to do this audit manually. This tool does it in 4 seconds.

**What you see**: verdict card (MATERIAL/GAP/OK), claimed-vs-realistic comparison chart per lever, counter-bid recommendation with earn-out alternative, full lever library reference.

### Bear Case Auto-Generator · `/diligence/bear-case`

**What it does**: Every investment committee memo needs a "bear case" section — what could break this thesis. Partners normally write this by hand (3–5 hours per memo × 3–5 memo drafts per deal = 20+ hours). This tool pulls evidence from 8 sources (Regulatory Calendar, Covenant Stress, Bridge Audit, Deal MC, Deal Autopsy, Exit Timing, Payer Stress, HCRIS X-Ray), ranks by severity and dollar impact, assigns citation keys `[R1/C1/B1/M1/A1/E1/P1/H1]`, and produces a print-ready memo block.

**Why it's powerful**: Every piece of evidence is sourced and clickable. The memo partners paste into IC isn't opinion — it's cited.

**What you see**: verdict card (EBITDA at risk as % of run-rate), theme-grouped evidence cards with citation keys + deep links back to source modules, copy-paste IC memo HTML.

### Payer Mix Stress Lab · `/diligence/payer-stress`

**What it does**: Hospital revenue depends on which insurance companies are paying. The big 5 national payers (UHC, Anthem, Aetna, Cigna, Humana) plus Blues regional plans + Medicare + Medicaid make up most of the pie. Each payer reprices their contracts every 1–3 years. Our tool curates 19 major payers with historical rate-move distributions, negotiating leverage scores, renewal cadences, and churn probabilities — then runs a Monte Carlo of rate shocks across your target's actual mix to compute NPR and EBITDA at risk.

**Why it's powerful**: Payer mix is the #1 driver of hospital economics but nobody quantifies dynamic rate risk this way. You see exactly how fragile your deal is to a 5% UHC cut.

**What you see**: mix donut chart with concentration ring, verdict card, per-payer cards with median/P10/P90 rate moves, aggregate NPR impact cone.

### Seeking Alpha Market Intelligence · `/market-intel/seeking-alpha`

**What it does**: Curated snapshot of public healthcare operators (HCA, THC, CYH, UHS, EHC, ARDT, PRVA, DVA, FMS, SGRY, UNH, ELV, MPW, WELL) with EV/EBITDA multiples + analyst consensus, plus 12 recent PE transactions with sponsor/target/multiple/narrative, plus a sector sentiment heatmap + news feed.

**Why it's powerful**: Gives you market context — "what's the tape saying right now?" — alongside your private-deal analysis.

**What you see**: ticker cards with color-coded EV/EBITDA + analyst BUY/HOLD/SELL badges, PE deal feed with sponsor leaderboard, news headlines, category band table.

### Deal Monte Carlo · `/diligence/deal-mc`

**What it does**: Runs 3,000 simulated 5-year futures for the deal. Each simulation varies organic growth, denial improvement realization, regulatory headwind, lease escalator, physician attrition, cyber incidents, V28 compression, and exit multiple. Outputs MOIC / IRR / proceeds distributions + attribution (which driver mattered most) + sensitivity tornado.

**Why it's powerful**: Classic Excel MOIC is one point estimate. This gives you the full distribution — "there's a 25% chance we lose money, median 2.1× MOIC, P90 3.7×."

### Exit Timing + Buyer Fit · `/diligence/exit-timing`

**What it does**: IRR / MOIC / proceeds curve across years 2–7 + buyer-fit scoring (Strategic / PE Secondary / IPO / Sponsor-Hold) + probability-weighted proceeds. Tells you when to sell and to whom.

### Thesis Pipeline · `/diligence/thesis-pipeline`

**What it does**: One-click orchestrator that runs all 14 analytic modules in sequence for a given deal. Produces a single report with every headline number + step log + deep-link tiles into each individual module.

### Management Scorecard · `/diligence/management`

**What it does**: Scores each executive (CEO/CFO/COO) on forecast reliability × comp × tenure × prior-role reputation. Produces a team-level roll-up with role weights (CEO 35% / CFO 25% / COO 20%).

### Physician Attrition · `/diligence/physician-attrition`

**What it does**: Per-NPI (National Provider Identifier) flight-risk prediction. Tells you which doctors will leave after the acquisition, estimates NPR at risk.

### Provider Economics · `/diligence/physician-eu`

**What it does**: Per-physician P&L. Finds "drop candidates" — doctors whose economic contribution is negative so removing them improves EBITDA.

### Deal Autopsy · `/diligence/deal-autopsy`

**What it does**: Matches your target's profile (payer mix × lease intensity × regulatory exposure × physician concentration) against a library of 12 historical PE healthcare deals (Steward, Cano, Envision, Surgery Partners, etc.) with known outcomes. Surfaces "you're about to do Deal X again" signatures.

### RCM Benchmarks · `/diligence/benchmarks`

**What it does**: 20+ revenue-cycle KPIs (days in AR, denial rate, clean claim rate, cost-to-collect, NPR realization, cohort liquidation, etc.) computed from claims data + HFMA peer-band compared.

### Diligence Checklist · `/diligence/checklist`

**What it does**: Tracks which diligence items have been completed. 40+ items across 5 phases (screening → CCD + benchmarks → risk workbench → financial → deliverables). Auto-checks based on which modules fired.

### IC Packet · `/diligence/ic-packet`

**What it does**: One-click investment committee deliverable. Bundles all module output into a print-ready HTML memo with bankruptcy scan, benchmarks, public comps, counterfactual, autopsy matches, regulatory timeline, bear case, and walkaway conditions.

---

## 8. How it's built under the hood

The technical vocabulary (for readers who care):

- **Language**: Python 3.14
- **Web server**: Python's built-in `http.server.ThreadingHTTPServer` — no Flask, no FastAPI, no Docker
- **Database**: SQLite (built into Python) for portfolio + alerts
- **Data files**: YAML for curated libraries (regulatory events, payer priors, PE transactions, public comps)
- **Front end**: Server-rendered HTML with inline CSS (dark terminal "Chartis" palette). One small JavaScript file for CSRF tokens + sortable tables.
- **Dependencies**: `numpy`, `pandas`, `pyyaml`, `matplotlib`, `openpyxl`. No `sklearn`, no `tensorflow`, no `torch`.
- **Monte Carlo**: all stdlib-only (Beasley-Springer-Moro inverse normal for lognormal path reconstruction) — no `scipy` needed.

The design philosophy is: **keep it boring so it runs anywhere**. A PE analyst can clone the repo on their work laptop behind corporate firewall, run the server locally, and never call out to the internet.

---

## 9. Project file layout

```
Coding Projects/
├── README.md                              ← you are here
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

## 10. If something breaks

**"python demo.py" fails with "no module named rcm_mc"**

You forgot to activate the virtual environment. Run:
```bash
source .venv/bin/activate
```

**Tests fail**

Run the subset that matters:
```bash
python -m pytest tests/test_hcris_xray.py tests/test_bear_case.py tests/test_payer_stress.py tests/test_bridge_audit.py tests/test_covenant_lab.py tests/test_regulatory_calendar.py -q
```
Should show `258 passed`. If not, open an issue with the error output.

**Port 8080 is already in use**

Another program is using it. Either:
```bash
# Option 1: kill what's using port 8080
lsof -ti:8080 | xargs kill -9

# Option 2: run on a different port
rcm-mc serve --port 8081
```

**I broke my local database**

Delete `seekingchartis.db` in the `RCM_MC/` folder and re-run `python demo.py`.

**I'm lost, where do I start?**

Read [WALKTHROUGH.md](WALKTHROUGH.md) — it's a longer hands-on tour, or jump into [RCM_MC/readME/00_Walkthrough_Tutorial.md](RCM_MC/readME/00_Walkthrough_Tutorial.md).

---

## Staying current

- Latest cycle summary: [COMPUTER_24HOUR_UPDATE_NUMBER_1.md](COMPUTER_24HOUR_UPDATE_NUMBER_1.md)
- GitHub: https://github.com/DrewThomas09/RCM
- Test status: 258/258 green on the new modules · 8,477/8,534 (99.3%) on the full suite

---

*If you got this far, you know more about PE healthcare diligence than 99% of the general public. Have fun.*
