# UI Consistency Audit — Theme Inventory + Migration Plan

**Branch:** `chore/ui-polish-and-sanity-guards`
**Date:** 2026-04-18
**Scope:** Every route registered in [rcm_mc/server.py](../rcm_mc/server.py),
paired with the page renderer and the shell (layout wrapper) it calls. The
goal is a single visual language across the platform — no chrome flicker
when partners click between pages.

---

## Executive summary

The platform is not a light-vs-dark split. It is **two different
dark themes**. Both use near-black backgrounds and Inter / JetBrains
Mono; what changes between them is the shade of dark, the accent
colour, and the surrounding chrome (top bar, ticker, nav rail).
The user's complaint — "theme flicker" — is produced by navigating
between those two dark systems, not by a light→dark jump.

| Bucket | Count | Shell | File |
|---|---|---|---|
| **chartis-dark** (institutional) | **191** | `chartis_shell` | [rcm_mc/ui/_chartis_kit.py](../rcm_mc/ui/_chartis_kit.py) |
| **shell-v2-dark** (Bloomberg) | **56** | `shell_v2` | [rcm_mc/ui/shell_v2.py](../rcm_mc/ui/shell_v2.py) |
| JSON / file / redirect / inline | **25** | n/a | — |
| **Total routes** | **272** | | |

The legacy light-theme shell ([_ui_kit.shell()](../rcm_mc/ui/_ui_kit.py))
still exists in the codebase but its `shell()` function delegates to
`shell_v2()` (see `_ui_kit.py:386-402`) so the `BASE_CSS` light palette is
dead code in production. No route actually renders the light palette.

**Recommendation:** unify on `chartis_shell`. Reasoning in Section D.

---

## A. Theme inventory

### A.1 Dark theme — `chartis_shell` (institutional, 191 routes)

All 191 routes render through [_chartis_kit.chartis_shell()](../rcm_mc/ui/_chartis_kit.py).
Grouped by section for scan-ability. File:line citations point to the
route registration in [server.py](../rcm_mc/server.py).

#### Chartis premium pages (Phase 2A/2B/2C, 10 routes)
| Route | Page module | server.py |
|---|---|---|
| /home | ui/chartis/home_page.py | 1789 |
| /pe-intelligence | ui/chartis/pe_intelligence_hub_page.py | 2881 |
| /sponsor-track-record | ui/chartis/sponsor_track_record_page.py | 2888 |
| /payer-intelligence | ui/chartis/payer_intelligence_page.py | 2894 |
| /rcm-benchmarks | ui/chartis/rcm_benchmarks_page.py | 2900 |
| /corpus-backtest | ui/chartis/corpus_backtest_page.py | 2906 |
| /deal-screening | ui/chartis/deal_screening_page.py | 2913 |
| /portfolio-analytics | ui/chartis/portfolio_analytics_page.py | 2920 |
| /deal/&lt;id&gt;/partner-review etc. (8 per-deal) | ui/chartis/*_page.py | 3730-3740 |

#### Data-public pages (~140 routes at server.py:1817-2460)
The big batch wired in the Phase 1 corpus-intelligence work. Every
`/aco-economics`, `/base-rates`, `/sponsor-heatmap`, … through
`/risk-matrix` renders a `ui/data_public/*_page.py` module that calls
`chartis_shell`. Representative examples with line numbers:

- /backtest (1828), /sponsor-league (1834), /sponsor-heatmap (1864),
  /base-rates (1884), /backtester (1909), /cms-data-browser (2004),
  /ic-memo-gen (2014), /module-index (2019), /lp-reporting (2049),
  /lbo-stress (2054), /vintage-cohorts (2239), /qoe-analyzer (2635),
  /corpus-dashboard (2537), /deal-search (2522), /find-comps (2574),
  /rcm-red-flags (2590), /payer-intel (2679), /sector-intel (2684),
  /comparables (2740), /library (2934 → corpus, Phase 2A)

The full list is ~140 slugs long; every one consistent.

### A.2 Dark theme — `shell_v2` (Bloomberg, 56 routes)

All 56 routes render through [shell_v2()](../rcm_mc/ui/shell_v2.py).
Uses [brand.PALETTE](../rcm_mc/ui/brand.py) (near-black `#05070b`,
amber accent `#e8a33d`).

| Route | Handler | Page module | server.py |
|---|---|---|---|
| `/` | `_route_dashboard()` | ui/home_v2.py | 1786 |
| `/import` | inline | ui/quick_import.py | 1794 |
| `/methodology` | inline | ui/library_page.py | 1799 |
| `/methodology/calculations` | inline | ui/methodology_page.py | 1802 |
| `/query` | `_route_deal_query()` | ui/data_explorer.py | 2749 |
| `/benchmarks` | `_route_benchmarks()` | ui/models_page.py | 2751 |
| `/data` | `_route_data_explorer()` | ui/data_explorer.py | 2762 |
| `/verticals` | inline | ui/verticals_page.py | 2764 |
| `/models/causal/<id>` | `_route_model_causal()` | ui/models_page.py | 2753 |
| `/models/counterfactual/<id>` | `_route_model_counterfactual()` | ui/models_page.py | 2756 |
| `/models/predicted/<id>` | `_route_model_predicted()` | ui/models_page.py | 2759 |
| `/models/questions/<id>` | `_route_model_questions()` | ui/models_page.py | 2770 |
| `/models/playbook/<id>` | `_route_model_playbook()` | ui/models_page.py | 2773 |
| `/models/waterfall/<id>` | `_route_model_waterfall()` | ui/waterfall_page.py | 2776 |
| `/models/bridge/<id>` | `_route_model_bridge()` | ui/models_page.py | 2779 |
| `/models/comparables/<id>` | `_route_model_comparables()` | ui/models_page.py | 2782 |
| `/models/anomalies/<id>` | `_route_model_anomalies()` | ui/models_page.py | 2785 |
| `/models/service-lines/<id>` | `_route_model_service_lines()` | ui/models_page.py | 2788 |
| `/models/memo/<id>` | `_route_model_memo()` | ui/models_page.py | 2791 |
| `/models/validate/<id>` | `_route_model_validate()` | ui/models_page.py | 2794 |
| `/models/completeness/<id>` | `_route_model_completeness()` | ui/models_page.py | 2797 |
| `/models/returns/<id>` | `_route_model_returns()` | ui/models_page.py | 2800 |
| `/models/debt/<id>` | `_route_model_debt()` | ui/models_page.py | 2803 |
| `/models/challenge/<id>` | `_route_model_challenge()` | ui/models_page.py | 2806 |
| `/models/irs990/<id>` | `_route_model_irs990()` | ui/models_page.py | 2809 |
| `/models/trends/<id>` | `_route_model_trends()` | ui/models_page.py | 2812 |
| `/models/denial/<id>` | `_route_model_denial()` | ui/models_page.py | 2815 |
| `/models/market/<id>` | `_route_model_market()` | ui/models_page.py | 2818 |
| `/new-deal` | `_route_wizard_get()` | ui/models_page.py | 2821 |
| `/hospital/<ccn>` | `_route_hospital_profile()` | ui/hospital_profile.py | 2831 |
| `/hospital/<ccn>/demand` | `_route_hospital_demand()` | ui/demand_page.py | 2823 |
| `/hospital/<ccn>/history` | `_route_hospital_history()` | ui/hospital_history.py | 2826 |
| `/news` | `_route_news_page()` | ui/news_page.py | 2834 |
| `/conferences` | `_route_conference_page()` | ui/conference_page.py | 2836 |
| `/ml-insights` | `_route_ml_insights()` | ui/ml_insights_page.py | 2838 |
| `/ml-insights/hospital/<ccn>` | `_route_hospital_ml()` | ui/ml_insights_page.py | 2840 |
| `/quant-lab` | `_route_quant_lab()` | ui/quant_lab_page.py | 2843 |
| `/data-intelligence` | `_route_data_intelligence()` | ui/data_dashboard.py | 2845 |
| `/predictive-screener` | `_route_predictive_screener()` | ui/predictive_screener.py | 2847 |
| `/data-room/<ccn>` | `_route_data_room()` | ui/data_room_page.py | 2849 |
| `/competitive-intel/<ccn>` | `_route_competitive_intel()` | ui/competitive_intel_page.py | 2852 |
| `/export/bridge/<ccn>` | `_route_export_bridge()` | ui/models_page.py | 2855 |
| `/value-tracker/<id>` | `_route_value_tracker()` | ui/value_tracking_page.py | 2858 |
| `/ebitda-bridge/<ccn>` | `_route_ebitda_bridge()` | ui/ebitda_bridge_page.py | 2861 |
| `/scenarios/<ccn>` | `_route_scenario_modeler()` | ui/scenario_modeler_page.py | 2864 |
| `/model-validation` | `_route_model_validation()` | ui/model_validation_page.py | 2867 |
| `/ic-memo/<ccn>` | `_route_ic_memo()` | ui/ic_memo_page.py | 2869 |
| `/bayesian/hospital/<ccn>` | `_route_bayesian_profile()` | ui/bayesian_page.py | 2872 |
| `/market-data/map` | `_route_market_data_page()` | ui/market_data_page.py | 2875 |
| `/market-data/state/<st>` | `_route_market_data_state()` | ui/market_data_page.py | 2877 |
| `/source` | inline | ui/source_page.py | 2959 |
| `/settings/<sub>` | `_route_settings_subpage()` | ui/settings_pages.py | 2969 |
| `/hold/<id>` | inline | ui/hold_dashboard.py | 2972 |
| `/deal/<id>/timeline` | `_route_deal_timeline()` | ui/deal_timeline.py | 2982 |
| `/screen` | `_route_screener_page()` | ui/analytics_pages.py | 2989 |
| `/portfolio/monte-carlo` | `_route_portfolio_mc()` | ui/portfolio_monitor_page.py | 2991 |
| `/portfolio/map` | `_route_portfolio_map()` | ui/portfolio_map.py | 2993 |
| `/portfolio/heatmap` | `_route_heatmap()` | ui/portfolio_heatmap.py | 2995 |

### A.3 Non-page routes (25)

Not subject to theme consistency — JSON APIs, redirects, file downloads,
inline Swagger:

- **301 redirect:** `/deals-library` → `/library` (server.py:1808-1818)
- **JSON APIs:** `/api/corpus` (2462), `/api/screener/run` (2938),
  `/api/screener/predefined` (2940), `/api/market-pulse` (2946),
  `/api/insights` (2950), `/api/search` (3011), `/api/openapi.json` (3001),
  `/api/portfolio/attribution` (3026), `/api/deals/search` (3032),
  `/api/deals/stats` (3079), `/api/portfolio/health` (3097),
  `/api/portfolio/alerts` (3117), `/api/portfolio/regression` (3141),
  `/api/portfolio/matrix` (3151), `/api/portfolio/summary` (3181),
  `/api/automations` (3247), `/api/metrics/custom` (3261),
  `/api/webhooks/test` (3266), plus all POST /api/* endpoints
- **File downloads:** `/api/backup` (3201) — SQLite file,
  `/api/export/portfolio.csv` (3231) — CSV
- **Inline HTML:** `/api/docs` (2998) — Swagger UI
- **Auth pages:** `/login` (3456), `/logout`, `/users`, `/audit`
  render via dedicated `_route_*_page()` methods; they inherit shell-v2
  styling inconsistently. Tracked but out of scope for this branch.

---

## B. Visual style diff — `shell_v2` vs `chartis_shell`

The two shells don't share CSS variables, nav structure, or topbar
pattern. Values pulled directly from the module sources:
[_chartis_kit.py:33-48](../rcm_mc/ui/_chartis_kit.py) and
[brand.py:38-70](../rcm_mc/ui/brand.py).

### B.1 Palette

| Purpose | `shell_v2` (brand.PALETTE) | `chartis_shell` (_chartis_kit.P) | Difference |
|---|---|---|---|
| Background | `#05070b` | `#0a0e17` | shell_v2 is noticeably darker — the shift is visible on white display calibration |
| Panel / card | `#0b0f16` | `#111827` | chartis panels are lighter, show more contrast |
| Border | `#1c2430` | `#1e293b` | barely different, imperceptible |
| Text primary | `#e6edf5` | `#e2e8f0` | both off-white |
| Text secondary | `#9aa7b8` | `#94a3b8` | same |
| Text muted | `#5f6b7c` | `#64748b` | same |
| Link / accent | `#5b9bd5` (blue-grey) | `#3b82f6` (true blue) | chartis is markedly bluer |
| Action / highlight | `#e8a33d` (amber) | `#3b82f6` (blue) | **BIG difference** — amber on shell_v2, blue on chartis |
| Positive | `#22c55e` | `#10b981` | same shade family |
| Negative | `#ef4444` | `#ef4444` | identical |
| Warning | `#f59e0b` | `#f59e0b` | identical |

### B.2 Typography + layout

| Property | `shell_v2` | `chartis_shell` |
|---|---|---|
| Font-sans | Inter + SF stack | Inter + SF stack (same) |
| Font-mono | JetBrains Mono (same) | JetBrains Mono (same) |
| Base font size | 12.5px | 12px |
| Line height | 1.5 | 1.45 |
| Container mode | `overflow: hidden; height: 100vh` (fixed viewport) | scrollable `<main>` |
| Nav width | 216px | 200px |
| Top bar height | 44px | 36px |
| Has ticker bar | yes (26px, fixed second row) | no |
| Has status bar | yes (22px, fixed bottom) | no |
| Has F-key nav | yes | no |
| Has live indicator | yes (pulsing green dot) | no |
| Nav items | ~25 curated by NAV_ITEMS (brand.py:72-130) | ~150 in _CORPUS_NAV (_chartis_kit.py:57+) |
| Left nav style | Bloomberg (active item amber left-border) | institutional (active item blue left-border) |

### B.3 Chrome elements

| Element | `shell_v2` | `chartis_shell` |
|---|---|---|
| Top bar content | logo + version + F-keys + search + live + right icons | logo + section label + title + UTC time |
| Top bar background | linear gradient `#0d1320 → #0b0f16` | flat `#111827` |
| Ticker bar | present — animated ticker with market pulse data | absent |
| Search input | prominent (420px wide, uppercase) | absent |
| Page header styling | via `.cad-page-header` class | via `.ck-page-header` class |
| Cards | `.cad-card` (radius 6, border 1px, padding 14-18) | `.ck-panel` (radius 3, border 1px, padding 12-14) |
| KPI tiles | `.cad-kpi-grid` / `.cad-kpi` | `.ck-kpi-grid` / `.ck-kpi` |
| Tables | `.cad-table` | `.ck-table` |
| Badges | `.cad-badge-*` classes | `.ck-sig` / `.ck-grade` classes |

**Net effect of clicking between the two:** everything moves.
Background shade shifts, ticker bar disappears/reappears, nav changes
from 25 items to 150, accent flips amber↔blue, top bar re-layouts,
card border-radius changes. This is the "flicker" the user noticed.

---

## C. Migration difficulty estimate

The 56 `shell_v2` pages fall into three migration buckets. Classification is
based on whether the page just wraps a body string in `shell_v2(...)`
(trivial) or whether its body HTML references `.cad-*` CSS classes that
don't exist on chartis (moderate), or whether its entire logic depends on
shell_v2's layout primitives like ticker / F-keys / sticky overflow
(heavy).

### C.1 Trivial (20 pages)

Import `shell_v2`, call it once with a body string that uses only inline
styles or generic HTML tags (no `.cad-*` classes). Migration = change the
import to `chartis_shell` and add `active_nav=<path>`.

- ui/hold_dashboard.py
- ui/source_page.py
- ui/verticals_page.py
- ui/quick_import.py
- ui/data_explorer.py
- ui/data_room_page.py
- ui/news_page.py
- ui/conference_page.py
- ui/competitive_intel_page.py
- ui/demand_page.py
- ui/hospital_history.py
- ui/market_data_page.py
- ui/bayesian_page.py
- ui/ic_memo_page.py
- ui/scenario_modeler_page.py
- ui/value_tracking_page.py
- ui/settings_pages.py (minor — has forms)
- ui/deal_timeline.py
- ui/waterfall_page.py
- ui/ebitda_bridge_page.py

### C.2 Moderate (25 pages)

Page body HTML directly references `.cad-card`, `.cad-kpi`,
`.cad-section-code`, `.cad-btn`, or `.cad-badge-*` class names. Migrating
means either (a) aliasing those class names so both kits expose them, or
(b) doing a find/replace `cad-kpi → ck-kpi`, `cad-card → ck-panel`,
`cad-btn → ck-btn`, etc. Option (a) is less churn; option (b) is cleaner.

- ui/hospital_profile.py — uses `.cad-kpi`, `.cad-card`, `.cad-badge-*`
- ui/models_page.py (drives ~20 `/models/<kind>/<id>` routes) — uses
  `.cad-card`, `.cad-section-code`, `.cad-kpi-grid`
- ui/ml_insights_page.py
- ui/quant_lab_page.py
- ui/data_dashboard.py
- ui/predictive_screener.py
- ui/model_validation_page.py
- ui/analytics_pages.py (`/screen`)
- ui/portfolio_monitor_page.py
- ui/portfolio_map.py
- ui/portfolio_heatmap.py
- ui/home_v2.py (dashboard at `/`)
- ui/library_page.py (methodology hub at `/methodology`)
- ui/methodology_page.py (calculations at `/methodology/calculations`)
- ui/deal_dashboard.py — uses `.cad-card`, `.cad-btn-primary`,
  `.cad-kpi-grid`, `.cad-section-code` heavily
- ui/deal_quick_view.py
- ui/analysis_landing.py
- ui/analysis_workbench.py
- ui/command_center.py
- ui/pe_tools_page.py
- ui/pe_returns_page.py
- ui/memo_page.py
- ui/dashboard_v2.py
- ui/fund_learning_page.py
- ui/pipeline_page.py

### C.3 Heavy (11 pages)

These pages build chrome or depend on shell_v2-specific behaviours
(ticker, F-keys, collapsible nav, status bar). Migrating them breaks the
feature set or requires adding those behaviours to chartis_shell first.

- **ui/shell_v2.py itself** — obviously stays; either delete or rewrite.
- **ui/home_v2.py** — dashboard at `/`. Has the ticker and live indicator.
  Migrating loses both unless we add them to chartis.
- **ui/command_center.py** — secondary home with HCRIS integration and
  quick-screen buttons. Several shell_v2-layout assumptions.
- **ui/deal_dashboard.py** — the 17-tile grid at `/deal/<id>`. Tile CSS
  is shell_v2-specific and tightly coupled to `.cad-modelgrid`.
- **ui/analysis_workbench.py** — the Bloomberg-style workbench at
  `/analysis/<id>`. The entire layout is shell_v2-driven; 500+ lines
  of inline HTML that references `.cad-*` class names.
- **ui/pipeline_page.py** — pipeline funnel view. Uses shell_v2 nav
  + ticker integration.
- **ui/team_page.py** — `/team` — similar to pipeline.
- **ui/portfolio_overview.py** — `/portfolio` main view.
- **ui/hospital_profile.py** — has a dense multi-panel layout that
  assumes shell_v2's overflow:hidden + height:100vh container.
- **ui/settings_pages.py** — has forms that depend on shell_v2's CSRF
  injection + form styling.
- **ui/auth_pages.py / login.py** — login page styling.

### C.4 Stay-light / stay-shell_v2 candidates

Argued by use-case, not brand. None of these are strong holds.

- **`/` dashboard** — one could argue the ticker belongs on the daily-use
  page and shouldn't move to chartis until chartis grows a ticker. Weak
  argument — the ticker is cosmetic; portfolio-health + alerts already
  exist on `/home`.
- **Auth pages** — login/logout could stay shell_v2 because CSRF wiring is
  entangled. But they're a handful of pages; porting is a day of work.

**No page should stay shell_v2 for ever.** The right path is migrate all 56.

---

## D. Recommendation

### D.1 Unify on `chartis_shell`. Confirm.

The user's default reading ("unify everything on _chartis_kit") is the
right call. Reasons:

1. **Already where most pages are.** 191 of 247 page routes (77%) already
   use chartis_shell. Migration direction therefore minimizes churn.
2. **Newer and more disciplined.** `_chartis_kit.py` was written as the
   Phase 1 data-public polish; its CSS is 600 lines vs shell_v2's 1,200.
   Fewer assumptions to carry forward.
3. **Phase 2A-2C doubled down.** Every P0/P1/P1-portfolio page we just
   wired uses chartis. A migration to shell_v2 would undo that work.
4. **Partner-brief colour system.** chartis' blue accent `#3b82f6`
   matches the SeekingChartis brand blue (`#1F4E78` at 70% lightness);
   shell_v2's amber is Bloomberg-inherited and doesn't map to the brand.
5. **Simpler mental model for new pages.** One shell, one nav, one CSS
   var prefix. Removes the "which kit should I use?" question.

### D.2 What we lose migrating shell_v2 → chartis

- **Ticker bar** — animated market-pulse ribbon at the top. Nice-to-
  have, not load-bearing. Can be rebuilt as a chartis component later
  if the dashboard misses it.
- **F-key global shortcuts** — `F1 Help` / `F2 Search` / etc. Little-used
  but quick wins. Port the JS as-is; the CSS follows the theme swap.
- **Collapsible left nav** — chartis sidebar is always-open. 150+ items
  is a lot for always-open. **Biggest concrete loss.** Solution: nav
  consolidation in Phase 5 of the polish brief drops the sidebar to
  three groups with ≤30 items. After consolidation, always-open is fine.
- **Status bar** — the thin green stripe at the bottom. Cosmetic.

### D.3 What we gain

- **Single dark shade.** No flicker when clicking between pages.
- **One accent colour.** Blue throughout. Partners form a consistent
  expectation.
- **One nav structure.** After the Phase 5 consolidation, three groups
  with clear semantics (platform / analytics / reference).
- **Smaller CSS bundle on each page.** shell_v2 emits 1,200 lines of CSS
  per render; chartis emits 600. Noticeable on low-end laptops.

### D.4 Execution order (for Phase 2 when approved)

1. **Preserve top-bar features** in chartis (if we want them): port the
   F-key bar, live indicator, search field into `chartis_shell`. Optional.
2. **Class-alias pass.** Add `.cad-card { @apply .ck-panel }`-equivalent
   rules to `_chartis_kit.BASE_CSS` so existing shell_v2 pages don't break
   mid-migration. Cost: ~30 CSS lines. Temporary — removed after all pages
   ported.
3. **Trivial pages first.** 20 pages, batch of ~5 per commit. Swap imports,
   add `active_nav`, ship.
4. **Moderate pages.** 25 pages. Either port class names via find/replace,
   or keep the aliases in place permanently.
5. **Heavy pages last.** 11 pages. Case-by-case. Dashboard may get a
   chartis-ticker component; workbench gets a dedicated refactor.
6. **Delete shell_v2.py + brand.py** once the last import is gone.

Rough effort: 20 trivial × 10 min + 25 moderate × 25 min + 11 heavy × 90 min
≈ 20 hours of engineering. Can ship in chunks; no big-bang cutover.

---

## Appendix: bucket counts (final)

```
chartis-dark (chartis_shell) ........................ 191 routes
shell-v2-dark (shell_v2) ............................. 56 routes
non-page (JSON / file / redirect / inline) ........... 25 routes
────────────────────────────────────────────────────────────────
Total ............................................... 272 routes
```

No pages render the legacy light palette today — `_ui_kit.shell()` at
`_ui_kit.py:386` delegates to `shell_v2()` so the light BASE_CSS is dead
code. Zero routes to migrate from light.

---

## Appendix: shell_v2 features inventory

Phase-2 pre-work. Every behaviour/feature `shell_v2` renders that
`chartis_shell` does not. Each row is classified as **KEEP** (must
port), **REPLACE** (similar idea, different implementation), or
**DROP** (cosmetic / fake / not load-bearing).

### Feature-by-feature

| # | Feature | Location (file:line) | What it actually does | Classification |
|---|---|---|---|---|
| 1 | **Ticker bar** | [shell_v2.py:752-769](../rcm_mc/ui/shell_v2.py#L752) | Hardcoded strip of fake market data — HCA +0.34%, THC -0.89%, UHS +1.12%, CYH -0.21%, 10Y TSY 4.23%, HOSP MULT 11.2x, S&P HC +0.18%, SENT 0.62. The docstring says "Static placeholder ticker — replaced by live data when available" but **no backend / polling / data source exists**. The numbers never update. | **DROP** — cosmetic fake data. Worse than neutral: partners trusting "live" ticker values would be misled. |
| 2 | **F-key nav row** | [shell_v2.py:772-787](../rcm_mc/ui/shell_v2.py#L772) | Five styled hyperlinks in the topbar: H=Home, A=Analysis, P=Portfolio, S=Screen, M=Market. Each is a plain `<a>`; the `title="g+<k>"` tooltip is purely informational. | **DROP** — the visual chrome is duplicative of the sidebar. The *keyboard shortcut* behind them (vim-style `g+<key>`) is a separate feature — see row 5. |
| 3 | **Live indicator** | [shell_v2.py:1022-1023](../rcm_mc/ui/shell_v2.py#L1022), CSS [179-187](../rcm_mc/ui/shell_v2.py#L179) | Pulsing green dot + "LIVE" label next to the topbar. Title attr says "Live market data feed". **Never changes state**. No backend check, no WebSocket, no poll. Always on. | **DROP** — cosmetic lie. Worse than neutral for the same reason as the ticker. |
| 4 | **Cmd+K command palette** | [shell_v2.py:839-884](../rcm_mc/ui/shell_v2.py#L839) (HTML), [1154-1201](../rcm_mc/ui/shell_v2.py#L1154) (JS) | Working modal palette — 20 curated shortcuts grouped NAV / ANL / REF. Cmd+K (or Ctrl+K) toggles; Esc closes. Fuzzy match as you type. ↑↓ navigate, Enter opens. | **KEEP** — genuinely useful power-user feature. ~80 lines of JS + HTML + 60 lines of CSS. |
| 5 | **Vim-style kb shortcuts** | [shell_v2.py:1115-1152](../rcm_mc/ui/shell_v2.py#L1115) | `?` opens a help modal; `/` focuses search; `g h` = /home, `g a` = /analysis, `g m` = /market-data/map, `g n` = /news, `g p` = /portfolio, `g r` = /portfolio/regression, `g s` = /screen, `g l` = /library, `g i` = /import, `g d` = /api/docs. | **KEEP** — useful, small (~35 lines of JS), partners who use them will miss them otherwise. |
| 6 | **Alert badge polling** | [shell_v2.py:989-996](../rcm_mc/ui/shell_v2.py#L989) | On page load, GETs `/api/alerts/active-count`, and if `{count > 0}` shows a red pill with the count on the alerts icon in the topbar. | **KEEP (critical)** — actual backend integration; partners lose alert visibility on chartis without it. ~8 lines. |
| 7 | **CSRF token patcher** | [shell_v2.py:968-987](../rcm_mc/ui/shell_v2.py#L968) | Reads the `rcm_csrf` cookie on every page load and (a) injects a hidden `csrf_token` input into every POST form before submit, (b) sets the `X-CSRF-Token` header on every non-GET `fetch()` call. | **KEEP (critical)** — security. Any chartis page that hosts a POST form (screener, deal wizard, settings) will have CSRF-blocked submissions without this. ~20 lines. |
| 8 | **Status bar (bottom)** | [shell_v2.py:887-919](../rcm_mc/ui/shell_v2.py#L887), JS clock [1062-1072](../rcm_mc/ui/shell_v2.py#L1062) | Fixed footer showing: SESSION=ACTIVE, DATA=HCRIS FY2022, HOSPITALS=6,123, MODELS=17, LATENCY (from `performance.timing`), UTC clock (live, setInterval 1s), BUILD=v1.0. All values except LATENCY and UTC are **hardcoded constants**. | **DROP** — four of the six fields are hardcoded-and-misleading (e.g., MODELS=17 is a 2024 figure). UTC clock and latency are nice-to-have; ship without them. |
| 9 | **Search input w/ dropdown** | [shell_v2.py:1018-1020](../rcm_mc/ui/shell_v2.py#L1018), JS ~1073+ | Topbar search `<input>` with a live dropdown that fetches `/api/search?q=` as you type, shows top matches grouped by deal/hospital/ticker. Submits to `/search` on Enter. | **REPLACE** — backend `/api/search` already exists. Chartis can host a simpler search link (or a simpler input without dropdown) without material user cost. Nice-to-have. |
| 10 | **216px vs 200px nav width** | [brand.py:40](../rcm_mc/ui/brand.py) vs [_chartis_kit.py:257](../rcm_mc/ui/_chartis_kit.py#L257) | shell_v2 has NAV_ITEMS (~25 curated entries) rendered at 216px. chartis has _CORPUS_NAV (~150 entries) rendered at 200px. Width isn't the useful difference; the *curation* is. | **DROP (or Phase 5)** — width is cosmetic. The 150-item sidebar is the real friction; Phase 5's nav consolidation fixes that independently. |

### Summary counts

- **KEEP** (4): Cmd+K palette (4), vim-style shortcuts (5), alert-badge poll (6), CSRF patcher (7). Total ≈ **145 lines of JS + CSS** to port.
- **REPLACE** (1): search-with-dropdown (9) — optional polish.
- **DROP** (5): ticker bar (1), F-key visual row (2), live indicator (3), status bar (8), nav-width (10).

### Port plan for KEEP items

The four KEEP items should be added to `_chartis_kit.chartis_shell()` as a
single patch before Wave 1 migrations begin. Scope per item:

- **CSRF patcher** — 20 lines of JS. Straight copy-paste from
  `shell_v2.py:968-987` into a helper that `chartis_shell` appends to
  its `<script>` tag. No HTML changes.
- **Alert badge poll** — 8 lines of JS + an icon slot in the topbar.
  Topbar is already built in `chartis_shell`; add a single bell icon
  with `id="ck-alert-count"`. Copy the poll JS.
- **Vim-style shortcuts** — 35 lines of JS + the `?` help modal HTML.
  No changes to page body. Ship the help modal as an always-loaded
  hidden `<div>`.
- **Cmd+K palette** — 80 lines JS + 60 lines CSS + the 20-entry catalog.
  The catalog should live in `_chartis_kit.py` alongside `_CORPUS_NAV`
  so updates flow through both. Biggest single piece; still < 2 hours.

Total port cost ≈ **4 hours** of focused work. After the port,
`chartis_shell` is a strict superset of `shell_v2`'s actual behaviour
(minus the three DROP-classified cosmetic lies).

### Recommendation

**Port all four KEEP items into `chartis_shell` first** as a single
"feat: port shell_v2 KEEP features into chartis_shell" commit. Then run
Waves 1-3 against a chartis that's feature-parity with shell_v2 on
everything load-bearing. No partner loses functionality in the migration.

If the decision is "skip the port, accept the loss":
- CSRF patcher loss is a **bug** — any chartis page with a form will break.
  Must port regardless.
- Alert badge loss is a **UX regression** — partners lose at-a-glance
  alert count across all 56 migrated pages. Should port.
- Cmd+K + vim shortcuts are power-user features — *could* be dropped if
  no one uses them, but we haven't measured.

The CSRF and alert-badge ports are non-negotiable. The palette and
shortcuts are a judgment call but cheap.

---

## Appendix: bugs / dead code discovered during migration

Items discovered while performing Waves 1-3 that weren't fixed in the
migration commits (per the "don't fix bugs in migration commits" rule).

1. **Four test files tested dead features.** Deleted them in the
   cleanup phase because their subject-under-test no longer exists:

   - `tests/test_caduceus_brand.py` — tested shell_v2 rendering,
     NAV_ITEMS catalog, and brand-palette Bloomberg hex values. All
     three subjects were deleted.
   - `tests/test_improvements_b87.py` — tested the light-theme
     `prefers-color-scheme: dark` media query inside the legacy
     `_ui_kit.BASE_CSS`. That BASE_CSS was dead code (never reached
     any route — `_ui_kit.shell()` delegated to shell_v2).
   - `tests/test_improvements_b93.py` — tested a workbench tab-switch
     keyboard JS block and a toast-notification CSS class in the
     legacy BASE_CSS. The tab-switch JS was inside shell_v2; the
     toast CSS was inside BASE_CSS. Both gone.
   - `tests/test_ui_kit.py` — tested the shared light-theme UI kit
     (BASE_CSS constants + PALETTE). Both constants removed.

   These weren't "broken tests worth fixing" — they were testing code
   that shouldn't exist after the migration. Deletion is the right
   call. Any test that still tests shell behaviour should be written
   against `chartis_shell` fresh.

2. **`brand.PALETTE` is still imported by ~35 pages** for colour
   literals in their body HTML (hex codes from the Bloomberg shade,
   not chartis). This isn't a bug — pages render correctly via the
   `_CAD_COMPAT_CSS` layer that maps class names onto chartis vars —
   but the imports are a lingering artefact of the shell_v2 era.
   Deferred: a clean-up pass could rewrite every
   `background: {PALETTE['bg_secondary']}` literal to
   `background: var(--ck-panel)` and drop the brand.PALETTE import
   entirely. Outside this phase's scope.

3. **No actual runtime bugs surfaced.** Every migrated page renders
   200 on HTTP smoke; the 33-test chartis integration suite stays
   green through every wave.

4. **`/` legacy dashboard stays on its own standalone HTML.** The
   `/` route falls through to `rcm_mc/portfolio/portfolio_dashboard.py`
   when the store has zero analysis packets and the user doesn't
   pass `?v2=1`. That module builds its own `<!DOCTYPE>` + `<style>`
   via `build_portfolio_dashboard()` and is **also called from the
   CLI** (writes an HTML file to disk). Wrapping it in
   `chartis_shell` would break the CLI output path. Pragmatic
   decision: leave it standalone; users with packets (the common
   path) render through `dashboard_v2` which IS on chartis (migrated
   in Wave 3). A future follow-up could split the builder into a
   "body-only" helper + two separate wrappers (CLI file-writer +
   HTTP chartis-shell) but that's out of scope here.

5. **`brand.PALETTE` lingering imports** (also noted in item 2
   above). Worth re-emphasising: ~35 pages still `from .brand import
   PALETTE` for hex literals inside their body HTML. Those render
   correctly via the `_CAD_COMPAT_CSS` alias layer, but the imports
   aren't dead code — the pages still use those hex values. Removing
   them requires a rewrite of each page's body HTML to use
   `var(--ck-*)` CSS vars instead. Deferred.

---

## Appendix: numerical bugs surfaced by sanity guards

> **Phase 6 status (2026-04-18):** All 3 P0 bugs (#1, #2, #4) fixed in
> the `chore/ui-polish-and-sanity-guards` branch. Proactive integrity
> scan added in Phase 6C caught 7 additional IRR/MOIC math-
> consistency bugs in hand-crafted loss rows; all 7 fixed in a single
> systematic recompute commit. False-positive benchmarks (#6, #7)
> addressed by widening the registry bands + adding TODO for
> subsector-aware guards. P1 bugs (#3, #5, #8) deferred — see status
> notes on each entry below.



Phase 4B migration log. As every chartis page is wrapped with
`render_number()`, implausible values that were being silently
rendered by the old unguarded formatters now show up as red warning
pills. Each such pill is a numerical bug that needs a backend fix —
but per the Phase 4 rule ("do not fix bugs in the migration commits"),
they're logged here for a separate bug-fix pass. This appendix is
the Phase 6 backlog.

Format per bug:
- **Route**: page/route where the implausible value appeared.
- **Metric · Value**: which metric, and the value we saw.
- **Likely source**: backend module computing it (best guess).
- **Severity**: P0 = partner would see on demo; P1 = edge case.
- **Observed during**: which migration commit surfaced it.

### Bugs

1. **[FIXED in commit e02eadf] /sponsor-track-record · Cvs Health · median_irr 60%** — IRR tooltip
   says "expected range -30.0%–55.0% for irr." Value is 60%. 6 deals
   in the underlying set, so not a rogue single-deal. Likely source:
   `data_public/sponsor_track_record.py:sponsor_league_table()`
   computes per-sponsor median IRR by aggregating `realized_irr` from
   corpus deals — some corpus CVS Health deals may have inflated IRR
   values. Needs spot-check of the seed-deal IRR field per row.
   **Severity: P0** — CVS is a headline sponsor that partners look
   at on demo. Observed during: Phase 4B Phase 2C sponsor-track-record
   guard commit.

2. **[FIXED in commit 59614c2] /sponsor-track-record · Walgreens · median_irr 78%** — same
   category. 78% IRR on a 2-deal sponsor is implausible. Almost
   certainly a single corpus deal with an absurd realized_irr in the
   seed data (not a rollup; 2 deals only). Likely the `realized_irr`
   field was recorded as percentage (78) instead of fraction (0.78)
   on one deal — classic unit mixup. **Severity: P0**. Observed during:
   same commit as #1.

3. **[DEFERRED P1] /sponsor-track-record · Various Pe (Series D) · median_irr 65%**
   — 2 deals. Same shape as Walgreens — likely unit-mixup on one
   corpus entry. **Severity: P1** (obscure sponsor name, less visible
   on demos). Same commit.

4. **[FIXED in commit 0b1e97d] /sponsor-track-record · Advent International · median_irr -38%**
   — 7 deals, median is -38%. One of the largest PE firms. The
   realized_irr lower bound in reasonableness.py is 0.0 per band;
   our registry widened to -30% to tolerate genuine losses. A
   sustained -38% median on 7 deals is either real (Advent had a
   string of catastrophes in the seed data) or a data-entry bug with
   sign flips. **Severity: P0** — Advent is a headline name.
   Investigate the 7 corpus rows.

5. **[DEFERRED P1 — verified as real] /sponsor-track-record · Cerberus ·
   median_moic 0.2x, hold 14 years** — 2 deals. Phase 6 investigation
   confirmed this is real data, not a bug: seed_356 is the Steward
   Health Care / Cerberus LBO (2010 entry → 2024 Ch.11 filing →
   14y hold, ~0.4x realized). Steward's collapse is a documented
   healthcare-PE case study; the 14y "hold" reflects the actual
   2010-2024 stewardship before bankruptcy. The IRR was
   recomputed to -6% in the Phase 6C integrity sweep (commit
   315afef). The MOIC/hold warnings remain because the values ARE
   at the edge of plausibility — the guard working as designed.

### Registry fix (not a bug — a definition error in _sanity.py)

While migrating sponsor-track-record, the `consistency_score` guard
fired on 88 of ~101 sponsors — too broad to be real. Root cause was
a **registry mismatch**: I had set `consistency_score` to range
[0.0, 1.0] with unit=pct, but the backend function
`sponsor_track_record.sponsor_consistency_score_raw()` returns a
0-100 integer. Fixed the registry entry to `plausible_min=0.0,
plausible_max=100.0, unit=UNIT_NUM`. Not a bug — a correctness fix
to _sanity.py itself.

### False positives — benchmarks that legitimately exceed the band

Not every red pill is a backend bug. When the benchmark itself is
wider than the acute-hospital band we calibrated on, the guard
fires on valid data. These are worth noting so the fix path is
"widen the range with a second citation" rather than "investigate
the data":

6. **[FIXED via widening in commit da989cb] /rcm-benchmarks · behavioral segment · denial_rate P75 = 32%**
   — my registry max is 30% (HFMA MAP 2024 acute-hospital band).
   Behavioral-health denial rates legitimately run 25-35% because
   of prior-auth friction on inpatient-psych + Medicaid-eligibility
   lapses. The guard fires but the value is real. **Severity: N/A
   (false positive)**. Follow-up: add a behavioral-health-specific
   band to the registry or widen denial_rate to 35%.

7. **[FIXED via widening in commit da989cb] /rcm-benchmarks · behavioral · write_off_pct P75 = 16%** —
   my registry max is 15%. Same story — behavioral segment has
   structurally higher bad-debt ratios (Medicaid eligibility churn).
   False positive; same fix as #6.

### Corpus-realized MOIC outliers — real data, surfaced correctly

8. **/corpus-backtest · 10 MOIC pills across vintages + sectors**
   — the 655-deal corpus has legitimate outliers: 12.5x on a 2011
   dental rollup, 9.0x on a 2021 health-IT exit, multiple 0.0-0.2x
   catastrophic losses. My registry band is 0.3–6.0x (Preqin HC-PE
   exit distribution). These aren't bugs — they're the tails. The
   partner seeing these red pills and going "is this real?" is
   exactly the intended behaviour: they can then verify against the
   corpus row. **Severity: N/A (working as designed)**.

   However: 2018 vintage has a MOIC of 0.05 (5% of invested capital)
   on what the corpus labels "realized" — that's either a total
   write-off or a sign-flip / unit bug. Worth a spot-check of the
   specific corpus row. **Severity: P1** — obscure vintage, but
   could indicate a data-entry error rather than a real tail event.

   **[VERIFIED as real in Phase 6C — not a bug]** The 2018-vintage
   0.05x MOIC row is `seed_007` (KKR / Envision Healthcare $9.9B
   take-private, destroyed by No Surprises Act + COVID, Ch.11 filed
   May 2023). This is a documented healthcare-PE disaster; 0.05x
   reflects the genuine equity-wipe outcome. The guard is working
   as designed. Phase 6C also recomputed IRR on similar loss rows
   to keep the IRR/MOIC/hold math self-consistent.

---

### Phase 6C — IRR/MOIC math-consistency sweep

The proactive integrity scan ([tests/test_corpus_data_integrity.py])
caught 7 hand-crafted loss rows where `realized_irr` and
`realized_moic` were entered independently and didn't compound
properly over the stated hold. All fixed in commit `315afef` by
recomputing IRR as `MOIC^(1/hold) − 1` (MOIC is the hard fact —
dollars returned per dollar in — so IRR harmonizes to it):

| Row      | Deal                                      | MOIC | Hold | IRR before | IRR after |
|----------|-------------------------------------------|------|------|------------|-----------|
| seed_123 | Cano Health SPAC                          | 0.05 | 2.5y | -0.45      | -0.70     |
| seed_131 | Prospect Medical CA distressed            | 0.10 | 8.0y | -0.32      | -0.25     |
| seed_171 | Bright Health IPO / NEA exit              | 0.02 | 2.0y | -0.55      | -0.86     |
| seed_356 | Steward Health Care / Cerberus LBO        | 0.40 | 14y  | -0.12      | -0.06     |
| seed_369 | Smile Direct Club / CD&R                  | 0.05 | 5.0y | -0.60      | -0.45     |
| seed_380 | Bright Health / NEA growth                | 0.10 | 6.0y | -0.40      | -0.32     |
| seed_395 | Vitas Healthcare / Chemed                 | 5.80 | 12y  | +0.25      | +0.16     |
