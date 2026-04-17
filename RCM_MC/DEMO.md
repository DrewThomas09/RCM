# SeekingChartis Demo Walkthrough

Complete hands-on tour of every feature. Takes about 25 minutes.

**Test suite: 2,965 passing tests.**

---

## Step 1: Launch (30 seconds)

```bash
cd "/Users/andrewthomas/Desktop/Coding Projects/RCM_MC"
source .venv/bin/activate
python seekingchartis.py
```

Your browser opens to **http://127.0.0.1:8080/home** automatically.

You should see:
- Dark mode UI with "SeekingChartis" in the top bar
- Market Pulse KPIs (Healthcare PE Index, 10Y Treasury, Hospital Multiple, Sentiment)
- Ticker bar with HCA, THC, UHS, CYH prices
- Left nav rail with 8 items
- Empty deals section with "Create your first deal" link
- Data Sources panel showing HCRIS hospital count
- Quick links: Market Heatmap, Regression, Screen Hospitals, Source Deals, Scenarios, Library

**Try:** Press `?` to see keyboard shortcuts. Press `/` to focus the search bar.

---

## Step 2: Explore Market Data (3 min)

Click **Market Data** in the left nav (or press `g` then `m`).

**http://127.0.0.1:8080/market-data/map**

What you see:
- KPI cards: Total hospitals, beds, revenue, avg margin, avg HHI, avg Medicare mix
- State-by-state heatmap table colored by the selected metric
- 6 metric buttons: Avg Margin, HHI, Hospital Count, Avg Beds, Medicare %, Total Revenue
- **Built-in OLS regression** showing what predicts hospital margins (R-squared, coefficients, magnitude bars)
- Data sources panel (HCRIS, FRED, Capital IQ)

**Try:**
- Click "HHI (Concentration)" to recolor by market concentration
- Click any state abbreviation (e.g., "AL") to drill into that state
- On the state page, click any hospital name to see its full profile

---

## Step 3: Hospital Profile (2 min)

From the AL state page, click any hospital. Or go directly:

**http://127.0.0.1:8080/hospital/010001**

What you see:
- CCN badge, bed count, location
- SeekingChartis Score (0-100) with letter grade
- Fundamentals: NPR, operating margin, net income, beds
- Payer mix bar (Medicare / Medicaid / Commercial)
- Score breakdown table with component bars
- Comparable hospitals in the same state
- Action buttons: Run Full Diligence, View Financials, Market Analysis, Quick DCF

---

## Step 4: Import Deals (2 min)

Click **+ Import Deal** on the home page, or press `g` then `i`.

**http://127.0.0.1:8080/import**

### Option A: Form input
Fill in:
- Deal ID: `southeast`
- Hospital Name: `Southeast Health Medical Center`
- Denial Rate: `14.2`
- Days in AR: `52`
- Net Collection Rate: `94.5`
- Clean Claim Rate: `88`
- Cost to Collect: `5.1`
- Net Revenue: `386000000`
- Bed Count: `332`
- State: `AL`

Click **Create Deal**. You're redirected to the deal page.

### Option B: JSON bulk import
Scroll down to "Bulk Import (JSON)" and paste:
```json
[
  {"deal_id": "southeast", "name": "Southeast Health Medical Center",
   "profile": {"bed_count": 332, "denial_rate": 14.2, "days_in_ar": 52,
               "net_collection_rate": 94.5, "cost_to_collect": 5.1,
               "clean_claim_rate": 88, "net_revenue": 386000000,
               "claims_volume": 180000}},
  {"deal_id": "marshall", "name": "Marshall Medical Center South",
   "profile": {"bed_count": 195, "denial_rate": 11.8, "days_in_ar": 44,
               "net_collection_rate": 96.1, "cost_to_collect": 4.3,
               "clean_claim_rate": 91, "net_revenue": 180000000,
               "claims_volume": 95000}},
  {"deal_id": "north_alabama", "name": "North Alabama Medical Center",
   "profile": {"bed_count": 223, "denial_rate": 18.5, "days_in_ar": 61,
               "net_collection_rate": 91.2, "cost_to_collect": 6.8,
               "clean_claim_rate": 82, "net_revenue": 195000000,
               "claims_volume": 110000}}
]
```

Click **Import JSON**. "Successfully imported 3 deal(s)."

### Option C: curl (if you prefer terminal)
```bash
curl -X POST http://localhost:8080/api/deals/import \
  -H "Content-Type: application/json" \
  -d '[{"deal_id":"southeast","name":"Southeast Health","profile":{"denial_rate":14.2,"days_in_ar":52,"net_revenue":386000000,"bed_count":332}}]'
```

---

## Step 5: Home Page With Deals (1 min)

Go back to **http://127.0.0.1:8080/home** (click the SeekingChartis logo or press `g h`).

Now you see:
- Market Pulse KPIs
- **Insights from SeekingChartis** — auto-generated articles about your portfolio (e.g., "2 Deals Have Denial Rates Above 15%")
- **Active Deals table** with denial rate, AR days, NPR, and action buttons (Analyze, DCF, LBO)
- Data Sources panel
- Quick links

---

## Step 6: Financial Models in the Browser (5 min)

### DCF Model
Click the **DCF** badge next to Southeast Health, or go to:

**http://127.0.0.1:8080/models/dcf/southeast**

What you see:
- Enterprise Value, PV of Cash Flows, PV of Terminal Value, Terminal Value, WACC, Terminal Growth
- 5-year Cash Flow Projections table (Revenue, EBITDA, Margin, FCF, PV)
- Sensitivity matrix: WACC x Terminal Growth
- Full assumptions breakdown
- Cross-links: LBO Model, 3-Statement, Full Analysis, Raw JSON

### LBO Model
**http://127.0.0.1:8080/models/lbo/southeast**

What you see:
- IRR (color-coded: green >20%, amber >15%, red <15%)
- MOIC, Entry EV, Exit EV, Equity Invested
- Sources & Uses table
- Annual projections: Revenue, EBITDA, Debt Balance, Interest, Leverage
- Returns waterfall

### 3-Statement Model
**http://127.0.0.1:8080/models/financials/southeast**

What you see:
- Income Statement with every line item tagged by source (HCRIS = green, deal_profile = blue, benchmark = amber, computed = gray)
- Balance Sheet
- Cash Flow Statement
- All reconstructed from HCRIS public data + deal profile inputs

---

## Step 7: Portfolio Overview (2 min)

Click **Portfolio** in the left nav (or press `g p`).

**http://127.0.0.1:8080/portfolio**

What you see:
- KPIs: Active Deals, Total Net Revenue, Avg Denial Rate, Avg Days in AR, Avg Net Collection
- Health distribution bar (green/amber/red)
- All Deals table with denial rate color-coding and action buttons
- **Portfolio Regression: Denial Rate Drivers** — what drives denial rates across your deals
- Navigation cards: Metric Heatmap, Compare Deals, Market Heatmap, Scenario Builder

---

## Step 8: Regression Analysis (2 min)

Press `g r` or navigate to:

**http://127.0.0.1:8080/portfolio/regression**

What you see:
- Data source selector: HCRIS National (~6000 hospitals) or Portfolio Deals
- Target variable dropdown
- R-Squared, Adjusted R-squared, Observations, Features, Intercept
- Coefficients table with t-statistics, significance stars, and magnitude bars
- Top Correlations table

**Try:**
- Change target to "beds" and click Run Regression
- Switch data source to "Portfolio Deals" to analyze your own portfolio

---

## Step 9: News & Research (1 min)

Press `g n` or click **News**.

**http://127.0.0.1:8080/news**

What you see:
- Category tabs: All, M&A Activity, Regulatory, Payer Policy, RCM Industry, Financial Results
- 6 curated articles with source, date, severity color, and "Diligence Impact" callout
- Market snapshot sidebar (Hospital EV/EBITDA, 10Y Treasury, S&P Healthcare)
- Key dates sidebar

**Try:** Click "Regulatory" to filter to CMS/Medicaid articles only.

---

## Step 10: Hospital Screener (2 min)

Press `g s` or click **Screener**.

**http://127.0.0.1:8080/screen**

Paste hospital names (one per line):
```
Southeast Health Medical Center
Marshall Medical Center
Huntsville Hospital
```

Click **Screen Hospitals**. See a ranked table with:
- Location, beds, risk score
- Verdict badges: STRONG_CANDIDATE (green), WORTH_INVESTIGATING (amber), PASS (red)
- "Deep dive" links to start diligence

---

## Step 11: Deal Sourcing (1 min)

Navigate to **http://127.0.0.1:8080/source**

- Select an investment thesis from the dropdown (e.g., "Denial Rate Turnaround")
- Click **Find Matches**
- See ranked hospitals from HCRIS that match your thesis

---

## Step 12: Analysis Workbench (3 min)

Press `g a` to go to the Analysis hub.

**http://127.0.0.1:8080/analysis**

What you see:
- Deal picker: click any deal to launch the full workbench
- 12-tool grid showing all available analytical tools
- Portfolio-level API quick links

Click **Southeast Health** to open the full workbench:

**http://127.0.0.1:8080/analysis/southeast**

This is the Bloomberg-style 7-tab workbench:
1. **Overview** — grade, completeness, "What Should I Do Next?"
2. **RCM Profile** — every metric with percentile and trend arrows
3. **EBITDA Bridge** — interactive 7-lever waterfall
4. **Monte Carlo** — simulation distributions with P10/P50/P90
5. **Scenarios** — custom scenario overrides
6. **Risk & Diligence** — severity-ranked risk flags + auto-generated questions
7. **Provenance** — trace every number to its source

**Keyboard shortcuts:** Press `1` through `7` to switch tabs. Press `?` for help.

---

## Step 13: Library (1 min)

Press `g l` or click **Library**.

**http://127.0.0.1:8080/library**

Reference documentation for all 15+ models and tools:
- Valuation Models (DCF, LBO, 3-Statement, EBITDA Bridge)
- Market Intelligence (Market Analysis, State Heatmap, Screener, Denial Drivers)
- Quantitative Tools (Monte Carlo, OLS Regression, Pressure Test, Scenario Builder)
- Data Sources (HCRIS, FRED, SeekingChartis Score)
- Benchmarks & Methodology (RCM Benchmarks, Valuation Guide, Mauboussin Moat Framework)

---

## Step 14: Settings & Admin (1 min)

Press `g` then click Settings in the nav.

**http://127.0.0.1:8080/settings**

Six admin cards:
- Custom KPIs, Automation Rules, Integrations
- API Documentation, System Info, Health Check

Click **API Documentation** to open Swagger UI:

**http://127.0.0.1:8080/api/docs**

Interactive API explorer with all 56 endpoints.

---

## Step 15: Keyboard Shortcuts (30 seconds)

Press `?` on any page to see the full shortcut reference:

| Shortcut | Action |
|----------|--------|
| `?` | Show/hide help |
| `/` | Focus search bar |
| `g h` | Go to Home |
| `g a` | Go to Analysis |
| `g m` | Go to Market Data |
| `g n` | Go to News |
| `g p` | Go to Portfolio |
| `g r` | Go to Regression |
| `g s` | Go to Screener |
| `g l` | Go to Library |
| `g i` | Go to Import |
| `g d` | Go to API Docs |

---

## Step 16: API Power Features (3 min)

Open a new terminal and try these:

```bash
# Portfolio summary
curl http://localhost:8080/api/portfolio/summary | python -m json.tool

# Deal comparison
curl "http://localhost:8080/api/deals/compare?ids=southeast,marshall,north_alabama" | python -m json.tool

# DCF model (raw JSON)
curl http://localhost:8080/api/deals/southeast/dcf | python -m json.tool

# LBO model
curl http://localhost:8080/api/deals/southeast/lbo | python -m json.tool

# Market analysis with Mauboussin moat
curl http://localhost:8080/api/deals/southeast/market | python -m json.tool

# Denial rate decomposition
curl http://localhost:8080/api/deals/southeast/denial-drivers | python -m json.tool

# Regression: what predicts EBITDA margin?
curl "http://localhost:8080/api/portfolio/regression?target=ebitda_margin" | python -m json.tool

# Portfolio CSV export
curl http://localhost:8080/api/export/portfolio.csv -o portfolio.csv

# Full diligence package (ZIP)
curl http://localhost:8080/api/deals/southeast/package -o southeast_package.zip

# System health
curl http://localhost:8080/api/health/deep | python -m json.tool

# All 56 API endpoints
curl http://localhost:8080/api | python -m json.tool | head -40
```

---

## Step 17: Search (30 seconds)

Click the search bar (or press `/`). Type "southeast" — the typeahead dropdown shows matching hospitals from HCRIS. Click one to see its full profile page.

Press Enter to do a full-text search across your portfolio.

---

## Step 18: Run Tests (2 min)

```bash
# Full suite (2,965 tests, ~6 minutes)
.venv/bin/python -m pytest -q --ignore=tests/test_integration_e2e.py

# Just SeekingChartis tests (99 tests, ~25 seconds)
.venv/bin/python -m pytest tests/test_seekingchartis_*.py tests/test_caduceus_*.py -q

# Just the model page tests
.venv/bin/python -m pytest tests/test_seekingchartis_models.py -v
```

---

## Cleanup

```bash
# Stop the server
Ctrl+C

# Remove demo database
rm seekingchartis.db
```

---

## Quick Reference: All Pages

| Page | URL | Shortcut |
|------|-----|----------|
| Home | /home | `g h` |
| Analysis Hub | /analysis | `g a` |
| Analysis Workbench | /analysis/{deal_id} | — |
| News | /news | `g n` |
| Market Heatmap | /market-data/map | `g m` |
| State Detail | /market-data/state/{ST} | — |
| Hospital Profile | /hospital/{CCN} | — |
| Screener | /screen | `g s` |
| Portfolio | /portfolio | `g p` |
| Regression | /portfolio/regression | `g r` |
| Import Deals | /import | `g i` |
| Library | /library | `g l` |
| DCF Model | /models/dcf/{deal_id} | — |
| LBO Model | /models/lbo/{deal_id} | — |
| 3-Statement | /models/financials/{deal_id} | — |
| Deal Sourcing | /source | — |
| Scenarios | /scenarios | — |
| Pressure Test | /pressure | — |
| Calibration | /calibration | — |
| Run History | /runs | — |
| Surrogate | /surrogate | — |
| Settings | /settings | — |
| API Docs | /api/docs | `g d` |
