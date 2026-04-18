# Phase 5 Nav Audit — before-state

**Scratch file — delete at the end of Phase 5.**

## Current nav structure

Defined in `rcm_mc/ui/_chartis_kit.py` as `_CORPUS_NAV` (list of
dicts). 189 entries total: 184 nav items + 5 separator headers.

### Group 1 — `SEEKING CHARTIS` (4 items)
- Home → `/home`
- PE Intelligence → `/pe-intelligence`
- Methodology → `/methodology`
- API Docs → `/api/docs`

### Group 2 — `REFERENCE DATA` (3 items)
- Sponsor Track Record → `/sponsor-track-record`
- Payer Intelligence → `/payer-intelligence`
- RCM Benchmarks → `/rcm-benchmarks`

### Group 3 — `CORPUS ANALYTICS` (3 items)
- Corpus Backtest → `/corpus-backtest`
- Deal Screening → `/deal-screening`
- Portfolio Analytics → `/portfolio-analytics`

### Group 4 — `CORPUS INTEL` (171 items)
The dumping ground. Every Phase-2 migration of a data_public page landed
here. Alphabetical-ish ordering by creation order, not by topic.
Examples: Deals Library, Comparables, Risk Matrix, Underwriting, Market
Rates, Backtest, Portfolio Optimizer, Deal Quality, Sector Intel,
Vintage Perf, Payer Intel, Leverage Intel, Size Intel, Corpus Dashboard,
Deal Search, IC Memo Gen, Return Attrib, Deal Flow Map, Concentration,
Hold Analysis, IRR Dispersion, Payer Trends, Entry Multiple, Coverage
Report, Find Comps, Sector Momentum, GP Benchmarking, Red Flag Detect,
Hold Optimizer, Payer Stress, Multiple Decomp, Capital Eff, Risk
Scores, Sector Corr, Acq Timing, Portfolio Sim, QoE Analyzer, Covenant
Mon, Provider Net, Exit Multiple, Diligence Chk, Value Creation, UW
Model, Fee Tracker, LP Dashboard, Bolt-on M&A, Working Cap, Debt
Service, Mgmt Comp, Physician Prod, Regulatory Risk, Cost Structure,
Quality Scorecard, ESG Dashboard, Exit Readiness, Tax Structure, Fund
Attribution, Unit Economics, Deal Pipeline, Payer Shift, Key Person
Risk, Scenario MC, TSA Tracker, Revenue Leakage, Reference Pricing, Geo
Market, Capital Schedule, Peer Valuation, VCP/100-Day, Cap Structure,
Real Estate, Workforce Plan, Tech Stack, Growth Runway, Dividend Recap,
Continuation Veh, Earnout, Clinical Outcomes, Competitive Intel,
Patient Exp/NPS, Supply Chain, Provider Retention, Demand Forecast,
Reinvestment, Partner Economics, Insurance Tracker, ACO Economics, Phys
Comp Plan, Locum Workforce, MA Contracts, 340B Drug Pricing, Sponsor
Heatmap, Payer Concentr, Roll-Up Economics, CIN Analyzer, Base Rates,
REIT/SLB, Capital Pacing, Covenant Headroom, Red-Flag Scanner, Value
Backtester, Direct Employer, Deal Origination, Trial Site Econ, HCIT
Platform, Biosimilars, Telehealth Econ, De Novo Expansion, Health
Equity, Physician Labor, Platform Maturity, Direct Lending, PMI
Playbook, FWA Detection, Drug Shortage, Anti-Trust Scr, AI Operating
Mdl, Cyber Risk, ZBB Tracker, CMS Data Browser, MSA Concentrat, IC Memo
Generator, Module Index, Deal Post-Mortem, Secondaries, Tax Structure
An, Diligence Vendors, Refi Optimizer, LP Reporting, LBO Stress Test,
Board Governance, VDR Tracker, Escrow & Earnout, Debt Financing, VCP
Tracker, Co-Invest Pipeline, DPI Tracker, NAV Loan Tracker, Medical RE
Tracker, CMS APM Tracker, MA/Stars Tracker, GPO/Supply, Capital Call,
Litigation, Fundraising, Operating Partners, Compliance/SOC 2,
ESG/Impact, 340B Program, Risk Adj/HCC, Clinical AI, Specialty
Benchmarks, Peer Transactions, NSA/IDR, Medicaid Unwinding, Workforce
Retention, Digital Front Door, Hospital Anchor, Payer Contracts, Capex
Budget, PMI Integration, Tax Credits, Deal Sourcing, Treasury,
Sell-Side Process, R&W Insurance, Vintage Cohorts, Sponsor League, Exit
Timing, CMS Sources, Data Admin.

### Group 5 — `MAIN APP` (3 items — back-link row)
- ← Portfolio → `/portfolio`
- ← Analysis → `/analysis`
- ← Home → `/home`

## Cmd+K palette — current (24 entries)

- **NAV (6):** Home, Dashboard, Pipeline, Portfolio, Alerts, Import Deal
- **ANL (12):** PE Intelligence, Deal Screening, Portfolio Analytics,
  Corpus Backtest, Sponsor Track Record, Payer Intelligence, RCM
  Benchmarks, Hospital Screener, Market Data, Deal Search, Corpus
  Dashboard, Quant Lab
- **REF (6):** Library (Corpus), Methodology, API Docs, Module Index,
  News, Settings

## Vim-style shortcuts (14 bindings)

`?`, `/`, `Cmd/Ctrl+K`, `g h` (Home), `g a` (Analysis), `g p`
(Portfolio), `g s` (Hospital Screener), `g m` (Market Data), `g n`
(News), `g r` (Portfolio Regression), `g l` (Library), `g i` (Import
Deal), `g d` (API Docs), `g b` (PE Intelligence), `g o` (Portfolio
Analytics).

## Problems with the current state

1. **171 items in one group** — CORPUS INTEL is a dumping ground;
   hitting it scroll-tires the reader and drowns the 10 entries in
   the top three groups.
2. **No hierarchy inside CORPUS INTEL** — deals / ops / exit /
   portfolio-admin modules are intermixed, no alpha order, no topic
   clustering.
3. **Back-links (← Home) duplicate** the SEEKING CHARTIS Home entry
   higher up. Pure noise.
4. **No PLATFORM-level group** for day-to-day operator entries
   (Dashboard, Alerts, Audit). They hide inside the Corpus Intel
   dump today.

## Target state

Three groups, each ≤ 8 items, plus keep all Cmd+K / vim shortcuts
working. Everything currently in CORPUS INTEL stays *reachable*
(Cmd+K for the top 28–30 routes; link-in from the remaining nav
pages for the rest), but is removed from the sidebar.
