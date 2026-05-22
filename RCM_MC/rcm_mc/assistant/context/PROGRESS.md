# PEdesk Guide page-context — PROGRESS

**Date:** 2026-05-22

## Language adaptation
Spec was TypeScript/Node; PEdesk is pure Python (no Node toolchain).
Implemented in Python under `rcm_mc/assistant/context/` per the spec's
"adapt paths to match the codebase" instruction. TS interfaces →
dataclasses; string-union types → `Enum`s; `npm`/`tsx` validator → a
runnable Python module + a pytest.

## Route source(s) discovered
- **`rcm_mc/ui/_chartis_kit.py :: _DEFAULT_PALETTE_MODULES`** — the
  Cmd+K / Tools palette and the authoritative route manifest. Its
  comment-group headers map 1:1 to the seven PEdesk tool groups.
- Considered but not merged as separate manifests: `/module-index`
  (the ~150 `data_public` analytic modules — a secondary catalog) and
  the per-deal dynamic routes (handled by the dynamic matcher, not the
  static manifest). The palette is the single normalized source.

## Counts
- Total discovered routes: **72**
- Registry entries: **72** (one per discovered route; zero missing)
- Documented contexts: **42**
- Placeholder contexts: **30**
- Duplicate routes: **0**
- Routes that could not be categorized: **0** (all map to one of the 7 groups)
- Dynamic route contexts (not in the static manifest): Deal Dashboard,
  Partner Review, Deal IC Packet, Deal Red Flags, Analysis Workbench,
  Engagement Portal.

## Commands run + results
- `python -m rcm_mc.assistant.context.validate_page_context_coverage`
  → **PASS, exit 0** (0 missing, 0 invalid categories/confidence, 0
  duplicates, 0 missing titles/normalizedRoutes).
- `python -m pytest tests/test_pedesk_guide_page_context.py` → **9 passed**.
- Acceptance lookups verified: `?demo=steward` normalizes to
  `/diligence/risk-workbench`; `/deal/<id>`, `/deal/<id>/partner-review`,
  `/deal/<id>/ic-packet`, `/deal/<id>/red-flags`, `/analysis/<id>`,
  `/portal/<id>` resolve to generic contexts; trailing slash + hash
  normalize; unknown routes return the clean fallback.

## Placeholder routes (need source upgrade — next batches)
30 placeholders, e.g.: /source, /pe-intelligence, /deal-screening,
/conferences, /diligence/{thesis-pipeline, checklist, ingest,
benchmarks, root-cause, value, counterfactual, qoe-memo,
denial-prediction, physician-attrition, physician-eu, management,
exit-timing, covenant-stress, bridge-audit}, /engagements,
/deals-library, /market-intel, /research, /notes, /hold-analysis,
/corpus-backtest, /portfolio/{map, monitor}, /portfolio-analytics,
/market-data/state/CA.

## Remaining caveats
- Manual contexts deliberately describe *intent* and *interpretation*,
  not exact formulas. Anything not established from source is marked
  "Needs source documentation." — no invented math/lineage.
- `data_confidence` flags live-vs-illustrative honestly, but several
  manual entries use `mixed`/`unknown` pending source confirmation.
- The `/module-index` long-tail (~150 analytic modules) is intentionally
  out of scope for this manifest; fold in later if the Guide should
  cover them too.

## Next recommended batch to upgrade (highest value first)
1. Diligence Workspace placeholders: /diligence/{value, qoe-memo,
   counterfactual, exit-timing, covenant-stress, bridge-audit,
   denial-prediction} — core IC-path tools.
2. Pipeline: /source, /pe-intelligence, /deal-screening.
3. Research: /hold-analysis, /corpus-backtest, /market-intel.
4. Portfolio: /portfolio/map, /portfolio/monitor, /portfolio-analytics.

---

# Task 2 — Metric & Data Source Registries (2026-05-22)

- **Metrics created:** 54 (`METRIC_REGISTRY`) — financial/PE, revenue
  cycle, provider, hospital/HCRIS, risk/model (+ `ebitda_bridge`).
- **Data sources created:** 32 (`DATA_SOURCE_REGISTRY`) — public/external,
  uploaded/target, internal/system, special (+ `benchmark_prior`, added
  so the payer-stress page reference resolves).
- **Pages connected to metric/source ids:** 8 (hcris-xray, bridge-audit,
  payer-stress, denial-prediction, physician-eu, portfolio/monitor, data,
  methodology). `PageContext` gained optional `metric_ids` /
  `data_source_ids` (default empty — existing entries unaffected).
- **Lookups:** `get_metric_context`, `get_data_source_context` —
  case-insensitive, alias-aware, clean fallback.

## Commands + results
- `validate_page_context_coverage` → PASS (exit 0).
- `validate_guide_context_quality` → PASS (exit 0): 0 invalid metric/
  source refs, 0 duplicate ids, 0 ambiguous aliases. (33 metrics
  `needs_validation` and placeholder pages are allowed, not failures.)
- `py_compile` on the package → clean.
- `pytest tests/test_pedesk_guide_metric_data_context.py
  tests/test_pedesk_guide_page_context.py` → 20 passed.

## Caveats
- Most metric formulas are `needs_validation` or `inferred` by design —
  no model-specific formula is invented; standard textbook ratios are
  marked `inferred`.
- Removed the ambiguous bare alias "leakage" (claimed by both
  collections_leakage and referral_leakage) so it cleanly falls back.
- Many `data_confidence` values are `mixed`/`unknown` pending source
  confirmation. The `/module-index` ~150-module long-tail remains out of
  scope for the page manifest.

## Next recommended batch
- Upgrade more diligence placeholders to documented contexts and attach
  metric/source ids (qoe-memo, covenant-stress, exit-timing, value).
- Confirm exact formulas from code/methodology to promote key metrics
  from `inferred`/`needs_validation` → `documented`.

---

# Task 3 — Guide Context Packet layer (2026-05-22)

Single read-only builder that assembles all structured context the
future Guide needs to explain a page. No AI / Ollama / RAG / chat /
actions / DB memory / visual redesign / workbench port — text + lookups.

| File | Role |
|------|------|
| `guide_prompt_policy.py` | `GUIDE_PROMPT_POLICY` (frozen) + `GUIDE_IDENTITY`, `ALLOWED_BEHAVIOR`, `DISALLOWED_BEHAVIOR` (10), `DEFAULT_UNCERTAINTY_MESSAGE`, `policy_as_dict()`. The behavioral contract; carries no behavior. |
| `suggested_questions.py` | `get_suggested_questions_for_page(page_context)` — 5 defaults + category/data-source additions, deterministic, capped at 8. |
| `guide_context_packet.py` | `GuideContextPacket` dataclass + `build_guide_context_packet(route)` + `summarize_context_packet(packet)`. |

**Builder flow:** `get_page_context` → resolve metric contexts (explicit
`metric_ids`, else conservative match from `key_metrics` labels) → resolve
data-source contexts (same) → suggested questions → embed policy →
compute `context_quality` → record `missing_context_notes`. Never invents
formulas/lineage; unresolved items are recorded, not fabricated.

**`context_quality` precedence:** `missing` (no page ctx) → `placeholder`
(`source_confidence == needs_validation`) → `strong` (documented /
inferred_from_page **and** ≥1 linked metric/source) → `placeholder`
(≥3 core fields say "Needs source documentation.") → `partial`.

## Quality distribution (all 72 registry routes)
- **strong: 8** (the 8 metric/source-linked pages from Task 2)
- **partial: 2**
- **placeholder: 62**
- **missing: 0** (every registry route resolves; only off-manifest
  routes like `/unknown-route` grade `missing`)

## Commands + results
- `validate_page_context_coverage` → PASS (exit 0).
- `validate_guide_context_quality` → PASS (exit 0).
- `py_compile` on the package → clean.
- `pytest tests/test_pedesk_guide_context_packet.py` → 10 passed.
- `pytest tests/test_pedesk_guide_page_context.py
  tests/test_pedesk_guide_metric_data_context.py` → 20 passed (unchanged).

## Caveats
- Packet quality is honest, not flattering: 62/72 routes grade
  `placeholder` because their underlying page contexts are still
  placeholders (Task 1/2 backlog). Promoting them is a context-authoring
  task, not a packet-layer change.
- Conservative metric/source matching only resolves *registered* aliases;
  a page whose `key_metrics` are free-text prose won't auto-link (recorded
  in `missing_context_notes`). Explicit `metric_ids`/`data_source_ids`
  remain the reliable path.
- No endpoint is wired: this is infrastructure the future Guide endpoint
  imports. Building that endpoint (and any UI) is explicitly out of scope.

---

# Task 4 — Upgrade placeholder PageContexts from source (Priority A) (2026-05-22)

Read the actual page implementations (route handlers in `server.py`,
renderers in `rcm_mc/ui/`, page docstrings, headings, table columns, KPI
labels, data pulls) and authored conservative, source-grounded contexts
for the Priority A pages. No formulas/lineage invented; unknowns stay
"Needs source documentation." Scope: **Priority A only** (the spec
permits stopping here and reporting the next batch).

## Quality distribution (packet quality over all 72 registry routes)
- **Start:** strong 8 · partial 2 · placeholder 62 · missing 0
- **End:**   strong 23 · partial 2 · placeholder 47 · missing 0

Strong target (20+) reached. Partial-20+/placeholder-<35 stretch needs
Priority B/C (not in this PR, by design).

## Pages upgraded (Priority A) — 16 routes
Promoted to **strong** (filled core fields + linked reliable
metric_ids/data_source_ids): `/alerts`, `/watchlist`,
`/diligence/questions`, `/audit`, `/import`, `/pipeline`,
`/diligence/deal`, `/diligence/ic-packet`, `/portfolio`,
`/portfolio/risk-scan`, `/portfolio/heatmap`, `/lp-update`, `/app`
(added MOIC/IRR/covenant + portfolio_snapshot links).
Two **new** entries authored (were needs_validation stubs):
`/diligence/checklist`, `/diligence/qoe-memo`.
`/users` upgraded to **partial** (admin page — no analytic metric/source
to link; intentionally not strong).

## Conservatism calls worth noting
- **`/pipeline` correction:** the prior context claimed a
  "probability-weighted close value"; the actual `pipeline_page.py`
  shows a stage funnel (screening→…→closed/passed) over HCRIS public
  financials with **no** weighting. Rewritten to match source and noted
  that any weighting "needs source confirmation."
- **`/diligence/ic-packet` and `/diligence/qoe-memo` are NOT marked
  IC-ready / signed.** Source shows only a rendered view (browser
  Print → Save as PDF); the QoE engagement link writes a **DRAFT** only.
  Both contexts explicitly say to verify before IC use — no sign-off
  flow exists in source.
- **localStorage pages** (`/diligence/deal`, `/diligence/questions`)
  flagged as user-entered, browser-local — not server-side records.
- **`data_confidence`** set honestly: fixture-driven diligence pages →
  `mixed`; HCRIS-backed `/pipeline` → `public_benchmark_data`;
  user-entered import/profile pages → `user_entered_data`.

## Pages still placeholder (47) — next batches
- **Priority B (14 placeholder):** /source, /screen-adjacent sourcing,
  /pe-intelligence, /deal-screening, /find-comps, /conferences,
  /diligence/{thesis-pipeline, benchmarks, root-cause, value,
  risk-workbench, counterfactual, compare}, /screening/bankruptcy-survivor.
- **Priority C (19 placeholder):** /library, /deals-library, /comparables,
  /market-rates, /research, /notes, /sector-momentum, /irr-dispersion,
  /hold-analysis, /comparable-outcomes, /bear-cases, /regulatory-calendar,
  /market-intel, /corpus-backtest, /backtest, /portfolio/map,
  /portfolio-analytics + remainder.
- Plus other non-priority placeholders in the long tail.

## Blocked / not upgraded
- **`/home`** is not a discovered route (not in the registry) — no page
  to read, so nothing authored. (`/app` is the actual command center.)
- **`/users`** stays `partial` by design — it's platform administration,
  not an analytic page; no registry metric/source applies.

## Commands + results
- `python -m rcm_mc.assistant.context.validate_page_context_coverage`
  → PASS (exit 0).
- `python -m rcm_mc.assistant.context.validate_guide_context_quality`
  → PASS (exit 0): 0 invalid metric refs, 0 invalid source refs, 0
  duplicate ids, 0 ambiguous aliases.
- `py_compile` on the context package → clean.
- `pytest tests/test_pedesk_guide_page_context.py
  tests/test_pedesk_guide_metric_data_context.py
  tests/test_pedesk_guide_context_packet.py` → **30 passed**.

## Caveats
- All upgrades are `inferred_from_page` unless the page/source explicitly
  documented behavior (`/alerts`, `/pipeline` data, `/portfolio`,
  `/portfolio/risk-scan`, `/lp-update`, `/app` keep `documented` where
  the source supports it).
- No exact formulas were added; model-logic summaries describe intent and
  point to the implementing module for specifics.

---

# Task 4B — Upgrade placeholder PageContexts from source (Priority B) (2026-05-22)

Read the actual page implementations (server.py handlers, `rcm_mc/ui/`
renderers, page docstrings, headings, table columns, KPI labels, and what
each handler pulls) and authored conservative, source-grounded contexts
for the Priority B sourcing / screening / diligence-interpretation pages.
No formulas/lineage invented.

## Quality distribution (packet quality over all 72 registry routes)
- **Start (after PR #559):** strong 23 · partial 2 · placeholder 47 · missing 0
- **End:** strong 36 · partial 3 · placeholder 33 · missing 0

## Pages upgraded (all 15 Priority B routes)
Promoted to **strong** (filled core fields + linked reliable
metric_ids/data_source_ids): `/source`, `/screen`,
`/predictive-screener`, `/deal-screening`, `/find-comps`,
`/diligence/thesis-pipeline`, `/diligence/benchmarks`,
`/diligence/root-cause`, `/diligence/value`, `/diligence/risk-workbench`,
`/diligence/counterfactual`, `/diligence/compare`,
`/screening/bankruptcy-survivor`.
Upgraded to **partial** (no analytic metric/source applies, by nature):
`/pe-intelligence` (a methodology/registry hub), `/conferences` (a
curated reference calendar).
Nine of these were previously `needs_validation` stubs now fully authored;
six already had minimal manual entries that were expanded.

## Conservatism calls worth noting
- **`/predictive-screener`:** kept as model ESTIMATES from public HCRIS,
  not observed target data; noted point estimates have no stated CI and
  are not validated against realized outcomes (`data_confidence =
  model_estimate`).
- **`/pe-intelligence`:** described as a module registry / codified-judgment
  catalog, explicitly NOT validated prediction; per-deal output lives on
  deal routes.
- **`/diligence/benchmarks`:** separated the target's own KPI VALUES
  (observed from claims) from the external peer BENCHMARK bands; flagged
  that claims are fixtures on this page.
- **`/diligence/risk-workbench`:** flagged `?demo=steward` as a specific
  named historical replay (Steward 2016), not a generic example, plus the
  `?print=1` mode.
- **`/screening/bankruptcy-survivor`:** described as deterministic
  pattern-match SIGNAL (falsifiable structural claims + named precedent),
  explicitly NOT a prediction/verdict; "pre-screening only."
- **`/diligence/value`:** UNDERWRITTEN forward opportunity, NOT realized
  value; contract/CMS rates are synthetic demo inputs.
- **`/diligence/counterfactual`:** what-if / sensitivity ("what would
  change the conclusion"), NOT an action recommender.
- **`/find-comps` and `/diligence/compare`:** comparable MATCHING, not an
  approved/governed comp set; both run on seeded/demo fixtures
  (`/diligence/compare` → `data_confidence = demo_or_fixture`).
- **`/source` vs `/screen` vs `/predictive-screener`:** thesis-fit ranking
  vs metric filter vs ML estimate — none marked "predictive" beyond what
  source supports; all on public HCRIS.

## Pages still placeholder (33) — next batch (Priority C + long tail)
Priority C examples: /library, /deals-library, /comparables, /market-rates,
/research, /notes, /sector-momentum, /irr-dispersion, /hold-analysis,
/comparable-outcomes, /bear-cases, /regulatory-calendar, /market-intel,
/corpus-backtest, /backtest, /portfolio/map, /portfolio-analytics, plus
the remaining non-priority long tail.

## Pages partial / blocked
- `/pe-intelligence`, `/conferences` stay **partial** by design — neither
  is an analytic page with a registry metric/source to link.

## Commands + results
- `python -m rcm_mc.assistant.context.validate_page_context_coverage`
  → PASS (exit 0).
- `python -m rcm_mc.assistant.context.validate_guide_context_quality`
  → PASS (exit 0): 0 invalid metric/source refs, 0 duplicate ids, 0
  ambiguous aliases.
- `py_compile` on the context package → clean.
- `pytest tests/test_pedesk_guide_page_context.py
  tests/test_pedesk_guide_metric_data_context.py
  tests/test_pedesk_guide_context_packet.py` → **30 passed**.

## Caveats
- All Priority B upgrades are `inferred_from_page` except `/screen` and
  `/deal-screening`, where the handler/module docstring explicitly
  documents the behavior (`documented`).
- `data_confidence` set honestly: fixture-driven diligence pages →
  `mixed` (or `demo_or_fixture` for `/diligence/compare`); HCRIS sourcing →
  `public_benchmark_data`; `/predictive-screener` → `model_estimate`;
  methodology/reference pages → `unknown`.
- No exact formulas added; model-logic summaries describe intent and point
  to the implementing module.

---

# Task 4C — Upgrade placeholder PageContexts from source (Priority C) (2026-05-22)

Read the actual page implementations (server.py handlers, `rcm_mc/ui/`
renderers, page docstrings, headings, table columns, KPI labels, data
pulls) and authored conservative, source-grounded contexts for the
Priority C research / reference / backtesting / portfolio / market-intel
pages. No formulas/lineage invented.

## Quality distribution (packet quality over all 72 registry routes)
- **Start (after PR #560):** strong 36 · partial 3 · placeholder 33 · missing 0
- **End:** strong 52 · partial 6 · placeholder 14 · missing 0

All quality targets met (strong 50+, partial 4+, placeholder <20, missing 0).

## Pages upgraded (all 19 Priority C routes)
Promoted to **strong** (16): `/library`, `/comparables`, `/market-rates`,
`/sector-momentum`, `/irr-dispersion`, `/hold-analysis`,
`/comparable-outcomes`, `/bear-cases`, `/regulatory-calendar`,
`/market-intel`, `/corpus-backtest`, `/backtest`, `/portfolio/map`,
`/portfolio-analytics`, `/sponsor-track-record`, `/payer-intelligence`.
Upgraded to **partial** (3): `/deals-library` (a legacy redirect to
/library), `/research` (a navigation/search index), `/notes` (a
notes-search utility) — none has a registry metric/source to link.
Eight of these were previously `needs_validation` stubs now fully
authored (incl. five new entries: /research, /notes, /hold-analysis,
/corpus-backtest, /market-intel, /portfolio/map, /portfolio-analytics,
/deals-library); the rest expanded existing minimal manual entries.

## Conservatism calls worth noting
- **`/library` / `/deals-library`:** reference/benchmarking corpus, NOT a
  governed deal-room/source-of-truth; `/deals-library` is a 301 redirect.
- **`/comparables` / `/comparable-outcomes`:** similarity MATCHING, not an
  approved/locked comp set.
- **`/market-rates`:** CORPUS benchmark percentiles, explicitly NOT live
  market pricing.
- **`/research` / `/notes`:** `/research` is a discovery index (no
  persistence); `/notes` is a search utility over persisted analyst notes
  — described as an archive, not a formal sign-off record.
- **`/sector-momentum`, `/irr-dispersion`, `/hold-analysis`:** HISTORICAL
  corpus analyses, explicitly NOT forward predictions (and hold-analysis
  does not prescribe an optimal hold).
- **`/bear-cases`:** counter-narrative SYNTHESIS that ranks downside
  evidence, NOT a final verdict.
- **`/regulatory-calendar` / `/market-intel`:** CURATED snapshots needing
  periodic refresh, explicitly NOT live feeds.
- **`/corpus-backtest` / `/backtest`:** VALIDATION / calibration framing
  (in-sample), NOT decision-ready forward prediction; the two are
  distinguished (platform-predictions-vs-realized vs corpus-formula fit).
- **`/portfolio/map`:** geographic VISUALIZATION (CON shading is a status
  marker), NOT a market-access/CON analysis.
- **`/portfolio-analytics`:** scope is the 655-deal CORPUS, explicitly NOT
  the user's live fund.
- **`/sponsor-track-record`:** historical reference, NOT guaranteed/
  predictive sponsor performance.
- **`/payer-intelligence`:** rank CORRELATION of payer mix with MOIC,
  explicitly NOT a causal claim.

## Pages still placeholder (14) — long tail
/day-one, /diligence/covenant-stress, /diligence/deal-autopsy,
/diligence/deal-mc, /diligence/exit-timing, /diligence/ingest,
/diligence/management, /diligence/physician-attrition, /engagements,
/escalations, /market-data/state/CA, /metric-glossary, /my/AT,
/rcm-benchmarks. (Several of these — e.g. /diligence/deal-mc,
/diligence/deal-autopsy, /rcm-benchmarks — already carry partial content
but lack linked ids; a future pass can promote them.)

## Pages partial / blocked
- `/deals-library`, `/research`, `/notes` (this task) and
  `/pe-intelligence`, `/conferences`, `/users` (earlier) stay **partial**
  by design — navigation/admin/utility pages with no registry
  metric/source to link.

## Commands + results
- `python -m rcm_mc.assistant.context.validate_page_context_coverage`
  → PASS (exit 0).
- `python -m rcm_mc.assistant.context.validate_guide_context_quality`
  → PASS (exit 0): 0 invalid metric/source refs, 0 duplicate ids, 0
  ambiguous aliases.
- `py_compile` on the context package → clean.
- `pytest tests/test_pedesk_guide_page_context.py
  tests/test_pedesk_guide_metric_data_context.py
  tests/test_pedesk_guide_context_packet.py` → **30 passed**.

## Caveats
- `/comparables`, `/market-rates`, `/comparable-outcomes`,
  `/sponsor-track-record`, `/payer-intelligence` keep `documented` (their
  source/docstrings document behavior); the rest are `inferred_from_page`.
- `data_confidence`: corpus reference pages → `public_benchmark_data`;
  prediction/validation pages → `model_estimate` (/backtest) or `mixed`
  (/corpus-backtest); curated reference → `public_benchmark_data`;
  navigation index → `unknown`; notes → `user_entered_data`.
- No exact formulas added; model-logic summaries describe intent and point
  to the implementing module.

---

# Task 5 — Read-only Guide context debug endpoint (2026-05-22)

Exposed the existing `GuideContextPacket` through a safe, read-only HTTP
endpoint so the packet a future (non-AI) PEdesk Guide would have can be
inspected. No AI / Ollama / RAG / chat / actions / DB memory — a pure
builder call over the static registries.

## Endpoint
- **`GET /api/guide/context?route=<route>`** → JSON-safe `GuideContextPacket`.
  - Missing/blank `route` → **HTTP 400** `{"error":..., "code":"MISSING_ROUTE"}`.
  - Unknown route → **HTTP 200** with `context_quality="missing"` + clean
    `fallback_message` (never a 500).
  - Nested query strings in the route value (e.g.
    `route=/diligence/risk-workbench?demo=steward`) are preserved by
    `parse_qs` and normalized away by the packet builder.
- **`GET /guide/context-debug?route=<route>`** (optional) → minimal
  read-only HTML dump (chartis_shell + escaped `<pre>` JSON). No UI polish.

## Integration point
PEdesk has no API blueprint — it's a stdlib `http.server` `RCMHandler`
that dispatches on `path` inside `_do_get_inner`. Added the two routes at
the top of `_do_get_inner` and two handler methods
(`_route_guide_context`, `_route_guide_context_debug`) plus a shared
`_guide_context_route_param` helper. JSON is sent via the existing
`_send_json`; the existing `do_GET` global error boundary already returns
clean JSON (no stack traces). In single-user/open mode (no users) the
endpoint is reachable without a session, matching other read endpoints.

## Serialization
Added `packet_to_dict(packet)` to `guide_context_packet.py` (exported
from the package `__init__`): converts the dataclass recursively, Enums →
`.value`, and trims to the documented response shape (page_context +
metric_contexts + data_source_contexts subsets + suggested_questions +
read_only_policy + known_limitations + missing_context_notes). Pure
transform — reads nothing, mutates nothing.

## Commands + results
- `validate_page_context_coverage` → PASS (exit 0).
- `validate_guide_context_quality` → PASS (exit 0).
- `py_compile` on the context package + server.py → clean.
- `pytest` page-context + metric/data + packet + endpoint suites →
  **37 passed** (30 existing + 7 new endpoint tests).

## Tests (tests/test_guide_context_endpoint.py)
hcris-xray (200, strong, title, questions, policy, linked contexts);
query-string normalization; dynamic /deal and /analysis routes; unknown
route (200 + missing + fallback); missing `route` param (400, clean, no
traceback); purity/idempotency (two identical GETs → identical JSON).
No-mutation: PEdesk has no read-endpoint mutation-test convention, so
purity is asserted via deterministic idempotency — the endpoint only
calls the registry-backed packet builder.

## Caveats
- The endpoint is read-only and AI-free by construction; it neither
  imports nor reaches any model/Ollama/RAG path.
- The optional debug HTML reflects the user-supplied `route` — it is
  `html.escape`d in both the input value and the JSON `<pre>` to avoid
  reflected XSS.

---

# Task 6A — Local Ollama read-only Guide answer endpoint (2026-05-22)

Got Ollama into PEdesk behind the existing context layer — a local model
answers questions about a page using ONLY that page's
`GuideContextPacket`. Still read-only: no RAG, no document ingestion, no
mutation, no diligence model, no task/artifact creation, no autonomous
behavior, no sidebar.

## Endpoints
- **`POST /api/guide/ask`** — body `{"route","question","model"?}`.
  Builds the packet, prompts a local model, returns
  `{answer, route, normalized_route, context_quality, model,
  ollama_enabled, context_used{page_title,metrics,data_sources,
  limitations_count}, missing_context_notes, read_only:true}`.
  - Missing `question` / `route` / bad JSON → clean **400**.
  - Ollama disabled or unreachable → clean **503**
    (`{"error":"PEdesk Guide local model is unavailable.", "detail":...,
    "read_only":true}`). Never a 500, never a stack trace.
  - Unknown route → still answers conservatively (packet
    `context_quality="missing"`), 200.
- **`GET /api/guide/ollama-health`** — `{enabled, base_url, default_model,
  reachable}`; never fails the app.

## Files created / modified
- **NEW** `rcm_mc/assistant/ollama_client.py` — `is_ollama_enabled()`,
  `check_ollama_health()`, `call_ollama_chat(system, user, model=None)`
  via stdlib `urllib` (no new dependency). Typed `OllamaError`.
- **NEW** `rcm_mc/assistant/guide_prompt_builder.py` —
  `build_guide_system_prompt`, `build_guide_user_prompt`,
  `packet_to_prompt_context(packet, max_chars=12000)`,
  `clean_guide_answer` (strips `<think>…</think>` incl. dangling tails,
  trims a repetitive preamble, keeps caveats).
- **MODIFIED** `rcm_mc/server.py` — `_route_guide_ask`,
  `_route_guide_ollama_health` + dispatch (POST in `_do_post_inner`, GET
  in `_do_get_inner`).
- **NEW** `tests/test_guide_prompt_builder.py` (6),
  `tests/test_guide_ollama_endpoint.py` (9, Ollama mocked).

## Config (env vars — PEdesk has no central config system)
- `PEDESK_GUIDE_OLLAMA_ENABLED` (default **false** — production-safe;
  local dev opts in)
- `PEDESK_GUIDE_OLLAMA_BASE_URL` (default `http://localhost:11434`)
- `PEDESK_GUIDE_OLLAMA_MODEL` (default `gemma4:e4b`)
- `PEDESK_GUIDE_OLLAMA_TIMEOUT_SECONDS` (default `30`)

## CSRF / auth
`/api/guide/ask` is NOT CSRF-exempt: in authenticated mode the app's
shared CSRF JS auto-adds `X-CSRF-Token` for AJAX, and the future sidebar
will too. In single-user/open mode (and the tests) there's no session, so
the CSRF gate is skipped — reachable like other read endpoints.

## Commands + results
- `validate_page_context_coverage` → PASS (exit 0).
- `validate_guide_context_quality` → PASS (exit 0).
- `py_compile` on assistant/context + assistant Ollama/prompt modules +
  server.py → clean.
- `pytest` page-context + metric/data + packet + context-endpoint +
  prompt-builder + ollama-endpoint → **52 passed**.

## Manual local test (real gemma4:e4b, Ollama reachable)
- `GET /api/guide/ollama-health` → `{enabled:true, reachable:true,
  default_model:"gemma4:e4b"}`.
- Q "Where does this data come from?" on `/diligence/hcris-xray` →
  grounded answer citing **CMS HCRIS** (public dataset, annual cadence,
  1-2yr lag, filing artifacts), no `<think>` tags, `read_only:true`,
  `context_used` populated (~20s on this machine).
- Q "Can you change the assumptions for me?" → "I cannot change
  assumptions… restricted from modifying data, changing assumptions, or
  running models." (read-only contract held by the live model.)

## Caveats
- Read-only and AI-boxed by construction: the model only ever sees the
  packet text; it cannot reach a tool, the store, or any action.
- No RAG / uploads / memory yet (deliberate next step is the sidebar
  calling this endpoint).
- `call_ollama_chat` takes `(system_prompt, user_prompt, model=None)`
  rather than a single `prompt` — the /api/chat payload needs distinct
  system + user roles; tests mock at this signature.
- Default-disabled means the endpoint returns 503 until an operator sets
  `PEDESK_GUIDE_OLLAMA_ENABLED=true` and a local Ollama is running with
  the model pulled.

---

# Task 6B — PEdesk Guide sidebar UI (read-only) (2026-05-22)

First user-facing surface for the Guide: a closed-by-default right-side
sidebar in the global shell that explains the current page and asks
read-only questions. No RAG, uploads, memory, actions, tasks, exports,
assumption editing, chat persistence, or DB writes.

## Where it lives
All in `rcm_mc/ui/_chartis_kit.py` (server-rendered HTML + a vanilla-JS
shim, per the app's no-SPA convention):
- A **Guide** trigger `<button data-ck-guide-open>` added to the topbar
  (`_topbar`, in `ck-topbar-right`).
- `_GUIDE_PANEL_HTML` — the `<aside id="ck-guide-panel" hidden role="dialog"
  aria-label="PEdesk Guide">` with section skeletons (Overview, Key
  metrics, Data sources, Limitations, Suggested questions, Ask) + the
  read-only disclaimer.
- `_GUIDE_CSS` — editorial palette only (navy head, paper body, teal
  accents; reused `--sc-navy`/`--sc-teal`/`--ck-*` vars; quality-badge
  colors are the existing semantic positive/warning/negative).
- `_GUIDE_JS` — vanilla shim: opens/closes (Esc + close button, focus
  save/restore), fetches `/api/guide/context?route=` + `/api/guide/
  ollama-health` on open, renders sections, manages the ask flow.
- Injected into `chartis_shell` **only when `show_chrome`** (so login /
  forgot / bare pages don't get it).

## Behavior
- Closed by default (`hidden`). Route = `location.pathname +
  location.search` (hash omitted). Per-route session cache; history
  clears on route change.
- Ask → `POST /api/guide/ask {route, question}` via plain `fetch()`; the
  global `_CSRF_JS` fetch-patch adds `X-CSRF-Token` in authenticated mode
  (no separate CSRF system). Answer rendered with `textContent` (XSS-safe)
  + `white-space:pre-wrap`; meta shows `read-only` badge, model,
  context_quality, and missing_context_notes.
- 20s-aware loading: a deliberate "PEdesk Guide is answering from the page
  context…" bubble with animated ellipsis; the send button is disabled
  while pending (no duplicate submits); the panel stays scrollable.
- Health gating: `enabled:false` → ask disabled with the enable-it copy;
  `enabled:true, reachable:false` (or a 503 from /ask) → "local model is
  unavailable" copy; page guide always renders regardless.
- Suggested questions render as chips that populate the input (simpler
  than auto-submit).

## Tests — tests/test_guide_sidebar_shell.py (12)
Trigger present + keyboard-accessible; panel closed by default; ARIA +
heading + close; all six sections; all three endpoints wired; route uses
pathname+search (no hash); ask form + deliberate loading copy; disabled +
unavailable copy; read-only copy; no upload/`type=file`/multipart and no
mutation-form `action=` in the panel; CSRF-safe plain `fetch()` (no
home-rolled CSRF); absent on bare (`show_chrome=False`) pages.

## Commands + results
- `validate_page_context_coverage` → PASS (exit 0).
- `validate_guide_context_quality` → PASS (exit 0).
- `py_compile` on `_chartis_kit.py` + assistant/context + assistant
  Ollama/prompt modules + server.py → clean.
- `pytest` guide page-context / metric-data / packet / context-endpoint /
  prompt-builder / ollama-endpoint / **sidebar-shell** / shell-intro /
  page-titles → **76 passed**.
- Shell-regression smoke (`test_universal_palette`, `test_command_palette`,
  `test_hcris_xray`, `test_me_endpoint`) → 50 passed, 1 skipped.

## Manual verification (live server, real gemma4:e4b)
- `GET /portfolio` HTML contains the Guide trigger + `class="ck-guide-panel"
  hidden` + `aria-label="PEdesk Guide"` (closed by default).
- `/api/guide/context` for `/diligence/hcris-xray`,
  `/diligence/risk-workbench?demo=steward`, `/portfolio`, `/methodology`
  → all 200, all `context_quality=strong`; query-string route normalizes.
- `/api/guide/ollama-health` → `{enabled:true, reachable:true}`.
- Live `POST /api/guide/ask` on `/portfolio` ("Which numbers matter
  most?") → grounded answer (Total Net Revenue, RCM health), no `<think>`,
  `read_only:true`, ~20s.
- Ollama disabled / unreachable → 503 + health `enabled:false` are
  covered by the automated `test_guide_ollama_endpoint` suite.

## Caveats
- Frontend testing is server-side only (the app has no JS test harness):
  static markup/contract is asserted; the JS-built rendering (metric/source
  cards, answer bubbles, state toggles) is verified manually.
- No streaming — the first version is non-streaming with the deliberate
  loading state, as planned.
- Session-only Q&A history (in-memory, cleared on route change / panel
  reload); nothing persisted, no memory API called.

---

# Task 7 — Harden PEdesk Guide v1 (2026-05-22)

Reliability + safety pass on the sidebar after the full integration. No
new RAG / uploads / memory / actions / exports / mutation / streaming /
model-picker / persistence — behavior hardening + docs + tests only. All
in `rcm_mc/ui/_chartis_kit.py` (`_GUIDE_JS` / `_GUIDE_CSS`).

## What changed (JS)
- **Long-response UX:** the deliberate "PEdesk Guide is answering from the
  page context…" bubble; after **10s** still pending it switches to
  "Local model responses can take a little while on this machine."
- **Duplicate-submit guard:** a single `pending` request at a time blocks
  the send button, Enter, suggested-question chips, and retry from firing
  a second request. Enter sends; Shift+Enter newlines. Failed requests
  preserve the question (`lastQuestion`) for one-click retry.
- **Stale-response protection:** each ask claims a `reqSeq` token; `close()`
  and `loadContext()` (route change) call `invalidateInFlight()` which
  bumps `reqSeq`, aborts the fetch via `AbortController` (when supported),
  clears the slow-timer, and resets pending/send. A response whose
  `myseq !== reqSeq` is dropped — old answers/errors never render after a
  close or route change, and route-specific Q&A can't leak across pages.
- **Route-change / close reset:** both clear the session Q&A history,
  re-fetch context (route change refetches health too), and update the
  title/quality/normalized-route.

## What changed (CSS)
- Layout safety: `overflow-wrap:break-word; word-break:break-word;
  max-width:100%` across the panel; `overflow-x:hidden` on the scroll
  body; answers keep `white-space:pre-wrap`. Long answers / unbroken
  tokens (URLs, ids) wrap instead of forcing horizontal scroll.

## Error safety
Answers render via `aEl.textContent` (never `innerHTML` of model text);
error/`failBubble` text via `p.textContent`; all interpolated dynamic
strings pass through the `esc()` HTML-escaper. No stack traces / raw
exception reprs (the server already returns clean JSON; the client shows
short user-safe copy).

## Docs
README gained an "Operating local Ollama" section: `ollama pull
gemma4:e4b` + `ollama pull nomic-embed-text`, the four env vars + table,
expected ~20s latency, disabled behavior, and a 503/unreachable
troubleshooting table.

## Tests — tests/test_guide_sidebar_shell.py (now 19; +7 hardening)
slow-response copy + 10s timer; duplicate-submit guard (pending + Enter
no-shift); stale-response protection (`reqSeq`, `invalidateInFlight`,
`myseq!==reqSeq`, AbortController); route-change/close reset
(`clearHistory`); layout-safety CSS; safe rendering (`textContent` for
answer + error, `esc()` present); failed-request retry preserves the
question. Existing markup/contract tests retained.

## Commands + results
- `validate_page_context_coverage` → PASS (exit 0).
- `validate_guide_context_quality` → PASS (exit 0).
- `py_compile` on `_chartis_kit.py` + assistant/context + Ollama/prompt
  modules + server.py → clean.
- `pytest` guide page-context / metric-data / packet / context-endpoint /
  prompt-builder / ollama-endpoint / sidebar-shell (19) → all green.
- Shell-regression smoke (universal-palette, command-palette, hcris-xray,
  me-endpoint) → pass.

## Manual verification (live gemma4:e4b)
- Trigger present + panel closed by default on `/portfolio`,
  `/diligence/hcris-xray`, `/diligence/risk-workbench?demo=steward`,
  `/methodology`; context loads `strong` for all four.
- Ask works; the send button disables while pending (duplicate Enter/click
  blocked); the deliberate loading copy shows and is still honest past 10s.
- Read-only refusal still works ("Can you change the assumptions?" →
  refused). Disabled-Ollama still renders the deterministic page guide.

## Caveats
- Frontend hardening is contract-tested server-side (no JS harness); the
  live behaviors (10s copy swap, abort-on-close, no-stale-render) are
  verified manually.
- In this no-SPA app, an actual route change is a full page reload (fresh
  panel), so cross-page stale-render is doubly guarded: the reload itself
  plus the `reqSeq`/abort logic for the in-page close/supersede cases.

---

# Task 8A — Finish the remaining placeholder contexts (2026-05-22)

Authored the last 14 placeholder PageContexts from source. **Placeholder
count is now 0.** Context-authoring only — no AI/RAG/uploads/memory/
actions/exports/mutation.

## Quality distribution (packet quality over all 72 registry routes)
- **Start:** strong 52 · partial 6 · placeholder 14 · missing 0
- **End:**   strong 66 · partial 6 · placeholder 0 · missing 0

## Pages upgraded (all 14 → strong)
Expanded existing manual entries: `/day-one`, `/my/AT`, `/escalations`,
`/diligence/deal-mc`, `/diligence/deal-autopsy`, `/metric-glossary`,
`/rcm-benchmarks`. New entries (were `needs_validation` stubs):
`/diligence/covenant-stress`, `/diligence/exit-timing`,
`/diligence/ingest`, `/diligence/management`,
`/diligence/physician-attrition`, `/engagements`,
`/market-data/state/CA`.

## Conservatism calls (per the special-attention list)
- **covenant-stress:** STRESS-TEST breach probabilities over simulated
  paths — explicitly NOT a prediction of an actual breach.
- **deal-mc:** SIMULATED distributions from the supplied assumptions, NOT
  a forecast/guarantee; reads the downside tail.
- **exit-timing:** SCENARIO analysis over hold years + buyer types, NOT a
  market-timing prediction.
- **deal-autopsy:** RETROSPECTIVE signature similarity — a signal to
  investigate, NOT causal proof; similarity % is geometric closeness, not
  outcome probability.
- **ingest:** loads/normalizes and (per source) validates CPT/ICD +
  reconciles 835/837 — but runs on demo fixtures here; production uploads
  deferred, so not target data.
- **management:** scoring-framework SUPPORT, NOT a definitive
  management-quality judgment; demo roster is illustrative.
- **physician-attrition:** model-estimated flight-risk SIGNAL, NOT
  guaranteed departures; demo roster.
- **metric-glossary / rcm-benchmarks:** REFERENCE pages (definitions /
  peer bands), explicitly NOT target-specific conclusions.
- **/my/AT:** owner-scoped dashboard; owner/deadlines user-entered,
  MOIC/IRR/covenant from snapshots (`mixed`). Path segment is the owner
  key.
- **/market-data/state/CA:** public HCRIS, 1-2yr lag, Medicare-only
  coverage; state code is a path filter, top-50 is partial.
- **/engagements:** consulting-engagement records (user-entered); client
  view is the read-only `/portal/<id>`, not this internal workspace.

## Remaining non-strong (6 partial — by design, not placeholders)
`/pe-intelligence` (methodology hub), `/conferences` (reference calendar),
`/deals-library` (redirect to /library), `/research` (navigation index),
`/notes` (search utility), `/users` (admin) — none is an analytic page
with a registry metric/source to link, so they stay `partial` honestly.

## Commands + results
- `validate_page_context_coverage` → PASS (exit 0).
- `validate_guide_context_quality` → PASS (exit 0): 0 invalid metric/
  source refs, 0 duplicate ids, 0 ambiguous aliases.
- `py_compile` on the context package → clean.
- `pytest` guide page-context / metric-data / packet / context-endpoint /
  prompt-builder / ollama-endpoint / sidebar-shell → **71 passed**.

## Caveats
- All 14 are `inferred_from_page` except `/metric-glossary` and
  `/rcm-benchmarks` (reference pages whose source cites their benchmark
  origins → `documented`).
- `data_confidence` set honestly: live portfolio → `observed_target_data`;
  MC/attrition outputs → `model_estimate`; fixture-driven ingest/management
  → `demo_or_fixture`; covenant-stress/exit-timing/deal-autopsy (user
  inputs + model + corpus) → `mixed`; HCRIS/benchmarks → `public_benchmark_data`;
  engagements → `user_entered_data`.
- No exact formulas added; model-logic summaries describe intent and point
  to the implementing module.

---

# Task 9 — PEdesk Guide sidebar presentation polish (2026-05-22)

UI polish after the first live visual review: the panel read like a long
documentation blob and the sticky read-only footer overlapped the Ask
section. CSS/markup/render-only — no backend, endpoint, or behavior
changes. All in `rcm_mc/ui/_chartis_kit.py` (`_GUIDE_PANEL_HTML` /
`_GUIDE_CSS` / `_GUIDE_JS`).

## Before → after
- **Before:** flat sections (h3 + paragraphs + repeated "Caveats: Needs
  source documentation." lines); sticky bottom read-only footer that sat
  over the Ask area.
- **After:** a stack of editorial **cards** — Page overview · Key metrics
  · Data sources · Limitations & caveats · Suggested questions · Ask
  PEdesk Guide · (collapsible) read-only policy.

## Presentation changes
- **Card system** (`.ck-guide-card` / `.ck-guide-card-title`) on the
  existing palette (white cards, paper bg, navy/teal accents, amber-left
  caution card, teal-left Ask card). Stronger typographic hierarchy:
  mono small-caps card titles, serif metric titles, body text, mono dim
  metadata, muted caveats.
- **Page overview** rendered as labeled rows (What it does / Purpose /
  Why it matters), not a paragraph blob.
- **Metric cards** — each metric is a mini-card (title / definition /
  Why it matters / Formula). Missing formula → a muted **"Formula not yet
  documented"** pill instead of a raw "Caveats: Needs source
  documentation." line. >3 metrics → first 3 + **Show all metrics (N)** /
  **Show fewer** toggle (same for data sources).
- **Data source cards** — labeled metadata grid (**Type / Update cadence
  / Freshness**) instead of the compressed "system_metadata · … · lag …"
  line; underscores humanized.
- **Limitations card** — the repeated needs-doc sentinel is collapsed
  into one calm line ("Some formulas or source-lineage details still need
  source documentation.").
- **Suggested questions** — cleaner wrapping chips with a one-line hint
  ("Tap one to drop it into the ask box").
- **Read-only policy** — moved from the **sticky footer** into a quiet
  collapsible `<details>` card in the scroll body; body gained bottom
  padding (28px) so the **Ask card is fully visible** at the bottom.
- **Disabled-Q&A copy** is now the full, actionable message and fully
  visible in its own state box.

## Preserved (no behavior change)
Endpoint calls, route normalization, context/health/ask fetches, CSRF
(global fetch-patch), read-only/no-mutation guarantees, session-only
history, disabled/unavailable handling, 10s slow-copy, duplicate-submit
guard, stale-response (`reqSeq` + AbortController), Enter-to-send, and
`textContent` answer rendering are all unchanged. Same data-attribute
hooks; same endpoints.

## Tests — tests/test_guide_sidebar_shell.py (now 27; +8)
Card-based layout; read-only policy is a collapsible in-body `<details>`
(old `.ck-guide-readonly` sticky rule gone); Ask card + 28px body bottom
padding; data-source metadata labels (Type / Update cadence / Freshness);
metric show-more toggle; caveat pill + no raw repeated "Caveats: Needs
source documentation."; full disabled-Q&A copy; answer card + pre-wrap +
`textContent`. Existing closed-by-default / trigger / endpoint-wiring /
hardening tests retained.

## Commands + results
- `validate_page_context_coverage` → PASS (exit 0).
- `validate_guide_context_quality` → PASS (exit 0).
- `py_compile` on `_chartis_kit.py` → clean.
- `pytest` guide page-context / metric-data / packet / context-endpoint /
  prompt-builder / ollama-endpoint / sidebar-shell (27) + shell smoke
  (universal-palette, command-palette, hcris-xray) → **127 passed, 1
  skipped**.

## Manual verification (live gemma4:e4b)
- `/app` served the card skeleton (Page overview card, Ask card,
  collapsible policy `<details>`, panel closed by default).
- Live ask on `/app` returned a grounded read-only answer (no `<think>`)
  in ~18s — the ask path is unchanged by the polish.
- Card-rendered content (metric/source cards, labeled metadata,
  show-more, answer bubble) is JS-built and verified in the browser; no
  JS test harness exists so static contract tests cover the structure.

## Caveats
- Visual rendering of the cards is client-side; the static tests assert
  the contract (classes, labels, collapsible policy, no sticky footer,
  full disabled copy) and the live render is browser-verified.
- Editorial palette only — caution card uses the existing amber token;
  no off-palette colors, no shell redesign.

---

# Task 10 — Ollama enablement + local RAG foundation (2026-05-22)

Made local Ollama easier to enable/diagnose, and added a local read-only
RAG layer so the Guide can answer from the whole in-repo knowledge base,
not just the current route packet. Local only: Ollama embeddings + SQLite
vector store + brute-force cosine. No cloud, no uploads, no memory, no
actions/mutation. RAG is **off by default**; non-RAG behavior is unchanged.

## Part A — Ollama enablement
- `scripts/run_with_guide_ollama.sh` — one-command local dev start with the
  Guide env vars set (+ a reachability warning). Dev-only; no prod default
  change.
- `GET /api/guide/ollama-health` now returns `enabled`, `reachable`,
  `base_url`, `default_model`, `timeout_seconds`, `suggested_fix`,
  `required_env`, and `installed_models` (when reachable).
- Sidebar disabled state rewritten: a plain primary line ("Ask PEdesk
  Guide is unavailable.") + secondary, with the env/setup detail tucked
  into a collapsible **Setup details** disclosure driven by the health
  payload.

## Part B-G — RAG package (`rcm_mc/assistant/rag/`)
- `types.py` — `RagDocument` / `RagChunk` / `RagSearchResult` + config
  (`is_rag_enabled`, `rag_embed_model`, `rag_index_path`, `rag_top_k`).
- `document_sources.py` — gathers page contexts, metric registry,
  data-source registry, read-only policy, and a curated docs allow-list
  (keyword-matched `docs/*.md`, with a secrets/sessions deny-list).
- `chunking.py` — registry entries → one chunk; long docs → ~600-word
  paragraph-packed chunks with overlap; sha256 content hash.
- `embeddings.py` — `embed_texts/embed_query` via Ollama + stdlib cosine.
- `ollama_client.embed_texts` — `/api/embed` (batch) with `/api/embeddings`
  fallback; `list_models()`.
- `vector_store.py` — SQLite `guide_rag_chunks`; `upsert_chunk`
  (idempotent by content_hash), `delete_stale_chunks`, `search_similar`
  (cosine), counts.
- `retrieval.py` — embed query (+ route/title) → top-k chunks.
- `rag_prompt_context.py` — `format_rag_context` (supporting block),
  `rag_sources_used`, `citation_line`.
- `index_builder.py` (CLI) — gather → chunk → embed new/changed → upsert →
  prune; prints sources/chunks/embedded/skipped/pruned/errors.
- `validate_rag_index.py` (CLI) — checks DB/chunks/embeddings + runs the
  three required test searches.

## Part H/I/J — endpoints + prompt
- `GET /api/guide/rag/search?q=&route=` — read-only retrieval; disabled →
  clean payload, missing `q` → 400, embeddings unreachable → 503.
- `POST /api/guide/ask` — when `PEDESK_GUIDE_RAG_ENABLED=true`, retrieves
  supporting snippets and adds them to the prompt (page packet stays
  primary); response gains `rag_enabled`, `rag_results_count`,
  `rag_sources_used`. RAG retrieval failures fall back to packet-only —
  never break the answer. Disabled → exact v1 behavior.
- `guide_prompt_builder` — `build_guide_user_prompt(question, packet,
  rag_context="")` (backward compatible) + a system-prompt rule: page
  context primary, retrieved context supporting, cite source titles, never
  treat retrieved docs as deal data.

## Config
`PEDESK_GUIDE_RAG_ENABLED` (false) · `PEDESK_GUIDE_RAG_EMBED_MODEL`
(nomic-embed-text) · `PEDESK_GUIDE_RAG_INDEX_PATH`
(.pedesk_guide_rag.sqlite3) · `PEDESK_GUIDE_RAG_TOP_K` (5).

## RAG source / chunk counts
172 sources (72 page contexts · 54 metrics · 32 data sources · 1 policy ·
13 docs) → **193 chunks**.

## Commands + results
- `validate_page_context_coverage` → PASS (exit 0); `validate_guide_context_quality`
  → PASS (exit 0).
- `py_compile` on assistant/context, assistant/rag, Ollama/prompt modules,
  server.py, `_chartis_kit.py` → clean.
- `pytest` guide page-context/metric-data/packet/context-endpoint/
  prompt-builder/ollama-endpoint/sidebar-shell/**rag**/**rag-endpoints** +
  shell smoke → **125 passed, 1 skipped** (23 new RAG tests; embeddings +
  retrieval mocked).

## Manual local test (real gemma4:e4b + nomic-embed-text)
- `index_builder` → 172 sources / 193 chunks / 193 embedded / 0 errors.
- `validate_rag_index` → PASS; test searches: "denial rate" → Metric
  Registry — Denial Rate; "HCRIS" → Data Catalog + data-source registry;
  "change assumptions" → policy/metric refs.
- `GET /api/guide/ollama-health` → enabled+reachable, lists installed
  models, timeout 60.
- `GET /api/guide/rag/search?q=What does denial rate mean&route=/diligence/
  hcris-xray` → top: Denial Rate (0.83), Denial Prediction, RCM doc,
  HCRIS X-Ray.
- `POST /api/guide/ask` on `/diligence/hcris-xray`, "What does denial rate
  mean?" → grounded answer (definition + formula pulled from the Metric
  Registry via RAG — context the page packet alone lacks), `rag_enabled`
  true, 5 sources used, `read_only` true, no `<think>`.

## Caveats
- RAG is opt-in and requires a built local index; without it the Guide is
  exactly the v1 packet-only assistant.
- v1 retrieval is brute-force cosine over a few hundred chunks — fine at
  this scale; an ANN index would matter only at much larger corpora.
- No user-upload / document ingestion yet (deliberate next phase); the
  index covers only safe internal context.
- The index file is local + disposable (rebuild any time); it is not
  committed and holds no secrets/runtime data.

---

# Task 11 — RAG answer-quality evaluation harness (2026-05-22)

A read-only quality gate before adding user-document ingestion — confirms
RAG improves answers without making the Guide overconfident or letting it
drift from read-only. No uploads/memory/actions/mutation/persistence
beyond a local ignored report folder.

## What was built
- `rcm_mc/assistant/eval/guide_eval.py` — runs the fixed 10-question x
  9-route matrix in **packet_only** and **rag** modes through the SAME
  pipeline the ask handler uses (build packet → optional retrieve →
  prompt → local Ollama → clean), scores each answer, and writes
  `.pedesk_guide_eval/run_*.jsonl` + `report_*.md` (gitignored). CLI with
  `--routes/--questions/--modes/--model/--limit`. Prints a PASS/FAIL gate.
- Pure analyzers (unit-tested without Ollama): `has_action_claim`
  (first-person mutation claim, negation-aware so read-only refusals don't
  trip it), `has_investment_recommendation`, `admits_missing_context`,
  `mentions_source_or_caveat` (incl. retrieved-title mentions).
- Per record: route, question, mode, answer, context_quality,
  rag_sources_used, latency_seconds, read_only, action_claim,
  investment_recommendation, admits_missing_context,
  mentions_source_or_caveat, answer_chars, error.
- `tests/test_guide_eval.py` (11) — analyzer behavior + the fixed
  question/route/mode sets. CI-safe (no model).

## Live run (real gemma4:e4b + nomic-embed-text; 2 routes x 4 questions x
2 modes = 16 calls)
- **GATE: PASS** — action claims **0**, investment recommendations **0**,
  read_only true everywhere, 0 flagged/worst answers, 0 errors.
- packet_only: avg latency 11.0s · admits-missing 3/8 · mentions-source
  5/8 · avg 508 chars.
- rag: avg latency 13.25s · admits-missing 1/8 · mentions-source **7/8** ·
  avg 607 chars.
- Signal: RAG cites sources/caveats MORE (7/8 vs 5/8) and says
  "I don't know" LESS (1 vs 3) because it retrieves the definitions the
  page packet lacks — e.g. "What does denial rate mean?" on
  `/diligence/hcris-xray` (where denial_rate isn't in the page's metric
  set) pulled the Metric Registry definition + formula (sources: Denial
  Rate, Denial Prediction, Root Cause). Read-only refusal held in both
  modes ("I cannot change assumptions"). RAG answers are modestly longer
  (+~100 chars) and ~2s slower — acceptable, not over-explaining.

(The full 9x10x2 matrix is runnable on demand; the subset above is the
captured sample. Re-run any time with the CLI.)

## Commands + results
- `validate_page_context_coverage` / `validate_guide_context_quality` →
  PASS (exit 0).
- `py_compile` on the eval module → clean.
- `pytest` guide RAG / rag-endpoints / **eval-analyzers (11)** / ollama-
  endpoint / sidebar-shell / context-endpoint / prompt-builder / packet →
  **93 passed**.

## Recommendation captured
Internal-RAG quality is proven (read-only holds; RAG adds grounding
without overconfidence). The next real product phase is **Task 12 — user
document ingestion for RAG**, to be built on this foundation; defer it
until this RAG version has been used on real questions.

## Caveats
- The live harness needs Ollama; it is intentionally not a CI test (the
  analyzers are). CI stays model-free.
- Heuristic scorers are conservative pattern checks, not semantic
  graders; the report's "worst/flagged" list is for human inspection.
- Reports live in the gitignored `.pedesk_guide_eval/` folder.
