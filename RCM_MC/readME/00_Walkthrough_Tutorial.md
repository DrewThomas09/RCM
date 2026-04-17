# RCM-MC Walkthrough Tutorial

A hands-on tour of everything RCM-MC can do. Takes about 30 minutes. By the end you'll have screened hospitals, created deals, run analysis, generated an AI memo, and explored a full portfolio dashboard.

> **Prerequisites**: Python 3.10+, the `.venv` activated, and `pip install -e ".[all]"` done.

---

## Part 1: Fire It Up (2 min)

### Start the server

```bash
cd /path/to/RCM_MC
source .venv/bin/activate
python demo.py
```

Or manually:

```bash
.venv/bin/python -m rcm_mc.server --port 8080 --db walkthrough.db
```

You should see:

```
rcm-mc v0.6.0 -- http://127.0.0.1:8080/
  portfolio DB: walkthrough.db
  deals:        0
  API docs:     http://127.0.0.1:8080/api/docs
  started in:   234ms
  Ctrl+C to stop
```

Open **http://127.0.0.1:8080** in your browser.

### What to notice

- Dark mode by default (respects your OS preference)
- Global nav bar: Dashboard, + New Deal, Screen, Source, Heatmap, Map, Alerts, Runs, Scenarios, Settings, API
- Alert badge in the nav (shows count when alerts exist)
- Empty dashboard with "no deals" state

---

## Part 2: Import Some Deals via API (3 min)

Open a new terminal. Let's create 3 deals using the API:

```bash
# Import 3 hospital deals
curl -X POST http://localhost:8080/api/deals/import \
  -H "Content-Type: application/json" \
  -d '[
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
  ]'
```

Expected: `{"imported": 3, "deal_ids": ["southeast", "marshall", "north_alabama"]}`

**Refresh your browser** -- the dashboard now shows 3 deals!

### Things to try

- Click each deal name to see the deal page
- Notice the health scores and trend sparklines
- Look at the stage funnel (all "pipeline" for now)

---

## Part 3: Explore the Dashboard API (3 min)

```bash
# Portfolio summary -- weighted MOIC, alerts, covenant status
curl http://localhost:8080/api/portfolio/summary | python -m json.tool

# Health distribution -- how many green/amber/red?
curl http://localhost:8080/api/portfolio/health | python -m json.tool

# Cross-deal metric matrix -- spreadsheet view
curl "http://localhost:8080/api/portfolio/matrix?metrics=denial_rate,days_in_ar,net_collection_rate" | python -m json.tool

# Deal stats
curl http://localhost:8080/api/deals/stats | python -m json.tool
```

### What to notice

- The matrix endpoint gives you a spreadsheet-ready comparison
- Health bands show which deals need attention
- Everything returns structured JSON with proper headers

---

## Part 4: Deep-Dive on a Deal (5 min)

### Validate the data

```bash
curl http://localhost:8080/api/deals/north_alabama/validate | python -m json.tool
```

North Alabama has high denial rate (18.5%) -- the validator may flag concerns.

### Check completeness

```bash
curl http://localhost:8080/api/deals/north_alabama/completeness | python -m json.tool
```

See how many of the 38-metric registry fields are populated. Missing keys tell you what data to request from the seller.

### Add notes

```bash
curl -X POST http://localhost:8080/api/deals/north_alabama/notes \
  -d "deal_id=north_alabama&body=Initial+review:+denial+rate+at+18.5%25+is+concerning.+Request+payer+mix+breakdown.&author=Partner+AT"
```

### Add tags

```bash
curl -X POST http://localhost:8080/api/deals/north_alabama/tags \
  -d "deal_id=north_alabama&tag=high-priority"

curl -X POST http://localhost:8080/api/deals/north_alabama/tags \
  -d "deal_id=north_alabama&tag=denial-turnaround"
```

### Set stage

```bash
curl -X POST http://localhost:8080/api/deals/north_alabama/stage \
  -d "deal_id=north_alabama&stage=diligence&changed_by=Partner+AT"
```

### Check the IC prep checklist

```bash
curl http://localhost:8080/api/deals/north_alabama/checklist | python -m json.tool
```

See which items are done and which are blocking IC readiness.

### Get badge counts (what the UI uses)

```bash
curl http://localhost:8080/api/deals/north_alabama/counts | python -m json.tool
```

### Now visit the deal page

Open **http://localhost:8080/deal/north_alabama** in your browser.

**Things to notice:**
- Your notes appear in the notes section
- Tags show as badges
- Stage is now "diligence"
- Health score with component breakdown
- Timeline shows all your actions

---

## Part 5: Run Analysis (5 min)

### Build an analysis packet

```bash
curl http://localhost:8080/api/analysis/north_alabama | python -m json.tool | head -50
```

This builds the full `DealAnalysisPacket` -- the canonical data structure everything renders from.

### Open the Analysis Workbench

Visit **http://localhost:8080/analysis/north_alabama**

**This is the crown jewel.** A Bloomberg-style 7-tab workbench:

1. **Overview** -- grade, completeness bar, "What Should I Do Next?" card
2. **RCM Profile** -- every metric with source icon, benchmark percentile, trend arrows
3. **EBITDA Bridge** -- interactive waterfall chart (drag the sliders!)
4. **Monte Carlo** -- simulation distributions with confidence intervals
5. **Scenarios** -- add custom scenarios with target overrides
6. **Risk & Diligence** -- severity-ranked risk flags + auto-generated questions
7. **Provenance** -- trace every number back to its source

### Keyboard shortcuts (try these!)

- Press **1** through **7** to switch tabs
- Press **Alt+Right/Left** to navigate tabs
- Press **?** to see the help dialog

### Action bar

- **Rebuild** -- regenerate the packet
- **JSON** -- raw packet data
- **Diligence CSV** -- questions for the seller
- **Provenance** -- full lineage graph
- **Archive** (amber) -- soft-delete the deal
- **Delete** (red) -- permanent removal with confirmation

---

## Part 6: Compare Deals (3 min)

### Side-by-side comparison

Visit **http://localhost:8080/compare?deals=southeast,marshall,north_alabama**

See the radar chart overlay and metric-by-metric comparison table.

### API comparison

```bash
curl "http://localhost:8080/api/deals/compare?ids=southeast,marshall,north_alabama" | python -m json.tool
```

### Find similar deals

```bash
curl http://localhost:8080/api/deals/north_alabama/similar | python -m json.tool
```

### Peer comparison with metric deltas

```bash
curl http://localhost:8080/api/deals/north_alabama/peers | python -m json.tool
```

---

## Part 7: Exports (3 min)

### One-click diligence package

```bash
curl http://localhost:8080/api/deals/north_alabama/package -o north_alabama_package.zip
unzip -l north_alabama_package.zip
```

Inside: executive summary HTML, EBITDA bridge, risk matrix, diligence questions, raw data CSVs, and a manifest.

### See all export links

```bash
curl http://localhost:8080/api/deals/north_alabama/export-links | python -m json.tool
```

### Portfolio CSV

```bash
curl http://localhost:8080/api/export/portfolio.csv -o portfolio.csv
cat portfolio.csv
```

---

## Part 8: AI Features (3 min)

### Generate an IC memo

```bash
# Template-based (no LLM needed)
curl http://localhost:8080/api/deals/north_alabama/memo | python -m json.tool
```

See the sections: executive summary, risk assessment, value creation, etc. Each section has `fact_checks_passed: true`.

### Document QA

```bash
curl "http://localhost:8080/api/deals/north_alabama/qa?q=what+is+the+denial+rate" | python -m json.tool
```

### Conversational chat

```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How many deals are in the portfolio?", "session_id": "demo"}'
```

(Without an LLM API key, you'll get a fallback message directing to the query interface. With `ANTHROPIC_API_KEY` set, you'd get an AI-powered answer with tool dispatch.)

---

## Part 9: Deal Lifecycle Operations (3 min)

### Clone a deal

```bash
curl -X POST http://localhost:8080/api/deals/north_alabama/duplicate \
  -H "Content-Type: application/json" \
  -d '{"new_deal_id": "north_alabama_v2", "new_name": "North Alabama (Scenario B)"}'
```

### PATCH a profile field

```bash
curl -X PATCH http://localhost:8080/api/deals/north_alabama_v2/profile \
  -H "Content-Type: application/json" \
  -d '{"denial_rate": 12.0, "name": "North Alabama (Post-Fix)"}'
```

### Archive a deal

```bash
curl -X POST http://localhost:8080/api/deals/marshall/archive
```

### Check it's hidden from the dashboard

```bash
curl http://localhost:8080/api/deals/stats | python -m json.tool
# archived_deals should be 1
```

### Unarchive it

```bash
curl -X POST http://localhost:8080/api/deals/marshall/unarchive
```

### Pin a deal

```bash
curl -X POST http://localhost:8080/api/deals/southeast/pin -d ""
```

### Bulk operations

```bash
curl -X POST http://localhost:8080/api/deals/bulk \
  -H "Content-Type: application/json" \
  -d '{"action": "tag", "deal_ids": ["southeast", "marshall"], "tag": "q2-review"}'
```

---

## Part 10: Infrastructure & Monitoring (3 min)

### System info

```bash
curl http://localhost:8080/api/system/info | python -m json.tool
```

### Deep health check

```bash
curl http://localhost:8080/api/health/deep | python -m json.tool
```

Check: DB latency, migration status, HCRIS data age, disk usage.

### Request metrics

```bash
# Make a few requests first, then:
curl http://localhost:8080/api/metrics | python -m json.tool
```

See p50/p95/p99 response times.

### Database backup

```bash
curl http://localhost:8080/api/backup -o backup.db
ls -la backup.db
```

### Migration status

```bash
curl http://localhost:8080/api/migrations | python -m json.tool
```

### API index

```bash
curl http://localhost:8080/api | python -m json.tool | head -30
```

All 56 methods listed with summaries.

---

## Part 11: Special Pages (3 min)

Visit each of these in your browser:

| URL | What You'll See |
|-----|----------------|
| **http://localhost:8080/screen** | Hospital screening page -- paste names for instant verdicts |
| **http://localhost:8080/source** | Thesis-driven deal sourcing from 17,974 HCRIS hospitals |
| **http://localhost:8080/scenarios** | Preset shock scenarios (Commercial IDR +20%, etc.) |
| **http://localhost:8080/runs** | Simulation run history table |
| **http://localhost:8080/calibration** | Per-payer prior sliders (interactive!) |
| **http://localhost:8080/pressure?deal_id=north_alabama** | Pressure test with risk flags |
| **http://localhost:8080/surrogate** | Surrogate model status page |
| **http://localhost:8080/settings** | Settings hub: Custom KPIs, Automations, Integrations |
| **http://localhost:8080/api/docs** | Swagger UI -- interactive API explorer |

---

## Part 12: Webhooks & Events (2 min)

### Register a webhook (use a test URL)

```bash
curl -X POST http://localhost:8080/api/webhooks \
  -H "Content-Type: application/json" \
  -d '{"url": "https://httpbin.org/post", "secret": "demo-secret", "events": ["*"]}'
```

### Test delivery

```bash
curl http://localhost:8080/api/webhooks/test | python -m json.tool
```

### Delete a deal (triggers webhook)

```bash
curl -X DELETE http://localhost:8080/api/deals/north_alabama_v2
```

---

## Part 13: Run the Test Suite (5 min)

```bash
# Full suite (2,883 tests, ~6 minutes)
.venv/bin/python -m pytest -q --ignore=tests/test_integration_e2e.py

# Just the API tests
.venv/bin/python -m pytest -m api -q

# Just the new feature tests
.venv/bin/python -m pytest tests/test_improvements_b*.py -q

# Single feature
.venv/bin/python -m pytest tests/test_improvements_b106.py -v
```

---

## Part 14: Response Headers (1 min)

Every API response is loaded with useful headers:

```bash
curl -v http://localhost:8080/api/health 2>&1 | grep -E "^< "
```

You'll see:
- `X-Request-Id` -- correlation ID for debugging
- `X-Response-Time` -- server timing
- `X-API-Version` -- API version
- `Access-Control-Allow-Origin` -- CORS
- `Content-Encoding: gzip` -- compression (for large responses)

```bash
# Conditional GET with ETags
curl -v http://localhost:8080/api/analysis/southeast 2>&1 | grep ETag
# Then use the ETag:
curl -H "If-None-Match: \"<etag-value>\"" http://localhost:8080/api/analysis/southeast
# Returns 304 Not Modified!
```

---

## Part 15: Print the Workbench (1 min)

Open **http://localhost:8080/analysis/southeast** and press **Ctrl+P**.

The print stylesheet kicks in:
- Nav, tabs, and buttons hidden
- White background, black text
- Cards get borders for clarity
- Links show their URLs inline
- Page breaks avoid splitting cards

---

## Cleanup

```bash
# Stop the server
Ctrl+C

# Remove the demo database
rm walkthrough.db
```

---

## Summary: What You Just Used

| Category | Count |
|----------|-------|
| API endpoints hit | ~35 |
| Web pages visited | ~12 |
| HTTP methods used | GET, POST, PATCH, DELETE |
| Features exercised | Import, validate, analyze, compare, export, memo, QA, chat, clone, archive, bulk ops, webhooks, monitoring |

**Total test count: 2,883 passing.** Every feature in this walkthrough is covered by automated tests.
