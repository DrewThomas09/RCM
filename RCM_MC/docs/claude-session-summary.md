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

## Recommended next improvements

1. Enable Ollama on the droplet and run the Guide eval harness
   (`tests/test_guide_eval.py`) against real questions to validate answer
   quality end-to-end.
2. Continue surgical UI enrichment only where a page is genuinely thin AND
   real-data-backed (verified case-by-case) — not a blanket migration.
3. Further metric/data-source registry depth as new pages reference new
   concepts.

## Guardrails honored

No fake data. Did not touch auth/session, Caddy, systemd, deploy workflow,
secrets, the Ollama/Tailscale/RAG runtime, or the gated `#898` weighted-ridge
predictor. Every change is additive, tested, and reversible.
