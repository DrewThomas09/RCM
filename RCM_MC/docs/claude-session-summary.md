# PE Desk — Claude Deep-Work Session Summary

_Session date: 2026-05-26. Autonomous multi-PR sprint. All changes shipped via
PR behind green CI (3.11/3.12/3.14) and auto-deployed to https://pedesk.app._

## Stack (confirmed by inspection — NOT the TS/Next stack the generic prompt assumed)

- **Python 3.10+**, stdlib-heavy. Runtime deps beyond stdlib: pandas, numpy,
  matplotlib only. No Flask/FastAPI/ORM/Node.
- **HTTP**: `http.server.ThreadingHTTPServer` in `rcm_mc/server.py`.
- **HTML**: server-rendered string concatenation through one shared editorial
  shell (`rcm_mc/ui/_chartis_kit.py` → `chartis_shell`).
- **DB**: SQLite via `rcm_mc/portfolio/store.py` (only module that talks to it).
- **Tests**: stdlib `unittest` via pytest (~12.4k tests).

## Addendum — 2026-05-27: regression inference/diagnostic suite

A focused sprint making `/portfolio/regression` statistically complete. Every
statistic is implemented from the correct formula in `finance/regression.py`
(reusable + unit-tested), wired into the page's `_run_ols`, and surfaced with a
plain-language verdict. No scipy — exact p-values reuse the incomplete-beta
machinery already present (`f_pvalue`). All behaviorally verified against data
with known properties; all merged behind green CI and deployed.

- **#1021** — HC1 heteroskedasticity-robust (White sandwich) SEs + Breusch–Pagan
  test + AIC/BIC. Coefficient inference now uses robust SEs; BP reports whether
  that mattered.
- **#1022** — Ramsey RESET functional-form test (is the linear shape right?).
- **#1023** — **exact Student-t** coefficient p-values + t-based CIs, replacing
  the normal approximation (`erfc`) and the flat 1.96 multiplier. The legacy
  `_t_dist_cdf_approx` (which ignored df) now delegates to the exact function,
  so `run_regression` is corrected too. Honest at small n (tight universe
  filters), unchanged for large n.
- **#1024** — Jarque–Bera residual-normality test (exact χ²(2) p = exp(−JB/2)).
  Completes the residual trio: BP (variance) / RESET (mean shape) / JB
  (distribution) — the normality JB checks is what validates the small-sample
  t/F inference from #1023.
- **#1025** — Shapley R² driver-importance decomposition (fair, additive split
  of R² across correlated drivers; capped at 8 features, O(2^p)).
- **#1026** — heteroskedasticity-robust joint F-test (HC1 Wald on the slopes,
  F-form). The classical overall F assumed homoskedasticity that BP routinely
  rejects on HCRIS data; this is the valid headline significance test.

Considered but **deliberately not done**: an always-on CV R² (already exists via
`run_cv_regression` behind the "Cross-validate" toggle — would have duplicated
well-built code). Durbin–Watson autocorrelation (meaningless on cross-sectional
data). Full-page render verified: all seven diagnostics appear, no NaN/inf leaks.

## Work completed this session

### 1. Statistical rigor (#960–#962, merged + deployed)
- `survival_analysis`: replaced magic-constant survival curve with a real
  P(margin>0) = Φ(projected_margin / SE) from the OLS prediction interval;
  dropped the false Kaplan-Meier/Cox docstring claim.
- `margin_predictor`: fixed in-sample "split conformal" leak → genuine split
  (train/calibrate disjoint, finite-sample quantile, seeded shuffle).
- `bayesian_calibration`: continuous-metric credible interval now data-anchored
  (CV from the by-type prior spread) instead of a magic 0.15; honest docstrings.
- Verified two audit "critical" flags were **false positives** (Mann-Kendall ±1
  continuity correction and the rank-rectangle AUC are both standard) — left
  untouched. No NN/Markov added (not warranted by the data).

### 2. Regression multicollinearity (#964, merged + deployed)
- `/portfolio/regression` still shipped catastrophic collinearity (maxVIF=999,
  cond#=∞) on non-curated targets because linear VIF can't see nonlinear
  duplicates (`payer_diversity`, `medicare_intensity`). Added structural-family
  dedup (collapse size / dollar / payer families to the most target-correlated
  RAW representative) then VIF-prune at 5. Every target now maxVIF<5, cond#≤26.
- Tables → charts: VIF bar chart with 5/10 threshold zones; univariate diverging
  chart. Each dropped feature explained ("redundant transform of X").

### 3. Top bar (#965, merged + deployed)
- Mega-menu feature blurb no longer floods the destinations column (definite
  panel width + earlier single-column stacking + word-break). Nav links
  flex-centered so text doesn't float high when the bar grows.

### 4. AI migration — Ollama Guide page-context coverage (#963, #966–#972)
- The Guide answers questions per-route from `PageContext` entries
  (`rcm_mc/assistant/context/manual_page_contexts.py`), enriched by the local
  RAG index and answered by local Ollama.
- **Mapped placeholders 144 → 1; documented contexts 200 → 343.** Every served
  route now has an honest, provenance-linked context. Data confidence labeled
  per page: corpus→PUBLIC_BENCHMARK, scenario→MODEL_ESTIMATE, trackers→MIXED/
  USER_ENTERED, per-deal models→MIXED. The 25-route `/models/*` family and all
  data_public analytic tools are covered. (Remaining: `/ebitda-bridge`, an
  unwired alias — the real bridge is `/pipeline/bridge` & `/models/bridge`.)
- Validators (`validate_page_context_coverage`, `validate_guide_context_quality`)
  pass with 0 invalid metric/data-source refs.

## Findings

- **UI is already structurally consistent.** A consistency audit flagged ~300
  modules, but spot-checks showed the hits were thin wrappers, embedded
  components, or dead modules — nearly everything routes through `chartis_shell`
  or `render_insights_page`. A blanket "migrate every page to look like X-Ray /
  Command Center" would be churn, not value. UI work should be surgical
  enrichment of genuinely-thin pages, verified case-by-case.
- **Snapshot ingestion + data quality already exist** — `rcm_mc/diligence/
  ingest/` (ingester, normalize), `parsers/` (X12 835/837 adapters),
  `snapshot.py`, `analysis/completeness.py`, `data_scrub.py`, `surface_status.py`,
  and the `/diligence/snapshot` upload UI. The generic prompt's "build a
  snapshot ingestion framework" is largely done; improve it, don't rebuild it.

### 5. Guide depth — metric/source links + registry expansion (#974–#977)
- Wired real `metric_ids` onto 12 core analytic pages (#974); expanded the
  metric registry **60 → 68** with HHI, CR3/CR5, DSCR, TVPI/DPI/RVPI, CMS
  five-star (NOT_APPLICABLE formula), and days-cash-on-hand, each with a
  textbook formula + honest caveats, and linked them to the pages that use
  them (#975); linked `data_source_ids` on HCRIS / CMS Care Compare / portfolio
  pages (#977, "no data sources" advisory 149 → 6).
- Added an offline context-sufficiency regression guard
  (`tests/test_guide_context_sufficiency.py`, #976) pinning placeholders ≈ 0,
  core routes STRONG, and (route → metric) sufficiency.

### 6. Surgical UI enrichment — geo suite KPI strips (#978–#982)
- The geographic-intelligence suite rendered dense real-data tables but lacked
  the leading KPI strip that defines the X-Ray / Command Center look. Added one
  — computed from the SAME real data, no fabrication — to **State Comparison,
  State Rankings, State Profile, County Explorer, and Metro Markets**. Each has
  a test pinning the strip renders with computed (not hard-coded) values.


### 7. Guide layer fully completed (#986–#989)
After the user asked to "finish all the Ollama work — every page, every metric,
every formula", I closed every remaining gap in the model-surfaced fields:
- **Every metric formula filled** (#986): 41 placeholders → 0 (61 standard
  textbook formulas, 10 NOT_APPLICABLE counts/CMS-composites, 7 proprietary
  scores honestly marked model-driven — no fabrication).
- **Last page context** (#987): /ebitda-bridge (the per-hospital 7-lever RCM
  bridge) documented STRONG → 344/344 pages, 0 placeholders.
- **Every metric caveat filled** (#988): 75 placeholders → 0 (caveats are sent
  to the model verbatim).
- **Every page why_it_matters filled** (#989): 64 placeholders → 0.
- Deliberately left `common_misread` and `model_logic_summary` placeholders:
  verified neither is sent to the model, and they are the honest "unconfirmed"
  state — inventing them would fabricate.

**Result:** 0 placeholders across all model-surfaced Guide fields (page
short_description / primary_purpose / why_it_matters; metric formula / caveats).
The static Guide knowledge layer is complete. The only remaining Ollama step
requires enabling Ollama on the box: rebuild the RAG embedding index
(`python -m rcm_mc.assistant.rag.index_builder`) and run the live eval.

## Guide depth follow-ups (2026-05-27)

- **Cross-link hygiene + /tools + acronym glossary (#1000, merged):** a
  related-routes gap scan found 7 pages whose "open this next" links pointed at
  unmapped routes (dead Guide cross-links). Added a post-build
  `_RELATED_ROUTE_FIXES` pass (repoint known-wrong, normalize trailing slashes,
  drop unresolved), mapped `/tools` (the searchable tool index), and added
  `docs/rag_sources/pe_healthcare_glossary.md` so the Guide can expand
  healthcare-PE acronyms. Guards: no dead cross-links, `/tools` mapped, glossary
  in corpus. Documented contexts 344→345.
- **On-screen figures (this PR):** the Guide can now analyze the live KPI
  values the user is viewing. The widget scrapes visible `.ck-kpi` label+value
  pairs and posts them; `/api/guide/ask` sanitizes (typed pairs, length/count
  caps) and the prompt builder renders them as an "as-displayed, NOT validated"
  block after the page packet, with a system rule that keeps every guardrail
  (carry the page's data confidence, never IC-ready, never invent figures).
  Backward compatible (omitting them = v1 prompt byte-for-byte).

## Addendum — 2026-05-28: editorial style-sweep loop (Phase 3 + 4)

A sustained multi-PR sweep against the 2026-05-28 editorial-style handoff
spec. Single source of truth: `docs/style-sweep/MIGRATION_INVENTORY.md` —
updated after every batch. PRs are 4-7 surfaces each so review stays small.

### Phase 3 — Groups B + D fully cleared

- **Group B** (30 files) — every `ck_section_intro()` masthead is now the
  universal strict Tier-1 5-block head via `ck_editorial_head()`.
  Cleared across batches 19-24 (PRs #1075-#1080).
- **Group D** (24 files) — every `editorial_intro=` shell kwarg is now the
  same universal helper inline. Cleared across batches 25-29
  (PRs #1081-#1085).
- The helper `ck_editorial_head()` lives in
  `rcm_mc/ui/_chartis_kit.py` and produces one `<h1>`, a 24×1px green dash
  glyph, a mono uppercase meta-line (REAL counts; never hard-coded), an
  italic-first-phrase serif lede in `--green-deep`, and a 4-bucket
  status-dot legend.

### Phase 4 — Group C trope sweep (in progress)

Strips spec-forbidden tropes (`border-left:[1-9]px solid` decorative accents,
`border-radius > 2px`, `box-shadow` on content cards, gradients on card
backgrounds). Semantic severity colors **preserved** — they carry meaning.

Migration recipe per file:
1. Strip decorative 3px left-border accents (`var(--cad-accent)`,
   `var(--cad-link)`, `P["accent"]`, non-semantic brand hex).
2. Preserve semantic severity stripes (`cad-pos/warn/neg`,
   `sc-positive/negative/warning/teal`, per-tone `var(--tone)`,
   `status_color`, per-event palette, `irr_color`, severity tier colors).
3. For stripe-with-variants (e.g. `.pa-callout` + `.pa-callout.alert/.warn/.good`):
   default goes flat-hairline; variants re-add their stripe with semantic color.
4. Cap `border-radius` at 2px on content surfaces.
5. Retire decorative gradients on card backgrounds; keep functional gradients
   (heatmap legends, skeleton loaders, semantic 2-3px tone-encoded top-bars).
6. Drop heavy box-shadows on content cards; keep affordance shadows on buttons
   / interactive elements.

Progress so far (batches 30-39, PRs #1086-#1095):
- **64 surfaces cleaned** across 24 files
- **7 decorative gradients retired**
- **3 dark box-shadows removed**

Files cleared in Phase 4:
- `command_center.py`, `conference_page.py`, `ml_insights_page.py`,
  `value_tracking_page.py`, `fund_learning_page.py`, `data_dashboard.py`,
  `bayesian_page.py`, `compare_page.py`, `deal_library_page.py`,
  `empty_states.py`, `exit_timing_page.py`, `hospital_providers_page.py`,
  `cliff_calendar_page.py`, `settings_ai_page.py`, `settings_pages.py`,
  `cms_apm_tracker_page.py`, `drug_shortage_page.py`, `payer_intel_page.py`,
  `deal_flow_heatmap_page.py`, `industry_page.py`,
  `_benchmark_panels.py`, `_colorado_context.py`, `physician_productivity_page.py`,
  `payer_rate_trends_page.py`, `ref_pricing_page.py`,
  `deal_timeline.py`, `cms_sources_page.py`, `models_page.py`,
  `market_analysis_page.py`, `waterfall_page.py`, `market_intel_page.py`,
  `payer_stress_page.py`, `covenant_lab_page.py`, `regulatory_calendar_page.py`,
  `physician_attrition_page.py`, `dashboard_page.py`, `hcris_xray_page.py`,
  `deal_autopsy_page.py`, `ic_memo_page.py`, `bridge_audit_page.py`,
  `bear_case_page.py`, `analysis_workbench.py`,
  `model_quality_dashboard.py`, `calibration_page.py`.

Group C still has ~116 surfaces remaining. Loop continues.

## Recommended next improvements

1. Enable Ollama on the droplet and run the Guide eval harness
   (`tests/test_guide_eval.py`) against real questions to validate answer
   quality end-to-end.
2. Continue surgical UI enrichment only where a page is genuinely thin AND
   real-data-backed (verified case-by-case) — not a blanket migration.
3. Further metric/data-source registry depth as new pages reference new
   concepts.
4. Finish the Phase-4 Group C trope sweep — see
   `docs/style-sweep/MIGRATION_INVENTORY.md` for the active per-batch
   worklist.

## Addendum — 2026-05-31: Guide-context drain (PRs #1250-#1281)

A 32-PR session that took the Guide-context layer from 'mostly populated
with some NEEDS placeholders' to **exhaustively populated and locked by
24 invariant tests**. Every PageContext, MetricContext, and
DataSourceContext field that flows into the Ollama Guide's prompt is
now real, page/metric/source-specific content — no `_NEEDS` placeholder
text can reach the model.

**Lanes drained + locked (each by a regression test in
`tests/test_pedesk_guide_5q_invariant.py`):**

- **List-fields** (`inputs` / `outputs` / `key_metrics` /
  `diligence_use_cases`) — drained across all 360 pages
  (PRs #1246-#1256).
- **`limitations` / `interpretation_guidance` / `model_logic_summary`**
  — drained on 360 pages (prior sprint).
- **`common_misread`** — drained on all 81 metrics (#1257-#1258).
- **`provenance_notes` + `strengths`** — drained on 51 data sources
  (#1262).
- **`update_cadence` + `freshness_lag`** — drained on 51 data sources
  (#1265).
- **`ic_ready`** — set explicitly on every data source (no `None`)
  (#1267).
- **Page → data source links** — 24 illustrative-overlay pages wired
  to their canonical anchor source (#1264).
- **Data source → metrics** — 10 public-data sources cross-linked to
  the metrics they feed (#1263).
- **All pages have ≥1 related_route** (#1259) + all resolve (#1259).
- **All metrics have ≥1 related_metrics** + all resolve (#1258).
- **All data-source related_metrics resolve** (#1263).
- **All page data_source_ids resolve** (#1264).
- **52 dup desc/purpose collapsed in the prompt** (#1266).
- **Orphan metrics in registry** — 7 metrics wired to owning pages
  (#1279); invariant guards.
- **Orphan data sources in registry** — 3 wired to owning pages
  (#1280); invariant guards (only `unknown_source` allowlisted).
- **Unwired key_metrics→metric_id** — 9 pairs wired via
  `_METRIC_LINK_EXTEND_2` (#1277); invariant guards.
- **/metric-glossary keys** — 4 mapped as registry aliases (#1275) +
  2 added as full new registry entries: `first_pass_resolution_rate`,
  `payer_diversity` (#1276).

**Prompt-builder enrichment** (9 new clauses added to the per-route
prompt):

- `Common misread:` per metric (#1260)
- `Diligence read:` per metric (#1261)
- Collapsed `Page description / primary purpose:` when duplicate (#1266)
- `IC-ready: yes/no` per data source (#1268)
- `Provenance:` per data source (#1269)
- `Route-specific assistant notes:` for parameterized pages (#1270)
- `Diligence use cases:` per page (#1271)
- `Model logic:` per page (#1272)
- `Strengths:` per data source (#1273)
- `Related metrics:` per metric (#1274)
- `Discussed on:` (metric.related_routes) (#1281)

**Test-maintenance fix**: 2 stale UI tests (mega-menu + topbar
dropdown) updated to track post-#1003/#1155 markup (#1278).

**Final state**: Real NEEDS placeholders across all 3 registries = 0
(excluding the `notes_for_assistant` lines that explicitly instruct
the model to say *'needs source documentation'* when it can't answer).
24 invariant tests + ~85 tests in the broader guide test suite all
green. Production health (https://pedesk.app/healthz) verified 200
throughout the sprint.

**Full local test suite confirmed green** at session close
(2026-05-31 ~08:54 UTC): `12,977 passed, 68 skipped, 1 xfailed in
1172.49s`. The two stale UI tests
(`test_mega_menu_hidden_by_default::test_open_states_use_grid` and
`test_topbar_dropdown::test_menu_lists_the_sections_subpages`) that
had silently drifted past CI's reduced set were caught and fixed in
#1278 — this is the first session in a long while where every test
in the repo passes locally, not just the CI subset.

Session totals at #1286: **37 PRs landed (#1250-#1286)** across:
- 11 list-fields drain batches
- 2 metric-registry hardening + 6 glossary-coverage + new metric entries
- 1 admin-page related_routes wiring
- 11 prompt-builder enrichment clauses
- 4 cross-link wirings (sources↔metrics, pages↔sources)
- 1 orphan-metrics + 1 orphan-data-sources closure
- 2 stale-UI-test maintenance fixes
- 1 eval question-set expansion
- 1 prompt-builder double-period cleanup
- 2 docs updates (session summary)

24 invariant tests in `tests/test_pedesk_guide_5q_invariant.py`
guard every gate. Test count progression across the session:
8 → 11 → 14 → 16 → 17 → 18 → 20 → 21 → 22 → 23 → 24.

## Addendum — 2026-05-31 (PM): continuous-work loop, PRs #1303-#1322

User requested explicit "no wakeups, do not stop, work" mode. Twenty
PRs landed in one continuous segment (#1303–#1322), no ScheduleWakeup
calls between them. Mix of feature wirings, partner-alias coverage,
two silent-bug fixes caught by structural tests, and four new
invariant tests.

**Partner-alias coverage**: probed the resolver against actual partner
phrasings across 4 rounds for metrics and 4 rounds for sources.
~78 new aliases total (~40 metric, ~38 source); each unambiguous and
locked in `test_partner_metric_aliases_resolve` (40+ cases) +
`test_partner_source_aliases_resolve`.

**Silent bug 1 (PR #1308 → PR #1310)**: `_PARTNER_SOURCE_ALIAS_EXTENSIONS`
allowed duplicate keys — a second `'cms_hcris': [...]` literal silently
wiped PR #1299's `'CCN'` and `'medicare cost reports'` aliases (Python
dict literals overwrite on duplicate keys). Fixed by merging the
lists; PR #1309 added a structural AST scan that fails on any dict
literal with duplicated keys across the three registry modules.

**Silent bug 2 (PR #1310)**: PR #1309's dup-key scan only walked
`ast.Assign` nodes — but `_ALIAS_EXTEND_COVERAGE` is a typed
`ast.AnnAssign` (`_ALIAS_EXTEND_COVERAGE: Dict[str, List[str]] = ...`).
The wider scan found 4 more duplicate keys (moic, days_in_ar,
capex_intensity, denial_rate) that had silently dropped 5 more
aliases over the round-1 → round-2 transitions. Fix + scan widened to
also handle `AnnAssign`. All 5 lost aliases restored ("days in ar",
"capex", "capital expenditure", "denial", "weighted moic") and locked
in tests.

**Page-wiring sweeps**: 27 more page → metric / page → source wirings
landed across `_METRIC_LINK_EXTEND_2`, `_DATA_SOURCE_LINK_PATCHES`,
and the new `_DATA_SOURCE_LINK_EXTEND` (append-not-replace) dict
introduced in #1307. Notable: `/medicaid-unwinding`, `/risk-adjustment`,
`/revenue-leakage`, `/initiatives`, `/industry`, `/diligence/bear-case`,
`/market-intel/geo`, 7 deal-pipeline/screening pages (#1315), 10
diligence pages (#1317), 3 payer-reference pages (#1318), and
6 source-link-extend pages (#1322).

**Content enrichments**: every metric now carries ≥2 caveats (PR #1319
closed the last 3 single-caveat metrics; PR #1320 locked the floor).
`cms_care_compare` extended with `cms_star_rating + readmission_rate`
related metrics (#1321). All 8 short-allowlisted pages (7 CSV exports
+ Seeking-Alpha viewer) bumped to the 5-Q floor (#1313); `_SHORT_OK`
now empty.

**Subtle wiring-order gotcha** (PR #1322): the `_DATA_SOURCE_LINK_EXTEND`
loop runs BEFORE the later `_PUBLIC_SOURCE_LINKS` fill-only-if-empty
loop. Adding `/cms-apm → cms_mssp_aco` via EXTEND pre-populated
`data_source_ids`, which then made `_PUBLIC_SOURCE_LINKS` skip the
later `cms_cmmi_apm` write — caught by the no-orphan-source invariant.
Fixed by also naming `cms_cmmi_apm` in the EXTEND.

Test count: 24 → 27 invariant tests (added: no-dup-keys-in-AnnAssign,
2+ caveats per metric, partner-metric-aliases-resolve). Total
guide-context suite: 75 → 77 across this segment.

Sprint cumulative through #1322: **57+ PRs landed in current
continuous-loop session** (#1250–#1322 spanning prior segments +
this PM continuous segment). All green CI, all auto-deployed.

## Addendum 2 — 2026-05-31 (PM continued): PRs #1323-#1328

Six more PRs landed continuing the same continuous-loop segment:

- **#1323** docs: this session-summary update through #1322.
- **#1324** Last unresolved `/metric-glossary` key closed
  (`net_patient_revenue` added as alias on revenue) + locked the
  floor with `TestNoUnresolvedGlossaryKeys`. All 24 glossary keys
  now resolve via the Guide.
- **#1325** Wired `/diligence/pe-tool` → `analysis_run` (prose names
  "the deal's analysis packet").
- **#1326** Two-part fix to `data_source.related_routes` back-fill:
  (a) EXTEND-with-cap=6 instead of fill-only-if-empty so the 30+
  page-wirings from PRs #1304-#1325 actually flow back-side too;
  (b) move the back-fill to run LAST (after `_GEO_SOURCE_LINKS` +
  `_PUBLIC_SOURCE_LINKS`) so it sees the complete consuming-page
  set. Source distribution improved from {1:27, 2:9, 3:5, 4:5, 5:1,
  6:3, 0:1} to {1:13, 2:9, 3:4, 4:2, 5:3, 6:18, 7:1, 0:1} — 18
  sources hit cap=6 vs 3 before. Also reverted a marginal #1322
  entry that hit the same wire-order gotcha as `/cms-apm` (caught
  by the no-orphan-source invariant).
- **#1327** `TestSourceRelatedRoutesBackFillIsComplete` locks the
  wire-order regression structurally so a future reorder can't
  silently re-break it.
- **#1328** Prompt-builder enrichment: per-source `Feeds metrics: a, b, c.`
  clause closes the symmetry gap with the per-metric block (which
  already surfaced "Related metrics" + "Discussed on"). Skips when
  `related_metrics` is empty (the ~20 system-meta sources).

Test count: 27 → 29 invariant tests (added: glossary-keys-resolve,
source-back-fill-completeness). Guide-context suite: 77 → 79+.

Sprint cumulative through #1328: **63+ PRs landed in current
continuous-loop session**. All green CI, all auto-deployed, prod
healthy across the entire segment (`https://pedesk.app/healthz` →
`ok` throughout).

### Segment final 3 PRs (#1329-#1331)

- **#1329** docs: prior addendum capturing #1323-#1328.
- **#1330** Distinct `primary_purpose` on 4 more analytic pages
  whose short_description and primary_purpose had been identical:
  /calibration, /specialty-benchmarks, /tracker-340b, /fund-learning.
  Trimmed redundant-pair count 22 → 18; updated the
  `test_user_prompt_collapses_duplicate_desc_and_purpose` fixture
  to use /news (a stable symmetric-default operational page).
- **#1331** Round-5 source aliases (8 more): 'co apcd' / 'colorado
  apcd' / 'cost of care' for civhc_rbp; 'snf five star' / 'snf
  five-star' / 'snf compare' for cms_provider_data_catalog;
  'hospital cahps' for cms_hcahps; 'ma geo data' for cms_ma_geo.

**Final segment totals: 29 PRs landed (#1303-#1331)**, all green
CI, all auto-deployed, all squash-merged. Guide-context test suite
at 79 (was 75 at segment start). 29 invariant tests (was 24).
Continuous-loop session cumulative: **66 PRs through #1331**
(#1250-#1331 spanning prior + this PM continuous segment).

### Continued — segment final (PRs #1333-#1337)

User asked for "more, more, more" — six more PRs landed:

- **#1333** Round-6 source aliases (13 more across 5 sources):
  HCRIS hyphen-variants, Care Compare 'hospital quality'/'hospital
  rating', EDGAR 'edgar filings'/'sec filing', PDC SNF five-star
  variants, transaction corpus 'm&a corpus'/'closed deals'/
  'realized deals corpus'/'transaction database'. Avoided
  'quality rating' (collides with existing cms_star_rating).
- **#1334** Round-6 metric aliases (27 more across 12 metrics):
  collection/denial/bad-debt/underpayment-rate `%` variants;
  capex `/rev` shorthand; gross/ebitda/op-margin `pct`/`mgn` variants;
  occupancy_rate `occ rate`/`occ %`; first_pass_yield variants;
  compensation_to_collections `comp to coll`/`physician comp ratio`.
- **#1335** Lock 60+ aliases across rounds 1-6 by extending
  test_partner_metric_aliases_resolve (+19) and
  test_partner_source_aliases_resolve (+20). Same defense pattern
  as PR #1310's restoration test — explicit enumeration so a dup
  key can't silently drop them.
- **#1336** Smoke test: prompt builder builds for every page in
  PAGE_CONTEXT_REGISTRY (360 pages, ~80ms) without raising;
  every prompt non-empty + carries '=== Question ===' terminator.
- **#1337** Self-resolution invariants: every metric_id resolves
  to itself; every metric label resolves to its own metric_id;
  same for sources. Locks the floor against typo/normalizer/
  collision regressions.

Test count: 29 → 30 invariant tests. Lookup tests: 16 → 18.
Prompt-builder tests: 34 → 35. Total Guide-context suite: 79 → 83.

**Final continuous-loop session cumulative through #1337: 35 PRs
landed (#1303-#1337)**, all green CI, all auto-deployed. Partner-
alias probing has reached genuine saturation: round-7 probe (28
metric + 17 source candidates) returned only 2 hits (837p/837i
already aliased via case+space normalization), confirming the
remaining misses correspond to concepts the registry doesn't track.

## Guardrails honored

No fake data. Did not touch auth/session, Caddy, systemd, deploy workflow,
secrets, the Ollama/Tailscale/RAG runtime, or the gated `#898` weighted-ridge
predictor. Every change is additive, tested, and reversible.
