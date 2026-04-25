# Phase 2 Proposal — Editorial `/app` Dashboard

**Branch:** `feat/ui-rework-v3` @ `9e3daaf` · **Status:** PROPOSAL — no implementation yet
**Author:** Claude Code · **Date:** 2026-04-26
**Baseline:** Phase 1 contract tests `12/12 PASS` in both legacy + editorial modes (re-confirmed at the head of this session)

---

## TL;DR

Phase 2 ports the dashboard at `/app` — the canonical authenticated screen, matching `04-command-center.html`. Seven paired-viz/dataset blocks, plus a deals table, a focused-deal context bar, and the editorial chrome. **The data layer already exists** (`portfolio_rollup()` returns the exact aggregates the dashboard needs); Phase 2 is renderer + route work, not data work.

The original Phase 2 plan in `UI_REWORK_PLAN.md` was "Marquee surfaces — Dashboard, Deal Profile, Screening, Analysis Workbench." That's 4 pages. **I'm proposing Phase 2 = dashboard only**, splitting the others into Phase 2b/2c/2d. Reasons:

1. The dashboard is ~7× the visual surface of any of the other three (9 distinct sections vs 1–3 each)
2. It's the architectural keystone — every helper it needs (KPI strip, paired blocks, focused-deal context, atoms) is reusable for Deal Profile / Screening / Workbench
3. Shipping it alone keeps the commit count human-reviewable (~10 commits vs ~25 for all four)
4. It activates the deferred `test_v3_authenticated_pages_render_phi_banner` and the parameterized `V3_CHARTED_PAGES` pair-pattern test — both important contract gates that should land standalone, not bundled with three more page ports

**Estimated commit count: 11.** If you'd rather see this as Phase 2a / 2b / 2c / 2d (one phase per marquee surface), say so — same architecture, just different commit-cluster boundaries.

---

## Step 0 — Baseline verification

```
branch: feat/ui-rework-v3
commit: 9e3daaf

Contract tests (legacy mode):
  12 passed in 1.59s

Contract tests (CHARTIS_UI_V2=1):
  12 passed in 1.48s
```

---

## Step 1 — Source-of-truth re-read

Re-confirmed:

- **`docs/UI_REWORK_PLAN.md`** Phase 2 row: "Marquee surfaces (Week 2-3) — Dashboard, Deal Profile, Screening, Analysis Workbench." Phase 2 of *this proposal* covers the Dashboard only; defers the others to 2b/2c/2d (see TL;DR).
- **`docs/design-handoff/EDITORIAL_STYLE_PORT.md`** §5 (paired pattern), §6 (chrome + 9 components), §7 (per-page ports — §7.7 is the dashboard quad replacement spec).
- **`docs/design-handoff/reference/04-command-center.html`** is the visual ground truth. ~650 lines, 7 `.pair` blocks confirmed.
- **`cc-app.jsx`** — 17 React components (`App`, `Topbar`, `Crumbs`, `PageHead`, `WhatBlock`, `KPIStrip`, `MetricCatalog`, `SelectedDealBar`, `Pipeline`, `DealsTable`, `CovenantSection`, `DragSection`, `InitiativeSection`, `VarianceDot`, `AlertSection`, `DelivSection`, `Footer`). Architecture reference only — we ship server-rendered Python, not React.
- **`cc-components.jsx`** — 4 atoms already shipped in Phase 1 as `covenant_pill`, `stage_pill`, `number_maybe`, `sparkline_svg`.
- **`cc-data.jsx`** — mock data shape useful for matching number formats. Particularly: `PORTFOLIO.kpis` (8-cell strip), `PORTFOLIO.funnel` (7 stages), `PORTFOLIO.covenants` (6×8 grid), `PORTFOLIO.initiatives` (variance-sorted rows), `PORTFOLIO.alerts`, `PORTFOLIO.deliverables`.
- **`docs/design-handoff/IA_MAP.md`** — `/app` not yet in the topnav inventory because it didn't exist. Phase 2 commit 11 adds it under PORTFOLIO (the editorial topnav's home). Q4.1 (the `/` reroute decision) stays deferred to Phase 4.
- **`tests/test_ui_rework_contract.py`** — confirmed: deferred PHI banner test sits as a `# TODO(phase 2):` comment at line ~302; `V3_CHARTED_PAGES = []` at line ~248 ready to flip to `["/app"]`.

---

## Step 2 — Inventory + gap analysis

### 2a. Paired-block inventory (confirmed against the reference HTML)

The dashboard has **7 paired-viz/dataset blocks** plus 2 unpaired surfaces and the chrome. The "empty state" column was added during Phase 2 review — every block has a defined empty/sparse render so edge cases don't look broken.

| # | Block | spec § | Data source | New aggregator? | Empty / sparse state |
|---|---|---|---|---|---|
| 1 | KPI strip | §6.3 | `portfolio_rollup()` + per-deal `quarterly_snapshots` for sparkline | **No** | Missing scalar values render `—`; a KPI cell with n<2 quarters hides its sparkline subgraph but keeps value+delta+label. Empty fund (zero deals) → all 8 cells render `—` and the eyebrow shows "No deals tracked yet" |
| 2 | Pipeline funnel | §6.4 | `portfolio_rollup()["stage_funnel"]` | **No** | Stages with zero deals render the bar at 0px width with the stage name only (no count badge). Empty fund → 7 zero-bars + lede "Add a deal to populate the funnel." Linked to the Import Deal flow |
| 3 | Covenant heatmap | §6.7 | Derived 6-cov × 8-Q grid via `covenant_grid(deal_id)` | **Yes — minor**: derives band labels from underlying metric thresholds | No focused deal → grid hidden; eyebrow shows "Select a deal in the table above to populate." Pre-snapshot deal (no quarterly data) → 6×8 grid renders with all `—` cells + eyebrow "Awaiting first quarterly snapshot." Partial data → known cells colored, missing cells `—` faint |
| 4 | EBITDA drag | §6.8 | `DealAnalysisPacket.ebitda_bridge` for focused deal | **No** | No focused deal → "Select a deal above to see drag breakdown." Focused deal with no bridge built yet → "Run the analysis pipeline first" with link to `/diligence/thesis-pipeline` |
| 5 | Initiative tracker | §6.9 | `_render_lagging_initiatives()` aggregator | **No** | No focused deal → cross-portfolio playbook signals (top variances across deals). Focused deal with zero initiatives → "No initiatives recorded yet for this deal" + link to add |
| 6 | Alerts | §6.10 | `alerts.evaluate_active(store)` | **No** | Zero active alerts → editorial "All clear" affirmative card with green hairline (NOT a hidden block — affirmative emptiness is a feature). Wording: "No active alerts. Last evaluated {timestamp}." |
| 7 | Deliverables | §6.11 | `analysis_runs` SQLite table + `exports/` folder | **Yes**: source-swap (see G4) | Zero artifacts → "No deliverables generated yet. Run an analysis to populate." with link to `/diligence/thesis-pipeline` |
| 8 | Deals table (unpaired) | §6.5 | `store.list_deals()` + `latest_per_deal()` | **No** | Empty portfolio → "No deals yet. Click 'Import Deal' above to add one." Stage-filter showing zero rows → "No {stage} deals" inline message; clearing filter restores |
| 9 | Focused-deal bar (chrome) | §6.6 | Derived from focused row | **No** | No focused deal → bar hidden entirely (downstream blocks render their own empty states) |

**Unpaired surfaces** (chrome only, no `.pair` wrapping):

- **Deals table** (§6.5): all deals, single-line rows, click → focused deal. `store.list_deals()` + `latest_per_deal()`.
- **Focused-deal context bar** (§6.6): chrome between deals table and downstream sections, shows the focused deal's id/name/stage/EV/MOIC/IRR. Pure derived render from the focused-deal row.

**Already from Phase 1**: editorial topbar, crumbs, page-head, PHI banner, footer, `pair_block()`, atoms.

### 2b. Data gaps — flagged for decision

| # | Gap | Where it surfaces | My recommendation |
|---|---|---|---|
| **G1** | `PORTFOLIO.funnel` in cc-data has **7 stages including "Screened"** (Sourced → Screened → IOI → LOI → SPA → Closed → Hold). Our `DEAL_STAGES` is 7 entries but **does not include "Screened"** — the canonical list is `(sourced, ioi, loi, spa, closed, hold, exit)` | KPI strip + Pipeline funnel | **Drop "Screened" from the editorial funnel.** Display 7 stages matching DB (including "Exit"). The visual "screened" bucket doesn't have any data backing it, and adding it would require a new DB column on `deals` |
| **G2** | The covenant heatmap shows **6 covenants × 8 quarters** with per-cell `safe/watch/trip` band. Our schema has `covenant_status` (string per deal per snapshot) but doesn't decompose by covenant *name* (Net Leverage, Interest Coverage, Days Cash, EBITDA/Plan, Denial Rate, A/R Days) — that's a calculation derived from raw metrics + thresholds, not a stored field | Covenant heatmap | **Build the 6-row grid in a new helper (`covenant_grid(deal_id)`) that derives band labels from the 6 underlying metrics**. If a deal lacks the underlying data, that row renders as "—" with a faint background. No new DB column |
| **G3** | The reference shows a **7-quarter sparkline** in each KPI cell (`spark: [2,2,2,2,3,3,3]` etc). Our `quarterly_snapshots` table has these values but only for deals that have ≥2 snapshots — fund-level kpis are aggregations | KPI strip | **Skip the sparkline cell when the data isn't available** — render the cell without it. The cell still has value+delta+label, just no trend trail. Pure-empty-state behavior |
| **G4** | `/app` deliverables grid lists **HTML/CSV/JSON/XLS artifacts from `output v1/`** — but I deleted `output v1/` from git in the front-page cleanup commit (`9a69244`); files now live ephemerally per-deploy | Deliverables block | **Source from `exports/` folder + the `analysis_runs` SQLite table instead.** Both are still tracked; both list per-deal artifacts. Update spec §6.11 implementation note in IA_MAP |
| **G5** | Reference HTML has **a metric catalog block** (`MetricCatalog` in cc-app.jsx, §6.x not numbered) — 4-column grid below the KPI strip showing fund-level vs deal-level metrics | Optional secondary block | **Defer to Phase 2c.** Not load-bearing for the dashboard's "what's the partner reading right now" function |

### 2c. Focused-deal context — URL design

Per the Phase 1 plan, focused-deal selection is a server-side round-trip via `?deal=<id>`:

- Deals table rows are `<a href="/app?deal=ccf_2026">` links
- Pipeline-funnel stages are `<a href="/app?stage=hold">` links (additionally filterable)
- Combined: `<a href="/app?deal=ccf_2026&stage=hold">`
- The handler parses `?deal` once, looks up the focused deal, passes it to every paired-block helper that needs it
- If `?deal` is absent or invalid: default to the first deal with `stage in (hold, closed)`. If none, the section reads `"Select a deal in the table above to populate."` (editorial empty state)

This keeps the architecture stateless and bookmarkable — partners can paste a `/app?deal=ccf_2026` URL into Slack and the recipient sees the same focused state.

---

## Step 3 — Architecture proposal

### 3a. File layout

**One file per paired-block helper.** Defended against "all 9 in one file":

- Tests can mock individual helpers without parsing a 1,500-line module
- The pair-pattern contract test (Phase 1) regex-walks page output; per-block files mean a regression in one block doesn't blow up debug context for the others
- File-level diffs in PRs become reviewable sub-units (each helper is a distinct visual change)

**Cost**: 9 new files vs 1. Acceptable.

```
rcm_mc/ui/chartis/
├── app_page.py                      # Top-level dashboard renderer (orchestrator)
├── _app_kpi_strip.py                # KPI strip + paired quarterly-history table
├── _app_pipeline_funnel.py          # Pipeline funnel + paired conversion table
├── _app_deals_table.py              # Deals table (unpaired)
├── _app_focused_deal_bar.py         # Focused-deal context bar (unpaired chrome)
├── _app_covenant_heatmap.py         # 6×8 heatmap + paired state-counts table
├── _app_ebitda_drag.py              # Stacked drag bar + paired breakdown table
├── _app_initiative_tracker.py       # Variance-sorted rows + paired dot-plot
├── _app_alerts.py                   # Alert cards + paired triage table
└── _app_deliverables.py             # 4-col manifest grid + paired counts table
```

The leading underscore on the block-helper modules signals "internal to app_page" — only `app_page.py` imports them; the route handler imports `app_page.render_app_page(...)`.

### 3b. Helper signatures (all 9)

```python
# rcm_mc/ui/chartis/app_page.py

def render_app_page(
    *,
    store: PortfolioStore,
    focused_deal_id: Optional[str] = None,
    selected_stage: Optional[str] = None,
    phi_mode: Optional[str] = None,
    user: Optional[str] = None,                     # for "AS OF" page-head meta
) -> str:
    """Orchestrate the editorial dashboard.

    Reads portfolio_rollup() once, picks the focused deal, calls each
    block helper, assembles into the editorial shell. Returns full HTML.
    """
```

```python
# rcm_mc/ui/chartis/_app_kpi_strip.py
def render_kpi_strip(rollup: dict, *, deals_df: pd.DataFrame) -> str:
    """8-cell KPI strip + paired quarterly-history table.
    
    rollup has weighted_moic/irr/covenant counts; deals_df gives
    per-quarter trend for the sparkline cells (skip cell when n<2).
    """

# rcm_mc/ui/chartis/_app_pipeline_funnel.py
def render_pipeline_funnel(
    rollup: dict, *, selected_stage: Optional[str] = None
) -> str:
    """7-stage funnel + paired conversion-percentage table. Each stage
    is an <a> with href=/app?stage=X; selected stage highlights."""

# rcm_mc/ui/chartis/_app_deals_table.py
def render_deals_table(
    deals_df: pd.DataFrame, *,
    focused_deal_id: Optional[str] = None,
    selected_stage: Optional[str] = None,
) -> str:
    """Deals table — id+name, stage pill, EV, MOIC, IRR, covenant pill,
    drift, headline. Stage filter applied here. Focused row gets bg-tint
    and teal ● indicator. Each row is <a href=/app?deal=ID>."""

# rcm_mc/ui/chartis/_app_focused_deal_bar.py
def render_focused_deal_bar(deal_row: pd.Series) -> str:
    """Chrome bar showing focused deal's name+id+stage+EV+MOIC/IRR.
    Toggle buttons on the right (next/prev held deal). Returns "" if no
    focused deal (caller decides whether to render an empty-state)."""

# rcm_mc/ui/chartis/_app_covenant_heatmap.py
def render_covenant_heatmap(store: PortfolioStore, deal_id: Optional[str]) -> str:
    """6 covenants × 8 quarters. Cell colored safe/watch/trip via
    --green-soft / --amber-soft / --red-soft + matching strong border.
    Trend column on the right. Paired with state-counts table.

    When deal_id is None: renders editorial empty-state ("Select a deal
    above to populate."). When data is partial: '—' cells.
    """

# rcm_mc/ui/chartis/_app_ebitda_drag.py
def render_ebitda_drag(packet: Optional[DealAnalysisPacket]) -> str:
    """Stacked horizontal bar (5 segments by drag component) + per-component
    rows + recovery sparkline. Paired with raw breakdown + recovery quarters.
    Reads packet.ebitda_bridge (already lever-decomposed)."""

# rcm_mc/ui/chartis/_app_initiative_tracker.py
def render_initiative_tracker(
    store: PortfolioStore, deal_id: Optional[str]
) -> str:
    """Variance-sorted rows: status icon, name, deal, actual, variance %,
    progress bar. Paired with VarianceDot SVG (dots on -30%..+30% axis)
    + playbook-signal counts table."""

# rcm_mc/ui/chartis/_app_alerts.py
def render_alerts(store: PortfolioStore) -> str:
    """Alert cards (amber/red/blue) with icon+title+desc+CTA. Paired with
    triage table (R/A/B counts) + rules-fired log. Cross-deal — does NOT
    filter on focused deal."""

# rcm_mc/ui/chartis/_app_deliverables.py
def render_deliverables(store: PortfolioStore) -> str:
    """4-column manifest grid pulling from analysis_runs SQLite table +
    exports/ folder. Each cell: kind pill (HTML/CSV/JSON/XLS), filename,
    size+date. Paired with manifest counts table."""
```

### 3c. Focused-deal context — single parse point

In `_route_app_page`:

```python
def _route_app_page(self) -> None:
    if self._ui_choice != "editorial":
        # /app is editorial-only; legacy users go to /dashboard.
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", "/dashboard")
        self.end_headers()
        return
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
    focused_deal_id = (qs.get("deal") or [None])[0]
    selected_stage = (qs.get("stage") or [None])[0]
    phi_mode = (os.environ.get("RCM_MC_PHI_MODE") or "").strip().lower() or None
    store = PortfolioStore(self.config.db_path)
    user = self._current_user()
    from .ui.chartis.app_page import render_app_page
    self._send_html(render_app_page(
        store=store,
        focused_deal_id=focused_deal_id,
        selected_stage=selected_stage,
        phi_mode=phi_mode,
        user=user,
    ))
```

**One env read, one parse, one downstream pass.** Block helpers don't read env or query string — they take their dependencies as arguments.

### 3d. Route registration

- **`/app`** GET — new route. Editorial-only; legacy `?ui=v2` request 303s to `/dashboard`. Auth-required.
- **No collision** with existing routes (verified by grep on server.py: no `path == "/app"` or `path.startswith("/app")`).
- **Unauthenticated visit** → existing auth gate at `_auth_ok()` returns 401, redirects to `/login` (already wired).

### 3d-bis. Performance budget for `/app`

**Target (added during Phase 2 review):**

- `p50 ≤ 500 ms` per request
- `p99 ≤ 1.5 s` per request
- Floor environment: existing production VM (B2ats_v2, 1 GB RAM)

**Cost analysis of the proposed architecture:**

| Source | Cost | Worst case |
|---|---|---|
| `portfolio_rollup(store)` | 1 call, scans `latest_per_deal` view | ~30 ms / 50 deals |
| Per-deal sparkline data (KPI strip, 8 cells) | If naive: 8 KPIs × N deals = 8N queries | ~80 ms at 30 deals if naive; ~5 ms if batched into one GROUP BY |
| `alerts.evaluate_active(store)` | One call, joins across deals | ~40 ms / 50 deals |
| `DealAnalysisPacket` for focused deal | Cold load via `analysis_store.get_or_build_packet()` | ~150–400 ms cold; ~5 ms cached (TTL cache exists from earlier work) |
| Deliverables (`analysis_runs` query + `exports/` listing) | One SQL + one `os.scandir()` | ~10 ms |
| HTML render (9 blocks + chrome) | String concatenation | ~5 ms |

**Sum at 30 deals + cold packet:** ~230–480 ms. **At 30 deals + warm packet:** ~95 ms. **At 1–3 deals (current production):** ~50 ms cold, ~15 ms warm.

**Verdict: budget is achievable with proposed architecture.** Two cheap mitigations the orchestrator will apply from the start:

1. **`portfolio_rollup()` cached on the request handler** — block helpers receive the rollup dict as an argument rather than calling the function. Saves the duplicate-call cost when (e.g.) KPI strip and pipeline funnel both consume it.
2. **Per-deal sparkline data batched into one GROUP BY query** in `_app_kpi_strip.render_kpi_strip` — never N+1 in a render path.

**Deferred mitigations (only if needed):**

- Lazy-load deliverables block via a separate `/api/app/deliverables` endpoint (adds complexity; defer until the simple version exceeds budget on real data)
- Add a `/app` p99 contract test that fails the suite if render time crosses 1.5s on the test fixture (defer to a Phase 2.5 perf-hardening commit if Phase 2's simple implementation comes in over budget on real partner instances)

**If the simple architecture exceeds budget at first measurement, surface it before commit 1** rather than after commit 9. Budget is a guard rail, not a Phase 2.5 sign-off requirement; Phase 2 ships the simple version, the budget gets verified at production-data scale, and Phase 2.5 hardens if needed.

### 3e. PHI mode wiring (per Phase 1 correction)

```python
# In _route_app_page (handler):
phi_mode = (os.environ.get("RCM_MC_PHI_MODE") or "").strip().lower() or None

# Passed to chartis_shell via app_page:
return editorial_chartis_shell(
    body, title="Command center",
    breadcrumbs=[("Home", "/app"), ("Portfolio & diligence", None)],
    phi_mode=phi_mode,
    show_phi_banner=True,    # /app is authenticated
)
```

**Block helpers do NOT read env.** Phase 1's correction stands.

---

## Step 4 — Test plan

### 4a. Activate deferred Phase 1 tests

**(A) `test_v3_authenticated_pages_render_phi_banner`** — currently a `# TODO(phase 2):` comment. Activate:

```python
def test_v3_authenticated_pages_render_phi_banner(self) -> None:
    """Per spec §7.5: every authenticated v3 page must render the PHI banner."""
    # /app is the first authenticated v3 page (login/forgot are unauthenticated)
    os.environ["RCM_MC_PHI_MODE"] = "disallowed"
    try:
        body = self._fetch_body("/app?ui=v3")
        self.assertIn('class="phi-banner"', body)
        self.assertIn('Public data only', body)
        self.assertIn('data-phi-mode="disallowed"', body)
    finally:
        os.environ.pop("RCM_MC_PHI_MODE", None)
```

**(B) `V3_CHARTED_PAGES` activation** — flip the empty list to `["/app"]`:

```python
V3_CHARTED_PAGES: List[str] = ["/app"]
```

`test_pair_pattern_when_v3_page_renders_a_chart` then actively guards every `<svg>`/`<canvas>` on `/app` to be paired with a `<table>` inside the same `.pair` block.

### 4b. New `/app`-specific contract tests

```python
def test_v3_app_route_renders_for_authenticated_user(self) -> None:
    """GET /app?ui=v3 returns 200 with editorial markers for an authed user."""
    body = self._fetch_body("/app?ui=v3")
    self.assertIn("/static/v3/chartis.css", body)
    self.assertIn('class="topbar"', body)               # editorial chrome
    self.assertIn('class="pair"', body)                 # at least one pair block
    self.assertIn("Command center", body)               # page title
    self.assertIn('href="/api/logout"', body) or self.assertIn(
        'action="/api/logout"', body)                   # SIGN OUT wired

def test_v3_app_handles_invalid_focused_deal_id(self) -> None:
    """?deal=<garbage> must not 500 — empty-state for unknown deal."""
    code = self._fetch("/app?ui=v3&deal=does_not_exist_12345")
    self.assertEqual(code, 200,
                     "/app should empty-state on unknown deal, not 500")

def test_v3_app_handles_invalid_stage_filter(self) -> None:
    """?stage=<garbage> must not 500."""
    code = self._fetch("/app?ui=v3&stage=does_not_exist")
    self.assertEqual(code, 200)

def test_v3_app_legacy_request_redirects_to_dashboard(self) -> None:
    """/app without ui=v3 redirects to /dashboard (no legacy /app exists)."""
    code = self._fetch("/app")  # default ui choice = legacy
    self.assertIn(code, (302, 303),
                  "GET /app with legacy ui_choice must redirect, not 404 or 500")
```

### 4c. Total expected test count

```
Phase 1 baseline           : 12
+ test_v3_authenticated_pages_render_phi_banner  : +1
+ test_v3_app_route_renders_for_authenticated_user : +1
+ test_v3_app_handles_invalid_focused_deal_id      : +1
+ test_v3_app_handles_invalid_stage_filter         : +1
+ test_v3_app_legacy_request_redirects_to_dashboard: +1
                                                   ────
Phase 2 final               : 17
```

The pair-pattern test count stays at 1 (it's parameterized; its behavior changes from "vacuously passes" to "actively guards `/app`").

---

## Step 5 — Conflicts and open questions

### 5a. Conflicts that need user decision

| # | Conflict | My recommendation |
|---|---|---|
| **C1** | `cc-data.jsx` funnel has 7 stages including **"Screened"** which doesn't exist in `DEAL_STAGES`. Adding "Screened" requires a new DB-backed concept | **Drop "Screened"; show 7 stages matching DB.** Confirm? |
| **C2** | `output v1/` was untracked + deleted in commit `9a69244` (Apr 25 cleanup). Reference deliverables block sources from there | **Source from `analysis_runs` SQLite table + `exports/` folder.** Update spec §6.11 implementation note. Confirm? |
| **C3** | `MetricCatalog` (4-column fund-vs-deal metric grid) appears in `cc-app.jsx` but isn't numbered in spec §6 | **Defer to Phase 2c** as "the 10th block." Phase 2 ships 9 main blocks per spec §6.3–6.11. Confirm? |
| **C4** | KPI strip "hover a cell → table updates to that KPI's history" is **client-side state**. Pushed back during review — replacing hover with click is a UX change, not just an implementation detail | **RESOLVED to option (b): defer interaction to Phase 3.** Phase 2 ships KPI cells static-but-rendered + a single fixed paired table showing the headline KPI's quarterly history (`Weighted MOIC` per `cc-app.jsx:157` default). A `# TODO(phase 3): KPI cell interaction` comment in `_app_kpi_strip.py` keeps the followup visible. Phase 3 makes a deliberate UX decision (hover JS / click toggle / small-multiples / palette filter) without prejudice from a stale Phase 2 implementation |
| **C5** | Spec §7.7 says "replace the dark four-quadrant grid with two .pair blocks stacked: Pipeline Funnel + (its conversion table); Active Alerts + (alert triage table). Then a third row: Portfolio Health as a paired covenant heatmap mini + state counts." | This describes a **simpler dashboard** than `04-command-center.html` shows. **Recommend: ship the full 9-block dashboard from `04-command-center.html`** since the reference HTML is byte-for-byte ground truth per the bundle's README. The 3-row simpler layout was an earlier description. Confirm? |
| **C6** | Real-time updates / animations / drag-to-reorder are mentioned in `cc-app.jsx` (the React app uses `useState` for `selectedDealId`, `stage`, etc.) | **All client-side state becomes server round-trips via URL params.** Already covered in §3c. Confirm acceptable? |

### 5b. Sub-split — Phase 2 commit count

**11 commits** (current proposal scope = dashboard only):

```
1.  feat(app-helpers): _app_kpi_strip render — KPI strip + paired
2.  feat(app-helpers): _app_pipeline_funnel render — funnel + paired conversion
3.  feat(app-helpers): _app_deals_table + _app_focused_deal_bar
4.  feat(app-helpers): _app_covenant_heatmap render + covenant_grid derivation
5.  feat(app-helpers): _app_ebitda_drag render
6.  feat(app-helpers): _app_initiative_tracker render
7.  feat(app-helpers): _app_alerts render
8.  feat(app-helpers): _app_deliverables render
9.  feat(app): app_page.py orchestrator + /app route handler
10. test(contract): activate phi_banner + V3_CHARTED_PAGES + /app routes (12→17)
11. docs(ui-rework): update IA_MAP + UI_REWORK_PLAN with /app placement + Phase 2 rollback + Phase 3 open questions
```

**Original Phase 2 plan was "Marquee surfaces" (4 pages).** Recommend splitting:

- **Phase 2** (this proposal) — Dashboard at `/app`. ~11 commits.
- **Phase 2b** — Deal Profile editorial port. ~6 commits (no new chrome; reuse paired blocks)
- **Phase 2c** — Screening editorial port. ~5 commits (mostly the deals table + filter UI; data already exists)
- **Phase 2d** — Analysis Workbench editorial port. ~8 commits (the Bloomberg six-tab page is the second-largest surface after the dashboard)

Each sub-phase ships independently with its own contract tests + rollback. If you'd rather call this "Phase 2a" formally, I'll rename in the proposal doc.

### 5c. Pause points during implementation

Per Phase 1 pattern:

- **After commit 1** (the first paired-block helper, KPI strip): paste the public API surface for review. Locks the helper signature shape that the next 8 helpers will follow.
- **Before commit 9** (the orchestrator): paste `app_page.render_app_page` body in pseudocode for review — that's the wiring surface where data + chrome + atoms come together, and where helper-API mismatches will surface.
- **Before commit 11** (docs): paste the IA_MAP / UI_REWORK_PLAN diffs.

---

## Step 6 — Decisions needed before commit 1

Six items in 5a (C1–C6), one structural question:

1. **C1** — Drop "Screened" from funnel? (yes/no)
2. **C2** — Source deliverables from `analysis_runs` + `exports/`? (yes/no)
3. **C3** — Defer MetricCatalog to Phase 2c? (yes/no)
4. **C4** — KPI hover via pure CSS click-toggle? (yes/no — alternative: ship without inter-cell selection, single static quarterly-history table)
5. **C5** — Ship full 9-block dashboard (matching `04-command-center.html`)? (yes/no — alternative: ship the simpler 3-row layout per spec §7.7)
6. **C6** — All UI state via URL round-trips, no JS? (yes/no — alternative: minimal vanilla JS for hover effects only)

Plus:

7. **Sub-split** — keep this proposal's scope as "Phase 2 = dashboard only, 2b/2c/2d for the others"? Or insist on the original "Marquee surfaces — all 4 in one phase, ~25 commits"?

Confirm those seven and I proceed to commit 1 → pause for KPI-strip API review → commits 2–8 → pause before commit 9 (orchestrator) → commits 9–11 → push.

**Hard rules respected throughout:**

- All work stays on `feat/ui-rework-v3`. Never push to `main`.
- Contract tests stay green at every commit (12 minimum, climbing to 17 by commit 10).
- Data model wins — every gap above (G1–G5) has a "do less, ask user" recommendation.
- Pause before committing the proposal-as-implementation; this document is the proposal.
