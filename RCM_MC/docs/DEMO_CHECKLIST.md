# Partner-walkthrough demo checklist

Phase 3 of the editorial UI rework targets a partner walkthrough of `/app?ui=v3`. This document captures (1) what data needs to be in the demo DB, (2) the walkthrough talking points, and (3) the things to NOT do in the demo because they're explicitly partial.

This is a runbook, not a script. The bullets give you decision-points (click here, then here, then say this); the talking is yours.

---

## Pre-demo data requirements

Run on a clean DB or reset the demo DB before walkthrough:

- [ ] At least **3 deals** in stage `hold` or `exit` (so cross-portfolio blocks have something to aggregate).
- [ ] At least **1 deal** in `loi` or `sourced` (so the funnel block has multi-stage representation).
- [ ] Each held deal has ≥ 2 `deal_snapshots` rows (so the covenant Net Leverage row has a trend, not a single point).
- [ ] At least **2 initiatives** recorded across ≥ 2 deals in the trailing 4 quarters with mean variance ≤ -10% (so the cross-portfolio initiative tracker shows a "PLAYBOOK GAP" pill).
- [ ] At least **1 generated_exports** row pointing to a real file under `/data/exports/<deal_id>/` (so the deliverables block shows a card, not the empty-state).
- [ ] `RCM_MC_PHI_MODE=disallowed` exported (so the muted-green compliance band is visible).

---

## Quick verification commands (run the night before)

Five lines of bash that take ~10 seconds total and tell you "is the demo DB in the right state?" Run these the night before the walkthrough:

```bash
cd ~/Desktop/Coding\ Projects/RCM_MC
DEMO_DB="$PWD/seekingchartis.db"   # adjust to your demo DB path

# 1. Verify deal counts and stages
.venv/bin/python -c "
from rcm_mc.portfolio.store import PortfolioStore
from rcm_mc.portfolio.portfolio_snapshots import latest_per_deal
df = latest_per_deal(PortfolioStore('${DEMO_DB}'))
print(df.groupby('stage').size() if not df.empty else 'EMPTY DB')
"

# 2. Verify generated_exports has rows for at least one deal
.venv/bin/python -c "
import sqlite3
con = sqlite3.connect('${DEMO_DB}')
con.row_factory = sqlite3.Row
rows = con.execute('SELECT deal_id, COUNT(*) AS n FROM generated_exports GROUP BY deal_id').fetchall()
print(f'Total deals with exports: {len(rows)}')
for r in rows:
    print(f'  {r[\"deal_id\"]}: {r[\"n\"]}')
"

# 3. Verify initiative_actuals has trailing-4Q rows
.venv/bin/python -c "
import sqlite3
con = sqlite3.connect('${DEMO_DB}')
con.row_factory = sqlite3.Row
rows = con.execute(
    \"SELECT initiative_id, COUNT(*) AS n FROM initiative_actuals \"
    \"WHERE quarter >= '2025Q3' GROUP BY initiative_id\"
).fetchall()
print(f'Initiatives in trailing 4Q: {len(rows)}')
for r in rows:
    print(f'  {r[\"initiative_id\"]}: {r[\"n\"]} actuals')
"

# 4. Verify contract suite is green
.venv/bin/python -m pytest tests/test_ui_rework_contract.py -q | tail -3
```

If step 1 prints `EMPTY DB` or step 2 prints `Total deals with exports: 0`, the demo DB needs seeding before walkthrough.

---

## Walkthrough flow (~8 min target)

Each step is tagged **[core]** (mandatory — these prove the load-bearing wiring) or **[expand-if-time]** (drop first if partner conversation eats the budget).

1. **[core] Land on `/app?ui=v3`.** Pause on the editorial chrome — the topbar, the page-head meta column, the muted PHI band. *"This is compliance signal as institutional chrome, not as a hero alert."*
2. **[expand-if-time] KPI strip.** Walk left-to-right: NAV, MOIC, IRR, hold years, etc. The static-but-rendered version (Q3.1 deferred); the right-side table is fixed to the headline KPI's history.
3. **[expand-if-time] Pipeline funnel.** Click a stage to filter the deals table; show that the funnel itself doesn't filter (it's context, not a target).
4. **[expand-if-time] Deals table.** Click a hold deal to focus it.
5. **[expand-if-time] Focused-deal context bar.** Prev/next switcher restricted to the `hold` ∪ `exit` subset.
6. **[core] Covenant heatmap.** *"Net Leverage is wired from real snapshots. The other five render `—` honestly — Q4.5 tracks the schema work to wire them."*
7. **[expand-if-time] EBITDA drag bar.** *"Five buckets with real per-`metric_key` impacts from the bridge. `net_collection_rate` is correctly routed to 'other' because it's a composite — Q4.6 tracks the proper 6th component."*
8. **[core] Initiative tracker.** Show focused-deal mode (variance-sorted), then unfocus the deal and show cross-portfolio mode with the PLAYBOOK GAP pill. *"Trailing 4 quarters by default — a no-time-window default would surface stale signals as if they were current playbook gaps."*
9. **[expand-if-time] Alerts + deliverables.** Show that deliverables are real files on disk at the canonical path; clicking opens the file.

If you only have 4 minutes, do steps 1, 6, 8 — that's the partner-readable proof that the dashboard is real.

---

## Things to NOT do in the demo

- **Do NOT** click through to the legacy `/dashboard` mid-walkthrough. The contrast is not the point; the editorial dashboard is.
- **Do NOT** demo the unwired 5 covenant rows as if they're real signals — call out the partial wiring honestly.
- **Do NOT** open the alerts block expecting interactivity beyond the cards. Phase 3 ships the read-only surface.
- **Do NOT** demo Q3.1 (KPI hover/click) or scroll-aid (Q3.6) — both are deferred to Phase 4.
- **Do NOT** ship a number for the "Self-pay vs. payer underpayment" split during partner Q&A. Q4.6's reasoning is exactly that this dashboard refuses to invent the attribution. Saying "we attribute it ⅔/⅓" verbally is the same misdirection as shipping it on the dashboard.

---

## Recovery script (if something flunks live)

If the dashboard 500s during the walkthrough:

1. Check `RCM_MC_PHI_MODE` is set (un-set falls back to no banner — not fatal, but visually different from rehearsal).
2. Check the demo DB has snapshots (empty DB → empty-state, not 500). Run the verification commands above.
3. Failover URL: `/dashboard` (legacy dark shell — old but reliable). The Phase 3 rollback procedure in `UI_REWORK_PLAN.md` documents the env-flag flip if the editorial path is broken.
4. Tail the server log for the actual exception. The route handler is wrapped to never 500 on bad query params (Q3 contract tests guard this), but a packet builder failure on a focused deal could still bubble. Unfocus the deal (remove `?deal=...`) to recover.

---

## See also

- [`UI_REWORK_PLAN.md`](UI_REWORK_PLAN.md) — full plan, conventions, rollback procedures
- [`design-handoff/EDITORIAL_STYLE_PORT.md`](design-handoff/EDITORIAL_STYLE_PORT.md) — the spec
- [`design-handoff/IA_MAP.md`](design-handoff/IA_MAP.md) — full nav inventory
